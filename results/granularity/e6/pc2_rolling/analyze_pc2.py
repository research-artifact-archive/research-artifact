#!/usr/bin/env python3
"""Fresh collection only, preserving incomplete and adverse one-shot results."""
import csv,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;V=HERE/'v2'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def metrics(p):
 if not p.exists():return {}
 lines=p.read_text(errors='replace').splitlines();heads=[i for i,s in enumerate(lines) if s.startswith('mode,result,solver_status,verification_status,')]
 if not heads:return {}
 start=heads[-1];tail=[]
 for s in lines[start:]:
  if not s or s.startswith('='):break
  tail.append(s)
 return {r['metric_key']:r['value'] for r in csv.DictReader(tail)}
manifest=read(V/'build/frozen_manifest.json');issues=[]
for f,h in manifest['files'].items():
 if sha(HERE/f)!=h:issues.append('Frozen file changed: '+f)
rows=[]
for name in manifest['schedule']:
 p=V/'raw'/name;inv=read(p/'invocation.json') if (p/'invocation.json').exists() else {};end=read(p/'completion.json') if (p/'completion.json').exists() else None;m=metrics(p/'output.txt');d=read(p/'certificate_summary.json') if (p/'certificate_summary.json').exists() else None
 status='NOT_RUN' if (p/'not_run.json').exists() else ('RUNNING' if inv else 'NOT_STARTED');reason=''
 if end:
  if end['timed_out']:status='TO';reason='Whole JVM reached fixed 1200-second limit; no completed decision/certificate.'
  else:status={0:'WIN',6:'LOSS',5:'OOM',7:'INVALID_CERTIFICATE',8:'INVALID_INPUT'}.get(end['exit_code'],'ERROR');reason=m.get('failure_reason','')
  for f,h in end['files'].items():
   if sha(p/f)!=h:issues.append(name+': raw hash mismatch '+f)
 if status in ['WIN','LOSS']:
  if not d or d['decision']!=status:issues.append(name+': missing/mismatched retained certificate diagnostic')
  if m.get('revised_decision')!=('realizable' if status=='WIN' else 'unrealizable'):issues.append(name+': CLI decision mismatch')
  for key,metric in [('states_discovered','revised_semantic_states_discovered'),('successor_queries','revised_successor_oracle_calls_cumulative'),('materialized_transitions','revised_materialized_transition_outcomes_cumulative')]:
   if str(d[key])!=m.get(metric):issues.append(name+': '+key+' mismatch')
  if status=='WIN' and str(d['worst_completion_rank'])!=m.get('revised_worst_completion_rank'):issues.append(name+': rank mismatch')
  if status=='LOSS' and str(d['losing_region_states'])!=m.get('revised_losing_region_states'):issues.append(name+': losing region mismatch')
  reason='Existing E1 certificate and Link PASS.' if status=='WIN' else d['loss_reason']
 completed=status in ['WIN','LOSS']
 row={'job_id':name,'model':'PC2-Calibration','solver':'direct_full' if name.startswith('direct_full') else 'lazy','merge':'transfers' if name=='lazy_transfers' else 'none','status':status,'states_discovered':d['states_discovered'] if completed else '', 'successor_queries':d['successor_queries'] if completed else '', 'materialized_transition_outcomes':d['materialized_transitions'] if completed else '', 'enabled_buckets':'','enabled_buckets_availability':'not directly recorded by fixed E1 CLI','worst_completion_rank':d.get('worst_completion_rank','') if completed else '', 'losing_region_states':d.get('losing_region_states','') if completed else '', 'certificate_states':d.get('certificate_states','') if completed else '', 'unsafe_region_states':d.get('unsafe_region_states','') if completed else '', 'initial_states_in_certificate':d.get('initial_states_in_region','') if completed else '', 'initial_states':d.get('initial_states','') if completed else '', 'preparation_seconds':float(m['revised_preparation_time'])/1000 if 'revised_preparation_time' in m else '', 'solve_and_internal_check_seconds':float(m['revised_solve_and_internal_check_time'])/1000 if 'revised_solve_and_internal_check_time' in m else '', 'diagnostic_seconds':d.get('diagnostic_seconds','') if completed else '', 'whole_jvm_seconds':end['wall_seconds'] if end else '', 'input_sha256':inv.get('input_sha256',''), 'jar_sha256':inv.get('jar_sha256',''), 'exit_code':end['exit_code'] if end else '', 'reason':reason,'raw_directory':str(p.relative_to(HERE))}
 rows.append(row)
(V/'tables').mkdir(exist_ok=True)
with (V/'tables/results.csv').open('w') as f:w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
report={'status':'PASS' if not issues else 'FAIL','terminal':sum(r['status'] not in ['NOT_STARTED','RUNNING'] for r in rows),'issues':issues,'statuses':{r['job_id']:r['status'] for r in rows},'scope':'Fresh postprocessing; absent/incomplete decisions retain blank state/rank/certificate metrics; fixed E1 CLI does not directly instrument distinct enabled buckets.'}
(V/'validation/raw_table_audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
