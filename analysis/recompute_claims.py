#!/usr/bin/env python3
"""Recompute the paper-facing FG-DUCS claims from the public payload.

This program deliberately does more than authenticate frozen summaries.  It
parses the public LTS inputs, recomputes the C1 raw-oracle decisions, rebuilds
the C2 descriptive ratios from CSV rows, reruns all 43 exact game comparisons,
checks both C3 game fixed points and the typed handoff bundle, reruns the M8o
restricted typed-game synthesis/certificate/flat-equivalence audit, and
recomputes the M8p unpartitioned typed-table discovery/obstruction audit and
coordinate-relative 43-game screen. Historical Java/PRISM executions remain recorded
observations; their binaries are not redistributed and are not silently
relabelled as executions of the current source overlay.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

from exact_game_isomorphism import (
    NonIsomorphic,
    compare_games,
    fixed_point,
    load_game_bundle,
)
from independent_raw_oracle import analyze_semantic_manifest
from check_residual_soundness import check_manifest as check_rs_manifest
from audit_typed_partition_discovery import (
    AuditError as PartitionAuditError,
    run as audit_typed_partition,
)
from audit_native_factorization import AuditError as NativeAuditError, audit as audit_native_factorization
from audit_native_source_dependencies import (
    AuditError as NativeDependencyAuditError,
    audit as audit_native_source_dependencies,
)
from audit_post_frontend_contract_certificate import (
    AuditError as PostFrontendAuditError,
    CampaignError as PostFrontendCampaignError,
    CheckError as PostFrontendCheckError,
    audit as audit_post_frontend_certificate,
)
from audit_productioncell_source_contract_certificate import (
    audit as audit_productioncell_source_certificate,
)
from audit_post_frontend_generated_win_panel import (
    AuditError as GeneratedWinAuditError,
    audit as audit_generated_win_panel,
)
from check_generated_post_frontend_win_certificate import (
    CheckError as GeneratedWinCheckError,
)
from check_productioncell_source_contract_certificate import SourceContractError
from run_post_frontend_generated_win_panel import (
    CampaignError as GeneratedWinCampaignError,
)
from run_productioncell_source_contract_certificate import (
    CampaignError as SourceCertificateCampaignError,
)


ROOT = Path(__file__).resolve().parents[1]
TYPED_PHASES = {
    "P_OLD_READ_COMPLETION": "old",
    "P_NEW_READ_COMPLETION": "new",
    "P_NO_FAULT": "new",
}


class ClaimError(RuntimeError):
    """A public input, observation, or recomputed claim is inconsistent."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ClaimError(message)


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ClaimError(f"invalid JSON: {path.relative_to(ROOT)}") from error
    if not isinstance(value, dict):
        raise ClaimError(f"JSON root is not an object: {path.relative_to(ROOT)}")
    return value


def read_csv(path: Path) -> list[dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
    except (OSError, UnicodeDecodeError, csv.Error) as error:
        raise ClaimError(f"invalid CSV: {path.relative_to(ROOT)}") from error
    if not rows or not rows[0]:
        raise ClaimError(f"empty CSV: {path.relative_to(ROOT)}")
    return rows


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ClaimError("value is not canonical finite JSON") from error


def exact_integer(value: Any, expected: int) -> bool:
    return type(value) is int and value == expected


def near(left: float, right: float, label: str) -> None:
    if not math.isclose(left, right, rel_tol=1e-12, abs_tol=1e-12):
        raise ClaimError(f"{label} differs: recomputed={left!r}, registered={right!r}")


def exact_counts(rows: Iterable[Mapping[str, str]], field: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row.get(field, "")) for row in rows).items()))


def manifest_models(
    manifest_path: Path,
    *,
    path_base: Path | None = None,
) -> dict[str, dict[str, Any]]:
    manifest = read_json(manifest_path)
    records = manifest.get("models")
    require(isinstance(records, list) and records, f"manifest has no models: {manifest_path.name}")
    result: dict[str, dict[str, Any]] = {}
    base = path_base or manifest_path.parent
    for record in records:
        require(isinstance(record, dict), "manifest model is not an object")
        identifier = record.get("id")
        relative = Path(str(record.get("path", "")))
        require(
            isinstance(identifier, str)
            and identifier
            and identifier not in result
            and not relative.is_absolute()
            and ".." not in relative.parts,
            "manifest model identity/path is invalid",
        )
        path = base / relative
        require(path.is_file() and not path.is_symlink(), f"manifest model is missing: {identifier}")
        require(
            path.stat().st_size == record.get("bytes")
            and sha256_file(path) == record.get("sha256"),
            f"manifest model bytes/hash differ: {identifier}",
        )
        result[identifier] = record
    return result


def bind_raw_to_plan(
    rows: Sequence[Mapping[str, str]],
    plan_path: Path,
    fields: Sequence[str],
) -> None:
    plan = read_json(plan_path)
    jobs = plan.get("jobs")
    require(isinstance(jobs, list) and len(jobs) == len(rows), "raw/plan job census differs")
    planned = {
        str(job.get("job_id")): job for job in jobs if isinstance(job, dict)
    }
    require(len(planned) == len(jobs), "plan job IDs are missing or duplicated")
    require(len({row.get("job_id") for row in rows}) == len(rows), "raw job IDs are duplicated")
    require(set(planned) == {row.get("job_id") for row in rows}, "raw/plan job IDs differ")
    for row in rows:
        job = planned[str(row["job_id"])]
        for field in fields:
            require(str(row.get(field, "")) == str(job.get(field, "")), f"raw/plan {field} differs for {row['job_id']}")
    require(
        len(rows) == plan.get("job_count")
        and {row.get("plan_sha256") for row in rows} == {str(plan.get("plan_sha256"))},
        "raw/plan registered semantic hash differs",
    )


def recompute_c1() -> dict[str, Any]:
    manifest_path = ROOT / "inputs/c1/semantic_boundaries_v2/manifest.json"
    raw_path = ROOT / "evidence/m8k-correctness/raw_runs.csv"
    registered_path = ROOT / "evidence/m8k-correctness/independent_raw_oracle.json"
    recomputed = analyze_semantic_manifest(manifest_path, raw_path)
    registered = read_json(registered_path)

    require(recomputed.get("model_count") == 41, "C1 model census is not 41")
    require(
        recomputed.get("raw_oracle_java_comparisons") == 82,
        "C1 Java/raw-oracle comparison census is not 82",
    )
    require(
        recomputed.get("all_registered_expectations_confirmed") is True
        and recomputed.get("all_java_decisions_confirmed") is True,
        "C1 raw-oracle decision gate failed",
    )
    scientific_fields = (
        "model_id",
        "base_case",
        "variant",
        "sha256",
        "decision",
        "registered_expected_decision",
        "agrees_with_registration",
        "java_decisions",
        "explicit_game_states",
        "explicit_game_action_outcomes",
        "q0_states",
        "goal_states",
        "winning_states",
        "losing_states",
        "winning_layers_after_goal",
        "loadable_new_endpoint_states",
    )

    def projection(value: Mapping[str, Any]) -> tuple[Any, ...]:
        return tuple(value.get(field) for field in scientific_fields)

    observed_models = {
        str(row.get("model_id")): projection(row)
        for row in recomputed.get("models", [])
        if isinstance(row, dict)
    }
    registered_models = {
        str(row.get("model_id")): projection(row)
        for row in registered.get("models", [])
        if isinstance(row, dict)
    }
    require(
        observed_models == registered_models,
        "C1 recomputed model decisions/censuses differ from the registered oracle",
    )

    rows = read_csv(raw_path)
    require(len(rows) == 92, "C1 raw job census is not 92")
    bind_raw_to_plan(
        rows,
        ROOT / "evidence/m8k-correctness/plan.json",
        ("job_id", "block_id", "model_id", "model_family", "method_id", "repetition"),
    )
    require(
        {row.get("config_sha256") for row in rows}
        == {sha256_file(ROOT / "evidence/m8k-correctness/config.json")}
        and {row.get("classpath_sha256") for row in rows}
        == {"1720533b2e3e54aefe6dd56cef5c95d9d9023ff5331eca52222fdd41f086decd"},
        "C1 config/runtime binding differs",
    )
    require(
        exact_counts(rows, "method_id") == {"fg_ducs_otf": 46, "generic_lazy": 46},
        "C1 method census differs",
    )
    require(
        exact_counts(rows, "process_status")
        == {"INVALID_INPUT": 8, "SUCCESS": 36, "UNREALIZABLE": 48},
        "C1 terminal-status census differs",
    )
    require(
        sum(row.get("internal_certificate_check") == "passed" for row in rows) == 84,
        "C1 certificate census is not 84",
    )
    semantic_records = {
        "semantic_" + identifier: record
        for identifier, record in manifest_models(manifest_path).items()
    }
    contract_manifest = ROOT / "inputs/c1/contract_gate/manifest.json"
    contract_records = {
        "contract_" + identifier: record
        for identifier, record in manifest_models(contract_manifest).items()
    }
    all_records = {**semantic_records, **contract_records}
    require(set(all_records) == {row.get("model_id") for row in rows}, "C1 model population differs")
    by_model: dict[str, list[Mapping[str, str]]] = defaultdict(list)
    for row in rows:
        by_model[str(row["model_id"])].append(row)
    for identifier, record in all_records.items():
        model_rows = by_model[identifier]
        require(
            len(model_rows) == 2
            and {row.get("method_id") for row in model_rows} == {"fg_ducs_otf", "generic_lazy"}
            and all(row.get("input_sha256") == record.get("sha256") for row in model_rows),
            f"C1 model/method/hash binding differs: {identifier}",
        )
        expected_status = record.get("expected_process_status")
        expected_decision = record.get("expected_decision")
        if identifier.startswith("contract_"):
            require(
                all(
                    row.get("process_status") == expected_status
                    and row.get("revised_decision") == expected_decision
                    for row in model_rows
                ),
                f"C1 contract expectation differs: {identifier}",
            )
        else:
            require(
                all(
                    row.get("revised_decision") == expected_decision
                    and row.get("run_verified") == "true"
                    and row.get("internal_certificate_check") == "passed"
                    for row in model_rows
                ),
                f"C1 semantic evidence differs: {identifier}",
            )
    decisions = Counter(row["decision"] for row in recomputed["models"])
    require(decisions == {"realizable": 17, "unrealizable": 24}, "C1 17/24 split differs")
    return {
        "status": "PASS",
        "public_raw_sha256": sha256_file(raw_path),
        "models_reparsed": 41,
        "contract_inputs_bound": 5,
        "java_decisions_compared": 82,
        "raw_jobs_checked": 92,
        "certificate_rows_checked": 84,
        "decisions": dict(sorted(decisions.items())),
    }


def model_median_ratios(
    rows: Sequence[Mapping[str, str]], field: str
) -> tuple[dict[str, float], float]:
    samples: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        model = str(row.get("model_id", ""))
        method = str(row.get("method_id", ""))
        try:
            value = float(str(row.get(field, "")))
        except ValueError as error:
            raise ClaimError(f"C2 {field} has a nonnumeric cell") from error
        if not math.isfinite(value) or value < 0:
            raise ClaimError(f"C2 {field} has an invalid value")
        samples[model][method].append(value)
    ratios: dict[str, float] = {}
    for model, methods in samples.items():
        require(
            set(methods) == {"fg_ducs_otf", "generic_lazy"}
            and all(len(values) == 5 for values in methods.values()),
            f"C2 {model}/{field} does not contain two complete five-run methods",
        )
        denominator = statistics.median(methods["fg_ducs_otf"])
        require(denominator > 0, f"C2 {model}/{field} has a zero FG median")
        ratios[model] = statistics.median(methods["generic_lazy"]) / denominator
    require(len(ratios) == 20, f"C2 {field} does not cover 20 models")
    return dict(sorted(ratios.items())), statistics.median(ratios.values())


def c2_family_statistics(rows: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    fields = (
        "states_discovered",
        "successor_queries",
        "solver_time_ms",
        "elapsed_monotonic_seconds",
        "peak_rss_kib",
    )
    samples: dict[str, dict[str, dict[str, dict[str, list[float]]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    )
    for row in rows:
        family = str(row.get("model_family", ""))
        model = str(row.get("model_id", ""))
        method = str(row.get("method_id", ""))
        for field in fields:
            try:
                value = float(str(row.get(field, "")))
            except ValueError as error:
                raise ClaimError(f"C2 {field} has a nonnumeric cell") from error
            require(math.isfinite(value) and value >= 0, f"C2 {field} has an invalid value")
            samples[family][model][method][field].append(value)

    expected_families = {
        "independent_one_state_reconfiguration": 8,
        "travel_agency_derived_fg_ducs": 12,
    }
    require(
        set(samples) == set(expected_families),
        "C2 family set differs from the paper population",
    )
    result: dict[str, Any] = {}
    for family, expected_models in expected_families.items():
        models = samples[family]
        require(len(models) == expected_models, f"C2 {family} model census differs")
        field_result: dict[str, Any] = {}
        for field in fields:
            fg_medians: list[float] = []
            generic_medians: list[float] = []
            ratios: list[float] = []
            for model, methods in sorted(models.items()):
                require(
                    set(methods) == {"fg_ducs_otf", "generic_lazy"}
                    and all(len(method_fields[field]) == 5 for method_fields in methods.values()),
                    f"C2 {family}/{model}/{field} does not contain two five-run methods",
                )
                fg = statistics.median(methods["fg_ducs_otf"][field])
                generic = statistics.median(methods["generic_lazy"][field])
                require(fg > 0, f"C2 {family}/{model}/{field} has a zero FG median")
                fg_medians.append(fg)
                generic_medians.append(generic)
                ratios.append(generic / fg)
            field_result[field] = {
                "fg_median": statistics.median(fg_medians),
                "fg_min": min(fg_medians),
                "fg_max": max(fg_medians),
                "generic_median": statistics.median(generic_medians),
                "generic_min": min(generic_medians),
                "generic_max": max(generic_medians),
                "generic_over_fg_median": statistics.median(ratios),
                "generic_over_fg_min": min(ratios),
                "generic_over_fg_max": max(ratios),
            }
        result[family] = field_result
    return result


def require_c2_paper_statistics(statistics_by_family: Mapping[str, Any]) -> None:
    expected = {
        "independent_one_state_reconfiguration": {
            "states_discovered": (10.0, 3.0, 21.0, 7.0),
            "successor_queries": (9.0, 2.0, 20.0, 20.7125),
            "solver_time_ms": (9.8975, 3.853, 22.331, 4.433754141347528),
            "elapsed_monotonic_seconds": (0.8102920625000001, 0.759237209, 0.869619125, 1.0666181930857652),
            "peak_rss_kib": (97520.0, 92784.0, 111408.0, 1.1186764151948259),
        },
        "travel_agency_derived_fg_ducs": {
            "states_discovered": (341.0, 12.0, 13757.0, 1.0306952662721893),
            "successor_queries": (7306.5, 85.0, 605535.0, 1.0429656275487293),
            "solver_time_ms": (195.6295, 9.243, 65146.072, 1.4965277298848427),
            "elapsed_monotonic_seconds": (1.341179312, 0.851760625, 102.53238975, 0.993404135831162),
            "peak_rss_kib": (294360.0, 97472.0, 2303472.0, 1.0460698478564017),
        },
    }
    for family, fields in expected.items():
        actual_fields = statistics_by_family.get(family)
        require(isinstance(actual_fields, dict), f"C2 {family} statistics are missing")
        for field, values in fields.items():
            actual = actual_fields.get(field)
            require(isinstance(actual, dict), f"C2 {family}/{field} statistics are missing")
            for key, expected_value in zip(
                ("fg_median", "fg_min", "fg_max", "generic_over_fg_median"), values
            ):
                near(float(actual.get(key)), expected_value, f"C2 paper {family}/{field}/{key}")


def recompute_c2() -> dict[str, Any]:
    raw_path = ROOT / "evidence/m8k-performance/raw_runs.csv"
    audit = read_json(ROOT / "evidence/m8k-performance/generic_lazy_audit.json")
    rows = read_csv(raw_path)
    require(len(rows) == 200, "C2 raw job census is not 200")
    bind_raw_to_plan(
        rows,
        ROOT / "evidence/m8k-performance/plan.json",
        ("job_id", "block_id", "model_id", "model_family", "method_id", "repetition"),
    )
    require(
        {row.get("config_sha256") for row in rows}
        == {sha256_file(ROOT / "evidence/m8k-performance/config.json")}
        and {row.get("classpath_sha256") for row in rows}
        == {"1720533b2e3e54aefe6dd56cef5c95d9d9023ff5331eca52222fdd41f086decd"},
        "C2 config/runtime binding differs",
    )
    independent = manifest_models(
        ROOT / "inputs/c2/inputs/generation_manifest.json",
        path_base=ROOT / "inputs/c2",
    )
    travel = manifest_models(ROOT / "inputs/c2/travel_agency_family/manifest.json")
    registered_models = {**independent, **travel}
    require(len(registered_models) == 20, "C2 manifest population is not 20")
    require(set(registered_models) == {row.get("model_id") for row in rows}, "C2 raw/manifest model sets differ")
    require(
        exact_counts(rows, "method_id") == {"fg_ducs_otf": 100, "generic_lazy": 100},
        "C2 method census differs",
    )
    for row in rows:
        require(
            row.get("process_status") == "SUCCESS"
            and row.get("completed") == "True"
            and row.get("exit_code") == "0"
            and row.get("timed_out") == "False"
            and row.get("revised_decision") == "realizable"
            and row.get("internal_certificate_check") == "passed",
            "C2 contains a non-success, timeout, or unchecked row",
        )
        record = registered_models[str(row["model_id"])]
        require(
            row.get("input_sha256") == record.get("sha256")
            and row.get("model_planned_repetitions") == "5"
            and row.get("link_checker") == "passed",
            f"C2 manifest/hash/link binding differs for {row.get('job_id')}",
        )

    metrics = {
        "states_discovered": "states_discovered_generic_over_typed",
        "successor_queries": "successor_queries_generic_over_typed",
        "solver_time_ms": "solver_time_ms_generic_over_typed",
        "elapsed_monotonic_seconds": "elapsed_monotonic_seconds_generic_over_typed",
        "peak_rss_kib": "peak_rss_kib_generic_over_typed",
    }
    recomputed: dict[str, float] = {}
    structural_direction: dict[str, int] = {}
    registered_rows = audit.get("model_level_metrics")
    require(isinstance(registered_rows, dict), "C2 registered metric table is missing")
    for raw_field, audit_field in metrics.items():
        ratios, median = model_median_ratios(rows, raw_field)
        record = registered_rows.get(audit_field)
        require(isinstance(record, dict), f"C2 registered {audit_field} is missing")
        near(median, float(record.get("median")), f"C2 {audit_field} median")
        require(record.get("n_models") == 20, f"C2 {audit_field} model census differs")
        recomputed[audit_field] = median
        structural_direction[audit_field] = sum(value >= 1.0 for value in ratios.values())
    require(
        structural_direction["states_discovered_generic_over_typed"] == 17
        and structural_direction["successor_queries_generic_over_typed"] == 17,
        "C2 structural direction is not 17/20",
    )
    require(audit.get("status") == "PASS", "C2 registered audit is not PASS")
    family_statistics = c2_family_statistics(rows)
    require_c2_paper_statistics(family_statistics)
    registered_families = audit.get("family_level_metrics")
    require(isinstance(registered_families, dict), "C2 registered family metrics are missing")
    for family, fields in family_statistics.items():
        registered_family = registered_families.get(family)
        require(isinstance(registered_family, dict), f"C2 registered {family} metrics are missing")
        for raw_field, audit_field in metrics.items():
            registered = registered_family.get(audit_field)
            require(isinstance(registered, dict), f"C2 registered {family}/{audit_field} is missing")
            near(
                float(fields[raw_field]["generic_over_fg_median"]),
                float(registered.get("median")),
                f"C2 {family}/{audit_field}",
            )
            require(
                registered.get("n_models")
                == (8 if family == "independent_one_state_reconfiguration" else 12),
                f"C2 {family}/{audit_field} model census differs",
            )
    return {
        "status": "PASS",
        "public_raw_sha256": sha256_file(raw_path),
        "jobs_recomputed": 200,
        "models_recomputed": 20,
        "generic_over_fg_model_medians": recomputed,
        "paper_family_statistics": family_statistics,
        "models_with_generic_ge_fg_states": 17,
        "models_with_generic_ge_fg_queries": 17,
    }


def load_bundle(path: Path):
    return load_game_bundle(read_json(path))


def recompute_m8n() -> dict[str, Any]:
    cases_root = ROOT / "evidence/m8n-game-equivalence/cases"
    c1_manifest_path = ROOT / "inputs/c1/semantic_boundaries_v2/manifest.json"
    c1_manifest = read_json(c1_manifest_path)
    c1_models = c1_manifest.get("models")
    require(isinstance(c1_models, list) and len(c1_models) == 41, "M8n C1 manifest census differs")
    expected_c1: dict[str, dict[str, Any]] = {}
    for record in c1_models:
        require(isinstance(record, dict), "M8n C1 manifest record is malformed")
        identifier = record.get("id")
        require(isinstance(identifier, str) and identifier not in expected_c1, "M8n C1 manifest ID differs")
        expected_c1[identifier] = record
    c1_dirs = sorted(
        path for path in cases_root.iterdir()
        if path.is_dir() and (path / "java-independent-game.json").is_file()
    )
    require(
        {path.name for path in c1_dirs} == set(expected_c1),
        "M8n public C1 case IDs differ from the C1 manifest",
    )
    summary = read_json(ROOT / "evidence/m8n-game-equivalence/summary.json")
    summary_cases_raw = summary.get("cases")
    require(isinstance(summary_cases_raw, list) and len(summary_cases_raw) == 43, "M8n summary case set differs")
    summary_cases: dict[str, dict[str, Any]] = {}
    for record in summary_cases_raw:
        require(isinstance(record, dict), "M8n summary case record is malformed")
        identifier = record.get("id")
        require(isinstance(identifier, str) and identifier not in summary_cases, "M8n summary case ID differs")
        summary_cases[identifier] = record
    require(
        set(summary_cases) == set(expected_c1) | {"ardrone_semantic_positive", "ardrone_semantic_negative"},
        "M8n summary population differs",
    )
    require(
        summary.get("c1_manifest_sha256") == sha256_file(c1_manifest_path),
        "M8n summary C1 manifest binding differs",
    )
    totals = Counter()
    decisions = Counter()
    for case in c1_dirs:
        left = load_bundle(case / "java-independent-game.json")
        right = load_bundle(case / "python-observer-exact-game.json")
        result = compare_games(
            left,
            right,
            maximum_search_nodes=100_000,
            require_typed_state_translation=False,
        )
        registered = read_json(case / "exact-isomorphism.json")
        require(result == registered, f"M8n exact result differs for {case.name}")
        summary_record = summary_cases[case.name]
        require(
            summary_record.get("model_sha256") == expected_c1[case.name].get("sha256")
            and summary_record.get("java_game_sha256") == sha256_file(case / "java-independent-game.json")
            and summary_record.get("python_game_sha256") == sha256_file(case / "python-observer-exact-game.json")
            and summary_record.get("comparison_sha256") == sha256_file(case / "exact-isomorphism.json"),
            f"M8n manifest/game hash binding differs for {case.name}",
        )
        totals["c1_states"] += int(result["state_count"])
        totals["c1_buckets"] += int(result["enabled_bucket_count"])
        totals["c1_edges"] += int(result["outcome_edge_count"])
        decisions[str(result["decision"])] += 1

    for identifier in ("ardrone_semantic_positive", "ardrone_semantic_negative"):
        public_case = ROOT / "evidence/m8m-source-anchored/external/cases" / identifier
        left = load_bundle(public_case / "java-independent-game.json")
        right = load_bundle(public_case / "python-raw-exact-game.json")
        result = compare_games(
            left,
            right,
            maximum_search_nodes=100_000,
            require_typed_state_translation=True,
            typed_requirement_phases=TYPED_PHASES,
        )
        registered = read_json(cases_root / identifier / "exact-typed-isomorphism.json")
        require(result == registered, f"M8n typed exact result differs for {identifier}")
        summary_record = summary_cases[identifier]
        require(
            summary_record.get("java_game_sha256") == sha256_file(public_case / "java-independent-game.json")
            and summary_record.get("python_game_sha256") == sha256_file(public_case / "python-raw-exact-game.json")
            and summary_record.get("comparison_sha256")
            == sha256_file(cases_root / identifier / "exact-typed-isomorphism.json"),
            f"M8n typed game hash binding differs for {identifier}",
        )
        totals["m8m_states"] += int(result["state_count"])
        totals["m8m_buckets"] += int(result["enabled_bucket_count"])
        totals["m8m_edges"] += int(result["outcome_edge_count"])

    expected = {
        "c1_states": 139,
        "c1_buckets": 184,
        "c1_edges": 196,
        "m8m_states": 276,
        "m8m_buckets": 1248,
        "m8m_edges": 1368,
    }
    require(dict(totals) == expected, f"M8n aggregate differs: {dict(totals)!r}")
    require(decisions == {"realizable": 17, "unrealizable": 24}, "M8n C1 split differs")
    require(
        summary.get("status") == "PASS"
        and summary.get("case_count") == 43
        and summary.get("passed_cases") == 43
        and summary.get("failed_cases") == 0,
        "M8n registered summary census differs",
    )
    return {
        "status": "PASS",
        "exact_game_comparisons_rerun": 43,
        "c1": {
            "cases": 41,
            "states": totals["c1_states"],
            "enabled_buckets": totals["c1_buckets"],
            "outcome_edges": totals["c1_edges"],
            "decisions": dict(sorted(decisions.items())),
        },
        "m8m": {
            "typed_cases": 2,
            "states": totals["m8m_states"],
            "enabled_buckets": totals["m8m_buckets"],
            "outcome_edges": totals["m8m_edges"],
        },
    }


def validate_c3_rows(
    path: Path,
    expected_family: str,
    *,
    config_path: Path,
    plan_path: Path,
    expected_runtime: str,
) -> dict[str, Any]:
    rows = read_csv(path)
    require(len(rows) == 6, f"C3 {expected_family} does not have six rows")
    bind_raw_to_plan(
        rows,
        plan_path,
        ("job_id", "block_id", "model_id", "model_family", "method_id", "repetition"),
    )
    require(
        {row.get("config_sha256") for row in rows} == {sha256_file(config_path)}
        and {row.get("classpath_sha256") for row in rows} == {expected_runtime},
        "C3 config/runtime binding differs",
    )
    require(
        exact_counts(rows, "method_id")
        == {"direct_full": 2, "fg_ducs_otf": 2, "generic_lazy": 2},
        "C3 method census differs",
    )
    require(exact_counts(rows, "model_family") == {expected_family: 6}, "C3 family differs")
    require(
        exact_counts(rows, "process_status") == {"SUCCESS": 3, "UNREALIZABLE": 3},
        "C3 status split differs",
    )
    models = manifest_models(ROOT / "inputs/c3/manifest.json")
    by_cell = {(row.get("model_id"), row.get("method_id")): row for row in rows}
    require(
        len(by_cell) == 6
        and set(by_cell)
        == {(model, method) for model in models for method in ("direct_full", "fg_ducs_otf", "generic_lazy")},
        "C3 exact model/method matrix differs",
    )
    for (model, _method), row in by_cell.items():
        record = models[str(model)]
        expected = str(record.get("expected_decision"))
        require(
            row.get("input_sha256") == record.get("sha256")
            and row.get("revised_decision") == expected
            and row.get("process_status") == ("SUCCESS" if expected == "realizable" else "UNREALIZABLE"),
            f"C3 model/hash/decision binding differs: {row.get('job_id')}",
        )
    require(
        exact_counts(rows, "revised_decision") == {"realizable": 3, "unrealizable": 3},
        "C3 decision split differs",
    )
    for row in rows:
        require(
            row.get("run_verified") == "true"
            and row.get("internal_certificate_check") == "passed"
            and row.get("timed_out") == "False",
            "C3 contains an unverified or timed-out row",
        )
    return {
        "public_raw_sha256": sha256_file(path),
        "rows_checked": 6,
        "decision_cells": {"realizable": 3, "unrealizable": 3},
    }


def validate_handoff_bundle() -> dict[str, Any]:
    bundle_path = (
        ROOT
        / "evidence/m8m-source-anchored/handoff/cases/ardrone_semantic_positive/atomic-handoff-bundle.json"
    )
    bundle = read_json(bundle_path)
    summary = read_json(ROOT / "evidence/m8m-source-anchored/handoff/summary.json")
    from atomic_handoff_validation import (
        cover_post_edges,
        cover_strategy_edges,
        deterministic_handoff_race,
        execute_q0_nondeterministic_forks,
        execute_q0_traces,
        parse_bundle,
        validate_required_actions_per_trace,
    )
    parsed = parse_bundle(bundle)
    configurations = bundle.get("configurations")
    q0_entries = bundle.get("q0_entries")
    strategy = bundle.get("strategy")
    handoffs = bundle.get("handoffs")
    post_states = bundle.get("post_states")
    require(
        all(isinstance(value, list) for value in (configurations, q0_entries, strategy, handoffs, post_states)),
        "C3 handoff bundle arrays are incomplete",
    )
    config_by_id = {row.get("id"): row for row in configurations if isinstance(row, dict)}
    post_by_id = {row.get("id"): row for row in post_states if isinstance(row, dict)}
    require(len(config_by_id) == len(configurations) == 29, "C3 configuration census differs")
    require(len(post_by_id) == len(post_states) == 12, "C3 post-state census differs")
    require(len(q0_entries) == 6, "C3 old endpoint entry census differs")
    roots = {row.get("root_configuration") for row in q0_entries}
    require(len(roots) == 5 and roots <= set(config_by_id), "C3 Q0 root census differs")
    goals = {identifier for identifier, row in config_by_id.items() if row.get("goal") is True}
    require(len(goals) == 6, "C3 goal census differs")

    strategy_edges = 0
    strategy_lookup: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in strategy:
        require(isinstance(row, dict), "C3 strategy row is not an object")
        key = (str(row.get("source")), str(row.get("action")))
        outcomes = row.get("outcomes")
        require(
            key not in strategy_lookup and key[0] in config_by_id and isinstance(outcomes, list) and outcomes,
            "C3 strategy bucket is malformed or duplicated",
        )
        for outcome in outcomes:
            require(
                isinstance(outcome, dict) and outcome.get("target") in config_by_id,
                "C3 strategy outcome target is invalid",
            )
        strategy_lookup[key] = outcomes
        strategy_edges += len(outcomes)
    require(len(strategy) == 23 and strategy_edges == 28, "C3 strategy census differs")

    handoff_goals = set()
    for row in handoffs:
        require(isinstance(row, dict), "C3 handoff row is not an object")
        goal = row.get("goal_configuration")
        post = row.get("post_state_id")
        require(goal in goals and post in post_by_id, "C3 handoff endpoint is invalid")
        require(
            row.get("controller_state_to_load") == post_by_id[post].get("controller_state"),
            "C3 handoff load state disagrees with the post state",
        )
        handoff_goals.add(goal)
    require(handoff_goals == goals, "C3 handoff map does not cover every goal")

    post_buckets = 0
    post_edges = 0
    for state in post_states:
        transitions = state.get("transitions")
        require(isinstance(transitions, list), "C3 post transitions are missing")
        seen_actions = set()
        for transition in transitions:
            require(isinstance(transition, dict), "C3 post transition is not an object")
            action = transition.get("action")
            outcomes = transition.get("outcomes")
            require(
                isinstance(action, str)
                and action not in seen_actions
                and isinstance(outcomes, list)
                and outcomes
                and all(target in post_by_id for target in outcomes),
                "C3 post bucket is malformed",
            )
            seen_actions.add(action)
            post_buckets += 1
            post_edges += len(outcomes)
    require((post_buckets, post_edges) == (54, 58), "C3 post graph census differs")

    cases = summary.get("cases")
    require(isinstance(cases, list) and len(cases) == 1 and isinstance(cases[0], dict), "C3 handoff case is missing")
    case = cases[0]
    require(case.get("bundle_sha256") == sha256_file(bundle_path), "C3 summary/bundle hash differs")
    all_q0 = case.get("all_q0_execution")
    forked = case.get("q0_required_action_outcome_completion")
    race = case.get("atomic_handoff_race")
    require(all(isinstance(value, dict) for value in (all_q0, forked, race)), "C3 execution summaries are missing")
    traces = all_q0.get("traces")
    require(isinstance(traces, list) and len(traces) == 5, "C3 canonical trace census differs")
    for trace in traces:
        visited = trace.get("visited_configurations")
        actions = trace.get("mid_actions")
        require(
            isinstance(visited, list)
            and isinstance(actions, list)
            and len(visited) == len(actions) + 1
            and visited[0] == trace.get("root")
            and visited[-1] in goals,
            "C3 canonical trace shape is invalid",
        )
        for source, action, target in zip(visited, actions, visited[1:]):
            outcomes = strategy_lookup.get((source, action), [])
            require(any(row.get("target") == target for row in outcomes), "C3 canonical trace leaves the strategy")
    fork_traces = forked.get("traces")
    require(isinstance(fork_traces, list) and len(fork_traces) == 10, "C3 transfer-result trace census differs")
    require(
        {(row.get("root"), row.get("required_outcome_index")) for row in fork_traces}
        == {(root, outcome) for root in roots for outcome in (0, 1)},
        "C3 transfer-result traces do not cover both results at every root",
    )
    require(
        race.get("repetitions") == 500
        and race.get("completed_atomic_handoffs") == 500
        and race.get("maximum_critical_occupancy") == 1
        and race.get("partial_load_observations") == 0
        and race.get("overlap_violations") == 0,
        "C3 recorded atomic-race census differs",
    )
    require(summary.get("status") == "PASS", "C3 handoff summary is not PASS")
    fresh_q0 = execute_q0_traces(parsed)
    fresh_forks = execute_q0_nondeterministic_forks(parsed, "reconfigure_BATTERY")
    required_actions = case.get("required_actions")
    require(isinstance(required_actions, list), "C3 required-action list is missing")
    validate_required_actions_per_trace(fresh_q0["traces"], set(required_actions))
    validate_required_actions_per_trace(fresh_forks["traces"], set(required_actions))
    fresh_strategy = cover_strategy_edges(parsed)
    fresh_post = cover_post_edges(parsed)
    fresh_race = deterministic_handoff_race(parsed, 500)
    require(
        fresh_q0.get("trace_count") == 5
        and fresh_forks.get("trace_count") == 10
        and fresh_strategy.get("covered_strategy_outcome_edges") == 28
        and fresh_post.get("covered_post_outcome_edges") == 58
        and fresh_race.get("completed_atomic_handoffs") == 500
        and fresh_race.get("maximum_critical_occupancy") == 1
        and fresh_race.get("partial_load_observations") == 0
        and fresh_race.get("overlap_violations") == 0,
        "C3 fresh handoff execution differs",
    )
    return {
        "bundle_sha256": sha256_file(bundle_path),
        "old_endpoint_entries": 6,
        "q0_roots": 5,
        "canonical_traces_reexecuted": 5,
        "transfer_result_traces_checked": 10,
        "strategy_outcome_edges_checked": 28,
        "post_outcome_edges_checked": 58,
        "atomic_races_reexecuted": 500,
        "reexecuted_maximum_critical_occupancy": 1,
        "reexecuted_partial_load_observations": 0,
        "reexecuted_overlap_violations": 0,
    }


def recompute_c3() -> dict[str, Any]:
    original = validate_c3_rows(
        ROOT / "evidence/m8m-source-anchored/original-frozen/raw_runs.csv",
        "prospective_ardrone_v6",
        config_path=ROOT / "evidence/m8m-source-anchored/original-frozen/config.json",
        plan_path=ROOT / "evidence/m8m-source-anchored/original-frozen/plan.json",
        expected_runtime="5d0f50b22d2ec84fd3b2c900aaf105506cd7bd76a8e8fd3f1a9af2d89ead3e92",
    )
    replay = validate_c3_rows(
        ROOT / "evidence/m8m-source-anchored/raw_runs.csv",
        "prospective_ardrone_v13_corrected_replay",
        config_path=ROOT / "evidence/m8m-source-anchored/config.json",
        plan_path=ROOT / "evidence/m8m-source-anchored/plan.json",
        expected_runtime="dd494999ffa1d0f4029b5f07988f408182d8a362a77926da436716a7221c751d",
    )
    external_summary = read_json(ROOT / "evidence/m8m-source-anchored/external/summary.json")
    registered_cases = {
        row.get("id"): row
        for row in external_summary.get("cases", [])
        if isinstance(row, dict)
    }
    require(set(registered_cases) == {"ardrone_semantic_positive", "ardrone_semantic_negative"}, "C3 external case census differs")
    decisions: dict[str, str] = {}
    for identifier, expected in (
        ("ardrone_semantic_positive", "realizable"),
        ("ardrone_semantic_negative", "unrealizable"),
    ):
        case = ROOT / "evidence/m8m-source-anchored/external/cases" / identifier
        java_game = load_bundle(case / "java-independent-game.json")
        python_game = load_bundle(case / "python-raw-exact-game.json")
        java_decision = fixed_point(java_game).decision
        python_decision = fixed_point(python_game).decision
        record = registered_cases[identifier]
        prism_stdout = (case / "prism-stdout.txt").read_text(encoding="utf-8")
        prism_expected = 1.0 if expected == "realizable" else 0.0
        require(
            java_decision == python_decision == expected
            and record.get("expected_decision") == expected
            and record.get("java_observed_decision") == expected
            and record.get("status") == "PASS",
            f"C3 external decision differs for {identifier}",
        )
        require(
            record.get("prism_status") == "PASS"
            and float(record.get("prism_value")) == prism_expected
            and "Version: 3.2.4" in prism_stdout
            and f"Result: {prism_expected:.1f}" in prism_stdout,
            f"C3 PRISM log/value differs for {identifier}",
        )
        decisions[identifier] = expected
    require(
        external_summary.get("status") == "PASS"
        and external_summary.get("registered_cases") == 2
        and external_summary.get("passed_cases") == 2,
        "C3 external summary census differs",
    )
    final_audit = read_json(ROOT / "evidence/m8m-source-anchored/final-audit/summary.json")
    require(
        final_audit.get("status") == "PASS"
        and final_audit.get("integrity_status") == "PASS"
        and final_audit.get("registered_hypothesis_status") == "PASS",
        "C3 final audit is not PASS",
    )
    return {
        "status": "PASS",
        "original_frozen_observation": original,
        "post_outcome_replay_observation": replay,
        "serialized_games_re_solved": 4,
        "external_decisions": decisions,
        "typed_handoff": validate_handoff_bundle(),
    }


def recompute_m6() -> dict[str, Any]:
    summary = read_json(ROOT / "evidence/m6-prism/summary.json")
    models = summary.get("models")
    require(isinstance(models, list) and len(models) == 41, "M6 PRISM model census is not 41")
    c1_manifest = read_json(ROOT / "inputs/c1/semantic_boundaries_v2/manifest.json")
    expected_by_id = {
        row.get("id"): row.get("expected_decision")
        for row in c1_manifest.get("models", [])
        if isinstance(row, dict)
    }
    seen = set()
    values = Counter()
    for row in models:
        require(isinstance(row, dict), "M6 PRISM summary row is not an object")
        identifier = row.get("model_id")
        game = ROOT / "evidence/m6-prism/games" / f"{identifier}.prism"
        stdout_path = ROOT / "evidence/m6-prism" / str(row.get("stdout_file", ""))
        stderr_path = ROOT / "evidence/m6-prism" / str(row.get("stderr_file", ""))
        require(
            identifier in expected_by_id
            and identifier not in seen
            and game.is_file()
            and stdout_path.is_file()
            and stderr_path.is_file()
            and sha256_file(game) == row.get("game_sha256")
            and row.get("expected_decision") == expected_by_id[identifier]
            and row.get("external_decision") == expected_by_id[identifier]
            and row.get("status") == "PASS",
            f"M6 PRISM evidence differs for {identifier}",
        )
        value = float(row.get("prism_value"))
        require(value in {0.0, 1.0}, f"M6 PRISM value is not Boolean for {identifier}")
        stdout = stdout_path.read_text(encoding="utf-8")
        require(
            "Version: 3.2.4" in stdout
            and summary.get("property") in stdout
            and f"Result: {value:.1f}" in stdout
            and value == (1.0 if expected_by_id[identifier] == "realizable" else 0.0),
            f"M6 PRISM stdout/value differs for {identifier}",
        )
        values[value] += 1
        seen.add(identifier)
    require(
        seen == set(expected_by_id)
        and summary.get("status") == "PASS"
        and summary.get("passed_models") == 41
        and summary.get("failed_models") == 0
        and values == {0.0: 24, 1.0: 17},
        "M6 PRISM aggregate differs",
    )
    return {
        "status": "PASS",
        "observed_game_files_authenticated": 41,
        "observed_solver_logs_present": 82,
        "observed_boolean_values": {"zero": 24, "one": 17},
        "execution_boundary": "recorded PRISM-games 3.2.4 observations; binary not redistributed",
    }


def recompute_m8o() -> dict[str, Any]:
    command = (
        sys.executable,
        "-I",
        "-S",
        "-B",
        "analysis/audit_c2_block_decomposition.py",
        "--independent-manifest",
        "inputs/c2/inputs/generation_manifest.json",
        "--travel-manifest",
        "inputs/c2/travel_agency_family/manifest.json",
        "--m8k-raw",
        "evidence/m8k-performance/raw_runs.csv",
        "--m8k-metrics",
        "evidence/m8k-performance/metrics_long.csv",
        "--legacy-raw",
        "evidence/m8o-block-decomposition/legacy-direct-full-raw.csv",
        "--multistate-games",
        "inputs/c2/factored-multistate-games.json",
        "--output",
        "-",
    )
    completed = subprocess.run(
        command,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    require(completed.returncode == 0, "M8o checker failed: " + completed.stderr.strip())
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise ClaimError("M8o checker did not emit JSON") from error
    summary = value.get("summary")
    require(isinstance(summary, dict), "M8o result summary is missing")
    independent = summary.get("independent_family")
    negative = summary.get("negative_control")
    factored = value.get("factored_certificates")
    require(isinstance(independent, dict) and isinstance(negative, dict), "M8o result is incomplete")
    require(isinstance(factored, dict), "M8o factored evidence is missing")
    stored_factored = read_json(ROOT / "evidence/m8o-block-decomposition/factored-certificates.json")
    require(factored == stored_factored, "M8o stored factored evidence differs from recomputation")
    expected = {
        "conditions": 8,
        "m8k_jobs_passed": 80,
        "certificate_metric_cells_passed": 400,
        "direct_full_formula_jobs_passed": 35,
        "direct_full_k20_timeouts_retained": 5,
    }
    require(summary.get("status") == "PASS", "M8o recomputation is not PASS")
    require(all(independent.get(key) == count for key, count in expected.items()), "M8o independent-family census differs")
    require(negative.get("rejected_by_shared_nonstutter_screen") == 12, "M8o negative-control census differs")
    require(
        summary.get("semantic_factor_conditions_independently_checked") is True
        and summary.get("factored_certificates_independently_checked") is True
        and summary.get("flat_products_independently_resolved") == 9
        and summary.get("winning_priority_executions_checked") == 9
        and summary.get("multistate_winning_cases") == 1
        and summary.get("multistate_losing_cases") == 1
        and summary.get("factor_mutations_rejected") == 21,
        "M8o semantic-check boundary differs",
    )
    registered = factored.get("registered_positive_cases")
    multistate = factored.get("multistate_cases")
    mutations = factored.get("mutation_rejections")
    require(isinstance(registered, list) and len(registered) == 8, "M8o registered certificate count differs")
    require(isinstance(multistate, list) and len(multistate) == 2, "M8o multistate count differs")
    manifest = read_json(ROOT / "inputs/c2/inputs/generation_manifest.json")
    expected_sources = {
        record["id"]: record["sha256"]
        for record in manifest["models"]
    }
    seen_sources = {}
    flat_registered = 0
    for record in registered:
        certificate = record.get("certificate", {})
        source = certificate.get("source_model", {})
        seen_sources[source.get("id")] = source.get("sha256")
        require(record.get("consumer_check", {}).get("decision") == "realizable", "M8o registered decision differs")
        require(record.get("priority_execution", {}).get("status") == "PASS", "M8o registered priority execution differs")
        if record.get("flat_cross_check") is not None:
            require(record["flat_cross_check"].get("status") == "PASS", "M8o registered flat cross-check differs")
            flat_registered += 1
    require(seen_sources == expected_sources, "M8o certificate/source-manifest binding differs")
    require(flat_registered == 7, "M8o registered flat cross-check count differs")
    k20_record = next(
        record for record in registered
        if record["certificate"]["source_model"]["id"] == "independent_k20"
    )
    require(
        independent.get("k20_semantic_flat_states") == 2**20
        and independent.get("k20_factored_local_states") == 40
        and independent.get("k20_serialized_certificate_bytes") == k20_record.get("certificate_bytes")
        and type(k20_record.get("certificate_bytes")) is int,
        "M8o K20 succinct-certificate census differs",
    )
    observed_multistate = {
        record.get("certificate", {}).get("id"): record.get("consumer_check", {}).get("decision")
        for record in multistate
    }
    require(
        observed_multistate
        == {
            "multistate-winning-nondeterministic-handover": "realizable",
            "multistate-losing-monitor-outcome": "unrealizable",
        },
        "M8o multistate decision matrix differs",
    )
    winning_record = next(record for record in multistate if record["consumer_check"]["decision"] == "realizable")
    losing_record = next(record for record in multistate if record["consumer_check"]["decision"] == "unrealizable")
    require(
        winning_record.get("priority_execution", {}).get("complete_outcome_trace_count") == 2
        and winning_record.get("flat_cross_check", {}).get("state_count") == 12
        and losing_record.get("flat_cross_check", {}).get("state_count") == 10
        and losing_record.get("consumer_check", {}).get("local_losing_states") == 3,
        "M8o multistate witness census differs",
    )
    require(
        mutations
        == [
            "cross-block-precedence",
            "shared-nonstutter",
            "foreign-coordinate-change",
            "goal-uncontrollable-loop",
            "broken-kappa",
            "omitted-root",
            "monitor-projection",
            "rank-corruption",
            "nondeterministic-outcome-target",
            "losing-counterstrategy-omission",
            "foreign-monitor-change",
            "foreign-rs-change",
            "shared-stutter-monitor-change",
            "shared-stutter-rs-change",
            "unknown-monitor-action",
            "unknown-rs-action",
            "unrelated-pending-update-drop",
            "internal-action-pending-drop",
            "initial-pending-update-omission",
            "internal-action-precedence",
            "uncontrollable-update-action",
        ],
        "M8o mutation matrix differs",
    )
    return {
        "status": "PASS",
        "independent_conditions_checked": 8,
        "m8k_jobs_checked": 80,
        "certificate_metric_cells_checked": 400,
        "direct_full_formula_jobs_checked": 35,
        "direct_full_k20_timeouts_retained": 5,
        "travel_shared_action_screen_rejections": 12,
        "semantic_factor_conditions_independently_checked": True,
        "factored_certificates_checked": 10,
        "flat_products_resolved": 9,
        "winning_priority_executions_checked": 9,
        "multistate_winning_losing_cases": 2,
        "factor_mutations_rejected": 21,
    }


def recompute_rs() -> dict[str, Any]:
    recomputed = check_rs_manifest(ROOT / "inputs/rs/manifest.json")
    stored = read_json(ROOT / "evidence/rs-full-sigma/summary.json")
    require(recomputed == stored, "full-Sigma RS stored summary differs from recomputation")
    require(recomputed["case_count"] == 3, "full-Sigma RS case denominator differs")
    require(
        {case["id"] for case in recomputed["cases"]}
        == {
            "ordinary_event_counterexample",
            "conservative_initialization",
            "common_residual_intersection",
        },
        "full-Sigma RS case identifiers differ",
    )
    require(
        recomputed["decision_counts"] == {"SOUND": 2, "UNSOUND": 1},
        "full-Sigma RS decision census differs",
    )
    ordinary = next(
        case for case in recomputed["cases"] if case["id"] == "ordinary_event_counterexample"
    )
    require(
        ordinary["counterexample"]["activation_prefix"] == ["a", "start_r"]
        and ordinary["counterexample"]["observed_prefix"] == ["a", "start_r"]
        and ordinary["counterexample"]["continuation"] == ["b"],
        "full-Sigma RS counterexample witness differs",
    )
    return {
        "status": "PASS",
        "post_outcome_theorem_linked_cases": recomputed["case_count"],
        "sound_cases": recomputed["decision_counts"]["SOUND"],
        "unsound_cases": recomputed["decision_counts"]["UNSOUND"],
        "ordinary_event_counterexample_replayed": True,
        "alphabet_partition_checked": recomputed["alphabet_partition_checked"],
        "full_sigma_observer_monitor_total": recomputed["full_sigma_observer_monitor_total"],
        "activation_graph_exactness": recomputed["activation_graph_exactness"],
    }


def recompute_m8p() -> dict[str, Any]:
    fixture = ROOT / "inputs/c2/typed-partition-fixtures.json"
    try:
        summary, certificates, coordinate_screen = audit_typed_partition(ROOT, fixture)
    except PartitionAuditError as error:
        raise ClaimError("M8p typed partition audit failed: " + str(error)) from error
    stored_root = ROOT / "evidence/m8p-partition-discovery"
    require(
        canonical_json_bytes(summary)
        == canonical_json_bytes(read_json(stored_root / "summary.json")),
        "M8p stored summary differs from recomputation",
    )
    require(
        canonical_json_bytes(certificates)
        == canonical_json_bytes(read_json(stored_root / "partition-certificates.json")),
        "M8p stored certificates differ from recomputation",
    )
    require(
        canonical_json_bytes(coordinate_screen)
        == canonical_json_bytes(read_json(stored_root / "coordinate-screen.json")),
        "M8p stored coordinate screen differs from recomputation",
    )
    require(
        exact_integer(summary.get("positive_factored_count"), 3)
        and exact_integer(summary.get("positive_winning_count"), 2)
        and exact_integer(summary.get("positive_losing_count"), 1)
        and exact_integer(summary.get("obstruction_case_count"), 10)
        and exact_integer(summary.get("independent_certificate_pass_count"), 13)
        and exact_integer(summary.get("transport_witness_count"), 3)
        and exact_integer(summary.get("independent_transport_pass_count"), 3)
        and exact_integer(summary.get("transport_direct_flat_agreement_count"), 3)
        and canonical_json_bytes(summary.get("positive_maximum_partition_counts"))
        == canonical_json_bytes({
            "multiroot-uncontrollable-progress": 1,
            "multistate-losing-monitor-outcome": 1,
            "multistate-winning-nondeterministic-handover": 1,
        })
        and canonical_json_bytes(summary.get("obstruction_result_counts"))
        == canonical_json_bytes({"INELIGIBLE": 1, "NON_FACTORABLE": 9}),
        "M8p typed discovery census differs",
    )
    require(
        exact_integer(coordinate_screen.get("case_count"), 43)
        and exact_integer(coordinate_screen.get("c1_semantic_family_count"), 10)
        and exact_integer(coordinate_screen.get("nontrivial_typed_positive_claim_count"), 0),
        "M8p coordinate-screen claim boundary differs",
    )
    return {
        "status": "PASS",
        "unpartitioned_typed_positive_cases": 3,
        "maximum_two_block_partitions_discovered": 3,
        "winning_positive_cases": 2,
        "losing_positive_cases": 1,
        "controlled_obstruction_cases": 10,
        "independent_certificates_checked": 13,
        "transport_witnesses_independently_checked": 3,
        "direct_flat_decision_agreements": 3,
        "coordinate_screen_cases": 43,
        "coordinate_screen_semantic_families": 10,
        "coordinate_screen_typed_positive_claims": 0,
    }


def recompute_m8q() -> dict[str, Any]:
    try:
        recomputed = audit_native_factorization()
    except NativeAuditError as error:
        raise ClaimError("M8q source-native factorization audit failed: " + str(error)) from error
    stored = read_json(ROOT / "evidence/m8q-native-factorization/summary.json")
    require(
        canonical_json_bytes(recomputed) == canonical_json_bytes(stored),
        "M8q stored summary differs from fresh structural/source-binding audit",
    )
    require(
        exact_integer(recomputed.get("source_files"), 23)
        and exact_integer(recomputed.get("target_cells"), 41)
        and exact_integer(recomputed.get("provenance_clusters"), 10)
        and exact_integer(recomputed.get("successful_cells"), 35)
        and exact_integer(recomputed.get("invalid_or_inconclusive_cells"), 6)
        and exact_integer(recomputed.get("trivial_one_block_cells"), 33)
        and exact_integer(recomputed.get("producer_verified_refined_win_cells"), 2)
        and exact_integer(recomputed.get("producer_verified_refined_win_clusters"), 1)
        and exact_integer(recomputed.get("structurally_checked_bundles"), 35),
        "M8q source-native denominator/status census differs",
    )
    require(
        recomputed.get("refined_local_solver_sums", {}).get("arms2-r2")
        == {"states": 127174, "queries": 831356, "outcomes": 294632},
        "M8q R2 local-solver metrics differ",
    )
    require(
        recomputed.get("registration")
        == "post-outcome outcome-complete denominator freeze; not prospective or held out"
        and "producer remains TCB" in str(recomputed.get("claim_boundary")),
        "M8q claim boundary differs",
    )
    return {
        "status": "PASS",
        "ordinary_lts_source_files": 23,
        "source_definition_cells": 41,
        "provenance_clusters": 10,
        "successful_cells": 35,
        "invalid_or_inconclusive_cells": 6,
        "trivial_one_block_cells": 33,
        "producer_verified_refined_win_cells": 2,
        "producer_verified_refined_win_clusters": 1,
        "structurally_checked_bundles": 35,
        "source_replay_count": 0,
        "ordinary_lts_translation_tcb": True,
        "global_loss_claims": 0,
    }


def recompute_m8r() -> dict[str, Any]:
    try:
        recomputed = audit_native_source_dependencies()
    except (NativeDependencyAuditError, OSError) as error:
        raise ClaimError("M8r compiled-facts dependency replay failed: " + str(error)) from error
    stored = read_json(ROOT / "evidence/m8r-native-source-dependency-replay/audit.json")
    require(
        canonical_json_bytes(recomputed) == canonical_json_bytes(stored),
        "M8r stored audit differs from fresh compiled-facts replay audit",
    )
    require(
        exact_integer(recomputed.get("compiled_facts_replay_pass"), 41)
        and exact_integer(recomputed.get("dependency_receipt_agreement_count"), 35)
        and exact_integer(recomputed.get("component_partition_agreement_count"), 35)
        and exact_integer(recomputed.get("ownerless_gate_agreement_count"), 6)
        and exact_integer(recomputed.get("shared_mtsa_frontend_count"), 41)
        and exact_integer(recomputed.get("independent_source_frontend_count"), 0)
        and exact_integer(recomputed.get("ordinary_lts_source_replay_count"), 0)
        and exact_integer(recomputed.get("source_to_witness_replay_count"), 0)
        and recomputed.get("dependency_outcome_counts")
        == {"NONTRIVIAL_PARTITION": 2, "ONE_BLOCK": 33, "OWNERLESS_REJECT": 6},
        "M8r dependency replay census or boundary differs",
    )
    return {
        "status": "PASS",
        "compiled_facts_replay_cells": 41,
        "dependency_receipt_agreements": 35,
        "component_partition_agreements": 35,
        "ownerless_gate_agreements": 6,
        "shared_mtsa_frontend_cells": 41,
        "independent_source_frontend_cells": 0,
        "ordinary_lts_source_replay_cells": 0,
        "source_to_witness_replay_cells": 0,
        "fixed_endpoint_products_replayed": 0,
        "local_update_games_replayed": 0,
        "producer_tcb_includes_old_new_controller_synthesis": True,
    }


def recompute_m8s() -> dict[str, Any]:
    try:
        recomputed = audit_post_frontend_certificate()
    except (PostFrontendAuditError, PostFrontendCampaignError,
            PostFrontendCheckError, OSError) as error:
        raise ClaimError(
            "M8s post-frontend certificate semantics audit failed: " + str(error)
        ) from error
    stored = read_json(
        ROOT / "evidence/m8s-post-frontend-contract-certificate/audit.json"
    )
    require(
        canonical_json_bytes(recomputed) == canonical_json_bytes(stored),
        "M8s stored audit differs from fresh contract/certificate semantics audit",
    )
    require(
        exact_integer(recomputed.get("source_files"), 1)
        and exact_integer(recomputed.get("target_cells"), 2)
        and exact_integer(recomputed.get("provenance_clusters"), 1)
        and exact_integer(
            recomputed.get(
                "post_frontend_contract_ir_to_winning_certificate_semantic_verification"
            ),
            2,
        )
        and exact_integer(recomputed.get("global_transport_and_kappa_verified"), 2)
        and exact_integer(recomputed.get("independent_raw_source_frontend"), 0)
        and exact_integer(recomputed.get("independent_controller_synthesis"), 0)
        and exact_integer(recomputed.get("independent_win_synthesis"), 0)
        and exact_integer(recomputed.get("source_to_win_replay"), 0)
        and recomputed.get("totals", {}).get("candidate_buckets") == 4774
        and recomputed.get("totals", {}).get("candidate_outcomes") == 2682
        and recomputed.get("totals", {}).get("rank_states") == 212
        and recomputed.get("totals", {}).get("strategy_buckets") == 228,
        "M8s certificate semantics census or claim boundary differs",
    )
    return {
        "status": "PASS",
        "post_frontend_contract_ir_cells": 2,
        "winning_certificate_semantic_verifications": 2,
        "global_transport_and_kappa_verifications": 2,
        "rank_states": 212,
        "candidate_buckets": 4774,
        "candidate_outcomes": 2682,
        "strategy_buckets": 228,
        "same_author_post_outcome_cases": 2,
        "provenance_clusters": 1,
        "independent_raw_source_frontend": 0,
        "independent_controller_synthesis": 0,
        "independent_win_synthesis": 0,
        "source_to_win_replay": 0,
    }


def recompute_m8t() -> dict[str, Any]:
    protocol = ROOT / "protocols/productioncell_source_contract_certificate_v1_20260814.json"
    evidence = ROOT / "evidence/m8t-productioncell-source-contract-certificate"
    try:
        recomputed = audit_productioncell_source_certificate(protocol, evidence)
    except (SourceCertificateCampaignError, SourceContractError,
            PostFrontendCheckError, OSError) as error:
        raise ClaimError(
            "M8t source-to-supplied-certificate audit failed: " + str(error)
        ) from error
    stored = read_json(evidence / "audit.json")
    require(
        canonical_json_bytes(recomputed) == canonical_json_bytes(stored),
        "M8t stored audit differs from fresh source/certificate semantics audit",
    )
    require(
        exact_integer(recomputed.get("source_files"), 1)
        and exact_integer(recomputed.get("target_cells"), 2)
        and exact_integer(recomputed.get("provenance_clusters"), 1)
        and exact_integer(
            recomputed.get("source_to_post_frontend_contract_semantic_verification"),
            2,
        )
        and exact_integer(
            recomputed.get(
                "post_frontend_contract_to_supplied_certificate_semantic_verification"
            ),
            2,
        )
        and exact_integer(
            recomputed.get("source_to_supplied_certificate_semantic_verification"),
            2,
        )
        and exact_integer(recomputed.get("independent_controller_synthesis_executions"), 2)
        and exact_integer(recomputed.get("unique_independent_controller_pairs"), 1)
        and exact_integer(recomputed.get("unique_source_semantic_contracts"), 2)
        and exact_integer(recomputed.get("independent_win_synthesis"), 0)
        and exact_integer(recomputed.get("source_to_win_replay"), 0)
        and recomputed.get("source_census", {}).get("old_controller_states") == 162
        and recomputed.get("source_census", {}).get("old_controller_edges") == 432
        and recomputed.get("source_census", {}).get("new_controller_states") == 162
        and recomputed.get("source_census", {}).get("new_controller_edges") == 432
        and recomputed.get("source_census", {}).get("transition_requirement_machines") == 24
        and recomputed.get("source_census", {}).get("observers") == 44
        and recomputed.get("source_census", {}).get("activation_rows") == 304
        and recomputed.get("source_census", {}).get("activation_error_rows") == 164
        and recomputed.get("supplied_certificate_census", {}).get("candidate_buckets") == 4774
        and recomputed.get("supplied_certificate_census", {}).get("candidate_outcomes") == 2682
        and recomputed.get("supplied_certificate_census", {}).get("rank_states") == 212
        and recomputed.get("supplied_certificate_census", {}).get("strategy_buckets") == 228
        and recomputed.get("supplied_certificate_census", {}).get(
            "global_transport_and_kappa_verified"
        ) == 2,
        "M8t source/certificate census or claim boundary differs",
    )
    boundary = recomputed.get("claim_boundary")
    require(
        boundary == {
            "bounded_registered_mtsa_lts_profile": True,
            "same_author_independent_python_frontend": True,
            "independent_old_new_controller_synthesis": True,
            "post_outcome": True,
            "supplied_historical_certificate": True,
            "source_to_supplied_certificate_semantic_verification": True,
            "general_mtsa_frontend": False,
            "independent_win_synthesis": False,
            "source_to_win_replay": False,
            "held_out_cases": 0,
            "third_party_cases": 0,
            "production_cases": 0,
            "source_files": 1,
            "provenance_clusters": 1,
            "source_checker_runtime_frozen": False,
            "historical_m8s_runtime_reproduced": False,
        },
        "M8t source/certificate claim boundary differs",
    )
    return {
        "status": "PASS",
        "source_files": 1,
        "target_cells": 2,
        "source_semantic_contracts": 2,
        "controller_synthesis_executions": 2,
        "unique_controller_pairs": 1,
        "controller_states_per_old_new_pair": [81, 81],
        "controller_edges_per_old_new_pair": [216, 216],
        "source_to_supplied_certificate_semantic_verifications": 2,
        "candidate_buckets": 4774,
        "candidate_outcomes": 2682,
        "rank_states": 212,
        "strategy_buckets": 228,
        "global_transport_and_kappa_verifications": 2,
        "same_author_post_outcome_cases": 2,
        "provenance_clusters": 1,
        "independent_win_synthesis": 0,
        "source_to_win_replay": 0,
        "held_out_cases": 0,
        "third_party_cases": 0,
        "production_cases": 0,
    }


def recompute_m8u() -> dict[str, Any]:
    protocol = ROOT / "protocols/post_frontend_generated_win_panel_v1_20260815.json"
    evidence = ROOT / "evidence/m8u-post-frontend-generated-win-panel"
    try:
        recomputed = audit_generated_win_panel(protocol, evidence)
    except (GeneratedWinAuditError, GeneratedWinCampaignError,
            GeneratedWinCheckError, OSError) as error:
        raise ClaimError(
            "M8u generated post-frontend WIN-certificate audit failed: "
            + str(error)
        ) from error
    stored = read_json(evidence / "audit.json")
    require(
        canonical_json_bytes(recomputed) == canonical_json_bytes(stored),
        "M8u stored audit differs from fresh generated-certificate audit",
    )
    require(
        recomputed.get("status") == "PASS"
        and exact_integer(recomputed.get("source_files"), 2)
        and exact_integer(recomputed.get("target_cells"), 3)
        and exact_integer(recomputed.get("provenance_clusters"), 2)
        and exact_integer(
            recomputed.get("verified_generated_win_certificates"), 3
        )
        and exact_integer(recomputed.get("historical_outcome_inputs"), 0)
        and exact_integer(recomputed.get("supplied_certificate_inputs"), 0)
        and recomputed.get("industry_whole_system_block") is True
        and recomputed.get("industry_nontrivial_factorization") is False
        and recomputed.get("status_counts") == {
            "SUCCESS_WIN": 3,
            "INVALID_INPUT": 0,
            "INCONCLUSIVE_RANK_BOUND": 0,
            "INCONCLUSIVE_STATE_LIMIT": 0,
            "INCONCLUSIVE_BUCKET_LIMIT": 0,
            "INCONCLUSIVE_OUTCOME_LIMIT": 0,
            "INCONCLUSIVE_TIMEOUT": 0,
            "INCONCLUSIVE_OOM": 0,
            "ERROR_CRASH": 0,
            "CERTIFICATE_REJECTED": 0,
        }
        and recomputed.get("verified_totals", {}).get("candidate_buckets")
        == 15049
        and recomputed.get("verified_totals", {}).get("candidate_outcomes")
        == 6319
        and recomputed.get("verified_totals", {}).get("rank_states") == 622
        and recomputed.get("verified_totals", {}).get("strategy_buckets")
        == 778,
        "M8u generated-certificate census or outcome boundary differs",
    )
    boundary = recomputed.get("claim_boundary")
    require(
        isinstance(boundary, dict)
        and boundary.get("same_author_generator") is True
        and boundary.get("same_author_separate_checker") is True
        and boundary.get("conclusion_free_post_frontend_ir_only") is True
        and boundary.get("post_outcome") is True
        and boundary.get("calibrated_rank_bound") is True
        and boundary.get("shared_mtsa_frontend") is True
        and boundary.get("shared_post_frontend_semantic_adapter") is True
        and boundary.get("fixed_controller_synthesis_shared") is True
        and boundary.get("general_mtsa_frontend") is False
        and boundary.get("independent_raw_source_frontend") is False
        and boundary.get("independent_controller_synthesis") is False
        and boundary.get("independent_source_to_win_replay") is False
        and exact_integer(boundary.get("historical_outcome_inputs"), 0)
        and exact_integer(boundary.get("supplied_certificate_inputs"), 0)
        and exact_integer(boundary.get("held_out_cases"), 0)
        and exact_integer(boundary.get("third_party_cases"), 0)
        and exact_integer(boundary.get("production_cases"), 0)
        and exact_integer(boundary.get("native_contract_cases"), 0),
        "M8u generated-certificate claim boundary differs",
    )
    return {
        "status": "PASS",
        "source_files": 2,
        "target_cells": 3,
        "provenance_clusters": 2,
        "generated_win_certificate_semantic_verifications": 3,
        "nontrivial_factorization_cells": 2,
        "whole_system_block_cells": 1,
        "industry_whole_system_block": True,
        "industry_nontrivial_factorization": False,
        "rank_states": 622,
        "candidate_buckets": 15049,
        "candidate_outcomes": 6319,
        "strategy_buckets": 778,
        "same_author_post_outcome_cells": 3,
        "historical_outcome_inputs": 0,
        "supplied_certificate_inputs": 0,
        "independent_raw_source_frontend": 0,
        "independent_controller_synthesis": 0,
        "source_to_win_replay": 0,
        "held_out_cases": 0,
        "third_party_cases": 0,
        "production_cases": 0,
        "native_contract_cases": 0,
    }


def run_all() -> dict[str, Any]:
    return {
        "schema_version": "fg-ducs-public-reproduction-report-v1",
        "status": "PASS",
        "boundary": {
            "recomputed": "public LTS decisions, CSV claim metrics, exact games, fixed points, full-Sigma residual soundness, handoff graph/traces, 500 atomic handoff races, restricted factored synthesis, typed partition/obstruction certificates, source-native panel source/hash/bundle structural consistency, post-frontend compiled-facts dependency/partition/ownerless semantics, two post-frontend contract-IR certificate/transport semantic checks, two composed bounded-source-to-supplied-certificate semantic checks, and three freshly generated post-frontend WIN certificates checked by a separate process",
            "authenticated_observations": "historical Java timing/terminal rows and PRISM solver logs/values",
            "current_source": "separate source-rebuild test/smoke boundary; not claimed byte-identical to historical JARs",
        },
        "c1": recompute_c1(),
        "c2": recompute_c2(),
        "c3": recompute_c3(),
        "m6_prism": recompute_m6(),
        "m8n": recompute_m8n(),
        "m8o": recompute_m8o(),
        "m8p": recompute_m8p(),
        "m8q": recompute_m8q(),
        "m8r": recompute_m8r(),
        "m8s": recompute_m8s(),
        "m8t": recompute_m8t(),
        "m8u": recompute_m8u(),
        "rs_full_sigma": recompute_rs(),
    }


def parse_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="write the report to this path; default is stdout")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    arguments = parse_arguments(argv)
    try:
        report = run_all()
        payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        if arguments.output is None:
            print(payload, end="")
        else:
            arguments.output.write_text(payload, encoding="utf-8")
            print(json.dumps({"status": "PASS", "output": str(arguments.output)}))
        return 0
    except (ClaimError, OSError, UnicodeDecodeError, ValueError, subprocess.SubprocessError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
