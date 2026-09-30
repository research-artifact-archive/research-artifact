#!/usr/bin/env python3
"""Read-only receipt validation and create-only derived Xeon tables. No JVM."""
import csv
import hashlib
import io
import json
import re
import zipfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parents[1]
PC2 = HERE.parent
E6 = PC2.parent
EXPERIMENTS = E6.parents[1]
RAW = HERE / 'raw'
ZIP = PC2 / 'xeon-raw-pc2rolling-20260929-2344.zip'
PACKAGE = EXPERIMENTS / 'rq3_xeon/fg-ducs-xeon-campaign-pc2rolling.zip'
ZIP_SHA = '57fea735d884d3a30587fb2677497d16d8c2ad3a1efe10553f678955d8352666'
JAR_SHA = 'ff1e6b176f004ea85f1e99690a90388a6a4d24f44cd8d8e636fcd9337dcf67d5'
LTS_SHA = 'ef731ff57935d5a880fb23cdef264c034378bf4954c1345d6b2fb5431c866a86'
CLASS_SHA = '0314a378d0ba6c03605f483f1dd28c1aa386426fc15ec71df1aa440079d3b6ae'
JOBS = ('lazy_none', 'lazy_transfers', 'direct_full_none')
EXECUTION_ORDER = ('lazy_transfers', 'direct_full_none', 'lazy_none')
RSS_SCOPE = 'Maximum sampled Windows Process.WorkingSet64; 500-ms polling; GiB = bytes / 2^30.'
LIMITATIONS = [
    'All three completion exit_code fields are null; no numerical exit code is inferred.',
    'Runtime class digest was not recorded or verified by the Xeon launcher. The distributed class is byte-identical to the fixed Mac class; this does not attest the runtime class bytes.',
    'JAR and input identities are recorded in environment/invocation and are checked by the supplied launcher; no new remote filesystem verification was performed.',
    'Peak RSS is the maximum sampled working set, not an exact continuous maximum or a Java-heap measurement.',
    'Xeon WIN is accepted from its recorded native certificate and Link passes plus returned diagnostic and transition export. No new synthesis or checker JVM was run; the full Mac validation export remains a separate artifact.',
    'This arrival manifest hashes received bytes after receipt; it is not a retrospective pre-execution freeze.'
]


def require(ok, reason):
    if not ok:
        raise AssertionError(reason)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def timestamp(value):
    # Python 3.10 accepts microseconds; the original seven-digit strings are retained.
    return datetime.fromisoformat(re.sub(r'(\.\d{6})\d+(?=[+-])', r'\1', value))


def metrics(path):
    lines = path.read_text(encoding='utf-8-sig').splitlines()
    heads = [i for i, s in enumerate(lines) if s.startswith('mode,result,solver_status,verification_status,')]
    if not heads:
        return {}
    tail = []
    for line in lines[heads[-1]:]:
        if not line or line.startswith('='):
            break
        tail.append(line)
    return {r['metric_key']: r['value'] for r in csv.DictReader(tail)}


def csv_bytes(rows, fields):
    out = io.StringIO(newline='')
    writer = csv.DictWriter(out, fields, lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue().encode()


def main():
    targets = ['validation/arrival_manifest.json', 'validation/raw_sha256_manifest.json', 'validation/arrival_audit.json',
               'tables/results.csv', 'tables/host_budget_comparison.csv', 'README.md']
    require(not any((HERE / name).exists() for name in targets), 'Create-only outputs already exist')
    files = {str(p.relative_to(HERE)): digest(p) for p in sorted(RAW.rglob('*')) if p.is_file()}
    require(len(files) == 18, 'Unexpected raw file count')
    require(digest(ZIP) == ZIP_SHA, 'Arrival ZIP digest differs')
    with zipfile.ZipFile(ZIP) as z:
        names = {i.filename.replace('\\', '/'): i for i in z.infolist() if not i.is_dir()}
        require(len(names) == len(z.infolist()) == 18 and set(names) == set(files), 'ZIP/raw inventory differs')
        for name, info in names.items():
            require('..' not in Path(name).parts and z.read(info) == (HERE / name).read_bytes(), 'ZIP entry bytes differ')
    package_matches = {}
    with zipfile.ZipFile(PACKAGE) as z:
        for name, expected in {
            'ablation_20260928/jars/e1.jar': JAR_SHA,
            'pc2_rolling_xeon/inputs/ProductionCell_Arms2_Calibration.lts': LTS_SHA,
            'pc2_rolling_xeon/classes/ltsa/updatingControllers/cli/Pc2DiagnosticRunner.class': CLASS_SHA,
        }.items():
            h = hashlib.sha256()
            with z.open(name) as f:
                for block in iter(lambda: f.read(1024 * 1024), b''):
                    h.update(block)
            require(h.hexdigest() == expected, 'Distributed package fixed identity differs')
            package_matches[name] = expected
        launcher = z.read('run-pc2rolling.ps1')
        require(launcher == (EXPERIMENTS / 'rq3_xeon/run-pc2rolling.ps1').read_bytes(), 'Distributed launcher differs')
    require(digest(PC2 / 'build/classes/ltsa/updatingControllers/cli/Pc2DiagnosticRunner.class') == CLASS_SHA,
            'Original Mac class differs')
    require(digest(PC2 / 'v2/inputs/ProductionCell_Arms2_Calibration.lts') == LTS_SHA, 'Original Mac input differs')
    env = read(RAW / 'environment.json')
    require(env['heap'] == '200g' and env['timeout_seconds'] == 7200 and
            env['jar_sha256'].lower() == JAR_SHA and env['lts_sha256'].lower() == LTS_SHA, 'Environment differs')
    require('17.0.20.1' in env['java_version'] and 'Xeon' in env['cpu'], 'Environment identity missing')
    # These are documented observations of the existing launcher, not launcher edits.
    require(b'$p.WorkingSet64' in launcher and b'Start-Sleep -Milliseconds 500' in launcher and
            b'[math]::Round($peak / 1GB, 2)' in launcher, 'RSS definition cannot be established')
    existing = PC2 / 'extended_7200/tables/host_budget_comparison.csv'
    old_bytes = existing.read_bytes()
    old_rows = list(csv.DictReader(io.StringIO(old_bytes.decode())))
    require(len(old_rows) == 5, 'Expected five existing Mac host/budget rows')
    fields = list(old_rows[0]) + ['peak_rss_bytes', 'peak_rss_gib', 'rss_scope', 'exit_code_availability',
                                'runtime_class_hash_availability', 'source_zip_sha256']
    rows, details, times = [], [], {}
    for job in JOBS:
        directory = RAW / job
        inv, end = read(directory / 'invocation.json'), read(directory / 'completion.json')
        solver, merge = ('direct_full', 'none') if job == 'direct_full_none' else ('otf', 'transfers' if job == 'lazy_transfers' else 'none')
        require(inv['cell'] == end['cell'] == job and inv['solver'] == solver and inv['merge'] == merge, 'Job identity differs')
        require(inv['host'] == 'xeon' and inv['heap'] == end['heap'] == '200g' and
                inv['timeout_seconds'] == end['timeout_seconds'] == 7200 and inv['timeout_scope'] == 'whole JVM', 'Budget differs')
        require(inv['jar_sha256'].lower() == JAR_SHA and inv['input_sha256'].lower() == LTS_SHA, 'Invocation fixed hash differs')
        require('-Xmx200g' in inv['command'] and '-Dmtsa.revised.otf.solver=' + solver in inv['command'] and
                '-Dmtsa.otf.contractMerge=' + merge in inv['command'], 'Actual command properties differ')
        require('-Dmtsa.otf.lazyControllableBuckets=' + ('false' if solver == 'direct_full' else 'true') in inv['command'],
                'Solver bucket setting differs')
        require(all(p in inv['command'] for p in ['-Dmtsa.otf.guidedStateLimit=0', '-Dmtsa.otf.guidedQueryLimit=0',
                                                '-Dmtsa.otf.controllableActionOrder=endpoint_guided']), 'Search properties differ')
        require(end['exit_code'] is None, 'Unexpected exit-code recording; inspect rather than reinterpret')
        require(round(end['peak_rss_bytes'] / 2**30, 2) == end['peak_rss_gib'], 'RSS byte/GiB mismatch')
        times[job] = (timestamp(inv['at']), timestamp(end['at']))
        require(times[job][1] > times[job][0] and abs((times[job][1] - times[job][0]).total_seconds() - end['wall_seconds']) < 1,
                'Invocation/completion wall time differs materially')
        m = metrics(directory / 'output.txt')
        completed = not end['timed_out']
        diagnostic = read(directory / 'certificate_summary.json') if completed else {}
        if completed:
            require(job == 'lazy_none' and diagnostic['decision'] == 'WIN' and m['revised_decision'] == 'realizable', 'Completed verdict differs')
            require(m['revised_internal_certificate_check'] == m['revised_link_checker'] == 'passed', 'Native checker/Link missing')
            require(diagnostic['certificate_checker'].startswith('PASS') and diagnostic['link_checker'].startswith('PASS'), 'Diagnostic checker/Link missing')
            pairs = {'states_discovered': 'revised_semantic_states_discovered', 'successor_queries': 'revised_successor_oracle_calls_cumulative',
                     'materialized_transitions': 'revised_materialized_transition_outcomes_cumulative', 'worst_completion_rank': 'revised_worst_completion_rank'}
            require(all(str(diagnostic[k]) == m[v] for k, v in pairs.items()), 'Diagnostic/CLI metrics differ')
            mac = read(PC2 / 'v2/raw/lazy_none/certificate_summary.json')
            require({k: v for k, v in diagnostic.items() if k != 'diagnostic_seconds'} ==
                    {k: v for k, v in mac.items() if k != 'diagnostic_seconds'}, 'Mac/Xeon diagnostic differs beyond time')
            require((directory / 'transitions.txt').read_text() == (PC2 / 'v2/raw/lazy_none/transitions.txt').read_text(),
                    'Mac/Xeon transition exports differ after line-ending normalization')
        else:
            require(job != 'lazy_none' and end['wall_seconds'] >= 7200 and not m and
                    not (directory / 'certificate_summary.json').exists(), 'TO contains unexpected completion evidence')
        def count(key):
            return diagnostic.get(key, '') if completed else ''
        row = dict.fromkeys(fields, '')
        row.update(campaign=HERE.name, host='xeon', heap='200g', timeout_seconds=7200, trial=1, job_id=job,
                   solver='direct_full' if solver == 'direct_full' else 'lazy', merge=merge, status='WIN' if completed else 'TO',
                   raw_diagnostic_decision='WIN' if completed else '', expected_decision='WIN' if job != 'lazy_transfers' else 'LOSS',
                   expectation_check='PASS' if completed else 'NOT_APPLICABLE_OR_INCOMPLETE',
                   states_discovered=count('states_discovered'), successor_queries=count('successor_queries'),
                   materialized_transition_outcomes=count('materialized_transitions'), enabled_buckets_availability='Not directly instrumented by the fixed E1 CLI.',
                   worst_completion_rank=count('worst_completion_rank'), losing_region_states=count('losing_region_states'),
                   certificate_states=count('certificate_states'), safe_region_states=count('safe_region_states'), unsafe_region_states=count('unsafe_region_states'),
                   initial_states=count('initial_states'), initial_states_in_certificate=count('initial_states_in_region'),
                   native_certificate_checker=m.get('revised_internal_certificate_check', ''), native_link_checker=m.get('revised_link_checker', ''),
                   preparation_seconds=float(m['revised_preparation_time']) / 1000 if completed else '',
                   solve_and_internal_check_seconds=float(m['revised_solve_and_internal_check_time']) / 1000 if completed else '',
                   diagnostic_seconds=count('diagnostic_seconds'), whole_jvm_seconds=end['wall_seconds'], started_at=inv['at'], finished_at=end['at'],
                   input_sha256=LTS_SHA, jar_sha256=JAR_SHA, exit_code='', raw_directory=HERE.name + '/raw/' + job,
                   validation='PASS_WITH_PROVENANCE_LIMITATIONS' if completed else 'INCOMPLETE_WITH_PROVENANCE_LIMITATIONS',
                   reason='Recorded native E1 WIN certificate and Link passed; exit code was not recorded.' if completed else
                   'Whole JVM exceeded 7200 seconds and was recorded timed_out=true; no completed decision/certificate is inferred; exit code was not recorded.',
                   peak_rss_bytes=end['peak_rss_bytes'], peak_rss_gib=end['peak_rss_gib'], rss_scope=RSS_SCOPE,
                   exit_code_availability='not_recorded_null', runtime_class_hash_availability='not_recorded; distributed_class_matches_fixed', source_zip_sha256=ZIP_SHA)
        rows.append(row)
        details.append(dict(job_id=job, status=row['status'], exit_code=None, timed_out=end['timed_out'],
                            wall_seconds=end['wall_seconds'], peak_rss_bytes=end['peak_rss_bytes'], peak_rss_gib=end['peak_rss_gib']))
    require(all(times[a][1] <= times[b][0] for a, b in zip(EXECUTION_ORDER, EXECUTION_ORDER[1:])), 'Xeon jobs overlap or differ in order')
    require(existing.read_bytes() == old_bytes and all(digest(HERE / name) == expected for name, expected in files.items()), 'Input evidence changed during collection')
    manifest = dict(schema='pc2-xeon-arrival-manifest-v1', created_at=datetime.now(ZoneInfo('Asia/Tokyo')).isoformat(),
                    files=files, files_base='pc2_rolling/xeon_20260929_2344',
                    archive={'base': 'pc2_rolling', 'path': ZIP.name, 'sha256': ZIP_SHA, 'bytes': ZIP.stat().st_size},
                    analysis_source={'path': 'validation/accept_and_tabulate.py', 'sha256': digest(Path(__file__))},
                    scope='Receipt-time hashes of unchanged incoming bytes; not a pre-execution freeze.')
    payloads = {'tables/results.csv': csv_bytes(rows, fields),
                'tables/host_budget_comparison.csv': csv_bytes([{**dict.fromkeys(fields, ''), **r} for r in old_rows] + rows, fields)}
    report = dict(schema='pc2-xeon-arrival-audit-v1', status='PASS_WITH_PROVENANCE_LIMITATIONS', checks='PASS',
                  at=datetime.now(ZoneInfo('Asia/Tokyo')).isoformat(), archive_sha256=ZIP_SHA, raw_files=18, zip_entry_bytes_match=True,
                  jar_sha256=JAR_SHA, input_sha256=LTS_SHA, distributed_class_sha256=CLASS_SHA, runtime_class_sha256=None,
                  distributed_package_sha256=digest(PACKAGE), distributed_package_files=package_matches,
                  launcher_sha256=hashlib.sha256(launcher).hexdigest(), analysis_source_sha256=digest(Path(__file__)),
                  host='xeon', heap='200g', timeout_seconds=7200, trials=3, execution_order=list(EXECUTION_ORDER), table_order=list(JOBS),
                  statuses={'WIN': 1, 'TO': 2}, pending=0, cells=details, mac_win_diagnostic_equal_except_diagnostic_seconds=True,
                  mac_win_transition_export_equal_after_line_ending_normalization=True, rss_scope=RSS_SCOPE, limitations=LIMITATIONS,
                  prior_mac_comparison_sha256=hashlib.sha256(old_bytes).hexdigest(),
                  table_sha256={k: hashlib.sha256(v).hexdigest() for k, v in payloads.items()},
                  no_new_jvm=True, raw_unchanged=True)
    payloads['validation/arrival_manifest.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
    raw_manifest = dict(schema='pc2-xeon-raw-sha256-v1', files=files,
                        files_base='pc2_rolling/xeon_20260929_2344',
                        archive_sha256=ZIP_SHA, scope='Receipt-time hashes; source raw bytes are unchanged.')
    payloads['validation/raw_sha256_manifest.json'] = (json.dumps(raw_manifest, indent=2) + '\n').encode()
    report['arrival_manifest_sha256'] = hashlib.sha256(payloads['validation/arrival_manifest.json']).hexdigest()
    report['raw_sha256_manifest'] = 'validation/raw_sha256_manifest.json'
    report['raw_sha256_manifest_sha256'] = hashlib.sha256(payloads['validation/raw_sha256_manifest.json']).hexdigest()
    payloads['validation/arrival_audit.json'] = (json.dumps(report, indent=2) + '\n').encode()
    payloads['README.md'] = ('''# Received PC2 Xeon trials

This directory preserves the 18 received raw files byte-for-byte from `../xeon-raw-pc2rolling-20260929-2344.zip` (SHA-256 `''' + ZIP_SHA + '''`). The receipt manifest is post-execution provenance, not a retrospective experiment freeze. No JVM or remote operation was performed during acceptance.

The three single trials used Xeon / `-Xmx200g` / a 7,200-second whole-JVM limit. Execution order was `lazy_transfers`, `direct_full_none`, `lazy_none`; the tables use `lazy_none`, `lazy_transfers`, `direct_full_none` for comparison. The received outcomes are WIN / TO / TO in table order. The WIN reports 6,639 discovered states, 134,128 queries, rank 37, and native certificate/Link passes, agreeing with Mac; the complete certificate-summary structure differs only in diagnostic time. Exported transitions agree after CRLF/LF normalization. TO is not LOSS.

`tables/results.csv` has three Xeon rows. `tables/host_budget_comparison.csv` retains all five existing Mac rows and appends the three Xeon rows; its first columns retain the extended-series schema. Appended columns are `peak_rss_bytes`, `peak_rss_gib`, `rss_scope`, `exit_code_availability`, `runtime_class_hash_availability`, and `source_zip_sha256`. Their values are empty on inherited Mac rows. Trial/host/heap/budget/campaign always distinguish measurements; no cross-host timing speedup is inferred.

All three completion exit codes are JSON null and stay empty in CSV. WIN is supported by the completed native output and diagnostic, not an inferred exit code. The distributed JAR/LTS/class match fixed identities, and the launcher records/checks JAR/LTS; however, runtime class SHA was neither recorded nor checked. This limitation is retained. The JSON files may have a UTF-8 BOM; acceptance strips it only for parsing and leaves their bytes unchanged.

The raw `peak_rss_*` fields mean maximum sampled Windows `Process.WorkingSet64`, polled at 500 ms, not a continuously measured peak or JVM heap. GiB = bytes / 2^30, rounded to two decimals in the received metadata. Whole-JVM seconds and sampled RSS remain available for TO, while decision/state/query/rank/certificate/solver-time fields stay empty. The Java-version capture includes PowerShell's native-stderr wrapper; it contains the Temurin 17.0.20.1 version output and is not reinterpreted as a failed measurement. Original seven-digit fractional timestamps are retained; order checks truncate to six digits only while parsing under Python 3.10. The initial parser failure and source are preserved in `validation/`.

`validation/arrival_audit.json` records checks and provenance limitations. `validation/arrival_manifest.json` binds received raw bytes, ZIP digest, and this collector source. Original Mac tables, raw, frozen source, and JAR were not edited. This is a separate received platform series, adding three trials to Mac's 395 (total 398: 195 WIN, 197 LOSS, 6 TO; pending zero).
''').encode()
    for name, data in payloads.items():
        path = HERE / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as f:
            f.write(data)
    print(json.dumps(dict(status=report['status'], checks='PASS', rows=3, comparison_rows=8, raw_files=18, statuses=report['statuses'])))


if __name__ == '__main__':
    main()
