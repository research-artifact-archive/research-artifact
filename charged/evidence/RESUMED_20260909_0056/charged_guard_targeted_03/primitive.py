"""Exploratory explicit minimax with separable, nonnegative operation charges."""
import argparse
from collections import defaultdict, deque
import datetime
from functools import lru_cache
import hashlib
import heapq
import itertools
import json
from pathlib import Path
import random
import signal
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
U, C, L, LC, D = range(5)
STOP = datetime.datetime(2026, 9, 9, 1, tzinfo=datetime.timezone.utc).timestamp()


def save(name, value):
    with (HERE/name).open('x') as f:
        json.dump(value, f, indent=2)
        f.write('\n')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def prepare():
    rng=random.Random(202609090123)
    cases=[]
    for k in range(2112):
        n=2+k%3 if k<2048 else 5
        stratum=k%4; jobs=[]
        for _ in range(n):
            w,p,g,v,r=[rng.randint(0,24) for _ in range(5)];w+=1
            if stratum==1: g,r=rng.randrange(3),rng.randrange(3);v=g+r+rng.randint(1,24)
            if stratum==2: g,r=rng.randint(20,200),rng.randint(20,200)
            if stratum==3: w,p=rng.randint(20,200),rng.randint(20,200)
            jobs.append((w,p,g,v,r))
        edges=[(i,j) for i in range(n) for j in range(i+1,n) if rng.random()<0.4]
        perm=list(range(n));rng.shuffle(perm);shuffled=[None]*n
        for i,job in enumerate(jobs):shuffled[perm[i]]=job
        cases.append({'id':f'fresh-{k:04d}','jobs':shuffled,'edges':[(perm[i],perm[j]) for i,j in edges], 'stratum':stratum, 'previously_observed':False})
    cases.extend([{'id':'observed-two-job-gap','jobs':[(3,2,0,0,0),(1,1,1,3,1)],'edges':[], 'previously_observed':True},
                  {'id':'published-four-job-zero-fee','jobs':[(3,2,0,0,0),(7,2,0,0,0),(5,6,0,0,0),(1,2,0,0,0)],'edges':[(0,1),(0,2),(1,3)],'previously_observed':True}])
    save('INPUTS.json',cases)
    save('MANIFEST.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(), 'files':{name:sha(HERE/name) for name in ['PLAN.md','explore.py','INPUTS.json']},'cases':len(cases),'budgets':list(range(13)),'python':sys.version,'per_case_seconds':5,'total_seconds':300,'hard_stop_utc':'2026-09-09T01:00:00Z'})
    print('materialized',len(cases),'inputs')


def graph(case):
    jobs, edges=case['jobs'],case['edges']; n=len(jobs)
    predicates=[{i for i,j in edges if j==k} for k in range(n)]
    roots=[((U,)*n,b) for b in range(13)]
    seen=set(roots); todo=deque(roots)
    actions=[]; owner=[]; outgoing=defaultdict(list); backward=defaultdict(list); goals=set()
    while todo:
        state=todo.popleft(); s,b=state
        completed={i for i,x in enumerate(s) if x==D}
        if len(completed)==n:
            goals.add(state); continue
        for i,x in enumerate(s):
            w,p,g,v,r=jobs[i]; ready=predicates[i]<=completed
            def add(name, branches):
                targets=[]
                for nx,db,cost in branches:
                    if db>b: continue
                    ns=list(s);ns[i]=nx; target=(tuple(ns),b-db)
                    targets.append((target,cost))
                    if target not in seen: seen.add(target);todo.append(target)
                aid=len(actions);actions.append({'job':i,'name':name,'edges':targets})
                owner.append(state);outgoing[state].append(aid)
                for target,cost in targets: backward[target].append((aid,cost))
            if x==U:
                add('guaranteed_acquire',[(L,0,g)])
                if ready:
                    add('prepare',[(C,0,w)])
                    add('fresh_callback',[(D,0,g+w+p+r)])
            elif x==C:
                assert ready
                add('conditional_commit',[(D,0,v),(U,1,v)])
                add('acquire_validate',[(LC,0,g),(L,1,g)])
                add('cached_callback',[(D,0,g+r),(D,1,g+w+p+r)])
                add('discard',[(U,0,0)])
            elif x==L:
                add('release',[(U,0,r)])
                if ready: add('guarded_prepare',[(LC,0,w+p)])
            elif x==LC:
                assert ready
                add('guarded_commit',[(D,0,r)])
                add('release_cached',[(C,0,r)])
                add('discard_guarded',[(L,0,0)])
    return seen,roots,actions,owner,outgoing,backward,goals


def solve_validate(g):
    states,roots,actions,owner,outgoing,backward,goals=g
    todo=[(0,s,-1) for s in goals];heapq.heapify(todo)
    values={};policy={};remaining=[len(a['edges']) for a in actions];acc=[0]*len(actions)
    while todo:
        value,state,aid=heapq.heappop(todo)
        if state in values: continue
        values[state]=value;policy[state]=aid
        for a,cost in backward[state]:
            remaining[a]-=1;acc[a]=max(acc[a],value+cost)
            if not remaining[a]:heapq.heappush(todo,(acc[a],owner[a],a))
    assert len(values)==len(states),'some reachable states not terminating'
    for s in states-goals:
        q={a:max(cost+values[t] for t,cost in actions[a]['edges']) for a in outgoing[s]}
        assert values[s]==min(q.values())==q[policy[s]],('Bellman',s)
    # Fresh traversal of only selected policy edges; zero-cost cycles are forbidden.
    rank={};visiting=set()
    def visit(s):
        if s in rank: return rank[s]
        assert s not in visiting,('nontermination',s)
        visiting.add(s)
        result=0 if s in goals else 1+max(visit(t) for t,_ in actions[policy[s]]['edges'])
        visiting.remove(s);rank[s]=result;return result
    for s in states:visit(s)
    return values,policy,max(rank.values())


def macro(case):
    jobs,edges=case['jobs'],case['edges'];n=len(jobs)
    @lru_cache(None)
    def f(s,b):
        if not s:return 0
        choices=[]
        for i,(w,p,g,v,r) in enumerate(jobs):
            if not s>>i&1 or any(j==i and s>>h&1 for h,j in edges):continue
            rest=s^(1<<i);m=min(v,g+r)
            choices.append(w+p+g+r+f(rest,b))
            choices.append(w+m+f(rest,b) if b==0 else w+m+max(f(rest,b),f(s,b-1)))
            choices.append(w+g+r+f(rest,b) if b==0 else max(w+g+r+f(rest,b),2*w+p+g+r+f(rest,b-1)))
        return min(choices)
    return [f((1<<n)-1,b) for b in range(13)]


def expired(sig,frame):
    raise TimeoutError('registered per-input/campaign wall cap')


def run():
    m=json.loads((HERE/'MANIFEST.json').read_text())
    for name,h in m['files'].items(): assert sha(HERE/name)==h,name
    cases=json.loads((HERE/'INPUTS.json').read_text());start=time.monotonic()
    save('RUN_STARTED.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                            'manifest_sha256':sha(HERE/'MANIFEST.json')})
    signal.signal(signal.SIGALRM,expired);rows=[];first_saved=False
    with (HERE/'RAW.jsonl').open('x') as raw:
        for case in cases:
            left=min(300-(time.monotonic()-start),STOP-time.time()); t=time.monotonic()
            row={'id':case['id']}
            if left<=0:row.update(status='NOT_RUN',reason='campaign/deadline cap')
            else:
                signal.setitimer(signal.ITIMER_REAL,min(5,left))
                try:
                    graph_data=graph(case);values,policy,rank=solve_validate(graph_data)
                    actual=[values[s] for s in graph_data[1]];expected=macro(case)
                    gaps=[{'budget':b,'primitive':a,'macro':e} for b,(a,e) in enumerate(zip(actual,expected)) if a!=e]
                    assert all(a<=e for a,e in zip(actual,expected)), 'macro must be executable upper bound'
                    row.update(status='SUCCESS',primitive=actual,macro=expected,gaps=gaps,
                               states=len(graph_data[0]),actions=len(graph_data[2]),max_policy_rank=rank,
                               root_actions=[graph_data[2][policy[s]]['name']+':'+str(graph_data[2][policy[s]]['job']) for s in graph_data[1]])
                    if gaps and not first_saved:
                        save('FIRST_GAP_GRAPH.json',{'input':case,'roots':graph_data[1],
                          'states':[{'state':s,'value':values[s],'action':policy[s]} for s in sorted(values)],
                          'actions':graph_data[2]});first_saved=True
                except TimeoutError as e:row.update(status='TIMEOUT',error=str(e))
                except Exception:row.update(status='INVALID',error=traceback.format_exc())
                finally:signal.setitimer(signal.ITIMER_REAL,0)
            row['elapsed_seconds']=time.monotonic()-t;rows.append(row)
            raw.write(json.dumps(row,separators=(',',':'))+'\n');raw.flush()
    summary={'planned':len(cases),'recorded':len(rows),'status_counts':{s:sum(r['status']==s for r in rows) for s in ['SUCCESS','FAILURE','TIMEOUT','INVALID','NOT_RUN']},
             'gap_inputs':sum(bool(r.get('gaps')) for r in rows),'gap_roots':sum(len(r.get('gaps',[])) for r in rows),
             'elapsed_seconds':time.monotonic()-start,'raw_sha256':sha(HERE/'RAW.jsonl'),
             'universal_equality_established':False,'application_established':False}
    save('SUMMARY.json',summary);print(json.dumps(summary,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['prepare','run'])
    {'prepare':prepare,'run':run}[parser.parse_args().command]()
