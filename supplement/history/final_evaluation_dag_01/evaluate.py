from pathlib import Path
import copy,hashlib,importlib.util,json,sys,time
import primitive,structure
ROOT=Path(__file__).resolve().parent
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result
hybrid=module('dag_hybrid_frozen',ROOT.parent/'dependency_hybrid_01/hybrid.py')
bellman=module('dag_bellman_frozen',ROOT.parent/'dependency_curves_01/checker.py')
packed=module('dag_packed_frozen',ROOT.parent/'dependency_hybrid_check_02/check.py')

def evaluate(case):
    start=time.perf_counter();jobs=case['cp'];edges=case['edges'];B=case['budget'];n=len(jobs)
    g=primitive.graph(jobs,edges,B)
    values,policy=primitive.reuse.solve(g)
    rank=primitive.reuse.validate(g,values,policy)
    v=primitive.scalar(jobs,edges,B)
    U,C,L,LC,D=primitive.U,primitive.C,primitive.L,primitive.LC,primitive.D
    pred=primitive.predecessors(n,edges)
    phi={};invariant_cells=0
    for state in g[0]:
        s,b=state;mask=sum(1<<i for i,x in enumerate(s) if x in (U,C,L))
        done={i for i,x in enumerate(s) if x==D}
        cached={i for i,x in enumerate(s) if x in (C,LC)}
        assert all(pred[i]<=done for i in done|cached)
        assert not any(a in cached and z in cached for a,z in edges)
        assert all(not(mask>>a&1) or mask>>z&1 for a,z in edges),'T not upset'
        assert all(not(mask>>i&1) or not pred[i]<=done or not any(mask>>a&1 for a in pred[i]) for i in range(n))
        phi[state]=sum(jobs[i][0] for i,x in enumerate(s) if x in (U,L))+v[b][mask]
        invariant_cells+=1
    defects=[]
    for aid,action in enumerate(g[1]):
        owner=g[2][aid]
        lhs=max(cost+phi[target] for target,cost in action['edges'])
        if lhs<phi[owner]:defects.append(dict(kind='action_potential',state=owner,action=aid,lhs=lhs,rhs=phi[owner]))
    for state in g[0]:
        if phi[state]>values[state]:defects.append(dict(kind='state_lower_bound',state=state,phi=phi[state],value=values[state]))
    stage_primitive=time.perf_counter()-start
    before=time.perf_counter();artifact=hybrid.compile_case(dict(cp=jobs,edges=edges))
    encoded=json.dumps(artifact,sort_keys=True,separators=(',',':')).encode()
    data=json.loads(encoded)
    compile_seconds=time.perf_counter()-before;before=time.perf_counter()
    if data['route']=='ordered':certificate=packed.check(data)
    else:
        shape=structure.check(data);certificate=bellman.check(data);certificate['shape']=shape
    assert not certificate['violations'],certificate
    certificate_seconds=time.perf_counter()-before
    compiled=hybrid.load(copy.deepcopy(data));base=sum(w for w,p in jobs)
    roots=[]
    for b in range(B+1):
        actual=values[((U,)*n,b)];expected=base+v[b][-1];serialized=base+hybrid.value(compiled,b)
        roots.append(dict(b=b,primitive=actual,scalar=expected,serialized=serialized))
        if actual!=expected or serialized!=expected:defects.append(dict(kind='root',**roots[-1]))
    if data['route']=='ordered':
        policy_states=[(k,sum(1<<i for i in data['order'][k:])) for k in range(n)]
    else:policy_states=[(int(mask),int(mask)) for mask in data['actions']]
    policy_cells=0
    for controller_state,mask in policy_states:
        for b in range(B+1):
            j,mode=hybrid.choose(compiled,controller_state,b)
            assert mask>>j&1 and not any(mask>>a&1 for a in pred[j])
            child=mask^(1<<j)
            q=jobs[j][1]+v[b][child] if mode=='protected' else (v[b][child] if not b else max(v[b][child],jobs[j][0]+v[b-1][mask]))
            if q!=v[b][mask]:defects.append(dict(kind='serialized_policy',mask=mask,b=b,job=j,mode=mode,value=q,optimal=v[b][mask]))
            policy_cells+=1
    row=dict(status='FAILURE' if defects else 'SUCCESS',input_id=case['id'],roots=roots,defects=defects,
             states=len(g[0]),actions=len(g[1]),outcomes=sum(len(a['edges']) for a in g[1]),
             invariant_cells=invariant_cells,policy_cells=policy_cells,rank_rounds=rank,
             route=data['route'],certificate=certificate,artifact_bytes=len(encoded),
             artifact_sha256=hashlib.sha256(encoded).hexdigest(),primitive_seconds=stage_primitive,
             compile_serialize_seconds=compile_seconds,load_certificate_seconds=certificate_seconds,
             elapsed_seconds=time.perf_counter()-start)
    return row,encoded
