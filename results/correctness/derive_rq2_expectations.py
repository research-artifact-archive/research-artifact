#!/usr/bin/env python3
"""Small direct-LTS oracle for the eight finite RQ2 witnesses.

This is a deliberately limited parser and explicit finite-state derivation,
independent of MTSA and the existing raw-oracle/generator implementations.
Endpoint safety is the literal !align / !bad used in these witnesses. The
one old/one new requirement case uses explicit activation bits and Aligned.
The requirement-block restriction forbids ordinary/transfer actions after
its first requirement event until both requirement events are complete.
Unsafe controllable moves lead to one losing sink; this quotient suffices
for decision derivation, and its sizes are not MTSA structural measurements.
"""
from pathlib import Path
from collections import deque
from itertools import product
import csv,json,re
ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'Implementation/Experiment/FSE2027'
OUT=Path(__file__).resolve().parent/'rq2'
CONFIG=json.loads((OUT/'raw/config.json').read_text())
ERROR=('unsafe',)

def read_lts(path):
    text=re.sub(r'//[^\n]*','',path.read_text())
    aliases={}; graphs={}
    for m in re.finditer(r'(?m)^\s*([A-Z][A-Z_0-9]*)\s*=\s*(?:([A-Z][A-Z_0-9]*)\s*[,\.]|\(([^)]*)\)\s*[,\.])',text):
        name,alias,body=m.groups()
        if alias: aliases[name]=alias
        else:
            edges={}
            for a,t in re.findall(r'([a-zA-Z_][a-zA-Z_0-9]*)\s*->\s*([A-Z][A-Z_0-9]*)',body):edges.setdefault(a,[]).append(t)
            graphs[name]=edges
    def resolve(s):
        while s in aliases:s=aliases[s]
        return s
    graphs={s:{a:tuple(resolve(t) for t in ts) for a,ts in edges.items()} for s,edges in graphs.items()}
    def component(name):
        start=resolve(name);seen={start};q=[start]
        for s in q:
            for ts in graphs[s].values():
                for t in ts:
                    if t not in seen:seen.add(t);q.append(t)
        return start,{s:graphs[s] for s in seen},set(a for s in seen for a in graphs[s])
    oldnames=re.search(r'oldEnvironment\s*=\s*\{([^}]+)\}',text).group(1).replace(' ','').split(',')
    newnames=re.search(r'newEnvironment\s*=\s*\{([^}]+)\}',text).group(1).replace(' ','').split(',')
    old=[component(n) for n in oldnames];new=[component(n) for n in newnames]
    transfers={}
    for m in re.finditer(r'([A-Z][A-Z_0-9]*)@([A-Z][A-Z_0-9]*)\s*=\s*(reconfigure_[A-Za-z_0-9]+)\s*->\s*([A-Z][A-Z_0-9]*)@([A-Z][A-Z_0-9]*)',text):
        s,on,a,t,nn=m.groups();i=oldnames.index(on);assert newnames[i]==nn;transfers.setdefault((i,resolve(s)),[]).append((a,resolve(t)))
    controllable=set(re.search(r'set ControllableActions\s*=\s*\{([^}]+)\}',text).group(1).replace(' ','').split(','))
    req='P_OLD_SAFETY' in text
    if 'R_FIXED_A' in text:
        assert re.search(r'ltl_property R_FIXED_A\s*=\s*\[\]\(!b\)',text)
        assert re.search(r'ltl_property R_FIXED_B\s*=\s*\[\]\(!a\)',text)
    if req:
        assert re.search(r'fluent Aligned\s*=\s*<align,\s*hotSwapIn>',text)
        assert re.search(r'startNewSpec_P_NEW_SAFETY\s*->\s*Aligned',text)
    forbidden=re.search(r'assert OLD_SAFETY\s*=\s*!([a-zA-Z_0-9]+)',text).group(1) if req else None
    return old,new,transfers,controllable,req,forbidden

def derive(path,method):
    old,new,transfers,controllable,req,forbidden=read_lts(path);ncomp=len(old)
    # State=(version bits, local states, old requirement active, new active, Aligned).
    def physical(v,x):
        comps=[new[i] if v[i] else old[i] for i in range(ncomp)]; result={}
        for a in set().union(*(c[2] for c in comps)):
            opts=[]
            for i,(_,g,alpha) in enumerate(comps):
                opts.append(g[x[i]].get(a,()) if a in alpha else (x[i],))
            if all(opts):result[a]=list(product(*opts))
        return result
    def endpoint(components):
        v=tuple(components is new for _ in components);initial=tuple(c[0] for c in components);seen={initial};q=[initial]
        for x in q:
            for a,targets in physical(v,x).items():
                if a==forbidden:continue
                for y in targets:
                    if y not in seen:seen.add(y);q.append(y)
        return seen
    old_roots=endpoint(old);new_targets=endpoint(new)
    roots={(tuple(False for _ in old),x,req,not req,False) for x in old_roots}
    def post(s):
        if s==ERROR:return {},set(),False
        v,x,h,z,aligned=s;ordinary=physical(v,x);uc={a for a in ordinary if a not in controllable};buckets={}
        block=(method=='requirement_block' and req and (h==z))
        for a,targets in ordinary.items():
            if block and a in controllable:continue
            bad=(req and a==forbidden and(h or z)) or (method=='fixed_script_a' and a=='b') or(method=='fixed_script_b' and a=='a')
            buckets[a]={ERROR} if bad else {(v,y,h,z,aligned or a=='align') for y in targets}
        if not uc:
            if not block:
                for i in range(ncomp):
                    if v[i]:continue
                    for a,t in transfers.get((i,x[i]),[]):
                        vv=list(v);vv[i]=True;xx=list(x);xx[i]=t;buckets.setdefault(a,set()).add((tuple(vv),tuple(xx),h,z,aligned))
            if req and h:buckets['stopOld']={(v,x,False,z,aligned)}
            if req and not z:buckets['startNew']={(v,x,h,True,aligned)} if aligned else {ERROR}
        goal=all(v) and not h and z and x in new_targets and not uc
        return buckets,uc,goal
    seen=set(roots);q=deque(roots);edges={};goal=set();uc_by={}
    while q:
        s=q.popleft();b,u,g=post(s);edges[s]=b;uc_by[s]=u
        if g:goal.add(s)
        for targets in b.values():
            for t in targets:
                if t not in seen:seen.add(t);q.append(t)
    winning=set(goal);rank={s:0 for s in goal};roundno=0
    while True:
        roundno+=1;add=set()
        for s in seen-winning:
            b=edges[s];u=uc_by[s]
            succeeds=(bool(u) and all(b[a] <= winning for a in u)) or (not u and any(ts and ts<=winning for ts in b.values()))
            if succeeds:add.add(s)
        if not add:break
        winning|=add;rank.update({s:roundno for s in add})
    return dict(expected_decision='WIN' if roots<=winning else 'LOSS',old_initial_set=repr(sorted(old_roots)),uncontrollable_actions='u enabled only at old WAIT, two outcomes' if 'u' not in controllable and any('u' in c[2] for c in old) else 'none',goal='all components new; old requirement off/new requirement on when present; new endpoint reachable local tuples '+repr(sorted(new_targets))+'; no enabled UC',enumerated_quotient_states=len(seen),enumerated_goal_states=len(goal),winning_roots=len(roots&winning),total_roots=len(roots),max_root_rank=max((rank[s] for s in roots if s in winning),default=''))

REASON={
'pc_separation_local_fg':'Exactly one workpiece invariant. Transfer the empty component, move the workpiece into it, transfer the other now-empty component. From either old root all moves and transfers are controllable; each reached all-new target has no UC.',
'pc_separation_global_product':'Global relation is literally empty. Both old product states remain closed under moveA/moveB, and no edge changes the version bit. No reachable Goal; neither timeout nor resource failure is used.',
'pc_neutral_local_fg':'Both local states belong to each transfer domain. Transfer both components in either order from both old roots; ordinary moves are unnecessary.',
'pc_neutral_global_product':'Each of the two old product states has its state-preserving reconfigure_CELL mapping. One transfer reaches its quiescent new counterpart.',
'branching_separation':'Full policy accepts both u outcomes at WAIT, observes BRANCH_A/B, chooses a/b respectively, then transfers READY_A/B. Fixed a forbids the only resolving b at BRANCH_B; fixed b symmetrically traps BRANCH_A. idle stutters cannot decrease rank. All five old states are roots.',
'branching_neutral':'After either uncontrollable u outcome, both a and b are enabled. Full, fixed-a and fixed-b each use an allowed head and transfer from READY_A/B. Roots already READY transfer immediately. No UC exists in the new component.',
'requirement_boundary_separation':'Only OLD_WAIT is old-endpoint reachable because old safety excludes align. Full policy stopOld, align, startNew, reconfigure reaches Goal (transfer/start may be exchanged after align). Requirement-block allows neither align before stop nor align inside the open requirement block; startNew before align violates R_START_AFTER_ALIGN, so the old waiting root is losing.',
'requirement_boundary_neutral':'Transfer old idle component to NEW_WAIT while old !bad monitor is active, execute align (allowed by old safety), then stopOld/startNew consecutively. This policy satisfies both full and requirement-block semantics; all actions are controllable.'}
rows=[]
for m in CONFIG['models']:
    for method in m.get('method_ids',[x['id'] for x in CONFIG['methods']]):
        d=derive(ROOT/m['path'],method);d.update(model_id=m['id'],method_id=method,source_lts=m['path'],derivation=REASON[m['id']],new_rule_effect='No expected-decision change: every handover is UC-quiescent; the sole UC u is only at old WAIT where transfer was already unavailable')
        rows.append(d)
fields=['model_id','method_id','expected_decision','old_initial_set','uncontrollable_actions','goal','derivation','new_rule_effect','enumerated_quotient_states','enumerated_goal_states','winning_roots','total_roots','max_root_rank','source_lts']
with (OUT/'expected.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
print('rows',len(rows),'WIN',sum(r['expected_decision']=='WIN' for r in rows),'LOSS',sum(r['expected_decision']=='LOSS' for r in rows))
for r in rows:print(r['model_id'],r['method_id'],r['expected_decision'],str(r['winning_roots'])+'/'+str(r['total_roots']))
