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
 if case['policy'] in ['qn_three','cached_all','protected_all']:assert Q==len(case['jobs']),'atomic-call cap violated'
 if case['policy']=='cached_all':
  total=8*sum(j[0] for j in case['jobs']);top=8*sum(sorted((j[0] for j in case['jobs']),reverse=True)[:min(run['budget'],len(case['jobs']))])
  assert L<=top and W<=total+top,'cached-all work bound violated'
 if case['policy']=='protected_all':assert W==L==8*sum(j[0] for j in case['jobs'])
 return dict(**expected,cost=row['cost'],metric='W + L + 8*kappa*Q; Q excludes readonly gets and writer calls')
