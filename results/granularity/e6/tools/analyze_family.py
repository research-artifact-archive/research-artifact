#!/usr/bin/env python3
"""Fresh-process E6 aggregation. Expected outcomes never fill missing measurements."""
import csv
import datetime as dt
import hashlib
import json
from collections import Counter
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
E6 = Path(__file__).resolve().parent.parent
JAR_SHA = 'ff1e6b176f004ea85f1e99690a90388a6a4d24f44cd8d8e636fcd9337dcf67d5'
METRICS = ['states_discovered','states_expanded','successor_queries','materialized_transitions',
           'enabled_buckets','worst_completion_rank','losing_region_states','certificate_states','linked_states',
           'preparation_seconds','solver_seconds','checking_and_link_seconds',
           'certificate_checker','link_checker','endpoint_checker']


def read(path): return json.loads(path.read_text())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def tex(value): return str(value).replace('_', r'\_').replace('&', r'\&')


def csv_write(path, rows, fields=None):
    fields = fields or list(dict.fromkeys(key for row in rows for key in row))
    tmp = path.with_suffix(path.suffix+'.tmp')
    with tmp.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields);writer.writeheader();writer.writerows(rows)
    tmp.replace(path)


def collect(family):
    config = read(family/'config.json');manifest = read(family/'build/frozen_manifest.json')
    rows = [];issues = [];loss_rows = []
    terminal = (family/'raw/runner_finished.json').exists() or (family/'raw/deadline_reached.json').exists()
    for index, job in enumerate(manifest['schedule'], 1):
        directory = family/'raw/series'/job['id'];input_file = family/job['input']
        row = dict(schedule_index=index, family=config['family'], version=config['version'], job_id=job['id'],
                   parameters=json.dumps(job.get('parameters', {}), sort_keys=True), input=job['input'],
                   merge=job['merge'], solver=job['solver'], expected_decision=job.get('expected_decision',''),
                   status='NOT_RUN_DEADLINE' if terminal else 'NOT_RUN', decision='NOT_RUN_DEADLINE' if terminal else 'NOT_RUN',
                   expected_check='NOT_COMPARABLE', **{m:'' for m in METRICS}, wall_seconds='', exit_code='',
                   input_sha256=manifest['files'][str(input_file.relative_to(E6))], jar_sha256=JAR_SHA,
                   frozen_manifest_sha256=sha(family/'build/frozen_manifest.json'), started_at='', finished_at='',
                   reason='', loss_summary='', result_file='', certificate_file='', validation_errors='')
        if directory.exists():
            errors = []
            invocation = read(directory/'invocation.json');row['started_at'] = invocation['started_at']
            if invocation['job'] != job: errors.append('Invocation job mismatch.')
            for field in ('input_sha256','jar_sha256','frozen_manifest_sha256'):
                if invocation[field] != row[field]: errors.append(field+' mismatch.')
            if invocation['heap'] != config['heap'] or invocation['timeout_seconds'] != config['timeout_seconds']:
                errors.append('Invocation budget mismatch.')
            if not (directory/'completion.json').exists():
                row.update(status='RUNNING', decision='RUNNING')
            else:
                completion = read(directory/'completion.json')
                row.update(wall_seconds=completion['wall_seconds'], exit_code=completion['exit_code'], finished_at=completion['finished_at'])
                for filename, expected in completion['files'].items():
                    if not (directory/filename).is_file() or sha(directory/filename) != expected:
                        errors.append('Raw digest mismatch: '+filename)
                row.update(status='TO' if completion['timed_out'] else 'ERROR', decision='TO' if completion['timed_out'] else 'ERROR')
                row['reason'] = 'Whole-JVM timeout; no partial synthesis metrics adopted.' if completion['timed_out'] else completion.get('exception') or ''
                if not completion['timed_out'] and (directory/'result.json').exists():
                    data = read(directory/'result.json')
                    if data.get('merge') != job['merge'] or data.get('solver') != job['solver']: errors.append('Result variant mismatch.')
                    if data.get('jar_sha256') != JAR_SHA: errors.append('Result JAR mismatch.')
                    if data.get('input_sha256') != row['input_sha256']: errors.append('Result input digest mismatch.')
                    if data.get('decision') not in ('WIN', 'LOSS'): errors.append('Missing checked decision.')
                    if completion['exit_code'] not in (0,2): errors.append('Unexpected JVM exit code.')
                    if data.get('certificate_checker') != 'PASS': errors.append('Certificate checker did not pass.')
                    if data.get('endpoint_checker') != 'PASS': errors.append('Endpoint checker did not pass.')
                    if data.get('decision') == 'WIN' and data.get('link_checker') != 'PASS': errors.append('Link checker did not pass.')
                    if not (directory/'certificate.json').exists(): errors.append('Certificate artifact absent.')
                    elif data.get('certificate_sha256') != sha(directory/'certificate.json'): errors.append('Certificate digest mismatch.')
                    if not errors:
                        row.update(status=data['decision'], decision=data['decision'], result_file=str((directory/'result.json').relative_to(family)),
                                   certificate_file=str((directory/'certificate.json').relative_to(family)))
                        for m in METRICS: row[m] = data.get(m) if data.get(m) is not None else ''
                        row['loss_summary'] = json.dumps(data['loss_summary'], sort_keys=True) if data.get('loss_summary') else ''
                        row['reason'] = data.get('loss_reason', 'Checked '+data['decision']+' certificate.')
                        row['expected_check'] = 'PASS' if row['decision'] == row['expected_decision'] else 'FAIL'
                        if row['decision'] == 'LOSS':
                            loss_rows.append(dict(job_id=job['id'], parameters=row['parameters'], merge=job['merge'], solver=job['solver'],
                                                  losing_region_states=row['losing_region_states'], reason=row['reason'], loss_summary=row['loss_summary'],
                                                  certificate_file=row['certificate_file'], result_file=row['result_file']))
                elif not completion['timed_out'] and not row['reason']:
                    row['reason'] = 'JVM produced no result JSON; see preserved stdout/stderr.'
            if errors:
                row.update(status='INVALID', decision='INVALID', validation_errors='; '.join(errors))
                issues.append({'job':job['id'], 'issues':errors})
        rows.append(row)
    tables = family/'tables';tables.mkdir(parents=True, exist_ok=True)
    csv_write(family/'summary.csv', rows);csv_write(tables/'results.csv', rows)
    csv_write(tables/'loss_reasons.csv', loss_rows, ['job_id','parameters','merge','solver','losing_region_states','reason','loss_summary','certificate_file','result_file'])
    summary = dict(provisional=any(r['decision'] in ('NOT_RUN','RUNNING') for r in rows), scheduled=len(rows),
                   decision_counts=dict(Counter(r['decision'] for r in rows)),
                   expectation_mismatches=[r['job_id'] for r in rows if r['expected_check']=='FAIL'], validation_errors=issues,
                   updated_at=dt.datetime.now(dt.timezone.utc).isoformat(),
                   metric_scope='Completed checked trials only. TO/ERROR/NR metrics are missing, not zero. Mac time is a reference measurement.')
    lines=[r'\begin{longtable}{llrrrrl}', r'\toprule', r'Parameters & Variant & Decision & States & Queries & Rank/$|L|$ & Expected \\',r'\midrule',r'\endhead']
    for row in rows:
        params=', '.join(str(k)+'='+str(v) for k,v in json.loads(row['parameters']).items())
        decision={'NOT_RUN_DEADLINE':'NR','NOT_RUN':'Pending','RUNNING':'Running'}.get(row['decision'],row['decision'])
        lines.append(' & '.join([tex(params),tex(row['merge']+'/'+row['solver']),tex(decision),str(row['states_discovered']),str(row['successor_queries']),
                                 str(row['worst_completion_rank'] if row['decision']=='WIN' else row['losing_region_states']),tex(row['expected_check'])])+r' \\')
    lines += [r'\bottomrule',r'\end{longtable}',r'{\par\smallskip\footnotesize Single trials, 32\,GiB heap, whole-JVM 1,200\,s cap. WIN reports the returned policy rank bound; LOSS reports the returned discovered losing-certificate size. NR denotes not started before the fixed cutoff. Expected values are preregistered hypotheses and never substitute for measurements.}']
    (tables/'results.tex').write_text('\n'.join(lines)+'\n')
    (tables/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    for command in config.get('analysis_commands', []):
        proc = subprocess.run(command, cwd=E6, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        print(proc.stdout,end='')
        if proc.returncode: issues.append({'analysis_command':command, 'exit_code':proc.returncode})
    (tables/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({'family':config['family'],**summary},sort_keys=True))
    return bool(issues)


if __name__ == '__main__': raise SystemExit(collect(Path(sys.argv[1]).resolve()))
