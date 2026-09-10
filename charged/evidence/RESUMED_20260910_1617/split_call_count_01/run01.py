from pathlib import Path
from datetime import datetime,timezone
import subprocess,os,signal,time,json,sys
D=Path(__file__).resolve().parent;start=time.monotonic();cap=600
with(D/'RUN01.stdout').open('xb') as out,(D/'RUN01.stderr').open('xb') as err:
 p=subprocess.Popen([sys.executable,'-B',str(D/'check01.py')],stdout=out,stderr=err,start_new_session=True)
 (D/'RUN_START01.json').write_text(json.dumps(dict(utc=datetime.now(timezone.utc).isoformat(),pid=p.pid,cap_seconds=cap),indent=2)+'\n')
 try:code=p.wait(timeout=cap);status='SUCCESS' if code==0 else 'FAILED'
 except subprocess.TimeoutExpired:
  os.killpg(p.pid,signal.SIGTERM)
  try:code=p.wait(timeout=3)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);code=p.wait()
  status='TIMEOUT'
r=dict(utc=datetime.now(timezone.utc).isoformat(),status=status,returncode=code,seconds=time.monotonic()-start);(D/'RUN_COMPLETION01.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);raise SystemExit(code if code>=0 else 1)
