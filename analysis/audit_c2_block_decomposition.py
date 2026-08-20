#!/usr/bin/env python3
"""Audit fixed block inputs, synthesize certificates, and bind the C2 census.

The restricted one-state extractor is source-bound and fail-closed.  It emits
explicit typed local games; a producer solves those games and emits succinct
rank-sum/kappa or losing-cylinder certificates; an independent consumer
rechecks the tables, factor contract, and witnesses.  Two public multistate
games exercise monitors, RS projections, nondeterministic outcomes, local
precedence, handover, winning and losing.  This remains post-hoc and is not a
general partition-discovery or arbitrary-LTS semantic parser.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence


ANALYSIS_DIR = Path(__file__).resolve().parent
if str(ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(ANALYSIS_DIR))

from check_factored_certificate import (  # noqa: E402
    FactorCertificateError,
    check_certificate,
    check_flat_equivalence,
    check_priority_execution,
    reconstruct_game,
)
from synthesize_factored_certificate import (  # noqa: E402
    GAME_SCHEMA_VERSION,
    SynthesisError,
    sha256_json,
    synthesize,
)


SCHEMA_VERSION = "fse2027-m8o-block-decomposition-audit-v1"
EXPECTED_K = (2, 4, 6, 8, 10, 12, 16, 20)
M8K_METHODS = frozenset({"fg_ducs_otf", "generic_lazy"})
CERTIFICATE_METRICS = {
    "revised_worst_completion_rank": lambda k: k,
    "revised_certificate_phase_masks": lambda k: k + 1,
    "revised_certificate_states": lambda k: k + 1,
    "revised_certificate_strategy_action_buckets": lambda k: k,
    "revised_certificate_strategy_transitions_unique": lambda k: k,
}


class AuditError(RuntimeError):
    """A fail-closed theorem or evidence mismatch."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AuditError(f"invalid JSON: {path}") from error
    if not isinstance(value, dict):
        raise AuditError(f"JSON root must be an object: {path}")
    return value


def safe_relative(base: Path, relative: str) -> Path:
    pure = PurePosixPath(relative)
    if pure.is_absolute() or not pure.parts or ".." in pure.parts:
        raise AuditError(f"unsafe manifest path: {relative}")
    candidate = base.joinpath(*pure.parts)
    if not candidate.is_file() or candidate.is_symlink():
        raise AuditError(f"manifest file is missing or unsafe: {candidate}")
    return candidate


def verify_manifest_file(base: Path, record: Mapping[str, Any]) -> Path:
    relative = record.get("path")
    digest = record.get("sha256")
    size = record.get("bytes")
    if not isinstance(relative, str) or not re.fullmatch(r"[0-9a-f]{64}", str(digest)):
        raise AuditError("invalid model manifest record")
    path = safe_relative(base, relative)
    if path.stat().st_size != size or sha256_file(path) != digest:
        raise AuditError(f"manifest identity mismatch: {relative}")
    return path


def action_occurrences(source: str) -> dict[str, list[tuple[str, str]]]:
    """Return action occurrences with a conservative enclosing process label."""
    current = "<none>"
    result: dict[str, list[tuple[str, str]]] = defaultdict(list)
    definition = re.compile(r"^\s*([A-Z][A-Z0-9_]*)\s*=\s*(?:\(|[A-Z])")
    transition = re.compile(r"([a-z][A-Za-z0-9_.]*(?:\[[0-9]+\])*)\s*->\s*([A-Z][A-Z0-9_]*)")
    for line in source.splitlines():
        match = definition.match(line)
        if match:
            current = match.group(1)
        for action, target in transition.findall(line):
            result[action].append((current, target))
    return dict(result)


def audit_independent_source(source: str, expected_k: int) -> dict[str, Any]:
    header = re.search(r"K=(?P<k>[0-9]+) independent one-state", source)
    if header is None or int(header.group("k")) != expected_k:
        raise AuditError("independent-family K header mismatch")
    old = set(re.findall(r"^OLD_COMPONENT_([0-9]+)\s*=\s*\(idle\s*->\s*OLD_COMPONENT_\1\)\.$", source, re.MULTILINE))
    new = set(re.findall(r"^NEW_COMPONENT_([0-9]+)\s*=\s*\(idle\s*->\s*NEW_COMPONENT_\1\)\.$", source, re.MULTILINE))
    relations = re.findall(
        r"^relation R_COMPONENT_([0-9]+)_FG = \{"
        r"OLD_COMPONENT_\1@OLD_COMPONENT_\1 = reconfigure_COMPONENT_\1 -> "
        r"NEW_COMPONENT_\1@NEW_COMPONENT_\1\}$",
        source,
        re.MULTILINE,
    )
    expected = {str(index) for index in range(1, expected_k + 1)}
    if old != expected or new != expected or set(relations) != expected:
        raise AuditError("independent family is not a K-block one-state frame product")
    if len(relations) != expected_k:
        raise AuditError("duplicate independent transfer relation")
    old_members = {f"OLD_COMPONENT_{index}" for index in expected}
    new_members = {f"NEW_COMPONENT_{index}" for index in expected}
    relation_members = {f"R_COMPONENT_{index}_FG" for index in expected}

    def composition_members(name: str) -> set[str]:
        match = re.search(
            rf"^\|\|{name}\s*=\s*\((?P<body>[^\n]+)\)\.$",
            source,
            re.MULTILINE,
        )
        if match is None:
            raise AuditError(f"{name} composition is missing")
        return {item.strip() for item in match.group("body").split("||") if item.strip()}

    if composition_members("OldEnvironment") != old_members:
        raise AuditError("OldEnvironment component list differs from the K blocks")
    if composition_members("NewEnvironment") != new_members:
        raise AuditError("NewEnvironment component list differs from the K blocks")
    if not re.search(
        r"controller\s+\|\|OldController\s*=\s*OldEnvironment~\{OldSpec\}\.", source
    ) or not re.search(
        r"controller\s+\|\|NewController\s*=\s*NewEnvironment~\{NewSpec\}\.", source
    ):
        raise AuditError("endpoint controller binding differs from the one-state family")
    updater_match = re.search(
        r"updatingController\s+IndependentFamily\s*=\s*\{(?P<body>.*?)\n\}",
        source,
        re.DOTALL,
    )
    if updater_match is None:
        raise AuditError("IndependentFamily updatingController is missing")
    updater = updater_match.group("body")

    def updater_set(field: str) -> set[str]:
        matches = re.findall(rf"\b{field}\s*=\s*\{{(?P<body>[^}}]*)\}}", updater)
        if len(matches) != 1:
            raise AuditError(f"IndependentFamily {field} field is missing or duplicated")
        members = [item.strip() for item in matches[0].split(",") if item.strip()]
        if len(members) != len(set(members)):
            raise AuditError(f"IndependentFamily {field} field has duplicate members")
        return set(members)

    scalar_fields = {
        "oldController": "OldController",
        "newController": "NewController",
        "oldGoal": "OldSpec",
        "newGoal": "NewSpec",
    }
    for field, expected_value in scalar_fields.items():
        values = re.findall(rf"\b{field}\s*=\s*([A-Za-z0-9_]+)", updater)
        if values != [expected_value]:
            raise AuditError(f"IndependentFamily {field} binding differs")
    if updater_set("oldEnvironment") != old_members:
        raise AuditError("updatingController oldEnvironment list differs from the K blocks")
    if updater_set("newEnvironment") != new_members:
        raise AuditError("updatingController newEnvironment list differs from the K blocks")
    if updater_set("mapRelation") != relation_members:
        raise AuditError("updatingController mapRelation list differs from the K blocks")
    if not all(flag in updater for flag in ("nonblocking", "revised_on_the_fly", "fine_grained")):
        raise AuditError("updatingController mode flags differ from the registered family")
    targets = re.findall(
        r"^\|\|UPDATE_CONTROLLER_OTF_FG\s*=\s*([A-Za-z0-9_]+)\.$",
        source,
        re.MULTILINE,
    )
    if targets != ["IndependentFamily"]:
        raise AuditError("restricted updating-controller target differs")
    declared_relations = set(re.findall(r"^relation\s+([A-Za-z0-9_]+)\s*=", source, re.MULTILINE))
    if declared_relations != relation_members:
        raise AuditError("relation declarations differ from the updatingController map")
    if not re.search(r"^set ControllableActions = \{idle\}$", source, re.MULTILINE):
        raise AuditError("shared idle action is not declared controllable")
    forbidden = ("safety =", "transition =", "startNewSpec", "precedes", "dependency")
    if any(token in source for token in forbidden):
        raise AuditError("independent family has a cross-block requirement or dependency")
    occurrences = action_occurrences(source)
    idle = occurrences.get("idle", [])
    if len(idle) != 2 * expected_k or any(process != target for process, target in idle):
        raise AuditError("shared idle is not a pure foreign-action stutter")
    reconfiguration_actions = set(re.findall(r"reconfigure_COMPONENT_([0-9]+)", source))
    if reconfiguration_actions != expected:
        raise AuditError("block-local reconfiguration actions are incomplete")
    return {
        "block_count": expected_k,
        "declared_action_partition": "block-local reconfiguration plus shared controllable pure stutter",
        "cross_block_precedence": 0,
        "requirements": 0,
        "endpoint_component_lists_checked": True,
        "updating_controller_lists_checked": True,
        "pure_shared_stutter_checked": True,
        "semantic_factor_conditions_independently_checked": True,
        "expected_flat_states": 2**expected_k,
        "expected_factored_table_states": 2 * expected_k,
        "expected_composed_rank": expected_k,
    }


COMPOSITION = {
    "state_space": "cartesian_product",
    "initial_states": "cartesian_product",
    "safe": "conjunction",
    "goal": "cartesian_product",
    "load_states": "cartesian_product",
    "handover": "cartesian_product",
    "post": "exact_asynchronous_one_block_frame",
    "foreign_monitor_actions": "stutter",
    "foreign_rs_actions": "stutter",
    "pending_and_precedence": "block_local",
    "shared_action_post": "global_self_loop",
}


def independent_local_game(model_id: str, model_sha256: str, k: int) -> dict[str, Any]:
    """Translate the checked restricted one-state grammar into typed tables."""
    blocks = []
    for index in range(1, k + 1):
        action = f"reconfigure_COMPONENT_{index}"
        old = f"old_{index}"
        new = f"new_{index}"
        monitor = f"monitor_{index}"
        residual = f"residual_{index}"
        load = f"image_{index}"
        blocks.append(
            {
                "id": f"COMPONENT_{index}",
                "states": [old, new],
                "state_annotations": {
                    old: {
                        "physical": old,
                        "physical_safe": True,
                        "monitor": monitor,
                        "rs_residual": residual,
                        "pending_actions": [action],
                    },
                    new: {
                        "physical": new,
                        "physical_safe": True,
                        "monitor": monitor,
                        "rs_residual": residual,
                        "pending_actions": [],
                    },
                },
                "initial_states": [old],
                "safe_states": [old, new],
                "goal_states": [new],
                "load_states": [load],
                "action_annotations": {
                    action: {"controllability": "controllable", "kind": "handover"}
                },
                "transitions": [{"source": old, "action": action, "targets": [new]}],
                "monitor": {
                    "states": [monitor],
                    "initial_states": [monitor],
                    "error_states": [],
                    "default": "stutter",
                    "transitions": [],
                },
                "rs_observer": {
                    "states": [residual],
                    "initial_states": [residual],
                    "error_states": [],
                    "default": "stutter",
                    "transitions": [],
                },
                "precedence_edges": [],
                "handover_relation": {new: [load]},
                "foreign_actions_stutter": True,
            }
        )
    return {
        "schema_version": GAME_SCHEMA_VERSION,
        "id": f"{model_id}-typed-factor-game",
        "source_model": {
            "id": model_id,
            "sha256": model_sha256,
            "kind": "restricted-one-state-lts-extraction",
        },
        "shared_controllable_pure_stutter": ["idle"],
        "cross_block_precedence": [],
        "cross_block_requirements": [],
        "composition": dict(COMPOSITION),
        "blocks": blocks,
    }


def load_multistate_games(path: Path) -> list[tuple[dict[str, Any], str]]:
    document = load_json(path)
    if document.get("schema_version") != "fg-ducs-explicit-local-games-v1":
        raise AuditError("multistate game schema differs")
    cases = document.get("cases")
    if not isinstance(cases, list) or len(cases) != 2:
        raise AuditError("multistate game case count differs")
    source_hash = sha256_file(path)
    result = []
    for case in cases:
        if not isinstance(case, dict):
            raise AuditError("multistate game case is invalid")
        expected = case.get("expected_decision")
        if expected not in {"realizable", "unrealizable"}:
            raise AuditError("multistate expected decision differs")
        game = {
            "schema_version": GAME_SCHEMA_VERSION,
            "id": case.get("id"),
            "source_model": {
                "id": path.name,
                "sha256": source_hash,
                "kind": "explicit-multistate-typed-local-games",
            },
            "shared_controllable_pure_stutter": case.get("shared_controllable_pure_stutter"),
            "cross_block_precedence": case.get("cross_block_precedence"),
            "cross_block_requirements": case.get("cross_block_requirements"),
            "composition": case.get("composition"),
            "blocks": case.get("blocks"),
        }
        result.append((game, expected))
    return result


def audit_travel_negative_control(source: str) -> dict[str, Any]:
    occurrences = action_occurrences(source)
    witnesses: dict[str, list[tuple[str, str]]] = {}
    for action in ("agency.succ", "agency.fail"):
        entries = occurrences.get(action, [])
        processes = {process for process, _ in entries}
        nonstutter = [(process, target) for process, target in entries if process != target]
        if len(processes) < 2 or not nonstutter:
            raise AuditError(f"Travel negative-control witness missing: {action}")
        witnesses[action] = nonstutter
    return {
        "passes_independent_family_syntax": False,
        "reason": "shared nonstuttering completion actions couple agency and services",
        "shared_nonstuttering_actions": sorted(witnesses),
        "witness_occurrence_counts": {
            action: len(occurrences[action]) for action in sorted(witnesses)
        },
    }


def read_csv(path: Path) -> list[dict[str, str]]:
    try:
        with path.open(encoding="utf-8", newline="") as source:
            return list(csv.DictReader(source))
    except (OSError, UnicodeDecodeError, csv.Error) as error:
        raise AuditError(f"invalid CSV: {path}") from error


def parse_k(model_id: str) -> int:
    match = re.fullmatch(r"independent_k(?P<k>[0-9]{2})", model_id)
    if match is None:
        raise AuditError(f"unexpected independent model id: {model_id}")
    return int(match.group("k"))


def require_int(row: Mapping[str, str], field: str) -> int:
    try:
        return int(row[field])
    except (KeyError, ValueError) as error:
        raise AuditError(f"invalid integer field {field}") from error


def audit_m8k_rows(rows: Sequence[Mapping[str, str]]) -> list[dict[str, Any]]:
    selected = [row for row in rows if row.get("model_id", "").startswith("independent_k")]
    if len(selected) != 80:
        raise AuditError(f"M8k independent job count mismatch: {len(selected)}")
    counts = Counter((row["model_id"], row["method_id"]) for row in selected)
    expected_pairs = {
        (f"independent_k{k:02d}", method): 5
        for k in EXPECTED_K
        for method in M8K_METHODS
    }
    if dict(counts) != expected_pairs:
        raise AuditError("M8k independent method/repetition matrix mismatch")
    summaries = []
    for row in selected:
        k = parse_k(row["model_id"])
        if (
            row.get("process_status") != "SUCCESS"
            or row.get("revised_decision") != "realizable"
            or row.get("internal_certificate_check") != "passed"
            or row.get("link_checker") != "passed"
        ):
            raise AuditError(f"M8k correctness gate failed: {row.get('job_id')}")
        if require_int(row, "certificate_states") != k + 1:
            raise AuditError(f"M8k certificate census mismatch: {row.get('job_id')}")
        if row["method_id"] == "fg_ducs_otf":
            states = require_int(row, "states_discovered")
            queries = require_int(row, "successor_queries")
            if states != k or queries != k:
                # Current M8k records K for semantic states, while the paper's
                # flat root-to-goal chain has K+1 certificate phase masks.
                if not (states == k + 1 and queries == k):
                    raise AuditError(f"M8k OTF census mismatch: {row.get('job_id')}")
        summaries.append(
            {
                "job_id": row["job_id"],
                "model_id": row["model_id"],
                "k": k,
                "method": row["method_id"],
                "status": row["process_status"],
                "states_discovered": require_int(row, "states_discovered"),
                "successor_queries": require_int(row, "successor_queries"),
                "certificate_states": require_int(row, "certificate_states"),
            }
        )
    return summaries


def audit_certificate_metrics(rows: Sequence[Mapping[str, str]]) -> None:
    selected = [
        row
        for row in rows
        if row.get("model_id", "").startswith("independent_k")
        and row.get("metric_key") in CERTIFICATE_METRICS
    ]
    expected = 80 * len(CERTIFICATE_METRICS)
    if len(selected) != expected:
        raise AuditError(f"certificate metric count mismatch: {len(selected)} != {expected}")
    keys = Counter((row["job_id"], row["metric_key"]) for row in selected)
    if any(count != 1 for count in keys.values()) or len(keys) != expected:
        raise AuditError("certificate metrics are missing or duplicated")
    for row in selected:
        k = parse_k(row["model_id"])
        expected_value = CERTIFICATE_METRICS[row["metric_key"]](k)
        if int(float(row["value"])) != expected_value:
            raise AuditError(
                f"certificate metric mismatch: {row['job_id']} {row['metric_key']}"
            )


def audit_legacy_direct_full(rows: Sequence[Mapping[str, str]]) -> list[dict[str, Any]]:
    selected = [
        row
        for row in rows
        if row.get("model_id", "").startswith("independent_k")
        and row.get("method_id") == "direct_full"
    ]
    if len(selected) != 40:
        raise AuditError(f"Direct-Full independent job count mismatch: {len(selected)}")
    summaries = []
    for row in selected:
        k = parse_k(row["model_id"])
        expected_states = 2**k
        expected_queries = (k + 2) * 2 ** (k - 1) - 1
        if k == 20:
            if row.get("process_status") != "TIMEOUT" or row.get("timed_out") != "True":
                raise AuditError("K=20 Direct-Full must remain an observed timeout")
            observed_states = None
            observed_queries = None
        else:
            if (
                row.get("process_status") != "SUCCESS"
                or row.get("revised_decision") != "realizable"
            ):
                raise AuditError(f"Direct-Full job failed: {row.get('job_id')}")
            observed_states = require_int(row, "states_discovered")
            observed_queries = require_int(row, "successor_queries")
            if observed_states != expected_states or observed_queries != expected_queries:
                raise AuditError(f"Direct-Full closed-form mismatch: {row.get('job_id')}")
        summaries.append(
            {
                "job_id": row["job_id"],
                "model_id": row["model_id"],
                "k": k,
                "status": row["process_status"],
                "expected_flat_states": expected_states,
                "observed_states": observed_states,
                "expected_queries": expected_queries,
                "observed_queries": observed_queries,
            }
        )
    return summaries


def model_base(manifest_path: Path, family: str) -> Path:
    if family == "independent":
        return manifest_path.parent.parent
    if family == "travel":
        return manifest_path.parent
    raise AssertionError(family)


def write_csv(path: Path, fieldnames: Sequence[str], rows: Iterable[Mapping[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_checksums(output: Path) -> None:
    names = (
        "condition_matrix.csv",
        "factored-certificates.json",
        "raw_comparison.csv",
        "summary.json",
    )
    (output / "SHA256SUMS").write_text(
        "".join(f"{sha256_file(output / name)}  {name}\n" for name in names),
        encoding="utf-8",
    )


def parse_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--independent-manifest", type=Path, required=True)
    parser.add_argument("--travel-manifest", type=Path, required=True)
    parser.add_argument("--m8k-raw", type=Path, required=True)
    parser.add_argument("--m8k-metrics", type=Path, required=True)
    parser.add_argument("--legacy-raw", type=Path, required=True)
    parser.add_argument("--multistate-games", type=Path, required=True)
    parser.add_argument("--output", required=True, help="new or empty result directory, or -")
    return parser.parse_args(argv)


def run(arguments: argparse.Namespace) -> dict[str, Any]:
    independent_manifest_path = arguments.independent_manifest.resolve()
    travel_manifest_path = arguments.travel_manifest.resolve()
    independent_manifest = load_json(independent_manifest_path)
    travel_manifest = load_json(travel_manifest_path)
    if independent_manifest.get("sizes_k") != list(EXPECTED_K):
        raise AuditError("independent K set mismatch")
    independent_records = independent_manifest.get("models")
    travel_records = travel_manifest.get("models")
    if not isinstance(independent_records, list) or len(independent_records) != 8:
        raise AuditError("independent manifest model count mismatch")
    if not isinstance(travel_records, list) or len(travel_records) != 12:
        raise AuditError("Travel manifest model count mismatch")

    conditions: list[dict[str, Any]] = []
    positive_evidence: list[dict[str, Any]] = []
    for record in independent_records:
        if not isinstance(record, dict):
            raise AuditError("invalid independent model record")
        k = record.get("k")
        if not isinstance(k, int) or k not in EXPECTED_K:
            raise AuditError("invalid independent K")
        path = verify_manifest_file(model_base(independent_manifest_path, "independent"), record)
        audit = audit_independent_source(path.read_text(encoding="utf-8"), k)
        game = independent_local_game(str(record["id"]), str(record["sha256"]), k)
        certificate = synthesize(game)
        checked = check_certificate(certificate)
        if checked["decision"] != "realizable":
            raise AuditError("independent typed game is not realizable")
        flat = check_flat_equivalence(certificate) if k <= 16 else None
        public_check = {key: value for key, value in checked.items() if not key.startswith("_")}
        positive_evidence.append(
            {
                "case_class": "registered-restricted-family",
                "certificate": certificate,
                "certificate_bytes": len(canonical_json(certificate).encode("utf-8")),
                "consumer_check": public_check,
                "priority_execution": check_priority_execution(certificate),
                "flat_cross_check": flat,
            }
        )
        conditions.append(
            {
                "family": "independent",
                "model_id": record["id"],
                "k": k,
                "passes_family_syntax": True,
                "passes_semantic_factor_certificate": True,
                "block_count": audit["block_count"],
                "witness": "typed local game, rank-sum/kappa certificate, and independent consumer passed",
                "model_sha256": record["sha256"],
            }
        )

    for record in travel_records:
        if not isinstance(record, dict):
            raise AuditError("invalid Travel model record")
        path = verify_manifest_file(model_base(travel_manifest_path, "travel"), record)
        audit = audit_travel_negative_control(path.read_text(encoding="utf-8"))
        conditions.append(
            {
                "family": "travel",
                "model_id": record["id"],
                "k": "",
                "passes_family_syntax": False,
                "passes_semantic_factor_certificate": False,
                "block_count": 1,
                "witness": audit["reason"],
                "model_sha256": record["sha256"],
            }
        )

    multistate_path = arguments.multistate_games.resolve()
    multistate_evidence: list[dict[str, Any]] = []
    for game, expected_decision in load_multistate_games(multistate_path):
        certificate = synthesize(game)
        checked = check_certificate(certificate)
        if checked["decision"] != expected_decision:
            raise AuditError(f"multistate decision differs: {game['id']}")
        flat = check_flat_equivalence(certificate)
        public_check = {key: value for key, value in checked.items() if not key.startswith("_")}
        multistate_evidence.append(
            {
                "case_class": "explicit-multistate-winning" if expected_decision == "realizable" else "explicit-multistate-losing",
                "certificate": certificate,
                "certificate_bytes": len(canonical_json(certificate).encode("utf-8")),
                "consumer_check": public_check,
                "priority_execution": (
                    check_priority_execution(certificate)
                    if expected_decision == "realizable"
                    else None
                ),
                "flat_cross_check": flat,
            }
        )

    winning_multistate = next(
        record["certificate"]
        for record in multistate_evidence
        if record["consumer_check"]["decision"] == "realizable"
    )

    def rehash(mutated: dict[str, Any]) -> None:
        mutated["input_game_sha256"] = sha256_json(reconstruct_game(mutated))

    mutations: list[tuple[str, dict[str, Any], bool]] = []
    mutated = copy.deepcopy(winning_multistate)
    mutated["cross_block_precedence"] = [["transfer.commit", "guard.arm"]]
    rehash(mutated)
    mutations.append(("cross-block-precedence", mutated, True))
    mutated = copy.deepcopy(winning_multistate)
    mutated["composition"]["shared_action_post"] = "synchronized_nonstutter"
    rehash(mutated)
    mutations.append(("shared-nonstutter", mutated, True))
    mutated = copy.deepcopy(winning_multistate)
    mutated["composition"]["post"] = "foreign-coordinate-change"
    rehash(mutated)
    mutations.append(("foreign-coordinate-change", mutated, True))
    mutated = copy.deepcopy(winning_multistate)
    goal_block = mutated["blocks"][0]
    goal_block["action_annotations"]["goal-spin"] = {"controllability": "uncontrollable", "kind": "internal"}
    goal_block["transitions"].append({"source": "tg", "action": "goal-spin", "targets": ["tg"]})
    rehash(mutated)
    mutations.append(("goal-uncontrollable-loop", mutated, True))
    mutated = copy.deepcopy(winning_multistate)
    mutated["blocks"][0]["kappa"]["tg"] = "not-loadable"
    mutations.append(("broken-kappa", mutated, False))
    mutated = copy.deepcopy(winning_multistate)
    mutated["blocks"][0]["initial_states"] = []
    rehash(mutated)
    mutations.append(("omitted-root", mutated, True))
    mutated = copy.deepcopy(winning_multistate)
    mutated["blocks"][0]["state_annotations"]["t1"]["monitor"] = "mi"
    rehash(mutated)
    mutations.append(("monitor-projection", mutated, True))
    mutated = copy.deepcopy(winning_multistate)
    mutated["blocks"][0]["rank"]["t0"] += 1
    mutations.append(("rank-corruption", mutated, False))
    mutated = copy.deepcopy(winning_multistate)
    mutated["blocks"][0]["transitions"][0]["targets"].append("unknown-state")
    rehash(mutated)
    mutations.append(("nondeterministic-outcome-target", mutated, True))
    losing_multistate = next(
        record["certificate"]
        for record in multistate_evidence
        if record["consumer_check"]["decision"] == "unrealizable"
    )
    mutated = copy.deepcopy(losing_multistate)
    del mutated["blocks"][0]["losing_counterstrategy"]["r0"]
    mutations.append(("losing-counterstrategy-omission", mutated, False))
    mutated = copy.deepcopy(winning_multistate)
    mutated["blocks"][0]["monitor"]["transitions"].append(
        {"source": "mi", "action": "arm", "target": "ma"}
    )
    rehash(mutated)
    mutations.append(("foreign-monitor-change", mutated, True))
    mutated = copy.deepcopy(winning_multistate)
    mutated["blocks"][0]["rs_observer"]["transitions"].append(
        {"source": "ri", "action": "arm", "target": "ra"}
    )
    rehash(mutated)
    mutations.append(("foreign-rs-change", mutated, True))
    mutated = copy.deepcopy(winning_multistate)
    mutated["blocks"][0]["monitor"]["transitions"].append(
        {"source": "mi", "action": "idle", "target": "ma"}
    )
    rehash(mutated)
    mutations.append(("shared-stutter-monitor-change", mutated, True))
    mutated = copy.deepcopy(winning_multistate)
    mutated["blocks"][0]["rs_observer"]["transitions"].append(
        {"source": "ri", "action": "idle", "target": "ra"}
    )
    rehash(mutated)
    mutations.append(("shared-stutter-rs-change", mutated, True))
    mutated = copy.deepcopy(winning_multistate)
    mutated["blocks"][0]["monitor"]["transitions"].append(
        {"source": "mi", "action": "unknown-monitor-action", "target": "ma"}
    )
    rehash(mutated)
    mutations.append(("unknown-monitor-action", mutated, True))
    mutated = copy.deepcopy(winning_multistate)
    mutated["blocks"][0]["rs_observer"]["transitions"].append(
        {"source": "ri", "action": "unknown-rs-action", "target": "ra"}
    )
    rehash(mutated)
    mutations.append(("unknown-rs-action", mutated, True))
    mutated = copy.deepcopy(winning_multistate)
    mutated["blocks"][0]["action_annotations"]["silent-drop"] = {
        "controllability": "controllable", "kind": "transfer"
    }
    mutated["blocks"][0]["state_annotations"]["t0"]["pending_actions"].append("silent-drop")
    rehash(mutated)
    mutations.append(("unrelated-pending-update-drop", mutated, True))
    mutated = copy.deepcopy(losing_multistate)
    mutated["blocks"][0]["state_annotations"]["re"]["pending_actions"] = []
    rehash(mutated)
    mutations.append(("internal-action-pending-drop", mutated, True))
    mutated = copy.deepcopy(winning_multistate)
    mutated["blocks"][0]["action_annotations"]["latent-update"] = {
        "controllability": "controllable", "kind": "transfer"
    }
    rehash(mutated)
    mutations.append(("initial-pending-update-omission", mutated, True))
    mutated = copy.deepcopy(winning_multistate)
    mutated["blocks"][1]["precedence_edges"].append(["arm", "ready"])
    rehash(mutated)
    mutations.append(("internal-action-precedence", mutated, True))
    mutated_game = reconstruct_game(copy.deepcopy(winning_multistate))
    mutated_game["blocks"][0]["action_annotations"]["prepare"]["controllability"] = "uncontrollable"
    mutated = synthesize(mutated_game)
    mutations.append(("uncontrollable-update-action", mutated, True))
    rejected_mutations: list[str] = []
    for label, mutated, _input_changed in mutations:
        try:
            check_certificate(mutated)
        except FactorCertificateError:
            rejected_mutations.append(label)
        else:
            raise AuditError(f"factor checker accepted mutation: {label}")

    factor_evidence = {
        "schema_version": "fg-ducs-factored-evidence-v1",
        "status": "PASS",
        "producer": "analysis/synthesize_factored_certificate.py",
        "independent_consumer": "analysis/check_factored_certificate.py",
        "registered_positive_cases": positive_evidence,
        "multistate_cases": multistate_evidence,
        "mutation_rejections": rejected_mutations,
        "claim_boundary": (
            "Explicit typed local games and a source-bound restricted one-state extractor; "
            "not arbitrary-LTS partition discovery, production integration, or a claim that the flat state space is additive."
        ),
    }

    m8k = audit_m8k_rows(read_csv(arguments.m8k_raw.resolve()))
    audit_certificate_metrics(read_csv(arguments.m8k_metrics.resolve()))
    legacy = audit_legacy_direct_full(read_csv(arguments.legacy_raw.resolve()))
    raw_rows: list[dict[str, Any]] = []
    for row in m8k:
        raw_rows.append(
            {
                "source": "M8k",
                "job_id": row["job_id"],
                "model_id": row["model_id"],
                "k": row["k"],
                "method": row["method"],
                "status": row["status"],
                "expected_states": row["k"] + 1 if row["method"] == "fg_ducs_otf" else "",
                "observed_states": row["states_discovered"],
                "expected_queries": row["k"] if row["method"] == "fg_ducs_otf" else "",
                "observed_queries": row["successor_queries"],
                "certificate_states": row["certificate_states"],
            }
        )
    for row in legacy:
        raw_rows.append(
            {
                "source": "legacy-direct-full",
                "job_id": row["job_id"],
                "model_id": row["model_id"],
                "k": row["k"],
                "method": "direct_full",
                "status": row["status"],
                "expected_states": row["expected_flat_states"],
                "observed_states": "" if row["observed_states"] is None else row["observed_states"],
                "expected_queries": row["expected_queries"],
                "observed_queries": "" if row["observed_queries"] is None else row["observed_queries"],
                "certificate_states": "",
            }
        )

    summary = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "analysis_class": "post-hoc restricted semantic factor, certificate, flat-equivalence, and census audit",
        "claim_boundary": (
            "A source-bound restricted extractor plus explicit typed local games; "
            "not general independence inference, arbitrary-LTS parsing, prospective or third-party evaluation, "
            "production integration, or a claim that the semantic flat product is additive."
        ),
        "syntactic_and_census_checks": [
            "one-state old/new component declarations",
            "updatingController old/new/mapRelation lists",
            "block-local reconfiguration relation syntax",
            "shared controllable pure-stutter declarations",
            "absence of declared precedence and requirements",
            "registered closed-form state/query/certificate census",
        ],
        "semantic_factor_conditions_independently_checked": True,
        "factored_certificates_independently_checked": True,
        "flat_products_independently_resolved": 9,
        "winning_priority_executions_checked": 9,
        "multistate_winning_cases": 1,
        "multistate_losing_cases": 1,
        "factor_mutations_rejected": len(rejected_mutations),
        "independent_family": {
            "conditions": 8,
            "k": list(EXPECTED_K),
            "syntactic_candidates_accepted": 8,
            "m8k_jobs_passed": 80,
            "otf_jobs_with_k_plus_one_certificate_states": 40,
            "certificate_metric_cells_passed": 80 * len(CERTIFICATE_METRICS),
            "direct_full_formula_jobs_passed": 35,
            "direct_full_k20_timeouts_retained": 5,
            "factored_winning_certificates_passed": 8,
            "flat_product_cross_checks_passed": 7,
            "k20_semantic_flat_states": 2**20,
            "k20_factored_local_states": 40,
            "k20_serialized_certificate_bytes": next(
                record["certificate_bytes"]
                for record in positive_evidence
                if record["certificate"]["source_model"]["id"] == "independent_k20"
            ),
            "factored_representation": "sum of local tables plus priority arbiter, rank sum, and factored kappa",
            "flat_state_space_boundary": "the semantic flat product remains exponential",
        },
        "negative_control": {
            "family": "Travel Agency adaptation",
            "conditions": 12,
            "rejected_by_shared_nonstutter_screen": 12,
            "reason": "shared nonstuttering agency.succ/agency.fail actions",
        },
        "input_files": {
            "independent_manifest": sha256_file(independent_manifest_path),
            "travel_manifest": sha256_file(travel_manifest_path),
            "m8k_raw": sha256_file(arguments.m8k_raw.resolve()),
            "m8k_metrics": sha256_file(arguments.m8k_metrics.resolve()),
            "legacy_raw": sha256_file(arguments.legacy_raw.resolve()),
            "multistate_games": sha256_file(multistate_path),
        },
    }

    if arguments.output == "-":
        return {
            "summary": summary,
            "conditions": conditions,
            "raw": raw_rows,
            "factored_certificates": factor_evidence,
        }
    output = Path(arguments.output).resolve()
    if output.exists():
        if not output.is_dir() or any(output.iterdir()):
            raise AuditError(f"output must be new or empty: {output}")
    else:
        output.mkdir(parents=True)
    (output / "summary.json").write_text(canonical_json(summary), encoding="utf-8")
    (output / "factored-certificates.json").write_text(
        canonical_json(factor_evidence), encoding="utf-8"
    )
    write_csv(
        output / "condition_matrix.csv",
        (
            "family", "model_id", "k", "passes_family_syntax",
            "passes_semantic_factor_certificate", "block_count", "witness", "model_sha256",
        ),
        conditions,
    )
    write_csv(
        output / "raw_comparison.csv",
        (
            "source", "job_id", "model_id", "k", "method", "status",
            "expected_states", "observed_states", "expected_queries",
            "observed_queries", "certificate_states",
        ),
        raw_rows,
    )
    write_checksums(output)
    return {"summary": summary, "output": str(output)}


def main(argv: Sequence[str] | None = None) -> int:
    try:
        arguments = parse_arguments(argv)
        result = run(arguments)
    except (
        AuditError,
        FactorCertificateError,
        SynthesisError,
        OSError,
        UnicodeDecodeError,
        ValueError,
    ) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(canonical_json(result), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
