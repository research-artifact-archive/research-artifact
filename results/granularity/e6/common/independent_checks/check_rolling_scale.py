#!/usr/bin/env python3
"""Lightweight Rolling scale audit: saved policies only, never full-game enumeration."""
import argparse,collections,csv,hashlib,importlib.util,json,sys,time
from pathlib import Path
sys.dont_write_bytecode=True
E6=Path(__file__).resolve().parents[2];P=E6/'rolling_scale/v1'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
V=module('post_v3',E6/'independent/check_games_v3.py');EP=module('endpoint',E6/'rolling/validate_endpoints.py')

def certificate(model,proof):
 byid={q['id']:V.from_json(q) for q in proof['states']};nodes=set(byid.values());assert len(nodes)==len(byid)==len(proof['states'])
 for q in proof['states']:
  s=byid[q['id']];assert model.valid(s)
  assert q['initial']==(s in model.roots) and q['safe']==model.safe(s) and q['goal']==model.goal(s)
 if proof['decision']=='WIN':
  assert model.roots<=nodes
  ranks={byid[q['id']]:q['rank'] for q in proof['states']};edges=collections.defaultdict(lambda:collections.defaultdict(set))
  for src,a,dst in proof['strategy_edges']:edges[byid[src]][a].add(byid[dst])
  for s in nodes:
   assert model.safe(s)
   # Exactly two required actions per old replica; exactly one per booting new replica.
   minimum_rank=2*sum(v=='OLD' for v,q in s[0])+sum(q=='booting' for v,q in s[0]);assert ranks[s]==minimum_rank
   if model.goal(s):assert ranks[s]==0 and not edges[s];continue
   buckets=model.post(s);uc={a for a in buckets if a not in model.control and a not in model.updates}
   if uc:assert set(edges[s])==uc
   else:assert len(edges[s])==1
   for a,targets in edges[s].items():
    assert a in buckets and targets==buckets[a],('Incomplete/invented Post bucket',a)
    assert all(t in nodes and ranks[t]<ranks[s] for t in targets)
  reached=set(model.roots);queue=collections.deque(reached)
  while queue:
   for targets in edges[queue.popleft()].values():
    for t in targets-reached:reached.add(t);queue.append(t)
  assert reached==nodes
  return {'checked_policy_states':len(nodes),'checked_strategy_edges':len(proof['strategy_edges']),'minimum_worst_root_rank':max(ranks[s] for s in model.roots)}
 assert model.roots.intersection(nodes)
 for s in nodes:
  assert not model.goal(s)
  if not model.safe(s):continue
  buckets=model.post(s);uc=[ts for a,ts in buckets.items() if a not in model.control and a not in model.updates]
  if uc:assert any(ts.intersection(nodes) for ts in uc)
  else:assert all(ts.intersection(nodes) for ts in buckets.values())
 return {'checked_losing_states':len(nodes),'unsafe_states':sum(not model.safe(s) for s in nodes)}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--final',action='store_true');args=ap.parse_args();start=time.monotonic()
 if args.final:
  assert (P/'raw/runner_finished.json').exists(),'Wait for fixed series termination.'
  ready=P/'build/final_tables_ready.json'
  queue_audit=E6/'integration/remaining_queue/rolling_scale_v1_4_audit.json'
  assert ready.exists() or (queue_audit.exists() and read(queue_audit)['phase']=='audit' and read(queue_audit)['exit_code']==0),'Wait for fresh final collect/audit.'
 config=read(P/'config.json');manifest=read(P/'build/frozen_manifest.json')
 for path,h in manifest['files'].items():assert sha(E6/path)==h,path
 assert sha(Path(manifest['jar_path']))==manifest['jar_sha256']
 rows=list(csv.DictReader((P/'summary.csv').open()));assert len(rows)==len(config['jobs'])==80
 if args.final:assert rows==list(csv.DictReader((P/'tables/results.csv').open()))
 by={r['job_id']:r for r in rows};inputs={};endpoints=[]
 for path in sorted((P/'inputs').glob('*.json')):
  d=read(path);n,m,k=(d['parameters'][x] for x in ('n','m','k'));assert n in range(7,17) and m in (1,n-1) and k in (1,n)
  assert len(d['components'])==n and d['precedence']==[] and len(d['requirements'])==1
  serve=[f'serve_{i+1}' for i in range(n)];ready=[f'ready_{i+1}' for i in range(n)]
  assert d['ordinary']==serve+ready and d['controllable']==serve
  transfers=['ablation.merge.transfers'] if k==n else [f'rho_{i+1}' for i in range(n)]
  for i,c in enumerate(d['components']):
   assert c['old']=={'states':['ready'],'initial':'ready','edges':[['ready',serve[i],'ready']]}
   assert c['new']=={'states':['booting','ready'],'initial':'ready','edges':[['booting',ready[i],'ready'],['ready',serve[i],'ready']]}
   assert c['transfer']=={'ready':['booting']} and c['transfer_action']==(transfers[0] if k==n else transfers[i])
  req=d['requirements'][0];assert req['role']=='interval';tester=req['tester'];assert tester['initial']==f'q{n}' and tester['errors']==['ERR_AVAILABILITY']
  assert set(tester['states'])=={f'q{i}' for i in range(m,n+1)}|{'ERR_AVAILABILITY'}
  changes=set(map(tuple,tester['changes']));expected=set()
  for count in range(m,n+1):
   for a in transfers:expected.add((f'q{count}',a,f'q{count-k}' if count-k>=m else 'ERR_AVAILABILITY'))
   for a in ready:expected.add((f'q{count}',a,f'q{min(n,count+1)}'))
  assert changes==expected
  for version in ['old','new']:
   q=EP.validate(d,version);assert q['projected_states']==1
  inputs[str(path.relative_to(P))]=d;endpoints.append({'input':str(path.relative_to(P)),'sha256':sha(path),'old_states':1,'new_states':1})
 assert len(inputs)==40
 checks=[];incomplete=[];full=[];models={}
 for index,job in enumerate(config['jobs'],1):
  row=by[job['id']];raw=P/'raw/series'/job['id'];endpath=raw/'completion.json'
  if not endpath.exists():incomplete.append({'job':job['id'],'status':row['status'],'reason':'No completed raw; no metric inferred.'});continue
  end=read(endpath);inv=read(raw/'invocation.json')
  for path,h in end['files'].items():assert sha(raw/path)==h
  assert sha(P/job['input'])==inv['input_sha256']==row['input_sha256']
  assert row['jar_sha256']==manifest['jar_sha256'] and row['frozen_manifest_sha256']==sha(P/'build/frozen_manifest.json')
  if row['decision'] not in ('WIN','LOSS'):
   assert row['decision'] in ('TO','OOM','ERROR','INVALID')
   assert all(not row[k] for k in ['states_discovered','worst_completion_rank','losing_region_states'])
   incomplete.append({'job':job['id'],'status':row['decision'],'reason':row['reason']});continue
  result=read(raw/'result.json');proof=read(raw/'certificate.json');assert result['certificate_sha256']==sha(raw/'certificate.json')
  assert result['decision']==proof['decision']==row['decision']==job['expected_decision']
  assert result['certificate_checker']=='PASS' and result['endpoint_checker']=='PASS'
  for k in ['states_discovered','successor_queries','materialized_transitions','enabled_buckets','worst_completion_rank','losing_region_states','certificate_states']:
   assert row[k]==('' if result[k] is None else str(result[k])),(job['id'],k)
  key=(job['input'],job['merge'])
  if key not in models:models[key]=V.Model(inputs[job['input']],job['merge'])
  model=models[key];n=job['parameters']['n'];m=job['parameters']['m'];audit=certificate(model,proof)
  if row['decision']=='WIN':
   assert result['link_checker']=='PASS' and result['worst_completion_rank']==2*n
   assert all(sum(q=='ready' for v,q in s['physical'])>=m for s in proof['states'])
   if row['solver']=='direct_full':
    predicted=(n+2)*2**(n-1);assert result['states_discovered']==predicted
    predicted_queries=2*n*(predicted-1)
    predicted_buckets=n*(n+3)*2**(n-1)-n
    assert result['successor_queries']==predicted_queries
    assert result['enabled_buckets']==result['materialized_transitions']==predicted_buckets
    full.append({'job':job['id'],'observed_states':result['states_discovered'],'analytical_states':predicted,'observed_queries':result['successor_queries'],'analytical_queries':predicted_queries,'observed_buckets':result['enabled_buckets'],'observed_outcomes':result['materialized_transitions'],'analytical_buckets_and_outcomes':predicted_buckets,'comparison':'PASS'})
   else:assert result['states_discovered']==2*n+1
  if 'compare_input' in job:assert result['game_equivalence']['status']=='PASS'
  checks.append({'job':job['id'],'decision':row['decision'],**audit})
 if args.final:
  pairs=list(csv.DictReader((P/'tables/scale_pairs.csv').open()));assert len(pairs)==20
  for p in pairs:
   n=int(p['n']);m=int(p['m']);base=f'n{n:02}_m{m:02}'
   assert int(p['analytical_full_states'])==(n+2)*2**(n-1) and int(p['analytical_rank'])==2*n
   for suffix,label in [('fine_lazy','fine'),('merged_lazy','merged'),('all_lazy','all'),('fine_df','df')]:
    for key in ['status','decision','states_discovered','successor_queries','worst_completion_rank','losing_region_states','solver_seconds']:assert p[label+'_'+key]==by[base+'_'+suffix][key]
   merged=by[base+'_merged_lazy'];allg=by[base+'_all_lazy']
   if merged['decision'] in ('WIN','LOSS') and allg['decision'] in ('WIN','LOSS'):
    for key in ['decision','states_discovered','successor_queries','materialized_transitions','enabled_buckets','worst_completion_rank','losing_region_states']:assert merged[key]==allg[key]
    assert p['generated_vs_e1']=='PASS'
 report={'status':'PASS','final':args.final,'observed_completed_cells':len(checks),'incomplete':incomplete,'frozen_files':len(manifest['files']),'endpoint_products':len(endpoints)*2,'direct_full_formula_checks':full,'checks':checks,'source_sha256':sha(Path(__file__)),'post_interpreter_sha256':sha(E6/'independent/check_games_v3.py'),'elapsed_seconds':time.monotonic()-start,'scope':'Only saved certificate states and their independent Post buckets are inspected. No full-game enumeration, JVM or measurement is started. Full-state formula follows 2^n stable placements plus n*2^(n-1) placements with one booting replica; enabled UC ready blocks further update events. Analytic predictions do not replace incomplete observations.'}
 out=Path(__file__).with_name('rolling_scale_final_review.json' if args.final else 'rolling_scale_progress_review.json')
 with out.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
 print({k:v for k,v in report.items() if k not in ('checks','direct_full_formula_checks')})
if __name__=='__main__':main()
