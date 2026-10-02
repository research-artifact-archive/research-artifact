#!/usr/bin/env python3
"""Read the saved PC2 certificate; no model, compiler, or solver is invoked."""
import argparse
import json
from collections import defaultdict, deque
from pathlib import Path

SOURCE = Path("results/granularity/e6/pc2_rolling/v2/validation/export/lazy_none/certificate.json")
START = "startNewSpec_P_NEW_OUT_IF_FINISHED_1"
MONITOR = "new:P_NEW_OUT_IF_FINISHED_1:7"
EXPECTED_SUFFIX = [
    [12, "startNewSpec_P_NEW_OUT_IF_FINISHED_2", 11],
    [11, "startNewSpec_P_NEW_TOOL_ORDER_1", 10],
    [10, "startNewSpec_P_NEW_TOOL_ORDER_2", 9],
    [9, "startNewSpec_P_PAINT_ONCE_1", 8],
    [8, "startNewSpec_P_PAINT_ONCE_2", 7],
]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def analyze(data):
    states = {state["id"]: state for state in data["states"]}
    edges = [tuple(edge) for edge in data["strategy_edges"]]
    require(len(states) == len(data["states"]), "Duplicate state identifiers")
    require(len(edges) == len(set(edges)), "Duplicate policy edges")
    require(data["decision"] == "WIN", "The saved result is not WIN")
    entries = {q for q, state in states.items() if state["initial"]}
    goals = {q for q, state in states.items() if state["goal"]}
    require((len(states), len(edges), len(entries)) == (381, 522, 126), "Unexpected saved population")
    require(goals == {7}, "Unexpected goal set")
    adjacency = defaultdict(list)
    for source, event, target in edges:
        require(source in states and target in states, "Edge leaves the saved state domain")
        require(source not in goals, "A goal has an outgoing policy edge")
        require(states[source]["rank"] > states[target]["rank"], "Nondecreasing rank")
        adjacency[source].append((event, target))
    for q, state in states.items():
        require(state["safe"] is True, "Unsafe state in the saved policy")
        require(type(state["rank"]) is int and state["rank"] >= 0, "Invalid natural rank")
        require(q in goals or bool(adjacency[q]), "Non-goal deadlock")
        require(q not in goals or state["rank"] == 0, "Nonzero goal rank")

    def reach(roots, omit=None):
        seen = set(roots)
        queue = deque(roots)
        while queue:
            source = queue.popleft()
            for event, target in adjacency[source]:
                if (source, event, target) == omit:
                    continue
                if target not in seen:
                    seen.add(target)
                    queue.append(target)
        return seen

    require(reach(entries) == set(states), "Saved domain differs from entry-reachable closure")
    start_edges = [edge for edge in edges if edge[1] == START]
    require(start_edges == [(13, START, 12)], "Unexpected selected start edges")
    start_edge = start_edges[0]
    without_start = reach(entries, omit=start_edge)
    require(not (without_start & goals), "A goal is reachable without the selected start")
    entry_reaches_start = {q: 12 in reach([q]) for q in sorted(entries)}
    require(all(entry_reaches_start.values()), "An entry cannot reach the selected start successor")

    suffix_states = reach([12])
    suffix_edges = [list(edge) for edge in edges if edge[0] in suffix_states]
    require(suffix_states == {7, 8, 9, 10, 11, 12}, "Unexpected suffix state set")
    require(sorted(suffix_edges) == sorted(EXPECTED_SUFFIX), "Unexpected suffix edges")
    for q in suffix_states:
        state = states[q]
        require(state["physical"] == [["NEW", 1, [0] * 24], ["NEW", 1, []]], "Suffix component or observer values changed")
        require(state["testers"][MONITOR] == 0, "Selected monitor does not remain in state zero")
        require(state["rank"] == q - 7, "Unexpected suffix rank")
    require(data["goal_matches"].get("7") == "new-00000009", "Unexpected handover target")

    return {
        "purpose": "Static analysis of one existing saved certificate; no synthesis, compilation, experiment, or changed input.",
        "source_certificate": SOURCE.as_posix(),
        "scope": "PC2-Rolling, P_NEW_OUT_IF_FINISHED_1, the unique reached activation tuple; no ACT claim for all 138 NEW occurrences.",
        "saved_population": {"states": len(states), "edges": len(edges), "entries": len(entries), "goals": sorted(goals)},
        "structural_checks": {
            "entry_reachable_domain_exact": True,
            "every_edge_stays_in_domain": True,
            "all_states_recorded_safe": True,
            "every_non_goal_has_successor": True,
            "all_ranks_natural": True,
            "every_edge_strictly_decreases_rank": True,
            "goals_terminal_and_rank_zero": True,
        },
        "selected_start": list(start_edge),
        "start_dominates_completion": {
            "every_entry_can_reach_start_successor": True,
            "per_entry_reaches_start_successor": entry_reaches_start,
            "entry_union_reachable_without_start_states": len(without_start),
            "goals_reachable_without_start": sorted(without_start & goals),
            "all_maximal_saved_policy_runs_cross_start": True,
            "proof": "Domain closure, a natural rank decreasing on every edge, and absence of non-goal deadlocks force every maximal saved policy run to a goal. Removing the selected start makes all goals unreachable from every entry, so every such run crosses it. This statement is about the saved policy graph; complete modeled-outcome coverage relies on the stored certificate check.",
        },
        "suffix": {
            "states": sorted(suffix_states),
            "edges_in_execution_order": EXPECTED_SUFFIX,
            "ordinary_events": [],
            "transfer_events": [],
            "all_edges_new_requirement_starts": True,
            "all_24_ordinary_observers_zero": True,
            "component_version_and_raw_state": [["NEW", 1], ["NEW", 1]],
            "selected_monitor_state": 0,
            "ranks_in_execution_order": [5, 4, 3, 2, 1, 0],
            "goal": 7,
            "handover_target": "new-00000009",
        },
        "stored_checks": {key: data[key] for key in ["certificate_checker", "link_checker"]},
        "interpretation": "At the selected start all relevant ordinary observer bits are zero. The five subsequent start commands preserve those values and contain no out event. Thus the selected source invariant holds on this active update suffix. The stored goal match and the assumed verified fixed new endpoint supply the post-handover part; this script does not independently verify endpoint semantics or runtime conformance.",
        "not_checked": ["Completeness of exported modeled outcomes", "Correctness of the frontend or compiler", "The full Rolling monitor DFA or activation lookup table", "Other requirements or activation tuples", "Runtime conformance", "Safety of pre-activation histories under history-inclusive interpretation H"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=next((p for p in Path(__file__).resolve().parents if (p / SOURCE).is_file()), Path.cwd()))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = analyze(json.loads((args.repository / SOURCE).read_text(encoding="utf-8")))
    text = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
