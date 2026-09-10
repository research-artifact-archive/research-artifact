from pathlib import Path
import json,hashlib,time,datetime
from collections import Counter
D=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def nd(pairs):
    out=[];floor=float('inf')
    for W,L in sorted(set(map(tuple,pairs))):
        if L<floor:out.append([W,L]);floor=L
    return out
def formula(w,B,r):
    a=sorted(w);n=len(a);A=[0]
    for v in a:A.append(A[-1]+v)
    h=min(r,B);p=B-h;candidates=[[A[-1],A[-1]]]
    if p<n:
        for k in range(1,n-p+1):
            C=h*a[k-1]+A[k+p-1]-A[k-1];candidates.append([A[-1]+C,A[-1]-A[k]])
    return candidates,nd(candidates)
def main():
    assert not(D/'INDEPENDENT_ROWS05.jsonl').exists();start=time.monotonic();src=D/'ROWS01.jsonl'
    assert sha(src)=='5f4dd8376ee94b92fad8c6530174d747ff2e09ca67faa71d1ddfca30fc717e59'
    stats=Counter();scope=Counter();failures=[]
    with(D/'INDEPENDENT_ROWS05.jsonl').open('x') as out:
        for line in src.open():
            old=json.loads(line);independent=not old['input']['edges'];retry_covers_budget=old['r']>=old['B']
            if not independent and not retry_covers_budget:continue
            row=dict(input=old['input'],r=old['r'],B=old['B'],independent=independent,retry_covers_budget=retry_covers_budget)
            scope['independent']+=independent;scope['all_DAG_enough_retry']+=retry_covers_budget
            try:
                assert old['status']=='SUCCESS';candidates,front=formula(old['input']['w'],old['B'],old['r'])
                row.update(candidates=candidates,formula_frontier=front,archived_immediate=old['immediate'],archived_retained=old['retained'])
                assert front==old['immediate']==old['retained'],('frontier_mismatch',row)
                row['status']='SUCCESS'
            except Exception as e:row.update(status='FAILURE',error=repr(e));failures.append(row.copy())
            stats[row['status']]+=1;out.write(json.dumps(row)+'\n')
    assert scope=={'independent':1998,'all_DAG_enough_retry':32526}
    (D/'INDEPENDENT_FAILURES05.json').write_text(json.dumps(failures,indent=2)+'\n')
    summary=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='SUCCESS' if not failures else 'FAILURE',counts=dict(stats),scope_counts=dict(scope),scope_overlap=1998+32526-sum(stats.values()),seconds=time.monotonic()-start,new_scientific_executions=0,retrospective_analysis=True,hashes={f:sha(D/f) for f in ['INDEPENDENT_ALL_RETRIES05.md','independent05.py','ROWS01.jsonl','INDEPENDENT_ROWS05.jsonl','INDEPENDENT_FAILURES05.json']})
    (D/'INDEPENDENT_SUMMARY05.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2));return not failures
if __name__=='__main__':raise SystemExit(not main())
