#!/usr/bin/env python3
"""Project a discovered typed partition and synthesize transport witnesses.

This producer consumes an unpartitioned complete flat table plus a checked
partition certificate.  It derives the local projected games, solves them,
and emits either a global rank-sum/policy/kappa witness or a losing cylinder.
The independent consumer is implemented in check_discovered_witness.py.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from math import prod
from pathlib import Path
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from discover_typed_partition import (  # noqa: E402
    TypedFlatGame,
    normalize_partition,
    sha256_json,
    verify_partition,
)


SCHEMA = "fg-ducs-discovered-witness-v1"


class WitnessError(RuntimeError):
    pass


def need(condition: bool, message: str) -> None:
    if not condition:
        raise WitnessError(message)


def canonical_sha(value: Any) -> str:
    payload = (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def value_key(value: tuple[Any, ...]) -> str:
    return json.dumps(list(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def solve_local(
    states: set[str],
    initials: set[str],
    safe: set[str],
    goals: set[str],
    actions: Mapping[str, str],
    post: Mapping[tuple[str, str], tuple[str, ...]],
    handover: set[tuple[str, str]],
) -> dict[str, Any]:
    controllable = {action for action, control in actions.items() if control == "controllable"}
    uncontrollable = set(actions) - controllable
    enabled_c: dict[str, list[str]] = defaultdict(list)
    enabled_uc: dict[str, list[str]] = defaultdict(list)
    for state, action in post:
        (enabled_c if action in controllable else enabled_uc)[state].append(action)

    winning = set(goals)
    rank = {state: 0 for state in goals}
    layer = 1
    while True:
        added: set[str] = set()
        for state in safe - winning:
            if enabled_uc[state]:
                admissible = all(
                    all(target in winning for target in post[(state, action)])
                    for action in enabled_uc[state]
                )
            else:
                admissible = any(
                    all(target in winning for target in post[(state, action)])
                    for action in enabled_c[state]
                )
            if admissible:
                added.add(state)
        if not added:
            break
        for state in added:
            rank[state] = layer
        winning |= added
        layer += 1

    policy: dict[str, str] = {}
    for state in sorted(winning - goals):
        if enabled_uc[state]:
            continue
        candidates = [
            action
            for action in sorted(enabled_c[state])
            if all(target in winning and rank[target] < rank[state] for target in post[(state, action)])
        ]
        need(bool(candidates), f"no decreasing local action at {state}")
        policy[state] = candidates[0]

    kappa: dict[str, str] = {}
    for goal in sorted(goals):
        candidates = sorted(load for source, load in handover if source == goal)
        need(bool(candidates), f"local handover is not total at {goal}")
        kappa[goal] = candidates[0]

    losing = states - winning
    counterstrategy: dict[str, Any] = {}
    for state in sorted(losing):
        if state not in safe:
            counterstrategy[state] = {"mode": "unsafe-terminal"}
        elif enabled_uc[state]:
            responses = sorted(
                (action, target)
                for action in enabled_uc[state]
                for target in post[(state, action)]
                if target in losing
            )
            need(bool(responses), f"no uncontrollable losing response at {state}")
            action, target = responses[0]
            counterstrategy[state] = {
                "mode": "uncontrollable",
                "action": action,
                "target": target,
            }
        else:
            responses: dict[str, str] = {}
            for action in sorted(enabled_c[state]):
                candidates = sorted(target for target in post[(state, action)] if target in losing)
                need(bool(candidates), f"no controlled losing outcome at {state}/{action}")
                responses[action] = candidates[0]
            counterstrategy[state] = {"mode": "controlled-outcomes", "responses": responses}
    return {
        "winning_region": sorted(winning),
        "rank": {state: rank[state] for state in sorted(winning)},
        "policy": policy,
        "kappa": kappa,
        "losing_region": sorted(losing),
        "losing_counterstrategy": counterstrategy,
        "all_initials_winning": initials <= winning,
    }


def build_factor(
    game: TypedFlatGame,
    block_index: int,
    block: tuple[str, ...],
    assignment: Mapping[str, str],
) -> dict[str, Any]:
    state_values = sorted(
        {game.projection(vector, block) for vector in game.state_values.values()},
        key=value_key,
    )
    state_id = {value: f"B{block_index}Q{index}" for index, value in enumerate(state_values)}
    load_values = sorted(
        {game.projection(vector, block) for vector in game.load_values.values()},
        key=value_key,
    )
    load_id = {value: f"B{block_index}Z{index}" for index, value in enumerate(load_values)}
    initials = {state_id[game.projection(game.state_values[state], block)] for state in game.initials}
    safe = {state_id[game.projection(game.state_values[state], block)] for state in game.safe}
    goals = {state_id[game.projection(game.state_values[state], block)] for state in game.goals}
    local_actions = {
        action: str(game.actions[action]["controllability"])
        for action, owner in assignment.items()
        if owner == ",".join(block)
    }

    representatives: dict[tuple[Any, ...], list[str]] = defaultdict(list)
    for state, vector in game.state_values.items():
        representatives[game.projection(vector, block)].append(state)
    local_post: dict[tuple[str, str], tuple[str, ...]] = {}
    for value in state_values:
        local_source = state_id[value]
        for action in sorted(local_actions):
            observed: set[tuple[str, ...]] = set()
            for source in representatives[value]:
                targets = game.post.get((source, action), frozenset())
                observed.add(tuple(sorted({
                    state_id[game.projection(game.state_values[target], block)]
                    for target in targets
                })))
            need(len(observed) == 1, f"action context differs after discovery: {action}/{local_source}")
            targets = next(iter(observed))
            if targets:
                local_post[(local_source, action)] = targets

    local_handover = {
        (
            state_id[game.projection(game.state_values[goal], block)],
            load_id[game.projection(game.load_values[load], block)],
        )
        for goal, load in game.handover
    }
    solved = solve_local(
        set(state_id.values()), initials, safe, goals, local_actions, local_post, local_handover
    )
    return {
        "id": f"B{block_index}",
        "atoms": list(block),
        "states": [
            {"id": state_id[value], "valuation": list(value)} for value in state_values
        ],
        "initial_states": sorted(initials),
        "safe_states": sorted(safe),
        "goal_states": sorted(goals),
        "load_states": [
            {"id": load_id[value], "valuation": list(value)} for value in load_values
        ],
        "actions": [
            {"id": action, "controllability": local_actions[action]}
            for action in sorted(local_actions)
        ],
        "buckets": [
            {"source": source, "action": action, "targets": list(targets)}
            for (source, action), targets in sorted(local_post.items())
        ],
        "handover_relation": [
            {"goal": goal, "load": load} for goal, load in sorted(local_handover)
        ],
        **solved,
    }


def direct_flat_winning(game: TypedFlatGame) -> set[str]:
    shared = {
        action for action, record in game.actions.items() if record["kind"] == "shared_stutter"
    }
    controllable = {
        action for action, record in game.actions.items()
        if record["controllability"] == "controllable" and action not in shared
    }
    uncontrollable = {
        action for action, record in game.actions.items()
        if record["controllability"] == "uncontrollable"
    }
    winning = set(game.goals)
    while True:
        added: set[str] = set()
        for state in game.safe - winning:
            enabled_uc = [action for action in uncontrollable if (state, action) in game.post]
            if enabled_uc:
                condition = all(game.post[(state, action)] <= winning for action in enabled_uc)
            else:
                condition = any(game.post[(state, action)] <= winning for action in controllable if (state, action) in game.post)
            if condition:
                added.add(state)
        if not added:
            return winning
        winning |= added


def synthesize(game_raw: Mapping[str, Any], partition_certificate: Mapping[str, Any]) -> dict[str, Any]:
    game = TypedFlatGame(game_raw)
    need(partition_certificate.get("input_game_sha256") == sha256_json(game_raw), "partition input binding differs")
    need(partition_certificate.get("game_id") == game.identifier, "partition game id differs")
    need(partition_certificate.get("result") == "FACTORED", "witness synthesis requires a nontrivial partition")
    partition = normalize_partition(partition_certificate.get("selected_partition", []))
    assignment, obstruction = verify_partition(game, partition)
    need(obstruction is None and assignment == partition_certificate.get("action_assignment"), "selected partition does not recheck")
    factors = [build_factor(game, index, block, assignment or {}) for index, block in enumerate(partition)]

    state_lookup = [
        {
            tuple(record["valuation"]): record["id"]
            for record in factor["states"]
        }
        for factor in factors
    ]
    load_lookup = [
        {
            tuple(record["valuation"]): record["id"]
            for record in factor["load_states"]
        }
        for factor in factors
    ]
    factored_winning = {
        state
        for state, vector in game.state_values.items()
        if all(
            state_lookup[index][game.projection(vector, block)] in set(factors[index]["winning_region"])
            for index, block in enumerate(partition)
        )
    }
    direct_winning = direct_flat_winning(game)
    need(factored_winning == direct_winning, "flat and factored winning regions differ")
    factored_decision = "realizable" if game.initials <= factored_winning else "unrealizable"

    global_witness: dict[str, Any] = {
        "decision": factored_decision,
        "semantic_flat_state_count": len(game.states),
        "factored_local_state_count": sum(len(factor["states"]) for factor in factors),
        "direct_flat_winning_region": sorted(direct_winning),
        "factored_winning_region": sorted(factored_winning),
        "direct_flat_decision_agrees": True,
    }
    if factored_decision == "realizable":
        rank: dict[str, int] = {}
        policy: dict[str, str] = {}
        kappa: dict[str, str] = {}
        priority = [factor["id"] for factor in factors]
        shared = {action for action, record in game.actions.items() if record["kind"] == "shared_stutter"}
        uncontrollable = {action for action, record in game.actions.items() if record["controllability"] == "uncontrollable"}
        for state in sorted(factored_winning):
            vector = game.state_values[state]
            local_states = [
                state_lookup[index][game.projection(vector, block)]
                for index, block in enumerate(partition)
            ]
            rank[state] = sum(int(factors[index]["rank"][local]) for index, local in enumerate(local_states))
            enabled_uc = [action for action in uncontrollable if (state, action) in game.post]
            if state not in game.goals and not enabled_uc:
                for index, local in enumerate(local_states):
                    if local not in set(factors[index]["goal_states"]):
                        action = factors[index]["policy"].get(local)
                        need(isinstance(action, str) and action not in shared, f"priority policy is undefined at {state}")
                        policy[state] = action
                        break
        for goal in sorted(game.goals):
            vector = game.state_values[goal]
            desired = []
            for index, block in enumerate(partition):
                local_goal = state_lookup[index][game.projection(vector, block)]
                local_load = factors[index]["kappa"][local_goal]
                desired.append(next(value for value, identifier in load_lookup[index].items() if identifier == local_load))
            matches = [
                load for load in game.loads
                if all(game.projection(game.load_values[load], block) == desired[index] for index, block in enumerate(partition))
            ]
            need(len(matches) == 1 and (goal, matches[0]) in game.handover, f"global kappa is not typed at {goal}")
            kappa[goal] = matches[0]
        for state, action in policy.items():
            need((state, action) in game.post, f"global policy action is disabled at {state}")
            need(all(target in factored_winning and rank[target] < rank[state] for target in game.post[(state, action)]), f"global policy does not decrease rank at {state}")
        for state in factored_winning - game.goals:
            for action in uncontrollable:
                if (state, action) in game.post:
                    need(all(target in factored_winning and rank[target] < rank[state] for target in game.post[(state, action)]), f"uncontrollable step does not decrease rank at {state}/{action}")
        global_witness.update({
            "priority": priority,
            "rank_operator": "sum",
            "kappa_operator": "cartesian_product",
            "global_rank": rank,
            "global_policy": policy,
            "global_kappa": kappa,
        })
    else:
        losing_index = next(
            index for index, factor in enumerate(factors) if not factor["all_initials_winning"]
        )
        losing = set(factors[losing_index]["losing_region"])
        block = partition[losing_index]
        cylinder = {
            state
            for state, vector in game.state_values.items()
            if state_lookup[losing_index][game.projection(vector, block)] in losing
        }
        need(bool(cylinder & game.initials) and not (cylinder & game.goals), "losing cylinder root/Goal boundary differs")
        global_witness.update({
            "losing_block_id": factors[losing_index]["id"],
            "losing_cylinder": sorted(cylinder),
            "losing_roots": sorted(cylinder & game.initials),
        })

    return {
        "schema_version": SCHEMA,
        "input_game_sha256": sha256_json(game_raw),
        "partition_certificate_sha256": canonical_sha(partition_certificate),
        "game_id": game.identifier,
        "selected_partition": [list(block) for block in partition],
        "local_factors": factors,
        "global_witness": global_witness,
    }


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    need(isinstance(value, dict), f"JSON root is not an object: {path}")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("game", type=Path)
    parser.add_argument("partition_certificate", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = synthesize(load(args.game), load(args.partition_certificate))
    payload = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8", newline="\n")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
