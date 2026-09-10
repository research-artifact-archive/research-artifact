#!/usr/bin/env python3
from pathlib import Path
import tarfile,subprocess,time,json,datetime,hashlib
HERE=Path(__file__).resolve().parent
ROOT=Path('/anonymous-author-home/Research/valkey_build_20260910/native01')
t=time.monotonic(); rec={'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':['make','-j4','MALLOC=libc','BUILD_TLS=no'],'status':'RUNNING','source_sha256':hashlib.sha256((HERE/'valkey-source.tar.gz').read_bytes()).hexdigest()}
(HERE/'BUILD_START.json').write_text(json.dumps(rec,indent=2)+'\n')
try:
 ROOT.mkdir(parents=True,exist_ok=False)
 with tarfile.open(HERE/'valkey-source.tar.gz') as tf:
  tf.extractall(ROOT,filter='data')
 source=next(ROOT.glob('valkey-*')); rec['source']=str(source)
 with (HERE/'BUILD_STDOUT.txt').open('x') as out,(HERE/'BUILD_STDERR.txt').open('x') as err:
  result=subprocess.run(rec['command'],cwd=source,stdout=out,stderr=err,timeout=600)
 rec['returncode']=result.returncode; rec['status']='SUCCESS' if result.returncode==0 else 'FAILURE'
 if result.returncode==0:
  binary=source/'src/valkey-server'; rec['binary']=str(binary); rec['binary_sha256']=hashlib.sha256(binary.read_bytes()).hexdigest();rec['version']=subprocess.check_output([binary,'--version'],text=True,timeout=10).strip()
except Exception as ex:
 rec['status']='TIMEOUT' if isinstance(ex,subprocess.TimeoutExpired) else 'FAILURE';rec['exception']=repr(ex)
rec['seconds']=time.monotonic()-t
(HERE/'BUILD_RESULT.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(rec));raise SystemExit(0 if rec['status']=='SUCCESS' else 1)
