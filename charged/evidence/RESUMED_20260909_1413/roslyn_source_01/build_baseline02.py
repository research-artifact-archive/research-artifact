from pathlib import Path
import os,subprocess,json,datetime,time,signal,hashlib
D=Path(__file__).resolve().parent;C=Path('<AUTHOR_HOME>/Research/roslyn_build_20260909');O=D/'baseline_build02';O.mkdir();C.mkdir()
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
write(O/'PATH_CHANGE_INTENT.json',{'utc':utc(),'hypothesis':'MSBuild wildcard import with literal asterisk in original source/SDK/NuGet physical paths','original':str(D),'physical_build_root':str(C),'copy_method':'APFS cp -cR clones, preserving original source bytes','source_edits':0,'previous_failed_build':'baseline_build01','scientific_outcomes':0})
for sub in ['source','dotnet','nuget_packages']:subprocess.run(['/bin/cp','-cR',str(D/sub),str(C/sub)],check=True,timeout=90)
R=C/'source/roslyn-6c4a46a31302167b425d5e0a31ea83c9a9aa1d09';sdk=C/'dotnet';env=os.environ.copy();suppressed=env.pop('__ToolsetLocationOutputFile',None)
env.update({'DOTNET_ROOT':str(sdk),'DOTNET_INSTALL_DIR':str(sdk),'DOTNET_CLI_HOME':str(C/'dotnet_cli_state'),'DOTNET_CLI_TELEMETRY_OPTOUT':'1','DOTNET_NOLOGO':'1','DOTNET_GENERATE_ASPNET_CERTIFICATE':'false','DOTNET_SKIP_FIRST_TIME_EXPERIENCE':'1','NUGET_PACKAGES':str(C/'nuget_packages'),'PATH':str(sdk)+os.pathsep+env.get('PATH','')})
argv=[str(sdk/'dotnet'),'build','src/Workspaces/CSharp/Portable/Microsoft.CodeAnalysis.CSharp.Workspaces.csproj','-c','Release','-f','net8.0','--disable-build-servers','--nologo','-v:minimal','-p:RunAnalyzersDuringBuild=false','-p:EnableSourceControlManagerQueries=false','-p:EnableSourceLink=false','-p:SourceRevisionId=6c4a46a31302167b425d5e0a31ea83c9a9aa1d09']
files={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(R.rglob('*')) if p.is_file() and 'artifacts' not in p.relative_to(R).parts}
write(O/'SOURCE_MANIFEST.json',files)
plan={'utc':utc(),'kind':'DEPENDENCY_BASELINE_BUILD_PATH_FIX','argv':argv,'cwd':str(R),'timeout_seconds':600,'source_revision':'6c4a46a31302167b425d5e0a31ea83c9a9aa1d09','workspace_source_sha256':hashlib.sha256((R/'src/Workspaces/Core/Portable/Workspace/Workspace.cs').read_bytes()).hexdigest(),'source_manifest_sha256':hashlib.sha256((O/'SOURCE_MANIFEST.json').read_bytes()).hexdigest(),'source_edits':0,'scientific_outcomes':0,'system_install':False,'inherited_toolset_suppression_was_set':suppressed is not None};write(O/'INTENT.json',plan);started=time.monotonic()
with (O/'stdout.txt').open('x') as out,(O/'stderr.txt').open('x') as err:
 p=subprocess.Popen(argv,cwd=R,env=env,stdout=out,stderr=err,start_new_session=True);write(O/'PROCESS.json',{'pid':p.pid,'pgid':p.pid,'argv':argv})
 try:code=p.wait(timeout=600);status='SUCCESS' if code==0 else 'FAILURE'
 except subprocess.TimeoutExpired:
  os.killpg(p.pid,signal.SIGTERM)
  try:code=p.wait(timeout=5)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);code=p.wait()
  status='TIMEOUT'
receipt={'utc':utc(),'status':status,'returncode':code,'seconds':time.monotonic()-started,'new_scientific_outcomes':0};write(O/'RESULT.json',receipt);print(json.dumps(receipt));print((O/'stdout.txt').read_text()[-16000:]);print((O/'stderr.txt').read_text()[-2500:])
