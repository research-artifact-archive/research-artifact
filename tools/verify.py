#!/usr/bin/env python3
"""Verify the publishable FG-DUCS artifact without external dependencies."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
CHECKSUM_RE = re.compile(r"^(?P<digest>[0-9a-f]{64})  (?P<path>.+)$")
FORBIDDEN_PATH_PARTS = {".git", "backup", "__pycache__", ".DS_Store"}
PRIVATE_HASH_TOKEN = "<PRIVATE_PRE_SANITIZATION_HASH_OMITTED>"
GENERIC_SECRET_PATTERNS = (
    re.compile(rb"AKIA[0-9A-Z]{16}"),
    re.compile(rb"gh[pousr]_[A-Za-z0-9_]{20,}"),
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"(?:/" + rb"Users/|/" + rb"home/|[A-Za-z]:\\" + rb"Users\\)"),
    re.compile(rb"turn-[0-9a-f]{8}"),
)
TEXT_SUFFIXES = {
    "", ".cff", ".csv", ".java", ".json", ".lts", ".md", ".patch", ".prism", ".ps1", ".py",
    ".sh", ".txt", ".xml", ".yaml", ".yml",
}


class VerificationError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def payload_files() -> list[Path]:
    result = []
    for path in sorted(ROOT.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(ROOT)
        if any(part in FORBIDDEN_PATH_PARTS for part in relative.parts):
            continue
        if path.is_symlink():
            raise VerificationError(f"symlink is forbidden: {relative}")
        if path.is_file() and relative.as_posix() != "SHA256SUMS":
            result.append(path)
    return result


def parse_checksums() -> dict[str, str]:
    path = ROOT / "SHA256SUMS"
    if not path.is_file() or path.is_symlink():
        raise VerificationError("SHA256SUMS is missing")
    declared: dict[str, str] = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        match = CHECKSUM_RE.fullmatch(line)
        if match is None:
            raise VerificationError(f"invalid SHA256SUMS line {number}")
        relative = PurePosixPath(match.group("path"))
        text = relative.as_posix()
        if relative.is_absolute() or ".." in relative.parts or text.startswith("./"):
            raise VerificationError(f"unsafe checksum path: {text}")
        if text in declared:
            raise VerificationError(f"duplicate checksum path: {text}")
        declared[text] = match.group("digest")
    return declared


def verify_checksums() -> int:
    declared = parse_checksums()
    files = payload_files()
    actual = {path.relative_to(ROOT).as_posix(): sha256_file(path) for path in files}
    if declared != actual:
        missing = sorted(set(actual) - set(declared))
        absent = sorted(set(declared) - set(actual))
        changed = sorted(path for path in set(actual) & set(declared) if actual[path] != declared[path])
        raise VerificationError(
            f"checksum mismatch: unlisted={missing}, missing={absent}, changed={changed}"
        )
    return len(files)


def scan() -> int:
    scanned = 0
    for path in payload_files():
        relative = path.relative_to(ROOT)
        if path.stat().st_size >= 100_000_000:
            raise VerificationError(f"file reaches GitHub hard limit: {relative}")
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        payload = path.read_bytes()
        for pattern in GENERIC_SECRET_PATTERNS:
            if pattern.search(payload):
                raise VerificationError(f"generic anonymity/secret pattern in {relative}")
        scanned += 1
    return scanned


def load_json(relative: str) -> dict[str, Any]:
    path = ROOT / relative
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise VerificationError(f"invalid JSON: {relative}") from error
    if not isinstance(value, dict):
        raise VerificationError(f"JSON root is not an object: {relative}")
    return value


def exact_integer(value: Any, expected: int) -> bool:
    return type(value) is int and value == expected


def nested(value: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = value
    for key in path:
        if isinstance(current, dict) and key in current:
            current = current[key]
        elif isinstance(current, list) and key.isdigit() and int(key) < len(current):
            current = current[int(key)]
        else:
            raise VerificationError(f"missing public-projection field: {'.'.join(path)}")
    return current


def scalar_paths(value: Any, prefix: tuple[str, ...] = ()) -> list[tuple[tuple[str, ...], Any]]:
    if isinstance(value, dict):
        result: list[tuple[tuple[str, ...], Any]] = []
        for key, child in value.items():
            result.extend(scalar_paths(child, prefix + (str(key),)))
        return result
    if isinstance(value, list):
        result = []
        for index, child in enumerate(value):
            result.extend(scalar_paths(child, prefix + (str(index),)))
        return result
    return [(prefix, value)]


def verify_public_hash_projection() -> None:
    """Reject private pre-sanitization hash crosswalks in public metadata."""
    forbidden_names = {"ORIGINAL_SHA256SUMS", "REGISTERED_SOURCE_SHA256SUMS"}
    leaked = sorted(
        path.relative_to(ROOT).as_posix()
        for path in payload_files()
        if path.name in forbidden_names
    )
    if leaked:
        raise VerificationError(f"private hash inventory is public: {leaked}")

    bindings = (
        ("evidence/m8k-correctness/generic_lazy_audit.json", ("raw_runs_sha256",), "evidence/m8k-correctness/raw_runs.csv"),
        ("evidence/m8k-correctness/independent_raw_oracle.json", ("java_runs_sha256",), "evidence/m8k-correctness/raw_runs.csv"),
        ("evidence/m8k-performance/generic_lazy_audit.json", ("raw_runs_sha256",), "evidence/m8k-performance/raw_runs.csv"),
        ("evidence/m8o-block-decomposition/summary.json", ("input_files", "m8k_raw"), "evidence/m8k-performance/raw_runs.csv"),
        ("evidence/m8o-block-decomposition/summary.json", ("input_files", "legacy_raw"), "evidence/m8o-block-decomposition/legacy-direct-full-raw.csv"),
        ("evidence/m8o-block-decomposition/summary.json", ("input_files", "multistate_games"), "inputs/c2/factored-multistate-games.json"),
        ("evidence/m8p-partition-discovery/summary.json", ("fixture_sha256",), "inputs/c2/typed-partition-fixtures.json"),
        ("evidence/m8p-partition-discovery/partition-certificates.json", ("fixture_sha256",), "inputs/c2/typed-partition-fixtures.json"),
        ("evidence/m8p-partition-discovery/coordinate-screen.json", ("input_summary_sha256",), "evidence/m8n-game-equivalence/summary.json"),
        ("evidence/m8p-partition-discovery/summary.json", ("protocol_sha256",), "protocols/typed_partition_discovery_v1_20260813.json"),
        ("protocols/typed_partition_discovery_v1_20260813.json", ("registered_files", "fixtures", "sha256"), "inputs/c2/typed-partition-fixtures.json"),
        ("protocols/typed_partition_discovery_v1_20260813.json", ("registered_files", "fixture_builder", "sha256"), "analysis/build_typed_partition_fixtures.py"),
        ("protocols/typed_partition_discovery_v1_20260813.json", ("registered_files", "producer", "sha256"), "analysis/discover_typed_partition.py"),
        ("protocols/typed_partition_discovery_v1_20260813.json", ("registered_files", "independent_consumer", "sha256"), "analysis/check_typed_partition_certificate.py"),
        ("protocols/typed_partition_discovery_v1_20260813.json", ("registered_files", "transport_producer", "sha256"), "analysis/synthesize_discovered_witness.py"),
        ("protocols/typed_partition_discovery_v1_20260813.json", ("registered_files", "independent_transport_consumer", "sha256"), "analysis/check_discovered_witness.py"),
        ("protocols/typed_partition_discovery_v1_20260813.json", ("registered_files", "audit_driver", "sha256"), "analysis/audit_typed_partition_discovery.py"),
        ("protocols/typed_partition_discovery_v1_20260813.json", ("registered_files", "coordinate_screen", "sha256"), "analysis/screen_complete_game_factorability.py"),
        ("protocols/m6-external-prism-v1.json", ("external_solver", "java_runs_sha256"), "evidence/m6-prism/java_runs.csv"),
        ("evidence/m6-prism/summary.json", ("java_runs_sha256",), "evidence/m6-prism/java_runs.csv"),
        ("protocols/prospective_ardrone_registration_v2j_20260811.json", ("observations_available_at_freeze", "original_campaign", "raw_runs_sha256"), "evidence/m8m-source-anchored/original-frozen/raw_runs.csv"),
        ("evidence/m8m-source-anchored/preexecution/summary.json", ("registration", "prior_prospective_evidence", "raw_runs_sha256"), "evidence/m8m-source-anchored/original-frozen/raw_runs.csv"),
        ("evidence/m8m-source-anchored/handoff/summary.json", ("decision_precondition", "raw_runs_sha256"), "evidence/m8m-source-anchored/raw_runs.csv"),
        ("evidence/m8m-source-anchored/final-audit/summary.json", ("campaign", "raw_runs_sha256"), "evidence/m8m-source-anchored/raw_runs.csv"),
        ("evidence/m8m-source-anchored/final-audit/summary.json", ("campaign", "handoff_precondition", "raw_runs_sha256"), "evidence/m8m-source-anchored/raw_runs.csv"),
        ("evidence/m8m-source-anchored/final-audit/summary.json", ("registration", "prior_prospective_evidence", "raw_runs_sha256"), "evidence/m8m-source-anchored/original-frozen/raw_runs.csv"),
        ("evidence/m8m-source-anchored/final-audit/summary.json", ("authorization", "sha256"), "evidence/m8m-source-anchored/preexecution/summary.json"),
        ("evidence/m8m-source-anchored/final-audit/summary.json", ("typed_handoff", "summary_sha256"), "evidence/m8m-source-anchored/handoff/summary.json"),
        ("evidence/m8n-game-equivalence/audit/summary.json", ("evidence_summary_sha256",), "evidence/m8n-game-equivalence/summary.json"),
    )
    for document, field, target in bindings:
        observed = nested(load_json(document), field)
        expected = sha256_file(ROOT / target)
        if observed != expected:
            raise VerificationError(
                f"public hash binding mismatch: {document}:{'.'.join(field)}"
            )

    omitted = {
        ("protocols/cross_frontend_game_equivalence_v1_20260811.json", ("m8m_external_checksums_sha256",)),
        ("evidence/m8m-source-anchored/preexecution/summary.json", ("registration", "prior_prospective_evidence", "campaign_checksums_sha256")),
        ("evidence/m8m-source-anchored/preexecution/summary.json", ("registration", "prior_prospective_evidence", "preexecution_checksums_sha256")),
        ("evidence/m8m-source-anchored/preexecution/summary.json", ("registration", "prior_prospective_evidence", "preexecution_summary_sha256")),
        ("evidence/m8m-source-anchored/final-audit/summary.json", ("campaign", "checksums", "sha256")),
        ("evidence/m8m-source-anchored/final-audit/summary.json", ("external_decision_checks", "checksums", "sha256")),
        ("evidence/m8m-source-anchored/final-audit/summary.json", ("registration", "prior_prospective_evidence", "campaign_checksums_sha256")),
        ("evidence/m8m-source-anchored/final-audit/summary.json", ("registration", "prior_prospective_evidence", "preexecution_checksums_sha256")),
        ("evidence/m8m-source-anchored/final-audit/summary.json", ("registration", "prior_prospective_evidence", "preexecution_summary_sha256")),
        ("evidence/m8m-source-anchored/final-audit/summary.json", ("typed_handoff", "checksums", "sha256")),
        ("evidence/m8n-game-equivalence/summary.json", ("m8m_external_seal", "sha256")),
        ("evidence/m8n-game-equivalence/audit/summary.json", ("evidence_checksums_sha256",)),
        ("evidence/m8m-source-anchored/preexecution/summary.json", ("registered_files", "retained_invalid_m8l_preflight", "sha256")),
        ("evidence/m8m-source-anchored/preexecution/summary.json", ("registered_files", "superseded_preflight_v2", "sha256")),
        ("evidence/m8m-source-anchored/preexecution/summary.json", ("registered_files", "superseded_preflight_v3", "sha256")),
        ("evidence/m8m-source-anchored/preexecution/summary.json", ("registered_files", "superseded_preflight_v4", "sha256")),
        ("evidence/m8m-source-anchored/final-audit/summary.json", ("pre_solver_validation", "retained_invalid_m8l_sha256")),
        ("evidence/m8m-source-anchored/final-audit/summary.json", ("pre_solver_validation", "superseded_v2_sha256")),
        ("evidence/m8m-source-anchored/final-audit/summary.json", ("pre_solver_validation", "superseded_v3_sha256")),
        ("evidence/m8m-source-anchored/final-audit/summary.json", ("pre_solver_validation", "superseded_v4_sha256")),
        ("evidence/m8m-source-anchored/final-audit/summary.json", ("registered_files", "retained_invalid_m8l_preflight", "sha256")),
        ("evidence/m8m-source-anchored/final-audit/summary.json", ("registered_files", "superseded_preflight_v2", "sha256")),
        ("evidence/m8m-source-anchored/final-audit/summary.json", ("registered_files", "superseded_preflight_v3", "sha256")),
        ("evidence/m8m-source-anchored/final-audit/summary.json", ("registered_files", "superseded_preflight_v4", "sha256")),
        ("evidence/m8m-source-anchored/preflight/summary.json", ("superseded_preflight_v4", "sha256")),
        ("evidence/m8m-source-anchored/preflight/summary.json", ("superseded_preflights", "0", "sha256")),
        ("evidence/m8m-source-anchored/preflight/summary.json", ("superseded_preflights", "1", "sha256")),
        ("evidence/m8m-source-anchored/preflight/summary.json", ("superseded_preflights", "2", "sha256")),
        ("protocols/prospective_ardrone_design_v2_20260810.json", ("design_history", "m8l_preflight_summary", "sha256")),
        ("protocols/prospective_ardrone_registration_v2j_20260811.json", ("registered_files", "retained_invalid_m8l_preflight", "sha256")),
        ("protocols/prospective_ardrone_registration_v2j_20260811.json", ("registered_files", "superseded_preflight_v2", "sha256")),
        ("protocols/prospective_ardrone_registration_v2j_20260811.json", ("registered_files", "superseded_preflight_v3", "sha256")),
        ("protocols/prospective_ardrone_registration_v2j_20260811.json", ("registered_files", "superseded_preflight_v4", "sha256")),
        ("protocols/prospective_ardrone_registration_v2j_20260811.json", ("observations_available_at_freeze", "original_preexecution_summary", "sha256")),
        ("protocols/prospective_ardrone_registration_v2j_20260811.json", ("observations_available_at_freeze", "original_preexecution_checksums", "sha256")),
        ("protocols/prospective_ardrone_registration_v2j_20260811.json", ("observations_available_at_freeze", "original_campaign", "checksums_sha256")),
        ("protocols/prospective_ardrone_registration_v2j_20260811.json", ("observations_available_at_freeze", "replay4", "campaign", "checksums_sha256")),
        ("protocols/prospective_ardrone_registration_v2j_20260811.json", ("observations_available_at_freeze", "replay4", "campaign", "raw_runs_sha256")),
        ("protocols/prospective_ardrone_registration_v2j_20260811.json", ("observations_available_at_freeze", "replay4", "external", "summary_sha256")),
        ("protocols/prospective_ardrone_registration_v2j_20260811.json", ("observations_available_at_freeze", "replay4", "external", "checksums_sha256")),
        ("protocols/prospective_ardrone_registration_v2j_20260811.json", ("observations_available_at_freeze", "replay4", "handoff", "summary_sha256")),
        ("protocols/prospective_ardrone_registration_v2j_20260811.json", ("observations_available_at_freeze", "replay4", "handoff", "checksums_sha256")),
    }
    for document, field in omitted:
        if nested(load_json(document), field) != PRIVATE_HASH_TOKEN:
            raise VerificationError(
                f"private pre-sanitization hash was not omitted: {document}:{'.'.join(field)}"
            )
    actual_omissions: set[tuple[str, tuple[str, ...]]] = set()
    for path in payload_files():
        if path.suffix != ".json":
            continue
        relative = path.relative_to(ROOT).as_posix()
        value = load_json(relative)
        actual_omissions.update(
            (relative, field)
            for field, scalar in scalar_paths(value)
            if scalar == PRIVATE_HASH_TOKEN
        )
    if actual_omissions != omitted:
        raise VerificationError(
            "public omission-marker allowlist drifted: "
            f"added={sorted(actual_omissions - omitted)}, removed={sorted(omitted - actual_omissions)}"
        )


def verify_science() -> None:
    verify_public_hash_projection()
    m8o = load_json("evidence/m8o-block-decomposition/summary.json")
    if m8o.get("status") != "PASS":
        raise VerificationError("M8o status is not PASS")
    independent = m8o.get("independent_family")
    negative = m8o.get("negative_control")
    if not isinstance(independent, dict) or not isinstance(negative, dict):
        raise VerificationError("M8o summary is incomplete")
    expected = {
        "conditions": 8,
        "m8k_jobs_passed": 80,
        "certificate_metric_cells_passed": 400,
        "direct_full_formula_jobs_passed": 35,
        "direct_full_k20_timeouts_retained": 5,
    }
    if any(independent.get(key) != value for key, value in expected.items()):
        raise VerificationError("M8o independent-family census mismatch")
    if negative.get("rejected_by_shared_nonstutter_screen") != 12:
        raise VerificationError("M8o negative-control census mismatch")
    if not (
        m8o.get("semantic_factor_conditions_independently_checked") is True
        and m8o.get("factored_certificates_independently_checked") is True
        and m8o.get("flat_products_independently_resolved") == 9
        and m8o.get("winning_priority_executions_checked") == 9
        and m8o.get("multistate_winning_cases") == 1
        and m8o.get("multistate_losing_cases") == 1
        and m8o.get("factor_mutations_rejected") == 21
        and independent.get("factored_winning_certificates_passed") == 8
        and independent.get("flat_product_cross_checks_passed") == 7
        and independent.get("k20_semantic_flat_states") == 2**20
        and independent.get("k20_factored_local_states") == 40
        and type(independent.get("k20_serialized_certificate_bytes")) is int
    ):
        raise VerificationError("M8o semantic-check boundary mismatch")

    c1 = load_json("evidence/m8k-correctness/independent_raw_oracle.json")
    if not (
        c1.get("model_count") == 41
        and c1.get("all_java_decisions_confirmed") is True
        and c1.get("all_registered_expectations_confirmed") is True
    ):
        raise VerificationError("M8k independent-oracle census mismatch")
    m8n = load_json("evidence/m8n-game-equivalence/summary.json")
    if not (
        m8n.get("status") == "PASS"
        and m8n.get("case_count") == 43
        and m8n.get("passed_cases") == 43
        and m8n.get("failed_cases") == 0
    ):
        raise VerificationError("M8n 43-case PASS census mismatch")
    m8p = load_json("evidence/m8p-partition-discovery/summary.json")
    coordinate = m8p.get("coordinate_screen")
    obstruction_counts = m8p.get("obstruction_result_counts")
    maximum_counts = m8p.get("positive_maximum_partition_counts")
    if not (
        m8p.get("status") == "PASS"
        and exact_integer(m8p.get("positive_case_count"), 3)
        and exact_integer(m8p.get("positive_factored_count"), 3)
        and exact_integer(m8p.get("positive_winning_count"), 2)
        and exact_integer(m8p.get("positive_losing_count"), 1)
        and exact_integer(m8p.get("obstruction_case_count"), 10)
        and isinstance(obstruction_counts, dict)
        and set(obstruction_counts) == {"INELIGIBLE", "NON_FACTORABLE"}
        and exact_integer(obstruction_counts.get("INELIGIBLE"), 1)
        and exact_integer(obstruction_counts.get("NON_FACTORABLE"), 9)
        and isinstance(maximum_counts, dict)
        and set(maximum_counts) == {
            "multiroot-uncontrollable-progress",
            "multistate-losing-monitor-outcome",
            "multistate-winning-nondeterministic-handover",
        }
        and all(exact_integer(value, 1) for value in maximum_counts.values())
        and exact_integer(m8p.get("independent_certificate_pass_count"), 13)
        and exact_integer(m8p.get("transport_witness_count"), 3)
        and exact_integer(m8p.get("independent_transport_pass_count"), 3)
        and exact_integer(m8p.get("transport_direct_flat_agreement_count"), 3)
        and isinstance(coordinate, dict)
        and exact_integer(coordinate.get("case_count"), 43)
        and exact_integer(coordinate.get("c1_semantic_family_count"), 10)
        and exact_integer(coordinate.get("typed_positive_claim_count"), 0)
    ):
        raise VerificationError("M8p typed partition/obstruction census mismatch")

    native = subprocess.run(
        (sys.executable, "-I", "-S", "-B", "analysis/audit_native_factorization.py"),
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if native.returncode != 0:
        detail = native.stderr.strip() or native.stdout.strip()
        raise VerificationError("M8q native-factorization audit failed: " + detail)
    try:
        native_report = json.loads(native.stdout)
    except json.JSONDecodeError as error:
        raise VerificationError("M8q audit did not emit JSON") from error
    stored_native = load_json("evidence/m8q-native-factorization/summary.json")
    native_bytes = json.dumps(native_report, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    stored_bytes = json.dumps(stored_native, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    if native_bytes != stored_bytes:
        raise VerificationError("M8q stored summary differs from fresh audit")
    if not (
        native_report.get("status") == "PASS"
        and exact_integer(native_report.get("source_files"), 23)
        and exact_integer(native_report.get("target_cells"), 41)
        and exact_integer(native_report.get("provenance_clusters"), 10)
        and exact_integer(native_report.get("successful_cells"), 35)
        and exact_integer(native_report.get("invalid_or_inconclusive_cells"), 6)
        and exact_integer(native_report.get("trivial_one_block_cells"), 33)
        and exact_integer(native_report.get("producer_verified_refined_win_cells"), 2)
        and exact_integer(native_report.get("producer_verified_refined_win_clusters"), 1)
        and exact_integer(native_report.get("structurally_checked_bundles"), 35)
        and native_report.get("refined_local_solver_sums", {}).get("arms2-r2")
        == {"states": 127174, "queries": 831356, "outcomes": 294632}
    ):
        raise VerificationError("M8q source-native census/boundary mismatch")

    dependency = subprocess.run(
        (sys.executable, "-I", "-S", "-B", "analysis/audit_native_source_dependencies.py"),
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if dependency.returncode != 0:
        detail = dependency.stderr.strip() or dependency.stdout.strip()
        raise VerificationError("M8r compiled-facts dependency audit failed: " + detail)
    try:
        dependency_report = json.loads(dependency.stdout)
    except json.JSONDecodeError as error:
        raise VerificationError("M8r audit did not emit JSON") from error
    stored_dependency = load_json(
        "evidence/m8r-native-source-dependency-replay/audit.json"
    )
    dependency_bytes = json.dumps(
        dependency_report, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    ).encode()
    stored_dependency_bytes = json.dumps(
        stored_dependency, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    ).encode()
    if dependency_bytes != stored_dependency_bytes:
        raise VerificationError("M8r stored audit differs from fresh audit")
    if not (
        dependency_report.get("status") == "PASS"
        and exact_integer(dependency_report.get("compiled_facts_replay_pass"), 41)
        and exact_integer(dependency_report.get("dependency_receipt_agreement_count"), 35)
        and exact_integer(dependency_report.get("component_partition_agreement_count"), 35)
        and exact_integer(dependency_report.get("ownerless_gate_agreement_count"), 6)
        and exact_integer(dependency_report.get("shared_mtsa_frontend_count"), 41)
        and exact_integer(dependency_report.get("independent_source_frontend_count"), 0)
        and exact_integer(dependency_report.get("ordinary_lts_source_replay_count"), 0)
        and exact_integer(dependency_report.get("source_to_witness_replay_count"), 0)
        and dependency_report.get("dependency_outcome_counts")
        == {"NONTRIVIAL_PARTITION": 2, "ONE_BLOCK": 33, "OWNERLESS_REJECT": 6}
    ):
        raise VerificationError("M8r dependency replay census/boundary mismatch")

    contract = subprocess.run(
        (
            sys.executable, "-I", "-S", "-B",
            "analysis/audit_post_frontend_contract_certificate.py",
            "--expected",
            "evidence/m8s-post-frontend-contract-certificate/audit.json",
        ),
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if contract.returncode != 0:
        detail = contract.stderr.strip() or contract.stdout.strip()
        raise VerificationError(
            "M8s post-frontend certificate audit failed: " + detail
        )
    try:
        contract_report = json.loads(contract.stdout)
    except json.JSONDecodeError as error:
        raise VerificationError("M8s audit did not emit JSON") from error
    if not (
        contract_report.get("status") == "PASS"
        and exact_integer(contract_report.get("source_files"), 1)
        and exact_integer(contract_report.get("target_cells"), 2)
        and exact_integer(contract_report.get("provenance_clusters"), 1)
        and exact_integer(
            contract_report.get(
                "post_frontend_contract_ir_to_winning_certificate_semantic_verification"
            ),
            2,
        )
        and exact_integer(
            contract_report.get("global_transport_and_kappa_verified"), 2
        )
        and exact_integer(contract_report.get("independent_raw_source_frontend"), 0)
        and exact_integer(contract_report.get("independent_win_synthesis"), 0)
        and exact_integer(contract_report.get("source_to_win_replay"), 0)
        and contract_report.get("totals", {}).get("candidate_buckets") == 4774
        and contract_report.get("totals", {}).get("candidate_outcomes") == 2682
        and contract_report.get("totals", {}).get("rank_states") == 212
    ):
        raise VerificationError("M8s certificate semantics census/boundary mismatch")

    source_certificate = subprocess.run(
        (
            sys.executable, "-I", "-S", "-B",
            "analysis/audit_productioncell_source_contract_certificate.py",
            "--protocol",
            "protocols/productioncell_source_contract_certificate_v1_20260814.json",
            "--evidence",
            "evidence/m8t-productioncell-source-contract-certificate",
            "--expected",
            "evidence/m8t-productioncell-source-contract-certificate/audit.json",
        ),
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if source_certificate.returncode != 0:
        detail = source_certificate.stderr.strip() or source_certificate.stdout.strip()
        raise VerificationError(
            "M8t source-to-supplied-certificate audit failed: " + detail
        )
    try:
        source_certificate_report = json.loads(source_certificate.stdout)
    except json.JSONDecodeError as error:
        raise VerificationError("M8t audit did not emit JSON") from error
    if not (
        source_certificate_report.get("status") ==
        "SOURCE_TO_SUPPLIED_CERTIFICATE_SEMANTICS_VERIFIED"
        and exact_integer(source_certificate_report.get("source_files"), 1)
        and exact_integer(source_certificate_report.get("target_cells"), 2)
        and exact_integer(source_certificate_report.get("provenance_clusters"), 1)
        and exact_integer(
            source_certificate_report.get(
                "source_to_supplied_certificate_semantic_verification"
            ),
            2,
        )
        and exact_integer(
            source_certificate_report.get("unique_independent_controller_pairs"),
            1,
        )
        and exact_integer(source_certificate_report.get("independent_win_synthesis"), 0)
        and exact_integer(source_certificate_report.get("source_to_win_replay"), 0)
        and source_certificate_report.get("source_census", {}).get(
            "old_controller_states"
        ) == 162
        and source_certificate_report.get("source_census", {}).get(
            "new_controller_states"
        ) == 162
        and source_certificate_report.get("source_census", {}).get(
            "activation_error_rows"
        ) == 164
        and source_certificate_report.get("supplied_certificate_census", {}).get(
            "candidate_buckets"
        ) == 4774
        and source_certificate_report.get("supplied_certificate_census", {}).get(
            "candidate_outcomes"
        ) == 2682
        and source_certificate_report.get("supplied_certificate_census", {}).get(
            "global_transport_and_kappa_verified"
        ) == 2
    ):
        raise VerificationError("M8t source/certificate census or boundary mismatch")

    flat_trace = subprocess.run(
        (
            sys.executable, "-I", "-S", "-B",
            "analysis/trace_typed_partition_predicate.py",
            "inputs/c2/typed-partition-predicate-example.json",
            "--check",
            "evidence/m8p-partition-discovery/predicate-trace-example.json",
        ),
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if flat_trace.returncode != 0:
        detail = flat_trace.stderr.strip() or flat_trace.stdout.strip()
        raise VerificationError("M8p complete flat predicate trace failed: " + detail)
    try:
        flat_trace_report = json.loads(flat_trace.stdout)
    except json.JSONDecodeError as error:
        raise VerificationError("M8p flat trace did not emit JSON") from error
    if not (
        flat_trace_report.get("status") == "PASS"
        and exact_integer(flat_trace_report.get("partition_count"), 2)
        and exact_integer(flat_trace_report.get("first_accepted_block_count"), 2)
        and flat_trace_report.get("all_accepted_candidates_transport_ready") is True
    ):
        raise VerificationError("M8p complete flat trace census differs")

    construction_trace = subprocess.run(
        (
            sys.executable, "-I", "-S", "-B",
            "analysis/check_ordinary_source_construction_trace.py",
        ),
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if construction_trace.returncode != 0:
        detail = construction_trace.stderr.strip() or construction_trace.stdout.strip()
        raise VerificationError("ordinary-source construction trace failed: " + detail)
    try:
        construction_trace_report = json.loads(construction_trace.stdout)
    except json.JSONDecodeError as error:
        raise VerificationError("ordinary-source construction trace did not emit JSON") from error
    if not (
        construction_trace_report.get("status") == "PASS"
        and exact_integer(construction_trace_report.get("source_in_fields"), 16)
        and exact_integer(construction_trace_report.get("source_stages"), 5)
        and exact_integer(construction_trace_report.get("output_y_fields"), 10)
        and exact_integer(construction_trace_report.get("source_theorem_mappings"), 7)
        and construction_trace_report.get("historical_producer_runtime_replayed") is False
        and construction_trace_report.get("source_to_win_replay") is False
        and construction_trace_report.get("one_way_result") ==
        "RECORDED_PRODUCER_LABEL_WITH_SEPARATE_SUPPLIED_WITNESS_SEMANTIC_CHECK"
    ):
        raise VerificationError("ordinary-source construction trace census or boundary differs")

    hand_source_trace = subprocess.run(
        (
            sys.executable, "-I", "-S", "-B",
            "analysis/check_hand_checkable_ordinary_source_trace.py",
        ),
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if hand_source_trace.returncode != 0:
        detail = hand_source_trace.stderr.strip() or hand_source_trace.stdout.strip()
        raise VerificationError("hand-checkable ordinary-source trace failed: " + detail)
    try:
        hand_source_trace_report = json.loads(hand_source_trace.stdout)
    except json.JSONDecodeError as error:
        raise VerificationError("hand-checkable ordinary-source trace did not emit JSON") from error
    if not (
        hand_source_trace_report.get("status") == "PASS"
        and exact_integer(hand_source_trace_report.get("source_in_fields"), 16)
        and exact_integer(hand_source_trace_report.get("source_stages"), 5)
        and exact_integer(hand_source_trace_report.get("output_y_fields"), 10)
        and exact_integer(hand_source_trace_report.get("rank_states"), 4)
        and exact_integer(hand_source_trace_report.get("candidate_buckets"), 2)
        and exact_integer(hand_source_trace_report.get("global_states"), 4)
        and exact_integer(hand_source_trace_report.get("global_post_buckets"), 12)
        and exact_integer(hand_source_trace_report.get("relation_pairs"), 4)
        and exact_integer(hand_source_trace_report.get("observer_relation_pairs"), 2)
        and exact_integer(hand_source_trace_report.get("load_selectors"), 1)
        and exact_integer(hand_source_trace_report.get("terminal_tuples"), 1)
        and exact_integer(hand_source_trace_report.get("theorem_5_3_premises"), 7)
        and exact_integer(hand_source_trace_report.get("theorem_5_4_predicates"), 5)
        and exact_integer(hand_source_trace_report.get("theorem_5_5_premises"), 7)
        and hand_source_trace_report.get("stored_bundle_is_execution_provenance") is False
        and hand_source_trace_report.get("independent_source_to_win_replay") is False
        and exact_integer(hand_source_trace_report.get("scientific_outcome_denominator_delta"), 0)
    ):
        raise VerificationError("hand-checkable ordinary-source trace census or boundary differs")

    generated_certificate = subprocess.run(
        (
            sys.executable, "-I", "-S", "-B",
            "analysis/audit_post_frontend_generated_win_panel.py",
            "--protocol",
            "protocols/post_frontend_generated_win_panel_v1_20260815.json",
            "--evidence",
            "evidence/m8u-post-frontend-generated-win-panel",
            "--expected",
            "evidence/m8u-post-frontend-generated-win-panel/audit.json",
        ),
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if generated_certificate.returncode != 0:
        detail = generated_certificate.stderr.strip() or generated_certificate.stdout.strip()
        raise VerificationError(
            "M8u generated post-frontend WIN-certificate audit failed: " + detail
        )
    try:
        generated_certificate_report = json.loads(generated_certificate.stdout)
    except json.JSONDecodeError as error:
        raise VerificationError("M8u audit did not emit JSON") from error
    generated_boundary = generated_certificate_report.get("claim_boundary")
    if not (
        generated_certificate_report.get("status") == "PASS"
        and exact_integer(generated_certificate_report.get("source_files"), 2)
        and exact_integer(generated_certificate_report.get("target_cells"), 3)
        and exact_integer(
            generated_certificate_report.get("provenance_clusters"), 2
        )
        and exact_integer(
            generated_certificate_report.get("verified_generated_win_certificates"),
            3,
        )
        and exact_integer(
            generated_certificate_report.get("historical_outcome_inputs"), 0
        )
        and exact_integer(
            generated_certificate_report.get("supplied_certificate_inputs"), 0
        )
        and generated_certificate_report.get("industry_whole_system_block") is True
        and generated_certificate_report.get("industry_nontrivial_factorization")
        is False
        and generated_certificate_report.get("verified_totals", {}).get(
            "candidate_buckets"
        ) == 15049
        and generated_certificate_report.get("verified_totals", {}).get(
            "candidate_outcomes"
        ) == 6319
        and generated_certificate_report.get("verified_totals", {}).get(
            "rank_states"
        ) == 622
        and generated_certificate_report.get("verified_totals", {}).get(
            "strategy_buckets"
        ) == 778
        and isinstance(generated_boundary, dict)
        and generated_boundary.get("post_outcome") is True
        and generated_boundary.get("same_author_generator") is True
        and generated_boundary.get("same_author_separate_checker") is True
        and generated_boundary.get("conclusion_free_post_frontend_ir_only") is True
        and generated_boundary.get("shared_mtsa_frontend") is True
        and generated_boundary.get("shared_post_frontend_semantic_adapter") is True
        and generated_boundary.get("independent_raw_source_frontend") is False
        and generated_boundary.get("independent_controller_synthesis") is False
        and generated_boundary.get("independent_source_to_win_replay") is False
        and exact_integer(generated_boundary.get("held_out_cases"), 0)
        and exact_integer(generated_boundary.get("third_party_cases"), 0)
        and exact_integer(generated_boundary.get("production_cases"), 0)
        and exact_integer(generated_boundary.get("native_contract_cases"), 0)
    ):
        raise VerificationError("M8u generated-certificate census or boundary mismatch")


def run_tests() -> None:
    completed = subprocess.run(
        (
            sys.executable,
            "-I",
            "-S",
            "-B",
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            "test_*.py",
            "-v",
        ),
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    print(completed.stdout, end="")
    print(completed.stderr, end="", file=sys.stderr)
    if completed.returncode != 0:
        raise VerificationError("public regression tests failed")
    match = re.search(r"Ran (\d+) tests", completed.stdout + completed.stderr)
    if match is None or int(match.group(1)) != 210:
        raise VerificationError("public regression test census differs from 210")
    native_test_methods = sum(
        len(re.findall(r"^    def test_", (ROOT / relative).read_text(encoding="utf-8"), re.MULTILINE))
        for relative in ("tests/test_native_refined_bundle.py", "tests/test_native_factorization_audit.py")
    )
    if native_test_methods != 31:
        raise VerificationError("M8q test census differs from 31 methods (2 registered checks + 29 mutation tests)")
    dependency_test_methods = len(re.findall(
        r"^    def test_",
        (ROOT / "tests/test_native_source_dependencies.py").read_text(encoding="utf-8"),
        re.MULTILINE,
    ))
    if dependency_test_methods != 16:
        raise VerificationError("M8r test census differs from 16 methods")
    contract_test_methods = len(re.findall(
        r"^    def test_",
        (ROOT / "tests/test_post_frontend_contract_certificate.py").read_text(
            encoding="utf-8"
        ),
        re.MULTILINE,
    ))
    if contract_test_methods != 7:
        raise VerificationError("M8s test census differs from 7 methods")
    source_certificate_test_methods = sum(
        len(re.findall(
            r"^    def test_",
            (ROOT / relative).read_text(encoding="utf-8"),
            re.MULTILINE,
        ))
        for relative in (
            "tests/test_productioncell_source_contract_certificate.py",
            "tests/test_productioncell_source_contract_campaign.py",
        )
    )
    if source_certificate_test_methods != 22:
        raise VerificationError("M8t test census differs from 22 methods")
    construction_trace_test_methods = len(re.findall(
        r"^    def test_",
        (ROOT / "tests/test_ordinary_source_construction_trace.py").read_text(
            encoding="utf-8"
        ),
        re.MULTILINE,
    ))
    if construction_trace_test_methods != 8:
        raise VerificationError("ordinary-source construction trace test census differs from 8 methods")
    hand_source_trace_test_methods = len(re.findall(
        r"^    def test_",
        (ROOT / "tests/test_hand_checkable_ordinary_source_trace.py").read_text(
            encoding="utf-8"
        ),
        re.MULTILINE,
    ))
    if hand_source_trace_test_methods != 10:
        raise VerificationError("hand-checkable ordinary-source trace test census differs from 10 methods")
    generated_certificate_test_methods = sum(
        len(re.findall(
            r"^    def test_",
            (ROOT / relative).read_text(encoding="utf-8"),
            re.MULTILINE,
        ))
        for relative in (
            "tests/test_strong_rank_certificate_core.py",
            "tests/test_synthesize_post_frontend_win_certificate.py",
            "tests/test_generated_post_frontend_win_certificate.py",
            "tests/test_post_frontend_generated_win_panel.py",
        )
    )
    if generated_certificate_test_methods != 46:
        raise VerificationError("M8u test census differs from 46 methods")


def run_analysis() -> None:
    completed = subprocess.run(
        (
            sys.executable,
            "-I",
            "-S",
            "-B",
            "analysis/recompute_claims.py",
        ),
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise VerificationError("raw-to-claim analysis failed: " + detail)
    try:
        report = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise VerificationError("raw-to-claim analysis did not emit JSON") from error
    if not isinstance(report, dict) or report.get("status") != "PASS":
        raise VerificationError("raw-to-claim analysis is not PASS")


def verify_git() -> None:
    if not (ROOT / ".git").is_dir():
        raise VerificationError("artifact is not initialized as a Git repository")
    commands = (
        ("git", "status", "--porcelain"),
        ("git", "remote"),
        ("git", "tag"),
    )
    for command in commands:
        completed = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        if completed.returncode != 0:
            raise VerificationError(f"Git check failed: {' '.join(command)}")
        if completed.stdout.strip():
            raise VerificationError(f"Git publication boundary is not clean: {' '.join(command)}")
    refs = subprocess.run(
        ("git", "for-each-ref", "--format=%(refname)"),
        cwd=ROOT,
        stdout=subprocess.PIPE,
        text=True,
        check=True,
    ).stdout.splitlines()
    if refs != ["refs/heads/main"]:
        raise VerificationError(f"unexpected Git refs: {refs}")
    count = subprocess.run(
        ("git", "rev-list", "--count", "HEAD"),
        cwd=ROOT,
        stdout=subprocess.PIPE,
        text=True,
        check=True,
    ).stdout.strip()
    if count != "1":
        raise VerificationError(f"expected one root commit, found {count}")
    head = subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=ROOT,
        stdout=subprocess.PIPE,
        text=True,
        check=True,
    ).stdout.strip()
    unreachable = subprocess.run(
        ("git", "fsck", "--full", "--no-reflogs", "--unreachable"),
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    if unreachable.returncode != 0 or unreachable.stdout.strip():
        raise VerificationError("Git object database contains unreachable history")
    reflog_commits = subprocess.run(
        ("git", "reflog", "--all", "--format=%H"),
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if reflog_commits.returncode != 0:
        raise VerificationError("Git reflog audit failed")
    if any(commit != head for commit in reflog_commits.stdout.splitlines()):
        raise VerificationError("Git reflog exposes pre-release history")
    rights = (ROOT / "RIGHTS_REVIEW.md").read_text(encoding="utf-8").splitlines()
    rows = [
        [cell.strip() for cell in line.strip().strip("|").split("|")]
        for line in rights
        if line.startswith("|") and not set(line.replace("|", "").strip()) <= {"-", ":", " "}
    ]
    decisions = [row[-1] for row in rows if row and row[0] != "File class"]
    allowed = {"AUTHOR_OWNED", "PERMISSION_CONFIRMED", "OMITTED"}
    if len(decisions) != 8 or any(
        decision not in allowed and not decision.startswith("LICENSED:")
        for decision in decisions
    ):
        raise VerificationError(
            "publication rights table must contain exactly 8 explicitly resolved rows"
        )


def parse_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode",
        choices=(
            "integrity",
            "verify",
            "scan",
            "test",
            "analyze",
            "portable",
            "handoff",
            "full",
        ),
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    arguments = parse_arguments(argv)
    try:
        if arguments.mode in {
            "integrity", "verify", "analyze", "portable", "handoff", "full"
        }:
            count = verify_checksums()
            verify_science()
            print(f"integrity/science PASS ({count} files)")
        if arguments.mode in {"scan", "portable", "handoff", "full"}:
            count = scan()
            print(f"generic anonymity/secret scan PASS ({count} text files)")
        if arguments.mode in {"test", "portable", "handoff", "full"}:
            run_tests()
            print("tests PASS")
        if arguments.mode in {"analyze", "portable", "handoff", "full"}:
            run_analysis()
            print("raw-to-claim analysis PASS")
        if arguments.mode in {"handoff", "full"}:
            verify_git()
            print("Git publication boundary PASS")
        return 0
    except (VerificationError, OSError, UnicodeDecodeError, subprocess.SubprocessError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
