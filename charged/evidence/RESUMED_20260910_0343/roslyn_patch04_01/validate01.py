from pathlib import Path
import collections,datetime,hashlib,json,os,shutil,signal,subprocess,time
D=Path(__file__).resolve().parent;P=D.parent
C=Path('<AUTHOR_HOME>/Research/roslyn_build_20260909');S=Path('<AUTHOR_HOME>/Research/roslyn_semantics_20260910')
assert json.loads((D/'build01/RESULT.json').read_text())['status']=='SUCCESS'
names=['Microsoft.CodeAnalysis','Microsoft.CodeAnalysis.CSharp','Microsoft.CodeAnalysis.Workspaces','Microsoft.CodeAnalysis.CSharp.Workspaces']
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
apps={}
for label,origin in [('error',S/'error_harness01/bin/Release/net10.0'),('semantics',S/'harness01/bin/Release/net10.0'),('same_text',C/'reentry_app_patch03')]:
 app=S/('patch04_'+label);assert not app.exists();subprocess.run(['/bin/cp','-cR',str(origin),str(app)],check=True,timeout=30)
 for name in names:shutil.copy2(S/f'patch04_source/artifacts/bin/{name}/Release/net8.0/{name}.dll',app/(name+'.dll'))
 apps[label]=app
write(D/'APPLICATIONS.json',{'utc':utc(),'source_sha256':sha(D/'patch04/Workspace.patched.cs'),'libraries':{label:{x.name:sha(x) for x in app.glob('*.dll')} for label,app in apps.items()},'harnesses_unchanged':True})
env=os.environ.copy();env.update({'DOTNET_ROOT':str(C/'dotnet'),'DOTNET_CLI_HOME':str(C/'dotnet_cli_state'),'DOTNET_CLI_TELEMETRY_OPTOUT':'1','DOTNET_NOLOGO':'1'})
def execute(out,folder,assembly,args,cap):
 out.mkdir();argv=[str(C/'dotnet/dotnet'),str(folder/(assembly+'.dll')),*map(str,args)];write(out/'INTENT.json',{'utc':utc(),'argv':argv,'timeout_seconds':cap})
 t=time.monotonic()
 with (out/'stdout.jsonl').open('x') as stdout,(out/'stderr.txt').open('x') as stderr:
  proc=subprocess.Popen(argv,cwd=folder,env=env,stdout=stdout,stderr=stderr,start_new_session=True);write(out/'PROCESS.json',{'pid':proc.pid,'pgid':proc.pid})
  try:rc=proc.wait(timeout=cap);status='SUCCESS' if rc==0 else 'FAILURE'
  except subprocess.TimeoutExpired:
   os.killpg(proc.pid,signal.SIGTERM)
   try:rc=proc.wait(timeout=2)
   except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);rc=proc.wait()
   status='TIMEOUT'
 try:rows=[json.loads(x) for x in (out/'stdout.jsonl').read_text().splitlines()]
 except Exception:rows=[];status='INVALID'
 result={'utc':utc(),'status':status,'returncode':rc,'seconds':time.monotonic()-t,'rows':len(rows),'unit_statuses':dict(collections.Counter(x.get('status','NONTERMINAL') for x in rows)),'stdout_sha256':sha(out/'stdout.jsonl'),'stderr_sha256':sha(out/'stderr.txt')};write(out/'RESULT.json',result);print(str(out.relative_to(D)),json.dumps(result),flush=True)
 return result,rows

# Exact same error inputs and executable as the failed predecessor, successor source only.
O=D/'error_run01';O.mkdir();units=json.loads((P/'roslyn_error_reentry_01/run01/INPUT_RECEIPT.json').read_text())['units']
write(O/'INPUT_RECEIPT.json',{'utc':utc(),'units':units,'total':14,'source_sha256':sha(D/'patch04/Workspace.patched.cs'),'harness_sha256':sha(apps['error']/'ReentryStudy.dll'),'applications_sha256':sha(D/'APPLICATIONS.json'),'predecessor_input_sha256':sha(P/'roslyn_error_reentry_01/run01/INPUT_RECEIPT.json'),'timeout_seconds_each':3})
details=[]
for idx,(mode,r,scenario) in enumerate(units,1):
 out=O/f'u{idx:02d}_{mode}_r{r}_{scenario}';result,rows=execute(out,S/'error_baseline01' if mode=='baseline' else apps['error'],'ReentryStudy',[mode,r,scenario],3)
 status=result['status'] if result['status']!='SUCCESS' else rows[0]['status'] if len(rows)==1 else 'INVALID'
 details.append({'unit':out.name,'status':status,'record':rows})
write(O/'SUMMARY.json',{'utc':utc(),'units':len(details),'status_counts':dict(collections.Counter(x['status'] for x in details)),'details':details})

# Same-text callback reentry from patch03, all four original modes.
O=D/'same_text_run01';O.mkdir();write(O/'INPUT_RECEIPT.json',{'utc':utc(),'modes':['baseline','original','two','three'],'harness_sha256':sha(apps['same_text']/'ReentryProbe.dll'),'applications_sha256':sha(D/'APPLICATIONS.json'),'timeout_seconds_each':3})
details=[]
for mode in ['baseline','original','two','three']:
 result,rows=execute(O/mode,C/'reentry_baseline_app02' if mode=='baseline' else apps['same_text'],'ReentryProbe',[mode],3)
 terminal=[x for x in rows if x.get('phase')=='terminal'];status=result['status'] if result['status']!='SUCCESS' else terminal[0]['status'] if len(terminal)==1 else 'INVALID'
 details.append({'mode':mode,'status':status,'rows':rows})
write(O/'SUMMARY.json',{'utc':utc(),'units':4,'status_counts':dict(collections.Counter(x['status'] for x in details)),'details':details})

# Unchanged native semantic executable, all input units, and byte-identical checker.
M=D/'semantics01';M.mkdir();(M/'harness01').mkdir();O=M/'run01';O.mkdir();origin=P/'roslyn_semantics_01'
for name in ['UNITS.tsv','BASELINE.tsv','Program.cs']:shutil.copy2(origin/'harness01'/name,M/'harness01'/name)
shutil.copy2(origin/'check01.py',M/'check01.py')
write(O/'INPUT_RECEIPT.json',{'utc':utc(),'source_sha256':sha(D/'patch04/Workspace.patched.cs'),'harness_sha256':sha(apps['semantics']/'SemanticsStudy.dll'),'checker_sha256':sha(M/'check01.py'),'applications_sha256':sha(D/'APPLICATIONS.json'),'units_sha256':{name:sha(M/'harness01'/name) for name in ['UNITS.tsv','BASELINE.tsv']},'patched_units':174,'unmodified_zero_writer_controls':4,'predecessor_input_sha256':sha(origin/'run01/INPUT_RECEIPT.json')})
for label,folder,unitfile,cap in [('baseline',S/'baseline_app01','BASELINE.tsv',60),('patched',apps['semantics'],'UNITS.tsv',300)]:
 execute(O/label,folder,'SemanticsStudy',[M/'harness01'/unitfile,origin/'PREDECESSOR/repository_inputs02/MANIFEST.json',P.parent/'RESUMED_20260909_1413/roslyn_source_01/source/roslyn-6c4a46a31302167b425d5e0a31ea83c9a9aa1d09'],cap)
result=subprocess.run(['python3',str(M/'check01.py')],capture_output=True,text=True,timeout=60);(M/'checker_stdout.txt').write_text(result.stdout);(M/'checker_stderr.txt').write_text(result.stderr);print(result.stdout[-5000:]);print(result.stderr[-2000:])
write(D/'VALIDATION_RECEIPT.json',{'utc':utc(),'error_run_sha256':sha(D/'error_run01/SUMMARY.json'),'same_text_run_sha256':sha(D/'same_text_run01/SUMMARY.json'),'semantic_checker_sha256':sha(M/'run01/check01/RECEIPT.json'),'checker_returncode':result.returncode,'interpretation':'Author-side source successor validation; all predecessor negative outcomes retained; no general lock-safety or performance certificate'})
