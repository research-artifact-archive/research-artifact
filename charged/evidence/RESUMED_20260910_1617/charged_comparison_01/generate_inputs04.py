from pathlib import Path
from itertools import product,combinations
import hashlib,json
from datetime import datetime,timezone
D=Path(__file__).resolve().parent
cases=[]
def add(n,e,w,g,c,f):cases.append(dict(id=len(cases),n=n,edges=e,w=w,g=g,c=c,family=f))
for n in range(1,4):
 edges=list(combinations(range(n),2))
 for em in range(1<<len(edges)):
  e=[list(a) for i,a in enumerate(edges) if em>>i&1]
  for w in product([1,3],repeat=n):
   for g in product([0,2],repeat=n):
    for c in product([0,1,4],repeat=n):add(n,e,list(w),list(g),list(c),'exhaustive_n_le_3')
for n in [4,5,6]:
 edges=list(combinations(range(n),2))
 shapes=([[list(a) for i,a in enumerate(edges) if em>>i&1] for em in range(1<<len(edges))] if n==4 else [[],[[i,i+1] for i in range(n-1)],[[0,i] for i in range(1,n)],[[i,n-1] for i in range(n-1)],[[i,j] for i,j in edges if i%2==0 and j%2==1]])
 for e in shapes:
  for p in range(8 if n==4 else 6):
   w=[[1,3,7,2,5,11][(i+p)%6] for i in range(n)]
   g=[0 if p==0 else [0,1,4][(i+2*p)%3] for i in range(n)]
   c=[[0,1,4,9][(i+p)%4] for i in range(n)]
   add(n,e,w,g,c,'all_n4_DAG_profiles' if n==4 else 'larger_fixed_shapes')
old=D/'INPUTS01.json';data=json.loads(old.read_text());emb=[]
for x in data['knapsack']:
 for topo in ['independent','final_dummy']:
  emb.append(dict(id=len(emb),origin=x['id'],family='knapsack_embedding',sizes=x['sizes'],values=x['values'],topology=topo))
for n in range(1,13):
 for topo in ['independent','final_dummy']:
  emb.append(dict(id=len(emb),origin=n,family='powers_two',sizes=[1<<i for i in range(n)],values=[1<<i for i in range(n)],topology=topo))
controls=['omit_comparison_from_total','charge_full_suffix_after_mismatch','omit_mismatch_branch','omit_required_dummy_guard','ignore_failed_call','free_stale_preparation']
out={'schema':'fully-charged-supplied-one-write-fixed-v1','general':cases,'embedding':emb,'controls':controls,'embedded_predecessor_sha256':hashlib.sha256(old.read_bytes()).hexdigest()}
p=D/'INPUTS04.json';assert not p.exists();p.write_text(json.dumps(out,separators=(',',':'))+'\n')
names=['INPUTS04.json','FULLY_CHARGED_CANDIDATE04.md','PROTOCOL04.md','generate_inputs04.py','check04.py']
r={'utc':datetime.now(timezone.utc).isoformat(),'counts':{'general':len(cases),'embedding':len(emb),'controls':len(controls)},'files':{n:{'sha256':hashlib.sha256((D/n).read_bytes()).hexdigest(),'bytes':(D/n).stat().st_size} for n in names},'results_not_executed':True}
(D/'INPUT_FIX_RECEIPT04.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
