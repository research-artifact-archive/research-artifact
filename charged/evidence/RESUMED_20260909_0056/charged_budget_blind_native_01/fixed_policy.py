"""One fixed policy for all finite writer budgets; budget is oracle-only."""
from functools import lru_cache
POLICIES=[f'blind_{kind}-{r}' for kind in ['three','two'] for r in range(4)]
def ordinary(case):
 jobs=case['jobs'];n=len(jobs);policy=case['policy'];assert policy in POLICIES
 kind,r=policy.split('-');r=int(r);pred=[sum(1<<u for u,v in case['edges'] if v==i) for i in range(n)]
 assert all(w>0 and p==w and g==0 and v==fee and v in (0,2) for w,p,g,v,fee in jobs)
 def choose(mask,a):
  assert 0<=a<=3
  i=next(i for i in range(n) if mask>>i&1 and not pred[i]&mask)
  return i,1 if a else (0 if kind=='blind_three' else 2)
 @lru_cache(None)
 def f(mask,b,a):
  assert type(b) is int and b>=0 and 0<=a<=3
  if not mask:return 0
  i,m=choose(mask,a);w,p,g,v,fee=jobs[i];child=mask^(1<<i)
  if m==2:return p+f(child,b,a)
  if m==1:return f(child,b,a) if b==0 else max(f(child,b,a),w+v+f(mask,b-1,a-1))
  return f(child,b,a) if b==0 else max(f(child,b,a),w+p+f(child,b-1,a))
 def paths(mask,b,a,path='',trace=(),cost=0):
  if not mask:yield path,list(trace),cost;return
  i,m=choose(mask,a);w,p,g,v,fee=jobs[i];child=mask^(1<<i)
  if m==2:yield from paths(child,b,a,path,trace+(f'{i}:P',),cost+w+p+g+fee);return
  label='C' if m==0 else 'V';paid=w+v
  yield from paths(child,b,a,path+'S',trace+(f'{i}:{label}S',),cost+paid)
  if b:yield from paths(child if m==0 else mask,b-1,a if m==0 else a-1,path+'F',trace+(f'{i}:{label}F',),cost+paid+(w+p if m==0 else 0))
 return f,choose,paths
