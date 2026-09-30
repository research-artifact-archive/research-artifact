#!/usr/bin/env python3
"""Three fresh Mac trials plus the already completed one-shot V cell."""
from pathlib import Path
import importlib.util,json,subprocess,sys
HERE=Path(__file__).resolve().parent
DELTA=HERE/'bundle_delta'
sys.path.insert(0,str(DELTA/'scripts'))
import campaign
common=campaign.common

def main():
    java=subprocess.check_output(['/usr/libexec/java_home','-v','17'],text=True).strip()+'/bin/java'
    for tool in (['published'] if '--adapter-fix' in sys.argv else ['published','fork']):
        raw=HERE/'raw'/('mac_pilot_'+tool+('_adapter_fix' if '--adapter-fix' in sys.argv else ''))
        if (raw/'runs').exists():raise RuntimeError('Pilot already started; no automatic reruns: '+str(raw))
        cfg=json.loads((DELTA/'configs'/('legacy_fidelity_'+tool+'.json')).read_text())
        cfg.update(experiment_id='legacy-fidelity-mac-pilot-'+tool,repetitions=1,java_heap='16g',timeout_seconds=1200,java=java,minimum_physical_memory_gib=20,minimum_free_disk_gib=5)
        cfg['models']=[m for m in cfg['models'] if m['id'].startswith('industry_') and (tool=='published' or m['id']=='industry_supplied')]
        if tool=='fork':cfg['classpath']=str((HERE.parent/'rq3_xeon/bundle'/cfg['classpath']).resolve())
        assert common.sha256_file(DELTA/cfg['classpath'])==cfg['required_classpath_sha256']
        common.validate_config(cfg);plan=common.build_plan(cfg)
        config_sha=campaign.initialize(cfg,raw,plan)
        env=common.environment_manifest(cfg,DELTA);env['measurement_use']='Mac correctness-only pilot; not Xeon results or paper performance'
        if tool=='published':env['runner_module']=common.file_digest(DELTA/cfg['runner_classpath'])
        common.atomic_write_json(raw/'environment.json',env)
        envsha=common.execution_environment_fingerprint(env)['sha256']
        for job in plan['jobs']:
            print('START',tool,job['model_id'],flush=True)
            result=campaign.runner.run_job(cfg,config_sha,plan['plan_sha256'],DELTA,raw,job,envsha)
            print('END',result['status'],flush=True)
        campaign.summarize(cfg,raw,plan)
    print('V reused by reference: raw/mac_v_industry_empty; no rerun.',flush=True)
if __name__=='__main__':main()
