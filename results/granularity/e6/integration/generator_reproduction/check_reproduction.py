#!/usr/bin/env python3
"""Read-only generator replay; every write is confined to this new directory."""
import contextlib
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import runpy
import sys
import traceback
from datetime import datetime
from zoneinfo import ZoneInfo

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
E6 = HERE.parents[1]
GENERATED = HERE / 'generated'
SERIES = {'rolling': 'v1', 'canary': 'v1', 'policy': 'v2', 'db_rolling': 'v2',
          'rolling_audit': 'v1', 'threads': 'v1', 'rolling_scale': 'v1',
          'canary_controls': 'v1', 'pc2_rolling': 'v2'}
GENERATORS = {'rolling': 'rolling/gen_rolling.py', 'canary': 'canary/gen_canary.py',
              'policy': 'policy/v2/gen_policy.py', 'db_rolling': 'db_rolling/gen_db_rolling.py',
              'rolling_audit': 'rolling_audit/gen_rolling_audit.py', 'threads': 'threads/gen_threads.py',
              'rolling_scale': 'rolling_scale/gen_scale.py', 'canary_controls': 'canary_controls/gen_controls.py',
              'pc2_rolling': 'pc2_rolling/gen_pc2.py'}
VIOLATIONS = []


def writable(path):
    if isinstance(path, int):
        return
    target = Path(os.fsdecode(path)).resolve()
    if not target.is_relative_to(HERE):
        VIOLATIONS.append({'operation': 'write_outside_scope', 'path': str(target)})
        raise PermissionError('Writes must stay in generator_reproduction')


def guard(event, args):
    if event == 'open':
        path, mode, flags = args
        if (mode and any(c in mode for c in 'wax+')) or flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
            writable(path)
    elif event in ('os.mkdir', 'os.remove', 'os.rmdir', 'os.chmod', 'os.chown', 'os.utime'):
        writable(args[0])
    elif event in ('os.rename', 'os.link', 'os.symlink'):
        writable(args[0]); writable(args[1])
    elif event in ('subprocess.Popen', 'os.system', 'os.exec', 'os.fork', 'os.posix_spawn'):
        VIOLATIONS.append({'operation': event})
        raise PermissionError('Process creation is prohibited in this reproduction check')


sys.addaudithook(guard)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as f:
        json.dump(data, f, indent=2)
        f.write('\n')


def load_generator(family):
    return runpy.run_path(str(E6 / GENERATORS[family]))


def emit(family, data, filename=None):
    save(GENERATED / family / SERIES[family] / 'inputs' / (filename or data['id'] + '.json'), data)


def raw_metadata():
    result = {}
    for family, version in SERIES.items():
        directory = E6 / family / version / 'raw'
        for path in directory.rglob('*'):
            if path.is_file():
                st = path.stat()
                result[str(path.relative_to(E6))] = [st.st_size, st.st_mtime_ns]
    return result


def main():
    started = datetime.now(ZoneInfo('Asia/Tokyo')).isoformat(timespec='seconds')
    manifests = {}
    protected = {}
    manifests_expected = []
    input_paths = {}
    for family, version in SERIES.items():
        manifest_path = E6 / family / version / 'build/frozen_manifest.json'
        manifest = json.loads(manifest_path.read_text())
        manifests[family] = manifest
        protected[manifest_path] = sha(manifest_path)
        base = E6 / family if family == 'pc2_rolling' else E6
        for rel, expected in manifest['files'].items():
            path = base / rel
            observed = sha(path)
            protected[path] = observed
            manifests_expected.append(dict(family=family, file=str(path.relative_to(E6)),
                                           expected_sha256=expected, actual_sha256=observed,
                                           match=expected == observed))
        paths = sorted((E6 / family / version / 'inputs').glob('*.lts' if family == 'pc2_rolling' else '*.json'))
        frozen_inputs = sorted((base / rel) for rel in manifest['files'] if '/inputs/' in rel)
        assert paths == frozen_inputs, (family, 'frozen-input coverage differs from input directory')
        input_paths[family] = paths
    if not all(r['match'] for r in manifests_expected):
        save(HERE / 'freeze_failure.json', manifests_expected)
        raise AssertionError('A frozen file differs; generators will not be run')

    jar = E6.parent.parent / 'ablation_20260928/jars/e1.jar'
    protected[jar] = sha(jar)
    assert protected[jar] == manifests['rolling']['jar_sha256']
    before_raw = raw_metadata()
    save(HERE / 'raw_metadata_before.json', before_raw)
    save(HERE / 'freeze_checks.json', manifests_expected)

    family_runs = []
    def execute(family, fn):
        log = io.StringIO()
        record = {'family': family, 'generator': GENERATORS[family],
                  'generator_sha256': sha(E6 / GENERATORS[family])}
        try:
            with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                fn()
            record['status'] = 'GENERATED'
        except Exception:
            record['status'] = 'ERROR'
            record['traceback'] = traceback.format_exc()
        with (HERE / (family + '.log')).open('x') as f:
            f.write(log.getvalue())
        family_runs.append(record)

    rolling = load_generator('rolling')
    execute('rolling', lambda: [emit('rolling', rolling['make'](n, m, k))
                               for n in range(2, 7) for m in range(1, n) for k in range(1, n + 1)])
    canary = load_generator('canary')
    execute('canary', lambda: [emit('canary', canary['generate'](n, m, grouped))
                              for n in range(2, 7) for m in range(1, n) for grouped in (False, True)])
    policy = load_generator('policy')
    execute('policy', lambda: [emit('policy', policy['model'](coarse)) for coarse in (False, True)])
    db = load_generator('db_rolling')
    execute('db_rolling', lambda: [emit('db_rolling', db['model'](m, merged))
                                  for m in (2, 3) for merged in (False, True)])
    audit = load_generator('rolling_audit')
    def audit_generation():
        base_path = GENERATED / 'rolling/v1/inputs/rolling_n02_m01_k01.json'
        content = base_path.read_bytes()
        fine = audit['fine_model'](json.loads(content), hashlib.sha256(content).hexdigest())
        emit('rolling_audit', fine, 'fine.json')
        for mode in ('transfers', 'boundaries', 'both'):
            emit('rolling_audit', audit['grouped'](fine, mode), 'generated_' + mode + '.json')
        target = GENERATED / 'rolling_audit/v1/reference' / base_path.name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as f:
            f.write(content)
    execute('rolling_audit', audit_generation)
    threads = load_generator('threads')
    execute('threads', lambda: [emit('threads', threads['make'](n, b, regime, grouped))
                               for n in range(2, 7) for b in (1, 2)
                               for regime in ('backpressure', 'saturated_offers') for grouped in (False, True)])
    scale = load_generator('rolling_scale')
    execute('rolling_scale', lambda: [emit('rolling_scale', scale['make'](n, m, k))
                                     for n in range(7, 17) for m in (1, n - 1) for k in (1, n)])
    controls = load_generator('canary_controls')
    def controls_generation():
        # The unchanged main checks these original frozen hashes against regenerated Canary bytes.
        # This minimal read fixture is not a new experiment freeze or a copied measurement.
        save(GENERATED / 'canary/v1/build/frozen_manifest.json', {'files': manifests['canary']['files'],
             'reproduction_fixture_only': True})
        globals_ = controls['main'].__globals__
        globals_['E6'] = GENERATED
        globals_['OUT'] = GENERATED / 'canary_controls/v1'
        controls['main']()
    execute('canary_controls', controls_generation)
    pc2 = load_generator('pc2_rolling')
    original_plant = pc2['ORIGINAL']
    protected[original_plant] = sha(original_plant)
    def pc2_generation():
        globals_ = pc2['main'].__globals__
        globals_['HERE'] = GENERATED / 'pc2_rolling'
        pc2['main']()
    execute('pc2_rolling', pc2_generation)

    results = []
    for family, paths in input_paths.items():
        for original in paths:
            rel = original.relative_to(E6)
            generated = GENERATED / rel
            record = dict(family=family, original=str(rel), regenerated=str(generated.relative_to(HERE)),
                          original_sha256=sha(original), frozen_sha256=protected[original])
            if not generated.exists():
                record.update(status='MISSING', byte_equal=False, canonical_equal=False)
            else:
                record['regenerated_sha256'] = sha(generated)
                record['byte_equal'] = original.read_bytes() == generated.read_bytes()
                if original.suffix == '.json':
                    canonical = lambda q: json.dumps(json.loads(q.read_bytes()), sort_keys=True, separators=(',', ':'), ensure_ascii=False)
                    record['canonical_equal'] = canonical(original) == canonical(generated)
                else:
                    record['canonical_equal'] = None
                record['status'] = 'BYTE_IDENTICAL' if record['byte_equal'] else ('CANONICAL_ONLY' if record['canonical_equal'] else 'MISMATCH')
                if record['status'] == 'CANONICAL_ONLY':
                    record['reason'] = 'Only JSON object-key order/whitespace differs; array order and all values remain exact.'
            results.append(record)

    reference_checks = []
    for family in ('rolling_audit', 'canary_controls'):
        for original in sorted((E6 / family / SERIES[family] / 'reference').glob('*.json')):
            generated = GENERATED / original.relative_to(E6)
            reference_checks.append({'original': str(original.relative_to(E6)),
                                     'sha256': sha(original), 'regenerated_sha256': sha(generated),
                                     'byte_equal': original.read_bytes() == generated.read_bytes()})
    after_raw = raw_metadata()
    preservation = {'frozen_and_extra_protected_files': len(protected),
                    'changed_files': [str(q.relative_to(E6)) if q.is_relative_to(E6) else q.name
                                      for q, old in protected.items() if sha(q) != old],
                    'raw_files_before': len(before_raw), 'raw_files_after': len(after_raw),
                    'raw_metadata_equal': before_raw == after_raw,
                    'write_or_process_guard_violations': VIOLATIONS,
                    'bytecode_disabled': sys.dont_write_bytecode,
                    'scope': 'All writes confined by audit hook; raw equality is size/mtime plus no writes allowed, not a full raw content rehash.'}
    counts = {family: {status: sum(r['family'] == family and r['status'] == status for r in results)
                      for status in ('BYTE_IDENTICAL', 'CANONICAL_ONLY', 'MISMATCH', 'MISSING')}
              for family in SERIES}
    good = (all(r['status'] == 'BYTE_IDENTICAL' for r in results)
            and all(r['status'] == 'GENERATED' for r in family_runs)
            and all(r['byte_equal'] for r in reference_checks)
            and not preservation['changed_files'] and preservation['raw_metadata_equal'] and not VIOLATIONS)
    report = {'status': 'PASS' if good else 'FAIL', 'started_at': started,
              'finished_at': datetime.now(ZoneInfo('Asia/Tokyo')).isoformat(timespec='seconds'),
              'method': 'Execute unchanged frozen pure generator functions; redirect only output globals for Controls and PC2 main. No input normalization or solver runs.',
              'script_sha256': sha(Path(__file__)), 'json_inputs': sum(r['family'] != 'pc2_rolling' for r in results),
              'fsp_inputs': sum(r['family'] == 'pc2_rolling' for r in results), 'counts': counts,
              'family_execution': family_runs, 'input_comparisons': results,
              'reference_comparisons': reference_checks, 'preservation': preservation}
    save(HERE / 'report.json', report)
    with (HERE / 'input_comparisons.csv').open('x') as f:
        fields = ['family', 'original', 'regenerated', 'status', 'byte_equal', 'canonical_equal',
                  'original_sha256', 'frozen_sha256', 'regenerated_sha256', 'reason']
        writer = csv.DictWriter(f, fields); writer.writeheader(); writer.writerows(results)
    print(json.dumps({k: report[k] for k in ('status', 'json_inputs', 'fsp_inputs', 'counts', 'preservation')}))
    return 0 if good else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception:
        save(HERE / 'execution_failure.json', {'error': traceback.format_exc(), 'guard_violations': VIOLATIONS})
        raise
