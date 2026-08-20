#!/usr/bin/env python3
"""Verify a freshly generated post-frontend strong-WIN certificate.

The checker accepts only conclusion-free post-frontend IR and the generated
certificate schema.  It never imports or invokes the certificate generator or
its rank-synthesis core, and it never accepts an M8q/M8s historical bundle.

The conclusion-free IR parser and the established FG-DUCS semantic
constructors are deliberately shared with
``check_post_frontend_contract_certificate``.  The certificate envelope,
rank-domain checks, generated activation rows, and report are implemented
here.  Every certificate claim is compared with semantics reconstructed from
the IR; generator-provided counters are not accepted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import check_post_frontend_contract_certificate as SEM


CERTIFICATE_SCHEMA = "fg-ducs-generated-post-frontend-win-certificate-v1"
REPORT_SCHEMA = "fg-ducs-generated-post-frontend-win-certificate-check-v1"
STATUS = "GENERATED_POST_FRONTEND_WIN_CERTIFICATE_VERIFIED"
MAX_STRONG_RANK = 32
ALGORITHM = "BOUNDED_MINIMUM_STRONG_RANK_PENDING_UPDATE_THEN_LEXICAL_V1"

ROOT_KEYS = {
    "schema_version", "generator_boundary", "ir_binding", "decision",
    "component_partition", "endpoints", "locals", "transport",
}
GENERATOR_BOUNDARY_KEYS = {
    "algorithm", "depth_bound", "historical_bundle_consumed",
    "supplied_certificate_consumed", "outcome_fields_consumed",
}
IR_BINDING_KEYS = {
    "sha256", "size", "source_name", "source_sha256", "definition",
}
ENDPOINT_KEYS = {"count", "semantic_sha256"}
LOCAL_KEYS = {
    "block_index", "components", "root_state_ids", "states",
    "candidate_buckets", "strategy_buckets", "goal_payloads",
    "quiet_goal_keys",
}
STATE_KEYS = {"id", "payload", "rank", "safe", "goal"}
CANDIDATE_KEYS = {
    "source", "action", "controllable", "update", "target_keys",
}
STRATEGY_KEYS = {"source", "action", "target_state_ids"}
GOAL_PAYLOAD_KEYS = {"id", "physical", "new_requirement_states"}
TRANSPORT_KEYS = {
    "activation_relations", "observer_relations", "load_selectors",
    "terminal_assemblies",
}
ACTIVATION_ROW_KEYS = {
    "block_index", "tester_id", "global_observer_indices", "pairs",
}
ACTIVATION_PAIR_KEYS = {
    "global", "local", "global_residual", "local_residual",
}


CheckError = SEM.CheckError
require = SEM.require
exact_int = SEM.exact_int
exact_bool = SEM.exact_bool
text = SEM.text
array = SEM.array
object_ = SEM.object_
exact_keys = SEM.exact_keys
strings = SEM.strings
integers = SEM.integers


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key: " + key)
        result[key] = value
    return result


def load_strict(path: Path, *, canonical: bool) -> tuple[dict[str, Any], bytes]:
    """Load duplicate-free finite JSON and retain the exact bound bytes."""
    try:
        raw = path.read_bytes()
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=lambda token: (_ for _ in ()).throw(
                ValueError(token)),
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise CheckError(f"invalid strict JSON: {path}") from error
    root = object_(value, "JSON root")
    if canonical:
        require(raw == SEM.canonical_bytes(root),
                "certificate is not canonical JSON with one trailing LF")
    return root, raw


def _hex_sha(value: Any, label: str) -> str:
    result = text(value, label)
    require(bool(re.fullmatch(r"[0-9a-f]{64}", result)),
            f"{label} is not a lowercase SHA-256")
    return result


def _optional_residual(value: Any, label: str) -> int | None:
    if value is None:
        return None
    return exact_int(value, label, 0)


def _endpoint_rows(endpoints: Sequence[SEM.Endpoint]) -> list[dict[str, Any]]:
    rows = [{
        "controller_state": endpoint.controller,
        "component_raw_states": [local.raw for local in endpoint.locals],
        "observer_states": list(endpoint.locals[0].observers),
        "tester_states": dict(sorted(endpoint.testers)),
    } for endpoint in endpoints]
    return sorted(rows, key=SEM.canonical_text)


def _endpoint_digest(endpoints: Sequence[SEM.Endpoint]) -> str:
    return SEM.sha256_bytes(SEM.canonical_bytes(_endpoint_rows(endpoints)))


def _verify_endpoint_declaration(
        value: Any, endpoints: Sequence[SEM.Endpoint], label: str) -> None:
    row = object_(value, label)
    exact_keys(row, ENDPOINT_KEYS, label)
    require(exact_int(row["count"], f"{label} count", 1) == len(endpoints),
            f"{label} endpoint census differs")
    require(_hex_sha(row["semantic_sha256"], f"{label} semantic SHA") ==
            _endpoint_digest(endpoints), f"{label} endpoint digest differs")


def _validate_partition(value: Any, component_count: int) -> list[list[int]]:
    raw = array(value, "component partition")
    partition = [integers(block, f"component partition[{offset}]")
                 for offset, block in enumerate(raw)]
    require(bool(partition) and all(partition)
            and partition == sorted(partition, key=lambda block: block[0]),
            "component partition is not canonical")
    require(sorted(index for block in partition for index in block) ==
            list(range(component_count)),
            "component partition is not total and disjoint")
    return partition


def _goal_payload(value: Any, label: str) -> tuple[str, SEM.GoalPayload]:
    row = object_(value, label)
    exact_keys(row, GOAL_PAYLOAD_KEYS, label)
    identifier = text(row["id"], f"{label} id")
    typed = SEM.parse_config_payload({
        "physical": row["physical"],
        "active_testers": row["new_requirement_states"],
        "pending_actions": [],
    }, label + " payload")
    return identifier, (typed.physical, typed.testers)


@dataclass(frozen=True)
class GeneratedLocalCheck:
    counts: Mapping[str, int]
    goal_ids: Mapping[str, SEM.GoalPayload]
    root_states: frozenset[SEM.Config]
    state_ids: Mapping[SEM.Config, str]


def verify_local(
        problem: SEM.BlockProblem, value: Any, expected_index: int,
        *, depth_bound: int = MAX_STRONG_RANK) -> GeneratedLocalCheck:
    """Recompute one retained rank domain and its complete candidate/Post."""
    row = object_(value, f"local[{expected_index}]")
    exact_keys(row, LOCAL_KEYS, f"local[{expected_index}]")
    require(exact_int(row["block_index"], "local block index", 0) ==
            expected_index, "local block index differs")
    require(integers(row["components"], "local components") ==
            list(problem.block), "local component block differs")

    states: dict[str, SEM.Config] = {}
    state_ids: dict[SEM.Config, str] = {}
    ranks: dict[str, int] = {}
    goals: dict[str, SEM.GoalPayload | None] = {}
    previous_identifier: str | None = None
    for offset, raw in enumerate(array(row["states"], "local states")):
        state_row = object_(raw, f"local state[{offset}]")
        exact_keys(state_row, STATE_KEYS, "local state")
        identifier = text(state_row["id"], "local state id")
        require(identifier not in states and
                (previous_identifier is None or identifier > previous_identifier),
                "local state IDs are not sorted and unique")
        previous_identifier = identifier
        state = SEM.parse_config_payload(state_row["payload"],
                                         "local state payload")
        require(state not in state_ids,
                "local rank domain repeats a semantic state")
        require(problem.structurally_valid(state),
                "local rank state is structurally invalid")
        independently_safe = problem.safe(state)
        require(exact_bool(state_row["safe"], "local state Safe") ==
                independently_safe,
                "local state Safe differs from independent semantics")
        require(independently_safe,
                "local rank domain contains an unsafe state")
        independently_goal = problem.goal_payload(state)
        require(exact_bool(state_row["goal"], "local state Goal") ==
                (independently_goal is not None),
                "local state Goal differs from independent quiet Goal")
        rank = exact_int(state_row["rank"], "local state rank", 0)
        require(rank <= depth_bound, "local rank exceeds the depth bound")
        require((independently_goal is not None and rank == 0) or
                (independently_goal is None and rank > 0),
                "rank zero is not equivalent to the independent quiet Goal")
        states[identifier] = state
        state_ids[state] = identifier
        ranks[identifier] = rank
        goals[identifier] = independently_goal

    require(bool(states), "local rank domain is empty")
    semantic_order = sorted(state_ids, key=SEM.config_key)
    expected_ids = {
        state: f"q{offset:08d}" for offset, state in enumerate(semantic_order)
    }
    require(state_ids == expected_ids,
            "local state IDs do not canonically enumerate semantic states")

    roots = strings(row["root_state_ids"], "local root IDs",
                    sorted_unique=True)
    require(set(roots) <= set(states), "a local root leaves the rank domain")
    root_states = frozenset(states[identifier] for identifier in roots)
    require(root_states == problem.roots,
            "local roots differ from all independently projected roots")

    candidates: dict[
        tuple[str, str], tuple[bool, bool, frozenset[SEM.Config]]
    ] = {}
    by_source: dict[str, set[str]] = defaultdict(set)
    previous_candidate: tuple[str, str] | None = None
    candidate_outcomes = 0
    nonempty_candidates = 0
    for offset, raw in enumerate(array(row["candidate_buckets"],
                                       "candidate buckets")):
        bucket = object_(raw, f"candidate[{offset}]")
        exact_keys(bucket, CANDIDATE_KEYS, "candidate bucket")
        source = text(bucket["source"], "candidate source")
        action = text(bucket["action"], "candidate action")
        key = (source, action)
        require(source in states and key not in candidates and
                (previous_candidate is None or key > previous_candidate),
                "candidate keys are not canonical")
        previous_candidate = key
        raw_targets = strings(bucket["target_keys"], "candidate target keys",
                              sorted_unique=True)
        parsed_targets = [
            SEM.parse_target_key(target, "candidate target key")
            for target in raw_targets
        ]
        require(all(raw_target == SEM.bundle_config_key(target)
                    for raw_target, target in zip(raw_targets, parsed_targets)),
                "candidate target key is not canonical")
        require(len(parsed_targets) == len(set(parsed_targets)),
                "candidate targets repeat a semantic state")
        targets = frozenset(parsed_targets)
        expected = problem.post(states[source], action)
        missing = sorted(SEM.config_key(target) for target in expected - targets)
        extra = sorted(SEM.config_key(target) for target in targets - expected)
        require(targets == expected,
                f"candidate Post differs: block={expected_index} "
                f"source={source} action={action} expected={len(expected)} "
                f"declared={len(targets)} missing={missing[:1]} extra={extra[:1]}")
        controllable = exact_bool(bucket["controllable"],
                                  "candidate controllability")
        update = exact_bool(bucket["update"], "candidate update flag")
        require(controllable == problem.is_controllable(action),
                "candidate controllability differs")
        require(update == (action in states[source].pending),
                "candidate update flag differs")
        candidates[key] = (controllable, update, targets)
        by_source[source].add(action)
        candidate_outcomes += len(targets)
        nonempty_candidates += int(bool(targets))
    for identifier, state in states.items():
        require(by_source[identifier] == set(problem.candidates(state)),
                f"candidate action census differs at {identifier}")

    strategies: dict[tuple[str, str], tuple[str, ...]] = {}
    selected_by_source: dict[str, set[str]] = defaultdict(set)
    previous_strategy: tuple[str, str] | None = None
    for offset, raw in enumerate(array(row["strategy_buckets"],
                                       "strategy buckets")):
        bucket = object_(raw, f"strategy[{offset}]")
        exact_keys(bucket, STRATEGY_KEYS, "strategy bucket")
        source = text(bucket["source"], "strategy source")
        action = text(bucket["action"], "strategy action")
        key = (source, action)
        require(key in candidates and key not in strategies and
                (previous_strategy is None or key > previous_strategy),
                "strategy keys are not canonical candidates")
        previous_strategy = key
        target_ids = tuple(strings(bucket["target_state_ids"],
                                   "strategy target IDs", sorted_unique=True))
        require(bool(target_ids) and set(target_ids) <= set(states),
                "strategy leaves the retained rank domain")
        declared_post = frozenset(states[target] for target in target_ids)
        require(declared_post == candidates[key][2],
                "strategy targets differ from the complete candidate Post")
        require(all(ranks[target] < ranks[source] for target in target_ids),
                "strategy rank does not strictly decrease for every outcome")
        strategies[key] = target_ids
        selected_by_source[source].add(action)

    for identifier in states:
        enabled_uc = {
            action for action in by_source[identifier]
            if candidates[(identifier, action)][2]
            and not candidates[(identifier, action)][0]
        }
        enabled_c = {
            action for action in by_source[identifier]
            if candidates[(identifier, action)][2]
            and candidates[(identifier, action)][0]
        }
        selected = selected_by_source[identifier]
        if goals[identifier] is not None:
            require(not enabled_uc and not selected,
                    "quiet Goal has enabled UC or a selected strategy")
        elif enabled_uc:
            require(selected == enabled_uc,
                    "strategy must retain exactly every enabled UC and no C")
        else:
            require(len(selected) == 1 and selected <= enabled_c,
                    "strategy must retain exactly one enabled C")

    reachable = set(roots)
    queue = deque(roots)
    while queue:
        source = queue.popleft()
        for action in sorted(selected_by_source[source]):
            for target in strategies[(source, action)]:
                if target not in reachable:
                    reachable.add(target)
                    queue.append(target)
    require(reachable == set(states),
            "rank domain is not exactly strategy reachability from all roots")

    declared_goal_ids: dict[str, SEM.GoalPayload] = {}
    declared_goal_payloads: set[SEM.GoalPayload] = set()
    previous_goal_id: str | None = None
    previous_goal_key: str | None = None
    for offset, raw in enumerate(array(row["goal_payloads"],
                                       "local Goal payloads")):
        identifier, payload = _goal_payload(raw, f"Goal payload[{offset}]")
        payload_key = SEM.goal_payload_key(payload)
        require(identifier not in declared_goal_ids and
                (previous_goal_id is None or identifier > previous_goal_id),
                "Goal payload IDs are not sorted and unique")
        require(payload not in declared_goal_payloads and
                (previous_goal_key is None or payload_key > previous_goal_key),
                "Goal payloads are not in canonical semantic order")
        previous_goal_id = identifier
        previous_goal_key = payload_key
        declared_goal_ids[identifier] = payload
        declared_goal_payloads.add(payload)
    reached_goals = {payload for payload in goals.values() if payload is not None}
    require(declared_goal_payloads == reached_goals,
            "declared Goal payloads differ from retained quiet Goals")
    quiet_keys = strings(row["quiet_goal_keys"], "quiet Goal keys",
                         sorted_unique=True)
    independently_quiet = sorted(
        SEM.goal_payload_key(payload) for payload in problem.quiet_goals)
    require(quiet_keys == independently_quiet,
            "quiet Goal key census differs from independent load projection")

    counts = {
        "rank_states": len(states),
        "root_states": len(roots),
        "candidate_buckets": len(candidates),
        "nonempty_candidate_buckets": nonempty_candidates,
        "candidate_outcomes": candidate_outcomes,
        "strategy_buckets": len(strategies),
        "goal_payloads": len(declared_goal_ids),
        "full_goals": len(problem.full_goals),
        "quiet_goals": len(problem.quiet_goals),
    }
    return GeneratedLocalCheck(
        counts, declared_goal_ids, root_states, state_ids)


def verify_activation_relations(
        contract: SEM.Contract, problems: Sequence[SEM.BlockProblem],
        old_endpoint: Sequence[SEM.Endpoint], value: Any) -> dict[str, int]:
    """Check the emitted activation quotient rows against source iota."""
    rows = array(value, "activation relations")
    expected_bindings = [
        (block_index, tester.identifier, problem, tester)
        for block_index, problem in enumerate(problems)
        for tester in sorted(problem.new_testers,
                             key=lambda item: item.identifier)
    ]
    require(len(rows) == len(expected_bindings),
            "activation relation tester census differs")
    total_pairs = 0
    for offset, (raw, binding) in enumerate(zip(rows, expected_bindings)):
        block_index, tester_id, problem, tester = binding
        row = object_(raw, f"activation relation[{offset}]")
        exact_keys(row, ACTIVATION_ROW_KEYS, "activation relation row")
        require(exact_int(row["block_index"], "activation block index", 0) ==
                block_index, "activation relation block index differs")
        require(text(row["tester_id"], "activation tester id") == tester_id,
                "activation relation tester differs")
        source = contract.activations[tester.identifier]
        indices = tuple(source.observer_global_indices)
        require(tuple(integers(row["global_observer_indices"],
                               "activation observer indices")) == indices,
                "activation observer-index binding differs")
        local_by_global = {
            observer.index: observer for observer in problem.observers
        }
        require(all(index in local_by_global for index in indices),
                "local activation omits a bound observer")
        global_observers = [contract.observers[index] for index in indices]
        local_observers = [local_by_global[index] for index in indices]
        seeds = {
            tuple(endpoint.locals[0].observers[index] for index in indices)
            for endpoint in old_endpoint
        }
        expected_pairs = sorted(SEM.observer_pair_closure(
            global_observers, local_observers, seeds, contract.normal))
        declared_pairs: list[tuple[tuple[int, ...], tuple[int, ...]]] = []
        for pair_offset, raw_pair in enumerate(array(row["pairs"],
                                                     "activation pairs")):
            pair = object_(raw_pair,
                           f"activation pair[{offset}][{pair_offset}]")
            exact_keys(pair, ACTIVATION_PAIR_KEYS, "activation pair")
            global_state = tuple(integers(
                pair["global"], "activation global tuple",
                sorted_unique=False))
            local_state = tuple(integers(
                pair["local"], "activation local tuple",
                sorted_unique=False))
            require(len(global_state) == len(indices) and
                    len(local_state) == len(indices),
                    "activation tuple arity differs")
            expected_global = SEM.activation_residual(
                source, tester, global_state)
            expected_local = SEM.activation_residual(
                source, tester, local_state)
            declared_global = _optional_residual(
                pair["global_residual"], "activation global residual")
            declared_local = _optional_residual(
                pair["local_residual"], "activation local residual")
            require(declared_global == expected_global and
                    declared_local == expected_local,
                    "activation residual differs from source iota")
            if expected_local is not None:
                require(expected_local == expected_global,
                        "local activation quotient differs from source iota")
            declared_pairs.append((global_state, local_state))
        require(declared_pairs == expected_pairs,
                "activation closure pairs differ or are noncanonical")
        total_pairs += len(expected_pairs)
    return {"activation_testers": len(expected_bindings),
            "activation_relation_pairs": total_pairs}


def _check_observer_pair_order(value: Any) -> None:
    """Strengthen the shared relation check with canonical row ordering."""
    for row_offset, raw in enumerate(array(value, "observer relations")):
        row = object_(raw, f"observer relation[{row_offset}]")
        # The shared verifier checks the exact row and pair schemas.
        declared: list[tuple[tuple[int, ...], tuple[int, ...]]] = []
        for pair_offset, raw_pair in enumerate(array(
                row.get("pairs"), f"observer pairs[{row_offset}]")):
            pair = object_(raw_pair,
                           f"observer pair[{row_offset}][{pair_offset}]")
            if set(pair) == {"global", "local"}:
                declared.append((
                    tuple(integers(pair["global"], "observer global tuple",
                                   sorted_unique=False)),
                    tuple(integers(pair["local"], "observer local tuple",
                                   sorted_unique=False)),
                ))
        require(declared == sorted(set(declared)),
                "observer relation pairs are not sorted and unique")


def verify_transport(
        contract: SEM.Contract, value: Any,
        problems: Sequence[SEM.BlockProblem],
        checks: Sequence[GeneratedLocalCheck],
        old_endpoint: Sequence[SEM.Endpoint],
        new_endpoint: Sequence[SEM.Endpoint]) -> dict[str, int]:
    """Recompute activation, observer, load, terminal assembly, and kappa."""
    transport = object_(value, "transport")
    exact_keys(transport, TRANSPORT_KEYS, "transport")
    activation = verify_activation_relations(
        contract, problems, old_endpoint, transport["activation_relations"])
    _check_observer_pair_order(transport["observer_relations"])
    relations = SEM.derive_observer_relations(
        contract, problems, old_endpoint, transport)
    observer_pairs = sum(len(pairs) for _indices, pairs in relations)

    # Feed only generated Goal IDs and the independently recomputed counts to
    # the established semantic transport checker.  No historical envelope or
    # historical certificate is read; the synthetic wrapper merely adapts the
    # four generated transport arrays to that stable function's call shape.
    loadable = SEM.loadable_endpoints(contract, new_endpoint)
    loadable_set = set(loadable)
    selector_keys: set[SEM.EndpointProjection] = set()
    load_endpoint_count = 0
    for endpoint in new_endpoint:
        if endpoint in loadable_set:
            load_endpoint_count += 1
            selector_keys.add(SEM.endpoint_projection(endpoint))
    terminal_tuple_count = 1
    for check in checks:
        require(bool(check.goal_ids), "certificate has no retained local Goal")
        terminal_tuple_count *= len(check.goal_ids)
    terminal_rows = array(transport["terminal_assemblies"],
                          "terminal assemblies")
    adapter = {
        "terminal_product_verified": True,
        "transport": {
            "verified": True,
            "activation_tester_count": activation["activation_testers"],
            "activation_relation_pair_count":
                activation["activation_relation_pairs"],
            "observer_relation_pair_count": observer_pairs,
            "load_selector_signature_count": len(selector_keys),
            "load_selector_endpoint_count": load_endpoint_count,
            "certificate_terminal_tuple_count": terminal_tuple_count,
            "terminal_observer_fiber_count": len(terminal_rows),
            "observer_relations": transport["observer_relations"],
            "load_selectors": transport["load_selectors"],
            "terminal_assemblies": terminal_rows,
        },
    }
    shared_checks = [SEM.LocalCheck(check.counts, check.goal_ids)
                     for check in checks]
    report = SEM.verify_transport(
        contract, adapter, problems, shared_checks, old_endpoint, new_endpoint)
    require(report["activation_testers"] == activation["activation_testers"]
            and report["activation_relation_pairs"] ==
            activation["activation_relation_pairs"],
            "activation transport adapter census differs")
    return report


def _project_global_roots(
        endpoint: SEM.Endpoint, problem: SEM.BlockProblem) -> SEM.Config:
    physical, endpoint_testers = SEM.project_endpoint(
        endpoint, problem.block, problem.components, problem.observers,
        problem.old_testers, "OLD")
    tester_map = dict(endpoint_testers)
    for tester in problem.update_testers:
        tester_map[tester.identifier] = tester.boundary_state
    ordered = problem.old_testers + problem.new_testers + problem.update_testers
    testers = tuple((tester.identifier, tester_map[tester.identifier])
                    for tester in ordered if tester.identifier in tester_map)
    return SEM.Config(physical, testers, problem.update_actions)


def verify(
        ir: Mapping[str, Any], certificate: Mapping[str, Any],
        ir_bytes: bytes) -> dict[str, Any]:
    """Verify a generated certificate without importing its producer."""
    require(type(ir_bytes) is bytes and bool(ir_bytes),
            "IR exact-byte binding is absent")
    root = object_(certificate, "generated certificate")
    exact_keys(root, ROOT_KEYS, "generated certificate")
    require(root["schema_version"] == CERTIFICATE_SCHEMA,
            "generated certificate schema differs")

    boundary = object_(root["generator_boundary"], "generator boundary")
    exact_keys(boundary, GENERATOR_BOUNDARY_KEYS, "generator boundary")
    require(boundary["algorithm"] == ALGORITHM,
            "generator algorithm identifier differs")
    depth_bound = exact_int(boundary["depth_bound"], "depth bound", 0)
    require(depth_bound == MAX_STRONG_RANK,
            "generator depth bound is not the audited bound 32")
    for field in ("historical_bundle_consumed",
                  "supplied_certificate_consumed",
                  "outcome_fields_consumed"):
        require(not exact_bool(boundary[field], f"generator boundary {field}"),
                f"generator boundary consumed forbidden input: {field}")
    require(root["decision"] == "WIN", "generated decision is not WIN")

    contract = SEM.parse_contract(ir)
    binding = object_(root["ir_binding"], "IR binding")
    exact_keys(binding, IR_BINDING_KEYS, "IR binding")
    require(_hex_sha(binding["sha256"], "IR SHA") ==
            hashlib.sha256(ir_bytes).hexdigest(), "IR exact-byte SHA differs")
    require(exact_int(binding["size"], "IR byte size", 1) == len(ir_bytes),
            "IR exact-byte size differs")
    for field, expected in {
        "source_name": contract.source_name,
        "source_sha256": contract.source_sha256,
        "definition": contract.definition,
    }.items():
        require(binding[field] == expected, f"IR binding {field} differs")

    declared_partition = _validate_partition(
        root["component_partition"], len(contract.components))
    partition, normal_owners, update_owners = SEM.dependency_partition(contract)
    require(declared_partition == partition,
            "component partition differs from independent owner closure")

    globals_ = SEM.global_components(contract)
    old_endpoint = SEM.build_endpoint(
        contract, globals_, contract.old_testers, "OLD")
    new_endpoint = SEM.build_endpoint(
        contract, globals_, contract.new_testers, "NEW")
    endpoints = object_(root["endpoints"], "endpoints")
    exact_keys(endpoints, {"old", "new"}, "endpoints")
    _verify_endpoint_declaration(endpoints["old"], old_endpoint, "old")
    _verify_endpoint_declaration(endpoints["new"], new_endpoint, "new")

    declared_locals = array(root["locals"], "locals")
    require(len(declared_locals) == len(partition),
            "local block census differs")
    problems: list[SEM.BlockProblem] = []
    checks: list[GeneratedLocalCheck] = []
    totals: dict[str, int] = defaultdict(int)
    local_reports: list[dict[str, Any]] = []
    for block_index, block in enumerate(partition):
        problem = SEM.build_block_problem(
            contract, block, old_endpoint, new_endpoint,
            normal_owners, update_owners)
        checked = verify_local(
            problem, declared_locals[block_index], block_index,
            depth_bound=depth_bound)
        for key, count in checked.counts.items():
            totals[key] += count
        problems.append(problem)
        checks.append(checked)
        local_reports.append({
            "block_index": block_index,
            "components": block,
            **checked.counts,
        })

    # Make the global-root coverage obligation explicit even when several
    # endpoint roots collapse to one local projection.
    roots_with_all_block_projections = 0
    for endpoint in old_endpoint:
        for problem, checked in zip(problems, checks):
            projected = _project_global_roots(endpoint, problem)
            require(projected in checked.root_states,
                    "a global old endpoint root lacks a declared local projection")
        roots_with_all_block_projections += 1

    transport_report = verify_transport(
        contract, root["transport"], problems, checks,
        old_endpoint, new_endpoint)
    owner_rows = {
        "normal": [{"action": action, "components": sorted(owners)}
                   for action, owners in sorted(normal_owners.items())],
        "update": [{"action": action, "components": sorted(owners)}
                   for action, owners in sorted(update_owners.items())],
    }
    report: dict[str, Any] = {
        "schema_version": REPORT_SCHEMA,
        "status": STATUS,
        "source_name": contract.source_name,
        "source_sha256": contract.source_sha256,
        "definition": contract.definition,
        "ir_exact_byte_sha256": hashlib.sha256(ir_bytes).hexdigest(),
        "ir_exact_byte_size": len(ir_bytes),
        "old_endpoint_states": len(old_endpoint),
        "new_endpoint_states": len(new_endpoint),
        "old_endpoint_semantic_sha256": _endpoint_digest(old_endpoint),
        "new_endpoint_semantic_sha256": _endpoint_digest(new_endpoint),
        "component_partition": partition,
        "whole_system_block": partition == [list(range(len(contract.components)))],
        "nontrivial_factorization": len(partition) > 1,
        "normal_owner_actions": len(normal_owners),
        "update_owner_actions": len(update_owners),
        "requirement_machines": len(contract.old_testers) +
            len(contract.new_testers) + len(contract.update_testers),
        "observer_machines": len(contract.observers),
        "owner_relation_sha256": SEM.sha256_bytes(
            SEM.canonical_bytes(owner_rows)),
        "global_old_root_projection_checks": roots_with_all_block_projections,
        "locals": local_reports,
        "totals": dict(sorted(totals.items())),
        "transport": transport_report,
        "semantic_reuse": {
            "module": "check_post_frontend_contract_certificate.py",
            "shared_functions": [
                "activation_residual", "array", "build_block_problem",
                "build_endpoint", "bundle_config_key", "canonical_bytes",
                "canonical_text", "config_key", "dependency_partition",
                "derive_observer_relations", "endpoint_projection",
                "exact_bool", "exact_int", "exact_keys",
                "global_components", "goal_payload_key", "integers",
                "loadable_endpoints", "object_", "observer_pair_closure",
                "parse_config_payload", "parse_contract",
                "parse_target_key", "project_endpoint", "require",
                "sha256_bytes", "strings", "text", "verify_transport",
            ],
            "shared_types": [
                "BlockProblem", "CheckError", "Config", "Contract",
                "Endpoint", "EndpointProjection", "GoalPayload",
                "LocalCheck",
            ],
            "transitive_functions_via_verify_transport": [
                "project_loadable_goal", "verify_activation_quotients",
                "verify_quiet_terminal_product",
            ],
        },
        "claim_boundary": {
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
        },
    }
    report["semantic_digest_sha256"] = SEM.sha256_bytes(
        SEM.canonical_bytes(report))
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ir", type=Path, required=True)
    parser.add_argument("--certificate", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        ir, ir_bytes = load_strict(args.ir, canonical=False)
        certificate, _certificate_bytes = load_strict(
            args.certificate, canonical=True)
        report = verify(ir, certificate, ir_bytes)
        raw = SEM.canonical_bytes(report)
        if args.output is None:
            print(raw.decode("utf-8"), end="")
        else:
            args.output.write_bytes(raw)
        return 0
    except CheckError as error:
        print("GENERATED_POST_FRONTEND_WIN_CERTIFICATE_INVALID=" + str(error))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
