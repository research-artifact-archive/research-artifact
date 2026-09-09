from pathlib import Path
import collections,csv,datetime,hashlib,json,math,statistics,time
from check01 import check,phase_check
D=Path(__file__).resolve().parent;O=D/'analysis01';O.mkdir();start=time.monotonic()
receipt=json.loads((D/'run01/check01/RECEIPT.json').read_text());assert receipt['status']=='PASS' and receipt['raw_units']==1728
rows=[json.loads(line) for p in sorted((D/'run01').glob('p*/stdout.jsonl')) for line in p.read_text().splitlines()];assert len(rows)==1728 and all(x['status']=='SUCCESS' for x in rows)
def quantile(x,p):s=sorted(x);return s[max(0,min(len(s)-1,math.ceil(p*len(s))-1))]
def stats(x):return {'n':len(x),'min':min(x),'median':statistics.median(x),'p95_nearest_rank':quantile(x,.95),'max':max(x)}
def metrics(row):
 bg=row['writer_requests'];fg=row['foreground_requests'];c=row['counters'];v={'foreground_us':row['foreground_ns']/1000,'foreground_call_p95_us':quantile([(x['returned_ns']-x['invoked_ns'])/1000 for x in fg],.95),'background_e2e_median_us':statistics.median([(x['returned_ns']-x['intended_ns'])/1000 for x in bg]),'background_e2e_p95_us':quantile([(x['returned_ns']-x['intended_ns'])/1000 for x in bg],.95),'background_queue_p95_us':quantile([(x['invoked_ns']-x['enqueued_ns'])/1000 for x in bg],.95),'background_service_p95_us':quantile([(x['returned_ns']-x['invoked_ns'])/1000 for x in bg],.95),'producer_lateness_p95_us':quantile([(x['enqueued_ns']-x['intended_ns'])/1000 for x in bg],.95),'writes_during_foreground':row['actual_writes_during_foreground'],'setup_ms':row['setup_ns']/1e6,'whole_unit_ms':row['whole_unit_ns']/1e6,'foreground_gc_events':sum(row['foreground_gc_collections'])}
 intervals=phase_check(row);v.update({'observed_protected_us':sum(b-a for a,b in intervals)/1000,'observed_protected_call_p95_us':quantile([(b-a)/1000 for a,b in intervals],.95)})
 if c:v.update({'calls':c['Calls'],'cheap_failures':c['CheapFailures'],'protected_transformations':c['PreparedInside'],'total_transformations':c['PreparedInside']+c['PreparedOutside'],'mismatches':c['Mismatches'],'protected_rebases':c['Rebases']})
 return v

arms=[('three',0),('three',2),('rebase',0),('rebase',2),('batch',0),('batch',2)];cells=[];forks=[]
for mode,r in arms:
 for period in [0,10,100,1000]:
  relevant=[x for x in rows if x['phase']=='measurement' and (x['mode'],x['r'],x['period_us'])==(mode,r,period)];values=[metrics(x) for x in relevant];assert len(values)==60
  cells.append(dict(mode=mode,r=r,period_us=period,units=60,forks=6,metrics={k:stats([v[k] for v in values]) for k in values[0]},totals={k:sum(x['counters'].get(k,0) for x in relevant) for k in ['Calls','CheapFailures','PreparedInside','PreparedOutside','Mismatches','Rebases']}))
  for fork in range(1,7):
   vs=[metrics(x) for x in relevant if x['fork']==fork];assert len(vs)==10
   forks.append(dict(mode=mode,r=r,period_us=period,fork=fork,units=10,metrics={k:stats([v[k] for v in vs]) for k in vs[0]}))
lookup={(x['mode'],x['r'],x['period_us']):x for x in cells};byfork={(x['mode'],x['r'],x['period_us'],x['fork']):x for x in forks};comparisons=[]
metric_names=['foreground_us','background_e2e_p95_us','observed_protected_us','observed_protected_call_p95_us']
for against in ['rebase','three']:
 for r in [0,2]:
  for period in [0,10,100,1000]:
   batch=lookup[('batch',r,period)];other=lookup[(against,r,period)]
   ratios={k:batch['metrics'][k]['median']/other['metrics'][k]['median'] for k in metric_names}
   paired={k:[byfork[('batch',r,period,f)]['metrics'][k]['median']/byfork[(against,r,period,f)]['metrics'][k]['median'] for f in range(1,7)] for k in metric_names}
   comparisons.append(dict(against=against,r=r,period_us=period,pooled_median_ratios=ratios,block_median_ratios=paired,blocks_with_batch_smaller={k:sum(x<1 for x in values) for k,values in paired.items()}))
nulls=[]
for mode in ['rebase','batch']:
 for period in [0,10,100,1000]:
  # In this unrelated-update workload both r values always complete by rebase,
  # hence never consult the cheap-failure allowance. Verify before using as a
  # descriptive same-policy variation check.
  relevant=[x for x in rows if x['mode']==mode];assert all(x['counters']['Calls']==32 and x['counters']['CheapFailures']==x['counters']['PreparedInside']==0 for x in relevant)
  nulls.append(dict(mode=mode,period_us=period,pooled_r0_over_r2={k:lookup[(mode,0,period)]['metrics'][k]['median']/lookup[(mode,2,period)]['metrics'][k]['median'] for k in metric_names},block_r0_over_r2={k:[byfork[(mode,0,period,f)]['metrics'][k]['median']/byfork[(mode,2,period,f)]['metrics'][k]['median'] for f in range(1,7)] for k in metric_names}))
report=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='PASS',all_units=1728,measurement=1440,warmup=288,processes=36,semantic_checker='PASS',quantile='nearest rank within each batch; process/cell aggregation explicitly labeled',cells=cells,per_fork_cells=forks,comparisons=comparisons,same_policy_variation=nulls,warmup_statuses=dict(collections.Counter(x['status'] for x in rows if x['phase']=='warmup')),source_checker_sha256=hashlib.sha256((D/'run01/check01/RECEIPT.json').read_bytes()).hexdigest(),analysis_seconds=time.monotonic()-start,scope='Six cyclic process positions, changed batch-source comparator, nonblocking timestamp observer. Lock-enter to terminal-hook interval excludes acquisition/release; not total lock residency, additive native repair cost or inferential speedup.')
(O/'SUMMARY.json').write_text(json.dumps(report,indent=2)+'\n')
header=['mode','r','period_us','n','FG_us_median','BG_p95_us_median','observed_protected_us_median','observed_protected_call_p95_us_median','Q_median','full_inside_total','rebase_total'];table=[]
for c in cells:
 m=c['metrics'];table.append([c['mode'],c['r'],c['period_us'],60,m['foreground_us']['median'],m['background_e2e_p95_us']['median'],m['observed_protected_us']['median'],m['observed_protected_call_p95_us']['median'],m['calls']['median'],c['totals']['PreparedInside'],c['totals']['Rebases']])
with (O/'CELLS.tsv').open('w') as f:w=csv.writer(f,delimiter='\t');w.writerow(header);w.writerows(table)
print('status PASS,1728checked units,24cells; ratios batch/comparator',flush=True)
for x in comparisons:print(json.dumps({k:v for k,v in x.items() if k!='block_median_ratios'}),flush=True)
print('same-policy variation',json.dumps([{k:v for k,v in x.items() if k!='block_r0_over_r2'} for x in nulls]),flush=True)
