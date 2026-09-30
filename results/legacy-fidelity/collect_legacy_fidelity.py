#!/usr/bin/env python3
"""Pair reference outcomes without treating the two tools as the same game."""
from pathlib import Path
import argparse,csv,json

def yes(v):return v is True or str(v).lower()=='true'
def read_csv(path):
    if not path.is_file():return []
    with path.open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
def collect(root,raw_root=None,config_root=None):
    # Optional locations preserve the deployed collector's columns and ordering.
    # They allow a returned raw tree to be read without copying or rewriting it.
    raw_root=raw_root or root/'raw';config_root=config_root or root/'configs'
    configs={tool:json.loads((config_root/('legacy_fidelity_'+tool+'.json')).read_text()) for tool in ('published','fork')}
    results={tool:{(r['model_id'],r['target_id']):r for r in read_csv(raw_root/('legacy_fidelity_'+tool)/'summary.csv')} for tool in configs}
    rows=[]
    for model in configs['published']['models']:
        key=(model['id'],model['target_ids'][0]);r=dict(model_id=key[0],target_id=key[1],condition=model['factors']['condition'],comparison_scope='reference_tools_not_identical_games')
        decisions=[]
        for tool in configs:
            v=results[tool].get(key,{})
            status=v.get('stage1_status','NOT_RUN')
            valid=status in {'SUCCESS','UNREALIZABLE'} and not yes(v.get('invalid',False)) and not yes(v.get('inconsistent',False))
            decision={'SUCCESS':'WIN','UNREALIZABLE':'LOSS'}.get(status,'UNDECIDED') if valid else 'UNDECIDED'
            decisions.append(decision)
            r.update({tool+'_stage1_status':status,tool+'_decision':decision,tool+'_statuses':v.get('statuses',''),tool+'_invalid':v.get('invalid',''),tool+'_inconsistent':v.get('inconsistent',''),tool+'_valid_repetitions':v.get('completed_valid_repetitions',''),tool+'_states':v.get('output_policy_states',''),tool+'_transitions':v.get('output_policy_transitions','')})
            full=yes(v.get('timing_summary_eligible',False))
            for metric in ['elapsed_monotonic_seconds','solver_time_ms','peak_rss_bytes']:
                for stat in ['median','min','max']:
                    field=metric+'_'+stat;r[tool+'_'+field]=v.get(field,'') if full else ''
            r[tool+'_internal_time_scope']=v.get('measurement_scope','')
        r['decision_agreement']='UNDECIDED' if 'UNDECIDED' in decisions else 'MATCH' if len(set(decisions))==1 else 'MISMATCH'
        rows.append(r)
    assert len(rows)==21
    return rows

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--raw-root',type=Path);p.add_argument('--config-root',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
    rows=collect(a.root,a.raw_root,a.config_root);out=a.output or a.root/'raw/legacy_fidelity_comparison.csv';out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    print(str(out)+': '+str({k:sum(r['decision_agreement']==k for r in rows) for k in ['MATCH','MISMATCH','UNDECIDED']}))
if __name__=='__main__':main()
