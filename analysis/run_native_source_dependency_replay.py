#!/usr/bin/env python3
"""Run the registered 41-cell post-frontend dependency replay campaign."""

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
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from check_native_source_dependencies import ReplayError, canonical, compare, load  # noqa: E402
from run_native_factorization_panel import expand as expand_registration  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
FACTS_RUNNER = "ltsa.lts.NativeSourceDependencyFactsRunner"


class CampaignError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CampaignError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_root_path(value: Any, label: str) -> Path:
    require(type(value) is str and bool(value), f"{label} is not text")
    relative = PurePosixPath(value)
    require(not relative.is_absolute() and ".." not in relative.parts and relative.as_posix() == value, f"unsafe {label}")
    return ROOT / Path(*relative.parts)


def strict_json(path: Path) -> dict[str, Any]:
    return load(path)


def verify_jar_entries(jar: Path, runtime: Mapping[str, Any]) -> None:
    expected = {
        "ltsa/lts/NativeSourceDependencyFactsRunner.class": runtime["facts_runner_class_sha256"],
        "ltsa/lts/NativeUpdatingContractLoader.class": runtime["native_loader_class_sha256"],
    }
    try:
        with zipfile.ZipFile(jar, "r") as archive:
            for name, digest in expected.items():
                require(hashlib.sha256(archive.read(name)).hexdigest() == digest, f"campaign JAR entry hash differs: {name}")
    except (OSError, KeyError, zipfile.BadZipFile) as error:
        raise CampaignError("campaign JAR entry verification failed") from error


def kill_group(process: subprocess.Popen[bytes]) -> tuple[bytes, bytes]:
    try:
        os.killpg(process.pid, signal.SIGTERM)
        return process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        return process.communicate()


def run_cell(
    row: Mapping[str, Any],
    *,
    jar: Path,
    java: str,
    heap: str,
    timeout_seconds: int,
    output: Path,
    original_panel: Path,
) -> dict[str, Any]:
    case_id = str(row["case_id"])
    source = safe_root_path(row["path"], "registered source path")
    require(source.is_file() and not source.is_symlink(), f"registered source is absent: {case_id}")
    require(sha256(source) == row["sha256"], f"registered source hash differs: {case_id}")
    original_case = original_panel / "cases" / case_id
    record_path = original_case / "record.json"
    stderr_path = original_case / "stderr.txt"
    original_record = strict_json(record_path)
    bundle_path = original_case / "bundle.json"
    original_bundle = strict_json(bundle_path) if bundle_path.is_file() else None

    case_dir = output / "cases" / case_id
    case_dir.mkdir(parents=True, exist_ok=False)
    facts_path = case_dir / "facts.json"
    command = [
        java, f"-Xmx{heap}", "-cp", str(jar), FACTS_RUNNER,
        "--lts", str(source), "--definition", str(row["definition"]),
        "--output", str(facts_path),
    ]
    started = time.monotonic_ns()
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        stdout, stderr = kill_group(process)
    wall_nanos = time.monotonic_ns() - started
    (case_dir / "stdout.txt").write_bytes(stdout)
    (case_dir / "stderr.txt").write_bytes(stderr)
    require(not timed_out, f"facts runner timed out: {case_id}")
    require(process.returncode == 0 and facts_path.is_file(), f"facts runner failed: {case_id}/{process.returncode}")

    facts = strict_json(facts_path)
    report = compare(
        facts,
        original_record,
        original_bundle,
        stderr_path.read_text(encoding="utf-8"),
    )
    report_path = case_dir / "report.json"
    report_path.write_bytes(canonical(report))
    result = {
        "case_id": case_id,
        "path": row["path"],
        "source_sha256": row["sha256"],
        "cluster": row["cluster"],
        "condition": row["condition"],
        "definition": row["definition"],
        "facts_exit_code": process.returncode,
        "facts_timed_out": timed_out,
        "wall_nanos": wall_nanos,
        "facts_path": facts_path.relative_to(output).as_posix(),
        "facts_sha256": sha256(facts_path),
        "facts_bytes": facts_path.stat().st_size,
        "report_path": report_path.relative_to(output).as_posix(),
        "report_sha256": sha256(report_path),
        "report_bytes": report_path.stat().st_size,
        "stdout_sha256": sha256(case_dir / "stdout.txt"),
        "stderr_sha256": sha256(case_dir / "stderr.txt"),
        "replay_status": report["status"],
        "dependency_outcome": report["dependency_outcome"],
        "dependency_receipt_agreement": report["dependency_receipt_agreement"],
        "component_partition_agreement": report["component_partition_agreement"],
        "ownerless_gate_agreement": report["ownerless_gate_agreement"],
        "registered_producer_process_status": report["registered_producer_process_status"],
        "registered_producer_factor_status": report["registered_producer_factor_status"],
        "component_partition": report["component_partition"],
        "dependency_receipt_count": report["dependency_receipt_count"],
        "ownerless_obstructions": report["ownerless_obstructions"],
    }
    record = case_dir / "record.json"
    record.write_bytes(canonical(result))
    result["record_path"] = record.relative_to(output).as_posix()
    result["record_sha256"] = sha256(record)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--jar", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--java", default="java")
    args = parser.parse_args(argv)
    try:
        protocol_path = args.protocol.resolve()
        protocol = strict_json(protocol_path)
        require(protocol.get("schema_version") == "fg-ducs-native-source-dependency-replay-protocol-v1", "campaign protocol schema differs")
        registration_relative = protocol.get("registration_protocol")
        require(type(registration_relative) is dict, "registration protocol binding is absent")
        registration_path = safe_root_path(registration_relative.get("path"), "registration protocol path")
        require(registration_path.is_file() and sha256(registration_path) == registration_relative.get("sha256"), "registration protocol binding differs")
        registration = strict_json(registration_path)
        rows = expand_registration(registration)
        denominator = protocol.get("denominator")
        require(denominator == {
            "source_files": 23, "target_cells": 41, "provenance_clusters": 10
        }, "campaign denominator differs")
        registered_denominator = registration.get("denominator")
        require(type(registered_denominator) is dict and all(
            registered_denominator.get(key) == expected
            for key, expected in denominator.items()
        ), "registration denominator differs")
        jar = args.jar.resolve()
        require(jar.is_file() and sha256(jar) == protocol["runtime"]["jar_sha256"], "campaign JAR hash differs")
        verify_jar_entries(jar, protocol["runtime"])
        output = args.output.resolve()
        output.mkdir(parents=True, exist_ok=False)
        original_panel = safe_root_path(protocol["registered_panel_path"], "registered panel path")
        require(original_panel.is_dir(), "registered M8q panel is absent")
        records: list[dict[str, Any]] = []
        for index, row in enumerate(rows, 1):
            print(f"[{index}/41] {row['case_id']}", flush=True)
            records.append(run_cell(
                row,
                jar=jar,
                java=args.java,
                heap=str(protocol["runtime"]["heap"]),
                timeout_seconds=int(protocol["runtime"]["per_case_timeout_seconds"]),
                output=output,
                original_panel=original_panel,
            ))
        outcomes = Counter(record["dependency_outcome"] for record in records)
        receipts = Counter()
        for record in records:
            report = strict_json(output / record["report_path"])
            receipts.update(report["receipt_counts"])
        summary = {
            "schema_version": "fg-ducs-native-source-dependency-replay-summary-v1",
            "protocol_sha256": sha256(protocol_path),
            "registration_protocol_sha256": sha256(registration_path),
            "jar_sha256": sha256(jar),
            "source_files": 23,
            "target_cells": 41,
            "provenance_clusters": 10,
            "facts_extraction_success": 41,
            "compiled_facts_replay_count": 41,
            "compiled_facts_replay_pass": 41,
            "dependency_receipt_agreement_count": sum(record["dependency_receipt_agreement"] for record in records),
            "component_partition_agreement_count": sum(record["component_partition_agreement"] for record in records),
            "ownerless_gate_agreement_count": sum(record["ownerless_gate_agreement"] is True for record in records),
            "shared_mtsa_frontend_count": 41,
            "independent_source_frontend_count": 0,
            "ordinary_lts_source_replay_count": 0,
            "source_to_witness_replay_count": 0,
            "dependency_outcome_counts": dict(sorted(outcomes.items())),
            "receipt_counts": dict(sorted(receipts.items())),
            "records": records,
            "claim_boundary": protocol["claim_boundary"],
        }
        require(outcomes == Counter({
            "ONE_BLOCK": 33,
            "NONTRIVIAL_PARTITION": 2,
            "OWNERLESS_REJECT": 6,
        }), "replayed dependency-outcome census differs")
        (output / "summary.json").write_bytes(canonical(summary))
        require(summary["dependency_receipt_agreement_count"] == 35, "dependency receipt agreement census differs")
        require(summary["component_partition_agreement_count"] == 35, "component partition agreement census differs")
        require(summary["ownerless_gate_agreement_count"] == 6, "ownerless gate agreement census differs")
        print("compiled_facts_replay_pass=41")
        print("ordinary_lts_source_replay_count=0")
        print("source_to_witness_replay_count=0")
        print("terminal_record=COMPLETE")
        return 0
    except (CampaignError, ReplayError, KeyError, OSError, ValueError) as error:
        print("NATIVE_SOURCE_DEPENDENCY_CAMPAIGN_ERROR=" + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
