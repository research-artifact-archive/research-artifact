import itertools,json,hashlib,time
from pathlib import Path
D=Path(__file__).resolve().parent
assert not(D/'INVISIBLE_SUMMARY05.json').exists() and not(D/'invisible05.jsonl').exists()
def nd(ps):
    ps=set(ps)
    return sorted(p for p in ps if not any(q!=p and q[0]<=p[0] and q[1]<=p[1] for q in ps))
def top(w,mask,B):return sum(sorted((v for i,v in enumerate(w) if mask>>i&1),reverse=True)[:B])
def interpret(w,C,H):
    W=L=0
    for i,v in enumerate(w):
        if C>>i&1:
            W+=v
            if H>>i&1:W+=v;L+=v
        else:W+=v;L+=v
    return W,L
start=time.monotonic();results=[]
with(D/'invisible05.jsonl').open('x') as out:
    for n in range(1,6):
        for w in itertools.product((1,2,4),repeat=n):
            for B in range(n+2):
                row=dict(n=n,w=w,B=B)
                try:
                    if time.monotonic()-start>110:row['status']='NOT_EXECUTED'
                    else:
                        full=(1<<n)-1;omega=sum(w);partitions=[]
                        for C in range(1<<n):
                            paths=[interpret(w,C,H) for H in range(1<<n) if H&~C==0 and H.bit_count()<=B]
                            pair=(max(x[0] for x in paths),max(x[1] for x in paths))
                            formula=(omega+top(w,C,B),sum(v for i,v in enumerate(w) if not C>>i&1)+top(w,C,B))
                            assert pair==formula,(C,pair,formula)
                            partitions.append([C,*pair])
                        a=sorted(w);A=[0]
                        for v in a:A.append(A[-1]+v)
                        prefixes=[(omega,0)] if B==0 else [(omega,omega)] if B>=n else [(omega,omega)]+[(omega+A[k]-A[k-B],omega-A[k-B]) for k in range(B+1,n+1)]
                        frontier=nd((x[1],x[2]) for x in partitions);assert frontier==nd(prefixes),(frontier,prefixes)
                        lcap=top(w,full,B);corner=min(x[1] for x in partitions if x[2]<=lcap)
                        expected=omega+lcap if B<n else omega;assert corner==expected
                        visible=omega+top(w,full,B+1)-max(w) if B<n else omega
                        price=max(w)-sorted(w,reverse=True)[B] if B<n else 0
                        assert corner-visible==price
                        row.update(status='SUCCESS',partitions=partitions,frontier=frontier,prefix_candidates=prefixes,L_cap=lcap,invisible_corner=corner,visible_corner=visible,Boolean_value=price)
                except Exception as e:row.update(status='FAILURE',error=repr(e))
                results.append(row);out.write(json.dumps(row)+'\n')
assert len(results)==2367
from collections import Counter
statuses=dict(Counter(r['status'] for r in results))
s=dict(status='SUCCESS' if statuses=={'SUCCESS':2367} else 'FAILURE',cases=2367,weight_vectors=363,statuses=statuses,seconds=time.monotonic()-start,strict_Boolean_value_cases=sum(r.get('Boolean_value',0)>0 for r in results),hashes={f:hashlib.sha256((D/f).read_bytes()).hexdigest() for f in ('INVISIBLE_PROTOCOL05.md','invisible05.py','invisible05.jsonl')})
(D/'INVISIBLE_SUMMARY05.json').write_text(json.dumps(s,indent=2)+'\n');print(json.dumps(s,indent=2));raise SystemExit(s['status']!='SUCCESS')
