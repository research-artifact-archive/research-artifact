from pathlib import Path
from fractions import Fraction as F
from functools import lru_cache
import hashlib,json,resource,sys,time
from compact01 import singleton_profile,compile_profile,check_certificate
start=time.monotonic();x=json.loads(sys.argv[1]);m=x['m'];q=x['q'];weights=[1 if x['pattern']=='uniform' else 1+(37*i%97) for i in range(m)];W=sum(weights);mu=W if x['mu']=='W' else int(x['mu'])
print(json.dumps(dict(phase='STARTED',input=x,weights_sha256=hashlib.sha256(json.dumps(weights,separators=(',',':')).encode()).hexdigest())),flush=True)
H,G,order=singleton_profile(weights)
if x['method']=='compact':
 result=compile_profile(H,G,mu,q,W);check_certificate(H,G,mu,q,W,result);value=result['ratio'];states=None
else:
 @lru_cache(None)
 def ref(left,e):
  worst=F(0)
  for k,h in enumerate(H):
   den=mu+G[(e+k)//q];num=mu+h;a=F(num,den) if den else (F(1) if not num else float('inf'))
   b=ref(left-1,e+k) if k and left>1 else float('inf');worst=max(worst,min(a,b))
  return worst
 value=ref(q,0);states=ref.cache_info().currsize;result=None
assert isinstance(value,F) and value>=1
print(json.dumps(dict(phase='COMPLETE',input=x,status='SUCCESS',ratio=str(value),mu=mu,total_work=W,coverage_profile=G,sorted_component_order=order,certificate=result,reference_states=states,worker_seconds=time.monotonic()-start,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,platform=sys.platform,peak_rss_unit='bytes on macOS',service='checked ratio/policy and two certificates' if result else 'root ratio only'),default=str,separators=(',',':')),flush=True)
