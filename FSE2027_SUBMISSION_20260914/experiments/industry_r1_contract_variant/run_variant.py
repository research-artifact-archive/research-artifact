#!/usr/bin/env python3
"""One explicitly authorized contract variant, correctness only, fixed JVM build.

The only changed input conditions are the three R1 bans, each exempting the
same existing label validateGF1. The physical process and old/new endpoint
specifications remain unchanged. This assumes gate-form validation is acceptable
during the stop/start gap; business acceptability is outside this experiment.

Model justification: validateGF1 enters GF1RESPONSE. Its three uncontrollable
responses adjustGF1/approveGF1/cancelGF1 all reset NewTORDone and DSD1Done.
They terminate at GATEFORM1_OLD/NEW. No fairness assumption on DSD1 approval is
added. The original contract's LOSS and all original benchmark results persist.
"""
from pathlib import Path
import difflib
import json
import subprocess
import sys

HERE = Path(__file__).resolve().parent
XEON = HERE.parent / 'rq3_xeon'
RAW = HERE / 'raw'


def resolve_layout(here=HERE):
    """Use the local frozen bundle or the self-contained distribution root."""
    xeon = here.parent / 'rq3_xeon'
    model = Path('Implementation/Experiment/Models/Industry_FG.lts')
    for root in (xeon / 'bundle', here.parents[2]):
        if not (root / model).is_file():
            continue
        for scripts in (xeon / 'runtime', root / 'Implementation/Experiment/FSE2027/scripts'):
            if all((scripts / name).is_file() for name in
                   ('harness_common.py', 'run_experiment.py', 'collect_results.py')):
                return root, scripts
    raise FileNotFoundError('Neither the local frozen bundle nor the distribution model/harness layout is present')


ROOT, SCRIPTS = resolve_layout()
sys.path.insert(0, str(SCRIPTS))
import harness_common as common
import run_experiment as runner


def main():
    if (RAW / 'runs').exists():
        raise RuntimeError('Variant has already started; preserve the outcome and do not retry')
    RAW.mkdir(parents=True, exist_ok=True)
    inputs = HERE / 'inputs'
    inputs.mkdir(exist_ok=True)
    original = ROOT / 'Implementation/Experiment/Models/Industry_FG.lts'
    source = original.read_text()
    variant = source
    for requirement in ('TOR_POLICY', 'DSD1_POLICY', 'DO_NOT_SEND_TWICE'):
        before = ('ltl_property R1_P_NEW_' + requirement
                  + ' = [](AfterStopBeforeStart_P_NEW_' + requirement + ' -> !AnyAction)')
        after = before.replace('!AnyAction', '!(AnyAction && !validateGF1)')
        assert variant.count(before) == 1, requirement
        variant = variant.replace(before, after)
    assert sum(a != b for a, b in zip(source.splitlines(), variant.splitlines())) == 3
    original_copy = inputs / 'Industry_FG.original.lts'
    original_copy.write_bytes(original.read_bytes())
    modified = inputs / 'Industry_FG_R1_allow_validateGF1.lts'
    modified.write_text(variant)
    (inputs / 'allow_validateGF1.diff').write_text(''.join(difflib.unified_diff(
        source.splitlines(True), variant.splitlines(True),
        fromfile=original_copy.name, tofile=modified.name)))

    config = json.loads((XEON / 'configs/rq3.json').read_text())
    config.update(experiment_id='industry-r1-allow-validateGF1-correctness-only',
                  repetitions=1, java_heap='16g', timeout_seconds=3600,
                  minimum_physical_memory_gib=20, minimum_free_disk_gib=5,
                  java=subprocess.check_output(['/usr/libexec/java_home', '-v', '17'],
                                               text=True).strip() + '/bin/java')
    config['models'] = [dict(id='industry', path=str(modified), method_ids=['fg_ducs_otf'])]
    config['targets'] = [target for target in config['targets'] if target['id'] == 'r1']
    method = next(m for m in config['methods'] if m['id'] == 'fg_ducs_otf')
    method['jvm_properties'].update({
        'mtsa.revised.otf.independentVerification': 'true',
        'mtsa.revised.otf.independentVerificationMode': 'exhaustive',
        'mtsa.revised.otf.independentStateLimit': '1000000',
        'mtsa.revised.otf.independentQueryLimit': '20000000'})
    common.validate_config(config)
    common.atomic_write_json(RAW / 'config.json', config)
    plan = common.build_plan(config)
    assert len(plan['jobs']) == 1
    common.atomic_write_json(RAW / 'plan.json', plan)
    environment = common.environment_manifest(config, ROOT)
    baseline = json.loads((XEON / 'raw/industry-r1-independent/environment.json').read_text())
    if environment['classpath'].get('sha256') != baseline['classpath']['sha256']:
        raise RuntimeError('The exact frozen campaign JAR is required; a missing or rebuilt JAR must not replace it')
    environment['measurement_use'] = 'correctness_only; not a performance measurement'
    environment['contract_change'] = 'Only validateGF1 is exempted from the three R1 normal-action bans'
    environment['business_assumption'] = 'Gate-form validation is acceptable during the update gap'
    common.atomic_write_json(RAW / 'environment.json', environment)
    original_command = runner.build_command

    def command(*args, **kwargs):
        return original_command(*args, **kwargs) + ['--game-output', str(RAW / 'independent-game.json')]

    runner.build_command = command
    print('START one variant / one JVM / 16g / 3600s / independent exhaustive check enabled', flush=True)
    result = runner.run_job(config, common.sha256_file(RAW / 'config.json'), plan['plan_sha256'],
                            ROOT, RAW, plan['jobs'][0],
                            common.execution_environment_fingerprint(environment)['sha256'])
    print('END ' + json.dumps({k: result.get(k) for k in
                              ['status', 'exit_code', 'completed', 'timed_out']}), flush=True)
    # Collection only; this process cannot launch any additional experiment JVM.
    collected = subprocess.run([sys.executable, str(SCRIPTS / 'collect_results.py'),
                                '--campaign', str(RAW), '--strict-complete'],
                               capture_output=True, text=True)
    (RAW / 'collection.log').write_text(collected.stdout + collected.stderr)
    if collected.returncode:
        raise RuntimeError('Collection failed; preserve logs and do not repeat the JVM')
    print('COLLECTION ' + collected.stdout, flush=True)


if __name__ == '__main__':
    main()
