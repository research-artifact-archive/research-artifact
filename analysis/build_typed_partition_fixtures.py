#!/usr/bin/env python3
"""Build unpartitioned typed flat fixtures for partition discovery evaluation.

The builder consumes the two already-public explicit local games and adds a
third non-isomorphic multi-root game.  It enumerates the semantic product and
then discards the block boundary: the resulting files contain only typed atoms
and a complete flat table.  Obstruction cases are controlled edits of those
tables and are marked as author-created post-outcome tests.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import itertools
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


GAME_SCHEMA = "fg-ducs-typed-flat-game-v1"
SEMANTICS = "complete-explicit-post-including-goal-and-unsafe-v1"
COMPOSITION = {
    "state_space": "cartesian_product",
    "initial_states": "cartesian_product",
    "safe": "conjunction",
    "goal": "cartesian_product",
    "load_states": "cartesian_product",
    "handover": "cartesian_product",
    "post": "exact_asynchronous_one_block_frame",
    "foreign_monitor_actions": "stutter",
    "foreign_rs_actions": "stutter",
    "pending_and_precedence": "block_local",
    "shared_action_post": "global_self_loop",
}


class FixtureError(RuntimeError):
    pass


def need(condition: bool, message: str) -> None:
    if not condition:
        raise FixtureError(message)


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def third_multiroot_case() -> dict[str, Any]:
    def automaton(states: list[str], initials: list[str], transitions: list[tuple[str, str, str]]) -> dict[str, Any]:
        return {
            "states": states,
            "initial_states": initials,
            "error_states": [],
            "default": "stutter",
            "transitions": [
                {"source": source, "action": action, "target": target}
                for source, action, target in transitions
            ],
        }

    route = {
        "id": "route",
        "states": ["ra", "rb", "rm", "rg"],
        "state_annotations": {
            "ra": {"physical": "old-a", "physical_safe": True, "monitor": "r0", "rs_residual": "s0", "pending_actions": ["migrate"]},
            "rb": {"physical": "old-b", "physical_safe": True, "monitor": "r0", "rs_residual": "s0", "pending_actions": ["migrate"]},
            "rm": {"physical": "new-wait", "physical_safe": True, "monitor": "r1", "rs_residual": "s1", "pending_actions": []},
            "rg": {"physical": "new-ready", "physical_safe": True, "monitor": "r2", "rs_residual": "s2", "pending_actions": []},
        },
        "initial_states": ["ra", "rb"],
        "safe_states": ["ra", "rb", "rm", "rg"],
        "goal_states": ["rg"],
        "load_states": ["image-route"],
        "action_annotations": {
            "migrate": {"controllability": "controllable", "kind": "transfer"},
            "routeAck": {"controllability": "uncontrollable", "kind": "internal"},
        },
        "transitions": [
            {"source": "ra", "action": "migrate", "targets": ["rm"]},
            {"source": "rb", "action": "migrate", "targets": ["rm"]},
            {"source": "rm", "action": "routeAck", "targets": ["rg"]},
        ],
        "monitor": automaton(["r0", "r1", "r2"], ["r0"], [("r0", "migrate", "r1"), ("r1", "routeAck", "r2")]),
        "rs_observer": automaton(["s0", "s1", "s2"], ["s0"], [("s0", "migrate", "s1"), ("s1", "routeAck", "s2")]),
        "precedence_edges": [],
        "handover_relation": {"rg": ["image-route"]},
        "foreign_actions_stutter": True,
    }
    cache = {
        "id": "cache",
        "states": ["ca", "cb", "cg"],
        "state_annotations": {
            "ca": {"physical": "cold-a", "physical_safe": True, "monitor": "c0", "rs_residual": "u0", "pending_actions": ["warm"]},
            "cb": {"physical": "cold-b", "physical_safe": True, "monitor": "c0", "rs_residual": "u0", "pending_actions": ["warm"]},
            "cg": {"physical": "warm", "physical_safe": True, "monitor": "c1", "rs_residual": "u1", "pending_actions": []},
        },
        "initial_states": ["ca", "cb"],
        "safe_states": ["ca", "cb", "cg"],
        "goal_states": ["cg"],
        "load_states": ["image-cache"],
        "action_annotations": {"warm": {"controllability": "controllable", "kind": "handover"}},
        "transitions": [
            {"source": "ca", "action": "warm", "targets": ["cg"]},
            {"source": "cb", "action": "warm", "targets": ["cg"]},
        ],
        "monitor": automaton(["c0", "c1"], ["c0"], [("c0", "warm", "c1")]),
        "rs_observer": automaton(["u0", "u1"], ["u0"], [("u0", "warm", "u1")]),
        "precedence_edges": [],
        "handover_relation": {"cg": ["image-cache"]},
        "foreign_actions_stutter": True,
    }
    return {
        "id": "multiroot-uncontrollable-progress",
        "expected_decision": "realizable",
        "shared_controllable_pure_stutter": ["idle"],
        "cross_block_precedence": [],
        "cross_block_requirements": [],
        "composition": COMPOSITION,
        "blocks": [route, cache],
    }


def block_atoms(block: Mapping[str, Any]) -> list[dict[str, str]]:
    identifier = str(block["id"])
    result = [
        {"id": f"component:{identifier}", "kind": "component"},
        {"id": f"monitor:{identifier}", "kind": "monitor"},
        {"id": f"rs:{identifier}", "kind": "rs"},
        {"id": f"load:{identifier}", "kind": "load"},
    ]
    for action, record in sorted(block["action_annotations"].items()):
        if record["kind"] != "internal":
            result.append({"id": f"pending:{action}", "kind": "pending"})
    return result


def state_valuation(block: Mapping[str, Any], state: str, *, load_value: str | None = None) -> dict[str, Any]:
    identifier = str(block["id"])
    annotation = block["state_annotations"][state]
    result: dict[str, Any] = {
        f"component:{identifier}": annotation["physical"],
        f"monitor:{identifier}": annotation["monitor"],
        f"rs:{identifier}": annotation["rs_residual"],
        f"load:{identifier}": load_value if load_value is not None else "<not-loaded>",
    }
    pending = set(annotation["pending_actions"])
    for action, record in sorted(block["action_annotations"].items()):
        if record["kind"] != "internal":
            result[f"pending:{action}"] = action in pending
    return result


def enumerate_flat(case: Mapping[str, Any], source_path: str, source_sha: str) -> dict[str, Any]:
    blocks = list(case["blocks"])
    atoms = sorted((atom for block in blocks for atom in block_atoms(block)), key=lambda x: x["id"])
    state_tuples = list(itertools.product(*(block["states"] for block in blocks)))
    identifiers = {values: f"Q{index}" for index, values in enumerate(state_tuples)}
    records: list[dict[str, Any]] = []
    for values in state_tuples:
        valuation: dict[str, Any] = {}
        for block, state in zip(blocks, values):
            valuation.update(state_valuation(block, state))
        records.append({
            "id": identifiers[values],
            "valuation": valuation,
            "initial": all(state in block["initial_states"] for block, state in zip(blocks, values)),
            "safe": all(state in block["safe_states"] for block, state in zip(blocks, values)),
            "goal": all(state in block["goal_states"] for block, state in zip(blocks, values)),
        })

    actions: list[dict[str, Any]] = []
    action_owner: dict[str, int] = {}
    for index, block in enumerate(blocks):
        identifier = str(block["id"])
        for action, annotation in sorted(block["action_annotations"].items()):
            need(action not in action_owner, f"local action is shared: {action}")
            action_owner[action] = index
            update = annotation["kind"] != "internal"
            # ``subjects`` identifies the action's direct contract subject,
            # not every observer coordinate that reacts to the event.  In
            # particular, pre-grouping monitor/RS here would disclose the
            # hidden block boundary to the discovery procedure.  Their block
            # membership must instead be forced by the complete Post/context
            # and foreign-stutter checks.
            subjects = [f"component:{identifier}"]
            pending_atom = None
            if update:
                pending_atom = f"pending:{action}"
                subjects.append(pending_atom)
            actions.append({
                "id": action,
                "controllability": annotation["controllability"],
                "kind": "update" if update else "normal",
                "subjects": subjects,
                "pending_atom": pending_atom,
            })
    for action in sorted(case.get("shared_controllable_pure_stutter", [])):
        need(action not in action_owner, f"shared action collides: {action}")
        actions.append({
            "id": action,
            "controllability": "controllable",
            "kind": "shared_stutter",
            "subjects": [],
            "pending_atom": None,
        })

    local_post: list[dict[tuple[str, str], list[str]]] = []
    for block in blocks:
        table: dict[tuple[str, str], list[str]] = {}
        for edge in block["transitions"]:
            table[(edge["source"], edge["action"])] = list(edge["targets"])
        local_post.append(table)
    buckets: list[dict[str, Any]] = []
    for values in state_tuples:
        source = identifiers[values]
        for action, owner in sorted(action_owner.items()):
            local_targets = local_post[owner].get((values[owner], action), [])
            if local_targets:
                targets = []
                for target in local_targets:
                    changed = list(values)
                    changed[owner] = target
                    targets.append(identifiers[tuple(changed)])
                buckets.append({"source": source, "action": action, "targets": targets})
        for action in sorted(case.get("shared_controllable_pure_stutter", [])):
            buckets.append({"source": source, "action": action, "targets": [source]})

    load_combinations = list(itertools.product(*(block["load_states"] for block in blocks)))
    load_ids = {values: f"Z{index}" for index, values in enumerate(load_combinations)}
    load_states: list[dict[str, Any]] = []
    for values in load_combinations:
        valuation: dict[str, Any] = {}
        for block, load_value in zip(blocks, values):
            goal = block["goal_states"][0]
            valuation.update(state_valuation(block, goal, load_value=load_value))
        load_states.append({"id": load_ids[values], "valuation": valuation})

    handover: list[dict[str, str]] = []
    for values in state_tuples:
        if not all(state in block["goal_states"] for block, state in zip(blocks, values)):
            continue
        local_load_domains = [block["handover_relation"][state] for block, state in zip(blocks, values)]
        for loads in itertools.product(*local_load_domains):
            handover.append({"goal": identifiers[values], "load": load_ids[loads]})

    dependencies: list[dict[str, Any]] = []
    for block in blocks:
        identifier = str(block["id"])
        # Only the component/load type correspondence is declared here.  The
        # monitor, RS and pending coordinates are not pre-grouped with their
        # component by this dependency.  Direct update subjects relate only
        # the executed component and its pending bit; Post context/frame checks
        # and precedence must force (or refute) the remaining groupings.
        dependencies.append({
            "kind": "handover",
            "atoms": [
                f"component:{identifier}", f"load:{identifier}",
            ],
            "detail": f"{identifier} and its load coordinate share a typed handover signature",
        })
        for before, after in block["precedence_edges"]:
            dependencies.append({
                "kind": "precedence",
                "atoms": [f"pending:{before}", f"pending:{after}"],
                "detail": f"{before} precedes {after}",
            })

    return {
        "schema_version": GAME_SCHEMA,
        "id": case["id"],
        "semantics": SEMANTICS,
        "atoms": atoms,
        "actions": sorted(actions, key=lambda x: x["id"]),
        "states": records,
        "buckets": sorted(buckets, key=lambda x: (x["source"], x["action"])),
        "load_states": load_states,
        "handover_relation": handover,
        "dependencies": dependencies,
        "provenance": {
            "classification": "post-outcome author fixture flattened from explicit typed local tables",
            "source_path": source_path,
            "source_sha256": source_sha,
            "expected_decision": case["expected_decision"],
        },
    }


def obstruction_cases(base: Mapping[str, Any], multiroot: Mapping[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []

    def mutate(identifier: str, kind: str, edit: Any) -> None:
        value = copy.deepcopy(base)
        value["id"] = identifier
        value["provenance"] = dict(value["provenance"])
        value["provenance"]["classification"] = "post-outcome author controlled obstruction"
        value["provenance"]["obstruction_kind"] = kind
        edit(value)
        result.append(value)

    def cross_precedence(value: dict[str, Any]) -> None:
        value["dependencies"].append({
            "kind": "precedence",
            "atoms": ["pending:prepare", "pending:arm"],
            "detail": "controlled cross-block precedence obstruction",
        })
    mutate("obstruction-cross-precedence", "CROSS_TYPED_DEPENDENCY", cross_precedence)

    def cross_subjects(value: dict[str, Any]) -> None:
        action = next(action for action in value["actions"] if action["id"] == "idle")
        action["kind"] = "normal"
        action["subjects"] = ["component:transfer", "component:guard"]
        for edge in value["buckets"]:
            if edge["action"] != "idle":
                continue
            source = next(state for state in value["states"] if state["id"] == edge["source"])
            target = next((
                state["id"] for state in value["states"]
                if state["id"] != edge["source"]
                and all(
                    state["valuation"][atom] == source["valuation"][atom]
                    for atom in source["valuation"]
                    if atom.startswith("pending:")
                )
            ), None)
            if target is not None:
                edge["targets"] = [target]
                return
        raise FixtureError("no pending-preserving shared nonstutter mutation target")
    mutate("obstruction-cross-subjects", "ACTION_SUBJECTS_CROSS_BLOCK", cross_subjects)

    def nonrectangular_goal(value: dict[str, Any]) -> None:
        goal = next(state for state in value["states"] if state["goal"])
        same_transfer = [
            state for state in value["states"]
            if state["valuation"]["component:transfer"] == goal["valuation"]["component:transfer"]
        ]
        extra = next(state for state in same_transfer if not state["goal"])
        extra["goal"] = True
        extra["safe"] = True
        for atom in ("pending:arm", "pending:commit", "pending:prepare"):
            extra["valuation"][atom] = False
        # Keep the full table well typed but deliberately select a non-product
        # Goal pair; handover remains total on the enlarged Goal.
        value["handover_relation"].append({"goal": extra["id"], "load": value["load_states"][0]["id"]})
    # This edit can violate pending semantics if the selected existing state had
    # updates left; the controlled fixture therefore uses a safer state-level
    # deletion below instead of being part of the released corpus.

    def state_nonrectangular(value: dict[str, Any]) -> None:
        removable = next(
            state for state in value["states"]
            if not state["initial"] and not state["goal"]
            and all(edge["source"] != state["id"] and state["id"] not in edge["targets"] for edge in value["buckets"])
        )
        value["states"].remove(removable)
    # The base product has no isolated state, so use a root-set obstruction.

    def root_nonrectangular(value: dict[str, Any]) -> None:
        initials = [state for state in value["states"] if state["initial"]]
        need(len(initials) == 1, "winning base must have one product root")
        root = initials[0]
        candidate = next(
            state for state in value["states"]
            if state["valuation"]["component:transfer"] == root["valuation"]["component:transfer"]
            and state["valuation"]["component:guard"] != root["valuation"]["component:guard"]
        )
        candidate["initial"] = True
        # Initial pending exactness is preserved by choosing another local root
        # only after converting its local annotations to the root values; the
        # absence of the opposite mixed root remains the intended obstruction.
        for atom, val in root["valuation"].items():
            if atom.startswith("pending:"):
                candidate["valuation"][atom] = val
    # Root edits above disturb injectivity/context and are better represented by
    # a fully defined manual case in the test suite, not the released fixtures.

    def action_context(value: dict[str, Any]) -> None:
        candidates = [edge for edge in value["buckets"] if edge["action"] == "prepare"]
        need(len(candidates) >= 2, "prepare needs multiple foreign contexts")
        value["buckets"].remove(candidates[-1])
    mutate("obstruction-foreign-enabledness", "ACTION_CONTEXT_DEPENDENCE", action_context)

    def action_outcome_context(value: dict[str, Any]) -> None:
        candidates = [edge for edge in value["buckets"] if edge["action"] == "prepare"]
        need(len(candidates) >= 2 and len(candidates[-1]["targets"]) == 2, "prepare needs two outcomes and foreign contexts")
        candidates[-1]["targets"] = candidates[-1]["targets"][:1]
    mutate("obstruction-foreign-outcome-set", "ACTION_CONTEXT_DEPENDENCE", action_outcome_context)

    def foreign_frame(value: dict[str, Any]) -> None:
        candidates = [edge for edge in value["buckets"] if edge["action"] == "ready"]
        for edge in candidates:
            source = next(state for state in value["states"] if state["id"] == edge["source"])
            original = next(state for state in value["states"] if state["id"] == edge["targets"][0])
            target = next((
                state for state in value["states"]
                if state["valuation"]["component:guard"] == original["valuation"]["component:guard"]
                and state["valuation"]["monitor:guard"] == original["valuation"]["monitor:guard"]
                and state["valuation"]["rs:guard"] == original["valuation"]["rs:guard"]
                and state["valuation"]["pending:arm"] == original["valuation"]["pending:arm"]
                and state["valuation"]["component:transfer"] != source["valuation"]["component:transfer"]
                and all(
                    state["valuation"][atom] == source["valuation"][atom]
                    for atom in source["valuation"]
                    if atom.startswith("pending:") and atom != "pending:arm"
                )
            ), None)
            if target is not None:
                edge["targets"] = [target["id"]]
                return
        raise FixtureError("no pending-preserving foreign-frame mutation target")
    mutate("obstruction-foreign-frame", "ACTION_FOREIGN_FRAME", foreign_frame)

    def safe_nonrectangular(value: dict[str, Any]) -> None:
        candidate = next(state for state in value["states"] if state["safe"] and not state["goal"] and not state["initial"])
        candidate["safe"] = False
    mutate("obstruction-safe-nonrectangular", "SAFE_NONRECTANGULAR", safe_nonrectangular)

    def state_nonrectangular_edit(value: dict[str, Any]) -> None:
        candidate = next(state for state in value["states"] if not state["goal"] and not state["initial"])
        identifier = candidate["id"]
        value["states"] = [state for state in value["states"] if state["id"] != identifier]
        value["buckets"] = [
            edge for edge in value["buckets"]
            if edge["source"] != identifier and identifier not in edge["targets"]
        ]
    mutate("obstruction-state-nonrectangular", "STATE_NONRECTANGULAR", state_nonrectangular_edit)

    def handover_nonrectangular(value: dict[str, Any]) -> None:
        original = copy.deepcopy(value["load_states"][0])
        variants = []
        for index, (transfer, guard) in enumerate((
            ("image-transfer", "image-guard"),
            ("image-transfer-alt", "image-guard"),
            ("image-transfer", "image-guard-alt"),
            ("image-transfer-alt", "image-guard-alt"),
        )):
            record = copy.deepcopy(original)
            record["id"] = f"Z{index}"
            record["valuation"]["load:transfer"] = transfer
            record["valuation"]["load:guard"] = guard
            variants.append(record)
        value["load_states"] = variants
        goal = next(state["id"] for state in value["states"] if state["goal"])
        value["handover_relation"] = [
            {"goal": goal, "load": f"Z{index}"} for index in range(3)
        ]
    mutate("obstruction-handover-nonrectangular", "HANDOVER_NONRECTANGULAR", handover_nonrectangular)

    def goal_uc(value: dict[str, Any]) -> None:
        goal = next(state for state in value["states"] if state["goal"])
        action = next(action for action in value["actions"] if action["id"] == "ready")
        owner_values = goal["valuation"]
        source = next(
            state for state in value["states"]
            if state["valuation"]["component:guard"] == owner_values["component:guard"]
            and state["valuation"]["monitor:guard"] == owner_values["monitor:guard"]
            and state["valuation"]["rs:guard"] == owner_values["rs:guard"]
            and state["valuation"]["pending:arm"] == owner_values["pending:arm"]
        )
        # Add the same local UC self-loop in every foreign context, preserving
        # action locality while violating local-Goal quiescence.
        guard_signature = (
            source["valuation"]["component:guard"],
            source["valuation"]["monitor:guard"],
            source["valuation"]["rs:guard"],
            source["valuation"]["pending:arm"],
        )
        for state in value["states"]:
            signature = (
                state["valuation"]["component:guard"],
                state["valuation"]["monitor:guard"],
                state["valuation"]["rs:guard"],
                state["valuation"]["pending:arm"],
            )
            if signature == guard_signature:
                value["buckets"].append({"source": state["id"], "action": action["id"], "targets": [state["id"]]})
        value["buckets"] = sorted(value["buckets"], key=lambda x: (x["source"], x["action"]))
    mutate("obstruction-goal-uc-activity", "GOAL_UNCONTROLLABLE_ACTIVITY", goal_uc)

    value = copy.deepcopy(multiroot)
    value["id"] = "obstruction-root-nonrectangular"
    value["provenance"] = dict(value["provenance"])
    value["provenance"]["classification"] = "post-outcome author controlled obstruction"
    value["provenance"]["obstruction_kind"] = "ROOT_NONRECTANGULAR"
    initials = [state for state in value["states"] if state["initial"]]
    need(len(initials) == 4, "multiroot positive must have a 2x2 Q0")
    initials[-1]["initial"] = False
    result.append(value)

    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    source = json.loads(args.source.read_text(encoding="utf-8"))
    need(isinstance(source, dict) and isinstance(source.get("cases"), list), "multistate source differs")
    source_sha = sha256_file(args.source)
    source_cases = list(source["cases"])
    flattened = [enumerate_flat(case, args.source.as_posix(), source_sha) for case in source_cases]
    builder_path = Path(__file__).resolve()
    flattened.append(enumerate_flat(
        third_multiroot_case(),
        "analysis/build_typed_partition_fixtures.py",
        sha256_file(builder_path),
    ))
    obstructed = obstruction_cases(flattened[0], flattened[2])
    corpus = {
        "schema_version": "fg-ducs-typed-partition-fixtures-v1",
        "source_sha256": source_sha,
        "positive_cases": flattened,
        "obstruction_cases": obstructed,
    }
    args.output.write_text(canonical(corpus), encoding="utf-8", newline="\n")
    print(f"wrote {len(flattened)} positive and {len(obstructed)} obstruction cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
