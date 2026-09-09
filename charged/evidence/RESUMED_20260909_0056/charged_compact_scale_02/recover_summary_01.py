"""Post-outcome aggregation only; never starts or reruns a measurement."""
from pathlib import Path
import collections,datetime,hashlib,json,statistics
HERE=Path(__file__).resolve().parent;D=HERE/'attempt01'
def read(p):return json.loads(p.read_text())
def save(p,x):
 with p.open('x') as f:json.dump(x,f,indent=2);f.write('\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
rows=[json.loads(s) for s in (D/'RAW.jsonl').read_text().splitlines()];units=read(D/'UNITS.json');cases=read(D/'CASES.json')
ids={u['id'] for u in units};assert len(rows)==len(units)==len(ids)==180 and {r['id'] for r in rows}==ids
assert all(read(D/'runs'/r['id']/'PROCESS.json')==r for r in rows)
lookup={u['id']:u for u in units};case_map={c['id']:c for c in cases};values=collections.defaultdict(list);analytic=[];shapes=[]
for row in rows:
 u=lookup[row['id']];assert all(row[k]==u[k] for k in ['case_id','method','budgets','seconds_cap'])
 if row['status']!='SUCCESS':continue
 result=row['worker_result'];assert result==read(D/'runs'/row['id']/'RESULT.json')
 for b,v in zip(row['budgets'],result['values']):values[row['case_id'],b].append((row['id'],v))
 c=case_map[row['case_id']];n,M,A=c['n'],c['copies'],c['scale'];pred=[]
 for b in u['budgets']:
  q,r=divmod(min(b,n*(M+1)),M+1);pred.append(A*((M+1)*q*(2*n-q+1)-q+2*(n-q)*r))
 assert pred==u['expected_values'] and A*n*(n+1)==u['expected_baseline']
 if result['values']!=pred or result['baseline']!=u['expected_baseline']:analytic.append(dict(id=row['id'],actual=result,expected_values=pred,expected_baseline=u['expected_baseline']))
 if row['method']=='PACK':
  expected_runs=[]
  for j in range(n,0,-1):expected_runs.extend([[2*j*A,M],[(2*j-1)*A,1]])
  artifact=read(D/'runs'/row['id']/'ARTIFACT.json');actual=artifact['backend']['value_slopes']
  shapes.append(dict(id=row['id'],expected_runs=2*n,actual_runs=len(actual),equal=actual==expected_runs))
already=read(D/'ANALYTICAL_CHECKS.json');assert already==dict(value_disagreements=analytic,whole_profile_checks=shapes)
disagreements=[dict(case_id=k[0],budget=k[1],observed=rs) for k,rs in values.items() if len({v for _,v in rs})>1]
by_method={}
for method in ['PACK','ROOT','ALL','PEAK','DP']:
 group=[r for r in rows if r['method']==method];ok=[r for r in group if r['status']=='SUCCESS']
 by_method[method]=dict(units=len(group),statuses=dict(collections.Counter(r['status'] for r in group)),reasons=dict(collections.Counter(r.get('reason','') for r in group if r['status']!='SUCCESS')),successful_cold_seconds=[r['cold_seconds'] for r in ok],completed_requested_roots=sum(len(r['budgets']) for r in ok),maximum_success_rss_bytes=max([r['worker_result']['process_peak_rss_bytes'] for r in ok],default=0),max_cold_seconds=max([r['cold_seconds'] for r in ok],default=0))
pairs=[];keyed={(r['case_id'],len(r['budgets']),r['method']):r for r in rows}
for c in cases:
 for size in [1,12]:
  a=keyed[c['id'],size,'PACK']
  for method in ['ROOT','ALL','PEAK','DP']:
   b=keyed[c['id'],size,method];pair=dict(case_id=c['id'],workload=size,comparator=method,PACK_status=a['status'],comparator_status=b['status'],timing_scope='same serial campaign; one sample; different output services')
   if a['status']==b['status']=='SUCCESS':pair.update(ratio_comparator_over_PACK=b['cold_seconds']/a['cold_seconds'],PACK_seconds=a['cold_seconds'],comparator_seconds=b['cold_seconds'])
   pairs.append(pair)
summary=dict(schema='charged-compact-stress-recovered-summary-v1',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),units=180,requested_roots=sum(len(u['budgets']) for u in units),statuses=dict(collections.Counter(r['status'] for r in rows)),by_method=by_method,paired_comparisons=pairs,disagreements=disagreements,analytic_disagreements=analytic,whole_profiles_checked=len(shapes),whole_profiles_equal=sum(r['equal'] for r in shapes),missing_ids=sorted(ids-{r['id'] for r in rows}),raw_sha256=sha(D/'RAW.jsonl'),analytical_checks_sha256=sha(D/'ANALYTICAL_CHECKS.json'),unmodified_benchmark_sha256=sha(HERE/'benchmark.py'),aggregation_script_sha256=sha(Path(__file__)),original_process_exit=1,original_error="TypeError at final SUMMARY argument: 'expected' set was shadowed by a root-run list; list minus set. All180 measurement PROCESS/RAW records and ANALYTICAL_CHECKS had completed.",measurements_rerun=0,seconds=None,elapsed_note='Console final180 record reports533.5022378749854s; no original aggregate completion time is manufactured.',result_scope='Post-outcome aggregation of preserved180 units; structural stress, not application distribution.')
save(D/'SUMMARY_RECOVERED_01.json',summary)
analysis=dict(by_method=by_method,paired_medians={m:dict(common_successes=len(rs),median=statistics.median(rs) if rs else None) for m in ['ROOT','ALL','PEAK','DP'] for rs in [[p['ratio_comparator_over_PACK'] for p in pairs if p['comparator']==m and 'ratio_comparator_over_PACK' in p]]},large_PACK=[dict(id=r['id'],cold_seconds=r['cold_seconds'],result=r['worker_result']) for r in rows if r['method']=='PACK' and r['status']=='SUCCESS' and case_map[r['case_id']]['n']==32768],large_ROOT=[dict(id=r['id'],cold_seconds=r['cold_seconds']) for r in rows if r['method']=='ROOT' and r['status']=='SUCCESS' and case_map[r['case_id']]['n']==32768])
save(D/'POSTHOC_ANALYSIS_RECOVERED_01.json',analysis)
print(json.dumps(dict(statuses=summary['statuses'],methods={k:{x:v[x] for x in ['statuses','reasons','max_cold_seconds','maximum_success_rss_bytes']} for k,v in by_method.items()},whole_profiles_equal=summary['whole_profiles_equal'],analytical_disagreements=len(analytic),shared_disagreements=len(disagreements),paired=analysis['paired_medians']),indent=2))
