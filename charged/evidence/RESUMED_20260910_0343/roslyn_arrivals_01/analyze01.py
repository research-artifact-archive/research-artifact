from pathlib import Path
import collections,csv,datetime,hashlib,json,math,statistics
D=Path(__file__).resolve().parent;O=D/'analysis01';O.mkdir()
rows=[json.loads(line) for p in sorted((D/'run01').glob('p*/stdout.jsonl')) for line in p.read_text().splitlines()]
assert len(rows)==864 and all(x['status']=='SUCCESS' for x in rows)
def quantile(x,p):s=sorted(x);return s[max(0,min(len(s)-1,math.ceil(p*len(s))-1))]
def stats(x):return {'n':len(x),'min':min(x),'median':statistics.median(x),'p95_nearest_rank':quantile(x,.95),'max':max(x)}
def metrics(row):
 bg=row['writer_requests'];fg=row['foreground_requests'];c=row['counters'];v={'foreground_us':row['foreground_ns']/1000,'foreground_call_p95_us':quantile([(x['returned_ns']-x['invoked_ns'])/1000 for x in fg],.95),'background_e2e_median_us':statistics.median([(x['returned_ns']-x['intended_ns'])/1000 for x in bg]),'background_e2e_p95_us':quantile([(x['returned_ns']-x['intended_ns'])/1000 for x in bg],.95),'background_queue_p95_us':quantile([(x['invoked_ns']-x['enqueued_ns'])/1000 for x in bg],.95),'background_service_p95_us':quantile([(x['returned_ns']-x['invoked_ns'])/1000 for x in bg],.95),'producer_lateness_p95_us':quantile([(x['enqueued_ns']-x['intended_ns'])/1000 for x in bg],.95),'writes_during_foreground':row['actual_writes_during_foreground'],'setup_ms':row['setup_ns']/1e6,'whole_unit_ms':row['whole_unit_ns']/1e6,'foreground_gc_events':sum(row['foreground_gc_collections'])}
 if c:v.update({'calls':c['Calls'],'cheap_failures':c['CheapFailures'],'protected_transformations':c['PreparedInside'],'total_transformations':c['PreparedInside']+c['PreparedOutside'],'mismatches':c['Mismatches']})
 return v
arms=[('baseline',0),('original',0),('two',0),('three',0),('two',2),('three',2)]
cells=[];forks=[]
for mode,r in arms:
 for period in [0,10,100,1000]:
  relevant=[x for x in rows if x['phase']=='measurement' and (x['mode'],x['r'],x['period_us'])==(mode,r,period)];values=[metrics(x) for x in relevant];assert len(values)==30
  cell={'mode':mode,'r':r,'period_us':period,'units':len(relevant),'forks':3,'metrics':{k:stats([v[k] for v in values]) for k in values[0]},'totals':{k:sum(x['counters'].get(k,0) for x in relevant) for k in ['Calls','CheapFailures','PreparedInside','PreparedOutside','Mismatches']},'units_with_any_mismatch':sum(x['counters'].get('Mismatches',0)>0 for x in relevant) if mode!='baseline' else None};cells.append(cell)
  for fork in [1,2,3]:
   vs=[metrics(x) for x in relevant if x['fork']==fork];forks.append({'mode':mode,'r':r,'period_us':period,'fork':fork,'units':10,'metrics':{k:stats([v[k] for v in vs]) for k in vs[0]}})
lookup={(x['mode'],x['r'],x['period_us']):x for x in cells}
for cell in cells:
 period=cell['period_us'];m=cell['metrics'];cell['median_ratios']={k:{metric:m[metric]['median']/lookup[(k,0,period)]['metrics'][metric]['median'] for metric in ['foreground_us','background_e2e_median_us','background_e2e_p95_us']} for k in ['baseline','original']}
report={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'all_units':864,'measurement':720,'warmup':144,'semantic_checker':'PASS','quantile':'nearest rank, within unit then across units as labeled','process_order_caveat':'Fixed random shuffle placed all three instrumented-original forks first; process order is a possible thermal/JIT/load confound and was not changed after observation. No rerun or causality claim.','cells':cells,'per_fork_cells':forks,'warmup_statuses':dict(collections.Counter(x['status'] for x in rows if x['phase']=='warmup')),'source_checker_sha256':hashlib.sha256((D/'run01/check01/RECEIPT.json').read_bytes()).hexdigest()}
(O/'SUMMARY.json').write_text(json.dumps(report,indent=2)+'\n')
header=['arm','interval_us','n','Q_median','L_count_median','W_count_median','B_fg_median','FG_us_median','FG_us_p95','BG_e2e_median_us','BG_e2e_p95_us_median','enqueue_late_p95_us_median','FG_ratio_original','FG_ratio_baseline']
table=[]
for c in cells:
 m=c['metrics'];get=lambda k:m.get(k,{}).get('median','NA')
 table.append([c['mode']+('_r'+str(c['r']) if c['mode'] in ('two','three') else ''),c['period_us'],30,get('calls'),get('protected_transformations'),get('total_transformations'),get('writes_during_foreground'),get('foreground_us'),m['foreground_us']['p95_nearest_rank'],get('background_e2e_median_us'),get('background_e2e_p95_us'),get('producer_lateness_p95_us'),c['median_ratios']['original']['foreground_us'],c['median_ratios']['baseline']['foreground_us']])
with (O/'CELLS.tsv').open('w') as f:w=csv.writer(f,delimiter='\t');w.writerow(header);w.writerows(table)
print('\t'.join(header))
for row in table:print('\t'.join(f'{v:.3f}' if isinstance(v,float) else str(v) for v in row))
print(json.dumps({'total_counters_by_arm':{mode+'_r'+str(r):{field:sum(x['counters'].get(field,0) for x in rows if x['phase']=='measurement' and (x['mode'],x['r'])==(mode,r)) for field in ['Calls','CheapFailures','PreparedInside','PreparedOutside','Mismatches']} for mode,r in arms}}))
