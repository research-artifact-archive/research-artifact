#!/usr/bin/env python3
"""Run one isolated JVM per planned FSE 2027 experiment trial."""

from __future__ import annotations

import argparse
import datetime as dt
import errno
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

from harness_common import (
    ORDER_ALGORITHM,
    atomic_write_json,
    build_command,
    build_plan,
    command_text,
    execution_environment_fingerprint,
    environment_manifest,
    file_digest,
    load_config,
    parse_evaluation_file,
    process_group_popen_kwargs,
    process_memory_probe_kind,
    process_rss_kib,
    read_json,
    repository_root,
    require_unsealed_output_path,
    resolve_path,
    sha256_bytes,
    status_from_exit,
    terminate_process_tree,
    validate_inputs,
)


def arguments() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    default_config = script_dir.parent / "configs" / "publication.json"
    parser = argparse.ArgumentParser(
        description=(
            "Execute the deterministic FSE2027 plan. Each trial uses a fresh JVM; "
            "terminal failures remain part of the dataset."
        )
    )
    parser.add_argument("--config", type=Path, default=default_config)
    parser.add_argument(
        "--run-id",
        help="Campaign directory name. Required for execution; reuse it to resume.",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--list", action="store_true", dest="list_plan")
    parser.add_argument("--method", action="append", default=[])
    parser.add_argument("--model", action="append", default=[])
    parser.add_argument("--target", action="append", default=[])
    parser.add_argument("--repetition", action="append", type=int, default=[])
    parser.add_argument(
        "--max-runs",
        type=int,
        help="Execute/print at most N selected jobs (pilot/debug only).",
    )
    return parser.parse_args()


def selected_jobs(plan: Mapping[str, Any], args: argparse.Namespace) -> List[Dict[str, Any]]:
    jobs = [
        job
        for job in plan["jobs"]
        if (not args.method or job["method_id"] in args.method)
        and (not args.model or job["model_id"] in args.model)
        and (not args.target or job["target_id"] in args.target)
        and (
            not args.repetition
            or int(job["repetition"]) in set(args.repetition)
        )
    ]
    if args.max_runs is not None:
        if args.max_runs < 0:
            raise ValueError("--max-runs cannot be negative")
        jobs = jobs[: args.max_runs]
    return jobs


def validate_run_id(value: str) -> str:
    candidate = Path(value)
    if (
        not value
        or candidate.is_absolute()
        or len(candidate.parts) != 1
        or candidate.name != value
        or value in {".", ".."}
    ):
        raise ValueError("--run-id must be one nonempty directory name")
    return value


def current_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def clear_trial_artifacts(paths: Iterable[Path]) -> None:
    for path in paths:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def run_job(
    config: Mapping[str, Any],
    config_sha256: str,
    plan_sha256: str,
    root: Path,
    campaign_dir: Path,
    job: Mapping[str, Any],
    environment_fingerprint_sha256: str,
) -> Dict[str, Any]:
    trial_dir = campaign_dir / "runs" / job["job_id"]
    trial_dir.mkdir(parents=True, exist_ok=True)
    meta_path = trial_dir / "meta.json"
    stdout_path = trial_dir / "stdout.txt"
    stderr_path = trial_dir / "stderr.txt"
    output_path = trial_dir / "output.txt"
    transitions_path = trial_dir / "transitions.txt"
    clear_trial_artifacts(
        [stdout_path, stderr_path, output_path, transitions_path]
    )
    command = build_command(
        config, job, root, output_path, transitions_path
    )
    started_utc = current_utc()
    base_meta: Dict[str, Any] = {
        "meta_schema_version": 1,
        "completed": False,
        "status": "RUNNING",
        "started_utc": started_utc,
        "experiment_id": config["experiment_id"],
        "config_sha256": config_sha256,
        "plan_sha256": plan_sha256,
        "execution_environment_fingerprint_sha256": (
            environment_fingerprint_sha256
        ),
        "order_algorithm": ORDER_ALGORITHM,
        "job": dict(job),
        "command": command,
        "command_text": command_text(command),
        "transition_output_mode": str(config["transition_output_mode"]),
        "cwd": str(root),
        "timeout_seconds": float(config["timeout_seconds"]),
        "rss_poll_interval_seconds": float(
            config["rss_poll_interval_seconds"]
        ),
        "rss_measurement_kind": process_memory_probe_kind(),
        "input_model": file_digest(
            resolve_path(root, str(job["model_path"]))
        ),
        "classpath": file_digest(
            resolve_path(root, str(config["classpath"]))
        ),
        "artifacts": {
            "stdout": str(stdout_path.relative_to(campaign_dir)),
            "stderr": str(stderr_path.relative_to(campaign_dir)),
            "output": str(output_path.relative_to(campaign_dir)),
            "transitions": str(transitions_path.relative_to(campaign_dir)),
        },
    }
    atomic_write_json(meta_path, base_meta)
    process: Optional[subprocess.Popen[Any]] = None
    spawn_error = ""
    harness_error = ""
    harness_errors: List[str] = []
    harness_termination_action = ""
    timeout_action = ""
    timed_out = False
    rss_samples = 0
    rss_available_samples = 0
    peak_rss = 0
    start_ns = time.monotonic_ns()

    def record_harness_error(error: Exception) -> None:
        nonlocal harness_error, harness_termination_action
        detail = "%s: %s" % (type(error).__name__, error)
        harness_errors.append(detail)
        harness_error = " | ".join(harness_errors)
        should_terminate = False
        if process is not None:
            try:
                should_terminate = process.poll() is None
            except Exception as poll_error:
                should_terminate = True
                harness_termination_action = "poll_error:%s: %s" % (
                    type(poll_error).__name__, poll_error
                )
        if should_terminate and process is not None:
            try:
                action = terminate_process_tree(process)
                harness_termination_action = ";".join(
                    value
                    for value in (harness_termination_action, action)
                    if value
                )
            except Exception as termination_exc:
                harness_termination_action = "termination_error:%s: %s" % (
                    type(termination_exc).__name__, termination_exc
                )
        for artifact in (stdout_path, stderr_path):
            try:
                artifact.touch(exist_ok=True)
            except OSError:
                pass
        try:
            with stderr_path.open("ab") as stderr_handle:
                stderr_handle.write(
                    ("\n[HARNESS_ERROR] " + detail + "\n").encode(
                        "utf-8", errors="replace"
                    )
                )
        except OSError:
            pass

    def safe_file_digest(path: Path) -> Dict[str, Any]:
        try:
            return file_digest(path)
        except Exception as error:
            return {
                "exists": False,
                "sha256": "",
                "bytes": "",
                "digest_error": "%s: %s" % (type(error).__name__, error),
            }

    try:
        with stdout_path.open("wb") as stdout_handle, stderr_path.open(
            "wb"
        ) as stderr_handle:
            try:
                process = subprocess.Popen(
                    command,
                    cwd=str(root),
                    stdin=subprocess.DEVNULL,
                    stdout=stdout_handle,
                    stderr=stderr_handle,
                    **process_group_popen_kwargs(),
                )
            except OSError as exc:
                spawn_error = "%s: %s" % (type(exc).__name__, exc)
                if exc.errno == errno.ENOMEM:
                    spawn_error += " [ENOMEM]"
            if process is not None:
                deadline = (
                    time.monotonic() + float(config["timeout_seconds"])
                )
                interval = float(config["rss_poll_interval_seconds"])
                while process.poll() is None:
                    rss_samples += 1
                    sample = process_rss_kib(process.pid)
                    if sample is not None:
                        rss_available_samples += 1
                        peak_rss = max(peak_rss, sample)
                    if time.monotonic() >= deadline:
                        timed_out = True
                        timeout_action = terminate_process_tree(process)
                        break
                    time.sleep(interval)
                if process.poll() is None:
                    process.wait()
                # Capture a final sample when the process remains visible briefly.
                sample = process_rss_kib(process.pid)
                if sample is not None:
                    rss_samples += 1
                    rss_available_samples += 1
                    peak_rss = max(peak_rss, sample)
    except Exception as exc:
        record_harness_error(exc)
    except BaseException:
        if process is not None and process.poll() is None:
            terminate_process_tree(process)
        raise
    try:
        end_ns = time.monotonic_ns()
        elapsed_ns = max(0, end_ns - start_ns)
        stderr_text = (
            stderr_path.read_text(encoding="utf-8", errors="replace")
            if stderr_path.is_file()
            else ""
        )
        exit_code = process.returncode if process is not None else None
        status = status_from_exit(
            exit_code, timed_out, stderr_text, spawn_error=spawn_error
        )
        if spawn_error and "ENOMEM" in spawn_error:
            status = "OOM"
        if harness_error:
            status = "HARNESS_ERROR"
        parsed = parse_evaluation_file(output_path)
        final_meta = dict(base_meta)
        final_meta.update(
            {
                "completed": True,
                "status": status,
                "finished_utc": current_utc(),
                "exit_code": exit_code,
                "timed_out": timed_out,
                "timeout_termination_action": timeout_action,
                "spawn_error": spawn_error,
                "harness_error": harness_error,
                "harness_errors": list(harness_errors),
                "harness_termination_action": harness_termination_action,
                "elapsed_monotonic_ns": elapsed_ns,
                "elapsed_monotonic_seconds": elapsed_ns / 1_000_000_000.0,
                "peak_rss_kib": peak_rss if rss_available_samples else "",
                "peak_rss_bytes": peak_rss * 1024
                if rss_available_samples
                else "",
                "rss_measurement_status": "measured"
                if rss_available_samples
                else "unavailable",
                "rss_samples_attempted": rss_samples,
                "rss_samples_available": rss_available_samples,
                "evaluation_csv": {
                    "found": parsed["found"],
                    "row_count": len(parsed["rows"]),
                    "header": parsed["header"],
                    "errors": parsed["errors"],
                    "marker_count": parsed["marker_count"],
                },
                "artifact_digests": {
                    "stdout": file_digest(stdout_path),
                    "stderr": file_digest(stderr_path),
                    "output": file_digest(output_path),
                    "transitions": file_digest(transitions_path),
                },
            }
        )
        atomic_write_json(meta_path, final_meta)
    except Exception as exc:
        record_harness_error(exc)
        end_ns = time.monotonic_ns()
        elapsed_ns = max(0, end_ns - start_ns)
        exit_code = process.returncode if process is not None else None
        final_meta = dict(base_meta)
        final_meta.update(
            {
                "completed": True,
                "status": "HARNESS_ERROR",
                "finished_utc": current_utc(),
                "exit_code": exit_code,
                "timed_out": timed_out,
                "timeout_termination_action": timeout_action,
                "spawn_error": spawn_error,
                "harness_error": harness_error,
                "harness_errors": list(harness_errors),
                "harness_termination_action": harness_termination_action,
                "elapsed_monotonic_ns": elapsed_ns,
                "elapsed_monotonic_seconds": elapsed_ns / 1_000_000_000.0,
                "peak_rss_kib": peak_rss if rss_available_samples else "",
                "peak_rss_bytes": peak_rss * 1024
                if rss_available_samples
                else "",
                "rss_measurement_status": "measured"
                if rss_available_samples
                else "unavailable",
                "rss_samples_attempted": rss_samples,
                "rss_samples_available": rss_available_samples,
                "evaluation_csv": {
                    "found": False,
                    "row_count": 0,
                    "header": [],
                    "errors": [harness_error],
                    "marker_count": 0,
                },
                "artifact_digests": {
                    "stdout": safe_file_digest(stdout_path),
                    "stderr": safe_file_digest(stderr_path),
                    "output": safe_file_digest(output_path),
                    "transitions": safe_file_digest(transitions_path),
                },
            }
        )
        # Persistent failure of this atomic commit is the unavoidable storage
        # boundary: no truthful terminal record can be written without storage.
        atomic_write_json(meta_path, final_meta)
    return final_meta


def ensure_campaign(
    config: Mapping[str, Any],
    config_path: Path,
    root: Path,
    plan: Mapping[str, Any],
    run_id: str,
) -> tuple[Path, str]:
    root = root.resolve()
    configured_results = Path(str(config["results_root"]))
    if configured_results.is_absolute():
        results_lexical = Path(os.path.abspath(str(configured_results)))
        try:
            results_relative = results_lexical.relative_to(root)
        except ValueError as error:
            raise RuntimeError("Results root escapes the repository") from error
    else:
        if ".." in configured_results.parts or not configured_results.parts:
            raise RuntimeError("Results root is not a safe repository path")
        results_relative = configured_results
        results_lexical = root / results_relative
    current = root
    for part in results_relative.parts:
        current = current / part
        if current.is_symlink():
            raise RuntimeError("Results root contains a symlink component")
    results_root = results_lexical.resolve()
    try:
        results_root.relative_to(root)
    except ValueError as error:
        raise RuntimeError("Results root escapes the repository") from error
    campaign_lexical = results_lexical / run_id
    if campaign_lexical.is_symlink():
        raise RuntimeError("Campaign directory is a symlink")
    campaign_dir = campaign_lexical.resolve()
    try:
        campaign_dir.relative_to(results_root)
    except ValueError as error:
        raise RuntimeError("Campaign directory escapes the results root") from error
    if campaign_dir.exists() and not campaign_dir.is_dir():
        raise RuntimeError("Campaign path is not a directory")
    try:
        require_unsealed_output_path(campaign_dir)
    except ValueError as error:
        raise RuntimeError("Campaign is inside checksum-sealed evidence") from error
    if campaign_dir.exists():
        for existing in campaign_dir.rglob("*"):
            if existing.is_symlink():
                raise RuntimeError("Existing campaign contains a symlink")
        for seal in campaign_dir.rglob("SHA256SUMS"):
            relative = seal.relative_to(campaign_dir)
            if not relative.parts or relative.parts[0] != "inputs":
                raise RuntimeError("Sealed campaign cannot be resumed or mutated")
    campaign_dir.mkdir(parents=True, exist_ok=True)
    config_bytes = config_path.read_bytes()
    config_sha = sha256_bytes(config_bytes)
    plan_path = campaign_dir / "plan.json"
    config_copy_path = campaign_dir / "config.json"
    if plan_path.exists():
        existing = read_json(plan_path)
        if existing.get("plan_sha256") != plan.get("plan_sha256"):
            raise RuntimeError(
                "Existing campaign plan differs; choose a new --run-id"
            )
    else:
        atomic_write_json(plan_path, plan)
    if config_copy_path.exists():
        if sha256_bytes(config_copy_path.read_bytes()) != config_sha:
            raise RuntimeError(
                "Existing campaign config differs; choose a new --run-id"
            )
    else:
        config_copy_path.write_bytes(config_bytes)
    environment_path = campaign_dir / "environment.json"
    if not environment_path.exists():
        manifest = environment_manifest(config, root)
        manifest.update(
            {
                "captured_utc": current_utc(),
                "experiment_id": config["experiment_id"],
                "config_sha256": config_sha,
                "plan_sha256": plan["plan_sha256"],
            }
        )
        manifest["execution_environment_fingerprint"] = (
            execution_environment_fingerprint(manifest)
        )
        atomic_write_json(environment_path, manifest)
    return campaign_dir, config_sha


def require_matching_execution_environment(
    campaign_dir: Path,
    config: Mapping[str, Any],
    root: Path,
) -> str:
    """Reject a resume invocation from any different host or JVM."""

    saved = read_json(campaign_dir / "environment.json")
    registered = saved.get("execution_environment_fingerprint")
    if not isinstance(registered, dict):
        raise RuntimeError("Campaign lacks an execution-environment fingerprint")
    current_manifest = environment_manifest(config, root)
    requirements = config.get("host_requirements", {})
    minimum_free = float(requirements.get("minimum_free_disk_gib", 0))
    if float(current_manifest.get("free_disk_bytes", 0)) < (
        minimum_free * (1024 ** 3)
    ):
        raise RuntimeError("Current host lacks the registered minimum free disk")
    current = execution_environment_fingerprint(current_manifest)
    if registered != current:
        raise RuntimeError(
            "Current host/JVM differs from the campaign execution fingerprint; "
            "choose a new --run-id"
        )
    return str(current["sha256"])


def acquire_campaign_execution_lock(campaign_dir: Path):
    """Acquire one nonblocking process lock for the whole serial invocation."""

    lock_path = campaign_dir / "execution.lock"
    handle = lock_path.open("a+b")
    try:
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            if handle.tell() == 0:
                handle.write(b"0")
                handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (BlockingIOError, OSError) as error:
        handle.close()
        raise RuntimeError(
            "Another process is already executing this campaign"
        ) from error
    return handle


def release_campaign_execution_lock(handle) -> None:
    try:
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        handle.close()


def main() -> int:
    args = arguments()
    config_argument = args.config.absolute()
    if config_argument.is_symlink():
        print("PRECHECK ERROR: Config path is a symlink", file=sys.stderr)
        return 2
    config_path = config_argument.resolve()
    config = load_config(config_path)
    root = repository_root(__file__)
    plan = build_plan(config)
    errors = validate_inputs(config, plan, root, config_argument)
    if errors:
        for error in errors:
            print("PRECHECK ERROR:", error, file=sys.stderr)
        return 2
    jobs = selected_jobs(plan, args)
    if (
        config.get("registered_run_id")
        and not args.dry_run
        and not args.list_plan
        and (
            args.method
            or args.model
            or args.target
            or args.repetition
            or args.max_runs is not None
        )
    ):
        print(
            "Registered campaign execution forbids job filters and --max-runs",
            file=sys.stderr,
        )
        return 2
    if args.list_plan:
        for job in jobs:
            print(
                "%04d %s target=%s role=%s order=%d"
                % (
                    job["global_order_index"],
                    job["job_id"],
                    job["target_name"],
                    job["analysis_role"],
                    job["method_order_index"],
                )
            )
        print(
            "selected=%d planned=%d plan_sha256=%s"
            % (len(jobs), plan["job_count"], plan["plan_sha256"])
        )
        if not args.dry_run:
            return 0
    if args.dry_run:
        placeholder = Path("/DRY_RUN")
        for job in jobs:
            command = build_command(
                config,
                job,
                root,
                placeholder / job["job_id"] / "output.txt",
                placeholder / job["job_id"] / "transitions.txt",
            )
            print("%s\t%s" % (job["job_id"], command_text(command)))
        print(
            "DRY RUN: selected=%d planned=%d; no JVM launched"
            % (len(jobs), plan["job_count"])
        )
        return 0
    if not args.run_id:
        print("--run-id is required for execution", file=sys.stderr)
        return 2
    registered_run_id = str(config.get("registered_run_id", ""))
    if registered_run_id and args.run_id != registered_run_id:
        print("--run-id differs from the prospectively registered run", file=sys.stderr)
        return 2
    try:
        validate_run_id(args.run_id)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    if "preexecution_gate" in config:
        campaign_candidate = (
            resolve_path(root, str(config["results_root"])) / args.run_id
        ).resolve()
        preexecution_tree = resolve_path(
            root, str(config["preexecution_gate"]["path"])
        ).parent
        if (
            campaign_candidate == preexecution_tree
            or preexecution_tree in campaign_candidate.parents
            or campaign_candidate in preexecution_tree.parents
        ):
            print(
                "--run-id would overlap the sealed pre-execution evidence tree",
                file=sys.stderr,
            )
            return 2
    if not jobs:
        print("No jobs match the filters", file=sys.stderr)
        return 2
    campaign_dir, config_sha = ensure_campaign(
        config, config_path, root, plan, args.run_id
    )
    completed = 0
    skipped = 0
    lock_handle = acquire_campaign_execution_lock(campaign_dir)
    try:
        environment_fingerprint_sha256 = require_matching_execution_environment(
            campaign_dir, config, root
        )
        for index, job in enumerate(jobs, start=1):
            meta_path = campaign_dir / "runs" / job["job_id"] / "meta.json"
            if meta_path.is_file():
                previous = read_json(meta_path)
                if previous.get("completed") is True:
                    skipped += 1
                    print(
                        "[%d/%d] SKIP terminal %s (%s)"
                        % (index, len(jobs), job["job_id"], previous.get("status"))
                    )
                    continue
            print("[%d/%d] RUN %s" % (index, len(jobs), job["job_id"]))
            result = run_job(
                config,
                config_sha,
                plan["plan_sha256"],
                root,
                campaign_dir,
                job,
                environment_fingerprint_sha256,
            )
            completed += 1
            print(
                "  status=%s time=%.6fs peak_rss_kib=%s"
                % (
                    result["status"],
                    result["elapsed_monotonic_seconds"],
                    result["peak_rss_kib"],
                )
            )
    finally:
        release_campaign_execution_lock(lock_handle)
    print(
        "Campaign %s: executed=%d skipped=%d selected=%d"
        % (campaign_dir, completed, skipped, len(jobs))
    )
    print(
        "Run collect_results.py --campaign %s to materialize CSV files."
        % campaign_dir
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
