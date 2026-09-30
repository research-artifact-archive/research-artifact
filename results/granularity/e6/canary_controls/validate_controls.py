#!/usr/bin/env python3
"""Independent permitted-difference, endpoint, and irreversible-broken checks."""
import hashlib,importlib.util,itertools,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
E6=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('endpoint_product',E6/'rolling/validate_endpoints.py');ep=importlib.util.module_from_spec(spec);spec.loader.exec_module(ep)
def main():
 family=Path(sys.argv[1]).resolve();records=[];models={};base_manifest=json.loads((E6/'canary/v1/build/frozen_manifest.json').read_text())
 for path in sorted((family/'inputs').glob('*.json')):
  d=json.loads(path.read_text());n,m,control=(d['parameters'][k] for k in ('n','m','control'));group='fine' if d['parameters']['k']==1 else 'all';assert 2<=n<=4 and 1<=m<n and control in ('healthy_only','no_recovery')
  ref=family/d['metadata']['reference_input'];base=E6/'canary/v1/inputs'/ref.name;digest=hashlib.sha256(ref.read_bytes()).hexdigest();assert ref.read_bytes()==base.read_bytes() and digest==d['metadata']['reference_sha256']==base_manifest['files'][str(base.relative_to(E6))]
  original=json.loads(ref.read_text());expected=json.loads(ref.read_text());expected['id']=d['id'];expected['family']='canary_controls';expected['parameters']['control']=control;expected['metadata']=d['metadata']
  for i,c in enumerate(expected['components'],1):
   if control=='healthy_only':c['transfer']={'H':['HP']}
   else:c['new']['edges'].remove(['B',f'restart_{i}','H'])
  assert expected==d,'Differences exceed the one registered model change.'
  irreversible=[]
  for i,c in enumerate(d['components'],1):
   if control=='healthy_only':assert c['transfer']=={'H':['HP']}
   else:
    assert c['transfer']=={'H':['HP','BP']};adj={q:set() for q in c['new']['states']}
    for s,a,t in c['new']['edges']:adj[s].add(t)
    reached={'BP'};todo=['BP']
    while todo:
     for q in adj[todo.pop()]:
      if q not in reached:reached.add(q);todo.append(q)
    assert reached=={'BP','B'} and not adj['B'];irreversible.append(dict(component=i,reachable_from_broken=sorted(reached)))
  old,new=ep.validate(d,'old'),ep.validate(d,'new');assert old['projected_states']==new['projected_states']==1 and old['edges']==new['edges']==n
  outcomes=set(itertools.product(*(c['transfer']['H'] for c in d['components'])))
  assert len(outcomes)==(1 if control=='healthy_only' else 2**n)
  assert (('BP',)*n in outcomes)==(control=='no_recovery')
  models[n,m,control,group]=d;records.append(dict(input=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),reference_sha256=digest,control=control,old=old,new=new,product_outcomes=len(outcomes),irreversible_broken=irreversible,status='PASS'))
 assert len(records)==24
 for n in range(2,5):
  for m in range(1,n):
   for c in ('healthy_only','no_recovery'):
    a=json.loads(json.dumps(models[n,m,c,'fine']));b=models[n,m,c,'all'];a['id']=b['id'];a['parameters']['k']=n;a['metadata']=b['metadata'];a['generated_contract_mode']='transfers'
    for part in a['components']:part['transfer_action']='ablation.merge.transfers'
    a['requirements'][0]['tester']['alphabet']=a['ordinary']+['ablation.merge.transfers'];assert a==b
 out=family/(sys.argv[2] if len(sys.argv)>2 else 'validation/endpoint_products.json');out.parent.mkdir(parents=True,exist_ok=True)
 with out.open('x') as f:json.dump(dict(status='PASS',inputs=24,endpoint_products=48,records=records,scope='Only registered changes relative to byte-preserved Canary references; local broken-state closure; independent endpoint products.'),f,indent=2);f.write('\n')
 print(json.dumps(dict(status='PASS',inputs=24,endpoint_products=48)))
if __name__=='__main__':main()
