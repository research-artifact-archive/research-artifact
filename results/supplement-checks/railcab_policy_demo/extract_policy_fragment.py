#!/usr/bin/env python3
"""Check the saved bundle and extract its unique multi-outcome policy branch.

Reads saved outputs only; never launches Java. These are structural consistency
checks of a certificate already accepted by the same-semantics Java checker and
Link checker, not an independent validation of the synthesis semantics. Retains
every descendant/outcome of the branch, plus a shortest recorded entry prefix.
"""
import collections
import csv
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent


def write_csv(name, rows):
    with (HERE / name).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    bundle = json.loads((HERE / "handoff-bundle.json").read_text())
    output = (HERE / "output.txt").read_text()
    assert "Internal certificate checker [revised_internal_certificate_check] : passed" in output
    assert "Atomic Link checker [revised_link_checker] : passed" in output
    cfg = {s["id"]: s for s in bundle["configurations"]}
    post = {s["id"]: s for s in bundle["post_states"]}
    controllable = set(bundle["controllable_actions"])
    adjacency = collections.defaultdict(list)
    for bucket in bundle["strategy"]:
        assert bucket["source"] in cfg and bucket["outcomes"]
        adjacency[bucket["source"]].append(bucket)
        for target in bucket["outcomes"]:
            assert target["target"] in cfg
            assert cfg[target["target"]]["rank"] < cfg[bucket["source"]]["rank"]
            assert target["goal"] == cfg[target["target"]]["goal"]
    for state in cfg.values():
        buckets = adjacency[state["id"]]
        if state["goal"]:
            assert state["rank"] == 0 and not buckets and not state["pending_update_actions"]
        else:
            assert buckets
            owned = [b for b in buckets if b["action"] in controllable]
            assert not owned or len(owned) == len(buckets) == 1
    entries = {r["root_configuration"] for r in bundle["q0_entries"]}
    assert entries == {s["id"] for s in cfg.values() if s["initial"]}
    goals = {s["id"] for s in cfg.values() if s["goal"]}
    assert goals == {h["goal_configuration"] for h in bundle["handoffs"]}
    for handoff in bundle["handoffs"]:
        goal = cfg[handoff["goal_configuration"]]
        target = post[handoff["post_state_id"]]
        assert handoff["controller_state_to_load"] == target["controller_state"]
        assert handoff["endpoint_id"] == goal["goal_endpoint_id"]
        assert re.findall(r"NEW\((.*?)\)", goal["physical_state"]) == target["local_states"]
        assert goal["active_monitor_states"] == target["monitor_states"]
        assert all(t["action"] in controllable for t in target["transitions"])

    def reachable(start):
        seen, queue = set(), collections.deque(start)
        while queue:
            state = queue.popleft()
            if state in seen:
                continue
            seen.add(state)
            for bucket in adjacency[state]:
                queue.extend(t["target"] for t in bucket["outcomes"])
        return seen

    assert reachable(entries) == set(cfg)
    assert len(cfg) == bundle["certificate_state_count"] == 115
    assert len(bundle["strategy"]) == bundle["strategy_bucket_count"] == 117
    assert sum(len(b["outcomes"]) for b in bundle["strategy"]) == bundle["strategy_outcome_edge_count"] == 118
    assert len(entries) == bundle["initial_configuration_count"] == 22
    assert len(goals) == bundle["goal_count"] == 2
    assert len(post) == bundle["post_state_count"] == 71
    assert max(s["rank"] for s in cfg.values()) == bundle["maximum_rank"] == 21
    branches = [b for b in bundle["strategy"] if len(b["outcomes"]) > 1]
    assert len(branches) == 1
    branch = branches[0]
    assert branch["action"] == "reconfigure_MILESTONES" and branch["action"] in controllable
    descendants = reachable([branch["source"]])
    paths = []
    for outcome in branch["outcomes"]:
        current = outcome["target"]
        path = []
        while not cfg[current]["goal"]:
            buckets = adjacency[current]
            assert len(buckets) == 1 and len(buckets[0]["outcomes"]) == 1, current
            bucket = buckets[0]
            target = bucket["outcomes"][0]["target"]
            path.append(dict(source=current, source_rank=cfg[current]["rank"],
                             action=bucket["action"], ownership="C" if bucket["action"] in controllable else "UC",
                             target=target, target_rank=cfg[target]["rank"]))
            current = target
        paths.append(dict(first_outcome=outcome["target"], length_after_transfer=len(path), edges=path,
                          handoff=next(h for h in bundle["handoffs"] if h["goal_configuration"] == current)))
    assert len(descendants) == 26 and sum(len(p["edges"]) for p in paths) == 23
    assert sorted(p["length_after_transfer"] for p in paths) == [11, 12]
    prefix_options = []
    for entry in bundle["q0_entries"]:
        queue = collections.deque([(entry["root_configuration"], [])])
        seen = set()
        while queue:
            state, path = queue.popleft()
            if state == branch["source"]:
                prefix_options.append((len(path), entry["old_state_id"], entry, path))
                break
            if state in seen:
                continue
            seen.add(state)
            for bucket in adjacency[state]:
                for target in bucket["outcomes"]:
                    queue.append((target["target"], path + [dict(source=state, action=bucket["action"], target=target["target"])]))
    _, _, entry, prefix = min(prefix_options, key=lambda row: (row[0], row[1]))
    for edge in prefix:
        assert len(adjacency[edge["source"]]) == 1 and len(adjacency[edge["source"]][0]["outcomes"]) == 1
    fragment = dict(source="handoff-bundle.json", scope="Complete descendant subgraph of the unique retained multi-outcome bucket; model-policy illustration only.",
                    semantic_check_scope="Java same-successor-semantics certificate checker and Link checker passed; no independent explicit game check in this demo.",
                    original_certificate=dict(states=115, buckets=117, outcomes=118, entries=22, goals=2),
                    fragment_state_count=26, fragment_edge_count=25,
                    branch=branch, branch_configuration=cfg[branch["source"]],
                    shortest_entry_witness=dict(entry=entry, edges=prefix),
                    branches_after_transfer=paths,
                    configurations=[cfg[s] for s in sorted(descendants, key=lambda q: int(q[1:]))])
    (HERE / "policy-fragment.json").write_text(json.dumps(fragment, indent=2) + "\n")
    edges = [dict(source=branch["source"], source_rank=cfg[branch["source"]]["rank"],
                  action=branch["action"], ownership="C", target=o["target"], target_rank=cfg[o["target"]]["rank"])
             for o in branch["outcomes"]]
    for path in paths:
        edges.extend(path["edges"])
    write_csv("policy-fragment-edges.csv", edges)
    write_csv("policy-fragment-states.csv", [dict(id=s["id"], rank=s["rank"], goal=s["goal"],
              physical_state=s["physical_state"], active_monitor_states=json.dumps(s["active_monitor_states"], sort_keys=True),
              pending_update_actions=";".join(s["pending_update_actions"])) for s in fragment["configurations"]])
    print("PASS: all 115 certificate states reachable from 22 entries; all 118 retained edges strictly decrease rank.")
    print("PASS: both goal tuples/monitor states equal their fixed endpoint/load records; both endpoints offer C actions only.")
    print("PASS: unique multi-outcome bucket retained with both outcomes; all 26 descendant states / 25 edges exported.")
    print("PASS: both suffixes and the shortest entry prefix are single-bucket/single-outcome paths; suffix lengths 11 and 12.")
    for path in paths:
        print(path["first_outcome"], ":", " > ".join(e["action"] for e in path["edges"]), "=>", path["handoff"])


if __name__ == "__main__":
    main()
