#!/usr/bin/env python3
"""Run the frozen three-cell post-frontend generated-WIN panel.

The generator receives only a copied conclusion-free IR and fixed resource
limits.  Each IR and generation is repeated in a fresh process.  A generation
seal is written before the checker is started.  Historical M8q/M8s outcomes
and supplied certificates are neither protocol inputs nor process arguments.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = (
    ROOT / "protocols/post_frontend_generated_win_panel_v1_20260815.json"
)
PROTOCOL_SCHEMA = "fg-ducs-post-frontend-generated-win-panel-protocol-v1"
SUMMARY_SCHEMA = "fg-ducs-post-frontend-generated-win-panel-summary-v1"
RECORD_SCHEMA = "fg-ducs-post-frontend-generated-win-panel-record-v1"
SEAL_SCHEMA = "fg-ducs-post-frontend-generation-seal-v1"
NOT_RUN_SCHEMA = "fg-ducs-generated-post-frontend-checker-not-run-v1"
CAMPAIGN_ID = "m8u-post-frontend-generated-win-panel-20260815a"
FACTS_CLASS = "ltsa.lts.NativePostFrontendContractFactsRunner"
IR_SCHEMA = "fg-ducs-post-frontend-contract-facts-v1"
IR_STAGE = "AFTER_FIXED_ENDPOINT_CONTROLLER_SYNTHESIS_BEFORE_ENDPOINT_PRODUCT"
CERTIFICATE_SCHEMA = "fg-ducs-generated-post-frontend-win-certificate-v1"
CHECK_REPORT_SCHEMA = "fg-ducs-generated-post-frontend-win-certificate-check-v1"
CHECK_STATUS = "GENERATED_POST_FRONTEND_WIN_CERTIFICATE_VERIFIED"

EXPECTED_CASE_ORDER = (
    "productioncell-arms2-base-productioncell-arms-2-fg",
    "productioncell-arms2-r2-productioncell-arms-2-fg",
    "industry-base-industry-fg",
)
EXPECTED_CASES: dict[str, dict[str, Any]] = {
    "productioncell-arms2-base-productioncell-arms-2-fg": {
        "condition": "arms2-base",
        "cluster": "productioncell",
        "definition": "UpdCont_OTF_FG",
        "source_path": "Implementation/Experiment/Models/ProductionCell_Arms=2_FG.lts",
        "source_sha256": "117210fa93185f5a814ad7debbdfcde00720019312c4ef68446a844700084e43",
        "ir_sha256": "a585319ee85d1bd4f21b402c2c9c671b8def43f20a1309c92a6b424a9e74dfd8",
        "ir_bytes": 383579,
    },
    "productioncell-arms2-r2-productioncell-arms-2-fg": {
        "condition": "arms2-r2",
        "cluster": "productioncell",
        "definition": "UpdCont_OTF_FG_R2",
        "source_path": "Implementation/Experiment/Models/ProductionCell_Arms=2_FG.lts",
        "source_sha256": "117210fa93185f5a814ad7debbdfcde00720019312c4ef68446a844700084e43",
        "ir_sha256": "29d701d7cfac3d5c8458043e6d773aa0df4d7234cea3639578aa43382d4f18f3",
        "ir_bytes": 394473,
    },
    "industry-base-industry-fg": {
        "condition": "industry-base",
        "cluster": "industry",
        "definition": "UpdCont_OTF_FG",
        "source_path": "Implementation/Experiment/Models/Industry_FG.lts",
        "source_sha256": "d8bd82a0ad6eeedc4986a688076fe4646f03a665a41a8c6c5f6cbfbd3b2506dd",
        "ir_sha256": "c86addf7de5c78fd9aadb54a67238029a693fcabf14465f985c9f1818eee7b7b",
        "ir_bytes": 72386,
    },
}

FAILURE_TAXONOMY = (
    "SUCCESS_WIN",
    "INVALID_INPUT",
    "INCONCLUSIVE_RANK_BOUND",
    "INCONCLUSIVE_STATE_LIMIT",
    "INCONCLUSIVE_BUCKET_LIMIT",
    "INCONCLUSIVE_OUTCOME_LIMIT",
    "INCONCLUSIVE_TIMEOUT",
    "INCONCLUSIVE_OOM",
    "ERROR_CRASH",
    "CERTIFICATE_REJECTED",
)
CLAIM_BOUNDARY = {
    "same_author_generator": True,
    "same_author_separate_checker": True,
    "shared_post_frontend_semantic_adapter": True,
    "shared_mtsa_frontend": True,
    "fixed_controller_synthesis_shared": True,
    "conclusion_free_post_frontend_ir_only": True,
    "post_outcome": True,
    "calibrated_rank_bound": True,
    "historical_outcome_inputs": 0,
    "supplied_certificate_inputs": 0,
    "independent_raw_source_frontend": False,
    "independent_controller_synthesis": False,
    "independent_source_to_win_replay": False,
    "general_mtsa_frontend": False,
    "held_out_cases": 0,
    "third_party_cases": 0,
    "production_cases": 0,
    "native_contract_cases": 0,
}
DENOMINATOR = {
    "source_files": 2,
    "target_cells": 3,
    "provenance_clusters": 2,
    "conclusion_free_ir_inputs": 3,
    "historical_outcome_inputs": 0,
    "supplied_certificate_inputs": 0,
    "held_out_cases": 0,
    "third_party_cases": 0,
    "production_cases": 0,
    "native_contract_cases": 0,
    "automatic_retries": 0,
    "replacements": 0,
}
LIMITS = {
    "max_rank": 32,
    "max_states": 2_000_000,
    "max_candidate_buckets": 20_000_000,
    "max_outcomes": 40_000_000,
    "generator_internal_timeout_seconds": 600,
}
RUNTIME_BINDING = {
    "observation_jar_sha256":
        "322325b8112ab8783f9b6ca1d7dc58da567d153f2357bbf5ad318bdb5d8666fa",
    "historical_m8q_jar_sha256":
        "5e09cd39b2c00428d104061590702fdbd48f42cf3c5a15a354a1ac3765d71edf",
    "class_entries": {
        "ltsa/lts/NativePostFrontendContractFactsRunner.class":
            "830dedd0840e31ae582e17e1e65ea7e1f703b3596c940c8908fbd7bfbcc639fb",
        "ltsa/lts/NativeSourceDependencyFactsRunner.class":
            "b0ec612626ddc5effbe03053dc9ddc3ed3b8d70045887bfedea00fd3d2aa054d",
        "ltsa/lts/NativeUpdatingContractLoader.class":
            "2d015e8b23c760f633cb7fd8db80eb9b47ad2292aaae7760ea2b39f967d1d114",
    },
    "facts_timeout_seconds": 120,
    "generator_timeout_seconds": 660,
    "checker_timeout_seconds": 600,
    "audit_timeout_seconds": 1200,
}
FIREWALL = {
    "generator_scientific_inputs": ["conclusion_free_ir", "fixed_resource_limits"],
    "historical_outcome_paths_registered": False,
    "supplied_certificate_paths_registered": False,
    "generator_checker_process_separation": True,
    "generator_repeat_byte_determinism": True,
    "generation_seal_before_checker": True,
    "checker_imports_generator": False,
    "checker_imports_rank_core": False,
    "checker_reuses_post_frontend_semantic_adapter": True,
    "os_level_sandbox_claimed": False,
}
REGISTERED_ROLES = {
    "facts_runner_source", "facts_runner_test", "inherited_facts_source",
    "native_loader_source", "generator", "rank_core", "checker",
    "semantic_adapter", "campaign_runner", "offline_audit",
    "rank_core_test", "generator_test", "checker_test", "campaign_test",
}
REGISTERED_PATHS = {
    "facts_runner_source": (
        "source-rebuild/added/maven-root/mtsa/src/main/java/ltsa/lts/"
        "NativePostFrontendContractFactsRunner.java"),
    "facts_runner_test": (
        "source-rebuild/added/maven-root/mtsa/src/test/java/ltsa/lts/"
        "NativePostFrontendContractFactsRunnerTest.java"),
    "inherited_facts_source": (
        "source-rebuild/added/maven-root/mtsa/src/main/java/ltsa/lts/"
        "NativeSourceDependencyFactsRunner.java"),
    "native_loader_source": (
        "source-rebuild/added/maven-root/mtsa/src/main/java/ltsa/lts/"
        "NativeUpdatingContractLoader.java"),
    "generator": "analysis/synthesize_post_frontend_win_certificate.py",
    "rank_core": "analysis/strong_rank_certificate_core.py",
    "checker": "analysis/check_generated_post_frontend_win_certificate.py",
    "semantic_adapter": "analysis/check_post_frontend_contract_certificate.py",
    "campaign_runner": "analysis/run_post_frontend_generated_win_panel.py",
    "offline_audit": "analysis/audit_post_frontend_generated_win_panel.py",
    "rank_core_test": "tests/test_strong_rank_certificate_core.py",
    "generator_test": "tests/test_synthesize_post_frontend_win_certificate.py",
    "checker_test": "tests/test_generated_post_frontend_win_certificate.py",
    "campaign_test": "tests/test_post_frontend_generated_win_panel.py",
}
FIXED_REGISTERED_HASHES = {
    "facts_runner_source":
        "f7764cf41f75e1270a409efb22e59f8e74cc86a0d062dcf9786983309260f13f",
    "facts_runner_test":
        "1182257177a63f1354ca5e3ee3262ef7a08de67b503a7bcb215c40828b32ddb8",
    "inherited_facts_source":
        "cf6b650217d545c4ce16ab89668f606aff733bce69615137705660b071880837",
    "native_loader_source":
        "c01d1471a64002e5540ba2525087e22c39fbf8d89cda44e99c82775e319371c6",
    "semantic_adapter":
        "cb7432049df13335992bdd6df550fb8ea1749e0aabdc629d556667b70c819c2d",
}
CASE_FILES = {
    "facts.json", "facts-repeat.json", "facts.stdout.txt",
    "facts.stderr.txt", "facts-repeat.stdout.txt",
    "facts-repeat.stderr.txt", "generated-output.json",
    "generated-output-repeat.json", "generator.stdout.txt",
    "generator.stderr.txt", "generator-repeat.stdout.txt",
    "generator-repeat.stderr.txt", "generation-seal.json",
    "checker-report.json", "checker.stdout.txt", "checker.stderr.txt",
    "record.json",
}
FORBIDDEN_IR_KEYS = {
    "component_partition", "dependency_receipts", "factor_status",
    "solve_status", "winning", "losing", "certificate", "strategy",
    "rank", "witness", "proof", "local_game", "endpoint_product",
    "owner_sets", "action_owners", "candidate_buckets",
    "strategy_buckets", "terminal_assemblies",
}
CHECK_REPORT_KEYS = {
    "schema_version", "status", "source_name", "source_sha256",
    "definition", "ir_exact_byte_sha256", "ir_exact_byte_size",
    "old_endpoint_states", "new_endpoint_states",
    "old_endpoint_semantic_sha256", "new_endpoint_semantic_sha256",
    "component_partition", "whole_system_block",
    "nontrivial_factorization", "normal_owner_actions",
    "update_owner_actions", "requirement_machines", "observer_machines",
    "owner_relation_sha256", "global_old_root_projection_checks",
    "locals", "totals", "transport", "semantic_reuse", "claim_boundary",
    "semantic_digest_sha256",
}
CHECK_CLAIM_BOUNDARY = {
    "conclusion_free_post_frontend_ir_only": True,
    "fresh_generated_certificate_checked": True,
    "historical_m8q_m8s_bundle_consumed": False,
    "supplied_historical_certificate_consumed": False,
    "generator_or_rank_core_imported_or_called": False,
    "shared_post_frontend_semantic_adapter": True,
    "independent_raw_source_frontend": False,
    "independent_controller_synthesis": False,
    "independent_post_frontend_win_generation": True,
    "all_roots_strong_rank_certificate_verified": True,
    "global_transport_and_kappa_verified": True,
}
INCONCLUSIVE_KEYS = {
    "schema_version", "generator_boundary", "ir_binding", "decision",
    "reason", "block_index", "loss_claimed",
}
SUCCESS_KEYS = {
    "schema_version", "generator_boundary", "ir_binding", "decision",
    "component_partition", "endpoints", "locals", "transport",
}
GENERATOR_BOUNDARY = {
    "algorithm": "BOUNDED_MINIMUM_STRONG_RANK_PENDING_UPDATE_THEN_LEXICAL_V1",
    "depth_bound": 32,
    "historical_bundle_consumed": False,
    "supplied_certificate_consumed": False,
    "outcome_fields_consumed": False,
}
INCONCLUSIVE_REASONS = {
    "ROOT_NOT_PROVED_WIN_WITHIN_RANK_BOUND", "STATE_LIMIT",
    "CANDIDATE_BUCKET_LIMIT", "OUTCOME_LIMIT", "TIMEOUT",
    "MEMORY_EXHAUSTED",
}


class CampaignError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CampaignError(message)


def canonical(value: Any) -> bytes:
    try:
        return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":"), allow_nan=False)
                + "\n").encode("utf-8")
    except (TypeError, ValueError) as error:
        raise CampaignError("value is not finite canonical JSON") from error


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key: " + key)
        result[key] = value
    return result


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_bytes().decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=lambda token: (_ for _ in ()).throw(
                ValueError(token)),
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError,
            ValueError) as error:
        raise CampaignError("invalid strict JSON: " + str(path)) from error
    require(type(value) is dict, "JSON root is not an object")
    return value


def load_bytes(raw: bytes, label: str, *, canonical_required: bool = False,
               allow_empty: bool = False) -> dict[str, Any] | None:
    if allow_empty and raw == b"":
        return None
    try:
        value = json.loads(
            raw.decode("utf-8"), object_pairs_hook=_unique_object,
            parse_constant=lambda token: (_ for _ in ()).throw(
                ValueError(token)),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise CampaignError(f"invalid strict JSON: {label}") from error
    require(type(value) is dict, f"{label} root is not an object")
    if canonical_required:
        require(raw == canonical(value), f"{label} is not canonical JSON")
    return value


def exact_keys(value: Any, expected: Iterable[str], label: str) -> Mapping[str, Any]:
    required = set(expected)
    require(type(value) is dict and set(value) == required,
            f"{label} key census differs: "
            f"{sorted(set(value) ^ required) if type(value) is dict else 'not-object'}")
    return value


def exact_int(value: Any, label: str, minimum: int = 0) -> int:
    require(type(value) is int and value >= minimum,
            f"{label} is not an exact integer >= {minimum}")
    return value


def hex64(value: Any, label: str) -> str:
    require(type(value) is str and bool(re.fullmatch(r"[0-9a-f]{64}", value)),
            f"{label} is not lowercase SHA-256")
    return value


def safe_relative(value: Any, label: str) -> PurePosixPath:
    require(type(value) is str and bool(value), f"{label} is not text")
    path = PurePosixPath(value)
    require(not path.is_absolute() and ".." not in path.parts
            and path.as_posix() == value, f"unsafe {label}")
    return path


def registered_path(row: Any, label: str, *, root: Path = ROOT,
                    verify_file: bool = True) -> Path:
    value = exact_keys(row, {"path", "sha256"}, label)
    relative = safe_relative(value["path"], label + " path")
    digest = hex64(value["sha256"], label + " hash")
    path = root / Path(*relative.parts)
    if verify_file:
        require(path.is_file() and not path.is_symlink(),
                f"registered {label} is absent or a symlink")
        require(sha256(path) == digest, f"registered {label} hash differs")
    return path


def _validate_runtime(value: Any) -> Mapping[str, Any]:
    row = exact_keys(value, {
        "observation_jar_sha256", "historical_m8q_jar_sha256",
        "facts_runner_class", "class_entries", "heap",
        "facts_timeout_seconds", "generator_timeout_seconds",
        "checker_timeout_seconds", "audit_timeout_seconds",
        "observation_current_source_only", "historical_runtime_reproduced",
        "transitive_runtime_closure_frozen", "python_isolated_flags",
    }, "runtime")
    require(row["facts_runner_class"] == FACTS_CLASS
            and row["heap"] == "16g", "runtime Java binding differs")
    for field in ("observation_jar_sha256", "historical_m8q_jar_sha256"):
        hex64(row[field], "runtime " + field)
    entries = exact_keys(row["class_entries"], {
        "ltsa/lts/NativePostFrontendContractFactsRunner.class",
        "ltsa/lts/NativeSourceDependencyFactsRunner.class",
        "ltsa/lts/NativeUpdatingContractLoader.class",
    }, "runtime class entries")
    for name, digest in entries.items():
        hex64(digest, "class entry " + name)
    for field in ("facts_timeout_seconds", "generator_timeout_seconds",
                  "checker_timeout_seconds", "audit_timeout_seconds"):
        exact_int(row[field], "runtime " + field, 1)
    require(row["observation_current_source_only"] is True
            and row["historical_runtime_reproduced"] is False
            and row["transitive_runtime_closure_frozen"] is False
            and row["python_isolated_flags"] == ["-I", "-S", "-B"],
            "runtime claim boundary differs")
    for field in ("observation_jar_sha256", "historical_m8q_jar_sha256",
                  "facts_timeout_seconds", "generator_timeout_seconds",
                  "checker_timeout_seconds", "audit_timeout_seconds"):
        require(row[field] == RUNTIME_BINDING[field],
                "runtime frozen binding differs: " + field)
    require(entries == RUNTIME_BINDING["class_entries"],
            "runtime class-entry hashes differ")
    return row


def verify_protocol(protocol: Mapping[str, Any], *, root: Path = ROOT,
                    verify_files: bool = True) -> list[Mapping[str, Any]]:
    exact_keys(protocol, {
        "schema_version", "date", "campaign_id", "denominator",
        "claim_boundary", "registered_files", "runtime", "limits", "cases",
        "scientific_input_firewall", "failure_taxonomy",
    }, "protocol")
    require(protocol["schema_version"] == PROTOCOL_SCHEMA
            and protocol["date"] == "2026-08-15"
            and protocol["campaign_id"] == CAMPAIGN_ID,
            "protocol identity differs")
    require(protocol["denominator"] == DENOMINATOR,
            "protocol denominator differs")
    require(protocol["claim_boundary"] == CLAIM_BOUNDARY,
            "protocol claim boundary differs")
    require(protocol["limits"] == LIMITS, "protocol limits differ")
    require(protocol["scientific_input_firewall"] == FIREWALL,
            "protocol input firewall differs")
    require(protocol["failure_taxonomy"] == list(FAILURE_TAXONOMY),
            "protocol failure taxonomy differs")
    runtime = _validate_runtime(protocol["runtime"])
    require(runtime["generator_timeout_seconds"] >
            LIMITS["generator_internal_timeout_seconds"],
            "outer generator timeout must exceed its internal bound")
    files = exact_keys(protocol["registered_files"], REGISTERED_ROLES,
                       "registered files")
    for role, row in files.items():
        require(type(row) is dict and row.get("path") == REGISTERED_PATHS[role],
                "registered path differs: " + role)
        if role in FIXED_REGISTERED_HASHES:
            require(row.get("sha256") == FIXED_REGISTERED_HASHES[role],
                    "registered frozen hash differs: " + role)
        registered_path(row, role, root=root, verify_file=verify_files)
    if verify_files:
        verify_import_firewall(
            registered_path(files["generator"], "generator", root=root),
            registered_path(files["rank_core"], "rank core", root=root),
            registered_path(files["checker"], "checker", root=root),
            registered_path(files["semantic_adapter"], "semantic adapter",
                            root=root),
        )

    cases = protocol["cases"]
    require(type(cases) is list and len(cases) == 3,
            "protocol case denominator differs")
    require(tuple(row.get("case_id") for row in cases
                  if type(row) is dict) == EXPECTED_CASE_ORDER,
            "protocol case order differs")
    sources: set[tuple[str, str]] = set()
    clusters: set[str] = set()
    for row in cases:
        exact_keys(row, {"case_id", "condition", "cluster", "definition",
                         "source", "expected_ir"}, "case")
        case_id = row["case_id"]
        expected = EXPECTED_CASES[case_id]
        require(row["condition"] == expected["condition"]
                and row["cluster"] == expected["cluster"]
                and row["definition"] == expected["definition"],
                f"case metadata differs: {case_id}")
        source = exact_keys(row["source"], {"path", "sha256"}, "case source")
        require(source == {"path": expected["source_path"],
                           "sha256": expected["source_sha256"]},
                f"case source identity differs: {case_id}")
        expected_ir = exact_keys(row["expected_ir"],
                                 {"schema", "stage", "sha256", "bytes"},
                                 "expected IR")
        require(expected_ir == {
            "schema": IR_SCHEMA, "stage": IR_STAGE,
            "sha256": expected["ir_sha256"], "bytes": expected["ir_bytes"],
        }, f"expected IR identity differs: {case_id}")
        if verify_files:
            registered_path(source, case_id + " source", root=root)
        sources.add((source["path"], source["sha256"]))
        clusters.add(row["cluster"])
    require(len(sources) == 2 and len(clusters) == 2,
            "derived panel denominator differs")
    return list(cases)


def _imports(path: Path) -> tuple[set[str], set[str]]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, UnicodeDecodeError, SyntaxError) as error:
        raise CampaignError("cannot inspect Python import firewall: " + str(path)) from error
    modules: set[str] = set()
    dynamic: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call):
            name = ""
            if isinstance(node.func, ast.Name):
                name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                name = node.func.attr
            if name in {"__import__", "import_module", "run_module",
                        "run_path", "exec", "eval", "compile"}:
                dynamic.add(name)
    return modules, dynamic


def verify_import_firewall(generator: Path, core: Path, checker: Path,
                           adapter: Path | None = None) -> None:
    generator_imports, generator_dynamic = _imports(generator)
    core_imports, core_dynamic = _imports(core)
    checker_imports, checker_dynamic = _imports(checker)
    adapter_imports: set[str] = set()
    adapter_dynamic: set[str] = set()
    if adapter is not None:
        adapter_imports, adapter_dynamic = _imports(adapter)
    require("strong_rank_certificate_core" in generator_imports,
            "generator does not bind the registered rank core")
    require(not generator_dynamic and not core_dynamic and not checker_dynamic
            and not adapter_dynamic,
            "dynamic import/execution crosses the static firewall")
    forbidden_generator = {
        "check_generated_post_frontend_win_certificate",
        "check_post_frontend_contract_certificate",
    }
    require(not (generator_imports & forbidden_generator),
            "generator imports a checker/semantic adapter")
    require(not (core_imports & forbidden_generator)
            and "synthesize_post_frontend_win_certificate" not in core_imports,
            "rank core imports campaign semantics")
    require("check_post_frontend_contract_certificate" in checker_imports,
            "checker does not declare its shared semantic adapter")
    require("synthesize_post_frontend_win_certificate" not in checker_imports
            and "strong_rank_certificate_core" not in checker_imports,
            "checker imports generator or rank core")
    require(not (adapter_imports & {
        "synthesize_post_frontend_win_certificate",
        "strong_rank_certificate_core",
        "check_generated_post_frontend_win_certificate",
    }), "semantic adapter imports generator, rank core, or wrapper checker")


def _reject_ir_conclusions(value: Any) -> None:
    if type(value) is dict:
        for key, child in value.items():
            require(key not in FORBIDDEN_IR_KEYS,
                    "IR contains forbidden conclusion field: " + key)
            _reject_ir_conclusions(child)
    elif type(value) is list:
        for child in value:
            _reject_ir_conclusions(child)


def validate_ir(raw: bytes, case: Mapping[str, Any]) -> dict[str, Any]:
    value = load_bytes(raw, case["case_id"] + " IR")
    assert value is not None
    _reject_ir_conclusions(value)
    expected = case["expected_ir"]
    require(sha256_bytes(raw) == expected["sha256"]
            and len(raw) == expected["bytes"],
            f"fresh IR identity differs: {case['case_id']}")
    require(value.get("schema_version") == IR_SCHEMA
            and value.get("extraction_stage") == IR_STAGE
            and value.get("source_sha256") == case["source"]["sha256"]
            and value.get("definition") == case["definition"]
            and value.get("conclusion_fields_present") is False,
            f"fresh IR boundary differs: {case['case_id']}")
    for field in (
        "fixed_endpoint_products_materialized", "physical_closure_materialized",
        "activation_relations_materialized", "goal_signatures_materialized",
        "local_update_games_materialized", "global_mixed_game_materialized",
        "dependency_partition_materialized", "winning_certificate_materialized",
        "source_to_witness_replay",
    ):
        require(value.get(field) is False,
                f"fresh IR materializes forbidden stage: {field}")
    return value


def expected_facts_streams(case: Mapping[str, Any]) -> tuple[bytes, bytes]:
    stdout = (
        f"source_sha256={case['source']['sha256']}\n"
        f"definition={case['definition']}\n"
        "conclusion_fields_present=false\n"
        "terminal_record=COMPLETE\n"
    ).encode("utf-8")
    size, winning = ((65, 64) if case["cluster"] == "industry" else (82, 81))
    stderr = (
        f"Game state size:{size}\nWinning state size:{winning}\n"
        f"Game state size:{size}\nWinning state size:{winning}\n"
    ).encode("utf-8")
    return stdout, stderr


@dataclass(frozen=True)
class Invocation:
    exit_code: int
    timed_out: bool
    wall_nanos: int
    stdout: bytes
    stderr: bytes

    def receipt(self, output: bytes) -> dict[str, Any]:
        return {
            "exit_code": self.exit_code,
            "timed_out": self.timed_out,
            "wall_nanos": self.wall_nanos,
            "stdout_sha256": sha256_bytes(self.stdout),
            "stderr_sha256": sha256_bytes(self.stderr),
            "output_sha256": sha256_bytes(output),
            "output_bytes": len(output),
        }


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


def invoke(command: Sequence[str], timeout: int, cwd: Path) -> Invocation:
    started = time.monotonic_ns()
    process = subprocess.Popen(
        list(command), cwd=cwd, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        start_new_session=True,
    )
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        stdout, stderr = terminate(process)
    return Invocation(process.returncode, timed_out,
                      max(1, time.monotonic_ns() - started), stdout, stderr)


def _write(path: Path, raw: bytes) -> None:
    path.write_bytes(raw)


def _copy(path: Path, destination: Path) -> None:
    shutil.copyfile(path, destination)
    require(destination.is_file() and sha256(destination) == sha256(path),
            "isolated input copy differs: " + path.name)


def verify_jar_class_entries(jar: Path, expected: Mapping[str, str]) -> None:
    try:
        with zipfile.ZipFile(jar) as archive:
            infos = archive.infolist()
            for name, digest in expected.items():
                matches = [info for info in infos if info.filename == name]
                require(len(matches) == 1 and not matches[0].is_dir(),
                        "observation JAR class-entry census differs: " + name)
                require(sha256_bytes(archive.read(matches[0])) == digest,
                        "observation JAR class-entry hash differs: " + name)
    except CampaignError:
        raise
    except (OSError, RuntimeError, zipfile.BadZipFile) as error:
        raise CampaignError("cannot verify observation JAR entries") from error


def _run_facts(case: Mapping[str, Any], case_dir: Path, work: Path,
               jar: Path, java: str, protocol: Mapping[str, Any]) -> tuple[
                   list[dict[str, Any]], bytes]:
    rows: list[dict[str, Any]] = []
    outputs: list[bytes] = []
    for index, prefix in enumerate(("facts", "facts-repeat")):
        sandbox = work / f"facts-{index + 1}"
        sandbox.mkdir()
        source = ROOT / case["source"]["path"]
        isolated_source = sandbox / source.name
        _copy(source, isolated_source)
        isolated_output = sandbox / "facts.json"
        result = invoke([
            java, "-Xmx" + protocol["runtime"]["heap"], "-cp", str(jar),
            FACTS_CLASS, "--lts", str(isolated_source), "--definition",
            case["definition"], "--output", str(isolated_output),
        ], protocol["runtime"]["facts_timeout_seconds"], sandbox)
        raw = isolated_output.read_bytes() if isolated_output.is_file() else b""
        _write(case_dir / (prefix + ".json"), raw)
        _write(case_dir / (prefix + ".stdout.txt"), result.stdout)
        _write(case_dir / (prefix + ".stderr.txt"), result.stderr)
        require(not result.timed_out and result.exit_code == 0
                and isolated_output.is_file(),
                f"facts extraction failed: {case['case_id']}/{prefix}")
        expected_stdout, expected_stderr = expected_facts_streams(case)
        require(result.stdout == expected_stdout
                and result.stderr == expected_stderr,
                f"facts terminal diagnostics differ: {case['case_id']}/{prefix}")
        validate_ir(raw, case)
        rows.append(result.receipt(raw))
        outputs.append(raw)
    require(outputs[0] == outputs[1],
            f"fresh-JVM IR is nondeterministic: {case['case_id']}")
    return rows, outputs[0]


def _generator_command(python: str, generator: Path, ir: Path, output: Path,
                       limits: Mapping[str, Any]) -> list[str]:
    return _isolated_module_prefix(python, generator) + [
        "--ir", str(ir), "--output", str(output),
        "--max-states", str(limits["max_states"]),
        "--max-candidate-buckets", str(limits["max_candidate_buckets"]),
        "--max-outcomes", str(limits["max_outcomes"]),
        "--timeout-seconds", str(limits["generator_internal_timeout_seconds"]),
    ]


def _isolated_module_prefix(python: str, module_path: Path) -> list[str]:
    """Import one copied module with only its sandbox added to isolated sys.path."""
    bootstrap = (
        "import sys;"
        "sys.path.insert(0,sys.argv[1]);"
        "module=__import__(sys.argv[2]);"
        "raise SystemExit(module.main(sys.argv[3:]))"
    )
    return [python, "-I", "-S", "-B", "-c", bootstrap,
            str(module_path.parent), module_path.stem]


def _run_generators(case: Mapping[str, Any], case_dir: Path, work: Path,
                    python: str, generator: Path, core: Path,
                    protocol: Mapping[str, Any], ir_raw: bytes) -> tuple[
                        list[dict[str, Any]], list[Invocation], list[bytes]]:
    receipts: list[dict[str, Any]] = []
    invocations: list[Invocation] = []
    outputs: list[bytes] = []
    prefixes = ("generator", "generator-repeat")
    evidence_names = ("generated-output.json", "generated-output-repeat.json")
    for index, (prefix, evidence_name) in enumerate(zip(prefixes, evidence_names)):
        sandbox = work / f"generator-{index + 1}"
        sandbox.mkdir()
        isolated_generator = sandbox / "synthesize_post_frontend_win_certificate.py"
        isolated_core = sandbox / "strong_rank_certificate_core.py"
        isolated_ir = sandbox / "facts.json"
        isolated_output = sandbox / "generated-output.json"
        _copy(generator, isolated_generator)
        _copy(core, isolated_core)
        _write(isolated_ir, ir_raw)
        result = invoke(
            _generator_command(python, isolated_generator, isolated_ir,
                               isolated_output, protocol["limits"]),
            protocol["runtime"]["generator_timeout_seconds"], sandbox)
        raw = isolated_output.read_bytes() if isolated_output.is_file() else b""
        _write(case_dir / evidence_name, raw)
        _write(case_dir / (prefix + ".stdout.txt"), result.stdout)
        _write(case_dir / (prefix + ".stderr.txt"), result.stderr)
        invocations.append(result)
        outputs.append(raw)
        receipts.append(result.receipt(raw))
    return receipts, invocations, outputs


def _reason_status(reason: str) -> str:
    upper = reason.upper()
    if "MEMORY" in upper or "OOM" in upper:
        return "INCONCLUSIVE_OOM"
    if "TIMEOUT" in upper:
        return "INCONCLUSIVE_TIMEOUT"
    if "STATE" in upper and "LIMIT" in upper:
        return "INCONCLUSIVE_STATE_LIMIT"
    if ("BUCKET" in upper or "CANDIDATE" in upper) and "LIMIT" in upper:
        return "INCONCLUSIVE_BUCKET_LIMIT"
    if "OUTCOME" in upper and "LIMIT" in upper:
        return "INCONCLUSIVE_OUTCOME_LIMIT"
    return "INCONCLUSIVE_RANK_BOUND"


def validate_generation_document(value: Mapping[str, Any],
                                 case: Mapping[str, Any], ir_raw: bytes) -> None:
    schema = value.get("schema_version")
    if schema == CERTIFICATE_SCHEMA:
        exact_keys(value, SUCCESS_KEYS, "successful generation output")
        require(value["decision"] == "WIN",
                "success certificate decision differs")
    else:
        require(schema == "fg-ducs-post-frontend-win-synthesis-inconclusive-v1",
                "generated output schema differs")
        exact_keys(value, INCONCLUSIVE_KEYS, "inconclusive generation output")
        require(value["decision"] == "INCONCLUSIVE"
                and value["reason"] in INCONCLUSIVE_REASONS
                and value["loss_claimed"] is False
                and (value["block_index"] is None
                     or type(value["block_index"]) is int
                     and value["block_index"] >= 0),
                "inconclusive generation boundary differs")
    require(value["generator_boundary"] == GENERATOR_BOUNDARY,
            "generation boundary differs")
    require(value["ir_binding"] == {
        "sha256": sha256_bytes(ir_raw), "size": len(ir_raw),
        "source_name": ("Industry_FG.lts" if case["cluster"] == "industry"
                        else "ProductionCell_Arms=2_FG.lts"),
        "source_sha256": case["source"]["sha256"],
        "definition": case["definition"],
    }, "generation IR binding differs")


def classify_generation(invocations: Sequence[Invocation],
                        outputs: Sequence[bytes]) -> tuple[str, str,
                                                           dict[str, Any] | None]:
    require(len(invocations) == len(outputs) == 2,
            "generation repetition census differs")
    identical = outputs[0] == outputs[1]
    if all(result.timed_out for result in invocations):
        return "INCONCLUSIVE_TIMEOUT", "GENERATOR_PROCESS_TIMEOUT", None
    if any(result.timed_out for result in invocations):
        return "ERROR_CRASH", "GENERATOR_REPETITIONS_DISAGREE_ON_TIMEOUT", None
    if not identical or invocations[0].exit_code != invocations[1].exit_code:
        return "ERROR_CRASH", "GENERATOR_REPETITIONS_ARE_NONDETERMINISTIC", None
    if any(result.stdout for result in invocations):
        return "ERROR_CRASH", "GENERATOR_UNEXPECTED_STDOUT", None
    code = invocations[0].exit_code
    try:
        value = load_bytes(outputs[0], "generated output", canonical_required=True,
                           allow_empty=True)
    except CampaignError:
        value = None
    if code == 0 and value is not None \
            and value.get("schema_version") == CERTIFICATE_SCHEMA \
            and value.get("decision") == "WIN" \
            and not any(result.stderr for result in invocations):
        return "SUCCESS_WIN", "GENERATED_STRONG_WIN_CERTIFICATE", value
    if code == 2:
        if invocations[0].stderr != invocations[1].stderr:
            return "ERROR_CRASH", "GENERATOR_REPETITIONS_DISAGREE_ON_STDERR", value
        reason: str | None = None
        if value is not None:
            if type(value.get("reason")) is str:
                reason = value["reason"]
        elif outputs[0] == b"":
            marker = b"POST_FRONTEND_WIN_SYNTHESIS_INCONCLUSIVE="
            for line in invocations[0].stderr.splitlines():
                if line.startswith(marker):
                    try:
                        reason = line[len(marker):].decode("utf-8")
                    except UnicodeDecodeError:
                        reason = None
                    break
            if reason != "MEMORY_EXHAUSTED":
                return "ERROR_CRASH", "GENERATOR_MISSING_INCONCLUSIVE_OUTPUT", None
        else:
            return "ERROR_CRASH", "GENERATOR_MALFORMED_INCONCLUSIVE_OUTPUT", None
        if reason is None:
            return "ERROR_CRASH", "GENERATOR_INCONCLUSIVE_REASON_MISSING", value
        expected_stderr = (
            "POST_FRONTEND_WIN_SYNTHESIS_INCONCLUSIVE=" + reason + "\n"
        ).encode("utf-8")
        if invocations[0].stderr != expected_stderr:
            return "ERROR_CRASH", "GENERATOR_INCONCLUSIVE_MARKER_DIFFERS", value
        return _reason_status(reason), reason, value
    if code == 3:
        marker = b"POST_FRONTEND_WIN_SYNTHESIS_INVALID="
        if (outputs[0] == b"" and value is None
                and invocations[0].stderr == invocations[1].stderr
                and invocations[0].stderr.startswith(marker)
                and invocations[0].stderr.endswith(b"\n")
                and len(invocations[0].stderr) > len(marker) + 1):
            try:
                reason = invocations[0].stderr[len(marker):-1].decode("utf-8")
            except UnicodeDecodeError:
                reason = "GENERATOR_INVALID_MARKER_NOT_UTF8"
            return "INVALID_INPUT", reason, None
        return "ERROR_CRASH", "GENERATOR_INVALID_TERMINAL_DIFFERS", value
    return "ERROR_CRASH", f"GENERATOR_EXIT_{code}", value


def build_generation_seal(
    case: Mapping[str, Any], protocol_path: Path,
    protocol: Mapping[str, Any], ir_raw: bytes,
    outputs: Sequence[bytes], invocations: Sequence[Invocation],
    generation_status: str, generation_reason: str,
) -> dict[str, Any]:
    files = protocol["registered_files"]
    return {
        "schema_version": SEAL_SCHEMA,
        "campaign_id": CAMPAIGN_ID,
        "case_id": case["case_id"],
        "protocol_sha256": sha256(protocol_path),
        "source_sha256": case["source"]["sha256"],
        "definition": case["definition"],
        "ir_sha256": sha256_bytes(ir_raw),
        "ir_bytes": len(ir_raw),
        "generator_sha256": files["generator"]["sha256"],
        "rank_core_sha256": files["rank_core"]["sha256"],
        "generation_output_sha256": sha256_bytes(outputs[0]),
        "generation_output_bytes": len(outputs[0]),
        "generation_repeat_sha256": sha256_bytes(outputs[1]),
        "generation_repeat_bytes": len(outputs[1]),
        "generation_outputs_byte_identical": outputs[0] == outputs[1],
        "generator_exit_codes": [row.exit_code for row in invocations],
        "generator_timed_out": [row.timed_out for row in invocations],
        "generation_status": generation_status,
        "generation_reason": generation_reason,
        "historical_outcome_inputs": 0,
        "supplied_certificate_inputs": 0,
        "checker_started": False,
        "phase_order": [
            "facts-1", "facts-2", "generator-1", "generator-2",
            "generation-seal",
        ],
        "generator_argv_contract": [
            "--ir", "--output", "--max-states",
            "--max-candidate-buckets", "--max-outcomes", "--timeout-seconds",
        ],
    }


def validate_generation_seal(
    seal: Mapping[str, Any], case: Mapping[str, Any], protocol_path: Path,
    protocol: Mapping[str, Any], ir_raw: bytes, outputs: Sequence[bytes],
) -> None:
    expected = build_generation_seal(
        case, protocol_path, protocol, ir_raw, outputs,
        [Invocation(code, timed, 1, b"", b"") for code, timed in zip(
            seal.get("generator_exit_codes", []),
            seal.get("generator_timed_out", []))],
        seal.get("generation_status"), seal.get("generation_reason"),
    )
    require(seal == expected, "generation seal binding differs")


def _checker_not_run(status: str, reason: str) -> dict[str, Any]:
    return {
        "schema_version": NOT_RUN_SCHEMA,
        "status": "NOT_RUN_GENERATION_NON_SUCCESS",
        "generation_status": status,
        "generation_reason": reason,
    }


def _run_checker(case: Mapping[str, Any], case_dir: Path, work: Path,
                 python: str, checker: Path, adapter: Path,
                 protocol: Mapping[str, Any], ir_raw: bytes,
                 certificate_raw: bytes) -> tuple[
                     dict[str, Any] | None, Invocation, bytes]:
    sandbox = work / "checker"
    sandbox.mkdir()
    isolated_checker = sandbox / "check_generated_post_frontend_win_certificate.py"
    isolated_adapter = sandbox / "check_post_frontend_contract_certificate.py"
    isolated_ir = sandbox / "facts.json"
    isolated_certificate = sandbox / "generated-output.json"
    isolated_report = sandbox / "checker-report.json"
    _copy(checker, isolated_checker)
    _copy(adapter, isolated_adapter)
    _write(isolated_ir, ir_raw)
    _write(isolated_certificate, certificate_raw)
    result = invoke(_isolated_module_prefix(python, isolated_checker) + [
        "--ir", str(isolated_ir), "--certificate", str(isolated_certificate),
        "--output", str(isolated_report),
    ], protocol["runtime"]["checker_timeout_seconds"], sandbox)
    raw = isolated_report.read_bytes() if isolated_report.is_file() else b""
    _write(case_dir / "checker-report.json", raw)
    _write(case_dir / "checker.stdout.txt", result.stdout)
    _write(case_dir / "checker.stderr.txt", result.stderr)
    report = None
    if raw:
        report = load_bytes(raw, case["case_id"] + " checker report",
                            canonical_required=True)
    return report, result, raw


def validate_check_report(report: Mapping[str, Any], case: Mapping[str, Any],
                          ir_raw: bytes) -> None:
    exact_keys(report, CHECK_REPORT_KEYS, "checker report")
    require(report["schema_version"] == CHECK_REPORT_SCHEMA
            and report["status"] == CHECK_STATUS
            and report["source_sha256"] == case["source"]["sha256"]
            and report["definition"] == case["definition"]
            and report["ir_exact_byte_sha256"] == sha256_bytes(ir_raw)
            and report["ir_exact_byte_size"] == len(ir_raw)
            and report["claim_boundary"] == CHECK_CLAIM_BOUNDARY,
            f"checker report binding differs: {case['case_id']}")
    if case["case_id"] == "industry-base-industry-fg":
        require(report["whole_system_block"] is True
                and report["nontrivial_factorization"] is False,
                "Industry must remain an explicit one-block result")
    else:
        require(report["whole_system_block"] is False
                and report["nontrivial_factorization"] is True,
                "ProductionCell must remain a nontrivial partition")


def _final_status(generation_status: str, generation_reason: str,
                  report: Mapping[str, Any] | None,
                  checker: Invocation | None) -> tuple[str, str]:
    if generation_status != "SUCCESS_WIN":
        return generation_status, generation_reason
    assert checker is not None
    if checker.timed_out:
        return "INCONCLUSIVE_TIMEOUT", "CHECKER_PROCESS_TIMEOUT"
    if checker.exit_code == 0 and report is not None:
        return "SUCCESS_WIN", "GENERATED_CERTIFICATE_SEMANTICALLY_VERIFIED"
    if checker.exit_code == 2:
        return "CERTIFICATE_REJECTED", "CHECKER_REJECTED_GENERATED_CERTIFICATE"
    return "ERROR_CRASH", f"CHECKER_EXIT_{checker.exit_code}"


def run_case(case: Mapping[str, Any], protocol_path: Path,
             protocol: Mapping[str, Any], case_dir: Path, work: Path,
             jar: Path, java: str, python: str) -> dict[str, Any]:
    case_dir.mkdir(parents=True)
    files = protocol["registered_files"]
    generator = registered_path(files["generator"], "generator")
    core = registered_path(files["rank_core"], "rank core")
    checker = registered_path(files["checker"], "checker")
    adapter = registered_path(files["semantic_adapter"], "semantic adapter")
    facts_runs, ir_raw = _run_facts(case, case_dir, work, jar, java, protocol)
    generator_runs, generator_invocations, outputs = _run_generators(
        case, case_dir, work, python, generator, core, protocol, ir_raw)
    generation_status, generation_reason, _generated = classify_generation(
        generator_invocations, outputs)
    if _generated is not None:
        validate_generation_document(_generated, case, ir_raw)

    # This write is the acceptance boundary: it always precedes checker start.
    seal = build_generation_seal(
        case, protocol_path, protocol, ir_raw, outputs,
        generator_invocations, generation_status, generation_reason)
    seal_raw = canonical(seal)
    _write(case_dir / "generation-seal.json", seal_raw)

    checker_result: Invocation | None = None
    checker_report: dict[str, Any] | None = None
    checker_raw: bytes
    if generation_status == "SUCCESS_WIN":
        checker_report, checker_result, checker_raw = _run_checker(
            case, case_dir, work, python, checker, adapter, protocol,
            ir_raw, outputs[0])
        if (not checker_result.timed_out and checker_result.exit_code == 0
                and checker_report is not None):
            validate_check_report(checker_report, case, ir_raw)
    else:
        checker_raw = canonical(_checker_not_run(
            generation_status, generation_reason))
        _write(case_dir / "checker-report.json", checker_raw)
        _write(case_dir / "checker.stdout.txt", b"")
        _write(case_dir / "checker.stderr.txt", b"")

    status, reason = _final_status(
        generation_status, generation_reason, checker_report, checker_result)
    checker_receipt = {
        "started": checker_result is not None,
        "exit_code": None if checker_result is None else checker_result.exit_code,
        "timed_out": False if checker_result is None else checker_result.timed_out,
        "wall_nanos": 0 if checker_result is None else checker_result.wall_nanos,
        "stdout_sha256": sha256(case_dir / "checker.stdout.txt"),
        "stderr_sha256": sha256(case_dir / "checker.stderr.txt"),
        "output_sha256": sha256_bytes(checker_raw),
        "output_bytes": len(checker_raw),
    }
    record = {
        "schema_version": RECORD_SCHEMA,
        "case_id": case["case_id"],
        "condition": case["condition"],
        "cluster": case["cluster"],
        "definition": case["definition"],
        "source": case["source"],
        "ir": {
            "path": f"cases/{case['case_id']}/facts.json",
            "repeat_path": f"cases/{case['case_id']}/facts-repeat.json",
            "sha256": sha256_bytes(ir_raw), "bytes": len(ir_raw),
            "fresh_jvm_byte_determinism": True,
        },
        "facts_runs": facts_runs,
        "generator_runs": generator_runs,
        "generation_status": generation_status,
        "generation_reason": generation_reason,
        "generation_outputs_byte_identical": (
            bool(outputs[0]) and outputs[0] == outputs[1]),
        "generation_seal_path": f"cases/{case['case_id']}/generation-seal.json",
        "generation_seal_sha256": sha256_bytes(seal_raw),
        "seal_written_before_checker": True,
        "checker": checker_receipt,
        "checker_report_path": f"cases/{case['case_id']}/checker-report.json",
        "checker_report_sha256": sha256_bytes(checker_raw),
        "status": status,
        "reason": reason,
        "loss_claimed": False,
        "historical_outcome_inputs": 0,
        "supplied_certificate_inputs": 0,
        "semantic_digest_sha256": (
            checker_report.get("semantic_digest_sha256")
            if checker_report is not None and status == "SUCCESS_WIN" else None),
        "component_partition": (
            checker_report.get("component_partition")
            if checker_report is not None and status == "SUCCESS_WIN" else None),
        "whole_system_block": (
            checker_report.get("whole_system_block")
            if checker_report is not None and status == "SUCCESS_WIN" else None),
        "nontrivial_factorization": (
            checker_report.get("nontrivial_factorization")
            if checker_report is not None and status == "SUCCESS_WIN" else None),
        "totals": (checker_report.get("totals")
                   if checker_report is not None and status == "SUCCESS_WIN" else None),
        "transport": (checker_report.get("transport")
                      if checker_report is not None and status == "SUCCESS_WIN" else None),
    }
    _write(case_dir / "record.json", canonical(record))
    observed = {path.name for path in case_dir.iterdir() if path.is_file()}
    require(observed == CASE_FILES,
            f"case evidence file census differs: {case['case_id']}")
    return record


def build_summary(protocol_path: Path, records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    status_counts = {status: 0 for status in FAILURE_TAXONOMY}
    for record in records:
        status_counts[record["status"]] += 1
    success = [record for record in records if record["status"] == "SUCCESS_WIN"]
    totals: dict[str, int] = {}
    transport: dict[str, int] = {}
    for record in success:
        for key, value in record["totals"].items():
            totals[key] = totals.get(key, 0) + value
        for key, value in record["transport"].items():
            transport[key] = transport.get(key, 0) + value
    return {
        "schema_version": SUMMARY_SCHEMA,
        "campaign_id": CAMPAIGN_ID,
        "protocol_sha256": sha256(protocol_path),
        "source_files": 2,
        "target_cells": 3,
        "provenance_clusters": 2,
        "conclusion_free_ir_inputs": 3,
        "historical_outcome_inputs": 0,
        "supplied_certificate_inputs": 0,
        "facts_executions": 6,
        "fresh_jvm_facts_deterministic": 3,
        "generation_executions": 6,
        "automatic_retry_executions": 0,
        "fresh_generation_outputs_deterministic": sum(
            record["generation_outputs_byte_identical"] is True
            for record in records),
        "generated_win_certificates": sum(
            record["generation_status"] == "SUCCESS_WIN" for record in records),
        "verified_generated_win_certificates": len(success),
        "status_counts": status_counts,
        "nontrivial_factorization_cells": sum(
            record["nontrivial_factorization"] is True for record in success),
        "whole_system_block_cells": sum(
            record["whole_system_block"] is True for record in success),
        "verified_totals": dict(sorted(totals.items())),
        "verified_transport_totals": dict(sorted(transport.items())),
        "records": [{
            "case_id": record["case_id"],
            "path": f"cases/{record['case_id']}/record.json",
            "sha256": "",  # Filled after canonical record bytes exist.
            "status": record["status"],
        } for record in records],
        "claim_boundary": CLAIM_BOUNDARY,
        "status": ("ALL_GENERATED_WIN_CERTIFICATES_VERIFIED"
                   if len(success) == 3 else "TERMINAL_WITH_NON_SUCCESS"),
    }


def _fill_record_hashes(summary: dict[str, Any], evidence: Path) -> None:
    for row in summary["records"]:
        row["sha256"] = sha256(evidence / row["path"])


def write_sha256sums(evidence: Path) -> None:
    rows = []
    for path in sorted(evidence.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS":
            require(not path.is_symlink(), "evidence contains a symlink")
            rows.append(f"{sha256(path)}  {path.relative_to(evidence).as_posix()}\n")
    _write(evidence / "SHA256SUMS", "".join(rows).encode("utf-8"))


def atomic_campaign(output: Path, builder: Callable[[Path], Any]) -> Any:
    require(not output.exists(), "output already exists")
    require(output.parent.is_dir() and not output.parent.is_symlink(),
            "output parent is absent or a symlink")
    scratch = Path(tempfile.mkdtemp(prefix="." + output.name + ".",
                                    dir=output.parent))
    try:
        result = builder(scratch)
        os.rename(scratch, output)
        return result
    except BaseException:
        shutil.rmtree(scratch, ignore_errors=True)
        raise


def absolute_cli_path(path: Path) -> Path:
    """Freeze a CLI path against the caller cwd without following symlinks."""
    return Path(os.path.abspath(os.fspath(path)))


def absolute_executable(command: str, label: str) -> str:
    require(type(command) is str and bool(command), label + " is not text")
    resolved = shutil.which(command)
    require(resolved is not None, label + " is not executable")
    return os.path.abspath(resolved)


def run(protocol_path: Path, jar: Path, output: Path, java: str,
        python: str) -> dict[str, Any]:
    protocol_path = absolute_cli_path(protocol_path)
    jar = absolute_cli_path(jar)
    output = absolute_cli_path(output)
    java = absolute_executable(java, "Java command")
    python = absolute_executable(python, "Python command")
    require(protocol_path.is_file() and not protocol_path.is_symlink(),
            "protocol is absent or a symlink")
    protocol = load(protocol_path)
    cases = verify_protocol(protocol)
    require(jar.is_file() and not jar.is_symlink(),
            "observation JAR is absent or a symlink")
    require(sha256(jar) == protocol["runtime"]["observation_jar_sha256"],
            "observation JAR hash differs")
    verify_jar_class_entries(jar, protocol["runtime"]["class_entries"])
    audit_script = registered_path(
        protocol["registered_files"]["offline_audit"], "offline audit")

    def build(scratch: Path) -> dict[str, Any]:
        cases_root = scratch / "cases"
        cases_root.mkdir()
        work_root = scratch / ".work"
        work_root.mkdir()
        records = []
        for case in cases:
            case_work = work_root / case["case_id"]
            case_work.mkdir()
            records.append(run_case(
                case, protocol_path, protocol,
                cases_root / case["case_id"], case_work,
                jar, java, python))
        shutil.rmtree(work_root)
        summary = build_summary(protocol_path, records)
        _fill_record_hashes(summary, scratch)
        _write(scratch / "summary.json", canonical(summary))

        audit_path = scratch / "audit.json"
        preaudit = invoke([
            python, "-I", "-S", "-B", str(audit_script),
            "--protocol", str(protocol_path), "--evidence", str(scratch),
            "--prepublish", "--output", str(audit_path),
        ], protocol["runtime"]["audit_timeout_seconds"], ROOT)
        require(preaudit.exit_code == 0 and not preaudit.timed_out
                and preaudit.stdout == b"" and preaudit.stderr == b""
                and audit_path.is_file(), "prepublication audit failed")
        write_sha256sums(scratch)
        final_audit = invoke([
            python, "-I", "-S", "-B", str(audit_script),
            "--protocol", str(protocol_path), "--evidence", str(scratch),
            "--expected", str(audit_path),
        ], protocol["runtime"]["audit_timeout_seconds"], ROOT)
        require(final_audit.exit_code == 0 and not final_audit.timed_out
                and final_audit.stderr == b""
                and final_audit.stdout == audit_path.read_bytes(),
                "final offline audit failed")
        return summary

    return atomic_campaign(output, build)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--jar", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--java", default="java")
    parser.add_argument("--python", default=sys.executable)
    args = parser.parse_args(argv)
    try:
        run(args.protocol, args.jar, args.output, args.java, args.python)
        return 0
    except (CampaignError, OSError, subprocess.SubprocessError) as error:
        print("POST_FRONTEND_GENERATED_WIN_PANEL_INVALID=" + str(error),
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
