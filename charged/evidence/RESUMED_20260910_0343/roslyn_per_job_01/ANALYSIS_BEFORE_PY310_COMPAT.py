from pathlib import Path
import collections,datetime,hashlib,json,math,random,statistics,time
D=Path(__file__).resolve().parent;O=D/'analysis01';O.mkdir();start=time.perf_counter();rng=random.Random(9101113)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,d):
 with p.open('x') as f:json.dump(d,f,indent=2);f.write('\n')
receipt=json.loads((D/'run01/check01/RECEIPT.json').read_text());assert receipt['status']=='PASS' and receipt['raw_units']==3072
rows=[]
for name,expected in receipt['raw_sha256'].items():
 p=D/'run01'/name;assert sha(p)==expected;rows.extend(json.loads(x) for x in p.read_text().splitlines())
assert len(rows)==3072 and collections.Counter(r['phase'] for r in rows)=={'warmup':512,'measurement':2560}
dump(O/'INPUT_RECEIPT.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_sha256=sha(Path(__file__)),plan_sha256=sha(D/'PLAN.md'),checker_receipt_sha256=sha(D/'run01/check01/RECEIPT.json'),bootstrap_seed=9101113,resamples=10000,estimator='geometric mean of8 paired block ratios of within-process medians; percentile95% interval',new_native_runs=0))
def summary(xs):
 xs=sorted(xs);assert xs
 return dict(n=len(xs),min=xs[0],median=statistics.median(xs),p95_nearest_rank=xs[math.ceil(.95*len(xs))-1],max=xs[-1])
def metrics(row):
 return dict(foreground_us=row['foreground_ns']/1000,writer_response_median_us=statistics.median((x['returned_ns']-x['intended_ns'])/1000 for x in row['writer_requests']),writer_service_median_us=statistics.median((x['returned_ns']-x['invoked_ns'])/1000 for x in row['writer_requests']))
arms=[('baseline',0),('original',0),('two',2),('three',2),('per-job-two',1),('per-job-three',1),('per-job-two',2),('per-job-three',2)]
measured=[r for r in rows if r['phase']=='measurement'];groups=collections.defaultdict(list)
for row in measured:groups[row['mode'],row['r'],row['period_us']].append(row)
cells=[];process_metrics={}
for mode,r in arms:
 for period in [0,10,100,1000]:
  selected=groups[mode,r,period];assert len(selected)==80 and collections.Counter(x['fork'] for x in selected)=={i:10 for i in range(1,9)}
  values=[metrics(x) for x in selected];names=list(values[0]);process=[]
  for block in range(1,9):
   vals=[metrics(x) for x in selected if x['fork']==block];med={k:statistics.median(v[k] for v in vals) for k in names};process_metrics[mode,r,period,block]=med;process.append(dict(block=block,medians=med))
  counts=dict(B_fg=summary([x['actual_writes_during_foreground'] for x in selected]))
  if mode!='baseline':
   for k in ['Calls','PreparedInside','PreparedOutside','CheapFailures']:counts[k]=summary([x['counters'][k] for x in selected])
  cells.append(dict(mode=mode,r=r,period_us=period,units=80,processes=8,metrics={k:summary([v[k] for v in values]) for k in names},counts=counts,process_medians=process))
contrasts=[(('original',0),('baseline',0)),(('three',2),('two',2)),(('per-job-two',1),('two',2)),(('per-job-three',1),('three',2)),(('per-job-two',2),('per-job-two',1)),(('per-job-three',2),('per-job-three',1)),(('per-job-three',1),('per-job-two',1)),(('per-job-three',2),('per-job-two',2))]
paired=[]
for numerator,denominator in contrasts:
 for period in [0,10,100,1000]:
  for metric in ['foreground_us','writer_response_median_us','writer_service_median_us']:
   ratios=[process_metrics[*numerator,period,i][metric]/process_metrics[*denominator,period,i][metric] for i in range(1,9)];logs=[math.log(v) for v in ratios]
   boot=sorted(math.exp(sum(logs[rng.randrange(8)] for _ in range(8))/8) for _ in range(10000))
   paired.append(dict(numerator=list(numerator),denominator=list(denominator),period_us=period,metric=metric,paired_process_ratios=ratios,geometric_mean_ratio=math.exp(sum(logs)/8),percentile95=[boot[249],boot[9749]],n_blocks=8,resamples=10000))
result=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='PASS',seconds=time.perf_counter()-start,all_units=len(rows),measurement=2560,warmup=512,cells=cells,paired_ratios=paired,new_native_runs=0,new_timing_samples=0,scope='Analysis of fixed authored arrivals. Paired process-block intervals are descriptive, with8 independent process blocks and no multiplicity correction. Contracts differ: shared r2 Q<=34; per-job r1 Q<=64; per-job r2 Q<=96. B_fg is policy-end dependent. Instrumentation and authored workload limit transfer to deployment.')
dump(O/'SUMMARY.json',result)
with (O/'CELLS.tsv').open('x') as f:
 f.write('mode\tr\tperiod_us\tforeground_us\twriter_response_median_us\twriter_service_median_us\tB_fg\tQ\tinside\n')
 for x in cells:
  v=[x['mode'],x['r'],x['period_us'],*[x['metrics'][k]['median'] for k in ['foreground_us','writer_response_median_us','writer_service_median_us']],x['counts']['B_fg']['median'],x['counts'].get('Calls',{}).get('median','NA'),x['counts'].get('PreparedInside',{}).get('median','NA')];f.write('\t'.join(map(str,v))+'\n')
print(json.dumps(dict(status='PASS',units=len(rows),cells=len(cells),paired_intervals=len(paired),seconds=result['seconds'])),flush=True)
