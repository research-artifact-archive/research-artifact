"""Direct fixed threshold modes; finite native domain b0..3."""
from functools import lru_cache
POLICIES=[f'slack_{kind}-{t}' for kind in ['three','two'] for t in range(4)]
def ordinary(case):
 jobs=case['jobs'];n=len(jobs);policy=case['policy'];assert policy in POLICIES
 kind,t=policy.split('-');t=int(t);pred=[sum(1<<u for u,v in case['edges'] if v==i) for i in range(n)]
 assert all(w>0 and p==w and g==0 and v==r and v in (0,2) for w,p,g,v,r in jobs)
 def mode(b):return 1 if b==0 or b>t else (0 if kind=='slack_three' else 2)
 @lru_cache(None)
 def f(mask,b):
  assert type(b) is int and b>=0
  if not mask:return 0
  i=next(i for i in range(n) if mask>>i&1 and not pred[i]&mask);w,p,g,v,r=jobs[i];child=mask^(1<<i);m=mode(b)
  if m==2:return p+f(child,b)
  if m==1:return f(child,b) if b==0 else max(f(child,b),w+v+f(mask,b-1))
  return f(child,b) if b==0 else max(f(child,b),w+p+f(child,b-1))
 def choose(mask,b):
  i=next(i for i in range(n) if mask>>i&1 and not pred[i]&mask);return f(mask,b),i,mode(b)
 def paths(mask,b,path='',trace=(),cost=0):
  if not mask:yield path,list(trace),cost;return
  _,i,m=choose(mask,b);w,p,g,v,r=jobs[i];child=mask^(1<<i)
  if m==2:yield from paths(child,b,path,trace+(f'{i}:P',),cost+w+p+g+r);return
  label='C' if m==0 else 'V';paid=w+v
  yield from paths(child,b,path+'S',trace+(f'{i}:{label}S',),cost+paid)
  if b:yield from paths(child if m==0 else mask,b-1,path+'F',trace+(f'{i}:{label}F',),cost+paid+(w+p if m==0 else 0))
 return f,choose,paths
