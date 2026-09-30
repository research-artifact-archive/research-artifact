#!/usr/bin/env python3
"""Validate and tabulate every cell, including non-completions; never modify inputs or raw."""
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
FIELDS=['n']+[v+'_'+field for v in ('none_lazy','transfers_lazy','boundaries_lazy','both_lazy','none_direct_full') for field in ('status','states','queries','buckets','rank','losing_region')]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(path,text):
    with path.open('x') as f:f.write(text)
def latex_value(value):return value if value else '--'
def main():
    rows=list(csv.DictReader((HERE/'summary.csv').open()));assert len(rows)==45
    original=list(csv.DictReader((HERE.parent/'e4_2/summary.csv').open()));assert len(original)==45
    frozen=json.loads((HERE/'build/frozen_manifest.json').read_text())
    for path,digest in frozen['files'].items():assert sha(HERE/path)==digest,path
    assert sha(HERE.parents[1]/'ablation_20260928/jars/e1.jar')==frozen['jar_sha256']
    wide=[];issues=[]
    for n in range(2,11):
        line={'n':n};by_variant={}
        for row in rows:
            if int(row['n'])!=n:continue
            key=row['merge']+'_'+row['solver'];by_variant[key]=row
            folder=HERE/'raw/series'/f"n{n:02d}_{key}"
            if row['status']!='NOT_RUN_DEADLINE':
                completion=json.loads((folder/'completion.json').read_text());assert completion['status']==row['status']
            assert row['input_sha256']==sha(HERE/'inputs'/f'cell_n{n:02d}.json')
            if row['decision']:
                data=json.loads((folder/'result.json').read_text());assert data['certificate_checker']=='PASS'
                for field in ('decision','states_discovered','successor_queries','materialized_transitions','worst_completion_rank','losing_region_states'):
                    assert row[field]==('' if data.get(field) is None else str(data[field])),(n,key,field)
                if row['decision']=='WIN':assert data['link_checker']=='PASS'
            for output,source in [('status','status'),('states','states_discovered'),('queries','successor_queries'),('buckets','enabled_buckets'),('rank','worst_completion_rank'),('losing_region','losing_region_states')]:line[key+'_'+output]=row[source]
        assert len(by_variant)==5
        for left,right in [('none_lazy','boundaries_lazy'),('transfers_lazy','both_lazy')]:
            for field in ('status','states_discovered','successor_queries','worst_completion_rank'):
                if by_variant[left][field]!=by_variant[right][field]:issues.append({'n':n,'left':left,'right':right,'field':field})
        if by_variant['none_lazy']['decision'] and by_variant['none_direct_full']['decision'] and by_variant['none_lazy']['decision']!=by_variant['none_direct_full']['decision']:issues.append({'n':n,'issue':'Lazy/DF decision disagreement'})
        wide.append(line)
    with (HERE/'summary_wide.csv').open('x',newline='') as f:
        writer=csv.DictWriter(f,FIELDS);writer.writeheader();writer.writerows(wide)
    s1=[r'% Corrected representation series, each cell one trial. Initial series retained: 9 WIN, 6 LOSS, 30 pre-solver input ERROR.',r'\begin{tabular}{rcccc}',r'\toprule',r'$n$ & None & Transfers & Boundaries & Both \\',r'\midrule']
    for r in wide:
        vals=[str(r['n'])]
        for v in ('none_lazy','transfers_lazy','boundaries_lazy','both_lazy'):
            status=r[v+'_status'];metric=r[v+'_rank'] if status=='WIN' else r[v+'_losing_region']
            vals.append(status+((' / '+metric) if metric else ''))
        s1.append(' & '.join(vals)+r' \\')
    s1 += [r'\bottomrule',r'\end{tabular}',r'% WIN / rank: returned certificate maximum rank. LOSS / size: discovered losing-certificate region.',r'% Neither metric is asserted optimal or the whole-game maximal losing set.']
    write(HERE/'table_s1_cell_ring.tex','\n'.join(s1)+'\n')
    s4=[r'% Fixed none contract; same E1 JAR, independent single trials. Mac timing is excluded.',r'\begin{tabular}{r rrrr rrrr}',r'\toprule',r' & \multicolumn{4}{c}{Lazy} & \multicolumn{4}{c}{Direct-Full} \\',r'$n$ & States & Queries & Buckets & Rank & States & Queries & Buckets & Rank \\',r'\midrule']
    for r in wide:
        vals=[str(r['n'])]
        for v in ('none_lazy','none_direct_full'):
            vals += [latex_value(r[v+'_'+f]) for f in ('states','queries','buckets','rank')] if r[v+'_status'] in ('WIN','LOSS') else [r[v+'_status'],'--','--','--']
        s4.append(' & '.join(vals)+r' \\')
    s4 += [r'\bottomrule',r'\end{tabular}',r'% Initial n>=5 input-name collision errors are preserved in ../e4_2; corrected input changes only the interval error label.',r'% Returned ranks are observations; no rank was forced to a constructive upper bound.']
    write(HERE/'table_s4_cell_ring.tex','\n'.join(s4)+'\n')
    audit={'status':'PASS','meaning':'All 45 records and frozen hashes checked; semantic comparison discrepancies, if any, remain explicit below.','initial_series_totals':dict(Counter(r['status'] for r in original)),'corrected_series_totals':dict(Counter(r['status'] for r in rows)),'comparison_discrepancies':issues,'jar_sha256':frozen['jar_sha256'],'input_count':9,'trial_count':45,'source_and_inputs_unchanged_after_freeze':True}
    write(HERE/'validation/final_series_audit.json',json.dumps(audit,indent=2)+'\n');print(json.dumps(audit,indent=2))
if __name__=='__main__':main()
