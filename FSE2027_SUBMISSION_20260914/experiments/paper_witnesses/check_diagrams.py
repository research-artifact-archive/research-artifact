#!/usr/bin/env python3
"""Check the drawn TikZ edges and the explicitly scoped RQ2 correspondence."""
from pathlib import Path
import re
import check_witnesses as w
HERE=Path(__file__).resolve().parent
SUB=HERE.parents[1]
ROOT=SUB.parent
FIG=SUB/'paper/figures'
FSP=ROOT/'Implementation/Experiment/FSE2027/rq2-formal-witness/models'
text='\n'.join(p.read_text() for p in FIG.glob('witness_*.tex'))
edge_re=r'\\FGedge\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}\{[^}]*\}'
graphs={}
for graph,src,labels,dst in re.findall(edge_re,text):
    if graph.startswith('#'):continue
    for label in labels.split(','):
        graphs.setdefault(graph,set()).add((src,label.removeprefix('\\'),dst))
def triples(machine):
    return {(s,a,t) for (s,a),targets in machine.edges.items() for t in targets}
def expect(name,edges):
    assert graphs[name]==edges,(name,'missing',edges-graphs[name],'extra',graphs[name]-edges)
wc,wb,wr=w.cell(),w.branch(),w.requirement()
for name,comp,v in [('Ao',0,'o'),('An',0,'n'),('Bo',1,'o'),('Bn',1,'n')]:expect(name,triples(wc.components[comp][v]))
for name,machine in [('BrO',wb.components[0]['o']),('BrN',wb.components[0]['n']),('ReqO',wr.components[0]['o']),('ReqN',wr.components[0]['n'])]:expect(name,triples(machine))
for name,i,states in [('One',0,('A','B','E')),('Old',1,('k','E')),('Ins',2,('c','d','E'))]:
    expect(name,{(s,a,t) for (j,s,a),t in wc.monitor_edges.items() if i==j}|{('E','Sigma','E')})
    # Expand the declared totalization convention, including every error loop.
    explicit={(s,a):t for s,a,t in graphs[name]}
    for state in states:
        for event in wc.events:
            actual='E' if state=='E' else explicit.get((state,event),state)
            target='E' if state=='E' else wc.monitor_edges.get((i,state,event),state)
            assert actual==target
expect('ReqM',{('k','align','E'),('E','Sigma','E')})
expect('Co',{('co','m_A','co'),('co','m_B','co')})
expect('Cn',{('c','m_A','c'),('c','j','c'),('c','m_B','d'),('d','m_B','d'),('d','j','c')})
expect('OldCL',{('xA','m_B','xB'),('xB','m_A','xA')})
expect('NewCL',{('zA','m_B','yB'),('yB','j','zB'),('zB','m_A','zA'),('zB','j','zB')})
seen=set();edge_count=0
for holder,graph,actions in [('A','PA',('rho_B','m_B','s','t','j','rho_A')),('B','PB',('rho_A','m_A','s','t','rho_B'))]:
    expect(graph,{(str(i),a,str(i+1)) for i,a in enumerate(actions)})
    q=next(q for q in wc.roots if q.monitors[0]==holder);path=[q]
    for a in actions:
        outcomes=wc.post(q,a);assert len(outcomes)==1
        q=next(iter(outcomes));assert wc.safe(q);path.append(q)
    assert wc.goal(q)
    # The foreach state strings must agree with the actual Post successors.
    match=re.search(r'\\foreach \\n/\\txt in \{([^}]+)\}\s*\\node\[ps\] \('+graph+r'-',text)
    assert match,graph
    labels=match[1].split(',')
    expected=[f'{i}/'+''.join(q.versions)+q.monitors[0]+';'+''.join(q.monitors[1:]) for i,q in enumerate(path)]
    assert labels==expected,(graph,labels,expected)
    seen.update(path);edge_count+=len(actions)
assert len(seen)==13 and edge_count==11
# Parse only the explicit, single-event finite state equations used by these fixtures.
def fsp_edges(filename):
    content=re.sub(r'//[^\n]*','',(FSP/filename).read_text())
    return {(s,a,t) for s,body in re.findall(r'(?<!\|)\b(\w+)\s*=\s*\(([^()]*)\)\s*[,.]',content)
            for a,t in re.findall(r'\b(\w+)\s*->\s*(\w+)',body)}
def compare(name,filename,mapping,events,omit=frozenset()):
    selected={(mapping[s],events.get(a,a),mapping[t]) for s,a,t in graphs[name] if a not in omit}
    actual={x for x in fsp_edges(filename) if x[0] in mapping.values()}
    assert selected==actual,(name,selected-actual,actual-selected)
    return len(actual)
n=0
for name,prefix in [('Ao','A_OLD'),('An','A_NEW'),('Bo','B_OLD'),('Bn','B_NEW')]:
    n+=compare(name,'pc_separation_local_fg.lts',{'h':prefix+'_HOLD','e':prefix+'_EMPTY'},{'m_A':'moveA','m_B':'moveB'},frozenset({'j'}))
b=compare('BrO','branching_separation.lts',dict(w='WAIT',a0='BRANCH_A',b0='BRANCH_B',a1='READY_A',b1='READY_B'),dict(d_A='dA',d_B='dB'))
b+=compare('BrN','branching_separation.lts',dict(x='NEW_A',y='NEW_B'),dict(d_A='dA',d_B='dB'))
r=compare('ReqO','requirement_boundary_separation.lts',dict(w='OLD_WAIT',r='OLD_READY'),{})
r+=compare('ReqN','requirement_boundary_separation.lts',dict(n='ALIGN_NEW'),{})
# Dashed transfer arrows are relations, never ordinary plant events. Parse the
# actual drawing commands and reject any unparsed or duplicate dashed arrow.
transfer_re=(r'\\draw\[([^\]]*\bdashed\b[^\]]*)\]\s*\(([^)]+)\)\s*--\s*'
             r'node\[[^\]]*\]\s*\{\$(g(?:_[A-Za-z]+)?)\$\}\s*\(([^)]+)\)\s*;')
drawn=[]
for options,source,label,target in re.findall(transfer_re,text):
    assert '->' in options,('transfer must be directed',source,target)
    old,src=source.rsplit('-',1);new,dst=target.rsplit('-',1)
    drawn.append((old,src,label,new,dst))
assert len(drawn)==len(re.findall(r'\\draw\[[^\]]*\bdashed\b[^\]]*\]',text)), 'Unparsed dashed transfer'
assert len(set(drawn))==len(drawn), 'Duplicate drawn transfer'

# This bounded parser accepts only the finite relation syntax present in the
# three fixed RQ2 fixtures. It validates every entry instead of skipping text.
def fixture_relations(filename):
    content=re.sub(r'//[^\n]*','',(FSP/filename).read_text())
    relations={}
    for name,body in re.findall(r'\brelation\s+(\w+)\s*=\s*\{([^{}]*)\}',content):
        assert name not in relations,('duplicate relation',filename,name)
        entries=[]
        for entry in body.split(','):
            match=re.fullmatch(r'\s*(\w+)@(\w+)\s*=\s*(\w+)\s*->\s*(\w+)@(\w+)\s*',entry)
            assert match,('unsupported relation entry',filename,name,entry)
            entries.append(match.groups())
        assert len(entries)==len(set(entries)),('duplicate relation pair',filename,name)
        relations[name]=set(entries)
    selections={}
    for controller,body in re.findall(r'\bupdatingController\s+(\w+)\s*=\s*\{(.*?)^\}',content,re.M|re.S):
        maps=re.findall(r'\bmapRelation\s*=\s*\{([^{}]*)\}',body)
        assert len(maps)==1,('one mapRelation expected',filename,controller)
        names=tuple(item.strip() for item in maps[0].split(','))
        assert len(names)==len(set(names)) and all(name in relations for name in names)
        selections[controller]=names
    return relations,selections

fixture_data={name:fixture_relations(name) for name in (
    'pc_separation_local_fg.lts','branching_separation.lts','requirement_boundary_separation.lts')}
expected_selections={
    'pc_separation_local_fg.lts':{'Rq2ProductionCellLocal':('R_A_FG','R_B_FG')},
    'branching_separation.lts':{name:('R_BRANCH_FG',) for name in ('BranchFull','BranchFixedA','BranchFixedB')},
    'requirement_boundary_separation.lts':{'RequirementBoundary':('R_ALIGN_FG',)}}
for filename,selections in expected_selections.items():
    relations,actual=fixture_data[filename]
    assert actual==selections,('mapRelation selection mismatch',filename,actual,selections)
    assert set(relations)=={name for selected in selections.values() for name in selected},('unaccounted relation',filename)

transfer_specs=[
    ('W_cell A',wc,0,'Ao','An','g_A','pc_separation_local_fg.lts','R_A_FG',
     {'e':'A_OLD_EMPTY','h':'A_OLD_HOLD'},{'e':'A_NEW_EMPTY','h':'A_NEW_HOLD'},'A_OLD','A_NEW','reconfigure_A'),
    ('W_cell B',wc,1,'Bo','Bn','g_B','pc_separation_local_fg.lts','R_B_FG',
     {'e':'B_OLD_EMPTY','h':'B_OLD_HOLD'},{'e':'B_NEW_EMPTY','h':'B_NEW_HOLD'},'B_OLD','B_NEW','reconfigure_B'),
    ('W_b',wb,0,'BrO','BrN','g','branching_separation.lts','R_BRANCH_FG',
     {'w':'WAIT','a0':'BRANCH_A','b0':'BRANCH_B','a1':'READY_A','b1':'READY_B'},
     {'x':'NEW_A','y':'NEW_B'},'BRANCH_OLD','BRANCH_NEW','reconfigure_BRANCH'),
    ('W_r',wr,0,'ReqO','ReqN','g','requirement_boundary_separation.lts','R_ALIGN_FG',
     {'w':'OLD_WAIT','r':'OLD_READY'},{'n':'ALIGN_NEW'},'ALIGN_OLD','ALIGN_NEW','reconfigure_ALIGN')]
checked=set();transfer_counts=[]
for label,contract,component,old,new,g,filename,relation,old_names,new_names,old_process,new_process,event in transfer_specs:
    arrows={item for item in drawn if item[0]==old and item[3]==new}
    assert all(item[2]==g for item in arrows),('wrong transfer label',label,arrows)
    pairs={(item[1],item[4]) for item in arrows}
    expected={(source,target) for source,targets in contract.transfers[component].items() for target in targets}
    assert pairs==expected,('drawn/finite-checker transfer mismatch',label,pairs,expected)
    projected={(old_names[source],old_process,event,new_names[target],new_process) for source,target in pairs}
    actual=fixture_data[filename][0][relation]
    assert projected==actual,('drawn/RQ2 transfer mismatch',label,projected,actual)
    checked.update(arrows);transfer_counts.append((label,len(pairs)))
assert checked==set(drawn),('unaccounted drawn transfer',set(drawn)-checked)

req=(FSP/'requirement_boundary_separation.lts').read_text()
for definition in ('assert OLD_SAFETY = !align','assert NEW_SAFETY = !align','startNewSpec_P_NEW_SAFETY -> Aligned'):assert definition in req
print('PASS: all drawn W_cell/W_b/W_r primitive edges, total monitor transitions, endpoints and 13-state/11-edge policy.')
print(f'RQ2 edge correspondence: cell plant projection {n}, branch {b}, requirement plant {r}; requirement rejection formulas/start guard confirmed.')
print('PASS dashed transfers: '+', '.join(label+'='+str(count) for label,count in transfer_counts)+'; all 5 drawn pairs equal the finite checker and the RQ2 relations under the explicit state/event renaming.')
print('PASS RQ2 mapRelation: all 5 updating-controller declarations select the expected 4 relation definitions; no extra/duplicate transfer pairs.')
print('Scope: cell equality is only the move-labelled plant projection and empty-state transfers. The executable cell has no inspection or lifecycle monitors; paper adds j and r_one/r_old/r_inspect. Requirement plant and transfer correspond, but the fixture uses safety formulas plus a start-after-align guard rather than the paper monitor error-state/Start encoding. Branch plant and transfer correspond under state/event renaming. No full-game isomorphism claimed.')
