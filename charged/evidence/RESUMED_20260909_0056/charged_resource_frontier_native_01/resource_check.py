"""Reconstruct separate resource counters from a source-checked native record."""
def from_trace(case,trace):
 W=L=0
 for label in trace:
  si,act=label.split(':');w=8*case['jobs'][int(si)][0]
  W+=w
  if act=='P':L+=w
  elif act=='CF':W+=w;L+=w
 return dict(W=W,L=L,Q=len(trace))

def check(case,run,row):
 expected=from_trace(case,row['trace']);W=L=0
 for e in row['events']:
  if e['kind']=='K':
   amount=8*case['jobs'][e['job']][0];W+=amount
   if e['inside']:L+=amount
 Q=sum(row['callbacks'])+sum(row['conditionals'])
 assert expected==dict(W=W,L=L,Q=Q),'event/trace resource disagreement'
 assert row['work']==W
 assert L==8*sum(case['jobs'][i][0]*q for i,q in enumerate(row['protected_calls']))
 k=case['kappa'];assert all(g==0 and v==r==k and p==w for w,p,g,v,r in case['jobs'])
 assert row['cost']==W+L+8*k*Q,'linear-resource metric disagreement'
 kind,t=case['policy'].split('-');t=int(t);b=run['budget'];slack=max(b-t,0);n=len(case['jobs']);residual=max(b-slack,0)
 assert Q<=n+slack,'call slack violated'
 bound=8*sum(sorted((j[0] for j in case['jobs']),reverse=True)[:min(residual,n)]) if kind=='slack_three' else (8*sum(j[0] for j in case['jobs']) if residual else 0)
 assert L<=bound,'protected work frontier cap violated'
 return dict(**expected,cost=row['cost'],slack=slack,protected_cap=bound,metric='W + L + 8*kappa*Q; Q excludes readonly gets and writer calls')
