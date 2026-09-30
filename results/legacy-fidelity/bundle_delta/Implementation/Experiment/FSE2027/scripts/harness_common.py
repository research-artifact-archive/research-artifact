#!/usr/bin/env python3
"""Shared, dependency-free helpers for the FSE 2027 experiment harness."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import platform
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


CSV_MARKER = "================ EVALUATION DATA CSV ================"
SUMMARY_MARKER = "================ EVALUATION SUMMARY ================"
ORDER_ALGORITHM = "seeded-per-unit-permutation/cyclic-rotation/reverse-every-cycle-v1"
TERMINAL_META_VERSION = 1
KNOWN_TERMINAL_PROCESS_STATUSES = frozenset({
    "SUCCESS", "UNREALIZABLE", "TIMEOUT", "OOM", "SPAWN_ERROR",
    "NO_COMPOSITION", "NO_TRANSITION_OUTPUT", "CRASH",
    "INVALID_CERTIFICATE", "INVALID_INPUT", "VERIFICATION_INCONCLUSIVE",
    "USAGE_ERROR", "SIGNALLED", "UNKNOWN_EXIT", "HARNESS_ERROR",
})


def process_memory_probe_kind(system: Optional[str] = None) -> str:
    """Describe the process-memory probe used on the current platform."""
    current = platform.system() if system is None else system
    if current == "Windows":
        return "windows_process_working_set"
    if current == "Darwin":
        return "darwin_proc_pid_rusage_resident"
    if current in {"Linux", "FreeBSD"}:
        return "posix_ps_rss"
    return "unavailable"


def physical_memory_bytes() -> Optional[int]:
    """Return installed physical memory from the standard POSIX interface."""
    try:
        pages = int(os.sysconf("SC_PHYS_PAGES"))
        page_size = int(os.sysconf("SC_PAGE_SIZE"))
        total = pages * page_size
        return total if pages > 0 and page_size > 0 else None
    except (AttributeError, OSError, TypeError, ValueError):
        return None


def _windows_working_set_bytes(pid: int) -> Optional[int]:
    """Read a process working set with the Windows PSAPI via ctypes."""
    try:
        import ctypes
        from ctypes import wintypes

        class ProcessMemoryCounters(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        process_query_limited_information = 0x1000
        process_vm_read = 0x0010
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        kernel32.OpenProcess.argtypes = [
            wintypes.DWORD,
            wintypes.BOOL,
            wintypes.DWORD,
        ]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        psapi.GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(ProcessMemoryCounters),
            wintypes.DWORD,
        ]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        handle = kernel32.OpenProcess(
            process_query_limited_information | process_vm_read,
            False,
            int(pid),
        )
        if not handle:
            return None
        try:
            counters = ProcessMemoryCounters()
            counters.cb = ctypes.sizeof(ProcessMemoryCounters)
            if not psapi.GetProcessMemoryInfo(
                    handle, ctypes.byref(counters), counters.cb):
                return None
            return int(counters.WorkingSetSize)
        finally:
            kernel32.CloseHandle(handle)
    except (AttributeError, OSError, TypeError, ValueError):
        return None


def _darwin_resident_bytes(pid: int) -> Optional[int]:
    """Read current resident bytes with macOS proc_pid_rusage.

    ``ps`` may be unavailable in sandboxed launch environments even though a
    parent process may inspect its own child.  The public libproc API avoids a
    shell utility and reports the same resident-size field directly.
    """
    try:
        import ctypes

        class RUsageInfoV0(ctypes.Structure):
            _fields_ = [
                ("uuid", ctypes.c_uint8 * 16),
                ("user_time", ctypes.c_uint64),
                ("system_time", ctypes.c_uint64),
                ("package_idle_wakeups", ctypes.c_uint64),
                ("interrupt_wakeups", ctypes.c_uint64),
                ("pageins", ctypes.c_uint64),
                ("wired_size", ctypes.c_uint64),
                ("resident_size", ctypes.c_uint64),
                ("physical_footprint", ctypes.c_uint64),
                ("process_start_abstime", ctypes.c_uint64),
                ("process_exit_abstime", ctypes.c_uint64),
            ]

        libproc = ctypes.CDLL("/usr/lib/libproc.dylib", use_errno=True)
        libproc.proc_pid_rusage.argtypes = [
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_void_p,
        ]
        libproc.proc_pid_rusage.restype = ctypes.c_int
        usage = RUsageInfoV0()
        if libproc.proc_pid_rusage(
                int(pid), 0, ctypes.byref(usage)) != 0:
            return None
        resident = int(usage.resident_size)
        return resident if resident >= 0 else None
    except (AttributeError, OSError, TypeError, ValueError):
        return None


def process_rss_kib(
        pid: int, system: Optional[str] = None) -> Optional[int]:
    """Return current resident memory in KiB on POSIX and Windows.

    Windows has no POSIX RSS field. Its process working set is the closest
    directly comparable resident-memory quantity and is sampled through
    GetProcessMemoryInfo rather than an optional shell utility.
    """
    current = platform.system() if system is None else system
    if current == "Windows":
        working_set = _windows_working_set_bytes(pid)
        return None if working_set is None else working_set // 1024
    if current == "Darwin":
        resident = _darwin_resident_bytes(pid)
        return None if resident is None else resident // 1024
    if current not in {"Linux", "FreeBSD"}:
        return None
    try:
        completed = subprocess.run(
            ["ps", "-o", "rss=", "-p", str(pid)],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=2,
            check=False,
        )
        if completed.returncode != 0 or not completed.stdout.strip():
            return None
        return int(completed.stdout.strip().splitlines()[0].strip())
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def process_group_popen_kwargs(
        os_name: Optional[str] = None) -> Dict[str, Any]:
    """Return platform-specific flags for an independently killable trial."""
    current = os.name if os_name is None else os_name
    if current == "posix":
        return {"start_new_session": True}
    if current == "nt":
        creation_flag = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        return {"creationflags": creation_flag}
    return {}


def terminate_process_tree(
        process: subprocess.Popen[Any], os_name: Optional[str] = None) -> str:
    """Terminate a timed-out trial and record every attempted action."""
    current = os.name if os_name is None else os_name
    actions: List[str] = []
    try:
        if current == "posix":
            os.killpg(process.pid, signal.SIGTERM)
            actions.append("SIGTERM_process_group")
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                actions.append("SIGKILL_process_group")
                process.wait(timeout=5)
            return ";".join(actions)

        if current == "nt":
            try:
                completed = subprocess.run(
                    ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=15,
                    check=False,
                )
                actions.append("taskkill_process_tree_exit_%d"
                               % completed.returncode)
            except (OSError, subprocess.SubprocessError) as error:
                actions.append("taskkill_error:%s" % error)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                actions.append("kill_fallback")
                process.wait(timeout=5)
            return ";".join(actions)

        process.terminate()
        actions.append("terminate")
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            actions.append("kill")
            process.wait(timeout=5)
    except (ProcessLookupError, OSError) as error:
        actions.append("termination_error:%s" % error)
    return ";".join(actions)


def repository_root(script_file: str) -> Path:
    """Resolve the repository root from FSE2027/scripts/<script>."""
    return Path(script_file).resolve().parents[4]


def load_config(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        config = json.load(handle)
    validate_config(config)
    return config


def validate_config(config: Mapping[str, Any]) -> None:
    required = {
        "schema_version",
        "experiment_id",
        "master_seed",
        "repetitions",
        "timeout_seconds",
        "rss_poll_interval_seconds",
        "java",
        "java_heap",
        "classpath",
        "main_class",
        "results_root",
        "models",
        "targets",
        "methods",
    }
    missing = sorted(required.difference(config))
    if missing:
        raise ValueError("Configuration is missing: " + ", ".join(missing))
    if config["schema_version"] != 1:
        raise ValueError("Only configuration schema_version=1 is supported")
    if int(config["repetitions"]) <= 0:
        raise ValueError("repetitions must be positive")
    if float(config["timeout_seconds"]) <= 0:
        raise ValueError("timeout_seconds must be positive")
    if float(config["rss_poll_interval_seconds"]) <= 0:
        raise ValueError("rss_poll_interval_seconds must be positive")
    for collection in ("models", "targets", "methods"):
        ids = [str(item.get("id", "")) for item in config[collection]]
        if not ids or any(not value for value in ids):
            raise ValueError(collection + " must contain non-empty ids")
        if len(set(ids)) != len(ids):
            raise ValueError(collection + " contains duplicate ids")
    if len(config["methods"]) < 2:
        raise ValueError("At least two methods are needed for a comparison")
    for method in config["methods"]:
        if "{suffix}" not in method.get("target_template", ""):
            raise ValueError(
                "method %s target_template must contain {suffix}" % method["id"]
            )
        properties = method.get("jvm_properties", {})
        if not isinstance(properties, dict):
            raise ValueError("jvm_properties must be an object for " + method["id"])
    target_ids = {str(item["id"]) for item in config["targets"]}
    method_ids = {str(item["id"]) for item in config["methods"]}
    for model in config["models"]:
        if int(model.get("repetitions", config["repetitions"])) <= 0:
            raise ValueError(
                "model %s repetitions must be positive" % model["id"]
            )
        selected_targets = model.get("target_ids")
        if selected_targets is not None:
            if (
                not isinstance(selected_targets, list)
                or not selected_targets
                or any(not isinstance(value, str) or not value
                       for value in selected_targets)
            ):
                raise ValueError(
                    "model %s target_ids must be a non-empty string list"
                    % model["id"]
                )
            unknown = sorted(set(selected_targets).difference(target_ids))
            if unknown:
                raise ValueError(
                    "model %s selects unknown target ids: %s"
                    % (model["id"], ", ".join(unknown))
                )
            if len(set(selected_targets)) != len(selected_targets):
                raise ValueError(
                    "model %s target_ids contains duplicates" % model["id"]
                )
        selected_methods = model.get("method_ids")
        if selected_methods is not None:
            if (
                not isinstance(selected_methods, list)
                or not selected_methods
                or any(not isinstance(value, str) or not value
                       for value in selected_methods)
            ):
                raise ValueError(
                    "model %s method_ids must be a non-empty string list"
                    % model["id"]
                )
            unknown_methods = sorted(
                set(selected_methods).difference(method_ids)
            )
            if unknown_methods:
                raise ValueError(
                    "model %s selects unknown method ids: %s"
                    % (model["id"], ", ".join(unknown_methods))
                )
            if len(set(selected_methods)) != len(selected_methods):
                raise ValueError(
                    "model %s method_ids contains duplicates" % model["id"]
                )
        properties_override = model.get("jvm_properties_override")
        if properties_override is not None and not isinstance(
                properties_override, dict):
            raise ValueError(
                "model %s jvm_properties_override must be an object"
                % model["id"]
            )


def canonical_json(value: Any) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_digest(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {"exists": False, "sha256": "", "bytes": ""}
    return {
        "exists": True,
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }


def stable_seed(master_seed: int, *parts: str) -> int:
    payload = "\0".join([str(master_seed)] + list(parts)).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def _seeded_permutation(items: Sequence[str], seed: int) -> List[str]:
    # Local import keeps the generated sequence isolated from all other randomness.
    import random

    result = list(items)
    random.Random(seed).shuffle(result)
    return result


def method_order(
    method_ids: Sequence[str], master_seed: int, unit_id: str, repetition: int
) -> Tuple[int, List[str], List[str]]:
    """Return seed, base order, and a counterbalanced order for one block."""
    seed = stable_seed(master_seed, "method-order", unit_id)
    base = _seeded_permutation(method_ids, seed)
    size = len(base)
    cycle = repetition // size
    offset = repetition % size
    oriented = list(reversed(base)) if cycle % 2 else base
    ordered = oriented[offset:] + oriented[:offset]
    return seed, base, ordered


def build_plan(config: Mapping[str, Any]) -> Dict[str, Any]:
    """Build the complete deterministic plan. No run can vanish during collection."""
    method_map = {item["id"]: item for item in config["methods"]}
    method_ids = list(method_map)
    jobs: List[Dict[str, Any]] = []
    global_index = 0
    default_repetitions = int(config["repetitions"])
    model_repetitions = {
        str(model["id"]): int(model.get("repetitions", default_repetitions))
        for model in config["models"]
    }
    maximum_repetitions = max(model_repetitions.values())
    for repetition in range(maximum_repetitions):
        units = []
        for model in config["models"]:
            if repetition >= model_repetitions[str(model["id"])]:
                continue
            selected_targets = set(
                model.get(
                    "target_ids",
                    [target["id"] for target in config["targets"]],
                )
            )
            units.extend(
                (model, target)
                for target in config["targets"]
                if target["id"] in selected_targets
            )
        unit_seed = stable_seed(
            int(config["master_seed"]), "unit-order", str(repetition)
        )
        unit_keys = ["%s/%s" % (m["id"], t["id"]) for m, t in units]
        key_to_unit = {
            "%s/%s" % (model["id"], target["id"]): (model, target)
            for model, target in units
        }
        ordered_units = [
            key_to_unit[key] for key in _seeded_permutation(unit_keys, unit_seed)
        ]
        for unit_position, (model, target) in enumerate(ordered_units):
            unit_id = "%s/%s" % (model["id"], target["id"])
            selected_method_ids = list(model.get("method_ids", method_ids))
            order_seed, base_order, ordered_methods = method_order(
                selected_method_ids,
                int(config["master_seed"]),
                unit_id,
                repetition,
            )
            block_id = "%s__%s__rep%02d" % (
                model["id"],
                target["id"],
                repetition + 1,
            )
            for order_index, method_id in enumerate(ordered_methods):
                method = method_map[method_id]
                jvm_properties = dict(method.get("jvm_properties", {}))
                jvm_properties.update(
                    model.get("jvm_properties_override", {})
                )
                target_name = method["target_template"].format(
                    suffix=target["suffix"]
                )
                job_id = "%s__%s" % (block_id, method_id)
                job = {
                    "job_id": job_id,
                    "block_id": block_id,
                    "model_id": model["id"],
                    "model_path": model["path"],
                    "target_id": target["id"],
                    "target_name": target_name,
                    "method_id": method_id,
                    "analysis_role": method.get("analysis_role", ""),
                    "repetition": repetition + 1,
                    "unit_order_seed": unit_seed,
                    "unit_order_index": unit_position,
                    "method_order_seed": order_seed,
                    "method_base_order": base_order,
                    "method_order": ordered_methods,
                    "method_order_index": order_index,
                    "global_order_index": global_index,
                    "jvm_properties": jvm_properties,
                }
                if "family" in model:
                    job["model_family"] = model["family"]
                if "factors" in model:
                    job["model_factors"] = model["factors"]
                if "repetitions" in model:
                    job["model_planned_repetitions"] = int(
                        model["repetitions"]
                    )
                jobs.append(job)
                global_index += 1
    plan_core = {
        "schema_version": 1,
        "experiment_id": config["experiment_id"],
        "master_seed": int(config["master_seed"]),
        "order_algorithm": ORDER_ALGORITHM,
        "repetitions": int(config["repetitions"]),
        "job_count": len(jobs),
        "jobs": jobs,
    }
    if any(
        "repetitions" in model for model in config["models"]
    ):
        plan_core["model_repetitions"] = model_repetitions
        plan_core["maximum_repetitions"] = maximum_repetitions
    plan_core["plan_sha256"] = sha256_bytes(canonical_json(plan_core).encode("utf-8"))
    return plan_core


def resolve_path(root: Path, configured_path: str) -> Path:
    path = Path(configured_path)
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def require_unsealed_output_path(path: Path) -> None:
    """Reject any output located at or below an existing checksum seal."""

    resolved = path.resolve()
    for ancestor in (resolved, *resolved.parents):
        if (ancestor / "SHA256SUMS").is_file():
            raise ValueError("output path is inside a checksum-sealed evidence tree")


def resolve_prospective_output(
    root: Path, registered_value: str, supplied_path: Path
) -> Path:
    """Resolve a registered, not-yet-created output without following aliases."""

    root = root.resolve()
    relative = Path(registered_value)
    if (
        relative.is_absolute()
        or not relative.parts
        or ".." in relative.parts
        or relative in {Path("."), Path("")}
    ):
        raise ValueError("registered output must be a repository-relative path")
    lexical = root / relative
    supplied_absolute = Path(os.path.abspath(str(supplied_path)))
    registered_absolute = Path(os.path.abspath(str(lexical)))
    if supplied_absolute != registered_absolute:
        raise ValueError("output differs from the prospectively registered path")
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("registered output contains a symlink component")
    resolved = lexical.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise ValueError("registered output escapes the repository") from error
    if lexical.exists() or lexical.is_symlink():
        raise ValueError("registered output already exists")
    require_unsealed_output_path(resolved)
    return resolved


def resolve_registered_existing(
    root: Path,
    registered_value: str,
    supplied_path: Path,
    expected_kind: str,
) -> Path:
    """Resolve existing registered evidence while rejecting every alias."""

    root = root.resolve()
    relative = Path(registered_value)
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise ValueError("registered evidence must be repository-relative")
    lexical = root / relative
    if Path(os.path.abspath(str(supplied_path))) != Path(
        os.path.abspath(str(lexical))
    ):
        raise ValueError("evidence path differs from the registered path")
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("registered evidence contains a symlink component")
    resolved = lexical.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise ValueError("registered evidence escapes the repository") from error
    if expected_kind == "file":
        if not resolved.is_file():
            raise ValueError("registered evidence file is missing")
    elif expected_kind == "directory":
        if not resolved.is_dir():
            raise ValueError("registered evidence directory is missing")
    else:
        raise ValueError("unsupported registered evidence kind")
    return resolved


def _resolve_gate_file(root: Path, value: str, label: str) -> Path:
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise ValueError(label + " must be a repository-relative path")
    lexical = root / relative
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(label + " contains a symlink component")
    resolved = lexical.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise ValueError(label + " escapes the repository") from error
    if not resolved.is_file():
        raise ValueError(label + " is missing")
    return resolved


def _validate_runtime_freeze(
    root: Path, summary: Mapping[str, Any]
) -> Mapping[str, Any]:
    """Revalidate the exact source/JAR build frozen by the pre-execution audit."""

    registration = summary.get("registration")
    freeze = (
        registration.get("runtime_freeze")
        if isinstance(registration, dict)
        else None
    )
    if not isinstance(freeze, dict):
        raise ValueError("pre-execution audit omits its runtime freeze")
    attestation_row = freeze.get("attestation")
    source_row = freeze.get("source_identity")
    jar_row = freeze.get("runtime_jar")
    validation_row = freeze.get("validation_summary")
    if not all(isinstance(value, dict) for value in (
        attestation_row, source_row, jar_row, validation_row
    )):
        raise ValueError("pre-execution runtime freeze is malformed")

    # Imported lazily: verify_runtime_build imports this module during startup.
    from verify_runtime_build import (  # pylint: disable=import-outside-toplevel
        ATTESTATION_PATH,
        load_and_validate_attestation,
    )

    attestation_path = _resolve_gate_file(
        root,
        str(attestation_row.get("path", "")),
        "frozen runtime-build attestation",
    )
    canonical_attestation = (root / ATTESTATION_PATH).resolve()
    if attestation_path != canonical_attestation:
        raise ValueError("pre-execution audit names a non-canonical attestation")
    if attestation_row.get("sha256") != sha256_file(attestation_path):
        raise ValueError("runtime-build attestation changed after pre-execution audit")

    current_attestation, current_validation = load_and_validate_attestation(root)
    if current_attestation.get("source_identity") != source_row:
        raise ValueError("source identity changed after pre-execution audit")
    if current_validation != validation_row:
        raise ValueError("runtime validation changed after pre-execution audit")
    current_jar = current_attestation.get("runtime_jar")
    if not isinstance(current_jar, dict):
        raise ValueError("validated attestation omits its runtime JAR")
    jar_path = _resolve_gate_file(
        root, str(jar_row.get("path", "")), "frozen runtime JAR"
    )
    if not all((
        current_jar.get("path") == jar_row.get("path"),
        current_jar.get("sha256") == jar_row.get("sha256"),
        current_jar.get("size_bytes") == jar_row.get("size_bytes"),
        jar_row.get("sha256") == sha256_file(jar_path),
        jar_row.get("size_bytes") == jar_path.stat().st_size,
    )):
        raise ValueError("runtime JAR changed after pre-execution audit")
    return freeze


def validate_preexecution_gate(
    contract: Mapping[str, Any],
    root: Path,
    *,
    expected_caller_role: Optional[str] = None,
    caller_path: Optional[Path] = None,
) -> Mapping[str, Any]:
    """Validate the separately sealed audit that authorizes first execution."""

    root = root.resolve()
    audit_path = _resolve_gate_file(
        root, str(contract.get("path", "")), "pre-execution audit"
    )
    registration_path = _resolve_gate_file(
        root,
        str(contract.get("registration_path", "")),
        "pre-execution registration",
    )
    for label, path in (("pre-execution audit", audit_path),
                        ("pre-execution registration", registration_path)):
        if not path.is_file() or path.is_symlink():
            raise ValueError(label + " is missing or a symlink")
    from campaign_checksums import check_checksums
    if check_checksums(audit_path.parent) <= 0:
        raise ValueError("pre-execution audit checksum seal is empty")
    summary = read_json(audit_path)
    if not isinstance(summary, dict) or not all((
        summary.get("schema_version")
        == "fse2027-prospective-ardrone-audit-v2",
        summary.get("phase") == "PRE_EXECUTION",
        summary.get("status") == "PASS",
        summary.get("integrity_status") == "PASS",
        summary.get("registered_hypothesis_status") == "NOT_RUN",
        summary.get("registration_path")
        == str(registration_path.relative_to(root)),
        summary.get("registration_sha256")
        == sha256_bytes(registration_path.read_bytes()),
    )):
        raise ValueError("pre-execution audit does not authorize execution")
    _validate_runtime_freeze(root, summary)
    if (expected_caller_role is None) != (caller_path is None):
        raise ValueError("caller role and path must be supplied together")
    if expected_caller_role is not None and caller_path is not None:
        registered_files = summary.get("registered_files")
        caller = (
            registered_files.get(expected_caller_role)
            if isinstance(registered_files, dict)
            else None
        )
        if not isinstance(caller, dict):
            raise ValueError("pre-execution audit omits the calling artifact")
        registered_caller = resolve_registered_existing(
            root,
            str(caller.get("path", "")),
            caller_path,
            "file",
        )
        if not isinstance(caller, dict) or not all((
            caller.get("sha256") == sha256_bytes(registered_caller.read_bytes()),
        )):
            raise ValueError(
                "pre-execution audit does not authorize the calling "
                + expected_caller_role
            )
    return summary


def validate_inputs(
    config: Mapping[str, Any],
    plan: Mapping[str, Any],
    root: Path,
    config_path: Optional[Path] = None,
) -> List[str]:
    errors: List[str] = []
    if "preexecution_gate" in config:
        try:
            if config_path is None:
                raise ValueError("config path is required by the pre-execution gate")
            validate_preexecution_gate(
                config["preexecution_gate"],
                root,
                expected_caller_role="config",
                caller_path=config_path,
            )
        except (OSError, ValueError, KeyError, TypeError) as error:
            errors.append("Pre-execution gate failed: " + str(error))
    classpath = resolve_path(root, str(config["classpath"]))
    if not classpath.is_file():
        errors.append("Classpath JAR does not exist: " + str(classpath))
    for model in config["models"]:
        path = resolve_path(root, model["path"])
        if not path.is_file():
            errors.append("Model does not exist: " + str(path))
            continue
        expected_model_hash = str(
            model.get("factors", {}).get("input_sha256", "")
        )
        if expected_model_hash:
            observed_model_hash = str(file_digest(path).get("sha256", ""))
            if observed_model_hash != expected_model_hash:
                errors.append(
                    "Model SHA-256 differs from registered factor: %s"
                    % path
                )
    for registration in config.get("generated_input_manifests", []):
        path = resolve_path(root, str(registration.get("path", "")))
        if not path.is_file():
            errors.append("Registered input manifest does not exist: " + str(path))
            continue
        expected_hash = str(registration.get("sha256", ""))
        observed_hash = str(file_digest(path).get("sha256", ""))
        if not expected_hash or observed_hash != expected_hash:
            errors.append(
                "Registered input manifest SHA-256 mismatch: %s" % path
            )
    checked: set[Tuple[str, str]] = set()
    for job in plan["jobs"]:
        key = (job["model_path"], job["target_name"])
        if key in checked:
            continue
        checked.add(key)
        path = resolve_path(root, job["model_path"])
        if not path.is_file():
            continue
        source = path.read_text(encoding="utf-8", errors="replace")
        target_pattern = re.compile(
            r"(?m)^\s*\|\|\s*" + re.escape(job["target_name"]) + r"\s*="
        )
        if target_pattern.search(source) is None:
            errors.append(
                "Target %s not found in %s" % (job["target_name"], path)
            )
    return errors


def build_command(
    config: Mapping[str, Any],
    job: Mapping[str, Any],
    root: Path,
    output_path: Path,
    transitions_path: Path,
) -> List[str]:
    configured_java = str(config["java"])
    resolved_java = shutil.which(configured_java)
    java = str(Path(resolved_java).resolve()) if resolved_java else configured_java
    configured_properties = dict(job["jvm_properties"])
    # The experiment runner is a CLI process. On macOS, allowing AWT to
    # register with AppKit can abort an otherwise headless synthesis JVM.
    # Keep the safe CLI default cross-platform, while allowing an explicitly
    # registered configuration to override it for a diagnostic run.
    configured_properties.setdefault("java.awt.headless", "true")
    if "mtsa.build.commit" not in configured_properties:
        jar_digest = file_digest(
            resolve_path(root, str(config["classpath"]))
        ).get("sha256", "")
        configured_properties["mtsa.build.commit"] = (
            "jar-sha256-" + jar_digest
            if jar_digest
            else "unavailable"
        )
    properties = [
        "-D%s=%s" % (key, value)
        for key, value in sorted(configured_properties.items())
    ]
    transition_output_mode = str(
        config.get("transition_output_mode", "summary")
    )
    if transition_output_mode not in {"full", "summary"}:
        raise ValueError(
            "transition_output_mode must be 'full' or 'summary'"
        )
    return (
        [java]
        + properties
        + ["-Xmx" + str(config["java_heap"])]
        + [
            "-cp",
            str(resolve_path(root, str(config["classpath"]))),
            str(config["main_class"]),
            "--lts",
            str(resolve_path(root, str(job["model_path"]))),
            "--target",
            str(job["target_name"]),
            "--output",
            str(output_path.resolve()),
            "--transitions",
            str(transitions_path.resolve()),
            "--transition-output",
            transition_output_mode,
        ]
    )


def command_text(command: Sequence[str]) -> str:
    if os.name == "nt":
        return subprocess.list2cmdline(list(command))
    return shlex.join(command)


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def probe_command(command: Sequence[str], timeout: float = 15.0) -> Dict[str, Any]:
    try:
        completed = subprocess.run(
            list(command),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            errors="replace",
            timeout=timeout,
            check=False,
        )
        return {
            "command": list(command),
            "exit_code": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
    except Exception as exc:
        return {
            "command": list(command),
            "exit_code": "",
            "stdout": "",
            "stderr": "",
            "error": "%s: %s" % (type(exc).__name__, exc),
        }


def darwin_hardware_summary() -> Dict[str, Any]:
    """Return only non-sensitive Mac hardware fields.

    ``system_profiler SPHardwareDataType`` can also print a serial number and
    hardware UUID.  Its full output must therefore never be copied into an
    experiment manifest.  This helper retains only the CPU/chip and model
    identifier fields and discards the source text immediately.
    """
    response = probe_command(
        ["system_profiler", "SPHardwareDataType", "-detailLevel", "mini"]
    )
    allowed = {
        "Chip": "chip",
        "Processor Name": "processor_name",
        "Model Identifier": "model_identifier",
    }
    summary: Dict[str, Any] = {
        "command": [
            "system_profiler",
            "SPHardwareDataType",
            "-detailLevel",
            "mini",
        ],
        "exit_code": response.get("exit_code", ""),
    }
    if response.get("error"):
        summary["error"] = response["error"]
    for line in str(response.get("stdout", "")).splitlines():
        stripped = line.strip()
        if ":" not in stripped:
            continue
        label, value = (part.strip() for part in stripped.split(":", 1))
        if label in allowed and value:
            summary[allowed[label]] = value
    return summary


def environment_manifest(
    config: Mapping[str, Any], root: Path
) -> Dict[str, Any]:
    configured_java = str(config["java"])
    resolved_java = shutil.which(configured_java)
    java_executable_path = (
        Path(resolved_java).resolve() if resolved_java else Path(configured_java)
    )
    java_version = probe_command([str(java_executable_path), "-version"])
    git_revision = probe_command(
        ["git", "-C", str(root), "rev-parse", "HEAD"]
    )
    git_status = probe_command(
        ["git", "-C", str(root), "status", "--porcelain=v1"]
    )
    processor = platform.processor()
    cpu_count = os.cpu_count()
    manifest: Dict[str, Any] = {
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "processor": processor,
        "logical_cpu_count": cpu_count,
        "process_memory_probe_kind": process_memory_probe_kind(),
        "python_version": sys.version,
        "python_executable": sys.executable,
        "java_version_probe": java_version,
        "java_executable": {
            "resolved_path": str(java_executable_path),
            "digest": file_digest(java_executable_path),
        },
        "git_revision_probe": git_revision,
        "git_status_probe": git_status,
        "locale": {
            "LANG": os.environ.get("LANG", ""),
            "LC_ALL": os.environ.get("LC_ALL", ""),
        },
        "java_home": os.environ.get("JAVA_HOME", ""),
        "classpath": file_digest(
            resolve_path(root, str(config["classpath"]))
        ),
        "free_disk_bytes": shutil.disk_usage(root).free,
        "free_disk_measurement": "shutil_disk_usage",
    }
    installed_memory = physical_memory_bytes()
    manifest["physical_memory_bytes"] = (
        installed_memory if installed_memory is not None else ""
    )
    manifest["physical_memory_measurement"] = (
        "posix_sysconf" if installed_memory is not None else "unavailable"
    )
    if platform.system() == "Linux":
        cpuinfo = Path("/proc/cpuinfo")
        meminfo = Path("/proc/meminfo")
        if cpuinfo.is_file():
            models = [
                line.split(":", 1)[1].strip()
                for line in cpuinfo.read_text(errors="replace").splitlines()
                if line.lower().startswith("model name") and ":" in line
            ]
            manifest["cpu_model"] = models[0] if models else ""
        if meminfo.is_file():
            first = meminfo.read_text(errors="replace").splitlines()
            manifest["memory_info"] = first[:5]
    elif platform.system() == "Darwin":
        cpu_model_probe = probe_command(
            ["sysctl", "-n", "machdep.cpu.brand_string"]
        )
        manifest["cpu_model_probe"] = cpu_model_probe
        cpu_model = str(cpu_model_probe.get("stdout", "")).strip()
        if not cpu_model:
            hardware = darwin_hardware_summary()
            manifest["darwin_hardware_summary"] = hardware
            cpu_model = str(
                hardware.get("chip", hardware.get("processor_name", ""))
            )
        manifest["cpu_model"] = cpu_model
        manifest["physical_memory_probe"] = probe_command(
            ["sysctl", "-n", "hw.memsize"]
        )
    elif platform.system() == "Windows":
        powershell = "powershell.exe"
        cim_script = (
            "$cpu = Get-CimInstance Win32_Processor | "
            "Select-Object Name,Manufacturer,NumberOfCores,"
            "NumberOfLogicalProcessors,MaxClockSpeed; "
            "$computer = Get-CimInstance Win32_ComputerSystem | "
            "Select-Object Manufacturer,Model,TotalPhysicalMemory,"
            "NumberOfProcessors,SystemType; "
            "$operatingSystem = Get-CimInstance Win32_OperatingSystem | "
            "Select-Object Caption,Version,BuildNumber,OSArchitecture,"
            "LastBootUpTime,LocalDateTime; "
            "$disk = Get-CimInstance Win32_LogicalDisk -Filter "
            "\"DriveType=3\" | Select-Object DeviceID,Size,FreeSpace; "
            "$timeZone = Get-TimeZone | Select-Object Id,DisplayName; "
            "[PSCustomObject]@{cpu=$cpu;computer=$computer;"
            "operating_system=$operatingSystem;local_disks=$disk;"
            "time_zone=$timeZone} | ConvertTo-Json -Compress -Depth 5"
        )
        manifest["windows_cim_probe"] = probe_command(
            [powershell, "-NoProfile", "-NonInteractive", "-Command", cim_script]
        )
        manifest["windows_power_plan_probe"] = probe_command(
            ["powercfg.exe", "/GETACTIVESCHEME"]
        )
    return manifest


def execution_environment_fingerprint(
    manifest: Mapping[str, Any],
) -> Dict[str, Any]:
    """Bind every resumed invocation to the same host and JVM identity."""

    payload = {
        key: manifest.get(key)
        for key in (
            "platform",
            "system",
            "release",
            "machine",
            "processor",
            "logical_cpu_count",
            "process_memory_probe_kind",
            "physical_memory_bytes",
            "physical_memory_measurement",
            "cpu_model",
            "java_home",
            "java_version_probe",
            "java_executable",
            "classpath",
        )
    }
    encoded = (canonical_json(payload) + "\n").encode("utf-8")
    return {
        "schema_version": "fse2027-execution-environment-fingerprint-v1",
        "payload": payload,
        "sha256": sha256_bytes(encoded),
    }


def parse_evaluation_csv(text: str) -> Dict[str, Any]:
    """Parse only the marked CSV block and retain malformed-row diagnostics."""
    lines = text.splitlines()
    marker_positions = [
        index for index, line in enumerate(lines) if line.strip() == CSV_MARKER
    ]
    if not marker_positions:
        return {
            "found": False,
            "rows": [],
            "header": [],
            "errors": ["EVALUATION DATA CSV marker is absent"],
            "marker_count": 0,
        }
    start = marker_positions[-1] + 1
    end = len(lines)
    for index in range(start, len(lines)):
        if lines[index].strip() == SUMMARY_MARKER:
            end = index
            break
    block_lines = [
        line
        for line in lines[start:end]
        if line.strip() and re.fullmatch(r"=+", line.strip()) is None
    ]
    if not block_lines:
        return {
            "found": True,
            "rows": [],
            "header": [],
            "errors": ["EVALUATION DATA CSV block is empty"],
            "marker_count": len(marker_positions),
        }
    errors: List[str] = []
    try:
        parsed = list(csv.reader(io.StringIO("\n".join(block_lines))))
    except csv.Error as exc:
        return {
            "found": True,
            "rows": [],
            "header": [],
            "errors": ["CSV parse error: " + str(exc)],
            "marker_count": len(marker_positions),
        }
    header = parsed[0]
    if "metric_key" not in header or "value" not in header:
        errors.append("CSV header lacks metric_key or value")
    rows: List[Dict[str, str]] = []
    for row_number, values in enumerate(parsed[1:], start=2):
        if len(values) != len(header):
            errors.append(
                "CSV row %d has %d columns; expected %d"
                % (row_number, len(values), len(header))
            )
            if len(values) < len(header):
                values = values + [""] * (len(header) - len(values))
            else:
                values = values[: len(header)]
        rows.append(dict(zip(header, values)))
    if len(marker_positions) > 1:
        errors.append(
            "Multiple EVALUATION DATA CSV blocks found; the final block was used"
        )
    return {
        "found": True,
        "rows": rows,
        "header": header,
        "errors": errors,
        "marker_count": len(marker_positions),
    }


def parse_evaluation_file(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {
            "found": False,
            "rows": [],
            "header": [],
            "errors": ["Output file is absent"],
            "marker_count": 0,
        }
    return parse_evaluation_csv(
        path.read_text(encoding="utf-8", errors="replace")
    )


def output_summary(parsed: Mapping[str, Any]) -> Dict[str, str]:
    rows = list(parsed.get("rows", []))
    summary: Dict[str, str] = {
        "evaluation_mode": "",
        "evaluation_result": "",
        "solver_status": "",
        "verification_status": "",
        "run_verified": "",
        "evaluation_failure_reason": "",
    }
    if rows:
        last = rows[-1]
        summary.update(
            {
                "evaluation_mode": last.get("mode", ""),
                "evaluation_result": last.get("result", ""),
                "solver_status": last.get("solver_status", ""),
                "verification_status": last.get("verification_status", ""),
                "run_verified": last.get("run_verified", ""),
                "evaluation_failure_reason": last.get("failure_reason", ""),
            }
        )
    values: Dict[str, str] = {}
    duplicates: Dict[str, int] = {}
    for row in rows:
        key = row.get("metric_key", "")
        if not key:
            continue
        if key in values:
            duplicates[key] = duplicates.get(key, 1) + 1
        values[key] = row.get("value", "")
    candidates = {
        "solver_time_ms": [
            "revised_solve_and_internal_check_time",
            "otf_dcs_update_controller_synthesis_time",
            "traditional_solve_control_problem_total_time",
        ],
        "states_discovered": ["revised_semantic_states_discovered"],
        "states_expanded": ["revised_semantic_states_expanded"],
        "successor_queries": ["revised_successor_oracle_calls_cumulative"],
        "transition_outcomes": [
            "revised_materialized_transition_outcomes_cumulative"
        ],
        "initial_endpoint_embeddings": [
            "revised_initial_endpoint_embeddings"
        ],
        "certificate_states": ["revised_certificate_states"],
        "losing_region_states": ["revised_losing_region_states"],
        "losing_region_phase_masks": [
            "revised_losing_region_phase_masks"
        ],
        "internal_certificate_check": ["revised_internal_certificate_check"],
        "independent_verification_basis": [
            "revised_independent_verification_basis"
        ],
        "link_checker": ["revised_link_checker"],
        "output_controller_states": ["revised_output_controller_states"],
        "output_controller_transitions": [
            "revised_output_controller_transitions"
        ],
        "revised_decision": ["revised_decision"],
        "guided_fallback": ["revised_guided_fallback_used"],
        "early_success": ["revised_early_success"],
    }
    for output_name, keys in candidates.items():
        summary[output_name] = next(
            (values[key] for key in keys if key in values), ""
        )
    summary["duplicate_metric_keys"] = canonical_json(duplicates) if duplicates else ""
    return summary


def status_from_exit(
    exit_code: Optional[int],
    timed_out: bool,
    stderr_text: str,
    spawn_error: str = "",
) -> str:
    if spawn_error:
        return "SPAWN_ERROR"
    if timed_out:
        return "TIMEOUT"
    lowered = stderr_text.lower()
    if exit_code == 5 or "outofmemoryerror" in lowered or "cannot allocate memory" in lowered:
        return "OOM"
    mapping = {
        0: "SUCCESS",
        2: "NO_COMPOSITION",
        3: "NO_TRANSITION_OUTPUT",
        4: "CRASH",
        6: "UNREALIZABLE",
        7: "INVALID_CERTIFICATE",
        8: "INVALID_INPUT",
        9: "VERIFICATION_INCONCLUSIVE",
        64: "USAGE_ERROR",
    }
    if exit_code in mapping:
        return mapping[exit_code]
    if exit_code is None:
        return "INCOMPLETE"
    if exit_code < 0:
        return "SIGNALLED"
    return "UNKNOWN_EXIT"


def csv_write(path: Path, fieldnames: Sequence[str], rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(fieldnames), extrasaction="ignore"
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: canonical_json(value)
                    if isinstance(value, (list, dict))
                    else value
                    for key, value in row.items()
                }
            )
