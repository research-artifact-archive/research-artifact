#!/usr/bin/env python3
"""Complete policy-cost frontiers, independent of the production recurrence."""
from pathlib import Path
from collections import deque
from functools import lru_cache
import itertools,json,hashlib,time,datetime,traceback
from model import compile_policy

HERE=Path(__file__).resolve().parent
START=time.monotonic()
def bound():
    if time.monotonic()-START>300: raise TimeoutError('fixed 300 second oracle bound')
def dump(p,x): p.write_text(json.dumps(x,indent=2)+'\n')
def sh(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def attain(foot):
    words={0:()};queue=deque([0])
    while queue:
        m=queue.popleft()
        for f in foot:
            z=m|f
            if z not in words: words[z]=words[m]+(f,);queue.append(z)
    return words
def pareto(vectors):
    bound();keep=[]
    for v in sorted(set(vectors),key=lambda v:(sum(v),v)):
        if not any(all(x<=y for x,y in zip(u,v)) for u in keep): keep.append(v)
    return tuple(keep)

def oracle(c):
    weights=c['weights'];q=c['q'];alpha,beta,rho=c['coefficients']
    words=attain(c['footprints']);cost={m:len(v) for m,v in words.items()}
    H=q*max(cost.values());P=sum(weights);I=beta*P+rho;S=(alpha+beta)*P+rho
    damage={m:sum(w for i,w in enumerate(weights) if m>>i&1) for m in words}
    levels=[]
    @lru_cache(None)
    def front(calls):
        child=front(calls-1) if calls>1 else ()
        merged=((-1,)*(H+1),);stats=[]
        for m in sorted(words):
            charge=cost[m];h=damage[m]
            accept=tuple(rho+(alpha+beta)*h if b>=charge else -1 for b in range(H+1))
            branches=[accept]
            for v in child:
                branches.append(tuple(rho+beta*h+v[b-charge] if b>=charge else -1 for b in range(H+1)))
            branches=pareto(branches);pairs=len(merged)*len(branches)
            merged=pareto(tuple(max(x,y) for x,y in zip(u,v)) for u in merged for v in branches)
            stats.append({'mask':m,'branch_frontier':len(branches),'cartesian_candidates':pairs,'combined_frontier':len(merged)})
        levels.append({'calls':calls,'stages':stats,'frontier_size':len(merged)})
        return merged
    prepared=tuple(tuple(I+x for x in v) for v in front(q))
    all_policies=prepared+((S,)*(H+1),)
    informed=tuple(min(v[b] for v in all_policies) for b in range(H+1))
    losses=[max(x-y for x,y in zip(v,informed)) for v in all_policies]
    compiled=compile_policy(weights,words,q,alpha,beta,rho)
    @lru_cache(None)
    def compiled_node(t,e,b):
        options=[]
        for m in sorted(words):
            if cost[m]>b:continue
            z=min(compiled['ceiling'],e+cost[m]);action=compiled['actions'][f'{t}:{e}:{m}']
            if action=='a':v=rho+(alpha+beta)*damage[m]
            else:
                assert t>0
                v=rho+beta*damage[m]+compiled_node(t-1,z,b-cost[m])
            options.append(v)
        return max(options)
    actual=tuple(S if compiled['root_action']=='direct' else I+compiled_node(q-1,0,b) for b in range(H+1))
    expected_curve=tuple(compiled['curve'][min(b,compiled['ceiling'])] for b in range(H+1))
    tests={'informed_curve':informed==expected_curve,'optimum':min(losses)==compiled['loss'],
        'mandatory_preparation':min(losses[:-1])==compiled['prepared_loss'],
        'compiled_policy':max(x-y for x,y in zip(actual,informed))==min(losses),
        'terminal_saturation':informed[-1]==S}
    formula=None
    if len(weights)==1:
        formula=min(max(alpha*P-rho,0),q*(beta*P+rho))
        tests['one_component_formula']=formula==min(losses)
    return {'id':c['id'],'status':'PASS' if all(tests.values()) else 'FAIL','tests':tests,'budget_ceiling_full':H,
        'informed':informed,'loss':min(losses),'prepared_loss':min(losses[:-1]),'direct_loss':losses[-1],
        'compiled_curve':actual,'compiler':compiled,'one_component_formula':formula,
        'prepared_frontier':prepared,'enumeration':levels}

def main():
    conditions=[]
    for weights in [(1,),(3,),(1,2),(2,5),(1,2,3)]:
        n=len(weights);single=tuple(1<<i for i in range(n));families={single,tuple(sorted(set(single+((1<<n)-1,))))}
        if n==3:families.add((1,3,6))
        for foot,q,co in itertools.product(sorted(families),range(1,{1:5,2:3,3:2}[n]+1),itertools.product([0,1,3],repeat=3)):
            conditions.append({'id':len(conditions),'weights':weights,'footprints':foot,'q':q,'coefficients':co})
    out=HERE/'oracle_run01';out.mkdir(exist_ok=False)
    dump(out/'INPUT_MANIFEST.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'conditions':conditions,
        'expected':len(conditions),'hashes':{p.name:sh(p) for p in [Path(__file__),HERE/'model.py',HERE/'ORACLE_PLAN.md']}})
    receipt={'status':'RUNNING','expected':len(conditions),'completed':0,'failed_ids':[]}
    dump(out/'START.json',receipt)
    try:
        with (out/'ROWS.jsonl').open('x') as f:
            for c in conditions:
                bound();r=oracle(c);f.write(json.dumps(r,separators=(',',':'))+'\n');f.flush()
                receipt['completed']+=1
                if r['status']!='PASS':receipt['failed_ids'].append(c['id'])
        receipt['status']='PASS' if not receipt['failed_ids'] else 'FAIL'
    except Exception as e:
        receipt.update(status='TIMEOUT' if isinstance(e,TimeoutError) else 'ERROR',exception=repr(e),traceback=traceback.format_exc())
    finally:
        receipt.update(seconds=time.monotonic()-START,unexecuted=len(conditions)-receipt['completed'])
        dump(out/'RESULT.json',receipt);print(json.dumps(receipt))
    return 0 if receipt['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
