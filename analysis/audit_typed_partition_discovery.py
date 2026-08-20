#!/usr/bin/env python3
"""End-to-end audit for typed factor discovery and obstruction evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from check_typed_partition_certificate import check as independent_check  # noqa: E402
from check_discovered_witness import check as independent_witness_check  # noqa: E402
from discover_typed_partition import discover, sha256_json  # noqa: E402
from screen_complete_game_factorability import run as screen_corpus  # noqa: E402
from synthesize_discovered_witness import synthesize as synthesize_witness  # noqa: E402


SUMMARY_SCHEMA = "fg-ducs-typed-partition-audit-v1"
FIXTURE_SCHEMA = "fg-ducs-typed-partition-fixtures-v1"
EXPECTED_POSITIVES = {
    "multistate-winning-nondeterministic-handover": "realizable",
    "multistate-losing-monitor-outcome": "unrealizable",
    "multiroot-uncontrollable-progress": "realizable",
}
EXPECTED_OBSTRUCTIONS = {
    "obstruction-cross-precedence": ("NON_FACTORABLE", "MANDATORY_CROSS_PRECEDENCE"),
    "obstruction-cross-subjects": ("NON_FACTORABLE", "ACTION_SUBJECTS_CROSS_BLOCK"),
    "obstruction-foreign-enabledness": ("NON_FACTORABLE", "ACTION_CONTEXT_DEPENDENCE"),
    "obstruction-foreign-outcome-set": ("NON_FACTORABLE", "ACTION_CONTEXT_DEPENDENCE"),
    "obstruction-foreign-frame": ("NON_FACTORABLE", "ACTION_FOREIGN_FRAME"),
    "obstruction-safe-nonrectangular": ("NON_FACTORABLE", "SAFE_NONRECTANGULAR"),
    "obstruction-state-nonrectangular": ("NON_FACTORABLE", "STATE_NONRECTANGULAR"),
    "obstruction-handover-nonrectangular": ("NON_FACTORABLE", "HANDOVER_NONRECTANGULAR"),
    "obstruction-goal-uc-activity": ("INELIGIBLE", "GOAL_UNCONTROLLABLE_ACTIVITY"),
    "obstruction-root-nonrectangular": ("NON_FACTORABLE", "ROOT_NONRECTANGULAR"),
}


class AuditError(RuntimeError):
    pass


def need(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AuditError(f"invalid JSON: {path}") from error
    need(isinstance(value, dict), f"JSON root is not an object: {path}")
    return value


def declared_support_unit_count(case: Mapping[str, Any]) -> int:
    """Count units disclosed by dependencies plus direct action subjects.

    This is deliberately stricter than the producer's mandatory-dependency
    contraction: a positive fixture must not encode its final partition merely
    by listing all same-block atoms together as action subjects.
    """
    atoms = [record.get("id") for record in case.get("atoms", [])]
    need(all(isinstance(atom, str) for atom in atoms), "fixture atom table differs")
    parent = {str(atom): str(atom) for atom in atoms}

    def root(atom: str) -> str:
        while parent[atom] != atom:
            parent[atom] = parent[parent[atom]]
            atom = parent[atom]
        return atom

    def merge(members: Sequence[str]) -> None:
        if not members:
            return
        head = root(members[0])
        for member in members[1:]:
            other = root(member)
            if head != other:
                if head > other:
                    head, other = other, head
                parent[other] = head

    for dependency in case.get("dependencies", []):
        merge([str(atom) for atom in dependency.get("atoms", [])])
    for action in case.get("actions", []):
        if action.get("kind") != "shared_stutter":
            merge([str(atom) for atom in action.get("subjects", [])])
    return len({root(atom) for atom in parent})


def contains_expected_obstruction(
    case: Mapping[str, Any], certificate: Mapping[str, Any], expected: str
) -> bool:
    if expected == "MANDATORY_CROSS_PRECEDENCE":
        target = {"pending:prepare", "pending:arm"}
        dependency = any(
            isinstance(record, dict)
            and record.get("kind") == "precedence"
            and set(record.get("atoms", [])) == target
            for record in case.get("dependencies", [])
        )
        same_unit = any(target <= set(unit) for unit in certificate.get("mandatory_units", []))
        return dependency and same_unit
    if certificate.get("result") == "INELIGIBLE":
        value = certificate.get("ineligibility_obstruction")
        return isinstance(value, dict) and value.get("kind") == expected
    return any(
        isinstance(record, dict)
        and isinstance(record.get("obstruction"), dict)
        and record["obstruction"].get("kind") == expected
        for record in certificate.get("root_cut_ledger", [])
    )


def run(root: Path, fixture_path: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    protocol_path = root / "protocols/typed_partition_discovery_v1_20260813.json"
    protocol = load(protocol_path)
    need(protocol.get("schema_version") == "fg-ducs-typed-partition-protocol-v1", "partition protocol schema differs")
    registered = protocol.get("registered_files")
    need(isinstance(registered, dict) and len(registered) == 8, "partition protocol file census differs")
    registered_fixture: Path | None = None
    for label, record in registered.items():
        need(isinstance(record, dict) and set(record) == {"path", "sha256"}, f"partition protocol record differs: {label}")
        relative = Path(str(record["path"]))
        need(not relative.is_absolute() and ".." not in relative.parts, f"partition protocol path is unsafe: {label}")
        target = root / relative
        need(target.is_file() and not target.is_symlink() and digest(target) == record["sha256"], f"partition protocol hash differs: {label}")
        if label == "fixtures":
            registered_fixture = target.resolve()
    need(
        registered_fixture is not None
        and fixture_path.resolve() == registered_fixture
        and digest(fixture_path) == registered["fixtures"]["sha256"],
        "requested fixture is not the protocol-registered fixture",
    )
    fixtures = load(fixture_path)
    need(fixtures.get("schema_version") == FIXTURE_SCHEMA, "fixture schema differs")
    positives = fixtures.get("positive_cases")
    obstructions = fixtures.get("obstruction_cases")
    need(isinstance(positives, list) and isinstance(obstructions, list), "fixture case tables differ")
    need({case.get("id") for case in positives} == set(EXPECTED_POSITIVES), "positive fixture ids differ")
    need({case.get("id") for case in obstructions} == set(EXPECTED_OBSTRUCTIONS), "obstruction fixture ids differ")
    for case in positives + obstructions:
        provenance = case.get("provenance")
        need(isinstance(provenance, dict), f"fixture provenance differs: {case.get('id')}")
        source_path = Path(str(provenance.get("source_path")))
        need(not source_path.is_absolute() and ".." not in source_path.parts, f"fixture source path is unsafe: {case.get('id')}")
        source = root / source_path
        need(source.is_file() and not source.is_symlink(), f"fixture source is absent: {case.get('id')}")
        need(provenance.get("source_sha256") == digest(source), f"fixture source hash differs: {case.get('id')}")

    certificates: list[dict[str, Any]] = []
    independent_reports: list[dict[str, Any]] = []
    transport_witnesses: list[dict[str, Any]] = []
    transport_reports: list[dict[str, Any]] = []
    for case in positives + obstructions:
        need(isinstance(case, dict), "fixture case is not an object")
        certificate = discover(case, partition_limit=2_000_000, maximum_partition_count=10_000)
        report = independent_check(case, certificate, max_atoms=12)
        need(report.get("status") == "PASS", f"independent certificate check failed: {case.get('id')}")
        need(certificate.get("input_game_sha256") == sha256_json(case), "producer input binding differs")
        certificates.append(certificate)
        independent_reports.append({"id": case["id"], **report})
        if case in positives:
            witness = synthesize_witness(case, certificate)
            transport = independent_witness_check(case, certificate, witness)
            need(transport.get("status") == "PASS", f"independent transport check failed: {case.get('id')}")
            transport_witnesses.append(witness)
            transport_reports.append(transport)

    by_id = {certificate["game_id"]: certificate for certificate in certificates}
    for identifier, decision in EXPECTED_POSITIVES.items():
        certificate = by_id[identifier]
        need(
            certificate["result"] == "FACTORED"
            and certificate["maximum_block_count"] == 2
            and certificate["maximum_partition_count"] == 1,
            f"positive partition differs or is not unique: {identifier}",
        )
        case = next(value for value in positives if value["id"] == identifier)
        need(case["provenance"]["expected_decision"] == decision, f"positive decision metadata differs: {identifier}")
        need(len(certificate["mandatory_units"]) > certificate["maximum_block_count"], f"positive boundary was supplied by mandatory units: {identifier}")
        need(declared_support_unit_count(case) > certificate["maximum_block_count"], f"positive boundary was supplied by dependency/action declarations: {identifier}")
        need(certificate["evaluated_partition_count"] > 1, f"positive partition search was not exercised: {identifier}")
    transport_by_id = {report["game_id"]: report for report in transport_reports}
    need(set(transport_by_id) == set(EXPECTED_POSITIVES), "transport report ids differ")
    for identifier, decision in EXPECTED_POSITIVES.items():
        need(transport_by_id[identifier]["decision"] == decision, f"transport decision differs: {identifier}")
    signatures = {
        (
            len(case["states"]),
            sum(state["initial"] for state in case["states"]),
            len(case["actions"]),
            len(case["buckets"]),
            case["provenance"]["expected_decision"],
        )
        for case in positives
    }
    need(len(signatures) == 3, "positive structural signatures are not pairwise distinct")
    obstruction_census: Counter[str] = Counter()
    for identifier, (result, expected_kind) in EXPECTED_OBSTRUCTIONS.items():
        certificate = by_id[identifier]
        need(certificate["result"] == result, f"obstruction decision differs: {identifier}")
        case = next(value for value in obstructions if value["id"] == identifier)
        need(contains_expected_obstruction(case, certificate, expected_kind), f"expected obstruction is absent: {identifier}/{expected_kind}")
        obstruction_census[expected_kind] += 1

    screen = screen_corpus(root)
    need(screen.get("status") == "PASS" and screen.get("case_count") == 43, "coordinate screen case count differs")
    need(screen.get("classifications") == {
        "MISSING_CARTESIAN_TUPLE": 13,
        "RECTANGULAR_BUT_GOAL_EMPTY": 4,
        "SINGLE_SUPPORT_COMPONENT": 26,
    }, "coordinate screen census differs")
    need(screen.get("c1_semantic_family_count") == 10, "coordinate screen family denominator differs")
    need(screen.get("nontrivial_typed_positive_claim_count") == 0, "coordinate screen overclaims a typed positive")

    bundle = {
        "schema_version": "fg-ducs-typed-partition-certificate-bundle-v1",
        "fixture_sha256": digest(fixture_path),
        "protocol_sha256": digest(protocol_path),
        "case_count": len(certificates),
        "certificates": certificates,
        "independent_reports": independent_reports,
        "transport_witnesses": transport_witnesses,
        "transport_reports": transport_reports,
    }
    summary = {
        "schema_version": SUMMARY_SCHEMA,
        "status": "PASS",
        "analysis_class": "post-outcome author typed-contract discovery and independent consumption",
        "fixture_sha256": digest(fixture_path),
        "protocol_sha256": digest(protocol_path),
        "positive_case_count": len(positives),
        "positive_nonisomorphic_multistate_count": 3,
        "positive_winning_count": sum(report["decision"] == "realizable" for report in transport_reports),
        "positive_losing_count": sum(report["decision"] == "unrealizable" for report in transport_reports),
        "positive_factored_count": sum(by_id[identifier]["result"] == "FACTORED" for identifier in EXPECTED_POSITIVES),
        "positive_maximum_block_counts": {identifier: by_id[identifier]["maximum_block_count"] for identifier in sorted(EXPECTED_POSITIVES)},
        "positive_maximum_partition_counts": {identifier: by_id[identifier]["maximum_partition_count"] for identifier in sorted(EXPECTED_POSITIVES)},
        "positive_mandatory_unit_counts": {identifier: len(by_id[identifier]["mandatory_units"]) for identifier in sorted(EXPECTED_POSITIVES)},
        "positive_declared_support_unit_counts": {
            identifier: declared_support_unit_count(next(value for value in positives if value["id"] == identifier))
            for identifier in sorted(EXPECTED_POSITIVES)
        },
        "positive_evaluated_partition_counts": {identifier: by_id[identifier]["evaluated_partition_count"] for identifier in sorted(EXPECTED_POSITIVES)},
        "obstruction_case_count": len(obstructions),
        "obstruction_result_counts": dict(sorted(Counter(by_id[identifier]["result"] for identifier in EXPECTED_OBSTRUCTIONS).items())),
        "obstruction_kind_counts": dict(sorted(obstruction_census.items())),
        "independent_certificate_pass_count": len(independent_reports),
        "transport_witness_count": len(transport_witnesses),
        "independent_transport_pass_count": len(transport_reports),
        "transport_direct_flat_agreement_count": sum(
            report.get("direct_flat_decision_agrees") is True for report in transport_reports
        ),
        "transport_semantic_flat_state_count": sum(
            int(report["semantic_flat_state_count"]) for report in transport_reports
        ),
        "transport_factored_local_state_count": sum(
            int(report["factored_local_state_count"]) for report in transport_reports
        ),
        "coordinate_screen": {
            "case_count": screen["case_count"],
            "c1_semantic_family_count": screen["c1_semantic_family_count"],
            "c3_author_adaptation_case_count": screen["c3_author_adaptation_case_count"],
            "totals": screen["totals"],
            "classifications": screen["classifications"],
            "typed_positive_claim_count": 0,
        },
        "claim_boundary": [
            "the exact discovery result is relative to the supplied total atomization and complete typed flat table",
            "the completeness of typed dependency declarations is an external input obligation, not inferred or proved by the checker",
            "typed dependency hyperedges and direct action subjects impose mandatory coupling but remain strictly finer than every positive partition",
            "the three positives and ten obstructions are post-outcome author fixtures",
            "the three positives connect discovered partitions to independently checked local solve, rank-sum/kappa or losing-cylinder witnesses and bounded flat decisions",
            "the v1 43-bundle screen is diagnostic only and cannot certify typed block-factorability",
            "no arbitrary-LTS atom inference, production parser, native third-party contract, held-out study, or prevalence claim",
        ],
    }
    return summary, bundle, screen


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--fixtures", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)
    root = args.artifact_root.resolve()
    fixture_path = (args.fixtures or root / "inputs/c2/typed-partition-fixtures.json").resolve()
    summary, bundle, screen = run(root, fixture_path)
    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        write_json(args.output_dir / "summary.json", summary)
        write_json(args.output_dir / "partition-certificates.json", bundle)
        write_json(args.output_dir / "coordinate-screen.json", screen)
        evidence_files = ["coordinate-screen.json", "partition-certificates.json", "summary.json"]
        (args.output_dir / "SHA256SUMS").write_text(
            "".join(f"{digest(args.output_dir / name)}  {name}\n" for name in evidence_files),
            encoding="utf-8",
            newline="\n",
        )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
