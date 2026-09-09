"""Reconstruct complete fixed-policy marginal W,L,Q maxima from retained events."""
from pathlib import Path
import json,sys
HERE=Path(__file__).resolve().parent
DATA=HERE/'evidence/RESUMED_20260909_0056'
OUT=Path(sys.argv[2])
def read(p):return json.loads(p.read_text())
def save(name,x):
 with (OUT/name).open('x') as f:json.dump(x,f,indent=2);f.write('\n')
def top(works,k):return sum(sorted(works,reverse=True)[:max(0,k)])
def expected(c,B):
 w=[8*j[0] for j in c['jobs']];pending=set(range(len(w)));order=[]
 while pending:
  ready=[i for i in pending if not any(v==i and u in pending for u,v in c['edges'])]
  assert ready
  i=min(ready);order.append(i);pending.remove(i)
 mode,allowance=c['policy'].split('-');r=int(allowance);omega=sum(w)
 if mode=='blind_two':W=omega+min(B,r)*max(w);L=omega if B>=r else 0
 else:
  assert mode=='blind_three';L=top(w,B-r)
  if r==0:W=omega+top(w,B)
  elif B<=r:W=omega+B*max(w)
  else:W=omega+max((r-1)*max(w[j] for j in order[:i+1])+w[job]+top([w[j] for j in order[i:]],B-r) for i,job in enumerate(order))
 return dict(W=W,L=L,Q=len(w)+min(B,r))
def main():
 if not __debug__:raise SystemExit('Assertions must be enabled.')
 base=DATA/'charged_budget_blind_native_01/attempt01'
 cases={c['id']:c for c in read(base/'CASES.json')};runs={r['id']:r for r in read(base/'RUNS.json')}
 assert len(cases)==128 and len(runs)==17714
 groups={};seen=set();count=0
 with (base/'RAW.jsonl').open() as stream:
  for line in stream:
   row=json.loads(line);assert row['id'] not in seen;seen.add(row['id'])
   run=runs[row['id']]
   if run['kind']!='replay' or run['control']:continue
   assert row['status']=='SUCCESS';w=[8*j[0] for j in cases[run['case']]['jobs']]
   W=sum(w[e['job']] for e in row['events'] if e['kind']=='K')
   L=sum(w[e['job']] for e in row['events'] if e['kind']=='K' and e['inside'])
   Q=sum(row['callbacks'])+sum(row['conditionals'])
   assert W==row['work'] and Q==len(row['trace'])
   key=(run['case'],run['budget'],run['layout']);g=groups.setdefault(key,dict(count=0,W=0,L=0,Q=0));g['count']+=1;count+=1
   for name,value in [('W',W),('L',L),('Q',Q)]:g[name]=max(g[name],value)
 assert seen==set(runs) and count==17200 and len(groups)==1280
 old=read(base/'REPLAY_GROUPS.json');analysis=read(DATA/'charged_universal_work_02/GROUPS.json')
 assert len(old)==len(analysis)==1280
 original={(r['case'],r['budget'],r['layout']):r for r in old};derived={(r['case'],r['budget'],r['layout']):r for r in analysis}
 assert len(original)==len(derived)==1280 and set(groups)==set(original)==set(derived)
 result=[]
 for key,g in groups.items():
  f=expected(cases[key[0]],key[1]);o=original[key];a=derived[key]
  assert g['count']==o['paths']==a['observed']['count']
  assert all(g[k]==f[k]==o['observed'][k]==a['observed'][k]==a['formula'][k] for k in ['W','L','Q'])
  result.append(dict(case=key[0],budget=key[1],layout=key[2],observed=g,expected=f))
 rzero=read(DATA/'charged_universal_work_01/GROUPS.json')
 assert len(rzero)==160
 for row in rzero:
  g=groups[row['case'],row['budget'],row['layout']]
  assert g['W']==row['expected_W']==row['observed']['W'] and g['L']==row['expected_L']==row['observed']['L'] and g['Q']==row['observed']['Q']
 save('GROUPS.json',result)
 save('SUMMARY.json',dict(status='SUCCESS',stage='universal-work',quick=False,post_outcome_analysis=True,raw_replay_records=count,complete_path_groups=len(groups),r_zero_groups=len(rzero),new_measurements=0,scope='fixed-policy component maxima; all-program W theorem separately restricted to simultaneous L optimality at r=0'))
 print(json.dumps(read(OUT/'SUMMARY.json')),flush=True)
if __name__=='__main__':main()
