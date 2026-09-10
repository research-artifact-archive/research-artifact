from pathlib import Path
from functools import lru_cache
from itertools import product
from collections import Counter
import datetime,hashlib,json,time,traceback
D=Path(__file__).resolve().parent
START=time.monotonic();DEADLINE=START+590
def bounded():
    if time.monotonic()>DEADLINE:raise TimeoutError('590s internal cap within600s attempt')
def nd(ps):
    best=float('inf');out=[]
    for w,l in sorted(set(ps)):
        if l<best:out.append((w,l));best=l
    return tuple(out)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
class Canonical:
    def __init__(self,w,pred):self.w=w;self.pred=pred;self.calls=0;self.solve=lru_cache(None)(self._solve)
    def ready(self,S):return [i for i in range(len(self.w)) if S>>i&1 and not self.pred[i]&S]
    def _solve(self,S,b,a):
        bounded();self.calls+=1
        if not S or not b:return ((0,0),)
        candidates=[]
        for i in self.ready(S):
            R=S^(1<<i);v=self.w[i];same=self.solve(R,b,a);less=self.solve(R,b-1,a)
            candidates.extend((e,v+l) for e,l in same)
            candidates.extend((max(e0,v+e1),max(l0,v+l1)) for e0,l0 in same for e1,l1 in less)
            if a:
                failed=self.solve(S,b-1,a-1)
                candidates.extend((max(e0,v+e1),max(l0,l1)) for e0,l0 in same for e1,l1 in failed)
        return nd(candidates)
class Retained:
    def __init__(self,w,pred):self.w=w;self.pred=pred;self.calls=0;self.solve=lru_cache(None)(self._solve)
    def _solve(self,S,R,b,a):
        bounded();self.calls+=1
        assert R&~S==0
        if not S:return ((0,0),)
        if not b:return ((sum(v for i,v in enumerate(self.w) if S>>i&1 and not R>>i&1),0),)
        out=[]
        for i,v in enumerate(self.w):
            if not S>>i&1 or self.pred[i]&S:continue
            rem=S&~(1<<i);records=R&~(1<<i)
            # Protected completion can discard its own prepaid record.
            out.extend((v+x,v+y) for x,y in self.solve(rem,records,b,a))
            if not R>>i&1:
                # Explicitly prepay a ready job without selecting its next mode.
                out.extend((v+x,y) for x,y in self.solve(S,R|(1<<i),b,a))
            else:
                matched=self.solve(rem,records,b,a);recomputed=self.solve(rem,records,b-1,a)
                out.extend((max(x0,v+x1),max(y0,v+y1)) for x0,y0 in matched for x1,y1 in recomputed)
                if a:
                    failed=self.solve(S,records,b-1,a-1)
                    out.extend((max(x0,x1),max(y0,y1)) for x0,y0 in matched for x1,y1 in failed)
        return nd(out)

def main():
    assert not(D/'SUMMARY01.json').exists() and not(D/'ROWS01.jsonl').exists()
    expected={}
    for line in(D.parent/'joint_work_01/known_frontiers01.jsonl').open():
        r=json.loads(line);inp=r['input']
        key=(tuple(inp['works']),tuple(tuple(e) for e in inp['edges']),inp['B'])
        expected[key]=tuple(sorted((sum(inp['works'])+p['E'],p['L']) for p in r['result']['frontier']))
    start=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),protocol_sha256=sha(D/'FINITE_PROTOCOL01.md'),script_sha256=sha(Path(__file__)),planned=96795,cap_seconds=600)
    (D/'ATTEMPT01_START.json').write_text(json.dumps(start,indent=2)+'\n')
    stats=Counter();visited=Counter();denom=Counter();failures=[];inputs=0
    with(D/'ROWS01.jsonl').open('x') as out:
        for n in range(1,5):
            pairs=[(i,j) for i in range(n) for j in range(i+1,n)]
            for mask in range(1<<len(pairs)):
                edges=[x for j,x in enumerate(pairs) if mask>>j&1];pred=[0]*n
                for i,j in edges:pred[j]|=1<<i
                for w in product((1,2,4),repeat=n):
                    inputs+=1;full=(1<<n)-1;omega=sum(w);c=Canonical(w,pred);ret=Retained(w,pred)
                    for a in range(3):
                        for b in range(n+a+1):
                            row=dict(input=dict(n=n,w=w,edges=edges),r=a,B=b)
                            try:
                                if time.monotonic()>DEADLINE:row['status']='NOT_EXECUTED'
                                else:
                                    one=tuple((omega+e,l) for e,l in c.solve(full,b,a));two=ret.solve(full,0,b,a)
                                    assert one==two,('retained_vs_immediate',one,two)
                                    lmin=sum(sorted(w,reverse=True)[:max(0,b-a)])
                                    assert min(l for e,l in one)==lmin,('protected_formula',one,lmin)
                                    assert any(x<=omega and y<=omega for x,y in one)
                                    if b==n+a:assert one==((omega,omega),)
                                    if a==0:assert one==expected[(w,tuple(tuple(e) for e in edges),b)],('archived_r0',one)
                                    row.update(status='SUCCESS',immediate=one,retained=two,minimum_L=lmin)
                            except TimeoutError as e:row.update(status='TIMEOUT',error=str(e))
                            except Exception as e:row.update(status='FAILURE',error=repr(e));failures.append(row.copy())
                            stats[row['status']]+=1;denom[n]+=1;out.write(json.dumps(row)+'\n')
                    visited['canonical_states']+=c.calls;visited['retained_states']+=ret.calls
    assert inputs==5421 and sum(stats.values())==96795 and dict(denom)=={1:27,2:216,3:3240,4:93312}
    # Compare against archived r0 rows separately using the recorded field schema.
    (D/'FAILURES01.json').write_text(json.dumps(failures,indent=2)+'\n')
    summary=dict(start,status='SUCCESS' if stats=={'SUCCESS':96795} else 'FAILURE',counts=dict(stats),input_count=inputs,by_n=dict(denom),visited=dict(visited),seconds=time.monotonic()-START,r0_archive_comparison='All26844r0frontiers compared' if stats=={'SUCCESS':96795} else 'See per-case failures',hashes={f:sha(D/f) for f in ['ROWS01.jsonl','FAILURES01.json']})
    (D/'SUMMARY01.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2));return summary['status']=='SUCCESS'
if __name__=='__main__':raise SystemExit(not main())
