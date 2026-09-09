from pathlib import Path
import itertools,random,json,math,hashlib,datetime,sys
P=Path(__file__).resolve().parent
cases=[]
for n in range(1,7):
 for coeff in itertools.combinations_with_replacement(range(1,5),n):
  for a,d in [(0,1),(1,4),(1,2),(1,1),(2,1),(4,1),(8,1)]:
   for k in [0,1,2,3,4,8,16,32,128]:
    cases.append(dict(id='grid-%05d'%len(cases),kind='grid',lam=[a,d],kappa=k,input=dict(jobs=[[x*d,x*a,0,k,k] for x in coeff],edges=[])))
rng=random.Random(202609091018)
for i in range(128):
 n=rng.randint(2,8);a=rng.randint(0,16);d=rng.randint(1,8);k=rng.randint(0,200);coeff=[rng.randint(1,32) for _ in range(n)]
 cases.append(dict(id='seed-%03d'%i,kind='seeded',lam=[a,d],kappa=k,input=dict(jobs=[[x*d,x*a,0,k,k] for x in coeff],edges=[])))
family=[]
for m in [4,8,16,32,64,128,256]:
 lam=math.isqrt(2*m*m)-m;n=m*m;b=(n*lam+m)//(m+1)
 family.append(dict(id='limit-M%d'%m,kind='tightness',M=m,lam=[lam,1],kappa=m,n=n,B=b,budgets=sorted(set([0,1,b-1,b,b+1,2**32])),input=dict(jobs=[[1,lam,0,m,m] for _ in range(n)],edges=[])))
def save(name,obj):
 with (P/name).open('x') as f:json.dump(obj,f,separators=(',',':'));f.write('\n')
save('INPUTS.json',dict(budgets=list(range(13)),cases=cases,family=family))
files=[P/x for x in ['prepare.py','study.py','PLAN.md','THEORY_DRAFT.md','INPUTS.json']]
files+=sorted(x for x in (P.parent/'charged_compact_03').rglob('*.py') if '__pycache__' not in x.parts)
files += [P.parent/'charged_curves_02'/x for x in ['checker.py']]
records=[dict(path=str(f.relative_to(P.parent)),bytes=f.stat().st_size,sha256=hashlib.sha256(f.read_bytes()).hexdigest()) for f in files]
save('MANIFEST.json',dict(schema='charged-common-price-sharp-bound-v1',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),cases=len(cases),root_budgets=len(cases)*13,families=len(family),family_queries=sum(len(x['budgets']) for x in family),files=records,python=sys.version,argv=[sys.executable,'-B',str(P/'study.py')],budget_seconds=900,new_scientific_outcomes_observed=False,interpretation='finite exploratory semantic checks and analytic tightness family; not application prevalence'))
print(json.dumps(dict(cases=len(cases),root_budgets=len(cases)*13,families=len(family),family_queries=sum(len(x['budgets']) for x in family))))
