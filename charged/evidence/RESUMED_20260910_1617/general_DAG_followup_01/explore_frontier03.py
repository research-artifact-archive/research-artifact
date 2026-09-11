"""Prospective larger-DAG search, preserving all inputs and every disposition."""
from pathlib import Path
from itertools import product
from collections import Counter
import datetime, hashlib, importlib.util, json, random, time

D=Path(__file__).resolve().parent
OLD=D.parent/'joint_work_general_r_01/unknown02.py'
spec=importlib.util.spec_from_file_location('frozen_universal_oracle',OLD)
U=importlib.util.module_from_spec(spec);spec.loader.exec_module(U)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def enc(x):return json.dumps(x,sort_keys=True,separators=(',',':'))
def population():
    rows=[dict(kind='known_four_job_regression',w=[3,1,1,2],edges=[[0,1],[1,2]],r=3)]
    rng=random.Random(202609110729)
    seen=set()
    for n in range(5,9):
        count=0
        while count<128:
            w=[rng.choice([1,2,3,5,8,13]) for _ in range(n)]
            edges=[[i,j] for i in range(n) for j in range(i+1,n) if rng.randrange(100)<35]
            r=rng.choice([1,2,3,4])
            inp=dict(kind='fixed_seed_larger_DAG',w=w,edges=edges,r=r)
            signature=enc(inp)
            if not edges or signature in seen:continue
            seen.add(signature);rows.append(inp);count+=1
    possible=[(i,j) for i in range(4) for j in range(i+1,4)]
    for mask in range(1,64):
        edges=[list(e) for k,e in enumerate(possible) if mask>>k&1]
        for w in product([1,2,5],repeat=4):
            for r in [1,2,3]:rows.append(dict(kind='complete_labeled_n4_nonempty_DAG',w=list(w),edges=edges,r=r))
    assert len(rows)==15822
    return rows

def freeze():
    path=D/'INPUTS03.json'
    with path.open('x') as f:f.write(json.dumps(population(),indent=2)+'\n')
    protocol='''# Prospective DAG least-curve exploration03

SCIENTIFIC exploration, root sole writer. This is an attempt to falsify the unproved existence of one least total-work curve for general DAGs under simultaneous all-budget optimal protected work and universal Q<=n+r. It does not change existing theorem or final-evaluation outcomes.

Before execution fix INPUTS03.json: one previously hand-derived four-job regression, 128 distinct fixed-seed cases for each n5--8 (weights1,2,3,5,8,13; retry1--4; forward edges), then every nonempty forward-edge mask on four vertices, weights1,2,5 and retries1--3. These are authored exploration inputs, not a representative empirical population. Exclude no observed unfavorable result. The known regression is not a new discovery.

Use the unchanged unknown02.py Universal oracle. Its state tracks unfinished set, remaining retries, observed useful-bad count and spent protected work. Return complete nondominated vectors of duplicate work over remaining budgets, under the global protection curve. Independently interpret each retained policy tree for readiness, Q, W and L over every useful-gate outcome path; require total W=mandatory work+oracle curve and exact L=globalTop_(B-r). Full-program transfer relies on the separate concrete-history theorem, not this finite code.

Use a300s campaign deadline and a5s per-input deadline. Preserve every selected input with SUCCESS, TIMEOUT, FAILURE or NOT_EXECUTED. Stop after a verified root frontier has more than one incomparable W curve, after any semantic failure, or at the campaign deadline; retain all remaining inputs as NOT_EXECUTED with cause. Save complete witness trees and interpreted vectors for the known case and any width>1 candidate. A width>1 result is a candidate counterexample requiring separate mathematical reconstruction; a width1 population proves no general theorem. No native timing, paidAPI, credit or human/proxy study. Prior inputs/raw remain unchanged.
'''
    with (D/'PROTOCOL03.md').open('x') as f:f.write(protocol)
    print('frozen',len(population()),'inputs')

def run():
    inputs=json.loads((D/'INPUTS03.json').read_text())
    assert inputs==population()
    start=time.monotonic();deadline=start+300
    receipt=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),planned=len(inputs),campaign_cap_seconds=300,per_input_cap_seconds=5,hashes={n:sha(D/n) for n in ['INPUTS03.json','PROTOCOL03.md','explore_frontier03.py']},frozen_oracle_sha256=sha(OLD))
    with (D/'START03.json').open('x') as f:f.write(json.dumps(receipt,indent=2)+'\n')
    stats=Counter();widths=Counter();witnesses=[];stop=None;totalstates=0;totalpaths=0
    with (D/'ROWS03.jsonl').open('x') as out:
        for idx,inp in enumerate(inputs):
            row=dict(index=idx,input=inp)
            if stop is None and time.monotonic()>=deadline:stop='campaign_deadline'
            if stop is not None:row.update(status='NOT_EXECUTED',reason=stop)
            else:
                attempt=time.monotonic();U.DEADLINE=min(deadline,attempt+5)
                game=None
                try:
                    w=inp['w'];r=inp['r'];pred=[0]*len(w)
                    for i,j in inp['edges']:pred[j]|=1<<i
                    game=U.Universal(w,pred,r);front=game.solve((1<<len(w))-1,r,0,0)
                    assert front,'empty root frontier'
                    checks=[]
                    for curve,tree in front:
                        got=U.interpret(tree,w,pred,r)
                        assert got['W']==[sum(w)+x for x in curve],('curve',got,curve)
                        assert got['L']==[U.top(w,B-r) for B in range(len(w)+r+1)],('protection',got)
                        totalpaths+=got['paths']
                        checks.append(dict(curve=got['W'],protection=got['L'],paths=got['paths'],max_Q=got['maximum_Q'],tree_sha256=hashlib.sha256(enc(tree).encode()).hexdigest()))
                    if inp['kind']=='known_four_job_regression':assert [x['curve'] for x in checks]==[[7,10,13,16,19,20,20,20]],checks
                    row.update(status='SUCCESS',root_frontier_width=len(front),frontier=checks,states=game.visits)
                    widths[len(front)]+=1
                    if idx==0 or len(front)>1:witnesses.append(dict(index=idx,input=inp,trees=[dict(extra_curve=c,tree=t) for c,t in front],checks=checks))
                    if len(front)>1:stop='verified_incomparable_root_curves_require_analytic_reconstruction'
                except TimeoutError as ex:row.update(status='TIMEOUT',error=str(ex))
                except Exception as ex:row.update(status='FAILURE',error=repr(ex));stop='semantic_failure_requires_new_version'
                if game:totalstates+=game.visits
                row['seconds']=time.monotonic()-attempt
            stats[row['status']]+=1;out.write(enc(row)+'\n');out.flush()
    with (D/'WITNESSES03.json').open('x') as f:f.write(json.dumps(witnesses,indent=2)+'\n')
    result=dict(receipt,ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='CANDIDATE_COUNTEREXAMPLE' if any(k>1 for k in widths) else 'EXPLORATION_COMPLETE',counts=dict(stats),frontier_widths=dict(widths),stop_reason=stop,visited_states=totalstates,interpreted_paths=totalpaths,seconds=time.monotonic()-start,outputs={n:sha(D/n) for n in ['ROWS03.jsonl','WITNESSES03.json']},general_theorem_established=False)
    if stats['FAILURE']:result['status']='SEMANTIC_FAILURE'
    with (D/'SUMMARY03.json').open('x') as f:f.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__':
    import sys
    {'freeze':freeze,'run':run}[sys.argv[1]]()
