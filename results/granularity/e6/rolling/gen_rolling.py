#!/usr/bin/env python3
"""Create-only Rolling v1 inputs: finite readiness, interval availability, fixed groups."""
import argparse
import json
from pathlib import Path


def make(n, m, k):
    groups = [list(range(i, min(i + k, n))) for i in range(0, n, k)]
    names = ['ablation.merge.transfers'] if k == n else ['rho_' + str(i + 1) for i in range(len(groups))]
    group_of = {i: (name, len(group)) for group, name in zip(groups, names) for i in group}
    ready = ['ready_' + str(i + 1) for i in range(n)]
    serve = ['serve_' + str(i + 1) for i in range(n)]
    ordinary = serve + ready
    components = []
    for i in range(n):
        components.append(dict(id='replica_' + str(i + 1),
            old=dict(states=['ready'], initial='ready', edges=[['ready', serve[i], 'ready']]),
            new=dict(states=['booting', 'ready'], initial='ready',
                     edges=[['booting', ready[i], 'ready'], ['ready', serve[i], 'ready']]),
            transfer_action=group_of[i][0], transfer={'ready': ['booting']}))
    states = ['q' + str(i) for i in range(m, n + 1)] + ['ERR_AVAILABILITY']
    changes = []
    for count in range(m, n + 1):
        for action, members in zip(names, groups):
            nxt = count - len(members)
            changes.append(['q' + str(count), action, 'q' + str(nxt) if nxt >= m else 'ERR_AVAILABILITY'])
        for action in ready:
            changes.append(['q' + str(count), action, 'q' + str(min(n, count + 1))])
    tester = dict(states=states, initial='q' + str(n), errors=['ERR_AVAILABILITY'],
                  alphabet=ordinary + names, changes=changes)
    req = dict(id='availability', role='interval', tester=tester,
               activation=dict(entries=[dict(physical=[['OLD', 'ready']] * n,
                                              tester_state='q' + str(n), residual_state='q' + str(n))]))
    def endpoint(version):
        state = 'O' if version == 'OLD' else 'N'
        graph = dict(states=[state], initial=state, edges=[[state, action, state] for action in serve])
        controller = dict(states=['C'], initial='C', edges=[['C', action, 'C'] for action in serve])
        projection = dict(physical=[[version, 'ready']] * n, testers={})
        if version == 'NEW': projection['goal_id'] = 'all_ready'
        out = dict(lts=graph, controller=controller, projection={state: projection})
        if version == 'NEW': out['loadable'] = [state]
        return out
    result = dict(schema='fg-ducs-witness-v1', id=f'rolling_n{n:02}_m{m:02}_k{k:02}', family='rolling',
        parameters=dict(n=n, m=m, k=k), ordinary=ordinary, controllable=serve,
        components=components, requirements=[req], precedence=[],
        endpoints=dict(old=endpoint('OLD'), new=endpoint('NEW')),
        metadata=dict(mechanism='M2', expected_decision='WIN' if k <= n - m else 'LOSS',
            groups=groups, group_sizes=[len(g) for g in groups],
            readiness_abstraction='Each booting replica has one enabled uncontrollable ready event and no waiting self-loop; no fairness assumption.',
            endpoint_initial_note='The fixed new endpoint starts ready; transfers enter its booting state.',
            interval_meaning='At least m replicas are ready at every update state; transfer removes its group size from the count and each ready event restores one.',
            group_construction='n physical components retained; shared transfer labels admitted only through the documented existing E1 generated-contract builder hook.',
            anchor='Kubernetes Deployment maxUnavailable/maxSurge/readiness, not PDB enforcement of Deployment rolling updates.',
            source_url='https://kubernetes.io/docs/concepts/workloads/controllers/deployment/'))
    if k > 1: result['generated_contract_mode'] = 'transfers'
    return result


def main():
    parser = argparse.ArgumentParser();parser.add_argument('--out', type=Path, default=Path(__file__).parent / 'v1')
    args = parser.parse_args();out = args.out.resolve();out.mkdir(parents=True, exist_ok=False)
    (out / 'inputs').mkdir()
    jobs = []
    for n in range(2, 7):
        for m in range(1, n):
            for k in range(1, n + 1):
                data = make(n, m, k);relative = 'inputs/' + data['id'] + '.json'
                with (out / relative).open('x') as f: json.dump(data, f, indent=2);f.write('\n')
                jobs.append(dict(id=data['id'] + '_lazy', input=relative, merge='none', solver='lazy',
                                 expected_decision=data['metadata']['expected_decision'], parameters=data['parameters']))
    for solver, merge in [('direct_full', 'none'), ('lazy', 'transfers')]:
        for n in range(2, 7):
            for m in range(1, n):
                identifier = f'rolling_n{n:02}_m{m:02}_k01'
                job = dict(id=identifier + ('_df' if solver == 'direct_full' else '_e1merged'),
                    input='inputs/' + identifier + '.json', merge=merge, solver=solver,
                    expected_decision='WIN' if merge == 'none' else 'LOSS', parameters=dict(n=n, m=m, k=1))
                if merge == 'transfers':
                    job.update(compare_input=f'inputs/rolling_n{n:02}_m{m:02}_k{n:02}.json', compare_merge='none')
                jobs.append(job)
    e6 = Path(__file__).resolve().parents[1]
    rel = str(out.relative_to(e6))
    config = dict(schema='e6-family-run-v1', family='rolling', version='v1', heap='32g', timeout_seconds=1200,
        trials=1, start_cutoff='2026-09-30T09:39:00+09:00', deadline='2026-09-30T10:00:00+09:00',
        jobs=jobs, frozen_paths=['rolling/gen_rolling.py', 'rolling/validate_endpoints.py',
              'common/witness.schema.json', 'common/SCHEMA.md'],
        endpoint_checks=[['python3', '-B', 'rolling/validate_endpoints.py', rel]],
        preflight_jobs=['rolling_n02_m01_k01_lazy', 'rolling_n02_m01_k02_lazy',
                        'rolling_n02_m01_k01_df', 'rolling_n02_m01_k01_e1merged'])
    with (out / 'config.json').open('x') as f: json.dump(config, f, indent=2);f.write('\n')
    print(json.dumps({'inputs':70, 'jobs':len(jobs), 'out':str(out), 'create_only':True}))


if __name__ == '__main__': main()
