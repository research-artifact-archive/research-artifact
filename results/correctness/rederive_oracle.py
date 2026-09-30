#!/usr/bin/env python3
"""Re-derive decisions from original LTS bytes under NP + quiescent goals.

The restricted Python raw-FSP parser and residual transition rules are reused
from the existing independent oracle, never from the Java implementation.
Expected labels/comments and Java outcomes are not inputs to the derivation.
The complete generated graph and finite ranks/losing closure are saved as data.
"""
from __future__ import annotations
import argparse
import csv
import json
import re
import sys
from collections import deque
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Implementation/Experiment/FSE2027/scripts'))
import independent_raw_oracle_v5 as old
from independent_raw_oracle import _without_comments, _ordinary_successors


def graph(path: Path, revised=True):
    # This call only constructs a raw graph; it neither solves nor reads labels.
    original = old.build_explicit_game(path)
    seen = set(original.initial_states)
    queue = deque(sorted(seen))
    edges, goals, rejected_matches = {}, set(), set()
    while queue:
        state = queue.popleft()
        ordinary = _ordinary_successors(original.model, state[0], state[1])
        uc = {a for a in ordinary if not original.is_controllable(a)}
        outgoing = old._successors(original, state)
        if revised and uc:
            updates = set(original.model.migration_actions.values()) | {original.start_action}
            outgoing = {a: targets for a, targets in outgoing.items() if a not in updates}
        match = (all(state[0]) and state[1] in original.loadable and state[2] and not state[3])
        if match and (not revised or not uc):
            goals.add(state)
        elif match:
            rejected_matches.add(state)
        edges[state] = outgoing
        for targets in outgoing.values():
            for target in targets:
                if target not in seen:
                    seen.add(target)
                    queue.append(target)
    result = replace(original, states=frozenset(seen), successors=edges, goals=frozenset(goals))
    return result, rejected_matches


def solve(g):
    rank = {s: 0 for s in g.goals}
    while True:
        added = {}
        for s in sorted(g.states - rank.keys()):
            if s[3]:  # violated safety is losing, even at a deadlock
                continue
            buckets = g.successors[s]
            uc = [targets for a, targets in buckets.items() if not g.is_controllable(a)]
            if uc:
                targets = set().union(*map(set, uc))
                if targets and targets <= rank.keys():
                    added[s] = 1 + max(rank[t] for t in targets)
            else:
                costs = [1 + max(rank[t] for t in ts) for ts in buckets.values()
                         if ts and set(ts) <= rank.keys()]
                if costs:
                    added[s] = min(costs)
        if not added:
            break
        rank.update(added)
    # Explicit closure checks ensure the saved losing set is a valid obstruction.
    losing = g.states - rank.keys()
    for s in losing:
        if s[3]:
            continue
        buckets = g.successors[s]
        uc = [ts for a, ts in buckets.items() if not g.is_controllable(a)]
        if uc:
            assert any(t in losing for ts in uc for t in ts)
        else:
            assert all(any(t in losing for t in ts) for ts in buckets.values())
    return ('realizable' if g.initial_states <= rank.keys() else 'unrealizable'), rank


def serialize(g, rank):
    states = sorted(g.states)
    ids = {s: i for i, s in enumerate(states)}
    return dict(states=states, roots=[ids[s] for s in sorted(g.initial_states)],
                goals=[ids[s] for s in sorted(g.goals)],
                ranks={str(ids[s]): r for s, r in rank.items()},
                losing=[ids[s] for s in states if s not in rank],
                successors={str(ids[s]): {a: [ids[t] for t in ts] for a, ts in es.items()}
                            for s, es in g.successors.items()})


def contract_reason(path):
    """Derive eligibility directly for the five one-state contract fixtures."""
    s = _without_comments(path.read_text())
    control = set(re.search(r'set ControllableActions\s*=\s*\{([^}]+)\}', s)[1].replace(' ', '').split(','))
    for role in ('OLD', 'NEW'):
        env_body = re.search(role + r'_COMPONENT\s*=\s*\(([^;]+?)\)\.', s)[1]
        env = set(re.findall(r'(\w+)\s*->', env_body))
        m = re.search(role + r'_POLICY\s*=\s*(.*?)\.', s, re.S)
        if m is None:
            enabled, alphabet = env, env
        else:
            body = m[1]
            enabled = set(re.findall(r'(\w+)\s*->', body))
            alphabet = enabled | set(re.findall(r'\w+', ''.join(re.findall(r'\+\s*\{([^}]+)\}', body))))
        if env - alphabet:
            return 'invalid_input', f'{role.lower()} controller omits environment alphabet: {sorted(env-alphabet)}'
        if (env - control) - enabled:
            return 'invalid_input', f'{role.lower()} controller suppresses uncontrollable event: {sorted((env-control)-enabled)}'
        if not env & enabled:
            return 'invalid_input', f'{role.lower()} closed-loop initial state is deadlocked'
    return 'realizable', 'Both endpoints have controllable idle loops; singleton transfer reaches a quiescent load target.'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--semantic-dir', type=Path, required=True)
    parser.add_argument('--contract-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    rows = []
    for path in sorted(args.semantic_dir.glob('*.lts')):
        g, rejected = graph(path)
        result, rank = solve(g)
        legacy_result, _ = solve(graph(path, revised=False)[0])
        row = dict(model_id=path.stem, stratum='semantic', source=str(path),
                   expected_decision=result, prior_rule_decision=legacy_result,
                   changed=result != legacy_result, roots=len(g.initial_states),
                   states=len(g.states), goals=len(g.goals), losing_roots=len(g.initial_states-rank.keys()),
                   rejected_nonquiescent_matches=len(rejected),
                   basis='Raw FSP composition; NP update guard; quiescent target; exhaustive all-outcome attractor and losing closure')
        rows.append(row)
        (args.output/'raw'/f'{path.stem}.json').parent.mkdir(exist_ok=True)
        (args.output/'raw'/f'{path.stem}.json').write_text(json.dumps(serialize(g, rank), indent=2)+'\n')
    for path in sorted(args.contract_dir.glob('*.lts')):
        decision, reason = contract_reason(path)
        if decision == 'realizable':
            g, _ = graph(path)
            actual, _ = solve(g)
            assert actual == decision
        rows.append(dict(model_id=path.stem, stratum='contract', source=str(path), expected_decision=decision,
                         prior_rule_decision=decision, changed=False, roots='', states='', goals='',
                         losing_roots='', rejected_nonquiescent_matches='', basis=reason))
    with (args.output/'summary.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    print(json.dumps(dict(models=len(rows), semantic=sum(r['stratum']=='semantic' for r in rows),
                         changed=[r['model_id'] for r in rows if r['changed']],
                         counts={x:sum(r['expected_decision']==x for r in rows) for x in ('realizable','unrealizable','invalid_input')})))

if __name__ == '__main__':
    main()
