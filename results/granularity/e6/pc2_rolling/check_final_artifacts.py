#!/usr/bin/env python3
"""Independent Python consistency audit; no solver execution or raw mutations."""
import csv,hashlib,json
from collections import defaultdict,deque
from pathlib import Path
P=Path(__file__).resolve().parent;V=P/'v2'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
issues=[]
def check(ok,message):
 if not ok:issues.append(message)
def hashes(base,obj):
 for name,h in obj['files'].items():check(sha(base/name)==h,'SHA mismatch: '+str(base/name))
man=read(V/'build/frozen_manifest.json');hashes(P,man)
expman=read(P/'validation_export/frozen_manifest.json');hashes(P/'validation_export',expman)
rows=list(csv.DictReader((V/'tables/results.csv').open()));check([r['job_id'] for r in rows]==man['schedule'],'CSV schedule mismatch')
for r in rows:
 p=V/'raw'/r['job_id'];inv=read(p/'invocation.json');end=read(p/'completion.json');hashes(p,end)
 check(r['input_sha256']==inv['input_sha256']==sha(V/'inputs/ProductionCell_Arms2_Calibration.lts'),'Input SHA mismatch')
 check(r['jar_sha256']==inv['jar_sha256']==man['jar_sha256'],'JAR SHA mismatch')
 check(float(r['whole_jvm_seconds'])==end['wall_seconds'],'Wall time mismatch')
 if end['timed_out']:
  check(r['status']=='TO' and all(not r[k] for k in ['states_discovered','successor_queries','worst_completion_rank','losing_region_states','certificate_states']),'TO has inferred metrics')
 else:
  d=read(p/'certificate_summary.json');check(r['status']==d['decision'],'Decision mismatch')
  for k in ['states_discovered','successor_queries','worst_completion_rank','certificate_states','initial_states']:check(int(r[k])==d[k],k+' mismatch')
  check(int(r['materialized_transition_outcomes'])==d['materialized_transitions'],'Outcome count mismatch')
p=V/'validation/export/lazy_none';end=read(p/'completion.json');hashes(p,end);inv=read(p/'invocation.json');a=read(p/'certificate.json');d=read(V/'raw/lazy_none/certificate_summary.json')
check(inv['original_invocation_sha256']==sha(V/'raw/lazy_none/invocation.json'),'Original invocation SHA mismatch')
check(inv['original_completion_sha256']==sha(V/'raw/lazy_none/completion.json'),'Original completion SHA mismatch')
for k in ['decision','states_discovered','successor_queries','materialized_transitions','worst_completion_rank']:check(a[k]==d[k],'Replay mismatch '+k)
s={x['id']:x for x in a['states']};check(len(s)==len(a['states'])==d['certificate_states'],'Certificate domain mismatch')
roots={i for i,x in s.items() if x['initial']};check(len(roots)==d['initial_states'],'Initial coverage mismatch')
edge=defaultdict(list)
for src,action,dst in a['strategy_edges']:
 check(src in s and dst in s,'Edge outside domain');edge[src].append((action,dst));check(s[src]['rank']>s[dst]['rank'],'Nondecreasing rank')
for i,x in s.items():
 check(x['safe'] and x['physical_operational_arms']>=1,'Unsafe/unavailable certificate state')
 check(bool(edge[i]) != x['goal'],'Goal outgoing or nonggoal deadlock')
 if x['goal']:check(x['rank']==0 and str(i) in a['goal_matches'],'Goal rank/match absent')
seen=set(roots);queue=deque(roots)
while queue:
 for _,dst in edge[queue.popleft()]:
  if dst not in seen:seen.add(dst);queue.append(dst)
check(seen==set(s),'Rank domain exceeds strategy reachable states')
check(max(x['rank'] for x in s.values())==a['worst_completion_rank'],'Maximum rank mismatch')
linked=a['linked_state_descriptions'];check(len(linked)==len(set(linked)),'Duplicate linked state description')
for src,action,dst in a['linked_edges']:check(0<=src<len(linked) and 0<=dst<len(linked),'Link edge outside domain')
summary=read(V/'validation/export/summary.json');check([x['status'] for x in summary['checks']]==['PASS','SKIP','SKIP'],'Export schedule mismatch')
check(a['certificate_checker'].startswith('PASS') and a['link_checker'].startswith('PASS'),'Native checker failed')
report={'status':'PASS' if not issues else 'FAIL','issues':issues,'scope':'Raw/CSV/SHA consistency and independent finite graph closure, exact reachable domain, rank, initial coverage, physical calibration availability; transition semantic closure and Link correctness are rechecked by the unchanged E1 checkers, not independently reimplemented for this FSP input.','measured_statuses':{r['job_id']:r['status'] for r in rows},'certificate_states':len(s),'certificate_initial_states':len(roots),'strategy_edges':len(a['strategy_edges']),'maximum_rank':a['worst_completion_rank'],'minimum_physical_operational_arms':min(x['physical_operational_arms'] for x in s.values()),'linked_states':len(linked),'linked_edges':len(a['linked_edges']),'certificate_sha256':sha(p/'certificate.json'),'timeout_retries':0}
with (V/'validation/final_artifact_audit.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps(report,indent=2))
raise SystemExit(bool(issues))
