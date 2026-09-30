#!/usr/bin/env python3
"""Preserve attempt 1; create the missing output parent, then finish comparison."""
import contextlib
import csv
import hashlib
import io
import json
from pathlib import Path
import runpy
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.dont_write_bytecode = True
CHECK = Path(__file__).resolve().with_name('check_reproduction.py')
api = runpy.run_path(str(CHECK))  # Installs the same write/process audit guard.
HERE, E6, GENERATED = api['HERE'], api['E6'], api['GENERATED']
SERIES, GENERATORS = api['SERIES'], api['GENERATORS']
sha, save = api['sha'], api['save']


def main():
    observed = sorted(str(q.relative_to(GENERATED)) for q in GENERATED.glob('*/v*/inputs/*'))
    assert len(observed) == 191
    assert not (GENERATED / 'canary_controls').exists()
    save(HERE / 'attempt01_failure_analysis.json', {
        'status': 'HARNESS_DIRECTORY_ERROR',
        'observed_generated_inputs': len(observed),
        'generated_inputs_before_repair': observed,
        'cause': 'The replay harness redirected OUT to generated/canary_controls/v1 without creating its parent. The unchanged generator uses OUT.mkdir(exist_ok=False), so that call cannot create missing parents. Final comparison then tried to read the absent copied references.',
        'evidence': ['execution_failure.json', 'check_reproduction.py controls_generation', 'canary_controls/gen_controls.py main line 9'],
        'repair': 'Create generated/canary_controls only, invoke unchanged Controls main there, and compare all preserved outputs. No generator, saved input, or earlier reproduced input is changed.'})
    (GENERATED / 'canary_controls').mkdir()
    controls = api['load_generator']('canary_controls')
    controls['main'].__globals__['E6'] = GENERATED
    controls['main'].__globals__['OUT'] = GENERATED / 'canary_controls/v1'
    log = io.StringIO()
    with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        controls['main']()
    with (HERE / 'controls_wrapper_retry.log').open('x') as f:
        f.write(log.getvalue())

    freeze_checks = json.loads((HERE / 'freeze_checks.json').read_text())
    after_checks = [dict(r, after_sha256=sha(E6 / r['file']),
                         unchanged=sha(E6 / r['file']) == r['actual_sha256']) for r in freeze_checks]
    results = []
    for family, version in SERIES.items():
        manifest = json.loads((E6 / family / version / 'build/frozen_manifest.json').read_text())
        base = E6 / family if family == 'pc2_rolling' else E6
        original_paths = sorted(base / q for q in manifest['files'] if '/inputs/' in q)
        generated_paths = sorted((GENERATED / family / version / 'inputs').glob('*'))
        assert [q.name for q in original_paths] == [q.name for q in generated_paths]
        for source, generated in zip(original_paths, generated_paths):
            source_bytes, regenerated_bytes = source.read_bytes(), generated.read_bytes()
            equal = source_bytes == regenerated_bytes
            canonical_equal = None
            if source.suffix == '.json':
                canonical = lambda b: json.dumps(json.loads(b), sort_keys=True, separators=(',', ':'), ensure_ascii=False)
                canonical_equal = canonical(source_bytes) == canonical(regenerated_bytes)
            status = 'BYTE_IDENTICAL' if equal else ('CANONICAL_ONLY' if canonical_equal else 'MISMATCH')
            record = dict(family=family, original=str(source.relative_to(E6)),
                          regenerated=str(generated.relative_to(HERE)), status=status,
                          original_sha256=sha(source), regenerated_sha256=sha(generated),
                          frozen_sha256=manifest['files'][str(source.relative_to(base))],
                          byte_equal=equal, canonical_equal=canonical_equal, reason='')
            if status == 'CANONICAL_ONLY':
                record['reason'] = 'Only object-key ordering or whitespace differs; all array order and values preserved.'
            results.append(record)
    references = []
    for family in ('rolling_audit', 'canary_controls'):
        for source in sorted((E6 / family / SERIES[family] / 'reference').glob('*.json')):
            generated = GENERATED / source.relative_to(E6)
            references.append(dict(original=str(source.relative_to(E6)), original_sha256=sha(source),
                                   regenerated_sha256=sha(generated), byte_equal=source.read_bytes() == generated.read_bytes()))
    raw_before = json.loads((HERE / 'raw_metadata_before.json').read_text())
    raw_after = api['raw_metadata']()
    pc2 = api['load_generator']('pc2_rolling')
    jar = E6.parent.parent / 'ablation_20260928/jars/e1.jar'
    preservation = dict(frozen_file_occurrences=len(after_checks),
                        unique_frozen_files=len({r['file'] for r in after_checks}),
                        frozen_files_unchanged=all(r['unchanged'] for r in after_checks),
                        frozen_hashes_match=all(r['match'] for r in after_checks),
                        raw_files=len(raw_before), raw_metadata_equal=raw_before == raw_after,
                        raw_scope='Size and mtime_ns before/after plus write-prohibiting audit hook, not a full raw content rehash.',
                        jar_sha256=sha(jar), jar_matches=sha(jar) == 'ff1e6b176f004ea85f1e99690a90388a6a4d24f44cd8d8e636fcd9337dcf67d5',
                        original_plant_sha256=sha(pc2['ORIGINAL']), original_plant_matches=sha(pc2['ORIGINAL']) == pc2['EXPECTED'],
                        guard_violations=api['VIOLATIONS'], bytecode_disabled=sys.dont_write_bytecode)
    counts = {family: {status: sum(r['family'] == family and r['status'] == status for r in results)
                      for status in ('BYTE_IDENTICAL', 'CANONICAL_ONLY', 'MISMATCH')}
              for family in SERIES}
    passed = (all(r['byte_equal'] for r in results) and all(r['byte_equal'] for r in references)
              and preservation['frozen_files_unchanged'] and preservation['frozen_hashes_match']
              and preservation['raw_metadata_equal'] and preservation['jar_matches']
              and preservation['original_plant_matches'] and not preservation['guard_violations'])
    report = dict(status='PASS' if passed else 'FAIL', finished_at=datetime.now(ZoneInfo('Asia/Tokyo')).isoformat(timespec='seconds'),
                  scope='Input generation reproducibility only; no solver, JVM, or original-file mutation.',
                  json_inputs=214, fsp_inputs=1, reference_copies=len(references),
                  canonical_comparison_needed=any(r['status'] == 'CANONICAL_ONLY' for r in results),
                  counts=counts, input_comparisons=results, reference_comparisons=references,
                  preservation=preservation, initial_failure='attempt01_failure_analysis.json',
                  check_script_sha256=sha(CHECK), finish_script_sha256=sha(Path(__file__)),
                  generator_sources={k: dict(path=v, sha256=sha(E6 / v)) for k, v in GENERATORS.items()})
    save(HERE / 'report.json', report)
    save(HERE / 'freeze_checks_after.json', after_checks)
    with (HERE / 'input_comparisons.csv').open('x') as f:
        writer = csv.DictWriter(f, list(results[0])); writer.writeheader(); writer.writerows(results)
    print(json.dumps({k: report[k] for k in ('status', 'json_inputs', 'fsp_inputs', 'reference_copies', 'counts', 'preservation')}))
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())
