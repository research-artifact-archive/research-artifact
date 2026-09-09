from pathlib import Path
import itertools,random,json,hashlib,datetime,sys
P=Path(__file__).resolve().parent
CATALOG=[[1,1,0,1,1],[2,1,1,2,1],[1,3,1,0,1],[2,0,2,0,0],[3,4,0,5,2],[1,0,1,0,2],[5,2,0,0,0],[1,12,3,1,2]]
bases=[]
for n in range(1,5):
 for ids in itertools.combinations_with_replacement(range(len(CATALOG)),n):bases.append(dict(id='grid-%04d'%len(bases),kind='systematic',jobs=[CATALOG[i] for i in ids]))
rng=random.Random(202609091052)
for i in range(128):
 n=rng.randint(2,6);jobs=[[rng.randint(1,16),rng.randint(0,128),rng.randint(0,32),rng.randint(0,32),rng.randint(0,32)] for _ in range(n)]
 bases.append(dict(id='seed-%03d'%i,kind='seeded',jobs=jobs))
cases=[]
for base in bases:
 for exponent in [0,32,96]:
  scale=1<<exponent;jobs=[[x*scale for x in row] for row in base['jobs']]
  sat=sum((p+max(0,g+r-v)+w+min(v,g+r)-1)//(w+min(v,g+r)) for w,p,g,v,r in jobs)
  cases.append(dict(id=base['id']+'-s%d'%exponent,base=base['id'],kind=base['kind'],exponent=exponent,saturation_bound=sat,input=dict(jobs=jobs,edges=[])))
def save(name,x):
 with (P/name).open('x') as f:json.dump(x,f,separators=(',',':'));f.write('\n')
save('INPUTS.json',dict(catalog=CATALOG,bases=len(bases),cases=cases,extra_budgets=[2**32,2**96]))
files=[P/x for x in ['PLAN.md','THEORY_DRAFT.md','prepare.py','study.py','INPUTS.json']]
files+=sorted(x for d in ['charged_compact_03','charged_curves_02'] for x in (P.parent/d).rglob('*.py') if '__pycache__' not in x.parts)
files.append(P.parent.parent/'RESUMED_20260907_1942/dependency_curves_01/curves.py')
records=[dict(path=str(x.relative_to(P.parent.parent)),bytes=x.stat().st_size,sha256=hashlib.sha256(x.read_bytes()).hexdigest()) for x in files]
save('MANIFEST.json',dict(schema='general-independent-charged-sharp-bound-v1',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),bases=len(bases),cases=len(cases),direct_roots=sum(x['saturation_bound']+1 for x in cases),extra_queries=2*len(cases),max_direct_budget=max(x['saturation_bound'] for x in cases),files=records,python=sys.version,argv=[sys.executable,'-B',str(P/'study.py')],campaign_seconds=900,scientific_outcomes_observed=False))
print(json.dumps(dict(bases=len(bases),cases=len(cases),direct_roots=sum(x['saturation_bound']+1 for x in cases),extra_queries=2*len(cases),max_direct_budget=max(x['saturation_bound'] for x in cases))))
