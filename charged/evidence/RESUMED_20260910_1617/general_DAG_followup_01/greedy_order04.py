"""Compare one fixed minimum-ready order to the already frozen full oracle."""
from pathlib import Path
from collections import Counter
import datetime, hashlib, importlib.util, json, time
D=Path(__file__).resolve().parent
OLD=D.parent/'joint_work_general_r_01/unknown02.py'
spec=importlib.util.spec_from_file_location('universal',OLD)
U=importlib.util.module_from_spec(spec);spec.loader.exec_module(U)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def enc(x):return json.dumps(x,sort_keys=True,separators=(',',':'))

class FixedOrder(U.Universal):
    def _solve(self,S,a,d,ell):
        U.bounded();self.visits+=1
        if ell>U.top(self.w,d-self.r):return ()
        if not S:return (((0,)*(self.H+1),('done',)),)
        front={}
        def offer(c,t):
            if any(all(x<=y for x,y in zip(old,c)) for old in front):return
            for old in [old for old in front if all(x<=y for x,y in zip(c,old))]:del front[old]
            front[c]=t
        ready=[i for i in range(len(self.w)) if S>>i&1 and not self.pred[i]&S]
        i=min(ready,key=lambda j:(self.w[j],j));v=self.w[i];R=S^(1<<i)
        for c,t in self.solve(R,a,d,ell+v):offer(c,('fresh',i,t))
        matched=self.solve(R,a,d,ell)
        for mode,other in [('cached',self.solve(R,a,d+1,ell+v)),('cheap',self.solve(S,a-1,d+1,ell) if a else ())]:
            for c0,t0 in matched:
                for c1,t1 in other:
                    c=(c0[0],)+tuple(max(c0[k],v+c1[k-1]) for k in range(1,self.H+1))
                    offer(c,(mode,i,t0,t1))
        return tuple(sorted(front.items()))

def freeze():
    protocol='''# Prospective fixed minimum-ready order comparison04

Hypothesis: selecting the ready job of least work, ties by job index, at every state might attain the least all-budget W curve on arbitrary DAGs when fresh/cheap/cached modes may still adapt. This is unproved; a fixed-order all-cached suffix is already known to be suboptimal on the preserved four-job case. The candidate leaves all mode choices and comparison branches in the residual DP.

Reuse exact INPUTS03 and successful ROWS03 as the already observed full-oracle reference. Do not label the reference a new prospective experiment. Compare every15822 fixed input in original order, with300s campaign and5s input limits; preserve all statuses. Interpret every candidate tree independently via the frozen operation interpreter, checking readiness, call cap, exact protected curve and computed total-work curve. Require the full-oracle least vector to dominate every restricted vector; any violation is a semantic failure. A root missing that least vector is a candidate greedy-order counterexample. Save the full trees and stop after the first such counterexample or semantic failure; keep every remaining input as NOT_EXECUTED. All candidate upper/lower/theorem claims still require a mathematical proof; no time/SE-importance conclusion follows from these counts. No edits to earlier inputs, raw, oracle or scientific claims; root sole writer.
'''
    with (D/'PROTOCOL04.md').open('x') as f:f.write(protocol)
    receipt=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),planned=15822,hashes={n:sha(D/n) for n in ['INPUTS03.json','ROWS03.jsonl','SUMMARY03.json','PROTOCOL04.md','greedy_order04.py']},oracle_sha256=sha(OLD))
    with (D/'INPUT_BINDING04.json').open('x') as f:f.write(json.dumps(receipt,indent=2)+'\n')
    print('fixed-order comparison frozen')

def run():
    receipt=json.loads((D/'INPUT_BINDING04.json').read_text())
    for n,h in receipt['hashes'].items():assert sha(D/n)==h,n
    assert sha(OLD)==receipt['oracle_sha256']
    inputs=json.loads((D/'INPUTS03.json').read_text());refs=[json.loads(x) for x in (D/'ROWS03.jsonl').read_text().splitlines()]
    assert len(inputs)==len(refs)==15822
    start=time.monotonic();deadline=start+300;stats=Counter();stop=None;witness=[];states=paths=0
    with (D/'START04.json').open('x') as f:f.write(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),binding_sha256=sha(D/'INPUT_BINDING04.json')),indent=2)+'\n')
    with (D/'ROWS04.jsonl').open('x') as out:
        for idx,(inp,ref) in enumerate(zip(inputs,refs)):
            assert ref['input']==inp and ref['status']=='SUCCESS' and ref['root_frontier_width']==1
            row=dict(index=idx,input=inp,reference_curve=ref['frontier'][0]['curve'])
            if stop is None and time.monotonic()>=deadline:stop='campaign_deadline'
            if stop is not None:row.update(status='NOT_EXECUTED',reason=stop)
            else:
                attempt=time.monotonic();U.DEADLINE=min(deadline,attempt+5);game=None
                try:
                    w=inp['w'];r=inp['r'];pred=[0]*len(w)
                    for i,j in inp['edges']:pred[j]|=1<<i
                    game=FixedOrder(w,pred,r);front=game.solve((1<<len(w))-1,r,0,0);assert front,'empty restricted root'
                    gotrows=[]
                    for c,t in front:
                        got=U.interpret(t,w,pred,r);assert got['W']==[sum(w)+x for x in c]
                        assert got['L']==[U.top(w,B-r) for B in range(len(w)+r+1)]
                        assert all(x<=y for x,y in zip(row['reference_curve'],got['W'])),'restricted beats complete oracle'
                        gotrows.append(got);paths+=got['paths']
                    equal=any(x['W']==row['reference_curve'] for x in gotrows)
                    row.update(status='SUCCESS' if equal else 'COUNTEREXAMPLE',restricted_frontier=gotrows,states=game.visits)
                    if not equal:
                        stop='candidate_greedy_order_counterexample'
                        witness.append(dict(index=idx,input=inp,reference=row['reference_curve'],trees=[dict(extra_curve=c,tree=t) for c,t in front],interpreted=gotrows))
                except TimeoutError as ex:row.update(status='TIMEOUT',error=str(ex))
                except Exception as ex:row.update(status='FAILURE',error=repr(ex));stop='semantic_failure'
                if game:states+=game.visits
                row['seconds']=time.monotonic()-attempt
            stats[row['status']]+=1;out.write(enc(row)+'\n');out.flush()
    with (D/'WITNESSES04.json').open('x') as f:f.write(json.dumps(witness,indent=2)+'\n')
    result=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='CANDIDATE_COUNTEREXAMPLE' if stats['COUNTEREXAMPLE'] else 'EXPLORATION_COMPLETE',counts=dict(stats),stop_reason=stop,states=states,paths=paths,seconds=time.monotonic()-start,hashes={n:sha(D/n) for n in ['ROWS04.jsonl','WITNESSES04.json']},general_theorem_established=False)
    if stats['FAILURE']:result['status']='SEMANTIC_FAILURE'
    with (D/'SUMMARY04.json').open('x') as f:f.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__':
    import sys
    {'freeze':freeze,'run':run}[sys.argv[1]]()
