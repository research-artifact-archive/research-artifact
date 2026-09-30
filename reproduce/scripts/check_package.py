#!/usr/bin/env python3
"""Check saved FG-DUCS counts, evidence fields, input paths and raw records."""
from pathlib import Path
from collections import Counter
import csv
import json
from fetch_assets import ASSETS, verify

ROOT = Path(__file__).resolve().parent
BASE = ROOT / 'FSE2027_SUBMISSION_20260914/experiments/semantic_revision_20260914'


def rows(path):
    with path.open(newline='', encoding='utf-8') as stream:
        return list(csv.DictReader(stream))


def check():
    totals = {}
    for phase, counts, eligible, wins in [
        ('rq1', {'SUCCESS': 36, 'UNREALIZABLE': 48, 'INVALID_INPUT': 8}, 84, 36),
        ('rq2', {'SUCCESS': 10, 'UNREALIZABLE': 4}, 14, 10),
    ]:
        saved = rows(BASE / phase / 'summary.csv')
        assert dict(Counter(row['process_status'] for row in saved)) == counts
        assert len({(r['model_id'], r['method_id']) for r in saved}) == len(saved)
        assert all(r['expected_agreement'].lower() == 'true' for r in saved)
        assert sum(r['internal_certificate_check'] == 'passed' for r in saved) == eligible
        assert sum(r['run_verified'].lower() == 'true' for r in saved) == eligible
        assert sum(r['link_checker'] == 'passed' for r in saved) == wins
        expected = rows(BASE / ('oracle/summary.csv' if phase == 'rq1' else 'rq2/expected.csv'))
        expectation = ({(r['stratum'] + '_' + r['model_id'], ''): r['expected_decision'] for r in expected}
                       if phase == 'rq1' else
                       {(r['model_id'], r['method_id']): r['expected_decision'] for r in expected})
        normalize = {'WIN': 'SUCCESS', 'LOSS': 'UNREALIZABLE', 'realizable': 'SUCCESS',
                     'unrealizable': 'UNREALIZABLE', 'invalid_input': 'INVALID_INPUT'}
        for row in saved:
            key = row['model_id'], '' if phase == 'rq1' else row['method_id']
            assert normalize[expectation[key]] == row['process_status'], key
            assert (ROOT / row['input_lts']).is_file(), row['input_lts']
            output = BASE / phase / 'raw' / row['raw_output']
            assert output.is_file() and output.stat().st_size, output
            assert (output.parent / 'meta.json').is_file(), output
            meta = json.loads((output.parent / 'meta.json').read_text())
            assert meta['status'] == row['process_status'], (key, meta)
        totals[phase] = {'jobs': len(saved), 'counts': counts,
                         'certificate_and_exhaustive_checks': eligible, 'link_checks': wins}
    jar = ROOT / 'Implementation/Source Code/maven-root/mtsa/target/mtsa-1.0-SNAPSHOT.jar'
    if jar.is_file():
        verify(jar, ASSETS['mtsa'])
        totals['solver_binary'] = 'present; frozen SHA-256 verified'
    else:
        totals['solver_binary'] = 'not bundled; saved-evidence checks above require no JAR'
    print(json.dumps(totals, indent=2))


if __name__ == '__main__':
    check()
