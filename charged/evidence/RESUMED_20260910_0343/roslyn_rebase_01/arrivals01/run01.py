from pathlib import Path
import collections,datetime,hashlib,json,os,signal,subprocess,time
D=Path(__file__).resolve().parent;C=Path('<AUTHOR_HOME>/Research/roslyn_build_20260909');S=Path('<AUTHOR_HOME>/Research/roslyn_semantics_20260910');app=S/'rebase01_arrivals/bin/Release/net10.0';baseline=S/'rebase01_arrivals_baseline'
assert json.loads((D/'build01/RESULT.json').read_text())['status']=='SUCCESS'
O=D/'run01';O.mkdir()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
order=json.loads((D/'harness01/PROCESS_ORDER.json').read_text());origin=D.parents[1]/'roslyn_semantics_01'
write(O/'INPUT_RECEIPT.json',{'utc':utc(),'kind':'AUTHOR_EXPLORATION_FIXED_BEFORE_FIRST_EXECUTION','files_sha256':{str(x.relative_to(D)):sha(x) for x in [D/'PLAN.md',D/'check01.py',D/'harness01/Program.cs',D/'harness01/PROCESS_ORDER.json',Path(__file__)]},'source_sha256':sha(D.parent/'patch01/Workspace.patched.cs'),'manifest_sha256':sha(origin/'PREDECESSOR/repository_inputs02/MANIFEST.json'),'applications':{label:{x.name:sha(x) for x in folder.glob('*.dll')} for label,folder in [('patched',app),('baseline',baseline)]},'planned_units':3072,'measurement':2560,'warmup':512,'timeout_per_process_seconds':180,'orchestration_limit_seconds':2700,'order':order})
env=os.environ.copy();env.update({'DOTNET_ROOT':str(C/'dotnet'),'DOTNET_CLI_HOME':str(C/'dotnet_cli_state'),'DOTNET_CLI_TELEMETRY_OPTOUT':'1','DOTNET_NOLOGO':'1'})
results=[];started=time.monotonic()
for p in order['processes']:
 out=O/Path(p['input']).stem;out.mkdir();folder=baseline if p['mode']=='baseline' else app
 argv=[str(C/'dotnet/dotnet'),str(folder/'ArrivalStudy.dll'),str(D/'harness01'/p['input']),str(origin/'PREDECESSOR/repository_inputs02/MANIFEST.json'),str(D.parents[2]/'RESUMED_20260909_1413/roslyn_source_01/source/roslyn-6c4a46a31302167b425d5e0a31ea83c9a9aa1d09')]
 write(out/'INTENT.json',{'utc':utc(),'argv':argv,'timeout_seconds':180,'input_sha256':sha(D/'harness01'/p['input'])});t=time.monotonic()
 if time.monotonic()-started>2700:write(out/'RESULT.json',{'utc':utc(),'status':'NOT_RUN_ORCHESTRATION_DEADLINE'});break
 with (out/'stdout.jsonl').open('x') as stdout,(out/'stderr.txt').open('x') as stderr:
  proc=subprocess.Popen(argv,cwd=folder,env=env,stdout=stdout,stderr=stderr,start_new_session=True);write(out/'PROCESS.json',{'pid':proc.pid,'pgid':proc.pid})
  try:rc=proc.wait(timeout=180);status='SUCCESS' if rc==0 else 'FAILURE'
  except subprocess.TimeoutExpired:
   os.killpg(proc.pid,signal.SIGTERM)
   try:rc=proc.wait(timeout=3)
   except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);rc=proc.wait()
   status='TIMEOUT'
  except BaseException:
   os.killpg(proc.pid,signal.SIGTERM);proc.wait(timeout=3);raise
 try:rows=[json.loads(x) for x in (out/'stdout.jsonl').read_text().splitlines()]
 except Exception:rows=[];status='INVALID'
 result={'utc':utc(),'process':out.name,'status':status,'returncode':rc,'seconds':time.monotonic()-t,'planned_units':48,'raw_units':len(rows),'unit_statuses':dict(collections.Counter(x['status'] for x in rows)),'stdout_sha256':sha(out/'stdout.jsonl'),'stderr_sha256':sha(out/'stderr.txt')};write(out/'RESULT.json',result);results.append(result);print(json.dumps(result),flush=True)
 for x in rows:
  if x['status']!='SUCCESS':print(json.dumps({'id':x['id'],'status':x['status'],'error':x['error'][:2000]}),flush=True)
write(O/'SUMMARY.json',{'utc':utc(),'seconds':time.monotonic()-started,'processes':results,'planned_units':3072,'raw_units':sum(x['raw_units'] for x in results),'scope':'authored independent-arrival study; all outcomes retained; not production traces or a general performance guarantee'})
result=subprocess.run(['python3',str(D/'check01.py')],capture_output=True,text=True,timeout=90);(O/'checker_stdout.txt').write_text(result.stdout);(O/'checker_stderr.txt').write_text(result.stderr);print(result.stdout[-7000:]);print(result.stderr[-2500:])
