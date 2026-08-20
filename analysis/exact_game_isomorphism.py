#!/usr/bin/env python3
"""Exact isomorphism checks for serialized FG-DUCS reachability games.

The checker treats an enabled action together with its complete successor set
as one labelled hyperedge.  Color refinement is only a pruning step: a PASS is
emitted solely after an explicit bijection has been constructed and every
root, state flag, action owner, and complete successor bucket has been checked
under that bijection.  Ambiguous color classes are individualized and searched
exactly.  Reaching the configured search bound is inconclusive, never a PASS.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Sequence, Tuple


BUNDLE_SCHEMA = "fse2027-independent-strong-game-bundle-v1"
COMPARISON_SCHEMA = "fse2027-exact-game-isomorphism-result-v1"


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


@dataclass(frozen=True)
class StateRecord:
    identifier: str
    initial: bool
    safe: bool
    goal: bool
    physical: str
    active_testers: Mapping[str, str]
    pending_actions: Tuple[str, ...]


@dataclass(frozen=True)
class Bucket:
    source: str
    action: str
    controllable: bool
    targets: Tuple[str, ...]


@dataclass(frozen=True)
class GameBundle:
    semantics_id: str
    claimed_decision: str
    states: Mapping[str, StateRecord]
    initials: frozenset[str]
    safe: frozenset[str]
    goals: frozenset[str]
    buckets: Mapping[Tuple[str, str], Bucket]
    raw: Mapping[str, Any]


@dataclass(frozen=True)
class FixedPoint:
    decision: str
    rank: Mapping[str, int]
    losing: frozenset[str]
    winning_actions: Mapping[str, Tuple[str, ...]]
    layers_after_goal: int


@dataclass
class SearchBudget:
    maximum_nodes: int
    visited_nodes: int = 0

    def consume(self) -> None:
        self.visited_nodes += 1
        if self.visited_nodes > self.maximum_nodes:
            raise InconclusiveIsomorphism(
                "exact isomorphism search exceeded the registered node bound"
            )


class InconclusiveIsomorphism(RuntimeError):
    """The exact search could not finish within the registered bound."""


class NonIsomorphic(ValueError):
    """The two serialized games violate an exact isomorphism obligation."""


def _exact_string_list(value: Any, label: str, *, allow_empty: bool = True) -> Tuple[str, ...]:
    if (
        not isinstance(value, list)
        or (not allow_empty and not value)
        or any(not isinstance(item, str) or not item for item in value)
        or len(value) != len(set(value))
    ):
        raise ValueError(label + " must be an exact string set")
    return tuple(value)


def _exact_nonnegative_int(raw: Mapping[str, Any], field: str) -> int:
    value = raw.get(field)
    if type(value) is not int or value < 0:
        raise ValueError(field + " must be an exact nonnegative JSON integer")
    return value


def load_game_bundle(
    raw: Mapping[str, Any],
    *,
    allowed_semantics: Iterable[str] | None = None,
) -> GameBundle:
    """Parse and independently validate one complete reachable game bundle."""

    if not isinstance(raw, dict) or raw.get("schema_version") != BUNDLE_SCHEMA:
        raise ValueError("unsupported independent-game bundle schema")
    semantics_id = raw.get("semantics_id")
    if not isinstance(semantics_id, str) or not semantics_id:
        raise ValueError("bundle semantics_id is missing")
    if allowed_semantics is not None and semantics_id not in set(allowed_semantics):
        raise ValueError("bundle semantics_id is not registered: " + semantics_id)
    if raw.get("policy_restriction") != "full_fg":
        raise ValueError("bundle is not the registered full-FG game")
    claimed = raw.get("claimed_decision")
    if claimed not in {"realizable", "unrealizable"}:
        raise ValueError("bundle claimed_decision is invalid")

    rows = raw.get("states")
    if not isinstance(rows, list) or not rows:
        raise ValueError("bundle states must be a non-empty array")
    states: Dict[str, StateRecord] = {}
    initials: set[str] = set()
    safe: set[str] = set()
    goals: set[str] = set()
    for raw_row in rows:
        if not isinstance(raw_row, dict):
            raise ValueError("bundle state is not an object")
        identifier = raw_row.get("id")
        if not isinstance(identifier, str) or not identifier or identifier in states:
            raise ValueError("bundle state identifier is empty or duplicated")
        for field in ("initial", "safe", "goal"):
            if type(raw_row.get(field)) is not bool:
                raise ValueError("state flag is not an exact boolean: " + field)
        physical = raw_row.get("physical")
        if not isinstance(physical, str):
            raise ValueError("state physical signature is not a string")
        tester_rows = raw_row.get("active_testers")
        if not isinstance(tester_rows, dict) or any(
            not isinstance(key, str)
            or not key
            or not isinstance(value, (str, int))
            for key, value in tester_rows.items()
        ):
            raise ValueError("state active_testers is not a typed object")
        pending = _exact_string_list(
            raw_row.get("pending_actions"), "state pending_actions"
        )
        record = StateRecord(
            identifier=identifier,
            initial=raw_row["initial"],
            safe=raw_row["safe"],
            goal=raw_row["goal"],
            physical=physical,
            active_testers={key: str(value) for key, value in tester_rows.items()},
            pending_actions=pending,
        )
        states[identifier] = record
        if record.initial:
            initials.add(identifier)
        if record.safe:
            safe.add(identifier)
        if record.goal:
            goals.add(identifier)

    state_ids = set(states)
    if not initials or not initials.issubset(safe):
        raise ValueError("bundle Q0 must be a non-empty safe set")
    if not goals.issubset(safe):
        raise ValueError("bundle Goal contains an unsafe state")

    def registered_ids(field: str, observed: set[str], *, allow_empty: bool) -> None:
        values = _exact_string_list(raw.get(field), field, allow_empty=allow_empty)
        if set(values) != observed or any(value not in state_ids for value in values):
            raise ValueError(field + " disagrees with state flags")

    registered_ids("initial_state_ids", initials, allow_empty=False)
    registered_ids("goal_state_ids", goals, allow_empty=True)

    bucket_rows = raw.get("buckets")
    if not isinstance(bucket_rows, list):
        raise ValueError("bundle buckets must be an array")
    buckets: Dict[Tuple[str, str], Bucket] = {}
    action_control: Dict[str, bool] = {}
    for raw_row in bucket_rows:
        if not isinstance(raw_row, dict):
            raise ValueError("bundle bucket is not an object")
        source = raw_row.get("source")
        action = raw_row.get("action")
        control = raw_row.get("controllable")
        targets = _exact_string_list(
            raw_row.get("targets"), "bundle bucket targets", allow_empty=False
        )
        if (
            not isinstance(source, str)
            or source not in state_ids
            or not isinstance(action, str)
            or not action
            or type(control) is not bool
            or (source, action) in buckets
            or any(target not in state_ids for target in targets)
        ):
            raise ValueError("bundle bucket identity or target is invalid")
        if source not in safe or source in goals:
            raise ValueError("unsafe/Goal state has an enabled exported bucket")
        previous = action_control.setdefault(action, control)
        if previous != control:
            raise ValueError("one action has inconsistent controllability")
        buckets[(source, action)] = Bucket(
            source=source,
            action=action,
            controllable=control,
            targets=targets,
        )

    if _exact_nonnegative_int(raw, "state_count") != len(states):
        raise ValueError("state_count disagrees with states")
    if _exact_nonnegative_int(raw, "controllable_bucket_count") != sum(
        bucket.controllable for bucket in buckets.values()
    ):
        raise ValueError("controllable bucket count is inconsistent")
    if _exact_nonnegative_int(raw, "uncontrollable_bucket_count") != sum(
        not bucket.controllable for bucket in buckets.values()
    ):
        raise ValueError("uncontrollable bucket count is inconsistent")
    if _exact_nonnegative_int(raw, "outcome_edge_count") != sum(
        len(bucket.targets) for bucket in buckets.values()
    ):
        raise ValueError("outcome edge count is inconsistent")
    if _exact_nonnegative_int(raw, "query_count") < len(buckets):
        raise ValueError("query_count is smaller than enabled bucket count")

    reachable = set(initials)
    pending = list(sorted(initials))
    outgoing_targets: MutableMapping[str, List[str]] = defaultdict(list)
    for bucket in buckets.values():
        outgoing_targets[bucket.source].extend(bucket.targets)
    while pending:
        source = pending.pop()
        for target in outgoing_targets.get(source, []):
            if target not in reachable:
                reachable.add(target)
                pending.append(target)
    if reachable != state_ids:
        raise ValueError("bundle has states outside exact Q0 reachability")

    return GameBundle(
        semantics_id=semantics_id,
        claimed_decision=claimed,
        states=states,
        initials=frozenset(initials),
        safe=frozenset(safe),
        goals=frozenset(goals),
        buckets=buckets,
        raw=raw,
    )


def fixed_point(game: GameBundle) -> FixedPoint:
    """Recompute the strong reachability attractor and its canonical witness."""

    rank: Dict[str, int] = {state: 0 for state in game.goals}
    layer = 0
    while True:
        added: set[str] = set()
        winning = set(rank)
        for state in sorted(game.safe - winning):
            rows = [
                bucket for (source, _), bucket in game.buckets.items()
                if source == state
            ]
            uncontrollable = [row for row in rows if not row.controllable]
            if uncontrollable:
                outcomes = {
                    target for row in uncontrollable for target in row.targets
                }
                if outcomes and outcomes.issubset(winning):
                    added.add(state)
                continue
            if any(set(row.targets).issubset(winning) for row in rows if row.controllable):
                added.add(state)
        if not added:
            break
        layer += 1
        for state in added:
            rank[state] = layer

    winning_actions: Dict[str, Tuple[str, ...]] = {}
    for state in sorted(rank):
        if state in game.goals:
            winning_actions[state] = ()
            continue
        rows = [
            bucket for (source, _), bucket in game.buckets.items()
            if source == state
        ]
        uncontrollable = sorted(
            row.action for row in rows if not row.controllable
        )
        if uncontrollable:
            if any(
                target not in rank or rank[target] >= rank[state]
                for row in rows if not row.controllable
                for target in row.targets
            ):
                raise ValueError("uncontrollable attractor edge does not decrease rank")
            winning_actions[state] = tuple(uncontrollable)
        else:
            winning_actions[state] = tuple(sorted(
                row.action
                for row in rows
                if row.controllable
                and all(
                    target in rank and rank[target] < rank[state]
                    for target in row.targets
                )
            ))
            if not winning_actions[state]:
                raise ValueError("attractor state has no reconstructible witness")

    losing = frozenset(set(game.states) - set(rank))
    decision = "realizable" if game.initials.issubset(rank) else "unrealizable"
    if decision != game.claimed_decision:
        raise ValueError("claimed decision disagrees with exact fixed point")
    return FixedPoint(
        decision=decision,
        rank=rank,
        losing=losing,
        winning_actions=winning_actions,
        layers_after_goal=max(rank.values(), default=0),
    )


def serialize_explicit_game(
    game: Any,
    *,
    semantics_id: str,
) -> Mapping[str, Any]:
    """Serialize an independent C1 explicit game with Java's terminal convention.

    ``game`` is intentionally duck-typed so this certifying layer does not own
    the raw-LTS parser.  Goal and unsafe states are terminal and reachability is
    recomputed after terminalization, matching the independent Java exporter.
    """

    if not isinstance(semantics_id, str) or not semantics_id:
        raise ValueError("serialized semantics_id must be non-empty")
    initial_states = set(game.initial_states)
    goals = set(game.goals)
    reachable = set(initial_states)
    queue = list(sorted(initial_states, key=repr))
    retained_successors: Dict[Any, Mapping[str, Tuple[Any, ...]]] = {}
    while queue:
        state = queue.pop(0)
        safe = not bool(state[3])
        outgoing = (
            game.successors.get(state, {}) if safe and state not in goals else {}
        )
        retained_successors[state] = outgoing
        for action in sorted(outgoing):
            for target in sorted(outgoing[action], key=repr):
                if target not in reachable:
                    reachable.add(target)
                    queue.append(target)
    ordered_states = sorted(reachable, key=repr)
    identifiers = {state: "R%d" % index for index, state in enumerate(ordered_states)}

    state_rows: List[Mapping[str, Any]] = []
    for state in ordered_states:
        versions, local_states, safety_started, violated = state[:4]
        observer = state[4] if len(state) > 4 else ""
        pending_actions = [
            game.model.migration_actions[index]
            for index, is_new in enumerate(versions)
            if not is_new
        ]
        if getattr(game, "start_action", None) and not safety_started:
            pending_actions.append(game.start_action)
        active_testers: Dict[str, str] = {}
        if getattr(game, "start_action", None) and safety_started:
            requirement = str(game.start_action).removeprefix("startNewSpec_")
            active_testers[requirement] = "E" if violated else "0"
        state_rows.append({
            "id": identifiers[state],
            "initial": state in initial_states,
            "safe": not bool(violated),
            "goal": state in goals,
            "physical": repr((versions, local_states, observer)),
            "active_testers": active_testers,
            "pending_actions": sorted(pending_actions),
        })

    bucket_rows: List[Mapping[str, Any]] = []
    for state in ordered_states:
        for action, targets in sorted(retained_successors.get(state, {}).items()):
            if not targets:
                raise ValueError("independent explicit game has an empty bucket")
            bucket_rows.append({
                "source": identifiers[state],
                "action": action,
                "controllable": bool(game.is_controllable(action)),
                "targets": sorted(identifiers[target] for target in targets),
            })

    initial_ids = {identifiers[state] for state in initial_states}
    goal_ids = {identifiers[state] for state in goals if state in reachable}
    safe_ids = {
        identifiers[state] for state in ordered_states if not bool(state[3])
    }
    outgoing_by_source: MutableMapping[str, List[Mapping[str, Any]]] = defaultdict(list)
    for row in bucket_rows:
        outgoing_by_source[str(row["source"])].append(row)
    winning = set(goal_ids)
    while True:
        added: set[str] = set()
        for state in sorted(safe_ids - winning):
            rows = outgoing_by_source.get(state, [])
            uncontrollable = [row for row in rows if not row["controllable"]]
            if uncontrollable:
                outcomes = {
                    target for row in uncontrollable for target in row["targets"]
                }
                if outcomes and outcomes.issubset(winning):
                    added.add(state)
            elif any(
                set(row["targets"]).issubset(winning)
                for row in rows if row["controllable"]
            ):
                added.add(state)
        if not added:
            break
        winning.update(added)
    decision = "realizable" if initial_ids.issubset(winning) else "unrealizable"
    return {
        "schema_version": BUNDLE_SCHEMA,
        "semantics_id": semantics_id,
        "policy_restriction": "full_fg",
        "claimed_decision": decision,
        "state_count": len(state_rows),
        "query_count": len(bucket_rows),
        "outcome_edge_count": sum(len(row["targets"]) for row in bucket_rows),
        "controllable_bucket_count": sum(
            bool(row["controllable"]) for row in bucket_rows
        ),
        "uncontrollable_bucket_count": sum(
            not bool(row["controllable"]) for row in bucket_rows
        ),
        "initial_state_ids": sorted(initial_ids),
        "goal_state_ids": sorted(goal_ids),
        "states": state_rows,
        "buckets": bucket_rows,
        "observer_exact_terminalization": True,
    }


def _adjacency(game: GameBundle) -> Tuple[
    Mapping[str, Tuple[Bucket, ...]], Mapping[str, Tuple[Tuple[Bucket, str], ...]]
]:
    outgoing: MutableMapping[str, List[Bucket]] = defaultdict(list)
    incoming: MutableMapping[str, List[Tuple[Bucket, str]]] = defaultdict(list)
    for bucket in game.buckets.values():
        outgoing[bucket.source].append(bucket)
        for target in bucket.targets:
            incoming[target].append((bucket, target))
    return (
        {state: tuple(rows) for state, rows in outgoing.items()},
        {state: tuple(rows) for state, rows in incoming.items()},
    )


def _joint_colors(
    left: GameBundle,
    right: GameBundle,
    individual_left: Mapping[str, int],
    individual_right: Mapping[str, int],
    extra_left: Mapping[str, Tuple[Any, ...]],
    extra_right: Mapping[str, Tuple[Any, ...]],
    preserve_physical_partition: bool,
) -> Tuple[Mapping[str, int], Mapping[str, int], int]:
    games = (left, right)
    individuals = (individual_left, individual_right)
    colors: List[Dict[str, int]] = []
    base_rows: List[Dict[str, Tuple[Any, ...]]] = []
    extras = (extra_left, extra_right)
    physical_groups: List[Mapping[str, Tuple[str, ...]]] = []
    for game in games:
        by_signature: MutableMapping[str, List[str]] = defaultdict(list)
        for state, record in game.states.items():
            by_signature[record.physical].append(state)
        physical_groups.append({
            state: tuple(sorted(by_signature[record.physical]))
            for state, record in game.states.items()
        })
    for game, marked, extra, groups in zip(
        games, individuals, extras, physical_groups
    ):
        rows = {
            state: (
                record.initial,
                record.safe,
                record.goal,
                marked.get(state),
                extra.get(state, ()),
                len(groups[state]) if preserve_physical_partition else 0,
            )
            for state, record in game.states.items()
        }
        base_rows.append(rows)
    all_base = [value for rows in base_rows for value in rows.values()]
    palette = {
        value: index for index, value in enumerate(sorted(set(all_base), key=repr))
    }
    colors = [
        {state: palette[value] for state, value in rows.items()}
        for rows in base_rows
    ]
    adjacency = [_adjacency(game) for game in games]
    rounds = 0
    while True:
        rounds += 1
        signatures: List[Dict[str, Tuple[Any, ...]]] = []
        for index, game in enumerate(games):
            outgoing, incoming = adjacency[index]
            current = colors[index]
            rows: Dict[str, Tuple[Any, ...]] = {}
            for state in game.states:
                out_signature = tuple(sorted(
                    (
                        bucket.action,
                        bucket.controllable,
                        tuple(sorted(current[target] for target in bucket.targets)),
                    )
                    for bucket in outgoing.get(state, ())
                ))
                in_signature = tuple(sorted(
                    (
                        bucket.action,
                        bucket.controllable,
                        len(bucket.targets),
                        current[bucket.source],
                    )
                    for bucket, _ in incoming.get(state, ())
                ))
                physical_signature = (
                    tuple(sorted(current[value] for value in physical_groups[index][state]))
                    if preserve_physical_partition
                    else ()
                )
                rows[state] = (
                    current[state], out_signature, in_signature, physical_signature
                )
            signatures.append(rows)
        all_signatures = [
            value for rows in signatures for value in rows.values()
        ]
        palette = {
            value: index
            for index, value in enumerate(sorted(set(all_signatures), key=repr))
        }
        refined = [
            {state: palette[value] for state, value in rows.items()}
            for rows in signatures
        ]
        old_partition_count = sum(len(set(row.values())) for row in colors)
        new_partition_count = sum(len(set(row.values())) for row in refined)
        colors = refined
        if new_partition_count == old_partition_count:
            break
        if rounds > len(left.states) + len(right.states):
            raise RuntimeError("color refinement failed to stabilize")
    return colors[0], colors[1], rounds


def _color_cells(colors: Mapping[str, int]) -> Mapping[int, Tuple[str, ...]]:
    cells: MutableMapping[int, List[str]] = defaultdict(list)
    for state, color in colors.items():
        cells[color].append(state)
    return {color: tuple(sorted(states)) for color, states in cells.items()}


def validate_bijection(
    left: GameBundle,
    right: GameBundle,
    mapping: Mapping[str, str],
) -> None:
    """Directly validate every game-isomorphism obligation."""

    if set(mapping) != set(left.states) or set(mapping.values()) != set(right.states):
        raise NonIsomorphic("candidate state relation is not a bijection")
    for source, target in mapping.items():
        left_row = left.states[source]
        right_row = right.states[target]
        if (
            left_row.initial,
            left_row.safe,
            left_row.goal,
        ) != (
            right_row.initial,
            right_row.safe,
            right_row.goal,
        ):
            raise NonIsomorphic("candidate mapping changes a state flag: " + source)
    expected = {
        (
            mapping[bucket.source],
            bucket.action,
            bucket.controllable,
            tuple(sorted(mapping[target] for target in bucket.targets)),
        )
        for bucket in left.buckets.values()
    }
    observed = {
        (
            bucket.source,
            bucket.action,
            bucket.controllable,
            tuple(sorted(bucket.targets)),
        )
        for bucket in right.buckets.values()
    }
    if expected != observed:
        missing = sorted(expected - observed, key=repr)
        extra = sorted(observed - expected, key=repr)
        raise NonIsomorphic(
            "complete Post bucket relation differs; missing=%r extra=%r"
            % (missing[:1], extra[:1])
        )


def _search_mapping(
    left: GameBundle,
    right: GameBundle,
    individual_left: Mapping[str, int],
    individual_right: Mapping[str, int],
    budget: SearchBudget,
    extra_left: Mapping[str, Tuple[Any, ...]],
    extra_right: Mapping[str, Tuple[Any, ...]],
    preserve_physical_partition: bool,
) -> Tuple[Mapping[str, str], int, bool]:
    budget.consume()
    left_colors, right_colors, rounds = _joint_colors(
        left,
        right,
        individual_left,
        individual_right,
        extra_left,
        extra_right,
        preserve_physical_partition,
    )
    left_cells = _color_cells(left_colors)
    right_cells = _color_cells(right_colors)
    if set(left_cells) != set(right_cells) or any(
        len(left_cells[color]) != len(right_cells[color]) for color in left_cells
    ):
        raise NonIsomorphic("joint color partition has different cell populations")
    ambiguous = [
        color for color, states in left_cells.items() if len(states) > 1
    ]
    if not ambiguous:
        mapping = {
            left_cells[color][0]: right_cells[color][0] for color in left_cells
        }
        validate_bijection(left, right, mapping)
        return mapping, rounds, not individual_left

    selected = min(ambiguous, key=lambda color: (len(left_cells[color]), color))
    source = left_cells[selected][0]
    marker = len(individual_left) + 1
    failures: List[str] = []
    for target in right_cells[selected]:
        next_left = dict(individual_left)
        next_right = dict(individual_right)
        next_left[source] = marker
        next_right[target] = marker
        try:
            mapping, child_rounds, _ = _search_mapping(
                left,
                right,
                next_left,
                next_right,
                budget,
                extra_left,
                extra_right,
                preserve_physical_partition,
            )
            return mapping, rounds + child_rounds, False
        except NonIsomorphic as error:
            failures.append(str(error))
    raise NonIsomorphic(
        "no exact individualization branch produced a bijection: "
        + (failures[0] if failures else "empty candidate cell")
    )


def exact_mapping(
    left: GameBundle,
    right: GameBundle,
    *,
    maximum_search_nodes: int,
    extra_left: Mapping[str, Tuple[Any, ...]] | None = None,
    extra_right: Mapping[str, Tuple[Any, ...]] | None = None,
    preserve_physical_partition: bool = False,
) -> Tuple[Mapping[str, str], Mapping[str, Any]]:
    if maximum_search_nodes <= 0:
        raise ValueError("maximum_search_nodes must be positive")
    if len(left.states) != len(right.states):
        raise NonIsomorphic("state populations differ")
    if len(left.buckets) != len(right.buckets):
        raise NonIsomorphic("enabled bucket populations differ")
    budget = SearchBudget(maximum_search_nodes)
    mapping, rounds, unique_by_refinement = _search_mapping(
        left,
        right,
        {},
        {},
        budget,
        extra_left or {},
        extra_right or {},
        preserve_physical_partition,
    )
    return mapping, {
        "search_nodes": budget.visited_nodes,
        "refinement_rounds_total": rounds,
        "unique_by_unindividualized_refinement": unique_by_refinement,
    }


def _normalized_testers(
    record: StateRecord,
    requirement_phases: Mapping[str, str],
) -> Tuple[Tuple[str, str, str], ...]:
    normalized: Dict[Tuple[str, str], str] = {}
    for key, raw_value in record.active_testers.items():
        parts = key.split(":")
        if len(parts) == 3 and parts[0] in {"old", "new"}:
            phase, name = parts[0], parts[1]
        else:
            name = key
            phase = requirement_phases.get(name, "")
        expected_phase = requirement_phases.get(name)
        if expected_phase not in {"old", "new"} or phase != expected_phase:
            raise NonIsomorphic(
                "active tester has an unregistered old/new role: " + key
            )
        value = "E" if raw_value == "-1" else raw_value
        identity = (phase, name)
        if identity in normalized:
            raise ValueError("tester key normalization is not injective: " + name)
        normalized[identity] = value
    return tuple(sorted((phase, name, value) for (phase, name), value in normalized.items()))


def validate_typed_state_translation(
    left: GameBundle,
    right: GameBundle,
    mapping: Mapping[str, str],
    requirement_phases: Mapping[str, str],
) -> Mapping[str, Any]:
    """Check lifecycle/tester roles and the physical equality partition."""

    if not requirement_phases or any(
        not isinstance(name, str)
        or not name
        or phase not in {"old", "new"}
        for name, phase in requirement_phases.items()
    ):
        raise ValueError("typed comparison needs exact old/new requirement roles")

    physical_forward: MutableMapping[str, set[str]] = defaultdict(set)
    physical_reverse: MutableMapping[str, set[str]] = defaultdict(set)
    for source, target in mapping.items():
        left_row = left.states[source]
        right_row = right.states[target]
        if tuple(sorted(left_row.pending_actions)) != tuple(
            sorted(right_row.pending_actions)
        ):
            raise NonIsomorphic("pending-action set differs at " + source)
        if _normalized_testers(left_row, requirement_phases) != _normalized_testers(
            right_row, requirement_phases
        ):
            raise NonIsomorphic("active tester residuals differ at " + source)
        physical_forward[left_row.physical].add(right_row.physical)
        physical_reverse[right_row.physical].add(left_row.physical)
    if any(len(values) != 1 for values in physical_forward.values()) or any(
        len(values) != 1 for values in physical_reverse.values()
    ):
        raise NonIsomorphic("physical state signatures do not induce a bijective renaming")
    rows = [
        {"left": source, "right": next(iter(targets))}
        for source, targets in sorted(physical_forward.items())
    ]
    return {
        "pending_actions_preserved": True,
        "old_new_requirement_roles_preserved": True,
        "active_tester_residuals_preserved": True,
        "physical_signature_classes": len(rows),
        "physical_equality_partition_preserved": True,
        "physical_signature_mapping_sha256": sha256_json(rows),
    }


def compare_games(
    left: GameBundle,
    right: GameBundle,
    *,
    maximum_search_nodes: int,
    require_typed_state_translation: bool,
    typed_requirement_phases: Mapping[str, str] | None = None,
) -> Mapping[str, Any]:
    """Construct, validate, and summarize an exact game isomorphism."""

    phase_map = typed_requirement_phases or {}
    if require_typed_state_translation:
        if not phase_map or any(
            not isinstance(name, str)
            or not name
            or phase not in {"old", "new"}
            for name, phase in phase_map.items()
        ):
            raise ValueError("typed comparison needs exact old/new requirement roles")
        extra_left = {
            state: (
                tuple(sorted(record.pending_actions)),
                _normalized_testers(record, phase_map),
            )
            for state, record in left.states.items()
        }
        extra_right = {
            state: (
                tuple(sorted(record.pending_actions)),
                _normalized_testers(record, phase_map),
            )
            for state, record in right.states.items()
        }
    else:
        extra_left = {}
        extra_right = {}
    mapping, search = exact_mapping(
        left,
        right,
        maximum_search_nodes=maximum_search_nodes,
        extra_left=extra_left,
        extra_right=extra_right,
        preserve_physical_partition=require_typed_state_translation,
    )
    left_fixed = fixed_point(left)
    right_fixed = fixed_point(right)
    for source, target in mapping.items():
        if left_fixed.rank.get(source) != right_fixed.rank.get(target):
            raise NonIsomorphic("attractor rank is not preserved at " + source)
        if (source in left_fixed.losing) != (target in right_fixed.losing):
            raise NonIsomorphic("losing-region membership is not preserved at " + source)
        if left_fixed.winning_actions.get(source) != right_fixed.winning_actions.get(target):
            raise NonIsomorphic("canonical winning actions are not preserved at " + source)
    typed = (
        validate_typed_state_translation(
            left, right, mapping, phase_map
        )
        if require_typed_state_translation
        else {"checked": False}
    )
    mapping_rows = [
        {"left": source, "right": mapping[source]} for source in sorted(mapping)
    ]
    certificate_rows = [
        {
            "left": source,
            "right": mapping[source],
            "rank": left_fixed.rank.get(source),
            "losing": source in left_fixed.losing,
            "winning_actions": list(left_fixed.winning_actions.get(source, ())),
        }
        for source in sorted(mapping)
    ]
    return {
        "schema_version": COMPARISON_SCHEMA,
        "status": "PASS",
        "left_semantics_id": left.semantics_id,
        "right_semantics_id": right.semantics_id,
        "state_count": len(left.states),
        "initial_state_count": len(left.initials),
        "safe_state_count": len(left.safe),
        "goal_state_count": len(left.goals),
        "controllable_bucket_count": sum(
            bucket.controllable for bucket in left.buckets.values()
        ),
        "uncontrollable_bucket_count": sum(
            not bucket.controllable for bucket in left.buckets.values()
        ),
        "enabled_bucket_count": len(left.buckets),
        "outcome_edge_count": sum(
            len(bucket.targets) for bucket in left.buckets.values()
        ),
        "decision": left_fixed.decision,
        "winning_state_count": len(left_fixed.rank),
        "losing_state_count": len(left_fixed.losing),
        "layers_after_goal": left_fixed.layers_after_goal,
        "mapping_sha256": sha256_json(mapping_rows),
        "certificate_transport_sha256": sha256_json(certificate_rows),
        "mapping": mapping_rows,
        "search": dict(search),
        "typed_state_translation": typed,
        "obligations": {
            "q0_preserved": True,
            "safe_preserved": True,
            "goal_preserved": True,
            "action_labels_preserved": True,
            "controllability_preserved": True,
            "complete_post_buckets_preserved": True,
            "attractor_rank_preserved": True,
            "winning_actions_preserved": True,
            "losing_region_preserved": True,
        },
    }
