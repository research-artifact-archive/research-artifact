#!/usr/bin/env python3
"""Independent endpoint products and physical protocol invariant enumeration."""
import argparse
import collections
import importlib.util
import itertools
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('policy_endpoint_check',ROOT.parent/'rolling/validate_endpoints.py')
checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)


def physical_post(model,physical,action):
    groups=[i for i,c in enumerate(model['components']) if c['transfer_action']==action]
    if groups:
        choices=[]
        for i,(tag,state) in enumerate(physical):
            if i in groups:
                if tag!='OLD':return set()
                choices.append([('NEW',s) for s in model['components'][i]['transfer'].get(state,[])])
            else:choices.append([(tag,state)])
        return set(itertools.product(*choices))
    if not any(action in {a for _,a,_ in c[tag.lower()]['edges']} for c,(tag,state) in zip(model['components'],physical)):return set()
    choices=[]
    for c,(tag,state) in zip(model['components'],physical):
        lts=c[tag.lower()];alphabet={a for _,a,_ in lts['edges']}
        successors={(tag,v) for u,a,v in lts['edges'] if u==state and a==action}
        choices.append(successors if action in alphabet else {(tag,state)})
    return set(itertools.product(*choices))


def physical_check(model):
    initial=tuple((tag,q) for tag,q in model['endpoints']['old']['projection']['q']['physical'])
    queue=collections.deque([initial]);seen={initial};edges=0;transfer_buckets=0;candidate_states=0
    actions=model['ordinary']+list(dict.fromkeys(c['transfer_action'] for c in model['components']))
    while queue:
        state=queue.popleft();local=[q for _,q in state]
        assert sum(q in ('P','E') for q in local)==1, ('leader/candidate invariant',state)
        if 'E' in local:candidate_states+=1
        for action in actions:
            successors=physical_post(model,state,action)
            if successors and action.startswith(('rho_','ablation.merge.')):transfer_buckets+=1
            edges+=len(successors)
            for target in successors:
                if target not in seen:seen.add(target);queue.append(target)
    merged='generated_contract_mode' in model
    if merged:assert transfer_buckets==0, 'Simultaneous transfer unexpectedly enabled'
    else:assert transfer_buckets>0
    return dict(status='PASS',physical_states=len(seen),physical_edges=edges,election_gap_states=candidate_states,
                exactly_one_primary_or_candidate=True,enabled_transfer_buckets=transfer_buckets,
                simultaneous_transfer_never_enabled=transfer_buckets==0 if merged else 'NOT_APPLICABLE')


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--family',type=Path,default=ROOT/'v2');args=p.parse_args()
    records=[]
    for path in sorted((args.family/'inputs').glob('*.json')):
        model=json.loads(path.read_text())
        records.append(dict(input=path.name,endpoints={v:checker.validate(model,v) for v in ('old','new')},
                            physical=physical_check(model)))
    result=dict(status='PASS',records=records,method='Independent Python plant/controller product and all reachable physical transitions; generator and solver not imported.')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result))


if __name__=='__main__':main()
