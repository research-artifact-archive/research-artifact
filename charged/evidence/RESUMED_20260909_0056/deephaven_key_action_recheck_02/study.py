from pathlib import Path
import argparse
import copy
import datetime
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
import traceback
import strict

HERE = Path(__file__).resolve().parent
OLD = strict.OLD
DEST = HERE / 'attempt01'
STOP = datetime.datetime(2026, 9, 9, 4, 50, tzinfo=datetime.timezone.utc).timestamp()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def prepare():
    DEST.mkdir(exist_ok=False)
    rows = {r['id']: r for r in map(json.loads, (OLD / 'RAW.jsonl').read_text().splitlines())}
    controls = [dict(id='prior-' + path.stem, expected_accept=False, row=json.loads(path.read_text()))
                for path in sorted((OLD / 'check01').glob('CONTROL_*.json'))]
    assert len(controls) == 9
    for name in ('missing_work', 'wrong_usePrev', 'foreground_before_mutation', 'foreground_before_return',
                 'delayed_cut', 'future_writer_exception', 'wrong_start_notification', 'missing_lock_entry'):
        source = '3_k_dir_full_curve_fast_tie'
        if name == 'missing_work':
            source = '3_none_curve_fast_tie'
        elif name in ('wrong_usePrev', 'wrong_start_notification'):
            source = '3_cross_stage_curve_fast_tie'
        elif name == 'future_writer_exception':
            source = '3_v_end_full_curve_fast_tie'
        elif name == 'missing_lock_entry':
            source = '3_cross_stage_upstream2'
        row = copy.deepcopy(rows[source])
        events = row['events']
        if name == 'missing_work':
            assert events[23][1] == 'V_CELL'
            del events[23]
        elif name == 'wrong_usePrev':
            assert events[14][1] == 'BEGIN' and events[19][1] == 'END' and events[20][1] == 'CHECK'
            events[14][3] = events[19][3] = events[20][4] = 0
        elif name in ('foreground_before_mutation', 'foreground_before_return'):
            assert events[9][1] == 'K_DIR'
            moving = events.pop(9)
            events.insert(7 if name == 'foreground_before_mutation' else 8, moving)
        elif name == 'delayed_cut':
            assert [e[1] for e in events[6:10]] == ['CUT', 'KEY_UPDATE', 'FULL', 'K_DIR']
            block = events[6:9]
            block[0][4] = 3
            events[6:10] = [events[9]] + block
        elif name == 'future_writer_exception':
            assert events[118][1] == 'END' and events[122][1] == 'CHECK'
            events[118][5] = -1
            events[122][5] = 0
            events.insert(118, ['V', 'INCONSISTENT_EXCEPTION', 1, 0, 0, 0])
        elif name == 'wrong_start_notification':
            assert events[10][1] == 'START'
            events[10][4] += 1
            events[10][5] += 1
        else:
            assert events[247][1] == 'BEFORE_LOCK'
            del events[247]
        controls.append(dict(id=name, expected_accept=False, row=row))
    for source in ('3_cross_stage_curve_fast_tie', '3_v_end_full_curve_fast_tie',
                   '3_cross_stage_upstream2', '3_k_full_v_split_curve_fast_tie'):
        controls.append(dict(id='unchanged-' + source, expected_accept=True, row=rows[source]))
    assert len(controls) == 21
    save(DEST / 'CONTROLS_INPUT.json', controls)
    files = [HERE / n for n in ('strict.py', 'study.py', 'PLAN.md')]
    files += list((OLD / 'sources').glob('*'))
    files += [OLD / 'RAW.jsonl', OLD / 'check01/TRACE_CHECK.json', DEST / 'CONTROLS_INPUT.json',
              HERE.parent / 'DEEPHAVEN_KEY_ACTION_AUTHOR_REPORT_23.md',
              HERE.parent / 'DEEPHAVEN_KEY_RECHECK_DESIGN_AUTHOR_REPORT_24.md', Path(sys.executable).resolve()]
    save(DEST / 'MANIFEST.json', dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
         saved_rows=36, old_negative_controls=9, new_negative_controls=8, unchanged_positive_controls=4,
         native_repeats=0, python=sys.version, inner_seconds=30, parent_seconds=45,
         files={str(path): sha(path) for path in files if path.is_file()}))
    print('Fixed36 saved rows and21 controls; no recheck02 outcomes.')


def checked(row):
    try:
        return dict(accepted=True, result=strict.check(row))
    except Exception:
        return dict(accepted=False, error=traceback.format_exc())


def worker():
    manifest = json.loads((DEST / 'MANIFEST.json').read_text())
    for path, digest in manifest['files'].items():
        assert sha(path) == digest
    save(DEST / 'RUN_STARTED.json', dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                       manifest_sha256=sha(DEST / 'MANIFEST.json')))
    rows = list(map(json.loads, (OLD / 'RAW.jsonl').read_text().splitlines()))
    expected = json.loads((OLD / 'sources/EXPECTED_IDS.json').read_text())
    assert len(rows) == 36 and len({r['id'] for r in rows}) == 36 and {r['id'] for r in rows} == set(expected)
    started = time.monotonic()
    results = []
    for row in rows:
        assert time.monotonic() - started < 30 and time.time() < STOP
        result = checked(row)
        result['id'] = row['id']
        results.append(result)
        if not result['accepted'] and not (DEST / 'FIRST_ADVERSE.json').exists():
            save(DEST / 'FIRST_ADVERSE.json', dict(row=row, result=result))
    save(DEST / 'VERIFICATION.json', results)
    controls = []
    for item in json.loads((DEST / 'CONTROLS_INPUT.json').read_text()):
        assert time.monotonic() - started < 30 and time.time() < STOP
        new = checked(item['row'])
        try:
            strict.legacy.check(item['row'])
            old = True
        except Exception:
            old = False
        controls.append(dict(id=item['id'], expected_accept=item['expected_accept'], old_accepted=old,
                             result=new, expected_result_met=new['accepted'] == item['expected_accept']))
    save(DEST / 'CONTROL_RESULTS.json', controls)
    summary = dict(rows=36, accepted=sum(r['accepted'] for r in results), controls=21,
                   controls_expected=sum(r['expected_result_met'] for r in controls),
                   new_controls_previously_missed=[c['id'] for c in controls if not c['expected_accept'] and c['old_accepted']],
                   seconds=time.monotonic() - started, new_native_executions=0,
                   raw_sha256=sha(OLD / 'RAW.jsonl'), verification_sha256=sha(DEST / 'VERIFICATION.json'))
    save(DEST / 'SUMMARY.json', summary)
    print(json.dumps(summary, indent=2))


def run():
    limit = min(45, STOP - time.time())
    assert limit > 0
    argv = [sys.executable, '-B', str(Path(__file__).resolve()), 'worker']
    with (DEST / 'stdout.txt').open('x') as out, (DEST / 'stderr.txt').open('x') as err:
        proc = subprocess.Popen(argv, stdout=out, stderr=err, start_new_session=True)
        try:
            code = proc.wait(timeout=limit)
            status = 'COMPLETED' if code == 0 else 'FAILURE'
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            code = proc.wait()
            status = 'TIMEOUT'
    save(DEST / 'PROCESS.json', dict(status=status, exit_code=code, argv=argv))
    print((DEST / 'stdout.txt').read_text())
    if status != 'COMPLETED':
        print((DEST / 'stderr.txt').read_text())
        raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('prepare', 'run', 'worker'))
    args = parser.parse_args()
    {'prepare': prepare, 'run': run, 'worker': worker}[args.command]()
