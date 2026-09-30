#!/usr/bin/env python3
"""Canary paired tables and independent physical/LOSS-mechanism certificate checks."""
import csv
import json
from collections import Counter,deque
from pathlib import Path
import sys

sys.dont_write_bytecode=True


def read(path):return json.loads(path.read_text())
def csv_write(path,rows,fields=None):
    fields=fields or list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(rows)


def nodekey(physical,testers,pending):
    return tuple(map(tuple,physical)),tuple(sorted(testers.items())),tuple(sorted(pending))


def mechanism(family,row,job):
    proof=read(family/row['certificate_file']);obj=read(family/job['input'])
    n,m=obj['parameters']['n'],obj['parameters']['m'];states=proof['states']
    report=dict(job_id=job['id'],n=n,m=m,decision=row['decision'],certificate_states=len(states),status='PASS')
    if row['decision']=='WIN':
        counts=[sum(s in ('H','HP') for version,s in q['physical']) for q in states]
        bad=[q['id'] for q,c in zip(states,counts) if c<m]
        report.update(minimum_physical_healthy=min(counts),required=m,violating_state_ids=bad,
                      reason=f'All {len(states)} returned WIN-certificate states have at least {m} physically healthy replicas; HP counts as healthy, BP and B as broken.')
        if bad:report['status']='FAIL'
        return report
    # Reconstruct report edges from explicit local LTS + tester, independently of Java's oracle.
    tester=obj['requirements'][0]['tester'];changes={(s,a):t for s,a,t in tester['changes']}
    bykey={nodekey(q['physical'],q['testers'],q['pending']):q for q in states}
    starts=[q for q in states if q['physical']==[['NEW','BP'] for _ in range(n)] and
            q['testers'].get('reported_availability')==tester['initial'] and not q['pending']]
    todo=deque((q,[]) for q in starts);seen=set();found=None
    while todo:
        q,path=todo.popleft()
        if q['id'] in seen:continue
        seen.add(q['id'])
        if not q['safe'] and q['testers'].get('reported_availability')=='ERR_HEALTH':
            found={'start_id':path[0]['source'] if path else q['id'],'end_id':q['id'],'edges':path};break
        for i,(version,state) in enumerate(q['physical']):
            if version!='NEW' or state!='BP':continue
            action=f'reportB_{i+1}';physical=[list(x) for x in q['physical']];physical[i][1]='B'
            testers=dict(q['testers']);s=testers['reported_availability']
            testers['reported_availability']='ERR_HEALTH' if s=='ERR_HEALTH' else changes.get((s,action),s)
            target=bykey.get(nodekey(physical,testers,q['pending']))
            if target is not None:todo.append((target,path+[{'source':q['id'],'action':action,'target':target['id']}]))
    data=read(family/row['result_file']);roots=data['loss_summary']['initial_examples']
    buckets=[b for q in roots for b in q['enabled_action_buckets'] if b['action']=='ablation.merge.transfers']
    bucket_ok=bool(buckets) and all(b['outcomes']==2**n and b['outcomes_in_certificate_region']>=1 for b in buckets)
    report.update(all_broken_state_ids=[q['id'] for q in starts],all_at_once_bucket_outcomes=[b['outcomes'] for b in buckets],
                  all_broken_to_error_path=found,bucket_evidence_pass=bucket_ok,
                  reason=(f'The checked LOSS certificate contains the all-broken result of the {2**n}-outcome merged transfer and an uncontrollable broken-report path to ERR_HEALTH before any restart.' if starts and found and bucket_ok else 'The intended all-broken/report mechanism was not established by this independent certificate check.'))
    if not starts or not found or not bucket_ok:report['status']='FAIL'
    return report


def main():
    family=Path(sys.argv[1]).resolve();config=read(family/'config.json')
    rows=list(csv.DictReader((family/'tables/results.csv').open()));jobs={j['id']:j for j in config['jobs']}
    by={(jobs[r['job_id']]['parameters']['n'],jobs[r['job_id']]['parameters']['m'],jobs[r['job_id']]['variant']):r for r in rows}
    checks=[];issues=[]
    for row in rows:
        if row['decision'] not in ('WIN','LOSS'):continue
        try:check=mechanism(family,row,jobs[row['job_id']])
        except Exception as exc:check={'job_id':row['job_id'],'status':'FAIL','error':type(exc).__name__+': '+str(exc)}
        checks.append(check)
        if check['status']!='PASS':issues.append(check)
    pairs=[]
    for n in range(2,7):
        for m in range(1,n):
            f,e,a,d=[by[(n,m,k)] for k in ('fine_lazy','merged_lazy','all_lazy','fine_df')]
            comparable=lambda x,y:x['decision'] in ('WIN','LOSS') and y['decision'] in ('WIN','LOSS')
            cat={('WIN','LOSS'):'witness',('LOSS','LOSS'):'bothLOSS',('WIN','WIN'):'null'}.get((f['decision'],e['decision']),'other')
            equality='NOT_COMPARABLE'
            if comparable(e,a):equality='PASS' if all(e[k]==a[k] for k in ('decision','states_discovered')) else 'FAIL'
            dfcheck='PASS' if comparable(f,d) and f['decision']==d['decision'] else 'FAIL' if comparable(f,d) else 'NOT_COMPARABLE'
            pair=dict(n=n,m=m,category=cat,fine_decision=f['decision'],merged_decision=e['decision'],all_decision=a['decision'],df_decision=d['decision'],
                      explicit_all_vs_e1_merge=equality,df_lazy_decision=dfcheck)
            for prefix,row in [('fine',f),('merged',e),('all',a),('df',d)]:
                for field in ('states_discovered','successor_queries','enabled_buckets','materialized_transitions','worst_completion_rank','losing_region_states'):
                    pair[prefix+'_'+field]=row[field]
            pairs.append(pair)
            if equality=='FAIL' or dfcheck=='FAIL':issues.append({'n':n,'m':m,'explicit_all_vs_e1_merge':equality,'df_lazy_decision':dfcheck})
    tables=family/'tables';csv_write(tables/'pairs.csv',pairs)
    (tables/'certificate_checks.json').write_text(json.dumps({'status':'FAIL' if issues else 'PASS','checks':checks,'issues':issues},indent=2)+'\n')
    csv_write(tables/'mechanism_reasons.csv',[{'job_id':c['job_id'],'status':c['status'],'decision':c.get('decision',''),'reason':c.get('reason',c.get('error',''))} for c in checks],['job_id','status','decision','reason'])
    summary=dict(provisional=any(r['decision'] in ('NOT_RUN','RUNNING') for r in rows),scheduled=60,parameter_pairs=15,
                 decision_counts=dict(Counter(r['decision'] for r in rows)),pair_categories=dict(Counter(p['category'] for p in pairs)),
                 checked_certificates=len(checks),certificate_mechanism_check='FAIL' if issues else 'PASS',issues=issues,
                 explicit_all_comparisons=sum(p['explicit_all_vs_e1_merge']=='PASS' for p in pairs),df_lazy_comparisons=sum(p['df_lazy_decision']=='PASS' for p in pairs),
                 scope='Reported-health interval requirement; physical health separately checked on all returned WIN certificate states. Canary/staging practice inspiration, not incident reproduction.')
    (tables/'canary_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    cell=lambda r,k:r[k] if r[k] else {'NOT_RUN':'Pending','NOT_RUN_DEADLINE':'NR','RUNNING':'Running'}.get(r['decision'],r['decision'])
    lines=[r'\begin{tabular}{rrrrrrrl}',r'\toprule',r'$n$ & $m$ & Fine states & Fine rank & Merged states & $|L|$ & DF states & Group \\',r'\midrule']
    for p in pairs:
        n,m=p['n'],p['m'];f,e,d=[by[(n,m,k)] for k in ('fine_lazy','merged_lazy','fine_df')]
        lines.append(' & '.join([str(n),str(m),cell(f,'states_discovered'),cell(f,'worst_completion_rank'),cell(e,'states_discovered'),cell(e,'losing_region_states'),cell(d,'states_discovered'),p['category']])+r' \\')
    lines += [r'\bottomrule',r'\end{tabular}',r'{\par\smallskip\footnotesize Fine and Merged use Lazy; DF uses separate transfers. WIN rank is a returned completion bound, not an optimum; $|L|$ is the discovered LOSS-certificate size. The interval tester observes finite health reports; physical health is independently checked on WIN certificates. An explicit all-at-once input is separately compared with E1 merging in CSV. One 32\,GiB, 1,200\,s trial per scheduled cell; TO/NR remain explicit.}']
    (tables/'table_canary.tex').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'canary':summary},sort_keys=True));return bool(issues)


if __name__=='__main__':raise SystemExit(main())
