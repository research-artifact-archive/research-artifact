#!/usr/bin/env python3
"""Fail-closed audit of the registered source-native factorization evidence.

The audit authenticates the frozen ordinary-LTS population, every recorded
panel file, and the three focused ProductionCell bundles.  It then invokes the
non-importing *structural* bundle checker.  It does not independently replay
ordinary-LTS semantics; the Java source-to-bundle producer remains the TCB.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from check_native_refined_bundle import BundleError, check as structural_check, load as load_bundle


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "protocols/native_factorization_panel_v1_20260814.json"
PANEL = ROOT / "evidence/m8q-native-factorization/panel"
FOCUSED = ROOT / "evidence/m8q-native-factorization/results"
BASELINE = ROOT / "evidence/m8q-native-factorization/legacy-productioncell-baseline.json"
BASELINE_ROW_KEYS = {
    "certificate_states", "classpath_sha256", "config_sha256",
    "elapsed_monotonic_seconds", "independent_verification_basis",
    "input_sha256", "internal_certificate_check", "job_id", "link_checker",
    "method_id", "model_id", "peak_rss_bytes", "plan_sha256",
    "process_status", "repetition", "revised_decision", "run_verified",
    "solver_status", "solver_time_ms", "states_discovered", "states_expanded",
    "successor_queries", "target_id", "timed_out", "transition_outcomes",
    "verification_status",
}


class AuditError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key: " + key)
            result[key] = value
        return result

    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
            object_pairs_hook=unique_object,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise AuditError(f"invalid strict JSON: {path.relative_to(ROOT)}") from error
    require(isinstance(value, dict), f"JSON root is not an object: {path.relative_to(ROOT)}")
    return value


def canonical(value: Any) -> bytes:
    try:
        return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
    except (TypeError, ValueError) as error:
        raise AuditError("non-canonical JSON value") from error


def safe_relative(value: Any, label: str) -> PurePosixPath:
    require(isinstance(value, str) and value, f"{label} is not text")
    path = PurePosixPath(value)
    require(not path.is_absolute() and ".." not in path.parts and value == path.as_posix(), f"unsafe {label}")
    return path


def slug(value: str) -> str:
    import re

    result = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    require(bool(result), "empty case ID")
    return result


def terminal_fields(payload: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in payload.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        require(key and key not in result, "duplicate terminal stdout field")
        result[key] = value
    return result


def positive_integer_text(value: Any, label: str) -> int:
    require(isinstance(value, str) and value.isdigit() and int(value) > 0, f"{label} is not a positive integer string")
    return int(value)


def positive_float_text(value: Any, label: str) -> float:
    require(isinstance(value, str), f"{label} is not a numeric string")
    try:
        observed = float(value)
    except ValueError as error:
        raise AuditError(f"{label} is not a numeric string") from error
    require(math.isfinite(observed) and observed > 0.0, f"{label} is not a positive finite number")
    return observed


def expand_protocol(protocol: Mapping[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    sources = protocol.get("sources")
    require(isinstance(sources, list), "protocol sources are absent")
    for entry in sources:
        require(isinstance(entry, dict), "protocol source is not an object")
        cluster = entry.get("cluster")
        require(isinstance(cluster, str) and cluster, "protocol cluster is invalid")
        if "instances" in entry:
            instances = entry.get("instances")
            require(isinstance(instances, list), "protocol instances are invalid")
            for instance in instances:
                require(isinstance(instance, dict), "protocol instance is invalid")
                source_path = str(entry["path_prefix"]) + str(instance["file"])
                condition = f"{entry['condition']}-{Path(str(instance['file'])).stem}"
                rows.append({
                    "case_id": slug(f"{cluster}-{condition}"),
                    "path": source_path,
                    "sha256": str(instance["sha256"]),
                    "cluster": cluster,
                    "condition": condition,
                    "definition": str(entry["definition"]),
                    "alias": str(entry["alias"]),
                    "hypothesis": str(entry["hypothesis"]),
                })
        else:
            targets = entry.get("targets")
            require(isinstance(targets, list), "protocol targets are invalid")
            for target in targets:
                require(isinstance(target, dict), "protocol target is invalid")
                source_path = str(entry["path"])
                condition = str(target["condition"])
                rows.append({
                    "case_id": slug(f"{cluster}-{condition}-{Path(source_path).stem}"),
                    "path": source_path,
                    "sha256": str(entry["sha256"]),
                    "cluster": cluster,
                    "condition": condition,
                    "definition": str(target["definition"]),
                    "alias": str(target["alias"]),
                    "hypothesis": str(target["hypothesis"]),
                })
    denominator = protocol.get("denominator")
    require(isinstance(denominator, dict), "protocol denominator is absent")
    require(len(rows) == denominator.get("target_cells") == 41, "protocol cell denominator differs")
    require(len({row["path"] for row in rows}) == denominator.get("source_files") == 23, "protocol source denominator differs")
    require(len({row["cluster"] for row in rows}) == denominator.get("provenance_clusters") == 10, "protocol cluster denominator differs")
    require(len({row["case_id"] for row in rows}) == len(rows), "protocol case IDs are not unique")
    require(
        Counter(row["hypothesis"] for row in rows)
        == Counter({"NONTRIVIAL_REFINED_CANDIDATE": 2, "TRIVIAL_ONE_COMPONENT": 6, "EXPECTED_COUPLED_OR_NONFACTOR": 33}),
        "protocol hypothesis denominator differs",
    )
    return rows


def verify_sources(rows: list[dict[str, str]]) -> None:
    checked: set[str] = set()
    for row in rows:
        if row["path"] in checked:
            continue
        relative = safe_relative(row["path"], "source path")
        path = ROOT / relative
        require(path.is_file() and not path.is_symlink(), f"registered source is absent: {relative}")
        require(sha256(path) == row["sha256"], f"registered source hash differs: {relative}")
        checked.add(row["path"])


def verify_public_producer_sources(protocol: Mapping[str, Any]) -> None:
    runtime = protocol["runtime"]
    expected = {
        "source-rebuild/added/maven-root/mtsa/src/main/java/ltsa/lts/NativeUpdatingContractLoader.java": "c01d1471a64002e5540ba2525087e22c39fbf8d89cda44e99c82775e319371c6",
        "source-rebuild/added/maven-root/mtsa/src/main/java/ltsa/updatingControllers/otf/NativeTierAFactorizer.java": runtime["factorizer_sha256"],
        "source-rebuild/added/maven-root/mtsa/src/main/java/ltsa/updatingControllers/otf/NativeTierABundleExporter.java": runtime["exporter_sha256"],
        "source-rebuild/added/maven-root/mtsa/src/main/java/ltsa/updatingControllers/cli/NativePartitionRunner.java": runtime["runner_sha256"],
        "source-rebuild/added/maven-root/mtsa/src/main/java/ltsa/updatingControllers/otf/MtsaRevisedOtfDucsAdapter.java": "c8cdf1da8545bb79619ee436d72fc36fa4c7c099779defbbee751551ad7b23b4",
    }
    for relative, digest in expected.items():
        path = ROOT / relative
        require(path.is_file() and not path.is_symlink(), f"public producer source is absent: {relative}")
        require(sha256(path) == digest, f"public producer source hash differs: {relative}")


def verify_panel(rows: list[dict[str, str]], protocol: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    summary = read_json(PANEL / "summary.json")
    require(summary.get("schema_version") == "fg-ducs-native-factorization-panel-summary-v1", "panel schema differs")
    require(summary.get("protocol_sha256") == sha256(PROTOCOL), "panel protocol binding differs")
    require(summary.get("jar_sha256") == protocol["runtime"]["jar_sha256"], "panel JAR binding differs")
    require(summary.get("source_files") == 23 and summary.get("target_cells") == 41 and summary.get("provenance_clusters") == 10, "panel denominator differs")
    records = summary.get("records")
    require(isinstance(records, list) and len(records) == 41, "panel record denominator differs")
    by_id: dict[str, dict[str, Any]] = {}
    expected = {row["case_id"]: row for row in rows}
    for record in records:
        require(isinstance(record, dict), "panel record is not an object")
        case_id = record.get("case_id")
        require(isinstance(case_id, str) and case_id in expected and case_id not in by_id, "panel case ID differs")
        row = expected[case_id]
        for field in ("path", "sha256", "cluster", "condition", "definition", "alias", "hypothesis"):
            require(record.get(field) == row[field], f"panel registration field differs: {case_id}.{field}")
        case_dir = PANEL / "cases" / case_id
        require(case_dir.is_dir() and not case_dir.is_symlink(), f"panel case directory is absent: {case_id}")
        require(sha256(case_dir / "stdout.txt") == record.get("stdout_sha256"), f"panel stdout hash differs: {case_id}")
        require(sha256(case_dir / "stderr.txt") == record.get("stderr_sha256"), f"panel stderr hash differs: {case_id}")
        require(canonical(read_json(case_dir / "record.json")) == canonical(record), f"panel record file differs: {case_id}")
        status = record.get("process_status")
        if status == "SUCCESS":
            require(type(record.get("exit_code")) is int and record["exit_code"] == 0, f"successful panel exit code differs: {case_id}")
            require(record.get("timed_out") is False, f"successful panel row is marked timed out: {case_id}")
            require(type(record.get("producer_elapsed_nanos")) is int and record["producer_elapsed_nanos"] > 0, f"successful producer elapsed time differs: {case_id}")
            require(type(record.get("wall_nanos")) is int and record["wall_nanos"] >= record["producer_elapsed_nanos"], f"successful panel wall time differs: {case_id}")
            require(type(record.get("max_rss_bytes")) is int and record["max_rss_bytes"] > 0, f"successful panel RSS differs: {case_id}")
            bundle_relative = safe_relative(record.get("bundle_path"), "bundle path")
            require(bundle_relative == PurePosixPath("cases") / case_id / "bundle.json", f"panel bundle path differs: {case_id}")
            bundle_path = PANEL / bundle_relative
            require(bundle_path.is_file() and sha256(bundle_path) == record.get("bundle_sha256"), f"panel bundle hash differs: {case_id}")
            require(bundle_path.stat().st_size == record.get("bundle_bytes"), f"panel bundle size differs: {case_id}")
            bundle = load_bundle(bundle_path)
            require(bundle.get("source_name") == Path(row["path"]).name, f"panel bundle source name differs: {case_id}")
            require(bundle.get("source_sha256") == row["sha256"] and bundle.get("definition") == row["definition"], f"panel bundle source binding differs: {case_id}")
            require(record.get("factor_status") == bundle.get("factor_status"), f"panel factor status differs from bundle: {case_id}")
            require(record.get("solve_status") == bundle.get("solve_status"), f"panel solve status differs from bundle: {case_id}")
            require(record.get("terminal_product_verified") is bundle.get("terminal_product_verified"), f"panel terminal status differs from bundle: {case_id}")
            require(record.get("block_count") == len(bundle.get("component_partition", [])), f"panel block count differs from bundle: {case_id}")
            stdout = (case_dir / "stdout.txt").read_text(encoding="utf-8")
            terminal = terminal_fields(stdout)
            expected_terminal = {
                "source_sha256": row["sha256"],
                "definition": row["definition"],
                "factor_status": str(bundle.get("factor_status")),
                "solve_status": str(bundle.get("solve_status")),
                "block_count": str(len(bundle.get("component_partition", []))),
                "terminal_product_verified": str(bundle.get("terminal_product_verified")).lower(),
                "elapsed_nanos": str(record.get("producer_elapsed_nanos")),
                "terminal_record": "COMPLETE",
            }
            require(terminal == expected_terminal, f"panel terminal stdout differs: {case_id}")
            stderr = (case_dir / "stderr.txt").read_text(encoding="utf-8")
            rss_match = re.search(r"^\s*(\d+)\s+maximum resident set size\s*$", stderr, re.MULTILINE)
            require(rss_match is not None and int(rss_match.group(1)) == record["max_rss_bytes"], f"panel RSS diagnostic differs: {case_id}")
            try:
                observed = structural_check(bundle)
            except BundleError as error:
                raise AuditError(f"panel structural check failed: {case_id}: {error}") from error
            require(record.get("consumer_status") == "PASS" and canonical(record.get("consumer_report")) == canonical(observed), f"panel structural report differs: {case_id}")
        else:
            require(status == "INVALID_OR_INCONCLUSIVE", f"unexpected panel process status: {case_id}")
            require(type(record.get("exit_code")) is int and record["exit_code"] == 2, f"inconclusive panel exit code differs: {case_id}")
            require(record.get("timed_out") is False, f"inconclusive panel row is marked timed out: {case_id}")
            require(record.get("bundle_path") is None and record.get("bundle_sha256") is None and record.get("consumer_status") == "NOT_RUN", f"inconclusive panel record retains a result: {case_id}")
            require(record.get("factor_status") is None and record.get("solve_status") is None and record.get("terminal_product_verified") is None, f"inconclusive panel row retains a decision: {case_id}")
            stderr = (case_dir / "stderr.txt").read_text(encoding="utf-8")
            expected_event = "des64" if row["cluster"] == "metasocket" else "procedure"
            expected_diagnostic = (
                "NATIVE_FACTOR_INVALID=ownerless normal event is not a disable-able "
                f"pure stutter: {expected_event}"
            )
            diagnostic_lines = [line for line in stderr.splitlines() if line.startswith("NATIVE_FACTOR_INVALID=")]
            require(diagnostic_lines == [expected_diagnostic], f"inconclusive panel diagnostic differs: {case_id}")
        by_id[case_id] = record

    require(set(by_id) == set(expected), "panel case set differs")
    process_counts = Counter(record["process_status"] for record in records)
    factor_counts = Counter(record.get("factor_status") or "NO_RESULT" for record in records)
    solve_counts = Counter(record.get("solve_status") or "NO_RESULT" for record in records)
    consumer_counts = Counter(record["consumer_status"] for record in records)
    require(process_counts == Counter({"SUCCESS": 35, "INVALID_OR_INCONCLUSIVE": 6}), "panel process census differs")
    require(factor_counts == Counter({"TRIVIAL_ONE_BLOCK": 33, "NONTRIVIAL_SOURCE_NATIVE": 2, "NO_RESULT": 6}), "panel factor census differs")
    require(solve_counts == Counter({"NOT_RUN": 33, "PRODUCER_VERIFIED_REFINED_WIN": 2, "NO_RESULT": 6}), "panel solve census differs")
    require(consumer_counts == Counter({"PASS": 35, "NOT_RUN": 6}), "panel structural-consumer census differs")
    for key, observed in (
        ("process_status_counts", process_counts),
        ("factor_status_counts", factor_counts),
        ("solve_status_counts", solve_counts),
        ("consumer_status_counts", consumer_counts),
    ):
        require(summary.get(key) == dict(sorted(observed.items())), f"panel summary {key} differs")
    refined = {case_id for case_id, record in by_id.items() if record.get("solve_status") == "PRODUCER_VERIFIED_REFINED_WIN"}
    require(refined == {"productioncell-arms2-base-productioncell-arms-2-fg", "productioncell-arms2-r2-productioncell-arms-2-fg"}, "panel refined-WIN case set differs")
    inconclusive = {case_id for case_id, record in by_id.items() if record["process_status"] == "INVALID_OR_INCONCLUSIVE"}
    require(inconclusive == {f"{family}-{condition}-{family}-fg" for family in ("metasocket", "powerplant") for condition in ("base", "r1", "r2")}, "panel inconclusive case set differs")
    return summary, by_id


def verify_focused() -> dict[str, Any]:
    expected = {
        "productioncell-arms2-base.json": ("UpdCont_OTF_FG", "NONTRIVIAL_SOURCE_NATIVE", "PRODUCER_VERIFIED_REFINED_WIN"),
        "productioncell-arms2-r1.json": ("UpdCont_OTF_FG_R1", "TRIVIAL_ONE_BLOCK", "NOT_RUN"),
        "productioncell-arms2-r2.json": ("UpdCont_OTF_FG_R2", "NONTRIVIAL_SOURCE_NATIVE", "PRODUCER_VERIFIED_REFINED_WIN"),
    }
    reports: dict[str, Any] = {}
    for name, (definition, factor, solve) in expected.items():
        path = FOCUSED / name
        bundle = load_bundle(path)
        require(bundle.get("source_name") == "ProductionCell_Arms=2_FG.lts" and bundle.get("source_sha256") == "117210fa93185f5a814ad7debbdfcde00720019312c4ef68446a844700084e43", f"focused source binding differs: {name}")
        require(bundle.get("definition") == definition and bundle.get("factor_status") == factor and bundle.get("solve_status") == solve, f"focused decision differs: {name}")
        try:
            report = structural_check(bundle)
        except BundleError as error:
            raise AuditError(f"focused structural check failed: {name}: {error}") from error
        reports[name] = {
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
            "structural_report": report,
            "local_solver_sums": {
                "states": bundle["local_solver_discovered_states_sum"],
                "queries": bundle["local_solver_successor_queries_sum"],
                "outcomes": bundle["local_solver_outcomes_sum"],
            },
        }
    return reports


def verify_baseline() -> dict[str, Any]:
    baseline = read_json(BASELINE)
    require(baseline.get("schema_version") == "fg-ducs-native-legacy-baseline-projection-v1", "legacy baseline schema differs")
    require(baseline.get("private_source_hash_omitted") is True, "legacy private source boundary differs")
    rows = baseline.get("rows")
    require(isinstance(rows, list) and len(rows) == 6, "legacy baseline row denominator differs")
    keyed: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        require(isinstance(row, dict), "legacy baseline row is invalid")
        require(set(row) == BASELINE_ROW_KEYS, "legacy baseline row fields differ")
        key = (row.get("target_id"), row.get("method_id"))
        require(key not in keyed and key[0] in {"base", "r1", "r2"} and key[1] in {"fg_ducs_otf", "direct_full"}, "legacy baseline key differs")
        require(row.get("input_sha256") == "117210fa93185f5a814ad7debbdfcde00720019312c4ef68446a844700084e43", "legacy baseline input binding differs")
        require(row.get("model_id") == "productioncell_arms2" and row.get("repetition") == "1", "legacy baseline identity differs")
        require(row.get("job_id") == f"productioncell_arms2__{key[0]}__rep01__{key[1]}", "legacy baseline job ID differs")
        require(row.get("classpath_sha256") == "b51ada39df37d8eace01d587a778e6f02d38922012efc9f67b935c68467b5daf", "legacy baseline classpath binding differs")
        require(row.get("config_sha256") == "99d8602f7418c333aeebff0fb1bc58d62786c41055187941cfba242aa1596cbd", "legacy baseline config binding differs")
        require(row.get("plan_sha256") == "cc5435bc0217e520c3aa32b2a68bbf0dab6c11bb6553b82d1794ef2f556fb206", "legacy baseline plan binding differs")
        elapsed = positive_float_text(row.get("elapsed_monotonic_seconds"), "legacy elapsed time")
        positive_integer_text(row.get("peak_rss_bytes"), "legacy peak RSS")
        status = row.get("process_status")
        require(status in {"SUCCESS", "TIMEOUT"}, "legacy baseline process status differs")
        if status == "TIMEOUT":
            require(row.get("timed_out") == "True" and 120.0 <= elapsed < 130.0, "legacy timeout timing differs")
            for field in (
                "certificate_states", "independent_verification_basis", "internal_certificate_check",
                "link_checker", "revised_decision", "run_verified", "solver_status",
                "solver_time_ms", "states_discovered", "states_expanded", "successor_queries",
                "transition_outcomes", "verification_status",
            ):
                require(row.get(field) == "", f"legacy timeout retains result field: {field}")
        else:
            require(row.get("timed_out") == "False" and elapsed < 120.0, "legacy success timing differs")
            require(row.get("revised_decision") == row.get("solver_status") == "realizable", "legacy success decision differs")
            require(row.get("run_verified") == "true" and row.get("verification_status") == "verified", "legacy success verification differs")
            require(row.get("internal_certificate_check") == "passed" and row.get("link_checker") == "passed", "legacy success certificate binding differs")
            require(row.get("independent_verification_basis") == "independent_certificate_proof", "legacy success proof basis differs")
            positive_float_text(row.get("solver_time_ms"), "legacy solver time")
            for field in ("certificate_states", "states_discovered", "states_expanded", "successor_queries", "transition_outcomes"):
                positive_integer_text(row.get(field), f"legacy {field}")
        keyed[key] = row
    require(len(keyed) == 6, "legacy baseline matrix differs")
    require(keyed[("base", "fg_ducs_otf")]["process_status"] == "SUCCESS" and keyed[("base", "direct_full")]["process_status"] == "TIMEOUT", "legacy base observation differs")
    require(keyed[("r1", "fg_ducs_otf")]["process_status"] == "SUCCESS" and keyed[("r1", "direct_full")]["process_status"] == "TIMEOUT", "legacy R1 observation differs")
    require(keyed[("r2", "fg_ducs_otf")]["process_status"] == "TIMEOUT" and keyed[("r2", "direct_full")]["process_status"] == "TIMEOUT", "legacy R2 timeout observation differs")
    return {"rows": 6, "r2_monolithic_timeouts": 2}


def audit() -> dict[str, Any]:
    protocol = read_json(PROTOCOL)
    require(protocol.get("schema_version") == "fg-ducs-native-factorization-panel-v1", "native protocol schema differs")
    require(protocol.get("registration_kind") == "post_outcome_denominator_freeze" and protocol.get("prospective_or_heldout_claim") is False, "native registration boundary differs")
    rows = expand_protocol(protocol)
    verify_sources(rows)
    verify_public_producer_sources(protocol)
    _, records = verify_panel(rows, protocol)
    focused = verify_focused()
    baseline = verify_baseline()
    refined_records = [record for record in records.values() if record.get("solve_status") == "PRODUCER_VERIFIED_REFINED_WIN"]
    refined_metrics: dict[str, dict[str, int]] = {}
    for label, case_id, focused_name in (
        ("arms2-base", "productioncell-arms2-base-productioncell-arms-2-fg", "productioncell-arms2-base.json"),
        ("arms2-r2", "productioncell-arms2-r2-productioncell-arms-2-fg", "productioncell-arms2-r2.json"),
    ):
        record = records[case_id]
        panel_bundle = load_bundle(PANEL / safe_relative(record["bundle_path"], "bundle path"))
        panel_metrics = {
            "states": panel_bundle["local_solver_discovered_states_sum"],
            "queries": panel_bundle["local_solver_successor_queries_sum"],
            "outcomes": panel_bundle["local_solver_outcomes_sum"],
        }
        require(panel_metrics == focused[focused_name]["local_solver_sums"], f"focused/panel local metrics differ: {label}")
        refined_metrics[label] = panel_metrics
    require(
        refined_metrics
        == {
            "arms2-base": {"states": 172, "queries": 1734, "outcomes": 272},
            "arms2-r2": {"states": 127174, "queries": 831356, "outcomes": 294632},
        },
        "refined local-solver metrics differ",
    )
    return {
        "schema_version": "fg-ducs-native-factorization-audit-v1",
        "status": "PASS",
        "claim_boundary": "producer-verified one-way sufficient WIN; structural bundle consistency; ordinary-LTS-to-bundle producer remains TCB",
        "registration": "post-outcome outcome-complete denominator freeze; not prospective or held out",
        "registered_bindings": {
            "protocol_sha256": sha256(PROTOCOL),
            "panel_summary_sha256": sha256(PANEL / "summary.json"),
            "structural_checker_sha256": sha256(ROOT / "analysis/check_native_refined_bundle.py"),
            "panel_runner_sha256": sha256(ROOT / "analysis/run_native_factorization_panel.py"),
            "producer_jar_sha256": protocol["runtime"]["jar_sha256"],
            "factorizer_source_sha256": protocol["runtime"]["factorizer_sha256"],
            "exporter_source_sha256": protocol["runtime"]["exporter_sha256"],
            "runner_source_sha256": protocol["runtime"]["runner_sha256"],
        },
        "source_files": 23,
        "target_cells": 41,
        "provenance_clusters": 10,
        "successful_cells": 35,
        "invalid_or_inconclusive_cells": 6,
        "trivial_one_block_cells": 33,
        "producer_verified_refined_win_cells": 2,
        "producer_verified_refined_win_clusters": 1,
        "structurally_checked_bundles": 35,
        "focused_results": focused,
        "refined_local_solver_sums": refined_metrics,
        "legacy_baseline": baseline,
        "refined_wall_seconds": {record["condition"]: record["wall_nanos"] / 1_000_000_000 for record in refined_records},
        "refined_max_rss_bytes": {record["condition"]: record["max_rss_bytes"] for record in refined_records},
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        report = audit()
        payload = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
        if args.output is None:
            print(payload, end="")
        else:
            args.output.write_text(payload, encoding="utf-8")
            print(json.dumps({"status": "PASS", "output": str(args.output)}))
        return 0
    except (AuditError, BundleError, OSError, UnicodeDecodeError, ValueError) as error:
        print(f"NATIVE_AUDIT_INVALID={error}", file=__import__("sys").stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
