#!/usr/bin/env python3
"""Read-only physical readiness crosscheck using the separate compiled plant probe."""
import hashlib,json,re
from collections import Counter
from pathlib import Path
P=Path(__file__).resolve().parent;V=P/'v2'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
plant=V/'preflight/cal_new_plant/transitions.txt';text=plant.read_text();cal=set();known=set()
for src,body in re.findall(r'Q(\d+)\s*=\s*\((.*?)\)(?:,|\.|\+)',text,re.S):
 known.add(int(src))
 if 'calibrated[1]' in body:cal.add(int(src))
assert len(known)==14 and len(cal)==7
proof=V/'validation/export/lazy_none/certificate.json';a=json.loads(proof.read_text());counts=Counter()
for s in a['states']:
 for version,raw,observers in s['physical']:
  if version=='NEW':assert raw in known
 computed=sum(version=='OLD' or raw not in cal for version,raw,observers in s['physical'])
 assert computed==s['physical_operational_arms'] and computed>=1
 counts[computed]+=1
r={'status':'PASS','scope':'Independent classification from separate compiled calibration-plant probe, applied to all exported certificate physical raw-state IDs; fixed E1 semantic checker separately verifies the raw-state/observer semantics.','certificate_states':len(a['states']),'operational_arm_counts':dict(sorted(counts.items())),'calibration_raw_states':sorted(cal),'plant_probe_sha256':sha(plant),'certificate_sha256':sha(proof)}
with (V/'validation/physical_certificate_crosscheck.json').open('x') as f:json.dump(r,f,indent=2);f.write('\n')
print(r)
