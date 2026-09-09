#!/usr/bin/env python3
"""Rebuild pinned Roslyn source and replay quiet controls, repository cases and repaired reentry.
Requires a separately obtained matching SDK and source archive. Does not rerun timing campaigns.
"""
from pathlib import Path
import argparse,datetime,hashlib,json,os,shutil,signal,subprocess,sys,tarfile,time
HERE=Path(__file__).resolve().parent;DATA=HERE/'evidence/RESUMED_20260909_1413/roslyn_source_01';REV='6c4a46a31302167b425d5e0a31ea83c9a9aa1d09';SDK_VERSION='10.0.100-rc.1.25451.107'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def read(p):return json.loads(p.read_text())
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--sdk',type=Path,required=True);a.add_argument('--source-archive',type=Path,required=True);a.add_argument('--packages',type=Path);a.add_argument('--out',type=Path,required=True);args=a.parse_args()
 sdk=args.sdk.resolve();archive=args.source_archive.resolve();out=args.out.resolve()
 if any(c in str(out) for c in '*?[]'):raise ValueError('Use an output path without glob metacharacters: MSBuild source item expansion treats these specially.')
 out.mkdir(parents=True,exist_ok=False);results=[];started=time.monotonic()
 env=dict(os.environ,DOTNET_ROOT=str(sdk),DOTNET_CLI_HOME=str(out/'dotnet_cli'),DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_NOLOGO='1',DOTNET_GENERATE_ASPNET_CERTIFICATE='false',DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1',NUGET_PACKAGES=str(args.packages.resolve() if args.packages else out/'nuget_packages'))
 env['PATH']=str(sdk)+os.pathsep+env.get('PATH','');dotnet=sdk/'dotnet'
 def run(label,argv,cwd,cap=300):
  folder=out/'logs'/label;folder.mkdir(parents=True);write(folder/'INTENT.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':list(map(str,argv)),'cwd':str(cwd),'cap_seconds':cap});t=time.monotonic()
  with (folder/'stdout.txt').open('x') as stdout,(folder/'stderr.txt').open('x') as stderr:
   p=subprocess.Popen(list(map(str,argv)),cwd=cwd,env=env,stdout=stdout,stderr=stderr,start_new_session=True);write(folder/'PROCESS.json',{'pid':p.pid,'pgid':p.pid})
   try:rc=p.wait(timeout=cap);status='SUCCESS' if rc==0 else 'FAILURE'
   except subprocess.TimeoutExpired:
    os.killpg(p.pid,signal.SIGTERM)
    try:rc=p.wait(timeout=3)
    except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);rc=p.wait()
    status='TIMEOUT'
  row={'stage':label,'status':status,'returncode':rc,'seconds':time.monotonic()-t,'stdout_sha256':sha(folder/'stdout.txt'),'stderr_sha256':sha(folder/'stderr.txt')};write(folder/'RESULT.json',row);results.append(row);print(json.dumps(row),flush=True)
  if status!='SUCCESS':raise RuntimeError('stage '+label+' '+status+'; logs preserved')
  return folder
 try:
  expected=next(x for x in read(DATA/'TOOLCHAIN_MATERIALIZATION_RESULT.json')['results'] if x['kind']=='source')['sha256'];assert sha(archive)==expected,'source archive hash'
  version=run('sdk-version',[dotnet,'--version'],out,20);assert (version/'stdout.txt').read_text().strip()==SDK_VERSION,'SDK version mismatch'
  source=out/'source';source.mkdir()
  with tarfile.open(archive) as tf:
   # The archive is authenticated above; still reject path traversal and links.
   for member in tf.getmembers():
    target=(source/member.name).resolve();assert target.is_relative_to(source) and not member.issym() and not member.islnk(),'unsafe source member'
   tf.extractall(source)
  root=source/('roslyn-'+REV);workspace=root/'src/Workspaces/Core/Portable/Workspace/Workspace.cs';assert sha(workspace)==sha(DATA/'patch01/Workspace.original.cs')
  manifest=read(DATA/'repository_inputs02/MANIFEST.json');pristine=out/'source_inputs'
  for name,meta in manifest['files'].items():
   p=root/name;assert p.stat().st_size==meta['bytes'] and sha(p)==meta['sha256'],name
   target=pristine/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
  harness=out/'harness_repo01';shutil.copytree(DATA/'harness_repo01',harness)
  switches=['-c','Release','--disable-build-servers','--nologo','-v:minimal','-p:NetRoslynSourceBuild=net8.0','-p:RunAnalyzersDuringBuild=false','-p:EnableSourceControlManagerQueries=false','-p:EnableSourceLink=false','-p:SourceRevisionId='+REV]
  def build(label,project):return run(label,[dotnet,'build',project,*switches],root,360)
  build('build-unmodified',harness/'RetryStudy.csproj');app=harness/'bin/Release/net10.0';baseline=out/'baseline_app';shutil.copytree(app,baseline)
  shutil.copyfile(DATA/'patch03/Workspace.patched.cs',workspace);build('build-patch03',harness/'RetryStudy.csproj')
  patched=out/'patched_app';shutil.copytree(app,patched)
  checkers=out/'checkers';checkers.mkdir();shutil.copyfile(DATA/'check_repository01.py',checkers/'check_repository01.py');(checkers/'repository_inputs02').mkdir();shutil.copyfile(DATA/'repository_inputs02/MANIFEST.json',checkers/'repository_inputs02/MANIFEST.json')
  checks=[]
  for label,folder,units,expected_rows in [('baseline',baseline,'BASELINE_RUNS.tsv',4),('patched',patched,'DEVELOPMENT_RUNS.tsv',69)]:
   native=run('native-'+label,[dotnet,folder/'RetryStudy.dll',harness/units,DATA/'repository_inputs02/MANIFEST.json',pristine],folder,120)
   check=out/(label+'-check');run('check-'+label,[sys.executable,'-B',checkers/'check_repository01.py','--runs',harness/units,'--raw',native/'stdout.txt','--out',check],out,60)
   receipt=read(check/'CHECK_RECEIPT.json');assert receipt['status']=='PASS' and receipt['counts']=={'SUCCESS':expected_rows};checks.append({'label':label,'records':expected_rows})
  reentry=out/'reentry_probe01';shutil.copytree(DATA/'reentry_probe01',reentry);build('build-reentry',reentry/'ReentryProbe.csproj');reentry_app=reentry/'bin/Release/net10.0';reentry_baseline=out/'reentry_baseline_app';shutil.copytree(reentry_app,reentry_baseline)
  for name in ['Microsoft.CodeAnalysis','Microsoft.CodeAnalysis.CSharp','Microsoft.CodeAnalysis.Workspaces','Microsoft.CodeAnalysis.CSharp.Workspaces']:shutil.copyfile(baseline/(name+'.dll'),reentry_baseline/(name+'.dll'))
  for mode in ['baseline','original','two','three']:
   folder=reentry_baseline if mode=='baseline' else reentry_app;result=run('reentry-'+mode,[dotnet,folder/'ReentryProbe.dll',mode],folder,10)
   rows=[json.loads(x) for x in (result/'stdout.txt').read_text().splitlines()];x=rows[-1];assert x['phase']=='terminal' and x['status']=='SUCCESS' and x['notifications']==1 and x['completed_reentries']==1 and x['same_text_identity'] is True
  summary={'status':'SUCCESS','checks':checks,'reentry_successes':4,'source_revision':REV,'sdk_version':SDK_VERSION,'source_archive_sha256':expected,'patch03_sha256':sha(workspace),'public_source_manifest_sha256':sha(DATA/'repository_inputs02/MANIFEST.json'),'whole_seconds':time.monotonic()-started,'steps':results,'scope':'New executions of fixed semantic inputs, with zero-writer unmodified controls and repaired same-text reentry. No new evaluation population or timing-campaign rerun; does not verify event payloads or arbitrary host safety.'};write(out/'SUMMARY.json',summary);print(json.dumps({k:v for k,v in summary.items() if k!='steps'},indent=2))
 except Exception as e:
  write(out/'FAILURE.json',{'status':'FAILURE','error':repr(e),'steps':results,'seconds':time.monotonic()-started,'retry':False});raise
if __name__=='__main__':main()
