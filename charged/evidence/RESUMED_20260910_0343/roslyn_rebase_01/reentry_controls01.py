from pathlib import Path
import collections,datetime,hashlib,json,os,shutil,signal,subprocess,time
D=Path(__file__).resolve().parent;P=D.parent;C=Path('<AUTHOR_HOME>/Research/roslyn_build_20260909');S=Path('<AUTHOR_HOME>/Research/roslyn_semantics_20260910');O=D/'reentry_controls01';O.mkdir()
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
env=os.environ.copy();env.update({'DOTNET_ROOT':str(C/'dotnet'),'DOTNET_CLI_HOME':str(C/'dotnet_cli_state'),'DOTNET_CLI_TELEMETRY_OPTOUT':'1','DOTNET_NOLOGO':'1','NUGET_PACKAGES':str(C/'nuget_packages')})
programs={
'error':(P/'roslyn_error_reentry_01/harness01/Program.cs').read_text(),
'same':(P.parent/'RESUMED_20260909_1413/roslyn_source_01/reentry_probe01/Program.cs').read_text()}
programs['error']=programs['error'].replace('Set(state,"Remaining",r);','Set(state,"Remaining",r);Set(state,"AllowPreparedRebase",mode=="rebase");').replace('"Mismatches","CheapFailures"}', '"Mismatches","CheapFailures","Rebases"}')
programs['same']=programs['same'].replace('"three"=>1,_=>','"three"=>1,"rebase"=>1,_=>').replace('type.GetField("Remaining",flags)!.SetValue(state,0);','type.GetField("Remaining",flags)!.SetValue(state,0);type.GetField("AllowPreparedRebase",flags)!.SetValue(state,args[0]=="rebase");')
apps={}
for label,program in programs.items():
 H=O/label;H.mkdir();safe=S/('rebase01_'+label+'_harness');safe.mkdir();lib=safe/'lib';lib.mkdir()
 for f in (S/'rebase01_semantics/lib').glob('*.dll'):shutil.copy2(f,lib/f.name)
 for dest in [H/'Program.cs',safe/'Program.cs']:dest.write_text(program)
 proj='<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net10.0</TargetFramework><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable><LangVersion>preview</LangVersion></PropertyGroup><ItemGroup>'+''.join('<Reference Include="'+f.stem+'"><HintPath>lib/'+f.name+'</HintPath><Private>true</Private></Reference>' for f in sorted(lib.glob('*.dll')))+ '</ItemGroup></Project>\n'
 (safe/'Control.csproj').write_text(proj);(H/'Control.csproj').write_text(proj);B=H/'build01';B.mkdir();argv=[str(C/'dotnet/dotnet'),'build',str(safe/'Control.csproj'),'--disable-build-servers','-c','Release'];write(B/'INTENT.json',{'utc':utc(),'argv':argv,'source_sha256':sha(safe/'Program.cs')})
 with (B/'stdout.txt').open('x') as out,(B/'stderr.txt').open('x') as err:r=subprocess.run(argv,cwd=safe,env=env,stdout=out,stderr=err,timeout=120)
 write(B/'RESULT.json',{'utc':utc(),'status':'SUCCESS' if r.returncode==0 else 'FAILURE','returncode':r.returncode});assert r.returncode==0,(B/'stdout.txt').read_text()[-4000:]
 app=safe/'bin/Release/net10.0';base=S/('rebase01_'+label+'_baseline');subprocess.run(['/bin/cp','-cR',str(app),str(base)],check=True,timeout=30)
 for name in ['Microsoft.CodeAnalysis','Microsoft.CodeAnalysis.CSharp','Microsoft.CodeAnalysis.Workspaces','Microsoft.CodeAnalysis.CSharp.Workspaces']:shutil.copy2(C/f'baseline_bin/{name}/Release/net8.0/{name}.dll',base/(name+'.dll'))
 apps[label]={'patched':app,'baseline':base}
error_units=json.loads((P/'roslyn_error_reentry_01/run01/INPUT_RECEIPT.json').read_text())['units']+[['rebase',r,scenario] for r in [0,1] for scenario in ['missing_before','removed_between']]
same_units=[[mode] for mode in ['baseline','original','two','three','rebase']]
write(O/'INPUT_RECEIPT.json',{'utc':utc(),'error_units':error_units,'same_units':same_units,'total':23,'timeout_seconds_each':3,'source_sha256':sha(D/'patch01/Workspace.patched.cs'),'harness_sha256':{k:sha(v['patched']/'Control.dll') for k,v in apps.items()},'modification':'New rebase label only sets Mode1 + opt-in true; all original modes retain their previous values'})
results=[]
for kind,units in [('error',error_units),('same',same_units)]:
 R=O/kind/'run01';R.mkdir()
 for i,args in enumerate(units,1):
  out=R/(f'u{i:02d}_'+'_'.join(map(str,args)));out.mkdir();folder=apps[kind]['baseline' if args[0]=='baseline' else 'patched'];argv=[str(C/'dotnet/dotnet'),str(folder/'Control.dll'),*map(str,args)];write(out/'INTENT.json',{'utc':utc(),'argv':argv,'timeout_seconds':3});t=time.monotonic()
  with (out/'stdout.jsonl').open('x') as stdout,(out/'stderr.txt').open('x') as stderr:
   proc=subprocess.Popen(argv,cwd=folder,env=env,stdout=stdout,stderr=stderr,start_new_session=True);write(out/'PROCESS.json',{'pid':proc.pid,'pgid':proc.pid})
   try:rc=proc.wait(timeout=3);status='SUCCESS' if rc==0 else 'FAILURE'
   except subprocess.TimeoutExpired:
    os.killpg(proc.pid,signal.SIGTERM)
    try:rc=proc.wait(timeout=2)
    except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);rc=proc.wait()
    status='TIMEOUT'
  try:rows=[json.loads(x) for x in (out/'stdout.jsonl').read_text().splitlines()]
  except Exception:rows=[];status='INVALID'
  terminal=[x for x in rows if kind=='error' or x.get('phase')=='terminal']
  if status=='SUCCESS':status=terminal[0]['status'] if len(terminal)==1 else 'INVALID'
  result={'utc':utc(),'kind':kind,'args':args,'status':status,'returncode':rc,'seconds':time.monotonic()-t,'rows':rows,'stdout_sha256':sha(out/'stdout.jsonl'),'stderr_sha256':sha(out/'stderr.txt')};write(out/'RESULT.json',result);results.append(result);print(kind,args,status,flush=True)
write(O/'SUMMARY.json',{'utc':utc(),'units':23,'status_counts':dict(collections.Counter(x['status'] for x in results)),'results':results});print(json.dumps({'units':23,'status_counts':dict(collections.Counter(x['status'] for x in results))}))
