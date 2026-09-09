from pathlib import Path
import collections,datetime,hashlib,json,os,shutil,signal,subprocess,time
D=Path(__file__).resolve().parent;C=Path('<AUTHOR_HOME>/Research/roslyn_build_20260909');S=Path('<AUTHOR_HOME>/Research/roslyn_semantics_20260910');old=D.parents[1]/'roslyn_semantics_01'
O=D/'run01';O.mkdir();app=S/'rebase01_semantics/bin/Release/net10.0';assert json.loads((D/'build01/RESULT.json').read_text())['status']=='SUCCESS'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
baseline=S/'rebase01_semantics_baseline';subprocess.run(['/bin/cp','-cR',str(app),str(baseline)],check=True,timeout=30)
names=['Microsoft.CodeAnalysis','Microsoft.CodeAnalysis.CSharp','Microsoft.CodeAnalysis.Workspaces','Microsoft.CodeAnalysis.CSharp.Workspaces']
for name in names:shutil.copy2(C/f'baseline_bin/{name}/Release/net8.0/{name}.dll',baseline/(name+'.dll'))
assert sha(app/'SemanticsStudy.dll')==sha(baseline/'SemanticsStudy.dll')
manifest=old/'PREDECESSOR/repository_inputs02/MANIFEST.json';source=old.parents[1]/'RESUMED_20260909_1413/roslyn_source_01/source/roslyn-6c4a46a31302167b425d5e0a31ea83c9a9aa1d09';assert manifest.is_file() and source.is_dir()
write(O/'INPUT_RECEIPT.json',{'utc':utc(),'kind':'AUTHOR_EXPLORATION_BEFORE_FIRST_NEW_EXECUTION','source_patch_sha256':sha(D.parent/'patch01/Workspace.patched.cs'),'files_sha256':{str(x.relative_to(D)):sha(x) for x in [D/'PLAN.md',D/'harness01/UNITS.tsv',D/'harness01/BASELINE.tsv',D/'harness01/Program.cs',D/'check01.py',Path(__file__)]},'manifest_sha256':sha(manifest),'harness_binary_sha256':sha(app/'SemanticsStudy.dll'),'patched_library_sha256':{name:sha(app/(name+'.dll')) for name in names},'baseline_library_sha256':{name:sha(baseline/(name+'.dll')) for name in names},'patched_units':232,'unmodified_zero_writer_controls':4,'repetitions':1,'purpose':'Conservative partial-merge comparator semantic conformance, protected merges reported separately'})
env=os.environ.copy();env.update({'DOTNET_ROOT':str(C/'dotnet'),'DOTNET_CLI_HOME':str(C/'dotnet_cli_state'),'DOTNET_CLI_TELEMETRY_OPTOUT':'1','DOTNET_NOLOGO':'1'})
for label,folder,unitfile,cap in [('baseline',baseline,'BASELINE.tsv',60),('patched',app,'UNITS.tsv',180)]:
 out=O/label;out.mkdir();argv=[str(C/'dotnet/dotnet'),str(folder/'SemanticsStudy.dll'),str(D/'harness01'/unitfile),str(manifest),str(source)];write(out/'INTENT.json',{'utc':utc(),'argv':argv,'timeout_seconds':cap});t=time.monotonic()
 with (out/'stdout.jsonl').open('x') as stdout,(out/'stderr.txt').open('x') as stderr:
  proc=subprocess.Popen(argv,cwd=folder,env=env,stdout=stdout,stderr=stderr,start_new_session=True);write(out/'PROCESS.json',{'pid':proc.pid,'pgid':proc.pid})
  try:rc=proc.wait(timeout=cap);status='SUCCESS' if rc==0 else 'FAILURE'
  except subprocess.TimeoutExpired:
   os.killpg(proc.pid,signal.SIGTERM)
   try:rc=proc.wait(timeout=3)
   except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);rc=proc.wait()
   status='TIMEOUT'
 rows=[json.loads(x) for x in (out/'stdout.jsonl').read_text().splitlines()];r={'utc':utc(),'status':status,'returncode':rc,'seconds':time.monotonic()-t,'rows':len(rows),'unit_statuses':dict(collections.Counter(x['status'] for x in rows)),'stdout_sha256':sha(out/'stdout.jsonl'),'stderr_sha256':sha(out/'stderr.txt')};write(out/'RESULT.json',r);print(label,json.dumps(r),flush=True)
 for x in rows:
  if x['status']!='SUCCESS':print(json.dumps({'id':x['id'],'mode':x['mode'],'scenario':x['scenario'],'r':x['r'],'B':x['B'],'status':x['status'],'error':x['error'][:1800]}),flush=True)
 if rc!=0:print((out/'stderr.txt').read_text()[-2500:],flush=True)
