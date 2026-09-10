from pathlib import Path
from functools import lru_cache
from itertools import product
from collections import Counter
import datetime, hashlib, json, time
D=Path(__file__).resolve().parent
START=time.monotonic(); DEADLINE=START+590
def bounded():
    if time.monotonic()>DEADLINE: raise TimeoutError('590s internal cap within600s attempt')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def encoded(x): return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def top(w,k): return sum(sorted(w,reverse=True)[:max(0,k)])

class Universal:
    def __init__(self,w,pred,r):
        self.w=w; self.pred=pred; self.r=r; self.H=len(w)+r; self.visits=0
        self.solve=lru_cache(None)(self._solve)
    def _solve(self,S,a,d,ell):
        bounded(); self.visits+=1
        if ell>top(self.w,d-self.r): return ()
        if not S: return (((0,)*(self.H+1),('done',)),)
        front={}
        def offer(c,t):
            if any(all(x<=y for x,y in zip(old,c)) for old in front): return
            obsolete=[old for old in front if all(x<=y for x,y in zip(c,old))]
            for old in obsolete: del front[old]
            front[c]=t
        for i,v in enumerate(self.w):
            if not S>>i&1 or self.pred[i]&S: continue
            R=S^(1<<i)
            for c,t in self.solve(R,a,d,ell+v): offer(c,('fresh',i,t))
            matched=self.solve(R,a,d,ell)
            for mode,other in [('cached',self.solve(R,a,d+1,ell+v)),('cheap',self.solve(S,a-1,d+1,ell) if a else ())]:
                for c0,t0 in matched:
                    for c1,t1 in other:
                        c=(c0[0],)+tuple(max(c0[k],v+c1[k-1]) for k in range(1,self.H+1))
                        offer(c,(mode,i,t0,t1))
        return tuple(sorted(front.items()))

def interpret(tree,w,pred,r):
    n=len(w); H=n+r; maxima=[None]*(H+1); maxL=[None]*(H+1); paths=0; largestQ=0
    def walk(t,completed,d,q,W,L):
        nonlocal paths,largestQ
        bounded(); mode=t[0]
        if mode=='done':
            assert completed==(1<<n)-1,('incomplete',completed)
            assert q<=H and L<=top(w,d-r),('universal_contract',d,q,W,L)
            paths+=1; largestQ=max(largestQ,q)
            for B in range(d,H+1):
                maxima[B]=W if maxima[B] is None else max(maxima[B],W)
                maxL[B]=L if maxL[B] is None else max(maxL[B],L)
            return
        i=t[1]; v=w[i]
        assert not completed>>i&1 and pred[i]&completed==pred[i],('not_ready',i,completed)
        if mode=='fresh': walk(t[2],completed|(1<<i),d,q+1,W+v,L+v)
        elif mode in ('cached','cheap'):
            # Each actual comparison has its own immediately computed result.
            prepaid=W+v
            walk(t[2],completed|(1<<i),d,q+1,prepaid,L)
            if mode=='cached': walk(t[3],completed|(1<<i),d+1,q+1,prepaid+v,L+v)
            else: walk(t[3],completed,d+1,q+1,prepaid,L)
        else: raise AssertionError(('unknown_mode',mode))
    walk(tree,0,0,0,0,0)
    assert all(x is not None for x in maxima)
    return dict(W=maxima,L=maxL,paths=paths,maximum_Q=largestQ)

def population():
    for n in range(1,4):
        edges=[(i,j) for i in range(n) for j in range(i+1,n)]
        for mask in range(1<<len(edges)):
            selected=[e for k,e in enumerate(edges) if mask>>k&1]
            for w in product((1,2,4),repeat=n):
                for r in range(3): yield dict(kind='exhaustive',w=w,edges=selected,r=r)
    for name,w in [('old_chain6',(2,4,1,1,2,1)),('old_chain7_intermediate_crossing',(2,1,1,1,4,3,6))]:
        yield dict(kind=name,w=w,edges=[(i,i+1) for i in range(len(w)-1)],r=1)

def main():
    assert not(D/'UNKNOWN_ROWS02.jsonl').exists() and not(D/'UNKNOWN_SUMMARY02.json').exists()
    inputs=list(population()); assert len(inputs)==713
    start=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),protocol_sha256=sha(D/'UNKNOWN_PROTOCOL02.md'),source_sha256=sha(Path(__file__)),planned=len(inputs),cap_seconds=600)
    (D/'UNKNOWN_ATTEMPT02_START.json').write_text(json.dumps(start,indent=2)+'\n')
    stats=Counter(); widths=Counter(); paths=0; visits=0; failures=[]; witnesses=[]
    with(D/'UNKNOWN_ROWS02.jsonl').open('x') as out:
        for index,inp in enumerate(inputs):
            row=dict(index=index,input=inp)
            try:
                if time.monotonic()>DEADLINE: row['status']='NOT_EXECUTED'
                else:
                    w=inp['w']; r=inp['r']; n=len(w); pred=[0]*n
                    for i,j in inp['edges']: pred[j]|=1<<i
                    game=Universal(w,pred,r); front=game.solve((1<<n)-1,r,0,0)
                    assert front,('empty_root_frontier',inp)
                    checks=[]
                    for curve,tree in front:
                        got=interpret(tree,w,pred,r); expected=[sum(w)+e for e in curve]
                        assert got['W']==expected,('interpreter_curve',got,expected)
                        assert got['L']==[top(w,B-r) for B in range(n+r+1)],('optimal_protection_curve',got['L'])
                        if r==0: assert expected==[sum(w)+top(w,B) for B in range(n+1)]
                        checks.append(dict(curve=expected,verification=got,witness_sha256=hashlib.sha256(encoded(tree)).hexdigest()))
                        paths+=got['paths']
                    if inp['kind']=='old_chain6': assert [x['curve'] for x in checks]==[[11,15,19,21,22,22,23,24]],('old_chain6_regression',checks)
                    if inp['kind']!='exhaustive' or len(front)>1: witnesses.append(dict(index=index,input=inp,trees=[dict(extra_curve=c,tree=t) for c,t in front]))
                    visits+=game.visits; widths[len(front)]+=1
                    row.update(status='SUCCESS',frontier=checks,states=game.visits)
            except TimeoutError as e: row.update(status='TIMEOUT',error=str(e))
            except Exception as e: row.update(status='FAILURE',error=repr(e)); failures.append(row.copy())
            stats[row['status']]+=1; out.write(json.dumps(row)+'\n')
    (D/'UNKNOWN_FAILURES02.json').write_text(json.dumps(failures,indent=2)+'\n')
    (D/'UNKNOWN_WITNESSES02.json').write_text(json.dumps(witnesses,indent=2)+'\n')
    summary=dict(start,status='SUCCESS' if stats=={'SUCCESS':713} else 'FAILURE',counts=dict(stats),frontier_widths=dict(widths),interpreted_paths=paths,visited_states=visits,seconds=time.monotonic()-START,hashes={f:sha(D/f) for f in ['UNKNOWN_ROWS02.jsonl','UNKNOWN_FAILURES02.json','UNKNOWN_WITNESSES02.json']})
    (D/'UNKNOWN_SUMMARY02.json').write_text(json.dumps(summary,indent=2)+'\n'); print(json.dumps(summary,indent=2)); return summary['status']=='SUCCESS'
if __name__=='__main__': raise SystemExit(not main())
