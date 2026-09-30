#!/usr/bin/env python3
import copy,hashlib,importlib.util,json,sys
from collections import deque
from pathlib import Path
sys.dont_write_bytecode=True;E6=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('reviewed_checker',OUT/'reviewed_checker_b8.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
source=(OUT/'reviewed_checker_b8.py').read_bytes();base=json.loads((E6/'rolling/v1/inputs/rolling_n02_m01_k01.json').read_text());model=mod.Model(base,'none');seen,graph=model.enumerate();ranks,_=model.solve(seen,graph)
proof=json.loads((E6/'rolling/v1/raw/series/rolling_n02_m01_k01_lazy/certificate.json').read_text());mutated=copy.deepcopy(proof);goal=next(s for s in mutated['states'] if s['goal']);mutated['strategy_edges'].append([goal['id'],'serve_1',goal['id']]);goal_result=mod.Model(base,'none').certificate(mutated,seen,ranks)
# Construct locally valid decreasing policy on all winning states, including states not reached by this policy.
ordered=sorted(ranks,key=str);ids={q:i for i,q in enumerate(ordered)};nodes=[];edges=[]
for q in ordered:
 p,t,pending=q;nodes.append({'id':ids[q],'physical':p,'testers':dict(t),'pending':list(pending),'initial':q in model.roots,'safe':model.safe(q),'goal':model.goal(q),'rank':ranks[q]})
 if model.goal(q):continue
 buckets=graph[q];uc=[a for a in buckets if a not in model.control and a not in model.updates]
 selected=uc if uc else [sorted(a for a,targets in buckets.items() if targets<=ranks.keys() and max(ranks[t] for t in targets)<ranks[q])[0]]
 for a in selected:
  for t in buckets[a]:edges.append([ids[q],a,ids[t]])
allproof={'decision':'WIN','states':nodes,'strategy_edges':edges};domain_result=model.certificate(allproof,seen,ranks)
adj={i:set() for i in ids.values()}
for a,event,b in edges:adj[a].add(b)
reach={ids[q] for q in model.roots};todo=deque(reach)
while todo:
 for t in adj[todo.popleft()]-reach:reach.add(t);todo.append(t)
assert len(reach)<len(nodes)
# Explicit residual whose bad-prefix language is identical but whose latent resets do not commute.
residual_input=copy.deepcopy(base);req=residual_input['requirements'][0];test=req['tester'];delta={(q,a):t for q,a,t in test['changes']};rho=[c['transfer_action'] for c in residual_input['components']]
res={'states':[q+'|'+str(x) for q in test['states'] for x in [0,1]],'initial':test['initial']+'|0','errors':[q+'|'+str(x) for q in test['errors'] for x in [0,1]],'alphabet':test['alphabet'],'changes':[]}
for q in test['states']:
 for x in [0,1]:
  for a in test['alphabet']:
   nx=0 if a==rho[0] else 1 if a==rho[1] else x;res['changes'].append([q+'|'+str(x),a,delta.get((q,a),q)+'|'+str(nx)])
req['activation']['residual']=res
for entry in req['activation']['entries']:entry['residual_state']=entry['tester_state']+'|0'
mod.Model(residual_input,'none');mod.Model(residual_input,'transfers')
rd={(q,a):t for q,a,t in res['changes']};q=res['initial'];ab=rd[rd[q,rho[0]],rho[1]];ba=rd[rd[q,rho[1]],rho[0]];assert ab!=ba
explicit=sum('residual' in r.get('activation',{}) for family in ['rolling/v1','canary/v1','policy/v2','db_rolling/v2','rolling_audit/v1'] for f in (E6/family/'inputs').glob('*.json') for r in json.loads(f.read_text())['requirements'])
report={'reviewed_sha256':hashlib.sha256(source).hexdigest(),'status':'LIMITATIONS_CONFIRMED','current_data_explicit_residual_automata':explicit,'findings':[{'id':'goal_outgoing','reproducer':'Added goal serve_1 self-loop to actual Rolling WIN certificate; checker accepts despite rank 0 goal needing no outgoing mid edge','python_result':goal_result,'fixed_E1_rule':'OtfDucsCertificateChecker.java:70 rejects Goal has a mid-mode transition'},{'id':'certificate_exact_domain','reproducer':'Locally decreasing certificate on all 8 independent winning states is accepted, but selected root-reachable policy has only 5 states','nodes':len(nodes),'strategy_reachable':len(reach),'python_result':domain_result,'fixed_E1_rule':'OtfDucsCertificateChecker.java:132 requires exact strategy-reachable rank domain'},{'id':'exact_bucket_policy_shape','reproducer':'Code uses UC subset and permits several C buckets; fixed E1 requires exactly all UC and no C, or exactly one C when UC absent','demonstration':'static source comparison; current solver proofs already obey E1 canonical shape'},{'id':'residual_commutation','reproducer':'Explicit residual has same bad-prefix language as tester but two safe latent resets do not commute; independent Model accepts transfers while E1 ContractMerge rejects all-state residual noncommutation','rho1_then_rho2':ab,'rho2_then_rho1':ba,'current_campaign_impact':'No explicit residual automata in the five audited families; default residual equals tester, whose commutation is checked'}],'positive_checks':['Atomic group stop removal precedes remaining-tester observation; all starts use pre-event physical initializer and do not observe own start.','Goal correctly excludes physically enabled UC before monitor safety/terminalization.','Ordinary alphabet ownership, nonowner stutter, synchronization blocking and set-valued Cartesian transfer semantics agree for the finite JSON frontend.','LOSS closure correctly requires some losing UC outcome, or a losing outcome in every C bucket; root intersection is sufficient for global multi-root LOSS.','The full independent attractor is separate from certificate validation, so these certificate strictness gaps do not establish any wrong reported decision.']}
for name,value in [('independent_v1_review.json',report),('counter_goal_outgoing.json',mutated),('counter_extra_domain.json',allproof),('counter_residual_noncommuting.json',residual_input)]:
 with (OUT/name).open('x') as f:json.dump(value,f,indent=2);f.write('\n')
print(json.dumps(report,indent=2))
