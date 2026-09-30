#!/usr/bin/env python3
"""Extract two continuous saved policy paths, without any solver execution."""
from collections import defaultdict
import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(__import__("os").environ["FGDUCS_PACKAGE_ROOT"]) if "FGDUCS_PACKAGE_ROOT" in __import__("os").environ else next(p for p in HERE.parents if (p / "Implementation/Experiment/Models").is_dir())
MONITOR = "R1_OTF_P_BRAKE_DURING_LASTBRAKE"
MONITOR_ID = "update_time:" + MONITOR + ":0"
STOP = "stopOldSpec_P_BRAKE_DURING_LASTBRAKE"


def load(name):
    directory = HERE / name
    data = json.loads((directory / "handoff-bundle.json").read_text())
    states = {s["id"]: s for s in data["configurations"]}
    adjacency = defaultdict(list)
    for bucket in data["strategy"]:
        for target in bucket["outcomes"]:
            adjacency[bucket["source"]].append((bucket["action"], target["target"]))
    return directory, data, states, adjacency


def path_to_goal(bundle, states, adjacency, start, selection):
    result = []
    current = start
    while not states[current]["goal"]:
        options = adjacency[current]
        if len(options) == 1:
            action, target = options[0]
        else:
            action, target = selection[current]
            assert (action, target) in options
        assert states[current]["rank"] > states[target]["rank"]
        result.append((current, action, target))
        current = target
    assert states[current]["rank"] == 0
    assert any(h["goal_configuration"] == current for h in bundle["handoffs"])
    return result


def step_monitor(row, state, event):
    if state == -1:
        return -1
    if event not in row["alphabet"]:
        return state
    matches = [t for s, a, t in row["transitions"] if s == state and a == event]
    assert len(matches) == 1
    return matches[0]


def main():
    base = load("railcab_policy_demo")
    r1 = load("railcab_r1_policy_demo")
    entries = [next(e for e in item[1]["q0_entries"] if e["old_state_id"] == "O1") for item in (base, r1)]
    assert entries[0]["old_controller_state"] == entries[1]["old_controller_state"] == 1
    assert [e["root_configuration"] for e in entries] == ["M64", "M28"]
    b0, r0 = [item[2][entry["root_configuration"]] for item, entry in zip((base, r1), entries)]
    assert b0["physical_state"] == r0["physical_state"]
    assert b0["active_monitor_states"] == {k: v for k, v in r0["active_monitor_states"].items() if k.startswith("old:")}
    base_path = path_to_goal(*base[1:], "M64", {"M69": ("reconfigure_MILESTONES", "M19")})
    r1_path = path_to_goal(*r1[1:], "M28", {"M30": ("enterAllowed.0", "M31")})
    r1_other = path_to_goal(*r1[1:], "M28", {"M30": ("enterAllowed.1", "M29")})
    assert not any(event == "brake" for _, event, _ in r1_other)
    assert len(base_path) == 18 and len(r1_path) == 22 and len(r1_other) == 27
    wanted = [("M19", "brake", "M1"), ("M1", "endOfTS", "M2"),
              ("M2", "approachingCrossing", "M13"), ("M13", STOP, "M14")]
    begin = r1_path.index(wanted[0])
    assert r1_path[begin:begin + len(wanted)] == wanted
    assert not any(a.startswith("stopOldSpec_") for _, a, _ in r1_path[:begin + 3])
    assert all(a.startswith("stopOldSpec_") for _, a, _ in base_path[:5])
    assert base_path[9] == ("M16", "brake", "M0")
    monitor_path = ROOT / "FSE2027_SUBMISSION_20260914/experiments/rs_coverage/raw/expanded-predicates/railcab.json"
    monitors = {r["requirement"]: r for r in json.loads(monitor_path.read_text())["requirements"] if r["target"] == "r1" and r["kind"] == "upd"}
    assert len(monitors) == 7
    for source, action, target in r1_path:
        for k, value in r1[2][source]["active_monitor_states"].items():
            if k.startswith("update_time:"):
                expected = step_monitor(monitors[k.split(":")[1]], value, action)
                assert expected != -1 and r1[2][target]["active_monitor_states"][k] == expected
    # Counterfactual monitor replay only: Base has no active UPD monitor.
    state = 0
    first_error = None
    for index, (_, event, _) in enumerate(base_path, 1):
        state = step_monitor(monitors[MONITOR], state, event)
        if state == -1:
            first_error = index
            break
    assert first_error == 10
    rows = []
    for variant, item, path in (("Base", base, base_path), ("R1", r1, r1_path)):
        directory, bundle, states, adjacency = item
        for index, (source, event, target) in enumerate(path, 1):
            before, after = states[source], states[target]
            rows.append(dict(variant=variant, step=index, source=source, source_rank=before["rank"],
                action=event, ownership="C" if event in bundle["controllable_actions"] else "UC",
                target=target, target_rank=after["rank"],
                source_old_monitors=sum(k.startswith("old:") for k in before["active_monitor_states"]),
                target_old_monitors=sum(k.startswith("old:") for k in after["active_monitor_states"]),
                source_new_monitors=sum(k.startswith("new:") for k in before["active_monitor_states"]),
                target_new_monitors=sum(k.startswith("new:") for k in after["active_monitor_states"]),
                source_example_R1_monitor_state=before["active_monitor_states"].get(MONITOR_ID, "ABSENT"),
                target_example_R1_monitor_state=after["active_monitor_states"].get(MONITOR_ID, "ABSENT"),
                source_outgoing_event_buckets=len({a for a, _ in adjacency[source]}),
                source_outcome_edges=len(adjacency[source]),
                selected_event_all_outcomes=";".join(t for a, t in adjacency[source] if a == event),
                other_outgoing_edges=";".join(a + "->" + t for a, t in adjacency[source] if (a, t) != (event, target)),
                target_goal=after["goal"], bundle=str(directory.relative_to(HERE) / "handoff-bundle.json")))
    with (HERE / "railcab_stop_brake_paths.csv").open("w", newline="") as stream:
        out = csv.DictWriter(stream, fieldnames=list(rows[0]))
        out.writeheader()
        out.writerows(rows)
    print("PASS: same old entry O1/controller 1 and same physical/old-monitor state.")
    print("PASS: Base 18-edge path and R1 22-edge path; every edge, ownership and rank checked against full saved bundles.")
    print("PASS: R1 M19->M1->M2->M13->M14 is consecutive; its stop is the first stop on this path.")
    print("PASS: seven R1 DFA states match every selected path edge; counterfactual Base monitor first rejects at step 10, brake.")
    print("PASS: retained R1 alternate UC response has a complete 27-edge no-brake path.")


if __name__ == "__main__":
    main()
