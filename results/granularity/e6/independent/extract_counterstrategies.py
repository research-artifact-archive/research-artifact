#!/usr/bin/env python3
"""Extract and independently check explicit adversarial responses from loss regions.

These are explanatory postprocessing artifacts, not returned E1 strategy objects,
new trials, or evidence selected to alter a decision.
"""
import argparse,importlib.util,json,hashlib
from pathlib import Path
from collections import defaultdict,deque
HERE=Path(__file__).resolve().parent;E6=HERE.parent
spec=importlib.util.spec_from_file_location('audit',HERE/'check_games_v3.py');audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
CASES=[('canary/v1','n02_m01_merged_lazy','canary_product'),
       ('policy/v2','policy_fine_boundaries_lazy','policy_global_boundaries'),
       ('db_rolling/v2','db_n3_m2_fine_transfers_lazy','db_joint_secondary'),
       ('db_rolling/v2','db_n3_m3_fine_none_lazy','db_no_slack'),
       ('threads/v1','threads_n02_b01_saturated_offers_fine_lazy','threads_saturated'),
       ('canary_controls/v1','n02_m01_no_recovery_fine_lazy','canary_no_recovery')]
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def extract(family,job,name,out):
    base=E6/family;raw=base/'raw/series'/job;inv=read(raw/'invocation.json');result=read(raw/'result.json');proof=read(raw/'certificate.json')
    assert result['decision']==proof['decision']=='LOSS' and result['certificate_checker']=='PASS'
    assert sha(raw/'certificate.json')==result['certificate_sha256']
    inp=base/inv['job']['input'];assert sha(inp)==result['input_sha256']
    model=audit.Model(read(inp),inv['job']['merge']);seen,graph=model.enumerate();ranks,_=model.solve(seen,graph)
    model.certificate(proof,seen,ranks)
    nodes={audit.from_json(x):x for x in proof['states']};ids={s:r['id'] for s,r in nodes.items()}
    responses=[];deadlocks=[]
    for s,record in sorted(nodes.items(),key=lambda item:item[1]['id']):
        if not model.safe(s):continue
        buckets=model.post(s);uc=[a for a,ts in buckets.items() if a not in model.control and a not in model.updates]
        if uc:
            candidates=[(a,t) for a in uc for t in buckets[a].intersection(nodes)]
            assert candidates
            action,target=min(candidates,key=lambda pair:(model.safe(pair[1]),pair[0],ids[pair[1]]))
            responses.append(dict(source=record['id'],action=action,target=ids[target],kind='environment_chooses_UC'))
        elif buckets:
            for action,targets in sorted(buckets.items()):
                options=targets.intersection(nodes);assert options
                target=min(options,key=lambda x:(model.safe(x),ids[x]))
                responses.append(dict(source=record['id'],action=action,target=ids[target],kind='response_to_controller_event'))
        else:deadlocks.append(record['id'])
    # Verify the exported response object independently of its construction loop.
    byid={r['id']:s for s,r in nodes.items()};by_source=defaultdict(list)
    for edge in responses:
        source=byid[edge['source']];target=byid[edge['target']]
        assert target in model.post(source)[edge['action']] and target in nodes
        by_source[edge['source']].append(edge)
    for ident,s in byid.items():
        assert not model.goal(s)
        if not model.safe(s):assert not by_source[ident];continue
        buckets=model.post(s);uc={a for a in buckets if a not in model.control and a not in model.updates}
        edges=by_source[ident]
        if uc:assert len(edges)==1 and edges[0]['action'] in uc and edges[0]['kind']=='environment_chooses_UC'
        else:assert {e['action'] for e in edges}==set(buckets) and len(edges)==len(buckets)
    roots=[ids[s] for s in model.roots.intersection(nodes)];assert roots
    reached=set(roots);queue=deque(roots)
    while queue:
        for edge in by_source[queue.popleft()]:
            if edge['target'] not in reached:reached.add(edge['target']);queue.append(edge['target'])
    # Backward existential reachability distinguishes forced obstruction types.
    unsafe={i for i,s in byid.items() if not model.safe(s)};can_reach_unsafe=set(unsafe)
    reverse=defaultdict(set)
    for e in responses:reverse[e['target']].add(e['source'])
    queue=deque(unsafe)
    while queue:
        for source in reverse[queue.popleft()]-can_reach_unsafe:can_reach_unsafe.add(source);queue.append(source)
    report=dict(status='PASS',family=family,job=job,decision='LOSS',input=str(inp.relative_to(E6)),input_sha256=sha(inp),
      certificate=str((raw/'certificate.json').relative_to(E6)),certificate_sha256=sha(raw/'certificate.json'),
      extractor_sha256=sha(Path(__file__)),independent_checker_sha256=sha(HERE/'check_games_v3.py'),
      rule='At a UC state choose one enabled uncontrollable event/outcome retained in the losing region. Otherwise give a retained outcome for every enabled controllable event. All retained states exclude goal.',
      selection='Prefer an unsafe successor when available, then sort action and original certificate-state ID; no input or measured policy is changed.',
      scope='An extracted adversarial response graph checked against independent Post and the original E1 loss certificate. A path alone is not used as proof. Without fairness, finite executions either reach unsafe/deadlock or continue forever outside goal.',
      certificate_states=len(nodes),initial_states_in_region=roots,states=[nodes[s] for i,s in sorted(byid.items())],responses=responses,
      safe_deadlock_states=deadlocks,response_reachable_states=sorted(reached),unsafe_states=sorted(unsafe),
      response_reachable_safe_states_without_any_unsafe_path=sorted(i for i in reached if i not in unsafe and i not in can_reach_unsafe))
    with (out/(name+'.json')).open('x') as f:json.dump(report,f,indent=2);f.write('\n')
    return dict(case=name,certificate_states=len(nodes),responses=len(responses),reachable_states=len(reached),unsafe_states=len(unsafe),safe_goal_avoidance_states=len(report['response_reachable_safe_states_without_any_unsafe_path']))
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--include-controls',action='store_true');a=ap.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    cases=CASES if a.include_controls else CASES[:-1]
    rows=[extract(*case,a.output) for case in cases]
    (a.output/'summary.json').write_text(json.dumps(dict(status='PASS',cases=rows),indent=2)+'\n')
    print(json.dumps(dict(status='PASS',cases=rows)))
if __name__=='__main__':main()
