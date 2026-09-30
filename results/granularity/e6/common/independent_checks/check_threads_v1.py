#!/usr/bin/env python3
"""Read-only independent Threads raw, endpoint product, and proof-mechanism audit."""
import collections,csv,hashlib,importlib.util,itertools,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
E6=Path(__file__).resolve().parents[2];P=E6/'threads/v1'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location('ep',E6/'rolling/validate_endpoints.py');ep=importlib.util.module_from_spec(spec);spec.loader.exec_module(ep)
c=read(P/'config.json');manifest=read(P/'build/frozen_manifest.json')
for f,h in manifest['files'].items():assert sha(E6/f)==h,f
assert sha(Path(manifest['jar_path']))==manifest['jar_sha256']
rows=list(csv.DictReader((P/'summary.csv').open()));table=list(csv.DictReader((P/'tables/results.csv').open()));assert rows==table
by={r['job_id']:r for r in rows};assert len(rows)==len(by)==len(c['jobs'])==80
endpoints=[]
for path in sorted((P/'inputs').glob('*.json')):
 d=read(path);n=d['parameters']['n'];B=d['parameters']['B'];expected=set(itertools.product(*[x['old']['states'] for x in d['components']]))
 assert len(expected)==(B+1)*2**n and d['requirements']==[] and d['precedence']==[]
 for version in ('old','new'):
  report=ep.validate(d,version);assert report['projected_states']==len(expected)
  projection=d['endpoints'][version]['projection']
  assert all(v==version.upper() for x in projection.values() for v,s in x['physical'])
  actual={tuple(s for v,s in x['physical']) for x in projection.values()};assert actual==expected
  if version=='new':assert set(d['endpoints'][version]['loadable'])==set(d['endpoints'][version]['lts']['states'])
 endpoints.append({'input':path.name,'states_per_endpoint':len(expected),'sha256':sha(path)})
assert len(endpoints)==40
checks=[]
for idx,j in enumerate(c['jobs'],1):
 raw=P/'raw/series'/j['id'];r=read(raw/'result.json');cert=read(raw/'certificate.json');inv=read(raw/'invocation.json');end=read(raw/'completion.json');row=by[j['id']];d=read(P/j['input']);n=j['parameters']['n'];B=j['parameters']['B'];regime=j['parameters']['regime']
 assert int(row['schedule_index'])==idx
 assert not end['timed_out'] and end['exit_code']==(0 if r['decision']=='WIN' else 2)
 for f,h in end['files'].items():assert sha(raw/f)==h
 assert sha(P/j['input'])==r['input_sha256']==inv['input_sha256']==row['input_sha256']
 assert r['certificate_sha256']==sha(raw/'certificate.json')
 assert row['jar_sha256']==manifest['jar_sha256'] and row['frozen_manifest_sha256']==sha(P/'build/frozen_manifest.json')
 assert r['decision']==cert['decision']==row['decision']==j['expected_decision']
 for k in ['states_discovered','successor_queries','materialized_transitions','enabled_buckets','worst_completion_rank','losing_region_states','certificate_states']:
  assert row[k]==('' if r[k] is None else str(r[k])),(j['id'],k)
 assert r['certificate_checker']=='PASS' and r['endpoint_checker']=='PASS'
 ss={s['id']:s for s in cert['states']};assert len(ss)==len(cert['states'])==r['certificate_states']
 for s in ss.values():
  assert len(s['physical'])==n and not s['testers'] and s['safe']
  for i,(v,x) in enumerate(s['physical']):assert v in ('OLD','NEW') and x in d['components'][i]['old']['states']
 if r['decision']=='WIN':
  assert regime=='backpressure' and r['link_checker']=='PASS'
  roots={i for i,s in ss.items() if s['initial']};assert len(roots)==(B+1)*2**n
  actual_initial={tuple(x for v,x in ss[i]['physical']) for i in roots};assert actual_initial==set(itertools.product(*[x['old']['states'] for x in d['components']]))
  edges=collections.defaultdict(list);transfers=0
  for src,a,dst in cert['strategy_edges']:
   q,t=ss[src],ss[dst];assert q['rank']>t['rank'];edges[src].append(dst)
   if a.startswith('rho_') or a=='ablation.merge.transfers':
    changes=[i for i,(x,y) in enumerate(zip(q['physical'],t['physical'])) if x!=y];assert changes
    assert q['physical'][0][1].split('_q')[1]==t['physical'][0][1].split('_q')[1]
    for i in changes:
     (v,x),(w,y)=q['physical'][i],t['physical'][i];assert v=='OLD' and w=='NEW' and x==y and x.startswith('I')
    transfers+=1
  seen=set(roots);queue=collections.deque(roots)
  while queue:
   for dst in edges[queue.popleft()]:
    if dst not in seen:seen.add(dst);queue.append(dst)
  assert seen==set(ss)
  for i,s in ss.items():assert bool(edges[i]) != s['goal']
  assert max(s['rank'] for s in ss.values())==r['worst_completion_rank']
  evidence={'initial_product_states':len(roots),'transfer_edges_checked':transfers,'reason':'Returned rank strictly decreases; all old endpoint states covered; transfers are idle-only and preserve queued work.'}
 else:
  assert regime=='saturated_offers' and len(ss)==r['losing_region_states']
  roots=[s for s in ss.values() if s['initial'] and int(s['physical'][0][1].split('_q')[1])==B];assert roots
  for s in roots:
   assert not s['goal'] and all(v=='OLD' for v,x in s['physical']) and s['pending']
   owner=[]
   for i,(v,x) in enumerate(s['physical']):
    edges=d['components'][i]['old']['edges'];alpha={a for _,a,_ in edges}
    if 'arrival' in alpha:owner.append(i);assert [x,'arrival',x] in edges
   assert owner==[0] and 'arrival' not in d['controllable']
  evidence={'full_queue_initial_self_loop_states':len(roots),'action':'arrival','reason':'Actual losing-certificate initial state has a physical UC arrival self-loop and pending updates; repeated UC offers avoid strong completion without fairness.'}
 if 'compare_input' in j:assert r['game_equivalence']['status']=='PASS'
 checks.append({'job_id':j['id'],'decision':r['decision'],**evidence})
pairs=list(csv.DictReader((P/'tables/pairs.csv').open()));assert len(pairs)==20
for p in pairs:
 base=f"threads_n{int(p['n']):02}_b{int(p['B']):02}_{p['regime']}";fine,merged,generated,df=[by[base+'_'+s] for s in ['fine_lazy','e1merged_lazy','generated_all_lazy','fine_df']]
 for k in ['decision','states_discovered','successor_queries','materialized_transitions','enabled_buckets','worst_completion_rank','losing_region_states']:assert merged[k]==generated[k]
 assert fine['decision']==df['decision']==merged['decision']
 assert p['category']==('null' if fine['decision']=='WIN' else 'both_loss')
 assert p['generated_equivalence']==p['df_decision_check']=='PASS'
report={'status':'PASS','jobs':80,'wins':sum(x['decision']=='WIN' for x in checks),'losses':sum(x['decision']=='LOSS' for x in checks),'pairs':20,'endpoint_products':80,'full_post_equivalence_pass':sum('compare_input' in j for j in c['jobs']),'frozen_files':len(manifest['files']),'scope':'Independent read-only raw/CSV/SHA, full endpoint product and all initial-state coverage, strategy rank/domain/idle transfer preservation, and certificate-supported UC-loop evidence. Parent independently reconstructs complete Post games; no JVM or new measurement here.','endpoints':endpoints,'checks':checks}
with Path(__file__).with_name('threads_v1_review.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print({k:v for k,v in report.items() if k not in ['endpoints','checks']})
