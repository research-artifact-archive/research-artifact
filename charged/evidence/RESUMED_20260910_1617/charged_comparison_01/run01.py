from pathlib import Path
import datetime, hashlib, json, os, signal, subprocess, sys, time

D=Path(__file__).resolve().parent;start=time.monotonic();cap=900
argv=[sys.executable,'-B',str(D/'check01.py'),'--out',str(D/'run01')]
with (D/'RUN01.stdout').open('xb') as out,(D/'RUN01.stderr').open('xb') as err:
 proc=subprocess.Popen(argv,stdout=out,stderr=err,start_new_session=True)
 receipt={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':argv,'pid':proc.pid,'cap_seconds':cap,'input_sha256':hashlib.sha256((D/'INPUTS01.json').read_bytes()).hexdigest(),'checker_sha256':hashlib.sha256((D/'check01.py').read_bytes()).hexdigest()}
 (D/'RUN_START01.json').write_text(json.dumps(receipt,indent=2)+'\n')
 try:code=proc.wait(timeout=cap);status='SUCCESS' if code==0 else 'FAILURE'
 except subprocess.TimeoutExpired:
  os.killpg(proc.pid,signal.SIGTERM)
  try:code=proc.wait(timeout=3)
  except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);code=proc.wait()
  status='TIMEOUT'
 receipt.update(ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status=status,returncode=code,seconds=time.monotonic()-start)
 with (D/'RUN_COMPLETION01.json').open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
 print(json.dumps(receipt,indent=2),flush=True)
 raise SystemExit(0 if status=='SUCCESS' else 1)
