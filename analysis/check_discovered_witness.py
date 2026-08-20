#!/usr/bin/env python3
"""Independent consumer for projected local games and transported witnesses.

The module imports only the independently implemented partition consumer.  It
does not import the discovery or witness producers.  It rebuilds every local
projection, re-solves all local and flat games, and compares the complete
serialized witness.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from check_typed_partition_certificate import (  # noqa: E402
    IndependentTable,
    check as check_partition,
    norm,
)


SCHEMA = "fg-ducs-discovered-witness-v1"


class TransportError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise TransportError(message)


def digest_json(value: Any) -> str:
    data = (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


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
        raise TransportError("witness is not canonical finite JSON") from error


def tuple_order(value: tuple[Any, ...]) -> str:
    return json.dumps(list(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def local_fixed_point(
    all_states: set[str],
    roots: set[str],
    safe: set[str],
    goal: set[str],
    controls: Mapping[str, str],
    edges: Mapping[tuple[str, str], tuple[str, ...]],
    relation: set[tuple[str, str]],
) -> dict[str, Any]:
    by_c: dict[str, list[str]] = defaultdict(list)
    by_u: dict[str, list[str]] = defaultdict(list)
    for state, action in edges:
        (by_c if controls[action] == "controllable" else by_u)[state].append(action)
    win = set(goal)
    layers = {state: 0 for state in goal}
    next_layer = 1
    while True:
        fresh: set[str] = set()
        for state in safe - win:
            if by_u[state]:
                ok = all(set(edges[(state, action)]) <= win for action in by_u[state])
            else:
                ok = any(set(edges[(state, action)]) <= win for action in by_c[state])
            if ok:
                fresh.add(state)
        if not fresh:
            break
        for state in fresh:
            layers[state] = next_layer
        win.update(fresh)
        next_layer += 1

    strategy: dict[str, str] = {}
    for state in sorted(win - goal):
        if by_u[state]:
            continue
        enabled = [
            action for action in sorted(by_c[state])
            if all(target in win and layers[target] < layers[state] for target in edges[(state, action)])
        ]
        require(bool(enabled), f"independent local strategy missing at {state}")
        strategy[state] = enabled[0]

    load_choice: dict[str, str] = {}
    for state in sorted(goal):
        targets = sorted(load for source, load in relation if source == state)
        require(bool(targets), f"independent local kappa missing at {state}")
        load_choice[state] = targets[0]

    lose = all_states - win
    spoiler: dict[str, Any] = {}
    for state in sorted(lose):
        if state not in safe:
            spoiler[state] = {"mode": "unsafe-terminal"}
        elif by_u[state]:
            candidates = sorted(
                (action, target)
                for action in by_u[state]
                for target in edges[(state, action)]
                if target in lose
            )
            require(bool(candidates), f"independent UC spoiler missing at {state}")
            action, target = candidates[0]
            spoiler[state] = {"mode": "uncontrollable", "action": action, "target": target}
        else:
            responses: dict[str, str] = {}
            for action in sorted(by_c[state]):
                candidates = sorted(target for target in edges[(state, action)] if target in lose)
                require(bool(candidates), f"independent outcome spoiler missing at {state}/{action}")
                responses[action] = candidates[0]
            spoiler[state] = {"mode": "controlled-outcomes", "responses": responses}
    return {
        "winning_region": sorted(win),
        "rank": {state: layers[state] for state in sorted(win)},
        "policy": strategy,
        "kappa": load_choice,
        "losing_region": sorted(lose),
        "losing_counterstrategy": spoiler,
        "all_initials_winning": roots <= win,
    }


def derive_factor(
    table: IndependentTable,
    index: int,
    block: tuple[str, ...],
    assignment: Mapping[str, str],
) -> dict[str, Any]:
    values = sorted({table.project(vector, block) for vector in table.states.values()}, key=tuple_order)
    names = {value: f"B{index}Q{number}" for number, value in enumerate(values)}
    load_values = sorted({table.project(vector, block) for vector in table.loads.values()}, key=tuple_order)
    load_names = {value: f"B{index}Z{number}" for number, value in enumerate(load_values)}
    roots = {names[table.project(table.states[state], block)] for state in table.initial}
    safe = {names[table.project(table.states[state], block)] for state in table.safe}
    goals = {names[table.project(table.states[state], block)] for state in table.goal}
    controls = {
        action: table.actions[action][0]
        for action, owner in assignment.items()
        if owner == ",".join(block)
    }

    contexts: dict[tuple[Any, ...], list[str]] = defaultdict(list)
    for state, vector in table.states.items():
        contexts[table.project(vector, block)].append(state)
    local_edges: dict[tuple[str, str], tuple[str, ...]] = {}
    for value in values:
        for action in sorted(controls):
            variants = {
                tuple(sorted({names[table.project(table.states[target], block)] for target in table.post.get((source, action), frozenset())}))
                for source in contexts[value]
            }
            require(len(variants) == 1, f"independent context mismatch at {action}/{value}")
            targets = next(iter(variants))
            if targets:
                local_edges[(names[value], action)] = targets
    relation = {
        (
            names[table.project(table.states[goal], block)],
            load_names[table.project(table.loads[load], block)],
        )
        for goal, load in table.handover
    }
    solved = local_fixed_point(set(names.values()), roots, safe, goals, controls, local_edges, relation)
    return {
        "id": f"B{index}",
        "atoms": list(block),
        "states": [{"id": names[value], "valuation": list(value)} for value in values],
        "initial_states": sorted(roots),
        "safe_states": sorted(safe),
        "goal_states": sorted(goals),
        "load_states": [{"id": load_names[value], "valuation": list(value)} for value in load_values],
        "actions": [{"id": action, "controllability": controls[action]} for action in sorted(controls)],
        "buckets": [
            {"source": source, "action": action, "targets": list(targets)}
            for (source, action), targets in sorted(local_edges.items())
        ],
        "handover_relation": [{"goal": goal, "load": load} for goal, load in sorted(relation)],
        **solved,
    }


def solve_flat(table: IndependentTable) -> set[str]:
    shared = {action for action, (_control, kind, _subjects, _pending) in table.actions.items() if kind == "shared_stutter"}
    c_actions = {action for action, (control, _kind, _subjects, _pending) in table.actions.items() if control == "controllable" and action not in shared}
    u_actions = {action for action, (control, _kind, _subjects, _pending) in table.actions.items() if control == "uncontrollable"}
    win = set(table.goal)
    while True:
        fresh: set[str] = set()
        for state in table.safe - win:
            enabled_u = [action for action in u_actions if (state, action) in table.post]
            if enabled_u:
                ok = all(table.post[(state, action)] <= win for action in enabled_u)
            else:
                ok = any(table.post[(state, action)] <= win for action in c_actions if (state, action) in table.post)
            if ok:
                fresh.add(state)
        if not fresh:
            return win
        win.update(fresh)


def expected_witness(
    game_raw: Mapping[str, Any],
    partition_certificate: Mapping[str, Any],
) -> dict[str, Any]:
    check_partition(game_raw, partition_certificate, max_atoms=12)
    require(partition_certificate.get("result") == "FACTORED", "transport certificate requires a factored input")
    table = IndependentTable(game_raw)
    part = norm(partition_certificate.get("selected_partition"))
    assignment = partition_certificate.get("action_assignment")
    require(isinstance(assignment, dict), "partition action assignment differs")
    factors = [derive_factor(table, index, block, assignment) for index, block in enumerate(part)]
    state_maps = [
        {tuple(record["valuation"]): record["id"] for record in factor["states"]}
        for factor in factors
    ]
    load_maps = [
        {tuple(record["valuation"]): record["id"] for record in factor["load_states"]}
        for factor in factors
    ]
    factored_win = {
        state for state, vector in table.states.items()
        if all(
            state_maps[index][table.project(vector, block)] in set(factors[index]["winning_region"])
            for index, block in enumerate(part)
        )
    }
    flat_win = solve_flat(table)
    require(flat_win == factored_win, "independent flat/factored winning regions differ")
    decision = "realizable" if table.initial <= factored_win else "unrealizable"
    global_record: dict[str, Any] = {
        "decision": decision,
        "semantic_flat_state_count": len(table.states),
        "factored_local_state_count": sum(len(factor["states"]) for factor in factors),
        "direct_flat_winning_region": sorted(flat_win),
        "factored_winning_region": sorted(factored_win),
        "direct_flat_decision_agrees": True,
    }
    if decision == "realizable":
        rank: dict[str, int] = {}
        policy: dict[str, str] = {}
        kappa: dict[str, str] = {}
        uncontrollable = {action for action, (control, _kind, _subjects, _pending) in table.actions.items() if control == "uncontrollable"}
        for state in sorted(factored_win):
            vector = table.states[state]
            locals_at_state = [state_maps[index][table.project(vector, block)] for index, block in enumerate(part)]
            rank[state] = sum(int(factors[index]["rank"][local]) for index, local in enumerate(locals_at_state))
            if state not in table.goal and not any((state, action) in table.post for action in uncontrollable):
                for index, local in enumerate(locals_at_state):
                    if local not in set(factors[index]["goal_states"]):
                        action = factors[index]["policy"].get(local)
                        require(isinstance(action, str), f"independent priority action missing at {state}")
                        policy[state] = action
                        break
        for goal in sorted(table.goal):
            vector = table.states[goal]
            wanted: list[tuple[Any, ...]] = []
            for index, block in enumerate(part):
                local_goal = state_maps[index][table.project(vector, block)]
                local_load = factors[index]["kappa"][local_goal]
                wanted.append(next(value for value, identifier in load_maps[index].items() if identifier == local_load))
            candidates = [
                load for load, load_vector in table.loads.items()
                if all(table.project(load_vector, block) == wanted[index] for index, block in enumerate(part))
            ]
            require(len(candidates) == 1 and (goal, candidates[0]) in table.handover, "independent global kappa differs")
            kappa[goal] = candidates[0]
        for state, action in policy.items():
            require((state, action) in table.post and all(target in factored_win and rank[target] < rank[state] for target in table.post[(state, action)]), "independent policy is not decreasing")
        for state in factored_win - table.goal:
            for action in uncontrollable:
                if (state, action) in table.post:
                    require(all(target in factored_win and rank[target] < rank[state] for target in table.post[(state, action)]), "independent UC step is not decreasing")
        global_record.update({
            "priority": [factor["id"] for factor in factors],
            "rank_operator": "sum",
            "kappa_operator": "cartesian_product",
            "global_rank": rank,
            "global_policy": policy,
            "global_kappa": kappa,
        })
    else:
        losing_index = next(index for index, factor in enumerate(factors) if not factor["all_initials_winning"])
        losing = set(factors[losing_index]["losing_region"])
        block = part[losing_index]
        cylinder = {
            state for state, vector in table.states.items()
            if state_maps[losing_index][table.project(vector, block)] in losing
        }
        require(bool(cylinder & table.initial) and not (cylinder & table.goal), "independent cylinder boundary differs")
        global_record.update({
            "losing_block_id": factors[losing_index]["id"],
            "losing_cylinder": sorted(cylinder),
            "losing_roots": sorted(cylinder & table.initial),
        })
    return {
        "schema_version": SCHEMA,
        "input_game_sha256": digest_json(game_raw),
        "partition_certificate_sha256": digest_json(partition_certificate),
        "game_id": game_raw.get("id"),
        "selected_partition": [list(block) for block in part],
        "local_factors": factors,
        "global_witness": global_record,
    }


def check(
    game_raw: Mapping[str, Any],
    partition_certificate: Mapping[str, Any],
    witness: Mapping[str, Any],
) -> dict[str, Any]:
    expected = expected_witness(game_raw, partition_certificate)
    require(
        canonical_json(witness) == canonical_json(expected),
        "transport witness differs from independent recomputation",
    )
    global_record = expected["global_witness"]
    return {
        "status": "PASS",
        "game_id": expected["game_id"],
        "decision": global_record["decision"],
        "local_factor_count": len(expected["local_factors"]),
        "semantic_flat_state_count": global_record["semantic_flat_state_count"],
        "factored_local_state_count": global_record["factored_local_state_count"],
        "direct_flat_decision_agrees": True,
    }


def read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"JSON root differs: {path}")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("game", type=Path)
    parser.add_argument("partition_certificate", type=Path)
    parser.add_argument("witness", type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(check(read(args.game), read(args.partition_certificate), read(args.witness)), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
