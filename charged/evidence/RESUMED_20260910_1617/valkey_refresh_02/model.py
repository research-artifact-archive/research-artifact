"""Fixed-action retained logical-snapshot model; all costs are supplied units."""
from functools import lru_cache

def compile_policy(weights,words,q,alpha,beta,rho):
 obs=tuple(sorted(words));counts={m:len(words[m]) for m in obs};h={m:sum(w for i,w in enumerate(weights) if m>>i&1) for m in obs};P=sum(weights);sigma=min(counts[m] for m in obs if h[m]==P);E=q*sigma;a=alpha+beta;I=beta*P+rho;S=a*P+rho
 @lru_cache(None)
 def informed_prepared(t,b):
  return max(rho+min(a*h[m],beta*h[m]+informed_prepared(t-1,b-counts[m]) if t else float('inf')) for m in obs if counts[m]<=b)
 curve=[min(S,I+informed_prepared(q-1,b)) for b in range(E+1)]
 assert curve[-1]==S
 @lru_cache(None)
 def theta(t,e):
  return min(max(curve[min(E,e+counts[m])]-rho-a*h[m],theta(t-1,min(E,e+counts[m]))-rho-beta*h[m] if t else float('-inf')) for m in obs)
 actions={}
 for t in range(q):
  for e in range(E+1):
   for m in obs:
    z=min(E,e+counts[m]);accept=curve[z]-rho-a*h[m];reject=theta(t-1,z)-rho-beta*h[m] if t else float('-inf')
    actions[f'{t}:{e}:{m}']='r' if reject>accept else 'a'
 dp=I-theta(q-1,0);dd=S-curve[0]
 return {'weights':weights,'counts':{str(m):counts[m] for m in obs},'damage':h,'q':q,'alpha':alpha,'beta':beta,'rho':rho,'initial_charge':I,'direct_charge':S,'ceiling':E,'curve':curve,'prepared_loss':dp,'direct_loss':dd,'loss':min(dp,dd),'root_action':'direct' if dd<=dp else 'prepare','actions':actions}
