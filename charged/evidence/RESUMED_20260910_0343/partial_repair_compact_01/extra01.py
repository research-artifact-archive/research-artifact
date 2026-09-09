from pathlib import Path
from fractions import Fraction as F
from functools import lru_cache
import datetime,hashlib,json,time,traceback
from compact01 import scale,geometry,compile_profile,check_certificate
P=Path(__file__).resolve().parent;O=P/'extra01';O.mkdir();start=time.monotonic()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(n,x):
 with (O/n).open('x') as f:json.dump(x,f,indent=2,default=str);f.write('\n')
put('INPUT_RECEIPT.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),plan_sha256=sha(P/'EXTRA_PLAN.md'),compiler_sha256=sha(P/'compact01.py'),script_sha256=sha(Path(__file__)),expected=108))
rows=[];failures=[]
try:
 for ww in [('1/3','2/5','7/2'),('9/7','1/5','2/3','11/2')]:
  m=len(ww);single=tuple(1<<i for i in range(m));families=[single,single+((1<<m)-1,),tuple((1<<i)|(1<<(i+1)) for i in range(m-1))]
  for footprints in families:
   for q in [1,2,3,4,8,16]:
    for baseline in ['0','1/11','5/3']:
     weights,mu,unit=scale(ww,baseline);H,G,witness,cover,work=geometry(weights,footprints);result=compile_profile(H,G,mu,q,sum(weights));check_certificate(H,G,mu,q,sum(weights),result)
     @lru_cache(None)
     def ref(left,e):
      worst=F(0)
      for d,k in cover.items():
       den=mu+G[(e+k)//q];num=mu+work[d];a=F(num,den) if den else (F(1) if not num else float('inf'))
       retry=ref(left-1,e+k) if left>1 and d else float('inf');worst=max(worst,min(a,retry))
      return worst
     exact=ref(q,0);ok=exact==result['ratio'];vals=[h for h in H if h is not None]
     row=dict(weights=ww,footprints=footprints,q=q,mu=baseline,scale=unit,H=H,G=G,nonmonotone_H=any(a>b for a,b in zip(vals,vals[1:])),missing_cost_entries=sum(h is None for h in H),ratio=str(result['ratio']),reference=str(exact),reference_states=ref.cache_info().currsize,status='PASS' if ok else 'FAIL',certificate=result);rows.append(row)
     if not ok:failures.append(row)
     if time.monotonic()-start>170:raise TimeoutError('170second cap')
 assert len(rows)==108
 put('OUTCOMES.json',rows);put('FAILURES.json',failures);put('RECEIPT.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='PASS' if not failures else 'FAIL',rows=len(rows),nonmonotone_H_rows=sum(x['nonmonotone_H'] for x in rows),missing_cost_rows=sum(bool(x['missing_cost_entries']) for x in rows),failures=len(failures),seconds=time.monotonic()-start,outcomes_sha256=sha(O/'OUTCOMES.json')))
 print((O/'RECEIPT.json').read_text(),flush=True)
except BaseException as e:
 put('FAILED_OUTCOMES.json',rows);put('FAILURE_RECEIPT.json',dict(status='TIMEOUT' if isinstance(e,TimeoutError) else 'FAILURE',error=repr(e),traceback=traceback.format_exc(),rows=len(rows),seconds=time.monotonic()-start));raise
