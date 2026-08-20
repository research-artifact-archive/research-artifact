#!/usr/bin/env python3
"""Offline semantic audit of the registered M8t campaign."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "analysis"
for entry in (SCRIPTS,):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

import check_post_frontend_contract_certificate as DOWNSTREAM  # noqa: E402
import check_productioncell_source_contract_certificate as SOURCE  # noqa: E402
from run_productioncell_source_contract_certificate import (  # noqa: E402
    CAMPAIGN_ID, CLAIM_BOUNDARY, CampaignError, canonical, load, require,
    safe_relative, sha256, sha256_bytes, validate_chain,
    validate_downstream_report, validate_source_report, verify_protocol,
)


AUDIT_SCHEMA = "fg-ducs-productioncell-source-certificate-audit-v1"
SUMMARY_KEYS = {
    "schema_version", "campaign_id", "protocol_sha256", "source_files",
    "target_cells", "provenance_clusters",
    "source_to_post_frontend_contract_semantic_verification",
    "post_frontend_contract_to_supplied_certificate_semantic_verification",
    "source_to_supplied_certificate_semantic_verification",
    "independent_controller_synthesis_executions",
    "unique_independent_controller_pairs", "unique_source_semantic_contracts",
    "independent_win_synthesis", "source_to_win_replay", "records",
    "claim_boundary", "status",
}
RECORD_KEYS = {
    "schema_version", "case_id", "condition", "definition", "cluster",
    "source_path", "source_sha256", "facts_path", "facts_sha256",
    "historical_bundle_path", "historical_bundle_sha256",
    "source_report_path", "source_report_sha256", "downstream_report_path",
    "downstream_report_sha256", "registered_m8s_report_path",
    "registered_m8s_report_sha256", "source_checker", "downstream_checker",
    "source_semantic_digest", "controller_pair_semantic_digest",
    "source_to_post_frontend_contract_semantics_verified",
    "post_frontend_contract_to_supplied_certificate_semantics_verified",
    "source_to_supplied_certificate_semantics_verified",
    "independent_win_synthesis", "source_to_win_replay", "status",
}
RECEIPT_KEYS = {"exit_code", "timed_out", "stdout_sha256", "stderr_sha256"}


def _evidence_path(root: Path, value: Any, label: str) -> Path:
    relative = safe_relative(value, label)
    path = root / Path(*relative.parts)
    require(path.is_file() and not path.is_symlink(), f"{label} is absent")
    return path


def _record_check(
    case: Mapping[str, Any], record: Mapping[str, Any],
    source_report: Mapping[str, Any], source_raw: bytes,
    downstream_raw: bytes, case_root: Path,
) -> None:
    case_id = case["case_id"]
    require(set(record) == RECORD_KEYS,
            f"stored record key census differs: {case_id}")
    require(record.get("schema_version") ==
            "fg-ducs-productioncell-source-certificate-record-v1"
            and record.get("case_id") == case_id
            and record.get("condition") == case["condition"]
            and record.get("definition") == case["definition"]
            and record.get("cluster") == case["cluster"]
            and record.get("source_sha256") == case["source"]["sha256"]
            and record.get("source_path") == case["source"]["path"]
            and record.get("facts_sha256") == case["facts"]["sha256"]
            and record.get("facts_path") == case["facts"]["path"]
            and record.get("historical_bundle_sha256") ==
            case["historical_bundle"]["sha256"]
            and record.get("historical_bundle_path") ==
            case["historical_bundle"]["path"]
            and record.get("source_report_path") ==
            f"cases/{case_id}/source-report.json"
            and record.get("source_report_sha256") == sha256_bytes(source_raw)
            and record.get("downstream_report_path") ==
            f"cases/{case_id}/downstream-report.json"
            and record.get("downstream_report_sha256") ==
            sha256_bytes(downstream_raw)
            and record.get("registered_m8s_report_path") ==
            case["m8s_report"]["path"]
            and record.get("registered_m8s_report_sha256") ==
            case["m8s_report"]["sha256"]
            and record.get("source_semantic_digest") ==
            source_report["source_semantic_digest"]
            and record.get("controller_pair_semantic_digest") ==
            source_report["controller_pair_semantic_digest"]
            and record.get("source_to_post_frontend_contract_semantics_verified")
            is True
            and record.get("post_frontend_contract_to_supplied_certificate_semantics_verified")
            is True
            and record.get("source_to_supplied_certificate_semantics_verified")
            is True
            and record.get("independent_win_synthesis") is False
            and record.get("source_to_win_replay") is False
            and record.get("status") ==
            "SOURCE_TO_SUPPLIED_CERTIFICATE_SEMANTICS_VERIFIED",
            f"stored record differs: {case_id}")
    for field in ("source_checker", "downstream_checker"):
        receipt = record.get(field)
        require(type(receipt) is dict and set(receipt) == RECEIPT_KEYS
                and receipt.get("exit_code") == 0
                and receipt.get("timed_out") is False
                and receipt.get("stdout_sha256") == sha256_bytes(b"")
                and receipt.get("stderr_sha256") == sha256_bytes(b""),
                f"stored worker receipt differs: {case_id}.{field}")
        prefix = "source-checker" if field == "source_checker" else "downstream-checker"
        for stream in ("stdout", "stderr"):
            path = case_root / f"{prefix}.{stream}.txt"
            require(path.is_file() and not path.is_symlink(),
                    f"stored worker log is absent: {case_id}.{field}.{stream}")
            raw = path.read_bytes()
            require(raw == b"" and sha256_bytes(raw) == receipt[f"{stream}_sha256"],
                    f"stored worker log differs: {case_id}.{field}.{stream}")


def verify_evidence_census(evidence: Path, case_ids: Sequence[str]) -> None:
    require(evidence.is_dir() and not evidence.is_symlink(),
            "evidence root is not a real directory")
    expected = {"summary.json"}
    for case_id in case_ids:
        prefix = f"cases/{case_id}/"
        expected.update(prefix + name for name in (
            "source-report.json", "downstream-report.json", "record.json",
            "source-checker.stdout.txt", "source-checker.stderr.txt",
            "downstream-checker.stdout.txt", "downstream-checker.stderr.txt",
        ))
    observed: set[str] = set()
    for path in evidence.rglob("*"):
        require(not path.is_symlink(), "evidence contains a symlink")
        if path.is_file():
            observed.add(path.relative_to(evidence).as_posix())
    require(observed in (expected, expected | {"audit.json"}),
            "evidence file census differs")


def audit(protocol_path: Path, evidence: Path) -> dict[str, Any]:
    protocol = load(protocol_path)
    cases = verify_protocol(protocol)
    verify_evidence_census(evidence, [case["case_id"] for case in cases])
    summary_path = evidence / "summary.json"
    summary = load(summary_path)
    require(set(summary) == SUMMARY_KEYS, "stored summary key census differs")
    require(summary.get("schema_version") ==
            "fg-ducs-productioncell-source-certificate-summary-v1"
            and summary.get("campaign_id") == CAMPAIGN_ID
            and summary.get("protocol_sha256") == sha256(protocol_path)
            and summary.get("claim_boundary") == CLAIM_BOUNDARY
            and summary.get("source_files") == 1
            and summary.get("target_cells") == 2
            and summary.get("provenance_clusters") == 1
            and summary.get("source_to_post_frontend_contract_semantic_verification") == 2
            and summary.get("post_frontend_contract_to_supplied_certificate_semantic_verification") == 2
            and summary.get("source_to_supplied_certificate_semantic_verification") == 2
            and summary.get("independent_controller_synthesis_executions") == 2
            and summary.get("unique_independent_controller_pairs") == 1
            and summary.get("unique_source_semantic_contracts") == 2
            and summary.get("independent_win_synthesis") == 0
            and summary.get("source_to_win_replay") == 0
            and summary.get("status") ==
            "SOURCE_TO_SUPPLIED_CERTIFICATE_SEMANTICS_VERIFIED",
            "stored campaign summary differs")
    expected_record_paths = [f"cases/{case['case_id']}/record.json"
                             for case in cases]
    require(summary.get("records") == expected_record_paths,
            "stored record list differs")

    controller_pairs: set[str] = set()
    source_semantics: set[str] = set()
    transition_machines = 0
    candidate_buckets = 0
    candidate_outcomes = 0
    rank_states = 0
    strategy_buckets = 0
    for case in cases:
        case_id = case["case_id"]
        source_path = ROOT / case["source"]["path"]
        facts_path = ROOT / case["facts"]["path"]
        bundle_path = ROOT / case["historical_bundle"]["path"]
        registered_m8s_report = ROOT / case["m8s_report"]["path"]

        # Preserve the central independence boundary in the audit too: derive
        # the source closure before facts bytes are opened.
        source_bytes = source_path.read_bytes()
        parsed = SOURCE.parse_source(source_bytes)
        derived = SOURCE.derive_source_contract(parsed, case["definition"])
        facts_bytes = facts_path.read_bytes()
        facts = SOURCE.strict_json_bytes(facts_bytes)
        source_report = SOURCE.compare_ir(parsed, derived, facts)
        source_report["ir_sha256"] = sha256_bytes(facts_bytes)
        source_raw = SOURCE.canonical_bytes(source_report)
        stored_source_path = evidence / "cases" / case_id / "source-report.json"
        require(source_raw == stored_source_path.read_bytes(),
                f"fresh source report differs: {case_id}")
        validate_source_report(case, source_report, source_raw)

        downstream_facts = DOWNSTREAM.load(facts_path)
        bundle = DOWNSTREAM.load(bundle_path)
        downstream_report = DOWNSTREAM.verify(downstream_facts, bundle)
        downstream_raw = DOWNSTREAM.canonical_bytes(downstream_report)
        stored_downstream_path = (
            evidence / "cases" / case_id / "downstream-report.json")
        require(downstream_raw == stored_downstream_path.read_bytes()
                == registered_m8s_report.read_bytes(),
                f"fresh downstream report differs: {case_id}")
        validate_downstream_report(case, downstream_report, downstream_raw)
        validate_chain(case, source_report, downstream_report)

        record_path = _evidence_path(evidence,
                                     f"cases/{case_id}/record.json",
                                     case_id + " record")
        record = load(record_path)
        _record_check(case, record, source_report, source_raw, downstream_raw,
                      evidence / "cases" / case_id)
        controller_pairs.add(source_report["controller_pair_semantic_digest"])
        source_semantics.add(source_report["source_semantic_digest"])
        transition_machines += source_report["census"][
            "transition_requirement_machines"]
        candidate_buckets += downstream_report["totals"]["candidate_buckets"]
        candidate_outcomes += downstream_report["totals"]["candidate_outcomes"]
        rank_states += downstream_report["totals"]["rank_states"]
        strategy_buckets += downstream_report["totals"]["strategy_buckets"]

    require(len(controller_pairs) == 1 and len(source_semantics) == 2,
            "fresh aggregate semantic denominator differs")
    return {
        "schema_version": AUDIT_SCHEMA,
        "campaign_id": CAMPAIGN_ID,
        "protocol_sha256": sha256(protocol_path),
        "summary_sha256": sha256(summary_path),
        "source_files": 1, "target_cells": 2, "provenance_clusters": 1,
        "source_to_post_frontend_contract_semantic_verification": 2,
        "post_frontend_contract_to_supplied_certificate_semantic_verification": 2,
        "source_to_supplied_certificate_semantic_verification": 2,
        "independent_controller_synthesis_executions": 2,
        "unique_independent_controller_pairs": 1,
        "unique_source_semantic_contracts": 2,
        "independent_win_synthesis": 0,
        "source_to_win_replay": 0,
        "source_census": {
            "components": 4,
            "old_controller_states": 162, "old_controller_edges": 432,
            "new_controller_states": 162, "new_controller_edges": 432,
            "old_safety_machines": 24, "new_safety_machines": 24,
            "transition_requirement_machines": transition_machines,
            "observers": 44, "activation_rows": 304,
            "activation_error_rows": 164, "progress_actions": 52,
        },
        "supplied_certificate_census": {
            "rank_states": rank_states,
            "candidate_buckets": candidate_buckets,
            "candidate_outcomes": candidate_outcomes,
            "strategy_buckets": strategy_buckets,
            "global_transport_and_kappa_verified": 2,
        },
        "claim_boundary": CLAIM_BOUNDARY,
        "status": "SOURCE_TO_SUPPLIED_CERTIFICATE_SEMANTICS_VERIFIED",
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--expected", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = audit(args.protocol, args.evidence)
        raw = canonical(result)
        if args.expected is not None:
            require(raw == canonical(load(args.expected)),
                    "stored audit differs from fresh audit")
        if args.output is None:
            sys.stdout.buffer.write(raw)
        else:
            args.output.write_bytes(raw)
        return 0
    except (CampaignError, SOURCE.SourceContractError, DOWNSTREAM.CheckError,
            OSError, KeyError, TypeError, ValueError) as error:
        print("SOURCE_CERTIFICATE_AUDIT_INVALID=" + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
