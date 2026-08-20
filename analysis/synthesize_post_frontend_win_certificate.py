#!/usr/bin/env python3
"""Generate a fresh strong-WIN certificate from conclusion-free contract IR.

The only scientific input is ``fg-ducs-post-frontend-contract-facts-v1``.
Historical M8q/M8s bundles, records, outcomes, and certificates are neither
accepted as arguments nor imported.  This same-author generator reconstructs
endpoint products, dependency blocks, local transition systems, activation
relations, quiet load Goals, and a bounded strong rank certificate.  A
separate checker is responsible for accepting the generated artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import defaultdict, deque
from dataclasses import dataclass
from itertools import product
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from strong_rank_certificate_core import (
    SynthesisLimits,
    canonical_json,
    synthesize_strong_rank,
)


IR_SCHEMA = "fg-ducs-post-frontend-contract-facts-v1"
CERT_SCHEMA = "fg-ducs-generated-post-frontend-win-certificate-v1"
INCONCLUSIVE_SCHEMA = "fg-ducs-post-frontend-win-synthesis-inconclusive-v1"
ALGORITHM = "BOUNDED_MINIMUM_STRONG_RANK_PENDING_UPDATE_THEN_LEXICAL_V1"
BOUNDARY = {"tau", "hotSwapIn", "hotSwapOut"}
IR_ROOT_KEYS = {
    "schema_version", "evidence_scope", "source_name", "source_sha256",
    "definition", "shared_mtsa_frontend", "independent_source_frontend",
    "fixed_endpoint_products_materialized", "local_update_games_materialized",
    "global_mixed_game_materialized", "old_new_controller_synthesis_performed",
    "source_to_witness_replay", "conclusion_fields_present", "flags",
    "controllable_actions", "components", "old_safety_machines",
    "new_safety_machines", "transition_requirement_machines",
    "observer_machines", "protocol", "extraction_stage", "controllers",
    "observer_registry", "new_activation_sources", "load_selector",
    "boundary_actions", "physical_closure_materialized",
    "activation_relations_materialized", "goal_signatures_materialized",
    "dependency_partition_materialized", "winning_certificate_materialized",
}
FORBIDDEN_IR_KEYS = {
    "component_partition", "dependency_receipts", "factor_status",
    "solve_status", "winning", "losing", "certificate", "strategy", "rank",
    "witness", "proof", "local_game", "endpoint_product", "owner_sets",
    "action_owners", "candidate_buckets", "strategy_buckets",
    "terminal_assemblies",
}


class GenerationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GenerationError(message)


def exact_int(value: Any, label: str, minimum: int | None = None) -> int:
    require(type(value) is int, f"{label} is not an exact integer")
    if minimum is not None:
        require(value >= minimum, f"{label} is below {minimum}")
    return value


def exact_bool(value: Any, label: str) -> bool:
    require(type(value) is bool, f"{label} is not Boolean")
    return value


def text(value: Any, label: str) -> str:
    require(type(value) is str and bool(value), f"{label} is not text")
    return value


def array(value: Any, label: str) -> list[Any]:
    require(type(value) is list, f"{label} is not an array")
    return value


def object_(value: Any, label: str) -> dict[str, Any]:
    require(type(value) is dict and all(type(key) is str for key in value),
            f"{label} is not an object")
    return value


def exact_keys(value: Mapping[str, Any], keys: Iterable[str], label: str) -> None:
    expected = set(keys)
    require(set(value) == expected,
            f"{label} key census differs: {sorted(set(value) ^ expected)}")


def strings(value: Any, label: str, *, sorted_unique: bool = False) -> list[str]:
    result = [text(item, f"{label}[]") for item in array(value, label)]
    require(len(result) == len(set(result)), f"{label} contains duplicates")
    if sorted_unique:
        require(result == sorted(result), f"{label} is not sorted")
    return result


def integers(value: Any, label: str, *, minimum: int = 0,
             sorted_unique: bool = True) -> list[int]:
    result = [exact_int(item, f"{label}[]", minimum)
              for item in array(value, label)]
    if sorted_unique:
        require(result == sorted(set(result)),
                f"{label} is not sorted and unique")
    return result


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key: " + key)
        result[key] = value
    return result


def load_strict(path: Path) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
        decoded = raw.decode("utf-8")
        value = json.loads(
            decoded,
            object_pairs_hook=_unique_object,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise GenerationError(f"invalid strict JSON: {path}") from error
    return object_(value, "IR root"), raw


def canonical_bytes(value: Any) -> bytes:
    return (canonical_json(value) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def reject_ir_conclusions(value: Any) -> None:
    if type(value) is dict:
        for key, child in value.items():
            require(key not in FORBIDDEN_IR_KEYS,
                    f"IR contains forbidden conclusion field: {key}")
            reject_ir_conclusions(child)
    elif type(value) is list:
        for child in value:
            reject_ir_conclusions(child)


@dataclass(frozen=True)
class Machine:
    name: str
    initial: int
    states: tuple[int, ...]
    alphabet: tuple[str, ...]
    post: Mapping[tuple[int, str], frozenset[int]]

    def targets(self, state: int, action: str) -> frozenset[int]:
        return self.post.get((state, action), frozenset())

    def step(self, state: int, action: str, *, missing_error: bool) -> int:
        if state == -1:
            return -1
        require(state in self.states, f"unknown state in {self.name}: {state}")
        if action not in self.alphabet:
            return state
        targets = self.targets(state, action)
        if not targets:
            return -1 if missing_error else state
        require(len(targets) == 1,
                f"nondeterministic tester/observer {self.name}/{state}/{action}")
        return next(iter(targets))


def parse_compact_machine(value: Any, label: str) -> Machine:
    row = object_(value, label)
    exact_keys(row, {"name", "max_states", "alphabet", "transitions",
                     "initial_state"}, label)
    name = text(row["name"], f"{label}.name")
    maximum = exact_int(row["max_states"], f"{label}.max_states", 1)
    initial = exact_int(row["initial_state"], f"{label}.initial_state", 0)
    require(initial == 0 and initial < maximum,
            f"{label} compact initial state differs")
    alphabet = strings(row["alphabet"], f"{label}.alphabet")
    transitions: dict[tuple[int, str], frozenset[int]] = {}
    previous: tuple[int, int] | None = None
    for offset, raw in enumerate(array(row["transitions"],
                                       f"{label}.transitions")):
        edge = object_(raw, f"{label}.transitions[{offset}]")
        exact_keys(edge, {"source", "action_index", "targets"}, "compact edge")
        source = exact_int(edge["source"], "compact source", 0)
        action_index = exact_int(edge["action_index"], "compact action", 0)
        require(source < maximum and action_index < len(alphabet),
                f"{label} edge leaves domain")
        order = (source, action_index)
        require(previous is None or order > previous,
                f"{label} transitions are not canonical")
        previous = order
        targets = integers(edge["targets"], "compact targets", minimum=-1)
        require(bool(targets) and all(target == -1 or target < maximum
                                      for target in targets),
                f"{label} target leaves domain")
        key = (source, alphabet[action_index])
        require(key not in transitions, f"duplicate edge in {label}")
        transitions[key] = frozenset(targets)
    return Machine(name, initial, tuple(range(maximum)), tuple(alphabet), transitions)


def parse_controller(value: Any, label: str) -> Machine:
    row = object_(value, label)
    exact_keys(row, {"initial_state", "states", "actions",
                     "required_transitions", "maybe_transition_count"}, label)
    require(exact_int(row["maybe_transition_count"], "maybe count", 0) == 0,
            f"{label} contains MAYBE transitions")
    states = integers(row["states"], f"{label}.states", minimum=-1)
    initial = exact_int(row["initial_state"], f"{label}.initial", -1)
    require(initial in states and initial != -1, f"{label} initial is invalid")
    actions = strings(row["actions"], f"{label}.actions", sorted_unique=True)
    transitions: dict[tuple[int, str], frozenset[int]] = {}
    previous: tuple[int, str] | None = None
    for offset, raw in enumerate(array(row["required_transitions"],
                                       f"{label}.required_transitions")):
        edge = object_(raw, f"{label}.edge[{offset}]")
        exact_keys(edge, {"source", "action", "targets"}, "controller edge")
        source = exact_int(edge["source"], "controller source", -1)
        action = text(edge["action"], "controller action")
        targets = integers(edge["targets"], "controller targets", minimum=-1)
        key = (source, action)
        require(source in states and action in actions and bool(targets)
                and set(targets) <= set(states), f"{label} edge leaves domain")
        require(previous is None or key > previous,
                f"{label} transitions are not canonical")
        previous = key
        transitions[key] = frozenset(targets)
    return Machine(label, initial, tuple(states), tuple(actions), transitions)


@dataclass(frozen=True, order=True)
class Local:
    raw: int
    observers: tuple[int, ...] = ()


@dataclass(frozen=True, order=True)
class Tagged:
    version: str
    local: Local


@dataclass(frozen=True)
class Config:
    physical: tuple[Tagged, ...]
    testers: tuple[tuple[str, int], ...]
    pending: frozenset[str]

    def __post_init__(self) -> None:
        ordered = tuple(sorted(self.testers))
        require(len(ordered) == len({identifier for identifier, _ in ordered}),
                "configuration repeats a tester")
        object.__setattr__(self, "testers", ordered)

    def tester_map(self) -> dict[str, int]:
        return dict(self.testers)


@dataclass(frozen=True)
class Endpoint:
    controller: int
    locals: tuple[Local, ...]
    testers: tuple[tuple[str, int], ...]

    def tester_map(self) -> dict[str, int]:
        return dict(self.testers)


@dataclass(frozen=True)
class Tester:
    identifier: str
    source_name: str
    role: str
    machine: Machine
    alphabet: frozenset[str]
    update_action: str | None
    boundary_state: int

    def step(self, state: int, action: str) -> int:
        return state if action not in self.alphabet else self.machine.step(
            state, action, missing_error=True)

    def effective_actions(self) -> frozenset[str]:
        return frozenset(action for action in self.alphabet
                         if any(self.step(state, action) != state
                                for state in self.machine.states))


@dataclass(frozen=True)
class Observer:
    identifier: str
    index: int
    name: str
    machine: Machine
    alphabet: frozenset[str]

    def step(self, state: int, action: str) -> int:
        if action not in self.alphabet:
            return state
        target = self.machine.step(state, action, missing_error=False)
        require(target != -1, f"observer reaches ERROR: {self.name}")
        return target

    def effective_actions(self) -> frozenset[str]:
        return frozenset(action for action in self.alphabet
                         if any(self.step(state, action) != state
                                for state in self.machine.states))


@dataclass(frozen=True)
class ComponentDecl:
    index: int
    old: Machine
    new: Machine
    transfer: Mapping[int, frozenset[int]]
    reconfigure: str


@dataclass(frozen=True)
class LocalComponent:
    global_index: int
    old_states: frozenset[Local]
    new_states: frozenset[Local]
    old_alphabet: frozenset[str]
    new_alphabet: frozenset[str]
    old_environment: frozenset[str]
    new_environment: frozenset[str]
    old_post: Mapping[tuple[Local, str], frozenset[Local]]
    new_post: Mapping[tuple[Local, str], frozenset[Local]]
    transfer: Mapping[Local, frozenset[Local]]
    reconfigure: str

    def states(self, version: str) -> frozenset[Local]:
        return self.old_states if version == "OLD" else self.new_states

    def alphabet(self, version: str) -> frozenset[str]:
        return self.old_alphabet if version == "OLD" else self.new_alphabet

    def environment(self, version: str) -> frozenset[str]:
        return self.old_environment if version == "OLD" else self.new_environment

    def successors(self, version: str, state: Local,
                   action: str) -> frozenset[Local]:
        table = self.old_post if version == "OLD" else self.new_post
        return table.get((state, action), frozenset())


@dataclass(frozen=True)
class Activation:
    mode: str
    observer_indices: tuple[int, ...]
    mapping: Mapping[tuple[int, ...], int]


@dataclass
class Contract:
    source_name: str
    source_sha256: str
    definition: str
    components: list[ComponentDecl]
    controllers: dict[str, Machine]
    observers: list[Observer]
    old_testers: list[Tester]
    new_testers: list[Tester]
    update_testers: list[Tester]
    activations: dict[str, Activation]
    normal: frozenset[str]
    controllable_normal: frozenset[str]
    progress: tuple[str, ...]
    precedence: tuple[tuple[str, str], ...]
    load_mode: str
    load_indices: tuple[int, ...]


def parse_contract(value: Mapping[str, Any]) -> Contract:
    exact_keys(value, IR_ROOT_KEYS, "IR root")
    reject_ir_conclusions(value)
    require(value["schema_version"] == IR_SCHEMA, "IR schema differs")
    require(value["evidence_scope"] ==
            "shared_mtsa_post_frontend_conclusion_free_contract",
            "IR evidence scope differs")
    require(value["extraction_stage"] ==
            "AFTER_FIXED_ENDPOINT_CONTROLLER_SYNTHESIS_BEFORE_ENDPOINT_PRODUCT",
            "IR extraction stage differs")
    false_boundaries = (
        "fixed_endpoint_products_materialized", "physical_closure_materialized",
        "activation_relations_materialized", "goal_signatures_materialized",
        "local_update_games_materialized", "global_mixed_game_materialized",
        "dependency_partition_materialized", "winning_certificate_materialized",
        "source_to_witness_replay", "conclusion_fields_present",
    )
    require(all(value[field] is False for field in false_boundaries),
            "IR materialization/conclusion boundary differs")
    require(value["old_new_controller_synthesis_performed"] is True,
            "old/new controller synthesis boundary differs")
    require(value["shared_mtsa_frontend"] is True
            and value["independent_source_frontend"] is False,
            "frontend provenance boundary differs")
    flags = object_(value["flags"], "flags")
    expected_flags = {
        "on_the_fly": True,
        "revised_on_the_fly": True,
        "fine_grained": True,
        "selective": False,
        "direct_transfer_relations": True,
    }
    exact_keys(flags, expected_flags, "flags")
    require(all(exact_bool(flags[key], f"flag {key}") is expected
                for key, expected in expected_flags.items()),
            "unsupported declaration flags")
    source_name = text(value["source_name"], "source name")
    source_sha = text(value["source_sha256"], "source SHA")
    require(len(source_sha) == 64
            and all(char in "0123456789abcdef" for char in source_sha),
            "source SHA is invalid")
    definition = text(value["definition"], "definition")

    components: list[ComponentDecl] = []
    for index, raw in enumerate(array(value["components"], "components")):
        row = object_(raw, f"component[{index}]")
        exact_keys(row, {"index", "old_machine", "new_machine",
                         "transfer_relation", "transfer_has_action_sequence",
                         "reconfigure_action"}, f"component[{index}]")
        require(exact_int(row["index"], "component index", 0) == index,
                "component order differs")
        require(row["transfer_has_action_sequence"] is False,
                "action-sequence transfer is unsupported")
        old = parse_compact_machine(row["old_machine"], f"component {index} old")
        new = parse_compact_machine(row["new_machine"], f"component {index} new")
        transfer: dict[int, frozenset[int]] = {}
        previous: int | None = None
        for offset, raw_edge in enumerate(array(row["transfer_relation"],
                                                "transfer relation")):
            edge = object_(raw_edge, f"transfer[{offset}]")
            exact_keys(edge, {"source", "targets"}, "transfer row")
            source = exact_int(edge["source"], "transfer source", 0)
            targets = integers(edge["targets"], "transfer targets", minimum=0)
            require(previous is None or source > previous,
                    "transfer relation is not canonical")
            previous = source
            require(source in old.states and set(targets) <= set(new.states)
                    and bool(targets), "transfer leaves state domain")
            transfer[source] = frozenset(targets)
        components.append(ComponentDecl(
            index, old, new, transfer,
            text(row["reconfigure_action"], "reconfigure action")))
    require(bool(components), "component set is empty")

    normal: set[str] = set()
    for component in components:
        normal.update(component.old.alphabet)
        normal.update(component.new.alphabet)
    normal = {action for action in normal
              if action not in BOUNDARY and not action.endswith("?")}
    controllable = set(strings(value["controllable_actions"],
                               "controllable actions", sorted_unique=True))
    controllable_normal = frozenset(controllable & normal)

    protocol = object_(value["protocol"], "protocol")
    exact_keys(protocol, {
        "progress_actions_in_index_order", "stop_old_actions",
        "reconfigure_actions", "start_new_actions",
        "old_safety_to_stop_action", "new_safety_to_start_action",
        "action_to_mapping_indices", "precedence",
    }, "protocol")
    progress = tuple(strings(protocol["progress_actions_in_index_order"],
                             "progress actions"))
    stops = strings(protocol["stop_old_actions"], "stop actions",
                    sorted_unique=True)
    reconfigures = strings(protocol["reconfigure_actions"],
                           "reconfigure actions", sorted_unique=True)
    starts = strings(protocol["start_new_actions"], "start actions",
                     sorted_unique=True)
    old_to_stop = {
        text(key, "old safety key"): text(action, "old stop action")
        for key, action in object_(protocol["old_safety_to_stop_action"],
                                   "old stop map").items()
    }
    new_to_start = {
        text(key, "new safety key"): text(action, "new start action")
        for key, action in object_(protocol["new_safety_to_start_action"],
                                   "new start map").items()
    }
    precedence: list[tuple[str, str]] = []
    for raw_edge in array(protocol["precedence"], "precedence"):
        edge = object_(raw_edge, "precedence edge")
        exact_keys(edge, {"before", "after"}, "precedence edge")
        precedence.append((text(edge["before"], "precedence before"),
                           text(edge["after"], "precedence after")))
    require(precedence == sorted(set(precedence)),
            "precedence is not canonical")
    expected_reconfigures = [component.reconfigure for component in components]
    require(len(expected_reconfigures) == len(set(expected_reconfigures))
            and reconfigures == sorted(expected_reconfigures),
            "reconfigure action binding differs")
    require(stops == sorted(old_to_stop.values())
            and starts == sorted(new_to_start.values()),
            "stop/start action binding differs")
    concrete = set(stops) | set(reconfigures) | set(starts)
    require(len(concrete) == len(stops) + len(reconfigures) + len(starts)
            and set(progress) == concrete and len(progress) == len(concrete),
            "progress action census differs")
    require(not (concrete & normal) and concrete <= controllable,
            "normal/update namespaces or controllability differ")
    expected_mapping = sorted([
        {"action": component.reconfigure, "mapping_indices": [component.index]}
        for component in components
    ], key=lambda row: row["action"])
    typed_mapping: list[dict[str, Any]] = []
    for raw_mapping in array(protocol["action_to_mapping_indices"],
                             "mapping rows"):
        mapping = object_(raw_mapping, "mapping row")
        exact_keys(mapping, {"action", "mapping_indices"}, "mapping row")
        typed_mapping.append({
            "action": text(mapping["action"], "mapping action"),
            "mapping_indices": integers(mapping["mapping_indices"],
                                         "mapping indices"),
        })
    require(typed_mapping == expected_mapping, "mapping binding differs")
    common = normal | set(progress)

    def tester_group(field: str, role: str,
                     updates: Mapping[str, str]) -> list[Tester]:
        machines = [parse_compact_machine(raw, f"{field}[{index}]")
                    for index, raw in enumerate(array(value[field], field))]
        require([machine.name for machine in machines] ==
                sorted(machine.name for machine in machines)
                and len({machine.name for machine in machines}) == len(machines),
                f"{field} name/order differs")
        result: list[Tester] = []
        for ordinal, machine in enumerate(machines):
            require(all(not machine.targets(state, "tau")
                        for state in machine.states),
                    f"tester has tau transition: {machine.name}")
            alphabet = frozenset(action for action in machine.alphabet
                                 if action not in BOUNDARY
                                 and not action.startswith("@"))
            require(alphabet <= common,
                    f"tester action leaves contract alphabet: {machine.name}")
            update_action = updates.get(machine.name)
            if role in {"old", "new"}:
                require(update_action is not None,
                        f"tester update action is absent: {machine.name}")
            boundary_state = machine.step(machine.initial, "hotSwapIn",
                                          missing_error=True)
            result.append(Tester(
                f"{role}:{machine.name}:{ordinal}", machine.name, role,
                machine, alphabet, update_action, boundary_state))
        return result

    old_testers = tester_group("old_safety_machines", "old", old_to_stop)
    new_testers = tester_group("new_safety_machines", "new", new_to_start)
    update_testers = tester_group(
        "transition_requirement_machines", "update_time", {})
    require(set(old_to_stop) == {tester.source_name for tester in old_testers}
            and set(new_to_start) == {
                tester.source_name for tester in new_testers
            }, "safety/update tester binding differs")

    observers: list[Observer] = []
    for index, raw in enumerate(array(value["observer_registry"],
                                      "observer registry")):
        row = object_(raw, f"observer[{index}]")
        exact_keys(row, {"id", "index", "name", "machine"}, "observer row")
        require(exact_int(row["index"], "observer index", 0) == index,
                "observer index differs")
        machine = parse_compact_machine(row["machine"], f"observer {index}")
        name = text(row["name"], "observer name")
        require(machine.name == name
                and all(not machine.targets(state, "tau")
                        for state in machine.states),
                "observer name/tau boundary differs")
        observers.append(Observer(
            text(row["id"], "observer id"), index, name, machine,
            frozenset(set(machine.alphabet) & normal)))
    require([observer.name for observer in observers] ==
            sorted(observer.name for observer in observers)
            and len({observer.name for observer in observers}) == len(observers),
            "observer order/census differs")
    inherited = [parse_compact_machine(raw, f"observer machine[{index}]")
                 for index, raw in enumerate(array(value["observer_machines"],
                                                   "observer machines"))]
    require(inherited == [observer.machine for observer in observers],
            "observer registry differs from inherited machines")

    activations: dict[str, Activation] = {}
    activation_rows = array(value["new_activation_sources"],
                            "new activation sources")
    require(len(activation_rows) == len(new_testers),
            "activation/new tester census differs")
    for offset, raw in enumerate(activation_rows):
        row = object_(raw, f"activation[{offset}]")
        exact_keys(row, {"new_requirement_id", "safety_machine", "mode",
                         "ordered_observer_indices", "ordered_observer_ids",
                         "mapping_rows"}, "activation row")
        identifier = text(row["new_requirement_id"], "activation tester id")
        require(identifier == new_testers[offset].identifier
                and row["safety_machine"] == new_testers[offset].source_name,
                "activation/new tester order differs")
        indices = tuple(integers(row["ordered_observer_indices"],
                                 "activation observer indices",
                                 sorted_unique=False))
        ids = strings(row["ordered_observer_ids"], "activation observer ids")
        require(len(indices) == len(ids)
                and all(index < len(observers) for index in indices)
                and ids == [observers[index].identifier for index in indices],
                "activation observer binding differs")
        mode = text(row["mode"], "activation mode")
        require(mode in {"INITIAL", "OBSERVER_MAPPING"},
                "activation mode is invalid")
        mapping: dict[tuple[int, ...], int] = {}
        for raw_mapping in array(row["mapping_rows"], "activation mapping"):
            item = object_(raw_mapping, "activation mapping row")
            exact_keys(item, {"observer_state_tuple", "tester_state"},
                       "activation mapping row")
            signature = tuple(integers(item["observer_state_tuple"],
                                       "observer tuple", sorted_unique=False))
            target = exact_int(item["tester_state"], "activation target", -1)
            require(len(signature) == len(indices)
                    and target in set(new_testers[offset].machine.states) | {-1}
                    and signature not in mapping,
                    "activation mapping leaves domain or repeats")
            mapping[signature] = target
        require((mode == "INITIAL" and not indices and not mapping)
                or (mode == "OBSERVER_MAPPING" and indices and mapping),
                "activation payload differs from mode")
        activations[identifier] = Activation(mode, indices, mapping)

    controller_rows = object_(value["controllers"], "controllers")
    exact_keys(controller_rows, {"old", "new"}, "controllers")
    controllers = {
        "OLD": parse_controller(controller_rows["old"], "old controller"),
        "NEW": parse_controller(controller_rows["new"], "new controller"),
    }
    for version, controller in controllers.items():
        environment: set[str] = set()
        for component in components:
            environment.update(component.old.alphabet if version == "OLD"
                               else component.new.alphabet)
        environment &= normal
        require(environment <= set(controller.alphabet),
                f"{version} controller omits an environment action")
        require(all(action in normal for _state, action in controller.post),
                f"{version} controller has a non-normal action")

    load = object_(value["load_selector"], "load selector")
    exact_keys(load, {"mode", "reachable_indices"}, "load selector")
    load_mode = text(load["mode"], "load mode")
    load_indices = tuple(integers(load["reachable_indices"], "load indices"))
    require(load_mode in {"ALL_REACHABLE", "EXPLICIT_REACHABLE_INDEX"}
            and ((load_mode == "ALL_REACHABLE" and not load_indices)
                 or (load_mode == "EXPLICIT_REACHABLE_INDEX" and load_indices)),
            "load selector mode/payload differs")
    require(value["boundary_actions"] == {
        "hot_swap_in": "hotSwapIn", "hot_swap_out": "hotSwapOut"
    }, "boundary action declaration differs")
    return Contract(
        source_name, source_sha, definition, components, controllers,
        observers, old_testers, new_testers, update_testers, activations,
        frozenset(normal), controllable_normal, progress, tuple(precedence),
        load_mode, load_indices)


def machine_lts(machine: Machine, actions: Iterable[str]) -> tuple[
        frozenset[Local], frozenset[str],
        dict[tuple[Local, str], frozenset[Local]]]:
    kept = frozenset(set(machine.alphabet) & set(actions))
    states = frozenset(Local(state) for state in machine.states)
    post: dict[tuple[Local, str], frozenset[Local]] = {}
    for state in states:
        for action in kept:
            targets = machine.targets(state.raw, action)
            require(all(target >= 0 for target in targets),
                    f"physical component reaches ERROR: {machine.name}")
            if targets:
                post[(state, action)] = frozenset(Local(target)
                                                   for target in targets)
    return states, kept, post


def augmented_lts(machine: Machine, observers: Sequence[Observer],
                  normal: frozenset[str], seeds: Iterable[Local]) -> tuple[
        frozenset[Local], frozenset[str],
        dict[tuple[Local, str], frozenset[Local]]]:
    observer_actions: set[str] = set()
    for observer in observers:
        observer_actions.update(observer.alphabet)
    alphabet = frozenset((set(machine.alphabet) | observer_actions) & set(normal))
    seen: set[Local] = set()
    queue: deque[Local] = deque()
    for seed in seeds:
        require(seed.raw in machine.states
                and len(seed.observers) == len(observers),
                "augmented seed leaves domain")
        if seed not in seen:
            seen.add(seed)
            queue.append(seed)
    post: dict[tuple[Local, str], frozenset[Local]] = {}
    while queue:
        source = queue.popleft()
        for action in sorted(alphabet):
            if action in machine.alphabet:
                raw_targets = machine.targets(source.raw, action)
                if not raw_targets:
                    continue
                require(all(target >= 0 for target in raw_targets),
                        f"augmented component reaches ERROR: {machine.name}")
            else:
                raw_targets = frozenset({source.raw})
            observer_targets = tuple(
                observer.step(source.observers[index], action)
                for index, observer in enumerate(observers))
            targets = frozenset(Local(target, observer_targets)
                                for target in raw_targets)
            post[(source, action)] = targets
            for target in targets:
                if target not in seen:
                    seen.add(target)
                    queue.append(target)
    return frozenset(seen), alphabet, post


def make_components(contract: Contract, block: Sequence[int],
                    observers: Sequence[Observer],
                    block_normal: frozenset[str]) -> list[LocalComponent]:
    result: list[LocalComponent] = []
    observer_initials = tuple(observer.machine.initial for observer in observers)
    for local_index, global_index in enumerate(block):
        declaration = contract.components[global_index]
        old_environment = frozenset(
            set(declaration.old.alphabet) & set(block_normal))
        new_environment = frozenset(
            set(declaration.new.alphabet) & set(block_normal))
        if local_index == 0:
            old_seed = Local(declaration.old.initial, observer_initials)
            old_states, old_alphabet, old_post = augmented_lts(
                declaration.old, observers, block_normal, [old_seed])
            new_seeds = {Local(declaration.new.initial, observer_initials)}
            for old_state in old_states:
                for target in declaration.transfer.get(
                        old_state.raw, frozenset()):
                    new_seeds.add(Local(target, old_state.observers))
            new_states, new_alphabet, new_post = augmented_lts(
                declaration.new, observers, block_normal, new_seeds)
            transfer = {
                old_state: frozenset(Local(target, old_state.observers)
                                     for target in declaration.transfer.get(
                                         old_state.raw, frozenset()))
                for old_state in old_states
            }
        else:
            old_states, old_alphabet, old_post = machine_lts(
                declaration.old, block_normal)
            new_states, new_alphabet, new_post = machine_lts(
                declaration.new, block_normal)
            transfer = {
                Local(source): frozenset(Local(target) for target in targets)
                for source, targets in declaration.transfer.items()
            }
        result.append(LocalComponent(
            global_index, old_states, new_states, old_alphabet, new_alphabet,
            old_environment, new_environment, old_post, new_post, transfer,
            declaration.reconfigure))
    return result


def global_components(contract: Contract) -> list[LocalComponent]:
    return make_components(contract, range(len(contract.components)),
                           contract.observers, contract.normal)


def product_post(components: Sequence[LocalComponent], states: Sequence[Local],
                 version: str, action: str, *, endpoint: bool) -> set[
                     tuple[Local, ...]]:
    choices: list[list[Local]] = []
    participant = False
    for index, component in enumerate(components):
        participates = action in (component.alphabet(version)
                                  if endpoint else component.environment(version))
        participant = participant or participates
        if action in component.alphabet(version):
            targets = component.successors(version, states[index], action)
            if not targets:
                return set()
            choices.append(sorted(targets))
        else:
            choices.append([states[index]])
    if not participant:
        return set()
    result: set[tuple[Local, ...]] = {()}
    for values in choices:
        result = {prefix + (value,) for prefix in result for value in values}
    return result


def build_endpoint(contract: Contract, components: Sequence[LocalComponent],
                   testers: Sequence[Tester], version: str) -> list[Endpoint]:
    controller = contract.controllers[version]
    initial_locals: list[Local] = []
    for index, component in enumerate(components):
        declaration = contract.components[index]
        raw_initial = (declaration.old.initial if version == "OLD"
                       else declaration.new.initial)
        candidates = [state for state in component.states(version)
                      if state.raw == raw_initial]
        require(bool(candidates), "endpoint initial component state is absent")
        initial_locals.append(min(candidates, key=lambda state: state.observers))
    initial = Endpoint(
        controller.initial,
        tuple(initial_locals),
        tuple(sorted((tester.identifier, tester.machine.initial)
                     for tester in testers)),
    )
    discovered = [initial]
    seen = {initial}
    queue: deque[Endpoint] = deque([initial])
    while queue:
        state = queue.popleft()
        tester_map = state.tester_map()
        enabled = False
        for action in sorted(contract.normal):
            controller_targets = controller.targets(state.controller, action)
            physical_targets = product_post(
                components, state.locals, version, action, endpoint=True)
            environment_targets = product_post(
                components, state.locals, version, action, endpoint=False)
            if controller_targets and physical_targets:
                require(physical_targets == environment_targets,
                        f"{version} endpoint fails environment preservation")
            if environment_targets and action not in contract.controllable_normal:
                require(bool(controller_targets),
                        f"{version} controller disables uncontrollable action")
            if not controller_targets or not physical_targets:
                continue
            enabled = True
            tester_targets = tuple(sorted(
                (tester.identifier,
                 tester.step(tester_map[tester.identifier], action))
                for tester in testers))
            require(all(target != -1 for _identifier, target in tester_targets),
                    f"{version} endpoint violates safety tester")
            for controller_target in sorted(controller_targets):
                for physical_target in sorted(physical_targets):
                    target = Endpoint(controller_target, physical_target,
                                      tester_targets)
                    if target not in seen:
                        seen.add(target)
                        discovered.append(target)
                        queue.append(target)
        require(enabled, f"{version} endpoint has reachable deadlock")
    return discovered


def build_global_endpoint_direct(contract: Contract,
                                 testers: Sequence[Tester],
                                 version: str) -> list[Endpoint]:
    """Explore the reachable global endpoint without a physical pre-closure.

    ``global_components`` first materializes every physical/observer tuple
    reachable without the endpoint controller.  Most of that product is never
    an endpoint state.  This routine applies the same synchronized machine and
    observer transitions on demand while traversing the controller product.
    """
    controller = contract.controllers[version]
    initial = Endpoint(
        controller.initial,
        tuple(
            Local(
                (component.old.initial if version == "OLD"
                 else component.new.initial),
                tuple(observer.machine.initial
                      for observer in contract.observers) if index == 0 else (),
            )
            for index, component in enumerate(contract.components)
        ),
        tuple(sorted((tester.identifier, tester.machine.initial)
                     for tester in testers)),
    )
    discovered = [initial]
    seen = {initial}
    queue: deque[Endpoint] = deque([initial])
    while queue:
        state = queue.popleft()
        tester_map = state.tester_map()
        enabled = False
        for action in sorted(contract.normal):
            controller_targets = controller.targets(state.controller, action)
            choices: list[list[Local]] = []
            alphabet_participant = False
            environment_participant = False
            blocked = False
            for index, declaration in enumerate(contract.components):
                machine = declaration.old if version == "OLD" else declaration.new
                source = state.locals[index]
                machine_participant = action in machine.alphabet
                observer_participant = index == 0 and any(
                    action in observer.alphabet for observer in contract.observers)
                alphabet_participant = (alphabet_participant
                                        or machine_participant
                                        or observer_participant)
                environment_participant = (environment_participant
                                            or machine_participant)
                if machine_participant:
                    raw_targets = machine.targets(source.raw, action)
                    if not raw_targets:
                        blocked = True
                        break
                    require(all(target >= 0 for target in raw_targets),
                            f"{version} endpoint physical reaches ERROR")
                else:
                    raw_targets = frozenset({source.raw})
                if index == 0:
                    observers = tuple(
                        observer.step(source.observers[offset], action)
                        for offset, observer in enumerate(contract.observers))
                else:
                    observers = ()
                choices.append([Local(target, observers)
                                for target in sorted(raw_targets)])
            physical_targets: set[tuple[Local, ...]] = set()
            if alphabet_participant and not blocked:
                physical_targets = {()}
                for values in choices:
                    physical_targets = {
                        prefix + (value,)
                        for prefix in physical_targets for value in values
                    }
            environment_targets = (physical_targets
                                   if environment_participant else set())
            if controller_targets and physical_targets:
                require(physical_targets == environment_targets,
                        f"{version} endpoint fails environment preservation")
            if (environment_targets
                    and action not in contract.controllable_normal):
                require(bool(controller_targets),
                        f"{version} controller disables uncontrollable action")
            if not controller_targets or not physical_targets:
                continue
            enabled = True
            tester_targets = tuple(sorted(
                (tester.identifier,
                 tester.step(tester_map[tester.identifier], action))
                for tester in testers))
            require(all(target != -1 for _identifier, target in tester_targets),
                    f"{version} endpoint violates safety tester")
            for controller_target in sorted(controller_targets):
                for physical_target in sorted(physical_targets):
                    target = Endpoint(controller_target, physical_target,
                                      tester_targets)
                    if target not in seen:
                        seen.add(target)
                        discovered.append(target)
                        queue.append(target)
        require(enabled, f"{version} endpoint has reachable deadlock")
    return discovered


def has_nonidentity(machine: Machine, action: str) -> bool:
    return action in machine.alphabet and any(
        machine.targets(state, action) != frozenset({state})
        for state in machine.states)


def dependency_partition(contract: Contract) -> tuple[
        list[list[int]], dict[str, frozenset[int]],
        dict[str, frozenset[int]]]:
    normal_owners = {
        action: frozenset(component.index for component in contract.components
                          if has_nonidentity(component.old, action)
                          or has_nonidentity(component.new, action))
        for action in sorted(contract.normal)
    }
    testers = (contract.old_testers + contract.new_testers
               + contract.update_testers)
    for action, owners in normal_owners.items():
        if owners:
            continue
        tester_effect = any(action in tester.effective_actions()
                            for tester in testers)
        observer_effect = any(action in observer.effective_actions()
                              for observer in contract.observers)
        require(action in contract.controllable_normal
                and not tester_effect and not observer_effect,
                f"ownerless normal action is not pure disable-able stutter: {action}")
    update_owners: dict[str, frozenset[int]] = {
        component.reconfigure: frozenset({component.index})
        for component in contract.components
    }
    for action in contract.progress:
        update_owners.setdefault(action, frozenset())

    def support(tester: Tester) -> frozenset[int]:
        result: set[int] = set()
        for action in tester.effective_actions():
            result.update(normal_owners.get(
                action, update_owners.get(action, frozenset())))
        if tester.update_action is not None:
            result.update(update_owners.get(tester.update_action, frozenset()))
        return frozenset(result)

    changed = True
    while changed:
        changed = False
        for tester in testers:
            if tester.update_action is None:
                continue
            merged = frozenset(set(update_owners[tester.update_action])
                               | set(support(tester)))
            if merged != update_owners[tester.update_action]:
                update_owners[tester.update_action] = merged
                changed = True
    parent = list(range(len(contract.components)))

    def find(value: int) -> int:
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    def join(values: Iterable[int]) -> None:
        ordered = sorted(set(values))
        for value in ordered[1:]:
            left, right = find(ordered[0]), find(value)
            if left != right:
                parent[max(left, right)] = min(left, right)

    for owners in normal_owners.values():
        join(owners)
    for action, owners in update_owners.items():
        require(bool(owners), f"update action has no support: {action}")
        join(owners)
    for tester in testers:
        owners = support(tester)
        require(bool(owners), f"tester has no support: {tester.source_name}")
        join(owners)
    for before, after in contract.precedence:
        join(set(update_owners[before]) | set(update_owners[after]))
    groups: dict[int, list[int]] = defaultdict(list)
    for index in range(len(parent)):
        groups[find(index)].append(index)
    return (sorted(groups.values(), key=lambda block: block[0]),
            normal_owners, update_owners)


def tester_support(tester: Tester,
                   normal_owners: Mapping[str, frozenset[int]],
                   update_owners: Mapping[str, frozenset[int]]) -> frozenset[int]:
    result: set[int] = set()
    for action in tester.effective_actions():
        result.update(normal_owners.get(
            action, update_owners.get(action, frozenset())))
    if tester.update_action is not None:
        result.update(update_owners.get(tester.update_action, frozenset()))
    return frozenset(result)


def projected_tester(tester: Tester,
                     block_common: frozenset[str]) -> Tester:
    return Tester(
        tester.identifier, tester.source_name, tester.role, tester.machine,
        tester.effective_actions() & block_common, tester.update_action,
        tester.boundary_state)


def block_observers(contract: Contract, selected_new: Sequence[Tester],
                    block_normal: frozenset[str]) -> list[Observer]:
    required: set[int] = set()
    language: set[str] = set()
    for tester in selected_new:
        required.update(contract.activations[tester.identifier].observer_indices)
        language.update(tester.effective_actions())
    return [
        Observer(observer.identifier, observer.index, observer.name,
                 observer.machine,
                 frozenset(set(observer.alphabet) & language
                           & set(block_normal)))
        for observer in contract.observers if observer.index in required
    ]


def project_endpoint(endpoint: Endpoint, block: Sequence[int],
                     components: Sequence[LocalComponent],
                     observers: Sequence[Observer],
                     selected_testers: Sequence[Tester],
                     version: str) -> tuple[
                         tuple[Tagged, ...], tuple[tuple[str, int], ...]]:
    global_testers = endpoint.tester_map()
    global_observer_indices = [observer.index for observer in observers]
    physical: list[Tagged] = []
    for local_index, global_index in enumerate(block):
        original = endpoint.locals[global_index]
        if local_index == 0:
            selected_observers = tuple(
                endpoint.locals[0].observers[index]
                for index in global_observer_indices)
        else:
            selected_observers = ()
        local = Local(original.raw, selected_observers)
        require(local in components[local_index].states(version),
                "projected endpoint leaves local component domain")
        physical.append(Tagged(version, local))
    testers = tuple(sorted(
        (tester.identifier, global_testers[tester.identifier])
        for tester in selected_testers))
    return tuple(physical), testers


def physical_closure(components: Sequence[LocalComponent],
                     roots: Iterable[tuple[Tagged, ...]],
                     normal: frozenset[str]) -> frozenset[tuple[Tagged, ...]]:
    seen = set(roots)
    queue: deque[tuple[Tagged, ...]] = deque(seen)
    while queue:
        physical = queue.popleft()
        for action in sorted(normal):
            choices: list[list[Tagged]] = []
            participant = False
            blocked = False
            for index, tagged in enumerate(physical):
                component = components[index]
                participant = participant or action in component.environment(
                    tagged.version)
                if action in component.alphabet(tagged.version):
                    targets = component.successors(
                        tagged.version, tagged.local, action)
                    if not targets:
                        blocked = True
                        break
                    choices.append([Tagged(tagged.version, target)
                                    for target in sorted(targets)])
                else:
                    choices.append([tagged])
            if participant and not blocked:
                products: set[tuple[Tagged, ...]] = {()}
                for values in choices:
                    products = {prefix + (value,) for prefix in products
                                for value in values}
                for target in products:
                    if target not in seen:
                        seen.add(target)
                        queue.append(target)
        for index, tagged in enumerate(physical):
            if tagged.version != "OLD":
                continue
            for local in components[index].transfer.get(
                    tagged.local, frozenset()):
                target = list(physical)
                target[index] = Tagged("NEW", local)
                immutable = tuple(target)
                if immutable not in seen:
                    seen.add(immutable)
                    queue.append(immutable)
    return frozenset(seen)


def physical_goal_distances(
        components: Sequence[LocalComponent],
        closure: Iterable[tuple[Tagged, ...]],
        normal: frozenset[str],
        goal_physical: Iterable[tuple[Tagged, ...]]) -> dict[
            tuple[Tagged, ...], int]:
    """Exact relaxed physical distance to a quiet physical projection.

    The graph forgets tester residuals, activation, and update precedence, so
    its distance can only underestimate the concrete distance.  It retains
    synchronized normal actions and OLD-to-NEW transfer edges.
    """
    domain = set(closure)
    reverse: dict[tuple[Tagged, ...], set[tuple[Tagged, ...]]] = defaultdict(set)
    for source in sorted(domain):
        for action in sorted(normal):
            choices: list[list[Tagged]] = []
            participant = False
            blocked = False
            for index, tagged in enumerate(source):
                component = components[index]
                participant = (participant
                               or action in component.environment(tagged.version))
                if action in component.alphabet(tagged.version):
                    targets = component.successors(
                        tagged.version, tagged.local, action)
                    if not targets:
                        blocked = True
                        break
                    choices.append([Tagged(tagged.version, target)
                                    for target in sorted(targets)])
                else:
                    choices.append([tagged])
            if participant and not blocked:
                targets_product: set[tuple[Tagged, ...]] = {()}
                for values in choices:
                    targets_product = {
                        prefix + (value,) for prefix in targets_product
                        for value in values
                    }
                for target in targets_product:
                    require(target in domain,
                            "physical closure omits a normal successor")
                    reverse[target].add(source)
        for index, tagged in enumerate(source):
            if tagged.version != "OLD":
                continue
            for local in components[index].transfer.get(
                    tagged.local, frozenset()):
                target = list(source)
                target[index] = Tagged("NEW", local)
                immutable = tuple(target)
                require(immutable in domain,
                        "physical closure omits a transfer successor")
                reverse[immutable].add(source)

    distances: dict[tuple[Tagged, ...], int] = {}
    queue: deque[tuple[Tagged, ...]] = deque()
    for goal in sorted(set(goal_physical)):
        require(goal in domain, "quiet Goal leaves physical closure")
        distances[goal] = 0
        queue.append(goal)
    while queue:
        target = queue.popleft()
        distance = distances[target] + 1
        for source in sorted(reverse.get(target, set())):
            if source not in distances:
                distances[source] = distance
                queue.append(source)
    return distances


GoalPayload = tuple[tuple[Tagged, ...], tuple[tuple[str, int], ...]]


@dataclass
class BlockProblem:
    block: tuple[int, ...]
    components: list[LocalComponent]
    observers: list[Observer]
    normal: frozenset[str]
    controllable_normal: frozenset[str]
    old_testers: list[Tester]
    new_testers: list[Tester]
    update_testers: list[Tester]
    activations: dict[str, dict[tuple[Tagged, ...], int]]
    update_actions: frozenset[str]
    predecessors: dict[str, frozenset[str]]
    physical_goal_distance: Mapping[tuple[Tagged, ...], int]
    roots: frozenset[Config]
    full_goals: frozenset[GoalPayload]
    quiet_goals: frozenset[GoalPayload]

    @property
    def requirements(self) -> dict[str, Tester]:
        return {tester.identifier: tester for tester in
                self.old_testers + self.new_testers + self.update_testers}

    def structurally_valid(self, state: Config) -> bool:
        if len(state.physical) != len(self.components):
            return False
        for index, tagged in enumerate(state.physical):
            if tagged.local not in self.components[index].states(tagged.version):
                return False
            pending = self.components[index].reconfigure in state.pending
            if (tagged.version == "OLD") != pending:
                return False
        active = state.tester_map()
        if not set(active) <= set(self.requirements):
            return False
        for tester in self.requirements.values():
            if tester.role == "old":
                should_be_active = tester.update_action in state.pending
            elif tester.role == "new":
                should_be_active = tester.update_action not in state.pending
            else:
                should_be_active = True
            if (tester.identifier in active) != should_be_active:
                return False
            if tester.identifier in active and active[tester.identifier] not in (
                    set(tester.machine.states) | {-1}):
                return False
        return state.pending <= self.update_actions

    def safe(self, state: Config) -> bool:
        return self.structurally_valid(state) and all(
            residual != -1 for residual in state.tester_map().values())

    def goal_payload(self, state: Config) -> GoalPayload | None:
        if (not self.safe(state) or state.pending
                or any(tagged.version != "NEW" for tagged in state.physical)):
            return None
        active = state.tester_map()
        new_states = tuple(sorted(
            (tester.identifier, active[tester.identifier])
            for tester in self.new_testers))
        payload = (state.physical, new_states)
        return payload if payload in self.quiet_goals else None

    def candidates(self, state: Config) -> list[str]:
        require(self.structurally_valid(state),
                "candidate source is structurally invalid")
        result: set[str] = set()
        for index, tagged in enumerate(state.physical):
            result.update(self.components[index].environment(tagged.version)
                          & self.normal)
        for action in state.pending:
            if not (self.predecessors[action] & state.pending):
                result.add(action)
        return sorted(result)

    def controllable(self, action: str) -> bool:
        return action in self.controllable_normal or action in self.update_actions

    def post(self, state: Config, action: str) -> frozenset[Config]:
        require(self.structurally_valid(state), "Post source is invalid")
        if action in self.normal:
            return self._normal_post(state, action)
        if (action not in self.update_actions or action not in state.pending
                or self.predecessors[action] & state.pending):
            return frozenset()
        for index, component in enumerate(self.components):
            if component.reconfigure == action:
                return self._reconfigure_post(state, action, index)
        for tester in self.old_testers:
            if tester.update_action == action:
                return self._stop_post(state, action, tester)
        for tester in self.new_testers:
            if tester.update_action == action:
                return self._start_post(state, action, tester)
        return frozenset()

    def _step(self, state: Config, action: str,
              excluded: str | None = None) -> tuple[tuple[str, int], ...]:
        requirements = self.requirements
        return tuple(sorted(
            (identifier, requirements[identifier].step(residual, action))
            for identifier, residual in state.testers
            if identifier != excluded))

    def _normal_post(self, state: Config, action: str) -> frozenset[Config]:
        choices: list[list[Tagged]] = []
        participant = False
        for index, tagged in enumerate(state.physical):
            component = self.components[index]
            participant = participant or action in component.environment(
                tagged.version)
            if action in component.alphabet(tagged.version):
                targets = component.successors(
                    tagged.version, tagged.local, action)
                if not targets:
                    return frozenset()
                choices.append([Tagged(tagged.version, target)
                                for target in sorted(targets)])
            else:
                choices.append([tagged])
        if not participant:
            return frozenset()
        products: set[tuple[Tagged, ...]] = {()}
        for values in choices:
            products = {prefix + (value,) for prefix in products
                        for value in values}
        testers = self._step(state, action)
        return frozenset(Config(physical, testers, state.pending)
                         for physical in products)

    def _reconfigure_post(self, state: Config, action: str,
                          index: int) -> frozenset[Config]:
        tagged = state.physical[index]
        if tagged.version != "OLD":
            return frozenset()
        targets = self.components[index].transfer.get(
            tagged.local, frozenset())
        if not targets:
            return frozenset()
        pending = frozenset(set(state.pending) - {action})
        testers = self._step(state, action)
        result: set[Config] = set()
        for target in targets:
            physical = list(state.physical)
            physical[index] = Tagged("NEW", target)
            result.add(Config(tuple(physical), testers, pending))
        return frozenset(result)

    def _stop_post(self, state: Config, action: str,
                   tester: Tester) -> frozenset[Config]:
        if tester.identifier not in state.tester_map():
            return frozenset()
        return frozenset({Config(
            state.physical,
            self._step(state, action, tester.identifier),
            frozenset(set(state.pending) - {action}),
        )})

    def _start_post(self, state: Config, action: str,
                    tester: Tester) -> frozenset[Config]:
        if tester.identifier in state.tester_map():
            return frozenset()
        activation = self.activations[tester.identifier]
        if state.physical not in activation:
            return frozenset()
        stepped = dict(self._step(state, action))
        stepped[tester.identifier] = activation[state.physical]
        return frozenset({Config(
            state.physical,
            tuple(sorted(stepped.items())),
            frozenset(set(state.pending) - {action}),
        )})


def build_block_problem(contract: Contract, block: Sequence[int],
                        old_endpoint: Sequence[Endpoint],
                        new_endpoint: Sequence[Endpoint],
                        normal_owners: Mapping[str, frozenset[int]],
                        update_owners: Mapping[str, frozenset[int]]) -> BlockProblem:
    block_set = set(block)
    block_normal = frozenset(
        action for action, owners in normal_owners.items()
        if owners and set(owners) <= block_set)
    selected_old = [
        tester for tester in contract.old_testers
        if set(tester_support(tester, normal_owners, update_owners)) <= block_set
    ]
    selected_new = [
        tester for tester in contract.new_testers
        if set(tester_support(tester, normal_owners, update_owners)) <= block_set
    ]
    selected_update = [
        tester for tester in contract.update_testers
        if set(tester_support(tester, normal_owners, update_owners)) <= block_set
    ]
    block_update = {contract.components[index].reconfigure for index in block}
    block_update.update(
        tester.update_action for tester in selected_old + selected_new
        if tester.update_action is not None)
    block_common = frozenset(set(block_normal) | block_update)
    old_testers = [projected_tester(tester, block_common)
                   for tester in selected_old]
    new_testers = [projected_tester(tester, block_common)
                   for tester in selected_new]
    update_testers = [projected_tester(tester, block_common)
                      for tester in selected_update]
    observers = block_observers(contract, selected_new, block_normal)
    components = make_components(contract, block, observers, block_normal)

    root_parts = {
        project_endpoint(endpoint, block, components, observers,
                         old_testers, "OLD")
        for endpoint in old_endpoint
    }
    root_physical = {physical for physical, _testers in root_parts}
    closure = physical_closure(components, root_physical, block_normal)
    activations: dict[str, dict[tuple[Tagged, ...], int]] = {}
    observer_local = {observer.index: index
                      for index, observer in enumerate(observers)}
    for tester in new_testers:
        source = contract.activations[tester.identifier]
        table: dict[tuple[Tagged, ...], int] = {}
        for physical in closure:
            if source.mode == "INITIAL":
                target = tester.machine.initial
            else:
                first_observers = physical[0].local.observers
                signature = tuple(
                    first_observers[observer_local[index]]
                    for index in source.observer_indices)
                target = source.mapping.get(signature, -1)
            if target != -1:
                table[physical] = target
        activations[tester.identifier] = table
    for tester in update_testers:
        require(tester.boundary_state != -1,
                f"update tester activates in ERROR: {tester.source_name}")
        activations[tester.identifier] = {
            physical: tester.boundary_state for physical in root_physical
        }

    update_actions = frozenset(block_update)
    direct = {action: set() for action in update_actions}
    for before, after in contract.precedence:
        if before in update_actions or after in update_actions:
            require(before in update_actions and after in update_actions,
                    "cross-block precedence survived partition")
            direct[after].add(before)
    predecessors: dict[str, frozenset[str]] = {}
    for action in update_actions:
        reached: set[str] = set()
        queue = list(direct[action])
        while queue:
            predecessor = queue.pop()
            require(predecessor != action, "precedence is cyclic")
            if predecessor not in reached:
                reached.add(predecessor)
                queue.extend(direct[predecessor])
        predecessors[action] = frozenset(reached)

    ordered_requirements = old_testers + new_testers + update_testers
    roots: set[Config] = set()
    for physical, endpoint_testers in root_parts:
        tester_map = dict(endpoint_testers)
        for tester in update_testers:
            tester_map[tester.identifier] = tester.boundary_state
        roots.add(Config(
            physical,
            tuple(sorted((tester.identifier, tester_map[tester.identifier])
                         for tester in ordered_requirements
                         if tester.identifier in tester_map)),
            update_actions,
        ))

    loadable = loadable_endpoints(contract, new_endpoint)
    full_goals: set[GoalPayload] = set()
    for endpoint in loadable:
        try:
            full_goals.add(project_endpoint(
                endpoint, block, components, observers, new_testers, "NEW"))
        except GenerationError as error:
            if not str(error).startswith("projected endpoint leaves"):
                raise
    quiet_goals: set[GoalPayload] = set()
    for physical, tester_states in full_goals:
        enabled_uc = False
        for action in block_normal - contract.controllable_normal:
            participant = False
            blocked = False
            for index, tagged in enumerate(physical):
                component = components[index]
                if action not in component.environment("NEW"):
                    continue
                participant = True
                if (action in component.new_alphabet
                        and not component.successors("NEW", tagged.local, action)):
                    blocked = True
            if participant and not blocked:
                enabled_uc = True
                break
        if not enabled_uc:
            quiet_goals.add((physical, tester_states))
    require(bool(quiet_goals), "local block has no quiet Goal")
    return BlockProblem(
        tuple(block), components, observers, block_normal,
        contract.controllable_normal & block_normal,
        old_testers, new_testers, update_testers, activations,
        update_actions, predecessors,
        physical_goal_distances(
            components, closure, block_normal,
            (physical for physical, _testers in quiet_goals)),
        frozenset(roots),
        frozenset(full_goals), frozenset(quiet_goals))


def loadable_endpoints(contract: Contract,
                       new_endpoint: Sequence[Endpoint]) -> list[Endpoint]:
    selected = list(new_endpoint)
    if contract.load_mode == "EXPLICIT_REACHABLE_INDEX":
        require(all(index < len(selected) for index in contract.load_indices),
                "load selector index leaves endpoint range")
        selected = [selected[index] for index in contract.load_indices]
    return selected


def physical_payload(physical: Sequence[Tagged]) -> list[dict[str, Any]]:
    return [
        {
            "version": tagged.version,
            "raw_state": tagged.local.raw,
            "observer_states": list(tagged.local.observers),
        }
        for tagged in physical
    ]


def config_payload(state: Config) -> dict[str, Any]:
    # Keep this insertion order: target_keys use the established compact
    # bundle spelling rather than sort-key canonical JSON.
    return {
        "physical": physical_payload(state.physical),
        "active_testers": dict(state.testers),
        "pending_actions": sorted(state.pending),
    }


def config_key(state: Config) -> str:
    return canonical_json(config_payload(state))


def bundle_config_key(state: Config) -> str:
    try:
        return json.dumps(config_payload(state), ensure_ascii=False,
                          separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as error:
        raise GenerationError("configuration is not a target key") from error


def goal_payload_key(payload: GoalPayload) -> str:
    physical, testers = payload
    return canonical_json({
        "physical": physical_payload(physical),
        "new_requirement_states": dict(testers),
    })


def endpoint_projection(endpoint: Endpoint) -> tuple[
        tuple[Local, ...], tuple[tuple[str, int], ...]]:
    return endpoint.locals, tuple(sorted(endpoint.testers))


ObserverPair = tuple[tuple[int, ...], tuple[int, ...]]


def observer_pair_closure(
        global_observers: Sequence[Observer],
        local_observers: Sequence[Observer],
        seeds: Iterable[tuple[int, ...]],
        actions: Iterable[str]) -> frozenset[ObserverPair]:
    require(len(global_observers) == len(local_observers),
            "observer relation arity differs")
    seen: set[ObserverPair] = set()
    queue: deque[ObserverPair] = deque()
    for seed in sorted(set(seeds)):
        require(len(seed) == len(global_observers),
                "observer relation seed arity differs")
        pair = (tuple(seed), tuple(seed))
        if pair not in seen:
            seen.add(pair)
            queue.append(pair)
    while queue:
        global_state, local_state = queue.popleft()
        for action in sorted(actions):
            target = (
                tuple(observer.step(global_state[index], action)
                      for index, observer in enumerate(global_observers)),
                tuple(observer.step(local_state[index], action)
                      for index, observer in enumerate(local_observers)),
            )
            if target not in seen:
                seen.add(target)
                queue.append(target)
    return frozenset(seen)


def activation_residual(source: Activation, tester: Tester,
                        observer_state: tuple[int, ...]) -> int | None:
    if source.mode == "INITIAL":
        return tester.machine.initial
    target = source.mapping.get(observer_state)
    return target if target in tester.machine.states else None


class ProblemGame:
    """Bind one reconstructed local problem to the generic rank interface."""

    def __init__(self, problem: BlockProblem) -> None:
        self.problem = problem
        self.states_by_key: dict[str, Config] = {}

    def roots(self) -> Iterable[Config]:
        return sorted(self.problem.roots, key=config_key)

    def safe(self, state: Config) -> bool:
        return self.problem.safe(state)

    def goal(self, state: Config) -> bool:
        return self.problem.goal_payload(state) is not None

    def rank_lower_bound(self, state: Config) -> int:
        # Normal actions preserve pending and every update removes one member.
        # The relaxed physical distance counts normal + reconfigure edges; all
        # still-OLD components must contribute exactly one reconfigure edge,
        # already counted among pending updates.  Tester/precedence constraints
        # are forgotten, so this remains an admissible conclusion-free bound.
        physical_distance = self.problem.physical_goal_distance.get(
            state.physical)
        if physical_distance is None:
            return 33
        reconfigures = sum(
            component.reconfigure in state.pending
            for component in self.problem.components)
        return (len(state.pending)
                + max(0, physical_distance - reconfigures))

    def candidates(self, state: Config) -> Iterable[str]:
        return self.problem.candidates(state)

    def post(self, state: Config, action: str) -> Iterable[Config]:
        return sorted(self.problem.post(state, action), key=config_key)

    def controllable(self, action: str) -> bool:
        return self.problem.controllable(action)

    def state_payload(self, state: Config) -> Mapping[str, Any]:
        payload = config_payload(state)
        key = canonical_json(payload)
        previous = self.states_by_key.get(key)
        require(previous is None or previous == state,
                "two local states share one semantic key")
        self.states_by_key[key] = state
        return payload

    def action_payload(self, action: str) -> Mapping[str, Any]:
        return {"action": action}

    def action_order_key(self, state: Config,
                         action: str) -> tuple[int, str]:
        # The registered deterministic choice order is pending update first,
        # then concrete action name.  Uncontrollables are never selected by
        # this ordering; the core retains all enabled UC buckets.
        return (0 if action in state.pending else 1, action)


@dataclass(frozen=True)
class GenerationOutcome:
    status: str
    document: Mapping[str, Any]


def _ir_binding(contract: Contract, raw: bytes) -> dict[str, Any]:
    return {
        "sha256": sha256_bytes(raw),
        "size": len(raw),
        "source_name": contract.source_name,
        "source_sha256": contract.source_sha256,
        "definition": contract.definition,
    }


def _generator_boundary() -> dict[str, Any]:
    return {
        "algorithm": ALGORITHM,
        "depth_bound": 32,
        "historical_bundle_consumed": False,
        "supplied_certificate_consumed": False,
        "outcome_fields_consumed": False,
    }


def _inconclusive(binding: Mapping[str, Any], reason: str,
                  block_index: int | None) -> GenerationOutcome:
    return GenerationOutcome("INCONCLUSIVE", {
        "schema_version": INCONCLUSIVE_SCHEMA,
        "generator_boundary": _generator_boundary(),
        "ir_binding": dict(binding),
        "decision": "INCONCLUSIVE",
        "reason": reason,
        "block_index": block_index,
        "loss_claimed": False,
    })


def _goal_row(identifier: str, payload: GoalPayload) -> dict[str, Any]:
    physical, testers = payload
    return {
        "id": identifier,
        "physical": physical_payload(physical),
        "new_requirement_states": dict(testers),
    }


def _serialize_local(block_index: int, problem: BlockProblem,
                     game: ProblemGame, certificate: Any) -> tuple[
                         dict[str, Any], dict[str, GoalPayload]]:
    ordered_states = sorted(certificate.states, key=lambda row: row.key)
    identifiers = {
        state.key: f"q{offset:08d}"
        for offset, state in enumerate(ordered_states)
    }
    retained_keys = set(identifiers)
    require(set(certificate.roots) <= retained_keys,
            "rank certificate root leaves retained domain")

    states: list[dict[str, Any]] = []
    reached_goals: set[GoalPayload] = set()
    for row in ordered_states:
        typed = game.states_by_key.get(row.key)
        require(typed is not None, "rank state lacks a typed configuration")
        goal = problem.goal_payload(typed)
        require(row.safe == problem.safe(typed)
                and row.goal == (goal is not None),
                "core Safe/Goal result differs at serialization")
        if goal is not None:
            reached_goals.add(goal)
        states.append({
            "id": identifiers[row.key],
            "payload": config_payload(typed),
            "rank": row.rank,
            "safe": row.safe,
            "goal": row.goal,
        })

    candidates: list[dict[str, Any]] = []
    for bucket in certificate.candidate_buckets:
        source = game.states_by_key.get(bucket.source_key)
        require(source is not None and bucket.source_key in retained_keys,
                "candidate source leaves retained domain")
        action = text(bucket.action_payload.get("action"),
                      "core candidate action")
        targets: list[str] = []
        for target_key in bucket.target_keys:
            target = game.states_by_key.get(target_key)
            require(target is not None,
                    "candidate target lacks a typed configuration")
            targets.append(bundle_config_key(target))
        candidates.append({
            "source": identifiers[bucket.source_key],
            "action": action,
            "controllable": bucket.controllable,
            "update": action in source.pending,
            "target_keys": sorted(set(targets)),
        })
    candidates.sort(key=lambda row: (row["source"], row["action"]))

    strategies: list[dict[str, Any]] = []
    for bucket in certificate.strategy_buckets:
        action = text(bucket.action_payload.get("action"),
                      "core strategy action")
        require(bucket.source_key in retained_keys
                and set(bucket.target_keys) <= retained_keys,
                "strategy leaves retained rank domain")
        strategies.append({
            "source": identifiers[bucket.source_key],
            "action": action,
            "target_state_ids": sorted(
                identifiers[target] for target in bucket.target_keys),
        })
    strategies.sort(key=lambda row: (row["source"], row["action"]))

    all_quiet = sorted(problem.quiet_goals, key=goal_payload_key)
    goal_identifier = {
        payload: f"block-goal-{offset:08d}"
        for offset, payload in enumerate(all_quiet)
    }
    reached_order = sorted(reached_goals, key=goal_payload_key)
    goal_ids = {goal_identifier[payload]: payload
                for payload in reached_order}
    local = {
        "block_index": block_index,
        "components": list(problem.block),
        "root_state_ids": sorted(identifiers[key]
                                 for key in certificate.roots),
        "states": states,
        "candidate_buckets": candidates,
        "strategy_buckets": strategies,
        "goal_payloads": [
            _goal_row(goal_identifier[payload], payload)
            for payload in reached_order
        ],
        "quiet_goal_keys": [goal_payload_key(payload)
                            for payload in all_quiet],
    }
    return local, goal_ids


def _endpoint_rows(endpoints: Sequence[Endpoint]) -> list[dict[str, Any]]:
    rows = [{
        "controller_state": endpoint.controller,
        "component_raw_states": [local.raw for local in endpoint.locals],
        "observer_states": list(endpoint.locals[0].observers),
        "tester_states": dict(sorted(endpoint.testers)),
    } for endpoint in endpoints]
    return sorted(rows, key=canonical_json)


def _endpoint_declaration(endpoints: Sequence[Endpoint]) -> dict[str, Any]:
    return {
        "count": len(endpoints),
        "semantic_sha256": sha256_bytes(canonical_bytes(
            _endpoint_rows(endpoints))),
    }


def _activation_relations(
        contract: Contract, problems: Sequence[BlockProblem],
        old_endpoint: Sequence[Endpoint]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for block_index, problem in enumerate(problems):
        local_by_global = {
            observer.index: observer for observer in problem.observers
        }
        for tester in sorted(problem.new_testers,
                             key=lambda item: item.identifier):
            source = contract.activations[tester.identifier]
            indices = tuple(source.observer_indices)
            require(all(index in local_by_global for index in indices),
                    "local activation omits a source observer")
            global_observers = [contract.observers[index]
                                for index in indices]
            local_observers = [local_by_global[index] for index in indices]
            seeds = {
                tuple(endpoint.locals[0].observers[index]
                      for index in indices)
                for endpoint in old_endpoint
            }
            pairs = sorted(observer_pair_closure(
                global_observers, local_observers, seeds, contract.normal))
            pair_rows: list[dict[str, Any]] = []
            for global_state, local_state in pairs:
                global_target = activation_residual(
                    source, tester, global_state)
                local_target = activation_residual(
                    source, tester, local_state)
                if local_target is not None:
                    require(local_target == global_target,
                            "local activation quotient differs from source")
                pair_rows.append({
                    "global": list(global_state),
                    "local": list(local_state),
                    "global_residual": global_target,
                    "local_residual": local_target,
                })
            rows.append({
                "block_index": block_index,
                "tester_id": tester.identifier,
                "global_observer_indices": list(indices),
                "pairs": pair_rows,
            })
    return rows


def _observer_relations(
        contract: Contract, problems: Sequence[BlockProblem],
        old_endpoint: Sequence[Endpoint]) -> tuple[
            list[dict[str, Any]],
            list[tuple[tuple[int, ...], frozenset[ObserverPair]]]]:
    rows: list[dict[str, Any]] = []
    typed: list[tuple[tuple[int, ...], frozenset[ObserverPair]]] = []
    for block_index, problem in enumerate(problems):
        indices = tuple(observer.index for observer in problem.observers)
        global_observers = [contract.observers[index] for index in indices]
        seeds = {
            tuple(endpoint.locals[0].observers[index] for index in indices)
            for endpoint in old_endpoint
        }
        pairs = observer_pair_closure(
            global_observers, problem.observers, seeds, contract.normal)
        rows.append({
            "block_index": block_index,
            "global_observer_indices": list(indices),
            "pairs": [
                {"global": list(global_state), "local": list(local_state)}
                for global_state, local_state in sorted(pairs)
            ],
        })
        typed.append((indices, pairs))
    return rows, typed


def _load_selectors(
        contract: Contract, new_endpoint: Sequence[Endpoint]) -> tuple[
            list[dict[str, Any]],
            dict[tuple[tuple[Local, ...], tuple[tuple[str, int], ...]],
                 tuple[str, int]]]:
    loadable = set(loadable_endpoints(contract, new_endpoint))
    rows: list[dict[str, Any]] = []
    selector: dict[
        tuple[tuple[Local, ...], tuple[tuple[str, int], ...]],
        tuple[str, int]
    ] = {}
    for endpoint_index, endpoint in enumerate(new_endpoint):
        if endpoint not in loadable:
            continue
        projection = endpoint_projection(endpoint)
        if projection in selector:
            continue
        identifier = f"new-{endpoint_index:08d}"
        selector[projection] = (identifier, endpoint.controller)
        rows.append({
            "endpoint_id": identifier,
            "controller_state": endpoint.controller,
            "component_raw_states": [local.raw for local in endpoint.locals],
            "observer_states": list(endpoint.locals[0].observers),
            "tester_states": dict(sorted(endpoint.testers)),
        })
    return rows, selector


def _project_loadable_goal(endpoint: Endpoint,
                           problem: BlockProblem) -> GoalPayload | None:
    try:
        return project_endpoint(
            endpoint, problem.block, problem.components, problem.observers,
            problem.new_testers, "NEW")
    except GenerationError as error:
        if str(error).startswith("projected endpoint leaves"):
            return None
        raise


def _verify_quiet_terminal_product(
        problems: Sequence[BlockProblem],
        loadable: Sequence[Endpoint]) -> None:
    choices = [sorted(problem.quiet_goals, key=goal_payload_key)
               for problem in problems]
    require(all(choices), "quiet terminal product has an empty factor")
    expected = set(product(*choices))
    actual: set[tuple[GoalPayload, ...]] = set()
    for endpoint in loadable:
        projected: list[GoalPayload] = []
        for problem in problems:
            payload = _project_loadable_goal(endpoint, problem)
            if payload is None or payload not in problem.quiet_goals:
                break
            projected.append(payload)
        if len(projected) == len(problems):
            actual.add(tuple(projected))
    require(actual == expected,
            "quiet Goal product differs from loadable endpoint projection")


def _terminal_assemblies(
        contract: Contract, problems: Sequence[BlockProblem],
        goal_ids: Sequence[Mapping[str, GoalPayload]],
        relations: Sequence[
            tuple[tuple[int, ...], frozenset[ObserverPair]]],
        selector: Mapping[
            tuple[tuple[Local, ...], tuple[tuple[str, int], ...]],
            tuple[str, int]]) -> list[dict[str, Any]]:
    choices = [sorted(mapping.items()) for mapping in goal_ids]
    require(all(choices), "certificate has no retained local Goal")
    expected_new_testers = {
        tester.identifier for tester in contract.new_testers
    }
    rows: list[dict[str, Any]] = []
    for terminal_index, terminal in enumerate(product(*choices)):
        global_observers: list[int | None] = [None] * len(contract.observers)
        for block_index, (_identifier, payload) in enumerate(terminal):
            indices, pairs = relations[block_index]
            local_observers = payload[0][0].local.observers
            fiber = {global_state for global_state, local_state in pairs
                     if local_state == local_observers}
            require(len(fiber) == 1,
                    "terminal observer fibre is not singleton")
            values = next(iter(fiber))
            for offset, global_index in enumerate(indices):
                previous = global_observers[global_index]
                require(previous is None or previous == values[offset],
                        "terminal observer fibres disagree")
                global_observers[global_index] = values[offset]
        require(all(value is not None for value in global_observers),
                "terminal observer fibres do not cover the registry")
        concrete_observers = tuple(int(value) for value in global_observers)

        concrete_locals: list[Local | None] = [None] * len(contract.components)
        tester_states: dict[str, int] = {}
        local_ids: list[str] = []
        for block_index, (identifier, payload) in enumerate(terminal):
            local_ids.append(identifier)
            physical, local_testers = payload
            problem = problems[block_index]
            require(len(physical) == len(problem.block),
                    "terminal physical arity differs")
            for offset, tagged in enumerate(physical):
                require(tagged.version == "NEW",
                        "terminal contains an OLD component")
                global_index = problem.block[offset]
                observers = concrete_observers if global_index == 0 else ()
                concrete_locals[global_index] = Local(
                    tagged.local.raw, tuple(observers))
            for tester_id, residual in local_testers:
                require(tester_id not in tester_states,
                        "new tester belongs to multiple blocks")
                tester_states[tester_id] = residual
        require(all(local is not None for local in concrete_locals),
                "terminal partition omits a component")
        require(set(tester_states) == expected_new_testers,
                "terminal partition omits a new tester")
        projection = (
            tuple(local for local in concrete_locals if local is not None),
            tuple(sorted(tester_states.items())),
        )
        require(projection in selector,
                "certificate terminal is outside loadable Goal")
        endpoint_id, controller_state = selector[projection]
        rows.append({
            "terminal_tuple_index": terminal_index,
            "observer_fiber_index": 0,
            "local_goal_signature_ids": local_ids,
            "global_observer_states": list(concrete_observers),
            "endpoint_id": endpoint_id,
            "controller_state": controller_state,
        })
    return rows


def generate(ir: Mapping[str, Any], raw: bytes,
             limits: SynthesisLimits = SynthesisLimits()) -> GenerationOutcome:
    """Generate one deterministic certificate or bounded INCONCLUSIVE row."""
    require(limits.max_rank == 32,
            "generated-certificate depth bound must be exactly 32")
    contract = parse_contract(ir)
    binding = _ir_binding(contract, raw)
    block_index: int | None = None
    try:
        old_endpoint = build_global_endpoint_direct(
            contract, contract.old_testers, "OLD")
        new_endpoint = build_global_endpoint_direct(
            contract, contract.new_testers, "NEW")
        partition, normal_owners, update_owners = dependency_partition(contract)

        problems: list[BlockProblem] = []
        locals_: list[dict[str, Any]] = []
        local_goal_ids: list[dict[str, GoalPayload]] = []
        for block_index, block in enumerate(partition):
            problem = build_block_problem(
                contract, block, old_endpoint, new_endpoint,
                normal_owners, update_owners)
            game = ProblemGame(problem)
            result = synthesize_strong_rank(game, limits)
            if not result.is_win:
                return _inconclusive(binding, result.reason, block_index)
            require(result.certificate is not None,
                    "successful rank synthesis omitted its certificate")
            local, goals = _serialize_local(
                block_index, problem, game, result.certificate)
            problems.append(problem)
            locals_.append(local)
            local_goal_ids.append(goals)

        loadable = loadable_endpoints(contract, new_endpoint)
        _verify_quiet_terminal_product(problems, loadable)
        activation_rows = _activation_relations(
            contract, problems, old_endpoint)
        observer_rows, relations = _observer_relations(
            contract, problems, old_endpoint)
        load_rows, selector = _load_selectors(contract, new_endpoint)
        terminal_rows = _terminal_assemblies(
            contract, problems, local_goal_ids, relations, selector)
        certificate = {
            "schema_version": CERT_SCHEMA,
            "generator_boundary": _generator_boundary(),
            "ir_binding": binding,
            "decision": "WIN",
            "component_partition": partition,
            "endpoints": {
                "old": _endpoint_declaration(old_endpoint),
                "new": _endpoint_declaration(new_endpoint),
            },
            "locals": locals_,
            "transport": {
                "activation_relations": activation_rows,
                "observer_relations": observer_rows,
                "load_selectors": load_rows,
                "terminal_assemblies": terminal_rows,
            },
        }
        return GenerationOutcome("WIN", certificate)
    except MemoryError:
        return _inconclusive(binding, "MEMORY_EXHAUSTED", block_index)


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise GenerationError("invalid arguments: " + message)


def _write_exclusive(path: Path, raw: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(raw)
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def main(argv: Sequence[str] | None = None) -> int:
    try:
        parser = _ArgumentParser()
        parser.add_argument("--ir", type=Path, required=True)
        parser.add_argument("--output", type=Path, required=True)
        parser.add_argument("--max-states", type=int, default=2_000_000)
        parser.add_argument("--max-candidate-buckets", type=int,
                            default=20_000_000)
        parser.add_argument("--max-outcomes", type=int, default=40_000_000)
        parser.add_argument("--timeout-seconds", type=float, default=600.0)
        args = parser.parse_args(argv)
        limits = SynthesisLimits(
            max_rank=32,
            max_states=args.max_states,
            max_candidate_buckets=args.max_candidate_buckets,
            max_outcomes=args.max_outcomes,
            timeout_seconds=args.timeout_seconds,
        )
        ir, raw = load_strict(args.ir)
        outcome = generate(ir, raw, limits)
        _write_exclusive(args.output, canonical_bytes(outcome.document))
        if outcome.status == "WIN":
            return 0
        print("POST_FRONTEND_WIN_SYNTHESIS_INCONCLUSIVE=" +
              text(outcome.document["reason"], "inconclusive reason"),
              file=sys.stderr)
        return 2
    except MemoryError:
        print("POST_FRONTEND_WIN_SYNTHESIS_INCONCLUSIVE=MEMORY_EXHAUSTED",
              file=sys.stderr)
        return 2
    except Exception as error:
        print("POST_FRONTEND_WIN_SYNTHESIS_INVALID=" + str(error),
              file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
