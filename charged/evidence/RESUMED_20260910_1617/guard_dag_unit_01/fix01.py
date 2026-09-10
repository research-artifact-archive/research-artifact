from pathlib import Path
from itertools import combinations
from datetime import datetime,timezone
import json,hashlib
D=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,x):
 with p.open('x') as f:json.dump(x,f,indent=2);f.write('\n')
sources=[];general=[]
for n in [3,4,5]:
 es=list(combinations(range(n),2))
 for mask in range(1<<len(es)):
  e=[list(v) for i,v in enumerate(es) if mask>>i&1]
  for k in range(3,n+1):sources.append(dict(id=f'v{n}-m{mask}-k{k}',v=n,edges=e,k=k,branch='trivial_no' if len(e)<k*(k-1)//2 else 'embedding'))
for n in range(1,5):
 es=list(combinations(range(n),2))
 for mask in range(1<<len(es)):
  e=[list(v) for i,v in enumerate(es) if mask>>i&1]
  for kind,w in [('ones',[1]*n),('linear',list(range(1,n+1))),('powers',[2**i for i in range(n)])]:
   for g in [0,1,3]:general.append(dict(id=f'n{n}-m{mask}-{kind}-g{g}',w=w,g=g,edges=e,d=list(range(1,n+1))))
counts=dict(source_cases=len(sources),embedding_cases=sum(x['branch']=='embedding' for x in sources),trivial_no_cases=sum(x['branch']=='trivial_no' for x in sources),general_cases=len(general),controls=3)
put(D/'INPUTS01.json',dict(sources=sources,general=general))
files={n:dict(sha256=sha(D/n),bytes=(D/n).stat().st_size) for n in ['CANDIDATE01.md','PROTOCOL01.md','fix01.py','check01.py','INPUTS01.json']}
put(D/'INPUT_FIX_RECEIPT01.json',dict(utc=datetime.now(timezone.utc).isoformat(),counts=counts,files=files,inherited_checker_sha256=sha(D.parent/'charged_comparison_01/check04.py'),results_observed_before_fix=False))
print(json.dumps(counts))
