from pathlib import Path
import datetime,hashlib,json,os,shutil,signal,subprocess,time
D=Path(__file__).resolve().parent;C=Path('<AUTHOR_HOME>/Research/roslyn_build_20260909');a=C/'reentry_probe01/bin/Release/net10.0';saved=C/'reentry_app_patch03';O=D/'reentry_outcomes02';O.mkdir()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
assert json.loads((D/'reentry_build02/RESULT.json').read_text())['status']=='SUCCESS'
subprocess.run(['/bin/cp','-cR',str(a),str(saved)],check=True)
names=['Microsoft.CodeAnalysis','Microsoft.CodeAnalysis.CSharp','Microsoft.CodeAnalysis.Workspaces','Microsoft.CodeAnalysis.CSharp.Workspaces']
for name in names:assert sha(saved/(name+'.dll'))==sha(C/f'source/roslyn-6c4a46a31302167b425d5e0a31ea83c9a9aa1d09/artifacts/bin/{name}/Release/net8.0/{name}.dll'),name
baseline=C/'reentry_baseline_app02';subprocess.run(['/bin/cp','-cR',str(saved),str(baseline)],check=True)
for name in names:shutil.copy2(C/f'baseline_bin/{name}/Release/net8.0/{name}.dll',baseline/(name+'.dll'))
write(O/'INPUT_RECEIPT.json',{'utc':utc(),'program_sha256':sha(saved/'ReentryProbe.dll'),'patched_workspace_sha256':sha(saved/'Microsoft.CodeAnalysis.Workspaces.dll'),'baseline_workspace_sha256':sha(baseline/'Microsoft.CodeAnalysis.Workspaces.dll'),'plan_sha256':sha(D/'reentry_probe01/PLAN_REPAIR.json'),'cap_seconds':3,'expected_from_static_finding':'All4 return normally after source-derived same-text guard repair; old patch02 TIMEOUT retained','not_runtime_benchmark':True})
env=os.environ.copy();env.update({'DOTNET_ROOT':str(C/'dotnet'),'DOTNET_CLI_HOME':str(C/'dotnet_cli_state'),'DOTNET_CLI_TELEMETRY_OPTOUT':'1','DOTNET_NOLOGO':'1'})
results=[]
for mode in ['baseline','original','two','three']:
 out=O/mode;out.mkdir();folder=baseline if mode=='baseline' else saved;argv=[str(C/'dotnet/dotnet'),str(folder/'ReentryProbe.dll'),mode];write(out/'INTENT.json',{'utc':utc(),'argv':argv,'timeout_seconds':3});start=time.monotonic()
 with (out/'stdout.jsonl').open('x') as stdout,(out/'stderr.txt').open('x') as stderr:
  child=subprocess.Popen(argv,cwd=folder,env=env,stdout=stdout,stderr=stderr,start_new_session=True);write(out/'PROCESS.json',{'pid':child.pid,'pgid':child.pid})
  try:rc=child.wait(timeout=3);status='SUCCESS' if rc==0 else 'FAILURE'
  except subprocess.TimeoutExpired:
   os.killpg(child.pid,signal.SIGTERM)
   try:rc=child.wait(timeout=2)
   except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);rc=child.wait()
   status='TIMEOUT'
 rows=[json.loads(x) for x in (out/'stdout.jsonl').read_text().splitlines()];receipt={'utc':utc(),'mode':mode,'status':status,'returncode':rc,'seconds':time.monotonic()-start,'rows':rows,'stdout_sha256':sha(out/'stdout.jsonl'),'stderr_sha256':sha(out/'stderr.txt')};write(out/'RESULT.json',receipt);results.append(receipt);print(json.dumps(receipt),flush=True)
write(O/'SUMMARY.json',{'utc':utc(),'results':results,'interpretation':'Patch03 reentry repair validation. Retain patch02 timeout as historical failure; do not generalize to arbitrary reentrant changed updates or other host callbacks.'})
