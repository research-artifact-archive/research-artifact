#!/usr/bin/env python3
"""Reconstruct the three paper-contained finite contracts using only Python.

Primitives are transcribed from paper Figures wcell-complete/other-witnesses.
The four Post rules, NP guard, unsafe terminals, and quiescent endpoint test
are implemented here without importing MTSA, the experiment oracle, or results.
Full closure includes successors beyond unsafe states and goals; winning and
policy checks terminalize them as specified. This is a finite-model check,
not verification of external RS or A1--A4 premises.
"""
from __future__ import annotations
import argparse, csv, json
from collections import Counter, deque
from dataclasses import dataclass, replace
from itertools import product
from pathlib import Path

@dataclass(frozen=True)
class State:
    versions: tuple
    local: tuple
    monitors: tuple
    pending: frozenset

@dataclass(frozen=True)
class ProgramState:
    game: State
    position: int

class FixedList:
    """Literal finite list; UC observations never advance its cursor."""
    def __init__(self,base,events):
        self.base=base;self.sequence=tuple(events);self.events=base.events;self.uc=base.uc
        self.name=base.name+'_list_'+'_'.join(events)
        self.roots=frozenset(ProgramState(q,0) for q in base.roots)
    def post(self,q,event):
        if event in self.uc:position=q.position
        elif q.position<len(self.sequence) and event==self.sequence[q.position]:position=q.position+1
        else:return frozenset()
        return frozenset(ProgramState(target,position) for target in self.base.post(q.game,event))
    def safe(self,q):return self.base.safe(q.game)
    def goal(self,q):return self.base.goal(q.game)
    def enabled_uc(self,q):return self.base.enabled_uc(q.game)

@dataclass
class Local:
    states: tuple
    initial: str
    alphabet: frozenset
    edges: dict

def local(states,initial,alphabet,triples):
    edges={}
    for source,event,target in triples:edges.setdefault((source,event),set()).add(target)
    return Local(tuple(states),initial,frozenset(alphabet),{k:frozenset(v) for k,v in edges.items()})

class Contract:
    def __init__(self,name,components,ordinary,uncontrollable,updates,transfers,monitor_names,monitor_edges,
                 old_monitors,new_monitors,update_monitors,starts,precedence,roots,load_projections):
        self.name=name;self.components=components;self.ordinary=tuple(ordinary);self.uc=frozenset(uncontrollable)
        self.updates=updates;self.events=tuple(ordinary)+tuple(updates);self.transfers=transfers
        self.monitor_names=tuple(monitor_names);self.monitor_edges=monitor_edges
        self.old=frozenset(old_monitors);self.new=frozenset(new_monitors);self.interval=frozenset(update_monitors)
        self.starts=starts;self.precedence=frozenset(precedence);self.roots=frozenset(roots)
        self.load=frozenset(load_projections)
    def active(self,q):
        return {i for i,value in enumerate(q.monitors) if value!='-'}
    def advance(self,q,event,excluded=frozenset()):
        result=list(q.monitors)
        for i in self.active(q)-set(excluded):
            state=result[i]
            result[i]='E' if state=='E' else self.monitor_edges.get((i,state,event),state)
        return tuple(result)
    def ordinary_targets(self,q,event):
        choices=[];participant=False
        for i,(version,state) in enumerate(zip(q.versions,q.local)):
            machine=self.components[i][version]
            if event in machine.alphabet:
                participant=True;choices.append(machine.edges.get((state,event),frozenset()))
            else:choices.append((state,))
        return frozenset(product(*choices)) if participant else frozenset()
    def enabled_uc(self,q):
        # Plant enabledness, including outcomes that enter error monitor states.
        return frozenset(event for event in self.uc if self.ordinary_targets(q,event))
    def post(self,q,event):
        if event in self.ordinary:
            return frozenset(replace(q,local=target,monitors=self.advance(q,event)) for target in self.ordinary_targets(q,event))
        if event not in q.pending or self.enabled_uc(q):return frozenset()
        if any(before in q.pending for before,after in self.precedence if after==event):return frozenset()
        kind,index=self.updates[event];pending=q.pending-{event}
        if kind=='transfer':
            if q.versions[index]!='o':return frozenset()
            result=set()
            for target in self.transfers[index].get(q.local[index],()):
                versions=list(q.versions);versions[index]='n';states=list(q.local);states[index]=target
                result.add(State(tuple(versions),tuple(states),self.advance(q,event),pending))
            return frozenset(result)
        if kind=='stop':
            monitors=list(self.advance(q,event,{index}));monitors[index]='-'
            return frozenset({replace(q,monitors=tuple(monitors),pending=pending)})
        if kind=='start':
            initialize=self.starts[index]
            initial=initialize(q)
            if initial is None:return frozenset()
            monitors=list(self.advance(q,event));monitors[index]=initial
            return frozenset({replace(q,monitors=tuple(monitors),pending=pending)})
        raise ValueError(kind)
    def safe(self,q):return all(q.monitors[i]!='E' for i in self.active(q))
    def goal(self,q):
        projection=(q.local,tuple(q.monitors[i] for i in sorted(self.new)))
        return not q.pending and all(v=='n' for v in q.versions) and self.safe(q) and not self.enabled_uc(q) and projection in self.load

def enumerate_game(contract,restriction=lambda q,a:True):
    seen=set(contract.roots);queue=deque(sorted(seen,key=repr));edges={}
    while queue:
        q=queue.popleft();buckets={}
        for event in contract.events:
            targets=contract.post(q,event) if restriction(q,event) else frozenset()
            buckets[event]=targets
            for target in targets:
                if target not in seen:seen.add(target);queue.append(target)
        edges[q]=buckets
    return frozenset(seen),edges

def solve(contract,states,edges):
    ranks={q:0 for q in states if contract.goal(q)};policy={}
    while True:
        added={};choices={}
        for q in sorted(states-ranks.keys(),key=repr):
            if not contract.safe(q):continue
            uc=[targets for event,targets in edges[q].items() if event in contract.uc and targets]
            if uc:
                targets=frozenset().union(*uc)
                if targets<=ranks.keys():added[q]=1+max(ranks[t] for t in targets);choices[q]=None
            else:
                winning=[(1+max(ranks[t] for t in targets),event) for event,targets in edges[q].items() if targets and targets<=ranks.keys()]
                if winning:added[q],choices[q]=min(winning)
        if not added:break
        ranks.update(added);policy.update(choices)
    losing=states-ranks.keys()
    # Check the complement as an explicit closed obstruction, including deadlocks.
    for q in losing:
        assert not contract.goal(q)
        if not contract.safe(q):continue
        uc=[targets for event,targets in edges[q].items() if event in contract.uc and targets]
        if uc:assert any(t in losing for targets in uc for t in targets)
        else:assert all(any(t in losing for t in targets) for targets in edges[q].values() if targets)
    return ranks,policy

def check_policy(contract,policy,ranks,roots=None):
    roots=contract.roots if roots is None else roots
    seen=set(roots);queue=deque(roots);edge_count=0
    while queue:
        q=queue.popleft();assert contract.safe(q),(contract.name,'unsafe retained',q)
        if contract.goal(q):assert ranks[q]==0;continue
        action=policy.get(q)
        events=set(contract.enabled_uc(q)) | ({action} if action is not None else set())
        targets=set()
        for event in events:
            outcomes=contract.post(q,event);assert outcomes,(q,event)
            edge_count+=len(outcomes);targets.update(outcomes)
        assert targets,(contract.name,'non-goal policy deadlock',q)
        for target in targets:
            assert target in ranks and ranks[target]<ranks[q],(q,target)
            if target not in seen:seen.add(target);queue.append(target)
    return seen,edge_count

def branch():
    labels=('idle','u','a','b','d_A','d_B');old_states=('w','a0','b0','a1','b1');new_states=('x','y')
    old=local(old_states,'w',labels,[(s,'idle',s) for s in old_states]+[('w','u','a0'),('w','u','b0'),('a0','a','a1'),('b0','b','b1'),('a1','d_A','w'),('b1','d_B','w')])
    new=local(new_states,'x',('idle','d_A','d_B'),[(s,'idle',s) for s in new_states]+[('x','d_A','y'),('y','d_B','x')])
    roots=[State(('o',),(s,),(),frozenset({'rho'})) for s in old_states]
    return Contract('W_b',[dict(o=old,n=new)],labels,{'u'},{'rho':('transfer',0)},[{'a1':('x',),'b1':('y',)}],[],{},[],[],[],{},[],roots,[(('x',),()),(('y',),())])

def requirement():
    old=local(('w','r'),'w',('idle','align'),[('w','idle','w'),('w','align','r'),('r','idle','r')])
    new=local(('n',),'n',('idle',),[('n','idle','n')])
    roots=[State(('o',),('w',),('k','-'),frozenset({'rho','t','s'}))]
    start=lambda q:'k' if (q.versions[0],q.local[0]) in {('o','r'),('n','n')} else None
    return Contract('W_r',[dict(o=old,n=new)],('idle','align'),[],{'rho':('transfer',0),'t':('stop',0),'s':('start',1)},[{'r':('n',)}],
                    ('old','new'),{(0,'k','align'):'E',(1,'k','align'):'E'},[0],[1],[],{1:start},[],roots,[(('n',),('k',))])

def cell(bulk=False):
    a=local(('h','e'),'h',('m_A','m_B'),[('h','m_B','e'),('e','m_A','h')])
    bo=local(('h','e'),'e',('m_A','m_B'),[('e','m_B','h'),('h','m_A','e')])
    bn=local(('h','e'),'e',('m_A','m_B','j'),[('e','m_B','h'),('h','m_A','e'),('h','j','h')])
    monitors={(0,'A','m_B'):'B',(0,'B','m_A'):'A',(0,'A','m_A'):'E',(0,'B','m_B'):'E',
              (1,'k','j'):'E',(2,'c','m_B'):'d',(2,'d','j'):'c',(2,'d','m_A'):'E'}
    if not bulk:
        updates={'rho_A':('transfer',0),'rho_B':('transfer',1),'s':('start',2),'t':('stop',1)}
        roots=[State(('o','o'),loc,(holder,'k','-'),frozenset(updates)) for loc,holder in [(('h','e'),'A'),(('e','h'),'B')]]
        start=lambda q:'d' if q.local[1]=='h' else 'c'
        return Contract('W_cell',[dict(o=a,n=a),dict(o=bo,n=bn)],('m_A','m_B','j'),[],updates,
                        [{'e':('e',)},{'e':('e',)}],('one','old','inspect'),monitors,[1],[2],[0],{2:start},{('s','t')},roots,
                        [(('h','e'),('c',)),(('e','h'),('c',))])
    old=local(('A','B'),'A',('m_A','m_B'),[('A','m_B','B'),('B','m_A','A')])
    new=local(('A','B'),'A',('m_A','m_B','j'),[('A','m_B','B'),('B','m_A','A'),('B','j','B')])
    updates={'rho_star':('transfer',0),'s':('start',2),'t':('stop',1)}
    roots=[State(('o',),(holder,),(holder,'k','-'),frozenset(updates)) for holder in ('A','B')]
    return Contract('W_cell_bulk',[dict(o=old,n=new)],('m_A','m_B','j'),[],updates,[{}],
                    ('one','old','inspect'),monitors,[1],[2],[0],{2:lambda q:'d' if q.local[0]=='B' else 'c'},{('s','t')},roots,
                    [(('A',),('c',)),(('B',),('c',))])

def encode(q):
    if isinstance(q,ProgramState):return dict(game=encode(q.game),list_position=q.position)
    return dict(versions=q.versions,local=q.local,monitors=q.monitors,pending=sorted(q.pending))
def analyze(contract,name,out,restriction=lambda q,a:True):
    states,edges=enumerate_game(contract,restriction);ranks,policy=solve(contract,states,edges)
    order=sorted(states,key=repr);ids={q:i for i,q in enumerate(order)}
    counts=Counter(event for q,buckets in edges.items() for event,targets in buckets.items() if targets)
    safe=sum(contract.safe(q) for q in states);goals=sum(contract.goal(q) for q in states)
    row=dict(case=name,states=len(states),safe=safe,unsafe=len(states)-safe,goals=goals,buckets=len(states)*len(contract.events),
             nonempty_buckets=sum(counts.values()),empty_buckets=len(states)*len(contract.events)-sum(counts.values()),
             outcomes=sum(len(ts) for buckets in edges.values() for ts in buckets.values()),roots=len(contract.roots),
             winning_roots=sum(q in ranks for q in contract.roots),all_root_decision='WIN' if contract.roots<=ranks.keys() else 'LOSS',
             root_ranks=json.dumps({str(encode(q)):ranks.get(q,'LOSS') for q in sorted(contract.roots,key=repr)}),
             nonempty_by_event=json.dumps(dict(counts),sort_keys=True))
    record=dict(case=name,source='paper/figures: wcell-complete and other-witnesses; supplement.tex:S1',
                closure_includes_unsafe_and_goal_successors=True,states=[encode(q) for q in order],roots=[ids[q] for q in contract.roots],
                goals=[ids[q] for q in states if contract.goal(q)],unsafe=[ids[q] for q in states if not contract.safe(q)],
                rank={ids[q]:rank for q,rank in ranks.items()},losing=[ids[q] for q in states if q not in ranks],
                buckets={ids[q]:{a:sorted(ids[t] for t in ts) for a,ts in edges[q].items()} for q in order},
                policy={ids[q]:a for q,a in policy.items()})
    if name=='W_b_fixed_head_a':record['restriction']='All-time removal of b; concrete obstruction, not literal list enumeration.'
    if name=='W_b_fixed_head_b':record['restriction']='All-time removal of a; concrete obstruction, not literal list enumeration.'
    if isinstance(contract,FixedList):record['fixed_list']=contract.sequence;record['uncontrollables_advance_position']=False
    (out/(name+'.json')).write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(row,sort_keys=True));return row,states,edges,ranks,policy

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parent/'raw');args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True);rows=[]
    wb=branch();wr=requirement()
    row,states,edges,ranks,policy=analyze(wb,'W_b_full',args.output);rows.append(row)
    assert row['all_root_decision']=='WIN' and row['winning_roots']==5
    assert {q.local[0]:ranks[q] for q in wb.roots}==dict(w=3,a0=2,b0=2,a1=1,b1=1)
    check_policy(wb,policy,ranks)
    for allowed,forbidden in [('a','b'),('b','a')]:
        result,*_=analyze(wb,'W_b_fixed_head_'+allowed,args.output,lambda q,event,forbidden=forbidden:event!=forbidden)
        assert result['all_root_decision']=='LOSS' and result['winning_roots']==3;rows.append(result)
    for head in ('a','b'):
        program=FixedList(wb,(head,'rho'))
        result,_,_,winning,_=analyze(program,'W_b_literal_list_'+head+'_rho',args.output)
        root_w=next(q for q in program.roots if q.game.local==('w',))
        assert result['all_root_decision']=='LOSS' and root_w not in winning
        assert all(q.position==0 for q in program.post(root_w,'u'))
        rows.append(result)
    # The universal fixed-list obstruction is a structural head test, not a
    # claim established by enumerating bounded list lengths. Idle prefixes
    # preserve both branch states; their non-idle enabled head sets are disjoint.
    branches={s:next(q for q in wb.roots if q.local==(s,)) for s in ('a0','b0')}
    heads={s:{a for a in wb.events if a not in wb.uc|{'idle'} and wb.post(q,a)} for s,q in branches.items()}
    assert heads=={'a0':{'a'},'b0':{'b'}}
    assert not set.intersection(*heads.values())
    for q in branches.values():assert wb.post(q,'idle')==frozenset({q})
    (args.output/'W_b_head_obstruction.json').write_text(json.dumps(dict(nonidle_enabled_heads={s:sorted(v) for s,v in heads.items()},common_heads=[],finite_idle_prefix_changes_branch=False),indent=2)+'\n')
    row,states,edges,ranks,policy=analyze(wr,'W_r_full',args.output);rows.append(row)
    assert row['all_root_decision']=='WIN'
    q=next(iter(wr.roots));path=[q]
    for action in ('t','align','s','rho'):
        outcomes=wr.post(q,action);assert len(outcomes)==1;q=next(iter(outcomes));path.append(q)
    assert [ranks[q] for q in path]==[4,3,2,1,0]
    check_policy(wr,{q:a for q,a in zip(path,('t','align','s','rho'))},{q:4-i for i,q in enumerate(path)})
    # Weaker than the Java block: only ordinary events, not component transfer,
    # are forbidden while exactly one boundary remains pending.
    contiguous=lambda q,a:not(a in wr.ordinary and len(q.pending&{'t','s'})==1)
    row,*_=analyze(wr,'W_r_contiguous',args.output,contiguous);rows.append(row);assert row['all_root_decision']=='LOSS'
    # Atomic stop/start has no enabled initial boundary: its start guard is
    # false at w; aligning first enters the active old monitor's error.
    assert wr.starts[1](next(iter(wr.roots))) is None
    assert all(not wr.safe(q) for q in wr.post(next(iter(wr.roots)),'align'))
    wc=cell();row,states,edges,ranks,policy=analyze(wc,'W_cell_full',args.output);rows.append(row)
    expected=dict(states=56,safe=26,unsafe=30,goals=2,buckets=392,nonempty_buckets=139,empty_buckets=253,outcomes=139)
    assert {k:row[k] for k in expected}==expected,('cell census mismatch',row)
    assert json.loads(row['nonempty_by_event'])==dict(m_A=30,m_B=26,j=20,rho_A=15,rho_B=10,s=12,t=26)
    assert sum(wc.safe(q) and not wc.safe(t) for q,bs in edges.items() for ts in bs.values() for t in ts)==12
    roots={q.monitors[0]:q for q in wc.roots};certificate={};certificate_rank={};certificate_states=set()
    for holder,actions in [('A',('rho_B','m_B','s','t','j','rho_A')),('B',('rho_A','m_A','s','t','rho_B'))]:
        q=roots[holder];certificate_states.add(q);certificate_rank[q]=len(actions)
        for i,action in enumerate(actions):
            certificate[q]=action;targets=wc.post(q,action);assert len(targets)==1
            q=next(iter(targets));certificate_states.add(q);certificate_rank[q]=len(actions)-i-1
        assert wc.goal(q)
    visited,retained_edges=check_policy(wc,certificate,certificate_rank)
    assert len(visited)==len(certificate_states)==13 and retained_edges==11
    (args.output/'W_cell_policy.json').write_text(json.dumps(dict(states=[encode(q) for q in sorted(visited,key=repr)],
        retained_states=13,retained_edges=11,ranked_policy=[dict(source=encode(q),event=a,rank=certificate_rank[q]) for q,a in certificate.items()]),indent=2)+'\n')
    bulk=cell(True);row,*_=analyze(bulk,'W_cell_bulk',args.output);rows.append(row)
    expected=dict(states=10,safe=6,unsafe=4,goals=0,buckets=60,nonempty_buckets=16,empty_buckets=44,outcomes=16)
    assert {k:row[k] for k in expected}==expected,('bulk census mismatch',row)
    assert row['all_root_decision']=='LOSS'
    with (args.output/'summary.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    print('PASS: paper W_b/W_r decisions, ranks and head obstruction; W_cell/bulk full census and 13-state/11-edge certificate')

if __name__=='__main__':main()
