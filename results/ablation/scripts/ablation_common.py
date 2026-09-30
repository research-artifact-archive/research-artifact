"""Read-only extraction and shared I/O for the separate E1/E2 campaigns."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from pathlib import Path

OLD_JAR = 'fbdc25f58d5441ed906d408a94b7414c9d9c3ed35e2ebce22d9751729967ba07'
METRICS = {
    'states_discovered': 'revised_semantic_states_discovered',
    'buckets': 'revised_direct_full_enabled_action_buckets',
    'successor_queries': 'revised_successor_oracle_calls_cumulative',
    'solver_time_ms': 'revised_solve_and_internal_check_time',
    'worst_completion_rank': 'revised_worst_completion_rank',
    'losing_region_states': 'revised_losing_region_states',
    'internal_certificate_check': 'revised_internal_certificate_check',
    'link_checker': 'revised_link_checker',
    'solver_variant': 'revised_implementation_variant',
    'contract_merge': 'revised_contract_merge',
}
STATUSES = {0: 'SUCCESS', 2: 'NO_COMPOSITION', 3: 'NO_TRANSITION_OUTPUT',
            4: 'CRASH', 5: 'OOM', 6: 'UNREALIZABLE', 7: 'INVALID_CERTIFICATE',
            8: 'INVALID_INPUT', 9: 'VERIFICATION_INCONCLUSIVE', 64: 'USAGE_ERROR'}


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    temporary.replace(path)


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def csv_write(path, rows, columns=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = columns or list(rows[0])
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def extract_output(path):
    data = {key: '' for key in METRICS}
    data.update(decision='', validation_errors='', solver_seconds='', failure_reason='')
    if not Path(path).is_file():
        data['validation_errors'] = 'evaluation output absent'
        return data
    lines = Path(path).read_text(encoding='utf-8', errors='replace').splitlines()
    starts = [i for i, line in enumerate(lines)
              if line.strip() == '================ EVALUATION DATA CSV ================']
    if len(starts) != 1:
        data['validation_errors'] = f'expected one evaluation CSV block, found {len(starts)}'
        return data
    block = []
    for line in lines[starts[0] + 1:]:
        if line.strip() == '================ EVALUATION SUMMARY ================':
            break
        if not line.strip() or re.fullmatch(r'=+', line.strip()):
            continue
        block.append(line)
    reader = csv.DictReader(io.StringIO('\n'.join(block)))
    values = {}
    errors = []
    for row in reader:
        if None in row or any(value is None for value in row.values()):
            errors.append('malformed evaluation CSV row')
            continue
        key = row.get('metric_key', '')
        if row.get('failure_reason'):
            data['failure_reason'] = row['failure_reason']
        if not key:
            continue
        if key in values:
            errors.append('duplicate metric: ' + key)
        values[key] = row.get('value', '')
    for key, metric in METRICS.items():
        data[key] = values.get(metric, '')
    value = values.get('revised_decision', '')
    data['decision'] = {'realizable': 'WIN', 'unrealizable': 'LOSS', 'winning': 'WIN', 'losing': 'LOSS'}.get(value, value.upper())
    if data['solver_time_ms'] != '':
        data['solver_seconds'] = float(data['solver_time_ms']) / 1000
    data['validation_errors'] = '; '.join(sorted(set(errors)))
    return data


def read_trial(meta_path):
    meta_path = Path(meta_path)
    if not meta_path.is_file():
        return {'status': 'NOT_RUN', 'decision': 'NOT_RUN', 'validation_errors': ''}
    meta = read_json(meta_path)
    data = extract_output(meta_path.parent / 'output.txt')
    status = meta.get('status', 'INCOMPLETE')
    if not meta.get('completed'):
        status = 'RUNNING' if status == 'RUNNING' else 'INCOMPLETE'
    data.update(status=status, jar_sha256=meta.get('jar_sha256', meta.get('classpath', {}).get('sha256', '')),
                input_sha256=meta.get('input_sha256', meta.get('input_model', {}).get('sha256', '')),
                source_commit=meta.get('source_commit', ''), elapsed_seconds=meta.get('elapsed_monotonic_seconds', ''),
                timeout_seconds=meta.get('timeout_seconds', ''), heap=meta.get('java_heap', ''),
                meta_path=str(meta_path), started_utc=meta.get('started_utc', ''), finished_utc=meta.get('finished_utc', ''))
    if status in {'SUCCESS', 'UNREALIZABLE'}:
        errors = [data['validation_errors']] if data['validation_errors'] else []
        expected = 'WIN' if status == 'SUCCESS' else 'LOSS'
        if data['decision'] != expected:
            errors.append('exit status disagrees with solver decision')
        if data['internal_certificate_check'] != 'passed':
            errors.append('internal certificate check not passed')
        if expected == 'WIN' and data['link_checker'] != 'passed':
            errors.append('link check not passed')
        if meta.get('jar_sha256'):
            properties = meta.get('job', {}).get('jvm_properties', {})
            solver = properties.get('mtsa.revised.otf.solver')
            variant = {'direct_full_ucpruned': 'revised_direct_full_ucpruned_v1',
                       'otf': 'revised_otf_ducs_direct_v1'}.get(solver)
            if not variant or data['solver_variant'] != variant:
                errors.append('solver variant differs from requested solver')
            command = meta.get('command', [])
            if '-Dmtsa.revised.otf.solver=' + str(solver) not in command:
                errors.append('command solver differs from job property')
            merge = properties.get('mtsa.otf.contractMerge')
            if merge is not None and (data['contract_merge'] != merge or '-Dmtsa.otf.contractMerge=' + merge not in command):
                errors.append('contract merge differs from requested transform')
        digest = meta.get('artifact_digests', {}).get('output', {}).get('sha256')
        if digest and sha256(meta_path.parent / 'output.txt') != digest:
            errors.append('output digest mismatch')
        data['validation_errors'] = '; '.join(errors)
        if errors:
            data['decision'] = 'INVALID'
    else:
        data['decision'] = {'TIMEOUT': 'TO'}.get(status, status)
        # Partial metrics are not completed-game measurements.
        for key in ('states_discovered', 'buckets', 'successor_queries', 'solver_seconds',
                    'worst_completion_rank', 'losing_region_states'):
            data[key] = ''
        stderr_path = meta_path.parent / 'stderr.txt'
        if not data['failure_reason'] and stderr_path.is_file():
            data['failure_reason'] = '\n'.join(line for line in stderr_path.read_text(errors='replace').splitlines()
                                                if re.search(r'exception|error|invalid|cannot', line, re.I))[:2000]
        if meta.get('harness_error'):
            data['failure_reason'] = meta['harness_error']
    return data


def planned_jobs(config):
    for model in config['models']:
        for target in config['targets']:
            for method in config['methods']:
                yield {
                    'job_id': f"{model['id']}__{target['id']}__rep01__{method['id']}",
                    'model_id': model['id'], 'model_path': model['path'],
                    'target_id': target['id'],
                    'target_name': method['target_template'].format(suffix=target['suffix']),
                    'method_id': method['id'], 'merge': method.get('merge', 'none'),
                    'repetition': 1, 'jvm_properties': method['jvm_properties'],
                }
