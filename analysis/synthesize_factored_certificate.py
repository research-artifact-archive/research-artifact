#!/usr/bin/env python3
"""Synthesize succinct certificates from explicit typed local FG-DUCS games.

This producer deliberately does not import the independent certificate
consumer.  The audit driver passes its output to check_factored_certificate.py,
which validates the typed tables and recomputes the result from scratch.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from math import prod
from typing import Any, Mapping


GAME_SCHEMA_VERSION = "fg-ducs-factored-game-v1"
CERTIFICATE_SCHEMA_VERSION = "fg-ducs-factored-certificate-v1"


class SynthesisError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SynthesisError(message)


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def solve_local(block: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    identifier = block.get("id")
    require(isinstance(identifier, str) and identifier, "block id is invalid")
    states_raw = block.get("states")
    require(isinstance(states_raw, list) and states_raw, f"{identifier}: states are invalid")
    states = set(states_raw)
    require(len(states) == len(states_raw) and all(isinstance(s, str) and s for s in states), f"{identifier}: states differ")
    initials = set(block.get("initial_states", []))
    safe = set(block.get("safe_states", []))
    goals = set(block.get("goal_states", []))
    require(initials and goals and initials <= states and goals <= safe <= states, f"{identifier}: state sets differ")

    annotations = block.get("action_annotations")
    require(isinstance(annotations, dict), f"{identifier}: action annotations are invalid")
    controllable = {a for a, record in annotations.items() if isinstance(record, dict) and record.get("controllability") == "controllable"}
    uncontrollable = {a for a, record in annotations.items() if isinstance(record, dict) and record.get("controllability") == "uncontrollable"}
    require(controllable | uncontrollable == set(annotations), f"{identifier}: action partition differs")

    post: dict[tuple[str, str], tuple[str, ...]] = {}
    for record in block.get("transitions", []):
        require(isinstance(record, dict), f"{identifier}: transition is invalid")
        source, action, targets = record.get("source"), record.get("action"), record.get("targets")
        require(source in states and action in annotations and isinstance(targets, list) and targets, f"{identifier}: transition typing differs")
        require(set(targets) <= states and len(targets) == len(set(targets)), f"{identifier}: transition targets differ")
        require((source, action) not in post, f"{identifier}: duplicate action bucket")
        post[(source, action)] = tuple(targets)

    enabled_c: dict[str, list[str]] = defaultdict(list)
    enabled_uc: dict[str, list[str]] = defaultdict(list)
    for state, action in post:
        (enabled_c if action in controllable else enabled_uc)[state].append(action)

    winning = set(goals)
    ranks = {state: 0 for state in goals}
    while True:
        added: set[str] = set()
        next_rank = max(ranks.values(), default=-1) + 1
        for state in safe - winning:
            if enabled_uc[state]:
                condition = all(all(target in winning for target in post[(state, action)]) for action in enabled_uc[state])
            else:
                condition = any(all(target in winning for target in post[(state, action)]) for action in enabled_c[state])
            if condition:
                added.add(state)
        if not added:
            break
        for state in added:
            ranks[state] = next_rank
        winning |= added

    policy: dict[str, str] = {}
    for state in sorted(winning - goals):
        if not enabled_uc[state]:
            candidates = [
                action
                for action in enabled_c[state]
                if all(target in winning and ranks[target] < ranks[state] for target in post[(state, action)])
            ]
            require(candidates, f"{identifier}: no rank-decreasing controlled action")
            policy[state] = min(candidates)

    relation = block.get("handover_relation")
    require(isinstance(relation, dict), f"{identifier}: handover relation is invalid")
    kappa: dict[str, str] = {}
    for goal in sorted(goals):
        candidates = relation.get(goal)
        require(isinstance(candidates, list) and candidates, f"{identifier}: no handover target for {goal}")
        kappa[goal] = min(candidates)

    losing = states - winning
    counterstrategy: dict[str, Any] = {}
    for state in sorted(losing):
        if state not in safe:
            counterstrategy[state] = {"mode": "unsafe-terminal"}
        elif enabled_uc[state]:
            choices = sorted(
                (action, target)
                for action in enabled_uc[state]
                for target in post[(state, action)]
                if target in losing
            )
            require(choices, f"{identifier}: no uncontrollable losing response")
            action, target = choices[0]
            counterstrategy[state] = {
                "mode": "uncontrollable",
                "action": action,
                "target": target,
            }
        else:
            responses: dict[str, str] = {}
            for action in sorted(enabled_c[state]):
                candidates = sorted(target for target in post[(state, action)] if target in losing)
                require(candidates, f"{identifier}: no losing response for {action}")
                responses[action] = candidates[0]
            counterstrategy[state] = {
                "mode": "controlled-outcomes",
                "responses": responses,
            }

    enriched = dict(block)
    enriched.update(
        {
            "rank": {state: ranks[state] for state in sorted(winning)},
            "policy": policy,
            "kappa": kappa,
            "losing_region": sorted(losing),
            "losing_counterstrategy": counterstrategy,
        }
    )
    result = {
        "id": identifier,
        "state_count": len(states),
        "bucket_count": len(post),
        "outcome_edge_count": sum(len(targets) for targets in post.values()),
        "all_initials_winning": initials <= winning,
        "maximum_initial_rank": max((ranks[state] for state in initials if state in ranks), default=0),
        "losing_region": sorted(losing),
    }
    return enriched, result


def synthesize(game: Mapping[str, Any]) -> dict[str, Any]:
    require(game.get("schema_version") == GAME_SCHEMA_VERSION, "unknown factored-game schema")
    blocks = game.get("blocks")
    require(isinstance(blocks, list) and blocks, "game has no blocks")
    enriched_blocks: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    for block in blocks:
        require(isinstance(block, dict), "block is invalid")
        enriched, result = solve_local(block)
        enriched_blocks.append(enriched)
        results.append(result)

    all_winning = all(result["all_initials_winning"] for result in results)
    counts = {
        "semantic_flat_state_count": prod(result["state_count"] for result in results),
        "factored_local_state_count": sum(result["state_count"] for result in results),
        "factored_bucket_count": sum(result["bucket_count"] for result in results),
        "factored_outcome_edge_count": sum(result["outcome_edge_count"] for result in results),
    }
    if all_winning:
        global_certificate = {
            "decision": "realizable",
            "priority": [result["id"] for result in results],
            "shared_stutter_enabled": False,
            "rank_operator": "sum",
            "kappa_operator": "cartesian_product",
            **counts,
            "maximum_initial_rank": sum(result["maximum_initial_rank"] for result in results),
        }
    else:
        losing = next(result for result in results if not result["all_initials_winning"])
        global_certificate = {
            "decision": "unrealizable",
            "losing_block_id": losing["id"],
            "cylinder_local_losing_region": losing["losing_region"],
            **counts,
        }

    certificate = {
        "schema_version": CERTIFICATE_SCHEMA_VERSION,
        "input_game_sha256": sha256_json(game),
        "id": game.get("id"),
        "source_model": game.get("source_model"),
        "shared_controllable_pure_stutter": game.get("shared_controllable_pure_stutter"),
        "cross_block_precedence": game.get("cross_block_precedence"),
        "cross_block_requirements": game.get("cross_block_requirements"),
        "composition": game.get("composition"),
        "blocks": enriched_blocks,
        "global_certificate": global_certificate,
    }
    return certificate
