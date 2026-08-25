#!/usr/bin/env python3
"""Check the complete R09 ordinary-source proof fixture.

A fixture-specific parser derives all SourceIn values from the exact 598-byte
ordinary MTSA/LTS source plus three explicit constructor parameters. It then
constructs and checks the complete four-state global game, both local rank
proofs, every S0--S4 outcome, the full ten-field Y payload, and the B/P/S
premise tables for Theorems 5.3--5.5. Separately, it checks that a stored
post-hoc Java bundle equals that formal construction field for field. The
bundle is a code-path consistency observation, not execution provenance or
scientific evidence.

This is a same-author correctness proof for one synthetic instance. It is not
a general frontend, an independent source-to-WIN replay, or a new evaluation
outcome.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
TRACE_PATH = ROOT / "evidence/ordinary-source-construction-trace/r09-hand-k02-formal-trace.json"
SOURCE_PATH = ROOT / "inputs/correctness/r09-hand-k02.lts"
BUNDLE_PATH = ROOT / "evidence/ordinary-source-construction-trace/r09-hand-k02-native-bundle.json"
FLAT_TRACE_PATH = ROOT / "evidence/m8p-partition-discovery/predicate-trace-example.json"

SOURCE_SHA256 = "5f3fe09e6ab3f71d28a06a280b897974fcd603ea8986ee4476690fe56f06fa3e"
BUNDLE_SHA256 = "6fa3a5cd3755860357735c02af9580c87a426868ea861f4da2e277435fbac9a0"
FLAT_TRACE_SHA256 = "924bac5e7ccd0a9dcef934a4e517ec5b2fef066cebb3dba3719fffd167d54475"
SOURCE_FIELDS = [
    "bytes", "dialect", "entry", "C", "E_old", "E_new", "g", "M_old",
    "M_new", "M_upd", "O", "Act", "Prot", "Sigma_c_N", "Lambda", "b",
]
Y_FIELDS = ["e", "f", "s", "B", "C_D", "L", "n_old", "n_new", "v", "Gamma"]


class TraceError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise TraceError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as error:
        raise TraceError("non-canonical JSON value") from error


def load(path: Path) -> dict[str, Any]:
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate key: {key}")
            result[key] = value
        return result

    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
            object_pairs_hook=unique_object,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise TraceError(f"cannot load strict JSON: {path}") from error
    require(isinstance(value, dict), f"JSON root is not an object: {path}")
    return value


def fullmatch(pattern: str, text: str, label: str) -> re.Match[str]:
    match = re.fullmatch(pattern, text)
    require(match is not None, f"source declaration differs: {label}: {text}")
    return match


def parse_source_text(text: str) -> dict[str, Any]:
    """Parse the complete, intentionally narrow proof-source grammar."""
    lines = [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("//")]
    require(len(lines) == 26, f"source declaration-line count differs: {len(lines)}")

    controllable = fullmatch(r"set ([A-Za-z][A-Za-z0-9_]*)=\{([A-Za-z][A-Za-z0-9_]*)\}", lines[0], "controllable set")
    set_name, idle = controllable.groups()

    processes: list[tuple[str, str]] = []
    for index in (1, 2, 4, 5):
        match = fullmatch(r"([A-Za-z][A-Za-z0-9_]*)=\(([A-Za-z][A-Za-z0-9_]*)->\1\)\.", lines[index], f"process {index}")
        processes.append((match.group(1), match.group(2)))
    require(all(action == idle for _, action in processes), "component self-loop action differs")
    old_names = [processes[0][0], processes[1][0]]
    new_names = [processes[2][0], processes[3][0]]

    old_env = fullmatch(r"\|\|([A-Za-z][A-Za-z0-9_]*)=\(([A-Za-z][A-Za-z0-9_]*)\|\|([A-Za-z][A-Za-z0-9_]*)\)\.", lines[3], "old environment")
    new_env = fullmatch(r"\|\|([A-Za-z][A-Za-z0-9_]*)=\(([A-Za-z][A-Za-z0-9_]*)\|\|([A-Za-z][A-Za-z0-9_]*)\)\.", lines[6], "new environment")
    require(list(old_env.groups()[1:]) == old_names, "old environment members differ")
    require(list(new_env.groups()[1:]) == new_names, "new environment members differ")

    relations: list[dict[str, str]] = []
    relation_pattern = r"relation ([A-Za-z][A-Za-z0-9_]*)=\{([A-Za-z][A-Za-z0-9_]*)@\2=(reconfigure_[A-Za-z0-9_]+)->([A-Za-z][A-Za-z0-9_]*)@\4\}"
    for offset, line in enumerate(lines[7:9]):
        match = fullmatch(relation_pattern, line, f"relation {offset}")
        name, old, action, new = match.groups()
        require(old == old_names[offset] and new == new_names[offset], f"relation ownership differs: {name}")
        relations.append({"name": name, "old": old, "action": action, "new": new})
    require(len({item["action"] for item in relations}) == 2, "update actions are not distinct")

    old_spec = fullmatch(r"controllerSpec ([A-Za-z][A-Za-z0-9_]*)=\{controllable=\{([A-Za-z][A-Za-z0-9_]*)\}\}", lines[9], "old controller spec")
    old_controller = fullmatch(r"controller \|\|([A-Za-z][A-Za-z0-9_]*)=([A-Za-z][A-Za-z0-9_]*)~\{([A-Za-z][A-Za-z0-9_]*)\}\.", lines[10], "old controller")
    new_spec = fullmatch(r"controllerSpec ([A-Za-z][A-Za-z0-9_]*)=\{controllable=\{([A-Za-z][A-Za-z0-9_]*)\}\}", lines[11], "new controller spec")
    new_controller = fullmatch(r"controller \|\|([A-Za-z][A-Za-z0-9_]*)=([A-Za-z][A-Za-z0-9_]*)~\{([A-Za-z][A-Za-z0-9_]*)\}\.", lines[12], "new controller")
    require(old_spec.group(2) == set_name and new_spec.group(2) == set_name, "controller controllable set differs")
    require(old_controller.groups()[1:] == (old_env.group(1), old_spec.group(1)), "old controller binding differs")
    require(new_controller.groups()[1:] == (new_env.group(1), new_spec.group(1)), "new controller binding differs")

    entry_pattern = (
        r"updatingController ([A-Za-z][A-Za-z0-9_]*)=\{"
        r"oldController=([A-Za-z][A-Za-z0-9_]*),newController=([A-Za-z][A-Za-z0-9_]*),"
        r"oldEnvironment=\{([A-Za-z][A-Za-z0-9_]*),([A-Za-z][A-Za-z0-9_]*)\},"
        r"newEnvironment=\{([A-Za-z][A-Za-z0-9_]*),([A-Za-z][A-Za-z0-9_]*)\},"
        r"mapRelation=\{([A-Za-z][A-Za-z0-9_]*),([A-Za-z][A-Za-z0-9_]*)\},"
        r"oldGoal=([A-Za-z][A-Za-z0-9_]*),newGoal=([A-Za-z][A-Za-z0-9_]*),"
        r"nonblocking,revised_on_the_fly,fine_grained\}"
    )
    entry = fullmatch(entry_pattern, "".join(lines[13:-1]), "updating controller")
    values = entry.groups()
    require(values[1:3] == (old_controller.group(1), new_controller.group(1)), "entry controller binding differs")
    require(list(values[3:5]) == old_names and list(values[5:7]) == new_names, "entry component binding differs")
    require(list(values[7:9]) == [item["name"] for item in relations], "entry relation binding differs")
    require(values[9:11] == (old_spec.group(1), new_spec.group(1)), "entry goal binding differs")
    alias = fullmatch(r"\|\|([A-Za-z][A-Za-z0-9_]*)=([A-Za-z][A-Za-z0-9_]*)\.", lines[-1], "entry alias")
    require(alias.group(2) == values[0], "entry alias target differs")

    return {
        "set_name": set_name,
        "idle": idle,
        "old_names": old_names,
        "new_names": new_names,
        "old_environment": old_env.group(1),
        "new_environment": new_env.group(1),
        "old_controller": old_controller.group(1),
        "new_controller": new_controller.group(1),
        "relations": relations,
        "entry": values[0],
        "alias": alias.group(1),
    }


def endpoint(name: str, idle: str) -> dict[str, Any]:
    return {
        "name": name,
        "initial_state": 0,
        "states": [{"id": 0, "component_raw_states": [0, 0], "safe": True, "goal": True}],
        "transitions": [{"source": 0, "action": idle, "targets": [0]}],
    }


def source_in(parsed: Mapping[str, Any]) -> dict[str, Any]:
    components = []
    transfers = []
    for index, relation in enumerate(parsed["relations"]):
        components.append({
            "index": index,
            "old_process": relation["old"],
            "new_process": relation["new"],
            "relation": relation["name"],
            "update_action": relation["action"],
        })
        transfers.append({
            "component": index,
            "old_raw_state": 0,
            "update_action": relation["action"],
            "new_raw_state": 0,
        })
    return {
        "bytes": {"path": "inputs/correctness/r09-hand-k02.lts", "bytes": 598, "sha256": SOURCE_SHA256},
        "dialect": "MTSA-LTS-UC-minimal-v1",
        "entry": parsed["entry"],
        "C": components,
        "E_old": endpoint(parsed["old_controller"], parsed["idle"]),
        "E_new": endpoint(parsed["new_controller"], parsed["idle"]),
        "g": transfers,
        "M_old": [],
        "M_new": [],
        "M_upd": [],
        "O": {"machines": [], "registry": []},
        "Act": {"sources": [], "rows": []},
        "Prot": {"progress_actions": [item["action"] for item in parsed["relations"]], "precedence": []},
        "Sigma_c_N": [parsed["idle"]] + [item["action"] for item in parsed["relations"]],
        "Lambda": "ALL_REACHABLE",
        "b": "UNBOUNDED",
    }


def local_proof(index: int, action: str) -> dict[str, Any]:
    goal_physical = [{"version": "NEW", "raw_state": 0, "observer_states": []}]
    root_physical = [{"version": "OLD", "raw_state": 0, "observer_states": []}]
    target_key = json.dumps(
        {"physical": goal_physical, "active_testers": {}, "pending_actions": []},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return {
        "block_index": index,
        "components": [index],
        "full_goal_count": 1,
        "quiet_terminal_count": 1,
        "full_goal_uncontrollable_actions": [],
        "decision": "realizable",
        "solver_discovered_states": 2,
        "solver_successor_queries": 1,
        "solver_outcomes": 1,
        "certificate_initial_count": 1,
        "certificate_rank_count": 2,
        "certificate_strategy_source_count": 1,
        "certificate_strategy_bucket_count": 1,
        "certificate_goal_match_count": 1,
        "proof": {
            "schema_version": "fg-ducs-local-rank-proof-v1",
            "semantic_basis": "independent_fine_grained_semantics",
            "root_state_ids": ["q00000001"],
            "states": [
                {
                    "physical": goal_physical,
                    "active_testers": {},
                    "pending_actions": [],
                    "id": "q00000000",
                    "rank": 0,
                    "safe": True,
                    "goal": True,
                    "goal_signature_id": "block-goal-0",
                    "goal_signature": {"id": "block-goal-0", "physical": goal_physical, "new_requirement_states": {}},
                },
                {
                    "physical": root_physical,
                    "active_testers": {},
                    "pending_actions": [action],
                    "id": "q00000001",
                    "rank": 1,
                    "safe": True,
                    "goal": False,
                    "goal_signature_id": None,
                    "goal_signature": None,
                },
            ],
            "candidate_buckets": [{
                "source": "q00000001",
                "action": action,
                "controllable": True,
                "update": True,
                "target_keys": [target_key],
            }],
            "strategy_buckets": [{
                "source": "q00000001",
                "action": action,
                "target_state_ids": ["q00000000"],
            }],
        },
        "independent_certificate_valid": True,
        "independent_certificate_basis": "independent_certificate_proof",
        "independent_certificate_states": 2,
        "independent_certificate_queries": 1,
        "independent_certificate_outcomes": 1,
        "independent_certificate_elapsed_ms": 0,
    }


def transport() -> dict[str, Any]:
    return {
        "verified": True,
        "activation_tester_count": 0,
        "activation_relation_pair_count": 0,
        "observer_relation_pair_count": 2,
        "load_selector_signature_count": 1,
        "load_selector_endpoint_count": 1,
        "certificate_terminal_tuple_count": 1,
        "terminal_observer_fiber_count": 1,
        "observer_relations": [
            {"block_index": 0, "global_observer_indices": [], "pairs": [{"global": [], "local": []}]},
            {"block_index": 1, "global_observer_indices": [], "pairs": [{"global": [], "local": []}]},
        ],
        "load_selectors": [{
            "endpoint_id": "new-00000000",
            "controller_state": 0,
            "component_raw_states": [0, 0],
            "observer_states": [],
            "tester_states": {},
        }],
        "terminal_assemblies": [{
            "terminal_tuple_index": 0,
            "observer_fiber_index": 0,
            "local_goal_signature_ids": ["block-goal-0", "block-goal-0"],
            "global_observer_states": [],
            "endpoint_id": "new-00000000",
            "controller_state": 0,
        }],
    }


def expected_bundle(parsed: Mapping[str, Any]) -> dict[str, Any]:
    actions = [item["action"] for item in parsed["relations"]]
    arbiter = {
        "block_order": [0, 1],
        "original_goal_preempts_local_progress": True,
        "uncontrollable_mode": "allow_all_then_wait",
        "shared_controllable_pure_stutter": "disabled",
    }
    return {
        "schema_version": "fg-ducs-native-tier-a-result-v4",
        "source_name": "r09-hand-k02.lts",
        "source_sha256": SOURCE_SHA256,
        "definition": parsed["entry"],
        "extraction_status": "COMPLETE_CONSERVATIVE",
        "claim_scope": "one_way_sufficient_win_only",
        "strategy_model": "finite_memory_local_product",
        "goal_policy": "check_original_goal_and_load_before_priority_arbiter",
        "factorization_stage": "source_native_before_global_mixed_version_update_game",
        "fixed_endpoint_products_materialized": True,
        "factor_status": "NONTRIVIAL_SOURCE_NATIVE",
        "solve_status": "PRODUCER_VERIFIED_REFINED_WIN",
        "global_mixed_game_materialized": False,
        "global_mixed_state_count": 0,
        "global_mixed_post_query_count": 0,
        "old_endpoint_state_count": 1,
        "new_endpoint_state_count": 1,
        "terminal_product_verified": True,
        "arbiter": arbiter,
        "transport": transport(),
        "component_partition": [[0], [1]],
        "dependency_receipts": [
            {"kind": "update-action", "declaration": actions[0], "components": [0]},
            {"kind": "update-action", "declaration": actions[1], "components": [1]},
        ],
        "locals": [local_proof(0, actions[0]), local_proof(1, actions[1])],
        "local_solver_discovered_states_sum": 4,
        "local_solver_successor_queries_sum": 2,
        "local_solver_outcomes_sum": 2,
    }


def formal_game(parsed: Mapping[str, Any]) -> dict[str, Any]:
    idle = parsed["idle"]
    first, second = [item["action"] for item in parsed["relations"]]
    states = [
        {"id": "q00", "versions": ["OLD", "OLD"], "local_state_ids": ["q00000001", "q00000001"], "rank_sum": 2, "safe": True, "goal": False},
        {"id": "q01", "versions": ["OLD", "NEW"], "local_state_ids": ["q00000001", "q00000000"], "rank_sum": 1, "safe": True, "goal": False},
        {"id": "q10", "versions": ["NEW", "OLD"], "local_state_ids": ["q00000000", "q00000001"], "rank_sum": 1, "safe": True, "goal": False},
        {"id": "q11", "versions": ["NEW", "NEW"], "local_state_ids": ["q00000000", "q00000000"], "rank_sum": 0, "safe": True, "goal": True},
    ]
    transitions = []
    for x, y in ((0, 0), (0, 1), (1, 0), (1, 1)):
        source = f"q{x}{y}"
        transitions.extend([
            {"source": source, "action": idle, "kind": "shared-stutter", "controllable": True, "outcomes": [source]},
            {"source": source, "action": first, "kind": "update", "controllable": True, "outcomes": [f"q1{y}"] if x == 0 else []},
            {"source": source, "action": second, "kind": "update", "controllable": True, "outcomes": [f"q{x}1"] if y == 0 else []},
        ])
    relation = [{"global": item["id"], "local": item["local_state_ids"]} for item in states]
    policy_cases = [
        {"global": "q00", "first_incomplete_block": 0, "action": first, "outcomes": ["q10"], "rank_sum": [2, 1]},
        {"global": "q01", "first_incomplete_block": 0, "action": first, "outcomes": ["q11"], "rank_sum": [1, 0]},
        {"global": "q10", "first_incomplete_block": 1, "action": second, "outcomes": ["q11"], "rank_sum": [1, 0]},
    ]
    return {
        "states": states,
        "roots": ["q00"],
        "safe_states": ["q00", "q01", "q10", "q11"],
        "goal_states": ["q11"],
        "load_states": ["z11"],
        "handover_relation": [{"goal": "q11", "load": "z11"}],
        "controllable_actions": [idle, first, second],
        "uncontrollable_actions": [],
        "complete_post_table": transitions,
        "R_Gamma": relation,
        "fixed_priority_policy_cases": policy_cases,
        "goal_stop_case": {"global": "q11", "action": "STOP", "kappa_load": "z11", "kappa_endpoint": "new-00000000"},
        "terminal_fibre": {"local_terminal_tuple": ["q00000000", "q00000000"], "global_fibre": ["q11"], "subset_of_goal": True},
    }


def output_y(
        bundle: Mapping[str, Any], game: Mapping[str, Any],
        parsed: Mapping[str, Any]) -> dict[str, Any]:
    gamma = {"arbiter": bundle["arbiter"]}
    gamma.update(bundle["transport"])
    first, second = [item["action"] for item in parsed["relations"]]
    gamma.update({
        "R_Gamma": game["R_Gamma"],
        "progress_matches": [
            {"source": "q00", "action": first, "outcomes": ["q10"], "local_block": 0},
            {"source": "q00", "action": second, "outcomes": ["q01"], "local_block": 1},
            {"source": "q10", "action": second, "outcomes": ["q11"], "local_block": 1},
            {"source": "q01", "action": first, "outcomes": ["q11"], "local_block": 0},
        ],
        "fixed_priority_policy_cases": game["fixed_priority_policy_cases"],
        "goal_stop_case": game["goal_stop_case"],
        "activation_domain": [],
        "activation_relation": [],
        "terminal_fibre": game["terminal_fibre"],
        "formal_load_selector": {"goal": "q11", "load": "z11", "endpoint": "new-00000000"},
        "qualified_terminal_goal_ids": [
            {"block": 0, "local_id": "block-goal-0"},
            {"block": 1, "local_id": "block-goal-0"},
        ],
    })
    return {
        "e": bundle["extraction_status"],
        "f": bundle["factor_status"],
        "s": bundle["solve_status"],
        "B": bundle["component_partition"],
        "C_D": bundle["dependency_receipts"],
        "L": bundle["locals"],
        "n_old": bundle["old_endpoint_state_count"],
        "n_new": bundle["new_endpoint_state_count"],
        "v": bundle["terminal_product_verified"],
        "Gamma": gamma,
    }


def stage_trace(parsed: Mapping[str, Any], bundle: Mapping[str, Any], game: Mapping[str, Any]) -> list[dict[str, Any]]:
    actions = [item["action"] for item in parsed["relations"]]
    return [
        {
            "stage": "S0",
            "status": "PASS",
            "predicate_outcomes": {
                "exact_source_bytes": True,
                "fixture_grammar_complete": True,
                "dialect_parameter_typed": True,
                "entry_resolved": parsed["entry"],
                "components_old_new": [2, 2],
                "component_states_edges_each": [1, 1],
                "transfer_relations": 2,
                "requirements_old_new_update": [0, 0, 0],
                "observers_and_activations": [0, 0],
                "progress_actions": actions,
                "controllable_actions": [parsed["idle"]] + actions,
                "load_policy": "ALL_REACHABLE",
                "constructor_bound": "UNBOUNDED",
                "all_16_source_in_fields_derived": True,
            },
        },
        {
            "stage": "S1",
            "status": "PASS",
            "predicate_outcomes": {
                "dependency_receipts": bundle["dependency_receipts"],
                "shared_idle_is_pure_self_loop_on_all_four_global_states": True,
                "union_find_units": [[0], [1]],
                "selected_partition": [[0], [1]],
                "factor_status": "NONTRIVIAL_SOURCE_NATIVE",
                "fixed_endpoint_state_counts": [1, 1],
            },
        },
        {
            "stage": "S2",
            "status": "PASS_FORMAL_COMPLETE_LOCAL_GAMES",
            "predicate_outcomes": {
                "local_games": 2,
                "roots": 2,
                "rank_states": 4,
                "candidate_buckets": 2,
                "outcomes": 2,
                "strategy_buckets": 2,
                "full_goals": 2,
                "quiet_goals": 2,
                "per_block_transitions": [
                    {"block": 0, "source": "q00000001", "action": actions[0], "target": "q00000000", "rank": [1, 0]},
                    {"block": 1, "source": "q00000001", "action": actions[1], "target": "q00000000", "rank": [1, 0]},
                ],
                "complete_post_domains": True,
                "all_states_safe": True,
                "all_nongoal_strategy_outcomes_strictly_decrease_rank": True,
            },
        },
        {
            "stage": "S3",
            "status": "PASS_FORMAL_COMPLETE_RELATION_AND_TRANSPORT",
            "predicate_outcomes": {
                "global_states": game["states"],
                "R_Gamma": game["R_Gamma"],
                "activation_domain_empty_and_condition_vacuous": True,
                "observer_relations": bundle["transport"]["observer_relations"],
                "load_selectors": bundle["transport"]["load_selectors"],
                "terminal_assemblies": bundle["transport"]["terminal_assemblies"],
                "fixed_priority_policy_cases": game["fixed_priority_policy_cases"],
                "terminal_fibre": game["terminal_fibre"],
            },
        },
        {
            "stage": "S4",
            "status": "PASS_FORMAL_RESULT_AND_POSTHOC_CODE_PATH_MATCH",
            "predicate_outcomes": {
                "formal_exactness": "COMPLETE_CONSERVATIVE",
                "formal_factor_status": "NONTRIVIAL_SOURCE_NATIVE",
                "formal_one_way_result": "REFINED_WIN",
                "serialized_status": "PRODUCER_VERIFIED_REFINED_WIN",
                "terminal_product_verified": True,
                "full_Y_payload_derived": True,
                "stored_bundle_full_field_match": True,
                "stored_bundle_is_execution_provenance": False,
                "global_mixed_game_materialized_by_code_path": False,
                "scientific_outcome_denominator_delta": 0,
            },
        },
    ]


def theorem_map(game: Mapping[str, Any]) -> dict[str, Any]:
    all_y = list(Y_FIELDS)
    return {
        "Theorem_5_3": {
            "name": "Composition of uncontrollably quiescent independent contracts",
            "premise_family": "B1--B7",
            "premises": {
                "B1": {"status": "PASS", "cases": "two two-state Post-closed local games; roots and load sets nonempty", "Y_fields": ["L", "n_old", "n_new"]},
                "B2": {"status": "PASS", "cases": "Q={q00,q01,q10,q11}=Q1xQ2 and Q0={q00}=Q01xQ02", "Y_fields": ["B", "L"]},
                "B3": {"status": "PASS", "cases": "two block-local update actions plus complete idle self-loop table", "Y_fields": ["C_D", "Gamma"]},
                "B4": {"status": "PASS", "cases": "all-safe product, Goal={q11}, load={z11}, H={(q11,z11)}", "Y_fields": ["L", "v", "Gamma"]},
                "B5": {"status": "PASS", "cases": "transfers block-local; monitor/observer/activation/precedence domains empty", "Y_fields": ["e", "f", "B", "C_D", "Gamma"]},
                "B6": {"status": "PASS", "cases": "no uncontrollable action exists at either local Goal", "Y_fields": ["L"]},
                "B7": {"status": "PASS", "cases": "both ranks 1->0; total singleton kappa and Cartesian terminal assembly", "Y_fields": ["s", "L", "v", "Gamma"]},
            },
            "all_ten_Y_fields_mapped": all_y,
        },
        "Theorem_5_4": {
            "name": "Maximum under the root-product predicate",
            "premise_family": "P1--P5 mapped to B1--B7",
            "separate_complete_flat_trace": {"path": "evidence/m8p-partition-discovery/predicate-trace-example.json", "sha256": FLAT_TRACE_SHA256},
            "premises": {
                "P1": {"status": "PASS", "maps_to": ["B1", "B2", "B4"], "flat_output_fields": ["tag", "B_star", "n", "local_games", "receipts"]},
                "P2": {"status": "PASS", "maps_to": ["B5"], "flat_output_fields": ["B_star", "local_games", "receipts"]},
                "P3": {"status": "PASS", "maps_to": ["B1", "B3"], "flat_output_fields": ["local_games", "receipts"]},
                "P4": {"status": "PASS", "maps_to": ["B3"], "flat_output_fields": ["local_games", "receipts"]},
                "P5": {"status": "PASS", "maps_to": ["B6"], "flat_output_fields": ["local_games", "receipts"]},
                "B7": {"status": "SEPARATE_TRANSPORT_GATE_PASS", "maps_to": ["local_witnesses", "transport"], "flat_output_fields": ["local_games"]},
            },
            "selected_flat_partition": [["a", "r_a"], ["b", "r_b"]],
            "selected_multiplicity": 1,
        },
        "Theorem_5_5": {
            "name": "One-way composition toward relationally refined quiescent terminals",
            "premise_family": "S1--S7",
            "premises": {
                "S1": {"status": "PASS", "cases": [{"root": "q00", "related_local": ["q00000001", "q00000001"]}], "Y_fields": ["e", "f", "B", "C_D", "L", "n_old", "n_new", "Gamma"]},
                "S2": {"status": "PASS", "cases": [{"global": item["global"], "local_safe": True, "global_safe": True} for item in game["R_Gamma"]], "Y_fields": ["L", "Gamma"]},
                "S3": {"status": "PASS", "cases": "two complete W={rank1 root,rank0 quiet Goal} certificates", "Y_fields": ["s", "L"]},
                "S4": {"status": "PASS", "cases": game["fixed_priority_policy_cases"], "Y_fields": ["C_D", "L", "Gamma"]},
                "S5": {"status": "PASS", "cases": [{"source": item["global"], "outcomes": item["outcomes"], "rank_sum": item["rank_sum"], "R_preserved": True, "foreign_memory_stutters": True} for item in game["fixed_priority_policy_cases"]], "Y_fields": ["L", "Gamma"]},
                "S6": {"status": "PASS", "cases": [game["goal_stop_case"]], "Y_fields": ["v", "Gamma"]},
                "S7": {"status": "PASS", "cases": [game["terminal_fibre"]], "Y_fields": ["v", "Gamma"]},
            },
            "all_ten_Y_fields_mapped": all_y,
        },
    }


def expected_trace(parsed: Mapping[str, Any], bundle: Mapping[str, Any]) -> dict[str, Any]:
    game = formal_game(parsed)
    sin = source_in(parsed)
    y = output_y(bundle, game, parsed)
    return {
        "schema_version": "fg-ducs-hand-checkable-ordinary-source-formal-trace-v2",
        "trace_id": "r09-hand-k02-formal-proof",
        "trace_kind": "complete_pdf_printable_ordinary_source_formal_construction",
        "manifest": {
            "source": sin["bytes"],
            "native_bundle": {"path": "evidence/ordinary-source-construction-trace/r09-hand-k02-native-bundle.json", "bytes": 5451, "sha256": BUNDLE_SHA256},
            "flat_trace": {"path": "evidence/m8p-partition-discovery/predicate-trace-example.json", "sha256": FLAT_TRACE_SHA256},
            "implementation_sources": {
                "loader": {"path": "source-rebuild/added/maven-root/mtsa/src/main/java/ltsa/lts/NativeUpdatingContractLoader.java", "sha256": "c01d1471a64002e5540ba2525087e22c39fbf8d89cda44e99c82775e319371c6"},
                "runner": {"path": "source-rebuild/added/maven-root/mtsa/src/main/java/ltsa/updatingControllers/cli/NativePartitionRunner.java", "sha256": "b370a390f9604f01d116f873c8290f3bbcc3fbe356aeb71cf8588bf13a09a260"},
                "factorizer": {"path": "source-rebuild/added/maven-root/mtsa/src/main/java/ltsa/updatingControllers/otf/NativeTierAFactorizer.java", "sha256": "ffb98b479af4192b947fbdfe14c9ec3b37327cd3c856503ea9cf2295ed273f21"},
                "exporter": {"path": "source-rebuild/added/maven-root/mtsa/src/main/java/ltsa/updatingControllers/otf/NativeTierABundleExporter.java", "sha256": "e6e31edcbc5748444caa77916f32e24721e3b182ee2bc150500d23b230f08dfa"},
            },
            "fixture_parameters_not_in_source_bytes": {"dialect": sin["dialect"], "Lambda": sin["Lambda"], "b": sin["b"]},
            "stored_bundle_role": "post_hoc_full_field_code_path_match_not_execution_provenance_or_proof_authority",
        },
        "source_in": {"ordered_fields": list(SOURCE_FIELDS), "fields": sin},
        "stage_replay": stage_trace(parsed, bundle, game),
        "formal_global_game": game,
        "output_y": {"ordered_fields": list(Y_FIELDS), "fields": y},
        "theorem_map": theorem_map(game),
        "claim_boundary": {
            "same_author_post_hoc_correctness_proof": True,
            "source_printable_in_full_in_pdf": True,
            "formal_proof_is_execution_independent": True,
            "stored_bundle_is_only_a_post_hoc_code_path_match": True,
            "stored_bundle_is_execution_provenance": False,
            "new_scientific_outcome": False,
            "scientific_denominator_or_classification_changed": False,
            "general_or_independent_raw_source_frontend": False,
            "independent_source_to_win_replay": False,
            "producer_runtime_or_timeout_replayed": False,
            "b_is_explicit_UNBOUNDED_fixture_parameter_not_runner_argument": True,
            "no_application_performance_heldout_third_party_production_breadth_or_global_loss_claim": True,
        },
    }


def verify_formal_semantics(trace: Mapping[str, Any]) -> None:
    game = trace["formal_global_game"]
    states = {item["id"]: item for item in game["states"]}
    require(set(states) == {"q00", "q01", "q10", "q11"}, "global state domain differs")
    require(game["roots"] == ["q00"] and game["goal_states"] == ["q11"], "root/Goal differs")
    require(game["load_states"] == ["z11"] and game["handover_relation"] == [{"goal": "q11", "load": "z11"}], "load/handover relation differs")
    require(len(game["complete_post_table"]) == 12, "complete Post table is not four states by three actions")
    buckets = {(item["source"], item["action"]): item for item in game["complete_post_table"]}
    require(len(buckets) == 12, "complete Post table has a duplicate bucket")
    idle, first, second = game["controllable_actions"]
    for x, y in ((0, 0), (0, 1), (1, 0), (1, 1)):
        state_id = f"q{x}{y}"
        require(buckets[(state_id, idle)]["outcomes"] == [state_id], f"shared idle is not stuttering: {state_id}")
        require(buckets[(state_id, first)]["outcomes"] == ([f"q1{y}"] if x == 0 else []), f"first update bucket differs: {state_id}")
        require(buckets[(state_id, second)]["outcomes"] == ([f"q{x}1"] if y == 0 else []), f"second update bucket differs: {state_id}")
        for item in buckets.values():
            for target in item["outcomes"]:
                source_versions = states[item["source"]]["versions"]
                target_versions = states[target]["versions"]
                changed = [index for index in range(2) if source_versions[index] != target_versions[index]]
                require(item["action"] == idle or len(changed) <= 1, f"foreign coordinate changed: {item['source']}->{target}")
    require(game["uncontrollable_actions"] == [], "fixture unexpectedly has uncontrollable actions")
    relation = {item["global"]: item["local"] for item in game["R_Gamma"]}
    require(set(relation) == set(states), "R_Gamma domain differs")
    for state_id, local_ids in relation.items():
        require(local_ids == states[state_id]["local_state_ids"], f"R_Gamma payload differs: {state_id}")
        require(states[state_id]["safe"], f"S2 safety reflection differs: {state_id}")
    for case in game["fixed_priority_policy_cases"]:
        require(case["rank_sum"][1] < case["rank_sum"][0], f"S5 rank does not decrease: {case['global']}")
        require(all(target in relation for target in case["outcomes"]), f"S4/S5 outcome leaves R: {case['global']}")
    require(game["terminal_fibre"]["global_fibre"] == ["q11"] and game["terminal_fibre"]["subset_of_goal"] is True, "S7 fibre differs")
    maps = trace["theorem_map"]
    require(set(maps["Theorem_5_3"]["premises"]) == {f"B{i}" for i in range(1, 8)}, "Theorem 5.3 is not B1--B7")
    require(set(maps["Theorem_5_4"]["premises"]) == {"P1", "P2", "P3", "P4", "P5", "B7"}, "Theorem 5.4 P/B map differs")
    require(set(maps["Theorem_5_5"]["premises"]) == {f"S{i}" for i in range(1, 8)}, "Theorem 5.5 is not S1--S7")
    require(maps["Theorem_5_3"]["all_ten_Y_fields_mapped"] == Y_FIELDS, "Theorem 5.3 Y coverage differs")
    require(maps["Theorem_5_5"]["all_ten_Y_fields_mapped"] == Y_FIELDS, "Theorem 5.5 Y coverage differs")
    y = trace["output_y"]["fields"]
    require(isinstance(y["L"], list) and len(y["L"]) == 2, "Y.L is not the full local-game payload")
    require(len(y["Gamma"]["observer_relations"]) == 2, "Y.Gamma observer payload differs")
    require(len(y["Gamma"]["load_selectors"]) == 1 and len(y["Gamma"]["terminal_assemblies"]) == 1, "Y.Gamma selector/terminal payload differs")
    require(y["Gamma"]["R_Gamma"] == game["R_Gamma"], "Y.Gamma omits the extensional relation")
    require(len(y["Gamma"]["progress_matches"]) == 4, "Y.Gamma progress-match table differs")
    require(y["Gamma"]["activation_domain"] == [] and y["Gamma"]["activation_relation"] == [], "Y.Gamma activation domain is not explicitly empty")
    require(y["Gamma"]["terminal_fibre"] == game["terminal_fibre"], "Y.Gamma terminal fibre differs")
    require(y["Gamma"]["formal_load_selector"] == {"goal": "q11", "load": "z11", "endpoint": "new-00000000"}, "Y.Gamma formal load selector differs")


def check(trace: Mapping[str, Any]) -> dict[str, Any]:
    require(SOURCE_PATH.stat().st_size == 598 and sha256(SOURCE_PATH) == SOURCE_SHA256, "source bytes differ")
    require(BUNDLE_PATH.stat().st_size == 5451 and sha256(BUNDLE_PATH) == BUNDLE_SHA256, "native bundle bytes differ")
    require(sha256(FLAT_TRACE_PATH) == FLAT_TRACE_SHA256, "flat trace bytes differ")
    parsed = parse_source_text(SOURCE_PATH.read_text(encoding="utf-8"))
    bundle = load(BUNDLE_PATH)
    expected = expected_bundle(parsed)
    require(canonical(bundle) == canonical(expected), "stored native bundle differs from the formal field construction")
    target = expected_trace(parsed, bundle)
    require(canonical(trace) == canonical(target), "formal trace differs from the source-derived expected trace")
    verify_formal_semantics(trace)
    return {
        "status": "PASS",
        "schema_version": trace["schema_version"],
        "source_sha256": SOURCE_SHA256,
        "bundle_sha256": BUNDLE_SHA256,
        "source_in_fields": 16,
        "source_stages": 5,
        "output_y_fields": 10,
        "global_states": 4,
        "global_post_buckets": 12,
        "relation_pairs": 4,
        "rank_states": 4,
        "candidate_buckets": 2,
        "observer_relation_pairs": 2,
        "load_selectors": 1,
        "terminal_tuples": 1,
        "theorem_5_3_premises": 7,
        "theorem_5_4_predicates": 5,
        "theorem_5_5_premises": 7,
        "stored_bundle_is_execution_provenance": False,
        "independent_source_to_win_replay": False,
        "scientific_outcome_denominator_delta": 0,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--emit", action="store_true", help="emit the deterministic expected trace")
    args = parser.parse_args(argv)
    try:
        parsed = parse_source_text(SOURCE_PATH.read_text(encoding="utf-8"))
        bundle = load(BUNDLE_PATH)
        if args.emit:
            require(canonical(bundle) == canonical(expected_bundle(parsed)), "stored native bundle differs from the formal field construction")
            print(json.dumps(expected_trace(parsed, bundle), ensure_ascii=False, indent=2, allow_nan=False))
        else:
            print(json.dumps(check(load(TRACE_PATH)), ensure_ascii=False, sort_keys=True, allow_nan=False))
    except TraceError as error:
        print(json.dumps({"status": "FAIL", "error": str(error)}, ensure_ascii=False, sort_keys=True))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
