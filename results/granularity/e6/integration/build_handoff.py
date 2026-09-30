#!/usr/bin/env python3
"""Derive integration tables only from completed, checked E6 measurements."""
from pathlib import Path
import csv,json,hashlib
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo
E6=Path(__file__).resolve().parents[1]
OUT=E6/'integration'
JAR='ff1e6b176f004ea85f1e99690a90388a6a4d24f44cd8d8e636fcd9337dcf67d5'
records=[]; sources=[]; family_counts=[]
def read(family):
    path=E6/family/'summary.csv'
    rows=list(csv.DictReader(path.open()))
    assert len({r['job_id'] for r in rows})==len(rows)
    for r in rows:
        assert r['jar_sha256']==JAR
        assert not r['validation_errors'], (family,r['job_id'],r['validation_errors'])
        assert r['decision'] in ('WIN','LOSS'), (family,r['job_id'],r['status'])
        assert r['certificate_checker']==r['endpoint_checker']=='PASS'
        assert r['link_checker']==('PASS' if r['decision']=='WIN' else 'NOT_APPLICABLE_LOSS')
        result_path=E6/family/r['result_file'];result=json.loads(result_path.read_text())
        for key in ('decision','states_discovered','successor_queries'):
            assert str(result[key])==r[key],(family,r['job_id'],key)
        cert_path=result_path.parent/'certificate.json'
        assert hashlib.sha256(cert_path.read_bytes()).hexdigest()==result['certificate_sha256']
    sources.append(dict(path=str(path.relative_to(E6)),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),rows=len(rows)))
    family_counts.append(dict(family=family,scheduled=len(rows),WIN=sum(r['decision']=='WIN' for r in rows),LOSS=sum(r['decision']=='LOSS' for r in rows),other=0))
    return {r['job_id']:r for r in rows}
def add(family,params,mechanism,contribution,anchor,location,fine,merged,df,generated,merge_kind,loss_reason):
    decisions=(fine['decision'],merged['decision'])
    category={('WIN','LOSS'):'witness',('LOSS','LOSS'):'both_loss',('WIN','WIN'):'both_win'}.get(decisions,'unexpected_other')
    assert category!='unexpected_other',decisions
    assert df['decision']==fine['decision']
    if generated:
        for key in ['decision','states_discovered','successor_queries','worst_completion_rank','losing_region_states']:
            assert generated[key]==merged[key],(family,params,key)
    result=json.loads((E6/location/merged['result_file']).read_text())
    if 'game_equivalence' not in result and generated:
        result=json.loads((E6/location/generated['result_file']).read_text())
    assert result.get('game_equivalence',{}).get('status')=='PASS',(family,params,'Post comparison')
    record=dict(family=family,params=params,mechanism=mechanism,contribution=contribution,anchor=anchor,
        fine_decision=fine['decision'],merged_decision=merged['decision'],**{'class':category},
        cert_checks='E1 certificate PASS; independent endpoints PASS; WIN Link PASS; mechanism PASS; generated/E1 Post PASS',location=location,
        comparison=merge_kind,fine_job=fine['job_id'],merged_job=merged['job_id'],direct_full_job=df['job_id'],
        fine_states=fine['states_discovered'],merged_states=merged['states_discovered'],direct_full_states=df['states_discovered'],
        fine_rank=fine['worst_completion_rank'],direct_full_rank=df['worst_completion_rank'],
        fine_loss_certificate_states=fine['losing_region_states'],merged_loss_certificate_states=merged['losing_region_states'],direct_full_loss_certificate_states=df['losing_region_states'],
        fine_queries=fine['successor_queries'],merged_queries=merged['successor_queries'],direct_full_queries=df['successor_queries'],
        fine_solver_seconds=fine['solver_seconds'],merged_solver_seconds=merged['solver_seconds'],direct_full_solver_seconds=df['solver_seconds'],
        fine_input_sha256=fine['input_sha256'],jar_sha256=JAR,loss_reason=loss_reason)
    records.append(record)
rolling=read('rolling/v1')
assert json.loads((E6/'rolling/v1/validation/rolling_results.json').read_text())['status']=='PASS'
for n in range(2,7):
 for m in range(1,n):
    prefix=f'rolling_n{n:02}_m{m:02}'
    add('Rolling',f'n={n};m={m}','M2','L1;L3','https://kubernetes.io/docs/concepts/workloads/controllers/deployment/','rolling/v1',
        rolling[prefix+'_k01_lazy'],rolling[prefix+'_k01_e1merged'],rolling[prefix+'_k01_df'],rolling[prefix+f'_k{n:02}_lazy'],'transfers',
        'The product transfer makes every replica booting, violating the positive ready floor before any readiness event.')
canary=read('canary/v1')
assert json.loads((E6/'canary/v1/tables/canary_summary.json').read_text())['certificate_mechanism_check']=='PASS'
for n in range(2,7):
 for m in range(1,n):
    prefix=f'n{n:02}_m{m:02}'
    add('Canary',f'n={n};m={m}','M3','L1;L2;L3','https://www.crowdstrike.com/en-us/blog/falcon-content-update-preliminary-post-incident-report/','canary/v1',
        canary[prefix+'_fine_lazy'],canary[prefix+'_merged_lazy'],canary[prefix+'_fine_df'],canary[prefix+'_all_lazy'],'transfers',
        'The environment chooses every broken outcome and can schedule the bad health reports before ordinary controlled recovery, exposing the availability violation.')
policy=read('policy/v2')
assert json.loads((E6/'policy/v2/validation/certificate_mechanism_audit.json').read_text())['status']=='PASS'
add('Policy','rule_pairs=2','M4','boundary;L3','https://docs.aws.amazon.com/cli/latest/reference/cloudtrail/stop-logging.html ; https://csrc.nist.gov/pubs/conference/1997/11/07/mutual-exclusion-of-roles-to-implement-separation/final','policy/v2',
    policy['policy_fine_none_lazy'],policy['policy_fine_boundaries_lazy'],policy['policy_fine_none_direct_full'],policy['policy_generated_coarse_none_lazy'],'boundaries',
    'Global starts create exclusive-role overlap, while global stops create an audit gap; each possible first boundary bucket is unsafe.')
db=read('db_rolling/v2')
assert json.loads((E6/'db_rolling/v2/validation/certificate_protocol_audit.json').read_text())['status']=='PASS'
for m in (2,3):
    prefix=f'db_n3_m{m}'
    reason='A primary or election candidate always exists, so the joint secondary-only transfer is never enabled.'
    if m==3:reason+=' Every individual replacement also violates the zero-downtime ready budget, so fine is LOSS as well.'
    add('DB-Rolling',f'n=3;m={m}','M1;M2','L1;L3' if m==2 else 'negative_control','https://www.mongodb.com/docs/v7.0/tutorial/upgrade-to-enterprise-replica-set/','db_rolling/v2',
        db[prefix+'_fine_none_lazy'],db[prefix+'_fine_transfers_lazy'],db[prefix+'_fine_none_direct_full'],db[prefix+'_all_none_lazy'],'transfers',reason)
audit=read('rolling_audit/v1')
assert json.loads((E6/'rolling_audit/v1/tables/rolling_audit_summary.json').read_text())['status']=='PASS'
add('Rolling+Audit','n=2;m=1;audit_pairs=1','M2','L1;L3;initialization;boundary_null','https://kubernetes.io/docs/concepts/workloads/controllers/deployment/ ; https://docs.aws.amazon.com/cli/latest/reference/cloudtrail/stop-logging.html','rolling_audit/v1',
    audit['fine_none_lazy'],audit['fine_transfers_lazy'],audit['fine_none_df'],audit['generated_transfers_lazy'],'transfers',
    'The joint transfer violates availability. Boundaries alone remain WIN because the sole old stop and new start are singleton groups.')
def write_csv(path, rows):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
write_csv(OUT/'core_results_index.csv',records)
write_csv(E6/'results_index.csv',records)
write_csv(OUT/'completed_run_counts.csv',family_counts)
summary=dict(status='INTERIM',generated_at=datetime.now(ZoneInfo('Asia/Tokyo')).isoformat(),pair_counts={key:sum(r['class']==key for r in records) for key in ('witness','both_loss','both_win')},
    families=dict(Counter(r['family'] for r in records)),canonical_pairs=len(records),canonical_runs=sum(x['rows'] for x in sources),sources=sources,
    counting='One main merge comparison per family/parameter tuple. Repeated solvers, generated coarse contracts, both-merge checks, and prior invalid versions are not independent examples.',
    exclusions='Rolling k-threshold cells are listed separately; Policy transfers null control is separate; PC2 remains active; Rolling+Audit boundaries WIN/WIN is a separate control.')
(OUT/'core_status.json').write_text(json.dumps(summary,indent=2)+'\n')
(OUT/'status.json').write_text(json.dumps(summary,indent=2)+'\n')
def latex(value): return str(value).replace('&', r'\&').replace('_', r'\_')
# Compact main-family comparison, with separate n,m rows in results_index.csv.
lines=[r'% Derived from completed E6 raw. Mac timings deliberately omitted.',r'\begin{tabular}{llrrrrl}',r'\toprule',r'Family & Parameters & Lazy states & Full states & Merge states & Rank & Fine / merged \\',r'\midrule']
for family,params in [('Rolling','n=2;m=1'),('Rolling','n=6;m=1'),('Canary','n=2;m=1'),('Canary','n=6;m=1'),('Policy','rule_pairs=2'),('DB-Rolling','n=3;m=2'),('DB-Rolling','n=3;m=3'),('Rolling+Audit','n=2;m=1;audit_pairs=1')]:
 r=next(x for x in records if x['family']==family and x['params']==params)
 lines.append(f"{family} & {latex(params.replace(';',', '))} & {r['fine_states']} & {r['direct_full_states']} & {r['merged_states']} & {r['fine_rank'] or '--'} & {r['fine_decision']} / {r['merged_decision']} "+r'\\')
lines += [r'\bottomrule',r'\end{tabular}',r'% Rank is the returned Lazy certificate bound; loss-region sizes are in results_index.csv.',r'% Policy uses boundaries merge; the other rows use transfers merge.']
(OUT/'main_comparison.tex').write_text('\n'.join(lines)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k not in ('sources','exclusions')},indent=2))
