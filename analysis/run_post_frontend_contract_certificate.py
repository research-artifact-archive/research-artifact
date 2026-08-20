#!/usr/bin/env python3
"""Run the two registered M8s post-frontend certificate checks.

This is deliberately a post-outcome, same-author verification campaign.  A
fresh JVM emits conclusion-free facts after the shared MTSA frontend and fixed
controller synthesis.  A separate isolated Python process reconstructs the
fixed endpoints, factorized Post, rank/strategy obligations, quiet terminal
product, and global load transport before checking the historical M8q bundle.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
FACTS_CLASS = "ltsa.lts.NativePostFrontendContractFactsRunner"
PROTOCOL_SCHEMA = "fg-ducs-post-frontend-certificate-protocol-v1"
SUMMARY_SCHEMA = "fg-ducs-post-frontend-certificate-summary-v1"
EXPECTED_CASES = {
    "productioncell-arms2-base-productioncell-arms-2-fg": {
        "condition": "arms2-base", "definition": "UpdCont_OTF_FG",
        "cluster": "productioncell",
    },
    "productioncell-arms2-r2-productioncell-arms-2-fg": {
        "condition": "arms2-r2", "definition": "UpdCont_OTF_FG_R2",
        "cluster": "productioncell",
    },
}
CLAIM_BOUNDARY = {
    "post_outcome_certificate_supplied": True,
    "same_author_independent_python_checker": True,
    "shared_mtsa_frontend": True,
    "fixed_controller_synthesis_shared": True,
    "historical_certificate_generated_before_m8s": True,
    "observation_runtime_reproduces_historical_jar": False,
    "independent_raw_source_frontend": False,
    "independent_controller_synthesis": False,
    "independent_win_synthesis": False,
    "source_to_win_replay": False,
    "held_out_cases": 0,
    "third_party_cases": 0,
    "provenance_clusters": 1,
}


class CampaignError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CampaignError(message)


def exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    require(type(value) is dict and set(value) == expected,
            f"{label} key census differs")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CampaignError("duplicate JSON key: " + key)
        result[key] = value
    return result


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise CampaignError("invalid strict JSON: " + str(path)) from error
    require(type(value) is dict, "JSON root is not an object")
    return value


def canonical(value: Any) -> bytes:
    try:
        return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
    except (TypeError, ValueError) as error:
        raise CampaignError("value is not canonical JSON") from error


def safe_relative(value: Any, label: str) -> PurePosixPath:
    require(type(value) is str and bool(value), f"{label} is not text")
    result = PurePosixPath(value)
    require(not result.is_absolute() and ".." not in result.parts
            and result.as_posix() == value, f"unsafe {label}")
    return result


def registered_path(value: Any, digest: Any, label: str) -> Path:
    path = ROOT / Path(*safe_relative(value, label).parts)
    require(path.is_file() and not path.is_symlink(), f"registered {label} is absent")
    require(type(digest) is str and sha256(path) == digest,
            f"registered {label} hash differs")
    return path


def verify_registered_files(protocol: Mapping[str, Any]) -> None:
    rows = protocol.get("registered_files")
    expected = {
        "facts_runner_source", "facts_runner_test", "inherited_facts_source",
        "native_loader_source", "independent_checker", "campaign_runner",
        "offline_audit", "campaign_test", "historical_panel_protocol",
        "historical_panel_summary",
    }
    require(type(rows) is dict and set(rows) == expected,
            "registered file census differs")
    for role, raw in rows.items():
        require(type(raw) is dict and set(raw) == {"path", "sha256"},
                f"registered file row differs: {role}")
        registered_path(raw["path"], raw["sha256"], role)


def validate_runtime(runtime: Any) -> Mapping[str, Any]:
    value = runtime if type(runtime) is dict else {}
    exact_keys(value, {
        "observation_jar_sha256", "historical_m8q_jar_sha256",
        "facts_runner_class", "class_entries", "heap",
        "facts_timeout_seconds", "checker_timeout_seconds",
        "observation_current_source_only", "historical_runtime_reproduced",
        "transitive_runtime_closure_frozen",
    }, "runtime")
    require(value["facts_runner_class"] == FACTS_CLASS
            and value["observation_current_source_only"] is True
            and value["historical_runtime_reproduced"] is False
            and value["transitive_runtime_closure_frozen"] is False,
            "runtime claim boundary differs")
    for field in ("observation_jar_sha256", "historical_m8q_jar_sha256"):
        digest = value[field]
        require(type(digest) is str and len(digest) == 64
                and all(character in "0123456789abcdef" for character in digest),
                f"runtime {field} is invalid")
    require(type(value["heap"]) is str and value["heap"] == "16g",
            "runtime heap differs")
    for field in ("facts_timeout_seconds", "checker_timeout_seconds"):
        require(type(value[field]) is int and value[field] > 0,
                f"runtime {field} is invalid")
    entries = value["class_entries"]
    require(type(entries) is dict and set(entries) == {
        "ltsa/lts/NativePostFrontendContractFactsRunner.class",
        "ltsa/lts/NativeSourceDependencyFactsRunner.class",
        "ltsa/lts/NativeUpdatingContractLoader.class",
    }, "observation class-entry census differs")
    for name, digest in entries.items():
        require(type(name) is str and type(digest) is str and len(digest) == 64
                and all(character in "0123456789abcdef" for character in digest),
                "observation class-entry binding is invalid")
    return value


def verify_protocol(protocol: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    require(protocol.get("schema_version") == PROTOCOL_SCHEMA,
            "campaign protocol schema differs")
    exact_keys(protocol, {
        "schema_version", "date", "campaign_id", "denominator",
        "registered_files", "runtime", "cases", "claim_boundary",
    }, "protocol")
    require(protocol["date"] == "2026-08-14"
            and protocol["campaign_id"] ==
            "m8s-post-frontend-contract-certificate-20260814a",
            "campaign identity differs")
    require(protocol["claim_boundary"] == CLAIM_BOUNDARY,
            "campaign claim boundary differs")
    verify_registered_files(protocol)
    runtime = validate_runtime(protocol["runtime"])
    cases = protocol.get("cases")
    require(type(cases) is list and len(cases) == 2,
            "registered case denominator differs")
    case_ids = [row.get("case_id") for row in cases if type(row) is dict]
    require(case_ids == sorted(EXPECTED_CASES),
            "registered case identity/order differs")
    sources: set[tuple[str, str]] = set()
    clusters: set[str] = set()
    for row in cases:
        exact_keys(row, {
            "case_id", "condition", "definition", "cluster", "source",
            "historical_bundle", "historical_record", "expected_ir",
            "expected_report",
        }, "registered case")
        expected = EXPECTED_CASES[row["case_id"]]
        for field in ("condition", "definition", "cluster"):
            require(row.get(field) == expected[field],
                    f"registered case field differs: {row['case_id']}.{field}")
        source = row.get("source")
        require(type(source) is dict and set(source) == {"path", "sha256"},
                "registered source row differs")
        bundle = row["historical_bundle"]
        history = row["historical_record"]
        expected_ir = row["expected_ir"]
        expected_report = row["expected_report"]
        require(type(bundle) is dict and set(bundle) == {
            "path", "sha256", "historical_producer_jar_sha256",
        }, "registered historical bundle row differs")
        require(type(history) is dict and set(history) == {"path", "sha256"},
                "registered historical record row differs")
        require(type(expected_ir) is dict
                and set(expected_ir) == {"sha256", "bytes"}
                and type(expected_ir["bytes"]) is int
                and expected_ir["bytes"] > 0,
                "registered expected IR row differs")
        require(type(expected_report) is dict and set(expected_report) == {
            "sha256", "semantic_digest_sha256", "old_endpoint_states",
            "new_endpoint_states", "rank_states", "candidate_buckets",
            "candidate_outcomes", "strategy_buckets", "transport",
        }, "registered expected report row differs")
        for digest in (source["sha256"], bundle["sha256"],
                       bundle["historical_producer_jar_sha256"],
                       history["sha256"], expected_ir["sha256"],
                       expected_report["sha256"],
                       expected_report["semantic_digest_sha256"]):
            require(type(digest) is str and len(digest) == 64
                    and all(character in "0123456789abcdef"
                            for character in digest),
                    "registered case digest is invalid")
        for field in ("old_endpoint_states", "new_endpoint_states",
                      "rank_states", "candidate_buckets",
                      "candidate_outcomes", "strategy_buckets"):
            require(type(expected_report[field]) is int
                    and expected_report[field] > 0,
                    f"registered expected report count differs: {field}")
        transport = expected_report["transport"]
        require(type(transport) is dict and set(transport) == {
            "quiet_terminal_product_tuples", "activation_testers",
            "activation_relation_pairs", "observer_relation_pairs",
            "load_selector_signatures", "load_selector_endpoints",
            "certificate_terminal_tuples", "terminal_observer_fibres",
        }
                and all(type(value) is int and value > 0
                        for value in transport.values()),
                "registered expected transport row differs")
        sources.add((source["path"], source["sha256"]))
        clusters.add(row["cluster"])
    derived_denominator = {
        "source_files": len(sources), "target_cells": len(cases),
        "provenance_clusters": len(clusters),
    }
    require(derived_denominator == protocol["denominator"] == {
        "source_files": 1, "target_cells": 2, "provenance_clusters": 1,
    }, "campaign denominator differs from registered cases")

    files = protocol["registered_files"]
    panel_protocol_path = registered_path(
        files["historical_panel_protocol"]["path"],
        files["historical_panel_protocol"]["sha256"],
        "historical panel protocol")
    panel_summary_path = registered_path(
        files["historical_panel_summary"]["path"],
        files["historical_panel_summary"]["sha256"],
        "historical panel summary")
    panel_protocol = load(panel_protocol_path)
    panel_summary = load(panel_summary_path)
    require(panel_protocol.get("schema_version") ==
            "fg-ducs-native-factorization-panel-v1"
            and panel_protocol.get("runtime", {}).get("jar_sha256") ==
            runtime["historical_m8q_jar_sha256"],
            "historical panel protocol/runtime binding differs")
    exact_keys(panel_summary, {
        "schema_version", "protocol_sha256", "jar_sha256", "source_files",
        "target_cells", "provenance_clusters", "process_status_counts",
        "factor_status_counts", "solve_status_counts", "consumer_status_counts",
        "records",
    }, "historical panel summary")
    require(panel_summary["schema_version"] ==
            "fg-ducs-native-factorization-panel-summary-v1"
            and panel_summary["protocol_sha256"] == sha256(panel_protocol_path)
            and panel_summary["jar_sha256"] ==
            runtime["historical_m8q_jar_sha256"]
            and panel_summary["source_files"] == 23
            and panel_summary["target_cells"] == 41
            and panel_summary["provenance_clusters"] == 10,
            "historical panel summary binding differs")
    summary_records = panel_summary["records"]
    require(type(summary_records) is list and len(summary_records) == 41,
            "historical panel record denominator differs")
    by_case: dict[str, Mapping[str, Any]] = {}
    for record in summary_records:
        require(type(record) is dict and type(record.get("case_id")) is str
                and record["case_id"] not in by_case,
                "historical panel record identity differs")
        by_case[record["case_id"]] = record
    return by_case


def verify_jar(jar: Path, runtime: Mapping[str, Any]) -> None:
    runtime = validate_runtime(runtime)
    require(jar.is_file() and not jar.is_symlink(), "observation JAR is absent")
    require(sha256(jar) == runtime.get("observation_jar_sha256"),
            "observation JAR hash differs")
    entries = runtime["class_entries"]
    try:
        with zipfile.ZipFile(jar, "r") as archive:
            for name, expected in entries.items():
                actual = hashlib.sha256(archive.read(name)).hexdigest()
                require(actual == expected, f"observation class hash differs: {name}")
    except (OSError, KeyError, zipfile.BadZipFile) as error:
        raise CampaignError("observation JAR verification failed") from error


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


def invoke(command: Sequence[str], *, timeout: int) -> tuple[int, bool, int, bytes, bytes]:
    started = time.monotonic_ns()
    process = subprocess.Popen(
        list(command), cwd=ROOT, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, start_new_session=True,
    )
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        stdout, stderr = terminate(process)
    return process.returncode, timed_out, time.monotonic_ns() - started, stdout, stderr


def verify_historical_case(
    row: Mapping[str, Any], protocol: Mapping[str, Any],
    panel_records: Mapping[str, Mapping[str, Any]],
) -> None:
    case_id = row["case_id"]
    source_row = row["source"]
    bundle_row = row["historical_bundle"]
    history_row = row["historical_record"]
    history_path = registered_path(
        history_row["path"], history_row["sha256"], "historical record")
    history = load(history_path)
    require(case_id in panel_records and history == panel_records[case_id],
            f"historical record/summary binding differs: {case_id}")
    expected_bundle_relative = (
        "cases/" + case_id + "/bundle.json"
    )
    expected_bundle_public = (
        "evidence/m8q-native-factorization/panel/" + expected_bundle_relative
    )
    for field, expected in {
        "case_id": case_id, "condition": row["condition"],
        "cluster": row["cluster"], "definition": row["definition"],
        "path": source_row["path"], "sha256": source_row["sha256"],
        "bundle_path": expected_bundle_relative,
        "bundle_sha256": bundle_row["sha256"],
        "process_status": "SUCCESS",
        "factor_status": "NONTRIVIAL_SOURCE_NATIVE",
        "solve_status": "PRODUCER_VERIFIED_REFINED_WIN",
        "consumer_status": "PASS",
    }.items():
        require(history.get(field) == expected,
                f"historical record field differs: {case_id}.{field}")
    require(bundle_row["path"] == expected_bundle_public,
            f"historical bundle path differs: {case_id}")
    require(type(history.get("exit_code")) is int and history["exit_code"] == 0
            and history.get("timed_out") is False
            and history.get("terminal_product_verified") is True
            and type(history.get("block_count")) is int
            and history["block_count"] == 2,
            f"historical record terminal differs: {case_id}")
    report = history.get("consumer_report")
    require(type(report) is dict and set(report) == {
        "assembly_count", "block_count", "factor_status", "local_proofs",
        "rank_states", "relation_pair_count", "selector_count",
        "solve_status", "verification_scope",
    }, f"historical consumer report differs: {case_id}")
    expected_report = row["expected_report"]
    require(report == {
        "assembly_count": 1,
        "block_count": 2,
        "factor_status": "NONTRIVIAL_SOURCE_NATIVE",
        "local_proofs": 2,
        "rank_states": expected_report["rank_states"],
        "relation_pair_count":
            expected_report["transport"]["observer_relation_pairs"],
        "selector_count":
            expected_report["transport"]["load_selector_signatures"],
        "solve_status": "STRUCTURALLY_CHECKED_PRODUCER_WITNESS",
        "verification_scope":
            "serialized_internal_consistency_only_source_replay_required",
    }, f"historical consumer report binding differs: {case_id}")
    require(bundle_row["historical_producer_jar_sha256"] ==
            protocol["runtime"]["historical_m8q_jar_sha256"],
            "historical producer JAR binding differs")


def run_case(
    row: Mapping[str, Any], *, protocol: Mapping[str, Any], jar: Path,
    checker: Path, java: str, python: str, output: Path,
    panel_records: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    expected_keys = {
        "case_id", "condition", "definition", "cluster", "source",
        "historical_bundle", "historical_record", "expected_ir",
        "expected_report",
    }
    require(type(row) is dict and set(row) == expected_keys,
            "registered case row differs")
    case_id = row["case_id"]
    require(type(case_id) is str and bool(case_id), "case ID is invalid")
    source_row = row["source"]
    bundle_row = row["historical_bundle"]
    history_row = row["historical_record"]
    require(type(source_row) is dict and set(source_row) == {"path", "sha256"},
            "source row differs")
    require(type(bundle_row) is dict and set(bundle_row) == {
        "path", "sha256", "historical_producer_jar_sha256"
    }, "historical bundle row differs")
    require(type(history_row) is dict and set(history_row) == {"path", "sha256"},
            "historical record row differs")
    source = registered_path(source_row["path"], source_row["sha256"], "source")
    bundle = registered_path(bundle_row["path"], bundle_row["sha256"],
                             "historical bundle")
    registered_path(history_row["path"], history_row["sha256"],
                    "historical record")
    verify_historical_case(row, protocol, panel_records)

    case_dir = output / "cases" / case_id
    case_dir.mkdir(parents=True, exist_ok=False)
    facts = case_dir / "facts.json"
    repeat = case_dir / "facts-repeat.json"
    java_base = [
        java, "-Xmx" + str(protocol["runtime"]["heap"]), "-cp", str(jar),
        FACTS_CLASS, "--lts", str(source), "--definition", str(row["definition"]),
    ]
    facts_runs: list[dict[str, Any]] = []
    for label, destination in (("facts", facts), ("facts-repeat", repeat)):
        code, timed_out, elapsed, stdout, stderr = invoke(
            java_base + ["--output", str(destination)],
            timeout=int(protocol["runtime"]["facts_timeout_seconds"]),
        )
        (case_dir / (label + ".stdout.txt")).write_bytes(stdout)
        (case_dir / (label + ".stderr.txt")).write_bytes(stderr)
        require(not timed_out and code == 0 and destination.is_file(),
                f"facts extraction failed: {case_id}/{label}/{code}")
        facts_runs.append({
            "exit_code": code, "timed_out": timed_out, "wall_nanos": elapsed,
            "stdout_sha256": sha256(case_dir / (label + ".stdout.txt")),
            "stderr_sha256": sha256(case_dir / (label + ".stderr.txt")),
        })
    require(facts.read_bytes() == repeat.read_bytes(),
            f"fresh-JVM facts are nondeterministic: {case_id}")
    expected_ir = row["expected_ir"]
    require(type(expected_ir) is dict and set(expected_ir) == {"sha256", "bytes"},
            "expected IR row differs")
    require(sha256(facts) == expected_ir["sha256"]
            and facts.stat().st_size == expected_ir["bytes"],
            f"facts identity differs: {case_id}")

    report = case_dir / "report.json"
    code, timed_out, checker_elapsed, stdout, stderr = invoke([
        python, "-I", "-S", "-B", str(checker),
        "--ir", str(facts), "--bundle", str(bundle), "--output", str(report),
    ], timeout=int(protocol["runtime"]["checker_timeout_seconds"]))
    (case_dir / "checker.stdout.txt").write_bytes(stdout)
    (case_dir / "checker.stderr.txt").write_bytes(stderr)
    require(not timed_out and code == 0 and report.is_file(),
            f"independent checker failed: {case_id}/{code}")
    expected_report = row["expected_report"]
    require(type(expected_report) is dict and set(expected_report) == {
        "sha256", "semantic_digest_sha256", "old_endpoint_states",
        "new_endpoint_states", "rank_states", "candidate_buckets",
        "candidate_outcomes", "strategy_buckets", "transport",
    }, "expected report row differs")
    observed = load(report)
    require(sha256(report) == expected_report["sha256"],
            f"report identity differs: {case_id}")
    require(observed.get("semantic_digest_sha256") ==
            expected_report["semantic_digest_sha256"],
            f"semantic digest differs: {case_id}")
    require(observed.get("old_endpoint_states") ==
            expected_report["old_endpoint_states"]
            and observed.get("new_endpoint_states") ==
            expected_report["new_endpoint_states"],
            f"endpoint census differs: {case_id}")
    totals = observed.get("totals")
    require(type(totals) is dict and all(
        totals.get(key) == expected_report[key] for key in (
            "rank_states", "candidate_buckets", "candidate_outcomes",
            "strategy_buckets")
    ), f"certificate census differs: {case_id}")
    require(observed.get("transport") == expected_report["transport"],
            f"transport census differs: {case_id}")
    require(observed.get("status") ==
            "POST_FRONTEND_CONTRACT_TO_CERTIFICATE_SEMANTICS_VERIFIED",
            f"checker status differs: {case_id}")

    record = {
        "schema_version": "fg-ducs-post-frontend-certificate-record-v1",
        "case_id": case_id,
        "condition": row["condition"],
        "definition": row["definition"],
        "cluster": row["cluster"],
        "source_path": source_row["path"],
        "source_sha256": source_row["sha256"],
        "historical_bundle_path": bundle_row["path"],
        "historical_bundle_sha256": bundle_row["sha256"],
        "historical_record_path": history_row["path"],
        "historical_record_sha256": history_row["sha256"],
        "historical_producer_jar_sha256":
            bundle_row["historical_producer_jar_sha256"],
        "observation_jar_sha256": protocol["runtime"]["observation_jar_sha256"],
        "facts_path": facts.relative_to(output).as_posix(),
        "facts_repeat_path": repeat.relative_to(output).as_posix(),
        "facts_sha256": sha256(facts),
        "facts_bytes": facts.stat().st_size,
        "fresh_jvm_byte_determinism": True,
        "facts_runs": facts_runs,
        "report_path": report.relative_to(output).as_posix(),
        "report_sha256": sha256(report),
        "report_bytes": report.stat().st_size,
        "checker_exit_code": code,
        "checker_timed_out": timed_out,
        "checker_wall_nanos": checker_elapsed,
        "checker_stdout_sha256": sha256(case_dir / "checker.stdout.txt"),
        "checker_stderr_sha256": sha256(case_dir / "checker.stderr.txt"),
        "status": observed["status"],
        "semantic_digest_sha256": observed["semantic_digest_sha256"],
        "totals": totals,
        "transport": observed["transport"],
    }
    record_path = case_dir / "record.json"
    record_path.write_bytes(canonical(record))
    return {
        "case_id": case_id,
        "record_path": record_path.relative_to(output).as_posix(),
        "record_sha256": sha256(record_path),
        "report_sha256": sha256(report),
        "semantic_digest_sha256": observed["semantic_digest_sha256"],
        "rank_states": totals["rank_states"],
        "candidate_buckets": totals["candidate_buckets"],
        "candidate_outcomes": totals["candidate_outcomes"],
        "strategy_buckets": totals["strategy_buckets"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--jar", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--java", default="java")
    parser.add_argument("--python", default=sys.executable)
    args = parser.parse_args(argv)
    try:
        protocol_path = args.protocol.resolve()
        protocol = load(protocol_path)
        panel_records = verify_protocol(protocol)
        checker_row = protocol["registered_files"]["independent_checker"]
        checker = registered_path(checker_row["path"], checker_row["sha256"],
                                  "independent checker")
        jar = args.jar.resolve()
        verify_jar(jar, protocol["runtime"])
        cases = protocol["cases"]
        output = args.output.resolve()
        output.mkdir(parents=True, exist_ok=False)
        records = [run_case(
            row, protocol=protocol, jar=jar, checker=checker,
            java=args.java, python=args.python, output=output,
            panel_records=panel_records,
        ) for row in cases]
        summary = {
            "schema_version": SUMMARY_SCHEMA,
            "protocol_sha256": sha256(protocol_path),
            "observation_jar_sha256": sha256(jar),
            "historical_m8q_jar_sha256":
                protocol["runtime"]["historical_m8q_jar_sha256"],
            "source_files": 1,
            "target_cells": 2,
            "provenance_clusters": 1,
            "fresh_jvm_facts_deterministic": 2,
            "post_frontend_contract_ir_to_winning_certificate_semantic_verification": 2,
            "global_transport_and_kappa_verified": 2,
            "independent_raw_source_frontend": 0,
            "independent_controller_synthesis": 0,
            "independent_win_synthesis": 0,
            "source_to_win_replay": 0,
            "rank_states": sum(row["rank_states"] for row in records),
            "candidate_buckets": sum(row["candidate_buckets"] for row in records),
            "candidate_outcomes": sum(row["candidate_outcomes"] for row in records),
            "strategy_buckets": sum(row["strategy_buckets"] for row in records),
            "records": records,
            "claim_boundary": protocol["claim_boundary"],
        }
        require(summary["rank_states"] == 212
                and summary["candidate_buckets"] == 4774
                and summary["candidate_outcomes"] == 2682
                and summary["strategy_buckets"] == 228,
                "aggregate certificate census differs")
        (output / "summary.json").write_bytes(canonical(summary))
        print("post_frontend_contract_certificate_verification=2")
        print("independent_raw_source_frontend=0")
        print("independent_win_synthesis=0")
        print("source_to_win_replay=0")
        print("terminal_record=COMPLETE")
        return 0
    except (CampaignError, OSError, KeyError, TypeError, ValueError) as error:
        print("POST_FRONTEND_CERTIFICATE_CAMPAIGN_INVALID=" + str(error),
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
