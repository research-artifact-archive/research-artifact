from pathlib import Path
import datetime,hashlib,json,os,shutil,signal,subprocess,time
D=Path(__file__).resolve().parent;C=Path('<AUTHOR_HOME>/Research/roslyn_build_20260909');R=C/'source/roslyn-6c4a46a31302167b425d5e0a31ea83c9a9aa1d09';app=C/'harness_repo01/bin/Release/net10.0';O=D/'repository_development01';O.mkdir()
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
assert json.loads((D/'harness_repo_build01/RESULT.json').read_text())['status']=='SUCCESS'
names=['Microsoft.CodeAnalysis','Microsoft.CodeAnalysis.CSharp','Microsoft.CodeAnalysis.Workspaces','Microsoft.CodeAnalysis.CSharp.Workspaces']
for name in names:assert sha(app/(name+'.dll'))==sha(R/f'artifacts/bin/{name}/Release/net8.0/{name}.dll'),name
baseline=C/'repository_baseline_app01';subprocess.run(['/bin/cp','-cR',str(app),str(baseline)],check=True,timeout=60)
for name in names:shutil.copy2(C/f'baseline_bin/{name}/Release/net8.0/{name}.dll',baseline/(name+'.dll'))
write(O/'INPUT_RECEIPT.json',{'utc':utc(),'kind':'DEVELOPMENT_BEFORE_FIRST_SOURCE_EXECUTION','source_patch_sha256':sha(D/'patch03/Workspace.patched.cs'),'harness_source_sha256':sha(D/'harness_repo01/Program.cs'),'harness_binary_sha256':sha(app/'RetryStudy.dll'),'patched_libraries':{name:sha(app/(name+'.dll')) for name in names},'baseline_libraries':{name:sha(baseline/(name+'.dll')) for name in names},'input_lists':{n:sha(D/'harness_repo01'/n) for n in ['DEVELOPMENT_RUNS.tsv','BASELINE_RUNS.tsv']},'development_units':69,'baseline_control_units':4,'runtime':'PinnedSDK10RC runtime, net10 harness with net8 Roslyn binaries','not_final_measurement':True})
env=os.environ.copy();env.update({'DOTNET_ROOT':str(C/'dotnet'),'DOTNET_CLI_HOME':str(C/'dotnet_cli_state'),'DOTNET_CLI_TELEMETRY_OPTOUT':'1','DOTNET_NOLOGO':'1'})
def run(label,folder,units,cap):
 out=O/label;out.mkdir();argv=[str(C/'dotnet/dotnet'),str(folder/'RetryStudy.dll'),str(D/'harness_repo01'/units),str(D/'repository_inputs02/MANIFEST.json'),str(D/'source/roslyn-6c4a46a31302167b425d5e0a31ea83c9a9aa1d09')];write(out/'INTENT.json',{'utc':utc(),'argv':argv,'timeout_seconds':cap});start=time.monotonic()
 with (out/'stdout.jsonl').open('x') as stdout,(out/'stderr.txt').open('x') as stderr:
  p=subprocess.Popen(argv,cwd=folder,env=env,stdout=stdout,stderr=stderr,start_new_session=True);write(out/'PROCESS.json',{'pid':p.pid,'pgid':p.pid})
  try:rc=p.wait(timeout=cap);status='SUCCESS' if rc==0 else 'FAILURE'
  except subprocess.TimeoutExpired:
   os.killpg(p.pid,signal.SIGTERM)
   try:rc=p.wait(timeout=3)
   except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);rc=p.wait()
   status='TIMEOUT'
 receipt={'utc':utc(),'status':status,'returncode':rc,'seconds':time.monotonic()-start,'stdout_sha256':sha(out/'stdout.jsonl'),'stderr_sha256':sha(out/'stderr.txt')};write(out/'RESULT.json',receipt);print(label,json.dumps(receipt),flush=True)
 rows=[json.loads(x) for x in (out/'stdout.jsonl').read_text().splitlines()]
 from collections import Counter
 print(label,len(rows),dict(Counter(x['status'] for x in rows)),flush=True)
 for x in rows:
  if x['status']!='SUCCESS':print(json.dumps({'id':x['id'],'projects':x['projects'],'r':x['r'],'B':x['B'],'mode':x['mode'],'scenario':x['scenario'],'status':x['status'],'error':x['error'][:1800]}),flush=True)
 return rows
run('baseline',baseline,'BASELINE_RUNS.tsv',90)
run('patched',app,'DEVELOPMENT_RUNS.tsv',240)
