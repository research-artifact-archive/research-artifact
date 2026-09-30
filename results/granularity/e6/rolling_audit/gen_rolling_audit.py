#!/usr/bin/env python3
"""Literal Rolling(2,1) plus one audit requirement pair; no measurement input."""
import copy
import hashlib
import itertools
import json
from pathlib import Path
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;E6=HERE.parent;OUT=HERE/'v1'
SOURCE=E6/'rolling/v1/inputs/rolling_n02_m01_k01.json'


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as f:json.dump(value,f,indent=2);f.write('\n')


def tester(alphabet,log):
    changes=[[q,log,'logged'] for q in ('unlogged','logged')]
    for a in ('serve_1','serve_2'):
        changes += [['unlogged',a,'ERR_AUDIT'],['logged',a,'unlogged']]
    return dict(states=['unlogged','logged','ERR_AUDIT'],initial='unlogged',errors=['ERR_AUDIT'],alphabet=alphabet,changes=changes)


def fine_model(base,base_sha):
    model=copy.deepcopy(base);model['id']='rolling_audit_literal_fine';model['family']='rolling_audit'
    model['parameters']={'n':2,'m':1,'k':1,'audit_pairs':1}
    start='start_audit_new';stop='stop_audit_old'
    model['ordinary']+=['log_old','log_new'];model['controllable']+=['log_old','log_new']
    for c in model['components']:
        for version in ('old','new'):
            c[version]['edges'] += [[q,a,q] for q in c[version]['states'] for a in ('log_old','log_new')]
    alphabet=model['ordinary']+[c['transfer_action'] for c in model['components']]+[start,stop]
    old=dict(id='audit_old',role='old',tester=tester(alphabet,'log_old'),update_action=stop)
    entries=[]
    for physical in itertools.product([['OLD','ready'],['NEW','booting'],['NEW','ready']],repeat=2):
        entries.append(dict(physical=list(physical),tester_state='unlogged',residual_state='unlogged'))
    new=dict(id='audit_new',role='new',tester=tester(alphabet,'log_new'),update_action=start,activation={'entries':entries})
    safe=[(r,o,s) for r in (1,2) for o,s in ((1,0),(1,1),(0,1))]
    name=lambda q:f'ready{q[0]}_old{q[1]}_new{q[2]}'
    changes=[]
    for q in safe:
        for action in alphabet:
            r,o,s=q
            if action.startswith('rho_'):r-=1
            elif action.startswith('ready_'):r=min(2,r+1)
            elif action==start:s=1
            elif action==stop:o=0
            target=(r,o,s)
            if target!=q:changes.append([name(q),action,name(target) if target in safe else 'ERR_INTERVAL'])
    interval=dict(id='availability_audit_coverage',role='interval',tester=dict(states=[name(q) for q in safe]+['ERR_INTERVAL'],
        initial=name((2,1,0)),errors=['ERR_INTERVAL'],alphabet=alphabet,changes=changes),
        activation={'entries':[dict(physical=[['OLD','ready'],['OLD','ready']],tester_state=name((2,1,0)),residual_state=name((2,1,0)))]})
    model['requirements']=[interval,old,new];model['precedence']=[]
    for version in ('old','new'):
        states=['unlogged','logged'];log='log_'+version
        graph=dict(states=states,initial='unlogged',edges=[['unlogged',log,'logged']]+[['logged',a,'unlogged'] for a in ('serve_1','serve_2')])
        controller=copy.deepcopy(graph);controller['states'].append('alphabet_only')
        controller['edges'] += [['alphabet_only',a,'alphabet_only'] for a in model['ordinary']]
        projection={q:dict(physical=[[version.upper(),'ready'] for _ in range(2)],testers={'audit_'+version:q}) for q in states}
        ep=dict(lts=graph,controller=controller,projection=projection)
        if version=='new':
            ep['loadable']=states
            for q in states:projection[q]['goal_id']='new_'+q
        model['endpoints'][version]=ep
    model['metadata']=dict(model_version='literal_v1',base_input='rolling/v1/inputs/rolling_n02_m01_k01.json',base_sha256=base_sha,
        physical_plant='Rolling local states and existing transitions retained; global log_old/log_new self-loops added at every local state as external log-sink action abstractions.',audit_semantics='One old/new audit pair, each requiring its matching log before the next serve; one availability x audit-coverage interval tester forbids both rules being inactive.',
        audit_scope='Finite event-order and activation-coverage contract; no claim about persisted log delivery or a particular logging implementation.',
        initializer='Uniform unlogged on all nine versioned physical products; no additional activation guard.',
        boundary_merge_expectation='One start and one stop are only renamed; no boundary-granularity witness is expected.',
        expected_decision='WIN',mechanism='M2 plus one audit coverage handoff',anchor='Rolling availability practice plus explicitly constructed audit activation coverage.')
    return model


def grouped(fine,mode):
    model=copy.deepcopy(fine);model['id']='rolling_audit_literal_generated_'+mode;model['generated_contract_mode']=mode
    old_actions=list(dict.fromkeys(fine['ordinary']+[c['transfer_action'] for c in fine['components']]+[r['update_action'] for r in fine['requirements'] if 'update_action' in r]))
    mapping={a:a for a in old_actions}
    if mode in ('transfers','both'):
        model['parameters']['k']=2
        for c in fine['components']:mapping[c['transfer_action']]='ablation.merge.transfers'
    if mode in ('boundaries','both'):
        mapping['start_audit_new']='ablation.merge.starts';mapping['stop_audit_old']='ablation.merge.stops'
    for c in model['components']:c['transfer_action']=mapping[c['transfer_action']]
    groups={}
    for action in old_actions:groups.setdefault(mapping[action],[]).append(action)
    for req,original in zip(model['requirements'],fine['requirements']):
        if 'update_action' in req:req['update_action']=mapping[req['update_action']]
        t=original['tester'];changes={(q,a):z for q,a,z in t['changes']};out=[]
        alphabet=[label for label,members in groups.items() if any(a in t['alphabet'] for a in members)]
        for q in t['states']:
            for label in alphabet:
                z=q
                for action in groups[label]:z=changes.get((z,action),z)
                if z!=q:out.append([q,label,z])
        req['tester']['alphabet']=alphabet;req['tester']['changes']=out
    model['precedence']=[[mapping[a],mapping[b]] for a,b in fine['precedence']]
    model['metadata']['expected_decision']='LOSS' if mode in ('transfers','both') else 'WIN'
    return model


def main():
    content=SOURCE.read_bytes();reference=OUT/'reference'/SOURCE.name
    reference.parent.mkdir(parents=True,exist_ok=True)
    with reference.open('xb') as f:f.write(content)
    base=json.loads(content);fine=fine_model(base,hashlib.sha256(content).hexdigest())
    save(OUT/'inputs/fine.json',fine)
    for mode in ('transfers','boundaries','both'):save(OUT/f'inputs/generated_{mode}.json',grouped(fine,mode))
    jobs=[]
    for mode in ('none','transfers','boundaries','both'):
        job=dict(id='fine_'+mode+'_lazy',input='inputs/fine.json',merge=mode,solver='lazy',expected_decision='LOSS' if mode in ('transfers','both') else 'WIN',parameters={'n':2,'m':1,'audit_pairs':1})
        if mode!='none':job.update(compare_input=f'inputs/generated_{mode}.json',compare_merge='none')
        jobs.append(job)
    jobs.append(dict(id='fine_none_df',input='inputs/fine.json',merge='none',solver='direct_full',expected_decision='WIN',parameters={'n':2,'m':1,'audit_pairs':1}))
    for mode in ('transfers','boundaries','both'):
        jobs.append(dict(id='generated_'+mode+'_lazy',input=f'inputs/generated_{mode}.json',merge='none',solver='lazy',expected_decision='LOSS' if mode in ('transfers','both') else 'WIN',parameters={'n':2,'m':1,'audit_pairs':1}))
    save(OUT/'config.json',dict(schema='e6-family-run-v1',family='rolling_audit',version='literal_v1',heap='32g',timeout_seconds=1200,trials=1,
        start_cutoff='2026-09-30T09:39:00+09:00',deadline='2026-09-30T10:00:00+09:00',jobs=jobs,
        frozen_paths=['rolling_audit/gen_rolling_audit.py','rolling_audit/validate_rolling_audit.py','rolling_audit/analyze_rolling_audit.py','rolling_audit/README.md',
                      'rolling_audit/v1/reference/'+SOURCE.name,'common/SCHEMA.md','common/witness.schema.json'],
        endpoint_checks=[['python3','-B','rolling_audit/validate_rolling_audit.py','rolling_audit/v1']],
        preflight_jobs=['fine_none_lazy','fine_transfers_lazy','fine_boundaries_lazy'],
        analysis_commands=[['python3','-B','rolling_audit/analyze_rolling_audit.py','rolling_audit/v1']]))
    print(json.dumps({'inputs':4,'jobs':len(jobs),'base_sha256':hashlib.sha256(content).hexdigest()}))


if __name__=='__main__':main()
