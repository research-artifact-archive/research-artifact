#!/usr/bin/env python3
"""Offline audit for the registered M8s post-frontend certificate evidence."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from check_post_frontend_contract_certificate import (  # noqa: E402
    CheckError, canonical_bytes, load as load_checker, verify,
)
from run_post_frontend_contract_certificate import (  # noqa: E402
    CampaignError, canonical, load, sha256,
    verify_historical_case, verify_protocol,
)


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "protocols/post_frontend_contract_certificate_v1_20260814.json"
EVIDENCE = ROOT / "evidence/m8s-post-frontend-contract-certificate"
AUDIT_SCHEMA = "fg-ducs-post-frontend-certificate-audit-v1"


class AuditError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def safe_relative(value: Any, label: str) -> PurePosixPath:
    require(type(value) is str and bool(value), f"{label} is not text")
    result = PurePosixPath(value)
    require(not result.is_absolute() and ".." not in result.parts
            and result.as_posix() == value, f"unsafe {label}")
    return result


def terminal_fields(raw: bytes, label: str) -> tuple[list[str], dict[str, str]]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise AuditError(f"{label} is not UTF-8") from error
    result: dict[str, str] = {}
    diagnostics: list[str] = []
    for line in text.splitlines():
        if "=" not in line:
            diagnostics.append(line)
            continue
        key, value = line.split("=", 1)
        require(bool(key) and key not in result,
                f"{label} repeats a terminal field")
        result[key] = value
    return diagnostics, result


def verify_case(
    row: Mapping[str, Any], summary_row: Mapping[str, Any],
    protocol: Mapping[str, Any],
    panel_records: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[str, int]]:
    case_id = row["case_id"]
    require(summary_row.get("case_id") == case_id,
            "summary case order differs")
    case_dir = EVIDENCE / "cases" / case_id
    expected_files = {
        "checker.stderr.txt", "checker.stdout.txt", "facts-repeat.json",
        "facts-repeat.stderr.txt", "facts-repeat.stdout.txt", "facts.json",
        "facts.stderr.txt", "facts.stdout.txt", "record.json", "report.json",
    }
    require(case_dir.is_dir() and {
        path.name for path in case_dir.iterdir() if path.is_file()
    } == expected_files, f"case file census differs: {case_id}")
    require(not any(path.is_symlink() for path in case_dir.iterdir()),
            f"case evidence contains a symlink: {case_id}")

    source_row = row["source"]
    source = ROOT / Path(*safe_relative(source_row["path"], "source path").parts)
    require(source.is_file() and not source.is_symlink()
            and sha256(source) == source_row["sha256"],
            f"registered source differs: {case_id}")
    bundle_row = row["historical_bundle"]
    bundle = ROOT / Path(*safe_relative(
        bundle_row["path"], "historical bundle path").parts)
    require(bundle.is_file() and not bundle.is_symlink()
            and sha256(bundle) == bundle_row["sha256"],
            f"historical bundle differs: {case_id}")
    history_row = row["historical_record"]
    history = ROOT / Path(*safe_relative(
        history_row["path"], "historical record path").parts)
    require(history.is_file() and not history.is_symlink()
            and sha256(history) == history_row["sha256"],
            f"historical record differs: {case_id}")
    verify_historical_case(row, protocol, panel_records)

    facts = case_dir / "facts.json"
    repeat = case_dir / "facts-repeat.json"
    report = case_dir / "report.json"
    record_path = case_dir / "record.json"
    require(facts.read_bytes() == repeat.read_bytes(),
            f"fresh-JVM facts differ: {case_id}")
    expected_ir = row["expected_ir"]
    require(sha256(facts) == expected_ir["sha256"]
            and facts.stat().st_size == expected_ir["bytes"],
            f"stored facts identity differs: {case_id}")
    recomputed = verify(load_checker(facts), load_checker(bundle))
    require(canonical_bytes(recomputed) == report.read_bytes(),
            f"stored checker report differs from fresh semantics: {case_id}")
    expected_report = row["expected_report"]
    require(sha256(report) == expected_report["sha256"]
            and recomputed["semantic_digest_sha256"] ==
            expected_report["semantic_digest_sha256"],
            f"stored report identity differs: {case_id}")

    expected_terminal = {
        "source_sha256": source_row["sha256"],
        "definition": row["definition"],
        "conclusion_fields_present": "false",
        "terminal_record": "COMPLETE",
    }
    expected_diagnostics: list[str] = []
    expected_stderr = (
        b"Game state size:82\nWinning state size:81\n"
        b"Game state size:82\nWinning state size:81\n"
    )
    for prefix in ("facts", "facts-repeat"):
        diagnostics, terminal = terminal_fields(
            (case_dir / (prefix + ".stdout.txt")).read_bytes(), prefix)
        require(diagnostics == expected_diagnostics
                and terminal == expected_terminal,
                f"facts terminal differs: {case_id}/{prefix}")
        require((case_dir / (prefix + ".stderr.txt")).read_bytes() ==
                expected_stderr,
                f"facts stderr diagnostics differ: {case_id}/{prefix}")
    require((case_dir / "checker.stdout.txt").read_bytes() == b""
            and (case_dir / "checker.stderr.txt").read_bytes() == b"",
            f"checker emitted diagnostics on success: {case_id}")

    record = load(record_path)
    exact_record_keys = {
        "schema_version", "case_id", "condition", "definition", "cluster",
        "source_path", "source_sha256", "historical_bundle_path",
        "historical_bundle_sha256", "historical_record_path",
        "historical_record_sha256", "historical_producer_jar_sha256",
        "observation_jar_sha256", "facts_path", "facts_repeat_path",
        "facts_sha256", "facts_bytes", "fresh_jvm_byte_determinism",
        "facts_runs", "report_path", "report_sha256", "report_bytes",
        "checker_exit_code", "checker_timed_out", "checker_wall_nanos",
        "checker_stdout_sha256", "checker_stderr_sha256", "status",
        "semantic_digest_sha256", "totals", "transport",
    }
    require(set(record) == exact_record_keys,
            f"record key census differs: {case_id}")
    require(record["schema_version"] ==
            "fg-ducs-post-frontend-certificate-record-v1",
            f"record schema differs: {case_id}")
    for field, expected in {
        "case_id": case_id, "condition": row["condition"],
        "definition": row["definition"], "cluster": row["cluster"],
        "source_path": source_row["path"],
        "source_sha256": source_row["sha256"],
        "historical_bundle_path": bundle_row["path"],
        "historical_bundle_sha256": bundle_row["sha256"],
        "historical_record_path": history_row["path"],
        "historical_record_sha256": history_row["sha256"],
        "historical_producer_jar_sha256":
            protocol["runtime"]["historical_m8q_jar_sha256"],
        "observation_jar_sha256":
            protocol["runtime"]["observation_jar_sha256"],
        "facts_path": facts.relative_to(EVIDENCE).as_posix(),
        "facts_repeat_path": repeat.relative_to(EVIDENCE).as_posix(),
        "facts_sha256": sha256(facts),
        "facts_bytes": facts.stat().st_size,
        "fresh_jvm_byte_determinism": True,
        "report_path": report.relative_to(EVIDENCE).as_posix(),
        "report_sha256": sha256(report),
        "report_bytes": report.stat().st_size,
        "checker_exit_code": 0, "checker_timed_out": False,
        "status": "POST_FRONTEND_CONTRACT_TO_CERTIFICATE_SEMANTICS_VERIFIED",
        "semantic_digest_sha256": recomputed["semantic_digest_sha256"],
        "totals": recomputed["totals"], "transport": recomputed["transport"],
    }.items():
        require(record.get(field) == expected,
                f"record binding differs: {case_id}.{field}")
    require(type(record["checker_wall_nanos"]) is int
            and record["checker_wall_nanos"] > 0,
            f"checker timing differs: {case_id}")
    facts_runs = record["facts_runs"]
    require(type(facts_runs) is list and len(facts_runs) == 2,
            f"facts-run census differs: {case_id}")
    for index, run in enumerate(facts_runs):
        require(type(run) is dict and set(run) == {
            "exit_code", "timed_out", "wall_nanos", "stdout_sha256",
            "stderr_sha256",
        }, f"facts-run row differs: {case_id}/{index}")
        prefix = "facts" if index == 0 else "facts-repeat"
        require(run["exit_code"] == 0 and run["timed_out"] is False
                and type(run["wall_nanos"]) is int and run["wall_nanos"] > 0
                and run["stdout_sha256"] == sha256(
                    case_dir / (prefix + ".stdout.txt"))
                and run["stderr_sha256"] == sha256(
                    case_dir / (prefix + ".stderr.txt")),
                f"facts-run terminal differs: {case_id}/{index}")
    require(record["checker_stdout_sha256"] == sha256(
        case_dir / "checker.stdout.txt")
        and record["checker_stderr_sha256"] == sha256(
            case_dir / "checker.stderr.txt"),
            f"checker stream hash differs: {case_id}")
    require(summary_row == {
        "case_id": case_id,
        "record_path": record_path.relative_to(EVIDENCE).as_posix(),
        "record_sha256": sha256(record_path),
        "report_sha256": sha256(report),
        "semantic_digest_sha256": recomputed["semantic_digest_sha256"],
        "rank_states": recomputed["totals"]["rank_states"],
        "candidate_buckets": recomputed["totals"]["candidate_buckets"],
        "candidate_outcomes": recomputed["totals"]["candidate_outcomes"],
        "strategy_buckets": recomputed["totals"]["strategy_buckets"],
    }, f"summary record differs: {case_id}")
    return recomputed, {
        "facts_bytes": facts.stat().st_size,
        "report_bytes": report.stat().st_size,
        "record_bytes": record_path.stat().st_size,
    }


def audit() -> dict[str, Any]:
    protocol = load(PROTOCOL)
    panel_records = verify_protocol(protocol)
    cases = protocol["cases"]
    summary_path = EVIDENCE / "summary.json"
    summary = load(summary_path)
    require(summary.get("schema_version") ==
            "fg-ducs-post-frontend-certificate-summary-v1",
            "summary schema differs")
    require(summary.get("protocol_sha256") == sha256(PROTOCOL),
            "summary protocol binding differs")
    require(summary.get("observation_jar_sha256") ==
            protocol["runtime"]["observation_jar_sha256"]
            and summary.get("historical_m8q_jar_sha256") ==
            protocol["runtime"]["historical_m8q_jar_sha256"],
            "summary runtime roles differ")
    summary_rows = summary.get("records")
    require(type(summary_rows) is list and len(summary_rows) == 2,
            "summary record denominator differs")
    require(sorted(path.name for path in (EVIDENCE / "cases").iterdir()
                   if path.is_dir()) == [row["case_id"] for row in cases],
            "evidence case-directory census differs")

    reports: list[dict[str, Any]] = []
    byte_counts = {"facts_bytes": 0, "report_bytes": 0, "record_bytes": 0}
    for row, summary_row in zip(cases, summary_rows):
        report, sizes = verify_case(
            row, summary_row, protocol, panel_records)
        reports.append(report)
        for key, value in sizes.items():
            byte_counts[key] += value

    expected_summary = {
        "schema_version": "fg-ducs-post-frontend-certificate-summary-v1",
        "protocol_sha256": sha256(PROTOCOL),
        "observation_jar_sha256": protocol["runtime"]["observation_jar_sha256"],
        "historical_m8q_jar_sha256": protocol["runtime"]["historical_m8q_jar_sha256"],
        "source_files": 1, "target_cells": 2, "provenance_clusters": 1,
        "fresh_jvm_facts_deterministic": 2,
        "post_frontend_contract_ir_to_winning_certificate_semantic_verification": 2,
        "global_transport_and_kappa_verified": 2,
        "independent_raw_source_frontend": 0,
        "independent_controller_synthesis": 0,
        "independent_win_synthesis": 0,
        "source_to_win_replay": 0,
        "rank_states": 212, "candidate_buckets": 4774,
        "candidate_outcomes": 2682, "strategy_buckets": 228,
        "records": summary_rows, "claim_boundary": protocol["claim_boundary"],
    }
    require(summary == expected_summary, "summary aggregate differs")
    transport_totals = {
        key: sum(report["transport"][key] for report in reports)
        for key in reports[0]["transport"]
    }
    totals = {
        key: sum(report["totals"][key] for report in reports)
        for key in reports[0]["totals"]
    }
    return {
        "schema_version": AUDIT_SCHEMA,
        "status": "PASS",
        "protocol_sha256": sha256(PROTOCOL),
        "evidence_summary_sha256": sha256(summary_path),
        "source_files": 1, "target_cells": 2, "provenance_clusters": 1,
        "fresh_jvm_facts_deterministic": 2,
        "post_frontend_contract_ir_to_winning_certificate_semantic_verification": 2,
        "global_transport_and_kappa_verified": 2,
        "independent_raw_source_frontend": 0,
        "independent_controller_synthesis": 0,
        "independent_win_synthesis": 0,
        "source_to_win_replay": 0,
        "totals": totals,
        "transport_totals": transport_totals,
        **byte_counts,
        "claim_boundary": protocol["claim_boundary"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        observed = audit()
        raw = canonical(observed)
        if args.expected is not None:
            require(raw == canonical(load(args.expected)),
                    "stored audit differs from fresh audit")
        if args.output is not None:
            args.output.write_bytes(raw)
        else:
            sys.stdout.buffer.write(raw)
        return 0
    except (AuditError, CampaignError, CheckError, OSError, KeyError,
            TypeError, ValueError) as error:
        print("POST_FRONTEND_CERTIFICATE_AUDIT_INVALID=" + str(error),
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
