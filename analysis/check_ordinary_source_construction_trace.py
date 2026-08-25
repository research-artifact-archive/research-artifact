#!/usr/bin/env python3
"""Check the manifest-bound ProductionCell SourceIn-to-recorded-Y trace.

The trace exposes all sixteen SourceIn bindings, S0--S4 intermediates and
predicate outcomes, all ten recorded Y fields, and the S1--S7 theorem map for
the existing ProductionCell Arms=2 R2 evidence.  It joins the exact raw source,
post-outcome protocols, conclusion-free facts, historical producer bundle, and
the saved outputs of two deterministic same-author Python semantic checkers.

This checker validates the stored-byte and semantic-report chain.  The existing
M8t audit (run separately by ``tools/verify.py``) freshly reruns both semantic
checkers.  Neither operation reruns the historical Java producer, synthesizes a
new WIN result, or establishes a general/independent source-to-WIN pipeline.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
CASE = "productioncell-arms2-r2-productioncell-arms-2-fg"
SOURCE_REL = "Implementation/Experiment/Models/ProductionCell_Arms=2_FG.lts"
TRACE_REL = "evidence/ordinary-source-construction-trace/productioncell-arms2-r2-trace.json"
INPUT_PATHS = {
    "flat_fixture": "inputs/c2/typed-partition-predicate-example.json",
    "flat_trace": "evidence/m8p-partition-discovery/predicate-trace-example.json",
    "flat_trace_checker": "analysis/trace_typed_partition_predicate.py",
    "source": SOURCE_REL,
    "native_protocol": "protocols/native_factorization_panel_v1_20260814.json",
    "panel_summary": "evidence/m8q-native-factorization/panel/summary.json",
    "m8q_record": f"evidence/m8q-native-factorization/panel/cases/{CASE}/record.json",
    "bundle": f"evidence/m8q-native-factorization/panel/cases/{CASE}/bundle.json",
    "m8s_protocol": "protocols/post_frontend_contract_certificate_v1_20260814.json",
    "facts": f"evidence/m8s-post-frontend-contract-certificate/cases/{CASE}/facts.json",
    "m8t_protocol": "protocols/productioncell_source_contract_certificate_v1_20260814.json",
    "source_report": f"evidence/m8t-productioncell-source-contract-certificate/cases/{CASE}/source-report.json",
    "downstream_report": f"evidence/m8t-productioncell-source-contract-certificate/cases/{CASE}/downstream-report.json",
    "m8t_record": f"evidence/m8t-productioncell-source-contract-certificate/cases/{CASE}/record.json",
    "m8t_summary": "evidence/m8t-productioncell-source-contract-certificate/summary.json",
    "m8t_audit": "evidence/m8t-productioncell-source-contract-certificate/audit.json",
    "source_checker": "analysis/check_productioncell_source_contract_certificate.py",
    "downstream_checker": "analysis/check_post_frontend_contract_certificate.py",
    "m8t_auditor": "analysis/audit_productioncell_source_contract_certificate.py",
    "trace_checker": "analysis/check_ordinary_source_construction_trace.py",
}
SOURCE_FIELDS = (
    "bytes", "dialect", "entry", "C", "E_old", "E_new", "g", "M_old",
    "M_new", "M_upd", "O", "Act", "Prot", "Sigma_c_N", "Lambda", "b",
)
Y_FIELDS = ("e", "f", "s", "B", "C_D", "L", "n_old", "n_new", "v", "Gamma")
EXPECTED_SOURCE_SHA256 = "117210fa93185f5a814ad7debbdfcde00720019312c4ef68446a844700084e43"
EXPECTED_SOURCE_BYTES = 35_136
EXPECTED_DEFINITION = "UpdCont_OTF_FG_R2"
EXPECTED_VERIFIED_FIELDS = {
    "components", "transfer_relations", "old_safety_machines",
    "new_safety_machines", "transition_requirement_machines",
    "observer_machines", "observer_registry", "new_activation_sources",
    "controllers", "protocol", "controllable_actions", "flags",
    "boundary_actions", "load_selector",
}
EXPECTED_FLAT_PREMISE_KEYS = {
    "ambient_state_product", "asynchronous_frame_product", "goal_product",
    "handover_product", "load_product", "local_goals_are_uncontrollably_quiescent",
    "nonempty_projected_roots", "root_projection_with_extra_rectangularity",
    "safe_conjunction", "shared_actions_are_controllable_pure_stutters",
    "typed_metadata_block_local",
}


class TraceError(RuntimeError):
    pass


def reject_constant(value: str) -> Any:
    raise TraceError(f"non-finite JSON number: {value}")


def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise TraceError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicates,
            parse_constant=reject_constant,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise TraceError(f"invalid JSON: {path}") from error
    if not isinstance(value, dict):
        raise TraceError(f"JSON root is not an object: {path}")
    return value


def require(condition: bool, message: str) -> None:
    if not condition:
        raise TraceError(message)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def manifest_entry(root: Path, relative: str) -> dict[str, Any]:
    pure = PurePosixPath(relative)
    require(not pure.is_absolute() and pure.parts and ".." not in pure.parts, "unsafe path")
    path = root.joinpath(*pure.parts)
    require(path.is_file() and not path.is_symlink(), f"missing regular input: {relative}")
    return {"path": relative, "bytes": path.stat().st_size, "sha256": sha256_file(path)}


def value_shape(value: Any) -> dict[str, Any]:
    if isinstance(value, bool):
        kind, count = "boolean", 1
    elif type(value) is int:
        kind, count = "integer", 1
    elif isinstance(value, str):
        kind, count = "string", 1
    elif isinstance(value, list):
        kind, count = "array", len(value)
    elif isinstance(value, dict):
        kind, count = "object", len(value)
    else:
        raise TraceError(f"unsupported value type: {type(value).__name__}")
    return {
        "type": kind,
        "count": count,
        "canonical_sha256": sha256_bytes(canonical_bytes(value)),
    }


def resolve_pointer(document: Any, pointer: str) -> Any:
    require(pointer == "" or pointer.startswith("/"), "JSON pointer is not RFC 6901")
    current = document
    if pointer == "":
        return current
    for raw_token in pointer[1:].split("/"):
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict):
            require(token in current, f"JSON pointer key is absent: {pointer}")
            current = current[token]
        elif isinstance(current, list):
            require(token.isdigit() and int(token) < len(current), f"JSON pointer index is absent: {pointer}")
            current = current[int(token)]
        else:
            raise TraceError(f"JSON pointer traverses a scalar: {pointer}")
    return current


def resolve_ref(documents: Mapping[str, Any], ref: Mapping[str, str]) -> Any:
    manifest_key = ref.get("manifest_key")
    pointer = ref.get("rfc6901")
    require(isinstance(manifest_key, str) and manifest_key in documents, "unknown manifest key in value ref")
    require(isinstance(pointer, str), "value ref lacks RFC 6901 pointer")
    return resolve_pointer(documents[manifest_key], pointer)


def construct_value(documents: Mapping[str, Any], refs: Sequence[Mapping[str, str]], construction: Mapping[str, Any]) -> Any:
    values = [resolve_ref(documents, ref) for ref in refs]
    operation = construction.get("op")
    if operation == "IDENTITY":
        require(len(values) == 1, "IDENTITY construction requires one ref")
        return values[0]
    if operation == "ARRAY_PROJECT":
        require(len(values) == 1 and isinstance(values[0], list), "ARRAY_PROJECT requires one array ref")
        keys = construction.get("keys")
        require(isinstance(keys, list) and keys and all(isinstance(key, str) for key in keys), "ARRAY_PROJECT keys differ")
        require(all(isinstance(row, dict) for row in values[0]), "ARRAY_PROJECT source row differs")
        return [{key: row.get(key) for key in keys} for row in values[0]]
    if operation == "OBJECT":
        fields = construction.get("fields")
        require(isinstance(fields, dict) and set(fields.values()) == set(range(len(values))), "OBJECT construction indices differ")
        return {name: values[index] for name, index in fields.items()}
    raise TraceError(f"unknown construction operation: {operation}")


def binding(
    documents: Mapping[str, Any],
    ordinal: int,
    name: str,
    value: Any,
    value_refs: Sequence[Mapping[str, str]],
    construction: Mapping[str, Any],
    basis: str,
    note: str,
    validation_refs: Sequence[Mapping[str, str]] = (),
) -> dict[str, Any]:
    require(construct_value(documents, value_refs, construction) == value, f"constructed value differs: {name}")
    for ref in validation_refs:
        resolve_ref(documents, ref)
    return {
        "ordinal": ordinal,
        "field": name,
        "status": "PASS",
        "basis": basis,
        "value_refs": [dict(ref) for ref in value_refs],
        "construction": dict(construction),
        "validation_refs": [dict(ref) for ref in validation_refs],
        "value_shape": value_shape(value),
        "value": value if isinstance(value, (bool, int, str)) else None,
        "note": note,
    }


def json_ref(manifest_key: str, pointer: str) -> dict[str, str]:
    require(pointer == "" or pointer.startswith("/"), "JSON pointer is not RFC 6901")
    return {"manifest_key": manifest_key, "rfc6901": pointer}


def byte_binding() -> dict[str, Any]:
    return {
        "ordinal": 1,
        "field": "bytes",
        "status": "PASS",
        "basis": "RECORDED_BYTES",
        "value_type": "byte_string",
        "value_refs": [{"manifest_key": "source", "representation": "raw_byte_string"}],
        "construction": "identity(raw bytes)",
        "value_shape": {
            "type": "byte_string",
            "bytes": EXPECTED_SOURCE_BYTES,
            "sha256": EXPECTED_SOURCE_SHA256,
        },
        "length_bytes": EXPECTED_SOURCE_BYTES,
        "sha256": EXPECTED_SOURCE_SHA256,
        "value": None,
        "note": "exact ordinary-LTS byte string; path, length, and digest are manifest metadata rather than the SourceIn value",
    }


def predicate(
    identifier: str,
    expected: Any,
    actual: Any,
    basis: str,
    evidence: Sequence[str],
    limitation: str = "NONE",
) -> dict[str, Any]:
    require(actual == expected, f"predicate differs: {identifier}")
    return {
        "id": identifier,
        "expected": expected,
        "actual": actual,
        "status": "PASS",
        "basis": basis,
        "evidence": list(evidence),
        "limitation": limitation,
    }


def theorem_row(
    identifier: str,
    statement: str,
    evidence: Sequence[str],
    limitation: str,
) -> dict[str, Any]:
    return {
        "premise_id": identifier,
        "mapping_status": "MAPPED",
        "evidence_status": "CHECKED_WITHIN_SUPPLIED_SYMBOLIC_CONTRACT",
        "basis": "DETERMINISTIC_SOURCE_AND_SUPPLIED_CERTIFICATE_CHECKERS",
        "statement": statement,
        "evidence": list(evidence),
        "limitation": limitation,
        "global_mixed_game_materialized": False,
        "independent_win_synthesis": False,
        "source_to_win_replay": False,
    }


def panel_record(summary: Mapping[str, Any]) -> dict[str, Any]:
    records = summary.get("records")
    require(isinstance(records, list), "panel records are absent")
    matches = [row for row in records if isinstance(row, dict) and row.get("case_id") == CASE]
    require(len(matches) == 1, "panel does not contain exactly one target record")
    return matches[0]


def derive(root: Path) -> dict[str, Any]:
    manifest = {name: manifest_entry(root, relative) for name, relative in INPUT_PATHS.items()}
    require(manifest["source"]["sha256"] == EXPECTED_SOURCE_SHA256, "source digest differs")
    require(manifest["source"]["bytes"] == EXPECTED_SOURCE_BYTES, "source byte count differs")

    flat_fixture = load_json(root / INPUT_PATHS["flat_fixture"])
    flat_trace = load_json(root / INPUT_PATHS["flat_trace"])
    native_protocol = load_json(root / INPUT_PATHS["native_protocol"])
    panel_summary = load_json(root / INPUT_PATHS["panel_summary"])
    record = load_json(root / INPUT_PATHS["m8q_record"])
    bundle = load_json(root / INPUT_PATHS["bundle"])
    m8s_protocol = load_json(root / INPUT_PATHS["m8s_protocol"])
    facts = load_json(root / INPUT_PATHS["facts"])
    m8t_protocol = load_json(root / INPUT_PATHS["m8t_protocol"])
    source_report = load_json(root / INPUT_PATHS["source_report"])
    downstream = load_json(root / INPUT_PATHS["downstream_report"])
    m8t_record = load_json(root / INPUT_PATHS["m8t_record"])
    m8t_summary = load_json(root / INPUT_PATHS["m8t_summary"])
    m8t_audit = load_json(root / INPUT_PATHS["m8t_audit"])
    documents = {
        "flat_fixture": flat_fixture, "flat_trace": flat_trace,
        "native_protocol": native_protocol, "panel_summary": panel_summary,
        "m8q_record": record, "bundle": bundle, "m8s_protocol": m8s_protocol,
        "facts": facts, "m8t_protocol": m8t_protocol,
        "source_report": source_report, "downstream_report": downstream,
        "m8t_record": m8t_record, "m8t_summary": m8t_summary,
        "m8t_audit": m8t_audit,
    }

    require(flat_trace.get("schema_version") == "fg-ducs-typed-partition-predicate-trace-v1", "flat trace schema differs")
    require(flat_trace.get("input_game_sha256") == sha256_bytes(canonical_bytes(flat_fixture) + b"\n"), "flat fixture binding differs")
    require(flat_trace.get("unit_partition_count") == 2, "flat partition coverage differs")
    require(flat_trace.get("first_accepted_block_count") == 2, "flat maximum differs")
    require(flat_trace.get("all_accepted_candidates_transport_ready") is True, "flat transport mapping differs")
    flat_partitions = flat_trace.get("partitions")
    require(isinstance(flat_partitions, list) and len(flat_partitions) == 2, "flat partition rows differ")
    require(flat_partitions[0].get("accepted") is True and flat_partitions[0].get("block_count") == 2, "flat selected candidate differs")
    require(flat_trace.get("selected_partition") == flat_partitions[0].get("partition"), "flat selected partition differs")
    require(flat_partitions[0].get("theorem_5_3_transport_ready") is True, "flat theorem transport differs")
    flat_premises = flat_partitions[0].get("theorem_5_3_premises")
    require(isinstance(flat_premises, dict) and set(flat_premises) == EXPECTED_FLAT_PREMISE_KEYS and all(value is True for value in flat_premises.values()), "flat theorem-premise mapping differs")

    require(panel_summary.get("protocol_sha256") == manifest["native_protocol"]["sha256"], "native protocol binding differs")
    require(panel_summary.get("jar_sha256") == native_protocol.get("runtime", {}).get("jar_sha256"), "historical JAR binding differs")
    require(panel_record(panel_summary) == record, "panel and case records differ")
    require(record.get("bundle_sha256") == manifest["bundle"]["sha256"], "record/bundle digest differs")
    require(record.get("bundle_bytes") == manifest["bundle"]["bytes"], "record/bundle size differs")
    require(record.get("sha256") == EXPECTED_SOURCE_SHA256, "record/source digest differs")
    require(record.get("path") == SOURCE_REL, "record/source path differs")
    require(record.get("definition") == EXPECTED_DEFINITION, "record definition differs")
    require(bundle.get("source_sha256") == EXPECTED_SOURCE_SHA256, "bundle/source digest differs")
    require(bundle.get("definition") == EXPECTED_DEFINITION, "bundle definition differs")
    require(facts.get("source_sha256") == EXPECTED_SOURCE_SHA256, "facts/source digest differs")
    require(facts.get("definition") == EXPECTED_DEFINITION, "facts definition differs")
    require(source_report.get("source_sha256") == EXPECTED_SOURCE_SHA256, "source-report digest differs")
    require(source_report.get("definition") == EXPECTED_DEFINITION, "source-report definition differs")
    require(downstream.get("source_sha256") == EXPECTED_SOURCE_SHA256, "downstream source digest differs")
    require(downstream.get("definition") == EXPECTED_DEFINITION, "downstream definition differs")

    require(m8t_record.get("source_sha256") == EXPECTED_SOURCE_SHA256, "M8t source binding differs")
    require(m8t_record.get("source_path") == SOURCE_REL, "M8t source path differs")
    require(m8t_record.get("facts_sha256") == manifest["facts"]["sha256"], "M8t facts binding differs")
    require(m8t_record.get("historical_bundle_sha256") == manifest["bundle"]["sha256"], "M8t bundle binding differs")
    require(m8t_record.get("source_report_sha256") == manifest["source_report"]["sha256"], "M8t source report binding differs")
    require(m8t_record.get("downstream_report_sha256") == manifest["downstream_report"]["sha256"], "M8t downstream binding differs")
    require(m8t_audit.get("protocol_sha256") == manifest["m8t_protocol"]["sha256"], "M8t protocol binding differs")
    require(m8t_audit.get("summary_sha256") == manifest["m8t_summary"]["sha256"], "M8t summary binding differs")
    require(m8s_protocol.get("schema_version") == "fg-ducs-post-frontend-certificate-protocol-v1", "M8s protocol differs")
    require(m8t_protocol.get("schema_version") == "fg-ducs-productioncell-source-certificate-protocol-v1", "M8t protocol differs")
    require(m8t_audit.get("status") == "SOURCE_TO_SUPPLIED_CERTIFICATE_SEMANTICS_VERIFIED", "M8t audit status differs")
    require(m8t_audit.get("source_to_post_frontend_contract_semantic_verification") == 2, "M8t source-check census differs")
    require(m8t_audit.get("post_frontend_contract_to_supplied_certificate_semantic_verification") == 2, "M8t downstream-check census differs")
    require(m8t_audit.get("source_to_win_replay") == 0, "M8t source-to-WIN boundary differs")
    require(m8t_audit.get("independent_win_synthesis") == 0, "M8t independent-WIN boundary differs")
    audit_boundary = m8t_audit.get("claim_boundary", {})
    require(audit_boundary.get("historical_m8s_runtime_reproduced") is False, "M8t historical-runtime boundary differs")
    require(audit_boundary.get("general_mtsa_frontend") is False, "M8t general-frontend boundary differs")
    require(audit_boundary.get("source_to_win_replay") is False, "M8t source-to-WIN claim boundary differs")
    require(audit_boundary.get("independent_win_synthesis") is False, "M8t independent-WIN claim boundary differs")
    require(source_report.get("status") == "SOURCE_TO_POST_FRONTEND_CONTRACT_SEMANTICS_VERIFIED", "source report status differs")
    require(downstream.get("status") == "POST_FRONTEND_CONTRACT_TO_CERTIFICATE_SEMANTICS_VERIFIED", "downstream report status differs")
    require(m8t_record.get("status") == "SOURCE_TO_SUPPLIED_CERTIFICATE_SEMANTICS_VERIFIED", "M8t record status differs")
    require(m8t_summary.get("status") == "SOURCE_TO_SUPPLIED_CERTIFICATE_SEMANTICS_VERIFIED", "M8t summary status differs")
    require(m8t_summary.get("source_files") == 1 and m8t_summary.get("target_cells") == 2, "M8t summary census differs")
    verified_fields = source_report.get("verified_fields")
    require(isinstance(verified_fields, list) and set(verified_fields) == EXPECTED_VERIFIED_FIELDS and len(verified_fields) == len(EXPECTED_VERIFIED_FIELDS), "source verified-field set differs")
    for checker_name in ("source_checker", "downstream_checker"):
        checker_record = m8t_record.get(checker_name, {})
        require(checker_record.get("exit_code") == 0 and checker_record.get("timed_out") is False, f"{checker_name} execution differs")
    runtime = native_protocol.get("runtime", {})
    require(runtime.get("java") == "17", "registered Java version differs")
    require(runtime.get("heap") == "16g", "registered heap differs")
    require(runtime.get("per_case_timeout_seconds") == 180, "registered case timeout differs")

    components = facts.get("components")
    controllers = facts.get("controllers")
    require(isinstance(components, list) and len(components) == 2, "component census differs")
    require(isinstance(controllers, dict) and set(controllers) == {"old", "new"}, "controller pair differs")
    transfers = [
        {
            "index": row.get("index"),
            "transfer_relation": row.get("transfer_relation"),
            "transfer_has_action_sequence": row.get("transfer_has_action_sequence"),
            "reconfigure_action": row.get("reconfigure_action"),
        }
        for row in components
    ]
    observers = {"machines": facts.get("observer_machines"), "registry": facts.get("observer_registry")}
    source_values = [
        source_report.get("profile"),
        facts.get("definition"),
        components,
        controllers["old"],
        controllers["new"],
        transfers,
        facts.get("old_safety_machines"),
        facts.get("new_safety_machines"),
        facts.get("transition_requirement_machines"),
        observers,
        facts.get("new_activation_sources"),
        facts.get("protocol"),
        facts.get("controllable_actions"),
        facts.get("load_selector"),
        native_protocol.get("runtime", {}).get("per_case_timeout_seconds"),
    ]
    source_refs = [
        [json_ref("source_report", "/profile")],
        [json_ref("facts", "/definition")],
        [json_ref("facts", "/components")],
        [json_ref("facts", "/controllers/old")],
        [json_ref("facts", "/controllers/new")],
        [json_ref("facts", "/components")],
        [json_ref("facts", "/old_safety_machines")],
        [json_ref("facts", "/new_safety_machines")],
        [json_ref("facts", "/transition_requirement_machines")],
        [json_ref("facts", "/observer_machines"), json_ref("facts", "/observer_registry")],
        [json_ref("facts", "/new_activation_sources")],
        [json_ref("facts", "/protocol")],
        [json_ref("facts", "/controllable_actions")],
        [json_ref("facts", "/load_selector")],
        [json_ref("native_protocol", "/runtime/per_case_timeout_seconds")],
    ]
    source_constructions = [
        {"op": "IDENTITY"}, {"op": "IDENTITY"}, {"op": "IDENTITY"},
        {"op": "IDENTITY"}, {"op": "IDENTITY"},
        {"op": "ARRAY_PROJECT", "keys": ["index", "transfer_relation", "transfer_has_action_sequence", "reconfigure_action"]},
        {"op": "IDENTITY"}, {"op": "IDENTITY"}, {"op": "IDENTITY"},
        {"op": "OBJECT", "fields": {"machines": 0, "registry": 1}},
        {"op": "IDENTITY"}, {"op": "IDENTITY"}, {"op": "IDENTITY"},
        {"op": "IDENTITY"}, {"op": "IDENTITY"},
    ]
    source_notes = [
        "bounded registered parser profile", "updatingController definition",
        "two complete component records", "independently reconstructed compiled old-controller automaton (81 states/216 edges)",
        "independently reconstructed compiled new-controller automaton (81 states/216 edges)", "two seven-row component transfers",
        "12 old safety machines", "12 new safety machines", "24 transition-requirement machines",
        "22 observer machines plus 22 registry rows", "12 activation sources with 152 rows", "26 progress actions and empty precedence",
        "exact 39-action controllable set", "ALL_REACHABLE load rule", "recorded 180-second per-case bound; Java version, heap, JAR, and checker hashes are execution provenance rather than b; historical property overrides/transitive runtime were not reproduced",
    ]
    source_basis = ["DETERMINISTIC_SOURCE_CHECKER"] * 14 + ["RECORDED_EXECUTION_BOUND"]
    source_in = [byte_binding()] + [
        binding(documents, index, name, value, refs, construction, basis, note)
        for index, (name, value, refs, construction, basis, note) in enumerate(
            zip(SOURCE_FIELDS[1:], source_values, source_refs, source_constructions, source_basis, source_notes), 2
        )
    ]
    source_in[-1]["status"] = "RECORDED"
    source_in[-1]["basis"] = "RECORDED_POST_OUTCOME_DECLARED_BOUND"

    receipts = bundle.get("dependency_receipts")
    locals_value = bundle.get("locals")
    transport = bundle.get("transport")
    require(isinstance(receipts, list) and len(receipts) == 114, "receipt census differs")
    require(isinstance(locals_value, list) and len(locals_value) == 2, "local proof census differs")
    require(isinstance(transport, dict), "transport is absent")
    require(bundle.get("component_partition") == downstream.get("component_partition"), "bundle/downstream partition differs")
    require(bundle.get("old_endpoint_state_count") == downstream.get("old_endpoint_states"), "old endpoint cross-check differs")
    require(bundle.get("new_endpoint_state_count") == downstream.get("new_endpoint_states"), "new endpoint cross-check differs")
    require(len(locals_value) == len(downstream.get("locals", [])), "local proof cross-check differs")
    require(bundle.get("terminal_product_verified") is downstream.get("global_transport_and_kappa_verified"), "terminal transport cross-check differs")
    require(record.get("terminal_product_verified") is True, "recorded terminal-product field differs")
    require(transport.get("verified") is True, "recorded transport verification differs")
    gamma = {"arbiter": bundle.get("arbiter"), "transport": transport}
    y_values = [
        bundle.get("extraction_status"), bundle.get("factor_status"), bundle.get("solve_status"),
        bundle.get("component_partition"), receipts, locals_value,
        bundle.get("old_endpoint_state_count"), bundle.get("new_endpoint_state_count"),
        bundle.get("terminal_product_verified"), gamma,
    ]
    y_refs = [
        [json_ref("bundle", "/extraction_status")],
        [json_ref("bundle", "/factor_status")],
        [json_ref("bundle", "/solve_status")],
        [json_ref("bundle", "/component_partition")],
        [json_ref("bundle", "/dependency_receipts")],
        [json_ref("bundle", "/locals")],
        [json_ref("bundle", "/old_endpoint_state_count")],
        [json_ref("bundle", "/new_endpoint_state_count")],
        [json_ref("bundle", "/terminal_product_verified")],
        [json_ref("bundle", "/arbiter"), json_ref("bundle", "/transport")],
    ]
    y_constructions = [
        {"op": "IDENTITY"}, {"op": "IDENTITY"}, {"op": "IDENTITY"},
        {"op": "IDENTITY"}, {"op": "IDENTITY"}, {"op": "IDENTITY"},
        {"op": "IDENTITY"}, {"op": "IDENTITY"}, {"op": "IDENTITY"},
        {"op": "OBJECT", "fields": {"arbiter": 0, "transport": 1}},
    ]
    y_validation_refs = [
        [], [],
        [json_ref("downstream_report", "/post_frontend_contract_ir_to_winning_certificate_semantic_verification"), json_ref("m8t_record", "/source_to_supplied_certificate_semantics_verified"), json_ref("downstream_report", "/status")],
        [json_ref("downstream_report", "/component_partition")],
        [json_ref("downstream_report", "/status")],
        [json_ref("downstream_report", "/locals"), json_ref("downstream_report", "/post_frontend_contract_ir_to_winning_certificate_semantic_verification")],
        [json_ref("downstream_report", "/old_endpoint_states")],
        [json_ref("downstream_report", "/new_endpoint_states")],
        [json_ref("m8q_record", "/terminal_product_verified"), json_ref("bundle", "/transport/verified"), json_ref("downstream_report", "/global_transport_and_kappa_verified"), json_ref("downstream_report", "/transport/quiet_terminal_product_tuples")],
        [json_ref("downstream_report", "/transport"), json_ref("downstream_report", "/global_transport_and_kappa_verified")],
    ]
    y_basis = [
        "RECORDED_PRODUCER_STATUS", "RECORDED_PRODUCER_STATUS",
        "RECORDED_PRODUCER_STATUS",
        "DETERMINISTIC_DEPENDENCY_CHECKER", "DETERMINISTIC_DEPENDENCY_CHECKER",
        "SUPPLIED_PROOFS_SEMANTICALLY_CHECKED", "DETERMINISTIC_ENDPOINT_RECONSTRUCTION",
        "DETERMINISTIC_ENDPOINT_RECONSTRUCTION", "RECORDED_VALUE_RECHECKED_WITHIN_SUPPLIED_SYMBOLIC_CONTRACT",
        "SUPPLIED_TRANSPORT_SEMANTICALLY_CHECKED",
    ]
    y_notes = [
        "census/provenance field, not a theorem premise", "census/provenance field, not a theorem premise",
        "recorded producer label only; the checker validates supplied witness semantics but does not derive this status or synthesize WIN", "conservative partition, not a maximum claim",
        "all 114 kind/declaration/component receipts", "two supplied local proofs checked on their complete rank domains",
        "census field, not a theorem premise", "census field, not a theorem premise",
        "checked one-way terminal product", "arbiter plus observer/activation/selector/terminal transport",
    ]
    output_y = [
        binding(documents, index, name, value, refs, construction, basis, note, validation_refs)
        for index, (name, value, refs, construction, basis, note, validation_refs) in enumerate(
            zip(Y_FIELDS, y_values, y_refs, y_constructions, y_basis, y_notes, y_validation_refs), 1
        )
    ]

    source_census = source_report.get("census", {})
    totals = downstream.get("totals", {})
    downstream_transport = downstream.get("transport", {})
    stages = [
        {
            "stage": "S0",
            "operation": "bounded strict source parse, independent controller synthesis, and exact SourceIn binding",
            "produces": list(SOURCE_FIELDS),
            "predicate_outcomes": [
                predicate("source-byte-identity", EXPECTED_SOURCE_SHA256, manifest["source"]["sha256"], "RECORDED_BYTES", ["manifest:/source"]),
                predicate("bounded-profile", True, source_report.get("bounded_registered_mtsa_lts_frontend_replay"), "DETERMINISTIC_SOURCE_CHECKER", ["source_report:/bounded_registered_mtsa_lts_frontend_replay"]),
                predicate("source-to-contract-agreement", True, source_report.get("source_to_post_frontend_contract_semantic_agreement"), "DETERMINISTIC_SOURCE_CHECKER", ["source_report:/source_to_post_frontend_contract_semantic_agreement"]),
                predicate("verified-field-families", 14, len(source_report.get("verified_fields", [])), "DETERMINISTIC_SOURCE_CHECKER", ["source_report:/verified_fields"]),
                predicate("controller-states", [81, 81], [source_census.get("old_controller_states"), source_census.get("new_controller_states")], "DETERMINISTIC_SOURCE_CHECKER", ["source_report:/census"]),
                predicate("controller-edges", [216, 216], [source_census.get("old_controller_edges"), source_census.get("new_controller_edges")], "DETERMINISTIC_SOURCE_CHECKER", ["source_report:/census"]),
                predicate("general-mtsa-frontend", False, source_report.get("claim_boundary", {}).get("general_mtsa_frontend"), "BOUNDARY", ["source_report:/claim_boundary/general_mtsa_frontend"]),
            ],
        },
        {
            "stage": "S1",
            "operation": "reconstruct fixed endpoints, complete dependency receipts, and conservative blocks",
            "produces": ["C_D", "B", "n_old", "n_new"],
            "predicate_outcomes": [
                predicate("endpoint-state-counts", [126, 137], [downstream.get("old_endpoint_states"), downstream.get("new_endpoint_states")], "DETERMINISTIC_SUPPLIED_CERTIFICATE_CHECKER", ["downstream_report:/old_endpoint_states", "downstream_report:/new_endpoint_states", "bundle:/old_endpoint_state_count", "bundle:/new_endpoint_state_count"]),
                predicate("dependency-receipts", 114, len(receipts), "RECORDED_BUNDLE_PLUS_DEPENDENCY_REPLAY", ["bundle:/dependency_receipts"]),
                predicate("conservative-partition", [[0], [1]], downstream.get("component_partition"), "DETERMINISTIC_SUPPLIED_CERTIFICATE_CHECKER", ["downstream_report:/component_partition"]),
                predicate("complete-conservative-extraction", "COMPLETE_CONSERVATIVE", bundle.get("extraction_status"), "RECORDED_PRODUCER_STATUS", ["bundle:/extraction_status"]),
            ],
        },
        {
            "stage": "S2",
            "operation": "check the two supplied local games on every supplied rank-domain candidate bucket/outcome",
            "produces": ["L"],
            "predicate_outcomes": [
                predicate("local-proofs", 2, len(downstream.get("locals", [])), "DETERMINISTIC_SUPPLIED_CERTIFICATE_CHECKER", ["downstream_report:/locals"]),
                predicate("root-states", 24, totals.get("root_states"), "DETERMINISTIC_SUPPLIED_CERTIFICATE_CHECKER", ["downstream_report:/totals/root_states"]),
                predicate("rank-states", 116, totals.get("rank_states"), "DETERMINISTIC_SUPPLIED_CERTIFICATE_CHECKER", ["downstream_report:/totals/rank_states"]),
                predicate("candidate-buckets", 2560, totals.get("candidate_buckets"), "DETERMINISTIC_SUPPLIED_CERTIFICATE_CHECKER", ["downstream_report:/totals/candidate_buckets"]),
                predicate("candidate-outcomes", 1424, totals.get("candidate_outcomes"), "DETERMINISTIC_SUPPLIED_CERTIFICATE_CHECKER", ["downstream_report:/totals/candidate_outcomes"]),
                predicate("strategy-buckets", 124, totals.get("strategy_buckets"), "DETERMINISTIC_SUPPLIED_CERTIFICATE_CHECKER", ["downstream_report:/totals/strategy_buckets"]),
                predicate("quiet-terminals", 8, totals.get("quiet_goals"), "DETERMINISTIC_SUPPLIED_CERTIFICATE_CHECKER", ["downstream_report:/totals/quiet_goals"]),
                predicate("nonempty-candidate-buckets", 1424, totals.get("nonempty_candidate_buckets"), "DETERMINISTIC_SUPPLIED_CERTIFICATE_CHECKER", ["downstream_report:/totals/nonempty_candidate_buckets"]),
                predicate("full-goals", 24, totals.get("full_goals"), "DETERMINISTIC_SUPPLIED_CERTIFICATE_CHECKER", ["downstream_report:/totals/full_goals"]),
                predicate("goal-payloads", 2, totals.get("goal_payloads"), "DETERMINISTIC_SUPPLIED_CERTIFICATE_CHECKER", ["downstream_report:/totals/goal_payloads"]),
                predicate("historical-solver-discovered-states", 127174, bundle.get("local_solver_discovered_states_sum"), "RECORDED_HISTORICAL_PRODUCER_CENSUS", ["bundle:/local_solver_discovered_states_sum"]),
                predicate("historical-solver-successor-queries", 831356, bundle.get("local_solver_successor_queries_sum"), "RECORDED_HISTORICAL_PRODUCER_CENSUS", ["bundle:/local_solver_successor_queries_sum"]),
                predicate("historical-solver-outcomes", 294632, bundle.get("local_solver_outcomes_sum"), "RECORDED_HISTORICAL_PRODUCER_CENSUS", ["bundle:/local_solver_outcomes_sum"]),
                predicate("supplied-certificate-semantics", True, downstream.get("post_frontend_contract_ir_to_winning_certificate_semantic_verification"), "DETERMINISTIC_SUPPLIED_CERTIFICATE_CHECKER", ["downstream_report:/post_frontend_contract_ir_to_winning_certificate_semantic_verification"]),
            ],
        },
        {
            "stage": "S3",
            "operation": "check symbolic relation/observer/activation transport, selectors, terminal fibre, and kappa",
            "produces": ["Gamma", "v"],
            "predicate_outcomes": [
                predicate("activation-testers", 12, downstream_transport.get("activation_testers"), "DETERMINISTIC_SUPPLIED_CERTIFICATE_CHECKER", ["downstream_report:/transport/activation_testers"]),
                predicate("activation-pairs", 218, downstream_transport.get("activation_relation_pairs"), "DETERMINISTIC_SUPPLIED_CERTIFICATE_CHECKER", ["downstream_report:/transport/activation_relation_pairs"]),
                predicate("observer-pairs", 1010, downstream_transport.get("observer_relation_pairs"), "DETERMINISTIC_SUPPLIED_CERTIFICATE_CHECKER", ["downstream_report:/transport/observer_relation_pairs"]),
                predicate("load-selectors", 137, downstream_transport.get("load_selector_endpoints"), "DETERMINISTIC_SUPPLIED_CERTIFICATE_CHECKER", ["downstream_report:/transport/load_selector_endpoints"]),
                predicate("load-selector-signatures", 137, downstream_transport.get("load_selector_signatures"), "DETERMINISTIC_SUPPLIED_CERTIFICATE_CHECKER", ["downstream_report:/transport/load_selector_signatures"]),
                predicate("terminal-assemblies", 1, downstream_transport.get("certificate_terminal_tuples"), "DETERMINISTIC_SUPPLIED_CERTIFICATE_CHECKER", ["downstream_report:/transport/certificate_terminal_tuples"]),
                predicate("terminal-fibres", 1, downstream_transport.get("terminal_observer_fibres"), "DETERMINISTIC_SUPPLIED_CERTIFICATE_CHECKER", ["downstream_report:/transport/terminal_observer_fibres"]),
                predicate("quiet-terminal-product", 16, downstream_transport.get("quiet_terminal_product_tuples"), "DETERMINISTIC_SUPPLIED_CERTIFICATE_CHECKER", ["downstream_report:/transport/quiet_terminal_product_tuples"]),
                predicate("transport-and-kappa", True, downstream.get("global_transport_and_kappa_verified"), "DETERMINISTIC_SUPPLIED_CERTIFICATE_CHECKER", ["downstream_report:/global_transport_and_kappa_verified"], "symbolic contract only; no mixed global game or runtime execution"),
            ],
        },
        {
            "stage": "S4",
            "operation": "reconstruct exact terminal and recorded Y while preserving producer/independence boundaries",
            "produces": list(Y_FIELDS),
            "predicate_outcomes": [
                predicate("process-status", "SUCCESS", record.get("process_status"), "RECORDED_HISTORICAL_PRODUCER", ["m8q_record:/process_status"]),
                predicate("exit-code", 0, record.get("exit_code"), "RECORDED_HISTORICAL_PRODUCER", ["m8q_record:/exit_code"]),
                predicate("timed-out", False, record.get("timed_out"), "RECORDED_HISTORICAL_PRODUCER", ["m8q_record:/timed_out"]),
                predicate("consumer-status", "PASS", record.get("consumer_status"), "RECORDED_STRUCTURAL_CONSUMER", ["m8q_record:/consumer_status"]),
                predicate("status-pair", ["NONTRIVIAL_SOURCE_NATIVE", "PRODUCER_VERIFIED_REFINED_WIN"], [bundle.get("factor_status"), bundle.get("solve_status")], "RECORDED_PRODUCER_STATUS_PAIR", ["bundle:/factor_status", "bundle:/solve_status"]),
                predicate("terminal-product-cross-check", [True, True, True, True, 16], [bundle.get("terminal_product_verified"), record.get("terminal_product_verified"), transport.get("verified"), downstream.get("global_transport_and_kappa_verified"), downstream_transport.get("quiet_terminal_product_tuples")], "RECORDED_VALUE_RECHECKED_WITHIN_SUPPLIED_SYMBOLIC_CONTRACT", ["bundle:/terminal_product_verified", "m8q_record:/terminal_product_verified", "bundle:/transport/verified", "downstream_report:/global_transport_and_kappa_verified", "downstream_report:/transport/quiet_terminal_product_tuples"]),
                predicate("source-to-supplied-certificate", True, m8t_record.get("source_to_supplied_certificate_semantics_verified"), "COMPOSED_DETERMINISTIC_CHECKERS", ["m8t_record:/source_to_supplied_certificate_semantics_verified"]),
                predicate("source-to-win-replay", False, m8t_record.get("source_to_win_replay"), "BOUNDARY", ["m8t_record:/source_to_win_replay"]),
                predicate("audit-status", "SOURCE_TO_SUPPLIED_CERTIFICATE_SEMANTICS_VERIFIED", m8t_audit.get("status"), "DETERMINISTIC_EXISTING_EVIDENCE_AUDIT", ["m8t_audit:/status"]),
            ],
        },
    ]

    theorem_map = {
        "source_S1_S7": [
            theorem_row("S1", "the supplied symbolic contract records local-root coverage and observer relations corresponding to the root-relation premise", ["downstream_report:/locals/0/root_states", "downstream_report:/locals/1/root_states", "downstream_report:/totals/root_states", "downstream_report:/old_endpoint_states", "downstream_report:/new_endpoint_states", "bundle:/transport/observer_relations"], "mapping and supplied-contract check only; no mixed global game materialized"),
            theorem_row("S2", "the source controllers and supplied observer relation map to the safety-reflection premise", ["facts:/controllers", "bundle:/transport/observer_relations", "downstream_report:/semantic_digest_sha256"], "mapping and supplied-contract check over the supplied proof domains; no materialized global relation census"),
            theorem_row("S3", "the two supplied local certificates cover their recorded roots, ranks, strategy buckets, and quiet terminals", ["downstream_report:/locals", "downstream_report:/totals"], "supplied certificate semantics checked; no independent WIN synthesis"),
            theorem_row("S4", "the supplied symbolic arbiter maps to uncontrollable handling and certified enabled-action selection", ["bundle:/arbiter", "downstream_report:/post_frontend_contract_ir_to_winning_certificate_semantic_verification"], "mapping and symbolic-contract check only; no materialized mixed game or runtime adapter execution"),
            theorem_row("S5", "the supplied observer/activation transport maps to relation, foreign-frame, and rank-progress preservation", ["bundle:/transport", "downstream_report:/transport"], "mapping and symbolic-contract check over supplied proof domains, not a materialized mixed game"),
            theorem_row("S6", "the supplied selector and kappa records map to total type-compatible goal loading", ["bundle:/transport/load_selectors", "downstream_report:/global_transport_and_kappa_verified"], "typed symbolic-model result, not actual controller loading"),
            theorem_row("S7", "the supplied terminal assembly and checked fibre map to the goal-only terminal-fibre premise", ["bundle:/transport/terminal_assemblies", "downstream_report:/transport/terminal_observer_fibres"], "one supplied terminal fibre in one same-author source cluster"),
        ],
        "output_field_map": {
            "e": {"premise_ids": [], "classification": "PROVENANCE_OR_CENSUS"},
            "f": {"premise_ids": [], "classification": "PROVENANCE_OR_CENSUS"},
            "s": {
                "premise_ids": [],
                "classification": "RECORDED_PRODUCER_LABEL",
                "producer_label_derived_by_replay": False,
                "supplied_witness_semantic_validation": {
                    "premise_ids": ["S1", "S2", "S3", "S4", "S5", "S6", "S7"],
                    "status": "CHECKED_WITHIN_SUPPLIED_SYMBOLIC_CONTRACT",
                    "does_not_derive_recorded_s": True,
                },
            },
            "B": {"premise_ids": ["S1", "S4", "S5"], "classification": "CONSTRUCTION_FIELD"},
            "C_D": {"premise_ids": ["S4", "S5"], "classification": "CONSTRUCTION_FIELD"},
            "L": {"premise_ids": ["S1", "S2", "S3", "S4", "S5"], "classification": "SUPPLIED_SYMBOLIC_THEOREM_WITNESS"},
            "n_old": {"premise_ids": [], "classification": "PROVENANCE_OR_CENSUS"},
            "n_new": {"premise_ids": [], "classification": "PROVENANCE_OR_CENSUS"},
            "v": {"premise_ids": ["S6", "S7"], "classification": "CHECKED_TERMINAL_FIELD"},
            "Gamma": {"premise_ids": ["S1", "S2", "S4", "S5", "S6", "S7"], "classification": "SUPPLIED_SYMBOLIC_THEOREM_WITNESS"},
        },
        "flat_B1_B7": {
            "status": "MANIFEST_BOUND_SEPARATE_FLAT_TRACE",
            "manifest_keys": ["flat_fixture", "flat_trace", "flat_trace_checker"],
            "checked_facts": {"unit_partition_count": 2, "first_accepted_block_count": 2, "all_accepted_candidates_transport_ready": True},
            "premise_map": {
                "B1": ["flat_trace:/partitions/0/theorem_5_3_premises/ambient_state_product", "flat_trace:/partitions/0/theorem_5_3_premises/nonempty_projected_roots"],
                "B2": ["flat_trace:/partitions/0/theorem_5_3_premises/root_projection_with_extra_rectangularity"],
                "B3": ["flat_trace:/partitions/0/theorem_5_3_premises/asynchronous_frame_product", "flat_trace:/partitions/0/theorem_5_3_premises/shared_actions_are_controllable_pure_stutters"],
                "B4": ["flat_trace:/partitions/0/theorem_5_3_premises/safe_conjunction", "flat_trace:/partitions/0/theorem_5_3_premises/goal_product", "flat_trace:/partitions/0/theorem_5_3_premises/load_product", "flat_trace:/partitions/0/theorem_5_3_premises/handover_product"],
                "B5": ["flat_trace:/partitions/0/theorem_5_3_premises/typed_metadata_block_local"],
                "B6": ["flat_trace:/partitions/0/theorem_5_3_premises/local_goals_are_uncontrollably_quiescent"],
                "B7": ["flat_trace:/partitions/0/theorem_5_3_transport_ready"],
            },
            "note": "the separate complete flat replay maps B1--B7; ProductionCell maps relational S1--S7 and does not claim the exact-product theorem",
        },
    }

    return {
        "schema_version": "fg-ducs-ordinary-source-construction-trace-v1",
        "trace_id": "productioncell-arms2-r2-sourcein-to-recorded-y",
        "trace_kind": "manifest_bound_deterministic_reconstruction_of_existing_bytes",
        "manifest": manifest,
        "source_in_type_definitions": {
            "bytes": "raw byte string identified by manifest length and SHA-256",
            "dialect": "bounded registered parser-profile identifier",
            "entry": "updatingController definition identifier",
            "C": "two complete source component records",
            "E_old": "independently reconstructed compiled old-controller automaton",
            "E_new": "independently reconstructed compiled new-controller automaton",
            "g": "per-component projected transfer records",
            "M_old": "old safety-machine records",
            "M_new": "new safety-machine records",
            "M_upd": "transition-requirement-machine records",
            "O": "observer-machine and observer-registry record",
            "Act": "activation-source records",
            "Prot": "progress-action and precedence record",
            "Sigma_c_N": "exact new-version controllable-action set",
            "Lambda": "load-selector rule",
            "b": "recorded outer per-case timeout in seconds; not an algorithmic receipt budget",
        },
        "runtime_provenance": {
            "java": runtime.get("java"),
            "heap": runtime.get("heap"),
            "historical_jar_sha256": runtime.get("jar_sha256"),
            "m8q_wall_nanos": record.get("wall_nanos"),
            "m8q_producer_elapsed_nanos": record.get("producer_elapsed_nanos"),
            "timed_out": record.get("timed_out"),
            "timeout_enforcement_replayed": False,
            "historical_producer_runtime_replayed": False,
        },
        "source_in": source_in,
        "stage_replay": stages,
        "output_y": output_y,
        "theorem_map": theorem_map,
        "selected_partition_or_obstacle": {"kind": "CONSERVATIVE_PARTITION", "partition": [[0], [1]], "obstacle": None, "maximum_partition_claim": False},
        "one_way_result": {
            "terminal": "SUCCESS", "e": "COMPLETE_CONSERVATIVE",
            "f": "NONTRIVIAL_SOURCE_NATIVE", "s": "PRODUCER_VERIFIED_REFINED_WIN",
            "B": [[0], [1]], "n_old": 126, "n_new": 137, "v": True,
            "source_to_supplied_certificate_semantics_verified": True,
            "source_to_win_replay": False,
            "producer_status_derived_by_replay": False,
            "supplied_witness_semantics_checked": True,
        },
        "coverage": {
            "source_in_fields": 16, "source_stages": 5, "output_y_fields": 10,
            "source_theorem_mappings": 7,
            "all_complex_values_have_exact_rfc6901_refs_or_raw_byte_refs": True,
            "all_synthetic_values_have_deterministic_construction_descriptors": True,
        },
        "claim_boundary": {
            "new_experimental_outcome": False,
            "changes_any_evaluation_denominator": False,
            "same_author": True,
            "post_outcome": True,
            "bounded_registered_source_profile": True,
            "historical_producer_runtime_replayed": False,
            "historical_property_override_environment_reproduced": False,
            "transitive_runtime_frozen": False,
            "general_mtsa_frontend": False,
            "independent_win_synthesis": False,
            "source_to_win_replay": False,
            "global_mixed_game_materialized": False,
            "machine_checkable_manifest_consistency_replay": True,
            "composite_semantic_verification_requires_fresh_m8t_rerun": True,
            "human_hand_checkable_complete_source_instance": False,
            "maximum_or_complete_source_decomposition": False,
            "global_loss_from_local_failure": False,
            "held_out_cases": 0,
            "third_party_cases": 0,
            "production_cases": 0,
        },
    }


def validate(root: Path, trace_path: Path) -> dict[str, Any]:
    expected = derive(root)
    observed = load_json(trace_path)
    require(observed == expected, "stored trace differs from deterministic reconstruction")
    require([row.get("field") for row in observed.get("source_in", [])] == list(SOURCE_FIELDS), "SourceIn coverage/order differs")
    require([row.get("stage") for row in observed.get("stage_replay", [])] == ["S0", "S1", "S2", "S3", "S4"], "stage coverage/order differs")
    require([row.get("field") for row in observed.get("output_y", [])] == list(Y_FIELDS), "Y coverage/order differs")
    require([row.get("premise_id") for row in observed.get("theorem_map", {}).get("source_S1_S7", [])] == [f"S{i}" for i in range(1, 8)], "S1-S7 coverage differs")
    require(all(row.get("mapping_status") == "MAPPED" and row.get("evidence_status") == "CHECKED_WITHIN_SUPPLIED_SYMBOLIC_CONTRACT" for row in observed.get("theorem_map", {}).get("source_S1_S7", [])), "S1-S7 qualified mapping status differs")
    require(set(observed.get("theorem_map", {}).get("output_field_map", {})) == set(Y_FIELDS), "Y theorem-map coverage differs")
    flat_map = observed.get("theorem_map", {}).get("flat_B1_B7", {})
    require(flat_map.get("status") == "MANIFEST_BOUND_SEPARATE_FLAT_TRACE", "flat B1-B7 binding differs")
    require(set(flat_map.get("premise_map", {})) == {f"B{i}" for i in range(1, 8)}, "flat B1-B7 premise coverage differs")
    boundary = observed.get("claim_boundary", {})
    require(boundary.get("historical_producer_runtime_replayed") is False, "historical runtime boundary changed")
    require(boundary.get("source_to_win_replay") is False, "source-to-WIN boundary changed")
    return {
        "schema_version": "fg-ducs-ordinary-source-construction-trace-check-v1",
        "status": "PASS",
        "trace_sha256": sha256_file(trace_path),
        "source_sha256": EXPECTED_SOURCE_SHA256,
        "source_in_fields": 16,
        "source_stages": 5,
        "output_y_fields": 10,
        "source_theorem_mappings": 7,
        "selected_partition": [[0], [1]],
        "one_way_result": "RECORDED_PRODUCER_LABEL_WITH_SEPARATE_SUPPLIED_WITNESS_SEMANTIC_CHECK",
        "historical_producer_runtime_replayed": False,
        "source_to_win_replay": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--trace", type=Path)
    parser.add_argument("--emit", action="store_true")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    trace = args.trace.resolve() if args.trace is not None else root / TRACE_REL
    try:
        value = derive(root) if args.emit else validate(root, trace)
        print(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2 if args.emit else None, allow_nan=False))
        return 0
    except (TraceError, OSError, UnicodeDecodeError, ValueError, KeyError, TypeError) as error:
        print(f"ordinary-source construction trace FAIL: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
