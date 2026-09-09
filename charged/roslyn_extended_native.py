#!/usr/bin/env python3
"""Rebuild unmodified and guarded-rebase Roslyn, then execute fixed semantics and reentry controls.
Requires the pinned external SDK and authenticated source archive. No timing campaign is rerun.
"""
from pathlib import Path
import argparse,datetime,hashlib,json,os,shutil,signal,subprocess,sys,tarfile,time
HERE=Path(__file__).resolve().parent;OLD=HERE/'evidence/RESUMED_20260909_1413/roslyn_source_01';DATA=HERE/'evidence/RESUMED_20260910_0343/roslyn_rebase_01'
REV='6c4a46a31302167b425d5e0a31ea83c9a9aa1d09';SDK_VERSION='10.0.100-rc.1.25451.107'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def read(p):return json.loads(p.read_text())
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--sdk',type=Path,required=True);parser.add_argument('--source-archive',type=Path,required=True);parser.add_argument('--packages',type=Path);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
 sdk=args.sdk.resolve();archive=args.source_archive.resolve();out=args.out.resolve()
 if any(c in str(out) for c in '*?[]'):raise ValueError('MSBuild requires an output path without glob metacharacters.')
 out.mkdir(parents=True,exist_ok=False);results=[];started=time.monotonic();deadline=started+1200
 env=dict(os.environ,DOTNET_ROOT=str(sdk),DOTNET_CLI_HOME=str(out/'dotnet_cli'),DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_NOLOGO='1',DOTNET_GENERATE_ASPNET_CERTIFICATE='false',DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1',NUGET_PACKAGES=str(args.packages.resolve() if args.packages else out/'nuget_packages'))
 env['PATH']=str(sdk)+os.pathsep+env.get('PATH','');dotnet=sdk/'dotnet'
 def run(label,argv,cwd,cap=300):
  cap=min(cap,max(1,int(deadline-time.monotonic())));folder=out/'logs'/label;folder.mkdir(parents=True);write(folder/'INTENT.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':list(map(str,argv)),'cwd':str(cwd),'cap_seconds':cap});t=time.monotonic()
  with (folder/'stdout.txt').open('x') as stdout,(folder/'stderr.txt').open('x') as stderr:
   proc=subprocess.Popen(list(map(str,argv)),cwd=cwd,env=env,stdout=stdout,stderr=stderr,start_new_session=True);write(folder/'PROCESS.json',{'pid':proc.pid,'pgid':proc.pid})
   try:rc=proc.wait(timeout=cap);status='SUCCESS' if rc==0 else 'FAILURE'
   except subprocess.TimeoutExpired:
    os.killpg(proc.pid,signal.SIGTERM)
    try:rc=proc.wait(timeout=3)
    except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);rc=proc.wait()
    status='TIMEOUT'
  row={'stage':label,'status':status,'returncode':rc,'seconds':time.monotonic()-t,'stdout_sha256':sha(folder/'stdout.txt'),'stderr_sha256':sha(folder/'stderr.txt')};write(folder/'RESULT.json',row);results.append(row);print(json.dumps(row),flush=True)
  if status!='SUCCESS':raise RuntimeError(label+' '+status+'; all logs preserved')
  return folder
 try:
  expected=next(x for x in read(OLD/'TOOLCHAIN_MATERIALIZATION_RESULT.json')['results'] if x['kind']=='source')['sha256'];assert sha(archive)==expected
  version=run('sdk-version',[dotnet,'--version'],out,20);assert (version/'stdout.txt').read_text().strip()==SDK_VERSION
  source=out/'source';source.mkdir()
  with tarfile.open(archive) as tf:
   for member in tf.getmembers():assert (source/member.name).resolve().is_relative_to(source) and not member.issym() and not member.islnk(),'unsafe archive member'
   tf.extractall(source)
  root=source/('roslyn-'+REV);workspace=root/'src/Workspaces/Core/Portable/Workspace/Workspace.cs';assert sha(workspace)==sha(OLD/'patch01/Workspace.original.cs')
  manifest=read(OLD/'repository_inputs02/MANIFEST.json');pristine=out/'source_inputs'
  for name,meta in manifest['files'].items():
   p=root/name;assert p.stat().st_size==meta['bytes'] and sha(p)==meta['sha256'],name
   target=pristine/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
  bootstrap=out/'harness_repo01';shutil.copytree(OLD/'harness_repo01',bootstrap)
  switches=['-c','Release','--disable-build-servers','--nologo','-v:minimal','-p:NetRoslynSourceBuild=net8.0','-p:RunAnalyzersDuringBuild=false','-p:EnableSourceControlManagerQueries=false','-p:EnableSourceLink=false','-p:SourceRevisionId='+REV]
  def build(label,project):return run(label,[dotnet,'build',project,*switches],root,360)
  build('build-unmodified',bootstrap/'RetryStudy.csproj');baseline=out/'baseline_app';shutil.copytree(bootstrap/'bin/Release/net10.0',baseline)
  shutil.copyfile(DATA/'patch01/Workspace.patched.cs',workspace);build('build-rebase',bootstrap/'RetryStudy.csproj');patched=bootstrap/'bin/Release/net10.0'
  # Published harness source and project files are unchanged; only their declared lib/ dependencies are materialized from this fresh source build.
  def harness(label,source_dir,project):
   dest=out/label;dest.mkdir()
   for p in source_dir.iterdir():
    if p.is_file() and p.suffix in ['.cs','.csproj','.tsv']:shutil.copyfile(p,dest/p.name)
   lib=dest/'lib';lib.mkdir()
   for p in patched.glob('*.dll'):shutil.copyfile(p,lib/p.name)
   build('build-'+label,dest/project);app=dest/'bin/Release/net10.0';original=out/(label+'_baseline');shutil.copytree(app,original)
   for name in ['Microsoft.CodeAnalysis','Microsoft.CodeAnalysis.CSharp','Microsoft.CodeAnalysis.Workspaces','Microsoft.CodeAnalysis.CSharp.Workspaces']:shutil.copyfile(baseline/(name+'.dll'),original/(name+'.dll'))
   return dest,app,original
  sem,sem_app,sem_base=harness('semantics',DATA/'semantics01/harness01','SemanticsStudy.csproj')
  check=out/'semantic_check';check.mkdir();shutil.copyfile(DATA/'semantics01/check01.py',check/'check01.py');shutil.copytree(DATA/'semantics01/harness01',check/'harness01');(check/'run01').mkdir()
  for label,folder,units in [('baseline',sem_base,'BASELINE.tsv'),('patched',sem_app,'UNITS.tsv')]:
   native=run('native-semantics-'+label,[dotnet,folder/'SemanticsStudy.dll',sem/units,OLD/'repository_inputs02/MANIFEST.json',pristine],folder,120);target=check/'run01'/label;target.mkdir();shutil.copyfile(native/'stdout.txt',target/'stdout.jsonl')
  run('check-semantics',[sys.executable,'-B',check/'check01.py'],out,60);receipt=read(check/'run01/check01/RECEIPT.json');assert receipt['status']=='PASS' and receipt['units']==236
  reentry=[]
  for kind in ['error','same']:
   _,app,original=harness(kind,DATA/'reentry_controls01'/kind,'Control.csproj')
   inputs=[x['args'] for x in read(DATA/'reentry_controls01/SUMMARY.json')['results'] if x['kind']==kind]
   for i,values in enumerate(inputs):
    folder=original if values[0]=='baseline' else app;record=run('reentry-'+kind+'-'+str(i),[dotnet,folder/'Control.dll',*map(str,values)],folder,10)
    rows=[json.loads(x) for x in (record/'stdout.txt').read_text().splitlines()]
    if kind=='error':
     assert len(rows)==1;x=rows[0];assert x['status']=='SUCCESS' and x['observed_exception']=='ArgumentException' and x['name_calls']==x['notifications']==1 and x['target_present'] is False and x['background']=='background revised from the error-name hook'
    else:
     assert len(rows)==2;x=rows[-1];assert x['phase']=='terminal' and x['status']=='SUCCESS' and x['notifications']==x['completed_reentries']==1 and x['same_text_identity'] is True
    reentry.append({'kind':kind,'args':values,'status':'SUCCESS'})
  assert len(reentry)==23
  summary={'status':'SUCCESS','source_revision':REV,'source_archive_sha256':expected,'sdk_version':SDK_VERSION,'patch_sha256':sha(workspace),'semantic_units':236,'semantic_counts':receipt['counts'],'semantic_corruption_controls':receipt['corruption_controls'],'reentry':reentry,'whole_seconds':time.monotonic()-started,'steps':results,'scope':'Fresh unmodified/rebase source builds and executions of fixed 236 event/payload/state cases plus 18 error-hook and 5 same-text controls. Does not rerun timing campaigns, remove old TIMEOUTs, prove arbitrary host safety, or generate a new evaluation population.'};write(out/'SUMMARY.json',summary);print(json.dumps({k:v for k,v in summary.items() if k!='steps'},indent=2))
 except Exception as e:
  write(out/'FAILURE.json',{'status':'FAILURE','error':repr(e),'steps':results,'seconds':time.monotonic()-started,'retry':False});raise
if __name__=='__main__':main()
