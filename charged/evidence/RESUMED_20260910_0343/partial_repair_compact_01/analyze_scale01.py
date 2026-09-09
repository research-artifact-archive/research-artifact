from pathlib import Path
from fractions import Fraction as F
import collections,datetime,hashlib,json,statistics,time
from compact01 import check_certificate
P=Path(__file__).resolve().parent;S=P/'scale01';O=P/'scale_analysis01';O.mkdir();start=time.monotonic()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(n,x):
 with (O/n).open('x') as f:json.dump(x,f,indent=2);f.write('\n')
rows=json.loads((S/'OUTCOMES.json').read_text());inputs=json.loads((S/'INPUTS.json').read_text());assert len(rows)==len(inputs)==216
checked=0;by={};failures=[]
for i,(r,x) in enumerate(zip(rows,inputs),1):
 assert r['index']==i and r['input']==x
 d=S/f'u{i:03}'
 for name,key in [('stdout.jsonl','stdout_sha256'),('stderr.txt','stderr_sha256')]:assert sha(d/name)==r[key]
 if r['status']!='SUCCESS':continue
 raw=[json.loads(s) for s in (d/'stdout.jsonl').read_text().splitlines()];assert len(raw)==2;z=raw[-1];m=x['m'];weights=[1 if x['pattern']=='uniform' else 1+(37*j%97) for j in range(m)];W=sum(weights);mu=W if x['mu']=='W' else int(x['mu'])
 assert raw[0]['weights_sha256']==hashlib.sha256(json.dumps(weights,separators=(',',':')).encode()).hexdigest()
 order=sorted(range(m),key=lambda j:(-weights[j],j));assert z['sorted_component_order']==order
 G=[0]
 for j in order:G.append(G[-1]+weights[j])
 assert z['coverage_profile']==G and z['total_work']==W and z['mu']==mu
 if x['method']=='compact':check_certificate(G,G,mu,x['q'],W,z['certificate']);checked+=1;assert F(z['ratio'])==F(z['certificate']['ratio'])
 key=(x['grid'],m,x['pattern'],x['q'],x['mu']);by.setdefault(key,{})[x['method']]=r
pairs=[]
for key,arms in by.items():
 if key[0]!='paired':continue
 if len(arms)==2:
  c=arms['compact'];b=arms['profiledp'];assert F(c['result']['ratio'])==F(b['result']['ratio'])
  pairs.append(dict(input=key,ratio=c['result']['ratio'],compact_process_seconds=c['seconds'],profiledp_process_seconds=b['seconds'],profiledp_over_compact=b['seconds']/c['seconds']))
groups=[]
for grid,method in [('large','compact'),('paired','compact'),('paired','profiledp')]:
 rr=[r for r in rows if r['input']['grid']==grid and r['input']['method']==method];ss=[r for r in rr if r['status']=='SUCCESS']
 groups.append(dict(grid=grid,method=method,units=len(rr),statuses=dict(collections.Counter(r['status'] for r in rr)),process_seconds_range=[min(r['seconds'] for r in ss),max(r['seconds'] for r in ss)],peak_rss_bytes_max=max(r['result']['peak_rss_bytes'] for r in ss),returned_artifact_bytes_max=max(r['artifact_bytes'] for r in ss)))
summary=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='PASS',planned=216,rows=216,groups=groups,certificates_rechecked=checked,joint_successes=len(pairs),all_joint_ratios_equal=True,complete_adverse_rows=[r for r in rows if r['status']!='SUCCESS'],paired_median_profiledp_over_compact=statistics.median(r['profiledp_over_compact'] for r in pairs),analysis_seconds=time.monotonic()-start,raw_outcomes_sha256=sha(S/'OUTCOMES.json'),scope='Single-process-per-cell descriptive construction times with different returned services. Joint-success ratio is censored by fixed timeouts; no population, inferential speedup, native calibration or enforced RSS claim.')
put('PAIRS.json',pairs);put('SUMMARY.json',summary);print(json.dumps({k:v for k,v in summary.items() if k!='complete_adverse_rows'},indent=2),flush=True)
