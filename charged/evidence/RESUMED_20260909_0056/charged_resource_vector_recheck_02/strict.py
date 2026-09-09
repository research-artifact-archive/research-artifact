def input_class(case):
 jobs=case['jobs'];assert type(jobs) is list and 2<=len(jobs)<=5,'native shape'
 assert all(type(j) is list and len(j)==5 and all(type(x) is int for x in j) and 1<=j[0]<=256 and j[1]==j[0] and j[2]==0 and j[3]==j[4] and j[3] in [0,2] for j in jobs),'vector price class'
 assert type(case['kappa']) is int and all(j[3]==case['kappa'] for j in jobs),'common kappa'
 n=len(jobs);edges=case['edges'];assert type(edges) is list and all(type(e) is list and len(e)==2 and all(type(x) is int and 0<=x<n for x in e) and e[0]!=e[1] for e in edges),'edge domain'
 assert len({tuple(e) for e in edges})==len(edges),'duplicate edge'
 done=set()
 while len(done)<n:
  ready=[i for i in range(n) if i not in done and all(u in done for u,v in edges if v==i)];assert ready,'acyclicity';done.update(ready)

def check(case,table,legacy):
 input_class(case);return legacy.check(case,table)

def native_control_met(result,expected_accept,raw_status):
 if raw_status!='SUCCESS':return False
 if expected_accept:return result.get('accepted') is True and result.get('status')=='FEASIBLE'
 return result.get('accepted') is False and result.get('status')=='REJECTED' and result.get('layer')=='fixed_policy_and_static' and result.get('reason','').startswith("('captured parent',")
