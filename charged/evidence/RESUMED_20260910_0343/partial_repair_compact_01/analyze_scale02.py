from pathlib import Path
from fractions import Fraction as F
import collections,datetime,hashlib,json,statistics,time
import compact01 as old
import compact02 as new
P=Path(__file__).resolve().parent;S=P/'scale02';O=P/'scale_analysis02';O.mkdir();start=time.monotonic()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(n,x):
 with (O/n).open('x') as f:json.dump(x,f,indent=2);f.write('\n')
rows=json.loads((S/'OUTCOMES.json').read_text());inputs=json.loads((S/'INPUTS.json').read_text());prior=json.loads((P/'scale01/OUTCOMES.json').read_text());assert len(rows)==len(inputs)==168 and len(prior)==216
key=lambda x:(x['grid'],x['m'],x['pattern'],x['q'],x['mu'],x['method'])
oldby={key(r['input']):r for r in prior};oldcomparisons=[];dpcomparisons=[];changed=[];checked=0
for i,(r,x) in enumerate(zip(rows,inputs),1):
 assert r['index']==i and r['input']==x
 d=S/f'u{i:03}'
 for name,k in [('stdout.jsonl','stdout_sha256'),('stderr.txt','stderr_sha256')]:assert sha(d/name)==r[k]
 previous=oldby[key(x)];assert previous['input']==x
 changed.append(dict(input=x,old_status=previous['status'],new_status=r['status'],old_seconds=previous['seconds'],new_seconds=r['seconds']))
 if r['status']!='SUCCESS':continue
 raw=[json.loads(s) for s in (d/'stdout.jsonl').read_text().splitlines()];assert len(raw)==2;z=raw[-1];m=x['m'];w=[1 if x['pattern']=='uniform' else 1+(37*j%97) for j in range(m)];W=sum(w);mu=W if x['mu']=='W' else int(x['mu'])
 assert raw[0]['weights_sha256']==hashlib.sha256(json.dumps(w,separators=(',',':')).encode()).hexdigest()
 order=sorted(range(m),key=lambda j:(-w[j],j));assert z['sorted_component_order']==order
 G=[0]
 for j in order:G.append(G[-1]+w[j])
 assert z['coverage_profile']==G and z['total_work']==W and z['mu']==mu
 old.check_certificate(G,G,mu,x['q'],W,z['certificate']);new.check_certificate(G,G,mu,x['q'],W,z['certificate']);checked+=1
 assert F(z['ratio'])==F(z['certificate']['ratio'])
 if previous['status']=='SUCCESS':
  assert F(z['ratio'])==F(previous['result']['ratio'])
  oldcomparisons.append(dict(input=x,ratio=z['ratio'],old_seconds=previous['seconds'],new_seconds=r['seconds']))
 if x['grid']=='paired':
  dp=oldby[key(dict(x,method='profiledp'))]
  if dp['status']=='SUCCESS':
   assert F(z['ratio'])==F(dp['result']['ratio']);dpcomparisons.append(dict(input=x,ratio=z['ratio'],old_profiledp_seconds=dp['seconds'],new_compact_seconds=r['seconds']))
 if i%24==0:print(json.dumps(dict(checked=checked,seconds=time.monotonic()-start)),flush=True)
groups=[]
for grid in ['large','paired']:
 rr=[r for r in rows if r['input']['grid']==grid];ss=[r for r in rr if r['status']=='SUCCESS']
 groups.append(dict(grid=grid,units=len(rr),statuses=dict(collections.Counter(r['status'] for r in rr)),process_seconds_range=[min(r['seconds'] for r in ss),max(r['seconds'] for r in ss)],peak_rss_bytes_max=max(r['result']['peak_rss_bytes'] for r in ss),returned_artifact_bytes_max=max(r['artifact_bytes'] for r in ss)))
summary=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='PASS',planned=168,rows=168,groups=groups,certificates_rechecked_by_both_versions=checked,old_compact_ratio_agreements=len(oldcomparisons),old_profiledp_ratio_agreements=len(dpcomparisons),previous_timeout_new_outcomes=[x for x in changed if x['old_status']=='TIMEOUT'],new_adverse_rows=[r for r in rows if r['status']!='SUCCESS'],original_adverse_rows=[r for r in prior if r['status']!='SUCCESS'],analysis_seconds=time.monotonic()-start,new_outcomes_sha256=sha(S/'OUTCOMES.json'),old_outcomes_sha256=sha(P/'scale01/OUTCOMES.json'),scope='Changed algorithm after observing version1. Old failures preserved. Single descriptive local process per cell; no inferential speedup/native cost/prevalence claim.')
put('VERSION_COMPARISONS.json',oldcomparisons);put('OLD_DP_COMPARISONS.json',dpcomparisons);put('STATUS_CHANGES.json',changed);put('SUMMARY.json',summary);print(json.dumps({k:v for k,v in summary.items() if k not in ['original_adverse_rows','new_adverse_rows']},indent=2),flush=True)
