from pathlib import Path
from itertools import combinations_with_replacement
from collections import Counter
import importlib.util,json,hashlib,datetime,time
D=Path(__file__).resolve().parent;START=time.monotonic();DEADLINE=START+590
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def bounded():
    if time.monotonic()>DEADLINE:raise TimeoutError('590s internal cap within600s attempt')
def imported(name,file):
    spec=importlib.util.spec_from_file_location(name,D/file);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
F=imported('closed05','independent05.py');C=imported('canonical01','check01.py');C.DEADLINE=DEADLINE
def interpret(w,B,r,k,cid,out):
    maximumW=maximumL=maximumQ=-1;count=0;ww=lw=None
    def walk(i,s,f,d,Q,W,L,trace):
        nonlocal maximumW,maximumL,maximumQ,count,ww,lw
        bounded();assert d<=B and f<=r
        if i==len(w):
            assert Q<=len(w)+r;count+=1
            row=dict(case=cid,k=k,d=d,Q=Q,W=W,L=L,trace=trace)
            out.write(json.dumps(row)+'\n')
            if W>maximumW:maximumW=W;ww=row
            if L>maximumL:maximumL=L;lw=row
            maximumQ=max(maximumQ,Q);return
        v=w[i]
        if k==0 or(s==k and d<B):walk(i+1,s,f,d,Q+1,W+v,L+v,trace+[(i,'fresh','complete')]);return
        mode='cheap' if d<B and f<r else 'cached'
        # An actual immediate preparation is charged on both branches.
        preparedW=W+v
        walk(i+1,s+1,f,d,Q+1,preparedW,L,trace+[(i,mode,'match')])
        if d<B:
            if mode=='cheap':walk(i,s,f+1,d+1,Q+1,preparedW,L,trace+[(i,mode,'failure')])
            else:walk(i+1,s,f,d+1,Q+1,preparedW+v,L+v,trace+[(i,mode,'mismatch')])
    walk(0,0,0,0,0,0,0,[])
    return dict(W=maximumW,L=maximumL,Q=maximumQ,paths=count,W_witness=ww,L_witness=lw)
def main():
    assert not(D/'INDEPENDENT_ROWS06.jsonl').exists()
    inputs=[dict(w=w,r=r,B=B) for n in range(1,7) for w in combinations_with_replacement((1,2,4,7,11),n) for r in range(4) for B in range(n+r+1)]
    assert len(inputs)==13850
    (D/'INDEPENDENT_INPUTS06.json').write_text(json.dumps(inputs)+'\n')
    start=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),planned=len(inputs),cap_seconds=600,hashes={f:sha(D/f) for f in ['PROSPECTIVE_INDEPENDENT06.md','independent06.py','independent05.py','check01.py','INDEPENDENT_INPUTS06.json']})
    (D/'INDEPENDENT_ATTEMPT06_START.json').write_text(json.dumps(start,indent=2)+'\n')
    stats=Counter();failed=[];totalpaths=0;lastw=None;oracle=None
    with(D/'INDEPENDENT_ROWS06.jsonl').open('x') as out,(D/'INDEPENDENT_PATHS06.jsonl').open('x') as paths:
        for index,inp in enumerate(inputs):
            row=dict(index=index,input=inp)
            try:
                if time.monotonic()>DEADLINE:row['status']='NOT_EXECUTED'
                else:
                    w=inp['w'];B=inp['B'];r=inp['r'];n=len(w)
                    if w!=lastw:oracle=C.Canonical(w,[0]*n);lastw=w
                    candidates,front=F.formula(w,B,r)
                    reference=[[sum(w)+e,l] for e,l in oracle.solve((1<<n)-1,B,r)]
                    checks=[];actual=[]
                    for k,bound in enumerate(candidates):
                        got=interpret(w,B,r,k,index,paths);totalpaths+=got['paths']
                        assert got['W']<=bound[0] and got['L']<=bound[1],('policy_bound',k,bound,got)
                        if B>0 or k==0:assert [got['W'],got['L']]==bound,('tightness',k,bound,got)
                        checks.append(dict(k=k,bound=bound,actual=got));actual.append([got['W'],got['L']])
                    actualfront=F.nd(actual)
                    assert front==reference==actualfront,('frontier',front,reference,actualfront)
                    row.update(status='SUCCESS',formula=front,oracle=reference,interpreted=actualfront,policies=checks)
            except TimeoutError as e:row.update(status='TIMEOUT',error=str(e))
            except Exception as e:row.update(status='FAILURE',error=repr(e));failed.append(row.copy())
            stats[row['status']]+=1;out.write(json.dumps(row)+'\n')
    rigidity=[]
    for line in(D/'UNKNOWN_ROWS02.jsonl').open():
        old=json.loads(line);w=old['input']['w'];r=old['input']['r'];expected=[sum(w)+B*max(w) for B in range(r+2)]
        found=[x['curve'][:r+2] for x in old['frontier']];ok=all(v==expected for v in found)
        rigidity.append(dict(index=old['index'],input=old['input'],expected=expected,found=found,status='SUCCESS' if ok else 'FAILURE'))
    (D/'INDEPENDENT_RIGIDITY06.json').write_text(json.dumps(rigidity,indent=2)+'\n')
    (D/'INDEPENDENT_FAILURES06.json').write_text(json.dumps(failed,indent=2)+'\n')
    good=stats=={'SUCCESS':13850} and len(rigidity)==713 and all(r['status']=='SUCCESS' for r in rigidity)
    summary=dict(start,status='SUCCESS' if good else 'FAILURE',counts=dict(stats),interpreted_paths=totalpaths,rigidity_cases=len(rigidity),rigidity_success=sum(r['status']=='SUCCESS' for r in rigidity),seconds=time.monotonic()-START,result_hashes={f:sha(D/f) for f in ['INDEPENDENT_ROWS06.jsonl','INDEPENDENT_PATHS06.jsonl','INDEPENDENT_RIGIDITY06.json','INDEPENDENT_FAILURES06.json']})
    (D/'INDEPENDENT_SUMMARY06.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2));return good
if __name__=='__main__':raise SystemExit(not main())
