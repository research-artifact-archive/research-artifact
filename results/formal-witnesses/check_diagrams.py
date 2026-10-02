#!/usr/bin/env python3
"""Check finite paper diagrams/tables against primitives and scoped RQ2 fixtures.

Supports the current main Cell table and appendix paths, the earlier split
tables/overview, and the original complete TikZ cell.
Parsers accept the explicitly displayed finite syntax; unsupported notation fails.
No JVM, saved baseline, synthesis, or model edit is used.
"""
from pathlib import Path
import argparse
import contextlib
import io
import shutil
import tempfile
import re
import json
import sys
import check_witnesses as w
HERE=Path(__file__).resolve().parent
SUB=HERE.parents[1]
ROOT=SUB.parent
FIG=SUB/'paper/figures'
FSP=ROOT/'Implementation/Experiment/FSE2027/rq2-formal-witness/models'
CURRENT_PAPER_FILES = (
    'main.tex', 'technical_appendix.tex', 'technical_fragments/cell.tex',
    'figures/cell_finite_main.tex', 'figures/cell_policy_paths.tex',
    'figures/cell_story_visual.tex', 'figures/policy_lifetimes.tex',
    'figures/witness_other.tex',
)


def current_layout(paper):
    main = paper/'main.tex'
    return main.is_file() and r'\input{figures/cell_finite_main.tex}' in read_text(main)


def current_paths(source):
    """Read every displayed Cell state, monitor coordinate, action and rank."""
    nodes = {}
    pattern = (r'\\node\[state\]\s*\(([ab]\d+)\)[^\n]*?\{\$\(([on]{2});([AB]);'
               r'([kcd{}-]+)\)\$\\\\rank (\d+)\};')
    for name, versions, holder, monitors, rank in re.findall(pattern, source):
        assert name not in nodes, ('duplicate policy state', name)
        nodes[name] = (versions+holder+';'+monitors.replace('{-}', '-'), int(rank))
    expected = {'a'+str(i) for i in range(7)} | {'b'+str(i) for i in range(6)}
    assert set(nodes) == expected, ('policy state inventory', set(nodes))
    assert len(re.findall(r'\\node\[state\]', source)) == len(nodes), 'Unparsed policy state'
    edge_pattern = (r'\\draw\[edge\]\s*\(([ab]\d+)\)--node\[action\]'
                    r'\{\$(.*?)\$\}\(([ab]\d+)\);')
    edges = re.findall(edge_pattern, source)
    assert len(edges) == len(set(edges)) == 11, 'Policy edge inventory/duplicates'
    assert len(re.findall(r'\\draw\[edge\]', source)) == len(edges), 'Unparsed policy edge'
    paths = {}
    for holder, prefix, length in [('A', 'a', 7), ('B', 'b', 6)]:
        incoming = {target: (origin, event(label)) for origin, label, target in edges
                    if target.startswith(prefix)}
        assert set(incoming) == {prefix+str(i) for i in range(1, length)}, ('policy targets', holder)
        rows = [('entry', *nodes[prefix+'0'])]
        for i in range(1, length):
            origin, action = incoming[prefix+str(i)]
            assert origin == prefix+str(i-1), ('policy edge source', holder, i, origin)
            rows.append((action, *nodes[prefix+str(i)]))
        paths[holder] = rows
    return paths


def current_visuals(paper):
    """Bind the two current figures to checked Cell paths and saved Policy data."""
    package = next((p for p in HERE.parents
                    if (p/'reproduce/check_visual_evidence.py').is_file()), None)
    assert package is not None, 'Missing packaged visual evidence readers'
    sys.path.insert(0, str(package/'reproduce'))
    import check_visual_evidence as visual
    import check_policy_evidence as policy
    visual.verify_cell(read_text(paper/'figures/cell_story_visual.tex'),
                       read_text(paper/'figures/cell_policy_paths.tex'))
    candidates = (package/'results/granularity/e6/policy/v2',
                  package/'FSE2027_SUBMISSION_20260914/experiments/witness_20260929/e6/policy/v2')
    evidence = next((p for p in candidates if (p/'inputs/policy_2_fine.json').is_file()), None)
    assert evidence is not None, 'Missing saved Policy input/certificate'
    load = lambda name: json.loads((evidence/name).read_text())
    policy.verify_figure(read_text(paper/'figures/policy_lifetimes.tex'),
                         load('inputs/policy_2_fine.json'), load('inputs/policy_2_coarse.json'),
                         load('raw/series/policy_fine_none_lazy/certificate.json'))
    print('PASS current figures: both Cell paths and all seven Policy states/six edges, entries, ranks and active bands.')
def read_text(path):
    return re.sub(r'%[^\n]*', '', path.read_text())


def atom(text):
    return text.replace(r"\mathsf{err}", "E").replace("c_o", "co").replace("c_0", "c").replace("c_1", "d")


def event(text):
    return text.strip().strip('$').replace(r"\mathsf{start}", "s").replace(r"\mathsf{stop}", "t").replace(r"\rho", "rho")


def table_cell(paper, current=False):
    """Strict parser for the displayed finite inventories; no baseline file comparison."""
    source = read_text(paper/('figures/cell_finite_main.tex' if current else 'figures/cell_components.tex'))
    aliases = {r'$A^o,A^n$': ('Ao','An'), r'$B^o$': ('Bo',), r'$B^n$': ('Bn',),
               r'$C^o$': ('Co',), r'$C^n$': ('Cn',),
               r'$t_{r_{\rm one}}$': ('One',), r'$t_{r_{\rm old}}$': ('Old',),
               r'$t_{r_{\rm inspect}}$': ('Ins',)}
    graphs, initials, states = {}, {}, {}
    for line in source.splitlines():
        fields = line.split(r'\\', 1)[0].split('&')
        if current and len(fields)==3 and fields[0].strip() not in aliases:
            assert fields[0].strip() == 'Object', ('unknown displayed object', fields[0])
        if len(fields)!=3 or fields[0].strip() not in aliases:
            continue
        names = aliases[fields[0].strip()]
        declaration = atom(fields[1]).replace('$','').strip()
        match = re.fullmatch(r'([A-Za-z,]+)\s*\(([A-Za-z]+)\)', declaration)
        assert match, ('unparsed states/initial', declaration)
        local_states, initial = tuple(match[1].split(',')), match[2]
        assert initial in local_states and len(set(local_states))==len(local_states)
        body = atom(fields[2]).replace('$','').strip()
        pattern = r'([A-Za-z]+)\\xrightarrow\{([^{}]+)\}([A-Za-z]+)'
        edges = []
        for a, labels, b in re.findall(pattern, body):
            assert a in local_states and b in local_states, ('unknown endpoint', names,a,b)
            edges.extend((a,label.strip(),b) for label in labels.split(','))
        assert re.sub(pattern, '', body).replace(',','').strip()=='', ('unparsed transitions', names,body)
        assert len(edges)==len(set(edges)), ('duplicate edge', names)
        for name in names:
            assert name not in graphs, ('duplicate object', name)
            graphs[name]=set(edges); initials[name]=initial; states[name]=local_states
    assert set(graphs)=={'Ao','An','Bo','Bn','Co','Cn','One','Old','Ins'}, ('incomplete component inventory',graphs.keys())
    contract=w.cell()
    for name,component,version in [('Ao',0,'o'),('An',0,'n'),('Bo',1,'o'),('Bn',1,'n')]:
        assert set(states[name])==set(contract.components[component][version].states), ('component states',name)
    for name,expected in [('Co',{'co'}),('Cn',{'c','d'}),('One',{'A','B','E'}),('Old',{'k','E'}),('Ins',{'c','d','E'})]:
        assert set(states[name])==expected, ('controller/monitor states',name)
    if current:
        main = read_text(paper/'main.tex')
        appendix = read_text(paper/'technical_appendix.tex')
        section = read_text(paper/'technical_fragments/cell.tex')
        assert r'\input{technical_fragments/cell.tex}' in appendix, 'Cell definitions not included in appendix'
        assert r'\input{figures/cell_policy_paths.tex}' in section, 'Cell paths not included in appendix'
        assert r'\input{figures/cell_story_visual.tex}' in main, 'Cell story not included in main'
        assert r'\input{figures/policy_lifetimes.tex}' in main+appendix, 'Policy figure not included'
        assert 'Component/controller alphabets are exactly their displayed labels; unlisted edges are absent.' in source
        assert 'Unlisted non-error monitor edges self-loop' in source
        assert r'\mathsf{err}$ absorbs every label' in source
        assert 'Each comma-separated label denotes an edge.' in source
    else:
        section = read_text(paper/'supplement.tex').split(r'\label{supp:cell-finite}',1)[1].split(r'\subsection',1)[0]
        assert 'unlisted non-error monitor transitions self-loop' in section
        assert r'\mathsf{err}$ absorbs every label' in section
        assert 'Unlisted component or controller transitions are absent' in section
        assert 'alphabets contain exactly their displayed outgoing labels' in section
    for name in ('One','Old','Ins'):
        graphs[name].add(('E','Sigma','E'))
    transfer = re.search(r'g_A=g_B=\\\{\(([he]),([he])\)\\\}', section)
    assert transfer, 'Unparsed cell transfer relation'
    if current:
        assert re.findall(r'g_A=g_B=\\\{\(([he]),([he])\)\\\}', main) == [transfer.groups()], 'Main/appendix transfers differ'
    drawn=[('Ao',transfer[1],'g_A','An',transfer[2]),('Bo',transfer[1],'g_B','Bn',transfer[2])]
    endpoints={name.replace('_',''):tuple(atom(values).split(','))
               for name,values in re.findall(r'([xyz]_[AB])=\(([^()]*)\)',section)}
    assert set(endpoints)=={'xA','xB','zA','yB','zB'}, ('endpoint tuples',endpoints)
    assert len(set(endpoints.values()))==5
    for version, prefix, label, monitor in [('o','x','OldCL','Old'),('n','zy','NewCL','Ins')]:
        expected={name:values for name,values in endpoints.items() if name[0] in prefix}
        inverse={values:name for name,values in expected.items()}
        components=('A'+version,'B'+version,'C'+version)
        initial=tuple(initials[n] for n in components)+(initials[monitor],)
        assert initial in inverse, ('endpoint initial absent',version,initial)
        assert inverse[initial]==('xA' if version=='o' else 'zA')
        pending=[initial]; reached={initial}; edges=set()
        while pending:
            q=pending.pop()
            for action in ('m_A','m_B','j'):
                target=[]
                for name,value in zip(components,q):
                    alphabet={a for _,a,_ in graphs[name]}
                    outcomes={b for a,e,b in graphs[name] if (a,e)==(value,action)} if action in alphabet else {value}
                    if not outcomes: break
                    assert len(outcomes)==1
                    target.append(next(iter(outcomes)))
                if len(target)!=3: continue
                outcomes={b for a,e,b in graphs[monitor] if (a,e)==(q[3],action)}
                assert len(outcomes)<=1
                m=next(iter(outcomes),q[3])
                if m=='E': continue
                target=tuple(target)+(m,)
                assert target in inverse, ('missing reachable endpoint',version,target)
                edges.add((inverse[q],action,inverse[target]))
                if target not in reached: reached.add(target); pending.append(target)
        assert reached==set(inverse), ('extra unreachable endpoint',version,set(inverse)-reached)
        graphs[label]=edges
    load=re.search(r'loadable targets are \$\\\{([^{}]+)\\\}' if current else r'Z_\{\\rm load\}=\\\{([^{}]+)\\\}',section)
    assert load and set(load[1].split(','))=={'z_A','z_B'}, 'Cell load targets'
    assert {((endpoints[n][0],endpoints[n][1]),(endpoints[n][3],)) for n in ('zA','zB')}==set(w.cell().load)
    assert 'Initial tuples are $x_A,z_A$' in section
    initializer=re.search(r'installing \$([cd])\$ when \$B\$ holds and \$([cd])\$ otherwise' if current else r'installing \$([cd])\$ if \$B\$ holds, \$([cd])\$ otherwise',section)
    assert initializer and initializer.groups()==('d','c'), 'Cell initializer values'
    assert ('all eight version-tagged one-workpiece tuples' if current else 'all eight version-tagged one-product tuples') in section
    if current:
        assert 'The interval initializer records the holder at either all-old one-workpiece tuple.' in section
        paths=current_paths(read_text(paper/'figures/cell_policy_paths.tex'))
    else:
        paths={'A':[],'B':[]}
    for line in ([] if current else read_text(paper/'figures/cell_paths.tex').splitlines()):
        fields=[x.strip() for x in line.split(r'\\',1)[0].split('&')]
        if len(fields)!=6 or '$(' not in fields[1]: continue
        for holder,offset in [('A',0),('B',3)]:
            action,state,rank=fields[offset:offset+3]
            if not state: continue
            match=re.fullmatch(r'\$\(([on]{2});([AB]);([kcd{}-]+)\)\$',state)
            assert match, ('unparsed policy state',holder,state)
            paths[holder].append((event(action),match[1]+match[2]+';'+match[3].replace('{-}','-'),int(rank)))
    for holder, rows in paths.items():
        assert rows and rows[0][0]=='entry', ('entry row',holder)
        graphs['P'+holder]={(str(i),row[0],str(i+1)) for i,row in enumerate(rows[1:])}
    return graphs, drawn, paths, initials


def check(paper=SUB/'paper', fsp=FSP):
    paper=Path(paper); fsp=Path(fsp)
    current=current_layout(paper)
    modern=(paper/'figures/cell_components.tex').is_file() and (paper/'figures/cell_paths.tex').is_file()
    supplement=read_text(paper/'supplement.tex') if (paper/'supplement.tex').is_file() else ''
    modern=current or (modern and r'\input{figures/cell_components.tex}' in supplement)
    text=read_text(paper/'figures/witness_other.tex')
    if modern:
        graphs, cell_transfers, table_paths, table_initials=table_cell(paper,current)
    else:
        graphs={};cell_transfers=[];table_paths=None
        assert (paper/'figures/witness_cell.tex').is_file(), 'Unsupported Cell layout: no included current table'
        legacy=read_text(paper/'figures/witness_cell.tex')
        assert r'\FGedge{Ao}' in legacy, 'Unsupported Cell layout: no included current table or complete legacy drawing'
        text+='\n'+legacy
    edge_re=r'\\FGedge\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}\{[^}]*\}'
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
        expected=[f'{i}/'+''.join(q.versions)+q.monitors[0]+';'+''.join(q.monitors[1:]) for i,q in enumerate(path)]
        if table_paths is None:
            match=re.search(r'\\foreach \\n/\\txt in \{([^}]+)\}\s*\\node\[ps\] \('+graph+r'-',text)
            assert match,graph
            labels=match[1].split(',')
            ranks=list(range(len(actions),-1,-1))
            assert re.search(r'Policy \$p_'+holder+r'\$ \(remaining rank \$'+str(len(actions))+r',\\ldots,0\$',text)
        else:
            labels=[str(i)+'/'+row[1] for i,row in enumerate(table_paths[holder])]
            ranks=[row[2] for row in table_paths[holder]]
        assert labels==expected,(graph,labels,expected)
        assert ranks==list(range(len(actions),-1,-1)), ('policy rank',holder,ranks)
        w.check_policy(wc,{q:a for q,a in zip(path,actions)},dict(zip(path,ranks)),[path[0]])
        seen.update(path);edge_count+=len(actions)
    assert len(seen)==13 and edge_count==11
    if modern:
        for name,comp,version in [('Ao',0,'o'),('An',0,'n'),('Bo',1,'o'),('Bn',1,'n')]:
            assert table_initials[name]==wc.components[comp][version].initial, ('component initial',name)
        assert {name:table_initials[name] for name in ('Co','Cn','One','Old','Ins')}==dict(Co='co',Cn='c',One='A',Old='k',Ins='c')
        if current:
            current_visuals(paper)
        else:
            overview=read_text(paper/'figures/update_overview.tex')
            heads=re.search(r'\\foreach \\dy/\\holder/\\target/\\rank in \{([^}]+)\}',overview)
            assert heads and heads[1]=='0/A/B/6,-1.9/B/A/5', 'Overview entry/target/rank'
            blocks=re.findall(r'\\foreach \\x/\\label/\\rk in \{(.*?)\}\s*\{',overview,re.S)
            assert len(blocks)==2, 'Overview paths'
            action_names={'replace $A$':'rho_A','replace $B$':'rho_B','move to $A$':'m_A','move to $B$':'m_B','start new':'s','stop old':'t','inspect':'j'}
            for holder,body in zip(('A','B'),blocks):
                items=re.findall(r'([0-9.]+)/\{([^{}]+)\}/([0-9]+)',body)
                assert re.sub(r'[0-9.]+/\{[^{}]+\}/[0-9]+','',body).replace(',','').strip()=='', 'Unparsed overview step'
                observed=[(action_names[label],int(rank)) for _,label,rank in items]
                assert observed==[(row[0],row[2]) for row in table_paths[holder][1:]], ('Overview action/rank',holder,observed)
            assert '$B$ holds the workpiece: inspection pending' in overview and '$B$ empty: no inspection needed' in overview
        print('PASS cell tables/overview: components, controllers, monitor totalization, endpoint products, both Post paths and every rank agree.')
    # Parse only the explicit, single-event finite state equations used by these fixtures.
    def fsp_edges(filename):
        content=re.sub(r'//[^\n]*','',(fsp/filename).read_text())
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
    drawn=list(cell_transfers)
    for options,source,label,target in re.findall(transfer_re,text):
        assert '->' in options,('transfer must be directed',source,target)
        old,src=source.rsplit('-',1);new,dst=target.rsplit('-',1)
        drawn.append((old,src,label,new,dst))
    assert len(drawn)-len(cell_transfers)==len(re.findall(r'\\draw\[[^\]]*\bdashed\b[^\]]*\]',text)), 'Unparsed dashed transfer'
    assert len(set(drawn))==len(drawn), 'Duplicate drawn transfer'

    # This bounded parser accepts only the finite relation syntax present in the
    # three fixed RQ2 fixtures. It validates every entry instead of skipping text.
    def fixture_relations(filename):
        content=re.sub(r'//[^\n]*','',(fsp/filename).read_text())
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

    req=(fsp/'requirement_boundary_separation.lts').read_text()
    for definition in ('assert OLD_SAFETY = !align','assert NEW_SAFETY = !align','startNewSpec_P_NEW_SAFETY -> Aligned'):assert definition in req
    print('PASS: all drawn W_cell/W_b/W_r primitive edges, total monitor transitions, endpoints and 13-state/11-edge policy.')
    print(f'RQ2 edge correspondence: cell plant projection {n}, branch {b}, requirement plant {r}; requirement rejection formulas/start guard confirmed.')
    print('PASS transfers: '+', '.join(label+'='+str(count) for label,count in transfer_counts)+'; all 5 displayed pairs equal the finite checker and the RQ2 relations under the explicit state/event renaming.')
    print('PASS RQ2 mapRelation: all 5 updating-controller declarations select the expected 4 relation definitions; no extra/duplicate transfer pairs.')
    print('Scope: cell equality is only the move-labelled plant projection and empty-state transfers. The executable cell has no inspection or lifecycle monitors; paper adds j and r_one/r_old/r_inspect. Requirement plant and transfer correspond, but the fixture uses safety formulas plus a start-after-align guard rather than the paper monitor error-state/Start encoding. Branch plant and transfer correspond under state/event renaming. No full-game isomorphism claimed.')


def negative_checks(paper, fsp=FSP):
    """Corrupt independent displayed facts in throwaway copies and require rejection."""
    current=current_layout(paper)
    mutations=[
        ('figures/cell_components.tex',r'$h\xrightarrow{m_B}e$',r'$h\xrightarrow{m_B}h$','component edge'),
        ('figures/cell_components.tex',r'$d\xrightarrow{m_A}\mathsf{err}$',r'$d\xrightarrow{m_A}c$','monitor error edge'),
        ('figures/cell_paths.tex','& 6 & entry','& 7 & entry','policy rank'),
        ('supplement.tex',r'g_A=g_B=\{(e,e)\}',r'g_A=g_B=\{(h,e)\}','transfer'),
        ('figures/update_overview.tex','replace $B$','replace $A$','overview action'),
        ('supplement.tex',r'z_B=(e,h,c_0,c)',r'z_B=(e,h,c_1,c)','endpoint controller'),
    ]
    if current:
        mutations=[
            ('figures/cell_finite_main.tex',r'$h\xrightarrow{m_B}e$',r'$h\xrightarrow{m_B}h$','component edge'),
            ('figures/cell_finite_main.tex',r'$h,e$ ($h$)',r'$h,e$ ($e$)','component initial'),
            ('figures/cell_finite_main.tex',r'$c_0\xrightarrow{m_B}c_1$',r'$c_0\xrightarrow{m_B}c_0$','controller edge'),
            ('figures/cell_finite_main.tex',r'$d\xrightarrow{m_A}\mathsf{err}$',r'$d\xrightarrow{m_A}c$','monitor error edge'),
            ('figures/cell_finite_main.tex','Unlisted non-error monitor edges self-loop','Unlisted non-error monitor edges are absent','monitor totalization'),
            ('figures/cell_finite_main.tex',r'$B^n$ &',r'$B^x$ &','unknown displayed object'),
            ('figures/cell_policy_paths.tex',r'$(oo;A;k{-})$\\rank 6',r'$(oo;A;k{-})$\\rank 7','Cell rank'),
            ('figures/cell_policy_paths.tex',r'$(on;B;kd)$',r'$(on;B;kc)$','Cell monitor state'),
            ('figures/cell_policy_paths.tex',r'{$\rho_B$}(a1)',r'{$\rho_A$}(a1)','Cell path action'),
            ('technical_fragments/cell.tex',r'g_A=g_B=\{(e,e)\}',r'g_A=g_B=\{(h,e)\}','transfer'),
            ('technical_fragments/cell.tex',r'z_B=(e,h,c_0,c)',r'z_B=(e,h,c_1,c)','endpoint controller'),
            ('technical_fragments/cell.tex',r'\{z_A,z_B\}',r'\{z_A,y_B\}','load targets'),
            ('technical_fragments/cell.tex',r'installing $d$ when $B$ holds',r'installing $c$ when $B$ holds','NEW initializer'),
            ('technical_fragments/cell.tex','records the holder at either all-old one-workpiece tuple','always records A at either all-old one-workpiece tuple','UPD initializer'),
            ('main.tex',r'\input{figures/cell_finite_main.tex}',r'\input{figures/cell_components.tex}','included main table'),
            ('technical_appendix.tex',r'\input{technical_fragments/cell.tex}',r'\input{technical_fragments/omitted_cell.tex}','included appendix definitions'),
            ('figures/cell_story_visual.tex',r'replace\\empty $B$',r'replace\\empty $A$','Cell story action'),
            ('figures/policy_lifetimes.tex',r'6/5/{service}',r'6/5/{start\\new audit}','Policy action'),
            ('figures/policy_lifetimes.tex','(0,-1.14) rectangle (4.25,-.86)','(0,-1.14) rectangle (2.55,-.86)','Policy active band'),
        ]
    check(paper,fsp)
    for filename,old,new,label in mutations:
        with tempfile.TemporaryDirectory(prefix='cell-diagram-negative-') as temporary:
            target=Path(temporary)/'paper';(target/'figures').mkdir(parents=True)
            files = CURRENT_PAPER_FILES if current else (
                'figures/cell_components.tex','figures/cell_paths.tex',
                'figures/update_overview.tex','figures/witness_other.tex','supplement.tex')
            for name in files:
                (target/name).parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(paper/name,target/name)
            path=target/filename; content=path.read_text()
            assert old in content, ('negative mutation target absent',label)
            path.write_text(content.replace(old,new,1))
            try:
                with contextlib.redirect_stdout(io.StringIO()): check(target,fsp)
            except (AssertionError,KeyError,ValueError):
                print('PASS negative check:',label)
            else: raise AssertionError(('accepted corrupted paper',label))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--paper-dir',type=Path,default=SUB/'paper')
    parser.add_argument('--fsp-dir',type=Path,default=FSP)
    parser.add_argument('--self-test',action='store_true',help='also reject corrupt displayed edges, states, initializers, targets, ranks and bindings')
    args=parser.parse_args()
    if args.self_test: negative_checks(args.paper_dir,args.fsp_dir)
    else: check(args.paper_dir,args.fsp_dir)


if __name__=='__main__': main()
