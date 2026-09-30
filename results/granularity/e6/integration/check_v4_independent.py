#!/usr/bin/env python3
"""Read-only private-original/public-snapshot audit; never creates an export or JVM.

Only --output is written, create-only. The 398 measurements comprise 395 Mac
trials plus three separately received Xeon trials. Preflights, validation replays,
failed model versions, and reference_e4 rows are excluded from this count;
those historical files are nevertheless retained by the inventory comparison.
"""
import argparse
import csv
import hashlib
import io
import json
import os
import re
import socket
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

E6 = Path(__file__).resolve().parents[1]
JAR_SHA = 'ff1e6b176f004ea85f1e99690a90388a6a4d24f44cd8d8e636fcd9337dcf67d5'
FAMILIES = ('rolling/v1', 'canary/v1', 'policy/v2', 'db_rolling/v2',
            'rolling_audit/v1', 'threads/v1', 'rolling_scale/v1', 'canary_controls/v1')
PC2 = 'pc2_rolling'
EXT = PC2 + '/extended_7200'
XEON = PC2 + '/xeon_20260929_2344'
JOBS = ('lazy_transfers', 'direct_full_none')
ORIGINAL_PC2_JOBS = ('lazy_none', 'lazy_transfers', 'direct_full_none')
TEXT = {'.md', '.json', '.csv', '.tex', '.bib', '.py', '.java', '.sh', '.ps1',
        '.log', '.txt', '.svg', '.xml', '.properties', '.yml', '.yaml', '.toml',
        '.aux', '.fls', '.fdb_latexmk', '.out'}
EMPTY_TO = ('raw_diagnostic_decision', 'states_discovered', 'successor_queries',
            'materialized_transition_outcomes', 'enabled_buckets',
            'worst_completion_rank', 'losing_region_states', 'certificate_states',
            'safe_region_states', 'unsafe_region_states', 'initial_states',
            'initial_states_in_certificate', 'native_certificate_checker',
            'native_link_checker', 'preparation_seconds',
            'solve_and_internal_check_seconds', 'diagnostic_seconds')


class AuditError(Exception):
    pass


def require(ok, message):
    if not ok:
        raise AuditError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def unique(pairs):
    out = {}
    for key, value in pairs:
        require(key not in out, 'duplicate JSON key')
        out[key] = value
    return out


def read_json(path):
    return json.loads(path.read_bytes(), object_pairs_hook=unique)


def read_csv(path):
    with path.open(newline='') as f:
        return list(csv.DictReader(f))


def timestamp(value):
    # Preserve raw timestamps; Python 3.10 accepts only up to six fractional digits.
    return datetime.fromisoformat(re.sub(r'(\.\d{6})\d+(?=[+-])', r'\1', value))


def safe_path(base, relative):
    path = base / relative
    require(not Path(relative).is_absolute() and '..' not in Path(relative).parts,
            'non-relative manifest reference')
    require(path.resolve().is_relative_to(base.resolve()) and not path.is_symlink(),
            'manifest reference escapes root or is a symlink')
    return path


def canonical_maps():
    maps = [(f + '/build/frozen_manifest.json', '', 'files') for f in FAMILIES]
    maps += [(PC2 + '/v2/build/frozen_manifest.json', PC2, 'files'),
             (PC2 + '/validation_export/frozen_manifest.json', PC2 + '/validation_export', 'files'),
             (EXT + '/build/frozen_manifest.json', EXT, 'files'),
             (EXT + '/build/frozen_manifest.json', PC2, 'original_pc2_files')]
    return maps


def check_evidence(base, original_digest):
    """Verify registered measurements and freeze references under either root."""
    freeze_counts = {}
    for manifest_name, prefix, key in canonical_maps():
        mapping = read_json(base / manifest_name)[key]
        for name, expected in mapping.items():
            rel = str(Path(prefix) / name)
            require(original_digest(rel) == expected, 'frozen reference mismatch: ' + rel)
        freeze_counts[manifest_name + ':' + key] = len(mapping)
    ext_freeze = read_json(base / EXT / 'build/frozen_manifest.json')
    require(len(ext_freeze['files']) == 6 and len(ext_freeze['original_pc2_files']) == 25,
            'extended freeze must retain its 6 new and 25 original files')
    require(ext_freeze['jar_sha256'] == JAR_SHA, 'extended freeze JAR differs')

    counts_table = read_csv(base / 'integration/all_registered_run_counts.csv')
    declared = {row['family']: row for row in counts_table}
    series = FAMILIES + (PC2 + '/v2', EXT, XEON)
    require(len(declared) == len(counts_table) == 11 and set(declared) == set(series),
            'registered family inventory differs')
    totals = Counter()
    counted = []
    for family in series:
        summary = family + ('/tables/results.csv' if family.startswith(PC2) else '/summary.csv')
        rows = read_csv(base / summary)
        actual = Counter(row['status'] for row in rows)
        require(original_digest(summary) == declared[family]['summary_sha256'],
                'summary original digest differs: ' + family)
        require(int(declared[family]['trials']) == len(rows), 'trial count differs: ' + family)
        for status in set(actual) | (set(declared[family]) - {'family', 'trials', 'summary_sha256'}):
            require(actual[status] == int(declared[family].get(status, -1)),
                    'status census differs: ' + family + ':' + status)
        require(len({row['job_id'] for row in rows}) == len(rows), 'duplicate job: ' + family)
        if family != XEON:
            require((base / family / 'raw/runner_finished.json').is_file(), 'missing terminal marker: ' + family)
        if family in FAMILIES:
            expected = [job['id'] for job in read_json(base / family / 'config.json')['jobs']]
            require([row['job_id'] for row in rows] == expected, 'schedule differs: ' + family)
        elif family in (PC2 + '/v2', XEON):
            require([row['job_id'] for row in rows] == list(ORIGINAL_PC2_JOBS),
                    'PC2 original/received table order differs')
        for row in rows:
            if family in FAMILIES:
                raw = base / family / 'raw/series' / row['job_id']
                result = read_json(raw / 'result.json')
                require(result['decision'] == row['status'], 'raw result differs: ' + family + ':' + row['job_id'])
            else:
                raw = base / family / 'raw' / row['job_id']
            completion = read_json(raw / 'completion.json')
            require(completion['timed_out'] == (row['status'] == 'TO'), 'timeout metadata differs')
            if family == XEON:
                require(completion['exit_code'] is None and row['exit_code'] == '', 'unrecorded Xeon exit code was changed')
            else:
                require(completion['exit_code'] == int(row['exit_code']), 'exit code differs')
                require('files' in completion, 'Mac completion lacks its required raw digest map')
            for name, expected in completion.get('files', {}).items():
                rel = str((raw / name).relative_to(base))
                require(original_digest(rel) == expected, 'raw original digest differs: ' + rel)
        totals.update(actual)
        counted.append(dict(family=family, trials=len(rows), statuses=dict(actual)))
    require(sum(totals.values()) == 398 and totals == Counter(WIN=195, LOSS=197, TO=6),
            'expected 398 terminal trials (195 WIN, 197 LOSS, 6 TO)')

    config = read_json(base / EXT / 'config.json')
    require(config['heap'] == '32g' and config['timeout_seconds'] == 7200 and config['trials'] == 1,
            'extended budget differs')
    require([job['id'] for job in config['jobs']] == list(JOBS), 'extended order differs')
    extended_rows = read_csv(base / EXT / 'tables/results.csv')
    require([row['job_id'] for row in extended_rows] == list(JOBS), 'extended table order differs')
    previous_end = None
    for row in extended_rows:
        job = row['job_id']
        invocation = read_json(base / EXT / 'raw' / job / 'invocation.json')
        completion = read_json(base / EXT / 'raw' / job / 'completion.json')
        solver, merge = ('otf', 'transfers') if job == JOBS[0] else ('direct_full', 'none')
        require(row['status'] == 'TO' and row['exit_code'] == '-9', 'extended result must remain TO')
        require(all(row[key] == '' for key in EMPTY_TO), 'TO has unsupported numerical/certificate values')
        require(invocation['solver'] == solver and invocation['merge'] == merge and
                invocation['heap'] == '32g' and invocation['timeout_seconds'] == 7200 and
                invocation['jar_sha256'] == JAR_SHA, 'extended invocation differs')
        require('-Xmx32g' in invocation['command'] and
                '-Dmtsa.revised.otf.solver=' + solver in invocation['command'] and
                '-Dmtsa.otf.contractMerge=' + merge in invocation['command'], 'extended JVM properties differ')
        start, end = datetime.fromisoformat(invocation['at']), datetime.fromisoformat(completion['at'])
        require(previous_end is None or start >= previous_end, 'extended JVM intervals overlap')
        previous_end = end
        require(float(row['whole_jvm_seconds']) == completion['wall_seconds'] >= 7200 and end > start,
                'extended observed wall time differs')
        require(not (base / EXT / 'raw' / job / 'certificate_summary.json').exists(),
                'TO unexpectedly contains a returned certificate')
    comparison = read_csv(base / EXT / 'tables/host_budget_comparison.csv')
    require(len(comparison) == 5 and Counter(row['status'] for row in comparison) == Counter(WIN=1, TO=4),
            'old/new host-budget rows were lost or reclassified')
    key_fields = ('campaign', 'host', 'heap', 'timeout_seconds', 'job_id')
    expected_keys = [('original_v2', 'mac', '32g', '1200', job) for job in ORIGINAL_PC2_JOBS]
    expected_keys += [('extended_7200', 'mac', '32g', '7200', job) for job in JOBS]
    require([tuple(row[key] for key in key_fields) for row in comparison] == expected_keys,
            'host-budget campaign/host/heap/budget/job keys differ or repeat')
    old_rows = {row['job_id']: row for row in read_csv(base / PC2 / 'v2/tables/results.csv')}
    new_rows = {row['job_id']: row for row in extended_rows}
    shared_metrics = set(EMPTY_TO) | {'job_id', 'solver', 'merge', 'status', 'exit_code',
                                    'input_sha256', 'jar_sha256', 'whole_jvm_seconds', 'raw_directory'}
    for row in comparison:
        source = (old_rows if row['campaign'] == 'original_v2' else new_rows)[row['job_id']]
        require(all(row[key] == source[key] for key in shared_metrics.intersection(source)),
                'host-budget row differs from its original result row')
        if row['campaign'] == 'extended_7200':
            require(row == source, 'extended host-budget row is not identical to its result row')
        if row['status'] == 'TO':
            require(all(row[key] == '' for key in EMPTY_TO), 'host-budget TO has unsupported values')
    ready = read_json(base / EXT / 'build/final_tables_ready.json')
    require(ready['status'] == 'PASS' and ready['terminal'] is True and ready['native_latex'] == 'PASS'
            and ready['statuses'] == dict.fromkeys(JOBS, 'TO'), 'extended final readiness marker differs')
    refs = {EXT + '/validation/final_independent_audit.json': ready['independent_audit_sha256'],
            EXT + '/build/frozen_manifest.json': ready['frozen_manifest_sha256']}
    refs.update({EXT + '/' + k: v for k, v in ready['derived_script_sha256'].items()})
    refs.update({EXT + '/tables/' + k: v for k, v in ready['table_sha256'].items()})
    for name, expected in refs.items():
        require(original_digest(name) == expected, 'extended final report reference differs: ' + name)
    xeon = check_xeon_receipt(base, original_digest)
    return dict(trials=398, statuses=dict(totals), pending_measurements=0, series=counted,
                mac_trials=395, mac_statuses=dict(WIN=194, LOSS=197, TO=4), received_xeon=xeon,
                canonical_freeze_references=sum(freeze_counts.values()), freeze_maps=freeze_counts,
                extended_to_trials=2, protected_original_pc2_files=25, new_frozen_files=6,
                host_budget_rows=5, extended_native_latex='PASS')


def check_xeon_receipt(base, original_digest):
    """Keep receipt hashes and runtime provenance limitations separate from freezes."""
    root = base / XEON
    audit = read_json(root / 'validation/arrival_audit.json')
    manifest = read_json(root / 'validation/arrival_manifest.json')
    raw_manifest = read_json(root / 'validation/raw_sha256_manifest.json')
    require(audit['checks'] == 'PASS' and audit['status'] == 'PASS_WITH_PROVENANCE_LIMITATIONS' and
            audit['runtime_class_sha256'] is None and len(audit['limitations']) >= 2,
            'Xeon acceptance/provenance limitations missing')
    require(raw_manifest['schema'] == 'pc2-xeon-raw-sha256-v1' and
            raw_manifest['files'] == manifest['files'] and len(raw_manifest['files']) == 18, 'Xeon raw receipt map differs')
    require(set(raw_manifest['files']) == {str(p.relative_to(root)) for p in (root / 'raw').rglob('*') if p.is_file()},
            'Xeon raw inventory differs')
    for name, expected in raw_manifest['files'].items():
        require(original_digest(XEON + '/' + name) == expected, 'Xeon raw receipt digest differs: ' + name)
    references = {'validation/arrival_manifest.json': audit['arrival_manifest_sha256'],
                  audit['raw_sha256_manifest']: audit['raw_sha256_manifest_sha256'],
                  manifest['analysis_source']['path']: manifest['analysis_source']['sha256']}
    references.update(audit['table_sha256'])
    for name, expected in references.items():
        require(original_digest(XEON + '/' + name) == expected, 'Xeon derived/source reference differs: ' + name)
    archive = manifest['archive']
    require(archive['base'] == PC2 and archive['sha256'] == audit['archive_sha256'] ==
            '57fea735d884d3a30587fb2677497d16d8c2ad3a1efe10553f678955d8352666', 'Xeon arrival archive identity differs')
    archive_path = base / PC2 / archive['path']
    require(original_digest(PC2 + '/' + archive['path']) == archive['sha256'] and
            archive_path.stat().st_size == archive['bytes'], 'Xeon archive hash or bytes differ')
    with zipfile.ZipFile(archive_path) as z:
        names = {entry.filename.replace('\\', '/'): entry for entry in z.infolist() if not entry.is_dir()}
        require(len(names) == 18 and set(names) == set(raw_manifest['files']), 'Xeon archive entry set differs')
        for name, entry in names.items():
            require(z.read(entry) == safe_path(root, name).read_bytes(), 'Xeon archive entry/raw byte mismatch: ' + name)
    rows = read_csv(root / 'tables/results.csv')
    require([r['job_id'] for r in rows] == list(ORIGINAL_PC2_JOBS), 'Xeon comparison order differs')
    times = {}
    for row in rows:
        job = row['job_id']
        inv = read_json(root / 'raw' / job / 'invocation.json')
        end = read_json(root / 'raw' / job / 'completion.json')
        solver, merge = ('direct_full', 'none') if job == 'direct_full_none' else ('otf', 'transfers' if job == 'lazy_transfers' else 'none')
        require((row['campaign'], row['host'], row['heap'], row['timeout_seconds'], row['trial']) ==
                ('xeon_20260929_2344', 'xeon', '200g', '7200', '1'), 'Xeon row host/budget differs')
        require(inv['cell'] == end['cell'] == job and inv['solver'] == solver and inv['merge'] == merge and
                inv['heap'] == end['heap'] == '200g' and inv['timeout_seconds'] == end['timeout_seconds'] == 7200,
                'Xeon invocation identity differs')
        require(inv['jar_sha256'].lower() == row['jar_sha256'] == JAR_SHA and
                inv['input_sha256'].lower() == row['input_sha256'] == audit['input_sha256'], 'Xeon fixed hashes differ')
        require(end['exit_code'] is None and row['exit_code'] == '' and row['exit_code_availability'] == 'not_recorded_null',
                'Xeon missing exit code was imputed')
        require(float(row['whole_jvm_seconds']) == end['wall_seconds'] and int(row['peak_rss_bytes']) == end['peak_rss_bytes'] and
                float(row['peak_rss_gib']) == end['peak_rss_gib'] == round(end['peak_rss_bytes'] / 2**30, 2), 'Xeon time/RSS differs')
        times[job] = (timestamp(inv['at']), timestamp(end['at']))
        if job == 'lazy_none':
            require(row['status'] == 'WIN' and end['timed_out'] is False, 'Xeon fine verdict differs')
            diagnostic = read_json(root / 'raw/lazy_none/certificate_summary.json')
            mac = read_json(base / PC2 / 'v2/raw/lazy_none/certificate_summary.json')
            require({k: v for k, v in diagnostic.items() if k != 'diagnostic_seconds'} ==
                    {k: v for k, v in mac.items() if k != 'diagnostic_seconds'}, 'Xeon/Mac WIN diagnostic differs')
            mapping = {'states_discovered': 'states_discovered', 'successor_queries': 'successor_queries',
                       'worst_completion_rank': 'worst_completion_rank', 'certificate_states': 'certificate_states',
                       'materialized_transition_outcomes': 'materialized_transitions'}
            require(all(row[key] == str(diagnostic[value]) for key, value in mapping.items()), 'Xeon WIN table/diagnostic differs')
            require(row['native_certificate_checker'] == row['native_link_checker'] == 'passed', 'Xeon native checker fields differ')
        else:
            require(row['status'] == 'TO' and end['timed_out'] is True and end['wall_seconds'] >= 7200 and
                    all(row[key] == '' for key in EMPTY_TO), 'Xeon TO was completed or assigned unsupported values')
    actual_order = ('lazy_transfers', 'direct_full_none', 'lazy_none')
    require(all(times[a][1] <= times[b][0] for a, b in zip(actual_order, actual_order[1:])), 'Xeon invocation intervals overlap')
    comparison = read_csv(root / 'tables/host_budget_comparison.csv')
    mac_rows = read_csv(base / EXT / 'tables/host_budget_comparison.csv')
    require(len(comparison) == 8 and comparison[5:] == rows, 'Xeon eight-row comparison differs')
    for row, mac in zip(comparison[:5], mac_rows):
        require(all(row[key] == value for key, value in mac.items()) and
                all(value == '' for key, value in row.items() if key not in mac), 'Inherited Mac comparison row differs')
    return dict(trials=3, statuses=dict(WIN=1, TO=2), pending=0, raw_digest_references=18, combined_host_budget_rows=8,
                exit_codes='All unrecorded/null; preserved as empty CSV values.', runtime_class_sha256=None,
                distributed_class_sha256=audit['distributed_class_sha256'], acceptance='PASS_WITH_PROVENANCE_LIMITATIONS')


def inventory():
    retained = set()
    for directory, dirs, names in os.walk(E6):
        dirs[:] = [name for name in dirs if name not in ('public_exports', '__pycache__')]
        for name in names:
            path = Path(directory) / name
            rel = path.relative_to(E6)
            if name in ('.DS_Store', 'jvm.lock') or path.suffix == '.pyc' or (path.suffix == '.tmp' and 'raw' not in rel.parts):
                continue
            if rel.parent == Path('integration') and name.startswith(('anonymity_scan_', 'anonymity_review_')):
                continue
            require(path.suffix != '.jar' and not path.is_symlink(), 'unapproved JAR or symlink')
            retained.add(str(rel))
    return retained


def transformed(value, replacements):
    if isinstance(value, str):
        for old, new in replacements:
            value = value.replace(old, new)
        return value
    if isinstance(value, list):
        return [transformed(item, replacements) for item in value]
    if isinstance(value, dict):
        pairs = [(transformed(k, replacements), transformed(v, replacements)) for k, v in value.items()]
        return unique(pairs)
    return value


def check_snapshot(snapshot):
    require(snapshot.name != 'evidence_20260929_v3', 'v3 is outside this new audit scope')
    require(snapshot.resolve().parent == (E6 / 'public_exports').resolve(), 'snapshot must be an existing E6 public export')
    require({p.name for p in snapshot.iterdir()} == {'e6', 'README.md', 'PUBLIC_COPY_MANIFEST.json'}, 'unexpected snapshot root files')
    manifest = read_json(snapshot / 'PUBLIC_COPY_MANIFEST.json')
    require(manifest['schema'] == 'e6-anonymous-copy-v1' and manifest['solver_jar_sha256'] == JAR_SHA
            and manifest['solver_jar_included'] is False, 'public manifest identity differs')
    entries = {row['path']: row for row in manifest['files']}
    require(len(entries) == len(manifest['files']), 'duplicate public manifest path')
    require(set(entries) == {'e6/' + rel for rel in inventory()}, 'current original/snapshot inventory differs')
    require(set(entries) == {str(p.relative_to(snapshot)) for p in (snapshot / 'e6').rglob('*') if p.is_file()},
            'public inventory differs')
    replacements = [(str(E6), '${E6_ROOT}'), (str(E6.parents[3]), '${PROJECT_ROOT}'), (str(Path.home()), '${HOME}')]
    hostname = socket.gethostname()
    if hostname and hostname.lower() not in ('localhost', 'unknown', 'mac'):
        replacements.append((hostname, '${HOSTNAME}'))
    counts = Counter()
    for rel, row in entries.items():
        original = safe_path(E6, str(Path(rel).relative_to('e6'))).read_bytes()
        public_path = safe_path(snapshot, rel)
        public = public_path.read_bytes()
        require(sha(original) == row['original_sha256'] and sha(public) == row['public_sha256']
                and len(public) == row['bytes'], 'file digest or length differs: ' + rel)
        expected = original
        if public_path.suffix in TEXT:
            for old, new in replacements:
                expected = expected.replace(old.encode(), new.encode())
        require(public == expected and row['path_redacted'] == (original != public), 'non-path change: ' + rel)
        if public != original and public_path.suffix == '.json':
            require(transformed(json.loads(original, object_pairs_hook=unique), replacements) ==
                    json.loads(public, object_pairs_hook=unique), 'JSON transformation differs: ' + rel)
        if public != original and public_path.suffix == '.csv':
            require(transformed(list(csv.reader(io.StringIO(original.decode()))), replacements) ==
                    list(csv.reader(io.StringIO(public.decode()))), 'CSV transformation differs: ' + rel)
        critical = '/inputs/' in rel or public_path.suffix == '.class' or public_path.name in (
            'result.json', 'certificate.json', 'certificate_summary.json')
        require(not critical or original == public, 'critical evidence bytes differ: ' + rel)
        counts['files'] += 1
        counts['path_redacted'] += original != public
        counts['critical_byte_identical'] += critical
        counts['raw_files_preserved'] += '/raw/' in rel
        if public_path.name == 'completion.json':
            for name, expected_sha in read_json(public_path).get('files', {}).items():
                target = str(Path(rel).parent / name)
                require(target in entries and entries[target]['original_sha256'] == expected_sha,
                        'retained completion reference differs: ' + rel)
                counts['completion_original_digest_references'] += 1
        if public_path.name == 'result.json':
            data = read_json(public_path)
            if 'certificate_sha256' in data:
                target = str(Path(rel).parent / 'certificate.json')
                require(entries[target]['original_sha256'] == data['certificate_sha256'], 'certificate reference differs')
                counts['certificate_original_digest_references'] += 1
    def original_digest(rel):
        return entries['e6/' + rel]['original_sha256']
    evidence = check_evidence(snapshot / 'e6', original_digest)
    return dict(snapshot=snapshot.name, manifest_sha256=sha((snapshot / 'PUBLIC_COPY_MANIFEST.json').read_bytes()),
                snapshot_checks=dict(counts), measurements=evidence,
                privacy_scope='Literal path/hostname transformation and byte preservation only. Identity/PDF semantic review remains separately required; prior PDF exceptions must match exact digests.')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument('--source-only', action='store_true', help='Preparation only; makes no public-copy claim')
    mode.add_argument('--snapshot', type=Path, help='Existing new snapshot to audit, never created here')
    ap.add_argument('--output', type=Path, required=True, help='Create-only report outside public_exports')
    args = ap.parse_args()
    output = args.output.resolve()
    require(output.parent == E6 / 'integration' and not output.exists(), 'report must be new and directly under integration')
    report = dict(schema='e6-v4-independent-audit-v1', at=datetime.now(ZoneInfo('Asia/Tokyo')).isoformat(),
                  mode='source_preparation' if args.source_only else 'existing_snapshot',
                  auditor_sha256=sha(Path(__file__).read_bytes()), no_jvm=True, no_copy_created=True)
    try:
        if args.source_only:
            report['measurements'] = check_evidence(E6, lambda rel: sha(safe_path(E6, rel).read_bytes()))
            report['scope'] = 'Read-only source preparation; v3 was not read and v4 has not been audited.'
        else:
            report.update(check_snapshot(args.snapshot.resolve()))
        report['status'] = 'PASS'
    except Exception as exc:
        report['status'] = 'FAIL'
        report['error_type'] = type(exc).__name__
        # Do not serialize arbitrary exception text containing private local paths.
        report['reason'] = str(exc) if isinstance(exc, AuditError) else 'Unexpected audit error; inspect locally.'
    with output.open('x') as f:
        json.dump(report, f, indent=2)
        f.write('\n')
    print(json.dumps(dict(status=report['status'], mode=report['mode'], report=output.name)))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
