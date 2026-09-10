from pathlib import Path
from itertools import product, combinations
import json, hashlib, datetime

D=Path(__file__).resolve().parent
def put(name, obj):
 p=D/name
 with p.open('x') as f: json.dump(obj,f,indent=2);f.write('\n')
 return {'path':name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def dags(n):
 possible=list(combinations(range(n),2))
 for mask in range(1<<len(possible)):
  yield [list(e) for k,e in enumerate(possible) if (mask>>k)&1]
def unique(vectors): return sorted(set(tuple(x) for x in vectors))

A=[]
for n in range(1,4):
 for edges in dags(n):
  for w in product([1,2,4],repeat=n):
   for g in product([0,1,3],repeat=n):
    A.append({'id':len(A),'n':n,'edges':edges,'w':list(w),'g':list(g),'family':'exhaustive_small'})
for n in [4,5,6]:
 graphs=list(dags(n)) if n==4 else [[],[[i,i+1] for i in range(n-1)],[[0,i] for i in range(1,n)],[[i,n-1] for i in range(n-1)],[[i,j] for i in range(n//2) for j in range(n//2,n)]]
 works=unique([[1]*n,[2]*n,list(range(1,n+1)),list(range(n,0,-1)),[1]*(n-1)+[100],[100]+[1]*(n-1),[1 if i%2 else 7 for i in range(n)],[2**i for i in range(n)]])
 for edges in graphs:
  for w in works:
   guards=unique([[0]*n,[1]*n,list(w),list(reversed(w)),[0 if i%2 else 13 for i in range(n)]])
   for g in guards:
    A.append({'id':len(A),'n':n,'edges':edges,'w':list(w),'g':list(g),'family':'topology_and_cost_boundaries'})

B=[]
for n in range(1,4):
 for w in product([1,2,4],repeat=n):
  for c in product([1,2,4],repeat=n):
   for g in unique([[0]*n,[1]*n,[i%3 for i in range(n)]]):
    B.append({'id':len(B),'n':n,'edges':[],'w':list(w),'c':list(c),'g':list(g),'family':'exhaustive_small'})
for n in [4,6,8]:
 for k in range(64):
  w=[1+((k+3)*(i+5)+(i*i+7*k))%31 for i in range(n)]
  c=[1+((k+7)*(i+2)+3*i*i)%19 for i in range(n)]
  g=[(k+i*3)%7 for i in range(n)]
  edges=[] if k%3==0 else ([[i,i+1] for i in range(n-1)] if k%3==1 else [[0,i] for i in range(1,n)])
  B.append({'id':len(B),'n':n,'edges':edges,'w':w,'c':c,'g':g,'family':'deterministic_boundary_grid'})
for n in range(1,13):
 B.append({'id':len(B),'n':n,'edges':[],'w':[2**(i+1) for i in range(n)],'c':[2**i for i in range(n)],'g':[1]*n,'family':'exponential_frontier'})
for n in [1,2,4,8]:
 for c in [1,2,7]:
  for shift in [0,1,4]:
   B.append({'id':len(B),'n':n,'edges':[[i,i+1] for i in range(n-1)],'w':[1+((i+shift)*5)%17 for i in range(n)],'c':[c]*n,'g':[i%3 for i in range(n)],'family':'uniform_comparison'})

K=[]
for n in range(1,4):
 for a in product([1,3,7],repeat=n):
  for v in product([1,2,6],repeat=n):
   K.append({'id':len(K),'n':n,'sizes':list(a),'values':list(v),'capacities':list(range(sum(a)+2)),'targets':list(range(sum(v)+2))})

fixed={'schema':'charged-comparison-fixed-inputs-v1','candidate_proof':'PROOF_CANDIDATE01.md','A':A,'B':B,'knapsack':K,'controls':[
 {'id':'A_omit_guard','w':[1,10],'g':[2,7],'edges':[],'M':10,'mutation':'set every g to0 in the formula'},
 {'id':'A_keep_guard_after_mismatch','w':[1,10],'g':[2,7],'edges':[[0,1]],'M':1,'mutation':'after first mismatch keep cached guard on suffix'},
 {'id':'B_omit_total_comparison','w':[3,5],'c':[1,2],'g':[1,1],'mutation':'omit c from Wt only'},
 {'id':'B_informed_zero','w':[3,5],'c':[1,2],'g':[1,1],'mutation':'allow a cheap no-write path by changing universal class to supplied B0'},
 {'id':'B_negative_profit_forced','w':[1,2],'c':[4,4],'g':[1,1],'mutation':'require caching all jobs'},
 {'id':'B_uniform_hardness_scope','w':[4,7,1,7],'c':[2,2,2,2],'g':[1,0,3,1],'mutation':'the generic exponential bound is inapplicable to this uniform-c family; verify <=n+1 points'}
]}
r=put('INPUTS01.json',fixed)
receipt={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'INPUTS_FIXED_BEFORE_CHECKER_EXECUTION','counts':{'A_inputs':len(A),'A_threshold_roots':sum(len(set([0]+x['w'])) for x in A),'B_inputs':len(B),'knapsack_inputs':len(K),'knapsack_decision_pairs':sum(len(x['capacities'])*len(x['targets']) for x in K),'controls':len(fixed['controls'])},'input':r,'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'new_native_runs':0,'proof_claims_established_by_generation':False}
put('INPUT_FIX_RECEIPT01.json',receipt);print(json.dumps(receipt,indent=2),flush=True)
