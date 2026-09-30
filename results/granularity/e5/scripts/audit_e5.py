#!/usr/bin/env python3
"""Lightweight provenance/schedule audit, no synthesis invocation."""
import sys,datetime as dt,subprocess
sys.dont_write_bytecode=True
from e5_common import *
from analyze_e5 import collect

def main():
    summary=collect();config=read_json(CONFIG);plan=list(jobs(config));frozen=read_json(RAW/'series_manifest.json');errors=[]
    if frozen['config']!=config:errors.append('current config differs from frozen config')
    if frozen['schedule']!=[j['job_id'] for j in plan]:errors.append('schedule mismatch')
    if sha256(ROOT/config['classpath'])!=frozen['jar']['jar_sha256']:errors.append('JAR hash mismatch')
    head=subprocess.check_output(['git','-C',str(E5/'source'),'rev-parse','HEAD'],text=True).strip()
    if head!=frozen['jar']['source_commit']:errors.append('source commit mismatch')
    if subprocess.run(['git','-C',str(E5/'source'),'diff','--quiet','HEAD','--']).returncode:errors.append('tracked source changed')
    for inp in frozen['inputs']:
        if sha256(ROOT/inp['source_path'])!=inp['source_sha256'] or sha256(ROOT/inp['copy_path'])!=inp['copy_sha256']:errors.append('input hash mismatch '+inp['model_id'])
    prev_finish=None;seen_gap=False;started=0;completed=0
    for i,job in enumerate(plan,1):
        path=RAW/ATTEMPT/'runs'/job['job_id']/'meta.json'
        if not path.exists():seen_gap=True;continue
        if seen_gap:errors.append('started later cell after unstarted gap '+job['job_id'])
        meta=read_json(path);started+=1;start=dt.datetime.fromisoformat(meta['started_utc'])
        if start>=dt.datetime.fromisoformat(config['start_cutoff']):errors.append('trial started after cutoff '+job['job_id'])
        if prev_finish and start<prev_finish:errors.append('overlapping trials '+job['job_id'])
        if meta.get('completed'):
            completed+=1;prev_finish=dt.datetime.fromisoformat(meta['finished_utc'])
        else:seen_gap=True
    actual={p.parent.name for p in (RAW/ATTEMPT/'runs').glob('*/meta.json')}
    if not actual<={j['job_id'] for j in plan}:errors.append('unexpected raw job')
    rows=list(csv.DictReader((E5/'tables/results.csv').open()));pairs=list(csv.DictReader((E5/'tables/pairs.csv').open()));models=list(csv.DictReader((E5/'tables/models.csv').open()))
    if (len(rows),len(pairs),len(models))!=(54,18,9):errors.append('CSV cardinality mismatch')
    if [r['method_id'] for r in rows]!=[j['method_id'] for j in plan]:errors.append('CSV order mismatch')
    inputsha={r['model_id']:r['copy_sha256'] for r in frozen['inputs']}
    for row in rows:
        if row['original_input_sha256']!=inputsha[row['model_id']]:errors.append('baseline input differs '+row['model_id'])
    if summary['validation_errors'] or summary['baseline_validation_errors'] or summary['domain_comparisons']['failed'] or summary['df_lazy_mismatches']:errors.append('derived validation failures present')
    result=dict(status='FAIL' if errors else 'PASS',provisional=summary['provisional'],scheduled=54,started=started,completed=completed,errors=errors,jar_sha256=frozen['jar']['jar_sha256'],source_commit=head,input_count=len(frozen['inputs']),csv_rows={'results':len(rows),'pairs':len(pairs),'models':len(models)},raw_selection='All schedule cells; no retries or extra cells; existing none baseline cited separately.')
    write_json(E5/'tables/integrity_check.json',result);print(json.dumps(result,indent=2))
    return bool(errors)

if __name__=='__main__':raise SystemExit(main())
