#!/usr/bin/env python3
"""Non-importing structural consistency checker for native-WIN bundles.

This checker deliberately does not import the Java producer or any Python
partition/witness producer.  It validates the serialized local rank/policy
proofs, conservative dependency partition, observer abstraction fibres, full
load selector, and concrete terminal-to-load assembly.  It does *not*
reconstruct ordinary-LTS semantics, roots, enabled actions, or Post.  The
ordinary-LTS-to-bundle translation therefore remains an explicit producer
TCB; a surrounding registered audit authenticates source and bundle bytes.
Successful output is deliberately named STRUCTURALLY_CHECKED_PRODUCER_WITNESS,
not independently verified WIN.
"""

from __future__ import annotations

import argparse
import itertools
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


SCHEMA = "fg-ducs-native-tier-a-result-v4"
TRANSPORT_KEYS = {
    "verified", "activation_tester_count", "activation_relation_pair_count",
    "observer_relation_pair_count", "load_selector_signature_count",
    "load_selector_endpoint_count", "certificate_terminal_tuple_count",
    "terminal_observer_fiber_count", "observer_relations", "load_selectors",
    "terminal_assemblies",
}


class BundleError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise BundleError(message)


def exact_int(value: Any, label: str, minimum: int = 0) -> int:
    require(type(value) is int and value >= minimum, f"{label} is not an exact integer")
    return value


def exact_bool(value: Any, label: str) -> bool:
    require(type(value) is bool, f"{label} is not a boolean")
    return value


def text(value: Any, label: str) -> str:
    require(isinstance(value, str) and bool(value.strip()), f"{label} is not text")
    return value


def object_(value: Any, label: str) -> dict[str, Any]:
    require(isinstance(value, dict) and all(isinstance(k, str) for k in value), f"{label} is not an object")
    return value


def array(value: Any, label: str) -> list[Any]:
    require(isinstance(value, list), f"{label} is not an array")
    return value


def exact_keys(value: Mapping[str, Any], keys: Iterable[str], label: str) -> None:
    expected = set(keys)
    require(set(value) == expected, f"{label} fields differ: {sorted(set(value) ^ expected)}")


def int_list(value: Any, label: str, *, unique: bool = False) -> list[int]:
    result = [exact_int(item, f"{label}[]") for item in array(value, label)]
    if unique:
        require(len(result) == len(set(result)), f"{label} contains duplicates")
    return result


def string_list(value: Any, label: str, *, unique: bool = False) -> list[str]:
    result = [text(item, f"{label}[]") for item in array(value, label)]
    if unique:
        require(len(result) == len(set(result)), f"{label} contains duplicates")
    return result


def canonical(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as error:
        raise BundleError("bundle contains non-canonical JSON values") from error


def state_payload(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "physical": record["physical"],
        "active_testers": record["active_testers"],
        "pending_actions": record["pending_actions"],
    }


def java_state_key(record: Mapping[str, Any]) -> str:
    # Java emits these three LinkedHashMap fields in this exact order.
    return json.dumps(state_payload(record), ensure_ascii=False, separators=(",", ":"), allow_nan=False)


class UnionFind:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))

    def find(self, value: int) -> int:
        while self.parent[value] != value:
            self.parent[value] = self.parent[self.parent[value]]
            value = self.parent[value]
        return value

    def join(self, left: int, right: int) -> None:
        a, b = self.find(left), self.find(right)
        if a != b:
            self.parent[max(a, b)] = min(a, b)

    def blocks(self) -> list[list[int]]:
        values: dict[int, list[int]] = defaultdict(list)
        for value in range(len(self.parent)):
            values[self.find(value)].append(value)
        return sorted(values.values(), key=lambda block: block[0])


def check_component(component: Any, label: str) -> dict[str, Any]:
    value = object_(component, label)
    exact_keys(value, {"version", "raw_state", "observer_states"}, label)
    require(value["version"] in {"OLD", "NEW"}, f"{label}.version is invalid")
    exact_int(value["raw_state"], f"{label}.raw_state")
    int_list(value["observer_states"], f"{label}.observer_states")
    return value


def check_goal_signature(value: Any, state: Mapping[str, Any], label: str) -> dict[str, Any]:
    goal = object_(value, label)
    exact_keys(goal, {"id", "physical", "new_requirement_states"}, label)
    text(goal["id"], f"{label}.id")
    physical = array(goal["physical"], f"{label}.physical")
    for index, component in enumerate(physical):
        check_component(component, f"{label}.physical[{index}]")
    testers = object_(goal["new_requirement_states"], f"{label}.new_requirement_states")
    for key, residual in testers.items():
        text(key, f"{label}.new_requirement_states key")
        exact_int(residual, f"{label}.new_requirement_states[{key}]")
    require(physical == state["physical"], f"{label} physical differs from its goal state")
    active = object_(state["active_testers"], f"{label} active testers")
    active_new = {key: residual for key, residual in active.items() if key.startswith("new:")}
    require(active_new == testers, f"{label} new tester projection differs from its goal state")
    return goal


def check_local(local: Any, expected_index: int, expected_block: list[int]) -> dict[str, Any]:
    value = object_(local, f"locals[{expected_index}]")
    required = {
        "block_index", "components", "full_goal_count", "quiet_terminal_count",
        "full_goal_uncontrollable_actions", "decision", "solver_discovered_states",
        "solver_successor_queries", "solver_outcomes", "certificate_initial_count",
        "certificate_rank_count", "certificate_strategy_source_count",
        "certificate_strategy_bucket_count", "certificate_goal_match_count", "proof",
        "independent_certificate_valid", "independent_certificate_basis",
        "independent_certificate_states", "independent_certificate_queries",
        "independent_certificate_outcomes", "independent_certificate_elapsed_ms",
    }
    exact_keys(value, required, f"locals[{expected_index}]")
    require(exact_int(value["block_index"], "local block index") == expected_index, "local block order differs")
    require(int_list(value["components"], "local components", unique=True) == expected_block, "local components differ from partition")
    require(value["decision"] == "realizable", "refined-WIN local is not realizable")
    require(exact_bool(value["independent_certificate_valid"], "independent certificate valid"), "independent certificate is invalid")
    for field in (
        "full_goal_count", "quiet_terminal_count", "solver_discovered_states",
        "solver_successor_queries", "solver_outcomes", "certificate_initial_count",
        "certificate_rank_count", "certificate_strategy_source_count",
        "certificate_strategy_bucket_count", "certificate_goal_match_count",
        "independent_certificate_states", "independent_certificate_queries",
        "independent_certificate_outcomes", "independent_certificate_elapsed_ms",
    ):
        exact_int(value[field], f"local {field}")
    require(value["quiet_terminal_count"] > 0, "local quiet target is empty")
    full_goal_uc = string_list(value["full_goal_uncontrollable_actions"], "full Goal UC actions", unique=True)
    require(value["independent_certificate_basis"] == "independent_certificate_proof", "independent certificate basis differs")

    proof = object_(value["proof"], "local proof")
    exact_keys(proof, {"schema_version", "semantic_basis", "root_state_ids", "states", "candidate_buckets", "strategy_buckets"}, "local proof")
    require(proof["schema_version"] == "fg-ducs-local-rank-proof-v1", "local proof schema differs")
    require(proof["semantic_basis"] == "independent_fine_grained_semantics", "local semantic basis differs")

    state_records = array(proof["states"], "local proof states")
    states: dict[str, dict[str, Any]] = {}
    state_keys: dict[str, str] = {}
    semantic_payload_keys: set[str] = set()
    goal_by_id: dict[str, dict[str, Any]] = {}
    for offset, raw in enumerate(state_records):
        state = object_(raw, f"local state[{offset}]")
        exact_keys(state, {"physical", "active_testers", "pending_actions", "id", "rank", "safe", "goal", "goal_signature_id", "goal_signature"}, f"local state[{offset}]")
        state_id = text(state["id"], "local state id")
        require(state_id not in states, "duplicate local state id")
        physical = array(state["physical"], "local state physical")
        require(len(physical) == len(expected_block), "local state physical arity differs")
        for index, component in enumerate(physical):
            check_component(component, f"local state physical[{index}]")
        active = object_(state["active_testers"], "local active testers")
        for key, residual in active.items():
            text(key, "active tester key")
            exact_int(residual, f"active tester {key}")
        pending = string_list(state["pending_actions"], "local pending", unique=True)
        require(pending == sorted(pending), "local pending set is not canonical")
        rank = exact_int(state["rank"], "local rank")
        require(exact_bool(state["safe"], "local safe"), "rank domain contains unsafe state")
        is_goal = exact_bool(state["goal"], "local goal")
        if is_goal:
            require(rank == 0, "local Goal rank is not zero")
            require(not pending, "local Goal retains a pending update")
            require(all(component["version"] == "NEW" for component in physical), "local Goal contains an OLD component")
            goal_id = text(state["goal_signature_id"], "goal signature id")
            goal = check_goal_signature(state["goal_signature"], state, "goal signature")
            require(goal["id"] == goal_id, "goal signature id/payload differ")
            require(goal_id not in goal_by_id or canonical(goal_by_id[goal_id]) == canonical(goal), "one goal id denotes different signatures")
            goal_by_id[goal_id] = goal
            require(
                all(key.startswith(("new:", "update_time:")) for key in active),
                "local Goal contains an untyped old/foreign tester",
            )
        else:
            require(rank > 0, "non-Goal rank is not positive")
            require(state["goal_signature_id"] is None and state["goal_signature"] is None, "non-Goal carries a goal signature")
        states[state_id] = state
        state_keys[state_id] = java_state_key(state)
        semantic_key = canonical(state_payload(state))
        require(
            semantic_key not in semantic_payload_keys,
            "two local state IDs denote the same typed semantic payload",
        )
        semantic_payload_keys.add(semantic_key)

    require(len(states) == value["certificate_rank_count"], "rank census differs")
    roots = string_list(proof["root_state_ids"], "local roots", unique=True)
    require(roots == sorted(roots) and roots and set(roots) <= set(states), "local root set is invalid")
    require(len(roots) == value["certificate_initial_count"], "root census differs")
    require(len(goal_by_id) == value["certificate_goal_match_count"], "goal signature census differs")
    require(value["full_goal_count"] >= value["quiet_terminal_count"] >= len(goal_by_id) > 0, "full/quiet/certificate Goal census differs")

    candidates: dict[tuple[str, str], dict[str, Any]] = {}
    action_control: dict[str, bool] = {}
    action_update: dict[str, bool] = {}
    for offset, raw in enumerate(array(proof["candidate_buckets"], "candidate buckets")):
        bucket = object_(raw, f"candidate bucket[{offset}]")
        exact_keys(bucket, {"source", "action", "controllable", "update", "target_keys"}, f"candidate bucket[{offset}]")
        source = text(bucket["source"], "candidate source")
        action = text(bucket["action"], "candidate action")
        require(source in states, "candidate source is outside rank domain")
        control = exact_bool(bucket["controllable"], "candidate controllability")
        update = exact_bool(bucket["update"], "candidate update flag")
        require(update == (action in states[source]["pending_actions"]), "candidate update flag differs from source pending membership")
        targets = string_list(bucket["target_keys"], "candidate target keys", unique=True)
        require(targets == sorted(targets), "candidate target keys are not canonical")
        key = (source, action)
        require(key not in candidates, "duplicate candidate bucket")
        candidates[key] = bucket
        require(action not in action_control or action_control[action] == control, "action controllability is context-dependent")
        action_control[action] = control
        require(action not in action_update or action_update[action] == update, "action update kind is context-dependent")
        action_update[action] = update

    for state_id, state in states.items():
        declared = {action for source, action in candidates if source == state_id}
        require(set(state["pending_actions"]) <= declared, "a pending update has no candidate bucket")

    strategies: dict[tuple[str, str], list[str]] = {}
    by_source: dict[str, set[str]] = defaultdict(set)
    for offset, raw in enumerate(array(proof["strategy_buckets"], "strategy buckets")):
        bucket = object_(raw, f"strategy bucket[{offset}]")
        exact_keys(bucket, {"source", "action", "target_state_ids"}, f"strategy bucket[{offset}]")
        source = text(bucket["source"], "strategy source")
        action = text(bucket["action"], "strategy action")
        key = (source, action)
        require(key in candidates and key not in strategies, "strategy bucket has no unique candidate")
        target_ids = string_list(bucket["target_state_ids"], "strategy targets", unique=True)
        require(target_ids == sorted(target_ids) and target_ids, "strategy targets are not canonical/nonempty")
        require(set(target_ids) <= set(states), "strategy leaves rank domain")
        require([state_keys[target] for target in target_ids] == candidates[key]["target_keys"], "strategy targets differ from complete candidate Post")
        source_rank = states[source]["rank"]
        require(all(states[target]["rank"] < source_rank for target in target_ids), "strategy rank does not strictly decrease for every outcome")
        strategies[key] = target_ids
        by_source[source].add(action)

    require(len(strategies) == value["certificate_strategy_bucket_count"], "strategy bucket census differs")
    require(len(by_source) == value["certificate_strategy_source_count"], "strategy source census differs")
    require(len(candidates) > 0, "local candidate table is empty")
    for state_id, state in states.items():
        enabled_uc = {
            action for (source, action), bucket in candidates.items()
            if source == state_id and bucket["target_keys"] and not bucket["controllable"]
        }
        enabled_c = {
            action for (source, action), bucket in candidates.items()
            if source == state_id and bucket["target_keys"] and bucket["controllable"]
        }
        selected = by_source.get(state_id, set())
        if state["goal"]:
            require(not enabled_uc and not selected, "quiet Goal has UC activity or a progress policy")
        elif enabled_uc:
            require(selected == enabled_uc, "non-Goal does not retain every enabled UC bucket")
        else:
            require(len(selected) == 1 and selected <= enabled_c, "non-Goal does not choose one enabled controllable bucket")

    update_actions = {action for action, update in action_update.items() if update}
    ordinary_actions = set(action_update) - update_actions
    require(all(action_control[action] for action in update_actions), "an update action is uncontrollable")
    expected_roots = {
        state_id
        for state_id, state in states.items()
        if all(component["version"] == "OLD" for component in state["physical"])
        and set(state["pending_actions"]) == update_actions
    }
    require(set(roots) == expected_roots, "serialized root set differs from all-OLD/full-pending rank states")
    non_goal_candidates = [
        bucket for bucket in candidates.values() if not states[bucket["source"]]["goal"]
    ]
    require(value["independent_certificate_states"] == len(states), "independent state census differs from rank domain")
    require(value["independent_certificate_queries"] == len(non_goal_candidates), "independent query census differs from candidate table")
    require(
        value["independent_certificate_outcomes"]
        == sum(len(bucket["target_keys"]) for bucket in non_goal_candidates),
        "independent outcome census differs from candidate table",
    )
    require(set(full_goal_uc) <= {action for action in ordinary_actions if not action_control[action]}, "full Goal UC census names an unknown/non-UC action")

    active_tester_ids = {
        tester for state in states.values() for tester in state["active_testers"]
    }
    require(
        all(tester.startswith(("old:", "new:", "update_time:")) and tester.count(":") >= 2 for tester in active_tester_ids),
        "active tester identifier is not typed",
    )
    tester_ids_by_phase_source: dict[tuple[str, str], str] = {}
    for tester in active_tester_ids:
        phase, remainder = tester.split(":", 1)
        source, ordinal = remainder.rsplit(":", 1)
        require(source and ordinal.isdigit(), "active tester identifier has an invalid source/ordinal")
        key = (phase, source)
        require(
            key not in tester_ids_by_phase_source or tester_ids_by_phase_source[key] == tester,
            "one tester phase/source is represented by multiple ordinals",
        )
        tester_ids_by_phase_source[key] = tester
    tester_sources = {
        tester.split(":", 1)[1].rsplit(":", 1)[0] for tester in active_tester_ids
    }
    goal_new_sources = {
        tester.split(":", 1)[1].rsplit(":", 1)[0]
        for goal in goal_by_id.values()
        for tester in goal["new_requirement_states"]
    }

    return {
        "states": states,
        "state_keys": state_keys,
        "goal_by_id": goal_by_id,
        "roots": roots,
        "candidate_count": len(candidates),
        "strategy_count": len(strategies),
        "ordinary_actions": ordinary_actions,
        "update_actions": update_actions,
        "tester_sources": tester_sources,
        "goal_new_sources": goal_new_sources,
        "anchor_observer_vectors": {
            tuple(state["physical"][0]["observer_states"]) for state in states.values()
        },
        "anchor_observer_arities": {
            len(state["physical"][0]["observer_states"]) for state in states.values()
        },
        "non_anchor_observers_empty": all(
            not component["observer_states"]
            for state in states.values()
            for component in state["physical"][1:]
        ),
    }


def check_transport(
    value: Any,
    locals_: list[dict[str, Any]],
    partition: list[list[int]],
    component_count: int,
    new_endpoint_state_count: int,
) -> dict[str, Any]:
    transport = object_(value, "transport")
    exact_keys(transport, TRANSPORT_KEYS, "transport")
    require(exact_bool(transport["verified"], "transport verified"), "transport is not verified")
    for field in (
        "activation_tester_count", "activation_relation_pair_count",
        "observer_relation_pair_count", "load_selector_signature_count",
        "load_selector_endpoint_count", "certificate_terminal_tuple_count",
        "terminal_observer_fiber_count",
    ):
        exact_int(transport[field], f"transport {field}")
    require(transport["activation_tester_count"] > 0 and transport["activation_relation_pair_count"] > 0, "activation quotient census is empty")

    expected_testers: set[str] = set()
    for local in locals_:
        local_testers = {
            tester
            for goal in local["goal_by_id"].values()
            for tester in goal["new_requirement_states"]
        }
        require(local_testers, "a local proof has no new-requirement tester")
        require(not (expected_testers & local_testers), "a new-requirement tester belongs to multiple blocks")
        expected_testers.update(local_testers)
    require(
        transport["activation_tester_count"] == len(expected_testers),
        "activation tester census differs from the local Goal tester domain",
    )

    selector_by_key: dict[str, dict[str, Any]] = {}
    selector_by_endpoint: dict[str, dict[str, Any]] = {}
    observer_count: int | None = None
    selectors = array(transport["load_selectors"], "load selectors")
    for index, raw in enumerate(selectors):
        selector = object_(raw, f"load selector[{index}]")
        exact_keys(selector, {"endpoint_id", "controller_state", "component_raw_states", "observer_states", "tester_states"}, f"load selector[{index}]")
        endpoint = text(selector["endpoint_id"], "selector endpoint")
        exact_int(selector["controller_state"], "selector controller state")
        components = int_list(selector["component_raw_states"], "selector components")
        require(len(components) == component_count, "selector component arity differs")
        observers = int_list(selector["observer_states"], "selector observers")
        if observer_count is None:
            observer_count = len(observers)
        require(len(observers) == observer_count, "selector observer arity differs")
        testers = object_(selector["tester_states"], "selector tester states")
        for tester, residual in testers.items():
            text(tester, "selector tester id")
            exact_int(residual, f"selector tester {tester}")
        require(set(testers) == expected_testers, "load selector new-tester domain differs from local Goal domains")
        key = canonical([components, observers, testers])
        require(key not in selector_by_key and endpoint not in selector_by_endpoint, "load selector is not functional/injective by endpoint")
        selector_by_key[key] = selector
        selector_by_endpoint[endpoint] = selector
    require(
        len(selectors)
        == transport["load_selector_signature_count"]
        == transport["load_selector_endpoint_count"]
        == new_endpoint_state_count,
        "load selector census differs from the fixed new endpoint",
    )
    require(observer_count is not None, "load selector is empty")
    require(set(selector_by_endpoint) == {f"new-{index:08d}" for index in range(new_endpoint_state_count)}, "load selector endpoint IDs are not the canonical complete endpoint census")

    relation_by_block: dict[int, dict[str, Any]] = {}
    relation_pair_count = 0
    covered: set[int] = set()
    for offset, raw in enumerate(array(transport["observer_relations"], "observer relations")):
        relation = object_(raw, f"observer relation[{offset}]")
        exact_keys(relation, {"block_index", "global_observer_indices", "pairs"}, f"observer relation[{offset}]")
        block = exact_int(relation["block_index"], "observer relation block")
        require(block < len(locals_) and block not in relation_by_block, "observer relation block differs")
        indices = int_list(relation["global_observer_indices"], "global observer indices", unique=True)
        require(all(index < observer_count for index in indices), "observer relation index is out of range")
        require(not (covered & set(indices)), "source observer belongs to multiple block relations")
        local_arities = locals_[block]["anchor_observer_arities"]
        require(len(local_arities) == 1, "local Goal observer arity is inconsistent")
        local_arity = next(iter(local_arities))
        require(
            locals_[block]["non_anchor_observers_empty"],
            "non-anchor local component carries an unmodeled observer vector",
        )
        pairs_seen: set[str] = set()
        pairs = array(relation["pairs"], "observer relation pairs")
        for pair_offset, raw_pair in enumerate(pairs):
            pair = object_(raw_pair, f"observer relation pair[{pair_offset}]")
            exact_keys(pair, {"global", "local"}, "observer relation pair")
            global_values = int_list(pair["global"], "observer pair global")
            local_values = int_list(pair["local"], "observer pair local")
            require(len(global_values) == len(indices), "observer pair global arity differs")
            require(len(local_values) == local_arity, "observer pair local arity differs")
            signature = canonical([global_values, local_values])
            require(signature not in pairs_seen, "duplicate observer relation pair")
            pairs_seen.add(signature)
        require(pairs, "observer relation is empty")
        require(
            locals_[block]["anchor_observer_vectors"]
            <= {tuple(pair["local"]) for pair in pairs},
            "observer relation does not cover every serialized local memory",
        )
        relation_pair_count += len(pairs)
        relation_by_block[block] = relation
        covered.update(indices)
    require(set(relation_by_block) == set(range(len(locals_))), "observer relation omits a block")
    require(covered == set(range(observer_count)), "observer relations do not cover every source observer")
    require(relation_pair_count == transport["observer_relation_pair_count"], "observer relation census differs")

    assemblies = array(transport["terminal_assemblies"], "terminal assemblies")
    require(assemblies, "terminal assembly is empty")
    require(len(assemblies) == transport["certificate_terminal_tuple_count"] == transport["terminal_observer_fiber_count"], "terminal assembly census differs")
    assembly_indices: set[int] = set()
    observed_goal_tuples: set[tuple[str, ...]] = set()
    for offset, raw in enumerate(assemblies):
        assembly = object_(raw, f"terminal assembly[{offset}]")
        exact_keys(assembly, {"terminal_tuple_index", "observer_fiber_index", "local_goal_signature_ids", "global_observer_states", "endpoint_id", "controller_state"}, f"terminal assembly[{offset}]")
        terminal_index = exact_int(assembly["terminal_tuple_index"], "terminal tuple index")
        require(terminal_index not in assembly_indices, "duplicate terminal tuple index")
        assembly_indices.add(terminal_index)
        require(exact_int(assembly["observer_fiber_index"], "observer fiber index") == 0, "terminal fibre is not the canonical singleton")
        goal_ids = string_list(assembly["local_goal_signature_ids"], "local goal signature ids")
        require(len(goal_ids) == len(locals_), "terminal tuple arity differs")
        require(tuple(goal_ids) not in observed_goal_tuples, "duplicate terminal Goal tuple")
        observed_goal_tuples.add(tuple(goal_ids))
        global_observers = int_list(assembly["global_observer_states"], "global observer states")
        require(len(global_observers) == observer_count, "terminal global observer arity differs")

        raw_components: list[int | None] = [None] * component_count
        tester_union: dict[str, int] = {}
        assigned_observers: dict[int, int] = {}
        for block, goal_id in enumerate(goal_ids):
            goal = locals_[block]["goal_by_id"].get(goal_id)
            require(goal is not None, "terminal assembly names an unknown local Goal")
            physical = goal["physical"]
            require(len(physical) == len(partition[block]), "terminal local physical arity differs")
            local_observers = physical[0]["observer_states"] if physical else []
            relation = relation_by_block[block]
            fibres = {
                tuple(pair["global"])
                for pair in relation["pairs"]
                if pair["local"] == local_observers
            }
            require(len(fibres) == 1, "terminal observer fibre is not singleton")
            fibre = next(iter(fibres))
            for index, value_ in zip(relation["global_observer_indices"], fibre):
                require(index not in assigned_observers or assigned_observers[index] == value_, "terminal observer fibres disagree")
                assigned_observers[index] = value_
                require(global_observers[index] == value_, "terminal assembly observer vector differs from relation")
            for component_offset, global_index in enumerate(partition[block]):
                component = physical[component_offset]
                require(component["version"] == "NEW", "terminal refinement contains an OLD component")
                raw_components[global_index] = component["raw_state"]
            for tester, residual in goal["new_requirement_states"].items():
                require(tester not in tester_union, "new tester belongs to multiple blocks")
                tester_union[tester] = residual
        require(all(value_ is not None for value_ in raw_components), "terminal assembly omits a component")
        selector_key = canonical([[int(value_) for value_ in raw_components], global_observers, tester_union])
        selector = selector_by_key.get(selector_key)
        require(selector is not None, "terminal assembly is outside the full load selector")
        require(selector["endpoint_id"] == assembly["endpoint_id"] and selector["controller_state"] == assembly["controller_state"], "terminal assembly chooses the wrong kappa endpoint")
    require(assembly_indices == set(range(len(assemblies))), "terminal tuple indices are not canonical")
    expected_goal_tuples = set(itertools.product(*(sorted(local["goal_by_id"]) for local in locals_)))
    require(observed_goal_tuples == expected_goal_tuples, "terminal assemblies do not cover the local Goal Cartesian product")
    return {"selector_count": len(selectors), "relation_pair_count": relation_pair_count, "assembly_count": len(assemblies)}


def check(bundle: Mapping[str, Any]) -> dict[str, Any]:
    root = object_(bundle, "bundle")
    exact_keys(root, {
        "schema_version", "source_name", "source_sha256", "definition",
        "extraction_status", "claim_scope", "strategy_model", "goal_policy",
        "factorization_stage", "fixed_endpoint_products_materialized",
        "factor_status", "solve_status", "global_mixed_game_materialized",
        "global_mixed_state_count", "global_mixed_post_query_count",
        "old_endpoint_state_count", "new_endpoint_state_count",
        "terminal_product_verified", "arbiter", "transport", "component_partition",
        "dependency_receipts", "locals", "local_solver_discovered_states_sum",
        "local_solver_successor_queries_sum", "local_solver_outcomes_sum",
    }, "bundle")
    require(root["schema_version"] == SCHEMA, "native bundle schema differs")
    text(root["source_name"], "source name")
    source_sha = text(root["source_sha256"], "source SHA-256")
    require(len(source_sha) == 64 and all(ch in "0123456789abcdef" for ch in source_sha), "source SHA-256 is invalid")
    text(root["definition"], "definition")
    require(root["extraction_status"] == "COMPLETE_CONSERVATIVE", "extraction status differs")
    require(root["claim_scope"] == "one_way_sufficient_win_only", "claim scope differs")
    require(root["strategy_model"] == "finite_memory_local_product", "strategy model differs")
    require(root["goal_policy"] == "check_original_goal_and_load_before_priority_arbiter", "Goal-first policy is absent")
    require(root["factorization_stage"] == "source_native_before_global_mixed_version_update_game", "factorization stage differs")
    require(exact_bool(root["fixed_endpoint_products_materialized"], "fixed endpoint products"), "fixed endpoint materialization is not disclosed")
    require(not exact_bool(root["global_mixed_game_materialized"], "global mixed materialization"), "global mixed game was materialized")
    require(exact_int(root["global_mixed_state_count"], "global mixed states") == 0 and exact_int(root["global_mixed_post_query_count"], "global mixed queries") == 0, "global mixed-game counters are nonzero")
    exact_int(root["old_endpoint_state_count"], "old endpoint states", 1)
    new_endpoint_state_count = exact_int(root["new_endpoint_state_count"], "new endpoint states", 1)
    terminal_verified = exact_bool(root["terminal_product_verified"], "terminal product verified")

    selectors_raw = object_(root["transport"], "transport").get("load_selectors", [])
    component_count = 0
    if selectors_raw:
        first_selector = object_(array(selectors_raw, "load selectors")[0], "first load selector")
        component_count = len(array(first_selector.get("component_raw_states"), "first selector components"))
    partition_raw = array(root["component_partition"], "component partition")
    partition = [int_list(block, f"partition[{index}]", unique=True) for index, block in enumerate(partition_raw)]
    require(partition and all(block and block == sorted(block) for block in partition), "component partition is not canonical")
    if component_count == 0:
        component_count = max((max(block) for block in partition), default=-1) + 1
    require(sorted(value for block in partition for value in block) == list(range(component_count)), "component partition is not total/disjoint")
    require(partition == sorted(partition, key=lambda block: block[0]), "component partition block order differs")

    dependencies = array(root["dependency_receipts"], "dependency receipts")
    seen_receipts: set[str] = set()
    union = UnionFind(component_count)
    for offset, raw in enumerate(dependencies):
        receipt = object_(raw, f"dependency receipt[{offset}]")
        exact_keys(receipt, {"kind", "declaration", "components"}, f"dependency receipt[{offset}]")
        text(receipt["kind"], "dependency kind")
        require(receipt["kind"] in {"ordinary-action", "update-action", "tester", "activation", "precedence"}, "dependency kind is unknown")
        text(receipt["declaration"], "dependency declaration")
        support = int_list(receipt["components"], "dependency support", unique=True)
        require(support and support == sorted(support) and all(value < component_count for value in support), "dependency support is invalid")
        signature = canonical(receipt)
        require(signature not in seen_receipts, "duplicate dependency receipt")
        seen_receipts.add(signature)
        for value in support[1:]:
            union.join(support[0], value)
    require(union.blocks() == partition, "dependency closure differs from component partition")

    arbiter = object_(root["arbiter"], "arbiter")
    exact_keys(arbiter, {"block_order", "original_goal_preempts_local_progress", "uncontrollable_mode", "shared_controllable_pure_stutter"}, "arbiter")
    require(int_list(arbiter["block_order"], "arbiter block order", unique=True) == list(range(len(partition))), "arbiter priority differs")
    require(exact_bool(arbiter["original_goal_preempts_local_progress"], "Goal preemption"), "arbiter omits Goal-first stop")
    require(arbiter["uncontrollable_mode"] == "allow_all_then_wait" and arbiter["shared_controllable_pure_stutter"] == "disabled", "arbiter semantics differ")

    factor_status = root["factor_status"]
    solve_status = root["solve_status"]
    locals_raw = array(root["locals"], "locals")
    if factor_status == "TRIVIAL_ONE_BLOCK":
        require(len(partition) == 1 and solve_status == "NOT_RUN" and not locals_raw and not terminal_verified, "trivial result fields differ")
        transport = object_(root["transport"], "transport")
        exact_keys(transport, TRANSPORT_KEYS, "transport")
        require(transport.get("verified") is False, "trivial result has verified transport")
        for field in (
            "activation_tester_count", "activation_relation_pair_count",
            "observer_relation_pair_count", "load_selector_signature_count",
            "load_selector_endpoint_count", "certificate_terminal_tuple_count",
            "terminal_observer_fiber_count",
        ):
            require(exact_int(transport[field], f"trivial transport {field}") == 0, f"trivial result has nonzero {field}")
        for field in ("observer_relations", "load_selectors", "terminal_assemblies"):
            require(transport.get(field) == [], f"trivial result retains {field}")
        for field in (
            "local_solver_discovered_states_sum", "local_solver_successor_queries_sum",
            "local_solver_outcomes_sum",
        ):
            require(exact_int(root[field], field) == 0, f"trivial result has nonzero {field}")
        return {"factor_status": factor_status, "solve_status": solve_status, "block_count": 1, "local_proofs": 0}

    require(factor_status == "NONTRIVIAL_SOURCE_NATIVE", "unknown factor status")
    require(solve_status == "PRODUCER_VERIFIED_REFINED_WIN", "producer did not establish refined WIN")
    require(len(partition) >= 2 and len(locals_raw) == len(partition) and terminal_verified, "nontrivial refined-WIN shape differs")
    local_checks = [check_local(local, index, partition[index]) for index, local in enumerate(locals_raw)]
    receipts_by_block: list[dict[str, set[str]]] = [defaultdict(set) for _ in partition]
    receipt_owner: dict[tuple[str, str], int] = {}
    for receipt in dependencies:
        support = receipt["components"]
        owners = [index for index, block in enumerate(partition) if set(support) <= set(block)]
        require(len(owners) == 1, "dependency receipt is not owned by exactly one selected block")
        owner = owners[0]
        declaration_key = (receipt["kind"], receipt["declaration"])
        require(
            declaration_key not in receipt_owner or receipt_owner[declaration_key] == owner,
            "one dependency declaration is assigned to multiple selected blocks",
        )
        receipt_owner[declaration_key] = owner
        receipts_by_block[owner][receipt["kind"]].add(receipt["declaration"])
    for index, local in enumerate(local_checks):
        require(receipts_by_block[index]["ordinary-action"] == local["ordinary_actions"], "ordinary-action receipts differ from the serialized local action table")
        require(receipts_by_block[index]["update-action"] == local["update_actions"], "update-action receipts differ from the serialized local action table")
        require(receipts_by_block[index]["tester"] == local["tester_sources"], "tester receipts differ from the serialized local tester domain")
        require(receipts_by_block[index]["activation"] == local["goal_new_sources"], "activation receipts differ from the serialized local Goal tester domain")
    seen_actions: set[str] = set()
    seen_testers: set[str] = set()
    seen_goal_testers: set[str] = set()
    for local in local_checks:
        action_domain = local["ordinary_actions"] | local["update_actions"]
        require(not (seen_actions & action_domain), "a nonstuttering action belongs to multiple selected blocks")
        require(not (seen_testers & local["tester_sources"]), "a tester source belongs to multiple selected blocks")
        require(not (seen_goal_testers & local["goal_new_sources"]), "an activation tester belongs to multiple selected blocks")
        seen_actions.update(action_domain)
        seen_testers.update(local["tester_sources"])
        seen_goal_testers.update(local["goal_new_sources"])
    transport_check = check_transport(
        root["transport"], local_checks, partition, component_count, new_endpoint_state_count
    )
    for field, stat in (
        ("local_solver_discovered_states_sum", "solver_discovered_states"),
        ("local_solver_successor_queries_sum", "solver_successor_queries"),
        ("local_solver_outcomes_sum", "solver_outcomes"),
    ):
        expected = sum(exact_int(object_(local, "local")[stat], stat) for local in locals_raw)
        require(exact_int(root[field], field) == expected, f"{field} differs")
    return {
        "factor_status": factor_status,
        "solve_status": "STRUCTURALLY_CHECKED_PRODUCER_WITNESS",
        "verification_scope": "serialized_internal_consistency_only_source_replay_required",
        "block_count": len(partition),
        "local_proofs": len(local_checks),
        "rank_states": sum(len(local["states"]) for local in local_checks),
        **transport_check,
    }


def load(path: Path) -> dict[str, Any]:
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
        raise BundleError(f"cannot load strict JSON: {path}") from error
    return object_(value, "bundle")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    try:
        report = check(load(args.bundle))
        if args.report is not None:
            args.report.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0
    except BundleError as error:
        print(f"NATIVE_BUNDLE_INVALID={error}", file=__import__("sys").stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
