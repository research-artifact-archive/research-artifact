#!/usr/bin/env python3
"""Fresh derived results: no expected outcome is substituted for a measurement."""
import csv,json,sys
from collections import Counter
from pathlib import Path
sys.dont_write_bytecode=True


def read(p):return json.loads(p.read_text())
def csvwrite(p,rows,fields=None):
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields or list(rows[0]));w.writeheader();w.writerows(rows)
def measured(row):return row['decision'] in ('WIN','LOSS')
def decision_tex(value):return {'NOT_RUN':'Pending','RUNNING':'Running','NOT_RUN_DEADLINE':'NR'}.get(value,value).replace('_',r'\_')


def main():
    family=Path(sys.argv[1]).resolve();rows=list(csv.DictReader((family/'tables/results.csv').open()));by={r['job_id']:r for r in rows};checks=[];issues=[];pairs=[]
    for row in rows:
        if not measured(row):continue
        p=json.loads(row['parameters']);proof=read(family/row['certificate_file']);states=proof['states'];lookup={q['id']:q for q in states};fail=[]
        for q in states:
            if len(q['physical'])!=p['n']:fail.append('Physical arity differs.')
            first=q['physical'][0][1];status,queue=first.split('_q')
            if status not in ('I','B') or not 0<=int(queue)<=p['B']:fail.append('Invalid queue/worker state.')
            if any(s not in ('I','B') for v,s in q['physical'][1:]):fail.append('Invalid worker state.')
            if q['testers']:fail.append('Unexpected safety tester.')
        rec=dict(job_id=row['job_id'],decision=row['decision'],certificate_states=len(states),status='PASS')
        if row['decision']=='WIN':
            transfers=[]
            for s,a,t in proof['strategy_edges']:
                source,target=lookup[s],lookup[t]
                if source['rank']<=target['rank']:fail.append('Nondecreasing strategy rank.')
                if a.startswith('rho_') or a=='ablation.merge.transfers':
                    changes=[i for i,(x,y) in enumerate(zip(source['physical'],target['physical'])) if x!=y]
                    if not changes:fail.append('Transfer changed no version.')
                    for i in changes:
                        x,y=source['physical'][i],target['physical'][i]
                        if x[0]!='OLD' or y[0]!='NEW' or x[1]!=y[1] or not x[1].startswith('I'):fail.append('Non-idle or non-preserving transfer.')
                    if source['physical'][0][1].split('_q')[1]!=target['physical'][0][1].split('_q')[1]:fail.append('Transfer changed queue.')
                    transfers.append(dict(source=s,action=a,target=t,changed_workers=changes))
            rec.update(transfer_edges_checked=len(transfers),reason='All returned strategy edges strictly decrease the checked rank; every transfer preserves the queue and changes only idle worker versions.')
            if p['regime']!='backpressure':rec['unexpected_regime']=True
        else:
            roots=[q for q in states if q['initial'] and int(q['physical'][0][1].split('_q')[1])==p['B'] and not q['goal']]
            if p['regime']=='saturated_offers' and not roots:fail.append('No full-queue initial losing self-loop witness in certificate.')
            rec.update(full_queue_initial_ids=[q['id'] for q in roots],self_loop_action='arrival' if roots and p['regime']=='saturated_offers' else '',
                reason='A returned full-queue initial non-goal state has an uncontrollable arrival self-loop, which admits infinite avoidance of update completion without fairness.' if roots and p['regime']=='saturated_offers' else 'Checked losing certificate; the registered full-queue loop explanation is not established for this result.')
        if fail:rec.update(status='FAIL',issues=fail);issues.append(rec)
        checks.append(rec)
    for n in range(2,7):
        for b in (1,2):
            for regime in ('backpressure','saturated_offers'):
                base=f'threads_n{n:02}_b{b:02}_{regime}';fine,merged,generated,df=[by[base+'_'+s] for s in ('fine_lazy','e1merged_lazy','generated_all_lazy','fine_df')]
                decision_pair=(fine['decision'],merged['decision'])
                category={('WIN','WIN'):'null',('WIN','LOSS'):'witness',('LOSS','LOSS'):'both_loss',('LOSS','WIN'):'reversal'}.get(decision_pair,'incomplete')
                equivalence='NOT_COMPARABLE'
                if measured(merged) and measured(generated):
                    raw=read(family/merged['result_file']);equivalence='PASS' if raw.get('game_equivalence',{}).get('status')=='PASS' and all(merged[k]==generated[k] for k in ('decision','states_discovered','successor_queries','worst_completion_rank','losing_region_states')) else 'FAIL'
                dfcheck='PASS' if measured(fine) and measured(df) and fine['decision']==df['decision'] else ('FAIL' if measured(fine) and measured(df) else 'NOT_COMPARABLE')
                pair=dict(n=n,B=b,regime=regime,category=category,fine=fine['decision'],merged=merged['decision'],generated=generated['decision'],df=df['decision'],fine_states=fine['states_discovered'],merged_states=merged['states_discovered'],df_states=df['states_discovered'],fine_queries=fine['successor_queries'],merged_queries=merged['successor_queries'],df_queries=df['successor_queries'],fine_rank=fine['worst_completion_rank'],df_rank=df['worst_completion_rank'],fine_losing_size=fine['losing_region_states'],merged_losing_size=merged['losing_region_states'],generated_equivalence=equivalence,df_decision_check=dfcheck)
                pairs.append(pair)
                if equivalence=='FAIL' or dfcheck=='FAIL':issues.append(pair)
    tables=family/'tables';csvwrite(tables/'pairs.csv',pairs);csvwrite(tables/'mechanism_reasons.csv',[{k:r.get(k,'') for k in ('job_id','decision','status','reason')} for r in checks],['job_id','decision','status','reason'])
    summary=dict(provisional=any(r['decision'] in ('RUNNING','NOT_RUN') for r in rows),scheduled=80,parameter_pairs=20,decision_counts=dict(Counter(r['decision'] for r in rows)),pair_counts=dict(Counter(p['category'] for p in pairs)),certificate_checks=len(checks),generated_equivalence_pass=sum(p['generated_equivalence']=='PASS' for p in pairs),df_check_pass=sum(p['df_decision_check']=='PASS' for p in pairs),status='FAIL' if issues else 'PASS',issues=issues,
        interpretation='Dispatch control with bounded backpressure may admit common quiescence, whereas an always-enabled uncontrollable offer loop may defeat both granularities. These are finite abstraction controls, not a reproduction of Kitsune and not a claimed L1 separation.')
    (tables/'threads_summary.json').write_text(json.dumps(summary,indent=2)+'\n');(tables/'certificate_checks.json').write_text(json.dumps(dict(status=summary['status'],checks=checks,issues=issues),indent=2)+'\n')
    lines=[r'\begin{tabular}{rrlccrrr}',r'\toprule',r'$n$ & $B$ & Arrivals & Fine & All & Fine states & All states & DF states \\',r'\midrule']
    for p in pairs:lines.append(' & '.join(map(str,[p['n'],p['B'],'Bounded' if p['regime']=='backpressure' else 'Saturated',decision_tex(p['fine']),decision_tex(p['merged']),p['fine_states'] or '--',p['merged_states'] or '--',p['df_states'] or '--']))+r' \\')
    lines += [r'\bottomrule',r'\end{tabular}',r'{\par\smallskip\footnotesize One 32\,GiB / 1,200\,s trial per cell. All is E1 transfer merging; generated all-group contracts are independently compared by full reachable Post. Bounded arrivals stop at queue capacity; saturated arrivals can self-loop there. Dispatch is controllable and completion is uncontrollable. No fairness assumption.}']
    (tables/'table_threads_states.tex').write_text('\n'.join(lines)+'\n')
    lines=[r'\begin{tabular}{rrlrrrrr}',r'\toprule',r'$n$ & $B$ & Arrivals & Fine rank & DF rank & Fine $|L|$ & All $|L|$ & Fine queries \\',r'\midrule']
    for p in pairs:lines.append(' & '.join(map(str,[p['n'],p['B'],'Bounded' if p['regime']=='backpressure' else 'Saturated',p['fine_rank'] or '--',p['df_rank'] or '--',p['fine_losing_size'] or '--',p['merged_losing_size'] or '--',p['fine_queries'] or '--']))+r' \\')
    lines += [r'\bottomrule',r'\end{tabular}',r'{\par\smallskip\footnotesize Rank is the returned worst-case completion bound, not an optimality claim; $|L|$ is the discovered losing-certificate region. Blank metrics are not inferred from expected outcomes.}']
    (tables/'table_threads_certificates.tex').write_text('\n'.join(lines)+'\n');print(json.dumps(summary,sort_keys=True));return bool(issues)

if __name__=='__main__':raise SystemExit(main())
