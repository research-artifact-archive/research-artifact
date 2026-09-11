from pathlib import Path
from functools import lru_cache
from itertools import combinations, product
from fractions import Fraction
import argparse, hashlib, json, time, traceback

BASE=Path(__file__).resolve().parent
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def top(xs,k): return sum(sorted(xs,reverse=True)[:max(0,k)])

def explore(w,pred,r):
    n=len(w); full=(1<<n)-1
    @lru_cache(None)
    def ds(d,k): return top([w[i] for i in range(n) if d>>i&1],k)
    @lru_cache(None)
    def go(d,f,k,ell,b,kind):
        if d==full: return (0,0,0)
        ready=[i for i in range(n) if not d>>i&1 and pred[i]&d==pred[i]]
        if kind=='ascending': ready=[min(ready,key=lambda i:(w[i],i))]
        choices=[]
        def add(child,cw,cl,cq=1):
            v=go(*child)
            choices.append((cw+v[0],cl+v[1],cq+v[2]))
        for i in ready:
            nd=d|(1<<i); wi=w[i]
            if f<r:
                add((nd,f,k,ell,b,kind),wi,0)
                if b: add((d,f+1,k,ell,b-1,kind),wi,0)
            else:
                # Directly charge preparation once on cached match, twice on mismatch.
                add((nd,f,k,ell,b,kind),wi,0)
                if b: add((nd,f,k+1,ell+wi,b-1,kind),2*wi,wi)
                if kind=='all' and ell+wi<=ds(nd,k):
                    add((nd,f,k,ell+wi,b,kind),wi,wi)
        return tuple(max(v[j] for v in choices) for j in range(3))
    return go

def run(out,cap):
    out.mkdir(exist_ok=False)
    started=time.monotonic(); violations=[]; roots=rows=states=0
    max_ratio=Fraction(0); worst=None
    receipt={'status':'RUNNING','cap_seconds':cap,'inputs':{p.name:sha(p) for p in [Path(__file__),BASE/'FINITE_PROTOCOL01.md',BASE/'PROOF01.md']}}
    (out/'START.json').write_text(json.dumps(receipt,indent=2)+'\n')
    def check(cond,tag,row):
        if not cond: violations.append({'tag':tag,'row':row})
    try:
        with (out/'ROWS.jsonl').open('w') as fout, (out/'ROOTS.jsonl').open('w') as froot:
            for n in range(1,5):
                pairs=list(combinations(range(n),2))
                for mask in range(1<<len(pairs)):
                    pred=[0]*n
                    for j,(a,b) in enumerate(pairs):
                        if mask>>j&1: pred[b]|=1<<a
                    for w in product((1,2,4),repeat=n):
                        om=sum(w); mx=max(w); desc=sorted(w,reverse=True)
                        for r in range(3):
                            if time.monotonic()-started>cap: raise TimeoutError('declared total cap')
                            go=explore(w,pred,r); roots+=1
                            for b in range(n+r+1):
                                aw,al,aq=go(0,0,0,0,b,'all')
                                fw,fl,fq=go(0,0,0,0,b,'ascending')
                                if b<=r: lower=upper=om+b*mx
                                else:
                                    m=min(b-r,n)
                                    lower=om+max(r*desc[s-1]+sum(desc[:s]) for s in range(1,m+1))
                                    upper=om+r*mx+sum(desc[:m])
                                alpha=Fraction(3*r+2,2*r+2)
                                row={'n':n,'edge_mask':mask,'weights':w,'r':r,'B':b,'all_caller_W':aw,'all_caller_L':al,'all_caller_Q':aq,'min_ready_cached_W':fw,'full_class_lower':lower,'coarse_upper':upper}
                                check(aw<=upper,'upper',row)
                                check(aq<=n+r,'Q',row)
                                check(al<=top(w,b-r),'L',row)
                                check(Fraction(aw,lower)<=alpha,'alpha',row)
                                check(fw<=aw,'reference_le_all',row)
                                if r==0 or b<=r+1: check(aw==lower,'early_exact',row)
                                if mask==0: check(fw==lower,'independent_exact_reference',row)
                                ratio=Fraction(aw,lower)
                                if ratio>max_ratio: max_ratio=ratio;worst=row
                                fout.write(json.dumps(row,separators=(',',':'))+'\n');rows+=1
                            info=go.cache_info();states+=info.currsize
                            froot.write(json.dumps({'root':roots,'n':n,'edge_mask':mask,'weights':w,'r':r,'expanded_states':info.currsize})+'\n')
                            go.cache_clear()
        geometry=[]
        for r in range(1,9):
            prior=Fraction(0)
            for n in (1,2,4,8,16,32,64,128,256):
                w=[r**i*(r+1)**(n-i-1) for i in range(n)]
                om=sum(w); h=(r+1)**n; prefix=0
                for x in w:
                    prefix+=x
                    check(r*x+prefix==h,'geometric_term',{'r':r,'n':n})
                uw=2*om+r*w[0]; opt=om+h; ratio=Fraction(uw,opt); alpha=Fraction(3*r+2,2*r+2)
                row={'r':r,'n':n,'weights':w,'caller_W':uw,'independent_optimal_W':opt,'ratio':str(ratio),'ratio_decimal':float(ratio),'alpha':str(alpha),'gap':str(alpha-ratio)}
                check(prior<=ratio<alpha,'geometric_approach',row);prior=ratio
                geometry.append(row)
        (out/'GEOMETRIC.json').write_text(json.dumps(geometry,indent=2)+'\n')
        receipt.update(status='SUCCESS' if not violations else 'VIOLATIONS',roots=roots,rows=rows,expanded_states=states,geometric_rows=len(geometry),max_finite_ratio=str(max_ratio),max_finite_row=worst)
    except Exception as exc:
        receipt.update(status='TIMEOUT' if isinstance(exc,TimeoutError) else 'ERROR',error=repr(exc),traceback=traceback.format_exc(),roots=roots,rows=rows,expanded_states=states)
    finally:
        (out/'VIOLATIONS.json').write_text(json.dumps(violations,indent=2)+'\n')
        receipt.update(violations=len(violations),elapsed_seconds=time.monotonic()-started)
        receipt['outputs']={p.name:sha(p) for p in out.iterdir() if p.is_file() and p.name not in ('START.json','RESULT.json')}
        (out/'RESULT.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))
    return 0 if receipt['status']=='SUCCESS' else 1

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--cap',type=float,default=300)
    a=ap.parse_args();raise SystemExit(run(a.out,a.cap))
