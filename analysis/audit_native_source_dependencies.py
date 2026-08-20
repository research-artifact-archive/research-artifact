#!/usr/bin/env python3
"""Offline audit of the registered M8r dependency-replay campaign."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from check_native_source_dependencies import ReplayError, canonical, compare, load  # noqa: E402
from run_native_factorization_panel import expand as expand_registration  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "protocols/native_source_dependency_replay_v1_20260814.json"
EVIDENCE = ROOT / "evidence/m8r-native-source-dependency-replay"


class AuditError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_relative(value: Any, label: str) -> PurePosixPath:
    require(type(value) is str and bool(value), f"{label} is not text")
    path = PurePosixPath(value)
    require(not path.is_absolute() and ".." not in path.parts and path.as_posix() == value, f"unsafe {label}")
    return path


def terminal_fields(payload: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in payload.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        require(bool(key) and key not in result, "duplicate facts-runner terminal field")
        result[key] = value
    return result


def verify_registered_files(protocol: Mapping[str, Any]) -> None:
    files = protocol.get("registered_files")
    require(type(files) is dict and set(files) == {
        "facts_runner_source", "independent_post_frontend_consumer", "campaign_runner", "offline_audit"
    }, "registered replay file census differs")
    for role, row in files.items():
        require(type(row) is dict and set(row) == {"path", "sha256"}, f"registered replay file binding differs: {role}")
        path = ROOT / safe_relative(row["path"], f"registered {role} path")
        require(path.is_file() and not path.is_symlink(), f"registered replay file is absent: {role}")
        require(sha256(path) == row["sha256"], f"registered replay file hash differs: {role}")


def audit() -> dict[str, Any]:
    protocol = load(PROTOCOL)
    require(protocol.get("schema_version") == "fg-ducs-native-source-dependency-replay-protocol-v1", "replay protocol schema differs")
    verify_registered_files(protocol)
    registration_row = protocol.get("registration_protocol")
    require(type(registration_row) is dict and set(registration_row) == {"path", "sha256"}, "registration protocol binding differs")
    registration_path = ROOT / safe_relative(registration_row["path"], "registration protocol path")
    require(sha256(registration_path) == registration_row["sha256"], "registration protocol hash differs")
    rows = expand_registration(load(registration_path))
    expected = {row["case_id"]: row for row in rows}
    checked_sources: set[str] = set()
    for row in rows:
        if row["path"] in checked_sources:
            continue
        source_path = ROOT / safe_relative(row["path"], "registered source path")
        require(source_path.is_file() and not source_path.is_symlink(), f"registered source is absent: {row['path']}")
        require(sha256(source_path) == row["sha256"], f"registered source hash differs: {row['path']}")
        checked_sources.add(row["path"])
    require(len(checked_sources) == 23, "registered source-file denominator differs")
    required_outcomes = protocol.get("required_dependency_outcome_census")
    require(required_outcomes == {
        "ONE_BLOCK": 33, "NONTRIVIAL_PARTITION": 2, "OWNERLESS_REJECT": 6
    }, "protocol dependency-outcome census differs")

    summary_path = EVIDENCE / "summary.json"
    summary = load(summary_path)
    require(summary.get("schema_version") == "fg-ducs-native-source-dependency-replay-summary-v1", "replay summary schema differs")
    require(summary.get("protocol_sha256") == sha256(PROTOCOL), "replay summary protocol binding differs")
    require(summary.get("registration_protocol_sha256") == sha256(registration_path), "replay summary registration binding differs")
    require(summary.get("jar_sha256") == protocol["runtime"]["jar_sha256"], "replay summary runtime binding differs")
    for key, expected_count in {
        "source_files": 23,
        "target_cells": 41,
        "provenance_clusters": 10,
        "facts_extraction_success": 41,
        "compiled_facts_replay_count": 41,
        "compiled_facts_replay_pass": 41,
        "dependency_receipt_agreement_count": 35,
        "component_partition_agreement_count": 35,
        "ownerless_gate_agreement_count": 6,
        "shared_mtsa_frontend_count": 41,
        "independent_source_frontend_count": 0,
        "ordinary_lts_source_replay_count": 0,
        "source_to_witness_replay_count": 0,
    }.items():
        require(type(summary.get(key)) is int and summary[key] == expected_count, f"replay summary count differs: {key}")
    require(summary.get("claim_boundary") == protocol.get("claim_boundary"), "replay claim boundary differs")
    records = summary.get("records")
    require(type(records) is list and len(records) == 41, "replay record denominator differs")
    case_directories = sorted(path.name for path in (EVIDENCE / "cases").iterdir() if path.is_dir())
    require(case_directories == sorted(expected), "replay case-directory census differs")

    outcome_counts: Counter[str] = Counter()
    receipt_counts: Counter[str] = Counter()
    facts_bytes = 0
    report_bytes = 0
    record_bytes = 0
    seen: set[str] = set()
    original_panel = ROOT / str(protocol["registered_panel_path"])
    for record in records:
        require(type(record) is dict, "replay record is not an object")
        case_id = record.get("case_id")
        require(type(case_id) is str and case_id in expected and case_id not in seen, "replay case ID differs")
        seen.add(case_id)
        row = expected[case_id]
        for record_field, source_field in {
            "path": "path", "source_sha256": "sha256", "cluster": "cluster",
            "condition": "condition", "definition": "definition",
        }.items():
            require(record.get(record_field) == row[source_field], f"replay registration differs: {case_id}.{record_field}")
        case_dir = EVIDENCE / "cases" / case_id
        files = sorted(path.name for path in case_dir.iterdir() if path.is_file())
        require(files == ["facts.json", "record.json", "report.json", "stderr.txt", "stdout.txt"], f"replay case file census differs: {case_id}")
        facts_path = case_dir / "facts.json"
        report_path = case_dir / "report.json"
        record_path = case_dir / "record.json"
        require(record.get("facts_path") == facts_path.relative_to(EVIDENCE).as_posix(), f"facts path differs: {case_id}")
        require(record.get("report_path") == report_path.relative_to(EVIDENCE).as_posix(), f"report path differs: {case_id}")
        require(record.get("record_path") == record_path.relative_to(EVIDENCE).as_posix(), f"record path differs: {case_id}")
        for path, prefix in ((facts_path, "facts"), (report_path, "report"), (record_path, "record")):
            require(sha256(path) == record.get(prefix + "_sha256"), f"{prefix} hash differs: {case_id}")
            if prefix != "record":
                require(path.stat().st_size == record.get(prefix + "_bytes"), f"{prefix} size differs: {case_id}")
        require(sha256(case_dir / "stdout.txt") == record.get("stdout_sha256"), f"stdout hash differs: {case_id}")
        require(sha256(case_dir / "stderr.txt") == record.get("stderr_sha256"), f"stderr hash differs: {case_id}")
        require(record.get("facts_exit_code") == 0 and record.get("facts_timed_out") is False, f"facts terminal differs: {case_id}")
        terminal = terminal_fields((case_dir / "stdout.txt").read_text(encoding="utf-8"))
        require(terminal == {
            "source_sha256": row["sha256"],
            "definition": row["definition"],
            "component_count": str(sum(len(block) for block in record["component_partition"])),
            "conclusion_fields_present": "false",
            "terminal_record": "COMPLETE",
        }, f"facts-runner terminal fields differ: {case_id}")
        stored_record = load(record_path)
        expected_record = dict(record)
        expected_record.pop("record_path")
        expected_record.pop("record_sha256")
        require(canonical(stored_record) == canonical(expected_record), f"stored replay record differs: {case_id}")

        original_case = original_panel / "cases" / case_id
        original_record = load(original_case / "record.json")
        original_bundle_path = original_case / "bundle.json"
        original_bundle = load(original_bundle_path) if original_bundle_path.is_file() else None
        recomputed = compare(
            load(facts_path), original_record, original_bundle,
            (original_case / "stderr.txt").read_text(encoding="utf-8"),
        )
        require(canonical(recomputed) == canonical(load(report_path)), f"recomputed replay report differs: {case_id}")
        require(recomputed["status"] == record.get("replay_status") == "PASS", f"replay status differs: {case_id}")
        require(recomputed["dependency_outcome"] == record.get("dependency_outcome"), f"dependency outcome differs: {case_id}")
        require(recomputed["registered_producer_process_status"] == record.get("registered_producer_process_status"), f"registered producer process status differs: {case_id}")
        require(recomputed["registered_producer_factor_status"] == record.get("registered_producer_factor_status"), f"registered producer factor status differs: {case_id}")
        require(recomputed["dependency_receipt_agreement"] == record.get("dependency_receipt_agreement"), f"dependency receipt agreement differs: {case_id}")
        require(recomputed["component_partition_agreement"] == record.get("component_partition_agreement"), f"component partition agreement differs: {case_id}")
        require(recomputed["ownerless_gate_agreement"] == record.get("ownerless_gate_agreement"), f"ownerless gate agreement differs: {case_id}")
        require(recomputed["component_partition"] == record.get("component_partition"), f"partition differs: {case_id}")
        require(recomputed["dependency_receipt_count"] == record.get("dependency_receipt_count"), f"receipt count differs: {case_id}")
        require(recomputed["ownerless_obstructions"] == record.get("ownerless_obstructions"), f"ownerless set differs: {case_id}")
        outcome_counts[recomputed["dependency_outcome"]] += 1
        receipt_counts.update(recomputed["receipt_counts"])
        facts_bytes += facts_path.stat().st_size
        report_bytes += report_path.stat().st_size
        record_bytes += record_path.stat().st_size

    require(outcome_counts == Counter(required_outcomes), "replayed dependency-outcome census differs")
    require(dict(sorted(outcome_counts.items())) == summary.get("dependency_outcome_counts"), "summary dependency-outcome census differs")
    require(dict(sorted(receipt_counts.items())) == summary.get("receipt_counts"), "summary receipt census differs")
    return {
        "schema_version": "fg-ducs-native-source-dependency-replay-audit-v1",
        "status": "PASS",
        "protocol_sha256": sha256(PROTOCOL),
        "evidence_summary_sha256": sha256(summary_path),
        "source_files": 23,
        "target_cells": 41,
        "provenance_clusters": 10,
        "compiled_facts_replay_pass": 41,
        "dependency_receipt_agreement_count": 35,
        "component_partition_agreement_count": 35,
        "ownerless_gate_agreement_count": 6,
        "shared_mtsa_frontend_count": 41,
        "independent_source_frontend_count": 0,
        "ordinary_lts_source_replay_count": 0,
        "source_to_witness_replay_count": 0,
        "dependency_outcome_counts": dict(sorted(outcome_counts.items())),
        "receipt_counts": dict(sorted(receipt_counts.items())),
        "facts_bytes": facts_bytes,
        "report_bytes": report_bytes,
        "record_bytes": record_bytes,
        "claim_boundary": protocol["claim_boundary"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected", type=Path)
    args = parser.parse_args(argv)
    try:
        observed = audit()
        if args.expected is not None:
            require(canonical(observed) == canonical(load(args.expected)), "stored audit summary differs")
    except (AuditError, ReplayError, OSError, KeyError, UnicodeDecodeError) as error:
        print("NATIVE_SOURCE_DEPENDENCY_AUDIT_REJECT=" + str(error), file=sys.stderr)
        return 2
    sys.stdout.buffer.write(canonical(observed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
