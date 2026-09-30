"""Finite static reconstruction from supplied Industry FSP and Java composition rules.
Specific, manually transcribed model: not a general FSP parser or Java solver.
No Java invocation, source/config modification, or performance measurements.
"""
from collections import deque, defaultdict, Counter
from pathlib import Path
import argparse
import re
T = [{'receiveTOR':1},{'validateTOR':2},{'torOk.0':3,'torOk.1':4},{'reviewTOR':0},{'readyTOR':0}]
D = [{'receiveDSD1':1},{'validateDSD1':2},{'dsd1Ok.0':3,'dsd1Ok.1':4},{'reviewDSD1':0},
     {'validateQA':5},{'qaOk.0':6,'qaOk.1':7},{'reviewDSD1':0},{'readyDSD1':0}]
G = [{'receiveGF1':1},{'validateGF1':2},{'adjustGF1':0,'approveGF1':0,'cancelGF1':0}]
C = ['validateTOR','validateDSD1','validateQA','validateGF1','reviewTOR','reviewDSD1','readyTOR','readyDSD1']
def physical(p):
    for i,L in enumerate([T,D,G]):
        for a,t in L[p[i]].items():
            q=list(p);q[i]=t;yield a,tuple(q)
def old_flags(f,a):
    t,d,x=f
    if a=='readyTOR':t=1
    if a in {'approveGF1','cancelGF1'}:t=0
    if a=='readyDSD1':d=1
    if a in {'approveGF1','cancelGF1','adjustGF1'}:d=0
    if a in {'approveGF1','cancelGF1'}:x=1
    if a in {'validateTOR','validateDSD1','validateGF1'}:x=0
    return t,d,x
def safe_old(f,a):
    t,d,x=f
    return not ((a in {'validateDSD1','validateGF1'} and not t) or (a=='validateGF1' and not d)
        or (d and a=='validateTOR') or (t and a=='validateTOR') or (d and a=='validateDSD1')
        or (x and a=='validateGF1'))
def old_controller():
    initial=((0,0,0),(0,0,0));Q=deque([initial]);S={initial};E={}
    while Q:
        q=Q.popleft();E[q]={}
        for a,p in physical(q[0]):
            f=old_flags(q[1],a)
            if not safe_old(f,a):continue
            # Finished is reset by validateGF1 itself, so its implication in
            # the old safety monitor is vacuous; the composed monitor need
            # only retain TORDone and DSD1Done. LTSA does not minimize the
            # complete old-controller/environment product in this log.
            t=(p,(f[0],f[1],0));E[q][a]=t
            if t not in S:S.add(t);Q.append(t)
    blocks={q:i for i,q in enumerate(sorted(S))}
    graph={blocks[q]:{a:blocks[t] for a,t in edges.items()} for q,edges in E.items()}
    mapping=defaultdict(set)
    for q in S:mapping[blocks[q]].add(q[0])
    assert len(graph)==64 and sum(map(len,graph.values()))==148
    return blocks[initial],graph,mapping

def check_mapping():
    root=(0,(0,0,0));seen={root};pending=deque([root]);count=0
    while pending:
        phase,state=pending.popleft()
        successors=[(phase,target) for _,target in physical(state)]
        if phase==0:successors.append((1,state))
        for target in successors:
            count+=1
            if target not in seen:seen.add(target);pending.append(target)
    assert (len(seen),count)==(240,1108)
    print('Mapping states/edges',len(seen),count)

def reconstruct(begin):
    initial,old,mapping=old_controller()
    normal=set(C)|{a for L in [T,D,G] for edges in L for a in edges}
    eu_alphabet=normal|{begin,'stopOldSpec','startNewSpec','reconfigure'}
    # Fluents: TORDone,DSD1Done,Finished,NewTORDone,internal stop/start,
    # user StopOldSpec/StartNewSpec, then one-hot last controllable event.
    def step(f,a):
        t,d,x,n,si,ni,su,nu,event=f
        t,d,x=old_flags((t,d,x),a)
        if a=='readyTOR':n=1
        if a in {'approveGF1','cancelGF1','adjustGF1'}:n=0
        if a=='stopOldSpec':si=su=1
        if a=='startNewSpec':ni=nu=1
        if a==begin:si=ni=0
        if a=='beginUpdate':su=nu=0
        if a in eu_alphabet:event=C.index(a)+1 if a in C else 0
        return t,d,x,n,si,ni,su,nu,event
    def edges(base):
        if base[0]=='C':
            for a,t in old[base[1]].items():yield a,('C',t)
            for p in mapping[base[1]]:yield begin,('M',0,p)
        else:
            _,phase,p=base
            for a,t in physical(p):yield a,('M',phase,t)
            for a in ['stopOldSpec','startNewSpec']:yield a,base
            if phase==0:yield 'reconfigure',('M',1,p)
        # An alphabet symbol found only in fluent automata interleaves freely.
        if 'beginUpdate' not in eu_alphabet:yield 'beginUpdate',base
    root=(('C',initial),(0,)*9);Q=deque([root]);S={root};E={}
    while Q:
        q=Q.popleft();E[q]=[]
        for a,base in edges(q[0]):
            target=(base,step(q[1],a));E[q].append((a,target))
            if target not in S:S.add(target);Q.append(target)
    print('BEGIN',begin,'meta states/edges',len(S),sum(map(len,E.values())),
          'pre/post',Counter(q[0][0] for q in S))
    def unsafe(q):
        t,d,x,n,si,ni,su,nu,event=q[1]
        a=C[event-1] if event else ''
        old_error=not safe_old((t,d,x),a)
        new_error=((a=='validateGF1' and not n) or (a in {'validateTOR','validateGF1'} and not d)
            or (n and a=='validateTOR') or (d and a=='validateDSD1') or (x and a=='validateGF1'))
        return ((not si and old_error) or (ni and new_error) or (su and not nu and event!=0))
    # Legacy pruning removes outgoing edges from violating states, then keeps
    # reachable states. Unsafe sinks are retained for the GR solver, not silently
    # removed as if the controller could suppress uncontrollables.
    def outgoing(q):return [] if unsafe(q) else E[q]
    Q=deque([root]);pruned={root};pruned_edges=0
    while Q:
        q=Q.popleft()
        for a,t in outgoing(q):
            pruned_edges+=1
            if t not in pruned:pruned.add(t);Q.append(t)
    print('pruned states/edges',len(pruned),pruned_edges)
    # Independent at-most-once monitors for stopOldSpec/startNewSpec. The mapping
    # process already makes reconfigure occur once. Repetitions lead to ERROR.
    error=('ERROR',)
    first=(root,0);Q=deque([first]);final={first};final_edges=0
    while Q:
        q=Q.popleft()
        if q==error:continue
        state,used=q
        for a,t in outgoing(state):
            bit={'stopOldSpec':1,'startNewSpec':2}.get(a,0)
            target=error if bit & used else (t,used|bit)
            final_edges+=1
            if target not in final:final.add(target);Q.append(target)
    print('after at-most-once states/edges',len(final),final_edges)
    expected={'hotSwapIn':(33093,257314,23810,129640,15177,90250),
              'beginUpdate':(14763,99676,None,None,3134,None)}[begin]
    actual=(len(S),sum(map(len,E.values())),len(pruned),pruned_edges,len(final),final_edges)
    assert all(x is None or x==y for x,y in zip(expected,actual)),(begin,actual,expected)
    request_target=next(t for a,t in E[root] if a==begin)
    if begin=='hotSwapIn':
        assert not unsafe(request_target)
        assert ('beginUpdate',request_target) in E[request_target]
        assert not any(request_target[1][4:8])
        assert (request_target,0) in final
        print('UC spoiler: hotSwapIn -> beginUpdate^omega; safe self-loop, all progress bits false')
    return root,S,E

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    default=Path(__file__).with_name('2017-TSE-Industry_T_Empty_active.lts')
    parser.add_argument('--model',type=Path,default=default)
    args=parser.parse_args()
    text=args.model.read_text()
    normalized=''.join(re.sub(r'//[^\n]*','',text).split())
    required=[
        'TOR=(receiveTOR->RECEIVED),RECEIVED=(validateTOR->RESPONSE),RESPONSE=(torOk[0]->reviewTOR->TOR|torOk[1]->readyTOR->TOR).',
        'DSD1=(receiveDSD1->RECEIVED),RECEIVED=(validateDSD1->DSD1RESPONSE),DSD1RESPONSE=(dsd1Ok[0]->reviewDSD1->DSD1|dsd1Ok[1]->validateQA->QARESPONSE),QARESPONSE=(qaOk[0]->reviewDSD1->DSD1|qaOk[1]->readyDSD1->DSD1).',
        'GATEFORM1=(receiveGF1->RECEIVED),RECEIVED=(validateGF1->GF1RESPONSE),GF1RESPONSE=({adjustGF1,approveGF1,cancelGF1}->GATEFORM1).',
        'BEFORE_RECONF=(reconfigure->AFTER_RECONF|A->BEFORE_RECONF),AFTER_RECONF=(A->AFTER_RECONF).',
        'fluentTORDone=<readyTOR,{approveGF1,cancelGF1}>',
        'fluentNewTORDone=<readyTOR,{approveGF1,adjustGF1,cancelGF1}>',
        'fluentDSD1Done=<readyDSD1,{approveGF1,adjustGF1,cancelGF1}>',
        'fluentFinished=<{approveGF1,cancelGF1},{validateTOR,validateDSD1,validateGF1}>',
        'fluentStopOldSpec=<stopOldSpec,beginUpdate>',
        'fluentStartNewSpec=<startNewSpec,beginUpdate>',
        'ltl_propertyT_Empty=((StopOldSpec&&!StartNewSpec)->(!AnyAction))',
        'assertAnyAction=(validateTOR||validateDSD1||validateQA||validateGF1||reviewTOR||reviewDSD1||readyTOR||readyDSD1)',
        'assertTOR_POLICY=((validateDSD1||validateGF1)->TORDone)',
        'assertDSD1_POLICY=((validateGF1->DSD1Done)&&(DSD1Done->!validateTOR))',
        'assertDO_NOT_SEND_TWICE=((TORDone->!validateTOR)&&(DSD1Done->!validateDSD1)&&(Finished->!validateGF1))',
        'assertNEW_TOR_POLICY=(validateGF1->NewTORDone)',
        'assertNEW_DSD1_POLICY=((validateTOR||validateGF1)->DSD1Done)',
        'assertNEW_DO_NOT_SEND_TWICE=((NewTORDone->!validateTOR)&&(DSD1Done->!validateDSD1)&&(Finished->!validateGF1))',
        'transition=T_Empty,']
    assert all(x in normalized for x in required),'Input does not match the supported, supplied Industry contract'
    print('Static model validated:',args.model.name)
    check_mapping()
    reconstruct('hotSwapIn')
    reconstruct('beginUpdate')
