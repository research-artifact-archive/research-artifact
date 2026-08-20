#!/usr/bin/env python3
"""Run the registered M8t source-to-supplied-certificate bridge.

The source checker independently parses and synthesizes the bounded
ProductionCell profile before it opens the unchanged M8s conclusion-free
facts.  The unchanged M8s checker then verifies the historical supplied
certificate.  This composes two semantic checks; it does not synthesize WIN
and is not a source-to-WIN replay.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_SCHEMA = "fg-ducs-productioncell-source-certificate-protocol-v1"
SUMMARY_SCHEMA = "fg-ducs-productioncell-source-certificate-summary-v1"
RECORD_SCHEMA = "fg-ducs-productioncell-source-certificate-record-v1"
CAMPAIGN_ID = "m8t-productioncell-source-contract-certificate-20260814a"
EXPECTED_CASES = {
    "productioncell-arms2-base-productioncell-arms-2-fg": {
        "condition": "arms2-base", "definition": "UpdCont_OTF_FG",
        "transition_requirement_machines": 0,
    },
    "productioncell-arms2-r2-productioncell-arms-2-fg": {
        "condition": "arms2-r2", "definition": "UpdCont_OTF_FG_R2",
        "transition_requirement_machines": 24,
    },
}
CLAIM_BOUNDARY = {
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
}
SOURCE_REPORT_KEYS = {
    "schema_version", "status", "profile", "source_name", "source_sha256",
    "definition", "source_semantic_digest", "controller_pair_semantic_digest",
    "bounded_registered_mtsa_lts_frontend_replay",
    "independent_old_new_controller_synthesis",
    "independent_controller_pair_synthesis_count",
    "source_to_post_frontend_contract_semantic_agreement",
    "independent_win_synthesis", "source_to_win_replay",
    "certificate_supplied_downstream", "verified_fields", "census",
    "claim_boundary", "ir_sha256",
}
VERIFIED_FIELDS = [
    "components", "transfer_relations", "old_safety_machines",
    "new_safety_machines", "transition_requirement_machines",
    "observer_machines", "observer_registry", "new_activation_sources",
    "controllers", "protocol", "controllable_actions", "flags",
    "boundary_actions", "load_selector",
]


class CampaignError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CampaignError(message)


def canonical(value: Any) -> bytes:
    try:
        return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":"), allow_nan=False)
                + "\n").encode("utf-8")
    except (TypeError, ValueError) as error:
        raise CampaignError("value is not canonical JSON") from error


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load(path: Path) -> dict[str, Any]:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            require(key not in result, "duplicate JSON key: " + key)
            result[key] = value
        return result

    try:
        value = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=unique,
            parse_constant=lambda token: (_ for _ in ()).throw(
                ValueError(token)),
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError,
            ValueError) as error:
        raise CampaignError("invalid strict JSON: " + str(path)) from error
    require(type(value) is dict, "JSON root is not an object")
    return value


def exact_keys(value: Any, expected: set[str], label: str) -> Mapping[str, Any]:
    require(type(value) is dict and set(value) == expected,
            f"{label} key census differs")
    return value


def hex64(value: Any, label: str) -> str:
    require(type(value) is str and len(value) == 64
            and all(character in "0123456789abcdef" for character in value),
            f"{label} is not lowercase SHA-256")
    return value


def safe_relative(value: Any, label: str) -> PurePosixPath:
    require(type(value) is str and bool(value), f"{label} is not text")
    path = PurePosixPath(value)
    require(not path.is_absolute() and ".." not in path.parts
            and path.as_posix() == value, f"unsafe {label}")
    return path


def registered_path(row: Any, label: str, *, bytes_field: bool = False) -> Path:
    expected = {"path", "sha256", "bytes"} if bytes_field else {"path", "sha256"}
    value = exact_keys(row, expected, label)
    relative = safe_relative(value["path"], label + " path")
    path = ROOT / Path(*relative.parts)
    require(path.is_file() and not path.is_symlink(), f"registered {label} is absent")
    require(sha256(path) == hex64(value["sha256"], label + " hash"),
            f"registered {label} hash differs")
    if bytes_field:
        require(type(value["bytes"]) is int and value["bytes"] > 0
                and path.stat().st_size == value["bytes"],
                f"registered {label} byte count differs")
    return path


def _validate_expected_source_report(value: Any, case_id: str) -> Mapping[str, Any]:
    row = exact_keys(value, {
        "sha256", "bytes", "source_semantic_digest",
        "controller_pair_semantic_digest", "census",
    }, f"{case_id} expected source report")
    hex64(row["sha256"], "source report hash")
    hex64(row["source_semantic_digest"], "source semantic digest")
    hex64(row["controller_pair_semantic_digest"], "controller pair digest")
    require(type(row["bytes"]) is int and row["bytes"] > 0,
            "source report bytes differ")
    census = exact_keys(row["census"], {
        "components", "old_controller_states", "old_controller_edges",
        "new_controller_states", "new_controller_edges",
        "old_safety_machines", "new_safety_machines",
        "transition_requirement_machines", "observers", "activation_rows",
        "activation_error_rows", "progress_actions",
    }, f"{case_id} source census")
    expected_transition = EXPECTED_CASES[case_id]["transition_requirement_machines"]
    require(census == {
        "components": 2,
        "old_controller_states": 81, "old_controller_edges": 216,
        "new_controller_states": 81, "new_controller_edges": 216,
        "old_safety_machines": 12, "new_safety_machines": 12,
        "transition_requirement_machines": expected_transition,
        "observers": 22, "activation_rows": 152,
        "activation_error_rows": 82, "progress_actions": 26,
    }, f"{case_id} source census differs")
    return row


def verify_protocol(protocol: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    exact_keys(protocol, {
        "schema_version", "date", "campaign_id", "denominator",
        "timeouts_seconds", "registered_files", "cases", "claim_boundary",
    }, "protocol")
    require(protocol["schema_version"] == PROTOCOL_SCHEMA
            and protocol["date"] == "2026-08-14"
            and protocol["campaign_id"] == CAMPAIGN_ID,
            "protocol identity differs")
    require(protocol["claim_boundary"] == CLAIM_BOUNDARY,
            "protocol claim boundary differs")
    require(protocol["denominator"] == {
        "source_files": 1, "target_cells": 2, "provenance_clusters": 1,
        "unique_controller_pairs": 1, "supplied_certificates": 2,
    }, "protocol denominator differs")
    require(protocol["timeouts_seconds"] == {
        "source_checker": 30, "downstream_checker": 180,
    }, "protocol timeout differs")
    files = exact_keys(protocol["registered_files"], {
        "source_checker", "source_checker_test", "downstream_checker",
        "downstream_protocol", "campaign_runner", "offline_audit",
        "campaign_test",
    }, "registered files")
    registered = {
        role: registered_path(row, "registered " + role)
        for role, row in files.items()
    }

    downstream_protocol = load(registered["downstream_protocol"])
    require(downstream_protocol.get("schema_version") ==
            "fg-ducs-post-frontend-certificate-protocol-v1"
            and downstream_protocol.get("campaign_id") ==
            "m8s-post-frontend-contract-certificate-20260814a",
            "downstream M8s protocol identity differs")
    downstream_cases = {
        row.get("case_id"): row for row in downstream_protocol.get("cases", [])
        if type(row) is dict and type(row.get("case_id")) is str
    }
    require(set(downstream_cases) == set(EXPECTED_CASES),
            "downstream M8s case census differs")

    cases = protocol["cases"]
    require(type(cases) is list and len(cases) == 2
            and [row.get("case_id") for row in cases if type(row) is dict]
            == sorted(EXPECTED_CASES), "protocol case order/census differs")
    source_bindings: set[tuple[str, str]] = set()
    clusters: set[str] = set()
    for row in cases:
        exact_keys(row, {
            "case_id", "condition", "definition", "cluster", "source",
            "facts", "historical_bundle", "m8s_record", "m8s_report",
            "expected_source_report",
        }, "case")
        case_id = row["case_id"]
        expected = EXPECTED_CASES[case_id]
        require(row["condition"] == expected["condition"]
                and row["definition"] == expected["definition"]
                and row["cluster"] == "productioncell",
                f"case registration differs: {case_id}")
        source = registered_path(row["source"], case_id + " source")
        facts = registered_path(row["facts"], case_id + " facts", bytes_field=True)
        bundle = registered_path(row["historical_bundle"], case_id + " bundle")
        record_path = registered_path(row["m8s_record"], case_id + " M8s record")
        report_path = registered_path(row["m8s_report"], case_id + " M8s report")
        _validate_expected_source_report(row["expected_source_report"], case_id)
        source_bindings.add((row["source"]["path"], row["source"]["sha256"]))
        clusters.add(row["cluster"])

        downstream = downstream_cases[case_id]
        require(downstream["condition"] == row["condition"]
                and downstream["definition"] == row["definition"]
                and downstream["cluster"] == row["cluster"]
                and downstream["source"] == row["source"]
                and downstream["expected_ir"] == {
                    "sha256": row["facts"]["sha256"],
                    "bytes": row["facts"]["bytes"],
                }
                and downstream["historical_bundle"]["path"] ==
                row["historical_bundle"]["path"]
                and downstream["historical_bundle"]["sha256"] ==
                row["historical_bundle"]["sha256"]
                and downstream["expected_report"]["sha256"] ==
                row["m8s_report"]["sha256"],
                f"M8t/M8s protocol cross-link differs: {case_id}")

        m8s_record = load(record_path)
        require(m8s_record.get("schema_version") ==
                "fg-ducs-post-frontend-certificate-record-v1"
                and m8s_record.get("case_id") == case_id
                and m8s_record.get("condition") == row["condition"]
                and m8s_record.get("definition") == row["definition"]
                and m8s_record.get("cluster") == row["cluster"]
                and m8s_record.get("source_sha256") == sha256(source)
                and m8s_record.get("facts_sha256") == sha256(facts)
                and m8s_record.get("historical_bundle_sha256") == sha256(bundle)
                and m8s_record.get("report_sha256") == sha256(report_path)
                and m8s_record.get("status") ==
                "POST_FRONTEND_CONTRACT_TO_CERTIFICATE_SEMANTICS_VERIFIED",
                f"registered M8s record differs: {case_id}")
    require(len(source_bindings) == 1 and len(clusters) == 1,
            "derived denominator differs")
    return list(cases)


def validate_source_report(
    case: Mapping[str, Any], report: Mapping[str, Any], raw: bytes,
) -> None:
    case_id = case["case_id"]
    expected = _validate_expected_source_report(
        case["expected_source_report"], case_id)
    require(set(report) == SOURCE_REPORT_KEYS,
            f"source report key census differs: {case_id}")
    require(sha256_bytes(raw) == expected["sha256"]
            and len(raw) == expected["bytes"],
            f"source report byte binding differs: {case_id}")
    require(report["schema_version"] ==
            "fg-ducs-productioncell-source-contract-bridge-report-v1"
            and report["status"] ==
            "SOURCE_TO_POST_FRONTEND_CONTRACT_SEMANTICS_VERIFIED"
            and report["profile"] == "productioncell-arms2-bounded-source-v1"
            and report["source_name"] == "ProductionCell_Arms=2_FG.lts"
            and report["source_sha256"] == case["source"]["sha256"]
            and report["definition"] == case["definition"]
            and report["ir_sha256"] == case["facts"]["sha256"]
            and report["source_semantic_digest"] ==
            expected["source_semantic_digest"]
            and report["controller_pair_semantic_digest"] ==
            expected["controller_pair_semantic_digest"]
            and report["verified_fields"] == VERIFIED_FIELDS
            and report["census"] == expected["census"],
            f"source report semantic binding differs: {case_id}")
    require(report["bounded_registered_mtsa_lts_frontend_replay"] is True
            and report["independent_old_new_controller_synthesis"] is True
            and report["independent_controller_pair_synthesis_count"] == 1
            and report["source_to_post_frontend_contract_semantic_agreement"]
            is True
            and report["independent_win_synthesis"] is False
            and report["source_to_win_replay"] is False
            and report["certificate_supplied_downstream"] is True,
            f"source report claim boundary differs: {case_id}")
    require(report["claim_boundary"] == {
        "bounded_registered_source_profile": True,
        "general_mtsa_frontend": False,
        "same_author_implementation": True,
        "post_outcome": True,
        "one_source": True,
        "one_provenance_cluster": True,
        "transitive_runtime_frozen": False,
        "held_out": False,
        "third_party": False,
        "production": False,
    }, f"source report nested claim boundary differs: {case_id}")


def validate_downstream_report(
    case: Mapping[str, Any], report: Mapping[str, Any], raw: bytes,
) -> None:
    case_id = case["case_id"]
    require(sha256_bytes(raw) == case["m8s_report"]["sha256"],
            f"downstream report hash differs: {case_id}")
    require(report.get("schema_version") ==
            "fg-ducs-post-frontend-certificate-check-v1"
            and report.get("status") ==
            "POST_FRONTEND_CONTRACT_TO_CERTIFICATE_SEMANTICS_VERIFIED"
            and report.get("definition") == case["definition"]
            and report.get("source_sha256") == case["source"]["sha256"]
            and report.get("post_frontend_contract_ir_to_winning_certificate_semantic_verification")
            is True
            and report.get("global_transport_and_kappa_verified") is True
            and report.get("independent_raw_source_frontend") is False
            and report.get("independent_controller_synthesis") is False
            and report.get("independent_win_synthesis") is False
            and report.get("source_to_win_replay") is False,
            f"downstream report boundary differs: {case_id}")


def validate_chain(
    case: Mapping[str, Any], source_report: Mapping[str, Any],
    downstream_report: Mapping[str, Any],
) -> None:
    require(source_report["source_sha256"] == downstream_report["source_sha256"]
            == case["source"]["sha256"]
            and source_report["definition"] == downstream_report["definition"]
            == case["definition"]
            and source_report["ir_sha256"] == case["facts"]["sha256"],
            f"source/facts/certificate chain differs: {case['case_id']}")


def terminate(process: subprocess.Popen[bytes]) -> tuple[bytes, bytes]:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        return process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        return process.communicate()


def invoke(command: Sequence[str], timeout: int) -> tuple[int, bool, bytes, bytes]:
    process = subprocess.Popen(
        list(command), cwd=ROOT, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        start_new_session=True,
    )
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        stdout, stderr = terminate(process)
    return process.returncode, timed_out, stdout, stderr


def _write(path: Path, raw: bytes) -> None:
    path.write_bytes(raw)


def run_case(
    case: Mapping[str, Any], protocol: Mapping[str, Any], root: Path,
    python: str,
) -> dict[str, Any]:
    case_id = case["case_id"]
    directory = root / "cases" / case_id
    directory.mkdir(parents=True)
    files = protocol["registered_files"]
    source_checker = registered_path(files["source_checker"], "source checker")
    downstream_checker = registered_path(files["downstream_checker"],
                                         "downstream checker")
    source = registered_path(case["source"], case_id + " source")
    facts = registered_path(case["facts"], case_id + " facts", bytes_field=True)
    bundle = registered_path(case["historical_bundle"], case_id + " bundle")
    registered_m8s_report = registered_path(case["m8s_report"],
                                            case_id + " M8s report")

    source_report_path = directory / "source-report.json"
    source_code, source_timeout, source_stdout, source_stderr = invoke([
        python, "-I", "-S", "-B", str(source_checker),
        "--source", str(source), "--definition", case["definition"],
        "--ir", str(facts), "--output", str(source_report_path),
    ], protocol["timeouts_seconds"]["source_checker"])
    _write(directory / "source-checker.stdout.txt", source_stdout)
    _write(directory / "source-checker.stderr.txt", source_stderr)
    require(source_code == 0 and source_timeout is False
            and source_stdout == b"" and source_stderr == b""
            and source_report_path.is_file(),
            f"source checker failed: {case_id}")
    source_raw = source_report_path.read_bytes()
    source_report = load(source_report_path)
    validate_source_report(case, source_report, source_raw)

    downstream_report_path = directory / "downstream-report.json"
    downstream_code, downstream_timeout, downstream_stdout, downstream_stderr = invoke([
        python, "-I", "-S", "-B", str(downstream_checker),
        "--ir", str(facts), "--bundle", str(bundle),
        "--output", str(downstream_report_path),
    ], protocol["timeouts_seconds"]["downstream_checker"])
    _write(directory / "downstream-checker.stdout.txt", downstream_stdout)
    _write(directory / "downstream-checker.stderr.txt", downstream_stderr)
    require(downstream_code == 0 and downstream_timeout is False
            and downstream_stdout == b"" and downstream_stderr == b""
            and downstream_report_path.is_file(),
            f"downstream checker failed: {case_id}")
    downstream_raw = downstream_report_path.read_bytes()
    require(downstream_raw == registered_m8s_report.read_bytes(),
            f"fresh downstream report differs from registered M8s report: {case_id}")
    downstream_report = load(downstream_report_path)
    validate_downstream_report(case, downstream_report, downstream_raw)
    validate_chain(case, source_report, downstream_report)

    record = {
        "schema_version": RECORD_SCHEMA,
        "case_id": case_id, "condition": case["condition"],
        "definition": case["definition"], "cluster": case["cluster"],
        "source_path": case["source"]["path"],
        "source_sha256": case["source"]["sha256"],
        "facts_path": case["facts"]["path"],
        "facts_sha256": case["facts"]["sha256"],
        "historical_bundle_path": case["historical_bundle"]["path"],
        "historical_bundle_sha256": case["historical_bundle"]["sha256"],
        "source_report_path": f"cases/{case_id}/source-report.json",
        "source_report_sha256": sha256_bytes(source_raw),
        "downstream_report_path": f"cases/{case_id}/downstream-report.json",
        "downstream_report_sha256": sha256_bytes(downstream_raw),
        "registered_m8s_report_path": case["m8s_report"]["path"],
        "registered_m8s_report_sha256": case["m8s_report"]["sha256"],
        "source_checker": {
            "exit_code": source_code, "timed_out": source_timeout,
            "stdout_sha256": sha256_bytes(source_stdout),
            "stderr_sha256": sha256_bytes(source_stderr),
        },
        "downstream_checker": {
            "exit_code": downstream_code, "timed_out": downstream_timeout,
            "stdout_sha256": sha256_bytes(downstream_stdout),
            "stderr_sha256": sha256_bytes(downstream_stderr),
        },
        "source_semantic_digest": source_report["source_semantic_digest"],
        "controller_pair_semantic_digest":
            source_report["controller_pair_semantic_digest"],
        "source_to_post_frontend_contract_semantics_verified": True,
        "post_frontend_contract_to_supplied_certificate_semantics_verified": True,
        "source_to_supplied_certificate_semantics_verified": True,
        "independent_win_synthesis": False,
        "source_to_win_replay": False,
        "status": "SOURCE_TO_SUPPLIED_CERTIFICATE_SEMANTICS_VERIFIED",
    }
    _write(directory / "record.json", canonical(record))
    return record


def run(protocol_path: Path, output: Path, python: str) -> dict[str, Any]:
    require(not output.exists(), "output already exists")
    require(output.parent.is_dir(), "output parent is absent")
    protocol = load(protocol_path)
    cases = verify_protocol(protocol)
    require(protocol_path.resolve() != registered_path(
        protocol["registered_files"]["downstream_protocol"],
        "downstream protocol").resolve(),
        "M8t protocol must not alias the M8s protocol")
    scratch = Path(tempfile.mkdtemp(prefix=".m8t-source-certificate-",
                                    dir=output.parent))
    try:
        records = [run_case(case, protocol, scratch, python) for case in cases]
        controller_pairs = {row["controller_pair_semantic_digest"] for row in records}
        source_semantics = {row["source_semantic_digest"] for row in records}
        require(len(controller_pairs) == 1 and len(source_semantics) == 2,
                "aggregate semantic denominator differs")
        summary = {
            "schema_version": SUMMARY_SCHEMA,
            "campaign_id": CAMPAIGN_ID,
            "protocol_sha256": sha256(protocol_path),
            "source_files": 1, "target_cells": 2,
            "provenance_clusters": 1,
            "source_to_post_frontend_contract_semantic_verification": 2,
            "post_frontend_contract_to_supplied_certificate_semantic_verification": 2,
            "source_to_supplied_certificate_semantic_verification": 2,
            "independent_controller_synthesis_executions": 2,
            "unique_independent_controller_pairs": 1,
            "unique_source_semantic_contracts": 2,
            "independent_win_synthesis": 0,
            "source_to_win_replay": 0,
            "records": [f"cases/{row['case_id']}/record.json" for row in records],
            "claim_boundary": CLAIM_BOUNDARY,
            "status": "SOURCE_TO_SUPPLIED_CERTIFICATE_SEMANTICS_VERIFIED",
        }
        _write(scratch / "summary.json", canonical(summary))
        os.rename(scratch, output)
        return summary
    except BaseException:
        shutil.rmtree(scratch, ignore_errors=True)
        raise


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--python", default=sys.executable)
    args = parser.parse_args(argv)
    try:
        run(args.protocol, args.output, args.python)
        return 0
    except (CampaignError, OSError, subprocess.SubprocessError) as error:
        print("SOURCE_CERTIFICATE_CAMPAIGN_INVALID=" + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
