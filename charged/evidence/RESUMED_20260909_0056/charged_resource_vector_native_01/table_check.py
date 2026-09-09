"""Check complete policy value tables by the declared original-mode equations."""
POLICIES={'scalar_three','scalar_two_protect','scalar_two_fast','qn_three','cached_all','protected_all'}
def check(case,table):
 jobs=case['jobs'];n=len(jobs);policy=case['policy'];assert policy in POLICIES
 assert set(table)==set(range(1<<n)) and all(len(x)==n+1 and all(type(v) is int and v>=0 for v in x) for x in table.values())
 assert table[0]==[0]*(n+1)
 edges=case['edges'];checked=0
 for b in range(n+1):
  for mask in range(1,1<<n):
   ready=[i for i in range(n) if mask>>i&1 and not any(v==i and mask>>u&1 for u,v in edges)];assert ready
   if policy in ['cached_all','protected_all']:ready=ready[:1]
   modes=[0] if policy=='cached_all' else [2] if policy=='protected_all' else [1,2] if policy.startswith('scalar_two') else [0,2] if policy=='qn_three' and b else [0,1,2]
   options=[]
   for i in ready:
    w,p,g,v,r=jobs[i];m=min(v,g+r);d=g+r-m;q=p+d;s=w+p;child=mask^(1<<i)
    for mode in modes:
     if mode==2:value=q+table[child][b]
     elif mode==1:value=table[child][b] if b==0 else max(table[child][b],w+m+table[mask][b-1])
     else:value=d+table[child][b] if b==0 else d+max(table[child][b],s+table[child][b-1])
     options.append(value)
   assert table[mask][b]==min(options),'table Bellman equality';checked+=1
 if policy!='cached_all':
  assert all(table[mask][-1]==sum(jobs[i][1] for i in range(n) if mask>>i&1) for mask in table),'saturation'
 else:
  assert all(table[mask][-1]==sum(jobs[i][0]+jobs[i][1] for i in range(n) if mask>>i&1) for mask in table),'cached saturation'
 return dict(states=len(table),budget_positions=n+1,equations=checked,tail_basis='p<=c gives private-budget/protected-all equality by n; cached-all has <=n completing failures; forced protection is constant',constructor_imported=False)
