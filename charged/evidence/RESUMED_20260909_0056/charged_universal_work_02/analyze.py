"""Post-outcome fixed-policy W,L,Q envelope; no constructor/policy oracle import."""
from pathlib import Path
import datetime,json,hashlib,sys,time
P=Path(__file__).resolve().parent;BASE=P.parent/'charged_budget_blind_native_01/attempt01'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def save(p,x):
 with p.open('x') as f:json.dump(x,f,indent=2);f.write('\n')
def top(w,k):return sum(sorted(w,reverse=True)[:min(max(k,0),len(w))])
def formula(case,B):
 w=[8*j[0] for j in case['jobs']];n=len(w);remaining=set(range(n));order=[]
 while remaining:
  i=min(i for i in remaining if not any(v==i and u in remaining for u,v in case['edges']));remaining.remove(i);order.append(i)
 kind,r=case['policy'].split('-');r=int(r);omega=sum(w);Q=n+min(B,r);terms=[]
 if kind=='blind_two':W=omega+min(B,r)*max(w);L=omega if B>=r else 0
 else:
  L=top(w,B-r)
  if r==0:W=omega+top(w,B)
  elif B<=r:W=omega+B*max(w)
  else:
   for at,i in enumerate(order):terms.append((r-1)*max(w[j] for j in order[:at+1])+w[i]+top([w[j] for j in order[at:]],B-r))
   W=omega+max(terms)
 return dict(W=W,L=L,Q=Q,order=order,transition_terms=terms)
def prepare():
 files=[P/'PLAN.md',Path(__file__)]+[BASE/f for f in ['CASES.json','RUNS.json','RAW.jsonl','REPLAY_GROUPS.json']]
 save(P/'INPUTS.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),post_outcome_analysis=True,new_measurements=0,groups=1280,records=17200,files={str(p):sha(p) for p in files}))
def execute():
 inp=read(P/'INPUTS.json');assert all(sha(Path(p))==h for p,h in inp['files'].items());start=time.monotonic();cases={c['id']:c for c in read(BASE/'CASES.json')};runs={r['id']:r for r in read(BASE/'RUNS.json')};groups={};count=0
 with (BASE/'RAW.jsonl').open() as f:
  for line in f:
   assert time.monotonic()-start<60,'analysis time cap'
   row=json.loads(line);run=runs[row['id']];case=cases[run['case']]
   if run['kind']!='replay' or run['control']:continue
   assert row['status']=='SUCCESS';w=[8*j[0] for j in case['jobs']];W=L=0
   for e in row['events']:
    if e['kind']=='K':W+=w[e['job']];L+=w[e['job']] if e['inside'] else 0
   Q=sum(row['callbacks'])+sum(row['conditionals']);assert W==row['work'] and Q==len(row['trace']);key=(run['case'],run['budget'],run['layout']);g=groups.setdefault(key,dict(count=0,W=0,L=0,Q=0));g['count']+=1;count+=1
   for k,v in [('W',W),('L',L),('Q',Q)]:g[k]=max(g[k],v)
 expected=read(BASE/'REPLAY_GROUPS.json');assert len(groups)==len(expected)==1280 and count==17200;rows=[]
 for e in expected:
  g=groups[e['case'],e['budget'],e['layout']];f=formula(cases[e['case']],e['budget']);met=g['count']==e['paths'] and all(g[k]==f[k]==e['observed'][k] for k in ['W','L','Q'])
  rows.append(dict(case=e['case'],budget=e['budget'],layout=e['layout'],observed=g,formula=f,met=met))
 save(P/'GROUPS.json',rows);save(P/'SUMMARY.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='SUCCESS' if all(r['met'] for r in rows) else 'FAILURE',post_outcome_analysis=True,new_measurements=0,groups=1280,groups_met=sum(r['met'] for r in rows),raw_records=count,seconds=time.monotonic()-start,scope='fixed-policy marginal component maxima; not joint scalar maxima or universal W-optimality'))
 print(json.dumps(read(P/'SUMMARY.json')))
if __name__=='__main__':
 if sys.argv[1]=='prepare':prepare()
 elif sys.argv[1]=='execute':execute()
 else:raise SystemExit('prepare|execute')
