from pathlib import Path
from functools import lru_cache
from itertools import permutations
from collections import Counter
import time,json,hashlib,datetime
D=Path(__file__).resolve().parent;BEGIN=time.monotonic();CAP=BEGIN+290
def bound():
    if time.monotonic()>CAP:raise TimeoutError('290-second internal cap')
def top(w,k):return sum(sorted(w,reverse=True)[:max(0,k)])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

class ScalarOracle:
    def __init__(self,w,g,edges,universal):
        self.w=w;self.g=g;self.n=len(w);self.universal=universal;self.pred=[0]*self.n
        for a,b in edges:self.pred[b]|=1<<a
        self.solve=lru_cache(None)(self._solve)
    def _solve(self,S,b,a):
        bound()
        if not S or (not b and not self.universal):return 0
        values=[]
        for i in range(self.n):
            if not S>>i&1 or self.pred[i]&S:continue
            R=S^(1<<i);w=self.w[i];g=self.g[i]
            values.append(g+w+self.solve(R,b,a))
            matched=self.solve(R,b,a)
            values.append(g+(max(matched,w+self.solve(R,b-1,a)) if b else matched))
            if a:
                values.append(max(matched,self.solve(S,b-1,a-1)) if b else matched)
        assert values,(S,b,a)
        return min(values)

def interpreted_counter_policy(w,g,edges,r):
    n=len(w);H=n+r;pred=[set() for _ in w]
    for a,b in edges:pred[b].add(a)
    leaves=[]
    def visit(done,failures,d,q,body,protected,entry,guards):
        bound()
        if len(done)==n:
            assert q<=H
            leaves.append(dict(B=d,Q=q,W=body,L=protected,entry=entry,G=guards,P=protected+entry));return
        ready=[i for i in range(n) if i not in done and pred[i]<=done]
        i=min(ready,key=lambda j:(w[j],j));after=done|{i}
        if failures<r:
            visit(after,failures,d,q+1,body+w[i],protected,entry,guards)
            visit(done,failures+1,d+1,q+1,body+w[i],protected,entry,guards)
        else:
            visit(after,failures,d,q+1,body+w[i],protected,entry+g[i],guards+1)
            visit(after,failures,d+1,q+1,body+2*w[i],protected+w[i],entry+g[i],guards+1)
    visit(set(),0,0,0,0,0,0,0)
    curve=[max(x['P'] for x in leaves if x['B']<=B) for B in range(H+1)]
    return curve,leaves

def schedules(w,g,edges):
    def cost(order):
        c=0;peak=sum(g)
        for i in order:c+=g[i];peak=max(peak,c+w[i])
        return peak
    orders=[]
    for order in permutations(range(len(w))):
        positions={i:k for k,i in enumerate(order)}
        if all(positions[a]<positions[b] for a,b in edges):orders.append((cost(order),order))
    remaining=set(range(len(w)));reverse=[]
    while remaining:
        sinks=[i for i in remaining if not any(a==i and b in remaining for a,b in edges)]
        pick=min(sinks,key=lambda i:(w[i],i));reverse.append(pick);remaining.remove(pick)
    chosen=tuple(reversed(reverse))
    return min(orders),cost(chosen),chosen,orders

def main():
    inputs=json.loads((D/'INPUTS01.json').read_text());planned=inputs['inputs']
    start=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_sha256=sha(Path(__file__)),protocol_sha256=sha(D/'PROTOCOL01.md'),input_sha256=sha(D/'INPUTS01.json'),proof_sha256=sha(D/'CANDIDATE_PROOF01.md'),planned_inputs=len(planned),planned_universal_roots=26874,planned_one_write=1809,planned_boundary_checks=5427,wall_cap_seconds=300)
    with(D/'START01.json').open('x') as f:json.dump(start,f,indent=2);f.write('\n')
    stats=Counter();errors=[];universal_roots=0;paths=0;informed_cases=0;boundary_checks=0;states=0;strict_order=0;examples=[]
    with(D/'ROWS01.jsonl').open('x') as out:
        for data in planned:
            row=dict(input=data)
            try:
                bound();w=data['w'];g=data['g'];edges=data['edges'];n=len(w);S=(1<<n)-1;Gamma=sum(g)
                u=ScalarOracle(w,g,edges,True);k=ScalarOracle(w,g,edges,False);curves=[]
                for r in range(3):
                    actual=[u.solve(S,B,r) for B in range(n+r+1)]
                    predicted=[(Gamma if B>=r else 0)+top(w,B-r) for B in range(n+r+1)]
                    played,leaves=interpreted_counter_policy(w,g,edges,r);paths+=len(leaves)
                    assert actual==predicted==played,('universal_curve',r,actual,predicted,played)
                    boundary=k.solve(S,r,r);boundary_checks+=1
                    assert boundary==0,('informed_boundary',r,boundary)
                    universal_roots+=len(actual);curves.append(dict(r=r,P=actual,policy_paths=len(leaves),informed_boundary=boundary))
                value=k.solve(S,1,0);informed_cases+=1
                (best,order),lawler,lawler_order,orders=schedules(w,g,edges)
                assert value==best==lawler,('one_write',value,best,lawler)
                strict_order+=len(set(x[0] for x in orders))>1
                if not edges:
                    descending=tuple(sorted(range(n),key=lambda i:(-w[i],i)))
                    assert dict((o,c) for c,o in orders)[descending]==best
                states+=u.solve.cache_info().currsize+k.solve.cache_info().currsize
                row.update(status='SUCCESS',universal=curves,informed_one_write=value,best_order=order,lawler_order=lawler_order,order_values=[dict(order=o,P=c) for c,o in orders])
                if data['kind']!='factorial':examples.append(row.copy())
            except TimeoutError as e:row.update(status='TIMEOUT',error=str(e));errors.append(row.copy())
            except Exception as e:row.update(status='FAILURE',error=repr(e));errors.append(row.copy())
            stats[row['status']]+=1;out.write(json.dumps(row)+'\n')
    assert sum(stats.values())==1809
    result=dict(start,status='PASS' if not errors else 'FAIL',counts=dict(stats),universal_roots=universal_roots,informed_one_write_cases=informed_cases,boundary_checks=boundary_checks,interpreted_policy_paths=paths,scalar_oracle_states=states,inputs_with_strict_order_effect=strict_order,errors=errors,examples=examples,seconds=time.monotonic()-BEGIN)
    result['scope']='finite canonical-policy/source-independent corroboration, no native g calibration, no joint frontier or least-W claim'
    with(D/'RESULT01.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['examples','errors']},indent=2));return not errors
if __name__=='__main__':raise SystemExit(not main())
