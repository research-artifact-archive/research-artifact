#!/usr/bin/env python3
"""Read-only raw/certificate checks and Rolling-specific derived handoff tables."""
import csv
import hashlib
import json
from pathlib import Path
import sys


def main():
    family = Path(sys.argv[1]).resolve(); config = json.loads((family / 'config.json').read_text())
    rows = list(csv.DictReader((family / 'summary.csv').open()));by = {r['job_id']:r for r in rows}
    checks = [];failures = [];thresholds = []
    for job in config['jobs']:
        row = by[job['id']]; params = job['parameters'];n,m,k = (params[x] for x in ('n','m','k'))
        if row['decision'] not in ('WIN','LOSS'): continue
        directory = family / 'raw/series' / job['id']
        result = json.loads((directory / 'result.json').read_text());proof = json.loads((directory / 'certificate.json').read_text())
        ready = [sum(q == 'ready' for version,q in state['physical']) for state in proof['states']]
        check = dict(job_id=job['id'], decision=row['decision'], certificate_states=len(proof['states']),
                     minimum_physical_ready=min(ready), expected_threshold=n-m,
                     rank_edges_decrease=None, physical_availability_holds=None)
        if row['decision'] == 'WIN':
            ranks = {s['id']:s['rank'] for s in proof['states']}
            check['rank_edges_decrease'] = all(ranks[t] < ranks[s] for s,a,t in proof['strategy_edges'])
            check['physical_availability_holds'] = min(ready) >= m
            if not check['rank_edges_decrease'] or not check['physical_availability_holds']:failures.append(job['id']+': invalid rank/physical safety')
            if max(ranks.values()) != result['worst_completion_rank']:failures.append(job['id']+': maximum rank differs')
        else:
            summary = result['loss_summary']
            check['certificate_unsafe_states'] = sum(not s['safe'] for s in proof['states'])
            if check['certificate_unsafe_states'] != summary['unsafe_region_states']:failures.append(job['id']+': unsafe count differs')
            check['root_updates_with_unsafe_outcomes'] = [b['action'] for e in summary['initial_examples'] for b in e['enabled_action_buckets'] if b['update'] and b['unsafe_outcomes']]
            check['physical_below_m_states'] = sum(count < m for count in ready)
            check['mechanism_sentence'] = (f'The checked losing certificate contains {check["physical_below_m_states"]} states with fewer than {m} ready replicas; '
                f'the sampled initial-root update buckets with unsafe outcomes are {check["root_updates_with_unsafe_outcomes"]}. '
                'This is certificate evidence of the availability gap in the generated grouped contract, not a claim about deployment prevalence.')
        checks.append(check)
    for n in range(2,7):
        for m in range(1,n):
            fine = by[f'rolling_n{n:02}_m{m:02}_k01_lazy']
            df = by[f'rolling_n{n:02}_m{m:02}_k01_df']
            merged = by[f'rolling_n{n:02}_m{m:02}_k01_e1merged']
            generated = by[f'rolling_n{n:02}_m{m:02}_k{n:02}_lazy']
            compared = merged['decision'] in ('WIN','LOSS') and generated['decision'] in ('WIN','LOSS')
            if compared:
                for key in ['decision','states_discovered','successor_queries','worst_completion_rank','losing_region_states']:
                    if merged[key] != generated[key]:failures.append(f'n{n}m{m}: E1/generated group differ in {key}')
                r = json.loads((family/merged['result_file']).read_text())
                if r.get('game_equivalence',{}).get('status')!='PASS':failures.append(f'n{n}m{m}: full Post comparison absent')
            if fine['decision'] in ('WIN','LOSS') and df['decision'] in ('WIN','LOSS'):
                if fine['decision'] != df['decision']:failures.append(f'n{n}m{m}: Lazy/DF decision differs')
                if int(fine['states_discovered']) > int(df['states_discovered']):failures.append(f'n{n}m{m}: Lazy explored more than DF')
            for k in range(1,n+1):
                row=by[f'rolling_n{n:02}_m{m:02}_k{k:02}_lazy']
                thresholds.append(dict(n=n,m=m,k=k,group_sizes=json.dumps([min(k,n-i) for i in range(0,n,k)]),
                    expected='WIN' if k<=n-m else 'LOSS', observed=row['decision'],
                    states=row['states_discovered'],queries=row['successor_queries'],rank=row['worst_completion_rank'],losing_region=row['losing_region_states']))
                if row['decision'] in ('WIN','LOSS') and row['decision'] != ('WIN' if k<=n-m else 'LOSS'):failures.append(f'n{n}m{m}k{k}: threshold mismatch')
    table=family/'tables/threshold.csv'
    with table.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(thresholds[0]));writer.writeheader();writer.writerows(thresholds)
    report=dict(status='PASS' if not failures else 'FAIL',issues=failures,checked_certificates=len(checks),
                scheduled=100,measurements_completed=sum(r['decision'] in ('WIN','LOSS') for r in rows),
                expected_threshold_scope='Hypothesis checked against actual measurements; no expected value fills an unmeasured cell.',checks=checks)
    (family/'validation/rolling_results.json').write_text(json.dumps(report,indent=2)+'\n')
    if by['rolling_n02_m01_k01_lazy']['decision']=='WIN':
        proof=json.loads((family/'raw/series/rolling_n02_m01_k01_lazy/certificate.json').read_text())
        nodes={s['id']:s for s in proof['states']};q=next(s['id'] for s in proof['states'] if s['initial']);path=[dict(state=nodes[q])]
        while not nodes[q]['goal']:
            edge=next(e for e in proof['strategy_edges'] if e[0]==q);q=edge[2];path.append(dict(action=edge[1],state=nodes[q]))
        (family/'validation/me_path.json').write_text(json.dumps(dict(scope='One path in the checked policy; all policy outcomes are retained in certificate.json.',path=path),indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='checks'}));return bool(failures)


if __name__=='__main__':raise SystemExit(main())
