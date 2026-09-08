from pathlib import Path
from collections import defaultdict
import datetime,hashlib,importlib.util,itertools,json,random,sys,time
ROOT=Path(__file__).resolve().parent
PARENT=ROOT.parent
REUSE=PARENT/'primitive_rmw_01/explore.py'
spec=importlib.util.spec_from_file_location('reused_and_or',REUSE)
reuse=importlib.util.module_from_spec(spec);spec.loader.exec_module(reuse)
U,C,L,LC,D=range(5)
def write(name,value):
    with (ROOT/name).open('x') as f:json.dump(value,f,indent=2);f.write('\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def prepare():
    rng=random.Random(202609072112);cases=[];seen=set()
    while len(cases)<128:
        jobs=tuple((rng.randint(1,20),rng.randint(0,40)) for _ in range(rng.randint(1,4)))
        if jobs in seen:continue
        seen.add(jobs);cases.append(dict(id=f'guard-{len(cases):04}',jobs=jobs,budget=6,
            provenance='author-generated-exploration',previously_observed=False))
    write('INPUTS.json',cases)
    fs=[ROOT/'PLAN.md',ROOT/'explore.py',ROOT/'INPUTS.json',PARENT/'GUARANTEED_GUARDS_ABSTRACTION_DRAFT.md',REUSE]
    write('MANIFEST.json',dict(files=[dict(path=str(p),sha256=sha(p)) for p in fs],planned_inputs=128,planned_root_values=896))
    print('fixed 128 inputs / 896 root values')
def h16(jobs,B):
    values=[[0]*(1<<len(jobs)) for _ in range(B+1)]
    for b in range(1,B+1):
        for mask in range(1,1<<len(jobs)):
            candidates=[]
            for i,(w,p) in enumerate(jobs):
                if mask&(1<<i):
                    rest=mask^(1<<i)
                    candidates.extend((p+values[b][rest],max(values[b][rest],w+values[b-1][mask])))
            values[b][mask]=min(candidates)
    return values
def graph(jobs,B):
    states=[(s,b) for b in range(B+1) for s in itertools.product(range(5),repeat=len(jobs))]
    actions=[];owners=[];outgoing={};backwards=defaultdict(list);goals=set()
    for state in states:
        s,b=state;outgoing[state]=[]
        if all(x==D for x in s):goals.add(state);continue
        def add(name,edges):
            aid=len(actions);actions.append(dict(name=name,edges=edges));owners.append(state);outgoing[state].append(aid)
            for target,cost in edges:backwards[target].append((aid,cost))
        def single(i,name,options):
            edges=[]
            for x,spent,cost in options:
                if spent<=b:
                    ns=list(s);ns[i]=x;edges.append(((tuple(ns),b-spent),cost))
            add(f'{name}:{i}',edges)
        for i,x in enumerate(s):
            w,p=jobs[i]
            if x==U:
                single(i,'prepare',[(C,0,w)])
                single(i,'acquire',[(L,0,0)])
                single(i,'conditional_acquire_raw',[(L,0,0),(U,1,0)])
                single(i,'atomic_fresh',[(D,0,w+p)])
            elif x==C:
                single(i,'conditional_commit',[(D,0,0),(U,1,0),(C,1,0)])
                single(i,'acquire_validate',[(LC,0,0),(L,1,0)])
                single(i,'atomic_cached',[(D,0,0),(D,1,w+p)])
                single(i,'inspect',[(C,0,0),(U,1,0)])
                single(i,'discard',[(U,0,0)])
            elif x==L:
                single(i,'prepare_guarded',[(LC,0,w+p)])
                single(i,'release',[(U,0,0)])
            elif x==LC:
                single(i,'commit_guarded',[(D,0,0)])
                single(i,'release_cached',[(C,0,0)])
                single(i,'discard_guarded',[(L,0,0)])
        unlocked=[i for i,x in enumerate(s) if x in (U,C)]
        for size in range(2,len(unlocked)+1):
            for subset in itertools.combinations(unlocked,size):
                cached=[i for i in subset if s[i]==C];edges=[]
                for k in range(min(b,len(cached))+1):
                    for failed in itertools.combinations(cached,k):
                        ns=list(s)
                        for i in subset:ns[i]=L if s[i]==U or i in failed else LC
                        edges.append(((tuple(ns),b-k),0))
                add('batch_acquire:'+','.join(map(str,subset)),edges)
    return states,actions,owners,outgoing,backwards,goals
def run():
    manifest=json.loads((ROOT/'MANIFEST.json').read_text())
    for f in manifest['files']:assert sha(Path(f['path']))==f['sha256']
    cases=json.loads((ROOT/'INPUTS.json').read_text());start=time.monotonic()
    write('RUN_STARTED.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),timeout_seconds=60))
    counts=dict(SUCCESS=0,FAILURE=0,TIMEOUT=0,INVALID=0);gaps=compares=states_total=actions_total=0
    with (ROOT/'RAW.jsonl').open('x') as output:
        for case in cases:
            row=dict(input=case)
            if time.monotonic()-start>=60 or datetime.datetime.now(datetime.timezone.utc)>=datetime.datetime(2026,9,8,0,50,tzinfo=datetime.timezone.utc):
                row['status']='TIMEOUT'
            else:
                try:
                    jobs=case['jobs'];B=case['budget'];g=graph(jobs,B)
                    values,policy=reuse.solve(g);rank=reuse.validate(g,values,policy);v=h16(jobs,B)
                    def phi(state):
                        s,b=state;mask=sum(1<<i for i,x in enumerate(s) if x in (U,C,L))
                        return sum(jobs[i][0] for i,x in enumerate(s) if x in (U,L))+v[b][mask]
                    potentials={s:phi(s) for s in g[0]};defects=[]
                    for aid,action in enumerate(g[1]):
                        owner=g[2][aid]
                        if max(cost+potentials[target] for target,cost in action['edges'])<potentials[owner]:
                            defects.append(dict(state=owner,action=aid,phi=potentials[owner]))
                    roots=[((U,)*len(jobs),b) for b in range(B+1)];actual=[values[s] for s in roots]
                    expected=[sum(w for w,p in jobs)+v[b][-1] for b in range(B+1)]
                    differences=[dict(b=b,primitive=x,h16=y) for b,(x,y) in enumerate(zip(actual,expected)) if x!=y]
                    row.update(status='SUCCESS',primitive=actual,h16=expected,differences=differences,potential_defects=defects,
                        states=len(g[0]),actions=len(g[1]),policy_rank_rounds=rank,
                        root_actions=[g[1][policy[s]]['name'] for s in roots])
                    if differences or defects:
                        row['all_states']=[dict(state=s,value=values[s],action=policy[s],phi=potentials[s]) for s in g[0]]
                        row['all_actions']=g[1]
                    gaps+=bool(differences or defects);compares+=len(roots);states_total+=len(g[0]);actions_total+=len(g[1])
                except Exception as e:row.update(status='INVALID',error=repr(e))
            counts[row['status']]+=1;output.write(json.dumps(row,separators=(',',':'))+'\n');output.flush()
    summary=dict(planned=128,recorded=sum(counts.values()),outcomes=counts,gap_or_defect_inputs=gaps,
        root_comparisons=compares,validated_states=states_total,actions=actions_total,elapsed_seconds=time.monotonic()-start,
        raw_sha256=sha(ROOT/'RAW.jsonl'),native_experiment=False,independent_implementation=False,novelty_established=False)
    write('SUMMARY.json',summary);print(json.dumps(summary,indent=2))
if __name__=='__main__':{'prepare':prepare,'run':run}[sys.argv[1]]()
