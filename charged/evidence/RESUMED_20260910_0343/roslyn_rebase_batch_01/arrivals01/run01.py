from pathlib import Path
import collections,datetime,hashlib,json,os,signal,subprocess,sys,time
D=Path(__file__).resolve().parent;P=D.parents[1];C=Path('/external/roslyn-toolchain');S=Path('/external/roslyn-semantics');apps={'batch-source':S/'batch_rebase_arrivals01/bin/Release/net10.0','sequential':S/'batch_rebase_arrivals01_sequential'}
assert json.loads((D/'build01/RESULT.json').read_text())['status']=='SUCCESS'
assert json.loads((P/'PUBLICATION_03/PUBLIC_REPLAY_COMPLETION01.json').read_text())['status']=='SUCCESS'
assert json.loads((S/'batch_rebase_native01/SUMMARY.json').read_text())['status']=='SUCCESS'
O=D/'run01';O.mkdir()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def write(p,x):
 with p.open('x') as f:json.dump(x,f,indent=2);f.write('\n')
order=json.loads((D/'harness01/PROCESS_ORDER.json').read_text());manifest=P/'roslyn_semantics_01/PREDECESSOR/repository_inputs02/MANIFEST.json';source=S/'batch_rebase_native01/source_inputs'
write(O/'INPUT_RECEIPT.json',dict(utc=utc(),kind='AUTHOR_NEW_PAIRED_DESIGN_FIXED_BEFORE_FIRST_EXECUTION',source_hashes={str(x.relative_to(D)):sha(x) for x in [D/'PLAN.md',D/'check01.py',D/'harness01/Program.cs',D/'harness01/PROCESS_ORDER.json',Path(__file__)]},new_patch_sha256=sha(D.parent/'patch01/Workspace.patched.cs'),old_patch_sha256=sha(P/'roslyn_rebase_01/patch01/Workspace.patched.cs'),source_manifest_sha256=sha(manifest),applications={label:{x.name:sha(x) for x in folder.glob('*.dll')} for label,folder in apps.items()},input_hashes={p['input']:sha(D/'harness01'/p['input']) for p in order['processes']},planned_units=1728,measurement=1440,warmup=288,processes=36,timeout_per_process_seconds=60,orchestration_limit_seconds=600,all_owned_builds_and_public_replay_complete_before_start=True,order=order))
env=dict(os.environ,DOTNET_ROOT=str(C/'dotnet'),DOTNET_CLI_HOME=str(C/'dotnet_cli_state'),DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_NOLOGO='1');results=[];started=time.monotonic();deadline=started+600
try:
 for p in order['processes']:
  out=O/Path(p['input']).stem;out.mkdir();folder=apps[p['implementation']];argv=[str(C/'dotnet/dotnet'),str(folder/'ArrivalStudy.dll'),str(D/'harness01'/p['input']),str(manifest),str(source)];t=time.monotonic()
  write(out/'INTENT.json',dict(utc=utc(),argv=argv,timeout_seconds=60,implementation=p['implementation'],input_sha256=sha(D/'harness01'/p['input'])))
  with (out/'stdout.jsonl').open('xb') as stdout,(out/'stderr.txt').open('xb') as stderr:
   if t>=deadline:rc=None;status='UNSTARTED'
   else:
    proc=subprocess.Popen(argv,cwd=folder,env=env,stdout=stdout,stderr=stderr,start_new_session=True);write(out/'PROCESS.json',dict(pid=proc.pid,pgid=proc.pid))
    try:rc=proc.wait(timeout=min(60,max(.01,deadline-time.monotonic())));status='SUCCESS' if rc==0 else 'FAILURE'
    except subprocess.TimeoutExpired:
     os.killpg(proc.pid,signal.SIGTERM)
     try:rc=proc.wait(timeout=2)
     except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);rc=proc.wait()
     status='TIMEOUT'
    except BaseException:
     os.killpg(proc.pid,signal.SIGTERM)
     try:proc.wait(timeout=2)
     except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
     raise
  try:rows=[json.loads(x) for x in (out/'stdout.jsonl').read_text().splitlines()]
  except Exception:rows=[];status='INVALID'
  result=dict(utc=utc(),process=out.name,implementation=p['implementation'],status=status,returncode=rc,seconds=time.monotonic()-t,planned_units=48,raw_units=len(rows),unit_statuses=dict(collections.Counter(x['status'] for x in rows)),stdout_sha256=sha(out/'stdout.jsonl'),stderr_sha256=sha(out/'stderr.txt'));write(out/'RESULT.json',result);results.append(result);print(json.dumps(result),flush=True)
 write(O/'SUMMARY.json',dict(utc=utc(),seconds=time.monotonic()-started,processes=results,process_statuses=dict(collections.Counter(r['status'] for r in results)),planned_units=1728,raw_units=sum(x['raw_units'] for x in results),scope='New paired comparison for a changed batched source merge, nonblocking phase observer, all outcomes retained; no old result is replaced.'))
 result=subprocess.run([sys.executable,'-B',str(D/'check01.py')],capture_output=True,text=True,timeout=90);(O/'checker_stdout.txt').write_text(result.stdout);(O/'checker_stderr.txt').write_text(result.stderr);print(result.stdout[-4000:],flush=True);print(result.stderr[-1500:],flush=True)
 assert result.returncode==0 and json.loads((O/'check01/RECEIPT.json').read_text())['status']=='PASS'
except BaseException as e:
 write(O/'FAILURE_RECEIPT.json',dict(utc=utc(),error=repr(e),completed_processes=len(results),seconds=time.monotonic()-started));raise
