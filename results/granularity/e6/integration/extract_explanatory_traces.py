#!/usr/bin/env python3
"""Read checked certificates and export compact explanatory traces, no re-solving JVM."""
import importlib.util, json, hashlib
from pathlib import Path
from collections import defaultdict,deque

E6=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('audit',E6/'independent/check_games_v3.py')
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
OUT=E6/'integration/explanatory_traces';OUT.mkdir(exist_ok=True)
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(family,job):
    base=E6/family;raw=base/'raw/series'/job;inv=read(raw/'invocation.json');jobdef=inv['job']
    inp=base/jobdef['input'];result=read(raw/'result.json');proof=read(raw/'certificate.json')
    assert sha(inp)==result['input_sha256'] and sha(raw/'certificate.json')==result['certificate_sha256']
    model=audit.Model(read(inp),jobdef['merge']);seen,graph=model.enumerate();ranks,_=model.solve(seen,graph)
    model.certificate(proof,seen,ranks)
    return model,proof,dict(input=str(inp.relative_to(E6)),input_sha256=sha(inp),certificate=str((raw/'certificate.json').relative_to(E6)),certificate_sha256=sha(raw/'certificate.json'),job=job,decision=result['decision'],states_discovered=result['states_discovered'])
def win_trace(family,job):
    model,proof,provenance=load(family,job);states={x['id']:x for x in proof['states']};edges=defaultdict(list)
    for u,a,v in proof['strategy_edges']:edges[u].append((a,v))
    root=max((x for x in proof['states'] if x['initial']),key=lambda x:(x['rank'],x['id']))
    curr=root['id'];trace=[]
    while not states[curr]['goal']:
        action,target=max(edges[curr],key=lambda pair:(states[pair[1]]['rank'],pair[0],pair[1]))
        trace.append(dict(source=states[curr],action=action,target=states[target],control='UC' if action in model.ordinary-model.control else 'C'))
        curr=target
    assert len(trace)<=root['rank']
    return dict(status='PASS',provenance=provenance,root_rank=root['rank'],steps=len(trace),trace=trace,scope='One maximal-rank successor trace of the full checked policy; all other adversarial branches remain in the original certificate.')
def canary_loss():
    model,proof,provenance=load('canary/v1','n02_m01_merged_lazy')
    bystate={audit.from_json(x):x for x in proof['states']};roots=[s for s in bystate if s in model.roots]
    queue=deque((s,[]) for s in roots);seen=set(roots);found=None
    while queue:
        s,path=queue.popleft()
        if not model.safe(s):found=path;break
        for action,targets in sorted(model.post(s).items()):
            for target in sorted(targets.intersection(bystate),key=repr):
                if target in seen:continue
                seen.add(target);queue.append((target,path+[dict(source=bystate[s],action=action,target=bystate[target],control='UC' if action in model.ordinary-model.control else 'C')]))
    assert found and len(found)==3
    root=roots[0];transfer='ablation.merge.transfers';outcomes=model.post(root)[transfer]
    assert len(outcomes)==4 and any(all(q=='BP' for v,q in s[0]) for s in outcomes)
    return dict(status='PASS',provenance=provenance,steps=len(found),transfer_outcomes=[dict(physical=s[0],testers=dict(s[1])) for s in sorted(outcomes,key=repr)],trace=found,scope='A path retained in the checked losing certificate. The full certificate closure, not this path alone, proves loss against all controller choices.')
def policy_boundary_buckets():
    model,proof,provenance=load('policy/v2','policy_fine_boundaries_lazy');observed=[]
    for root in sorted(model.roots,key=repr):
        for action in ('ablation.merge.starts','ablation.merge.stops'):
            targets=model.post(root)[action]
            assert targets and all(not model.safe(t) for t in targets)
            observed.append(dict(root_physical=root[0],root_testers=dict(root[1]),action=action,outcomes=[dict(physical=t[0],testers=dict(t[1]),safe=model.safe(t)) for t in targets]))
    return dict(status='PASS',provenance=provenance,buckets=observed,scope='Both initial audit-history roots have unsafe global starts and unsafe global stops. Ordinary events and identity transfer cannot change the interval activation bits; the complete losing certificate also checks their closure.')

reports={'canary_fine_worst_path.json':win_trace('canary/v1','n02_m01_fine_lazy'),
         'canary_merged_bad_path.json':canary_loss(),
         'policy_fine_worst_path.json':win_trace('policy/v2','policy_fine_none_lazy'),
         'policy_global_boundary_buckets.json':policy_boundary_buckets()}
for name,data in reports.items():
    data['extractor_sha256']=sha(Path(__file__));data['checker_sha256']=sha(E6/'independent/check_games_v3.py')
    with (OUT/name).open('x') as f:json.dump(data,f,indent=2);f.write('\n')
print(json.dumps({name:dict(status=d['status'],steps=d.get('steps')) for name,d in reports.items()}))
