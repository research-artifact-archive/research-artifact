#!/usr/bin/env python3
import collections,csv,hashlib,json
from pathlib import Path
E6=Path(__file__).resolve().parents[2];P=E6/'canary/v1'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
c=read(P/'config.json');rows={r['job_id']:r for r in csv.DictReader((P/'summary.csv').open())};assert len(rows)==len(c['jobs'])==60
manifest=read(P/'build/frozen_manifest.json')
for f,h in manifest['files'].items():assert sha(E6/f)==h,f
assert sha(Path(manifest['jar_path']))==manifest['jar_sha256']
checks=[]
for j in c['jobs']:
 p=P/'raw/series'/j['id'];r=read(p/'result.json');cert=read(p/'certificate.json');inv=read(p/'invocation.json');end=read(p/'completion.json');row=rows[j['id']];inp=read(P/j['input']);n=j['parameters']['n'];m=j['parameters']['m']
 assert not end['timed_out'] and end['exit_code']==(0 if r['decision']=='WIN' else 2)
 for f,h in end['files'].items():assert sha(p/f)==h
 assert sha(p/'certificate.json')==r['certificate_sha256']
 assert sha(P/j['input'])==r['input_sha256']==inv['input_sha256']
 assert r['decision']==cert['decision']==row['decision']==j['expected_decision']
 for k in ['states_discovered','successor_queries','materialized_transitions','enabled_buckets','worst_completion_rank','losing_region_states']:
  assert row[k]==('' if r[k] is None else str(r[k])),(j['id'],k)
 assert r['materialized_transitions']>r['enabled_buckets'],'set-valued outcomes must exceed buckets here'
 states=cert['states'];assert len(states)==r['certificate_states'];byid={s['id']:s for s in states}
 if r['decision']=='WIN':
  assert all(s['safe'] and sum(v=='OLD' or x in ('H','HP') for v,x in s['physical'])>=m for s in states)
  assert max(s['rank'] for s in states)==r['worst_completion_rank']
  assert r['link_checker']=='PASS'
  for a,event,b in cert['strategy_edges']:assert byid[a]['rank']>byid[b]['rank']
  evidence='all winning certificate nodes satisfy actual physical healthy>=m; every stored policy edge strictly decreases rank'
 else:
  assert len(states)==r['losing_region_states'];summary=r['loss_summary'];assert sum(not s['safe'] for s in states)==summary['unsafe_region_states']
  root=next(s for s in states if s['initial']);bucket=next(b for b in summary['initial_examples'][0]['enabled_action_buckets'] if b['action']=='ablation.merge.transfers');assert bucket['outcomes']==2**n
  tester=inp['requirements'][0]['tester'];delta={(a,event):b for a,event,b in tester['changes']};errors=set(tester['errors'])
  def key(physical,tester):return (tuple(tuple(x) for x in physical),tester)
  nodes={key(s['physical'],s['testers']['reported_availability']):s for s in states}
  initial=key([['NEW','BP'] for _ in range(n)],root['testers']['reported_availability']);assert initial in nodes
  todo=collections.deque([(initial,[])]);seen={initial};trace=None
  while todo:
   q,path=todo.popleft()
   if q[1] in errors:trace=path;break
   for i,(v,x) in enumerate(q[0]):
    if x!='BP':continue
    action=f'reportB_{i+1}';physical=list(q[0]);physical[i]=('NEW','B');nextq=(tuple(physical),delta.get((q[1],action),q[1]))
    if nextq in nodes and nextq not in seen:seen.add(nextq);todo.append((nextq,path+[action]))
  assert trace is not None and len(trace)==n-m+1
  evidence=f'all-broken transfer outcome belongs to losing certificate and reaches tester error in {len(trace)} one-shot UC reports'
 if 'compare_input' in j:assert r['game_equivalence']['status']=='PASS'
 checks.append({'job_id':j['id'],'decision':r['decision'],'evidence':evidence})
report={'status':'PASS','jobs':len(checks),'wins':sum(x['decision']=='WIN' for x in checks),'losses':sum(x['decision']=='LOSS' for x in checks),'frozen_files':len(manifest['files']),'checks':checks,'scope':'Read-only independent raw/CSV/provenance/certificate-mechanism checks; no JVM or new measurement.'}
out=Path(__file__).with_name('canary_v1_review.json')
with out.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print({k:v for k,v in report.items() if k!='checks'})
