from pathlib import Path
import datetime,hashlib,itertools,json,random
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,data):
    with (ROOT/name).open('x') as f:json.dump(data,f,indent=2);f.write('\n')
def key(case):return json.dumps([case['cp'],sorted(case['edges'])],separators=(',',':'))
def main():
    files=[ROOT/'PLAN.md',Path(__file__)]
    save('GENERATOR_MANIFEST.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),seed=202609080250,files=[dict(path=str(p),sha256=sha(p)) for p in files],model_values_observed=False,native_outcomes_observed=False))
    rng=random.Random(202609080250);vectors=[]
    for n in (3,4,5):
        for route in ('ordered','ideal'):
            for index in range(8):
                edges=[e for e in itertools.combinations(range(n),2) if rng.random()<0.35]
                if (0,n-1) not in edges:edges.append((0,n-1))
                costs=[rng.randint(1,12) for _ in range(n)]
                if route=='ordered':costs.sort()
                else:costs[0]=rng.randint(2,12);costs[-1]=rng.randint(1,costs[0]-1)
                premiums=[rng.randint(0,24) for _ in range(n)];labels=list(range(n));rng.shuffle(labels)
                cp=[None]*n
                for i in range(n):cp[labels[i]]=[costs[i],premiums[i]]
                edges=sorted([[labels[a],labels[b]] for a,b in edges])
                vectors.append(dict(id=f'native-final-{len(vectors):02}',cp=cp,edges=edges,expected_route=route,n=n,stratum_index=index))
    prior=json.loads((ROOT.parent/'dependency_native_01/INPUTS.json').read_text())['cases']
    prior_keys={key(c):name for name,c in prior.items()}
    for c in vectors:c['prior_exact_native_case']=prior_keys.get(key(c))
    save('VECTORS.json',dict(vectors=vectors,core_vectors=48,duplicate_vectors=48-len({key(c) for c in vectors}),prior_exact_overlap=sum(c['prior_exact_native_case'] is not None for c in vectors),model_values_observed=False))
    print(dict(vectors=48,duplicate_vectors=48-len({key(c) for c in vectors}),prior_exact_overlap=sum(c['prior_exact_native_case'] is not None for c in vectors)))
if __name__=='__main__':main()
