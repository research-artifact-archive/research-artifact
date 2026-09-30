#!/usr/bin/env python3
"""Run the preregistered 24 E4-1 trials, preserving every attempt."""
import argparse
import platform
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[3]
ABL = HERE.parents[1] / 'ablation_20260928'
sys.path.insert(0, str(ABL / 'scripts'))
from ablation_common import csv_write, planned_jobs, read_json, sha256, write_json
from run_ablation import execution_lock, remaining, run_trial, utc_now

JAR_SHA = 'ff1e6b176f004ea85f1e99690a90388a6a4d24f44cd8d8e636fcd9337dcf67d5'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    config = read_json(HERE / 'configs/e4_1_mac.json')
    jobs = list(planned_jobs(config))
    assert len(jobs) == 24 and config['java_heap'] == '32g' and config['timeout_seconds'] == 1200
    assert config['repetitions'] == config['parallel_trials'] == 1
    provenance = read_json(HERE / 'inputs/jar.json')
    assert sha256(ROOT / config['classpath']) == provenance['jar_sha256'] == JAR_SHA
    for row in read_json(HERE / 'inputs/input_manifest.json'):
        assert sha256(ROOT / row['source_path']) == row['source_sha256']
        assert sha256(ROOT / row['copy_path']) == row['source_sha256'] == row['copy_sha256']
    if args.dry_run:
        print('Validated 24 jobs, eight identical copies, fixed E1 JAR; no JVM launched.')
        return
    assert sys.platform == 'darwin'
    active = subprocess.run(['ps', '-axo', 'pid=,comm=,args='], text=True, capture_output=True, check=True).stdout
    if any('SingleCompositionRunner' in line and '/java ' in line for line in active.splitlines()):
        raise RuntimeError('Another synthesis JVM is running; E4-1 must be serial with all campaigns')
    with execution_lock(HERE / 'raw/execution.lock'):
        write_json(HERE / 'raw/environment.json', dict(system=platform.system(), machine=platform.machine(),
                   java_version=subprocess.run([config['java'], '-version'], capture_output=True, text=True).stderr,
                   captured_utc=utc_now().isoformat(), timing_scope='No timing comparison; correctness witness only'))
        results = []
        for i, job in enumerate(jobs, 1):
            if remaining(config['deadline']) < 1210:
                print('Deadline: unstarted cells remain NOT_RUN.', flush=True)
                break
            print(f'[{i}/24] {job["job_id"]}', flush=True)
            result = run_trial(config, job, 1200, 'single_1200s', HERE / 'raw', ROOT, provenance)
            results.append(dict(model_id=job['model_id'], merge=job['merge'], **result))
            csv_write(HERE / 'raw/progress.csv', results, list(dict.fromkeys(k for r in results for k in r)))
            print(f'  {result["decision"]}, states={result.get("states_discovered", "")}', flush=True)
    subprocess.run([sys.executable, '-B', str(HERE / 'scripts/analyze_e4_1.py')], check=True, cwd=ROOT)


if __name__ == '__main__':
    main()
