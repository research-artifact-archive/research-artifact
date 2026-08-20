#!/usr/bin/env python3
"""Independent post-frontend contract-to-certificate semantic verifier.

The input IR is emitted after MTSA parsing/composition, safety compilation,
and fixed old/new controller synthesis, but before endpoint products,
activation closure, Goal construction, local games, solving, or certificate
construction.  This module uses only the Python standard library.  It does
not import the Java factorizer/adapter/solver, the historical bundle checker,
or another FG-DUCS successor implementation.

The verifier reconstructs fixed endpoints, local projections, activation
guards, loadable quiet Goals, candidates, and complete Post for every state in
a supplied winning-rank certificate.  It verifies the certificate but does
not synthesize a winning region and does not parse ordinary .lts source.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict, deque
from dataclasses import dataclass
from itertools import product
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


IR_SCHEMA = "fg-ducs-post-frontend-contract-facts-v1"
BUNDLE_SCHEMA = "fg-ducs-native-tier-a-result-v4"
REPORT_SCHEMA = "fg-ducs-post-frontend-certificate-check-v1"
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
    "solve_status", "winning", "losing", "certificate", "strategy",
    "rank", "witness", "proof", "local_game", "endpoint_product",
    "owner_sets", "action_owners", "candidate_buckets",
    "strategy_buckets", "terminal_assemblies",
}
BUNDLE_ROOT_KEYS = {
    "schema_version", "source_name", "source_sha256", "definition",
    "extraction_status", "claim_scope", "strategy_model", "goal_policy",
    "factorization_stage", "fixed_endpoint_products_materialized",
    "factor_status", "solve_status", "global_mixed_game_materialized",
    "global_mixed_state_count", "global_mixed_post_query_count",
    "old_endpoint_state_count", "new_endpoint_state_count",
    "terminal_product_verified", "arbiter", "transport",
    "component_partition", "dependency_receipts", "locals",
    "local_solver_discovered_states_sum",
    "local_solver_successor_queries_sum", "local_solver_outcomes_sum",
}
BUNDLE_LOCAL_KEYS = {
    "block_index", "components", "full_goal_count", "quiet_terminal_count",
    "full_goal_uncontrollable_actions", "decision",
    "solver_discovered_states", "solver_successor_queries", "solver_outcomes",
    "certificate_initial_count", "certificate_rank_count",
    "certificate_strategy_source_count", "certificate_strategy_bucket_count",
    "certificate_goal_match_count", "proof", "independent_certificate_valid",
    "independent_certificate_basis", "independent_certificate_states",
    "independent_certificate_queries", "independent_certificate_outcomes",
    "independent_certificate_elapsed_ms",
}


class CheckError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CheckError(message)


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
    result = [exact_int(item, f"{label}[]", minimum) for item in array(value, label)]
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


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise CheckError(f"invalid strict JSON: {path}") from error
    return object_(value, "JSON root")


def canonical_text(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as error:
        raise CheckError("non-canonical JSON value") from error


def canonical_bytes(value: Any) -> bytes:
    return (canonical_text(value) + "\n").encode("utf-8")


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

    def has_action(self, action: str) -> bool:
        return action in self.alphabet

    def targets(self, state: int, action: str) -> frozenset[int]:
        return self.post.get((state, action), frozenset())

    def deterministic(self, state: int, action: str, *, missing_error: bool) -> int:
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
        target = next(iter(targets))
        require(target == -1 or target in self.states,
                f"{self.name} target leaves state space")
        return target


def compact_machine(value: Any, label: str) -> Machine:
    row = object_(value, label)
    exact_keys(row, {"name", "max_states", "alphabet", "transitions",
                     "initial_state"}, label)
    name = text(row["name"], f"{label}.name")
    maximum = exact_int(row["max_states"], f"{label}.max_states", 1)
    initial = exact_int(row["initial_state"], f"{label}.initial_state", 0)
    require(initial == 0 and initial < maximum,
            f"{label} compact initial state differs from zero")
    alphabet = strings(row["alphabet"], f"{label}.alphabet")
    transitions: dict[tuple[int, str], frozenset[int]] = {}
    last: tuple[int, int] | None = None
    for offset, raw in enumerate(array(row["transitions"], f"{label}.transitions")):
        edge = object_(raw, f"{label}.transitions[{offset}]")
        exact_keys(edge, {"source", "action_index", "targets"}, "compact edge")
        source = exact_int(edge["source"], "compact edge source", 0)
        action_index = exact_int(edge["action_index"], "compact action index", 0)
        require(source < maximum and action_index < len(alphabet),
                f"{label} edge declaration leaves domain")
        order = (source, action_index)
        require(last is None or order > last, f"{label} edges are not canonical")
        last = order
        action = alphabet[action_index]
        require(not action.endswith("?"), f"modal action in {label}")
        targets = integers(edge["targets"], "compact targets", minimum=-1)
        require(bool(targets) and all(target == -1 or target < maximum for target in targets),
                f"{label} target leaves state space")
        key = (source, action)
        require(key not in transitions, f"duplicate compact edge in {label}")
        transitions[key] = frozenset(targets)
    return Machine(name, initial, tuple(range(maximum)), tuple(alphabet), transitions)


def controller_machine(value: Any, label: str) -> Machine:
    row = object_(value, label)
    exact_keys(row, {"initial_state", "states", "actions",
                     "required_transitions", "maybe_transition_count"}, label)
    require(exact_int(row["maybe_transition_count"], "maybe count", 0) == 0,
            f"{label} has MAYBE transitions")
    states = integers(row["states"], f"{label}.states", minimum=-1)
    initial = exact_int(row["initial_state"], f"{label}.initial", -1)
    require(initial in states and initial != -1, f"{label} initial is invalid")
    actions = strings(row["actions"], f"{label}.actions", sorted_unique=True)
    transitions: dict[tuple[int, str], frozenset[int]] = {}
    last: tuple[int, str] | None = None
    for offset, raw in enumerate(array(row["required_transitions"],
                                       f"{label}.required_transitions")):
        edge = object_(raw, f"{label}.edge[{offset}]")
        exact_keys(edge, {"source", "action", "targets"}, "controller edge")
        source = exact_int(edge["source"], "controller source", -1)
        action = text(edge["action"], "controller action")
        targets = integers(edge["targets"], "controller targets", minimum=-1)
        require(source in states and action in actions and bool(targets)
                and set(targets) <= set(states), f"{label} edge leaves domain")
        key = (source, action)
        require(last is None or key > last, f"{label} edges are not canonical")
        last = key
        require(key not in transitions, f"duplicate controller edge in {label}")
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
        identifiers = [identifier for identifier, _residual in self.testers]
        require(len(identifiers) == len(set(identifiers)),
                "configuration repeats an active tester")
        # Active testers are a finite map.  Bundle JSON objects are key-sorted,
        # while the independently reconstructed transition rules naturally
        # visit old/new/update requirements by semantic role.  Canonicalize the
        # map at the typed boundary so ordering cannot affect state identity.
        object.__setattr__(self, "testers", tuple(sorted(self.testers)))

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
        if action not in self.alphabet:
            return state
        return self.machine.deterministic(state, action, missing_error=True)

    def effective_actions(self) -> frozenset[str]:
        return frozenset(
            action for action in self.alphabet
            if any(self.step(state, action) != state for state in self.machine.states)
        )


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
        target = self.machine.deterministic(state, action, missing_error=False)
        require(target != -1, f"observer reaches ERROR: {self.name}")
        return target

    def effective_actions(self) -> frozenset[str]:
        return frozenset(
            action for action in self.alphabet
            if any(self.step(state, action) != state for state in self.machine.states)
        )


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

    def successors(self, version: str, state: Local, action: str) -> frozenset[Local]:
        table = self.old_post if version == "OLD" else self.new_post
        return table.get((state, action), frozenset())


@dataclass(frozen=True)
class Activation:
    mode: str
    observer_global_indices: tuple[int, ...]
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
    old_to_stop: dict[str, str]
    new_to_start: dict[str, str]
    load_mode: str
    load_indices: tuple[int, ...]


def parse_contract(value: Mapping[str, Any]) -> Contract:
    exact_keys(value, IR_ROOT_KEYS, "IR root")
    reject_ir_conclusions(value)
    require(value.get("schema_version") == IR_SCHEMA, "IR schema differs")
    require(value.get("evidence_scope") ==
            "shared_mtsa_post_frontend_conclusion_free_contract",
            "IR evidence scope differs")
    require(value.get("extraction_stage") ==
            "AFTER_FIXED_ENDPOINT_CONTROLLER_SYNTHESIS_BEFORE_ENDPOINT_PRODUCT",
            "IR extraction stage differs")
    for field in (
        "fixed_endpoint_products_materialized", "physical_closure_materialized",
        "activation_relations_materialized", "goal_signatures_materialized",
        "local_update_games_materialized", "global_mixed_game_materialized",
        "dependency_partition_materialized", "winning_certificate_materialized",
        "source_to_witness_replay", "conclusion_fields_present",
    ):
        require(value.get(field) is False, f"IR boundary flag differs: {field}")
    require(value.get("old_new_controller_synthesis_performed") is True,
            "controller synthesis boundary differs")
    require(value.get("shared_mtsa_frontend") is True
            and value.get("independent_source_frontend") is False,
            "frontend provenance boundary differs")
    flags = object_(value.get("flags"), "IR flags")
    expected_flags = {
        "on_the_fly": True, "revised_on_the_fly": True,
        "fine_grained": True, "selective": False,
        "direct_transfer_relations": True,
    }
    exact_keys(flags, expected_flags, "IR flags")
    for field, expected in expected_flags.items():
        require(exact_bool(flags[field], f"IR flag {field}") is expected,
                f"unsupported IR declaration profile: {field}")
    source_name = text(value.get("source_name"), "source name")
    source_sha = text(value.get("source_sha256"), "source SHA")
    require(len(source_sha) == 64 and all(c in "0123456789abcdef" for c in source_sha),
            "source SHA is invalid")
    definition = text(value.get("definition"), "definition")

    raw_components = array(value.get("components"), "components")
    require(bool(raw_components), "components are empty")
    components: list[ComponentDecl] = []
    for index, raw in enumerate(raw_components):
        row = object_(raw, f"components[{index}]")
        exact_keys(row, {
            "index", "old_machine", "new_machine", "transfer_relation",
            "transfer_has_action_sequence", "reconfigure_action",
        }, f"components[{index}]")
        require(exact_int(row.get("index"), "component index", 0) == index,
                "component order differs")
        old = compact_machine(row.get("old_machine"), f"component {index} old")
        new = compact_machine(row.get("new_machine"), f"component {index} new")
        require(row.get("transfer_has_action_sequence") is False,
                "action-sequence transfer is unsupported")
        transfer: dict[int, frozenset[int]] = {}
        previous_transfer_source: int | None = None
        for offset, raw_transfer in enumerate(array(row.get("transfer_relation"),
                                                     "transfer relation")):
            edge = object_(raw_transfer, f"transfer[{offset}]")
            exact_keys(edge, {"source", "targets"}, "transfer row")
            source = exact_int(edge["source"], "transfer source", 0)
            require(previous_transfer_source is None
                    or source > previous_transfer_source,
                    "transfer rows are not canonical")
            previous_transfer_source = source
            targets = integers(edge["targets"], "transfer targets", minimum=0)
            require(source in old.states and set(targets) <= set(new.states)
                    and bool(targets), "transfer leaves component state domain")
            require(source not in transfer, "duplicate transfer source")
            transfer[source] = frozenset(targets)
        components.append(ComponentDecl(index, old, new, transfer,
                                        text(row.get("reconfigure_action"), "reconfigure")))

    normal = set()
    for component in components:
        normal.update(component.old.alphabet)
        normal.update(component.new.alphabet)
    # Match the adapter's CompactState -> required-LTS import.  LTSA keeps
    # modal companion labels (``a?``) and ``tau`` in the raw alphabet even
    # though AutomataToMTSConverter does not expose them as required endpoint
    # actions.  They remain present in the conclusion-free IR, but are not
    # part of the endpoint decision alphabet.
    normal = {action for action in normal
              if action not in BOUNDARY and not action.endswith("?")}
    controllable = set(strings(value.get("controllable_actions"),
                               "controllable actions", sorted_unique=True))
    controllable_normal = frozenset(controllable & normal)

    protocol = object_(value.get("protocol"), "protocol")
    exact_keys(protocol, {
        "progress_actions_in_index_order", "stop_old_actions",
        "reconfigure_actions", "start_new_actions",
        "old_safety_to_stop_action", "new_safety_to_start_action",
        "action_to_mapping_indices", "precedence",
    }, "protocol")
    progress = tuple(strings(protocol.get("progress_actions_in_index_order"),
                             "progress actions"))
    stop_actions = strings(protocol.get("stop_old_actions"),
                           "stop actions", sorted_unique=True)
    reconfigure_actions = strings(protocol.get("reconfigure_actions"),
                                  "reconfigure actions", sorted_unique=True)
    start_actions = strings(protocol.get("start_new_actions"),
                            "start actions", sorted_unique=True)
    old_to_stop = {text(k, "old safety key"): text(v, "old stop")
                   for k, v in object_(protocol.get("old_safety_to_stop_action"),
                                       "old safety map").items()}
    new_to_start = {text(k, "new safety key"): text(v, "new start")
                    for k, v in object_(protocol.get("new_safety_to_start_action"),
                                        "new safety map").items()}
    precedence: list[tuple[str, str]] = []
    for edge in array(protocol.get("precedence"), "precedence"):
        item = object_(edge, "precedence edge")
        exact_keys(item, {"before", "after"}, "precedence edge")
        precedence.append((text(item["before"], "precedence before"),
                           text(item["after"], "precedence after")))
    require(precedence == sorted(set(precedence)), "precedence is not canonical")
    expected_reconfigure = [component.reconfigure for component in components]
    require(len(expected_reconfigure) == len(set(expected_reconfigure)),
            "concrete reconfigure action is shared by components")
    require(reconfigure_actions == sorted(expected_reconfigure),
            "protocol reconfigure action census differs")
    require(stop_actions == sorted(old_to_stop.values())
            and start_actions == sorted(new_to_start.values()),
            "protocol stop/start action census differs")
    concrete = set(stop_actions) | set(reconfigure_actions) | set(start_actions)
    require(len(concrete) == len(stop_actions) + len(reconfigure_actions)
            + len(start_actions), "concrete update action is not unique")
    require(set(progress) == concrete and len(progress) == len(concrete),
            "progress action census differs from concrete update actions")
    require(not (concrete & normal),
            "normal/update action namespaces overlap")
    require(concrete <= controllable,
            "a concrete update action is not controllable")
    expected_mapping_rows = [
        {"action": component.reconfigure, "mapping_indices": [component.index]}
        for component in components
    ]
    expected_mapping_rows.sort(key=lambda item: item["action"])
    typed_mapping_rows: list[dict[str, Any]] = []
    for raw in array(protocol.get("action_to_mapping_indices"),
                     "action-to-mapping rows"):
        mapping_row = object_(raw, "action-to-mapping row")
        exact_keys(mapping_row, {"action", "mapping_indices"},
                   "action-to-mapping row")
        typed_mapping_rows.append({
            "action": text(mapping_row["action"], "mapping action"),
            "mapping_indices": integers(mapping_row["mapping_indices"],
                                         "mapping indices"),
        })
    require(typed_mapping_rows == expected_mapping_rows,
            "action-to-mapping binding differs")
    common = normal | set(progress)

    def parse_tester_group(field: str, role: str,
                           updates: Mapping[str, str]) -> list[Tester]:
        machines = [compact_machine(item, f"{field}[{index}]")
                    for index, item in enumerate(array(value.get(field), field))]
        require([machine.name for machine in machines] ==
                sorted(machine.name for machine in machines),
                f"{field} is not name sorted")
        require(len({machine.name for machine in machines}) == len(machines),
                f"{field} repeats a name")
        result: list[Tester] = []
        for ordinal, machine in enumerate(machines):
            require(all(not machine.targets(state, "tau")
                        for state in machine.states),
                    f"tester has tau transition: {machine.name}")
            local = frozenset(action for action in machine.alphabet
                              if action not in BOUNDARY and not action.startswith("@"))
            require(local <= common, f"tester action leaves common alphabet: {machine.name}")
            identifier = f"{role}:{machine.name}:{ordinal}"
            update = updates.get(machine.name)
            if role in {"old", "new"}:
                require(update is not None, f"tester update action is absent: {machine.name}")
            boundary = machine.deterministic(machine.initial, "hotSwapIn",
                                             missing_error=True)
            result.append(Tester(identifier, machine.name, role, machine,
                                 local, update, boundary))
        return result

    old_testers = parse_tester_group("old_safety_machines", "old", old_to_stop)
    new_testers = parse_tester_group("new_safety_machines", "new", new_to_start)
    update_testers = parse_tester_group("transition_requirement_machines",
                                        "update_time", {})
    require(set(old_to_stop) == {tester.source_name for tester in old_testers}
            and set(new_to_start) == {
                tester.source_name for tester in new_testers
            }, "safety/update-action binding census differs")

    observer_rows = array(value.get("observer_registry"), "observer registry")
    observers: list[Observer] = []
    for index, raw in enumerate(observer_rows):
        row = object_(raw, f"observer[{index}]")
        exact_keys(row, {"id", "index", "name", "machine"}, "observer row")
        require(exact_int(row["index"], "observer index", 0) == index,
                "observer index differs")
        machine = compact_machine(row["machine"], f"observer {index} machine")
        name = text(row["name"], "observer name")
        require(machine.name == name, "observer name/machine differs")
        require(all(not machine.targets(state, "tau")
                    for state in machine.states),
                f"observer has tau transition: {name}")
        observers.append(Observer(text(row["id"], "observer id"), index, name,
                                  machine, frozenset(set(machine.alphabet) & normal)))
    require([observer.name for observer in observers] ==
            sorted(observer.name for observer in observers),
            "observer registry is not name sorted")
    require(len({observer.name for observer in observers}) == len(observers),
            "observer registry repeats a name")
    inherited_observers = [
        compact_machine(raw, f"observer_machines[{index}]")
        for index, raw in enumerate(array(value.get("observer_machines"),
                                           "observer machines"))
    ]
    require(inherited_observers == [observer.machine for observer in observers],
            "observer registry differs from inherited observer machines")

    activation_rows = array(value.get("new_activation_sources"),
                            "new activation sources")
    activations: dict[str, Activation] = {}
    for offset, raw in enumerate(activation_rows):
        row = object_(raw, f"activation[{offset}]")
        exact_keys(row, {"new_requirement_id", "safety_machine", "mode",
                         "ordered_observer_indices", "ordered_observer_ids",
                         "mapping_rows"}, "activation row")
        identifier = text(row["new_requirement_id"], "activation requirement id")
        require(identifier == new_testers[offset].identifier,
                "activation/new tester order differs")
        require(row["safety_machine"] == new_testers[offset].source_name,
                "activation safety name differs")
        indices = tuple(integers(row["ordered_observer_indices"],
                                 "activation observer indices", minimum=0,
                                 sorted_unique=False))
        ids = strings(row["ordered_observer_ids"], "activation observer ids")
        require(len(indices) == len(ids) and all(index < len(observers)
                                                for index in indices),
                "activation observer census differs")
        require(ids == [observers[index].identifier for index in indices],
                "activation observer ids differ")
        mode = text(row["mode"], "activation mode")
        require(mode in {"INITIAL", "OBSERVER_MAPPING"},
                "activation mode is invalid")
        mapping: dict[tuple[int, ...], int] = {}
        for mapping_raw in array(row["mapping_rows"], "activation mapping rows"):
            mapping_row = object_(mapping_raw, "activation mapping row")
            exact_keys(mapping_row, {"observer_state_tuple", "tester_state"},
                       "activation mapping row")
            signature = tuple(integers(mapping_row["observer_state_tuple"],
                                       "observer tuple", minimum=0,
                                       sorted_unique=False))
            target = exact_int(mapping_row["tester_state"], "mapped tester state", -1)
            require(len(signature) == len(indices)
                    and target in set(new_testers[offset].machine.states) | {-1},
                    "activation mapping leaves domain")
            require(signature not in mapping, "duplicate activation tuple")
            mapping[signature] = target
        require((mode == "INITIAL" and not indices and not mapping)
                or (mode == "OBSERVER_MAPPING" and bool(indices) and bool(mapping)),
                "activation mode payload differs")
        activations[identifier] = Activation(mode, indices, mapping)

    controller_row = object_(value.get("controllers"), "controllers")
    exact_keys(controller_row, {"old", "new"}, "controllers")
    controllers = {
        "OLD": controller_machine(controller_row["old"], "old controller"),
        "NEW": controller_machine(controller_row["new"], "new controller"),
    }
    for version, controller in controllers.items():
        environment = set().union(*(
            set(component.old.alphabet if version == "OLD" else component.new.alphabet)
            for component in components
        )) & normal
        require(environment <= set(controller.alphabet),
                f"{version} controller omits an environment action")
        for (_state, action) in controller.post:
            require(action in normal,
                    f"{version} controller has a non-normal transition")

    load = object_(value.get("load_selector"), "load selector")
    exact_keys(load, {"mode", "reachable_indices"}, "load selector")
    load_mode = text(load["mode"], "load mode")
    require(load_mode in {"ALL_REACHABLE", "EXPLICIT_REACHABLE_INDEX"},
            "load mode is invalid")
    load_indices = tuple(integers(load["reachable_indices"], "load indices", minimum=0))
    require((load_mode == "ALL_REACHABLE" and not load_indices)
            or (load_mode == "EXPLICIT_REACHABLE_INDEX" and bool(load_indices)),
            "load selector payload differs")
    boundary = object_(value.get("boundary_actions"), "boundary actions")
    require(boundary == {"hot_swap_in": "hotSwapIn", "hot_swap_out": "hotSwapOut"},
            "boundary action declarations differ")
    return Contract(source_name, source_sha, definition, components, controllers,
                    observers, old_testers, new_testers, update_testers,
                    activations, frozenset(normal), controllable_normal,
                    progress, tuple(precedence), old_to_stop, new_to_start,
                    load_mode, load_indices)


def machine_lts(machine: Machine, actions: Iterable[str]) -> tuple[
        frozenset[Local], frozenset[str], dict[tuple[Local, str], frozenset[Local]]]:
    kept = frozenset(set(machine.alphabet) & set(actions))
    states = frozenset(Local(state) for state in machine.states)
    post: dict[tuple[Local, str], frozenset[Local]] = {}
    for state in states:
        for action in kept:
            targets = machine.targets(state.raw, action)
            require(all(target >= 0 for target in targets),
                    f"physical component reaches ERROR: {machine.name}")
            if targets:
                post[(state, action)] = frozenset(Local(target) for target in targets)
    return states, kept, post


def augmented_lts(machine: Machine, observers: Sequence[Observer],
                  normal: frozenset[str], seeds: Iterable[Local]) -> tuple[
        frozenset[Local], frozenset[str], dict[tuple[Local, str], frozenset[Local]]]:
    alphabet = frozenset((set(machine.alphabet)
                          | set().union(*(set(observer.alphabet) for observer in observers)))
                         & set(normal))
    discovered: set[Local] = set()
    queue: deque[Local] = deque()
    for seed in seeds:
        require(seed.raw in machine.states and len(seed.observers) == len(observers),
                "augmented seed leaves state domain")
        if seed not in discovered:
            discovered.add(seed)
            queue.append(seed)
    post: dict[tuple[Local, str], frozenset[Local]] = {}
    while queue:
        source = queue.popleft()
        for action in sorted(alphabet):
            if machine.has_action(action):
                raw_targets = machine.targets(source.raw, action)
                if not raw_targets:
                    continue
                require(all(target >= 0 for target in raw_targets),
                        f"augmented component reaches ERROR: {machine.name}")
            else:
                raw_targets = frozenset({source.raw})
            observer_target = tuple(observer.step(source.observers[index], action)
                                    for index, observer in enumerate(observers))
            targets = frozenset(Local(target, observer_target) for target in raw_targets)
            post[(source, action)] = targets
            for target in targets:
                if target not in discovered:
                    discovered.add(target)
                    queue.append(target)
    return frozenset(discovered), alphabet, post


def make_components(contract: Contract, block: Sequence[int],
                    observers: Sequence[Observer], block_normal: frozenset[str]) -> list[LocalComponent]:
    result: list[LocalComponent] = []
    initial_observers = tuple(observer.machine.initial for observer in observers)
    for local_index, global_index in enumerate(block):
        declaration = contract.components[global_index]
        old_environment = frozenset(set(declaration.old.alphabet) & set(block_normal))
        new_environment = frozenset(set(declaration.new.alphabet) & set(block_normal))
        if local_index == 0:
            old_seed = Local(declaration.old.initial, initial_observers)
            old_states, old_alphabet, old_post = augmented_lts(
                declaration.old, observers, block_normal, [old_seed])
            new_seeds = {Local(declaration.new.initial, initial_observers)}
            for old_state in old_states:
                for target in declaration.transfer.get(old_state.raw, frozenset()):
                    new_seeds.add(Local(target, old_state.observers))
            new_states, new_alphabet, new_post = augmented_lts(
                declaration.new, observers, block_normal, new_seeds)
            transfer = {
                old_state: frozenset(Local(target, old_state.observers)
                                     for target in declaration.transfer.get(old_state.raw, frozenset()))
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
        result.append(LocalComponent(global_index, old_states, new_states,
                                     old_alphabet, new_alphabet,
                                     old_environment, new_environment,
                                     old_post, new_post, transfer,
                                     declaration.reconfigure))
    return result


def global_components(contract: Contract) -> list[LocalComponent]:
    return make_components(contract, list(range(len(contract.components))),
                           contract.observers, contract.normal)


def product_post(components: Sequence[LocalComponent], states: Sequence[Local],
                 version: str, action: str, *, endpoint: bool) -> set[tuple[Local, ...]]:
    choices: list[list[Local]] = []
    participant = False
    for index, component in enumerate(components):
        if endpoint:
            participates = action in component.alphabet(version)
        else:
            participates = action in component.environment(version)
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
    initial_locals = tuple(min(component.states(version),
                               key=lambda value: (value.raw, value.observers))
                           for component in components)
    # The augmented initial is always raw initial plus observer initials; raw
    # components have a single empty-observer initial with the declared id.
    fixed_initial: list[Local] = []
    for index, component in enumerate(components):
        raw_initial = contract.components[index].old.initial if version == "OLD" \
            else contract.components[index].new.initial
        candidates = [state for state in component.states(version)
                      if state.raw == raw_initial]
        fixed_initial.append(min(candidates, key=lambda value: value.observers))
    initial = Endpoint(controller.initial, tuple(fixed_initial),
                       tuple((tester.identifier, tester.machine.initial)
                             for tester in testers))
    actions = sorted(contract.normal)
    discovered: list[Endpoint] = [initial]
    seen = {initial}
    queue: deque[Endpoint] = deque([initial])
    while queue:
        state = queue.popleft()
        tester_map = state.tester_map()
        enabled = False
        for action in actions:
            controller_targets = controller.targets(state.controller, action)
            physical_targets = product_post(components, state.locals, version,
                                            action, endpoint=True)
            # The augmented first component also carries observer-only
            # actions.  Those actions participate in the concrete endpoint
            # product, but they are not physical environment moves and hence
            # do not impose an uncontrollable-preservation obligation.  Replay
            # the factorizer's separate environment-participation projection
            # before comparing it with an enabled controller transition.
            environment_targets = product_post(
                components, state.locals, version, action, endpoint=False)
            if controller_targets and physical_targets:
                require(physical_targets == environment_targets,
                        f"{version} endpoint does not preserve every "
                        f"environment outcome at reachable state: "
                        f"controller={state.controller}, action={action}")
            if (environment_targets
                    and action not in contract.controllable_normal):
                require(bool(controller_targets),
                        f"{version} controller disables an uncontrollable "
                        f"environment action at reachable state: "
                        f"controller={state.controller}, action={action}")
            if not controller_targets:
                continue
            if not physical_targets:
                continue
            enabled = True
            tester_targets = tuple(
                (tester.identifier, tester.step(tester_map[tester.identifier], action))
                for tester in testers
            )
            require(all(target != -1 for _identifier, target in tester_targets),
                    f"{version} endpoint violates a safety tester")
            for controller_target in sorted(controller_targets):
                for physical_target in sorted(physical_targets):
                    target = Endpoint(controller_target, physical_target,
                                      tester_targets)
                    if target not in seen:
                        seen.add(target)
                        discovered.append(target)
                        queue.append(target)
        require(enabled, f"{version} endpoint contains a reachable deadlock")
    return discovered


def has_nonidentity(machine: Machine, action: str) -> bool:
    if action not in machine.alphabet:
        return False
    return any(machine.targets(state, action) != frozenset({state})
               for state in machine.states)


def dependency_partition(contract: Contract) -> tuple[list[list[int]],
                                                     dict[str, frozenset[int]],
                                                     dict[str, frozenset[int]]]:
    normal_owners = {
        action: frozenset(component.index for component in contract.components
                          if has_nonidentity(component.old, action)
                          or has_nonidentity(component.new, action))
        for action in sorted(contract.normal)
    }
    all_testers = (contract.old_testers + contract.new_testers
                   + contract.update_testers)
    for action, owners in normal_owners.items():
        if owners:
            continue
        tester_effect = any(action in tester.effective_actions()
                            for tester in all_testers)
        observer_effect = any(action in observer.effective_actions()
                              for observer in contract.observers)
        require(action in contract.controllable_normal
                and not tester_effect and not observer_effect,
                "ownerless normal event is not a disable-able pure "
                f"stutter: {action}")
    update_owners: dict[str, frozenset[int]] = {
        component.reconfigure: frozenset({component.index})
        for component in contract.components
    }
    for action in contract.progress:
        update_owners.setdefault(action, frozenset())
    testers = all_testers

    def support(tester: Tester) -> frozenset[int]:
        result: set[int] = set()
        for action in tester.effective_actions():
            result.update(normal_owners.get(action, update_owners.get(action, frozenset())))
        if tester.update_action is not None:
            result.update(update_owners.get(tester.update_action, frozenset()))
        return frozenset(result)

    changed = True
    while changed:
        changed = False
        for tester in testers:
            if tester.update_action is None:
                continue
            merged = frozenset(set(update_owners[tester.update_action]) | set(support(tester)))
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
    return sorted(groups.values(), key=lambda block: block[0]), normal_owners, update_owners


def tester_support(tester: Tester, normal_owners: Mapping[str, frozenset[int]],
                   update_owners: Mapping[str, frozenset[int]]) -> frozenset[int]:
    result: set[int] = set()
    for action in tester.effective_actions():
        result.update(normal_owners.get(action, update_owners.get(action, frozenset())))
    if tester.update_action is not None:
        result.update(update_owners.get(tester.update_action, frozenset()))
    return frozenset(result)


def projected_tester(tester: Tester, block_common: frozenset[str]) -> Tester:
    kept = tester.effective_actions() & block_common
    return Tester(tester.identifier, tester.source_name, tester.role,
                  tester.machine, kept, tester.update_action,
                  tester.boundary_state)


def block_observers(contract: Contract, selected_new: Sequence[Tester],
                    block_normal: frozenset[str]) -> list[Observer]:
    required: set[int] = set()
    language: set[str] = set()
    for tester in selected_new:
        activation = contract.activations[tester.identifier]
        required.update(activation.observer_global_indices)
        language.update(tester.effective_actions())
    return [Observer(observer.identifier, observer.index, observer.name,
                     observer.machine,
                     frozenset(set(observer.alphabet) & language & set(block_normal)))
            for observer in contract.observers if observer.index in required]


def project_endpoint(endpoint: Endpoint, block: Sequence[int],
                     components: Sequence[LocalComponent],
                     observers: Sequence[Observer],
                     selected_testers: Sequence[Tester], version: str) -> tuple[
                         tuple[Tagged, ...], tuple[tuple[str, int], ...]]:
    global_tester = endpoint.tester_map()
    selected_global_indices = [observer.index for observer in observers]
    result: list[Tagged] = []
    for local_index, global_index in enumerate(block):
        original = endpoint.locals[global_index]
        if local_index == 0:
            global_observers = endpoint.locals[0].observers
            selected = tuple(global_observers[index] for index in selected_global_indices)
        else:
            selected = ()
        local = Local(original.raw, selected)
        require(local in components[local_index].states(version),
                "projected endpoint state is absent from local component: "
                f"version={version}, block={list(block)}, local_index={local_index}, "
                f"global_index={global_index}, raw={local.raw}, "
                f"observers={list(local.observers)}, "
                f"selected_global_observers={selected_global_indices}")
        result.append(Tagged(version, local))
    testers = tuple((tester.identifier, global_tester[tester.identifier])
                    for tester in selected_testers)
    return tuple(result), testers


def physical_closure(components: Sequence[LocalComponent], roots: Iterable[tuple[Tagged, ...]],
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
                if action in component.environment(tagged.version):
                    participant = True
                if action in component.alphabet(tagged.version):
                    targets = component.successors(tagged.version, tagged.local, action)
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
                    products = {prefix + (value,) for prefix in products for value in values}
                for target in products:
                    if target not in seen:
                        seen.add(target)
                        queue.append(target)
        for index, tagged in enumerate(physical):
            if tagged.version != "OLD":
                continue
            for target_local in components[index].transfer.get(tagged.local, frozenset()):
                target = list(physical)
                target[index] = Tagged("NEW", target_local)
                immutable = tuple(target)
                if immutable not in seen:
                    seen.add(immutable)
                    queue.append(immutable)
    return frozenset(seen)


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
    roots: frozenset[Config]
    full_goals: frozenset[tuple[tuple[Tagged, ...], tuple[tuple[str, int], ...]]]
    quiet_goals: frozenset[tuple[tuple[Tagged, ...], tuple[tuple[str, int], ...]]]
    full_goal_uc: frozenset[str]

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
            if ((tagged.version == "OLD") !=
                    (self.components[index].reconfigure in state.pending)):
                return False
        active = state.tester_map()
        if not set(active) <= set(self.requirements):
            return False
        for tester in self.requirements.values():
            should = (tester.update_action in state.pending
                      if tester.role == "old" else
                      tester.update_action not in state.pending
                      if tester.role == "new" else True)
            if (tester.identifier in active) != should:
                return False
            if tester.identifier in active and active[tester.identifier] not in set(tester.machine.states) | {-1}:
                return False
        return state.pending <= self.update_actions

    def safe(self, state: Config) -> bool:
        return self.structurally_valid(state) and all(
            residual != -1 for residual in state.tester_map().values())

    def goal_payload(self, state: Config) -> tuple[
            tuple[Tagged, ...], tuple[tuple[str, int], ...]] | None:
        if not self.safe(state) or state.pending or any(
                tagged.version != "NEW" for tagged in state.physical):
            return None
        active = state.tester_map()
        new_states = tuple((tester.identifier, active[tester.identifier])
                           for tester in self.new_testers)
        payload = (state.physical, new_states)
        return payload if payload in self.quiet_goals else None

    def candidates(self, state: Config) -> list[str]:
        require(self.structurally_valid(state), "candidate source is noncanonical")
        result: set[str] = set()
        for index, tagged in enumerate(state.physical):
            result.update(self.components[index].environment(tagged.version) & self.normal)
        for action in state.pending:
            if not (self.predecessors[action] & state.pending):
                result.add(action)
        return sorted(result)

    def is_controllable(self, action: str) -> bool:
        return action in self.controllable_normal or action in self.update_actions

    def post(self, state: Config, action: str) -> frozenset[Config]:
        require(self.structurally_valid(state), "Post source is noncanonical")
        if action in self.normal:
            return self._post_normal(state, action)
        if action not in self.update_actions or action not in state.pending \
                or self.predecessors[action] & state.pending:
            return frozenset()
        for index, component in enumerate(self.components):
            if component.reconfigure == action:
                return self._post_reconfigure(state, action, index)
        for tester in self.old_testers:
            if tester.update_action == action:
                return self._post_stop(state, action, tester)
        for tester in self.new_testers:
            if tester.update_action == action:
                return self._post_start(state, action, tester)
        return frozenset()

    def _step(self, state: Config, action: str,
              excluded: str | None = None) -> tuple[tuple[str, int], ...]:
        requirements = self.requirements
        return tuple((identifier, requirements[identifier].step(residual, action))
                     for identifier, residual in state.testers
                     if identifier != excluded)

    def _post_normal(self, state: Config, action: str) -> frozenset[Config]:
        choices: list[list[Tagged]] = []
        participant = False
        for index, tagged in enumerate(state.physical):
            component = self.components[index]
            participant = participant or action in component.environment(tagged.version)
            if action in component.alphabet(tagged.version):
                targets = component.successors(tagged.version, tagged.local, action)
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
            products = {prefix + (value,) for prefix in products for value in values}
        testers = self._step(state, action)
        return frozenset(Config(physical, testers, state.pending)
                         for physical in products)

    def _post_reconfigure(self, state: Config, action: str,
                          index: int) -> frozenset[Config]:
        tagged = state.physical[index]
        if tagged.version != "OLD":
            return frozenset()
        targets = self.components[index].transfer.get(tagged.local, frozenset())
        if not targets:
            return frozenset()
        pending = frozenset(set(state.pending) - {action})
        testers = self._step(state, action)
        result = set()
        for target in targets:
            physical = list(state.physical)
            physical[index] = Tagged("NEW", target)
            result.add(Config(tuple(physical), testers, pending))
        return frozenset(result)

    def _post_stop(self, state: Config, action: str,
                   tester: Tester) -> frozenset[Config]:
        if tester.identifier not in state.tester_map():
            return frozenset()
        return frozenset({Config(state.physical,
                                 self._step(state, action, tester.identifier),
                                 frozenset(set(state.pending) - {action}))})

    def _post_start(self, state: Config, action: str,
                    tester: Tester) -> frozenset[Config]:
        if tester.identifier in state.tester_map():
            return frozenset()
        activation = self.activations[tester.identifier]
        if state.physical not in activation:
            return frozenset()
        stepped = dict(self._step(state, action))
        stepped[tester.identifier] = activation[state.physical]
        order = [item.identifier for item in
                 self.old_testers + self.new_testers + self.update_testers]
        testers = tuple((identifier, stepped[identifier])
                        for identifier in order if identifier in stepped)
        return frozenset({Config(state.physical, testers,
                                 frozenset(set(state.pending) - {action}))})


def build_block_problem(contract: Contract, block: Sequence[int],
                        old_endpoint: Sequence[Endpoint],
                        new_endpoint: Sequence[Endpoint],
                        normal_owners: Mapping[str, frozenset[int]],
                        update_owners: Mapping[str, frozenset[int]]) -> BlockProblem:
    block_set = set(block)
    block_normal = frozenset(action for action, owners in normal_owners.items()
                             if owners and set(owners) <= block_set)
    selected_old = [tester for tester in contract.old_testers
                    if set(tester_support(tester, normal_owners, update_owners)) <= block_set]
    selected_new = [tester for tester in contract.new_testers
                    if set(tester_support(tester, normal_owners, update_owners)) <= block_set]
    selected_update = [tester for tester in contract.update_testers
                       if set(tester_support(tester, normal_owners, update_owners)) <= block_set]
    block_update = {contract.components[index].reconfigure for index in block}
    block_update.update(tester.update_action for tester in selected_old + selected_new
                        if tester.update_action is not None)
    block_common = frozenset(set(block_normal) | block_update)
    old_testers = [projected_tester(tester, block_common) for tester in selected_old]
    new_testers = [projected_tester(tester, block_common) for tester in selected_new]
    update_testers = [projected_tester(tester, block_common) for tester in selected_update]
    observers = block_observers(contract, selected_new, block_normal)
    components = make_components(contract, block, observers, block_normal)

    root_parts = {
        project_endpoint(endpoint, block, components, observers, old_testers, "OLD")
        for endpoint in old_endpoint
    }
    root_physical = {physical for physical, _testers in root_parts}
    closure = physical_closure(components, root_physical, block_normal)
    activations: dict[str, dict[tuple[Tagged, ...], int]] = {}
    observer_local = {observer.index: index for index, observer in enumerate(observers)}
    for tester in new_testers:
        source = contract.activations[tester.identifier]
        table: dict[tuple[Tagged, ...], int] = {}
        for physical in closure:
            if source.mode == "INITIAL":
                target = tester.machine.initial
            else:
                first_observers = physical[0].local.observers
                signature = tuple(first_observers[observer_local[index]]
                                  for index in source.observer_global_indices)
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
                    "cross-block precedence survived dependency closure")
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
        testers = tuple((tester.identifier, tester_map[tester.identifier])
                        for tester in ordered_requirements
                        if tester.identifier in tester_map)
        roots.add(Config(physical, testers, update_actions))

    loadable = list(new_endpoint)
    if contract.load_mode == "EXPLICIT_REACHABLE_INDEX":
        require(all(index < len(loadable) for index in contract.load_indices),
                "load selector index leaves endpoint range")
        loadable = [loadable[index] for index in contract.load_indices]
    # A loadable global endpoint can project outside the refined local
    # observer slice.  NativeTierAFactorizer deliberately omits exactly those
    # endpoints while constructing local Goal signatures; roots remain strict.
    full_goals: set[
        tuple[tuple[Tagged, ...], tuple[tuple[str, int], ...]]
    ] = set()
    for endpoint in loadable:
        try:
            full_goals.add(project_endpoint(
                endpoint, block, components, observers, new_testers, "NEW"))
        except CheckError as error:
            if not str(error).startswith(
                    "projected endpoint state is absent from local component"):
                raise
    quiet: set[tuple[tuple[Tagged, ...], tuple[tuple[str, int], ...]]] = set()
    full_uc: set[str] = set()
    for physical, tester_states in full_goals:
        enabled: set[str] = set()
        for action in block_normal - contract.controllable_normal:
            participant = False
            blocked = False
            for index, tagged in enumerate(physical):
                component = components[index]
                if action not in component.environment("NEW"):
                    continue
                participant = True
                if action in component.new_alphabet and not component.successors(
                        "NEW", tagged.local, action):
                    blocked = True
            if participant and not blocked:
                enabled.add(action)
        if enabled:
            full_uc.update(enabled)
        else:
            quiet.add((physical, tester_states))
    require(bool(quiet), "local block has no quiet Goal")
    return BlockProblem(tuple(block), components, observers, block_normal,
                        contract.controllable_normal & block_normal,
                        old_testers, new_testers, update_testers, activations,
                        update_actions, predecessors, frozenset(roots),
                        frozenset(full_goals), frozenset(quiet), frozenset(full_uc))


def config_payload(state: Config) -> dict[str, Any]:
    return {
        "physical": [
            {"version": tagged.version, "raw_state": tagged.local.raw,
             "observer_states": list(tagged.local.observers)}
            for tagged in state.physical
        ],
        "active_testers": dict(state.testers),
        "pending_actions": sorted(state.pending),
    }


def config_key(state: Config) -> str:
    return canonical_text(config_payload(state))


def bundle_config_key(state: Config) -> str:
    """Canonical key syntax used by the frozen v4 Java bundle writer."""
    try:
        return json.dumps(config_payload(state), ensure_ascii=False,
                          separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as error:
        raise CheckError("configuration is not a bundle key") from error


def parse_config_payload(value: Any, label: str) -> Config:
    row = object_(value, label)
    exact_keys(row, {"physical", "active_testers", "pending_actions"}, label)
    physical: list[Tagged] = []
    for offset, raw in enumerate(array(row["physical"], f"{label}.physical")):
        component = object_(raw, f"{label}.physical[{offset}]")
        exact_keys(component, {"version", "raw_state", "observer_states"},
                   "physical component")
        version = text(component["version"], "component version")
        require(version in {"OLD", "NEW"}, "component version is invalid")
        physical.append(Tagged(version, Local(
            exact_int(component["raw_state"], "raw state", 0),
            tuple(integers(component["observer_states"], "observer states",
                           minimum=0, sorted_unique=False)),
        )))
    active = object_(row["active_testers"], f"{label}.active_testers")
    testers = tuple((text(identifier, "tester id"),
                     exact_int(residual, "tester residual", -1))
                    for identifier, residual in active.items())
    pending = frozenset(strings(row["pending_actions"], f"{label}.pending",
                                sorted_unique=True))
    return Config(tuple(physical), testers, pending)


def semantic_config_key(state: Config) -> str:
    return canonical_text(config_payload(state))


def parse_target_key(value: Any, label: str) -> Config:
    raw = text(value, label)
    try:
        parsed = json.loads(raw, object_pairs_hook=_unique_object,
                            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
    except (json.JSONDecodeError, ValueError) as error:
        raise CheckError(f"{label} is not strict target JSON") from error
    return parse_config_payload(parsed, label)


GoalPayload = tuple[tuple[Tagged, ...], tuple[tuple[str, int], ...]]


@dataclass(frozen=True)
class LocalCheck:
    counts: Mapping[str, int]
    goal_ids: Mapping[str, GoalPayload]


def verify_local(problem: BlockProblem, local: Any,
                 expected_index: int) -> LocalCheck:
    row = object_(local, f"local[{expected_index}]")
    exact_keys(row, BUNDLE_LOCAL_KEYS, f"local[{expected_index}]")
    require(exact_int(row.get("block_index"), "block index", 0) == expected_index,
            "local block index differs")
    require(integers(row.get("components"), "local components") == list(problem.block),
            "local component block differs")
    require(row.get("decision") == "realizable", "local decision is not realizable")
    require(exact_bool(row["independent_certificate_valid"],
                       "independent certificate valid"),
            "historical independent certificate is invalid")
    require(row["independent_certificate_basis"] ==
            "independent_certificate_proof",
            "historical independent certificate basis differs")
    for field in (
        "full_goal_count", "quiet_terminal_count", "solver_discovered_states",
        "solver_successor_queries", "solver_outcomes",
        "certificate_initial_count", "certificate_rank_count",
        "certificate_strategy_source_count", "certificate_strategy_bucket_count",
        "certificate_goal_match_count", "independent_certificate_states",
        "independent_certificate_queries", "independent_certificate_outcomes",
        "independent_certificate_elapsed_ms",
    ):
        exact_int(row[field], f"local {field}", 0)
    proof = object_(row.get("proof"), "local proof")
    exact_keys(proof, {"schema_version", "semantic_basis", "root_state_ids",
                       "states", "candidate_buckets", "strategy_buckets"},
               "local proof")
    require(proof["schema_version"] == "fg-ducs-local-rank-proof-v1",
            "local proof schema differs")
    require(proof["semantic_basis"] == "independent_fine_grained_semantics",
            "local proof semantic basis differs")
    states: dict[str, Config] = {}
    ranks: dict[str, int] = {}
    goals: dict[str, tuple[tuple[Tagged, ...], tuple[tuple[str, int], ...]] | None] = {}
    declared_safe: dict[str, bool] = {}
    goal_ids: dict[str, tuple[tuple[Tagged, ...], tuple[tuple[str, int], ...]]] = {}
    previous_state_id: str | None = None
    state_payloads: set[Config] = set()
    for offset, raw in enumerate(array(proof["states"], "proof states")):
        record = object_(raw, f"proof state[{offset}]")
        exact_keys(record, {"physical", "active_testers", "pending_actions",
                            "id", "rank", "safe", "goal",
                            "goal_signature_id", "goal_signature"},
                   "proof state")
        identifier = text(record["id"], "proof state id")
        require(identifier not in states
                and (previous_state_id is None or identifier > previous_state_id),
                "proof state IDs are not canonical")
        previous_state_id = identifier
        state = parse_config_payload({
            "physical": record["physical"],
            "active_testers": record["active_testers"],
            "pending_actions": record["pending_actions"],
        }, "proof state payload")
        require(state not in state_payloads,
                "proof rank domain repeats a semantic state")
        state_payloads.add(state)
        require(problem.structurally_valid(state), "proof state is structurally invalid")
        independent_safe = problem.safe(state)
        require(exact_bool(record["safe"], "proof safe") == independent_safe,
                "proof Safe differs from independent semantics")
        require(independent_safe,
                "proof rank domain contains an unsafe state")
        independent_goal = problem.goal_payload(state)
        require(exact_bool(record["goal"], "proof Goal") ==
                (independent_goal is not None),
                "proof Goal differs from independent semantics")
        rank = exact_int(record["rank"], "proof rank", 0)
        require((independent_goal is not None and rank == 0)
                or (independent_goal is None and rank > 0),
                "proof rank/Goal boundary differs")
        if independent_goal is None:
            require(record["goal_signature_id"] is None
                    and record["goal_signature"] is None,
                    "non-Goal carries a local Goal payload")
        else:
            goal_id = text(record["goal_signature_id"], "goal signature id")
            signature = object_(record["goal_signature"], "goal signature")
            exact_keys(signature, {"id", "physical", "new_requirement_states"},
                       "goal signature")
            require(signature["id"] == goal_id, "goal signature id differs")
            payload = parse_config_payload({
                "physical": signature["physical"],
                "active_testers": signature["new_requirement_states"],
                "pending_actions": [],
            }, "goal signature payload")
            typed = (payload.physical, payload.testers)
            require(typed == independent_goal,
                    "local Goal payload differs from independent quiet load Goal")
            require(goal_id not in goal_ids or goal_ids[goal_id] == typed,
                    "one goal id denotes multiple payloads")
            goal_ids[goal_id] = typed
        states[identifier] = state
        ranks[identifier] = rank
        goals[identifier] = independent_goal
        declared_safe[identifier] = independent_safe

    roots = strings(proof["root_state_ids"], "proof roots", sorted_unique=True)
    require(set(roots) <= set(states), "proof root leaves rank domain")
    root_payloads = {states[identifier] for identifier in roots}
    require(root_payloads == set(problem.roots),
            "proof roots differ from independently projected old endpoint roots")

    candidates: dict[tuple[str, str], tuple[bool, bool, frozenset[Config]]] = {}
    by_source: dict[str, set[str]] = defaultdict(set)
    nonempty = 0
    outcomes = 0
    previous_candidate: tuple[str, str] | None = None
    for offset, raw in enumerate(array(proof["candidate_buckets"],
                                       "candidate buckets")):
        bucket = object_(raw, f"candidate[{offset}]")
        exact_keys(bucket, {"source", "action", "controllable", "update",
                            "target_keys"}, "candidate bucket")
        source = text(bucket["source"], "candidate source")
        action = text(bucket["action"], "candidate action")
        candidate_key = (source, action)
        require(source in states and candidate_key not in candidates
                and (previous_candidate is None
                     or candidate_key > previous_candidate),
                "candidate source/key is invalid")
        previous_candidate = candidate_key
        raw_targets = strings(bucket["target_keys"], "target keys",
                              sorted_unique=True)
        parsed_targets = [parse_target_key(item, "candidate target")
                          for item in raw_targets]
        require(all(raw == bundle_config_key(parsed)
                    for raw, parsed in zip(raw_targets, parsed_targets)),
                "candidate target key is not canonical")
        require(len(parsed_targets) == len(set(parsed_targets)),
                "candidate target keys repeat a semantic state")
        targets = frozenset(parsed_targets)
        expected_targets = problem.post(states[source], action)
        missing_targets = sorted(config_key(target)
                                 for target in expected_targets - targets)
        extra_targets = sorted(config_key(target)
                               for target in targets - expected_targets)
        require(targets == expected_targets,
                f"candidate Post differs: block={expected_index} state={source} "
                f"action={action} expected={len(expected_targets)} "
                f"declared={len(targets)} missing={missing_targets[:1]} "
                f"extra={extra_targets[:1]}")
        controllable = exact_bool(bucket["controllable"], "candidate controllable")
        update = exact_bool(bucket["update"], "candidate update")
        require(controllable == problem.is_controllable(action),
                "candidate controllability differs")
        require(update == (action in states[source].pending),
                "candidate update flag differs")
        candidates[(source, action)] = (controllable, update, targets)
        by_source[source].add(action)
        if targets:
            nonempty += 1
            outcomes += len(targets)
    for identifier, state in states.items():
        require(by_source[identifier] == set(problem.candidates(state)),
                f"candidate action census differs at {identifier}")

    strategies: dict[tuple[str, str], tuple[str, ...]] = {}
    selected_by_source: dict[str, set[str]] = defaultdict(set)
    previous_strategy: tuple[str, str] | None = None
    for offset, raw in enumerate(array(proof["strategy_buckets"],
                                       "strategy buckets")):
        bucket = object_(raw, f"strategy[{offset}]")
        exact_keys(bucket, {"source", "action", "target_state_ids"},
                   "strategy bucket")
        source = text(bucket["source"], "strategy source")
        action = text(bucket["action"], "strategy action")
        key = (source, action)
        require(key in candidates and key not in strategies
                and (previous_strategy is None or key > previous_strategy),
                "strategy has no unique candidate")
        previous_strategy = key
        targets = tuple(strings(bucket["target_state_ids"], "strategy targets",
                                sorted_unique=True))
        require(bool(targets) and set(targets) <= set(states),
                "strategy leaves rank domain")
        require(frozenset(states[target] for target in targets) == candidates[key][2],
                "strategy targets differ from complete Post")
        require(all(ranks[target] < ranks[source] for target in targets),
                "strategy rank does not strictly decrease")
        strategies[key] = targets
        selected_by_source[source].add(action)
    for identifier, state in states.items():
        enabled_uc = {action for action in by_source[identifier]
                      if candidates[(identifier, action)][2]
                      and not candidates[(identifier, action)][0]}
        enabled_c = {action for action in by_source[identifier]
                     if candidates[(identifier, action)][2]
                     and candidates[(identifier, action)][0]}
        selected = selected_by_source[identifier]
        if goals[identifier] is not None:
            require(not enabled_uc and not selected,
                    "quiet Goal has enabled UC or selected action")
        elif enabled_uc:
            require(selected == enabled_uc,
                    "strategy does not retain every enabled UC bucket")
        else:
            require(len(selected) == 1 and selected <= enabled_c,
                    "strategy does not select exactly one enabled C bucket")

    reachable = set(roots)
    queue = deque(roots)
    while queue:
        source = queue.popleft()
        for action in selected_by_source[source]:
            for target in strategies[(source, action)]:
                if target not in reachable:
                    reachable.add(target)
                    queue.append(target)
    require(reachable == set(states),
            "retained certificate graph does not cover its complete rank domain")
    require(row["certificate_initial_count"] == len(roots),
            "certificate initial-state census differs")
    require(row["certificate_rank_count"] == len(states),
            "certificate rank-state census differs")
    require(row["certificate_strategy_source_count"] ==
            sum(bool(actions) for actions in selected_by_source.values()),
            "certificate strategy-source census differs")
    require(row["certificate_strategy_bucket_count"] == len(strategies),
            "certificate strategy-bucket census differs")
    require(row["certificate_goal_match_count"] == len(goal_ids),
            "certificate Goal-match census differs")
    require(row["independent_certificate_states"] == len(states),
            "historical independent-certificate state census differs")
    non_goal_candidates = [
        payload for (source, _action), payload in candidates.items()
        if goals[source] is None
    ]
    require(row["independent_certificate_queries"] ==
            len(non_goal_candidates),
            "historical independent-certificate query census differs")
    require(row["independent_certificate_outcomes"] == sum(
        len(payload[2]) for payload in non_goal_candidates),
        "historical independent-certificate outcome census differs")
    require(exact_int(row.get("full_goal_count"), "full Goal count", 0) ==
            len(problem.full_goals), "full Goal census differs")
    require(exact_int(row.get("quiet_terminal_count"), "quiet Goal count", 0) ==
            len(problem.quiet_goals), "quiet Goal census differs")
    require(set(strings(row.get("full_goal_uncontrollable_actions"),
                        "full Goal UC")) ==
            set(problem.full_goal_uc), "full Goal UC action census differs")
    counts = {
        "rank_states": len(states),
        "root_states": len(roots),
        "candidate_buckets": len(candidates),
        "nonempty_candidate_buckets": nonempty,
        "candidate_outcomes": outcomes,
        "strategy_buckets": len(strategies),
        "goal_payloads": len(goal_ids),
        "full_goals": len(problem.full_goals),
        "quiet_goals": len(problem.quiet_goals),
    }
    return LocalCheck(counts, dict(goal_ids))


ObserverPair = tuple[tuple[int, ...], tuple[int, ...]]
EndpointProjection = tuple[tuple[Local, ...], tuple[tuple[str, int], ...]]


def loadable_endpoints(contract: Contract,
                       new_endpoint: Sequence[Endpoint]) -> list[Endpoint]:
    selected = list(new_endpoint)
    if contract.load_mode == "EXPLICIT_REACHABLE_INDEX":
        require(all(index < len(selected) for index in contract.load_indices),
                "load selector index leaves endpoint range")
        selected = [selected[index] for index in contract.load_indices]
    return selected


def goal_payload_key(payload: GoalPayload) -> str:
    physical, testers = payload
    return canonical_text({
        "physical": [
            {"version": tagged.version, "raw_state": tagged.local.raw,
             "observer_states": list(tagged.local.observers)}
            for tagged in physical
        ],
        "new_requirement_states": dict(testers),
    })


def observer_pair_closure(
        global_observers: Sequence[Observer],
        local_observers: Sequence[Observer],
        seeds: Iterable[tuple[int, ...]],
        actions: Iterable[str]) -> frozenset[ObserverPair]:
    require(len(global_observers) == len(local_observers),
            "observer relation arity differs")
    seen: set[ObserverPair] = set()
    queue: deque[ObserverPair] = deque()
    for seed in seeds:
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


def derive_observer_relations(
        contract: Contract,
        problems: Sequence[BlockProblem],
        old_endpoint: Sequence[Endpoint],
        transport: Mapping[str, Any]) -> list[
            tuple[tuple[int, ...], frozenset[ObserverPair]]]:
    declared_rows = array(transport.get("observer_relations"),
                          "transport observer relations")
    require(len(declared_rows) == len(problems),
            "observer relation block census differs")
    result: list[tuple[tuple[int, ...], frozenset[ObserverPair]]] = []
    for block_index, problem in enumerate(problems):
        indices = tuple(observer.index for observer in problem.observers)
        global_observers = [contract.observers[index] for index in indices]
        seeds = {
            tuple(endpoint.locals[0].observers[index] for index in indices)
            for endpoint in old_endpoint
        }
        pairs = observer_pair_closure(
            global_observers, problem.observers, seeds, contract.normal)
        row = object_(declared_rows[block_index],
                      f"observer relation[{block_index}]")
        exact_keys(row, {"block_index", "global_observer_indices", "pairs"},
                   "observer relation row")
        require(exact_int(row["block_index"], "observer relation block", 0)
                == block_index, "observer relation block index differs")
        require(tuple(integers(row["global_observer_indices"],
                               "global observer indices")) == indices,
                "observer relation global-index census differs")
        declared_pairs: set[ObserverPair] = set()
        for offset, raw in enumerate(array(row["pairs"],
                                           "observer relation pairs")):
            pair = object_(raw, f"observer relation pair[{offset}]")
            exact_keys(pair, {"global", "local"}, "observer relation pair")
            typed = (
                tuple(integers(pair["global"], "global observer tuple",
                               sorted_unique=False)),
                tuple(integers(pair["local"], "local observer tuple",
                               sorted_unique=False)),
            )
            require(len(typed[0]) == len(indices)
                    and len(typed[1]) == len(indices),
                    "observer relation pair arity differs")
            require(typed not in declared_pairs,
                    "observer relation repeats a pair")
            declared_pairs.add(typed)
        require(declared_pairs == set(pairs),
                f"observer relation differs at block {block_index}")
        result.append((indices, pairs))
    return result


def activation_residual(source: Activation, tester: Tester,
                        observer_state: tuple[int, ...]) -> int | None:
    if source.mode == "INITIAL":
        return tester.machine.initial
    target = source.mapping.get(observer_state)
    return target if target in tester.machine.states else None


def verify_activation_quotients(
        contract: Contract,
        problems: Sequence[BlockProblem],
        old_endpoint: Sequence[Endpoint]) -> tuple[int, int]:
    tester_count = 0
    pair_count = 0
    for problem in problems:
        local_by_global = {
            observer.index: observer for observer in problem.observers
        }
        for tester in problem.new_testers:
            tester_count += 1
            source = contract.activations[tester.identifier]
            indices = source.observer_global_indices
            global_observers = [contract.observers[index] for index in indices]
            require(all(index in local_by_global for index in indices),
                    "local activation omits a bound observer")
            local_observers = [local_by_global[index] for index in indices]
            seeds = {
                tuple(endpoint.locals[0].observers[index] for index in indices)
                for endpoint in old_endpoint
            }
            pairs = observer_pair_closure(
                global_observers, local_observers, seeds, contract.normal)
            for global_state, local_state in pairs:
                global_target = activation_residual(
                    source, tester, global_state)
                local_target = activation_residual(source, tester, local_state)
                if local_target is not None:
                    require(local_target == global_target,
                            "local activation quotient differs from source iota: "
                            + tester.source_name)
            pair_count += len(pairs)
    return tester_count, pair_count


def project_loadable_goal(
        endpoint: Endpoint,
        problem: BlockProblem) -> GoalPayload | None:
    try:
        return project_endpoint(
            endpoint, problem.block, problem.components, problem.observers,
            problem.new_testers, "NEW")
    except CheckError as error:
        if str(error).startswith(
                "projected endpoint state is absent from local component"):
            return None
        raise


def verify_quiet_terminal_product(
        problems: Sequence[BlockProblem],
        loadable: Sequence[Endpoint]) -> int:
    choices = [sorted(problem.quiet_goals, key=goal_payload_key)
               for problem in problems]
    require(all(choices), "quiet terminal product has an empty factor")
    expected = set(product(*choices))
    actual: set[tuple[GoalPayload, ...]] = set()
    for endpoint in loadable:
        projected: list[GoalPayload] = []
        for problem in problems:
            payload = project_loadable_goal(endpoint, problem)
            if payload is None or payload not in problem.quiet_goals:
                break
            projected.append(payload)
        if len(projected) == len(problems):
            actual.add(tuple(projected))
    require(actual == expected,
            "quiet Goal product differs from loadable endpoint projection")
    return len(expected)


def endpoint_projection(endpoint: Endpoint) -> EndpointProjection:
    return endpoint.locals, tuple(sorted(endpoint.testers))


def verify_transport(
        contract: Contract,
        bundle: Mapping[str, Any],
        problems: Sequence[BlockProblem],
        local_checks: Sequence[LocalCheck],
        old_endpoint: Sequence[Endpoint],
        new_endpoint: Sequence[Endpoint]) -> dict[str, int]:
    require(exact_bool(bundle.get("terminal_product_verified"),
                       "terminal product flag"),
            "bundle terminal product is not verified")
    transport = object_(bundle.get("transport"), "transport")
    exact_keys(transport, {
        "verified", "activation_tester_count",
        "activation_relation_pair_count", "observer_relation_pair_count",
        "load_selector_signature_count", "load_selector_endpoint_count",
        "certificate_terminal_tuple_count", "terminal_observer_fiber_count",
        "observer_relations", "load_selectors", "terminal_assemblies",
    }, "transport")
    require(exact_bool(transport["verified"], "transport verified"),
            "bundle transport is not verified")

    loadable = loadable_endpoints(contract, new_endpoint)
    quiet_product_count = verify_quiet_terminal_product(problems, loadable)
    activation_testers, activation_pairs = verify_activation_quotients(
        contract, problems, old_endpoint)
    require(exact_int(transport["activation_tester_count"],
                      "activation tester count", 0) == activation_testers,
            "activation tester census differs")
    require(exact_int(transport["activation_relation_pair_count"],
                      "activation relation pair count", 0) == activation_pairs,
            "activation quotient relation census differs")

    relations = derive_observer_relations(
        contract, problems, old_endpoint, transport)
    observer_pair_count = sum(len(pairs) for _indices, pairs in relations)
    require(exact_int(transport["observer_relation_pair_count"],
                      "observer relation pair count", 0) == observer_pair_count,
            "observer relation pair census differs")

    loadable_set = set(loadable)
    selector: dict[EndpointProjection, tuple[str, int]] = {}
    selector_rows: list[dict[str, Any]] = []
    load_endpoint_count = 0
    for endpoint_index, endpoint in enumerate(new_endpoint):
        if endpoint not in loadable_set:
            continue
        load_endpoint_count += 1
        key = endpoint_projection(endpoint)
        if key in selector:
            continue
        endpoint_id = f"new-{endpoint_index:08d}"
        selector[key] = (endpoint_id, endpoint.controller)
        selector_rows.append({
            "endpoint_id": endpoint_id,
            "controller_state": endpoint.controller,
            "component_raw_states": [local.raw for local in endpoint.locals],
            "observer_states": list(endpoint.locals[0].observers),
            "tester_states": dict(sorted(endpoint.testers)),
        })
    declared_selectors = array(transport["load_selectors"], "load selectors")
    require(len(declared_selectors) == len(selector_rows),
            "load selector row census differs")
    for index, (raw, expected) in enumerate(zip(declared_selectors,
                                                 selector_rows)):
        row = object_(raw, f"load selector[{index}]")
        exact_keys(row, {"endpoint_id", "controller_state",
                         "component_raw_states", "observer_states",
                         "tester_states"}, "load selector row")
        typed = {
            "endpoint_id": text(row["endpoint_id"], "load endpoint id"),
            "controller_state": exact_int(row["controller_state"],
                                          "load controller state", 0),
            "component_raw_states": integers(
                row["component_raw_states"], "load component states",
                sorted_unique=False),
            "observer_states": integers(
                row["observer_states"], "load observer states",
                sorted_unique=False),
            "tester_states": {
                text(identifier, "load tester id"):
                    exact_int(state, "load tester state", 0)
                for identifier, state in object_(
                    row["tester_states"], "load tester states").items()
            },
        }
        require(typed == expected, f"load selector differs at row {index}")
    require(exact_int(transport["load_selector_signature_count"],
                      "load selector signature count", 0) == len(selector),
            "load selector signature census differs")
    require(exact_int(transport["load_selector_endpoint_count"],
                      "load selector endpoint count", 0) == load_endpoint_count,
            "load selector endpoint census differs")

    choices = [sorted(check.goal_ids.items()) for check in local_checks]
    require(all(choices), "certificate has no local Goal match")
    terminal_combinations = list(product(*choices))
    assemblies: list[dict[str, Any]] = []
    expected_new_testers = {
        tester.identifier for tester in contract.new_testers
    }
    for terminal_index, terminal in enumerate(terminal_combinations):
        global_observers: list[int | None] = [None] * len(contract.observers)
        for block_index, (_goal_id, payload) in enumerate(terminal):
            indices, pairs = relations[block_index]
            local_observers = payload[0][0].local.observers
            fiber = {global_state for global_state, local_state in pairs
                     if local_state == local_observers}
            require(len(fiber) == 1,
                    "certificate terminal observer fibre is not singleton: "
                    f"block={block_index} size={len(fiber)}")
            values = next(iter(fiber))
            for offset, global_index in enumerate(indices):
                previous = global_observers[global_index]
                require(previous is None or previous == values[offset],
                        "overlapping terminal observer fibres disagree")
                global_observers[global_index] = values[offset]
        require(all(value is not None for value in global_observers),
                "terminal observer fibres do not cover the global registry")
        concrete_observers = tuple(int(value) for value in global_observers)
        concrete_locals: list[Local | None] = [None] * len(contract.components)
        tester_states: dict[str, int] = {}
        local_goal_ids: list[str] = []
        for block_index, (goal_id, payload) in enumerate(terminal):
            local_goal_ids.append(goal_id)
            physical, local_testers = payload
            problem = problems[block_index]
            require(len(physical) == len(problem.block),
                    "terminal physical arity differs from its block")
            for offset, tagged in enumerate(physical):
                require(tagged.version == "NEW",
                        "terminal contains an OLD component")
                global_index = problem.block[offset]
                observers = concrete_observers if global_index == 0 else ()
                concrete_locals[global_index] = Local(tagged.local.raw,
                                                       tuple(observers))
            for identifier, residual in local_testers:
                require(identifier not in tester_states,
                        "new tester belongs to more than one block")
                tester_states[identifier] = residual
        require(all(local is not None for local in concrete_locals),
                "terminal partition omits a component")
        require(set(tester_states) == expected_new_testers,
                "terminal partition omits a new tester")
        projection = (
            tuple(local for local in concrete_locals if local is not None),
            tuple(sorted(tester_states.items())),
        )
        require(projection in selector,
                "certificate terminal is outside the loadable Goal")
        endpoint_id, controller_state = selector[projection]
        assemblies.append({
            "terminal_tuple_index": terminal_index,
            "observer_fiber_index": 0,
            "local_goal_signature_ids": local_goal_ids,
            "global_observer_states": list(concrete_observers),
            "endpoint_id": endpoint_id,
            "controller_state": controller_state,
        })
    declared_assemblies: list[dict[str, Any]] = []
    for offset, raw in enumerate(array(transport["terminal_assemblies"],
                                       "terminal assemblies")):
        row = object_(raw, f"terminal assembly[{offset}]")
        exact_keys(row, {
            "terminal_tuple_index", "observer_fiber_index",
            "local_goal_signature_ids", "global_observer_states",
            "endpoint_id", "controller_state",
        }, "terminal assembly")
        declared_assemblies.append({
            "terminal_tuple_index": exact_int(
                row["terminal_tuple_index"], "terminal tuple index", 0),
            "observer_fiber_index": exact_int(
                row["observer_fiber_index"], "observer fibre index", 0),
            "local_goal_signature_ids": [
                text(value, "local Goal signature id")
                for value in array(row["local_goal_signature_ids"],
                                   "local Goal signature ids")
            ],
            "global_observer_states": integers(
                row["global_observer_states"], "terminal global observers",
                sorted_unique=False),
            "endpoint_id": text(row["endpoint_id"], "terminal endpoint id"),
            "controller_state": exact_int(
                row["controller_state"], "terminal controller state", 0),
        })
    require(declared_assemblies == assemblies,
            "terminal assembly rows differ")
    require(exact_int(transport["certificate_terminal_tuple_count"],
                      "certificate terminal tuple count", 0) ==
            len(terminal_combinations),
            "certificate terminal tuple census differs")
    require(exact_int(transport["terminal_observer_fiber_count"],
                      "terminal observer fiber count", 0) == len(assemblies),
            "terminal observer fibre census differs")
    return {
        "quiet_terminal_product_tuples": quiet_product_count,
        "activation_testers": activation_testers,
        "activation_relation_pairs": activation_pairs,
        "observer_relation_pairs": observer_pair_count,
        "load_selector_signatures": len(selector),
        "load_selector_endpoints": load_endpoint_count,
        "certificate_terminal_tuples": len(terminal_combinations),
        "terminal_observer_fibres": len(assemblies),
    }


ReceiptBinding = tuple[str, str, tuple[int, ...]]


def validate_bundle_envelope(
        bundle: Mapping[str, Any], component_count: int
) -> tuple[list[list[int]], frozenset[ReceiptBinding]]:
    """Validate the historical v4 envelope independently of its proof body."""
    root = object_(bundle, "bundle")
    exact_keys(root, BUNDLE_ROOT_KEYS, "bundle")
    require(root["schema_version"] == BUNDLE_SCHEMA, "bundle schema differs")
    source_name = text(root["source_name"], "bundle source name")
    require(bool(source_name), "bundle source name is empty")
    source_sha = text(root["source_sha256"], "bundle source SHA")
    require(len(source_sha) == 64
            and all(character in "0123456789abcdef" for character in source_sha),
            "bundle source SHA is invalid")
    text(root["definition"], "bundle definition")
    for field, expected in {
        "extraction_status": "COMPLETE_CONSERVATIVE",
        "claim_scope": "one_way_sufficient_win_only",
        "strategy_model": "finite_memory_local_product",
        "goal_policy": "check_original_goal_and_load_before_priority_arbiter",
        "factorization_stage":
            "source_native_before_global_mixed_version_update_game",
        "factor_status": "NONTRIVIAL_SOURCE_NATIVE",
        "solve_status": "PRODUCER_VERIFIED_REFINED_WIN",
    }.items():
        require(root[field] == expected, f"bundle {field} differs")
    require(exact_bool(root["fixed_endpoint_products_materialized"],
                       "fixed endpoint materialization"),
            "fixed endpoint products were not materialized")
    require(not exact_bool(root["global_mixed_game_materialized"],
                           "global mixed-game materialization"),
            "global mixed game was materialized")
    require(exact_int(root["global_mixed_state_count"],
                      "global mixed state count", 0) == 0
            and exact_int(root["global_mixed_post_query_count"],
                          "global mixed query count", 0) == 0,
            "global mixed-game counters are nonzero")
    exact_int(root["old_endpoint_state_count"], "old endpoint count", 1)
    exact_int(root["new_endpoint_state_count"], "new endpoint count", 1)
    require(exact_bool(root["terminal_product_verified"],
                       "terminal product flag"),
            "terminal product is not producer-verified")

    raw_partition = array(root["component_partition"], "component partition")
    partition = [integers(block, f"component partition[{index}]")
                 for index, block in enumerate(raw_partition)]
    require(bool(partition) and all(block for block in partition)
            and partition == sorted(partition, key=lambda block: block[0]),
            "component partition is not canonical")
    require(sorted(component for block in partition for component in block)
            == list(range(component_count)),
            "component partition is not total and disjoint")

    parent = list(range(component_count))

    def find(value: int) -> int:
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    def join(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    seen_receipts: set[str] = set()
    typed_receipts: set[ReceiptBinding] = set()
    receipts = array(root["dependency_receipts"], "dependency receipts")
    require(bool(receipts), "dependency receipts are empty")
    for offset, raw in enumerate(receipts):
        row = object_(raw, f"dependency receipt[{offset}]")
        exact_keys(row, {"kind", "declaration", "components"},
                   f"dependency receipt[{offset}]")
        kind = text(row["kind"], "dependency receipt kind")
        require(kind in {"ordinary-action", "update-action", "tester",
                         "activation", "precedence"},
                "dependency receipt kind differs")
        text(row["declaration"], "dependency receipt declaration")
        support = integers(row["components"], "dependency receipt support")
        require(bool(support) and all(value < component_count for value in support),
                "dependency receipt support leaves component domain")
        signature = canonical_text(row)
        require(signature not in seen_receipts,
                "dependency receipts contain a duplicate")
        seen_receipts.add(signature)
        binding = (kind, row["declaration"], tuple(support))
        require(binding not in typed_receipts,
                "dependency receipt binding is duplicated")
        typed_receipts.add(binding)
        for value in support[1:]:
            join(support[0], value)
    derived: dict[int, list[int]] = defaultdict(list)
    for component in range(component_count):
        derived[find(component)].append(component)
    derived_partition = sorted(derived.values(), key=lambda block: block[0])
    require(derived_partition == partition,
            "dependency receipt closure differs from component partition")

    arbiter = object_(root["arbiter"], "arbiter")
    exact_keys(arbiter, {
        "block_order", "original_goal_preempts_local_progress",
        "uncontrollable_mode", "shared_controllable_pure_stutter",
    }, "arbiter")
    require(integers(arbiter["block_order"], "arbiter block order")
            == list(range(len(partition))), "arbiter block order differs")
    require(exact_bool(arbiter["original_goal_preempts_local_progress"],
                       "arbiter Goal preemption"),
            "arbiter omits original-Goal preemption")
    require(arbiter["uncontrollable_mode"] == "allow_all_then_wait"
            and arbiter["shared_controllable_pure_stutter"] == "disabled",
            "arbiter policy differs")
    for field in ("local_solver_discovered_states_sum",
                  "local_solver_successor_queries_sum",
                  "local_solver_outcomes_sum"):
        exact_int(root[field], f"bundle {field}", 0)
    return partition, frozenset(typed_receipts)


def verify(ir: Mapping[str, Any], bundle: Mapping[str, Any]) -> dict[str, Any]:
    contract = parse_contract(ir)
    declared_partition, declared_receipts = validate_bundle_envelope(
        bundle, len(contract.components))
    for field, expected in {
        "source_name": contract.source_name,
        "source_sha256": contract.source_sha256,
        "definition": contract.definition,
    }.items():
        require(bundle.get(field) == expected, f"IR/bundle {field} differs")
    partition, normal_owners, update_owners = dependency_partition(contract)
    require(declared_partition == partition,
            "independent dependency partition differs from bundle")
    expected_receipts: set[ReceiptBinding] = set()

    def add_receipt(kind: str, declaration: str,
                    support: Iterable[int]) -> None:
        ordered = tuple(sorted(set(support)))
        if ordered:
            expected_receipts.add((kind, declaration, ordered))

    for action in sorted(normal_owners):
        add_receipt("ordinary-action", action, normal_owners[action])
    for action in sorted(update_owners):
        add_receipt("update-action", action, update_owners[action])
    testers = contract.old_testers + contract.new_testers + contract.update_testers
    for tester in testers:
        add_receipt("tester", tester.source_name,
                    tester_support(tester, normal_owners, update_owners))
    for tester in contract.new_testers:
        add_receipt("activation", tester.source_name,
                    tester_support(tester, normal_owners, update_owners))
    for before, after in contract.precedence:
        add_receipt("precedence", before + "<" + after,
                    set(update_owners[before]) | set(update_owners[after]))
    require(declared_receipts == expected_receipts,
            "dependency receipts differ from independent reconstruction")
    globals_ = global_components(contract)
    old_endpoint = build_endpoint(contract, globals_, contract.old_testers, "OLD")
    new_endpoint = build_endpoint(contract, globals_, contract.new_testers, "NEW")
    require(exact_int(bundle.get("old_endpoint_state_count"),
                      "bundle old endpoint count", 1) == len(old_endpoint),
            "old endpoint census differs")
    require(exact_int(bundle.get("new_endpoint_state_count"),
                      "bundle new endpoint count", 1) == len(new_endpoint),
            "new endpoint census differs")
    locals_ = array(bundle.get("locals"), "bundle locals")
    require(len(locals_) == len(partition), "local block census differs")
    totals: dict[str, int] = defaultdict(int)
    local_reports: list[dict[str, Any]] = []
    problems: list[BlockProblem] = []
    local_checks: list[LocalCheck] = []
    for index, block in enumerate(partition):
        problem = build_block_problem(contract, block, old_endpoint, new_endpoint,
                                      normal_owners, update_owners)
        checked = verify_local(problem, locals_[index], index)
        for key, value in checked.counts.items():
            totals[key] += value
        local_reports.append({"block_index": index, "components": block,
                              **checked.counts})
        problems.append(problem)
        local_checks.append(checked)
    for root_field, local_field in (
        ("local_solver_discovered_states_sum", "solver_discovered_states"),
        ("local_solver_successor_queries_sum", "solver_successor_queries"),
        ("local_solver_outcomes_sum", "solver_outcomes"),
    ):
        require(bundle[root_field] == sum(
            object_(local, "bundle local")[local_field] for local in locals_),
            f"bundle {root_field} differs from local sum")
    transport = verify_transport(
        contract, bundle, problems, local_checks, old_endpoint, new_endpoint)
    report = {
        "schema_version": REPORT_SCHEMA,
        "status": "POST_FRONTEND_CONTRACT_TO_CERTIFICATE_SEMANTICS_VERIFIED",
        "source_name": contract.source_name,
        "source_sha256": contract.source_sha256,
        "definition": contract.definition,
        "shared_mtsa_frontend": True,
        "independent_raw_source_frontend": False,
        "independent_controller_synthesis": False,
        "independent_win_synthesis": False,
        "source_to_win_replay": False,
        "post_frontend_contract_ir_to_winning_certificate_semantic_verification": True,
        "global_transport_and_kappa_verified": True,
        "old_endpoint_states": len(old_endpoint),
        "new_endpoint_states": len(new_endpoint),
        "component_partition": partition,
        "locals": local_reports,
        "totals": dict(sorted(totals.items())),
        "transport": transport,
        "claim_boundary": {
            "post_outcome_certificate_supplied": True,
            "same_author_independent_python_checker": True,
            "ordinary_lts_parser_shared": True,
            "fixed_controller_synthesis_shared": True,
            "held_out_or_third_party_cases": 0,
        },
    }
    report["semantic_digest_sha256"] = sha256_bytes(canonical_bytes(report))
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ir", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        report = verify(load(args.ir), load(args.bundle))
        raw = canonical_bytes(report)
        if args.output is not None:
            args.output.write_bytes(raw)
        else:
            print(raw.decode("utf-8"), end="")
        return 0
    except CheckError as error:
        print("POST_FRONTEND_CERTIFICATE_INVALID=" + str(error))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
