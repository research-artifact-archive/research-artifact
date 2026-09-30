#!/usr/bin/env python3
"""Decision V: exactly one frozen-fork JVM; correctness only."""
from pathlib import Path
import copy,difflib,hashlib,json,subprocess,sys
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'rq3_xeon'
sys.path.insert(0,str(BASE/'runtime'))
import harness_common as common
import run_experiment as runner
import collect_results as collector

def main():
    raw=HERE/'raw/mac_v_industry_empty'
    if (raw/'runs').exists():raise RuntimeError('V already started; no rerun permitted')
    raw.mkdir(parents=True,exist_ok=True)
    source=HERE.parent/'industry_r1_legacy_monolithic_check/2017-TSE-Industry_T_Empty_active.lts'
    text=source.read_text();lines=text.splitlines(keepends=True);n=0
    for i,line in enumerate(lines):
        if line.strip().startswith('fluent ') and 'beginUpdate' in line:
            lines[i]=line.replace('beginUpdate','hotSwapIn');n+=1
    assert n==3,n
    dest=HERE/'inputs/v/Industry_T_Empty_fork.lts';dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(''.join(lines))
    (dest.with_suffix('.diff')).write_text(''.join(difflib.unified_diff(text.splitlines(True),lines,fromfile=source.name,tofile=dest.name)))
    jar=BASE/'bundle/Implementation/Source Code/maven-root/mtsa/target/mtsa-1.0-SNAPSHOT.jar'
    assert common.sha256_file(jar)=='fbdc25f58d5441ed906d408a94b7414c9d9c3ed35e2ebce22d9751729967ba07'
    cfg=json.loads((BASE/'configs/rq3.json').read_text())
    cfg.update(experiment_id='legacy-fidelity-V-correctness-only',repetitions=1,java_heap='16g',timeout_seconds=1200,minimum_physical_memory_gib=20,minimum_free_disk_gib=5,
        java=subprocess.check_output(['/usr/libexec/java_home','-v','17'],text=True).strip()+'/bin/java',classpath=str(jar.resolve()))
    cfg['models']=[{'id':'industry_empty','path':str(dest.resolve()),'method_ids':['legacy_ducs']}]
    cfg['targets']=[{'id':'empty','suffix':''}]
    cfg['methods']=[m for m in cfg['methods'] if m['id']=='legacy_ducs'];cfg['methods'][0]['target_template']='UPDATE_CONTROLLER{suffix}'
    common.atomic_write_json(raw/'config.json',cfg);plan=common.build_plan(cfg);assert len(plan['jobs'])==1
    common.atomic_write_json(raw/'plan.json',plan)
    env=common.environment_manifest(cfg,BASE/'bundle');env['measurement_use']='Correctness only. Mac time and RSS excluded from paper performance.'
    common.atomic_write_json(raw/'environment.json',env)
    result=runner.run_job(cfg,common.sha256_file(raw/'config.json'),plan['plan_sha256'],BASE/'bundle',raw,plan['jobs'][0],common.execution_environment_fingerprint(env)['sha256'])
    print(json.dumps(result,indent=2))
    rows,metrics,counts=collector.collect(raw);common.csv_write(raw/'raw_runs.csv',collector.RAW_FIELDS,rows)
    if metrics:common.csv_write(raw/'metrics_long.csv',list(dict.fromkeys(k for r in metrics for k in r)),metrics)
    print('COUNTS',counts)
if __name__=='__main__':main()
