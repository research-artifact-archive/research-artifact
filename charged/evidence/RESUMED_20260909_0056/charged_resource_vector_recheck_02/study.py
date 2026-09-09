from pathlib import Path
import json,sys,hashlib,datetime,traceback,copy
import strict
P=Path(__file__).resolve().parent;OLD=P.parent/'charged_resource_vector_native_01';sys.path.insert(0,str(OLD));import table_check
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):
 with p.open('x') as f:json.dump(x,f,indent=2);f.write('\n')
def main():
 cases=json.loads((OLD/'attempt01/CASES.json').read_text());sources=[P/'PLAN.md',P/'strict.py',P/'study.py',OLD/'table_check.py',OLD/'attempt01/MANIFEST.json',OLD/'attempt01/VERIFICATION.jsonl',OLD/'attempt01/RAW.jsonl'];sources+=list((OLD/'attempt01').glob('table_*.json'))
 save(P/'MANIFEST.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),files={str(p):sha(p) for p in sources},post_outcome=True,native_rerun=False))
 toy=dict(jobs=[[1,1,0,0,1]],edges=[],policy='scalar_three',kappa=1);table={0:[0,0],1:[0,1]};legacy=table_check.check(toy,table);rejected=False
 try:strict.check(toy,table,table_check)
 except AssertionError:rejected=True
 save(P/'LEGACY_TAIL_COUNTEREXAMPLE.json',dict(case=toy,table=table,old_accepted=True,old_result=legacy,true_excess_at_B2=2,old_clipped_excess_at_B2=1,strict_rejected=rejected))
 tables=[]
 for c in cases:
  x=json.loads((OLD/'attempt01'/('table_'+c['id']+'.json')).read_text());vals={int(k):v for k,v in x['values'].items()};result=strict.check(c,vals,table_check);tables.append(dict(id=c['id'],status='SUCCESS',result=result))
 save(P/'TABLE_RESULTS.json',tables);allrows=[json.loads(l) for l in (OLD/'attempt01/VERIFICATION.jsonl').read_text().splitlines()];raw={r['id']:r for r in map(json.loads,(OLD/'attempt01/RAW.jsonl').read_text().splitlines())};rows=[]
 for row in allrows:rows.append(dict(id=row['id'],met=strict.native_control_met(row,row['expected_accept'],raw[row['id']]['status'])))
 save(P/'NATIVE_AGGREGATION_RESULTS.json',rows)
 neg=next(r for r in allrows if not r['expected_accept']);controls=[]
 for name in ['unchanged','resource_failure','wrong_layer','wrong_reason','timeout']:
  r=copy.deepcopy(neg)
  if name=='resource_failure':r.update(status='RESOURCE_CHECK_FAILURE',layer=None)
  elif name=='wrong_layer':r['layer']='resource'
  elif name=='wrong_reason':r['reason']='unrelated resource failure'
  elif name=='timeout':r['status']='TIMEOUT'
  accepted=strict.native_control_met(r,False,'SUCCESS');controls.append(dict(id=name,expected=name=='unchanged',accepted=accepted,met=accepted==(name=='unchanged'),input=r))
 save(P/'AGGREGATION_CONTROLS.json',controls);summary=dict(tables=len(tables),native_rows=len(rows),all_met=all(r['met'] for r in rows+controls) and rejected,controls=len(controls),legacy_counterexample_preserved=True,native_rerun=False);save(P/'SUMMARY.json',summary);print(json.dumps(summary));assert summary['all_met']
if __name__=='__main__':main()
