from fractions import Fraction as F
from heapq import merge

def known_curve(G,q,kappa):
 assert q>=1 and kappa>=0 and G[0]==0 and G[-1]>0 and all(a<=b for a,b in zip(G,G[1:]))
 cap=kappa+G[-1]
 return [min(cap,x) for x in merge(*([t*kappa+g for g in G[:-1]] for t in range(1,q+1)))]+[cap]

def feasible(H,K,mu,kappa,q,R):
 e=0;path=[];p,d=R.numerator,R.denominator
 for step in range(q):
  chosen=None
  for k,h in enumerate(H):
   if h is None:continue
   a=mu+kappa*(step+1)+h;b=mu+K[e+k]
   if a*d>p*b:chosen=k;break
  if chosen is None:return True,path,dict(step=step,e=e)
  k=chosen;path.append(dict(step=step,e=e,k=k,numerator=mu+kappa*(step+1)+H[k],denominator=mu+K[e+k]));e+=k
 return False,path,dict(step=q,e=e)

def compile_profile(H,G,mu,kappa,q):
 K=known_curve(G,q,kappa);U=mu+q*kappa+G[-1];assert isinstance(U,int) and U>0
 lo=F(1);hi=F(U);calls=1;ok,path,end=feasible(H,K,mu,kappa,q,lo)
 if ok:return dict(ratio=lo,upper_path=path,upper_end=end,lower_path=[],lower_kind='ratio_at_least_one',decisions=calls,known_curve=K)
 ok,_,_=feasible(H,K,mu,kappa,q,hi);calls+=1;assert ok;lower=path
 while hi-lo>=F(1,U*U):
  mid=(hi+lo)/2;ok,path,_=feasible(H,K,mu,kappa,q,mid);calls+=1
  if ok:hi=mid
  else:lo=mid;lower=path
 finite=[F(x['numerator'],x['denominator']) for x in lower if x['denominator']];assert finite
 rho=min(finite);assert lo<rho<=hi
 ok,upper,end=feasible(H,K,mu,kappa,q,rho);calls+=1;assert ok
 return dict(ratio=rho,upper_path=upper,upper_end=end,lower_path=lower,lower_kind='complete_adversarial_path',decisions=calls,known_curve=K,isolation_lower=lo,isolation_upper=hi,integer_bound=U)

def check_certificate(H,G,mu,kappa,q,r):
 assert mu>=0 and kappa>=0 and q>=1 and len(H)==len(G) and H[0]==G[0]==0
 maxval=0
 for h,g in zip(H,G):
  if h is not None:assert isinstance(h,int) and h>=0;maxval=max(maxval,h)
  assert g==maxval
 K=r['known_curve'];assert K==known_curve(G,q,kappa);R=F(r['ratio']);assert R>=1
 if r['lower_kind']=='ratio_at_least_one':assert R==1 and r['lower_path']==[]
 else:
  assert r['lower_kind']=='complete_adversarial_path' and len(r['lower_path'])==q;e=0;values=[]
  for step,x in enumerate(r['lower_path']):
   k=x['k'];assert 0<=k<len(H) and H[k] is not None
   a=mu+kappa*(step+1)+H[k];b=mu+K[e+k]
   assert x==dict(step=step,e=e,k=k,numerator=a,denominator=b)
   if b:values.append(F(a,b));assert F(a,b)>=R
   else:assert a>0
   e+=k
  assert values and min(values)==R
 assert len(r['upper_path'])<q;e=0
 def accepted(step,k):return (mu+kappa*(step+1)+H[k])*R.denominator<=R.numerator*(mu+K[e+k])
 for step,x in enumerate(r['upper_path']):
  k=x['k'];assert 0<=k<len(H) and H[k] is not None
  assert x==dict(step=step,e=e,k=k,numerator=mu+kappa*(step+1)+H[k],denominator=mu+K[e+k])
  assert not accepted(step,k) and all(accepted(step,j) for j,h in enumerate(H[:k]) if h is not None);e+=k
 assert r['upper_end']==dict(step=len(r['upper_path']),e=e)
 assert all(accepted(len(r['upper_path']),k) for k,h in enumerate(H) if h is not None)
 return True
