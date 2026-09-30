#!/usr/bin/env python3
"""Independent tiny-input interpretation and comparison with saved Java output.

Reads only the restricted FSP grammar actually used by the three fixtures.
Constructs endpoint products, transfer reachability, and a least fixed point in
Python; it does not import the Java solver or derive expected decisions from it.
The Java game export stops expansion at goals, which this comparison preserves.
"""
import csv
import hashlib
import json
from collections import deque
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
CASES = ("all_targets", "reachable_transfer_target", "unreachable_load_target")


def parse(text):
    states = {}
    for name, body in re.findall(r"^([A-Z][A-Z0-9_]*) = \(([^\n]+)\)[.,]$", text, re.M):
        outgoing = {}
        for branch in body.split("|"):
            label, target = re.fullmatch(r"\s*([A-Za-z0-9_]+)\s*->\s*([A-Z][A-Z0-9_]*)\s*", branch).groups()
            outgoing.setdefault(label, set()).add(target)
        states[name] = outgoing
    assert states == {
        "O": {"idle": {"O"}},
        "N0": {"idle": {"N0"}, "move": {"N1"}},
        "N1": {"idle": {"N1"}},
        "OLD_C": {"idle": {"OLD_C"}},
        "C0": {"idle": {"C0"}, "move": {"C1"}},
        "C1": {"idle": {"C1"}},
    }
    assert re.search(r"TEST_OLD = O,", text) and re.search(r"TEST_NEW = N0,", text)
    assert re.search(r"NEW_C = C0,", text)
    assert re.search(r"O@TEST_OLD = reconfigure_TEST -> N1@TEST_NEW", text)
    assert "safety =" not in text and "transition =" not in text and "precedence =" not in text
    selector = tuple(int(x.strip()) for x in re.search(r"loadable_new_states = \{([^}]+)\}", text).group(1).split(","))
    return states, selector


def endpoint(states, initial):
    """Reachable synchronized environment/controller product in sorted-label BFS."""
    reached, queue, edges = [initial], deque([initial]), {}
    while queue:
        source = queue.popleft()
        outgoing = {}
        env, ctrl = source
        for action in sorted(set(states[env]) & set(states[ctrl])):
            targets = {(e, c) for e in states[env][action] for c in states[ctrl][action]}
            outgoing[action] = targets
            for target in sorted(targets):
                if target not in reached:
                    reached.append(target)
                    queue.append(target)
        edges[source] = outgoing
    return reached, edges


def attractor(states, edges, goals):
    winning = set(goals)
    rank = {s: 0 for s in goals}
    while True:
        added = {s for s in states if s not in winning and any(
            targets and targets <= winning for targets in edges[s].values())}
        if not added:
            return winning, rank
        for s in added:
            rank[s] = 1 + min(max(rank[t] for t in targets) for targets in edges[s].values()
                              if targets and targets <= winning)
        winning |= added


def main():
    rows, details, normalized = [], {}, []
    for case in CASES:
        folder = HERE / case
        text = (folder / "model.lts").read_text()
        normalized.append(re.sub(r"loadable_new_states = \{[^}]+\}", "loadable_new_states = {S}", text))
        fsp, selected = parse(text)
        old_states, old_edges = endpoint(fsp, ("O", "OLD_C"))
        new_states, new_edges = endpoint(fsp, ("N0", "C0"))
        assert old_states == [("O", "OLD_C")]
        assert new_states == [("N0", "C0"), ("N1", "C1")]
        domain = {new_states[i][0] for i in selected}
        # Update states retain the environment tuple, pending transfer, and empty
        # monitor map. Endpoint controller states are used only before/after update.
        edges = {"O": {"idle": {"O"}, "reconfigure_TEST": {"N1"}},
                 "N0": {"idle": {"N0"}, "move": {"N1"}},
                 "N1": {"idle": {"N1"}}}
        winning, ranks = attractor(set(edges), edges, domain)
        expected = "WIN" if "O" in winning else "LOSS"
        # Fully enumerate from the old entry, treating goals as terminal handoffs.
        reachable, queue, reduced_edges = {"O"}, deque(["O"]), set()
        while queue:
            source = queue.popleft()
            if source in domain:
                continue
            for action, targets in edges[source].items():
                reduced_edges.add((source, action, tuple(sorted(targets))))
                for target in targets:
                    if target not in reachable:
                        reachable.add(target)
                        queue.append(target)
        game = json.loads((folder / "independent-game-bundle.json").read_text())
        conversion = {"[OLD(0)]": "O", "[NEW(0)]": "N0", "[NEW(1)]": "N1"}
        by_id = {s["id"]: conversion[s["physical"]] for s in game["states"]}
        assert set(by_id.values()) == reachable == {"O", "N1"}
        assert {by_id[s] for s in game["initial_state_ids"]} == {"O"}
        assert {by_id[s] for s in game["goal_state_ids"]} == reachable & domain
        assert game["uncontrollable_bucket_count"] == 0
        for state in game["states"]:
            assert state["safe"] and not state["active_testers"]
            assert state["pending_actions"] == (["reconfigure_TEST"] if by_id[state["id"]] == "O" else [])
        actual_edges = {(by_id[b["source"]], b["action"], tuple(sorted(by_id[t] for t in b["targets"])))
                        for b in game["buckets"]}
        assert actual_edges == reduced_edges
        assert all(b["controllable"] for b in game["buckets"])
        actual = {"realizable": "WIN", "unrealizable": "LOSS"}[game["claimed_decision"]]
        assert actual == expected
        output = (folder / "output.txt").read_text()
        assert "Requirements: old=0, new=0, update-time=0" in output
        assert f"Loadable new endpoint signatures: {len(domain)} / 2" in output
        assert "Independent explicit verification: PASSED" in output
        assert "Internal certificate checker (same successor semantics): passed" in output
        meta = json.loads((folder / "meta.json").read_text())
        assert meta["status"] == "finished"
        assert meta["exit_code"] == (0 if expected == "WIN" else 6)
        assert hashlib.sha256((folder / "model.lts").read_bytes()).hexdigest() == meta["input_sha256"]
        if expected == "WIN":
            bundle = json.loads((folder / "handoff-bundle.json").read_text())
            assert bundle["certificate_state_count"] == 2 and bundle["maximum_rank"] == 1
            assert bundle["strategy_bucket_count"] == bundle["strategy_outcome_edge_count"] == 1
            assert bundle["strategy"] == [{"source": "M1", "action": "reconfigure_TEST",
                                            "outcomes": [{"index": 0, "target": "M0", "goal": True}]}]
            configurations = {c["id"]: c for c in bundle["configurations"]}
            assert configurations["M1"]["physical_state"] == "[OLD(0)]"
            assert configurations["M1"]["rank"] == 1 and configurations["M1"]["initial"]
            assert configurations["M0"]["physical_state"] == "[NEW(1)]"
            assert configurations["M0"]["rank"] == 0 and configurations["M0"]["goal"]
            assert len(bundle["handoffs"]) == 1
            handoff = bundle["handoffs"][0]
            assert handoff["endpoint_id"] == "new-00000001"
            assert handoff["post_state_id"] == "N1" and handoff["controller_state_to_load"] == 1
            assert "N1" in domain
            # Validate all new endpoint state/controller pairs, not just the goal.
            saved_post = bundle["post_states"]
            assert len(saved_post) == 2
            for i, saved in enumerate(saved_post):
                assert saved["id"] == f"N{i}" and saved["controller_state"] == i
                assert saved["local_states"] == [str(i)] and saved["monitor_states"] == {}
                observed = {e["action"]: set(e["outcomes"]) for e in saved["transitions"]}
                expected_edges = {a: {t[0] for t in targets} for a, targets in new_edges[new_states[i]].items()}
                assert observed == expected_edges
            assert bundle["q0_entries"] == [{"old_state_id": "O0", "old_controller_state": 0,
                                              "root_configuration": "M1"}]
            assert all(not c["active_monitor_states"] for c in bundle["configurations"])
            assert "Atomic Link checker: passed" in output
            certificate_states, certificate_rank, loaded = 2, 1, "N1 / controller state 1"
        else:
            assert not (folder / "handoff-bundle.json").exists()
            certificate_states, certificate_rank, loaded = "not applicable", "not applicable", "none"
        rows.append({"case": case, "selected_indices": ";".join(map(str, selected)),
                     "eligible_new_endpoint_states": "N0;N1", "selected_load_targets": ";".join(sorted(domain)),
                     "python_expected": expected, "java_decision": actual, "reachable_game_states": len(reachable),
                     "reachable_goal_states": len(reachable & domain), "certificate_states": certificate_states,
                     "certificate_max_rank": certificate_rank, "loaded_target": loaded, "checks": "PASS"})
        details[case] = {"source_input": f"{case}/model.lts", "old_endpoint_product": old_states,
                         "new_endpoint_product_in_bfs_order": new_states,
                         "selected_eligible_endpoint_states": sorted(domain),
                         "independent_full_graph": {s: {a: sorted(t) for a, t in outgoing.items()} for s, outgoing in edges.items()},
                         "independent_winning_states": sorted(winning), "independent_rank": ranks,
                         "reachable_update_states": sorted(reachable), "reachable_goal_states": sorted(reachable & domain),
                         "expected_decision": expected, "exported_graph_exact_match": True,
                         "scope": "monitor-free functional selector check; no initializer, UC, dependency, performance, or runtime claim"}
    assert len(set(normalized)) == 1, "Cases must vary only the selector clause."
    assert [row["selected_indices"] for row in rows] == ["0;1", "1", "0"]
    assert [row["python_expected"] for row in rows] == ["WIN", "WIN", "LOSS"]
    with (HERE / "summary.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    (HERE / "independent_oracle.json").write_text(json.dumps(details, indent=2) + "\n")
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
