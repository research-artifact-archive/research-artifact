#!/usr/bin/env python3
"""Independent declaration-dependency replay for source-native FG-DUCS.

The input is the conclusion-free compiled-declaration export produced after MTSA's
ordinary-LTS parser/composer.  This module does not import or execute the Java
factorizer, adapter, bundle exporter, or solvers.  It independently rebuilds
normal/update action support, deterministic tester/observer effects, the
tester/update fixed point, precedence edges, the union-find partition, and the
ownerless-event rejection gate.

This is intentionally *not* an independent source frontend or a source-to-WIN
replay.  The shared MTSA parser/composer and all endpoint, Goal/load, local-game,
and witness-transport semantics remain in the disclosed producer TCB.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


SCHEMA = "fg-ducs-native-source-dependency-facts-v1"
REPORT_SCHEMA = "fg-ducs-native-source-dependency-replay-v1"
BOUNDARY_ACTIONS = {"tau", "hotSwapIn", "hotSwapOut"}
RECEIPT_KINDS = {
    "ordinary-action", "update-action", "tester", "activation", "precedence"
}
FACT_KEYS = {
    "schema_version", "evidence_scope", "source_name", "source_sha256",
    "definition", "shared_mtsa_frontend", "independent_source_frontend",
    "fixed_endpoint_products_materialized", "local_update_games_materialized",
    "global_mixed_game_materialized",
    "old_new_controller_synthesis_performed",
    "source_to_witness_replay", "conclusion_fields_present", "flags",
    "controllable_actions", "components", "old_safety_machines",
    "new_safety_machines", "transition_requirement_machines",
    "observer_machines", "protocol",
}
MACHINE_KEYS = {"name", "max_states", "alphabet", "transitions"}
TRANSITION_KEYS = {"source", "action_index", "targets"}
COMPONENT_KEYS = {
    "index", "old_machine", "new_machine", "transfer_relation",
    "transfer_has_action_sequence", "reconfigure_action",
}
TRANSFER_KEYS = {"source", "targets"}
PROTOCOL_KEYS = {
    "progress_actions_in_index_order", "stop_old_actions",
    "reconfigure_actions", "start_new_actions", "old_safety_to_stop_action",
    "new_safety_to_start_action", "action_to_mapping_indices", "precedence",
}
MAPPING_KEYS = {"action", "mapping_indices"}
PRECEDENCE_KEYS = {"before", "after"}
FLAGS_KEYS = {
    "on_the_fly", "revised_on_the_fly", "fine_grained", "selective",
    "direct_transfer_relations",
}
FORBIDDEN_CONCLUSION_KEYS = {
    "component_partition", "dependency_receipts", "factor_status",
    "solve_status", "factorization_status", "winning", "losing",
    "certificate", "strategy", "rank", "witness", "local_game",
    "endpoint_product", "owner_sets", "action_owners",
}


class ReplayError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReplayError(message)


def exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    require(type(value) is dict, f"{label} is not an object")
    observed = set(value)
    require(observed == expected, f"{label} key census differs: {sorted(observed ^ expected)}")


def integer(value: Any, label: str, *, minimum: int | None = None) -> int:
    require(type(value) is int, f"{label} is not an integer")
    if minimum is not None:
        require(value >= minimum, f"{label} is below {minimum}")
    return value


def text(value: Any, label: str) -> str:
    require(type(value) is str and bool(value), f"{label} is not nonempty text")
    return value


def sha256_text(value: Any, label: str) -> str:
    observed = text(value, label)
    require(re.fullmatch(r"[0-9a-f]{64}", observed) is not None, f"{label} is not lowercase SHA-256")
    return observed


def string_list(value: Any, label: str, *, sorted_unique: bool = False) -> list[str]:
    require(type(value) is list, f"{label} is not a list")
    result = [text(item, f"{label} item") for item in value]
    require(len(result) == len(set(result)), f"{label} contains duplicates")
    if sorted_unique:
        require(result == sorted(result), f"{label} is not sorted")
    return result


def integer_list(value: Any, label: str, *, minimum: int = 0) -> list[int]:
    require(type(value) is list, f"{label} is not a list")
    result = [integer(item, f"{label} item", minimum=minimum) for item in value]
    require(result == sorted(set(result)), f"{label} is not sorted and unique")
    return result


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key: " + key)
        result[key] = value
    return result


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise ReplayError(f"invalid strict JSON: {path}") from error
    require(type(value) is dict, "JSON root is not an object")
    return value


def canonical(value: Any) -> bytes:
    try:
        return (json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
            allow_nan=False,
        ) + "\n").encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ReplayError("value is not canonical JSON") from error


def reject_conclusions(value: Any) -> None:
    if type(value) is dict:
        for key, child in value.items():
            require(key not in FORBIDDEN_CONCLUSION_KEYS, f"facts contain forbidden conclusion field: {key}")
            reject_conclusions(child)
    elif type(value) is list:
        for child in value:
            reject_conclusions(child)


@dataclass(frozen=True)
class Machine:
    name: str
    max_states: int
    alphabet: tuple[str, ...]
    transitions: Mapping[tuple[int, str], frozenset[int]]

    @property
    def semantic_alphabet(self) -> frozenset[str]:
        return frozenset(action.replace("?", "") for action in self.alphabet)

    def targets(self, state: int, action: str) -> frozenset[int]:
        return self.transitions.get((state, action), frozenset())

    def reachable_states(self) -> frozenset[int]:
        discovered = {0}
        pending = [0]
        while pending:
            source = pending.pop(0)
            for (edge_source, _action), targets in self.transitions.items():
                if edge_source != source:
                    continue
                for target in targets:
                    if target >= 0 and target not in discovered:
                        discovered.add(target)
                        pending.append(target)
        return frozenset(discovered)

    def reject_internal_tau(self) -> None:
        for state in range(self.max_states):
            require(not self.targets(state, "tau"), f"internal tau transition in {self.name}")

    def deterministic_target(self, state: int, action: str, *, missing_is_error: bool) -> int:
        if action not in self.semantic_alphabet:
            return state
        targets = self.targets(state, action)
        if not targets:
            return -1 if missing_is_error else state
        require(len(targets) == 1, f"nondeterministic tester/observer transition: {self.name}/{state}/{action}")
        target = next(iter(targets))
        if target < 0:
            return -1
        require(target < self.max_states, f"tester/observer target leaves state space: {self.name}")
        return target


def parse_machine(value: Any, label: str) -> Machine:
    exact_keys(value, MACHINE_KEYS, label)
    name = text(value["name"], f"{label}.name")
    max_states = integer(value["max_states"], f"{label}.max_states", minimum=1)
    alphabet = string_list(value["alphabet"], f"{label}.alphabet")
    rows = value["transitions"]
    require(type(rows) is list, f"{label}.transitions is not a list")
    transitions: dict[tuple[int, str], frozenset[int]] = {}
    last_order: tuple[int, int] | None = None
    for index, row in enumerate(rows):
        exact_keys(row, TRANSITION_KEYS, f"{label}.transitions[{index}]")
        source = integer(row["source"], f"{label}.source", minimum=0)
        require(source < max_states, f"{label} transition source leaves state space")
        action_index = integer(row["action_index"], f"{label}.action_index", minimum=0)
        require(action_index < len(alphabet), f"{label} action index leaves alphabet")
        targets = integer_list(row["targets"], f"{label}.targets", minimum=-1)
        require(bool(targets), f"{label} transition has no target")
        order = (source, action_index)
        require(last_order is None or order > last_order, f"{label} transition rows are not canonical")
        last_order = order
        raw_action = alphabet[action_index]
        require("?" not in raw_action, f"modal transition is unsupported: {label}/{raw_action}")
        key = (source, raw_action.replace("?", ""))
        require(key not in transitions, f"{label} repeats a semantic transition row")
        transitions[key] = frozenset(targets)
    return Machine(name, max_states, tuple(alphabet), transitions)


def parse_machine_list(value: Any, label: str) -> list[Machine]:
    require(type(value) is list, f"{label} is not a list")
    result = [parse_machine(item, f"{label}[{index}]") for index, item in enumerate(value)]
    require([item.name for item in result] == sorted(item.name for item in result), f"{label} is not name-sorted")
    require(len({item.name for item in result}) == len(result), f"{label} repeats a machine name")
    return result


@dataclass(frozen=True)
class Component:
    index: int
    old: Machine
    new: Machine
    reconfigure_action: str


@dataclass(frozen=True)
class Tester:
    role: str
    source_name: str
    machine: Machine
    local_alphabet: frozenset[str]
    update_action: str | None
    effective_actions: frozenset[str]


@dataclass(frozen=True, order=True)
class Receipt:
    kind: str
    declaration: str
    components: tuple[int, ...]

    def json(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "declaration": self.declaration,
            "components": list(self.components),
        }


class UnionFind:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))

    def find(self, value: int) -> int:
        while self.parent[value] != value:
            self.parent[value] = self.parent[self.parent[value]]
            value = self.parent[value]
        return value

    def union_support(self, support: Iterable[int]) -> None:
        ordered = sorted(set(support))
        if not ordered:
            return
        root = self.find(ordered[0])
        for value in ordered[1:]:
            other = self.find(value)
            if root != other:
                self.parent[other] = root

    def partition(self) -> list[list[int]]:
        blocks: dict[int, list[int]] = {}
        for value in range(len(self.parent)):
            blocks.setdefault(self.find(value), []).append(value)
        return sorted((sorted(block) for block in blocks.values()), key=lambda block: block[0])


def parse_string_map(value: Any, label: str) -> dict[str, str]:
    require(type(value) is dict, f"{label} is not an object")
    keys = list(value)
    require(keys == sorted(keys), f"{label} keys are not sorted")
    result = {text(key, f"{label} key"): text(child, f"{label}[{key}]") for key, child in value.items()}
    return result


def validate_component_machine(machine: Machine, label: str) -> None:
    reachable = machine.reachable_states()
    for (source, action), targets in machine.transitions.items():
        if source in reachable:
            require(action != "tau", f"internal tau transition in {label}")
        require(all(0 <= target < machine.max_states for target in targets), f"component target leaves state space: {label}")


def has_nonidentity(machine: Machine, action: str) -> bool:
    if action not in machine.semantic_alphabet:
        return False
    for state in machine.reachable_states():
        if machine.targets(state, action) != frozenset({state}):
            return True
    return False


def compile_testers(
    machines: list[Machine], role: str, common: set[str], update_map: Mapping[str, str]
) -> list[Tester]:
    result: list[Tester] = []
    for machine in machines:
        machine.reject_internal_tau()
        local: set[str] = set()
        for action in machine.alphabet:
            if action in BOUNDARY_ACTIONS or action.startswith("@"):
                continue
            require(not action.endswith("?"), f"modal action in safety tester {machine.name}: {action}")
            require(action in common, f"tester action outside common alphabet: {machine.name}/{action}")
            local.add(action)
        update_action = None if role == "update_time" else update_map.get(machine.name)
        if role != "update_time":
            require(update_action is not None, f"missing update action for {role} safety {machine.name}")
        effective: set[str] = set()
        for action in local:
            for state in range(machine.max_states):
                if machine.deterministic_target(state, action, missing_is_error=True) != state:
                    effective.add(action)
                    break
        result.append(Tester(
            role, machine.name, machine, frozenset(local), update_action,
            frozenset(effective),
        ))
    return result


def effective_observer_actions(machine: Machine, normal: set[str]) -> set[str]:
    machine.reject_internal_tau()
    result: set[str] = set()
    for action in machine.semantic_alphabet & normal:
        for state in range(machine.max_states):
            target = machine.deterministic_target(state, action, missing_is_error=False)
            require(target >= 0, f"observer reaches ERROR: {machine.name}")
            if target != state:
                result.add(action)
                break
    return result


def union_sets(left: Iterable[int] | None, right: Iterable[int] | None) -> frozenset[int]:
    return frozenset(set(left or ()) | set(right or ()))


def owners_of(actions: Iterable[str], normal: Mapping[str, frozenset[int]], update: Mapping[str, frozenset[int]]) -> frozenset[int]:
    result: set[int] = set()
    for action in actions:
        result.update(normal.get(action, update.get(action, frozenset())))
    return frozenset(result)


def tester_support(tester: Tester, normal: Mapping[str, frozenset[int]], update: Mapping[str, frozenset[int]]) -> frozenset[int]:
    result = set(owners_of(tester.effective_actions, normal, update))
    if tester.update_action is not None:
        result.update(update.get(tester.update_action, frozenset()))
    return frozenset(result)


def parse_facts(value: Mapping[str, Any]) -> dict[str, Any]:
    exact_keys(value, FACT_KEYS, "facts")
    reject_conclusions(value)
    require(value["schema_version"] == SCHEMA, "facts schema differs")
    require(value["evidence_scope"] == "shared_mtsa_frontend_compiled_declaration_facts", "facts evidence scope differs")
    source_name = text(value["source_name"], "source_name")
    source_sha256 = sha256_text(value["source_sha256"], "source_sha256")
    definition = text(value["definition"], "definition")
    for key, expected in {
        "shared_mtsa_frontend": True,
        "independent_source_frontend": False,
        "fixed_endpoint_products_materialized": False,
        "local_update_games_materialized": False,
        "global_mixed_game_materialized": False,
        "old_new_controller_synthesis_performed": True,
        "source_to_witness_replay": False,
        "conclusion_fields_present": False,
    }.items():
        require(type(value[key]) is bool and value[key] is expected, f"facts boundary flag differs: {key}")

    flags = value["flags"]
    exact_keys(flags, FLAGS_KEYS, "flags")
    for key in FLAGS_KEYS:
        require(type(flags[key]) is bool, f"flags.{key} is not Boolean")
    require(flags == {
        "on_the_fly": True,
        "revised_on_the_fly": True,
        "fine_grained": True,
        "selective": False,
        "direct_transfer_relations": True,
    }, "unsupported native declaration flags")
    controllable = set(string_list(value["controllable_actions"], "controllable_actions", sorted_unique=True))

    raw_components = value["components"]
    require(type(raw_components) is list and bool(raw_components), "components are absent")
    components: list[Component] = []
    for expected_index, row in enumerate(raw_components):
        exact_keys(row, COMPONENT_KEYS, f"components[{expected_index}]")
        index = integer(row["index"], "component index", minimum=0)
        require(index == expected_index, "component indices are not contiguous")
        old = parse_machine(row["old_machine"], f"components[{index}].old")
        new = parse_machine(row["new_machine"], f"components[{index}].new")
        validate_component_machine(old, f"component {index} old")
        validate_component_machine(new, f"component {index} new")
        require(row["transfer_has_action_sequence"] is False, "action-sequence transfer is unsupported")
        transfer_rows = row["transfer_relation"]
        require(type(transfer_rows) is list and bool(transfer_rows), "transfer relation is empty")
        seen_sources: list[int] = []
        for transfer_index, transfer in enumerate(transfer_rows):
            exact_keys(transfer, TRANSFER_KEYS, f"component {index} transfer {transfer_index}")
            source_state = integer(transfer["source"], "transfer source", minimum=0)
            require(source_state < old.max_states, "transfer source leaves old state space")
            targets = integer_list(transfer["targets"], "transfer targets", minimum=0)
            require(bool(targets) and all(target < new.max_states for target in targets), "transfer target leaves new state space")
            seen_sources.append(source_state)
        require(seen_sources == sorted(set(seen_sources)), "transfer sources are not canonical")
        components.append(Component(index, old, new, text(row["reconfigure_action"], "reconfigure action")))

    protocol = value["protocol"]
    exact_keys(protocol, PROTOCOL_KEYS, "protocol")
    progress = string_list(protocol["progress_actions_in_index_order"], "protocol progress actions")
    stop_actions = set(string_list(protocol["stop_old_actions"], "stop actions", sorted_unique=True))
    reconfigure_actions = set(string_list(protocol["reconfigure_actions"], "reconfigure actions", sorted_unique=True))
    start_actions = set(string_list(protocol["start_new_actions"], "start actions", sorted_unique=True))
    old_update_map = parse_string_map(protocol["old_safety_to_stop_action"], "old safety map")
    new_update_map = parse_string_map(protocol["new_safety_to_start_action"], "new safety map")
    require(set(old_update_map.values()) == stop_actions, "old safety/stop action census differs")
    require(set(new_update_map.values()) == start_actions, "new safety/start action census differs")

    mapping_rows = protocol["action_to_mapping_indices"]
    require(type(mapping_rows) is list, "action-to-mapping table is not a list")
    action_to_mappings: dict[str, tuple[int, ...]] = {}
    for mapping_index, row in enumerate(mapping_rows):
        exact_keys(row, MAPPING_KEYS, f"action mapping {mapping_index}")
        action = text(row["action"], "mapped action")
        indices = tuple(integer_list(row["mapping_indices"], "mapping indices", minimum=0))
        require(action not in action_to_mappings, "duplicate action mapping")
        require(all(index < len(components) for index in indices), "mapping index leaves component range")
        action_to_mappings[action] = indices
    require(list(action_to_mappings) == sorted(action_to_mappings), "action mapping rows are not sorted")
    component_reconfigures = [component.reconfigure_action for component in components]
    require(len(set(component_reconfigures)) == len(component_reconfigures), "reconfigure action is shared across components")
    require(set(component_reconfigures) == reconfigure_actions, "component reconfigure census differs")
    require(action_to_mappings == {
        component.reconfigure_action: (component.index,) for component in sorted(components, key=lambda item: item.reconfigure_action)
    }, "action-to-mapping relation differs from components")

    concrete_updates = component_reconfigures + list(old_update_map.values()) + list(new_update_map.values())
    require(len(concrete_updates) == len(set(concrete_updates)), "concrete update actions are not unique")
    require(set(concrete_updates) == set(progress), "progress/concrete update census differs")
    require(set(progress) == stop_actions | reconfigure_actions | start_actions, "update action kind census differs")

    old_safety = parse_machine_list(value["old_safety_machines"], "old safety machines")
    new_safety = parse_machine_list(value["new_safety_machines"], "new safety machines")
    update_safety = parse_machine_list(value["transition_requirement_machines"], "transition requirements")
    observers = parse_machine_list(value["observer_machines"], "observer machines")
    require(set(old_update_map) == {machine.name for machine in old_safety}, "old safety name census differs")
    require(set(new_update_map) == {machine.name for machine in new_safety}, "new safety name census differs")

    normal: set[str] = set()
    for component in components:
        normal.update(component.old.semantic_alphabet)
        normal.update(component.new.semantic_alphabet)
    normal.difference_update(BOUNDARY_ACTIONS)
    require(not (normal & set(progress)), "normal/update action namespaces overlap")
    common = normal | set(progress)
    testers = (
        compile_testers(old_safety, "old", common, old_update_map)
        + compile_testers(new_safety, "new", common, new_update_map)
        + compile_testers(update_safety, "update_time", common, {})
    )

    normal_owners: dict[str, frozenset[int]] = {}
    for action in sorted(normal):
        owners = {
            component.index for component in components
            if has_nonidentity(component.old, action) or has_nonidentity(component.new, action)
        }
        normal_owners[action] = frozenset(owners)

    update_owners: dict[str, frozenset[int]] = {
        component.reconfigure_action: frozenset({component.index}) for component in components
    }
    for action in progress:
        update_owners.setdefault(action, frozenset())
    changed = True
    while changed:
        changed = False
        for tester in testers:
            support = tester_support(tester, normal_owners, update_owners)
            if tester.update_action is not None:
                previous = update_owners.get(tester.update_action, frozenset())
                merged = union_sets(previous, support)
                if merged != previous:
                    update_owners[tester.update_action] = merged
                    changed = True

    receipts: set[Receipt] = set()
    union_find = UnionFind(len(components))

    def add_receipt(kind: str, declaration: str, support: Iterable[int]) -> None:
        ordered = tuple(sorted(set(support)))
        if not ordered:
            return
        require(kind in RECEIPT_KINDS, "unknown receipt kind")
        require(all(0 <= item < len(components) for item in ordered), "receipt support leaves component range")
        union_find.union_support(ordered)
        receipts.add(Receipt(kind, declaration, ordered))

    for action in sorted(normal_owners):
        if normal_owners[action]:
            add_receipt("ordinary-action", action, normal_owners[action])
    for action in sorted(update_owners):
        require(bool(update_owners[action]), f"update action has no component support: {action}")
        add_receipt("update-action", action, update_owners[action])
    for tester in testers:
        support = tester_support(tester, normal_owners, update_owners)
        require(bool(support), f"opaque tester has no component support: {tester.source_name}")
        add_receipt("tester", tester.source_name, support)
    for tester in (item for item in testers if item.role == "new"):
        add_receipt("activation", tester.source_name, tester_support(tester, normal_owners, update_owners))

    precedence_rows = protocol["precedence"]
    require(type(precedence_rows) is list, "precedence is not a list")
    precedence: list[tuple[str, str]] = []
    last_edge: tuple[str, str] | None = None
    for edge_index, row in enumerate(precedence_rows):
        exact_keys(row, PRECEDENCE_KEYS, f"precedence[{edge_index}]")
        edge = (text(row["before"], "precedence before"), text(row["after"], "precedence after"))
        require(edge[0] in update_owners and edge[1] in update_owners and edge[0] != edge[1], "invalid precedence edge")
        require(last_edge is None or edge > last_edge, "precedence rows are not canonical")
        last_edge = edge
        precedence.append(edge)
        add_receipt("precedence", edge[0] + "<" + edge[1], union_sets(update_owners[edge[0]], update_owners[edge[1]]))

    successors = {action: set() for action in progress}
    for before, after in precedence:
        successors[before].add(after)
    colors: dict[str, int] = {action: 0 for action in progress}

    def visit(action: str) -> None:
        require(colors[action] != 1, "update precedence is cyclic")
        if colors[action] == 2:
            return
        colors[action] = 1
        for target in successors[action]:
            visit(target)
        colors[action] = 2

    for action in progress:
        visit(action)

    controllable_normal = controllable & normal
    tester_effects = set().union(*(set(tester.effective_actions) for tester in testers)) if testers else set()
    observer_effects = set().union(*(effective_observer_actions(observer, normal) for observer in observers)) if observers else set()
    ownerless_obstructions = sorted(
        action for action, owners in normal_owners.items()
        if not owners and (
            action not in controllable_normal
            or action in tester_effects
            or action in observer_effects
        )
    )
    partition = union_find.partition()
    ordered_receipts = sorted(receipts)
    return {
        "source_name": source_name,
        "source_sha256": source_sha256,
        "definition": definition,
        "component_count": len(components),
        "normal_action_count": len(normal),
        "normal_actions": sorted(normal),
        "controllable_normal_actions": sorted(controllable_normal),
        "ownerless_obstructions": ownerless_obstructions,
        "component_partition": partition,
        "dependency_receipts": [receipt.json() for receipt in ordered_receipts],
        "receipt_counts": dict(sorted(Counter(receipt.kind for receipt in ordered_receipts).items())),
    }


def _receipt_set(value: Any, label: str) -> set[Receipt]:
    require(type(value) is list, f"{label} is not a list")
    result: set[Receipt] = set()
    for index, row in enumerate(value):
        exact_keys(row, {"kind", "declaration", "components"}, f"{label}[{index}]")
        kind = text(row["kind"], f"{label} kind")
        require(kind in RECEIPT_KINDS, f"{label} kind differs")
        receipt = Receipt(
            kind,
            text(row["declaration"], f"{label} declaration"),
            tuple(integer_list(row["components"], f"{label} components", minimum=0)),
        )
        require(receipt not in result, f"{label} contains duplicate receipt")
        result.add(receipt)
    return result


def compare(
    facts: Mapping[str, Any],
    record: Mapping[str, Any],
    bundle: Mapping[str, Any] | None,
    stderr_text: str,
) -> dict[str, Any]:
    replay = parse_facts(facts)
    for field in ("source_sha256", "definition"):
        require(record.get("sha256" if field == "source_sha256" else field) == replay[field], f"record {field} binding differs")
    require(record.get("case_id") and type(record.get("case_id")) is str, "record case ID is absent")
    require(Path(text(record.get("path"), "record source path")).name == replay["source_name"], "record source name binding differs")
    obstructions = replay["ownerless_obstructions"]
    if obstructions:
        require(record.get("process_status") == "INVALID_OR_INCONCLUSIVE", "ownerless replay did not match invalid record")
        require(record.get("exit_code") == 2 and record.get("timed_out") is False, "invalid record terminal fields differ")
        require(bundle is None, "invalid ownerless case unexpectedly has a bundle")
        prefix = "NATIVE_FACTOR_INVALID=ownerless normal event is not a disable-able pure stutter: "
        diagnostic_actions = re.findall(re.escape(prefix) + r"([^\r\n]+)", stderr_text)
        require(len(diagnostic_actions) == 1 and diagnostic_actions[0] in obstructions, "ownerless diagnostic differs")
        dependency_outcome = "OWNERLESS_REJECT"
    else:
        require(record.get("process_status") == "SUCCESS", "dependency replay did not match successful record")
        require(record.get("exit_code") == 0 and record.get("timed_out") is False, "successful record terminal fields differ")
        require(type(bundle) is dict, "successful dependency replay lacks a bundle")
        require(bundle.get("source_sha256") == replay["source_sha256"] and bundle.get("definition") == replay["definition"], "bundle source binding differs")
        expected_receipts = _receipt_set(replay["dependency_receipts"], "replay receipts")
        observed_receipts = _receipt_set(bundle.get("dependency_receipts"), "bundle receipts")
        require(observed_receipts == expected_receipts, "bundle dependency receipts differ from independent replay")
        require(bundle.get("component_partition") == replay["component_partition"], "bundle partition differs from independent replay")
        dependency_outcome = "ONE_BLOCK" if len(replay["component_partition"]) == 1 else "NONTRIVIAL_PARTITION"
        require(bundle.get("factor_status") == record.get("factor_status"), "registered producer factor status differs between record and bundle")
        require(
            bundle.get("factor_status")
            == ("TRIVIAL_ONE_BLOCK" if dependency_outcome == "ONE_BLOCK" else "NONTRIVIAL_SOURCE_NATIVE"),
            "registered producer factor status is not concordant with replayed partition",
        )

    return {
        "schema_version": REPORT_SCHEMA,
        "status": "PASS",
        "case_id": record["case_id"],
        "source_name": replay["source_name"],
        "source_sha256": replay["source_sha256"],
        "definition": replay["definition"],
        "evidence_scope": "post_frontend_dependency_partition_and_ownerless_gate_replay",
        "shared_mtsa_frontend": True,
        "independent_source_frontend": False,
        "source_to_witness_replay": False,
        "post_frontend_dependency_replay": True,
        "ordinary_lts_source_replay": False,
        "component_count": replay["component_count"],
        "normal_action_count": replay["normal_action_count"],
        "dependency_receipt_count": len(replay["dependency_receipts"]),
        "receipt_counts": replay["receipt_counts"],
        "component_partition": replay["component_partition"],
        "ownerless_obstructions": obstructions,
        "dependency_outcome": dependency_outcome,
        "dependency_receipt_agreement": bundle is not None,
        "component_partition_agreement": bundle is not None,
        "ownerless_gate_agreement": True if obstructions else None,
        "registered_producer_process_status": record.get("process_status"),
        "registered_producer_factor_status": record.get("factor_status"),
        "claim_boundary": (
            "The independent Python replay starts after the shared MTSA parser/composer. "
            "It checks declaration dependency closure, partition, and the ownerless gate only; "
            "endpoint, Goal/load, local-game, and WIN-witness semantics remain producer TCB."
        ),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("facts", type=Path)
    parser.add_argument("record", type=Path)
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--stderr", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = compare(
            load(args.facts),
            load(args.record),
            load(args.bundle) if args.bundle is not None else None,
            args.stderr.read_text(encoding="utf-8"),
        )
    except (ReplayError, OSError, UnicodeDecodeError) as error:
        print("NATIVE_SOURCE_DEPENDENCY_REPLAY_REJECT=" + str(error), file=__import__("sys").stderr)
        return 2
    __import__("sys").stdout.buffer.write(canonical(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
