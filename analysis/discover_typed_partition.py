#!/usr/bin/env python3
"""Discover a maximum-block partition for the paper's typed composition theorem.

The input deliberately contains atoms, full valuations, complete Post buckets,
load values, handover pairs, and typed action subjects, but no proposed block
partition.  The procedure is exact relative to that supplied finite table.  It
does not infer the atomization from an arbitrary LTS and it never treats a
resource limit as evidence of non-factorability.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence


GAME_SCHEMA = "fg-ducs-typed-flat-game-v1"
CERT_SCHEMA = "fg-ducs-partition-certificate-v1"
SEMANTICS = "complete-explicit-post-including-goal-and-unsafe-v1"


class DiscoveryError(RuntimeError):
    """Malformed input or exhausted explicit-search budget."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise DiscoveryError(message)


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
        raise DiscoveryError("input is not canonical finite JSON") from error


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    require(set(value) == expected, f"{label} fields differ: {sorted(set(value) ^ expected)}")


def string_list(value: Any, label: str, *, nonempty: bool = True) -> list[str]:
    require(isinstance(value, list), f"{label} must be a list")
    require(all(isinstance(item, str) and item for item in value), f"{label} has an invalid item")
    require(len(value) == len(set(value)), f"{label} has duplicates")
    require(not nonempty or bool(value), f"{label} must be nonempty")
    return list(value)


def _json_scalar(value: Any) -> bool:
    return (
        value is None
        or type(value) is str
        or type(value) is bool
        or type(value) is int
        or (type(value) is float and math.isfinite(value))
    )


def _typed_scalar(value: Any) -> tuple[str, Any]:
    """Preserve JSON scalar sorts during Cartesian comparison.

    Python considers ``True == 1`` and ``False == 0``.  A typed contract must
    not collapse those distinct JSON values when forming coordinate domains.
    Integers and finite floats remain one JSON-number sort.
    """
    if value is None:
        return ("null", None)
    if type(value) is bool:
        return ("bool", value)
    if type(value) in {int, float}:
        require(type(value) is int or math.isfinite(value), "non-finite JSON number")
        return ("number", value)
    require(type(value) is str, "value is not a JSON scalar")
    return ("string", value)


def normalize_partition(blocks: Iterable[Iterable[str]]) -> tuple[tuple[str, ...], ...]:
    return tuple(sorted((tuple(sorted(block)) for block in blocks), key=lambda block: block))


def mandatory_units(game: "TypedFlatGame") -> tuple[tuple[str, ...], ...]:
    """Contract typed-dependency hyperedges into indivisible search units."""
    parent = {atom: atom for atom in game.atoms}

    def find(atom: str) -> str:
        while parent[atom] != atom:
            parent[atom] = parent[parent[atom]]
            atom = parent[atom]
        return atom

    def union(left: str, right: str) -> None:
        a, b = find(left), find(right)
        if a != b:
            if a > b:
                a, b = b, a
            parent[b] = a

    for dependency in game.dependencies:
        members = tuple(dependency["atoms"])
        for member in members[1:]:
            union(members[0], member)
    groups: dict[str, list[str]] = {}
    for atom in game.atoms:
        groups.setdefault(find(atom), []).append(atom)
    return normalize_partition(groups.values())


def expand_unit_partition(
    unit_partition: tuple[tuple[str, ...], ...],
    units: tuple[tuple[str, ...], ...],
) -> tuple[tuple[str, ...], ...]:
    return normalize_partition(
        [atom for unit_index in block for atom in units[int(unit_index)]]
        for block in unit_partition
    )


def set_partitions(items: Sequence[str], block_count: int) -> Iterator[tuple[tuple[str, ...], ...]]:
    """Generate each canonical set partition with exactly ``block_count`` blocks."""
    ordered = tuple(sorted(items))
    require(1 <= block_count <= len(ordered), "partition block count is invalid")
    blocks: list[list[str]] = []

    def visit(index: int) -> Iterator[tuple[tuple[str, ...], ...]]:
        remaining = len(ordered) - index
        if len(blocks) > block_count or len(blocks) + remaining < block_count:
            return
        if index == len(ordered):
            if len(blocks) == block_count:
                yield normalize_partition(blocks)
            return
        item = ordered[index]
        for block in blocks:
            block.append(item)
            yield from visit(index + 1)
            block.pop()
        if len(blocks) < block_count:
            blocks.append([item])
            yield from visit(index + 1)
            blocks.pop()

    yield from visit(0)


class TypedFlatGame:
    def __init__(self, raw: Mapping[str, Any]) -> None:
        exact_keys(
            raw,
            {
                "schema_version", "id", "semantics", "atoms", "actions",
                "states", "buckets", "load_states", "handover_relation",
                "dependencies", "provenance",
            },
            "typed flat game",
        )
        require(raw.get("schema_version") == GAME_SCHEMA, "unknown typed-flat-game schema")
        require(raw.get("semantics") == SEMANTICS, "typed flat game is not a complete preterminal Post table")
        require(isinstance(raw.get("id"), str) and raw["id"], "game id is invalid")
        require(isinstance(raw.get("provenance"), dict), "provenance is invalid")
        self.raw = dict(raw)
        self.identifier = str(raw["id"])

        atoms_raw = raw.get("atoms")
        require(isinstance(atoms_raw, list) and atoms_raw, "atoms must be a nonempty list")
        self.atom_kinds: dict[str, str] = {}
        for record in atoms_raw:
            require(isinstance(record, dict), "atom record is invalid")
            exact_keys(record, {"id", "kind"}, "atom")
            atom = record.get("id")
            kind = record.get("kind")
            require(isinstance(atom, str) and atom and atom not in self.atom_kinds, "atom id is invalid or duplicated")
            require("," not in atom and atom != "<shared-stutter>", f"atom id uses a reserved assignment delimiter: {atom}")
            require(kind in {"component", "monitor", "rs", "pending", "load", "auxiliary"}, f"atom kind differs: {atom}")
            self.atom_kinds[atom] = str(kind)
        self.atoms = tuple(sorted(self.atom_kinds))
        atom_set = set(self.atoms)

        actions_raw = raw.get("actions")
        require(isinstance(actions_raw, list), "actions must be a list")
        self.actions: dict[str, dict[str, Any]] = {}
        for record in actions_raw:
            require(isinstance(record, dict), "action record is invalid")
            exact_keys(record, {"id", "controllability", "kind", "subjects", "pending_atom"}, "action")
            action = record.get("id")
            require(isinstance(action, str) and action and action not in self.actions, "action id is invalid or duplicated")
            require(record.get("controllability") in {"controllable", "uncontrollable"}, f"action controllability differs: {action}")
            require(record.get("kind") in {"update", "normal", "shared_stutter"}, f"action kind differs: {action}")
            subjects = set(string_list(record.get("subjects"), f"{action}.subjects", nonempty=False))
            require(subjects <= atom_set, f"action subject is outside the atom set: {action}")
            pending_atom = record.get("pending_atom")
            if record.get("kind") == "update":
                require(record.get("controllability") == "controllable", f"update action is uncontrollable: {action}")
                require(isinstance(pending_atom, str) and self.atom_kinds.get(pending_atom) == "pending", f"update pending atom differs: {action}")
                require(pending_atom in subjects, f"update pending atom is not a typed subject: {action}")
            else:
                require(pending_atom is None, f"non-update action has a pending atom: {action}")
            if record.get("kind") == "shared_stutter":
                require(not subjects and record.get("controllability") == "controllable", f"shared stutter typing differs: {action}")
            else:
                require(bool(subjects), f"local action has no typed subject: {action}")
            self.actions[str(action)] = dict(record)

        self.states, self.state_values, self.initials, self.safe, self.goals = self._parse_states(raw.get("states"))
        require(self.initials and self.goals, "Q0 and Goal must be nonempty")
        require(self.goals <= self.safe, "Goal is not a subset of Safe")
        self.loads, self.load_values = self._parse_loads(raw.get("load_states"))
        require(self.loads, "Z_load must be nonempty")

        buckets_raw = raw.get("buckets")
        require(isinstance(buckets_raw, list), "buckets must be a list")
        self.post: dict[tuple[str, str], frozenset[str]] = {}
        for record in buckets_raw:
            require(isinstance(record, dict), "bucket record is invalid")
            exact_keys(record, {"source", "action", "targets"}, "bucket")
            source = record.get("source")
            action = record.get("action")
            targets = frozenset(string_list(record.get("targets"), "bucket.targets"))
            require(source in self.states and action in self.actions and targets <= self.states, "bucket typing differs")
            key = (str(source), str(action))
            require(key not in self.post, "duplicate action bucket")
            self.post[key] = targets

        relation_raw = raw.get("handover_relation")
        require(isinstance(relation_raw, list), "handover relation must be a list")
        self.handover: set[tuple[str, str]] = set()
        for record in relation_raw:
            require(isinstance(record, dict), "handover pair is invalid")
            exact_keys(record, {"goal", "load"}, "handover pair")
            pair = (record.get("goal"), record.get("load"))
            require(pair[0] in self.goals and pair[1] in self.loads, "handover pair typing differs")
            require(pair not in self.handover, "duplicate handover pair")
            self.handover.add((str(pair[0]), str(pair[1])))
        require({goal for goal, _ in self.handover} == self.goals, "handover relation is not total on Goal")

        dependencies_raw = raw.get("dependencies")
        require(isinstance(dependencies_raw, list), "dependencies must be a list")
        self.dependencies: list[dict[str, Any]] = []
        seen_dependencies: set[tuple[str, tuple[str, ...]]] = set()
        for record in dependencies_raw:
            require(isinstance(record, dict), "dependency is invalid")
            exact_keys(record, {"kind", "atoms", "detail"}, "dependency")
            kind = record.get("kind")
            require(kind in {"component", "requirement", "precedence", "start", "iota", "handover", "pending"}, "dependency kind differs")
            atoms = tuple(sorted(string_list(record.get("atoms"), "dependency.atoms")))
            require(set(atoms) <= atom_set and len(atoms) >= 2, "dependency atoms differ")
            require(isinstance(record.get("detail"), str), "dependency detail is invalid")
            key = (str(kind), atoms)
            require(key not in seen_dependencies, "duplicate dependency")
            seen_dependencies.add(key)
            self.dependencies.append({"kind": str(kind), "atoms": atoms, "detail": str(record["detail"])})

        self._validate_pending_semantics()

    def _parse_states(self, value: Any) -> tuple[set[str], dict[str, tuple[Any, ...]], set[str], set[str], set[str]]:
        require(isinstance(value, list) and value, "states must be a nonempty list")
        identifiers: set[str] = set()
        valuations: dict[str, tuple[Any, ...]] = {}
        initials: set[str] = set()
        safe: set[str] = set()
        goals: set[str] = set()
        seen_values: set[tuple[tuple[str, Any], ...]] = set()
        for record in value:
            require(isinstance(record, dict), "state record is invalid")
            exact_keys(record, {"id", "valuation", "initial", "safe", "goal"}, "state")
            identifier = record.get("id")
            require(isinstance(identifier, str) and identifier and identifier not in identifiers, "state id is invalid or duplicated")
            valuation = record.get("valuation")
            require(isinstance(valuation, dict) and set(valuation) == set(self.atoms), f"state valuation domain differs: {identifier}")
            require(all(_json_scalar(valuation[atom]) for atom in self.atoms), f"state valuation is not scalar: {identifier}")
            vector = tuple(valuation[atom] for atom in self.atoms)
            typed_vector = tuple(_typed_scalar(item) for item in vector)
            require(typed_vector not in seen_values, f"state valuation is not injective: {identifier}")
            require(type(record.get("initial")) is bool and type(record.get("safe")) is bool and type(record.get("goal")) is bool, f"state flags differ: {identifier}")
            identifiers.add(identifier)
            seen_values.add(typed_vector)
            valuations[identifier] = vector
            if record["initial"]:
                initials.add(identifier)
            if record["safe"]:
                safe.add(identifier)
            if record["goal"]:
                goals.add(identifier)
        return identifiers, valuations, initials, safe, goals

    def _parse_loads(self, value: Any) -> tuple[set[str], dict[str, tuple[Any, ...]]]:
        require(isinstance(value, list) and value, "load_states must be a nonempty list")
        identifiers: set[str] = set()
        valuations: dict[str, tuple[Any, ...]] = {}
        seen_values: set[tuple[tuple[str, Any], ...]] = set()
        for record in value:
            require(isinstance(record, dict), "load record is invalid")
            exact_keys(record, {"id", "valuation"}, "load state")
            identifier = record.get("id")
            valuation = record.get("valuation")
            require(isinstance(identifier, str) and identifier and identifier not in identifiers, "load id is invalid or duplicated")
            require(isinstance(valuation, dict) and set(valuation) == set(self.atoms), f"load valuation domain differs: {identifier}")
            require(all(_json_scalar(valuation[atom]) for atom in self.atoms), f"load valuation is not scalar: {identifier}")
            vector = tuple(valuation[atom] for atom in self.atoms)
            typed_vector = tuple(_typed_scalar(item) for item in vector)
            require(typed_vector not in seen_values, f"load valuation is not injective: {identifier}")
            identifiers.add(identifier)
            seen_values.add(typed_vector)
            valuations[identifier] = vector
        return identifiers, valuations

    def projection(self, vector: tuple[Any, ...], block: Sequence[str]) -> tuple[Any, ...]:
        positions = [self.atoms.index(atom) for atom in block]
        return tuple(_typed_scalar(vector[position]) for position in positions)

    def _validate_pending_semantics(self) -> None:
        updates = {
            action: str(record["pending_atom"])
            for action, record in self.actions.items()
            if record["kind"] == "update"
        }
        pending_atoms = {atom for atom, kind in self.atom_kinds.items() if kind == "pending"}
        require(
            len(updates) == len(pending_atoms) and set(updates.values()) == pending_atoms,
            "pending atoms and update actions are not bijective",
        )
        positions = {atom: self.atoms.index(atom) for atom in pending_atoms}
        for state in self.states:
            for atom in pending_atoms:
                require(type(self.state_values[state][positions[atom]]) is bool, f"pending valuation is not Boolean: {state}/{atom}")
        for state in self.initials:
            require(all(self.state_values[state][positions[atom]] is True for atom in pending_atoms), f"initial pending set is incomplete: {state}")
        for (source, action), targets in self.post.items():
            source_values = self.state_values[source]
            record = self.actions[action]
            if record["kind"] == "update":
                pending = str(record["pending_atom"])
                require(source_values[positions[pending]] is True, f"non-pending update is enabled: {source}/{action}")
            for target in targets:
                target_values = self.state_values[target]
                for atom in pending_atoms:
                    expected = False if record["kind"] == "update" and atom == record["pending_atom"] else source_values[positions[atom]]
                    require(target_values[positions[atom]] is expected, f"pending projection differs: {source}/{action}/{target}/{atom}")
        for goal in self.goals:
            require(all(self.state_values[goal][positions[atom]] is False for atom in pending_atoms), f"Goal retains a pending update: {goal}")


def _missing_product(
    projections: list[set[tuple[Any, ...]]],
    observed: set[tuple[tuple[Any, ...], ...]],
) -> tuple[tuple[Any, ...], ...] | None:
    for candidate in itertools.product(*(sorted(values, key=repr) for values in projections)):
        if candidate not in observed:
            return tuple(candidate)
    return None


def rectangular_obstruction(
    game: TypedFlatGame,
    identifiers: set[str],
    values: Mapping[str, tuple[Any, ...]],
    partition: tuple[tuple[str, ...], ...],
    kind: str,
) -> dict[str, Any] | None:
    projected = [
        {game.projection(values[identifier], block) for identifier in identifiers}
        for block in partition
    ]
    observed = {
        tuple(game.projection(values[identifier], block) for block in partition)
        for identifier in identifiers
    }
    expected_count = 1
    for domain in projected:
        expected_count *= len(domain)
    if expected_count == len(observed):
        return None
    missing = _missing_product(projected, observed)
    return {
        "kind": f"{kind}_NONRECTANGULAR",
        "expected_count": expected_count,
        "observed_count": len(observed),
        "missing_projection_tuple": missing,
    }


def handover_obstruction(
    game: TypedFlatGame,
    partition: tuple[tuple[str, ...], ...],
) -> dict[str, Any] | None:
    projected: list[set[tuple[tuple[Any, ...], tuple[Any, ...]]]] = []
    observed: set[tuple[tuple[tuple[Any, ...], tuple[Any, ...]], ...]] = set()
    for block in partition:
        projected.append({
            (game.projection(game.state_values[goal], block), game.projection(game.load_values[load], block))
            for goal, load in game.handover
        })
    for goal, load in game.handover:
        observed.add(tuple(
            (game.projection(game.state_values[goal], block), game.projection(game.load_values[load], block))
            for block in partition
        ))
    expected_count = 1
    for domain in projected:
        expected_count *= len(domain)
    if expected_count == len(observed):
        return None
    missing = _missing_product(projected, observed)
    return {
        "kind": "HANDOVER_NONRECTANGULAR",
        "expected_count": expected_count,
        "observed_count": len(observed),
        "missing_projection_tuple": missing,
    }


def local_action_obstruction(
    game: TypedFlatGame,
    action: str,
    block: tuple[str, ...],
    partition: tuple[tuple[str, ...], ...],
) -> dict[str, Any] | None:
    other_atoms = tuple(atom for candidate in partition if candidate != block for atom in candidate)
    contexts: dict[tuple[Any, ...], tuple[frozenset[tuple[Any, ...]], str]] = {}
    for source in sorted(game.states):
        source_values = game.state_values[source]
        targets = game.post.get((source, action), frozenset())
        for target in targets:
            if game.projection(game.state_values[target], other_atoms) != game.projection(source_values, other_atoms):
                return {
                    "kind": "ACTION_FOREIGN_FRAME",
                    "action": action,
                    "source": source,
                    "target": target,
                    "owner_block": block,
                }
        local_source = game.projection(source_values, block)
        local_targets = frozenset(game.projection(game.state_values[target], block) for target in targets)
        previous = contexts.get(local_source)
        if previous is not None and previous[0] != local_targets:
            return {
                "kind": "ACTION_CONTEXT_DEPENDENCE",
                "action": action,
                "local_source": local_source,
                "first_context_state": previous[1],
                "second_context_state": source,
                "first_local_targets": sorted(previous[0], key=repr),
                "second_local_targets": sorted(local_targets, key=repr),
            }
        contexts[local_source] = (local_targets, source)
    return None


def verify_partition(
    game: TypedFlatGame,
    partition: tuple[tuple[str, ...], ...],
) -> tuple[dict[str, str] | None, dict[str, Any] | None]:
    atoms = {atom for block in partition for atom in block}
    if atoms != set(game.atoms) or sum(len(block) for block in partition) != len(game.atoms) or not all(partition):
        return None, {"kind": "PARTITION_DOMAIN_MISMATCH"}

    owner = {atom: index for index, block in enumerate(partition) for atom in block}
    for dependency in game.dependencies:
        blocks = sorted({owner[atom] for atom in dependency["atoms"]})
        if len(blocks) != 1:
            return None, {
                "kind": "CROSS_TYPED_DEPENDENCY",
                "dependency_kind": dependency["kind"],
                "atoms": dependency["atoms"],
                "blocks": blocks,
                "detail": dependency["detail"],
            }

    for label, identifiers, values in (
        ("STATE", game.states, game.state_values),
        ("ROOT", game.initials, game.state_values),
        ("SAFE", game.safe, game.state_values),
        ("GOAL", game.goals, game.state_values),
        ("LOAD", game.loads, game.load_values),
    ):
        obstruction = rectangular_obstruction(game, identifiers, values, partition, label)
        if obstruction is not None:
            return None, obstruction
    obstruction = handover_obstruction(game, partition)
    if obstruction is not None:
        return None, obstruction

    assignment: dict[str, str] = {}
    for action, record in sorted(game.actions.items()):
        if record["kind"] == "shared_stutter":
            for source in sorted(game.states):
                if game.post.get((source, action), frozenset()) != frozenset({source}):
                    return None, {"kind": "SHARED_NOT_GLOBAL_PURE_STUTTER", "action": action, "source": source}
            assignment[action] = "<shared-stutter>"
            continue
        subject_blocks = {owner[atom] for atom in record["subjects"]}
        if len(subject_blocks) != 1:
            return None, {
                "kind": "ACTION_SUBJECTS_CROSS_BLOCK",
                "action": action,
                "subjects": sorted(record["subjects"]),
                "blocks": sorted(subject_blocks),
            }
        block_index = next(iter(subject_blocks))
        block = partition[block_index]
        obstruction = local_action_obstruction(game, action, block, partition)
        if obstruction is not None:
            return None, obstruction
        assignment[action] = ",".join(block)

    local_goal = [
        {game.projection(game.state_values[goal], block) for goal in game.goals}
        for block in partition
    ]
    for action, record in sorted(game.actions.items()):
        if record["controllability"] != "uncontrollable" or record["kind"] == "shared_stutter":
            continue
        block_index = next(iter({owner[atom] for atom in record["subjects"]}))
        block = partition[block_index]
        for source in sorted(game.states):
            if (
                game.projection(game.state_values[source], block) in local_goal[block_index]
                and game.post.get((source, action), frozenset())
            ):
                return None, {
                    "kind": "GOAL_UNCONTROLLABLE_ACTIVITY",
                    "action": action,
                    "source": source,
                    "owner_block": block,
                }
    return assignment, None


def discover(
    raw: Mapping[str, Any],
    *,
    partition_limit: int = 2_000_000,
    maximum_partition_count: int = 10_000,
) -> dict[str, Any]:
    require(
        type(partition_limit) is int and partition_limit >= 0,
        "partition verification limit must be a nonnegative integer",
    )
    require(
        type(maximum_partition_count) is int and maximum_partition_count >= 1,
        "maximum-partition count limit must be a positive integer; result is inconclusive",
    )
    game = TypedFlatGame(raw)
    units = mandatory_units(game)
    unit_ids = tuple(str(index) for index in range(len(units)))
    one = normalize_partition([game.atoms])
    evaluated = 0

    def checked(partition: tuple[tuple[str, ...], ...]) -> tuple[dict[str, str] | None, dict[str, Any] | None]:
        nonlocal evaluated
        evaluated += 1
        if evaluated > partition_limit:
            raise DiscoveryError(
                f"explicit partition verification limit exceeded ({partition_limit}); result is inconclusive"
            )
        return verify_partition(game, partition)

    assignment, obstruction = checked(one)
    if obstruction is not None:
        result = {
            "schema_version": CERT_SCHEMA,
            "input_game_sha256": sha256_json(raw),
            "game_id": game.identifier,
            "result": "INELIGIBLE",
            "maximum_block_count": 0,
            "maximum_partition_count": 0,
            "selected_partition": [],
            "mandatory_units": [list(block) for block in mandatory_units(game)],
            "action_assignment": {},
            "evaluated_partition_count": evaluated,
            "root_cut_ledger": [],
            "ineligibility_obstruction": obstruction,
            "scope": "exact-relative-to-supplied-atoms-and-complete-table",
        }
        return result

    selected: tuple[tuple[str, ...], ...] | None = None
    maximum_count = 0
    maximum_seen = 0
    selected_assignment: dict[str, str] | None = None
    if len(units) > 1:
        singleton = units
        singleton_assignment, singleton_obstruction = checked(singleton)
        if singleton_obstruction is None:
            selected = singleton
            maximum_count = len(singleton)
            maximum_seen = 1
            selected_assignment = singleton_assignment
    if selected is None:
        for block_count in range(len(units) - 1, 1, -1):
            for unit_partition in set_partitions(unit_ids, block_count):
                partition = expand_unit_partition(unit_partition, units)
                candidate_assignment, candidate_obstruction = checked(partition)
                if candidate_obstruction is None:
                    maximum_seen += 1
                    if maximum_seen > maximum_partition_count:
                        raise DiscoveryError(
                            "maximum-partition count limit exceeded; result is inconclusive"
                        )
                    if selected is None or partition < selected:
                        selected = partition
                        selected_assignment = candidate_assignment
            if selected is not None:
                maximum_count = block_count
                break
    if selected is None:
        selected = one
        maximum_count = 1
        maximum_seen = 1
        selected_assignment = assignment

    if selected_assignment is None:
        selected_assignment, obstruction = checked(selected)
        require(obstruction is None and selected_assignment is not None, "selected partition failed recheck")

    root_ledger: list[dict[str, Any]] = []
    if len(units) > 1:
        for unit_partition in set_partitions(unit_ids, 2):
            partition = expand_unit_partition(unit_partition, units)
            root_assignment, root_obstruction = checked(partition)
            root_ledger.append({
                "cut": partition,
                "status": "PASS" if root_obstruction is None else "FAIL",
                "obstruction": root_obstruction,
                "action_assignment": root_assignment or {},
            })

    return {
        "schema_version": CERT_SCHEMA,
        "input_game_sha256": sha256_json(raw),
        "game_id": game.identifier,
        "result": "FACTORED" if len(selected) > 1 else "NON_FACTORABLE",
        "maximum_block_count": maximum_count,
        "maximum_partition_count": maximum_seen,
        "selected_partition": [list(block) for block in selected],
        "mandatory_units": [list(block) for block in units],
        "action_assignment": selected_assignment,
        "evaluated_partition_count": evaluated,
        "root_cut_ledger": root_ledger,
        "ineligibility_obstruction": None,
        "scope": "exact-relative-to-supplied-atoms-and-complete-table",
    }


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise DiscoveryError(f"invalid JSON: {path}") from error
    require(isinstance(value, dict), "JSON root must be an object")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--partition-limit", type=int, default=2_000_000)
    parser.add_argument("--maximum-partition-count", type=int, default=10_000)
    args = parser.parse_args(argv)
    raw = load_json(args.input)
    certificate = discover(
        raw,
        partition_limit=args.partition_limit,
        maximum_partition_count=args.maximum_partition_count,
    )
    payload = json.dumps(certificate, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(payload, end="")
    else:
        args.output.write_text(payload, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
