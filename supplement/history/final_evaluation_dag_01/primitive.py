"""Development extension of guaranteed_guards_01 to admissible DAG states.
Only solve/validate are reused from primitive_rmw_01; its old graph is unused.
"""
from pathlib import Path
from collections import defaultdict
import importlib.util,itertools
PARENT=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('unchanged_and_or',PARENT/'primitive_rmw_01/explore.py')
reuse=importlib.util.module_from_spec(spec);spec.loader.exec_module(reuse)
U,C,L,LC,D=range(5)
def predecessors(n,edges):return [set(a for a,b in edges if b==i) for i in range(n)]
def admissible(s,pred):
    return all(x not in (C,LC,D) or all(s[j]==D for j in pred[i]) for i,x in enumerate(s))
def scalar(jobs,edges,B):
    n=len(jobs);pred=[sum(1<<a for a in ps) for ps in predecessors(n,edges)]
    v=[[0]*(1<<n) for _ in range(B+1)]
    for b in range(1,B+1):
        for mask in range(1,1<<n):
            candidates=[]
            for i,(w,p) in enumerate(jobs):
                if mask>>i&1 and not mask&pred[i]:
                    child=mask^(1<<i)
                    candidates.extend([p+v[b][child],max(v[b][child],w+v[b-1][mask])])
            assert candidates
            v[b][mask]=min(candidates)
    return v
def graph(jobs,edges,B):
    pred=predecessors(len(jobs),edges)
    states=[(s,b) for b in range(B+1) for s in itertools.product(range(5),repeat=len(jobs)) if admissible(s,pred)]
    state_set=set(states)
    actions=[];owners=[];outgoing={};backwards=defaultdict(list);goals=set()
    for state in states:
        s,b=state;outgoing[state]=[]
        if all(x==D for x in s):goals.add(state);continue
        def add(name,edges):
            assert edges and all(target in state_set and cost>=0 for target,cost in edges)
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
                if all(s[j]==D for j in pred[i]):single(i,'prepare',[(C,0,w)])
                single(i,'acquire',[(L,0,0)])
                single(i,'conditional_acquire_raw',[(L,0,0),(U,1,0)])
                if all(s[j]==D for j in pred[i]):single(i,'atomic_fresh',[(D,0,w+p)])
            elif x==C:
                single(i,'conditional_commit',[(D,0,0),(U,1,0),(C,1,0)])
                single(i,'acquire_validate',[(LC,0,0),(L,1,0)])
                single(i,'atomic_cached',[(D,0,0),(D,1,w+p)])
                single(i,'inspect',[(C,0,0),(U,1,0)])
                single(i,'discard',[(U,0,0)])
            elif x==L:
                if all(s[j]==D for j in pred[i]):single(i,'prepare_guarded',[(LC,0,w+p)])
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
