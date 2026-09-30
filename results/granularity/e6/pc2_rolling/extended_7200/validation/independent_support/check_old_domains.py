#!/usr/bin/env python3
"""Independent old source-plant/controller product; no E1 Post or JVM."""
import collections, hashlib, json, re
from pathlib import Path
HERE=Path(__file__).resolve().parent
PC2=HERE.parents[2]
SOURCE=PC2/'v2/inputs/ProductionCell_Arms2_Calibration.lts'
GRAPH=PC2/'v2/preflight/old_endpoint/transitions.txt'
source=SOURCE.read_text();assert re.search(r'const K = (\d+)',source)[1]=='1'
block=re.search(r'PRODUCTION_CELL_OLD\(I=1\) = .*?TRASHED = \(stampOk\[I\] -> ARM\)\.',source,re.S)[0]
plant={}
for name,decl,body in re.findall(r'([A-Z_]+)(\(I=1\)|\[k:Stages\])?\s*=\s*\((.*?)\)(?:,|\.)',block,re.S):
 state=name+('[1]' if decl=='[k:Stages]' else '');edges={}
 for clause in body.split('|'):
  clause=clause.strip();guard=re.match(r'when\((.*?)\)\s*',clause)
  if guard:
   assert guard[1] in ('k<K','k==K')
   if guard[1]=='k<K':continue
   clause=clause[guard.end():]
  action,target=[x.strip() for x in clause.split('->')]
  actions=action.strip('{}').split(',')
  for a in actions:edges[a.strip().replace('[I]','')]=target.replace('[k]','[1]')
 plant[state]=edges
assert len(plant)==7 and all(t in plant for es in plant.values() for t in es.values())
domains=[]
for i in (1,2):
 rel=re.search(r'relation R_PRODUCTION_CELL_'+str(i)+r'_CAL = \{(.*?)\}',source,re.S)[1]
 domain={x.replace('[k]','[1]') for x in re.findall(r'(\w+(?:\[k\])?)@PRODUCTION_CELL_OLD\('+str(i)+r'\)\s*=',rel)}
 assert domain==set(plant);domains.append(domain)
text=GRAPH.read_text();controller={}
for q,body in re.findall(r'Q(\d+)\s*=\s*\((.*?)\)(?:,|\.|\+)',text,re.S):
 edges={}
 for action,target in re.findall(r'([^|]+?)\s*->\s*Q(\d+)',body):
  action=action.strip();group=re.fullmatch(r'\{([^}]+)\}(.*)',action)
  for a in ([x.strip()+group[2] for x in group[1].split(',')] if group else [action]):edges[a]=int(target)
 controller[int(q)]=edges
assert len(controller)==int(re.search(r'States:\s*(\d+)',text)[1])
decl=re.search(r'set OldControllableActions = \{(.*?)\}',source,re.S)[1]
decl=re.sub(r'/\*.*?\*/','',decl,flags=re.S)
controlled={a.strip().replace('[Arms]','') for a in decl.split(',') if a.strip()}
q0=(0,'PRODUCTION_CELL_OLD','PRODUCTION_CELL_OLD');todo=collections.deque([q0]);seen={q0};all_edges=[]
while todo:
 c,x,y=todo.popleft()
 for action,nc in controller[c].items():
  verb,arm=re.fullmatch(r'(\w+)\[([12])\]',action).groups();i=int(arm)-1;physical=[x,y]
  assert verb in plant[physical[i]],(c,physical,action)
  physical[i]=plant[physical[i]][verb];target=(nc,*physical);all_edges.append(((c,x,y),action,target))
  if target not in seen:seen.add(target);todo.append(target)
records=[]
for c,x,y in sorted(seen):
 uc=[a for a in controller[c] if a.split('[')[0] not in controlled]
 records.append(dict(controller_state=c,physical=[x,y],component_domain_membership=[x in domains[0],y in domains[1]],
                     both_domains=x in domains[0] and y in domains[1],enabled_uc=sorted(uc),uc_quiescent=not uc))
result=dict(status='PASS',input_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
 controller_export_sha256=hashlib.sha256(GRAPH.read_bytes()).hexdigest(),script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
 local_plant_source='PRODUCTION_CELL_OLD(I=1), expanded directly from frozen FSP at K=1 for each arm',
 controller_source='SingleCompositionRunner target C_DRILL_POLISH_CLEAN; a synthesized endpoint controller with closed-loop behavior, not a separately supplied raw physical-plant graph',
 noncircular_scope='The physical LTS is independently parsed from FSP and synchronized with every exported controller transition. This validates the physical projection and reachability of the provided endpoint controller; it does not independently re-synthesize that controller or use E1 Post.',
 local_states=len(plant),domain_sizes=[len(x) for x in domains],reachable_product_states=len(seen),reachable_product_edges=len(all_edges),
 controller_states=len(controller),reachable_physical_tuples=len({x[1:] for x in seen}),
 both_domain_states=sum(r['both_domains'] for r in records),uc_quiescent_states=sum(r['uc_quiescent'] for r in records),
 both_domain_and_uc_quiescent_states=sum(r['both_domains'] and r['uc_quiescent'] for r in records),
 augmented_root_caution='The original update run records 126 initial embeddings. This 81-state census contains only endpoint-controller and raw physical coordinates, not adapter fluent/residual observations. No bijection to the 126 augmented roots is established by this check; the counts have different state signatures.',
 conclusion='Both raw transfer domains hold at every reachable old product state. This refutes an empty-joint-domain explanation; UC eligibility and safety of the joint CAL outcome remain separate questions.',
 records=records)
with (HERE/'old_domain_product.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in result.items() if k!='records'}))
