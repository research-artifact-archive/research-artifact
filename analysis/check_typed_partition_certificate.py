#!/usr/bin/env python3
"""Independent consumer for typed partition and obstruction certificates.

This module intentionally does not import ``discover_typed_partition``.  It
reparses the flat table, recomputes factor obligations, enumerates all set
partitions within the registered bound, and checks maximum block count and all
root-cut obstruction classifications from scratch.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence


GAME_SCHEMA = "fg-ducs-typed-flat-game-v1"
CERT_SCHEMA = "fg-ducs-partition-certificate-v1"
SEMANTICS = "complete-explicit-post-including-goal-and-unsafe-v1"


class CertificateError(RuntimeError):
    pass


def need(condition: bool, message: str) -> None:
    if not condition:
        raise CertificateError(message)


def canonical_sha(value: Any) -> str:
    payload = canonical_json(value) + b"\n"
    return hashlib.sha256(payload).hexdigest()


def canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise CertificateError("value is not canonical finite JSON") from error


def strict_json_equal(left: Any, right: Any) -> bool:
    return canonical_json(left) == canonical_json(right)


def partition_payload(value: Any, label: str, *, allow_empty: bool) -> list[list[str]]:
    need(isinstance(value, list), f"{label} is not a list")
    need(allow_empty or bool(value), f"{label} is empty")
    seen: set[str] = set()
    for block in value:
        need(
            isinstance(block, (list, tuple))
            and bool(block)
            and all(isinstance(atom, str) and atom for atom in block),
            f"{label} block differs",
        )
        need(len(block) == len(set(block)), f"{label} block has duplicates")
        need(not (seen & set(block)), f"{label} repeats an atom")
        seen.update(block)
    return value


def json_scalar(value: Any) -> bool:
    return (
        value is None
        or type(value) is str
        or type(value) is bool
        or type(value) is int
        or (type(value) is float and math.isfinite(value))
    )


def typed_scalar(value: Any) -> tuple[str, Any]:
    if value is None:
        return ("null", None)
    if type(value) is bool:
        return ("bool", value)
    if type(value) in {int, float}:
        need(type(value) is int or math.isfinite(value), "non-finite JSON number")
        return ("number", value)
    need(type(value) is str, "value is not a JSON scalar")
    return ("string", value)


def norm(blocks: Sequence[Sequence[str]]) -> tuple[tuple[str, ...], ...]:
    return tuple(sorted((tuple(sorted(block)) for block in blocks), key=lambda block: block))


def partitions(items: Sequence[str]) -> Iterator[tuple[tuple[str, ...], ...]]:
    ordered = tuple(sorted(items))
    blocks: list[list[str]] = []

    def walk(index: int) -> Iterator[tuple[tuple[str, ...], ...]]:
        if index == len(ordered):
            yield norm(blocks)
            return
        item = ordered[index]
        for block in blocks:
            block.append(item)
            yield from walk(index + 1)
            block.pop()
        blocks.append([item])
        yield from walk(index + 1)
        blocks.pop()

    yield from walk(0)


def dependency_units(table: "IndependentTable") -> tuple[tuple[str, ...], ...]:
    parent = {atom: atom for atom in table.atoms}

    def root(atom: str) -> str:
        trail = []
        while parent[atom] != atom:
            trail.append(atom)
            atom = parent[atom]
        for child in trail:
            parent[child] = atom
        return atom

    def merge(left: str, right: str) -> None:
        a, b = root(left), root(right)
        if a == b:
            return
        if a > b:
            a, b = b, a
        parent[b] = a

    for _kind, members, _detail in table.dependencies:
        ordered = sorted(members)
        for member in ordered[1:]:
            merge(ordered[0], member)
    groups: dict[str, list[str]] = {}
    for atom in table.atoms:
        groups.setdefault(root(atom), []).append(atom)
    return norm(list(groups.values()))


def expand_partition(
    unit_part: tuple[tuple[str, ...], ...],
    units: tuple[tuple[str, ...], ...],
) -> tuple[tuple[str, ...], ...]:
    return norm([
        atom for unit_index in block for atom in units[int(unit_index)]
    ] for block in unit_part)


class IndependentTable:
    def __init__(self, raw: Mapping[str, Any]) -> None:
        expected = {
            "schema_version", "id", "semantics", "atoms", "actions", "states",
            "buckets", "load_states", "handover_relation", "dependencies", "provenance",
        }
        need(set(raw) == expected, "typed input fields differ")
        need(raw.get("schema_version") == GAME_SCHEMA and raw.get("semantics") == SEMANTICS, "typed input schema/semantics differ")
        need(isinstance(raw.get("id"), str) and raw["id"] and isinstance(raw.get("provenance"), dict), "typed input identity differs")

        atom_records = raw.get("atoms")
        need(isinstance(atom_records, list) and atom_records, "atom table differs")
        self.kinds: dict[str, str] = {}
        for record in atom_records:
            need(isinstance(record, dict) and set(record) == {"id", "kind"}, "atom record differs")
            atom = record.get("id")
            kind = record.get("kind")
            need(isinstance(atom, str) and atom and atom not in self.kinds, "atom id differs")
            need("," not in atom and atom != "<shared-stutter>", "atom id uses a reserved assignment delimiter")
            need(kind in {"component", "monitor", "rs", "pending", "load", "auxiliary"}, "atom kind differs")
            self.kinds[atom] = str(kind)
        self.atoms = tuple(sorted(self.kinds))
        atom_set = set(self.atoms)
        self.position = {atom: index for index, atom in enumerate(self.atoms)}

        action_records = raw.get("actions")
        need(isinstance(action_records, list), "action table differs")
        self.actions: dict[str, tuple[str, str, frozenset[str], str | None]] = {}
        for record in action_records:
            need(isinstance(record, dict) and set(record) == {"id", "controllability", "kind", "subjects", "pending_atom"}, "action record differs")
            action = record.get("id")
            control = record.get("controllability")
            kind = record.get("kind")
            subjects_raw = record.get("subjects")
            pending = record.get("pending_atom")
            need(isinstance(action, str) and action and action not in self.actions, "action id differs")
            need(control in {"controllable", "uncontrollable"} and kind in {"update", "normal", "shared_stutter"}, "action type differs")
            need(isinstance(subjects_raw, list) and len(subjects_raw) == len(set(subjects_raw)) and all(isinstance(x, str) and x in atom_set for x in subjects_raw), "action subjects differ")
            subjects = frozenset(subjects_raw)
            if kind == "update":
                need(control == "controllable" and isinstance(pending, str) and self.kinds.get(pending) == "pending" and pending in subjects, "update action typing differs")
            else:
                need(pending is None, "normal/shared action has a pending atom")
            if kind == "shared_stutter":
                need(control == "controllable" and not subjects, "shared stutter typing differs")
            else:
                need(bool(subjects), "local action lacks subjects")
            self.actions[action] = (str(control), str(kind), subjects, pending if isinstance(pending, str) else None)

        self.states: dict[str, tuple[Any, ...]] = {}
        self.initial: set[str] = set()
        self.safe: set[str] = set()
        self.goal: set[str] = set()
        state_records = raw.get("states")
        need(isinstance(state_records, list) and state_records, "state table differs")
        seen_state_values: set[tuple[tuple[str, Any], ...]] = set()
        for record in state_records:
            need(isinstance(record, dict) and set(record) == {"id", "valuation", "initial", "safe", "goal"}, "state record differs")
            identifier = record.get("id")
            valuation = record.get("valuation")
            need(isinstance(identifier, str) and identifier and identifier not in self.states, "state id differs")
            need(isinstance(valuation, dict) and set(valuation) == atom_set, "state valuation domain differs")
            vector = tuple(valuation[atom] for atom in self.atoms)
            need(all(json_scalar(x) for x in vector), "state valuation is not a finite JSON scalar")
            typed_vector = tuple(typed_scalar(x) for x in vector)
            need(typed_vector not in seen_state_values, "state valuation differs")
            need(all(type(record.get(flag)) is bool for flag in ("initial", "safe", "goal")), "state flags differ")
            self.states[identifier] = vector
            seen_state_values.add(typed_vector)
            if record["initial"]:
                self.initial.add(identifier)
            if record["safe"]:
                self.safe.add(identifier)
            if record["goal"]:
                self.goal.add(identifier)
        need(self.initial and self.goal and self.goal <= self.safe, "Q0/Safe/Goal typing differs")

        self.loads: dict[str, tuple[Any, ...]] = {}
        load_records = raw.get("load_states")
        need(isinstance(load_records, list) and load_records, "load table differs")
        seen_load_values: set[tuple[tuple[str, Any], ...]] = set()
        for record in load_records:
            need(isinstance(record, dict) and set(record) == {"id", "valuation"}, "load record differs")
            identifier = record.get("id")
            valuation = record.get("valuation")
            need(isinstance(identifier, str) and identifier and identifier not in self.loads, "load id differs")
            need(isinstance(valuation, dict) and set(valuation) == atom_set, "load valuation domain differs")
            vector = tuple(valuation[atom] for atom in self.atoms)
            need(all(json_scalar(x) for x in vector), "load valuation is not a finite JSON scalar")
            typed_vector = tuple(typed_scalar(x) for x in vector)
            need(typed_vector not in seen_load_values, "load valuation differs")
            self.loads[identifier] = vector
            seen_load_values.add(typed_vector)

        self.post: dict[tuple[str, str], frozenset[str]] = {}
        buckets = raw.get("buckets")
        need(isinstance(buckets, list), "bucket table differs")
        for record in buckets:
            need(isinstance(record, dict) and set(record) == {"source", "action", "targets"}, "bucket record differs")
            source, action, targets = record.get("source"), record.get("action"), record.get("targets")
            need(source in self.states and action in self.actions and isinstance(targets, list) and targets and len(targets) == len(set(targets)) and set(targets) <= set(self.states), "bucket typing differs")
            key = (str(source), str(action))
            need(key not in self.post, "duplicate bucket")
            self.post[key] = frozenset(targets)

        handover_records = raw.get("handover_relation")
        need(isinstance(handover_records, list), "handover table differs")
        self.handover: set[tuple[str, str]] = set()
        for record in handover_records:
            need(isinstance(record, dict) and set(record) == {"goal", "load"}, "handover record differs")
            pair = (record.get("goal"), record.get("load"))
            need(pair[0] in self.goal and pair[1] in self.loads and pair not in self.handover, "handover typing differs")
            self.handover.add((str(pair[0]), str(pair[1])))
        need({goal for goal, _ in self.handover} == self.goal, "handover domain differs")

        dependency_records = raw.get("dependencies")
        need(isinstance(dependency_records, list), "dependency table differs")
        self.dependencies: list[tuple[str, frozenset[str], str]] = []
        seen_dependencies: set[tuple[str, frozenset[str]]] = set()
        for record in dependency_records:
            need(isinstance(record, dict) and set(record) == {"kind", "atoms", "detail"}, "dependency record differs")
            kind, members, detail = record.get("kind"), record.get("atoms"), record.get("detail")
            need(kind in {"component", "requirement", "precedence", "start", "iota", "handover", "pending"}, "dependency kind differs")
            need(isinstance(members, list) and len(members) >= 2 and len(members) == len(set(members)) and set(members) <= atom_set, "dependency atoms differ")
            need(isinstance(detail, str), "dependency detail differs")
            key = (str(kind), frozenset(members))
            need(key not in seen_dependencies, "duplicate dependency")
            seen_dependencies.add(key)
            self.dependencies.append((str(kind), frozenset(members), detail))
        self._pending_check()

    def project(self, vector: tuple[Any, ...], block: Sequence[str]) -> tuple[Any, ...]:
        return tuple(typed_scalar(vector[self.position[atom]]) for atom in block)

    def _pending_check(self) -> None:
        update_to_pending = {
            action: pending
            for action, (_control, kind, _subjects, pending) in self.actions.items()
            if kind == "update"
        }
        pending_atoms = {atom for atom, kind in self.kinds.items() if kind == "pending"}
        need(
            len(update_to_pending) == len(pending_atoms)
            and set(update_to_pending.values()) == pending_atoms,
            "pending/update bijection differs",
        )
        for vector in self.states.values():
            need(all(type(vector[self.position[atom]]) is bool for atom in pending_atoms), "pending value is not Boolean")
        for state in self.initial:
            need(all(self.states[state][self.position[atom]] is True for atom in pending_atoms), "initial pending set differs")
        for (source, action), targets in self.post.items():
            control, kind, _subjects, pending = self.actions[action]
            del control
            before = self.states[source]
            if kind == "update":
                need(before[self.position[str(pending)]] is True, "non-pending update is enabled")
            for target in targets:
                after = self.states[target]
                for atom in pending_atoms:
                    expected = False if kind == "update" and atom == pending else before[self.position[atom]]
                    need(after[self.position[atom]] is expected, "pending transition differs")
        for state in self.goal:
            need(all(self.states[state][self.position[atom]] is False for atom in pending_atoms), "Goal retains pending action")


def first_missing(domains: list[set[Any]], observed: set[tuple[Any, ...]]) -> tuple[Any, ...] | None:
    for value in itertools.product(*(sorted(domain, key=repr) for domain in domains)):
        if value not in observed:
            return value
    return None


def rectangular(table: IndependentTable, ids: set[str], values: Mapping[str, tuple[Any, ...]], part: tuple[tuple[str, ...], ...], label: str) -> dict[str, Any] | None:
    domains = [{table.project(values[i], block) for i in ids} for block in part]
    observed = {tuple(table.project(values[i], block) for block in part) for i in ids}
    expected = 1
    for domain in domains:
        expected *= len(domain)
    if expected == len(observed):
        return None
    return {"kind": label + "_NONRECTANGULAR", "expected_count": expected, "observed_count": len(observed), "missing_projection_tuple": first_missing(domains, observed)}


def check_part(table: IndependentTable, part: tuple[tuple[str, ...], ...]) -> tuple[dict[str, str] | None, dict[str, Any] | None]:
    if {x for block in part for x in block} != set(table.atoms) or sum(map(len, part)) != len(table.atoms):
        return None, {"kind": "PARTITION_DOMAIN_MISMATCH"}
    owner = {atom: i for i, block in enumerate(part) for atom in block}
    for kind, members, detail in table.dependencies:
        blocks = sorted({owner[atom] for atom in members})
        if len(blocks) > 1:
            return None, {"kind": "CROSS_TYPED_DEPENDENCY", "dependency_kind": kind, "atoms": tuple(sorted(members)), "blocks": blocks, "detail": detail}
    for label, ids, values in (
        ("STATE", set(table.states), table.states),
        ("ROOT", table.initial, table.states),
        ("SAFE", table.safe, table.states),
        ("GOAL", table.goal, table.states),
        ("LOAD", set(table.loads), table.loads),
    ):
        problem = rectangular(table, ids, values, part, label)
        if problem:
            return None, problem

    h_domains = [
        {(table.project(table.states[g], block), table.project(table.loads[z], block)) for g, z in table.handover}
        for block in part
    ]
    h_observed = {
        tuple((table.project(table.states[g], block), table.project(table.loads[z], block)) for block in part)
        for g, z in table.handover
    }
    expected_h = 1
    for domain in h_domains:
        expected_h *= len(domain)
    if expected_h != len(h_observed):
        return None, {"kind": "HANDOVER_NONRECTANGULAR", "expected_count": expected_h, "observed_count": len(h_observed), "missing_projection_tuple": first_missing(h_domains, h_observed)}

    assignment: dict[str, str] = {}
    for action in sorted(table.actions):
        control, kind, subjects, _pending = table.actions[action]
        if kind == "shared_stutter":
            for source in sorted(table.states):
                if table.post.get((source, action), frozenset()) != frozenset({source}):
                    return None, {"kind": "SHARED_NOT_GLOBAL_PURE_STUTTER", "action": action, "source": source}
            assignment[action] = "<shared-stutter>"
            continue
        blocks = {owner[atom] for atom in subjects}
        if len(blocks) != 1:
            return None, {"kind": "ACTION_SUBJECTS_CROSS_BLOCK", "action": action, "subjects": sorted(subjects), "blocks": sorted(blocks)}
        block_index = next(iter(blocks))
        block = part[block_index]
        outside = tuple(atom for i, candidate in enumerate(part) if i != block_index for atom in candidate)
        by_local: dict[tuple[Any, ...], tuple[frozenset[tuple[Any, ...]], str]] = {}
        for source in sorted(table.states):
            source_vector = table.states[source]
            targets = table.post.get((source, action), frozenset())
            for target in targets:
                if table.project(table.states[target], outside) != table.project(source_vector, outside):
                    return None, {"kind": "ACTION_FOREIGN_FRAME", "action": action, "source": source, "target": target, "owner_block": block}
            key = table.project(source_vector, block)
            projected_targets = frozenset(table.project(table.states[target], block) for target in targets)
            previous = by_local.get(key)
            if previous is not None and previous[0] != projected_targets:
                return None, {"kind": "ACTION_CONTEXT_DEPENDENCE", "action": action, "local_source": key, "first_context_state": previous[1], "second_context_state": source, "first_local_targets": sorted(previous[0], key=repr), "second_local_targets": sorted(projected_targets, key=repr)}
            by_local[key] = (projected_targets, source)
        assignment[action] = ",".join(block)

        if control == "uncontrollable":
            local_goals = {table.project(table.states[g], block) for g in table.goal}
            for source in sorted(table.states):
                if table.project(table.states[source], block) in local_goals and table.post.get((source, action), frozenset()):
                    return None, {"kind": "GOAL_UNCONTROLLABLE_ACTIVITY", "action": action, "source": source, "owner_block": block}
    return assignment, None


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CertificateError(f"invalid JSON: {path}") from error
    need(isinstance(value, dict), "JSON root is not an object")
    return value


def check(game_raw: Mapping[str, Any], certificate: Mapping[str, Any], *, max_atoms: int = 9) -> dict[str, Any]:
    expected_fields = {
        "schema_version", "input_game_sha256", "game_id", "result",
        "maximum_block_count", "maximum_partition_count", "selected_partition",
        "mandatory_units", "action_assignment", "evaluated_partition_count", "root_cut_ledger",
        "ineligibility_obstruction", "scope",
    }
    need(set(certificate) == expected_fields and certificate.get("schema_version") == CERT_SCHEMA, "certificate schema differs")
    for field in ("maximum_block_count", "maximum_partition_count", "evaluated_partition_count"):
        need(type(certificate.get(field)) is int and certificate[field] >= 0, f"certificate {field} is not a nonnegative integer")
    need(certificate.get("result") in {"FACTORED", "NON_FACTORABLE", "INELIGIBLE"}, "certificate result value differs")
    need(isinstance(certificate.get("scope"), str), "certificate scope type differs")
    partition_payload(certificate.get("mandatory_units"), "mandatory units", allow_empty=False)
    partition_payload(certificate.get("selected_partition"), "selected partition", allow_empty=True)
    need(certificate.get("input_game_sha256") == canonical_sha(game_raw), "certificate input hash differs")
    table = IndependentTable(game_raw)
    need(certificate.get("game_id") == game_raw.get("id"), "certificate game id differs")
    need(len(table.atoms) <= max_atoms, f"independent exhaustive checker atom bound exceeded: {len(table.atoms)} > {max_atoms}")

    units = dependency_units(table)
    need(norm(certificate.get("mandatory_units")) == units, "mandatory dependency units differ")
    unit_ids = tuple(str(index) for index in range(len(units)))
    candidate_parts = {
        expand_partition(part, units)
        for part in partitions(unit_ids)
    }
    valid: list[tuple[tuple[str, ...], ...]] = []
    obstructions: dict[tuple[tuple[str, ...], ...], dict[str, Any]] = {}
    assignments: dict[tuple[tuple[str, ...], ...], dict[str, str]] = {}
    for part in sorted(candidate_parts):
        assignment, problem = check_part(table, part)
        if problem is None:
            valid.append(part)
            assignments[part] = assignment or {}
        else:
            obstructions[part] = problem

    if not valid:
        need(certificate.get("result") == "INELIGIBLE", "ineligible result differs")
        need(
            certificate.get("maximum_block_count") == 0
            and certificate.get("maximum_partition_count") == 0
            and certificate.get("selected_partition") == [],
            "ineligible maximum differs",
        )
        one = norm([table.atoms])
        need(
            strict_json_equal(certificate.get("ineligibility_obstruction"), obstructions[one]),
            "ineligibility obstruction differs",
        )
        need(certificate.get("action_assignment") == {}, "ineligible action assignment differs")
        need(certificate.get("root_cut_ledger") == [], "ineligible root-cut ledger differs")
        need(certificate.get("evaluated_partition_count") == 1, "ineligible evaluated count differs")
        need(certificate.get("scope") == "exact-relative-to-supplied-atoms-and-complete-table", "ineligible scope differs")
        return {"status": "PASS", "result": "INELIGIBLE", "atom_count": len(table.atoms), "valid_partition_count": 0}

    maximum_count = max(len(part) for part in valid)
    maxima = sorted(part for part in valid if len(part) == maximum_count)
    selected = maxima[0]
    expected_result = "FACTORED" if maximum_count > 1 else "NON_FACTORABLE"
    need(certificate.get("result") == expected_result, "certificate result differs")
    need(certificate.get("maximum_block_count") == maximum_count, "maximum block count differs")
    need(certificate.get("maximum_partition_count") == len(maxima), "maximum partition count differs")
    need(norm(certificate.get("selected_partition")) == selected, "selected partition differs")
    need(certificate.get("action_assignment") == assignments[selected], "selected action assignment differs")
    need(certificate.get("ineligibility_obstruction") is None, "eligible certificate has ineligibility obstruction")
    need(certificate.get("scope") == "exact-relative-to-supplied-atoms-and-complete-table", "certificate scope differs")

    expected_root = []
    for part in sorted(p for p in candidate_parts if len(p) == 2):
        problem = obstructions.get(part)
        expected_root.append({
            "cut": part,
            "status": "FAIL" if problem is not None else "PASS",
            "obstruction": problem,
            "action_assignment": {} if problem is not None else assignments[part],
        })
    observed_root = certificate.get("root_cut_ledger")
    need(isinstance(observed_root, list), "root-cut ledger is not a list")
    def normalized_ledger(value: list[Any]) -> list[Any]:
        need(
            all(
                isinstance(record, dict)
                and set(record) == {"cut", "status", "obstruction", "action_assignment"}
                and isinstance(record.get("cut"), (list, tuple))
                for record in value
            ),
            "root-cut ledger record differs",
        )
        return sorted(value, key=lambda record: canonical_json(record["cut"]))
    need(
        strict_json_equal(normalized_ledger(observed_root), normalized_ledger(expected_root)),
        "root-cut ledger differs",
    )
    by_count: dict[int, list[tuple[tuple[str, ...], ...]]] = {}
    for part in candidate_parts:
        by_count.setdefault(len(part), []).append(part)
    expected_evaluated = 1
    if len(units) > 1:
        expected_evaluated += 1  # fully split mandatory units
        fully_split = norm(units)
        if fully_split not in valid:
            for block_count in range(len(units) - 1, 1, -1):
                expected_evaluated += len(by_count.get(block_count, []))
                if any(part in valid for part in by_count.get(block_count, [])):
                    break
        expected_evaluated += len(by_count.get(2, []))  # serialized root-cut ledger recheck
    need(certificate.get("evaluated_partition_count") == expected_evaluated, "evaluated partition count differs")
    return {
        "status": "PASS",
        "result": expected_result,
        "atom_count": len(table.atoms),
        "valid_partition_count": len(valid),
        "maximum_block_count": maximum_count,
        "maximum_partition_count": len(maxima),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("game", type=Path)
    parser.add_argument("certificate", type=Path)
    parser.add_argument("--max-atoms", type=int, default=12)
    args = parser.parse_args(argv)
    report = check(load(args.game), load(args.certificate), max_atoms=args.max_atoms)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
