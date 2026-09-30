#!/usr/bin/env python3
"""Audit observed certificates against DB physical protocol; write derived tables."""
import csv
import importlib.util
import json
from pathlib import Path
P=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('db_independent',P/'validate_db_rolling.py')
independent=importlib.util.module_from_spec(spec);spec.loader.exec_module(independent)
F=P/'v2'


def physical(node):return tuple(tuple(x) for x in node['physical'])


def load(job,filename='result.json'):return json.loads((F/'raw/series'/job/filename).read_text())


def audit(job,model):
    result=load(job);model=json.loads(json.dumps(model))
    if result['merge'] in ('transfers','both'):
        for c in model['components']:c['transfer_action']='ablation.merge.transfers'
    proof=load(job,'certificate.json');nodes={n['id']:n for n in proof['states']}
    m=model['parameters']['m'];physical_states={physical(n) for n in nodes.values()};transfer_actions={c['transfer_action'] for c in model['components']}
    checked_edges=0
    for node in nodes.values():
        p=physical(node);local=[q for _,q in p]
        assert sum(q in ('P','E') for q in local)==1
        count=sum(q!='B' for q in local)
        if node['safe']:assert count>=m and node['testers']['ready_budget']==str(count)
        else:assert node['testers']['ready_budget']=='ERROR' and count<m
        expected_goal=all(tag=='NEW' for tag,q in p) and local==['S','P','S'] and not node['pending'] and node['safe']
        assert expected_goal==node['goal']
    if result['decision']=='WIN':
        outgoing={i:[] for i in nodes}
        for source,action,target in proof['strategy_edges']:
            outgoing[source].append((action,target));assert nodes[source]['rank']>nodes[target]['rank'];checked_edges+=1
        for source,edges in outgoing.items():
            node=nodes[source]
            if node['goal']:continue
            assert edges
            selected={a for a,_ in edges}
            enabled_uc={a for a in model['ordinary'] if a not in model['controllable'] and independent.physical_post(model,physical(node),a)}
            assert enabled_uc<=selected
            for action in selected:
                expected=independent.physical_post(model,physical(node),action)
                actual={physical(nodes[t]) for a,t in edges if a==action}
                assert actual==expected
                for a,t in edges:
                    if a!=action:continue
                    assert set(nodes[t]['pending'])==set(node['pending'])-({action} if action in transfer_actions else set())
    elif result['merge']=='transfers' or 'generated_contract_mode' in model:
        assert all(n['safe'] and not n['goal'] for n in nodes.values())
        for node in nodes.values():
            p=physical(node)
            for action in transfer_actions:assert not independent.physical_post(model,p,action)
            for action in model['ordinary']:
                assert independent.physical_post(model,p,action)<=physical_states
                checked_edges+=len(independent.physical_post(model,p,action))
    else:
        assert m==3
        for node in nodes.values():
            if not node['safe']:continue
            p=physical(node)
            for action in transfer_actions:
                for target in independent.physical_post(model,p,action):assert sum(q!='B' for _,q in target)<m
    return dict(status='PASS',job=job,decision=result['decision'],certificate_states=len(nodes),independently_checked_edges=checked_edges,
                leader_or_candidate_invariant=True,physical_ready_budget_for_safe_states=True)


def main():
    config=json.loads((F/'config.json').read_text());audits=[]
    for job in config['jobs']:
        model=json.loads((F/job['input']).read_text())
        audits.append(audit(job['id'],model))
    comparisons=[]
    for m in (2,3):
        fine=load(f'db_n3_m{m}_fine_none_lazy');merged=load(f'db_n3_m{m}_fine_transfers_lazy');all_=load(f'db_n3_m{m}_all_none_lazy');df=load(f'db_n3_m{m}_fine_none_direct_full')
        assert merged['decision']==all_['decision'] and merged['states_discovered']==all_['states_discovered']
        assert all_['game_equivalence']['status']=='PASS' and fine['decision']==df['decision']
        comparisons.append(dict(family='DB-Rolling',n=3,m=m,fine_decision=fine['decision'],merged_decision=merged['decision'],
                                classification='witness' if fine['decision']=='WIN' else 'both_LOSS',fine_states=fine['states_discovered'],
                                direct_full_states=df['states_discovered'],merged_states=merged['states_discovered'],
                                fine_rank=fine['worst_completion_rank'],merged_losing_region=merged['losing_region_states'],
                                generated_merge_equality='PASS',all_post_equality='PASS',
                                loss_reason='The simultaneous secondary-only transfer is disabled throughout the closed losing region because exactly one old member is primary or election candidate.' if m==2 else 'Requiring all three members ready makes every individual transfer unsafe; simultaneous transfer is also disabled by the leader/candidate invariant.'))
    with (F/'tables/comparison.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=comparisons[0]);w.writeheader();w.writerows(comparisons)
    with (F/'tables/db_comparison.tex').open('w') as f:
        f.write('% Constructed maintenance contract; m=3 is a preregistered negative control.\n\\begin{tabular}{rrrrrr}\n\\toprule\n$m$ & Fine & Merged & Lazy states & Full states & Rank \\\\\n\\midrule\n')
        for r in comparisons:f.write(f"{r['m']} & {r['fine_decision']} & {r['merged_decision']} & {r['fine_states']} & {r['direct_full_states']} & {r['fine_rank'] if r['fine_rank'] is not None else '--'} \\\\\n")
        f.write('\\bottomrule\n\\end{tabular}\n')
    (F/'validation/certificate_protocol_audit.json').write_text(json.dumps(dict(status='PASS',audits=audits,comparisons=comparisons),indent=2)+'\n')
    print(json.dumps(dict(status='PASS',cells=len(audits),comparisons=comparisons)))


if __name__=='__main__':main()
