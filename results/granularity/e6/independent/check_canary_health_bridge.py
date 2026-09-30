#!/usr/bin/env python3
"""Read-only validation: delayed reports cannot hide a winning unsafe health state."""
import importlib.util,json,hashlib,time
from pathlib import Path
from collections import deque

HERE=Path(__file__).resolve().parent;E6=HERE.parent
spec=importlib.util.spec_from_file_location('audit',HERE/'check_games_v3.py');audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def healthy(s):return sum(q in ('H','HP') for v,q in s[0])
def pending_reports(s):return sum(q in ('HP','BP') for v,q in s[0])
started=time.monotonic();rows=[]
for n in range(2,7):
 for m in range(1,n):
  path=E6/f'canary/v1/inputs/canary_n{n:02}_m{m:02}_fine.json'
  data=json.loads(path.read_text())
  for merge in ('none','transfers'):
   model=audit.Model(data,merge);seen,graph=model.enumerate();ranks,_=model.solve(seen,graph)
   assert all(healthy(s)>=m for s in ranks),'A winning state violates the physical floor'
   hidden=[s for s in graph if model.safe(s) and healthy(s)<m]
   longest=0;uc_checked=0
   for source in hidden:
    assert source not in ranks
    queue=deque([(source,0)]);visited={source};found=None
    while queue:
     state,depth=queue.popleft()
     if not model.safe(state):found=depth;break
     for action,targets in model.post(state).items():
      if action in model.control or action in model.updates:continue
      for target in targets:
       uc_checked+=1
       assert pending_reports(target)==pending_reports(state)-1
       if target not in visited:visited.add(target);queue.append((target,depth+1))
    assert found is not None and 1<=found<=pending_reports(source)
    longest=max(longest,found)
   rows.append(dict(n=n,m=m,merge=merge,input=str(path.relative_to(E6)),input_sha256=sha(path),reachable_states=len(seen),winning_states=len(ranks),safe_tester_below_physical_floor=len(hidden),largest_shortest_uc_path_to_error=longest,checked_uc_edges=uc_checked,status='PASS'))
report=dict(status='PASS',method='Independent full terminalized game enumeration and strong attractor. Every winning state meets the physical floor. Every tester-safe reachable state below the physical floor has an uncontrollable-only finite path to monitor error, strictly reducing pending reports on each step.',scope='All 15 measured n,m tuples, both fine and E1 transfers merge. This is semantic validation, not a new trial or metric substitution. Controllable restart may remain physically enabled during UC reporting but cannot prevent the adversarial report path.',checker_sha256=sha(HERE/'check_games_v3.py'),script_sha256=sha(Path(__file__)),elapsed_seconds=time.monotonic()-started,checks=rows)
with (HERE/'canary_health_bridge.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps(dict(status=report['status'],games=len(rows),hidden_unsafe_states=sum(x['safe_tester_below_physical_floor'] for x in rows),elapsed_seconds=report['elapsed_seconds'])))
