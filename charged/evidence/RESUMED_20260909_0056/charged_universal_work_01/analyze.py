"""Post-outcome aggregate check of the r=0 universal protection curve's work."""
from pathlib import Path
import json,hashlib,datetime,collections,sys
P=Path(__file__).resolve().parent;NEW=P.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def save(p,x):
 with p.open('x') as f:json.dump(x,f,indent=2);f.write('\n')
def prepare():
 files=[P/'PLAN.md',P/'THEORY_CANDIDATE.md',Path(__file__)]
 for study in ['charged_budget_blind_native_01','charged_resource_vector_native_01']:
  files.extend(NEW/study/'attempt01'/f for f in ['CASES.json','RUNS.json','RAW.jsonl','REPLAY_GROUPS.json'])
 save(P/'INPUTS.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),post_outcome_analysis=True,new_scientific_measurements=0,groups=160,reference_pairs=2,criterion='ordinary replay policy blind_three-0, every B/layout/shape/price; no outcome selection',files={str(p):sha(p) for p in files}))
def execute():
 inputs=read(P/'INPUTS.json');assert all(sha(Path(p))==h for p,h in inputs['files'].items())
 base=NEW/'charged_budget_blind_native_01/attempt01';cases={r['id']:r for r in read(base/'CASES.json')};runs={r['id']:r for r in read(base/'RUNS.json')};groups={};expected={}
 for g in read(base/'REPLAY_GROUPS.json'):
  if g['policy']=='blind_three-0':expected[g['case'],g['budget'],g['layout']]=g
 assert len(expected)==160
 with (base/'RAW.jsonl').open() as f:
  for line in f:
   row=json.loads(line);run=runs[row['id']];case=cases[run['case']]
   if run['control'] or run['kind']!='replay' or case['policy']!='blind_three-0':continue
   assert row['status']=='SUCCESS';w=[8*j[0] for j in case['jobs']];W=sum(w[e['job']] for e in row['events'] if e['kind']=='K');L=sum(w[e['job']] for e in row['events'] if e['kind']=='K' and e['inside']);Q=sum(row['callbacks'])+sum(row['conditionals'])
   assert W==row['work'] and Q==len(row['trace'])==len(w)
   key=(case['id'],run['budget'],run['layout']);g=groups.setdefault(key,dict(ids=[],W=0,L=0,Q=0))
   g['ids'].append(run['id'])
   for k,v in [('W',W),('L',L),('Q',Q)]:g[k]=max(g[k],v)
 assert set(groups)==set(expected);rows=[]
 for key,g in groups.items():
  c=cases[key[0]];w=[8*j[0] for j in c['jobs']];omega=sum(w);top=sum(sorted(w,reverse=True)[:min(key[1],len(w))]);e=expected[key]
  met=g['W']==omega+top and g['L']==top and g['Q']==len(w) and len(g['ids'])==e['paths'] and all(g[k]==e['observed'][k] for k in ['W','L','Q'])
  rows.append(dict(case=key[0],budget=key[1],layout=key[2],omega=omega,largest_work_sum=top,expected_W=omega+top,expected_L=top,met=met,observed=g))
 old=read(NEW/'charged_resource_vector_native_01/attempt01/REPLAY_GROUPS.json');pairs=[]
 for layout in ['distinct','colliding']:
  a=next(x for x in old if x['case']=='common-two-chain-k2-scalar_three' and x['budget']==1 and x['layout']==layout)
  b=next(x for x in rows if x['case']=='common-two-chain-k2-blind_three-0' and x['budget']==1 and x['layout']==layout)
  assert a['met'] and b['met'];assert [a['observed'][k] for k in ['W','L','Q']]==[32,16,2] and [b['observed'][k] for k in ['W','L','Q']]==[40,16,2]
  pairs.append(dict(layout=layout,known_B_witness=a,budget_blind_all_L_curves=b,interpretation='cost of simultaneous L-optimality, not budget ignorance alone; component extrema may differ'))
 save(P/'GROUPS.json',rows);save(P/'PAIRS.json',pairs);save(P/'SUMMARY.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='SUCCESS' if all(r['met'] for r in rows) else 'FAILURE',post_outcome_analysis=True,new_measurements=0,groups=len(rows),groups_met=sum(r['met'] for r in rows),raw_records=sum(len(r['observed']['ids']) for r in rows),reference_pairs=len(pairs),universal_claim_established_by_finite_tests=False))
 print(json.dumps(read(P/'SUMMARY.json')))
if __name__=='__main__':
 if sys.argv[1]=='prepare':prepare()
 elif sys.argv[1]=='execute':execute()
 else:raise SystemExit('prepare|execute')
