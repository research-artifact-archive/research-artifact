"""One source-model recheck of immutable native rows and fixed adversarial controls."""
from pathlib import Path
import argparse
import copy
import datetime
import hashlib
import importlib.util
import json
import os
import signal
import subprocess
import sys
import time
import traceback
import model
import search
import sequence_checker

HERE = Path(__file__).resolve().parent
PREVIOUS = HERE.parent / 'charged_callback_recheck_02'
spec = importlib.util.spec_from_file_location('retained_charged_recheck02', PREVIOUS / 'strong.py')
strong = importlib.util.module_from_spec(spec)
spec.loader.exec_module(strong)
OLD = strong.OLD
DEST = HERE / 'attempt01'
STOP = datetime.datetime(2026, 9, 9, 4, 50, tzinfo=datetime.timezone.utc).timestamp()
FIXED_PATHS = {
    'constructed_valid': [1] * 5 + [0] * 11 + [1] * 3 + [0] * 14,
    'constructed_stale_read': [1] * 8 + [0] * 25,
    'constructed_lock_overlap': [1] * 5 + [0] * 12 + [1] * 3 + [0] * 13,
    'constructed_allocation_order': [0] * 3 + [1] * 8 + [0] * 22,
    'constructed_log_order': [1] * 4 + [0] * 4 + [1] * 4 + [0] * 21,
    'constructed_premature_join': [1] * 5 + [0] * 11 + [1] * 2 + [0] * 14 + [1],
    'constructed_colliding_bin': [1] * 5 + [0] * 11 + [1] * 3 + [0] * 14,
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def remap(row, table):
    result = copy.deepcopy(row)
    for event in result['events']:
        for key in ('id', 'source'):
            if key in event:
                event[key] = table.get(event[key], event[key])
        if 'parents' in event:
            event['parents'] = [table.get(x, x) for x in event['parents']]
    for key in ('completed', 'live'):
        result[key] = [table.get(x, x) for x in result[key]]
    return result


def bin_witness(layout):
    # Authored logical records, not native executions or independent populations.
    case = dict(id='constructed-bin-witness', jobs=[[4, 1, 1, 1, 1], [1, 10, 1, 1, 1]], edges=[[0, 1]])
    seed = next(s for s in range(100) if model.writer_jobs(s, 2, 1) == [1])
    run = dict(id='constructed-' + layout, case=case['id'], layout=layout, kind='concurrent', budget=1,
               outcomes='', seed=seed, mutant='none', control=True, expected_accept=layout == 'distinct')
    events, values = [], {}
    for i, size in enumerate((32, 7)):
        values[i + 1] = [17 * (i + 1) + 31 * j for j in range(size)]
        events.append(dict(kind='I', job=i, id=i + 1, seed=strong.legacy.fold(values[i + 1])))
    values[3] = [strong.legacy.signed(3 * x + 7) for x in values[2]]
    events.append(dict(kind='B', job=1, source=2, id=3, epoch=1, seed=strong.legacy.fold(values[3])))
    for job, source, ident, inside, parent_id in ((0, 1, 4, True, -1), (1, 2, 5, False, 4), (1, 3, 6, False, 4)):
        parent = 0 if parent_id == -1 else strong.legacy.fold(values[parent_id])
        values[ident] = [strong.legacy.signed(1664525 * x + 1013904223 + parent) for x in values[source]]
        events.append(dict(kind='K', job=job, source=source, id=ident, inside=inside,
                           parents=[parent_id, -1], seed=strong.legacy.fold(values[ident])))
        if ident in (4, 6):
            events.append(dict(kind='D', job=job, id=ident))
    row = dict(id=run['id'], status='SUCCESS', error='', work=48, protected_calls=[1, 0], callbacks=[1, 0],
               conditionals=[0, 2], cost=88, ceiling=88, writes=1, failures=[[1, 1]],
               trace=['0:P', '1:VF', '1:VS'], completed=[4, 6], live=[4, 6], events=events,
               elapsed_ns=0, initialization_ns=0, provenance='constructed logical record; never executed natively')
    return case, run, row


def prepare():
    DEST.mkdir(exist_ok=False)
    runs = json.loads((OLD / 'RUNS.json').read_text())
    cases = {x['id']: x for x in json.loads((OLD / 'CASES.json').read_text())}
    rows = {x['id']: x for x in map(json.loads, (OLD / 'RAW.jsonl').read_text().splitlines())}
    run = next(r for r in runs if r['id'] == 'run-000364')
    case, original = cases[run['case']], rows[run['id']]
    controls = [dict(id='prior-' + c['id'], case=case, run=run, row=c['mutated_record'],
                     expected_accept=c['expected_accept'], expected_old_accept=c['new_accepted'],
                     expected_status='FEASIBLE' if c['expected_accept'] else 'REJECTED',
                     provenance='previously observed recheck02 control')
                for c in json.loads((PREVIOUS / 'CONTROLS.json').read_text())]
    moved = copy.deepcopy(original)
    selected = [e for e in moved['events'] if e['kind'] == 'B' and e['id'] in (8, 9)]
    assert [e['id'] for e in selected] == [8, 9]
    moved['events'] = [e for e in moved['events'] if not (e['kind'] == 'B' and e['id'] in (8, 9))]
    where = next(i for i, e in enumerate(moved['events']) if e['kind'] == 'D' and e['job'] == 0)
    moved['events'][where:where] = selected
    for name, row in (('moved_B_logs', moved),
                      ('moved_B_logs_relabelled', remap(moved, {8: 7, 9: 8, 7: 9})),
                      ('allocation_swap_5_6', remap(original, {5: 6, 6: 5}))):
        controls.append(dict(id=name, case=case, run=run, row=row, expected_accept=False,
                             expected_old_accept=True, expected_status='INFEASIBLE',
                             provenance='source-derived impossible record, fixed before recheck03 outcomes'))
    wrong = copy.deepcopy(run)
    jobs = [e['job'] for e in original['events'] if e['kind'] == 'B']
    wrong['seed'] = next(s for s in range(100) if model.writer_jobs(s, len(case['jobs']), run['budget']) != jobs)
    controls.append(dict(id='wrong_writer_seed', case=case, run=wrong, row=original, expected_accept=False,
                         expected_old_accept=True, expected_status='REJECTED', expected_layer='model_translation',
                         expected_reason='writer Random sequence differs',
                         provenance='fixed incorrect source-level Random input'))
    for layout in ('distinct', 'colliding'):
        c, r, row = bin_witness(layout)
        controls.append(dict(id='bin_' + layout, case=c, run=r, row=row,
                             expected_accept=layout == 'distinct', expected_old_accept=True,
                             expected_status='FEASIBLE' if layout == 'distinct' else 'INFEASIBLE',
                             provenance='constructed source-model schedule witness'))
    assert len(controls) == 12
    save(DEST / 'CONTROLS_INPUT.json', controls)
    files = [HERE / n for n in ('PLAN.md', 'model.py', 'search.py', 'sequence_checker.py', 'study.py')]
    files += [OLD / n for n in ('RAW.jsonl', 'RUNS.json', 'CASES.json', 'study.py', 'ChargedCallbacks.java', 'MANIFEST.json')]
    files += [PREVIOUS / n for n in ('strong.py', 'CONTROLS.json', 'SUMMARY.json', 'MANIFEST.json')]
    files += [DEST / 'CONTROLS_INPUT.json', HERE.parent / 'CHARGED_CAUSAL_FEASIBILITY_AUTHOR_REPORT_20.md',
              HERE.parent / 'CHARGED_MICROPROGRAM_AUTHOR_REPORT_26.md',
              Path('/opt/homebrew/Cellar/openjdk@17/17.0.19/libexec/openjdk.jdk/Contents/Home/lib/src.zip'),
              Path(sys.executable).resolve()]
    save(DEST / 'MANIFEST.json', dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
         ordinary=3094, original_native_controls=4, prior_record_controls=6, new_record_controls=6,
         sequence_controls=['unchanged', 'missing_step', 'duplicate_step', 'wrong_raw_binding'],
         constructed_sequence_controls=FIXED_PATHS,
         source_row_count=3098, new_native_executions=0, python=sys.version,
         per_search_seconds=2, per_search_pc_states=100000, campaign_seconds=180, parent_seconds=200,
         absolute_stop_utc='2026-09-09T04:50:00Z', files={str(p): sha(p) for p in files}))
    print('Fixed3098 source rows,12 record controls,11 certificate controls; no recheck03 outcomes.')


def verify(case, run, row):
    try:
        static = strong.verify_run(case, run, row)
    except AssertionError as exc:
        return dict(status='REJECTED', accepted=False, layer='retained_static', reason=str(exc), error=traceback.format_exc())
    except Exception:
        return dict(status='CHECKER_FAILURE', accepted=None, layer='retained_static', error=traceback.format_exc())
    try:
        program = model.build(case, run, row)
    except AssertionError as exc:
        return dict(status='REJECTED', accepted=False, layer='model_translation', reason=str(exc), error=traceback.format_exc())
    except Exception:
        return dict(status='CHECKER_FAILURE', accepted=None, layer='model_translation', error=traceback.format_exc())
    try:
        result = search.solve(program)
    except Exception:
        return dict(status='CHECKER_FAILURE', accepted=None, layer='search', error=traceback.format_exc())
    if result['status'] == 'FEASIBLE':
        try:
            checked = sequence_checker.check(program, result['certificate'])
        except Exception:
            return dict(status='CHECKER_FAILURE', accepted=None, error=traceback.format_exc(), search=result)
        return dict(status='FEASIBLE', accepted=True, static=static, sequence_check=checked,
                    search_states=result['visited_states'], search_seconds=result['seconds'], certificate=result['certificate'])
    return dict(status=result['status'], accepted=False if result['status'] == 'INFEASIBLE' else None, search=result)


def run_worker():
    m = json.loads((DEST / 'MANIFEST.json').read_text())
    for path, digest in m['files'].items():
        assert sha(path) == digest, path
    save(DEST / 'RUN_STARTED.json', dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                       manifest_sha256=sha(DEST / 'MANIFEST.json')))
    runs = json.loads((OLD / 'RUNS.json').read_text())
    cases = {x['id']: x for x in json.loads((OLD / 'CASES.json').read_text())}
    raw_rows = list(map(json.loads, (OLD / 'RAW.jsonl').read_text().splitlines()))
    assert len(runs) == len(raw_rows) == 3098 and len({r['id'] for r in runs}) == 3098
    assert len({r['id'] for r in raw_rows}) == 3098 and {r['id'] for r in raw_rows} == {r['id'] for r in runs}
    rows = {x['id']: x for x in raw_rows}
    started = time.monotonic()
    results = []
    with (DEST / 'VERIFICATION.jsonl').open('x') as raw, (DEST / 'CERTIFICATES.jsonl').open('x') as certs:
        for i, run in enumerate(runs):
            if time.monotonic() - started >= 180 or time.time() >= STOP:
                result = dict(status='NOT_RUN', accepted=None, reason='campaign cutoff')
            else:
                result = verify(cases[run['case']], run, rows[run['id']])
            if 'certificate' in result:
                cert = result.pop('certificate')
                certs.write(json.dumps(dict(id=run['id'], certificate=cert), separators=(',', ':')) + '\n')
                certs.flush()
                result['certificate_sha256'] = model.digest(cert)
            result.update(id=run['id'], control=run['control'], expected_accept=run['expected_accept'],
                          expected_result_met=result['accepted'] == run['expected_accept'])
            if not result['expected_result_met'] and not (DEST / 'FIRST_ADVERSE.json').exists():
                save(DEST / 'FIRST_ADVERSE.json', dict(case=cases[run['case']], run=run, row=rows[run['id']], result=result))
            results.append(result)
            raw.write(json.dumps(result, separators=(',', ':')) + '\n')
            raw.flush()
            if (i + 1) % 500 == 0:
                print(json.dumps(dict(done=i + 1, seconds=time.monotonic() - started,
                                      adverse=sum(not r['expected_result_met'] for r in results))), flush=True)
    controls = []
    for item in json.loads((DEST / 'CONTROLS_INPUT.json').read_text()):
        if time.monotonic() - started >= 180 or time.time() >= STOP:
            result = dict(status='NOT_RUN', accepted=None)
        else:
            result = verify(item['case'], item['run'], item['row'])
        try:
            strong.verify_run(item['case'], item['run'], item['row'])
            old = True
        except Exception:
            old = False
        met = (result['accepted'] == item['expected_accept'] and old == item['expected_old_accept']
               and result['status'] == item['expected_status'])
        if 'expected_layer' in item:
            met = met and result.get('layer') == item['expected_layer'] and result.get('reason') == item['expected_reason']
        controls.append(dict(id=item['id'], expected_accept=item['expected_accept'], old_accepted=old,
                             expected_status=item['expected_status'], expected_result_met=met, result=result))
    save(DEST / 'CONTROL_RESULTS.json', controls)
    target = next(r for r in runs if r['id'] == 'run-000364')
    program = model.build(cases[target['case']], target, rows[target['id']])
    certificate = next((x['certificate'] for x in map(json.loads, (DEST / 'CERTIFICATES.jsonl').read_text().splitlines())
                       if x['id'] == target['id']), None)
    seq_controls = []
    for name in m['sequence_controls']:
        if certificate is None:
            seq_controls.append(dict(id=name, status='NOT_RUN', accepted=None, expected_result_met=False,
                                     reason='fixed source run-000364 has no feasible certificate; no replacement target'))
            continue
        cert = copy.deepcopy(certificate)
        if name == 'missing_step':
            cert['order'].pop()
        elif name == 'duplicate_step':
            cert['order'].insert(0, cert['order'][0])
        elif name == 'wrong_raw_binding':
            cert['raw_sha256'] = '0' * 64
        try:
            sequence_checker.check(program, cert)
            accepted, error = True, None
        except Exception:
            accepted, error = False, traceback.format_exc()
        seq_controls.append(dict(id=name, expected_accept=name == 'unchanged', accepted=accepted,
                                 expected_result_met=accepted == (name == 'unchanged'), error=error, certificate=cert))
    for name, order in m['constructed_sequence_controls'].items():
        if time.monotonic() - started >= 180 or time.time() >= STOP:
            seq_controls.append(dict(id=name, status='NOT_RUN', accepted=None, expected_result_met=False, reason='campaign cutoff'))
            continue
        case, run, row = bin_witness('colliding' if name == 'constructed_colliding_bin' else 'distinct')
        program = model.build(case, run, row)
        assert len(program['programs'][0]) == 25 and len(program['programs'][1]) == 8
        assert len(order) == 33 and order.count(0) == 25 and order.count(1) == 8
        cert = dict(schema='charged-microprogram-path-v1', model_sha256=model.digest(program),
                    raw_sha256=program['raw_sha256'], input_sha256=program['input_sha256'], order=order)
        try:
            sequence_checker.check(program, cert)
            accepted, error = True, None
        except AssertionError:
            accepted, error = False, traceback.format_exc()
        except Exception:
            accepted, error = None, traceback.format_exc()
        expected = name == 'constructed_valid'
        seq_controls.append(dict(id=name, expected_accept=expected, accepted=accepted,
                                 expected_result_met=accepted == expected, error=error, certificate=cert))
    save(DEST / 'SEQUENCE_CONTROLS.json', seq_controls)
    from collections import Counter
    summary = dict(source_rows=len(results), ordinary=3094, native_controls=4,
                   statuses=dict(Counter(r['status'] for r in results)),
                   ordinary_expected=sum(r['expected_result_met'] and not r['control'] for r in results),
                   native_controls_expected=sum(r['expected_result_met'] and r['control'] for r in results),
                   record_controls=12, record_controls_expected=sum(r['expected_result_met'] for r in controls),
                   sequence_controls=11, sequence_controls_expected=sum(r['expected_result_met'] for r in seq_controls),
                   new_native_executions=0, seconds=time.monotonic() - started,
                   maximum_search_states=max((r.get('search_states', 0) for r in results), default=0),
                   verification_sha256=sha(DEST / 'VERIFICATION.jsonl'),
                   certificates_sha256=sha(DEST / 'CERTIFICATES.jsonl'), original_raw_sha256=sha(OLD / 'RAW.jsonl'))
    save(DEST / 'SUMMARY.json', summary)
    print(json.dumps(summary, indent=2), flush=True)


def bounded_run():
    limit = min(200, STOP - time.time())
    if limit <= 0:
        raise RuntimeError('absolute stop reached')
    argv = [sys.executable, '-B', str(Path(__file__).resolve()), 'worker']
    with (DEST / 'stdout.txt').open('x') as stdout, (DEST / 'stderr.txt').open('x') as stderr:
        proc = subprocess.Popen(argv, stdout=stdout, stderr=stderr, start_new_session=True)
        try:
            code = proc.wait(timeout=limit)
            status = 'COMPLETED' if code == 0 else 'FAILURE'
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            code = proc.wait()
            status = 'TIMEOUT'
    save(DEST / 'PROCESS.json', dict(status=status, exit_code=code, argv=argv, cap_seconds=limit,
                                    incomplete_rows_must_remain_in_denominator=status != 'COMPLETED'))
    print((DEST / 'stdout.txt').read_text())
    if status != 'COMPLETED':
        print((DEST / 'stderr.txt').read_text())
        raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('prepare', 'run', 'worker'))
    args = parser.parse_args()
    {'prepare': prepare, 'run': bounded_run, 'worker': run_worker}[args.command]()
