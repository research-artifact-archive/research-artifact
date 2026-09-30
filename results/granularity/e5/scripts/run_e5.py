#!/usr/bin/env python3
"""Fixed 54-cell E5 schedule; one JVM, no retries, deadline-preserved missing cells."""
import argparse,platform,subprocess,sys
sys.dont_write_bytecode=True
from e5_common import *

def main():
    p=argparse.ArgumentParser();p.add_argument('--dry-run',action='store_true');args=p.parse_args()
    config=read_json(CONFIG);plan=list(jobs(config))
    assert len(plan)==54 and len({j['job_id'] for j in plan})==54
    assert all(j['solver']=='otf' for j in plan[:36]) and all(j['solver']=='direct_full' for j in plan[36:])
    assert config['timeout_seconds']==1200 and config['java_heap']=='32g' and config['repetitions']==config['parallel_trials']==1
    if args.dry_run:
        for i,job in enumerate(plan,1):print(i,job['job_id'])
        print('54 fixed cells; 36 Lazy followed by 18 DF; no JVM launched.');return
    if sys.platform!='darwin':raise RuntimeError('Mac series requires macOS')
    provenance=read_json(ROOT/config['jar_metadata']);jar=ROOT/config['classpath']
    assert sha256(jar)==provenance['jar_sha256'] and provenance['source_commit']
    source=E5/'source'
    assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==provenance['source_commit']
    assert subprocess.run(['git','-C',str(source),'diff','--quiet','HEAD','--']).returncode==0
    manifest=read_json(E5/'inputs/input_manifest.json')
    for item in manifest:
        assert sha256(ROOT/item['source_path'])==sha256(ROOT/item['copy_path'])==item['source_sha256']==item['copy_sha256']
    frozen={'config':config,'jar':provenance,'inputs':manifest,'schedule':[j['job_id'] for j in plan]}
    frozen_path=RAW/'series_manifest.json'
    if frozen_path.exists():assert read_json(frozen_path)==frozen,'Frozen plan changed'
    else:write_json(frozen_path,frozen)
    write_json(RAW/'environment.json',dict(system=platform.system(),machine=platform.machine(),python=platform.python_version(),java_version=subprocess.run([config['java'],'-version'],capture_output=True,text=True).stderr,captured_utc=utc_now().isoformat(),timing_scope='Mac reference only; no Xeon comparison'))
    from analyze_e5 import collect
    with execution_lock(RAW/'e5.lock'):
        for i,job in enumerate(plan,1):
            existing=RAW/ATTEMPT/'runs'/job['job_id']
            if existing.exists():
                if trial(job)['status']=='RUNNING':raise RuntimeError('Incomplete attempt retained; no restart allowed')
                continue
            if remaining(config['start_cutoff'])<=0 or remaining(config['deadline'])<1210:
                write_json(RAW/'deadline_reached.json',dict(utc=utc_now().isoformat(),next_job=job['job_id'],reason='No new trial at/after 15:39 JST; all unstarted cells retained as NOT_RUN_DEADLINE.'))
                break
            assert sha256(jar)==provenance['jar_sha256']
            assert sha256(ROOT/job['model_path'])==next(x['copy_sha256'] for x in manifest if x['model_id']==job['model_id'])
            print(f'[{i}/54] {job["job_id"]}',flush=True)
            run_trial(config,job,1200,ATTEMPT,RAW,ROOT,provenance)
            result=trial(job);print(f'  {result["decision"]}; states={result.get("states_discovered","")}; validation={result["validation_errors"]}',flush=True)
            collect()
        collect()
        assert sha256(jar)==provenance['jar_sha256']
        assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==provenance['source_commit']
        assert subprocess.run(['git','-C',str(source),'diff','--quiet','HEAD','--']).returncode==0
        for item in manifest:
            assert sha256(ROOT/item['source_path'])==sha256(ROOT/item['copy_path'])==item['source_sha256']
        write_json(RAW/'runner_finished.json',dict(finished_utc=utc_now().isoformat(),counts={s:sum(trial(j)['decision']==s for j in plan) for s in sorted({trial(j)['decision'] for j in plan})}))

if __name__=='__main__':main()
