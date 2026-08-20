#!/usr/bin/env python3
"""Offline audit for the frozen three-cell generated-WIN panel."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import check_generated_post_frontend_win_certificate as CHECK  # noqa: E402
import run_post_frontend_generated_win_panel as RUN  # noqa: E402


AUDIT_SCHEMA = "fg-ducs-post-frontend-generated-win-panel-audit-v1"
SUMMARY_KEYS = {
    "schema_version", "campaign_id", "protocol_sha256", "source_files",
    "target_cells", "provenance_clusters", "conclusion_free_ir_inputs",
    "historical_outcome_inputs", "supplied_certificate_inputs",
    "facts_executions", "fresh_jvm_facts_deterministic",
    "generation_executions", "automatic_retry_executions",
    "fresh_generation_outputs_deterministic", "generated_win_certificates",
    "verified_generated_win_certificates", "status_counts",
    "nontrivial_factorization_cells", "whole_system_block_cells",
    "verified_totals", "verified_transport_totals", "records",
    "claim_boundary", "status",
}
RECORD_KEYS = {
    "schema_version", "case_id", "condition", "cluster", "definition",
    "source", "ir", "facts_runs", "generator_runs", "generation_status",
    "generation_reason", "generation_outputs_byte_identical",
    "generation_seal_path", "generation_seal_sha256",
    "seal_written_before_checker", "checker", "checker_report_path",
    "checker_report_sha256", "status", "reason", "loss_claimed",
    "historical_outcome_inputs", "supplied_certificate_inputs",
    "semantic_digest_sha256", "component_partition", "whole_system_block",
    "nontrivial_factorization", "totals", "transport",
}
RUN_RECEIPT_KEYS = {
    "exit_code", "timed_out", "wall_nanos", "stdout_sha256",
    "stderr_sha256", "output_sha256", "output_bytes",
}
CHECKER_RECEIPT_KEYS = {
    "started", "exit_code", "timed_out", "wall_nanos", "stdout_sha256",
    "stderr_sha256", "output_sha256", "output_bytes",
}
EXPECTED_INPUT_CENSUS = {
    "productioncell-arms2-base-productioncell-arms-2-fg": {
        "components": 2, "partition": [[0], [1]], "blocks": 2,
        "old_endpoints": 126, "new_endpoints": 137,
        "local_roots": [12, 12], "full_goals": [12, 12],
        "quiet_goals": [4, 4], "requirement_machines": 24,
        "observer_machines": 22, "activation_testers": 12,
        "activation_relation_pairs": 218, "observer_relation_pairs": 1010,
        "load_selector_signatures": 137, "load_selector_endpoints": 137,
        "quiet_terminal_product_tuples": 16,
    },
    "productioncell-arms2-r2-productioncell-arms-2-fg": {
        "components": 2, "partition": [[0], [1]], "blocks": 2,
        "old_endpoints": 126, "new_endpoints": 137,
        "local_roots": [12, 12], "full_goals": [12, 12],
        "quiet_goals": [4, 4], "requirement_machines": 48,
        "observer_machines": 22, "activation_testers": 12,
        "activation_relation_pairs": 218, "observer_relation_pairs": 1010,
        "load_selector_signatures": 137, "load_selector_endpoints": 137,
        "quiet_terminal_product_tuples": 16,
    },
    "industry-base-industry-fg": {
        "components": 3, "partition": [[0, 1, 2]], "blocks": 1,
        "old_endpoints": 131, "new_endpoints": 81,
        "local_roots": [131], "full_goals": [81], "quiet_goals": [10],
        "requirement_machines": 6, "observer_machines": 6,
        "activation_testers": 3, "activation_relation_pairs": 48,
        "observer_relation_pairs": 32, "load_selector_signatures": 81,
        "load_selector_endpoints": 81,
        "quiet_terminal_product_tuples": 10,
    },
}


class AuditError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def evidence_path(root: Path, value: Any, label: str) -> Path:
    relative = RUN.safe_relative(value, label)
    path = root / Path(*relative.parts)
    require(path.is_file() and not path.is_symlink(), f"{label} is absent")
    return path


def expected_payload_paths(case_ids: Sequence[str]) -> set[str]:
    result = {"summary.json"}
    for case_id in case_ids:
        result.update(f"cases/{case_id}/{name}" for name in RUN.CASE_FILES)
    return result


def verify_evidence_census(evidence: Path, case_ids: Sequence[str],
                           *, prepublish: bool) -> None:
    require(evidence.is_dir() and not evidence.is_symlink(),
            "evidence root is not a real directory")
    expected = expected_payload_paths(case_ids)
    if not prepublish:
        expected.update({"audit.json", "SHA256SUMS"})
    observed: set[str] = set()
    observed_directories: set[str] = set()
    for path in evidence.rglob("*"):
        require(not path.is_symlink(), "evidence contains a symlink")
        if path.is_file():
            observed.add(path.relative_to(evidence).as_posix())
        elif path.is_dir():
            observed_directories.add(path.relative_to(evidence).as_posix())
    require(observed == expected, "evidence file census differs")
    require(observed_directories == ({"cases"} | {
        f"cases/{case_id}" for case_id in case_ids
    }), "evidence directory census differs")


def verify_sha256sums(evidence: Path) -> None:
    manifest = evidence / "SHA256SUMS"
    try:
        text = manifest.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise AuditError("invalid SHA256SUMS") from error
    expected = []
    for path in sorted(evidence.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS":
            expected.append(
                f"{RUN.sha256(path)}  {path.relative_to(evidence).as_posix()}\n")
    require(text == "".join(expected), "SHA256SUMS differs from evidence")


def _derive_input_census(ir: Mapping[str, Any]) -> dict[str, Any]:
    sem = CHECK.SEM
    contract = sem.parse_contract(ir)
    globals_ = sem.global_components(contract)
    old = sem.build_endpoint(contract, globals_, contract.old_testers, "OLD")
    new = sem.build_endpoint(contract, globals_, contract.new_testers, "NEW")
    partition, normal_owners, update_owners = sem.dependency_partition(contract)
    problems = [sem.build_block_problem(
        contract, block, old, new, normal_owners, update_owners)
        for block in partition]
    activation_testers, activation_pairs = sem.verify_activation_quotients(
        contract, problems, old)
    observer_pairs = 0
    for problem in problems:
        indices = tuple(observer.index for observer in problem.observers)
        global_observers = [contract.observers[index] for index in indices]
        seeds = {
            tuple(endpoint.locals[0].observers[index] for index in indices)
            for endpoint in old
        }
        observer_pairs += len(sem.observer_pair_closure(
            global_observers, problem.observers, seeds, contract.normal))
    loadable = sem.loadable_endpoints(contract, new)
    selector_signatures = len({sem.endpoint_projection(endpoint)
                               for endpoint in loadable})
    quiet_product = sem.verify_quiet_terminal_product(problems, loadable)
    return {
        "components": len(contract.components),
        "partition": partition,
        "blocks": len(partition),
        "old_endpoints": len(old),
        "new_endpoints": len(new),
        "local_roots": [len(problem.roots) for problem in problems],
        "full_goals": [len(problem.full_goals) for problem in problems],
        "quiet_goals": [len(problem.quiet_goals) for problem in problems],
        "requirement_machines": (len(contract.old_testers)
                                 + len(contract.new_testers)
                                 + len(contract.update_testers)),
        "observer_machines": len(contract.observers),
        "activation_testers": activation_testers,
        "activation_relation_pairs": activation_pairs,
        "observer_relation_pairs": observer_pairs,
        "load_selector_signatures": selector_signatures,
        "load_selector_endpoints": len(loadable),
        "quiet_terminal_product_tuples": quiet_product,
    }


def _verify_run_receipt(receipt: Any, output: bytes, stdout: bytes,
                        stderr: bytes, label: str) -> None:
    RUN.exact_keys(receipt, RUN_RECEIPT_KEYS, label)
    RUN.exact_int(receipt["exit_code"], label + " exit", -255)
    require(type(receipt["timed_out"]) is bool, label + " timeout is not Boolean")
    RUN.exact_int(receipt["wall_nanos"], label + " wall", 1)
    require(receipt["stdout_sha256"] == RUN.sha256_bytes(stdout)
            and receipt["stderr_sha256"] == RUN.sha256_bytes(stderr)
            and receipt["output_sha256"] == RUN.sha256_bytes(output)
            and receipt["output_bytes"] == len(output),
            label + " receipt binding differs")


def _invocation_from_receipt(receipt: Mapping[str, Any], *,
                             stderr: bytes = b"") -> RUN.Invocation:
    return RUN.Invocation(receipt["exit_code"], receipt["timed_out"],
                          receipt["wall_nanos"], b"", stderr)


def _verify_record_common(case: Mapping[str, Any], record: Mapping[str, Any],
                          ir_raw: bytes) -> None:
    RUN.exact_keys(record, RECORD_KEYS, "case record")
    require(record["schema_version"] == RUN.RECORD_SCHEMA
            and record["case_id"] == case["case_id"]
            and record["condition"] == case["condition"]
            and record["cluster"] == case["cluster"]
            and record["definition"] == case["definition"]
            and record["source"] == case["source"]
            and record["loss_claimed"] is False
            and record["historical_outcome_inputs"] == 0
            and record["supplied_certificate_inputs"] == 0
            and record["status"] in RUN.FAILURE_TAXONOMY,
            f"record boundary differs: {case['case_id']}")
    require(record["ir"] == {
        "path": f"cases/{case['case_id']}/facts.json",
        "repeat_path": f"cases/{case['case_id']}/facts-repeat.json",
        "sha256": RUN.sha256_bytes(ir_raw), "bytes": len(ir_raw),
        "fresh_jvm_byte_determinism": True,
    }, f"record IR binding differs: {case['case_id']}")


def verify_case(case: Mapping[str, Any], protocol_path: Path,
                protocol: Mapping[str, Any], evidence: Path) -> tuple[
                    dict[str, Any], dict[str, Any], dict[str, Any]]:
    case_id = case["case_id"]
    case_root = evidence / "cases" / case_id
    require(case_root.is_dir() and not case_root.is_symlink(),
            f"case directory is absent: {case_id}")
    require({path.name for path in case_root.iterdir() if path.is_file()}
            == RUN.CASE_FILES, f"case file census differs: {case_id}")

    source = RUN.ROOT / case["source"]["path"]
    require(source.is_file() and not source.is_symlink()
            and RUN.sha256(source) == case["source"]["sha256"],
            f"registered source differs: {case_id}")
    facts = (case_root / "facts.json").read_bytes()
    repeat = (case_root / "facts-repeat.json").read_bytes()
    require(facts == repeat, f"fresh IR repetition differs: {case_id}")
    ir = RUN.validate_ir(facts, case)
    input_census = _derive_input_census(ir)
    require(input_census == EXPECTED_INPUT_CENSUS[case_id],
            f"input-derived semantic census differs: {case_id}")

    record_path = case_root / "record.json"
    record = RUN.load(record_path)
    _verify_record_common(case, record, facts)
    facts_runs = record["facts_runs"]
    require(type(facts_runs) is list and len(facts_runs) == 2,
            f"facts receipt census differs: {case_id}")
    for index, prefix in enumerate(("facts", "facts-repeat")):
        stdout = (case_root / f"{prefix}.stdout.txt").read_bytes()
        stderr = (case_root / f"{prefix}.stderr.txt").read_bytes()
        _verify_run_receipt(
            facts_runs[index], facts, stdout, stderr,
            f"{case_id}/{prefix}")
        expected_stdout, expected_stderr = RUN.expected_facts_streams(case)
        require(facts_runs[index]["exit_code"] == 0
                and facts_runs[index]["timed_out"] is False
                and stdout == expected_stdout and stderr == expected_stderr,
                f"facts run was not successful: {case_id}/{prefix}")

    generated = (case_root / "generated-output.json").read_bytes()
    generated_repeat = (case_root / "generated-output-repeat.json").read_bytes()
    generator_runs = record["generator_runs"]
    require(type(generator_runs) is list and len(generator_runs) == 2,
            f"generator receipt census differs: {case_id}")
    for index, (prefix, raw) in enumerate((
        ("generator", generated), ("generator-repeat", generated_repeat))):
        _verify_run_receipt(
            generator_runs[index], raw,
            (case_root / f"{prefix}.stdout.txt").read_bytes(),
            (case_root / f"{prefix}.stderr.txt").read_bytes(),
            f"{case_id}/{prefix}")
    generation_status, generation_reason, _value = RUN.classify_generation(
        [_invocation_from_receipt(
            row, stderr=(case_root / f"{prefix}.stderr.txt").read_bytes())
         for row, prefix in zip(generator_runs,
                                ("generator", "generator-repeat"))],
        [generated, generated_repeat])
    if _value is not None:
        RUN.validate_generation_document(_value, case, facts)
    require(record["generation_status"] == generation_status
            and record["generation_reason"] == generation_reason
            and record["generation_outputs_byte_identical"] ==
            (bool(generated) and generated == generated_repeat),
            f"generation classification differs: {case_id}")

    seal_path = case_root / "generation-seal.json"
    seal_raw = seal_path.read_bytes()
    seal = RUN.load_bytes(seal_raw, case_id + " seal", canonical_required=True)
    assert seal is not None
    expected_seal = RUN.build_generation_seal(
        case, protocol_path, protocol, facts, [generated, generated_repeat],
        [_invocation_from_receipt(row) for row in generator_runs],
        generation_status, generation_reason)
    require(seal == expected_seal
            and record["generation_seal_path"] ==
            f"cases/{case_id}/generation-seal.json"
            and record["generation_seal_sha256"] == RUN.sha256_bytes(seal_raw)
            and record["seal_written_before_checker"] is True
            and seal["checker_started"] is False
            and seal["phase_order"][-1] == "generation-seal",
            f"generation seal/order binding differs: {case_id}")

    checker_raw = (case_root / "checker-report.json").read_bytes()
    checker_stdout = (case_root / "checker.stdout.txt").read_bytes()
    checker_stderr = (case_root / "checker.stderr.txt").read_bytes()
    checker_receipt = record["checker"]
    RUN.exact_keys(checker_receipt, CHECKER_RECEIPT_KEYS, "checker receipt")
    require(type(checker_receipt["started"]) is bool
            and type(checker_receipt["timed_out"]) is bool,
            f"checker receipt flags differ: {case_id}")
    if checker_receipt["started"]:
        require(type(checker_receipt["exit_code"]) is int
                and type(checker_receipt["wall_nanos"]) is int
                and checker_receipt["wall_nanos"] > 0,
                f"started checker terminal differs: {case_id}")
        checker_invocation: RUN.Invocation | None = RUN.Invocation(
            checker_receipt["exit_code"], checker_receipt["timed_out"],
            checker_receipt["wall_nanos"], checker_stdout, checker_stderr)
    else:
        require(checker_receipt["exit_code"] is None
                and checker_receipt["timed_out"] is False
                and checker_receipt["wall_nanos"] == 0,
                f"not-run checker terminal differs: {case_id}")
        checker_invocation = None
    require(checker_receipt["stdout_sha256"] == RUN.sha256_bytes(checker_stdout)
            and checker_receipt["stderr_sha256"] == RUN.sha256_bytes(checker_stderr)
            and checker_receipt["output_sha256"] == RUN.sha256_bytes(checker_raw)
            and checker_receipt["output_bytes"] == len(checker_raw)
            and record["checker_report_path"] ==
            f"cases/{case_id}/checker-report.json"
            and record["checker_report_sha256"] == RUN.sha256_bytes(checker_raw),
            f"checker receipt binding differs: {case_id}")

    parsed_checker: dict[str, Any] | None = None
    if checker_raw:
        try:
            parsed_checker = RUN.load_bytes(
                checker_raw, case_id + " checker output",
                canonical_required=True)
        except RUN.CampaignError:
            parsed_checker = None
    require(generation_status != "SUCCESS_WIN" or checker_invocation is not None,
            f"successful generation omitted checker execution: {case_id}")
    expected_status, expected_reason = RUN._final_status(
        generation_status, generation_reason, parsed_checker,
        checker_invocation)
    require(record["status"] == expected_status
            and record["reason"] == expected_reason,
            f"final case classification differs: {case_id}")

    report: dict[str, Any] = {}
    if record["status"] == "SUCCESS_WIN":
        require(generation_status == "SUCCESS_WIN"
                and checker_receipt["started"] is True
                and checker_receipt["exit_code"] == 0
                and checker_receipt["timed_out"] is False,
                f"successful checker terminal differs: {case_id}")
        report = CHECK.verify(ir, RUN.load_bytes(
            generated, case_id + " generated certificate",
            canonical_required=True), facts)
        fresh_raw = CHECK.SEM.canonical_bytes(report)
        require(fresh_raw == checker_raw,
                f"fresh checker report differs: {case_id}")
        RUN.validate_check_report(report, case, facts)
        require(record["semantic_digest_sha256"] ==
                report["semantic_digest_sha256"]
                and report["global_old_root_projection_checks"] ==
                input_census["old_endpoints"]
                and record["component_partition"] == report["component_partition"]
                and record["whole_system_block"] == report["whole_system_block"]
                and record["nontrivial_factorization"] ==
                report["nontrivial_factorization"]
                and record["totals"] == report["totals"]
                and record["transport"] == report["transport"],
                f"record semantic result differs: {case_id}")
    elif generation_status != "SUCCESS_WIN":
        not_run = RUN._checker_not_run(generation_status, generation_reason)
        require(checker_raw == RUN.canonical(not_run)
                and checker_receipt["started"] is False
                and checker_receipt["exit_code"] is None
                and checker_receipt["timed_out"] is False
                and checker_receipt["wall_nanos"] == 0
                and checker_stdout == checker_stderr == b""
                and record["semantic_digest_sha256"] is None
                and record["component_partition"] is None
                and record["totals"] is None and record["transport"] is None,
                f"non-success checker boundary differs: {case_id}")
    else:
        require(checker_receipt["started"] is True,
                f"post-generation checker was not started: {case_id}")
    return record, input_census, report


def _aggregate_input(censuses: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "ir_bytes": 850438,
        "components": sum(row["components"] for row in censuses),
        "blocks": sum(row["blocks"] for row in censuses),
        "old_endpoints": sum(row["old_endpoints"] for row in censuses),
        "new_endpoints": sum(row["new_endpoints"] for row in censuses),
        "global_old_endpoint_roots": sum(row["old_endpoints"] for row in censuses),
        "global_root_block_projection_obligations": sum(
            row["old_endpoints"] * row["blocks"] for row in censuses),
        "distinct_local_roots": sum(sum(row["local_roots"]) for row in censuses),
        "full_goals": sum(sum(row["full_goals"]) for row in censuses),
        "quiet_goals": sum(sum(row["quiet_goals"]) for row in censuses),
        "requirement_machines": sum(row["requirement_machines"] for row in censuses),
        "observer_machines": sum(row["observer_machines"] for row in censuses),
        "activation_testers": sum(row["activation_testers"] for row in censuses),
        "activation_relation_pairs": sum(
            row["activation_relation_pairs"] for row in censuses),
        "observer_relation_pairs": sum(
            row["observer_relation_pairs"] for row in censuses),
        "load_selector_signatures": sum(
            row["load_selector_signatures"] for row in censuses),
        "load_selector_endpoints": sum(
            row["load_selector_endpoints"] for row in censuses),
        "quiet_terminal_product_tuples": sum(
            row["quiet_terminal_product_tuples"] for row in censuses),
    }


def audit(protocol_path: Path, evidence: Path, *, prepublish: bool = False) -> dict[str, Any]:
    protocol = RUN.load(protocol_path)
    cases = RUN.verify_protocol(protocol)
    verify_evidence_census(evidence, [row["case_id"] for row in cases],
                           prepublish=prepublish)
    if not prepublish:
        verify_sha256sums(evidence)

    summary_path = evidence / "summary.json"
    summary = RUN.load(summary_path)
    RUN.exact_keys(summary, SUMMARY_KEYS, "summary")
    records: list[dict[str, Any]] = []
    input_censuses: list[dict[str, Any]] = []
    reports: list[dict[str, Any]] = []
    for case in cases:
        record, input_census, report = verify_case(
            case, protocol_path, protocol, evidence)
        records.append(record)
        input_censuses.append(input_census)
        reports.append(report)
    expected_summary = RUN.build_summary(protocol_path, records)
    RUN._fill_record_hashes(expected_summary, evidence)
    require(summary == expected_summary, "stored summary differs from evidence")

    input_totals = _aggregate_input(input_censuses)
    require(input_totals == {
        "ir_bytes": 850438, "components": 7, "blocks": 5,
        "old_endpoints": 383, "new_endpoints": 355,
        "global_old_endpoint_roots": 383,
        "global_root_block_projection_obligations": 635,
        "distinct_local_roots": 179, "full_goals": 129,
        "quiet_goals": 26, "requirement_machines": 78,
        "observer_machines": 50, "activation_testers": 27,
        "activation_relation_pairs": 484, "observer_relation_pairs": 2052,
        "load_selector_signatures": 355, "load_selector_endpoints": 355,
        "quiet_terminal_product_tuples": 42,
    }, "aggregate input-derived census differs")
    return {
        "schema_version": AUDIT_SCHEMA,
        "campaign_id": RUN.CAMPAIGN_ID,
        "status": "PASS",
        "protocol_sha256": RUN.sha256(protocol_path),
        "summary_sha256": RUN.sha256(summary_path),
        "expected_final_evidence_files": 54,
        "expected_checksum_entries": 53,
        "target_cells": 3,
        "source_files": 2,
        "provenance_clusters": 2,
        "historical_outcome_inputs": 0,
        "supplied_certificate_inputs": 0,
        "input_census": input_totals,
        "status_counts": summary["status_counts"],
        "verified_generated_win_certificates":
            summary["verified_generated_win_certificates"],
        "verified_totals": summary["verified_totals"],
        "verified_transport_totals": summary["verified_transport_totals"],
        "industry_whole_system_block": (
            records[2]["whole_system_block"] is True
            if records[2]["status"] == "SUCCESS_WIN" else None),
        "industry_nontrivial_factorization": (
            records[2]["nontrivial_factorization"]
            if records[2]["status"] == "SUCCESS_WIN" else None),
        "import_firewall_verified": True,
        "generation_seals_precede_checker": True,
        "claim_boundary": RUN.CLAIM_BOUNDARY,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=RUN.DEFAULT_PROTOCOL)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--expected", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--prepublish", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = audit(args.protocol, args.evidence,
                       prepublish=args.prepublish)
        raw = RUN.canonical(result)
        if args.expected is not None:
            require(raw == RUN.canonical(RUN.load(args.expected)),
                    "stored audit differs from fresh audit")
        if args.output is None:
            sys.stdout.buffer.write(raw)
        else:
            args.output.write_bytes(raw)
        return 0
    except (AuditError, RUN.CampaignError, CHECK.CheckError, OSError,
            KeyError, TypeError, ValueError) as error:
        print("POST_FRONTEND_GENERATED_WIN_PANEL_AUDIT_INVALID=" + str(error),
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
