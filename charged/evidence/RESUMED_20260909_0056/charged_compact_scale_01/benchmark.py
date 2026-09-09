"""Fixed charged construction experiment: serial cold processes, full denominator."""
from pathlib import Path
import argparse
import collections
import copy
import datetime
import hashlib
import json
import os
import platform
import signal
import statistics
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
DEST = HERE / 'attempt01'
Q = [1, 2, 4, 8, 16, 32, 64, 256, 4096, 65536, 1 << 32, 1 << 64]
STOP = datetime.datetime(2026, 9, 9, 4, 50, tzinfo=datetime.timezone.utc).timestamp()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, data):
    with Path(path).open('x') as stream:
        json.dump(data, stream, indent=2)
        stream.write('\n')


def prepare():
    assert __debug__
    core=HERE.parent/'charged_compact_03';semantic=HERE.parent/'charged_compact_02'
    assert json.loads((semantic/'conformance01/SUMMARY.json').read_text())['statuses']['SUCCESS']==19485
    assert json.loads((HERE/'conformance01/SUMMARY.json').read_text())['success']==76
    cases=[];units=[];methods=['PACK','ROOT','ALL','PEAK','DP']
    for n in [8,12,32,128,512,4096,32768]:
        for topology in ['INDEPENDENT','COMPATIBLE_HEIGHT2']:
            for family in ['LOW','LONG_P','WIDE']:
                jobs=[]
                for i in range(n):
                    w=1+7*i%17;p=1+11*i%29;k=1+13*i%23;g=k//2;r=k-g;v=k+i%3
                    if family=='LONG_P':p*=2**32+i%7
                    if family=='WIDE':w,p,g,v,r=[x*2**96 for x in [w,p,g,v,r]]
                    jobs.append([w,p,g,v,r])
                order=sorted(range(n),key=lambda i:(min(jobs[i][0]+jobs[i][2]+jobs[i][4],jobs[i][0]+jobs[i][1]),i))
                edges=[] if topology=='INDEPENDENT' else [[order[i],order[i+n//2]] for i in range(n//2)]
                case_id=f'{n}_{topology}_{family}';case=dict(jobs=jobs,edges=edges)
                cases.append(dict(id=case_id,n=n,topology=topology,family=family,case=case))
                for size in [1,12]:
                    shift=(len(cases)-1+(size==12))%len(methods)
                    for method in methods[shift:]+methods[:shift]:
                        units.append(dict(id=f'{case_id}_Q{size}_{method}',case_id=case_id,method=method,case=case,budgets=Q[:size],seconds_cap=8))
    assert len(cases)==42 and len(units)==420 and sum(len(u['budgets']) for u in units)==2730
    DEST.mkdir(exist_ok=False);(DEST/'inputs').mkdir()
    save(DEST/'CASES.json',cases);save(DEST/'UNITS.json',units)
    for unit in units:save(DEST/'inputs'/(unit['id']+'.json'),unit)
    sources=list(HERE.glob('*.py'))+[HERE/'PLAN.md',HERE/'BOUND_PROOF.md',Path(sys.executable).resolve()]
    sources+=list(core.glob('*.py'))+list((core/'inherited').rglob('*.py'))
    sources+=[core/'PLAN.md',core/'SEMANTIC_SOURCE_BINDING.json']+[semantic/'conformance01'/name for name in ['MANIFEST.json','SUMMARY.json','RAW.jsonl','CONTROLS.json']]
    sources+=[HERE/'conformance01'/name for name in ['MANIFEST.json','SUMMARY.json','RAW.jsonl','CONTROLS.json']]
    sources+=[HERE.parent/'charged_curves_02'/name for name in ['basis.py','compiler.py','checker.py']]
    sources+=[HERE.parent.parent/'RESUMED_20260907_1942/dependency_curves_01/curves.py']
    sources+=list((core/'cli_conformance01').glob('*.json'))
    sources+=list((HERE/'worker_conformance01').rglob('*.json'))
    sources+=list((DEST/'inputs').glob('*.json'))+[DEST/'CASES.json',DEST/'UNITS.json']
    save(DEST/'MANIFEST.json',dict(schema='charged-compact-cold-comparison-v1',utc=utc(),cases=42,process_units=420,root_requests=2730,methods=methods,inputs_previously_observed=False,
        per_unit_seconds_cap=8,rss_cap_bytes=1<<30,campaign_seconds_cap=2400,absolute_stop_utc='2026-09-09T04:50:00Z',poll_seconds=.005,rss_sample_seconds=.05,
        measurement='parent cold elapsed including startup through final termination',order='size/topology/family, Q1/Q12, rotate methods by case index plus workload index',
        python=sys.version,executable=str(Path(sys.executable).resolve()),platform=platform.platform(),argv_template=[sys.executable,'-B',str(HERE/'worker.py'),'METHOD','INPUT','OUTPUTDIR'],
        environment_overrides=dict(PYTHONHASHSEED='0',PYTHONDONTWRITEBYTECODE='1'),request_controls=['unchanged_peak','reversed_budget','wrong_peak_input','wrong_all_input'],
        files={str(path):sha(path) for path in sources}))
    print('Fixed42 new cases/420 cold processes/2730 roots; no main outcomes observed.')


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def controls():
    from worker import bind_certificate
    import oracle
    case = dict(jobs=[[2, 5, 0, 0, 0]], edges=[])
    budgets = [1, 2]
    original = json.loads(json.dumps(oracle.solve_many(case, budgets)['artifact']))
    result = []
    for name in ('unchanged_peak', 'reversed_budget', 'wrong_peak_input', 'wrong_all_input'):
        item = copy.deepcopy(original)
        method = 'ALL' if name == 'wrong_all_input' else 'PEAK'
        if name == 'reversed_budget':
            item['budgets'].reverse()
            item['values'].reverse()
        if name in ('wrong_peak_input', 'wrong_all_input'):
            item['input']['jobs'][0][0] += 1
        try:
            bind_certificate(method, item, case, budgets)
            accepted, error = True, None
        except Exception as exc:
            accepted, error = False, str(exc)
        result.append(dict(id=name, accepted=accepted, expected_accept=name == 'unchanged_peak',
                           passed=accepted == (name == 'unchanged_peak'), error=error))
    save(DEST / 'REQUEST_BINDING_CONTROLS.json', result)
    assert all(r['passed'] for r in result)


def kill(proc):
    if proc.poll() is None:
        os.killpg(proc.pid, signal.SIGKILL)
    proc.wait()


def run():
    manifest = json.loads((DEST / 'MANIFEST.json').read_text())
    for path, digest in manifest['files'].items():
        assert sha(path) == digest, path
    assert __debug__
    save(DEST / 'RUN_STARTED.json', dict(utc=utc(), manifest_sha256=sha(DEST / 'MANIFEST.json')))
    controls()
    begin = time.monotonic()
    records = []
    units = json.loads((DEST / 'UNITS.json').read_text())
    with (DEST / 'RAW.jsonl').open('x') as raw:
        for index, unit in enumerate(units):
            out = DEST / 'runs' / unit['id']
            out.mkdir(parents=True, exist_ok=False)
            argv = [sys.executable, '-B', str(HERE / 'worker.py'), unit['method'],
                    str(DEST / 'inputs' / (unit['id'] + '.json')), str(out)]
            record = {k: unit[k] for k in ('id', 'case_id', 'method', 'budgets', 'seconds_cap')}
            record.update(argv=argv, utc=utc(), sampled_peak_rss_bytes=0, samples=0)
            if time.monotonic() - begin >= 2400 or time.time() >= STOP:
                record.update(status='NOT_RUN', reason='campaign or absolute cutoff')
            else:
                env = os.environ.copy()
                env.update(PYTHONHASHSEED='0', PYTHONDONTWRITEBYTECODE='1')
                started = time.monotonic()
                proc = None
                try:
                    with (out / 'stdout.txt').open('x') as stdout, (out / 'stderr.txt').open('x') as stderr:
                        proc = subprocess.Popen(argv, stdout=stdout, stderr=stderr, env=env,
                                                cwd=HERE, start_new_session=True)
                        reason = None
                        next_sample = started + .05
                        while proc.poll() is None:
                            now = time.monotonic()
                            if now - started >= unit['seconds_cap'] or now - begin >= 2400 or time.time() >= STOP:
                                reason = 'TIMEOUT'
                                kill(proc)
                                break
                            if now >= next_sample:
                                sample = subprocess.run(['/bin/ps', '-o', 'rss=', '-p', str(proc.pid)],
                                                        capture_output=True, text=True, timeout=.5)
                                rows = sample.stdout.split()
                                rss = int(rows[0]) * 1024 if rows else 0
                                record['samples'] += 1
                                record['sampled_peak_rss_bytes'] = max(record['sampled_peak_rss_bytes'], rss)
                                next_sample = now + .05
                                if rss > 1 << 30:
                                    reason = 'MEMORY_LIMIT'
                                    kill(proc)
                                    break
                            time.sleep(.005)
                        record.update(cold_seconds=time.monotonic() - started, exit_code=proc.returncode)
                    if reason is None and (record['cold_seconds'] > unit['seconds_cap'] or time.monotonic() - begin > 2400 or time.time() >= STOP):
                        reason = 'TIMEOUT'
                    if reason:
                        record.update(status='TIMEOUT' if reason == 'TIMEOUT' else 'FAILURE', reason=reason)
                    elif proc.returncode != 0:
                        record.update(status='FAILURE', reason='worker_nonzero')
                        if (out/'RESULT.json').exists():record['worker_failure']=json.loads((out/'RESULT.json').read_text())
                    elif not (out / 'RESULT.json').is_file():
                        record.update(status='INVALID', reason='missing_worker_result')
                    else:
                        result = json.loads((out / 'RESULT.json').read_text())
                        record['worker_result'] = result
                        assert result['method'] == unit['method'] and result['budgets'] == unit['budgets']
                        assert len(result['values']) == len(unit['budgets'])
                        assert all(type(v) == int and v >= 0 for v in result['values'])
                        if result['process_peak_rss_bytes'] > 1 << 30:
                            record.update(status='FAILURE', reason='MEMORY_LIMIT_IN_FINAL_RUSAGE')
                        else:
                            record['status'] = result['status']
                except Exception:
                    if proc is not None:
                        kill(proc)
                    record.update(status='INVALID', reason=traceback.format_exc(), cold_seconds=time.monotonic() - started)
            save(out / 'PROCESS.json', record)
            records.append(record)
            raw.write(json.dumps(record, separators=(',', ':')) + '\n')
            raw.flush()
            if (index + 1) % 12 == 0 or record['status'] != 'SUCCESS':
                print(json.dumps(dict(done=index + 1, total=len(units), id=unit['id'], status=record['status'],
                                      seconds=time.monotonic() - begin)), flush=True)
    expected = {u['id'] for u in units}
    assert len(records) == len(expected) == 420 and {r['id'] for r in records} == expected
    values = collections.defaultdict(list)
    for record in records:
        if record['status'] == 'SUCCESS':
            for b, v in zip(record['budgets'], record['worker_result']['values']):
                values[record['case_id'], b].append((record['id'], v))
    disagreements = [dict(case_id=key[0], budget=key[1], observed=rows) for key, rows in values.items()
                     if len({v for _, v in rows}) > 1]
    by_method = {}
    for method in ('PACK','ROOT','ALL','PEAK','DP'):
        rows = [r for r in records if r['method'] == method]
        success = [r for r in rows if r['status'] == 'SUCCESS']
        by_method[method] = dict(units=len(rows), statuses=dict(collections.Counter(r['status'] for r in rows)),
            successful_cold_seconds=[r['cold_seconds'] for r in success],
            completed_requested_roots=sum(len(r['budgets']) for r in success),
            maximum_success_rss_bytes=max([r['worker_result']['process_peak_rss_bytes'] for r in success], default=0))
    lookup={(r['case_id'],len(r['budgets']),r['method']):r for r in records}
    pairs=[]
    for case in json.loads((DEST/'CASES.json').read_text()):
        for size in (1,12):
            a=lookup[case['id'],size,'PACK']
            for method in ('ROOT','ALL','PEAK','DP'):
                b=lookup[case['id'],size,method]
                row=dict(case_id=case['id'],workload=size,comparator=method,PACK_status=a['status'],comparator_status=b['status'],timing_scope='same serial campaign; one sample; different output services')
                if a['status']==b['status']=='SUCCESS':row.update(ratio_comparator_over_PACK=b['cold_seconds']/a['cold_seconds'],PACK_seconds=a['cold_seconds'],comparator_seconds=b['cold_seconds'])
                pairs.append(row)
    save(DEST/'SUMMARY.json',dict(units=420,requested_roots=2730,statuses=dict(collections.Counter(r['status'] for r in records)),by_method=by_method,paired_comparisons=pairs,
        disagreements=disagreements,seconds=time.monotonic()-begin,raw_sha256=sha(DEST/'RAW.jsonl'),missing_ids=sorted(expected-{r['id'] for r in records}),
        result_scope='New author-constructed compatible cases. PACK cursor policy, ROOT reduction-aware value-only ablation, ALL all unfinished states, PEAK requested certificates, DP requested values.'))
    print(json.dumps(dict(units=420,statuses=dict(collections.Counter(r['status'] for r in records)),disagreements=len(disagreements),seconds=time.monotonic()-begin)),flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('prepare', 'run'))
    args = parser.parse_args()
    {'prepare': prepare, 'run': run}[args.command]()

