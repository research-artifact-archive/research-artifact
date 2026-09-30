#!/usr/bin/env python3
"""Generate the preregistered Canary v1 inputs; never reads measured results."""
import itertools
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
E6 = HERE.parent
OUT = HERE/'v1'


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        json.dump(obj, stream, indent=2);stream.write('\n')


def lts(states, initial, edges): return dict(states=states, initial=initial, edges=edges)


def generate(n, m, grouped):
    ordinary = [f'{a}_{i}' for i in range(1,n+1) for a in ('serve','reportH','reportB','restart')]
    control = [f'{a}_{i}' for i in range(1,n+1) for a in ('serve','restart')]
    rhos = ['ablation.merge.transfers'] if grouped else [f'rho_{i}' for i in range(1,n+1)]
    components = []
    for i in range(1,n+1):
        components.append(dict(id=f'replica_{i}', old=lts(['H'],'H',[['H',f'serve_{i}','H']]),
            new=lts(['H','HP','BP','B'],'H', [['H',f'serve_{i}','H'],['HP',f'reportH_{i}','H'],
                                          ['BP',f'reportB_{i}','B'],['B',f'restart_{i}','H']]),
            transfer_action=rhos[0] if grouped else rhos[i-1], transfer={'H':['HP','BP']}))
    masks = [x for x in range(1<<n) if x.bit_count() <= n-m]
    name = lambda mask:'b'+format(mask,f'0{n}b')
    changes = []
    for mask in masks:
        for i in range(1,n+1):
            broken = mask | (1<<(i-1));restored = mask & ~(1<<(i-1))
            changes.extend([[name(mask),f'reportB_{i}',name(broken) if broken.bit_count() <= n-m else 'ERR_HEALTH'],
                            [name(mask),f'restart_{i}',name(restored)]])
    tester = dict(states=[name(x) for x in masks]+['ERR_HEALTH'], initial=name(0), errors=['ERR_HEALTH'],
                  alphabet=ordinary+rhos, changes=changes)
    old_physical = [['OLD','H'] for _ in range(n)];new_physical = [['NEW','H'] for _ in range(n)]
    endpoint_lts = lts(['all_healthy'],'all_healthy',[['all_healthy',f'serve_{i}','all_healthy'] for i in range(1,n+1)])
    obj = dict(schema='fg-ducs-witness-v1',id=f'canary_n{n:02d}_m{m:02d}_'+('all' if grouped else 'fine'),
               family='canary',parameters={'n':n,'m':m,'k':n if grouped else 1},ordinary=ordinary,controllable=control,
               components=components, requirements=[dict(id='reported_availability',role='interval',tester=tester,
                   activation={'entries':[{'physical':old_physical,'tester_state':name(0),'residual_state':name(0)}]})],
               precedence=[], endpoints={'old':{'lts':endpoint_lts,'controller':endpoint_lts,
                    'projection':{'all_healthy':{'physical':old_physical,'testers':{}}}},
                    'new':{'lts':endpoint_lts,'controller':endpoint_lts,'loadable':['all_healthy'],
                    'projection':{'all_healthy':{'physical':new_physical,'testers':{},'goal_id':'all_healthy'}}}},
               metadata={'model_version':'v1_reports','physical_health':{'H':True,'HP':True,'BP':False,'B':False},
                         'state_legend':{'H':'healthy, report complete','HP':'healthy, report pending','BP':'broken, report pending','B':'broken, report complete'},
                         'requirement_scope':'reported-health safety; physical safety checked independently on returned WIN certificate',
                         'anchor':'CrowdStrike 2024 preliminary review and technical RCA staged deployment/telemetry practice; not incident reproduction',
                         'restart_scope':'abstract controllable restoration, not a claim that a simple restart repaired the real incident'})
    if grouped: obj['generated_contract_mode'] = 'transfers'
    return obj


def main():
    jobs = []
    for n in range(2,7):
        for m in range(1,n):
            for grouped in (False,True):
                obj = generate(n,m,grouped);save(OUT/'inputs'/(obj['id']+'.json'),obj)
            fine = f'inputs/canary_n{n:02d}_m{m:02d}_fine.json';all_input = f'inputs/canary_n{n:02d}_m{m:02d}_all.json'
            for label, path, merge, solver, expected in [
                ('fine_lazy',fine,'none','lazy','WIN'),('merged_lazy',fine,'transfers','lazy','LOSS'),
                ('all_lazy',all_input,'none','lazy','LOSS'),('fine_df',fine,'none','direct_full','WIN')]:
                jobs.append(dict(id=f'n{n:02d}_m{m:02d}_{label}',input=path,merge=merge,solver=solver,
                                 expected_decision=expected,parameters={'n':n,'m':m,'k':1 if label.startswith('fine') else n},variant=label))
                if label=='merged_lazy':jobs[-1].update(compare_input=all_input,compare_merge='none')
    config = dict(schema='e6-family-run-v1',family='canary',version='v1_reports',heap='32g',timeout_seconds=1200,trials=1,
                  start_cutoff='2026-09-30T09:39:00+09:00',deadline='2026-09-30T10:00:00+09:00',jobs=jobs,
                  frozen_paths=['canary/gen_canary.py','canary/validate_canary.py','canary/analyze_canary.py',
                                'canary/design/v0_literal_unimplemented/README.md','canary/design/v1_reports/README.md',
                                'common/SCHEMA.md','common/witness.schema.json'],
                  endpoint_checks=[['python3','-B','canary/validate_canary.py','canary/v1']],
                  preflight_jobs=['n02_m01_fine_lazy','n02_m01_merged_lazy','n02_m01_all_lazy'],
                  analysis_commands=[['python3','-B','canary/analyze_canary.py','canary/v1']])
    save(OUT/'config.json', config)
    print(json.dumps({'inputs':30,'jobs':len(jobs),'output':str(OUT)}))


if __name__ == '__main__': main()
