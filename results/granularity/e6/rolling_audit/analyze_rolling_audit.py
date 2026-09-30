#!/usr/bin/env python3
"""Derived literal Audit comparisons, including expected boundary null result."""
import csv,json
from collections import Counter,deque
from pathlib import Path
import sys
sys.dont_write_bytecode=True


def read(p):return json.loads(p.read_text())
def write_csv(p,rows):
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else ['job_id','status']);w.writeheader();w.writerows(rows)


def main():
    root=Path(sys.argv[1]).resolve();rows=list(csv.DictReader((root/'tables/results.csv').open()));by={r['job_id']:r for r in rows};checks=[];issues=[];paths=[]
    for row in rows:
        if row['decision'] not in ('WIN','LOSS'):continue
        proof=read(root/row['certificate_file']);states=proof['states'];report=dict(job_id=row['job_id'],decision=row['decision'],status='PASS')
        if row['decision']=='WIN':
            low=[q['id'] for q in states if sum(s=='ready' for v,s in q['physical'])<1]
            gap=[q['id'] for q in states if not ({'audit_old','audit_new'}&set(q['testers']))]
            report.update(low_availability_ids=low,audit_gap_ids=gap,certificate_states=len(states),reason='Every returned WIN-certificate state has a ready replica and at least one active audit rule; the checked old/new testers enforce matching log-before-serve.')
            if low or gap:report['status']='FAIL'
            lookup={q['id']:q for q in states};edges={}
            for s,a,t in proof['strategy_edges']:edges.setdefault(s,[]).append((a,t))
            for q in states:
                if not q['initial']:continue
                todo=deque([(q['id'],[])]);seen=set();found=None
                while todo:
                    s,path=todo.popleft()
                    if s in seen:continue
                    seen.add(s)
                    if lookup[s]['goal']:found=path;break
                    for a,t in edges.get(s,[]):todo.append((t,path+[{'source':s,'action':a,'target':t}]))
                paths.append(dict(job_id=row['job_id'],initial=q['id'],path=found,
                                  scope='One path through the returned strategy; all adversarial outcomes remain checked by the certificate.'))
        else:
            data=read(root/row['result_file']);examples=data['loss_summary']['initial_examples']
            bad=[b for q in examples for b in q['enabled_action_buckets'] if b['action']=='ablation.merge.transfers' and b['unsafe_outcomes']>0]
            report.update(unsafe_merged_transfer_buckets=bad,reason='A merged transfer puts both replicas into booting and reaches the interval error immediately; an audit handoff cannot restore the availability already lost.')
            if not bad:report['status']='FAIL'
        checks.append(report)
        if report['status']!='PASS':issues.append(report)
    comparisons=[]
    for mode in ('transfers','boundaries','both'):
        a,b=by['fine_'+mode+'_lazy'],by['generated_'+mode+'_lazy']
        status='NOT_COMPARABLE'
        if a['decision'] in ('WIN','LOSS') and b['decision'] in ('WIN','LOSS'):
            data=read(root/a['result_file']);status='PASS' if data.get('game_equivalence',{}).get('status')=='PASS' and all(a[k]==b[k] for k in ('decision','states_discovered')) else 'FAIL'
        comparisons.append(dict(mode=mode,status=status,e1_decision=a['decision'],generated_decision=b['decision'],e1_states=a['states_discovered'],generated_states=b['states_discovered']))
        if status=='FAIL':issues.append(comparisons[-1])
    a,b=by['fine_none_lazy'],by['fine_boundaries_lazy'];boundary_null='NOT_COMPARABLE'
    if a['decision'] in ('WIN','LOSS') and b['decision'] in ('WIN','LOSS'):
        boundary_null='PASS' if all(a[k]==b[k] for k in ('decision','states_discovered','successor_queries','worst_completion_rank')) else 'FAIL'
        if boundary_null=='FAIL':issues.append({'boundary_null':boundary_null})
    df=by['fine_none_df'];dfcheck='NOT_COMPARABLE'
    if a['decision'] in ('WIN','LOSS') and df['decision'] in ('WIN','LOSS'):
        dfcheck='PASS' if a['decision']==df['decision'] else 'FAIL'
        if dfcheck=='FAIL':issues.append({'dfcheck':dfcheck})
    summary=dict(provisional=any(r['decision'] in ('NOT_RUN','RUNNING') for r in rows),scheduled=8,
        decision_counts=dict(Counter(r['decision'] for r in rows)),certificate_checks=len(checks),boundary_null_check=boundary_null,df_decision_check=dfcheck,
        generated_comparisons=comparisons,status='FAIL' if issues else 'PASS',issues=issues,
        interpretation='One audit start and one audit stop yield a boundary-renaming null result. Transfer merging tests Rolling availability; no opposing-order requirement is added.')
    tables=root/'tables';(tables/'rolling_audit_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (tables/'certificate_checks.json').write_text(json.dumps({'status':summary['status'],'checks':checks,'issues':issues},indent=2)+'\n')
    (tables/'completion_paths.json').write_text(json.dumps(paths,indent=2)+'\n');write_csv(tables/'generated_comparisons.csv',comparisons)
    write_csv(tables/'mechanism_reasons.csv',[{k:c.get(k,'') for k in ('job_id','decision','status','reason')} for c in checks])
    lines=[r'\begin{tabular}{lrrrrl}',r'\toprule',r'Variant & States & Queries & Rank & $|L|$ & Decision \\',r'\midrule']
    for row in rows:
        lines.append(' & '.join([row['job_id'].replace('_',r'\_'),row['states_discovered'],row['successor_queries'],row['worst_completion_rank'],row['losing_region_states'],row['decision'].replace('_',r'\_')])+r' \\')
    lines += [r'\bottomrule',r'\end{tabular}',r'{\par\smallskip\footnotesize Literal Rolling(2,1) with one old/new audit pair. One product interval requirement enforces availability and continuous audit activation. Boundary merging renames the sole start and stop; it is expected to preserve the outcome. One trial per cell, 32\,GiB heap and a whole-JVM 1,200\,s cap. Rank is the returned completion bound; $|L|$ is the discovered losing-certificate size.}']
    (tables/'table_rolling_audit.tex').write_text('\n'.join(lines)+'\n');print(json.dumps(summary,sort_keys=True));return bool(issues)


if __name__=='__main__':raise SystemExit(main())
