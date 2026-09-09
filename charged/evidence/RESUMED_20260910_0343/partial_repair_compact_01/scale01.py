from pathlib import Path
import collections,datetime,hashlib,json,os,signal,subprocess,sys,time,traceback
P=Path(__file__).resolve().parent;O=P/'scale01';O.mkdir();start=time.monotonic();deadline=start+1200
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,x):
 with p.open('x') as f:json.dump(x,f,indent=2);f.write('\n')
units=[]
for m in [16,256,4096,65536]:
 for pattern in ['uniform','mixed']:
  for q in [1,2,3,8,64]:
   for mu in ['0','2','W']:units.append(dict(grid='large',m=m,pattern=pattern,q=q,mu=mu,method='compact',cap=8))
idx=0
for m in [8,32,128,512]:
 for pattern in ['uniform','mixed']:
  for q in [2,4,8]:
   for mu in ['2','W']:
    for method in (['compact','profiledp'] if idx%2==0 else ['profiledp','compact']):units.append(dict(grid='paired',m=m,pattern=pattern,q=q,mu=mu,method=method,cap=3))
    idx+=1
assert len(units)==216
put(O/'INPUTS.json',units);put(O/'INPUT_RECEIPT.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),units=216,large_inputs=120,paired_inputs=48,paired_units=96,source_hashes={s:sha(P/s) for s in ['SCALE_PLAN.md','compact01.py','scale_worker01.py','scale01.py']},inputs_sha256=sha(O/'INPUTS.json'),total_cap_seconds=1200))
rows=[]
try:
 for i,x in enumerate(units):
  d=O/f'u{i+1:03}';d.mkdir();t=time.monotonic();row=dict(index=i+1,input=x,started=datetime.datetime.now(datetime.timezone.utc).isoformat())
  if t>=deadline:row.update(status='UNSTARTED',reason='total controller cap');rows.append(row);continue
  with (d/'stdout.jsonl').open('xb') as out,(d/'stderr.txt').open('xb') as err:
   proc=subprocess.Popen([sys.executable,'-B',str(P/'scale_worker01.py'),json.dumps(x,separators=(',',':'))],stdout=out,stderr=err,start_new_session=True)
   try:code=proc.wait(timeout=min(x['cap'],max(.01,deadline-time.monotonic())));status='SUCCESS' if code==0 else 'FAILURE'
   except subprocess.TimeoutExpired:
    status='TIMEOUT';os.killpg(proc.pid,signal.SIGTERM)
    try:code=proc.wait(timeout=1)
    except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);code=proc.wait()
  row.update(status=status,returncode=code,seconds=time.monotonic()-t,stdout_sha256=sha(d/'stdout.jsonl'),stderr_sha256=sha(d/'stderr.txt'))
  if status=='SUCCESS':
   try:
    lines=[json.loads(line) for line in (d/'stdout.jsonl').read_text().splitlines()];z=lines[-1];assert len(lines)==2 and z['phase']=='COMPLETE' and z['input']==x and z['status']=='SUCCESS'
    row['result']={k:v for k,v in z.items() if k not in ['input','coverage_profile','sorted_component_order','certificate']};row['artifact_bytes']=(d/'stdout.jsonl').stat().st_size
   except Exception as e:row.update(status='INVALID',parse_error=repr(e))
  put(d/'RESULT.json',row);rows.append(row)
  if (i+1)%12==0 or row['status']!='SUCCESS':print(json.dumps(dict(completed=i+1,statuses=dict(collections.Counter(r['status'] for r in rows)),seconds=time.monotonic()-start)),flush=True)
 put(O/'OUTCOMES.json',rows)
 put(O/'RECEIPT.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='COMPLETE' if len(rows)==216 and not any(r['status']=='UNSTARTED' for r in rows) else 'INCOMPLETE',planned=216,rows=len(rows),statuses=dict(collections.Counter(r['status'] for r in rows)),seconds=time.monotonic()-start,outcomes_sha256=sha(O/'OUTCOMES.json'),scope='One local process per fixed algorithm/input unit. All statuses retained. Ratio agreement/certificate rechecking require a separate analysis.'))
 print((O/'RECEIPT.json').read_text(),flush=True)
except BaseException as e:
 put(O/'FAILURE_RECEIPT.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),error=repr(e),traceback=traceback.format_exc(),rows=len(rows),seconds=time.monotonic()-start));raise
