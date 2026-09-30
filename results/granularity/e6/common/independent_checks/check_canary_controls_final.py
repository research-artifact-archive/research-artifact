#!/usr/bin/env python3
"""Read-only control audit: raw provenance, exact intervention, saved Post certificates."""
import collections,csv,hashlib,importlib.util,json,sys,time
from pathlib import Path
sys.dont_write_bytecode=True
E6=Path(__file__).resolve().parents[2];P=E6/'canary_controls/v1'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location('post_v3',E6/'independent/check_games_v3.py');V=importlib.util.module_from_spec(spec);spec.loader.exec_module(V)

def main():
 assert (P/'build/final_tables_ready.json').exists(),'Wait for fresh final tables.'
 start=time.monotonic();cfg=read(P/'config.json');manifest=read(P/'build/frozen_manifest.json')
 for path,h in manifest['files'].items():assert sha(E6/path)==h
 assert sha(Path(manifest['jar_path']))==manifest['jar_sha256']
 rows=list(csv.DictReader((P/'summary.csv').open()));assert rows==list(csv.DictReader((P/'tables/results.csv').open())) and len(rows)==len(cfg['jobs'])==48
 by={r['job_id']:r for r in rows};checks=[];models={};incomplete=[]
 for j in cfg['jobs']:
  row=by[j['id']];raw=P/'raw/series'/j['id'];endpath=raw/'completion.json'
  if not endpath.exists():incomplete.append({'job':j['id'],'status':row['status']});continue
  end=read(endpath);inv=read(raw/'invocation.json')
  for f,h in end['files'].items():assert sha(raw/f)==h
  assert inv['input_sha256']==row['input_sha256']==sha(P/j['input']) and row['jar_sha256']==manifest['jar_sha256']
  assert row['frozen_manifest_sha256']==sha(P/'build/frozen_manifest.json')
  if row['decision'] not in ('WIN','LOSS'):
   assert all(not row[k] for k in ['states_discovered','worst_completion_rank','losing_region_states'])
   incomplete.append({'job':j['id'],'status':row['decision'],'reason':row['reason']});continue
  result=read(raw/'result.json');proof=read(raw/'certificate.json');d=read(P/j['input']);control=j['parameters']['control'];n=j['parameters']['n'];m=j['parameters']['m']
  assert result['decision']==proof['decision']==row['decision']==j['expected_decision'] and not end['timed_out']
  assert result['certificate_sha256']==sha(raw/'certificate.json') and result['certificate_checker']==result['endpoint_checker']=='PASS'
  for field in ['states_discovered','successor_queries','materialized_transitions','enabled_buckets','worst_completion_rank','losing_region_states','certificate_states']:
   assert row[field]==('' if result[field] is None else str(result[field]))
  ref=P/d['metadata']['reference_input'];original=E6/'canary/v1/inputs'/ref.name;assert ref.read_bytes()==original.read_bytes()
  expected=read(ref);expected.update(id=d['id'],family='canary_controls',metadata=d['metadata']);expected['parameters']['control']=control
  for i,c in enumerate(expected['components'],1):
   if control=='healthy_only':c['transfer']['H'].remove('BP')
   else:assert control=='no_recovery';c['new']['edges'].remove(['B',f'restart_{i}','H'])
  assert expected==d
  key=(j['input'],j['merge'])
  if key not in models:models[key]=V.Model(d,j['merge'])
  model=models[key];nodes={V.from_json(s) for s in proof['states']};ranks={V.from_json(s):s['rank'] for s in proof['states']} if row['decision']=='WIN' else {}
  assert all(model.valid(s) for s in nodes)
  # The strict checker verifies exact Post closure/rank/root domain. Supplying the
  # saved node set avoids full enumeration; no minimum-rank/reachability-of-loss claim.
  certcheck=model.certificate(proof,nodes,ranks)
  rec={'job':j['id'],'decision':row['decision'],'control':control,**certcheck}
  if row['decision']=='WIN':
   assert control=='healthy_only' and result['link_checker']=='PASS'
   healthy=[sum(s in ('H','HP') for v,s in q['physical']) for q in proof['states']];assert min(healthy)==n
   assert max(q['rank'] for q in proof['states'])==result['worst_completion_rank']
   rec['minimum_physical_healthy']=min(healthy)
  else:
   assert control=='no_recovery'
   examples=[q for q in proof['states'] if any(v=='NEW' and s in ('BP','B') for v,s in q['physical'])];assert examples
   for c in d['components']:
    reached={'BP'}
    while True:
     more=reached|{t for s,a,t in c['new']['edges'] if s in reached}
     if more==reached:break
     reached=more
    assert reached=={'BP','B'}
   assert all(all(v=='NEW' and s=='H' for v,s in p['physical']) for p in d['endpoints']['new']['projection'].values())
   rec['broken_region_states']=len(examples);rec['safe_broken_region_states']=sum(q['safe'] for q in examples)
   rec['reason']='Checked losing closure includes a broken replacement in an irreversible BP/B class; mandatory all-H completion is impossible from that branch. This does not assert immediate interval error.'
  if 'compare_input' in j:assert result['game_equivalence']['status']=='PASS'
  checks.append(rec)
 pairs=list(csv.DictReader((P/'tables/pairs.csv').open()));assert len(pairs)==12
 for p in pairs:
  n=int(p['n']);m=int(p['m']);base=f"n{n:02}_m{m:02}_{p['control']}_"
  fine,merged,allg,df=[by[base+x] for x in ['fine_lazy','merged_lazy','all_lazy','fine_df']]
  for variant in ['fine','merged']:
   orig=E6/p[f'original_{variant}_result'];assert sha(orig)==p[f'original_{variant}_sha256'] and read(orig)['decision']==p[f'original_{variant}']
  for label,row in [('fine',fine),('merged',merged),('generated',allg),('df',df)]:
   for field in ['states_discovered','successor_queries','enabled_buckets','materialized_transitions','worst_completion_rank','losing_region_states']:assert p[label+'_'+field]==row[field]
  if all(row['decision'] in ('WIN','LOSS') for row in [fine,merged,allg,df]):
   assert fine['decision']==df['decision']==merged['decision']==allg['decision']
   assert p['category']==('null' if fine['decision']=='WIN' else 'both_loss')
   assert p['generated_equivalence']==p['df_decision_check']=='PASS'
   for field in ['decision','states_discovered','successor_queries','enabled_buckets','materialized_transitions','worst_completion_rank','losing_region_states']:assert merged[field]==allg[field]
 report={'status':'PASS','jobs':len(checks),'incomplete':incomplete,'wins':sum(x['decision']=='WIN' for x in checks),'losses':sum(x['decision']=='LOSS' for x in checks),'pairs':12,'frozen_files':len(manifest['files']),'checks':checks,'post_interpreter_sha256':sha(E6/'independent/check_games_v3.py'),'elapsed_seconds':time.monotonic()-start,'scope':'Read-only raw/CSV/SHA and exact registered input difference; saved-node Post closure, all outcomes, rank decrease and exact WIN root-reachable domain. No full-game enumeration/minimum-rank computation or JVM. A valid losing certificate is a root-intersecting inductive region, not the full losing set.'}
 with Path(__file__).with_name('canary_controls_final_review.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
 print({k:v for k,v in report.items() if k!='checks'})
if __name__=='__main__':main()
