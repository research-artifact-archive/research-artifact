"""Direct original-mode recurrence for each declared selector; no compiler imports."""
from functools import lru_cache
POLICIES=['scalar_three','scalar_two_protect','scalar_two_fast','qn_three','cached_all','protected_all']

def ordinary(case):
 jobs=case['jobs'];n=len(jobs);policy=case['policy'];assert policy in POLICIES
 pred=[sum(1<<u for u,v in case['edges'] if v==i) for i in range(n)]
 assert all(w>0 and p==w and g==0 and v==r and v in (0,2) for w,p,g,v,r in jobs)
 def modes(b):
  if policy=='scalar_three':return [2,1,0]
  if policy=='scalar_two_protect':return [2,1]
  if policy=='scalar_two_fast':return [1,2]
  if policy=='qn_three':return [2,0] if b else [1,2,0]
  return [0] if policy=='cached_all' else [2]
 @lru_cache(None)
 def f(mask,b):
  assert type(b) is int and b>=0
  if b>n:return f(mask,n)
  if not mask:return 0
  return min(x[0] for x in choices(mask,b))
 def choices(mask,b):
  ready=[i for i in range(n) if mask>>i&1 and not pred[i]&mask]
  if policy in ['cached_all','protected_all']:ready=ready[:1]
  out=[]
  for priority,mode in enumerate(modes(b)):
   for i in ready:
    w,p,g,v,r=jobs[i];m=min(v,g+r);delta=g+r-m;child=f(mask^(1<<i),b)
    if mode==2:q=p+delta+child
    elif mode==1:q=child if b==0 else max(child,w+m+f(mask,b-1))
    else:q=delta+child if b==0 else delta+max(child,w+p+f(mask^(1<<i),b-1))
    out.append((q,priority,i,mode))
  assert out,'cyclic or empty readiness'
  return out
 def choose(mask,b):
  q,priority,i,mode=min(choices(mask,b));assert q==f(mask,b)
  return q,i,mode
 def paths(mask,b,path='',trace=(),cost=0):
  if not mask:yield path,list(trace),cost;return
  _,i,mode=choose(mask,b);w,p,g,v,r=jobs[i];child=mask^(1<<i)
  if mode==2:
   yield from paths(child,b,path,trace+(f'{i}:P',),cost+w+p+g+r);return
  label='C' if mode==0 else ('V' if v<=g+r else 'A');paid=w+g+r if mode==0 else w+min(v,g+r)
  yield from paths(child,b,path+'S',trace+(f'{i}:{label}S',),cost+paid)
  if b:yield from paths(child if mode==0 else mask,b-1,path+'F',trace+(f'{i}:{label}F',),cost+paid+(w+p if mode==0 else 0))
 return f,choose,paths
