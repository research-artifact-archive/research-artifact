#!/usr/bin/env python3
"""Derived scale tables; missing measurements stay missing, predictions stay separate."""
import csv,json,sys
from pathlib import Path
from collections import Counter

def main():
 base=Path(sys.argv[1]).resolve();rows=list(csv.DictReader((base/'summary.csv').open()));by={r['job_id']:r for r in rows};checks=[];pairs=[];issues=[]
 for row in rows:
  if row['decision'] not in ('WIN','LOSS'):continue
  n,m,k=[json.loads(row['parameters'])[x] for x in ('n','m','k')]
  proof=json.loads((base/row['certificate_file']).read_text())
  if row['decision']=='WIN':
   ids={s['id']:s for s in proof['states']}
   assert all(sum(q=='ready' for v,q in s['physical'])>=m for s in proof['states'])
   assert all(ids[v]['rank']<ids[u]['rank'] for u,a,v in proof['strategy_edges'])
   assert int(row['worst_completion_rank'])==2*n
   if row['solver']=='direct_full' and int(row['states_discovered'])!=(n+2)*2**(n-1):issues.append(row['job_id']+': analytic Full count mismatch')
  else:
   result=json.loads((base/row['result_file']).read_text())
   assert any(not s['safe'] and sum(q=='ready' for v,q in s['physical'])<m for s in proof['states'])
   assert any(b['update'] and b['unsafe_outcomes'] for root in result['loss_summary']['initial_examples'] for b in root['enabled_action_buckets'])
  checks.append(dict(job=row['job_id'],status='PASS',decision=row['decision'],certificate_states=len(proof['states'])))
 for n in range(7,17):
  for m in [1,n-1]:
   prefix=f'n{n:02}_m{m:02}';fine,merged,allg,df=[by[prefix+'_'+s] for s in ['fine_lazy','merged_lazy','all_lazy','fine_df']]
   cat={('WIN','LOSS'):'witness',('WIN','WIN'):'both_win',('LOSS','LOSS'):'both_loss'}.get((fine['decision'],merged['decision']),'incomplete')
   equality='NOT_CHECKED'
   if merged['decision'] in ('WIN','LOSS') and allg['decision'] in ('WIN','LOSS'):
    result=json.loads((base/merged['result_file']).read_text());equality='PASS'
    for key in ['decision','states_discovered','successor_queries','worst_completion_rank','losing_region_states']:
     if merged[key]!=allg[key]:issues.append(prefix+': generated/merged '+key);equality='FAIL'
    if result.get('game_equivalence',{}).get('status')!='PASS':issues.append(prefix+': full Post equality unavailable');equality='FAIL'
   pair=dict(n=n,m=m,category=cat,generated_vs_e1=equality,analytical_full_states=(n+2)*2**(n-1),analytical_rank=2*n)
   for label,row in [('fine',fine),('merged',merged),('all',allg),('df',df)]:
    for key in ['status','decision','states_discovered','successor_queries','worst_completion_rank','losing_region_states','solver_seconds']:
     pair[label+'_'+key]=row[key]
   pairs.append(pair)
 (base/'tables').mkdir(exist_ok=True)
 with (base/'tables/scale_pairs.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(pairs[0]));w.writeheader();w.writerows(pairs)
 report=dict(status='FAIL' if issues else 'PASS',provisional=any(r['decision'] not in ('WIN','LOSS','TO','OOM','ERROR','NOT_RUN_DEADLINE') for r in rows),
  scheduled=len(rows),run_status_counts=dict(Counter(r['status'] for r in rows)),pair_categories=dict(Counter(r['category'] for r in pairs)),issues=issues,certificate_checks=checks,
  scope='Scale extension of an existing constructed family, not additional operational case studies. Analytical counts never replace measurements.')
 (base/'tables/scale_checks.json').write_text(json.dumps(report,indent=2)+'\n')
 lines=[r'\begin{longtable}{rrrrrlll}',r'\caption{Rolling scale extension. Full prediction is analytical; blank measured values remain unmeasured.}\\',r'\toprule',r'$n$ & $m$ & Lazy states & Full states & Full prediction & Fine / merged & Rank & Status \\',r'\midrule',r'\endfirsthead',r'\toprule',r'$n$ & $m$ & Lazy states & Full states & Full prediction & Fine / merged & Rank & Status \\',r'\midrule',r'\endhead']
 esc=lambda x:str(x).replace('_',r'\_')
 for r in pairs:
  vals=[r['n'],r['m'],r['fine_states_discovered'] or '--',r['df_states_discovered'] or '--',r['analytical_full_states'],r['fine_decision']+' / '+r['merged_decision'],r['fine_worst_completion_rank'] or '--',r['df_status']]
  lines.append(' & '.join(esc(x) for x in vals)+r' \\')
 lines += [r'\bottomrule',r'\end{longtable}']
 (base/'tables/scale_table.tex').write_text('\n'.join(lines)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k!='certificate_checks'}));return bool(issues)
if __name__=='__main__':raise SystemExit(main())
