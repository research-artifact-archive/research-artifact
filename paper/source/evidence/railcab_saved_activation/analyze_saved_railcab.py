#!/usr/bin/env python3
"""Analyze the two already saved Railcab policy graphs. No Java/solver execution.

Observer names use the experiment JAR's name-sorted compileObservers order.
The source formulas and Boolean update functions are read by the archived
restricted parser. Source and Java artifacts are never modified.
"""
from pathlib import Path
from collections import defaultdict, deque, Counter
import argparse, importlib.util, json, re, sys
sys.dont_write_bytecode = True

def need(ok,msg):
    if not ok: raise ValueError(msg)

def parse_observers(text,n):
    matches=re.findall(r'@\[([^\]]+)\]',text)
    need(len(matches)==1,'Expected exactly one attached observer vector')
    values=tuple(int(x.strip()) for x in matches[0].split(','))
    need(len(values)==n and set(values)<={0,1},'Unexpected observer vector')
    return values

def check(root,variant,H):
    checks=root/'results/supplement-checks'
    folder='railcab_policy_demo' if variant=='base' else 'railcab_r1_policy_demo'
    bundle=json.loads((checks/folder/'handoff-bundle.json').read_text())
    lookup=json.loads((checks/'frontend_lookup_demo/runs'/('railcab__'+variant)/'lookup.json').read_text())
    export=json.loads((root/'results/initialization/raw/expanded-predicates/railcab.json').read_text())
    source=H.Source(root/'tool/models/Railcab_FG.lts')
    rows={r['requirement']:r for r in export['requirements'] if r['target']==variant and r['kind']=='new'}
    reqs={r['requirement']:r for r in lookup['requirements']}
    need(len(reqs)==7 and reqs.keys()==rows.keys(),'Unexpected requirement population')
    columns={}
    for req in reqs.values():
        for col in req['observers_in_actual_column_order']:
            name=col['name']
            need(name not in columns or columns[name]==col,'Different same-named columns')
            columns[name]=col
            need(col['nonerror_states']==2 and col['initial_state']==0 and not col['initial_value'],
                 'Boolean encoding outside the saved-case convention')
    names=sorted(columns)
    need(len(names)==10,'Unexpected global observer count')
    n=len(names);index={name:i for i,name in enumerate(names)}
    source_fluents={};formulas={};source_lines={}
    for name in reqs:
        body,line=source.definition('ltl_property',name)
        need(body.startswith('[]'),'Expected pure invariant')
        formulas[name]=H.Formula(source,body[2:].strip()).ast;source_lines[name]=line
        for atom in H.atoms(formulas[name]):
            fluent=source.fluent(atom);source_fluents[H.canonical(atom)]=fluent
    # Match names of frontend action predicates to their source event atoms
    # by their initiating/terminating signatures, not an inferred suffix.
    global_fluents=[]
    for name in names:
        matches=[f for f in source_fluents.values() if H.semantic_signature(f)==H.semantic_signature(columns[name])]
        need(len(matches)==1,'Nonunique source observer match: '+name)
        global_fluents.append(matches[0])
    need(len({f['name'] for f in global_fluents})==n,'Duplicate source mapping')
    def source_values(vals):
        return {f['name']:bool(v) for f,v in zip(global_fluents,vals)}
    def advance(vals,event):
        return tuple(map(int,H.advance(tuple(map(bool,vals)),global_fluents,event)))
    def phi(name,vals):
        return H.evaluate(formulas[name],source_values(vals))
    states={x['id']:x for x in bundle['configurations']};post={x['id']:x for x in bundle['post_states']}
    need(len(states)==bundle['certificate_state_count'] and len(post)==bundle['post_state_count'],'Duplicate states')
    raw={s:parse_observers(x['physical_state'],n) for s,x in states.items()}
    post_raw={s:parse_observers(' '.join(x['local_states']),n) for s,x in post.items()}
    nexts=defaultdict(list)
    for b in bundle['strategy']:
        for o in b['outcomes']:
            need(b['source'] in states and o['target'] in states,'Unknown update state')
            nexts[b['source']].append((b['action'],o['target']))
    need(sum(map(len,nexts.values()))==bundle['strategy_outcome_edge_count'],'Wrong edge count')
    links={h['goal_configuration']:h['post_state_id'] for h in bundle['handoffs']}
    need(len(links)==bundle['goal_count'],'Handover count disagreement')
    roots=[x['root_configuration'] for x in bundle['q0_entries']]
    need(len(roots)==bundle['initial_configuration_count']==22,'Wrong entry population')
    def active_monitors(phase,node):
        d=states[node]['active_monitor_states'] if phase=='update' else post[node]['monitor_states']
        result={}
        for k,v in d.items():
            if k.startswith('new:'):
                parts=k.split(':');need(len(parts)==3 and parts[1] in reqs,'Unexpected new-monitor name')
                need(parts[1] not in result,'Duplicate new monitor')
                result[parts[1]]=v
        return result
    lookup_tables={name:{tuple(e['observer_state_indices']):e['monitor_state'] for e in r['actual_lookup_entries']} for name,r in reqs.items()}
    # Record every saved start edge, independently of the source replay.
    start_rows=[]
    for s,edges in nexts.items():
        for event,t in edges:
            if not event.startswith('startNewSpec_'):continue
            name=event.removeprefix('startNewSpec_');need(name in reqs,'Unknown start')
            need(name not in active_monitors('update',s),'Repeated start')
            installed=active_monitors('update',t)[name]
            cs=reqs[name]['observers_in_actual_column_order']
            key=tuple(raw[t][index[c['name']]] for c in cs)
            value=lookup_tables[name].get(key)
            start_rows.append(dict(source=s,event=event,target=t,requirement=name,
                columns=[c['name'] for c in cs],global_indices=[index[c['name']] for c in cs],
                saved_physical_key=list(key),table_value=value,installed_state=installed,
                table_match=(value is not None and value==installed),
                physical_vector_unchanged=raw[s]==raw[t],source_property_line=source_lines[name]))
    need(len(start_rows)==(14 if variant=='base' else 7),'Unexpected saved start edge count')
    # Replay reference observers on the complete saved policy, seeded from each
    # exported old entry; commands are consumed once in reference semantics.
    # Handover is an event-free connection to the selected fixed post graph.
    queue=deque();parent={}
    for node in roots:
        item=('update',node,raw[node]);parent[item]=None;queue.append(item)
    issues=[];state_counts=Counter();step_counts=Counter();active_checks=Counter()
    raw_differences=[];activation_checks=[];seen_start=set()
    def witness(item):
        out=[]
        while parent[item] is not None:
            item,event=parent[item];out.append(event)
        return list(reversed(out))
    def insert(new,old,event):
        if new not in parent:
            need(len(parent)<100000,'Analysis cap exceeded')
            parent[new]=(old,event);queue.append(new)
    while queue:
        item=queue.popleft();phase,node,vals=item;state_counts[phase]+=1
        stored=raw[node] if phase=='update' else post_raw[node]
        if vals!=stored:
            raw_differences.append(dict(phase=phase,state=node,reference=list(vals),stored=list(stored),
                columns=[names[i] for i in range(n) if vals[i]!=stored[i]],prefix=witness(item)))
        active=active_monitors(phase,node)
        for name,m in active.items():
            active_checks[phase]+=1
            if not phi(name,vals):
                issues.append(dict(kind='active_source_invariant_false',phase=phase,state=node,requirement=name,
                    reference=list(vals),monitor=m,prefix=witness(item)))
        if phase=='update':
            if states[node]['goal']:
                need(node in links,'Missing goal handover')
                target=links[node]
                need(target in post,'Unknown post state')
                need(raw[node]==post_raw[target],'Physical observer mismatch at handover')
                insert(('post',target,vals),item,'<handover>');step_counts['handover']+=1
                continue
            need(nexts[node],'Non-goal deadlock in saved policy')
            edges=nexts[node]
        else:
            edges=[(x['action'],t) for x in post[node]['transitions'] for t in x['outcomes']]
        for event,target in edges:
            newvals=advance(vals,event)
            step_counts[phase]+=1
            if phase=='update' and event.startswith('startNewSpec_'):
                name=event.removeprefix('startNewSpec_');seen_start.add((node,event,target))
                cs=reqs[name]['observers_in_actual_column_order']
                key=tuple(newvals[index[c['name']]] for c in cs)
                installed=active_monitors('update',target)[name]
                row=dict(source=node,event=event,target=target,requirement=name,
                    reference_post_start_key=list(key),table_value=lookup_tables[name].get(key),
                    installed_state=installed,invariant_at_start=phi(name,newvals),
                    matches_stored_key=all(newvals[index[c['name']]]==raw[target][index[c['name']]] for c in cs),
                    prefix=witness(item))
                activation_checks.append(row)
                if row['table_value']!=installed or not row['invariant_at_start']:
                    issues.append(dict(kind='reference_activation_mismatch',**row))
            insert((phase,target,newvals),item,event)
    reached_update={x[1] for x in parent if x[0]=='update'}
    need(reached_update==set(states),'Saved configurations outside complete policy closure')
    need(len(seen_start)==len(start_rows),'Unreached saved start edge')
    return dict(variant=variant,roots=len(roots),saved_policy_states=len(states),saved_outcome_edges=sum(map(len,nexts.values())),
        all_saved_start_edges=len(start_rows),start_rows=start_rows,
        source_replay=dict(states=dict(state_counts),steps=dict(step_counts),active_invariant_checks=dict(active_checks),
            reached_post_states=len({x[1] for x in parent if x[0]=='post'}),activation_checks=activation_checks,
            physical_reference_differences=raw_differences),
        issues=issues,status='PASS' if not issues and not raw_differences and all(x['table_match'] for x in start_rows) else 'MISMATCH',
        observer_order=names,source_observer_names=[x['name'] for x in global_fluents])

def main():
    p=argparse.ArgumentParser();p.add_argument('--artifact-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    need(not args.output.exists(),'Use a new output path')
    path=args.artifact_root/'results/supplement-checks/source_invariant_lookup/analyze_new_invariants.py'
    spec=importlib.util.spec_from_file_location('archived_source_invariants',path);H=importlib.util.module_from_spec(spec);spec.loader.exec_module(H)
    reports=[check(args.artifact_root,v,H) for v in ['base','r1']]
    payload=dict(analysis_kind='Finite analysis of two saved Railcab policy exports; no synthesis or performance experiment',
        ordering_basis='Experiment JAR compileObservers sorts Observer.name; confirmed by static javap disassembly including bootstrap 54 and lambda target',
        source_parser='Reuses archived restricted source-invariant parser and Boolean evaluator',
        scope='Every saved NEW start edge and every source-observer continuation in the saved update policies and their selected exported new-controller graphs',
        premise='Saved observer columns decoded in the JAR name order and seeded from the exported old entry vectors',
        not_checked=['source reconstruction of old-entry histories','runtime execution','historic lookup call arguments or fallback branch','unselected policies','other application contracts','general compiler correctness'],
        population_limits=['Both variants connect to the same exported post graph; the two traversals are not independent applications.',
            'In these saved policies no ordinary update action occurs after the first NEW start and before handover.'],
        reports=reports)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(payload,indent=2)+'\n')
    for r in reports:
        print(json.dumps({k:r[k] for k in ['variant','status','roots','saved_policy_states','all_saved_start_edges']}))
        print(json.dumps({k:r['source_replay'][k] for k in ['states','steps','active_invariant_checks','reached_post_states']}))
        print('physical_reference_differences',len(r['source_replay']['physical_reference_differences']),'issues',len(r['issues']))
        print(json.dumps(r['issues'][:3],indent=2))
    if any(r['status']!='PASS' for r in reports):
        raise SystemExit(1)
if __name__=='__main__':main()
