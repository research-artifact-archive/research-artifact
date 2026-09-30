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


def tester(alphabet):
    return dict(states=['ok','ERR_AUDIT'],initial='ok',errors=['ERR_AUDIT'],alphabet=alphabet,changes=[])


def fine_model(base,base_sha):
    model=copy.deepcopy(base);model['id']='rolling_audit_literal_fine';model['family']='rolling_audit'
    model['parameters']={'n':2,'m':1,'k':1,'audit_pairs':1}
    start='start_audit_new';stop='stop_audit_old'
    alphabet=model['ordinary']+[c['transfer_action'] for c in model['components']]+[start,stop]
    old=dict(id='audit_old',role='old',tester=tester(alphabet),update_action=stop)
    entries=[]
    for physical in itertools.product([['OLD','ready'],['NEW','booting'],['NEW','ready']],repeat=2):
        entries.append(dict(physical=list(physical),tester_state='ok',residual_state='ok'))
    new=dict(id='audit_new',role='new',tester=tester(alphabet),update_action=start,activation={'entries':entries})
    model['requirements'] += [old,new]
    model['precedence']=[[start,stop]]
    for ep in model['endpoints']['old']['projection'].values():ep['testers']={'audit_old':'ok'}
    for ep in model['endpoints']['new']['projection'].values():ep['testers']={'audit_new':'ok'}
    model['metadata']=dict(model_version='literal_v1',base_input='rolling/v1/inputs/rolling_n02_m01_k01.json',base_sha256=base_sha,
        physical_plant='Identical to the fixed Rolling(2,1,k1) input.',audit_semantics='One old/new audit-rule activation pair; strict start-new-before-stop-old precedence forbids an activation gap.',
        audit_scope='Activation coverage only; no claim about successful log delivery or a particular logging implementation.',
        initializer='Uniform ok on all nine versioned physical products; no additional activation guard.',
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
