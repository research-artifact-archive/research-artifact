#!/usr/bin/env python3
"""Independent source/endpoint check; does not import the Canary generator or Java."""
from collections import deque
import datetime as dt
import hashlib
import itertools
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True


def transitions(lts):
    states = lts['states'];assert len(set(states)) == len(states) and lts['initial'] in states
    edges = [tuple(e) for e in lts['edges']];assert len(set(edges)) == len(edges)
    assert all(len(e)==3 and e[0] in states and e[2] in states for e in edges)
    return {(q,a):{t for s,b,t in edges if (s,b)==(q,a)} for q in states for a in {e[1] for e in edges}}


def check_endpoint(obj, version):
    ep = obj['endpoints'][version];controller = ep['controller'];ct = transitions(controller)
    local = [c[version] for c in obj['components']];tables = [transitions(x) for x in local]
    alphabets = [{e[1] for e in x['edges']} for x in local]
    root = (tuple(x['initial'] for x in local), controller['initial'])
    reached = {root};todo = deque([root]);edges = set()
    while todo:
        q,cq = todo.popleft()
        for a in obj['ordinary']:
            cps = ct.get((cq,a),set())
            targets = [tables[i].get((s,a),set()) if a in alphabets[i] else {s} for i,s in enumerate(q)]
            if not cps or not all(targets):continue
            for p in itertools.product(*targets):
                for cc in cps:
                    nxt = (p,cc);edges.add(((q,cq),a,nxt))
                    if nxt not in reached:reached.add(nxt);todo.append(nxt)
    declared = ep['lts'];transitions(declared)
    # Both endpoint controllers have one state, so every physical projection determines the product state.
    assert len(controller['states']) == 1
    projection = {k:(tuple(v[1] for v in p['physical']),controller['initial']) for k,p in ep['projection'].items()}
    assert set(projection)==set(declared['states']) and set(projection.values())==reached
    assert projection[declared['initial']]==root
    assert {(projection[s],a,projection[t]) for s,a,t in declared['edges']}==edges
    assert all(p['testers']=={} for p in ep['projection'].values())
    assert all(all(v==version.upper() for v,s in p['physical']) for p in ep['projection'].values())
    assert all(all(s=='H' for s in q) for q,c in reached)
    if version=='new':assert set(ep['loadable'])==set(declared['states'])
    return {'reachable_product_states':len(reached),'product_edges':len(edges),'all_physically_healthy':True}


def check(path):
    obj = json.loads(path.read_text());n,m,k = [obj['parameters'][p] for p in ('n','m','k')]
    assert 2<=n<=6 and 1<=m<n and k in (1,n)
    assert len(obj['components'])==n and obj['precedence']==[]
    ordinary = {f'{a}_{i}' for i in range(1,n+1) for a in ('serve','reportH','reportB','restart')}
    controls = {f'{a}_{i}' for i in range(1,n+1) for a in ('serve','restart')}
    assert set(obj['ordinary'])==ordinary and len(obj['ordinary'])==len(ordinary)
    assert set(obj['controllable'])==controls and len(obj['controllable'])==len(controls)
    for i,c in enumerate(obj['components'],1):
        assert c['id']==f'replica_{i}' and c['transfer']=={'H':['HP','BP']}
        assert c['old']=={'states':['H'],'initial':'H','edges':[['H',f'serve_{i}','H']]}
        transitions(c['new']);assert set(c['new']['states'])=={'H','HP','BP','B'} and c['new']['initial']=='H'
        assert {tuple(e) for e in c['new']['edges']}=={('H',f'serve_{i}','H'),('HP',f'reportH_{i}','H'),('BP',f'reportB_{i}','B'),('B',f'restart_{i}','H')}
        assert c['transfer_action']==(f'rho_{i}' if k==1 else 'ablation.merge.transfers')
    assert obj.get('generated_contract_mode')==('transfers' if k==n else None)
    assert len(obj['requirements'])==1
    requirement = obj['requirements'][0];tester = requirement['tester']
    assert requirement['id']=='reported_availability' and requirement['role']=='interval'
    safe_masks = {i for i in range(1<<n) if i.bit_count()<=n-m}
    masks = {f'b{i:0{n}b}':i for i in safe_masks};assert set(tester['states'])==set(masks)|{'ERR_HEALTH'}
    assert tester['initial']==f'b{0:0{n}b}' and tester['errors']==['ERR_HEALTH']
    updates={c['transfer_action'] for c in obj['components']};assert set(tester['alphabet'])==ordinary|updates
    changes={(s,a):t for s,a,t in tester['changes']};assert len(changes)==len(tester['changes'])
    for s,mask in masks.items():
        for a in tester['alphabet']:
            if a.startswith('reportB_'): target=mask|(1<<(int(a.split('_')[1])-1))
            elif a.startswith('restart_'):target=mask&~(1<<(int(a.split('_')[1])-1))
            else:target=mask
            expected=f'b{target:0{n}b}' if target in safe_masks else 'ERR_HEALTH'
            assert changes.get((s,a),s)==expected,(s,a)
    assert requirement['activation']['entries']==[{'physical':[['OLD','H'] for _ in range(n)],'tester_state':tester['initial'],'residual_state':tester['initial']}]
    assert 'residual' not in requirement['activation']
    outcomes=set(itertools.product(*[c['transfer']['H'] for c in obj['components']]))
    assert len(outcomes)==2**n and ('BP',)*n in outcomes and ('HP',)*n in outcomes
    return dict(input=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),n=n,m=m,k=k,
                endpoint_old=check_endpoint(obj,'old'),endpoint_new=check_endpoint(obj,'new'),
                all_at_once_product_outcomes=len(outcomes),all_broken_in_product=True,
                finite_uc_reports='Each report consumes exactly one HP/BP state; no report self-loop.',status='PASS')


def main():
    family = Path(sys.argv[1]).resolve();reports=[];issues=[]
    paths = sorted((family/'inputs').glob('*.json'))
    if len(paths)!=30:issues.append(f'Expected 30 fixed inputs, found {len(paths)}.')
    for path in paths:
        try: reports.append(check(path))
        except Exception as exc:issues.append({'input':path.name,'error':type(exc).__name__+': '+str(exc)})
    # Compare the fine and coarse contracts independently, without invoking E1 merging.
    for n in range(2,7):
        for m in range(1,n):
            try:
                a=json.loads((family/f'inputs/canary_n{n:02d}_m{m:02d}_fine.json').read_text())
                b=json.loads((family/f'inputs/canary_n{n:02d}_m{m:02d}_all.json').read_text())
                a['id']=b['id'];a['parameters']['k']=n;a['generated_contract_mode']='transfers'
                for c in a['components']:c['transfer_action']='ablation.merge.transfers'
                a['requirements'][0]['tester']['alphabet']=a['ordinary']+['ablation.merge.transfers']
                assert a==b,'Fine/coarse changes exceed declared event grouping.'
            except Exception as exc:issues.append({'n':n,'m':m,'error':type(exc).__name__+': '+str(exc)})
    result=dict(status='FAIL' if issues else 'PASS',at=dt.datetime.now(dt.timezone.utc).isoformat(),inputs=len(reports),reports=reports,issues=issues,
                scope='Independent explicit plant/controller endpoint product, local relation/monitor checks, finite reporting, and fine/coarse grouping. Not a substitute for synthesis.')
    target=family/'validation';target.mkdir(parents=True,exist_ok=True)
    timestamp=dt.datetime.now().strftime('%Y%m%dT%H%M%S%f')
    (target/f'endpoints-{timestamp}.json').write_text(json.dumps(result,indent=2)+'\n')
    (target/'endpoints.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'inputs':result['inputs'],'issues':issues}));return bool(issues)


if __name__=='__main__':raise SystemExit(main())
