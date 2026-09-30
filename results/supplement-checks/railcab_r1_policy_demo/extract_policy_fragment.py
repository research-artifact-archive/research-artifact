#!/usr/bin/env python3
"""Validate saved R1 structure and retain all paths from the Base-matched entry.

No Java invocation and no timing comparison. The returned R1 policy has zero
multi-outcome buckets; this fact is retained, not repaired by selecting another
run. The fragment uses the identical old endpoint entry used for the Base
illustration and includes every descendant edge, including both UC responses.
Checks are structural and compare the seven UPD states with saved monitor DFAs;
they do not independently reconstruct all game successors or runtime histories.
"""
import collections
import csv
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = Path(__import__("os").environ["FGDUCS_PACKAGE_ROOT"]) if "FGDUCS_PACKAGE_ROOT" in __import__("os").environ else next(p for p in HERE.parents if (p / "Implementation/Experiment/Models").is_dir())


def write_csv(name, rows):
    with (HERE / name).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    b = json.loads((HERE / "handoff-bundle.json").read_text())
    base_fragment = json.loads((HERE.parent / "railcab_policy_demo/policy-fragment.json").read_text())
    base_bundle = json.loads((HERE.parent / "railcab_policy_demo/handoff-bundle.json").read_text())
    cfg = {s["id"]: s for s in b["configurations"]}
    adjacency = collections.defaultdict(list)
    for bucket in b["strategy"]:
        adjacency[bucket["source"]].append(bucket)
    control = set(b["controllable_actions"])
    roots = {e["root_configuration"] for e in b["q0_entries"]}
    assert roots == {s["id"] for s in cfg.values() if s["initial"]}
    output = (HERE / "output.txt").read_text()
    assert "Internal certificate checker [revised_internal_certificate_check] : passed" in output
    assert "Atomic Link checker [revised_link_checker] : passed" in output
    assert (len(cfg), len(b["strategy"]), sum(len(r["outcomes"]) for r in b["strategy"]),
            len(roots), len(b["handoffs"]), len(b["post_states"]), max(s["rank"] for s in cfg.values())) == (44, 46, 46, 22, 1, 71, 33)
    multi_outcome = [r for r in b["strategy"] if len(r["outcomes"]) > 1]
    assert not multi_outcome
    monitor_path = ROOT / "FSE2027_SUBMISSION_20260914/experiments/rs_coverage/raw/expanded-predicates/railcab.json"
    monitors = {r["requirement"]: r for r in json.loads(monitor_path.read_text())["requirements"]
                if r["target"] == "r1" and r["kind"] == "upd"}
    assert len(monitors) == 7
    expected_upd_keys = {k for k in next(iter(cfg.values()))["active_monitor_states"] if k.startswith("update_time:")}
    assert len(expected_upd_keys) == 7
    forbidden = {"requestEnter", "brake", "emergencyBrake", "idle_c", "checkCrossingStatus"}
    checked_upd_edges = 0
    for state in cfg.values():
        buckets = adjacency[state["id"]]
        upd = {k: v for k, v in state["active_monitor_states"].items() if k.startswith("update_time:")}
        assert set(upd) == expected_upd_keys and set(upd.values()) <= {0, 1}
        if state["initial"]:
            assert set(upd.values()) == {0}
        if state["goal"]:
            assert not buckets and state["rank"] == 0 and not state["pending_update_actions"]
        else:
            assert buckets
            owned = [r for r in buckets if r["action"] in control]
            assert not owned or len(owned) == len(buckets) == 1
        for bucket in buckets:
            for outcome in bucket["outcomes"]:
                target = cfg[outcome["target"]]
                assert outcome["goal"] == target["goal"] and state["rank"] > target["rank"]
                for key, value in upd.items():
                    monitor = monitors[key.split(":")[1]]
                    transitions = {(s, a): t for s, a, t in monitor["transitions"]}
                    assert all(transitions[(1, a)] == -1 for a in forbidden)
                    expected = transitions[(value, bucket["action"])] if bucket["action"] in monitor["alphabet"] else value
                    assert expected != -1 and target["active_monitor_states"][key] == expected
                    checked_upd_edges += 1
    post = {s["id"]: s for s in b["post_states"]}
    for handoff in b["handoffs"]:
        goal, endpoint = cfg[handoff["goal_configuration"]], post[handoff["post_state_id"]]
        assert handoff["controller_state_to_load"] == endpoint["controller_state"]
        assert handoff["endpoint_id"] == goal["goal_endpoint_id"]
        assert re.findall(r"NEW\((.*?)\)", goal["physical_state"]) == endpoint["local_states"]
        # UPD remains active in the game; only NEW monitors belong to C_new.
        assert {k: v for k, v in goal["active_monitor_states"].items() if k.startswith("new:")} == endpoint["monitor_states"]
        assert all(t["action"] in control for t in endpoint["transitions"])

    def reachable(start):
        seen, queue = set(), collections.deque(start)
        while queue:
            source = queue.popleft()
            if source in seen:
                continue
            seen.add(source)
            for bucket in adjacency[source]:
                queue.extend(t["target"] for t in bucket["outcomes"])
        return seen

    assert reachable(roots) == set(cfg)
    selected_base = base_fragment["shortest_entry_witness"]["entry"]
    selected = next(e for e in b["q0_entries"] if e["old_state_id"] == selected_base["old_state_id"])
    assert selected["old_controller_state"] == selected_base["old_controller_state"]
    base_root = next(s for s in base_bundle["configurations"] if s["id"] == selected_base["root_configuration"])
    r1_root = cfg[selected["root_configuration"]]
    assert base_root["physical_state"] == r1_root["physical_state"]
    assert base_root["active_monitor_states"] == {k: v for k, v in r1_root["active_monitor_states"].items() if k.startswith("old:")}
    descendants = reachable([selected["root_configuration"]])
    buckets = [r for r in b["strategy"] if r["source"] in descendants]
    assert len(descendants) == len(buckets) == sum(len(r["outcomes"]) for r in buckets) == 32
    branch_sources = [q for q in descendants if len(adjacency[q]) > 1]
    assert len(branch_sources) == 1
    assert {r["action"] for r in adjacency[branch_sources[0]]} == {"enterAllowed.0", "enterAllowed.1"}
    edge_rows = []
    for bucket in buckets:
        for outcome in bucket["outcomes"]:
            source, target = cfg[bucket["source"]], cfg[outcome["target"]]
            edge_rows.append(dict(source=source["id"], source_rank=source["rank"], action=bucket["action"],
                                  ownership="C" if bucket["action"] in control else "UC", target=target["id"], target_rank=target["rank"]))
    fields = ["revised_certificate_states", "revised_certificate_strategy_action_buckets",
              "revised_certificate_strategy_transitions_unique", "revised_certificate_goal_matches",
              "revised_worst_completion_rank", "revised_initial_endpoint_embeddings",
              "revised_new_endpoint_signatures", "revised_update_requirement_count"]
    campaign = ROOT / "FSE2027_SUBMISSION_20260914/experiments/rq3_xeon/raw/rq3/runs"
    original_runs = sorted(campaign.glob("railcab__r1__rep*__fg_ducs_otf"))
    assert len(original_runs) == 5
    for path in original_runs:
        original = (path / "output.txt").read_text()
        for field in fields:
            pattern = r"\[" + re.escape(field) + r"\] : ([^\r\n]+)"
            assert re.search(pattern, original).group(1) == re.search(pattern, output).group(1)
    fragment = dict(source="handoff-bundle.json", scope="Complete descendant subgraph of the exact old endpoint entry used by the Base illustration.",
                    selection="Matched Base old endpoint O1/controller state 1 and identical physical state/old monitors; no performance-based choice.",
                    note="Returned R1 certificate contains zero multi-outcome transfer buckets. Its response branch uses two distinct UC labels.",
                    full_certificate=dict(states=44, buckets=46, outcomes=46, entries=22, goals=1, maximum_rank=33),
                    campaign_structure_check="All eight reported structural fields match each of the five original R1 repetitions; no timing comparison.",
                    fragment_state_count=32, fragment_edge_count=32, entry=selected,
                    configurations=[cfg[q] for q in sorted(descendants, key=lambda q: int(q[1:]))],
                    strategy=buckets, handoffs=b["handoffs"],
                    milestone_transfer_buckets=[r for r in b["strategy"] if r["action"] == "reconfigure_MILESTONES"],
                    updater_monitor_source=str(monitor_path.relative_to(ROOT)),
                    checked_upd_edge_steps=checked_upd_edges,
                    semantic_check_scope="Saved Java same-successor-semantics certificate/Link checks plus structural and saved-DFA consistency; no complete independent game or physical-runtime proof.")
    (HERE / "policy-fragment.json").write_text(json.dumps(fragment, indent=2) + "\n")
    write_csv("policy-fragment-edges.csv", edge_rows)
    write_csv("policy-fragment-states.csv", [dict(id=s["id"], rank=s["rank"], goal=s["goal"], physical_state=s["physical_state"],
              active_monitor_states=json.dumps(s["active_monitor_states"], sort_keys=True), pending_update_actions=";".join(s["pending_update_actions"]))
              for s in fragment["configurations"]])
    print("PASS: 44 states / 46 buckets / 46 outcomes / 22 entries / 1 goal / max rank 33; matches all five original repetitions.")
    print("PASS: zero multi-outcome buckets retained as observed; Base-matched O1 fragment includes all 32 states and 32 edges.")
    print("PASS: all certificate edges decrease rank;", checked_upd_edges, "UPD steps match the seven saved monitor DFAs.")
    print("PASS: goal physical state and NEW monitor values match fixed endpoint N3/controller state 3; UPD is not part of C_new.")


if __name__ == "__main__":
    main()
