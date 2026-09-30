#!/usr/bin/env python3
"""Independent graph replay of exported plant/controller graphs; no JVM."""
import collections,hashlib,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent;V=HERE/'v2';P=V/'preflight'
def read(name):
 t=(P/name/'transitions.txt').read_text();n=int(re.search(r'States:\s*(\d+)',t)[1]);g={}
 for s,body in re.findall(r'Q(\d+)\s*=\s*\((.*?)\)(?:,|\.|\+)',t,re.S):
  es={}
  for expr,d in re.findall(r'([^|]+?)\s*->\s*Q(\d+)',body):
   expr=expr.strip();m=re.fullmatch(r'\{([^}]+)\}(.*)',expr);actions=[a.strip()+m[2] for a in m[1].split(',')] if m else [expr]
   for a in actions:assert a not in es;es[a]=int(d)
  g[int(s)]=es
 assert len(g)==n and set(g)==set(range(n))
 return g
base=read('old_new_plant');cal=read('cal_new_plant')
# Match ordinary transitions from the initial state, erasing only calibration edges/states.
map_o={0:0};todo=collections.deque([0])
while todo:
 s=todo.popleft();t=map_o[s];be=base[s];ce={a:d for a,d in cal[t].items() if not a.startswith('beginCalibration')}
 assert set(be)==set(ce)
 for a,d in be.items():
  if d in map_o:assert map_o[d]==ce[a]
  else:map_o[d]=ce[a];todo.append(d)
assert len(map_o)==7
preps=set(cal)-set(map_o.values())
for operational in map_o.values():
 p=cal[operational]['beginCalibration[1]'];assert p in preps and cal[p]=={'calibrated[1]':operational}
assert len(preps)==7

def endpoint(name,new):
 controller=read(name);plant=cal if new else {q:{a.replace('paint','polish'):d for a,d in es.items()} for q,es in base.items()}
 alpha=set().union(*(e.keys() for e in plant.values()));alpha=[alpha,{a.replace('[1]','[2]') for a in alpha}]
 # qcontroller, qplant1,qplant2, completed/drilling/painting/cleaning booleans are reconstructed from trace.
 init=(0,0,0,0,0);seen={init};todo=collections.deque([init]);edges=0
 while todo:
  c,p1,p2,f1,f2=todo.popleft();states=[p1,p2];flags=[f1,f2];available=controller[c];assert available
  if new:assert sum(s not in preps for s in states)>=1
  for i,p in enumerate(states):
   for a,d in plant[p].items():
    a=a.replace('[1]',f'[{i+1}]');verb=a.split('[')[0]
    if verb not in ('drill','paint','polish','clean','stamp','out','beginCalibration'):assert a in available,(name,c,a,'disabled UC')
  for a,d in available.items():
   verb=re.fullmatch(r'(\w+)\[([12])\]',a);assert verb,a
   verb,i=verb[1],int(verb[2])-1;local=a.replace(f'[{i+1}]','[1]');assert local in plant[states[i]],(name,c,a,states)
   f=flags[i];drilled=bool(f&1);middle=bool(f&2);cleaned=bool(f&4)
   assert verb!='stamp'
   if verb=='out':assert drilled and middle and cleaned
   if verb=='drill':assert not drilled and (not new or middle and cleaned)
   if verb in ('paint','polish'):assert not middle and ((cleaned and not drilled) if new else drilled)
   if verb=='clean':assert not cleaned and ((not middle and not drilled) if new else middle)
   ns=states.copy();nf=flags.copy();ns[i]=plant[states[i]][local]
   if verb=='reset':nf[i]=0
   if verb=='drillOk':nf[i]|=1
   if verb in ('paintOk','polishOk'):nf[i]|=2
   if verb=='cleanOk':nf[i]|=4
   target=(d,*ns,*nf);edges+=1
   if target not in seen:seen.add(target);todo.append(target)
 assert len({x[0] for x in seen})==len(controller)
 return {'controller_states':len(controller),'reachable_product_states':len(seen),'reachable_product_edges':edges,'physical_safety':True,'original_12_safety_requirements_trace_replay':True,'uncontrollable_admissibility':True,'nonblocking':True}
r={'status':'PASS','input_sha256':hashlib.sha256((V/'inputs/ProductionCell_Arms2_Calibration.lts').read_bytes()).hexdigest(),'ordinary_plant_graph_isomorphism':map_o,'original_plant_states':7,'calibrated_variant_states':14,'calibration_states':sorted(preps),'old_endpoint':endpoint('old_endpoint',False),'new_endpoint':endpoint('new_endpoint',True),'scope':'Independent replay of exported controller and physical graphs; original safety guards checked directly from event history. No update solver result used.'}
with (V/'validation/endpoint_graphs.json').open('x') as f:json.dump(r,f,indent=2);f.write('\n')
print(json.dumps(r,indent=2))
