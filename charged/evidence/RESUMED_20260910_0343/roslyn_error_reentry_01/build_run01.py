from pathlib import Path
import collections,datetime,hashlib,json,os,shutil,signal,subprocess,time
D=Path(__file__).resolve().parent;C=Path('<AUTHOR_HOME>/Research/roslyn_build_20260909');S=Path('<AUTHOR_HOME>/Research/roslyn_semantics_20260910');H=S/'error_harness01';H.mkdir()
O=D/'build01';O.mkdir()
shutil.copy2(D/'harness01/Program.cs',H/'Program.cs')
subprocess.run(['/bin/cp','-cR',str(S/'harness01/lib'),str(H/'lib')],check=True,timeout=30)
proj=(S/'harness01/SemanticsStudy.csproj').read_text();(H/'ReentryStudy.csproj').write_text(proj);(D/'harness01/ReentryStudy.csproj').write_text(proj)
env=os.environ.copy();env.update({'DOTNET_ROOT':str(C/'dotnet'),'DOTNET_CLI_HOME':str(C/'dotnet_cli_state'),'DOTNET_CLI_TELEMETRY_OPTOUT':'1','DOTNET_NOLOGO':'1','NUGET_PACKAGES':str(C/'nuget_packages')})
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
argv=[str(C/'dotnet/dotnet'),'build',str(H/'ReentryStudy.csproj'),'--disable-build-servers','-c','Release'];write(O/'INTENT.json',{'utc':utc(),'argv':argv,'source_sha256':sha(H/'Program.cs')})
with (O/'stdout.txt').open('x') as out,(O/'stderr.txt').open('x') as err:result=subprocess.run(argv,cwd=H,env=env,stdout=out,stderr=err,timeout=120)
write(O/'RESULT.json',{'utc':utc(),'status':'SUCCESS' if result.returncode==0 else 'FAILURE','rc':result.returncode})
print((O/'stdout.txt').read_text()[-3000:],flush=True)
if result.returncode:raise SystemExit(result.returncode)
app=H/'bin/Release/net10.0';baseline=S/'error_baseline01';subprocess.run(['/bin/cp','-cR',str(app),str(baseline)],check=True,timeout=30)
for name in ['Microsoft.CodeAnalysis','Microsoft.CodeAnalysis.CSharp','Microsoft.CodeAnalysis.Workspaces','Microsoft.CodeAnalysis.CSharp.Workspaces']:shutil.copy2(C/f'baseline_bin/{name}/Release/net8.0/{name}.dll',baseline/(name+'.dll'))
units=[(mode,r,scenario) for mode in ['original','two','three'] for r in [0,1] for scenario in ['missing_before','removed_between']]+[('baseline',r,'missing_before') for r in [0,1]]
run=D/'run01';run.mkdir();write(run/'INPUT_RECEIPT.json',{'utc':utc(),'units':units,'total':len(units),'harness_source_sha256':sha(D/'harness01/Program.cs'),'harness_binary_sha256':sha(app/'ReentryStudy.dll'),'patched_workspace_sha256':sha(app/'Microsoft.CodeAnalysis.Workspaces.dll'),'baseline_workspace_sha256':sha(baseline/'Microsoft.CodeAnalysis.Workspaces.dll'),'plan_sha256':sha(D/'PLAN.md'),'timeout_seconds_each':3})
rows=[]
for idx,(mode,r,scenario) in enumerate(units,1):
 folder=baseline if mode=='baseline' else app;out=run/f'u{idx:02d}_{mode}_r{r}_{scenario}';out.mkdir();argv=[str(C/'dotnet/dotnet'),str(folder/'ReentryStudy.dll'),mode,str(r),scenario];write(out/'INTENT.json',{'utc':utc(),'argv':argv})
 t=time.monotonic()
 with (out/'stdout.jsonl').open('x') as stdout,(out/'stderr.jsonl').open('x') as stderr:
  proc=subprocess.Popen(argv,cwd=folder,env=env,stdout=stdout,stderr=stderr,start_new_session=True);write(out/'PROCESS.json',{'pid':proc.pid,'pgid':proc.pid})
  try:rc=proc.wait(timeout=3);status='SUCCESS' if rc==0 else 'FAILURE'
  except subprocess.TimeoutExpired:
   os.killpg(proc.pid,signal.SIGTERM)
   try:rc=proc.wait(timeout=1)
   except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);rc=proc.wait()
   status='TIMEOUT'
 records=[json.loads(x) for x in (out/'stdout.jsonl').read_text().splitlines()]
 row={'utc':utc(),'unit':out.name,'mode':mode,'r':r,'scenario':scenario,'process_status':status,'status':status if status!='SUCCESS' else records[0]['status'] if len(records)==1 else 'INVALID','returncode':rc,'seconds':time.monotonic()-t,'stdout_sha256':sha(out/'stdout.jsonl'),'stderr_sha256':sha(out/'stderr.jsonl'),'record':records}
 write(out/'RESULT.json',row);rows.append(row);print(json.dumps(row),flush=True)
summary={'utc':utc(),'total':len(rows),'status_counts':dict(collections.Counter(r['status'] for r in rows)),'results':rows,'remaining_processes':0}
write(run/'SUMMARY.json',summary)

