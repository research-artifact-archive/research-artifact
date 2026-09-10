"""First native attempt only; after failures, checker still accounts for all rows."""
from pathlib import Path
import json,hashlib,subprocess,time,datetime
D=Path(__file__).resolve().parent
assert not(D/'RUN_RECEIPT01.json').exists() and not(D/'RAW01.jsonl').exists()
start=time.monotonic();r=dict(start=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='STARTED',hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in D.iterdir() if p.is_file()})
(D/'RUN_RECEIPT01.json').write_text(json.dumps(r,indent=2)+'\n')
try:
    versions={}
    for cmd in [['java','-version'],['javac','-version']]:
        p=subprocess.run(cmd,text=True,capture_output=True,timeout=10,check=True);versions[cmd[0]]=p.stdout+p.stderr
    r['versions']=versions;(D/'classes01').mkdir()
    p=subprocess.run(['javac','-d',str(D/'classes01'),str(D/'UniversalCallbacks.java')],capture_output=True,text=True,timeout=max(1,180-(time.monotonic()-start)))
    (D/'COMPILE01.stdout').write_text(p.stdout);(D/'COMPILE01.stderr').write_text(p.stderr);r['compile_returncode']=p.returncode
    if p.returncode:raise RuntimeError('Compilation failed; all cases remain unexecuted')
    argv=['java','--add-opens','java.base/java.util.concurrent=ALL-UNNAMED','-cp',str(D/'classes01'),'UniversalCallbacks',str(D/'RUNS.tsv')];r['argv']=argv
    with(D/'RAW01.jsonl').open('x') as out,(D/'RUN01.stderr').open('x') as err:p=subprocess.run(argv,stdout=out,stderr=err,timeout=max(1,180-(time.monotonic()-start)))
    r['returncode']=p.returncode;r['status']='SUCCESS' if p.returncode==0 else 'FAILURE'
except subprocess.TimeoutExpired as e:r.update(status='TIMEOUT',error=str(e))
except Exception as e:r.update(status='FAILURE',error=repr(e))
finally:
    r.update(end=datetime.datetime.now(datetime.timezone.utc).isoformat(),elapsed_seconds=time.monotonic()-start)
    (D/'RUN_RECEIPT01.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r,indent=2));raise SystemExit(r['status']!='SUCCESS')
