#!/usr/bin/env python3
"""Independent raw-LTS oracle for the decisive FG-DUCS evidence families.

This checker deliberately shares no Java parser, adapter, problem object,
successor table, or winning-layer implementation with the production solver.
It reads the registered ``.lts`` bytes directly, accepts only the small FSP
subset emitted by ``generate_decisive_evidence.py``, composes endpoint states,
constructs the mixed-version reachability game, and solves the strong
reachability fixed point explicitly.

The authoritative target, endpoint, relation, controller, safety, and
precedence declarations are bound fail-closed.  Unreachable process
declarations may remain because the registered metamorphic suite contains
them.  This is an independent oracle for the registered evidence families,
not a second general MTSA front end.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import os
import re
import tempfile
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, DefaultDict, Dict, Iterable, List, Mapping, Sequence, Set, Tuple


ORACLE_SCHEMA = "fse2027-independent-raw-lts-oracle-v4"
ORACLE_ID = "python-raw-fsp-subset-bound-explicit-strong-reachability-v4"
StateTuple = Tuple[str, ...]
VersionTuple = Tuple[bool, ...]  # False=old, True=new.
GameState = Tuple[VersionTuple, StateTuple, bool, bool]


@dataclass(frozen=True)
class ParsedModel:
    path: Path
    sha256: str
    controllable: frozenset[str]
    transitions: Mapping[str, Mapping[str, Tuple[str, ...]]]
    old_processes: Tuple[str, ...]
    new_processes: Tuple[str, ...]
    initial_states: Mapping[str, str]
    alphabets: Mapping[str, frozenset[str]]
    migrations: Mapping[int, Mapping[str, Tuple[str, ...]]]
    migration_actions: Mapping[int, str]
    forbidden_new_actions: frozenset[str]
    forbidden_transition_actions: frozenset[str]
    precedence: Mapping[str, frozenset[str]]


@dataclass(frozen=True)
class ExplicitStrongGame:
    """Complete game constructed by the independent restricted front-end.

    The object is intentionally solver-neutral.  The local oracle consumes it
    as a least fixed point, while the M6 validation campaign translates the
    same complete graph to an external turn-based game solver.
    """

    model: ParsedModel
    initial_states: frozenset[GameState]
    successors: Mapping[GameState, Mapping[str, Tuple[GameState, ...]]]
    goals: frozenset[GameState]
    states: frozenset[GameState]
    loadable: frozenset[StateTuple]

    def is_controllable(self, action: str) -> bool:
        return (
            action in self.model.controllable
            or action == "__start_new_safety__"
            or action in self.model.migration_actions.values()
        )


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def atomic_write_exact(path: Path, payload: bytes) -> None:
    if path.exists():
        if not path.is_file() or path.is_symlink() or path.read_bytes() != payload:
            raise ValueError("existing oracle report differs: " + str(path))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise


def _without_comments(source: str) -> str:
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", "", source)


def _csv_names(value: str) -> Tuple[str, ...]:
    names = tuple(token.strip() for token in value.split(",") if token.strip())
    if not names or any(not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name) for name in names):
        raise ValueError("invalid name list: " + value)
    return names


def _environment(source: str, name: str) -> Tuple[str, ...]:
    matches = re.findall(
        r"^\s*\|\|%s\s*=\s*\((.*?)\)\.\s*$" % re.escape(name),
        source,
        flags=re.MULTILINE,
    )
    if len(matches) != 1:
        raise ValueError("expected exactly one environment composition: " + name)
    processes = tuple(
        token.strip() for token in matches[0].split("||") if token.strip()
    )
    if not processes or any(
        not re.fullmatch(r"[A-Z][A-Z0-9_]*", process)
        for process in processes
    ):
        raise ValueError("unsupported environment composition: " + name)
    return processes


def _named_brace_block(source: str, keyword: str, name: str) -> str:
    matches = re.findall(
        r"\b%s\s+%s\s*=\s*\{(.*?)\n\s*\}"
        % (re.escape(keyword), re.escape(name)),
        source,
        flags=re.DOTALL,
    )
    if len(matches) != 1:
        raise ValueError("expected exactly one %s block: %s" % (keyword, name))
    return matches[0]


def _controller_spec(source: str, name: str) -> Mapping[str, Tuple[str, ...]]:
    body = _named_brace_block(source, "controllerSpec", name)
    fields: Dict[str, Tuple[str, ...]] = {}
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        match = re.fullmatch(
            r"(controllable|safety)\s*=\s*\{([^}]*)\}\s*,?", stripped
        )
        if not match:
            raise ValueError("unsupported %s syntax: %s" % (name, stripped))
        key = match.group(1)
        if key in fields:
            raise ValueError("duplicate %s field: %s" % (name, key))
        fields[key] = _csv_names(match.group(2))
    if fields.get("controllable") != ("ControllableActions",):
        raise ValueError(name + " must bind ControllableActions")
    return fields


def _controller_binding(source: str, controller: str) -> tuple[str, str]:
    matches = re.findall(
        r"^\s*controller\s+\|\|%s\s*=\s*"
        r"([A-Za-z][A-Za-z0-9_]*)~\{([A-Za-z][A-Za-z0-9_]*)\}\.\s*$"
        % re.escape(controller),
        source,
        flags=re.MULTILINE,
    )
    if len(matches) != 1:
        raise ValueError("expected exactly one controller binding: " + controller)
    return matches[0]


def _updating_contract(source: str) -> tuple[str, Mapping[str, str], frozenset[str]]:
    blocks = re.findall(
        r"\bupdatingController\s+([A-Za-z][A-Za-z0-9_]*)\s*=\s*"
        r"\{(.*?)\n\s*\}",
        source,
        flags=re.DOTALL,
    )
    if len(blocks) != 1:
        raise ValueError("expected exactly one updatingController block")
    name, body = blocks[0]
    fields: Dict[str, str] = {}
    flags: Set[str] = set()
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        stripped = stripped.removesuffix(",").strip()
        if "=" not in stripped:
            if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", stripped):
                raise ValueError("unsupported updatingController syntax: " + stripped)
            if stripped in flags:
                raise ValueError("duplicate updatingController flag: " + stripped)
            flags.add(stripped)
            continue
        match = re.fullmatch(
            r"([A-Za-z][A-Za-z0-9_]*)\s*=\s*"
            r"(\{[^}]*\}|[A-Za-z][A-Za-z0-9_]*)",
            stripped,
        )
        if not match:
            raise ValueError("unsupported updatingController field: " + stripped)
        key, value = match.groups()
        if key in fields:
            raise ValueError("duplicate updatingController field: " + key)
        fields[key] = value
    required = {
        "oldController",
        "newController",
        "oldEnvironment",
        "newEnvironment",
        "mapRelation",
        "oldGoal",
        "newGoal",
    }
    optional = {"transition", "precedence"}
    if set(fields).difference(required | optional):
        raise ValueError(
            "unsupported updatingController fields: "
            + ", ".join(sorted(set(fields).difference(required | optional)))
        )
    if not required.issubset(fields):
        raise ValueError(
            "missing updatingController fields: "
            + ", ".join(sorted(required.difference(fields)))
        )
    expected_flags = {"nonblocking", "revised_on_the_fly", "fine_grained"}
    if flags != expected_flags:
        raise ValueError("updatingController flags differ from the oracle scope")
    target_matches = re.findall(
        r"^\s*\|\|UPDATE_CONTROLLER_OTF_FG\s*=\s*"
        r"([A-Za-z][A-Za-z0-9_]*)\.\s*$",
        source,
        flags=re.MULTILINE,
    )
    if target_matches != [name]:
        raise ValueError("target does not bind the parsed updatingController")
    return name, fields, frozenset(flags)


def _brace_names(value: str, field: str) -> Tuple[str, ...]:
    match = re.fullmatch(r"\{([^}]*)\}", value)
    if not match:
        raise ValueError(field + " must be a brace-delimited name list")
    return _csv_names(match.group(1))


def _parse_state_lines(source: str) -> tuple[
    Dict[str, str], Dict[str, Dict[str, Tuple[str, ...]]]
]:
    aliases: Dict[str, str] = {}
    raw_transitions: DefaultDict[str, DefaultDict[str, List[str]]] = defaultdict(
        lambda: defaultdict(list)
    )
    assignment = re.compile(
        r"^\s*([A-Z][A-Z0-9_]*)\s*=\s*(.*?)\s*([,.])\s*$"
    )
    transition = re.compile(
        r"([A-Za-z][A-Za-z0-9_]*)\s*->\s*([A-Z][A-Z0-9_]*)"
    )
    declared: Set[str] = set()
    for line in source.splitlines():
        stripped = line.strip()
        if (
            not stripped
            or stripped.startswith("||")
            or stripped.startswith("relation ")
            or stripped.startswith("controller ")
            or stripped.startswith("controllerSpec ")
            or stripped.startswith("updatingController ")
            or stripped.startswith("set ")
            or stripped.startswith("ltl_property ")
        ):
            continue
        match = assignment.match(line)
        if not match:
            continue
        left, right = match.group(1), match.group(2).strip()
        if left in declared:
            raise ValueError("duplicate process/state declaration: " + left)
        declared.add(left)
        if re.fullmatch(r"[A-Z][A-Z0-9_]*", right):
            aliases[left] = right
            continue
        if not (right.startswith("(") and right.endswith(")")):
            continue
        parsed = transition.findall(right)
        if not parsed:
            raise ValueError("state has no supported transitions: " + left)
        residue = transition.sub("", right[1:-1])
        residue = residue.replace("|", "").strip()
        if residue:
            raise ValueError("unsupported transition syntax in state " + left)
        for action, target in parsed:
            raw_transitions[left][action].append(target)
    transitions: Dict[str, Dict[str, Tuple[str, ...]]] = {
        state: {
            action: tuple(targets) for action, targets in actions.items()
        }
        for state, actions in raw_transitions.items()
    }
    if not transitions:
        raise ValueError("no process states parsed")
    return aliases, transitions


def _process_structure(
    process: str,
    aliases: Mapping[str, str],
    transitions: Mapping[str, Mapping[str, Tuple[str, ...]]],
) -> tuple[str, frozenset[str], frozenset[str]]:
    initial = aliases.get(process, process)
    if initial not in transitions:
        raise ValueError("process initial state is undefined: " + process)
    seen: Set[str] = set()
    alphabet: Set[str] = set()
    queue = deque([initial])
    while queue:
        state = queue.popleft()
        if state in seen:
            continue
        if state not in transitions:
            raise ValueError("transition target is undefined: " + state)
        seen.add(state)
        for action, targets in transitions[state].items():
            alphabet.add(action)
            for target in targets:
                if target not in seen:
                    queue.append(target)
    return initial, frozenset(seen), frozenset(alphabet)


def _relations(
    source: str,
    selected_relations: Sequence[str],
    old_processes: Sequence[str],
    new_processes: Sequence[str],
) -> tuple[Dict[int, Dict[str, Tuple[str, ...]]], Dict[int, str]]:
    relation_blocks = re.findall(
        r"relation\s+([A-Za-z][A-Za-z0-9_]*)\s*=\s*\{(.*?)\}",
        source,
        flags=re.DOTALL,
    )
    entry_pattern = re.compile(
        r"([A-Z][A-Z0-9_]*)@([A-Z][A-Z0-9_]*)\s*=\s*"
        r"([A-Za-z][A-Za-z0-9_]*)\s*->\s*"
        r"([A-Z][A-Z0-9_]*)@([A-Z][A-Z0-9_]*)"
    )
    by_old_process = {process: index for index, process in enumerate(old_processes)}
    targets: DefaultDict[int, DefaultDict[str, List[str]]] = defaultdict(
        lambda: defaultdict(list)
    )
    actions: Dict[int, str] = {}
    observed_relations: Set[str] = set()
    relation_components: Set[int] = set()
    observed_entries: Set[Tuple[str, str, str, str, str]] = set()
    for relation_name, body in relation_blocks:
        if relation_name in observed_relations:
            raise ValueError("duplicate relation declaration: " + relation_name)
        entries = entry_pattern.findall(body)
        residue = entry_pattern.sub("", body).replace(",", "").strip()
        if not entries or residue:
            raise ValueError("unsupported relation syntax: " + relation_name)
        observed_relations.add(relation_name)
        if relation_name not in selected_relations:
            raise ValueError("unselected relation is outside the oracle scope")
        components_in_relation: Set[int] = set()
        for entry in entries:
            old_state, old_process, action, new_state, new_process = entry
            if entry in observed_entries:
                raise ValueError("duplicate relation entry")
            observed_entries.add(entry)
            if old_process not in by_old_process:
                raise ValueError("relation names an unknown old process")
            index = by_old_process[old_process]
            components_in_relation.add(index)
            if new_processes[index] != new_process:
                raise ValueError("relation crosses component identities")
            if index in actions and actions[index] != action:
                raise ValueError("component uses multiple migration actions")
            actions[index] = action
            targets[index][old_state].append(new_state)
        if len(components_in_relation) != 1:
            raise ValueError("one relation must describe exactly one component")
        component = next(iter(components_in_relation))
        if component in relation_components:
            raise ValueError("a component is selected by multiple relations")
        relation_components.add(component)
    if observed_relations != set(selected_relations):
        raise ValueError("mapRelation does not match the relation declarations")
    if len(selected_relations) != len(set(selected_relations)):
        raise ValueError("mapRelation contains a duplicate relation")
    if len(selected_relations) != len(old_processes):
        raise ValueError("mapRelation must select one relation per component")
    if len(actions) != len(old_processes):
        raise ValueError("each component must have one parsed migration relation")
    immutable = {
        index: {state: tuple(values) for state, values in mapping.items()}
        for index, mapping in targets.items()
    }
    return immutable, actions


def _assert_acyclic_precedence(
    actions: Set[str], predecessors: Mapping[str, Set[str]]
) -> None:
    outgoing: DefaultDict[str, Set[str]] = defaultdict(set)
    indegree = {action: 0 for action in actions}
    for successor, values in predecessors.items():
        for predecessor in values:
            if predecessor == successor:
                raise ValueError("precedence is reflexive")
            if successor not in outgoing[predecessor]:
                outgoing[predecessor].add(successor)
                indegree[successor] += 1
    queue = deque(sorted(action for action, degree in indegree.items() if degree == 0))
    visited = 0
    while queue:
        action = queue.popleft()
        visited += 1
        for successor in sorted(outgoing[action]):
            indegree[successor] -= 1
            if indegree[successor] == 0:
                queue.append(successor)
    if visited != len(actions):
        raise ValueError("precedence contains a cycle")


def parse_model(path: Path) -> ParsedModel:
    payload = path.read_bytes()
    raw_source = payload.decode("utf-8")
    source = _without_comments(raw_source)
    controllable_matches = re.findall(
        r"set\s+ControllableActions\s*=\s*\{([^}]*)\}", source
    )
    if len(controllable_matches) != 1:
        raise ValueError("expected exactly one ControllableActions declaration")
    controllable_names = _csv_names(controllable_matches[0])
    if len(set(controllable_names)) != len(controllable_names):
        raise ValueError("ControllableActions contains a duplicate")
    controllable = frozenset(controllable_names)
    _, updating_fields, _ = _updating_contract(source)
    if updating_fields["oldController"] != "OldController":
        raise ValueError("oldController must bind OldController")
    if updating_fields["newController"] != "NewController":
        raise ValueError("newController must bind NewController")
    if updating_fields["oldGoal"] != "OldSpec":
        raise ValueError("oldGoal must bind OldSpec")
    if updating_fields["newGoal"] != "NewSpec":
        raise ValueError("newGoal must bind NewSpec")
    old_processes = _environment(source, "OldEnvironment")
    new_processes = _environment(source, "NewEnvironment")
    if len(old_processes) != len(new_processes):
        raise ValueError("old/new component counts differ")
    if _brace_names(updating_fields["oldEnvironment"], "oldEnvironment") != old_processes:
        raise ValueError("oldEnvironment field differs from OldEnvironment")
    if _brace_names(updating_fields["newEnvironment"], "newEnvironment") != new_processes:
        raise ValueError("newEnvironment field differs from NewEnvironment")
    if _controller_binding(source, "OldController") != (
        "OldEnvironment",
        "OldSpec",
    ):
        raise ValueError("OldController does not bind OldEnvironment and OldSpec")
    if _controller_binding(source, "NewController") != (
        "NewEnvironment",
        "NewSpec",
    ):
        raise ValueError("NewController does not bind NewEnvironment and NewSpec")
    old_spec_fields = _controller_spec(source, "OldSpec")
    new_spec_fields = _controller_spec(source, "NewSpec")
    if old_spec_fields.get("safety"):
        raise ValueError("old safety is outside the registered oracle scope")
    aliases, transitions = _parse_state_lines(source)
    initial_states: Dict[str, str] = {}
    alphabets: Dict[str, frozenset[str]] = {}
    process_states: Dict[str, frozenset[str]] = {}
    for process in old_processes + new_processes:
        initial, states, alphabet = _process_structure(
            process, aliases, transitions
        )
        initial_states[process] = initial
        process_states[process] = states
        alphabets[process] = alphabet
    selected_relations = _brace_names(
        updating_fields["mapRelation"], "mapRelation"
    )
    migrations, migration_actions = _relations(
        source, selected_relations, old_processes, new_processes
    )
    migration_action_values = tuple(migration_actions.values())
    if len(set(migration_action_values)) != len(old_processes):
        raise ValueError("migration actions must be unique per component")
    ordinary_actions = set().union(
        *(alphabets[process] for process in old_processes + new_processes)
    )
    if set(migration_action_values).intersection(ordinary_actions):
        raise ValueError("migration actions must be disjoint from ordinary actions")
    for index, mapping in migrations.items():
        if not set(mapping).issubset(process_states[old_processes[index]]):
            raise ValueError("migration source is outside its old component")
        if not {
            target for targets in mapping.values() for target in targets
        }.issubset(process_states[new_processes[index]]):
            raise ValueError("migration target is outside its new component")

    property_pairs = re.findall(
        r"ltl_property\s+([A-Za-z][A-Za-z0-9_]*)\s*=\s*"
        r"\[\]\s*\(\s*!([A-Za-z][A-Za-z0-9_]*)\s*\)",
        source,
    )
    declared_property_names = re.findall(
        r"\bltl_property\s+([A-Za-z][A-Za-z0-9_]*)\s*=", source
    )
    if len(property_pairs) != len(declared_property_names):
        raise ValueError("unsupported ltl_property syntax")
    if len({name for name, _ in property_pairs}) != len(property_pairs):
        raise ValueError("duplicate ltl_property declaration")
    property_actions = dict(property_pairs)
    safety_names = new_spec_fields.get("safety", ())
    unknown = [name for name in safety_names if name not in property_actions]
    if unknown:
        raise ValueError("unsupported new safety property: " + ", ".join(unknown))
    forbidden_new_actions = frozenset(property_actions[name] for name in safety_names)
    if not forbidden_new_actions.issubset(controllable):
        raise ValueError("registered safety action must be controllable")
    transition_name = updating_fields.get("transition")
    transition_names = (transition_name,) if transition_name else ()
    unknown_transition = [
        name for name in transition_names if name not in property_actions
    ]
    if unknown_transition:
        raise ValueError(
            "unsupported transition safety property: "
            + ", ".join(unknown_transition)
        )
    forbidden_transition_actions = frozenset(
        property_actions[name] for name in transition_names
    )
    precedence_sets: DefaultDict[str, Set[str]] = defaultdict(set)
    precedence_value = updating_fields.get("precedence")
    if precedence_value:
        match = re.fullmatch(r"\{([^}]*)\}", precedence_value)
        if not match:
            raise ValueError("precedence must be brace-delimited")
        tokens = [token.strip() for token in match.group(1).split(",") if token.strip()]
        if not tokens:
            raise ValueError("precedence cannot be empty")
        for token in tokens:
            fields = [field.strip() for field in token.split("<")]
            if len(fields) != 2 or any(
                not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", field)
                for field in fields
            ):
                raise ValueError("unsupported precedence syntax")
            predecessor, successor = fields
            precedence_sets[successor].add(predecessor)
    migration_action_set = set(migration_actions.values())
    if any(
        action not in migration_action_set
        for action in set(precedence_sets).union(
            *(set(values) for values in precedence_sets.values())
        )
    ):
        raise ValueError("precedence names a non-migration action")
    _assert_acyclic_precedence(migration_action_set, precedence_sets)
    return ParsedModel(
        path=path,
        sha256=sha256_bytes(payload),
        controllable=controllable,
        transitions=transitions,
        old_processes=old_processes,
        new_processes=new_processes,
        initial_states=initial_states,
        alphabets=alphabets,
        migrations=migrations,
        migration_actions=migration_actions,
        forbidden_new_actions=forbidden_new_actions,
        forbidden_transition_actions=forbidden_transition_actions,
        precedence={
            action: frozenset(values)
            for action, values in precedence_sets.items()
        },
    )


def _ordinary_successors(
    model: ParsedModel,
    versions: VersionTuple,
    local_states: StateTuple,
    blocked_actions: frozenset[str] = frozenset(),
) -> Dict[str, Tuple[StateTuple, ...]]:
    processes = tuple(
        model.new_processes[index] if is_new else model.old_processes[index]
        for index, is_new in enumerate(versions)
    )
    candidate_actions = sorted(
        set().union(*(model.alphabets[process] for process in processes))
        - set(blocked_actions)
    )
    result: Dict[str, Tuple[StateTuple, ...]] = {}
    for action in candidate_actions:
        participants = [
            index
            for index, process in enumerate(processes)
            if action in model.alphabets[process]
        ]
        if not participants:
            continue
        choices: List[Tuple[str, ...]] = []
        enabled = True
        for index, (process, state) in enumerate(zip(processes, local_states)):
            if index not in participants:
                choices.append((state,))
                continue
            targets = model.transitions[state].get(action, ())
            if not targets:
                enabled = False
                break
            choices.append(tuple(targets))
        if enabled:
            result[action] = tuple(tuple(values) for values in itertools.product(*choices))
    return result


def _endpoint_reachable(
    model: ParsedModel, new: bool, blocked_actions: frozenset[str]
) -> frozenset[StateTuple]:
    processes = model.new_processes if new else model.old_processes
    versions = tuple(new for _ in processes)
    initial = tuple(model.initial_states[process] for process in processes)
    seen: Set[StateTuple] = {initial}
    queue = deque([initial])
    while queue:
        current = queue.popleft()
        for targets in _ordinary_successors(
            model, versions, current, blocked_actions
        ).values():
            for target in targets:
                if target not in seen:
                    seen.add(target)
                    queue.append(target)
    return frozenset(seen)


def _game_successors(
    model: ParsedModel,
    state: GameState,
) -> Dict[str, Tuple[GameState, ...]]:
    versions, locals_, safety_started, violated = state
    if violated:
        return {}
    result: Dict[str, Tuple[GameState, ...]] = {}
    for action, local_targets in _ordinary_successors(
        model, versions, locals_
    ).items():
        next_violated = (
            action in model.forbidden_transition_actions
            or (safety_started and action in model.forbidden_new_actions)
        )
        result[action] = tuple(
            (versions, target, safety_started, next_violated)
            for target in local_targets
        )
    for index, is_new in enumerate(versions):
        if is_new:
            continue
        action = model.migration_actions[index]
        completed_actions = {
            model.migration_actions[completed_index]
            for completed_index, completed in enumerate(versions)
            if completed
        }
        if not model.precedence.get(action, frozenset()).issubset(
            completed_actions
        ):
            continue
        targets = model.migrations[index].get(locals_[index], ())
        if not targets:
            continue
        next_versions = list(versions)
        next_versions[index] = True
        states = []
        for target in targets:
            next_locals = list(locals_)
            next_locals[index] = target
            states.append(
                (tuple(next_versions), tuple(next_locals), safety_started, False)
            )
        result[action] = tuple(states)
    if model.forbidden_new_actions and not safety_started:
        result["__start_new_safety__"] = (
            (versions, locals_, True, False),
        )
    return result


def build_explicit_game(path: Path) -> ExplicitStrongGame:
    """Parse ``path`` and construct the complete reachable FG-DUCS game."""
    model = parse_model(path)
    old_roots = _endpoint_reachable(model, new=False, blocked_actions=frozenset())
    loadable = _endpoint_reachable(
        model, new=True, blocked_actions=model.forbidden_new_actions
    )
    initial_versions = tuple(False for _ in model.old_processes)
    initially_started = not bool(model.forbidden_new_actions)
    initial_states: Set[GameState] = {
        (initial_versions, root, initially_started, False) for root in old_roots
    }
    all_new = tuple(True for _ in model.new_processes)

    successors: Dict[GameState, Dict[str, Tuple[GameState, ...]]] = {}
    seen: Set[GameState] = set(initial_states)
    queue = deque(sorted(initial_states))
    while queue:
        state = queue.popleft()
        outgoing = _game_successors(model, state)
        successors[state] = outgoing
        for action in sorted(outgoing):
            for target in sorted(outgoing[action]):
                if target not in seen:
                    seen.add(target)
                    queue.append(target)

    goals = {
        state
        for state in seen
        if state[0] == all_new
        and state[1] in loadable
        and state[2]
        and not state[3]
    }
    return ExplicitStrongGame(
        model=model,
        initial_states=frozenset(initial_states),
        successors=successors,
        goals=frozenset(goals),
        states=frozenset(seen),
        loadable=frozenset(loadable),
    )


def analyze_model(path: Path) -> Dict[str, Any]:
    game = build_explicit_game(path)
    model = game.model
    winning = set(game.goals)
    changed = True
    layers = 0
    while changed:
        changed = False
        add: Set[GameState] = set()
        for state in game.states - winning:
            if state[3]:
                continue
            outgoing = game.successors.get(state, {})
            uncontrollable = [
                targets
                for action, targets in outgoing.items()
                if not game.is_controllable(action)
            ]
            if uncontrollable:
                union = {target for targets in uncontrollable for target in targets}
                if union and union.issubset(winning):
                    add.add(state)
                continue
            controllable_witness = any(
                targets and set(targets).issubset(winning)
                for targets in outgoing.values()
            )
            if controllable_witness:
                add.add(state)
        if add:
            winning.update(add)
            layers += 1
            changed = True
    initial_winning = game.initial_states.issubset(winning)
    outcome_count = sum(
        len(targets)
        for outgoing in game.successors.values()
        for targets in outgoing.values()
    )
    return {
        "model": path.name,
        "path": str(path),
        "sha256": model.sha256,
        "decision": "realizable" if initial_winning else "unrealizable",
        "q0_states": len(game.initial_states),
        "loadable_new_endpoint_states": len(game.loadable),
        "explicit_game_states": len(game.states),
        "explicit_game_action_outcomes": outcome_count,
        "goal_states": len(game.goals),
        "winning_states": len(winning),
        "losing_states": len(game.states - winning),
        "winning_layers_after_goal": layers,
        "old_components": len(model.old_processes),
        "new_safety_forbidden_actions": sorted(model.forbidden_new_actions),
        "transition_safety_forbidden_actions": sorted(
            model.forbidden_transition_actions
        ),
        "precedence_edges": sum(len(values) for values in model.precedence.values()),
        "basis": (
            "raw UTF-8 LTS; independent restricted parser; explicit endpoint "
            "composition; exact mixed-version successors; strong-reachability "
            "least fixed point"
        ),
    }


def analyze_manifest(manifest_path: Path) -> Dict[str, Any]:
    manifest_payload = manifest_path.read_bytes()
    manifest = json.loads(manifest_payload.decode("utf-8"))
    records = manifest.get("models")
    if not isinstance(records, list) or not records:
        raise ValueError("manifest has no models")
    campaign = manifest_path.resolve().parents[2]
    results = []
    for record in records:
        relative = Path(str(record.get("path", "")))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("unsafe model path in manifest")
        path = (campaign / relative).resolve()
        if not path.is_file() or path.is_symlink():
            raise ValueError("missing or unsafe model: " + str(path))
        try:
            path.relative_to(campaign)
        except ValueError as error:
            raise ValueError("model escapes campaign") from error
        payload = path.read_bytes()
        if (
            record.get("bytes") != len(payload)
            or record.get("sha256") != sha256_bytes(payload)
        ):
            raise ValueError("manifest hash mismatch: " + str(path))
        result = analyze_model(path)
        result["path"] = relative.as_posix()
        result["model_id"] = str(record.get("id", ""))
        result["registered_expected_decision"] = str(
            record.get("expected_decision", "")
        )
        result["registered_expected_q0"] = record.get("expected_q0")
        result["agrees_with_registration"] = (
            result["decision"] == result["registered_expected_decision"]
            and result["q0_states"] == result["registered_expected_q0"]
        )
        if not result["agrees_with_registration"]:
            raise ValueError("raw oracle disagrees with registration: " + result["model_id"])
        results.append(result)
    return {
        "schema_version": ORACLE_SCHEMA,
        "oracle_id": ORACLE_ID,
        "manifest": manifest_path.name,
        "manifest_sha256": sha256_bytes(manifest_payload),
        "model_count": len(results),
        "all_registered_expectations_confirmed": True,
        "shared_code_components": [],
        "shared_evidence_inputs": [
            "registered raw LTS bytes",
            "registration manifest and expected decision",
        ],
        "scope": (
            "Only the fail-closed FSP subset used by the registered decisive "
            "evidence families; not a general FG-DUCS front end"
        ),
        "models": results,
    }


def analyze_semantic_manifest(
    manifest_path: Path, java_runs_path: Path | None = None
) -> Dict[str, Any]:
    """Check the 41 registered RQ1 semantic inputs from raw LTS bytes."""
    manifest_payload = manifest_path.read_bytes()
    manifest = json.loads(manifest_payload.decode("utf-8"))
    records = manifest.get("models")
    if not isinstance(records, list) or not records:
        raise ValueError("semantic manifest has no models")
    results: List[Dict[str, Any]] = []
    by_id: Dict[str, Dict[str, Any]] = {}
    for record in records:
        relative = Path(str(record.get("path", "")))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("unsafe semantic-model path")
        path = (manifest_path.parent / relative).resolve()
        if not path.is_file() or path.is_symlink():
            raise ValueError("missing semantic model: " + str(path))
        payload = path.read_bytes()
        if (
            record.get("bytes") != len(payload)
            or record.get("sha256") != sha256_bytes(payload)
        ):
            raise ValueError("semantic manifest hash mismatch: " + str(path))
        result = analyze_model(path)
        result["path"] = relative.as_posix()
        model_id = str(record.get("id", ""))
        if not model_id or model_id in by_id:
            raise ValueError("invalid or duplicate semantic model id")
        result.update(
            {
                "model_id": model_id,
                "base_case": str(record.get("base_case", "")),
                "variant": str(record.get("variant", "")),
                "registered_expected_decision": str(
                    record.get("expected_decision", "")
                ),
            }
        )
        result["agrees_with_registration"] = (
            result["decision"] == result["registered_expected_decision"]
        )
        if not result["agrees_with_registration"]:
            raise ValueError(
                "raw oracle disagrees with semantic registration: " + model_id
            )
        by_id[model_id] = result
        results.append(result)

    java_comparisons = 0
    java_methods: Set[str] = set()
    if java_runs_path is not None:
        with java_runs_path.open("r", encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        observed: DefaultDict[str, Dict[str, str]] = defaultdict(dict)
        for row in rows:
            if row.get("model_family") != "rq1_semantic_boundary_v2":
                continue
            raw_id = str(row.get("model_id", ""))
            model_id = raw_id.removeprefix("semantic_")
            method = str(row.get("method_id", ""))
            decision = str(row.get("revised_decision", ""))
            if model_id not in by_id or not method or not decision:
                raise ValueError("invalid Java semantic result identity")
            if method in observed[model_id]:
                raise ValueError("duplicate Java semantic result")
            observed[model_id][method] = decision
            java_methods.add(method)
            java_comparisons += 1
        if set(observed) != set(by_id):
            raise ValueError("Java semantic result coverage differs from manifest")
        for model_id, method_decisions in observed.items():
            if set(method_decisions.values()) != {by_id[model_id]["decision"]}:
                raise ValueError("raw oracle disagrees with Java: " + model_id)
            by_id[model_id]["java_decisions"] = dict(sorted(method_decisions.items()))

    return {
        "schema_version": ORACLE_SCHEMA,
        "oracle_id": ORACLE_ID,
        "manifest": manifest_path.name,
        "manifest_sha256": sha256_bytes(manifest_payload),
        "java_runs": java_runs_path.name if java_runs_path else "",
        "java_runs_sha256": (
            sha256_bytes(java_runs_path.read_bytes()) if java_runs_path else ""
        ),
        "model_count": len(results),
        "raw_oracle_java_comparisons": java_comparisons,
        "java_methods": sorted(java_methods),
        "all_registered_expectations_confirmed": True,
        "all_java_decisions_confirmed": java_runs_path is not None,
        "shared_code_components": [],
        "shared_evidence_inputs": [
            "registered raw LTS bytes",
            "registration manifest and expected decision",
            "Java decision CSV used only for the final comparison",
        ],
        "scope": (
            "Fail-closed raw FSP subset covering the registered RQ1 semantic "
            "boundary suite: process transitions, synchronous product, "
            "controllability, transfer relations, single-action safety, and "
            "migration precedence"
        ),
        "models": results,
    }


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--manifest", type=Path)
    group.add_argument("--semantic-manifest", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--model", type=Path)
    parser.add_argument("--java-runs", type=Path)
    return parser.parse_args()


def main() -> int:
    args = arguments()
    if args.model is not None:
        result: Dict[str, Any] = {
            "schema_version": ORACLE_SCHEMA,
            "oracle_id": ORACLE_ID,
            "model_result": analyze_model(args.model.resolve()),
        }
    elif args.semantic_manifest is not None:
        result = analyze_semantic_manifest(
            args.semantic_manifest.resolve(),
            args.java_runs.resolve() if args.java_runs else None,
        )
    else:
        result = analyze_manifest(args.manifest.resolve())
    payload = canonical_json_bytes(result)
    if args.output is None:
        print(payload.decode("utf-8"), end="")
    else:
        atomic_write_exact(args.output.resolve(), payload)
        print(json.dumps({"status": "PASS", "output": str(args.output.resolve())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
