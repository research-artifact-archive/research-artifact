#!/usr/bin/env python3
"""Bounded replay into a new directory; original measurements remain immutable."""
import argparse,datetime,gzip,hashlib,json,os,signal,subprocess,sys,time
from pathlib import Path

HERE=Path(__file__).resolve().parent
COMPACT_STAGES=['compact','compact-native','compact-scale']
STAGES=['curves','native','deephaven','scale','calibration','ordering','refutations']+COMPACT_STAGES

def save(p,x):
    with p.open('x') as f:json.dump(x,f,indent=2);f.write('\n')
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def verify():
    m=json.loads((HERE/'PROVENANCE.json').read_text())
    seen=set()
    for row in m['files']:
        p=HERE/row['path'];assert p.resolve().is_relative_to(HERE.resolve()) and row['path'] not in seen
        assert p.is_file() and p.stat().st_size==row['public_bytes'] and digest(p)==row['public_sha256'],row['path']
        if row.get('storage_encoding')=='gzip':
            hasher=hashlib.sha256();size=0
            with gzip.open(p,'rb') as f:
                for block in iter(lambda:f.read(1048576),b''):
                    hasher.update(block);size+=len(block)
                    assert size<=row['decoded_bytes'],row['path']
            assert size==row['decoded_bytes'] and hasher.hexdigest()==row['decoded_sha256'],row['path']
        seen.add(row['path'])
    return len(seen)

def main():
    if not __debug__:raise SystemExit('Assertions must be enabled; do not use python -O.')
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage',choices=['verify','all','native-java','compact-native-java']+STAGES)
    p.add_argument('--out',type=Path);p.add_argument('--quick',action='store_true');p.add_argument('--timeout',type=int,default=300)
    a=p.parse_args();count=verify()
    if a.stage=='verify':print(json.dumps(dict(status='VERIFIED',files=count)));return
    if a.out is None:p.error('--out is required for a replay')
    if a.timeout<1:p.error('--timeout must be positive')
    a.out.mkdir(parents=True,exist_ok=False)
    stages=STAGES if a.stage=='all' else [a.stage]
    save(a.out/'REPLAY_INPUT.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),stage=a.stage,quick=a.quick,timeout_per_stage=a.timeout,python=sys.version,executable=sys.executable,source_manifest_sha256=digest(HERE/'PROVENANCE.json'),worker_sha256=digest(HERE/'worker.py'),compact_worker_sha256=digest(HERE/'compact_worker.py'),driver_sha256=digest(Path(__file__)),replay_only=True,new_evaluation_population=False))
    results=[]
    for stage in stages:
        output=a.out/stage;output.mkdir()
        worker='compact_worker.py' if stage in COMPACT_STAGES+['compact-native-java'] else 'worker.py'
        argv=[sys.executable,'-B',str(HERE/worker),stage,str(output)]
        if a.quick:argv.append('--quick')
        start=time.monotonic()
        with (output/'stdout.txt').open('xb') as stdout,(output/'stderr.txt').open('xb') as stderr:
            proc=subprocess.Popen(argv,stdout=stdout,stderr=stderr,start_new_session=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE="1"))
            try:code=proc.wait(timeout=a.timeout);status='SUCCESS' if code==0 else 'FAILURE'
            except subprocess.TimeoutExpired:
                status='TIMEOUT';os.killpg(proc.pid,signal.SIGTERM)
                try:code=proc.wait(timeout=2)
                except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);code=proc.wait()
        row=dict(stage=stage,status=status,returncode=code,seconds=time.monotonic()-start,argv=argv)
        if (output/'SUMMARY.json').exists():row['summary']=json.loads((output/'SUMMARY.json').read_text())
        save(output/'PROCESS_RESULT.json',row);results.append(row)
        print(json.dumps(dict(stage=stage,status=status,seconds=row['seconds'])),flush=True)
    save(a.out/'REPLAY_RESULT.json',dict(status='SUCCESS' if all(r['status']=='SUCCESS' for r in results) else 'FAILURE',stages=results,replay_only=True))
    raise SystemExit(0 if all(r['status']=='SUCCESS' for r in results) else 1)

if __name__=='__main__':main()
