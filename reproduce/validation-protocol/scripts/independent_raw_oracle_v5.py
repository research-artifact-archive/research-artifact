#!/usr/bin/env python3
"""Observer-exact successor semantics for the registered C1 raw-LTS subset.

Version 4 deliberately quotiented away action-proposition observer states.  A
decision oracle may soundly use that quotient, but an exact comparison with the
Java game exporter must retain the post-event residual used at a later
``startNewSpec`` boundary.  This module leaves the frozen v4 implementation
untouched and adds precisely that residual to the independent raw state.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Mapping, Set, Tuple

from independent_raw_oracle import (
    ParsedModel,
    StateTuple,
    VersionTuple,
    _controller_binding,
    _controller_spec,
    _endpoint_reachable,
    _ordinary_successors,
    _updating_contract,
    _without_comments,
    parse_model,
)


ORACLE_ID = "python-raw-fsp-subset-observer-exact-v5"
ObserverState = str  # empty string means that no forbidden action is current.
GameStateV5 = Tuple[VersionTuple, StateTuple, bool, bool, ObserverState]


@dataclass(frozen=True)
class ExplicitStrongGameV5:
    model: ParsedModel
    start_action: str | None
    initial_states: frozenset[GameStateV5]
    successors: Mapping[GameStateV5, Mapping[str, Tuple[GameStateV5, ...]]]
    goals: frozenset[GameStateV5]
    states: frozenset[GameStateV5]
    loadable: frozenset[StateTuple]

    def is_controllable(self, action: str) -> bool:
        return (
            action in self.model.controllable
            or action == self.start_action
            or action in self.model.migration_actions.values()
        )


def _new_safety_requirement(path: Path, model: ParsedModel) -> str | None:
    source = _without_comments(path.read_text(encoding="utf-8"))
    _, fields, _ = _updating_contract(source)
    new_controller = fields["newController"]
    _, specification = _controller_binding(source, new_controller)
    safety = _controller_spec(source, specification).get("safety", ())
    if model.forbidden_new_actions:
        if len(safety) != 1:
            raise ValueError(
                "observer-exact subset requires exactly one new safety requirement"
            )
        return safety[0]
    if safety:
        raise ValueError("new safety declaration has no parsed forbidden actions")
    return None


def _successors(
    game: ExplicitStrongGameV5,
    state: GameStateV5,
) -> Dict[str, Tuple[GameStateV5, ...]]:
    model = game.model
    versions, locals_, safety_started, violated, observer = state
    if violated:
        return {}
    result: Dict[str, Tuple[GameStateV5, ...]] = {}
    for action, local_targets in _ordinary_successors(
        model, versions, locals_
    ).items():
        next_observer = action if action in model.forbidden_new_actions else ""
        next_violated = (
            action in model.forbidden_transition_actions
            or (safety_started and action in model.forbidden_new_actions)
        )
        result[action] = tuple(
            (versions, target, safety_started, next_violated, next_observer)
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
        if not model.precedence.get(action, frozenset()).issubset(completed_actions):
            continue
        targets = model.migrations[index].get(locals_[index], ())
        if not targets:
            continue
        next_versions = list(versions)
        next_versions[index] = True
        next_states = []
        for target in targets:
            next_locals = list(locals_)
            next_locals[index] = target
            next_states.append((
                tuple(next_versions),
                tuple(next_locals),
                safety_started,
                False,
                observer,
            ))
        result[action] = tuple(next_states)
    if (
        game.start_action is not None
        and not safety_started
        and observer not in model.forbidden_new_actions
    ):
        result[game.start_action] = (
            (versions, locals_, True, False, observer),
        )
    return result


def build_explicit_game(path: Path) -> ExplicitStrongGameV5:
    path = path.resolve()
    model = parse_model(path)
    requirement = _new_safety_requirement(path, model)
    start_action = (
        "startNewSpec_" + requirement if requirement is not None else None
    )
    old_roots = _endpoint_reachable(model, new=False, blocked_actions=frozenset())
    loadable = _endpoint_reachable(
        model, new=True, blocked_actions=model.forbidden_new_actions
    )
    initial_versions = tuple(False for _ in model.old_processes)
    initially_started = not bool(model.forbidden_new_actions)
    initial_states: Set[GameStateV5] = {
        (initial_versions, root, initially_started, False, "")
        for root in old_roots
    }
    provisional = ExplicitStrongGameV5(
        model=model,
        start_action=start_action,
        initial_states=frozenset(initial_states),
        successors={},
        goals=frozenset(),
        states=frozenset(initial_states),
        loadable=loadable,
    )
    successors: Dict[GameStateV5, Dict[str, Tuple[GameStateV5, ...]]] = {}
    seen: Set[GameStateV5] = set(initial_states)
    queue = deque(sorted(initial_states))
    while queue:
        state = queue.popleft()
        outgoing = _successors(provisional, state)
        successors[state] = outgoing
        for action in sorted(outgoing):
            for target in sorted(outgoing[action]):
                if target not in seen:
                    seen.add(target)
                    queue.append(target)
    all_new = tuple(True for _ in model.new_processes)
    goals = frozenset(
        state
        for state in seen
        if state[0] == all_new
        and state[1] in loadable
        and state[2]
        and not state[3]
    )
    return ExplicitStrongGameV5(
        model=model,
        start_action=start_action,
        initial_states=frozenset(initial_states),
        successors=successors,
        goals=goals,
        states=frozenset(seen),
        loadable=loadable,
    )


def legacy_projection(state: GameStateV5) -> tuple:
    """Expose the exact v4 quotient for regression tests only."""

    return state[:4]
