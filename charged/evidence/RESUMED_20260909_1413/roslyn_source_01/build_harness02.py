from pathlib import Path
import os,subprocess,json,datetime,time,signal,hashlib
D=Path(__file__).resolve().parent;C=Path('<AUTHOR_HOME>/Research/roslyn_build_20260909');R=C/'source/roslyn-6c4a46a31302167b425d5e0a31ea83c9a9aa1d09';O=D/'harness_build02';O.mkdir();sdk=C/'dotnet';env=os.environ.copy();env.update({'DOTNET_ROOT':str(sdk),'DOTNET_CLI_HOME':str(C/'dotnet_cli_state'),'DOTNET_CLI_TELEMETRY_OPTOUT':'1','DOTNET_NOLOGO':'1','DOTNET_GENERATE_ASPNET_CERTIFICATE':'false','DOTNET_SKIP_FIRST_TIME_EXPERIENCE':'1','NUGET_PACKAGES':str(C/'nuget_packages'),'PATH':str(sdk)+os.pathsep+env.get('PATH','')})
argv=[str(sdk/'dotnet'),'build',str(C/'harness01/RetryStudy.csproj'),'-c','Release','--disable-build-servers','--nologo','-v:minimal','-p:NetRoslynSourceBuild=net8.0','-p:RunAnalyzersDuringBuild=false','-p:EnableSourceControlManagerQueries=false','-p:EnableSourceLink=false','-p:SourceRevisionId=6c4a46a31302167b425d5e0a31ea83c9a9aa1d09']
plan={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'kind':'HARNESS_BUILD','argv':argv,'cwd':str(R),'timeout_seconds':600,'source_revision':'6c4a46a31302167b425d5e0a31ea83c9a9aa1d09','workspace_source_sha256':hashlib.sha256((R/'src/Workspaces/Core/Portable/Workspace/Workspace.cs').read_bytes()).hexdigest(),'source_edits':1,'scientific_outcomes':0,'system_install':False};(O/'INTENT.json').write_text(json.dumps(plan,indent=2)+'\n');started=time.monotonic()
with (O/'stdout.txt').open('x') as out,(O/'stderr.txt').open('x') as err:
 p=subprocess.Popen(argv,cwd=R,env=env,stdout=out,stderr=err,start_new_session=True)
 (O/'PROCESS.json').write_text(json.dumps({'pid':p.pid,'pgid':p.pid,'argv':argv},indent=2)+'\n')
 try:code=p.wait(timeout=600);status='SUCCESS' if code==0 else 'FAILURE'
 except subprocess.TimeoutExpired:
  os.killpg(p.pid,signal.SIGTERM)
  try:code=p.wait(timeout=5)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);code=p.wait()
  status='TIMEOUT'
receipt={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':status,'returncode':code,'seconds':time.monotonic()-started,'new_scientific_outcomes':0};(O/'RESULT.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt));print((O/'stdout.txt').read_text()[-10000:]);print((O/'stderr.txt').read_text()[-2500:])
