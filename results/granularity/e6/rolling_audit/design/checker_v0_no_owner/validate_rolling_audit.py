#!/usr/bin/env python3
"""Independent RollingAudit endpoint, physical-extension and monitor audit."""
from collections import defaultdict,deque
import itertools,json,datetime
from pathlib import Path
import sys
sys.dont_write_bytecode=True


def step(t,q,a):return next((z for s,b,z in t['changes'] if (s,b)==(q,a)),q)
def index(lts):
    assert lts['initial'] in lts['states'] and len(set(lts['states']))==len(lts['states'])
    assert len({tuple(e) for e in lts['edges']})==len(lts['edges'])
    result=defaultdict(set)
    for s,a,t in lts['edges']:
        assert s in lts['states'] and t in lts['states'];result[s,a].add(t)
    return result


def endpoint(model,version):
    ep=model['endpoints'][version];controller=ep['controller'];ct=index(controller)
    c_alpha={a for s,a,t in controller['edges']};assert c_alpha==set(model['ordinary'])
    plants=[c[version] for c in model['components']];pts=[index(x) for x in plants];alphas=[{a for s,a,t in x['edges']} for x in plants]
    reqs=[r for r in model['requirements'] if r['role']==version];assert len(reqs)==1
    initial=(tuple(x['initial'] for x in plants),controller['initial'],tuple(r['tester']['initial'] for r in reqs))
    seen={initial};todo=deque([initial]);edges=set()
    while todo:
        q,c,mon=todo.popleft();enabled=0
        assert all(s not in r['tester']['errors'] for r,s in zip(reqs,mon))
        for action in model['ordinary']:
            targets=[pts[i][q[i],action] if action in alphas[i] else {q[i]} for i in range(len(q))]
            if not all(targets):continue
            if not ct[c,action]:assert action in model['controllable'];continue
            enabled+=1
            for p,cc in itertools.product(itertools.product(*targets),ct[c,action]):
                nxt=(p,cc,tuple(step(r['tester'],s,action) for r,s in zip(reqs,mon)))
                edges.add(((q,c,mon),action,nxt))
                if nxt not in seen:seen.add(nxt);todo.append(nxt)
        assert enabled,'Deadlocked endpoint'
    declared={s:(tuple(v for tag,v in p['physical']),s,tuple(p['testers'][r['id']] for r in reqs)) for s,p in ep['projection'].items()}
    assert set(declared.values())==seen
    assert {(declared[s],a,declared[t]) for s,a,t in ep['lts']['edges']}==edges
    assert declared[ep['lts']['initial']]==initial
    assert all(all(tag==version.upper() and q=='ready' for tag,q in p['physical']) for p in ep['projection'].values())
    if version=='new':assert set(ep['loadable'])==set(declared)
    return dict(states=len(seen),edges=len(edges),uncontrollable_closed=True,nonblocking=True,safe=True)


def main():
    directory=Path(sys.argv[1]).resolve();fine=json.loads((directory/'inputs/fine.json').read_text())
    base=json.loads((directory/'reference/rolling_n02_m01_k01.json').read_text())
    issues=[];report={}
    try:
        assert fine['precedence']==[]
        assert len(fine['components'])==2 and len(fine['requirements'])==3
        assert sorted(r['role'] for r in fine['requirements'])==['interval','new','old']
        for a,b in zip(fine['components'],base['components']):
            copied=json.loads(json.dumps(a))
            for version in ('old','new'):
                extra=[e for e in copied[version]['edges'] if e[1] in ('log_old','log_new')]
                assert {tuple(e) for e in extra}=={(q,action,q) for q in copied[version]['states'] for action in ('log_old','log_new')}
                copied[version]['edges']=[e for e in copied[version]['edges'] if e not in extra]
            assert copied==b,'Physical extension exceeded the declared log self-loops.'
        interval=next(r for r in fine['requirements'] if r['role']=='interval')['tester']
        safe={(r,o,n) for r in (1,2) for o,n in ((1,0),(1,1),(0,1))}
        name=lambda q:f'ready{q[0]}_old{q[1]}_new{q[2]}'
        for q in safe:
            for action in interval['alphabet']:
                r,o,n=q
                if action.startswith('rho_'):r-=1
                elif action.startswith('ready_'):r=min(2,r+1)
                elif action=='start_audit_new':n=1
                elif action=='stop_audit_old':o=0
                target=(r,o,n);assert step(interval,name(q),action)==(name(target) if target in safe else 'ERR_INTERVAL')
        assert step(interval,interval['initial'],'stop_audit_old')=='ERR_INTERVAL'
        assert step(interval,step(interval,interval['initial'],'start_audit_new'),'stop_audit_old')=='ready2_old0_new1'
        new=next(r for r in fine['requirements'] if r['role']=='new');entries=new['activation']['entries']
        expected=set(itertools.product((('OLD','ready'),('NEW','booting'),('NEW','ready')),repeat=2))
        assert {tuple(map(tuple,e['physical'])) for e in entries}==expected and len(entries)==9
        assert all(e['tester_state']==e['residual_state']=='unlogged' for e in entries)
        for r in fine['requirements']:
            t=r['tester'];assert len({(s,a) for s,a,z in t['changes']})==len(t['changes'])
            assert set(t['errors'])<=set(t['states'])
            for q in t['states']:
                assert step(t,step(t,q,'rho_1'),'rho_2')==step(t,step(t,q,'rho_2'),'rho_1')
            if r['role'] in ('old','new'):
                assert step(t,'unlogged','serve_1')=='ERR_AUDIT'
                assert step(t,step(t,'unlogged','log_'+r['role']),'serve_1')=='unlogged'
        report['endpoints']={v:endpoint(fine,v) for v in ('old','new')}
        comparisons=[]
        for mode in ('transfers','boundaries','both'):
            coarse=json.loads((directory/f'inputs/generated_{mode}.json').read_text())
            assert coarse['generated_contract_mode']==mode and coarse['precedence']==[]
            mapping={a:a for a in fine['ordinary']+['rho_1','rho_2','start_audit_new','stop_audit_old']}
            if mode in ('transfers','both'):mapping.update(rho_1='ablation.merge.transfers',rho_2='ablation.merge.transfers')
            if mode in ('boundaries','both'):mapping.update(start_audit_new='ablation.merge.starts',stop_audit_old='ablation.merge.stops')
            for f,c in zip(fine['components'],coarse['components']):
                normalized=json.loads(json.dumps(c));normalized['transfer_action']=f['transfer_action'];assert normalized==f
            groups={}
            for a,label in mapping.items():groups.setdefault(label,[]).append(a)
            for f,c in zip(fine['requirements'],coarse['requirements']):
                for q in f['tester']['states']:
                    for label,actions in groups.items():
                        z=q
                        for a in actions:z=step(f['tester'],z,a)
                        assert step(c['tester'],q,label)==z
                if 'activation' in f:assert f['activation']==c['activation']
            assert fine['endpoints']==coarse['endpoints']
            comparisons.append(dict(mode=mode,status='PASS',boundary_only_is_renaming=mode=='boundaries'))
        report['generated_grouping']=comparisons
    except Exception as exc:issues.append(type(exc).__name__+': '+str(exc))
    result=dict(status='FAIL' if issues else 'PASS',at=datetime.datetime.now(datetime.timezone.utc).isoformat(),issues=issues,**report,
                scope='Independent endpoint synchronous products, declared append-only log extension, full nine-state initializer, interval/audit requirements, and generated event groups; no synthesis.')
    folder=directory/'validation';folder.mkdir(parents=True,exist_ok=True)
    (folder/('design-'+datetime.datetime.now().strftime('%Y%m%dT%H%M%S%f')+'.json')).write_text(json.dumps(result,indent=2)+'\n')
    (folder/'design_latest.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result));return bool(issues)


if __name__=='__main__':raise SystemExit(main())
