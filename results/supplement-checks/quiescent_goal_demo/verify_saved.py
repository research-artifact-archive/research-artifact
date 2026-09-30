#!/usr/bin/env python3
"""Restricted source-FSP oracle; no Java classes or Java decisions define truth.

Derives endpoints, controller eligibility, NP successors, quiescent goals and
the strong attractor from the saved inputs. Then checks every exported game
state/bucket and every WIN certificate, strategy, endpoint and handover record.
"""
import argparse
import csv
import hashlib
import json
from collections import deque
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
CASES = ("persistent_uc", "finite_uc_all_targets", "finite_uc_nonquiescent_target_only")


def parse(text):
    text = re.sub(r"//[^\n]*", "", text)
    states = {}
    for name, body in re.findall(r"^([A-Z][A-Z0-9_]*) = \(([^\n]+)\)[.,]$", text, re.M):
        outgoing = {}
        for branch in body.split("|"):
            label, target = re.fullmatch(r"\s*([A-Za-z0-9_]+)\s*->\s*([A-Z][A-Z0-9_]*)\s*", branch).groups()
            outgoing.setdefault(label, set()).add(target)
        states[name] = outgoing
    aliases = dict(re.findall(r"^([A-Z][A-Z0-9_]*) = ([A-Z][A-Z0-9_]*),$", text, re.M))
    controllable = set(x.strip() for x in re.search(r"set ControllableActions = \{([^}]+)\}", text)[1].split(","))
    src, action, dst = re.search(r"([A-Z0-9_]+)@TEST_OLD = ([A-Za-z0-9_]+) -> ([A-Z0-9_]+)@TEST_NEW", text).groups()
    selected = tuple(int(x.strip()) for x in re.search(r"loadable_new_states = \{([^}]+)\}", text)[1].split(","))
    assert all(target in states for es in states.values() for ts in es.values() for target in ts)
    assert aliases["TEST_OLD"] == "O" and aliases["TEST_NEW"] == "N0" and aliases["NEW_C"] == "C0"
    assert "||OldController = (OLD_C)." in text and "||NewController = (NEW_C)." in text
    assert all(clause in text for clause in ("oldEnvironment = {TEST_OLD}", "newEnvironment = {TEST_NEW}", "mapRelation = {R_TEST_FG}", "oldGoal = OldSpec", "newGoal = NewSpec"))
    assert "safety =" not in text and "transition =" not in text and "precedence =" not in text
    assert controllable == {"idle"} and action == "reconfigure_TEST"
    return states, aliases, controllable, (src, action, dst), selected


def bfs_states(states, initial):
    found, queue = [initial], deque([initial])
    while queue:
        for action, targets in sorted(states[queue.popleft()].items()):
            for target in sorted(targets):
                if target not in found:
                    found.append(target); queue.append(target)
    return found


def endpoint(states, initial, controllable):
    found, queue, edges = [initial], deque([initial]), {}
    env_states = bfs_states(states, initial[0])
    ctrl_states = bfs_states(states, initial[1])
    env_alphabet = set().union(*(set(states[s]) for s in env_states))
    ctrl_alphabet = set().union(*(set(states[s]) for s in ctrl_states))
    assert env_alphabet <= ctrl_alphabet
    while queue:
        source = queue.popleft()
        env, ctrl = source
        outgoing = {}
        for action in sorted(set(states[env]) & set(states[ctrl])):
            targets = {(e, c) for e in states[env][action] for c in states[ctrl][action]}
            outgoing[action] = targets
            for target in sorted(targets):
                if target not in found:
                    found.append(target); queue.append(target)
        assert outgoing, "Endpoint deadlock."
        for action in set(states[env]) - controllable:
            assert action in outgoing
            assert {t[0] for t in outgoing[action]} == states[env][action], "UC outcome suppressed."
        edges[source] = outgoing
    return found, edges, env_states, ctrl_states


def derive(text):
    fsp, aliases, controlled, transfer, selected = parse(text)
    old, old_edges, old_local, old_ctrl = endpoint(fsp, (aliases["TEST_OLD"], "OLD_C"), controlled)
    new, new_edges, new_local, new_ctrl = endpoint(fsp, (aliases["TEST_NEW"], aliases["NEW_C"]), controlled)
    assert old == [("O", "OLD_C")]
    assert all(0 <= index < len(new) for index in selected)
    load_targets = {new[index][0] for index in selected}
    initial = {"OLD:" + e for e, _ in old}
    found, queue, edges, goals, rejected = set(initial), deque(sorted(initial)), {}, set(), set()
    while queue:
        state = queue.popleft()
        version, local = state.split(":")
        ordinary = {a: {version + ":" + t for t in ts} for a, ts in fsp[local].items()}
        uc = set(ordinary) - controlled
        match = version == "NEW" and local in load_targets
        if match and not uc:
            goals.add(state); edges[state] = {}; continue
        if match and uc:
            rejected.add(state)
        outgoing = dict(ordinary)
        if version == "OLD" and not uc and local == transfer[0]:
            outgoing[transfer[1]] = {"NEW:" + transfer[2]}
        edges[state] = outgoing
        for targets in outgoing.values():
            for target in sorted(targets):
                if target not in found:
                    found.add(target); queue.append(target)
    all_controls = controlled | {transfer[1]}
    rank = {g: 0 for g in goals}
    while True:
        added = {}
        for state in sorted(found - rank.keys()):
            uc = [ts for a, ts in edges[state].items() if a not in all_controls]
            if uc:
                targets = set().union(*uc)
                if targets and targets <= rank.keys():
                    added[state] = 1 + max(rank[t] for t in targets)
            else:
                values = [1 + max(rank[t] for t in ts) for ts in edges[state].values() if ts and ts <= rank.keys()]
                if values: added[state] = min(values)
        if not added: break
        rank.update(added)
    losing = found - rank.keys()
    for state in losing:
        uc = [ts for a, ts in edges[state].items() if a not in all_controls]
        if uc: assert any(ts & losing for ts in uc)
        else: assert all(ts & losing for ts in edges[state].values())
    expected = "WIN" if initial <= rank.keys() else "LOSS"
    return dict(fsp=fsp, old=old, new=new, old_edges=old_edges, new_edges=new_edges,
                old_local=old_local, new_local=new_local, old_ctrl=old_ctrl, new_ctrl=new_ctrl,
                controls=all_controls, selector=selected, load_targets=load_targets,
                initial=initial, states=found, edges=edges, goals=goals, rejected=rejected,
                rank=rank, losing=losing, expected=expected)


def serial(d):
    return {"old_endpoint_product": d["old"], "new_endpoint_product": d["new"],
            "selected_endpoint_indices": d["selector"], "selected_load_targets": sorted(d["load_targets"]),
            "initial_states": sorted(d["initial"]), "reachable_states": sorted(d["states"]),
            "goals": sorted(d["goals"]), "nonquiescent_matches_rejected": sorted(d["rejected"]),
            "buckets": {s: {a: sorted(ts) for a, ts in es.items()} for s, es in d["edges"].items()},
            "ranks": d["rank"], "losing_closure": sorted(d["losing"]), "expected_decision": d["expected"]}


def physical_names(d):
    return {f"[{version}({i})]": version + ":" + local
            for version, key in (("OLD", "old_local"), ("NEW", "new_local"))
            for i, local in enumerate(d[key])}


def check_saved(case, d):
    folder = HERE / case
    game = json.loads((folder / "independent-game-bundle.json").read_text())
    names = physical_names(d)
    by_id = {s["id"]: names[s["physical"]] for s in game["states"]}
    assert len(by_id) == len(set(by_id.values())) == len(d["states"]) == game["state_count"]
    assert set(by_id.values()) == d["states"]
    assert {by_id[s] for s in game["initial_state_ids"]} == d["initial"]
    assert {by_id[s] for s in game["goal_state_ids"]} == d["goals"]
    for state in game["states"]:
        name = by_id[state["id"]]
        assert state["safe"] and not state["active_testers"]
        assert state["goal"] == (name in d["goals"]) and state["initial"] == (name in d["initial"])
        assert state["pending_actions"] == (["reconfigure_TEST"] if name.startswith("OLD:") else [])
    actual_edges = {(by_id[b["source"]], b["action"], tuple(sorted(by_id[t] for t in b["targets"]))) for b in game["buckets"]}
    expected_edges = {(s, a, tuple(sorted(ts))) for s, es in d["edges"].items() for a, ts in es.items()}
    assert actual_edges == expected_edges
    assert len(game["buckets"]) == len(actual_edges)
    # The exporter counts empty candidates as queries but serializes nonempty
    # buckets only. At NEW:N1, `step` remains in the component alphabet and is
    # queried empty when N1 is not a goal (the restricted-target LOSS case).
    expected_queries = 0
    for name in d["states"] - d["goals"]:
        version, _ = name.split(":")
        local_states = d["old_local" if version == "OLD" else "new_local"]
        candidates = set().union(*(set(d["fsp"][s]) for s in local_states))
        if version == "OLD": candidates.add("reconfigure_TEST")
        expected_queries += len(candidates)
    assert game["query_count"] == expected_queries
    assert sum(len(b["targets"]) for b in game["buckets"]) == game["outcome_edge_count"]
    for b in game["buckets"]: assert b["controllable"] == (b["action"] in d["controls"])
    assert game["uncontrollable_bucket_count"] == sum(a not in d["controls"] for _, a, _ in actual_edges)
    assert game["controllable_bucket_count"] == len(actual_edges) - game["uncontrollable_bucket_count"]
    actual = {"realizable": "WIN", "unrealizable": "LOSS"}[game["claimed_decision"]]
    assert actual == d["expected"]
    output = (folder / "output.txt").read_text()
    for phrase in ("Requirements: old=0, new=0, update-time=0", "Independent explicit verification: PASSED", "Internal certificate checker (same successor semantics): passed", "FG-DUCS input contract status [revised_input_contract_status] : valid"):
        assert phrase in output, phrase
    assert f"Loadable new endpoint signatures: {len(d['selector'])} / {len(d['new'])}" in output
    meta = json.loads((folder / "meta.json").read_text())
    assert meta["status"] == "finished" and meta["attempt"] == 1
    assert meta["exit_code"] == (0 if actual == "WIN" else 6)
    assert hashlib.sha256((folder / "model.lts").read_bytes()).hexdigest() == meta["input_sha256"]
    certificate_states, certificate_rank, loaded = "not applicable", "not applicable", "none"
    if actual == "WIN":
        bundle = json.loads((folder / "handoff-bundle.json").read_text())
        configurations = {c["id"]: c for c in bundle["configurations"]}
        c_names = {i: names[c["physical_state"]] for i, c in configurations.items()}
        assert set(c_names.values()) == d["states"] == set(d["rank"])
        assert len(configurations) == bundle["certificate_state_count"] == 3
        assert bundle["initial_configuration_count"] == 1 and bundle["goal_count"] == 1
        assert bundle["maximum_rank"] == max(d["rank"].values()) == 2
        for i, c in configurations.items():
            name = c_names[i]
            assert c["rank"] == d["rank"][name]
            assert c["initial"] == (name in d["initial"]) and c["goal"] == (name in d["goals"])
            assert not c["active_monitor_states"]
            assert c["pending_update_actions"] == (["reconfigure_TEST"] if name.startswith("OLD:") else [])
            if c["goal"]: assert c["goal_endpoint_id"] == "new-00000001"
        expected_policy = set()
        for s in d["states"] - d["goals"]:
            uc_actions = [a for a in d["edges"][s] if a not in d["controls"]]
            if uc_actions:
                retained = uc_actions
            else:
                retained = [a for a, ts in d["edges"][s].items() if ts and all(d["rank"][t] < d["rank"][s] for t in ts)]
                assert len(retained) == 1
            expected_policy.update((s, a, tuple(sorted(d["edges"][s][a]))) for a in retained)
        actual_policy = set()
        for bucket in bundle["strategy"]:
            s = c_names[bucket["source"]]
            targets = []
            for index, outcome in enumerate(bucket["outcomes"]):
                target = c_names[outcome["target"]]
                assert outcome["index"] == index and outcome["goal"] == (target in d["goals"])
                assert d["rank"][target] < d["rank"][s]
                targets.append(target)
            actual_policy.add((s, bucket["action"], tuple(sorted(targets))))
        assert actual_policy == expected_policy
        assert len(actual_policy) == bundle["strategy_bucket_count"] == 2
        assert sum(len(x[2]) for x in actual_policy) == bundle["strategy_outcome_edge_count"] == 2
        assert len(bundle["handoffs"]) == 1
        handoff = bundle["handoffs"][0]
        assert c_names[handoff["goal_configuration"]] == "NEW:N1"
        assert handoff["endpoint_id"] == "new-00000001" and handoff["post_state_id"] == "N1"
        assert handoff["controller_state_to_load"] == 1
        assert len(bundle["post_states"]) == bundle["post_state_count"] == len(d["new"]) == 2
        for index, saved in enumerate(bundle["post_states"]):
            env, ctrl = d["new"][index]
            assert saved["id"] == f"N{index}" and saved["controller_state"] == d["new_ctrl"].index(ctrl)
            assert saved["local_states"] == [str(d["new_local"].index(env))] and saved["monitor_states"] == {}
            actual_post = {e["action"]: set(e["outcomes"]) for e in saved["transitions"]}
            expected_post = {a: {f"N{d['new'].index(t)}" for t in ts} for a, ts in d["new_edges"][(env, ctrl)].items()}
            assert actual_post == expected_post
        assert len(bundle["q0_entries"]) == 1
        entry = bundle["q0_entries"][0]
        assert entry["old_state_id"] == "O0" and entry["old_controller_state"] == 0
        assert c_names[entry["root_configuration"]] == "OLD:O"
        assert set(bundle["controllable_actions"]) == d["controls"] | {"hotSwapIn"}
        assert "Atomic Link checker: passed" in output
        # The full FSP includes the old controller before admission, the update
        # policy, and the loaded endpoint continuation. Check all four states.
        rendered = (folder / "transitions.txt").read_text()
        assert re.search(r"States:\s*4\s*Transitions:", rendered)
        fsp_graph = {}
        for state, body in re.findall(r"\b(Q\d+)\s*=\s*\(([^)]*)\)", rendered, re.S):
            outgoing = {}
            for a, target in re.findall(r"([A-Za-z0-9_]+)\s*->\s*(Q\d+)", body):
                outgoing.setdefault(a, set()).add(target)
            fsp_graph[state] = outgoing
        pre = re.search(r"UPDATE_CONTROLLER_OTF_FG\s*=\s*(Q\d+)", rendered)[1]
        assert set(fsp_graph[pre]) == {"idle", "hotSwapIn"}
        assert fsp_graph[pre]["idle"] == {pre}
        assert len(fsp_graph[pre]["hotSwapIn"]) == 1
        update_old = next(iter(fsp_graph[pre]["hotSwapIn"]))
        assert set(fsp_graph[update_old]) == {"reconfigure_TEST"}
        assert len(fsp_graph[update_old]["reconfigure_TEST"]) == 1
        update_new0 = next(iter(fsp_graph[update_old]["reconfigure_TEST"]))
        assert set(fsp_graph[update_new0]) == {"step"}
        assert len(fsp_graph[update_new0]["step"]) == 1
        loaded_new1 = next(iter(fsp_graph[update_new0]["step"]))
        assert fsp_graph[loaded_new1] == {"idle": {loaded_new1}}
        assert set(fsp_graph) == {pre, update_old, update_new0, loaded_new1}
        certificate_states, certificate_rank, loaded = 3, 2, "N1 / controller state 1"
    else:
        assert not (folder / "handoff-bundle.json").exists()
        count = int(re.search(r"Internal losing-region certificate states: (\d+)", output)[1])
        assert count == len(d["losing"]) == len(d["states"])
    return {"case": case, "selected_indices": ";".join(map(str, d["selector"])),
            "python_expected": d["expected"], "java_decision": actual,
            "reachable_game_states": len(d["states"]), "reachable_goals": len(d["goals"]),
            "nonquiescent_matches_rejected": len(d["rejected"]), "exported_buckets": len(actual_edges),
            "exported_queries_including_empty": expected_queries,
            "exported_uc_buckets": game["uncontrollable_bucket_count"],
            "win_certificate_states": certificate_states, "win_max_rank": certificate_rank,
            "loaded_target": loaded, "checks": "PASS"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs-only", action="store_true")
    args = parser.parse_args()
    inputs = {case: (HERE / case / "model.lts").read_text() for case in CASES}
    derived = {case: derive(text) for case, text in inputs.items()}
    # The two finite-UC cases differ only in supplied load targets.
    normalize = lambda s: re.sub(r"loadable_new_states = \{[^}]+\}", "loadable_new_states = {S}", s)
    assert normalize(inputs[CASES[1]]) == normalize(inputs[CASES[2]])
    assert [derived[case]["expected"] for case in CASES] == ["LOSS", "WIN", "LOSS"]
    assert all(derived[case]["rejected"] == {"NEW:N0"} for case in CASES)
    details = {case: serial(d) for case, d in derived.items()}
    (HERE / "independent_oracle.json").write_text(json.dumps(details, indent=2) + "\n")
    if args.inputs_only:
        print(json.dumps({case: {k: v for k, v in details[case].items() if k in ("expected_decision", "goals", "nonquiescent_matches_rejected", "ranks")} for case in CASES}, indent=2))
        return
    rows = [check_saved(case, d) for case, d in derived.items()]
    with (HERE / "summary.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
