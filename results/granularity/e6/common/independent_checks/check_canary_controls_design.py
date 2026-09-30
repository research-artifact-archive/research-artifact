#!/usr/bin/env python3
import copy,hashlib,importlib.util,json,sys
from pathlib import Path
sys.dont_write_bytecode=True;E6=Path(__file__).resolve().parents[2];P=E6/'canary_controls/v1'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
s=importlib.util.spec_from_file_location('endpoint_product_independent',E6/'rolling/validate_endpoints.py');ep=importlib.util.module_from_spec(s);s.loader.exec_module(ep)
basefrozen=read(E6/'canary/v1/build/frozen_manifest.json');frozen=read(P/'build/frozen_manifest.json')
for path,h in frozen['files'].items():assert sha(E6/path)==h
assert sha(Path(frozen['jar_path']))==frozen['jar_sha256'];records=[];params=set()
for path in sorted((P/'inputs').glob('*.json')):
 d=read(path);n,m,control=(d['parameters'][k] for k in ['n','m','control']);group='fine' if d['parameters']['k']==1 else 'all';params.add((n,m,control,group))
 ref=P/d['metadata']['reference_input'];original=E6/'canary/v1/inputs'/ref.name;assert original.read_bytes()==ref.read_bytes() and sha(ref)==basefrozen['files'][str(original.relative_to(E6))]
 expected=read(ref);expected.update(id=d['id'],family='canary_controls',metadata=d['metadata']);expected['parameters']['control']=control
 for i,c in enumerate(expected['components'],1):
  if control=='healthy_only':assert c['transfer']=={'H':['HP','BP']};c['transfer']['H'].remove('BP')
  elif control=='no_recovery':c['new']['edges'].remove(['B',f'restart_{i}','H'])
  else:raise AssertionError(control)
 assert expected==d,(path.name,'Unregistered model difference')
 for i,c in enumerate(d['components'],1):
  if control=='no_recovery':
   reachable={'BP'}
   while True:
    more=reachable|{t for q,a,t in c['new']['edges'] if q in reachable}
    if more==reachable:break
    reachable=more
   assert reachable=={'BP','B'} and 'H' not in reachable
  else:assert c['transfer']=={'H':['HP']}
 old=ep.validate(d,'old');new=ep.validate(d,'new');assert old['product_states']==new['product_states']==1
 assert all(project['physical']==[['NEW','H']]*n for project in d['endpoints']['new']['projection'].values())
 records.append({'input':path.name,'control':control,'old':old,'new':new,'sha256':sha(path)})
assert params=={(n,m,c,g) for n in range(2,5) for m in range(1,n) for c in ['healthy_only','no_recovery'] for g in ['fine','all']}
cfg=read(P/'config.json');assert len(cfg['jobs'])==48;assert not (P/'raw/runner_finished.json').exists()
for start in range(0,48,4):
 jobs=cfg['jobs'][start:start+4];assert [j['solver'] for j in jobs]==['lazy','lazy','lazy','direct_full'];assert [j['merge'] for j in jobs]==['none','transfers','none','none']
 for j in jobs:assert j['expected_decision']==('WIN' if j['parameters']['control']=='healthy_only' else 'LOSS')
report={'status':'PASS','scope':'Independent read-only design and schedule check before measurement; no solver outcome claimed','inputs':24,'references':12,'planned_trials':48,'frozen_files':len(frozen['files']),'records':records,'notes':['Healthy-only changes only transfer support, preserving all reports/recovery/monitors/endpoints.','No-recovery removes only B-to-H physical edges; remaining declarations do not create physical transitions.','The no-recovery LOSS expectation concerns mandatory all-H completion as well as possible interval violation; it does not imply every broken state violates the interval.']}
with Path(__file__).with_name('canary_controls_design_review.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print({k:v for k,v in report.items() if k not in ['records','notes']})
