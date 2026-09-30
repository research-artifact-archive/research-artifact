#!/usr/bin/env python3
"""Source-level obstruction check, kept distinct from a solver verdict/certificate."""
import hashlib,itertools,json,re
from pathlib import Path
P=Path(__file__).resolve().parent;f=P/'v2/inputs/ProductionCell_Arms2_Calibration.lts';source=f.read_text()
old=re.search(r'PRODUCTION_CELL_OLD\(I=1\) = .*?TRASHED = \(stampOk\[I\] -> ARM\)\.',source,re.S)[0]
assert 'calibrated' not in old and 'beginCalibration' not in old
for i in [1,2]:
 relation=re.search(r'relation R_PRODUCTION_CELL_'+str(i)+r'_CAL = \{.*?\}',source,re.S)[0]
 targets=re.findall(r'-> ([A-Z_]+)(?:\[k\])?@PRODUCTION_CELL_NEW_CAL',relation)
 assert len(targets)==7 and all(t.startswith('CAL_') for t in targets)
 assert f'fluent CalReady{i} = <calibrated[{i}],{{reconfigure_PRODUCTION_CELL_{i},beginCalibration[{i}]}}> initially 1' in source
assert 'ltl_property R_CAL_READY = [](CalReady1 || CalReady2)' in source
assert 'transition = R_CAL_READY,' in source
# The source fluent semantics sets each readiness bit to false at its transfer.
# Safety error is absorbing; merging applies both commuting transfer observations.
def step(q,i):
 if q=='ERROR':return q
 bits=list(q);bits[i]=False
 return tuple(bits) if any(bits) else 'ERROR'
checks=[]
for bits in itertools.product([False,True],repeat=2):
 if not any(bits):continue
 a=step(step(bits,0),1);b=step(step(bits,1),0);assert a==b=='ERROR';checks.append({'initial':bits,'rho1_then_rho2':a,'rho2_then_rho1':b})
r={'status':'PASS','scope':'Source-level structural obstruction, NOT a completed E1 decision or a persisted E1 LOSS certificate','input_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'checks':checks,'argument':['Before the unique merged transfer both physical components remain OLD, so their active old LTSs cannot execute calibrated or beginCalibration.','The interval starts with both ready bits true. Old ordinary actions and stop/start events do not change these bits.','The merged transfer applies both local mappings, entering two CAL states, and both transfer observations set the interval ready bits false. Either observation order reaches absorbing safety error.','Strong completion requires the pending transfer to be completed; the all-new goal cannot be reached without this unsafe event.'],'measurement_separation':'A measured timeout remains TO even when this source-level argument holds.'}
with (P/'v2/validation/merge_obstruction.json').open('x') as out:json.dump(r,out,indent=2);out.write('\n')
print({'status':r['status'],'scope':r['scope']})
