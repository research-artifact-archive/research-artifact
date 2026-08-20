#!/usr/bin/env python3
"""Independent consumer for explicit factored FG-DUCS certificates.

The consumer reconstructs and hashes the typed input, validates monitor and RS
projections, local precedence and handover typing, recomputes every local
attractor, and checks the global rank-sum or losing-cylinder certificate.  For
bounded products, ``check_flat_equivalence`` independently enumerates the flat
game and compares its winning region and rank with the succinct witness.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import re
from collections import defaultdict
from math import prod
from typing import Any, Mapping, Sequence


GAME_SCHEMA_VERSION = "fg-ducs-factored-game-v1"
CERTIFICATE_SCHEMA_VERSION = "fg-ducs-factored-certificate-v1"


class FactorCertificateError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise FactorCertificateError(message)


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def string_list(value: Any, label: str, *, nonempty: bool = True) -> list[str]:
    require(isinstance(value, list), f"{label} must be a list")
    require(all(isinstance(item, str) and item for item in value), f"{label} has an invalid item")
    require(len(value) == len(set(value)), f"{label} has duplicates")
    require(not nonempty or bool(value), f"{label} must be nonempty")
    return list(value)


def exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    require(set(value) == expected, f"{label} fields differ: {sorted(set(value) ^ expected)}")


def automaton_projection(
    block_id: str,
    name: str,
    automaton: Any,
    annotation_field: str,
    state_annotations: Mapping[str, Any],
    transitions: Sequence[Mapping[str, Any]],
    initials: set[str],
) -> tuple[set[str], dict[tuple[str, str], str]]:
    require(isinstance(automaton, dict), f"{block_id}.{name} is invalid")
    expected = {"states", "initial_states", "error_states", "default", "transitions"}
    exact_keys(automaton, expected, f"{block_id}.{name}")
    states = set(string_list(automaton.get("states"), f"{block_id}.{name}.states"))
    auto_initials = set(string_list(automaton.get("initial_states"), f"{block_id}.{name}.initial_states"))
    errors = set(string_list(automaton.get("error_states"), f"{block_id}.{name}.error_states", nonempty=False))
    require(auto_initials <= states and errors <= states, f"{block_id}.{name} state typing differs")
    require(automaton.get("default") == "stutter", f"{block_id}.{name} default is not stutter")
    delta: dict[tuple[str, str], str] = {}
    raw_delta = automaton.get("transitions")
    require(isinstance(raw_delta, list), f"{block_id}.{name}.transitions is invalid")
    for record in raw_delta:
        require(isinstance(record, dict), f"{block_id}.{name} transition is invalid")
        exact_keys(record, {"source", "action", "target"}, f"{block_id}.{name} transition")
        key = (record.get("source"), record.get("action"))
        require(key[0] in states and isinstance(key[1], str) and key[1], f"{block_id}.{name} transition typing differs")
        require(record.get("target") in states and key not in delta, f"{block_id}.{name} transition differs")
        delta[(str(key[0]), str(key[1]))] = str(record["target"])
    for (source, _action), target in delta.items():
        if source in errors:
            require(target in errors, f"{block_id}.{name} error state is not absorbing")
    for state in initials:
        require(state_annotations[state][annotation_field] in auto_initials, f"{block_id}.{name} initial projection differs")
    for record in transitions:
        source_projection = state_annotations[str(record["source"])][annotation_field]
        expected_target = delta.get((source_projection, str(record["action"])), source_projection)
        for target in record["targets"]:
            require(state_annotations[target][annotation_field] == expected_target, f"{block_id}.{name} projection differs")
    return errors, delta


def check_block(block: Mapping[str, Any]) -> dict[str, Any]:
    input_fields = {
        "id", "states", "state_annotations", "initial_states", "safe_states", "goal_states",
        "load_states", "action_annotations", "transitions", "monitor", "rs_observer",
        "precedence_edges", "handover_relation", "foreign_actions_stutter",
    }
    certificate_fields = {
        "rank", "policy", "kappa", "losing_region", "losing_counterstrategy"
    }
    exact_keys(block, input_fields | certificate_fields, "block")
    identifier = block.get("id")
    require(isinstance(identifier, str) and identifier, "block id is invalid")
    states = set(string_list(block.get("states"), f"{identifier}.states"))
    initials = set(string_list(block.get("initial_states"), f"{identifier}.initial_states"))
    safe = set(string_list(block.get("safe_states"), f"{identifier}.safe_states"))
    goals = set(string_list(block.get("goal_states"), f"{identifier}.goal_states"))
    loads = set(string_list(block.get("load_states"), f"{identifier}.load_states"))
    require(initials <= states and safe <= states and goals <= safe, f"{identifier} state typing differs")
    require(block.get("foreign_actions_stutter") is True, f"{identifier} foreign actions do not stutter")

    state_annotations = block.get("state_annotations")
    require(isinstance(state_annotations, dict) and set(state_annotations) == states, f"{identifier} state annotation domain differs")
    for state, record in state_annotations.items():
        require(isinstance(record, dict), f"{identifier}.{state} annotation is invalid")
        exact_keys(record, {"physical", "physical_safe", "monitor", "rs_residual", "pending_actions"}, f"{identifier}.{state} annotation")
        require(isinstance(record.get("physical"), str) and record["physical"], f"{identifier}.{state} physical state is invalid")
        require(isinstance(record.get("physical_safe"), bool), f"{identifier}.{state} physical safety is invalid")
        require(isinstance(record.get("monitor"), str) and record["monitor"], f"{identifier}.{state} monitor state is invalid")
        require(isinstance(record.get("rs_residual"), str) and record["rs_residual"], f"{identifier}.{state} RS residual is invalid")

    action_annotations = block.get("action_annotations")
    require(isinstance(action_annotations, dict), f"{identifier} action annotations are invalid")
    controllable: set[str] = set()
    uncontrollable: set[str] = set()
    for action, record in action_annotations.items():
        require(isinstance(action, str) and action and isinstance(record, dict), f"{identifier} action annotation is invalid")
        exact_keys(record, {"controllability", "kind"}, f"{identifier}.{action} action annotation")
        require(record.get("kind") in {"transfer", "monitor", "handover", "internal"}, f"{identifier}.{action} kind differs")
        partition = record.get("controllability")
        require(partition in {"controllable", "uncontrollable"}, f"{identifier}.{action} controllability differs")
        (controllable if partition == "controllable" else uncontrollable).add(action)
    actions = controllable | uncontrollable
    update_actions = {
        action for action, record in action_annotations.items()
        if record["kind"] != "internal"
    }
    require(update_actions <= controllable, f"{identifier} has an uncontrollable update action")
    for state, record in state_annotations.items():
        pending = set(string_list(record.get("pending_actions"), f"{identifier}.{state}.pending_actions", nonempty=False))
        require(pending <= update_actions, f"{identifier}.{state} pending action is not an update action")
    for state in initials:
        require(
            set(state_annotations[state]["pending_actions"]) == update_actions,
            f"{identifier}.{state} initial pending actions do not equal all update actions",
        )

    transitions_raw = block.get("transitions")
    require(isinstance(transitions_raw, list), f"{identifier}.transitions must be a list")
    transitions: list[Mapping[str, Any]] = []
    post: dict[tuple[str, str], tuple[str, ...]] = {}
    for record in transitions_raw:
        require(isinstance(record, dict), f"{identifier} transition is not an object")
        exact_keys(record, {"source", "action", "targets"}, f"{identifier} transition")
        source, action = record.get("source"), record.get("action")
        targets = string_list(record.get("targets"), f"{identifier} transition targets")
        require(source in states and action in actions and set(targets) <= states, f"{identifier} transition typing differs")
        key = (str(source), str(action))
        require(key not in post, f"{identifier} has a duplicate action bucket")
        post[key] = tuple(targets)
        transitions.append(record)

    precedence_raw = block.get("precedence_edges")
    require(isinstance(precedence_raw, list), f"{identifier}.precedence_edges is invalid")
    predecessors: dict[str, set[str]] = defaultdict(set)
    graph: dict[str, set[str]] = defaultdict(set)
    for edge in precedence_raw:
        require(isinstance(edge, list) and len(edge) == 2 and all(item in update_actions for item in edge), f"{identifier} precedence edge is not between update actions")
        before, after = edge
        require(before != after and after not in graph[before], f"{identifier} precedence edge is invalid")
        graph[before].add(after)
        predecessors[after].add(before)
    visiting: set[str] = set()
    visited: set[str] = set()
    def visit(action: str) -> None:
        require(action not in visiting, f"{identifier} precedence is cyclic")
        if action in visited:
            return
        visiting.add(action)
        for successor in graph[action]:
            visit(successor)
        visiting.remove(action)
        visited.add(action)
    for action in actions:
        visit(action)
    for (source, action), targets in post.items():
        pending_source = set(state_annotations[source]["pending_actions"])
        is_update = action_annotations[action]["kind"] != "internal"
        if is_update:
            require(action in pending_source, f"{identifier} enables a non-pending update action")
        require(not (predecessors[action] & pending_source), f"{identifier} enables an order-blocked action")
        for target in targets:
            pending_target = set(state_annotations[target]["pending_actions"])
            expected_pending = pending_source - {action} if is_update else pending_source
            require(pending_target == expected_pending, f"{identifier} pending-action projection is not exact")
    require(all(not state_annotations[goal]["pending_actions"] for goal in goals), f"{identifier} Goal has pending actions")

    monitor_errors, monitor_delta = automaton_projection(identifier, "monitor", block.get("monitor"), "monitor", state_annotations, transitions, initials)
    _rs_errors, rs_delta = automaton_projection(identifier, "rs_observer", block.get("rs_observer"), "rs_residual", state_annotations, transitions, initials)
    expected_safe = {
        state for state in states
        if state_annotations[state]["physical_safe"] and state_annotations[state]["monitor"] not in monitor_errors
    }
    require(safe == expected_safe, f"{identifier} Safe does not equal physical-safe and monitor-safe states")

    handover = block.get("handover_relation")
    require(isinstance(handover, dict) and set(handover) == goals, f"{identifier} handover relation domain differs")
    for goal, candidates in handover.items():
        values = string_list(candidates, f"{identifier}.handover_relation.{goal}")
        require(set(values) <= loads, f"{identifier} handover target is not loadable")

    enabled_c: dict[str, list[str]] = defaultdict(list)
    enabled_uc: dict[str, list[str]] = defaultdict(list)
    for state, action in post:
        (enabled_c if action in controllable else enabled_uc)[state].append(action)
    for goal in goals:
        require(not enabled_uc[goal], f"{identifier} Goal is not uncontrollable-quiescent")

    winning = set(goals)
    ranks = {state: 0 for state in goals}
    layer = 0
    while True:
        layer += 1
        added: set[str] = set()
        for state in safe - winning:
            if enabled_uc[state]:
                condition = all(all(target in winning for target in post[(state, action)]) for action in enabled_uc[state])
            else:
                condition = any(all(target in winning for target in post[(state, action)]) for action in enabled_c[state])
            if condition:
                added.add(state)
        if not added:
            break
        for state in added:
            ranks[state] = layer
        winning |= added

    losing = states - winning
    provided_rank = block.get("rank")
    require(isinstance(provided_rank, dict) and set(provided_rank) == winning, f"{identifier} rank domain differs")
    require(all(type(provided_rank[state]) is int and provided_rank[state] == ranks[state] for state in winning), f"{identifier} rank differs")
    policy = block.get("policy")
    require(isinstance(policy, dict), f"{identifier} policy is invalid")
    expected_policy_domain = {state for state in winning - goals if not enabled_uc[state]}
    require(set(policy) == expected_policy_domain, f"{identifier} policy domain differs")
    for state in winning - goals:
        if enabled_uc[state]:
            require(all(all(target in winning and ranks[target] < ranks[state] for target in post[(state, action)]) for action in enabled_uc[state]), f"{identifier} uncontrollable rank progress differs")
        else:
            action = policy[state]
            require(action in enabled_c[state], f"{identifier} policy selects a disabled action")
            require(all(target in winning and ranks[target] < ranks[state] for target in post[(state, action)]), f"{identifier} policy does not decrease rank")

    kappa = block.get("kappa")
    require(isinstance(kappa, dict) and set(kappa) == goals, f"{identifier} kappa domain differs")
    require(all(kappa[goal] in handover[goal] for goal in goals), f"{identifier} kappa is outside the handover relation")
    provided_losing = set(string_list(block.get("losing_region"), f"{identifier}.losing_region", nonempty=False))
    require(provided_losing == losing, f"{identifier} losing region differs")
    counterstrategy = block.get("losing_counterstrategy")
    require(isinstance(counterstrategy, dict) and set(counterstrategy) == losing, f"{identifier} losing counterstrategy domain differs")
    for state in (losing & safe) - goals:
        response = counterstrategy[state]
        require(isinstance(response, dict), f"{identifier} losing response is invalid")
        if enabled_uc[state]:
            require(any(any(target in losing for target in post[(state, action)]) for action in enabled_uc[state]), f"{identifier} losing uncontrollable witness is missing")
            exact_keys(response, {"mode", "action", "target"}, f"{identifier} uncontrollable losing response")
            require(
                response.get("mode") == "uncontrollable"
                and response.get("action") in enabled_uc[state]
                and response.get("target") in post[(state, response["action"])]
                and response.get("target") in losing,
                f"{identifier} uncontrollable losing response differs",
            )
        else:
            require(all(any(target in losing for target in post[(state, action)]) for action in enabled_c[state]), f"{identifier} losing controllable closure differs")
            exact_keys(response, {"mode", "responses"}, f"{identifier} controlled losing response")
            responses = response.get("responses")
            require(
                response.get("mode") == "controlled-outcomes"
                and isinstance(responses, dict)
                and set(responses) == set(enabled_c[state]),
                f"{identifier} controlled losing response domain differs",
            )
            require(
                all(responses[action] in post[(state, action)] and responses[action] in losing for action in responses),
                f"{identifier} controlled losing response differs",
            )
    for state in losing - safe:
        require(counterstrategy[state] == {"mode": "unsafe-terminal"}, f"{identifier} unsafe losing response differs")
    return {
        "id": identifier,
        "states": sorted(states),
        "initial_states": sorted(initials),
        "safe_states": sorted(safe),
        "goal_states": sorted(goals),
        "winning_states": sorted(winning),
        "ranks": ranks,
        "state_count": len(states),
        "bucket_count": len(post),
        "outcome_edge_count": sum(len(targets) for targets in post.values()),
        "all_initials_winning": initials <= winning,
        "max_initial_rank": max((ranks[state] for state in initials if state in ranks), default=0),
        "losing_region": sorted(losing),
        "controllable_actions": sorted(controllable),
        "uncontrollable_actions": sorted(uncontrollable),
        "post": post,
        "monitor_delta": monitor_delta,
        "rs_delta": rs_delta,
    }


def reconstruct_game(raw: Mapping[str, Any]) -> dict[str, Any]:
    input_fields = {
        "id", "states", "state_annotations", "initial_states", "safe_states", "goal_states",
        "load_states", "action_annotations", "transitions", "monitor", "rs_observer",
        "precedence_edges", "handover_relation", "foreign_actions_stutter",
    }
    blocks = [{key: block[key] for key in input_fields} for block in raw["blocks"]]
    return {
        "schema_version": GAME_SCHEMA_VERSION,
        "id": raw["id"],
        "source_model": raw["source_model"],
        "shared_controllable_pure_stutter": raw["shared_controllable_pure_stutter"],
        "cross_block_precedence": raw["cross_block_precedence"],
        "cross_block_requirements": raw["cross_block_requirements"],
        "composition": raw["composition"],
        "blocks": blocks,
    }


def check_certificate(raw: Mapping[str, Any]) -> dict[str, Any]:
    exact_keys(raw, {"schema_version", "input_game_sha256", "id", "source_model", "shared_controllable_pure_stutter", "cross_block_precedence", "cross_block_requirements", "composition", "blocks", "global_certificate"}, "certificate")
    require(raw.get("schema_version") == CERTIFICATE_SCHEMA_VERSION, "unknown factored-certificate schema")
    identifier = raw.get("id")
    require(isinstance(identifier, str) and identifier, "certificate id is invalid")
    source = raw.get("source_model")
    require(isinstance(source, dict), "source_model is invalid")
    exact_keys(source, {"id", "sha256", "kind"}, "source_model")
    require(isinstance(source.get("id"), str) and isinstance(source.get("kind"), str) and re.fullmatch(r"[0-9a-f]{64}", str(source.get("sha256"))) is not None, "source_model fields differ")
    require(re.fullmatch(r"[0-9a-f]{64}", str(raw.get("input_game_sha256"))) is not None, "input game hash is invalid")
    require(sha256_json(reconstruct_game(raw)) == raw.get("input_game_sha256"), "input game hash differs")
    shared = set(string_list(raw.get("shared_controllable_pure_stutter"), "shared_controllable_pure_stutter", nonempty=False))
    require(raw.get("cross_block_precedence") == [], "cross-block precedence is not empty")
    require(raw.get("cross_block_requirements") == [], "cross-block requirements are not empty")
    expected_composition = {
        "state_space": "cartesian_product", "initial_states": "cartesian_product", "safe": "conjunction",
        "goal": "cartesian_product", "load_states": "cartesian_product", "handover": "cartesian_product",
        "post": "exact_asynchronous_one_block_frame", "foreign_monitor_actions": "stutter",
        "foreign_rs_actions": "stutter", "pending_and_precedence": "block_local",
        "shared_action_post": "global_self_loop",
    }
    require(raw.get("composition") == expected_composition, "composition semantics differ")
    blocks_raw = raw.get("blocks")
    require(isinstance(blocks_raw, list) and blocks_raw, "blocks must be nonempty")
    results: list[dict[str, Any]] = []
    block_ids: set[str] = set()
    local_actions: set[str] = set()
    for block in blocks_raw:
        require(isinstance(block, dict), "block is invalid")
        result = check_block(block)
        require(result["id"] not in block_ids, "block id is duplicated")
        block_ids.add(result["id"])
        actions = set(result["controllable_actions"]) | set(result["uncontrollable_actions"])
        require(local_actions.isdisjoint(actions), "block-changing action alphabets overlap")
        local_actions |= actions
        results.append(result)
    require(local_actions.isdisjoint(shared), "shared pure-stutter action overlaps a block action")
    global_actions = local_actions | shared
    for result in results:
        owned = set(result["controllable_actions"]) | set(result["uncontrollable_actions"])
        foreign = (local_actions - owned) | shared
        for label in ("monitor_delta", "rs_delta"):
            for (source, action), target in result[label].items():
                require(action in global_actions, f"{result['id']} {label} uses an unknown action")
                if action in foreign:
                    require(target == source, f"{result['id']} {label} changes on a foreign action")

    all_winning = all(result["all_initials_winning"] for result in results)
    global_certificate = raw.get("global_certificate")
    require(isinstance(global_certificate, dict), "global certificate is invalid")
    counts = {
        "semantic_flat_state_count": prod(result["state_count"] for result in results),
        "factored_local_state_count": sum(result["state_count"] for result in results),
        "factored_bucket_count": sum(result["bucket_count"] for result in results),
        "factored_outcome_edge_count": sum(result["outcome_edge_count"] for result in results),
    }
    if all_winning:
        exact_keys(global_certificate, {"decision", "priority", "shared_stutter_enabled", "rank_operator", "kappa_operator", "semantic_flat_state_count", "factored_local_state_count", "factored_bucket_count", "factored_outcome_edge_count", "maximum_initial_rank"}, "winning global certificate")
        require(global_certificate.get("decision") == "realizable", "global decision differs")
        require(global_certificate.get("priority") == [result["id"] for result in results], "priority differs")
        require(global_certificate.get("shared_stutter_enabled") is False, "shared pure stutter is enabled")
        require(global_certificate.get("rank_operator") == "sum" and global_certificate.get("kappa_operator") == "cartesian_product", "global witness operators differ")
        require(global_certificate.get("maximum_initial_rank") == sum(result["max_initial_rank"] for result in results), "global initial rank differs")
    else:
        exact_keys(global_certificate, {"decision", "losing_block_id", "cylinder_local_losing_region", "semantic_flat_state_count", "factored_local_state_count", "factored_bucket_count", "factored_outcome_edge_count"}, "losing global certificate")
        require(global_certificate.get("decision") == "unrealizable", "global decision differs")
        losing = next((result for result in results if result["id"] == global_certificate.get("losing_block_id")), None)
        require(losing is not None and not losing["all_initials_winning"], "losing block witness differs")
        require(global_certificate.get("cylinder_local_losing_region") == losing["losing_region"], "losing cylinder differs")
    require(
        all(type(global_certificate.get(key)) is int and global_certificate.get(key) == value for key, value in counts.items()),
        "global/factored size census differs",
    )
    return {"id": identifier, "decision": "realizable" if all_winning else "unrealizable", "block_count": len(results), **counts, "maximum_initial_rank": sum(result["max_initial_rank"] for result in results), "local_losing_states": sum(len(result["losing_region"]) for result in results), "status": "PASS", "_blocks": results}


def check_priority_execution(raw: Mapping[str, Any], *, maximum_traces: int = 100_000) -> dict[str, Any]:
    """Execute the certified priority arbiter over every adversarial outcome."""
    checked = check_certificate(raw)
    require(checked["decision"] == "realizable", "priority execution requires a winning certificate")
    results = checked["_blocks"]
    blocks_raw = raw["blocks"]
    priority = raw["global_certificate"]["priority"]
    require(priority == [block["id"] for block in blocks_raw], "execution priority differs")
    initials = list(itertools.product(*(result["initial_states"] for result in results)))
    traces: list[dict[str, Any]] = []
    reached: set[tuple[str, ...]] = set()

    def rank_sum(state: tuple[str, ...]) -> int:
        return sum(int(blocks_raw[index]["rank"][local]) for index, local in enumerate(state))

    def explore(state: tuple[str, ...], steps: list[dict[str, Any]]) -> None:
        require(len(traces) < maximum_traces, "priority trace bound exceeded")
        reached.add(state)
        if all(state[index] in results[index]["goal_states"] for index in range(len(results))):
            traces.append(
                {
                    "actions": [step["action"] for step in steps],
                    "outcomes": [step["target"] for step in steps],
                    "load_tuple": [blocks_raw[index]["kappa"][local] for index, local in enumerate(state)],
                }
            )
            return
        choices: list[tuple[int, str, tuple[str, ...]]] = []
        for index, result in enumerate(results):
            for (source, action), targets in result["post"].items():
                if source == state[index] and action in result["uncontrollable_actions"]:
                    choices.append((index, action, targets))
        if not choices:
            index = next(
                j for j, result in enumerate(results)
                if state[j] not in result["goal_states"]
            )
            action = blocks_raw[index]["policy"][state[index]]
            targets = results[index]["post"][(state[index], action)]
            choices.append((index, action, targets))
        source_rank = rank_sum(state)
        for index, action, targets in choices:
            for target in targets:
                successor = state[:index] + (target,) + state[index + 1:]
                require(rank_sum(successor) < source_rank, "priority execution does not decrease rank sum")
                explore(
                    successor,
                    steps + [{"block": results[index]["id"], "action": action, "target": list(successor)}],
                )

    for initial in initials:
        explore(initial, [])
    require(traces and all(trace["load_tuple"] for trace in traces), "priority execution has no typed terminal trace")
    lengths = [len(trace["actions"]) for trace in traces]
    return {
        "id": raw["id"],
        "initial_tuple_count": len(initials),
        "reached_tuple_count": len(reached),
        "complete_outcome_trace_count": len(traces),
        "minimum_trace_length": min(lengths),
        "maximum_trace_length": max(lengths),
        "traces": traces,
        "status": "PASS",
    }


def check_flat_equivalence(raw: Mapping[str, Any], *, maximum_states: int = 100_000) -> dict[str, Any]:
    checked = check_certificate(raw)
    blocks = checked["_blocks"]
    state_count = prod(block["state_count"] for block in blocks)
    require(state_count <= maximum_states, "flat product exceeds the audit bound")
    tuples = list(itertools.product(*(block["states"] for block in blocks)))
    safe = {q for q in tuples if all(q[j] in blocks[j]["safe_states"] for j in range(len(blocks)))}
    goals = {q for q in tuples if all(q[j] in blocks[j]["goal_states"] for j in range(len(blocks)))}
    initials = {q for q in tuples if all(q[j] in blocks[j]["initial_states"] for j in range(len(blocks)))}
    enabled_c: dict[tuple[str, ...], list[tuple[tuple[str, ...], ...]]] = defaultdict(list)
    enabled_uc: dict[tuple[str, ...], list[tuple[tuple[str, ...], ...]]] = defaultdict(list)
    bucket_count = 0
    edge_count = 0
    for q in tuples:
        for j, block in enumerate(blocks):
            for (source, action), targets in block["post"].items():
                if source != q[j]:
                    continue
                successors = tuple(q[:j] + (target,) + q[j + 1:] for target in targets)
                bucket_count += 1
                edge_count += len(successors)
                target = enabled_c if action in block["controllable_actions"] else enabled_uc
                target[q].append(successors)
        for _shared_action in raw["shared_controllable_pure_stutter"]:
            enabled_c[q].append((q,))
            bucket_count += 1
            edge_count += 1
    winning = set(goals)
    ranks = {q: 0 for q in goals}
    layer = 0
    while True:
        layer += 1
        added = set()
        for q in safe - winning:
            if enabled_uc[q]:
                condition = all(all(target in winning for target in bucket) for bucket in enabled_uc[q])
            else:
                condition = any(all(target in winning for target in bucket) for bucket in enabled_c[q])
            if condition:
                added.add(q)
        if not added:
            break
        for q in added:
            ranks[q] = layer
        winning |= added
    expected_winning = set(itertools.product(*(block["winning_states"] for block in blocks)))
    require(winning == expected_winning, "flat winning region differs from the factored product")
    for q in winning:
        require(
            ranks[q] == sum(blocks[index]["ranks"][local] for index, local in enumerate(q)),
            "flat attractor rank differs from the local rank sum",
        )
    decision = initials <= winning
    require(decision == (checked["decision"] == "realizable"), "flat decision differs")
    if decision:
        flat_initial_rank = max(ranks[q] for q in initials)
        require(flat_initial_rank == checked["maximum_initial_rank"], "flat initial rank differs from rank sum")
    else:
        losing_block_id = raw["global_certificate"]["losing_block_id"]
        j = next(index for index, block in enumerate(blocks) if block["id"] == losing_block_id)
        cylinder = {q for q in tuples if q[j] in raw["global_certificate"]["cylinder_local_losing_region"]}
        require(cylinder <= set(tuples) - winning, "losing cylinder is not contained in the flat losing region")
        flat_initial_rank = None
    return {
        "id": raw["id"], "decision": checked["decision"], "state_count": state_count,
        "winning_state_count": len(winning), "maximum_initial_rank": flat_initial_rank,
        "bucket_count": bucket_count, "outcome_edge_count": edge_count, "status": "PASS",
    }
