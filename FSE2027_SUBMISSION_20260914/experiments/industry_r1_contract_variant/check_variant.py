#!/usr/bin/env python3
"""Validate the single contract change and reproduce the exported game's decision.

This does not execute Java, edit source inputs, or explore further variants.
The independently exported game shares the adapter's prepared endpoint problem.
"""
from pathlib import Path
from collections import Counter, defaultdict, deque
import csv
import json

HERE = Path(__file__).resolve().parent
RAW = HERE / 'raw'
BASE = HERE.parent / 'rq3_xeon/raw/industry-r1-independent'


def source_model(here=HERE):
    """Resolve the same input in the local bundle and distributed artifact."""
    relative = Path('Implementation/Experiment/Models/Industry_FG.lts')
    for root in (here.parent / 'rq3_xeon/bundle', here.parents[2]):
        if (root / relative).is_file():
            return root / relative
    raise FileNotFoundError('Industry_FG.lts is absent from both supported layouts')


def key(state):
    return (state['physical'], tuple(sorted(state['active_testers'].items())),
            tuple(sorted(state['pending_actions'])))


def main():
    original = (HERE / 'inputs/Industry_FG.original.lts').read_text()
    modified = (HERE / 'inputs/Industry_FG_R1_allow_validateGF1.lts').read_text()
    expected = original
    expected_bytes = (HERE / 'inputs/Industry_FG.original.lts').read_bytes()
    for requirement in ('TOR_POLICY', 'DSD1_POLICY', 'DO_NOT_SEND_TWICE'):
        before = ('ltl_property R1_P_NEW_' + requirement + ' = [](AfterStopBeforeStart_P_NEW_'
                  + requirement + ' -> !AnyAction)')
        expected = expected.replace(before, before.replace('!AnyAction', '!(AnyAction && !validateGF1)'))
        expected_bytes = expected_bytes.replace(before.encode(), before.replace(
            '!AnyAction', '!(AnyAction && !validateGF1)').encode())
    assert modified == expected
    assert (HERE / 'inputs/Industry_FG_R1_allow_validateGF1.lts').read_bytes() == expected_bytes
    assert (HERE / 'inputs/Industry_FG.original.lts').read_bytes() == source_model().read_bytes()
    clauses = [
        'fluent NewTORDone = <readyTOR,{approveGF1,adjustGF1,cancelGF1}>',
        'fluent DSD1Done = <readyDSD1,{approveGF1,adjustGF1,cancelGF1}>',
        'GF1RESPONSE = ({adjustGF1,approveGF1,cancelGF1} -> GATEFORM1_OLD).',
        'GF1RESPONSE = ({adjustGF1,approveGF1,cancelGF1} -> GATEFORM1_NEW).']
    assert all(clause in original and clause in modified for clause in clauses)
    assert json.loads((RAW / 'environment.json').read_text())['classpath']['sha256'] == json.loads(
        (BASE / 'environment.json').read_text())['classpath']['sha256']
    game = json.loads((RAW / 'independent-game.json').read_text())
    states = {s['id']: s for s in game['states']}
    buckets = game['buckets']
    by_key = {key(s): s['id'] for s in game['states']}
    assert len(by_key) == len(states)
    outgoing, reverse = defaultdict(list), defaultdict(list)
    left, uc_left, has_uc = [], Counter(), set()
    maximum_rank = [0] * len(buckets)
    uc_maximum_rank = Counter()
    for i, b in enumerate(buckets):
        outgoing[b['source']].append(i)
        assert len(b['targets']) > 0
        left.append(len(b['targets']))
        if not b['controllable']:
            has_uc.add(b['source'])
            uc_left[b['source']] += len(b['targets'])
        for target in b['targets']:
            reverse[target].append(i)
    ranks = {q: 0 for q in game['goal_state_ids']}
    chosen = {}
    queue = deque(sorted(ranks))
    while queue:
        t = queue.popleft()
        for i in reverse[t]:
            b = buckets[i]
            q = b['source']
            left[i] -= 1
            maximum_rank[i] = max(maximum_rank[i], ranks[t])
            if not b['controllable']:
                uc_left[q] -= 1
                uc_maximum_rank[q] = max(uc_maximum_rank[q], ranks[t])
                ready, rank = uc_left[q] == 0, uc_maximum_rank[q] + 1
            else:
                ready, rank = q not in has_uc and left[i] == 0, maximum_rank[i] + 1
            if ready and states[q]['safe'] and q not in ranks:
                ranks[q] = rank
                chosen[q] = ([j for j in outgoing[q] if not buckets[j]['controllable']]
                             if q in has_uc else [i])
                queue.append(q)
    roots = game['initial_state_ids']
    assert len(roots) == 131 and all(q in ranks for q in roots)
    assert game['claimed_decision'] == 'realizable'

    # Save and validate a complete all-root policy, with a strict rank on every edge.
    reached = set(roots)
    queue = deque(roots)
    policy = []
    while queue:
        q = queue.popleft()
        assert states[q]['safe']
        if q in game['goal_state_ids']:
            assert ranks[q] == 0
            continue
        selected = chosen[q]
        assert selected
        if q in has_uc:
            assert selected == [j for j in outgoing[q] if not buckets[j]['controllable']]
        else:
            assert len(selected) == 1 and buckets[selected[0]]['controllable']
        for i in selected:
            b = buckets[i]
            for t in b['targets']:
                assert t in ranks and ranks[t] < ranks[q]
                if t not in reached:
                    reached.add(t)
                    queue.append(t)
            policy.append(dict(**b, rank=ranks[q], target_ranks=[ranks[t] for t in b['targets']]))
    (RAW / 'python-winning-policy.json').write_text(json.dumps(dict(
        roots=roots, states=[dict(state=states[q], rank=ranks[q]) for q in sorted(reached)],
        buckets=policy, all_outcomes_rank_decrease=True), indent=2) + '\n')

    old_analysis = json.loads((BASE / 'graph-analysis.json').read_text())
    witness = by_key[key(old_analysis['illustrative_losing_root'])]
    assert witness in roots and witness in ranks
    # Find the first permitted validateGF1 on the policy rooted at the old witness.
    queue = deque([witness])
    visited, previous = {witness}, {}
    selected_validation = None
    while queue and selected_validation is None:
        q = queue.popleft()
        for i in chosen.get(q, []):
            b = buckets[i]
            if b['action'] == 'validateGF1':
                selected_validation = b
                break
            for t in b['targets']:
                if t not in visited:
                    visited.add(t); previous[t] = (q, b['action']); queue.append(t)
    assert selected_validation is not None
    prefix = []
    q = selected_validation['source']
    while q != witness:
        before, action = previous[q]
        prefix.append(dict(source=before, action=action, target=q))
        q = before
    prefix.reverse()
    response_state = selected_validation['targets'][0]
    responses = [buckets[i] for i in outgoing[response_state] if not buckets[i]['controllable']]
    assert {b['action'] for b in responses} == {'adjustGF1', 'approveGF1', 'cancelGF1'}

    def sample_to_goal(start):
        path, q = [], start
        while not states[q]['goal']:
            b = buckets[chosen[q][0]]
            t = b['targets'][0]
            assert ranks[t] < ranks[q]
            path.append(dict(source=q, action=b['action'], target=t))
            q = t
        return path, q

    response_evidence = []
    for b in responses:
        for target in b['targets']:
            path, goal = sample_to_goal(target)
            response_evidence.append(dict(action=b['action'], target=target, rank=ranks[target],
                                          example_suffix=path, goal=states[goal]))
    old_game = json.loads((BASE / 'independent-game.json').read_text())
    old_roots = [s for s in old_game['states'] if s['initial']]
    correspondence = [dict(original_root=s['id'], variant_root=by_key[key(s)],
                           original_decision=('LOSS' if s['id'] in old_analysis['losing_root_ids'] else 'WIN'),
                           variant_decision='WIN', variant_rank=ranks[by_key[key(s)]]) for s in old_roots]
    assert set(row['variant_root'] for row in correspondence) == set(roots)
    with (RAW / 'root-correspondence.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(correspondence[0]))
        writer.writeheader(); writer.writerows(correspondence)
    result = dict(decision='WIN', initial_states=131, winning_initial_states=131,
                  unchanged_initial_configurations=True, original_losing_initial_states=42,
                  modified_contract_elements=3, exempted_existing_event='validateGF1',
                  source_reset_and_response_clauses=clauses,
                  source_input_difference='Only the three R1 bans; all other source lines unchanged',
                  exported_states=len(states), exported_queries=game['query_count'],
                  exported_outcomes=game['outcome_edge_count'], winning_states=len(ranks),
                  python_policy_states=len(reached), python_policy_buckets=len(policy),
                  all_root_rank_certificate_verified=True,
                  original_witness=old_analysis['illustrative_losing_root']['id'], variant_witness=witness,
                  policy_prefix=prefix, permitted_validation=selected_validation,
                  validation_source=states[selected_validation['source']],
                  all_uncontrollable_responses=response_evidence,
                  qualification='Assumes gate-form validation is allowed during the update gap; '
                  'no claim of business acceptability or comparison of performance',
                  original_contract_and_27_cases_unchanged=True)
    (RAW / 'contract-variant-analysis.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('decision', 'initial_states', 'winning_initial_states',
        'unchanged_initial_configurations', 'exported_states', 'winning_states', 'python_policy_states',
        'python_policy_buckets', 'all_root_rank_certificate_verified')}, indent=2))
    print('Witness prefix:', ' -> '.join(e['action'] for e in prefix + [selected_validation]))
    print('All UC responses:', ', '.join(x['action'] for x in response_evidence))


if __name__ == '__main__':
    main()
