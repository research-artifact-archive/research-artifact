#!/usr/bin/env python3
"""Run every registered ordinary-LTS native-factorization cell.

The runner never filters by outcome.  It records SUCCESS, INVALID,
RESOURCE_TIMEOUT, or ERROR for every frozen cell and invokes the non-importing
bundle consumer for every successful refined-WIN/trivial result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Sequence


ROOT = Path(__file__).resolve().parents[1]
RUNNER = "ltsa.updatingControllers.cli.NativePartitionRunner"


class PanelError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PanelError(f"invalid JSON: {path}") from error
    if not isinstance(value, dict):
        raise PanelError(f"JSON root is not an object: {path}")
    return value


def slug(value: str) -> str:
    result = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not result:
        raise PanelError("empty case slug")
    return result


def expand(protocol: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source in protocol.get("sources", []):
        if not isinstance(source, dict):
            raise PanelError("source entry is not an object")
        cluster = source["cluster"]
        if "instances" in source:
            for instance in source["instances"]:
                path = source["path_prefix"] + instance["file"]
                condition = f"{source['condition']}-{Path(instance['file']).stem}"
                rows.append({
                    "case_id": slug(f"{cluster}-{condition}"),
                    "path": path,
                    "sha256": instance["sha256"],
                    "cluster": cluster,
                    "condition": condition,
                    "definition": source["definition"],
                    "alias": source["alias"],
                    "hypothesis": source["hypothesis"],
                })
        else:
            for target in source["targets"]:
                rows.append({
                    "case_id": slug(f"{cluster}-{target['condition']}-{Path(source['path']).stem}"),
                    "path": source["path"],
                    "sha256": source["sha256"],
                    "cluster": cluster,
                    "condition": target["condition"],
                    "definition": target["definition"],
                    "alias": target["alias"],
                    "hypothesis": target["hypothesis"],
                })
    ids = [row["case_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise PanelError("expanded case IDs are not unique")
    expected = protocol["denominator"]
    if len(rows) != expected["target_cells"]:
        raise PanelError("expanded target-cell denominator differs")
    if len({row["cluster"] for row in rows}) != expected["provenance_clusters"]:
        raise PanelError("expanded cluster denominator differs")
    return rows


def exact_java_hash(protocol: dict[str, Any], jar: Path) -> None:
    expected = protocol["runtime"]["jar_sha256"]
    actual = sha256(jar)
    if actual != expected:
        raise PanelError(f"JAR SHA-256 mismatch: {actual} != {expected}")


def parse_stdout(payload: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in payload.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            if key and key not in result:
                result[key] = value
    return result


def parse_rss(payload: str) -> int | None:
    match = re.search(r"^\s*(\d+)\s+maximum resident set size\s*$", payload, re.MULTILINE)
    return int(match.group(1)) if match else None


def run_case(
    row: dict[str, Any],
    *,
    jar: Path,
    output: Path,
    timeout: int,
    heap: str,
    java: str,
) -> dict[str, Any]:
    source = ROOT / row["path"]
    if not source.is_file() or source.is_symlink():
        raise PanelError(f"registered source is absent: {row['path']}")
    actual_source_hash = sha256(source)
    if actual_source_hash != row["sha256"]:
        raise PanelError(f"source SHA-256 mismatch: {row['case_id']}")

    case_dir = output / "cases" / row["case_id"]
    case_dir.mkdir(parents=True, exist_ok=False)
    bundle = case_dir / "bundle.json"
    command = [
        "/usr/bin/time", "-l", java, f"-Xmx{heap}", "-cp", str(jar), RUNNER,
        "--lts", str(source), "--definition", row["definition"], "--output", str(bundle),
    ]
    started = time.monotonic_ns()
    timed_out = False
    process = subprocess.Popen(
            command,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
    try:
        stdout_bytes, stderr_bytes = process.communicate(timeout=timeout)
        exit_code = process.returncode
        stdout = stdout_bytes.decode("utf-8", "replace")
        stderr = stderr_bytes.decode("utf-8", "replace")
    except subprocess.TimeoutExpired as error:
        timed_out = True
        try:
            os.killpg(process.pid, signal.SIGTERM)
            stdout_bytes, stderr_bytes = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            stdout_bytes, stderr_bytes = process.communicate()
        exit_code = 124
        stdout = stdout_bytes.decode("utf-8", "replace")
        stderr = stderr_bytes.decode("utf-8", "replace")
    wall_nanos = time.monotonic_ns() - started
    (case_dir / "stdout.txt").write_text(stdout, encoding="utf-8")
    (case_dir / "stderr.txt").write_text(stderr, encoding="utf-8")

    terminal = parse_stdout(stdout)
    if timed_out:
        process_status = "RESOURCE_TIMEOUT"
    elif exit_code == 0 and bundle.is_file():
        process_status = "SUCCESS"
    elif exit_code == 2:
        process_status = "INVALID_OR_INCONCLUSIVE"
    else:
        process_status = "ERROR"

    consumer_status = "NOT_RUN"
    consumer_report: dict[str, Any] | None = None
    bundle_hash: str | None = None
    bundle_bytes: int | None = None
    if process_status == "SUCCESS":
        checker = ROOT / "analysis/check_native_refined_bundle.py"
        checked = subprocess.run(
            [sys.executable, "-I", "-S", "-B", str(checker), str(bundle)],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        (case_dir / "consumer.stdout.txt").write_bytes(checked.stdout)
        (case_dir / "consumer.stderr.txt").write_bytes(checked.stderr)
        if checked.returncode == 0:
            consumer_status = "PASS"
            consumer_report = json.loads(checked.stdout.decode("utf-8"))
        else:
            consumer_status = "FAIL"
        bundle_hash = sha256(bundle)
        bundle_bytes = bundle.stat().st_size

    record = dict(row)
    record.update({
        "process_status": process_status,
        "exit_code": exit_code,
        "timed_out": timed_out,
        "wall_nanos": wall_nanos,
        "max_rss_bytes": parse_rss(stderr),
        "factor_status": terminal.get("factor_status"),
        "solve_status": terminal.get("solve_status"),
        "block_count": int(terminal["block_count"]) if terminal.get("block_count", "").isdigit() else None,
        "terminal_product_verified": terminal.get("terminal_product_verified") == "true" if "terminal_product_verified" in terminal else None,
        "producer_elapsed_nanos": int(terminal["elapsed_nanos"]) if terminal.get("elapsed_nanos", "").isdigit() else None,
        "consumer_status": consumer_status,
        "consumer_report": consumer_report,
        "bundle_path": bundle.relative_to(output).as_posix() if bundle.is_file() else None,
        "bundle_sha256": bundle_hash,
        "bundle_bytes": bundle_bytes,
        "stderr_sha256": sha256(case_dir / "stderr.txt"),
        "stdout_sha256": sha256(case_dir / "stdout.txt"),
    })
    (case_dir / "record.json").write_text(
        json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return record


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, default=ROOT / "protocols/native_factorization_panel_v1_20260814.json")
    parser.add_argument("--jar", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--java", default="java")
    args = parser.parse_args(argv)
    protocol = load_json(args.protocol.resolve())
    rows = expand(protocol)
    jar = args.jar.resolve()
    exact_java_hash(protocol, jar)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    timeout = int(protocol["runtime"]["per_case_timeout_seconds"])
    heap = str(protocol["runtime"]["heap"])
    records: list[dict[str, Any]] = []
    for index, row in enumerate(rows, 1):
        print(f"[{index}/{len(rows)}] {row['case_id']}", flush=True)
        records.append(run_case(row, jar=jar, output=output, timeout=timeout, heap=heap, java=args.java))
    status = Counter(record["process_status"] for record in records)
    factors = Counter(record["factor_status"] or "NO_RESULT" for record in records)
    solves = Counter(record["solve_status"] or "NO_RESULT" for record in records)
    consumers = Counter(record["consumer_status"] for record in records)
    summary = {
        "schema_version": "fg-ducs-native-factorization-panel-summary-v1",
        "protocol_sha256": sha256(args.protocol.resolve()),
        "jar_sha256": sha256(jar),
        "source_files": protocol["denominator"]["source_files"],
        "target_cells": len(records),
        "provenance_clusters": len({record["cluster"] for record in records}),
        "process_status_counts": dict(sorted(status.items())),
        "factor_status_counts": dict(sorted(factors.items())),
        "solve_status_counts": dict(sorted(solves.items())),
        "consumer_status_counts": dict(sorted(consumers.items())),
        "records": records,
    }
    write_json(output / "summary.json", summary)
    print(json.dumps({key: summary[key] for key in ("target_cells", "process_status_counts", "factor_status_counts", "solve_status_counts", "consumer_status_counts")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
