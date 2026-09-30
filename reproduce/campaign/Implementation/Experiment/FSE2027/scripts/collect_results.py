#!/usr/bin/env python3
"""Collect every planned trial, including failures and unexecuted trials."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping

from harness_common import (
    csv_write,
    output_summary,
    parse_evaluation_file,
    read_json,
)


RAW_FIELDS = [
    "job_id",
    "block_id",
    "global_order_index",
    "unit_order_seed",
    "unit_order_index",
    "method_order_seed",
    "method_base_order",
    "method_order",
    "method_order_index",
    "model_id",
    "model_path",
    "model_family",
    "model_factors",
    "model_planned_repetitions",
    "target_id",
    "target_name",
    "method_id",
    "analysis_role",
    "repetition",
    "process_status",
    "completed",
    "exit_code",
    "timed_out",
    "timeout_termination_action",
    "spawn_error",
    "elapsed_monotonic_ns",
    "elapsed_monotonic_seconds",
    "peak_rss_kib",
    "peak_rss_bytes",
    "rss_measurement_kind",
    "rss_measurement_status",
    "rss_samples_attempted",
    "rss_samples_available",
    "evaluation_csv_found",
    "evaluation_csv_rows",
    "evaluation_csv_marker_count",
    "evaluation_csv_errors",
    "evaluation_mode",
    "evaluation_result",
    "solver_status",
    "verification_status",
    "run_verified",
    "evaluation_failure_reason",
    "revised_decision",
    "solver_time_ms",
    "states_discovered",
    "states_expanded",
    "successor_queries",
    "transition_outcomes",
    "initial_endpoint_embeddings",
    "certificate_states",
    "losing_region_states",
    "losing_region_phase_masks",
    "internal_certificate_check",
    "independent_verification_basis",
    "link_checker",
    "output_controller_states",
    "output_controller_transitions",
    "guided_fallback",
    "early_success",
    "duplicate_metric_keys",
    "input_sha256",
    "classpath_sha256",
    "stdout_sha256",
    "stderr_sha256",
    "output_sha256",
    "transitions_sha256",
    "started_utc",
    "finished_utc",
    "timeout_seconds",
    "rss_poll_interval_seconds",
    "command",
    "command_text",
    "transition_output_mode",
    "cwd",
    "meta_path",
    "stdout_path",
    "stderr_path",
    "output_path",
    "transitions_path",
    "config_sha256",
    "plan_sha256",
    "execution_environment_fingerprint_sha256",
]

METRIC_IDENTITY_FIELDS = [
    "job_id",
    "block_id",
    "global_order_index",
    "model_id",
    "model_family",
    "model_factors",
    "model_planned_repetitions",
    "target_id",
    "target_name",
    "method_id",
    "analysis_role",
    "repetition",
    "method_order_index",
    "process_status",
    "completed",
]


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--campaign",
        type=Path,
        required=True,
        help="Campaign directory containing plan.json and runs/.",
    )
    parser.add_argument(
        "--strict-complete",
        action="store_true",
        help="Return nonzero if any planned trial is not terminal.",
    )
    return parser.parse_args()


def blank_row(job: Mapping[str, Any], campaign: Path) -> Dict[str, Any]:
    row: Dict[str, Any] = {field: "" for field in RAW_FIELDS}
    for key in (
        "job_id",
        "block_id",
        "global_order_index",
        "unit_order_seed",
        "unit_order_index",
        "method_order_seed",
        "method_base_order",
        "method_order",
        "method_order_index",
        "model_id",
        "model_path",
        "model_family",
        "model_factors",
        "model_planned_repetitions",
        "target_id",
        "target_name",
        "method_id",
        "analysis_role",
        "repetition",
    ):
        row[key] = job.get(key, "")
    row.update(
        {
            "process_status": "NOT_RUN",
            "completed": False,
            "evaluation_csv_found": False,
            "evaluation_csv_rows": 0,
            "meta_path": str(
                (
                    campaign / "runs" / job["job_id"] / "meta.json"
                ).relative_to(campaign)
            ),
        }
    )
    return row


def artifact_path(campaign: Path, meta: Mapping[str, Any], name: str) -> Path:
    relative = meta.get("artifacts", {}).get(name, "")
    return campaign / relative if relative else Path("")


def collect(campaign: Path) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, int]]:
    plan_path = campaign / "plan.json"
    if not plan_path.is_file():
        raise FileNotFoundError("Missing plan.json in " + str(campaign))
    plan = read_json(plan_path)
    raw_rows: List[Dict[str, Any]] = []
    metric_rows: List[Dict[str, Any]] = []
    counts: Dict[str, int] = {}
    for job in plan["jobs"]:
        row = blank_row(job, campaign)
        meta_path = campaign / row["meta_path"]
        if not meta_path.is_file():
            raw_rows.append(row)
            counts["NOT_RUN"] = counts.get("NOT_RUN", 0) + 1
            continue
        try:
            meta = read_json(meta_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            row["process_status"] = "META_INVALID"
            row["evaluation_csv_errors"] = "%s: %s" % (
                type(exc).__name__,
                exc,
            )
            raw_rows.append(row)
            counts["META_INVALID"] = counts.get("META_INVALID", 0) + 1
            continue
        status = str(meta.get("status", "INCOMPLETE"))
        row.update(
            {
                "process_status": status,
                "completed": meta.get("completed", False),
                "exit_code": meta.get("exit_code", ""),
                "timed_out": meta.get("timed_out", ""),
                "timeout_termination_action": meta.get(
                    "timeout_termination_action", ""
                ),
                "spawn_error": meta.get("spawn_error", ""),
                "elapsed_monotonic_ns": meta.get(
                    "elapsed_monotonic_ns", ""
                ),
                "elapsed_monotonic_seconds": meta.get(
                    "elapsed_monotonic_seconds", ""
                ),
                "peak_rss_kib": meta.get("peak_rss_kib", ""),
                "peak_rss_bytes": meta.get("peak_rss_bytes", ""),
                "rss_measurement_kind": meta.get(
                    "rss_measurement_kind", ""
                ),
                "rss_measurement_status": meta.get(
                    "rss_measurement_status", ""
                ),
                "rss_samples_attempted": meta.get(
                    "rss_samples_attempted", ""
                ),
                "rss_samples_available": meta.get(
                    "rss_samples_available", ""
                ),
                "started_utc": meta.get("started_utc", ""),
                "finished_utc": meta.get("finished_utc", ""),
                "timeout_seconds": meta.get("timeout_seconds", ""),
                "rss_poll_interval_seconds": meta.get(
                    "rss_poll_interval_seconds", ""
                ),
                "command": meta.get("command", []),
                "command_text": meta.get("command_text", ""),
                "transition_output_mode": meta.get(
                    "transition_output_mode", ""
                ),
                "cwd": meta.get("cwd", ""),
                "config_sha256": meta.get("config_sha256", ""),
                "plan_sha256": meta.get("plan_sha256", ""),
                "execution_environment_fingerprint_sha256": meta.get(
                    "execution_environment_fingerprint_sha256", ""
                ),
                "input_sha256": meta.get("input_model", {}).get(
                    "sha256", ""
                ),
                "classpath_sha256": meta.get("classpath", {}).get(
                    "sha256", ""
                ),
            }
        )
        for artifact in ("stdout", "stderr", "output", "transitions"):
            row[artifact + "_path"] = meta.get("artifacts", {}).get(
                artifact, ""
            )
            row[artifact + "_sha256"] = meta.get(
                "artifact_digests", {}
            ).get(artifact, {}).get("sha256", "")
        output_path = artifact_path(campaign, meta, "output")
        parsed = parse_evaluation_file(output_path)
        summary = output_summary(parsed)
        row.update(summary)
        row.update(
            {
                "evaluation_csv_found": parsed["found"],
                "evaluation_csv_rows": len(parsed["rows"]),
                "evaluation_csv_marker_count": parsed["marker_count"],
                "evaluation_csv_errors": parsed["errors"],
            }
        )
        for metric_index, metric in enumerate(parsed["rows"]):
            metric_row: Dict[str, Any] = {
                field: row.get(field, "")
                for field in METRIC_IDENTITY_FIELDS
            }
            metric_row["metric_row_index"] = metric_index
            metric_row.update(metric)
            metric_rows.append(metric_row)
        raw_rows.append(row)
        counts[status] = counts.get(status, 0) + 1
    return raw_rows, metric_rows, counts


def main() -> int:
    args = arguments()
    campaign = args.campaign.resolve()
    raw_rows, metric_rows, counts = collect(campaign)
    raw_path = campaign / "raw_runs.csv"
    metrics_path = campaign / "metrics_long.csv"
    csv_write(raw_path, RAW_FIELDS, raw_rows)
    metric_fields = list(METRIC_IDENTITY_FIELDS) + ["metric_row_index"]
    seen = set(metric_fields)
    for metric in metric_rows:
        for key in metric:
            if key not in seen:
                metric_fields.append(key)
                seen.add(key)
    csv_write(metrics_path, metric_fields, metric_rows)
    summary = {
        "planned_runs": len(raw_rows),
        "metric_rows": len(metric_rows),
        "status_counts": counts,
        "raw_runs_csv": str(raw_path),
        "metrics_long_csv": str(metrics_path),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    incomplete = sum(
        count
        for status, count in counts.items()
        if status in {"NOT_RUN", "INCOMPLETE", "META_INVALID", "RUNNING"}
    )
    return 3 if args.strict_complete and incomplete else 0


if __name__ == "__main__":
    raise SystemExit(main())
