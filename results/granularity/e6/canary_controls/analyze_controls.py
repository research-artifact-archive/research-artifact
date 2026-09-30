#!/usr/bin/env python3
"""Keep both controls, all variants, failures, and original measured comparisons."""
import csv,hashlib,json,sys
from collections import Counter
from pathlib import Path
sys.dont_write_bytecode=True
E6=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text())
def savecsv(p,rows,fields=None):
 with p.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields or list(rows[0]));w.writeheader();w.writerows(rows)
def completed(r):return r['decision'] in ('WIN','LOSS')
def tex(v):return {'NOT_RUN':'Pending','RUNNING':'Running','NOT_RUN_DEADLINE':'NR'}.get(v,str(v)).replace('_',r'\_')
def main():
 family=Path(sys.argv[1]).resolve();rows=list(csv.DictReader((family/'tables/results.csv').open()));config=read(family/'config.json');jobs={j['id']:j for j in config['jobs']};by={r['job_id']:r for r in rows};checks=[];issues=[];pairs=[]
 for row in rows:
  if not completed(row):continue
  job=jobs[row['job_id']];model=read(family/job['input']);p=job['parameters'];proof=read(family/row['certificate_file']);states=proof['states'];lookup={q['id']:q for q in states};fail=[]
  rec=dict(job_id=row['job_id'],control=p['control'],decision=row['decision'],certificate_states=len(states),status='PASS')
  if row['decision']=='WIN':
   minimum=min(sum(s in ('H','HP') for v,s in q['physical']) for q in states);rankbad=[(s,a,t) for s,a,t in proof['strategy_edges'] if lookup[s]['rank']<=lookup[t]['rank']]
   if minimum<p['m']:fail.append('Physical health falls below m.')
   if rankbad:fail.append('Rank does not decrease along every strategy edge.')
   rec.update(minimum_physical_healthy=minimum,rank_edges_checked=len(proof['strategy_edges']),reason=f'All {len(states)} returned WIN-certificate states retain at least {p["m"]} physically healthy replicas and every returned strategy edge decreases rank.')
  else:
   samples=[dict(state_id=q['id'],component=i+1,local_state=s,goal=q['goal']) for q in states for i,(v,s) in enumerate(q['physical']) if v=='NEW' and s in ('BP','B')][:3]
   irreversible=[]
   for i,c in enumerate(model['components'],1):
    adj={q:set() for q in c['new']['states']}
    for s,a,t in c['new']['edges']:adj[s].add(t)
    seen={'BP'};todo=['BP']
    while todo:
     for q in adj[todo.pop()]:
      if q not in seen:seen.add(q);todo.append(q)
    irreversible.append('H' not in seen)
   if p['control']=='no_recovery' and (not samples or not all(irreversible)):fail.append('Irreversible broken-state mechanism not established.')
   rec.update(broken_state_examples=samples,all_components_irreversible=all(irreversible),reason='The returned LOSS certificate contains a transferred BP/B state; its component cannot return to H in the no-recovery graph, whereas every loadable goal requires all components in H.' if samples and all(irreversible) else 'Checked LOSS certificate; the irreversible broken-state explanation is not established.')
  if fail:rec.update(status='FAIL',issues=fail);issues.append(rec)
  checks.append(rec)
 for n in range(2,5):
  for m in range(1,n):
   original={}
   for variant in ('fine_lazy','merged_lazy'):
    f=E6/f'canary/v1/raw/series/n{n:02}_m{m:02}_{variant}/result.json';data=read(f);original[variant]=(data['decision'],str(f.relative_to(E6)),hashlib.sha256(f.read_bytes()).hexdigest())
   for c in ('healthy_only','no_recovery'):
    base=f'n{n:02}_m{m:02}_{c}_';f,e,a,d=[by[base+s] for s in ('fine_lazy','merged_lazy','all_lazy','fine_df')];cat={('WIN','LOSS'):'witness',('WIN','WIN'):'null',('LOSS','LOSS'):'both_loss',('LOSS','WIN'):'reversal'}.get((f['decision'],e['decision']),'incomplete');equal='NOT_COMPARABLE'
    if completed(e) and completed(a):equal='PASS' if read(family/e['result_file']).get('game_equivalence',{}).get('status')=='PASS' and all(e[k]==a[k] for k in ('decision','states_discovered','successor_queries','worst_completion_rank','losing_region_states')) else 'FAIL'
    df='PASS' if completed(f) and completed(d) and f['decision']==d['decision'] else ('FAIL' if completed(f) and completed(d) else 'NOT_COMPARABLE')
    pair=dict(n=n,m=m,control=c,category=cat,original_fine=original['fine_lazy'][0],original_merged=original['merged_lazy'][0],fine=f['decision'],merged=e['decision'],generated=a['decision'],df=d['decision'],generated_equivalence=equal,df_decision_check=df,
     original_fine_result=original['fine_lazy'][1],original_fine_sha256=original['fine_lazy'][2],original_merged_result=original['merged_lazy'][1],original_merged_sha256=original['merged_lazy'][2])
    for prefix,r in [('fine',f),('merged',e),('generated',a),('df',d)]:
     for field in ('states_discovered','successor_queries','enabled_buckets','materialized_transitions','worst_completion_rank','losing_region_states'):pair[prefix+'_'+field]=r[field]
    pairs.append(pair)
    if equal=='FAIL' or df=='FAIL':issues.append(pair)
 summary=dict(provisional=any(r['decision'] in ('NOT_RUN','RUNNING') for r in rows),scheduled=48,parameter_conditions=12,decision_counts=dict(Counter(r['decision'] for r in rows)),pair_counts=dict(Counter(p['category'] for p in pairs)),certificate_checks=len(checks),generated_equivalence_pass=sum(p['generated_equivalence']=='PASS' for p in pairs),df_check_pass=sum(p['df_decision_check']=='PASS' for p in pairs),status='FAIL' if issues else 'PASS',issues=issues,scope='Controls of outcome nondeterminism and recoverability in the unchanged Canary abstraction. Both unfavorable results and null results are retained; no operational efficacy claim.')
 tables=family/'tables';savecsv(tables/'pairs.csv',pairs);savecsv(tables/'mechanism_reasons.csv',[{k:r.get(k,'') for k in ('job_id','control','decision','status','reason')} for r in checks],['job_id','control','decision','status','reason']);(tables/'controls_summary.json').write_text(json.dumps(summary,indent=2)+'\n');(tables/'certificate_checks.json').write_text(json.dumps(dict(status=summary['status'],checks=checks,issues=issues),indent=2)+'\n')
 lines=[r'\begin{tabular}{rrlccrrrr}',r'\toprule',r'$n$ & $m$ & Control & Fine & All & Fine states & All states & Fine rank/$|L|$ & DF states \\',r'\midrule']
 for p in pairs:
  metric=p['fine_worst_completion_rank'] if p['fine']=='WIN' else p['fine_losing_region_states'];lines.append(' & '.join([str(p['n']),str(p['m']),'Healthy only' if p['control']=='healthy_only' else 'No recovery',tex(p['fine']),tex(p['merged']),p['fine_states_discovered'] or '--',p['merged_states_discovered'] or '--',metric or '--',p['df_states_discovered'] or '--'])+r' \\')
 lines += [r'\bottomrule',r'\end{tabular}',r'{\par\smallskip\footnotesize Fine and All use Lazy; All is E1 transfer merging, also checked against generated all-group input. Original Canary has fine WIN / all LOSS at every listed point. Healthy only removes broken transfer outcomes; No recovery removes only B-to-H restoration edges. One trial, 32\,GiB, 1,200\,s cap. Rank is a returned bound and $|L|$ a discovered losing-certificate region. Mac times are not Xeon comparisons.}'];(tables/'table_canary_controls.tex').write_text('\n'.join(lines)+'\n');print(json.dumps(summary,sort_keys=True));return bool(issues)
if __name__=='__main__':raise SystemExit(main())
