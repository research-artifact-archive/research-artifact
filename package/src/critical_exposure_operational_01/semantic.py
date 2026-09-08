from pathlib import Path
import datetime
import hashlib
import importlib.util
import json
import signal
import sys
import time
import traceback
import types

ROOT=Path(__file__).resolve().parent
S=ROOT.parent
sys.path.insert(0,str(S/'final_evaluation_dag_01'))
import evaluate_final as reference
spec=importlib.util.spec_from_file_location('selected_common_policy_check',S/'sweep_certificate_02/certificate.py')
sweep=importlib.util.module_from_spec(spec);spec.loader.exec_module(sweep)


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(name,value):
    with (ROOT/name).open('x') as f:
        json.dump(value,f,sort_keys=True,indent=2);f.write('\n')
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()


def prepare():
    paths={Path(__file__).resolve(),ROOT/'PLAN.md',ROOT/'CASE.json'}
    seen=set();pending=[reference,sweep]
    while pending:
        m=pending.pop()
        if id(m) in seen:continue
        seen.add(id(m))
        path=Path(getattr(m,'__file__','/outside')).resolve()
        if not path.is_relative_to(S) or path.suffix!='.py':continue
        paths.add(path)
        pending.extend(v for v in vars(m).values() if isinstance(v,types.ModuleType))
    save('SEMANTIC_MANIFEST.json',dict(utc=now(),case=json.loads((ROOT/'CASE.json').read_text()),
        files=[dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(paths)],
        python=sys.executable,python_version=sys.version,python_sha256=sha(sys.executable),
        unit_seconds=20,selected_after_scalar_observation=True,final_evaluation=False))


def run():
    manifest=json.loads((ROOT/'SEMANTIC_MANIFEST.json').read_text())
    for f in manifest['files']:assert sha(f['path'])==f['sha256']
    assert sha(sys.executable)==manifest['python_sha256'] and __debug__
    assert datetime.datetime.now(datetime.timezone.utc)<datetime.datetime.fromisoformat('2026-09-08T01:45:00+00:00')
    save('SEMANTIC_RUN_STARTED.json',dict(utc=now(),manifest_sha256=sha(ROOT/'SEMANTIC_MANIFEST.json')))
    start=time.monotonic()
    def timeout(signum,frame):raise TimeoutError('fixed20second selected primitive cap')
    signal.signal(signal.SIGALRM,timeout);signal.setitimer(signal.ITIMER_REAL,20)
    try:
        row,data=reference.evaluate(manifest['case'])
        with (ROOT/'ARTIFACT.json').open('xb') as f:f.write(data)
        row['policy_sweep']=sweep.check(json.loads(data))
        assert not row['policy_sweep']['violations']
        assert [r['primitive'] for r in row['roots']]==manifest['case']['expected_totals']
    except TimeoutError:row=dict(status='TIMEOUT',error=traceback.format_exc())
    except AssertionError:row=dict(status='FAILURE',error=traceback.format_exc())
    except Exception:row=dict(status='INVALID',error=traceback.format_exc())
    finally:signal.setitimer(signal.ITIMER_REAL,0)
    row.update(utc=now(),total_seconds=time.monotonic()-start,selected_validation=True,final_evaluation=False)
    save('SEMANTIC_RESULT.json',row)
    print(json.dumps(row,indent=2))


if __name__=='__main__':{'prepare':prepare,'run':run}[sys.argv[1]]()
