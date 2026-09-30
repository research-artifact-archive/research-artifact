#!/usr/bin/env python3
import csv,hashlib,importlib.util,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
E6=Path(__file__).resolve().parents[2];P=E6/'rolling_audit/v1'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location('independent_rolling',E6/'rolling/validate_endpoints.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
endpoints=[]
for p in sorted((P/'inputs').glob('*.json')):
 data=read(p)
 endpoints.append({'input':p.name,'old':module.validate(data,'old'),'new':module.validate(data,'new')})
 new=next(r for r in data['requirements'] if r['id']=='audit_new');entries=new['activation']['entries'];assert len(entries)==9 and len({str(e['physical']) for e in entries})==9 and all(e['tester_state']==e['residual_state']=='unlogged' for e in entries)
m=read(P/'build/frozen_manifest.json')
for f,h in m['files'].items():assert sha(E6/f)==h
assert sha(Path(m['jar_path']))==m['jar_sha256']
rows={r['job_id']:r for r in csv.DictReader((P/'summary.csv').open())};c=read(P/'config.json');assert len(rows)==len(c['jobs'])==8;results={};equiv=0
for j in c['jobs']:
 p=P/'raw/series'/j['id'];r=read(p/'result.json');cert=read(p/'certificate.json');completion=read(p/'completion.json');row=rows[j['id']];results[j['id']]=r
 assert not completion['timed_out'] and completion['exit_code']==(0 if r['decision']=='WIN' else 2)
 for f,h in completion['files'].items():assert sha(p/f)==h
 assert sha(p/'certificate.json')==r['certificate_sha256'] and sha(P/j['input'])==r['input_sha256']
 assert r['decision']==row['decision']==cert['decision']==j['expected_decision']
 for k in ['states_discovered','successor_queries','materialized_transitions','enabled_buckets','worst_completion_rank','losing_region_states']:
  assert row[k]==('' if r[k] is None else str(r[k]))
 assert len(cert['states'])==r['certificate_states']
 if r['decision']=='WIN':
  for s in cert['states']:
   assert s['safe'] and sum(x=='ready' for v,x in s['physical'])>=1
   assert any(a in s['testers'] for a in ('audit_old','audit_new'))
   expected='ready'+str(sum(x=='ready' for v,x in s['physical']))+'_old'+str(int('audit_old' in s['testers']))+'_new'+str(int('audit_new' in s['testers']))
   assert s['testers']['availability_audit_coverage']==expected
  byid={s['id']:s for s in cert['states']};assert max(s['rank'] for s in cert['states'])==r['worst_completion_rank']
  for a,event,b in cert['strategy_edges']:assert byid[a]['rank']>byid[b]['rank']
 else:
  assert r['losing_region_states']==len(cert['states']) and any(not s['safe'] and all(x=='booting' for v,x in s['physical']) for s in cert['states'])
 if 'game_equivalence' in r:assert r['game_equivalence']['status']=='PASS';equiv+=1
assert equiv==3
for a,b in [('fine_none_lazy','fine_boundaries_lazy'),('fine_transfers_lazy','fine_both_lazy')]:
 for k in ['decision','states_discovered','successor_queries','worst_completion_rank','losing_region_states']:assert results[a][k]==results[b][k]
path=read(P/'tables/me_six_step_path.json');certpath=P/path['source'];assert sha(certpath)==path['sha256'];cert=read(certpath);nodes={s['id']:s for s in cert['states']};edges={tuple(e) for e in cert['strategy_edges']}
trace=path['path'];assert len(trace)==7 and path['events']==6
for a,b in zip(trace,trace[1:]):assert (a['state_id'],b['event'],b['state_id']) in edges
for q in trace:assert q['rank']==nodes[q['state_id']]['rank'] and q['goal']==nodes[q['state_id']]['goal']
assert nodes[trace[0]['state_id']]['initial'] and nodes[trace[-1]['state_id']]['goal']
report={'status':'PASS','jobs':8,'wins':4,'losses':4,'full_post_equivalence_checks':equiv,'endpoints':endpoints,'six_step_path':'verified against stored measured Lazy certificate; the other root has rank 7','single_audit_pair_boundary_merge':'none/boundaries and transfers/both have identical decision/states/query/rank/losing counts','scope':'Read-only raw/CSV/SHA/frozen and independent plant-controller-testers endpoint products; no JVM.'}
with Path(__file__).with_name('rolling_audit_v1_review.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print({k:v for k,v in report.items() if k!='endpoints'})
