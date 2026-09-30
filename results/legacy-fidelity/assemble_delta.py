#!/usr/bin/env python3
"""Extend COPIES of the existing staged runner; never change the live bundle."""
from pathlib import Path
import difflib,shutil
HERE=Path(__file__).resolve().parent
XEON=HERE.parent/'rq3_xeon'
DELTA=HERE/'bundle_delta'
def change(s,a,b):
    assert a in s,a
    return s.replace(a,b)
def main():
    source=(XEON/'scripts/campaign.py').read_text();s=source
    s=change(s,"    if config.get('backend')!='synthetic_hub':return ORIGINAL_COMMAND(config,job,root,output,transitions)","""    if config.get('backend')=='published_mtsa':
        result=ORIGINAL_COMMAND(config,job,root,output,transitions)
        index=result.index('-cp')+1
        result[index]=os.pathsep.join([str(root/config['runner_classpath']),result[index]])
        return result
    if config.get('backend')!='synthetic_hub':return ORIGINAL_COMMAND(config,job,root,output,transitions)""")
    s=change(s,"if job['method_id']=='legacy_ducs' and row.get('output_path'):","if job['method_id'] in {'legacy_ducs','published_mtsa'} and row.get('output_path'):")
    marker="            row['legacy_peak_state_space_transitions']=values.get('peak_state_space_transitions','')"
    s=change(s,marker,marker+"""
            if config.get('backend')=='published_mtsa':
                row['solver_time_ms']=values.get('published_compile_compose_time_ms','')
                row['compile_compose_time_ms']=values.get('published_compile_compose_time_ms','')
                row['reference_tool']='lab-maintained build of the original DUCS source'
                if status in GOOD and (parsed['errors'] or row.get('solver_status')!={'SUCCESS':'REALIZABLE','UNREALIZABLE':'UNREALIZABLE'}[status]):
                    row['invalid']=True;row['invalid_reason']='published adapter decision/CSV mismatch'
""")
    s=change(s,"if job['method_id']!='legacy_ducs':","if job['method_id'] not in {'legacy_ducs','published_mtsa'}:")
    s=change(s,"if row['method_id']!='legacy_ducs':instances", "if row['method_id'] not in {'legacy_ducs','published_mtsa'}:instances")
    s=change(s,"measurement_scope=('solver_only_synthetic'", "measurement_scope=('published_compile_and_compose' if config.get('backend')=='published_mtsa' else 'solver_only_synthetic'")
    s=change(s,"    stamp=time.strftime('%Y%m%d-%H%M%S')", """    if config.get('required_classpath_sha256') and common.sha256_file(ROOT/config['classpath'])!=config['required_classpath_sha256']:
        raise RuntimeError('Fixed synthesis JAR bytes differ')
    if config.get('runner_classpath') and common.sha256_file(ROOT/config['runner_classpath'])!=config['required_runner_sha256']:
        raise RuntimeError('Published adapter bytes differ')
    stamp=time.strftime('%Y%m%d-%H%M%S')""")
    s=change(s,"    env=common.environment_manifest(config,ROOT);env['physical_memory_bytes_portable']=ram", """    env=common.environment_manifest(config,ROOT);env['physical_memory_bytes_portable']=ram
    if config.get('runner_classpath'):env['runner_module']=common.file_digest(ROOT/config['runner_classpath'])""")
    s=change(s,"'python_version','model_input_bytes'):","'python_version','model_input_bytes','runner_module'):")
    scripts=DELTA/'scripts';scripts.mkdir(parents=True,exist_ok=True)
    (scripts/'campaign.py').write_text(s)
    (HERE/'campaign.diff').write_text(''.join(difflib.unified_diff(source.splitlines(True),s.splitlines(True),fromfile='existing/scripts/campaign.py',tofile='delta/scripts/campaign.py')))
    for file in ['process_probe.py','PortableProcessProbe.java','check_orchestration.py']:
        shutil.copyfile(XEON/'scripts'/file,scripts/file)
    runtime=DELTA/'Implementation/Experiment/FSE2027/scripts';runtime.mkdir(parents=True,exist_ok=True)
    for file in ['harness_common.py','run_experiment.py','collect_results.py']:
        shutil.copyfile(XEON/'runtime'/file,runtime/file)
    old=(XEON/'run-all.ps1').read_text();new=change(old,"    'rq3'             = @('stage1','stage2','collect')","    'legacy_fidelity_published' = @('stage1','stage2','collect')\n    'legacy_fidelity_fork' = @('stage1','stage2','collect')\n    'rq3'             = @('stage1','stage2','collect')")
    new=change(new,"Write-Host '=== Summary ==='","""if ($Campaigns -contains 'legacy_fidelity_published' -or $Campaigns -contains 'legacy_fidelity_fork') {
    & $PythonPath (Join-Path $PSScriptRoot 'scripts\\collect_legacy_fidelity.py') --root $PSScriptRoot
    if ($LASTEXITCODE -ne 0) { Fail 'Legacy fidelity comparison collection failed; raw preserved.' }
}
Write-Host '=== Summary ==='""")
    shutil.copyfile(HERE/'collect_legacy_fidelity.py',scripts/'collect_legacy_fidelity.py')
    (DELTA/'run-all.ps1').write_text(new)
    (HERE/'run-all.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='existing/run-all.ps1',tofile='delta/run-all.ps1')))
    print('Copied runner supports both reference tools; existing scripts/bundle unchanged.')
if __name__=='__main__':main()
