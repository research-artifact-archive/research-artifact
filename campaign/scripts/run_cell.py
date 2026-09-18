#!/usr/bin/env python3
"""Run a separate, single-cell local example using the campaign's original runner."""
from pathlib import Path
import argparse
import copy
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / 'Implementation/Experiment/FSE2027/scripts'
sys.path.insert(0, str(SCRIPTS))
import harness_common as common
import run_experiment as runner


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', choices=['gsm', 'metasocket'], default='gsm')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--java', default='java')
    parser.add_argument('--plan-only', action='store_true')
    args = parser.parse_args()
    output = args.output.resolve()
    output.relative_to(ROOT)
    if output.exists():
        raise FileExistsError('Choose a fresh output directory: ' + str(output))
    config = common.load_config(ROOT / 'campaign/configs/rq3.json')
    original = common.build_plan(config)
    jobs = [j for j in original['jobs'] if j['model_id'] == args.model
            and j['target_id'] == 'base' and j['method_id'] == 'fg_ducs_otf' and j['repetition'] == 1]
    if len(jobs) != 1:
        raise ValueError('Expected exactly one matching frozen-plan cell')
    job = copy.deepcopy(jobs[0])
    config.update(java=args.java, java_heap='4g', timeout_seconds=60, repetitions=1,
                  experiment_id='local-' + args.model + '-base', results_root=output.relative_to(ROOT).as_posix())
    config['models'] = [dict(next(m for m in config['models'] if m['id'] == args.model), method_ids=['fg_ducs_otf'])]
    config['targets'] = [t for t in config['targets'] if t['id'] == 'base']
    local_plan = common.build_plan(config)
    if len(local_plan['jobs']) != 1:
        raise ValueError('Local plan must contain one trial')
    job = local_plan['jobs'][0]
    config.pop('host_requirements', None)
    output.mkdir(parents=True, exist_ok=False)
    config_path = output / 'local-example-config.json'
    config_path.write_text(json.dumps(config, indent=2) + '\n')
    plan = dict(scope='separate local example; not a published measurement',
                original_plan_sha256=original['plan_sha256'], jobs=[job], heap='4g', timeout_seconds=60)
    (output / 'local-example-plan.json').write_text(json.dumps(plan, indent=2) + '\n')
    command = runner.build_command(config, job, ROOT, output / 'output.txt', output / 'transitions.txt')
    print(json.dumps(dict(model=args.model, command=command, plan_only=args.plan_only), indent=2))
    if args.plan_only:
        return
    if not (ROOT / config['classpath']).is_file():
        raise FileNotFoundError('Build the JAR before running the example')
    if shutil.which(args.java) is None:
        raise FileNotFoundError('Java executable not found: ' + args.java)
    env = common.environment_manifest(config, ROOT)
    common.atomic_write_json(output / 'environment.json', env)
    result = runner.run_job(config, common.file_digest(config_path)['sha256'],
                            local_plan['plan_sha256'], ROOT, output, job,
                            common.file_digest(output / 'environment.json')['sha256'])
    print(json.dumps(dict(status=result['status'], elapsed_seconds=result['elapsed_monotonic_seconds'])))
    if result['status'] not in {'SUCCESS', 'UNREALIZABLE'}:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
