#!/usr/bin/env python3
"""Emit a complete, deterministic trace of the M8p acceptance predicate.

This is a correctness trace, not a new empirical study.  It exposes every
candidate partition, every required Cartesian source context, every predicate
conjunct, and the local games induced by accepted candidates.  The accepted
class deliberately includes rectangular roots and is therefore a sufficient
subclass of the paper's composition theorem, which itself permits correlated
global roots.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

from discover_typed_partition import (  # noqa: E402
    TypedFlatGame,
    _typed_scalar,
    expand_unit_partition,
    mandatory_units,
    normalize_partition,
    set_partitions,
    verify_partition,
)


TRACE_SCHEMA = "fg-ducs-typed-partition-predicate-trace-v1"


class TraceError(RuntimeError):
    """Malformed trace or input."""


def canonical_bytes(value: Any) -> bytes:
    try:
        return (
            json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise TraceError("value is not canonical finite JSON") from error


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _json_key(value: Any) -> str:
    return canonical_bytes(value).decode("utf-8")


def _projection(game: TypedFlatGame, state: str, block: Sequence[str]) -> tuple[Any, ...]:
    return game.projection(game.state_values[state], block)


def _load_projection(game: TypedFlatGame, load: str, block: Sequence[str]) -> tuple[Any, ...]:
    return game.projection(game.load_values[load], block)


def _product(values: Sequence[Sequence[Any]]) -> list[tuple[Any, ...]]:
    if not values:
        return [tuple()]
    return [tuple(item) for item in itertools.product(*values)]


def _sorted_unique(values: Iterable[Any]) -> list[Any]:
    by_key = {_json_key(value): value for value in values}
    return [by_key[key] for key in sorted(by_key)]


def _rectangular_record(
    game: TypedFlatGame,
    identifiers: set[str],
    values: Mapping[str, tuple[Any, ...]],
    partition: tuple[tuple[str, ...], ...],
) -> dict[str, Any]:
    domains = [
        _sorted_unique(game.projection(values[identifier], block) for identifier in identifiers)
        for block in partition
    ]
    observed = _sorted_unique(
        tuple(game.projection(values[identifier], block) for block in partition)
        for identifier in identifiers
    )
    expected = _product(domains)
    observed_keys = {_json_key(value) for value in observed}
    missing = [value for value in expected if _json_key(value) not in observed_keys]
    return {
        "pass": not missing and len(expected) == len(observed),
        "projection_domains": domains,
        "expected_tuple_count": len(expected),
        "observed_tuple_count": len(observed),
        "missing_tuples": missing,
    }


def _handover_record(
    game: TypedFlatGame,
    partition: tuple[tuple[str, ...], ...],
) -> dict[str, Any]:
    domains = [
        _sorted_unique(
            (
                _projection(game, goal, block),
                _load_projection(game, load, block),
            )
            for goal, load in game.handover
        )
        for block in partition
    ]
    observed = _sorted_unique(
        tuple(
            (
                _projection(game, goal, block),
                _load_projection(game, load, block),
            )
            for block in partition
        )
        for goal, load in game.handover
    )
    expected = _product(domains)
    observed_keys = {_json_key(value) for value in observed}
    missing = [value for value in expected if _json_key(value) not in observed_keys]
    return {
        "pass": not missing and len(expected) == len(observed),
        "local_relations": domains,
        "expected_tuple_count": len(expected),
        "observed_tuple_count": len(observed),
        "missing_tuples": missing,
    }


def _partition_owner(
    game: TypedFlatGame,
    partition: tuple[tuple[str, ...], ...],
) -> tuple[dict[str, int], bool]:
    owner: dict[str, int] = {}
    duplicated = False
    for index, block in enumerate(partition):
        for atom in block:
            if atom in owner:
                duplicated = True
            owner[atom] = index
    valid = (
        not duplicated
        and all(partition)
        and set(owner) == set(game.atoms)
        and sum(len(block) for block in partition) == len(game.atoms)
    )
    return owner, valid


def _context_rows(
    game: TypedFlatGame,
    partition: tuple[tuple[str, ...], ...],
    action_owner: Mapping[str, int],
) -> tuple[list[dict[str, Any]], dict[tuple[int, str], dict[tuple[Any, ...], frozenset[tuple[Any, ...]]]], bool, bool]:
    block_domains = [
        _sorted_unique(_projection(game, state, block) for state in game.states)
        for block in partition
    ]
    state_by_tuple = {
        tuple(_projection(game, state, block) for block in partition): state
        for state in game.states
    }
    rows: list[dict[str, Any]] = []
    local_posts: dict[tuple[int, str], dict[tuple[Any, ...], frozenset[tuple[Any, ...]]]] = {}
    all_frame = True
    all_context_independent = True

    for action in sorted(game.actions):
        record = game.actions[action]
        if record["kind"] == "shared_stutter" or action not in action_owner:
            continue
        block_index = action_owner[action]
        other_indices = [index for index in range(len(partition)) if index != block_index]
        observed_posts: dict[tuple[Any, ...], list[frozenset[tuple[Any, ...]]]] = {}
        for local_source in block_domains[block_index]:
            foreign_domains = [block_domains[index] for index in other_indices]
            for foreign_values in _product(foreign_domains):
                global_tuple: list[Any] = [None] * len(partition)
                global_tuple[block_index] = local_source
                for position, index in enumerate(other_indices):
                    global_tuple[index] = foreign_values[position]
                source = state_by_tuple.get(tuple(global_tuple))
                targets = frozenset() if source is None else game.post.get((source, action), frozenset())
                local_targets = frozenset(
                    _projection(game, target, partition[block_index]) for target in targets
                )
                frame_pass = source is not None and all(
                    all(
                        _projection(game, target, partition[index]) == global_tuple[index]
                        for index in other_indices
                    )
                    for target in targets
                )
                all_frame = all_frame and frame_pass
                observed_posts.setdefault(local_source, []).append(local_targets)
                rows.append({
                    "action": action,
                    "owner_block": block_index,
                    "local_source": local_source,
                    "foreign_context": [global_tuple[index] for index in other_indices],
                    "global_state": source,
                    "context_present": source is not None,
                    "global_targets": sorted(targets),
                    "projected_local_targets": sorted(local_targets, key=_json_key),
                    "foreign_frame": frame_pass,
                })
        post_for_action: dict[tuple[Any, ...], frozenset[tuple[Any, ...]]] = {}
        for local_source, outcomes in observed_posts.items():
            same = bool(outcomes) and all(outcome == outcomes[0] for outcome in outcomes)
            all_context_independent = all_context_independent and same
            if same:
                post_for_action[local_source] = outcomes[0]
        local_posts[(block_index, action)] = post_for_action

    rows.sort(key=_json_key)
    return rows, local_posts, all_frame, all_context_independent


def _shared_stutter_rows(game: TypedFlatGame) -> tuple[list[dict[str, Any]], bool]:
    rows: list[dict[str, Any]] = []
    passed = True
    for action, record in sorted(game.actions.items()):
        if record["kind"] != "shared_stutter":
            continue
        for state in sorted(game.states):
            targets = game.post.get((state, action), frozenset())
            row_pass = targets == frozenset({state})
            passed = passed and row_pass
            rows.append({
                "action": action,
                "state": state,
                "targets": sorted(targets),
                "pass": row_pass,
            })
    return rows, passed


def _local_games(
    game: TypedFlatGame,
    partition: tuple[tuple[str, ...], ...],
    action_owner: Mapping[str, int],
    local_posts: Mapping[tuple[int, str], Mapping[tuple[Any, ...], frozenset[tuple[Any, ...]]]],
) -> list[dict[str, Any]]:
    local: list[dict[str, Any]] = []
    for index, block in enumerate(partition):
        states = _sorted_unique(_projection(game, state, block) for state in game.states)
        initials = _sorted_unique(_projection(game, state, block) for state in game.initials)
        safe = _sorted_unique(_projection(game, state, block) for state in game.safe)
        goals = _sorted_unique(_projection(game, state, block) for state in game.goals)
        loads = _sorted_unique(_load_projection(game, load, block) for load in game.loads)
        handover = _sorted_unique(
            (_projection(game, goal, block), _load_projection(game, load, block))
            for goal, load in game.handover
        )
        actions = sorted(action for action, owner in action_owner.items() if owner == index)
        buckets: list[dict[str, Any]] = []
        for action in actions:
            action_posts = local_posts.get((index, action), {})
            for state in states:
                buckets.append({
                    "source": state,
                    "action": action,
                    "targets": sorted(action_posts.get(tuple(state), frozenset()), key=_json_key),
                })
        residual_atoms = [atom for atom in block if game.atom_kinds[atom] == "rs"]
        residual_values = {
            atom: _sorted_unique(
                _typed_scalar(game.state_values[state][game.atoms.index(atom)])
                for state in game.states
            )
            for atom in residual_atoms
        }
        local.append({
            "block_index": index,
            "atoms": list(block),
            "states": states,
            "initial_states": initials,
            "safe_states": safe,
            "goal_states": goals,
            "load_states": loads,
            "actions": actions,
            "post_buckets_including_empty": buckets,
            "residual_atoms": residual_atoms,
            "residual_values": residual_values,
            "handover_relation": handover,
        })
    return local


def trace_partition(
    game: TypedFlatGame,
    partition: tuple[tuple[str, ...], ...],
) -> dict[str, Any]:
    owner, partition_domain = _partition_owner(game, partition)
    dependency_locality = partition_domain and all(
        len({owner[atom] for atom in dependency["atoms"]}) == 1
        for dependency in game.dependencies
    )
    action_owner: dict[str, int] = {}
    action_subject_locality = partition_domain
    for action, record in sorted(game.actions.items()):
        if record["kind"] == "shared_stutter":
            continue
        blocks = {owner[atom] for atom in record["subjects"] if atom in owner}
        local = bool(record["subjects"]) and len(blocks) == 1
        action_subject_locality = action_subject_locality and local
        if local:
            action_owner[action] = next(iter(blocks))

    rectangles = {
        "state_rectangular": _rectangular_record(game, game.states, game.state_values, partition),
        "root_rectangular": _rectangular_record(game, game.initials, game.state_values, partition),
        "safe_rectangular": _rectangular_record(game, game.safe, game.state_values, partition),
        "goal_rectangular": _rectangular_record(game, game.goals, game.state_values, partition),
        "load_rectangular": _rectangular_record(game, game.loads, game.load_values, partition),
    }
    handover = _handover_record(game, partition)
    context_rows, local_posts, foreign_frame, context_independent_post = _context_rows(
        game, partition, action_owner
    )
    stutter_rows, shared_stutter = _shared_stutter_rows(game)

    goal_uc_quiescence = True
    quiescence_rows: list[dict[str, Any]] = []
    for action, record in sorted(game.actions.items()):
        if record["controllability"] != "uncontrollable" or action not in action_owner:
            continue
        index = action_owner[action]
        local_goals = _sorted_unique(_projection(game, goal, partition[index]) for goal in game.goals)
        action_posts = local_posts.get((index, action), {})
        for goal in local_goals:
            targets = action_posts.get(tuple(goal), frozenset())
            row_pass = not targets
            goal_uc_quiescence = goal_uc_quiescence and row_pass
            quiescence_rows.append({
                "block_index": index,
                "goal": goal,
                "action": action,
                "targets": sorted(targets, key=_json_key),
                "pass": row_pass,
            })

    pending_locality = all(
        record["kind"] != "update"
        or (
            action in action_owner
            and record["pending_atom"] in partition[action_owner[action]]
        )
        for action, record in game.actions.items()
    )
    conjuncts = {
        "typed_table_eligibility": True,
        "partition_domain": partition_domain,
        "dependency_locality": dependency_locality,
        "state_rectangular": rectangles["state_rectangular"]["pass"],
        "root_rectangular": rectangles["root_rectangular"]["pass"],
        "safe_rectangular": rectangles["safe_rectangular"]["pass"],
        "goal_rectangular": rectangles["goal_rectangular"]["pass"],
        "load_rectangular": rectangles["load_rectangular"]["pass"],
        "handover_rectangular": handover["pass"],
        "action_subject_locality": action_subject_locality,
        "foreign_frame": foreign_frame,
        "context_independent_complete_post": context_independent_post,
        "shared_controllable_pure_stutter": shared_stutter,
        "pending_locality": pending_locality,
        "local_goal_uncontrollable_quiescence": goal_uc_quiescence,
    }
    accepted = all(conjuncts.values())
    legacy_assignment, legacy_problem = verify_partition(game, partition)
    if accepted != (legacy_problem is None):
        raise TraceError("trace predicate differs from the registered M8p predicate")

    local = _local_games(game, partition, action_owner, local_posts) if accepted else []
    theorem_premises = {
        "ambient_state_product": conjuncts["state_rectangular"],
        "nonempty_projected_roots": bool(game.initials),
        "root_projection_with_extra_rectangularity": conjuncts["root_rectangular"],
        "asynchronous_frame_product": (
            conjuncts["action_subject_locality"]
            and conjuncts["foreign_frame"]
            and conjuncts["context_independent_complete_post"]
        ),
        "safe_conjunction": conjuncts["safe_rectangular"],
        "goal_product": conjuncts["goal_rectangular"],
        "load_product": conjuncts["load_rectangular"],
        "handover_product": conjuncts["handover_rectangular"],
        "typed_metadata_block_local": (
            conjuncts["dependency_locality"] and conjuncts["pending_locality"]
        ),
        "shared_actions_are_controllable_pure_stutters": conjuncts["shared_controllable_pure_stutter"],
        "local_goals_are_uncontrollably_quiescent": conjuncts["local_goal_uncontrollable_quiescence"],
    }
    theorem_transport_ready = accepted and all(theorem_premises.values())
    return {
        "partition": [list(block) for block in partition],
        "block_count": len(partition),
        "conjuncts": conjuncts,
        "accepted": accepted,
        "rectangularity_details": rectangles,
        "handover_details": handover,
        "action_assignment": legacy_assignment or {},
        "cartesian_context_rows": context_rows,
        "shared_stutter_rows": stutter_rows,
        "goal_quiescence_rows": quiescence_rows,
        "derived_local_games": local,
        "theorem_5_3_premises": theorem_premises,
        "theorem_5_3_transport_ready": theorem_transport_ready,
        "legacy_first_obstruction": legacy_problem,
    }


def all_partitions(game: TypedFlatGame) -> list[tuple[tuple[str, ...], ...]]:
    units = mandatory_units(game)
    unit_ids = tuple(str(index) for index in range(len(units)))
    candidates: list[tuple[tuple[str, ...], ...]] = []
    for count in range(len(units), 0, -1):
        candidates.extend(
            expand_unit_partition(partition, units)
            for partition in set_partitions(unit_ids, count)
        )
    return candidates


def generate(raw: Mapping[str, Any]) -> dict[str, Any]:
    game = TypedFlatGame(raw)
    units = mandatory_units(game)
    traces = [trace_partition(game, partition) for partition in all_partitions(game)]
    accepted_counts = sorted(
        {record["block_count"] for record in traces if record["accepted"]}, reverse=True
    )
    first_count = accepted_counts[0] if accepted_counts else None
    first_layer = [
        record["partition"]
        for record in traces
        if record["accepted"] and record["block_count"] == first_count
    ]
    return {
        "schema_version": TRACE_SCHEMA,
        "input_game_id": game.identifier,
        "input_game_sha256": sha256_json(raw),
        "scope": "exact-relative-to-supplied-atoms-total-table-and-externally-complete-dependencies",
        "root_boundary": (
            "accepted candidates require Q0 to equal the product of its projections; "
            "the composition theorem also permits correlated Q0 and is strictly broader"
        ),
        "post_convention": "a missing source/action bucket is the empty successor set",
        "mandatory_units": [list(unit) for unit in units],
        "unit_partition_count": len(traces),
        "partitions": traces,
        "first_accepted_block_count": first_count,
        "first_accepted_layer": first_layer,
        "selected_partition": min(first_layer, key=_json_key) if first_layer else None,
        "all_accepted_candidates_transport_ready": all(
            record["theorem_5_3_transport_ready"]
            for record in traces
            if record["accepted"]
        ),
    }


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise TraceError(f"invalid JSON: {path}") from error
    if not isinstance(value, dict):
        raise TraceError(f"JSON root is not an object: {path}")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("game", type=Path)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--output", type=Path)
    group.add_argument("--check", type=Path)
    args = parser.parse_args(argv)
    expected = generate(load_json(args.game))
    if args.output is not None:
        args.output.write_text(
            json.dumps(expected, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(json.dumps({
            "status": "PASS",
            "trace_sha256": sha256_json(expected),
            "partition_count": expected["unit_partition_count"],
            "first_accepted_block_count": expected["first_accepted_block_count"],
        }, sort_keys=True))
        return 0
    observed = load_json(args.check)
    if canonical_bytes(observed) != canonical_bytes(expected):
        raise TraceError("saved predicate trace differs from deterministic recomputation")
    print(json.dumps({
        "status": "PASS",
        "trace_sha256": sha256_json(observed),
        "partition_count": observed["unit_partition_count"],
        "first_accepted_block_count": observed["first_accepted_block_count"],
        "all_accepted_candidates_transport_ready": observed["all_accepted_candidates_transport_ready"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
