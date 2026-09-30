#!/usr/bin/env python3
"""Check the extension evidence in a materialized artifact; never run Java.

Checks complete denominators, saved decisions/counters against raw records,
unaltered input/certificate hashes, and 22 small E6 games independently. This
is saved-evidence validation, not a timing replication or a new measurement.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

SUB = 'FSE2027_SUBMISSION_20260914'
STATUS = {'SUCCESS': 'WIN', 'UNREALIZABLE': 'LOSS', 'TIMEOUT': 'TO'}
METRICS = {'states_discovered': 'revised_semantic_states_discovered',
           'successor_queries': 'revised_successor_oracle_calls_cumulative',
           'worst_completion_rank': 'revised_worst_completion_rank',
           'losing_region_states': 'revised_losing_region_states'}
EXT_EXPECTED = {
    'ext1_travel_frontier': {'SUCCESS': 4},
    'ext2_rq3_df_cpu': {'SUCCESS': 1, 'UNREALIZABLE': 1},
    'ext3_travel_next': {'SUCCESS': 1, 'TIMEOUT': 4},
    'ext4_rq3_df_heap200': {'SUCCESS': 1, 'TIMEOUT': 10, 'OOM': 1},
    'ext5_travel_heap200': {'TIMEOUT': 2, 'SKIPPED_MONOTONE': 2},
    'ext6_legacy_heap200': {'OOM': 11, 'CRASH': 7},
    'ext7_eager_heap200': {'SUCCESS': 3, 'UNREALIZABLE': 1, 'TIMEOUT': 5, 'OOM': 1},
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


class Checker:
    def __init__(self, root):
        self.root = root.resolve()
        self.sub = self.root / SUB
        self.exp = self.sub / 'experiments'
        self.witness = self.exp / 'witness_20260929'
        self.e6 = self.witness / 'e6'
        self.read_hashes = {}
        self.relationships = Counter()
        self.redacted_metadata_references = []

    def read(self, path):
        path = Path(path)
        value = path.read_bytes()
        self.read_hashes[path] = hashlib.sha256(value).hexdigest()
        return value

    def js(self, path):
        return json.loads(self.read(path).decode('utf-8-sig'))

    def rows(self, path):
        return list(csv.DictReader(io.StringIO(self.read(path).decode('utf-8-sig'))))

    def relative(self, path):
        return Path(path).relative_to(self.root).as_posix()

    def saved_path(self, value):
        value = value.replace('\\', '/')
        if SUB + '/' in value:
            value = value[value.index(SUB + '/'):]
        p = Path(value)
        require(not p.is_absolute() and '..' not in p.parts, 'Unsafe saved relative path: ' + value)
        return self.sub / p if value.startswith('experiments/') else self.root / p

    def equal_hash(self, path, expected, kind):
        actual = hashlib.sha256(self.read(path)).hexdigest()
        require(actual == expected, kind + ' digest mismatch: ' + self.relative(path))
        self.relationships[kind] += 1

    def metrics(self, path):
        text = self.read(path).decode('utf-8', errors='replace')
        start = '================ EVALUATION DATA CSV ================'
        stop = '================ EVALUATION SUMMARY ================'
        require(text.count(start) == 1 and text.count(stop) == 1,
                'Expected one evaluation CSV block: ' + self.relative(path))
        block = text.split(start, 1)[1].split(stop, 1)[0].strip()
        result = {}
        for row in csv.DictReader(io.StringIO(block)):
            key = row.get('metric_key')
            if key:
                require(key not in result, 'Duplicate raw metric: ' + key)
                result[key] = row.get('value', '')
        return result

    def trial(self, row, meta_path, decision_key='decision'):
        meta = self.js(meta_path)
        decision = row.get(decision_key, '')
        actual = STATUS.get(meta['status'], meta['status'])
        require(actual == decision, 'Saved/raw status mismatch: ' + self.relative(meta_path))
        job = meta.get('job', {})
        for key in ('model_id', 'target_id'):
            if row.get(key):
                require(job.get(key) == row[key], 'Saved/raw identity mismatch: ' + key)
        input_hash = meta.get('input_sha256') or meta.get('input_model', {}).get('sha256')
        if input_hash:
            source = self.saved_path(job['model_path'])
            if not source.is_file():
                source = self.exp / 'rq3_xeon' / job['model_path']
            self.equal_hash(source, input_hash, 'input_to_invocation')
            if row.get('input_sha256'):
                require(row['input_sha256'] == input_hash, 'Table/input hash mismatch')
        for name, record in meta.get('artifact_digests', {}).items():
            if record.get('sha256'):
                self.equal_hash(meta_path.parent / (name + '.txt'), record['sha256'], 'raw_to_invocation')
        if decision in ('WIN', 'LOSS'):
            m = self.metrics(meta_path.parent / 'output.txt')
            expected = {'realizable': 'WIN', 'unrealizable': 'LOSS', 'winning': 'WIN', 'losing': 'LOSS'}
            require(expected.get(m.get('revised_decision'), m.get('revised_decision')) == decision,
                    'Native raw decision differs: ' + self.relative(meta_path))
            require(m.get('revised_internal_certificate_check') == 'passed', 'Native certificate check did not pass')
            if decision == 'WIN':
                require(m.get('revised_link_checker') == 'passed', 'Native WIN Link check did not pass')
            for key, metric in METRICS.items():
                if row.get(key):
                    require(str(m.get(metric)) == row[key], 'Saved/raw metric mismatch: ' + key)
            self.relationships['checked_lts_decisions'] += 1
        return meta

    def ablations(self):
        a = self.exp / 'ablation_20260928'
        e1 = self.rows(a / 'tables/e1_comparison.csv')
        require(Counter(r['decision'] for r in e1) == {'WIN': 51, 'LOSS': 3}, 'E1 counts differ')
        require(len({(r['model_id'], r['target_id'], r['merge']) for r in e1}) == 54, 'E1 denominator/keys differ')
        for row in e1:
            self.trial(row, self.saved_path(row['meta_path']))
            require(row['original_decision'] == row['decision'] and row['decision_changed'] == 'False', 'E1 decision change')
        e2 = [r for r in self.rows(a / 'tables/e2_comparison.csv') if r['reference_only'] == 'False']
        require(len(e2) == 27 and Counter(r['ucpruned_decision'] for r in e2) == {'WIN': 16, 'LOSS': 1, 'TO': 10}, 'E2 Mac counts differ')
        attempts = self.rows(a / 'tables/e2_trials.csv')
        require(len(attempts) == 38 and Counter(r['decision'] for r in attempts) == {'WIN': 16, 'LOSS': 1, 'TO': 21}, 'E2 original/retry attempts differ')
        for row in attempts:
            self.trial(row, self.saved_path(row['meta_path']))
        xeon = self.rows(a / 'raw/e2_xeon/progress.csv')
        require(len(xeon) == 27 and Counter(r['decision'] for r in xeon) == {'WIN': 15, 'TO': 12}, 'E2 Xeon counts differ')
        for row in xeon:
            path = a / 'raw/e2_xeon/pass1_1200s/runs' / (row['model_id'] + '__' + row['target_id'] + '__rep01__direct_full_ucpruned') / 'meta.json'
            self.trial(row, path)
        return {'e1': {'comparisons': 54, 'WIN': 51, 'LOSS': 3, 'decision_changes': 0},
                'e2_mac': {'conditions': 27, 'WIN': 16, 'LOSS': 1, 'TO': 10, 'all_attempts': 38},
                'e2_xeon': {'conditions': 27, 'WIN': 15, 'TO': 12},
                'scope': 'Mac/Xeon and additional attempts are separate; no pooled timing statistic.'}

    def earlier_witnesses(self):
        e41 = self.rows(self.witness / 'e4_1/tables/e4_1_trials.csv')
        require(len(e41) == 24 and Counter(r['decision'] for r in e41) == {'WIN': 19, 'LOSS': 5}, 'E4 fixture counts differ')
        for row in e41:
            self.trial(row, self.saved_path(row['meta_path']))
            self.equal_hash(self.saved_path(row['copy_path']), row['copy_sha256'], 'e4_fixture_copy')
        for group, expected in [('e4_2_corrected', {'WIN': 27, 'LOSS': 18}),
                                ('e4_2', {'WIN': 9, 'LOSS': 6, 'ERROR': 30})]:
            rows = self.rows(self.witness / group / 'summary.csv')
            require(len(rows) == 45 and Counter(r['status'] for r in rows) == expected, 'E4 ring counts differ: ' + group)
            for row in rows:
                if row['status'] in ('WIN', 'LOSS'):
                    result = self.js(self.witness / group / row['result_file'])
                    require(result['decision'] == row['decision'] == row['status'], 'Ring decision differs')
                    require(result['certificate_checker'] == 'PASS', 'Ring saved native certificate check differs')
                    self.equal_hash(self.witness / group / 'inputs' / ('cell_n' + f"{int(row['n']):02d}" + '.json'), row['input_sha256'], 'ring_input')
        e5 = self.rows(self.witness / 'e5/tables/results.csv')
        require(len(e5) == 54 and Counter(r['decision'] for r in e5) == {'WIN': 4, 'LOSS': 12, 'TO': 9, 'NOT_RUN_DEADLINE': 29}, 'E5 scheduled counts differ')
        pairs = self.rows(self.witness / 'e5/tables/pairs.csv')
        require(len(pairs) == 18 and Counter(r['category'] for r in pairs) == {'null': 2, 'bothLOSS': 6, 'other': 10}, 'E5 pair counts differ')
        for row in e5:
            if row['decision'] != 'NOT_RUN_DEADLINE':
                self.trial(row, self.saved_path(row['meta_path']))
        return {'e4_fixtures': {'trials': 24, 'WIN': 19, 'LOSS': 5},
                'e4_corrected_rings': {'trials': 45, 'WIN': 27, 'LOSS': 18},
                'e4_initial_rings_retained': {'trials': 45, 'WIN': 9, 'LOSS': 6, 'ERROR': 30},
                'e5': {'planned': 54, 'WIN': 4, 'LOSS': 12, 'TO': 9, 'NOT_RUN_DEADLINE': 29,
                       'pairs': 18, 'witness': 0, 'both_loss': 6, 'both_win': 2, 'incomplete': 10}}

    def e6_evidence(self):
        index = self.rows(self.e6 / 'results_index.csv')
        main = [r for r in index if r['population'] in ('core', 'operational_control', 'application_plant_attempt')]
        require(len(main) == 55 and Counter(r['class'] for r in main) == {'witness': 33, 'both_loss': 11, 'both_win': 10, 'incomplete': 1}, 'E6 comparison counts differ')
        require(Counter(r['population'] for r in index) == {'core': 34, 'operational_control': 20, 'scale_extension': 20,
                    'assumption_control': 12, 'application_plant_attempt': 1, 'reference_e4': 9}, 'E6 full index denominator differs')
        registered = self.rows(self.e6 / 'integration/all_registered_run_counts.csv')
        totals = Counter()
        for series in registered:
            folder = self.e6 / series['family']
            summary = folder / 'summary.csv'
            if not summary.exists():
                summary = folder / 'tables/results.csv'
            rows = self.rows(summary)
            counts = Counter(row['status'] for row in rows)
            require(len(rows) == int(series['trials']) and all(counts[k] == int(series[k]) for k in ('WIN', 'LOSS', 'TO')), 'E6 series tally differs: ' + series['family'])
            totals.update(counts)
            for row in rows:
                if row.get('input'):
                    self.equal_hash(folder / row['input'], row['input_sha256'], 'e6_input')
                if row.get('result_file'):
                    result = self.js(folder / row['result_file'])
                    require(result['decision'] == row['status'], 'E6 result/summary decision mismatch')
                    for key in ('states_discovered', 'successor_queries', 'certificate_states'):
                        require(str(result.get(key) if result.get(key) is not None else '') == row[key], 'E6 raw metric mismatch: ' + key)
                    proof_path = folder / row['certificate_file']
                    self.equal_hash(proof_path, result['certificate_sha256'], 'e6_serialized_certificate')
                    proof = self.js(proof_path)
                    require(proof['decision'] == result['decision'] and proof['jar_sha256'] == row['jar_sha256'], 'E6 certificate identity mismatch')
                    require(result['certificate_checker'] == result['endpoint_checker'] == 'PASS', 'E6 saved native check differs')
                    if result['decision'] == 'WIN':
                        require(result['link_checker'] == 'PASS', 'E6 saved WIN Link differs')
                elif row.get('raw_directory'):
                    raw = self.e6 / 'pc2_rolling' / row['raw_directory']
                    completion = self.js(raw / 'completion.json')
                    require(completion['timed_out'] == (row['status'] == 'TO'), 'PC2 timeout/decision mismatch')
                    if row['status'] == 'TO':
                        require(not row.get('states_discovered') and not row.get('certificate_states'), 'PC2 TO has fabricated counters')
                    else:
                        proof = self.js(raw / 'certificate_summary.json')
                        require(proof['decision'] == 'WIN' and proof['certificate_checker'].startswith('PASS') and proof['link_checker'].startswith('PASS'), 'PC2 saved WIN check differs')
        require(totals == {'WIN': 195, 'LOSS': 197, 'TO': 6}, 'E6 all-host counts differ')
        for path in self.e6.rglob('completion.json'):
            for name, expected in self.js(path).get('files', {}).items():
                target = path.parent / name
                require(target.is_file(), 'Missing completion member: ' + self.relative(target))
                actual = hashlib.sha256(self.read(target)).hexdigest()
                if actual != expected and name in ('invocation.json', 'frozen_manifest.json'):
                    # Their absolute command paths were deliberately redacted;
                    # the original digest is retained as historical provenance.
                    self.redacted_metadata_references.append(self.relative(target))
                else:
                    require(actual == expected, 'E6 completion/scientific raw hash mismatch: ' + self.relative(target))
                    self.relationships['e6_completion_member'] += 1
        return {'main_pairs': 55, 'witness': 33, 'both_loss': 11, 'both_win': 10, 'incomplete': 1,
                'registered_trials': sum(totals.values()), 'WIN': 195, 'LOSS': 197, 'TO': 6,
                'scope': '395 Mac trials and 3 received Xeon trials; scale/assumption controls and E4 references remain separate.'}

    def extended_budgets(self):
        records = {}
        for name, expected in EXT_EXPECTED.items():
            folder = self.exp / 'rq3_xeon/raw' / name
            rows = self.rows(folder / 'raw_runs.csv')
            summary = self.rows(folder / 'summary.csv')
            require(Counter(r['process_status'] for r in rows) == expected and
                    Counter(r['stage1_status'] for r in summary) == expected, 'Extension tallies differ: ' + name)
            plan = self.js(folder / 'plan.json')
            require({j['job_id'] for j in plan['jobs']} == {r['job_id'] for r in rows} and len(rows) == len(plan['jobs']), 'Extension planned denominator differs')
            for row in rows:
                row = dict(row, checked_status=STATUS.get(row['process_status'], row['process_status']))
                meta = self.trial(row, folder / 'runs' / row['job_id'] / 'meta.json', 'checked_status')
                if row['process_status'] == 'SKIPPED_MONOTONE':
                    require(meta.get('skip_reason') and not row.get('states_discovered'), 'Skip lacks reason or has inferred metrics')
            records[name] = {'planned': len(rows), **expected}
        require(sum(r['planned'] for r in records.values()) == 55, 'Extension total differs')
        return records

    def independent_small_games(self):
        with tempfile.TemporaryDirectory(prefix='fgducs-independent-') as directory:
            path = Path(directory) / 'checks.json'
            command = [sys.executable, '-B', str(self.e6 / 'independent/check_games_v3.py'), '--output', str(path),
                       '--families', 'policy/v2', 'db_rolling/v2', 'rolling_audit/v1']
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONHASHSEED='0')
            run = subprocess.run(command, capture_output=True, text=True, env=env, timeout=60)
            require(run.returncode == 0 and path.exists(), 'Independent small-game check failed: ' + run.stdout + run.stderr)
            result = json.loads(path.read_text())
            require(result['status'] == 'PASS' and len(result['audits']) == 22 and result['distinct_input_merge_games'] == 18,
                    'Independent game denominator differs')
            return {'status': 'PASS', 'jobs': 22, 'distinct_input_merge_games': 18,
                    'families': ['policy/v2', 'db_rolling/v2', 'rolling_audit/v1'],
                    'scope': result['method'], 'elapsed_seconds': result['elapsed_seconds']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True, type=Path, help='materialized original-layout package root')
    parser.add_argument('--output', required=True, type=Path, help='new JSON file outside the workspace')
    args = parser.parse_args()
    root = args.workspace.resolve()
    out = args.output.resolve()
    if out.exists() or args.output.is_symlink():
        parser.error('Output exists; choose a new JSON file')
    if out.is_relative_to(root):
        parser.error('Output must be outside the saved workspace')
    if not (root / SUB / 'experiments').is_dir():
        parser.error('Workspace lacks the original experiment layout')
    checker = Checker(root)
    start = time.monotonic()
    report = {'status': 'PASS', 'started_utc': datetime.now(timezone.utc).isoformat(), 'checks': {}, 'errors': []}
    for key, function in [('ablations', checker.ablations), ('e4_e5', checker.earlier_witnesses),
                          ('e6', checker.e6_evidence), ('ext1_to_ext7', checker.extended_budgets),
                          ('independent_small_games', checker.independent_small_games)]:
        try:
            report['checks'][key] = function()
            print('PASS:', key, flush=True)
        except Exception as error:
            report['status'] = 'FAIL'
            message = type(error).__name__ + ': ' + str(error)
            report['errors'].append({'check': key, 'error': message.replace(str(root), '<WORKSPACE>')})
            print('FAIL:', key, message, flush=True)
    changed = [checker.relative(p) for p, expected in checker.read_hashes.items() if digest(p) != expected]
    if changed:
        report['status'] = 'FAIL'
        report['errors'].append({'check': 'source_immutability', 'changed': changed})
    report.update(elapsed_seconds=time.monotonic() - start, source_files_read=len(checker.read_hashes),
                  source_files_unchanged=not changed, verified_digest_relationships=dict(checker.relationships),
                  preserved_original_metadata_digest_references=sorted(set(checker.redacted_metadata_references)),
                  scope='No JVM, network, synthesis timing, or original-file write. Saved native LTS checks are not claimed as newly re-executed serialized-certificate checks. Historical hashes of redacted invocation metadata are preserved but not claimed to equal the redacted bytes.')
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'status': report['status'], 'source_files_read': report['source_files_read'],
                      'source_files_unchanged': report['source_files_unchanged'], 'output': str(out)}))
    return report['status'] != 'PASS'


if __name__ == '__main__':
    raise SystemExit(main())
