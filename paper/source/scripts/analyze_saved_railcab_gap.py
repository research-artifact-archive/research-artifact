#!/usr/bin/env python3
"""Read-only gap analysis of two saved qualitative RailCab policy exports.

No solver, successor oracle, model compilation or experiment is called. The
analysis follows every saved strategy outcome from every q0 entry to a goal.
It concerns the selected exported policies, not all policies of the contracts.
It does not infer enabled unselected events, suppression, optimality or time.

For each complete path, L is the last old-stop event and F the first new-start
event. The principal gap counts events strictly between L and F, excluding
both boundary events, and is reported only when L precedes F. Ordinary events
are labels outside the complete pending command set at the old entries. The
additional boundary distance counts edges after L up to and including F.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from functools import lru_cache
import json
from pathlib import Path


SCHEMA = "fse2027-atomic-handoff-bundle-v1"
BUNDLES = {
    "RailCab/Base": "results/supplement-checks/railcab_policy_demo/handoff-bundle.json",
    "RailCab/R1": "results/supplement-checks/railcab_r1_policy_demo/handoff-bundle.json",
}
BEFORE = "all_old_stops_before_first_new_start"
AFTER = "first_new_start_before_all_old_stops"
SAME = "same_boundary_event"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def extent(values):
    return {"min": min(values), "max": max(values)} if values else None


def analyze(bundle, metadata):
    require(bundle["schema_version"] == SCHEMA, "Unsupported saved bundle schema")
    require(metadata["status"] == "completed" and
            metadata["semantic_and_solver_properties_equal_to_source"] is True,
            "Saved qualitative export does not have its expected provenance")
    states = {s["id"]: s for s in bundle["configurations"]}
    require(len(states) == len(bundle["configurations"]) == bundle["certificate_state_count"],
            "Duplicate states or inconsistent certificate state count")
    roots = bundle["q0_entries"]
    require(len({r["old_state_id"] for r in roots}) == len(roots), "Duplicate old entry ID")
    root_ids = {r["root_configuration"] for r in roots}
    require(root_ids == {s["id"] for s in states.values() if s["initial"]} and
            len(root_ids) == bundle["initial_configuration_count"], "Incomplete entry coverage")
    pending = {q: set(s["pending_update_actions"]) for q, s in states.items()}
    command_sets = {frozenset(pending[q]) for q in root_ids}
    require(len(command_sets) == 1, "Entry command sets differ")
    commands = set(next(iter(command_sets)))
    stops = {a for a in commands if a.startswith("stopOldSpec_")}
    starts = {a for a in commands if a.startswith("startNewSpec_")}
    transfers = {a for a in commands if a.startswith("reconfigure_")}
    require(stops and starts and commands == stops | starts | transfers,
            "Unknown command class or absent lifetime boundary")
    require(all(type(s["rank"]) is int and s["rank"] >= 0 for s in states.values()),
            "Invalid saved rank")
    for q, s in states.items():
        monitors = s["active_monitor_states"]
        active_stops = {"stopOldSpec_" + k.split(":")[1]
                        for k in monitors if k.startswith("old:")}
        active_starts = {"startNewSpec_" + k.split(":")[1]
                         for k in monitors if k.startswith("new:")}
        require(active_stops == pending[q] & stops and
                active_starts == starts - pending[q],
                "Saved active monitor membership disagrees with pending boundaries at " + q)
        require(not s["goal"] or not pending[q], "Goal still has a pending command")

    edges = defaultdict(list)
    buckets = set()
    for b in bundle["strategy"]:
        source, action = b["source"], b["action"]
        require(source in states and not states[source]["goal"], "Unknown or terminal source")
        require((source, action) not in buckets, "Duplicate strategy bucket")
        buckets.add((source, action))
        require(bool(b["outcomes"]), "Empty saved strategy bucket")
        require(len({o["target"] for o in b["outcomes"]}) == len(b["outcomes"]),
                "Repeated outcome in a set-valued bucket")
        for outcome in b["outcomes"]:
            target = outcome["target"]
            require(target in states and states[source]["rank"] > states[target]["rank"],
                    "Missing successor or nondecreasing rank")
            require(outcome["goal"] == states[target]["goal"], "Inconsistent outcome goal flag")
            if action in commands:
                require(action in pending[source] and pending[target] == pending[source] - {action},
                        "Command does not consume exactly its pending action")
            else:
                require(not action.startswith(("stopOldSpec_", "startNewSpec_", "reconfigure_")) and
                        pending[target] == pending[source], "Ordinary event changes commands")
            edges[source].append((action, target))
    require(len(buckets) == bundle["strategy_bucket_count"] and
            sum(map(len, edges.values())) == bundle["strategy_outcome_edge_count"],
            "Saved strategy counts do not match the complete edge list")
    require(all(s["goal"] or edges[q] for q, s in states.items()), "Non-goal dead end")
    require(sum(s["goal"] for s in states.values()) == bundle["goal_count"], "Goal count differs")

    @lru_cache(None)
    def path_count(q):
        return 1 if states[q]["goal"] else sum(path_count(t) for _, t in edges[q])

    visited = set()

    def paths(q, labels=(), vertices=()):
        visited.add(q)
        vertices += (q,)
        if states[q]["goal"]:
            yield labels, vertices
        else:
            for action, target in edges[q]:
                yield from paths(target, labels + (action,), vertices)

    per_entry, all_records = [], []
    for entry in roots:
        records = []
        for labels, vertices in paths(entry["root_configuration"]):
            selected_commands = [a for a in labels if a in commands]
            require(Counter(selected_commands) == Counter(commands),
                    "Complete path does not execute every command exactly once")
            last_stop = max(i for i, action in enumerate(labels) if action in stops)
            first_start = min(i for i, action in enumerate(labels) if action in starts)
            order = BEFORE if last_stop < first_start else AFTER if first_start < last_stop else SAME
            gap = labels[last_stop + 1:first_start] if order == BEFORE else None
            record = {"entry": entry["old_state_id"], "order": order,
                      "last_stop_position_1based": last_stop + 1,
                      "first_start_position_1based": first_start + 1,
                      "gap_all_labels": len(gap) if gap is not None else None,
                      "gap_ordinary_labels": sum(a not in commands for a in gap) if gap is not None else None,
                      "boundary_distance_including_first_start": first_start - last_stop if order == BEFORE else None,
                      "gap_labels": list(gap) if gap is not None else None,
                      "gap_vertex_ids": list(vertices[last_stop + 1:first_start + 1]) if gap is not None else None}
            records.append(record)
        require(len(records) == path_count(entry["root_configuration"]), "Incomplete path traversal")
        order_counts = Counter(r["order"] for r in records)
        before = [r for r in records if r["order"] == BEFORE]
        per_entry.append({"old_entry": entry["old_state_id"],
                          "root_configuration": entry["root_configuration"],
                          "complete_saved_outcome_paths": len(records),
                          "order_path_counts": {k: order_counts[k] for k in (BEFORE, AFTER, SAME)},
                          "entry_class": next(iter(order_counts)) if len(order_counts) == 1 else "mixed_order",
                          "strict_gap_all_labels": extent([r["gap_all_labels"] for r in before]),
                          "strict_gap_ordinary_labels": extent([r["gap_ordinary_labels"] for r in before])})
        all_records.extend(records)
    require(visited == set(states), "Saved certificate contains states outside the analyzed entry closure")
    before = [r for r in all_records if r["order"] == BEFORE]
    classes = Counter(e["entry_class"] for e in per_entry)
    order_counts = Counter(r["order"] for r in all_records)
    witnesses = {}
    for metric in ("gap_all_labels", "gap_ordinary_labels"):
        if before:
            witnesses[metric] = {"minimum": min(before, key=lambda r: r[metric]),
                                 "maximum": max(before, key=lambda r: r[metric])}
    return {"schema": SCHEMA, "source_campaign_meta": metadata["source_meta"],
            "saved_export_purpose": metadata["purpose"],
            "entry_count": len(roots), "certificate_states": len(states),
            "strategy_buckets": len(buckets), "strategy_outcome_edges": sum(map(len, edges.values())),
            "command_counts": {"old_stops": len(stops), "new_starts": len(starts), "transfers": len(transfers)},
            "complete_paths_with_entry_multiplicity": len(all_records),
            "order_path_counts": {k: order_counts[k] for k in (BEFORE, AFTER, SAME)},
            "entry_class_counts": {k: classes[k] for k in (BEFORE, AFTER, SAME, "mixed_order")},
            "strict_gap_all_labels": extent([r["gap_all_labels"] for r in before]),
            "strict_gap_ordinary_labels": extent([r["gap_ordinary_labels"] for r in before]),
            "boundary_distance_including_first_start": extent([r["boundary_distance_including_first_start"] for r in before]),
            "per_entry": per_entry, "extreme_saved_path_segments": witnesses}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-root", type=Path, required=True)
    args = parser.parse_args()
    output = {"analysis": "complete traversal of saved selected-policy DAGs only",
              "definition": "Gap labels lie strictly after the last old-stop edge and before the first new-start edge; both boundaries excluded. Ordinary labels are outside the root pending command set.",
              "order_definition": "Boundary order is the event position along each complete path, not a comparison of ranks across different paths. A tie would require the same edge to be both boundaries.",
              "scope": "Separate qualitative exports; not timing samples, all 25 benchmark policies, optimal policies, enabled-unselected-event or suppression measurements.",
              "new_solver_or_experiment_executed": False, "results": {}}
    for name, relative in BUNDLES.items():
        path = args.artifact_root / relative
        result = analyze(json.loads(path.read_text()), json.loads(path.with_name("meta.json").read_text()))
        result["input_bundle"] = relative
        output["results"][name] = result
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
