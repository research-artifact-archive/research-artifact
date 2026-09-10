from pathlib import Path
import json,hashlib,datetime
D=Path(__file__).resolve().parent
families=[('root',[],'alternate'),('leaf',['short'],'alternate'),('shallow',['driver','cache','entry','leaf'],'alternate'),('deep16',[f'node{i:02d}' for i in range(16)],'alternate'),('external',[c*n for c,n in zip('abcd',[39,40,127,255])],'replacement'),('transient',['bb','c'],'aaaa'),('deep80',[f'n{i:02d}' for i in range(80)],'alternate'),('shrink',['long_name_'*5,'c'],'z')]
caps=[1,2,8,32,128,4096]
profiles=[dict(name='clean',gates=0,pre=0,mid=0,late=0,kind=0),dict(name='first',gates=1,pre=0,mid=0,late=0,kind=0),dict(name='both',gates=3,pre=0,mid=0,late=0,kind=0),dict(name='unrelated',gates=3,pre=0,mid=0,late=0,kind=1),dict(name='pre_and_first',gates=1,pre=1,mid=0,late=0,kind=0),dict(name='mid_parent',gates=0,pre=0,mid=1,late=0,kind=0),dict(name='ancestor',gates=3,pre=0,mid=0,late=0,kind=2),dict(name='late',gates=0,pre=0,mid=0,late=1,kind=0)]
inputs=[]
for family,(_,names,alt) in enumerate(families):
 for cap in caps:
  for profile in range(len(profiles)):
   for policy in range(4):inputs.append(dict(id=len(inputs),family=family,cap=cap,profile=profile,policy=policy,mutation=0,control=False))
for family,cap,profile,mutation in [(2,128,2,1),(2,128,1,2),(7,8,1,3),(5,8,5,4)]:inputs.append(dict(id=len(inputs),family=family,cap=cap,profile=profile,policy=1,mutation=mutation,control=True))
assert len(inputs)==1540
data=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),purpose='first exploratory actual-Linux semantic/resource matrix',families=[dict(name=n,components=cs,alternate=a) for n,cs,a in families],caps=caps,profiles=profiles,policies=['upstream','cached','all_locked','snapshot64'],rows=inputs,planned_valid=1536,planned_mutation_controls=4,expected_failure_controls=['ignore_second_validation','reuse_first_sequence','omit_buffer_restore','early_unvalidated_overflow'],notes=['All writer sections use actual lock_rename/d_exchange.','Unreachable requested gates remain explicit, not dropped.','Mid-parent gate runs on two guest CPUs without sleeping in RCU.','Kernel source-event counts; no native-time inference from TCG.'])
with(D/'INPUTS01.json').open('x') as f:json.dump(data,f,indent=2);f.write('\n')
lines=['/* SPDX-License-Identifier: GPL-2.0 */','/* Generated before the first exploratory research execution. */','struct dp_family { const char *name; unsigned int depth; const char *names[80]; const char *alternate; };','struct dp_profile { const char *name; unsigned int gates, pre, mid, late, kind; };','struct dp_case { unsigned int id, family, cap, profile, policy, mutation; bool control; };','static const struct dp_family dp_families[] = {']
for name,names,alt in families:lines.append('{'+json.dumps(name)+','+str(len(names))+',{'+','.join(json.dumps(s) for s in names)+'},'+json.dumps(alt)+'},')
lines+=['};','static const struct dp_profile dp_profiles[] = {']
for p in profiles:lines.append('{'+json.dumps(p['name'])+','+','.join(str(p[k]) for k in ['gates','pre','mid','late','kind'])+'},')
lines+=['};','static const struct dp_case dp_cases[] = {']
for row in inputs:lines.append('{'+','.join(str(row[k]) for k in ['id','family','cap','profile','policy','mutation'])+','+str(row['control']).lower()+'},')
lines+=['};','']
with(D/'implementation01/d_path_retry_inputs.h').open('x') as f:f.write('\n'.join(lines))
print(json.dumps(dict(planned=len(inputs),valid=1536,controls=4,input_sha256=hashlib.sha256((D/'INPUTS01.json').read_bytes()).hexdigest()),indent=2))
