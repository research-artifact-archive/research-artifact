from pathlib import Path
import datetime,hashlib,json,os,random,shutil,subprocess,time
D=Path(__file__).resolve().parent/'arrivals01';old=D.parents[1]/'roslyn_arrivals_01';C=Path('<AUTHOR_HOME>/Research/roslyn_build_20260909');S=Path('<AUTHOR_HOME>/Research/roslyn_semantics_20260910')
assert json.loads((D.parent/'semantics01/run01/check01/RECEIPT.json').read_text())['status']=='PASS';assert json.loads((D.parent/'reentry_controls01/SUMMARY.json').read_text())['status_counts']=={'SUCCESS':23}
H=D/'harness01';H.mkdir();s=(old/'harness01/Program.cs').read_text()
s=s.replace('Set(state,"Remaining",u.R);','Set(state,"Remaining",u.R);Set(state,"AllowPreparedRebase",u.Mode=="rebase");').replace('"Mismatches","CheapFailures"}', '"Mismatches","CheapFailures","Rebases"}')
s=s.replace('if(u.Mode=="three"&&','if((u.Mode=="three"||u.Mode=="rebase")&&')
(H/'Program.cs').write_text(s)
base=[('baseline',0),('rebase',2),('two',0),('original',0),('three',0),('rebase',0),('two',2),('three',2)];rng=random.Random(9100530);procs=[]
for block in range(8):
 for position,(mode,r) in enumerate(base[block:]+base[:block],1):
  fork=block+1;seq=len(procs)+1;name=f'p{seq:02d}_b{fork}_pos{position}_{mode}_r{r}.tsv';rows=[]
  for phase,reps in [('warmup',2),('measurement',10)]:
   for rep in range(1,reps+1):
    periods=[0,10,100,1000];rng.shuffle(periods)
    for interval in periods:rows.append([f'b{fork}_{mode}_r{r}_{phase}_{rep}_d{interval}',phase,fork,rep,interval,mode,r])
  (H/name).write_text(''.join('\t'.join(map(str,x))+'\n' for x in rows));procs.append({'sequence':seq,'fork':fork,'block':fork,'position':position,'mode':mode,'r':r,'units':48,'input':name,'sha256':hashlib.sha256((H/name).read_bytes()).hexdigest()})
(H/'PROCESS_ORDER.json').write_text(json.dumps({'seed':9100530,'design':'eight cyclic Latin-square blocks','processes':procs,'units':3072,'measurement':2560,'warmup':512},indent=2)+'\n')
check=(old/'check01.py').read_text().replace('864','3072')
check=check.replace("  require(q==32+fail and 0<=fail<=during,'call accounting')", "  require(q==32+fail and 0<=fail<=during,'call accounting')\n  require(c['Rebases']>=0 and (row['mode']=='rebase' or c['Rebases']==0),'rebase mode binding')")
check=check.replace("row['mode']=='three' and outside==q and c['Mismatches']==fail+inside", "row['mode'] in ('three','rebase') and outside==q and c['Mismatches']==fail+inside+c['Rebases']")
a=" candidate=next((x for x in allrows if x['status']=='SUCCESS' and x['mode']=='original'),None);ctrl=controls(candidate) if candidate else []";assert a in check
b=""" candidate=next((x for x in allrows if x['status']=='SUCCESS' and x['mode']=='original'),None);ctrl=controls(candidate) if candidate else []
 for name,mode in [('rebase_mismatch_partition','rebase'),('original_rebase_ineligible','original')]:
  sample=next((x for x in allrows if x['status']=='SUCCESS' and x['mode']==mode),None)
  if sample:
   corrupt=copy.deepcopy(sample);corrupt['counters']['Rebases']+=1
   try:check(corrupt);detected=False
   except Exception:detected=True
   ctrl.append({'name':name,'detected':detected})
 require(len(ctrl)==10,'corruption-control denominator')"""
check=check.replace(a,b);(D/'check01.py').write_text(check)
run=(old/'run01.py').read_text().replace("app=S/'arrivals_harness01/bin/Release/net10.0';baseline=S/'arrivals_baseline01'", "app=S/'rebase01_arrivals/bin/Release/net10.0';baseline=S/'rebase01_arrivals_baseline'")
run=run.replace("origin=D.parent/'roslyn_semantics_01'","origin=D.parents[1]/'roslyn_semantics_01'").replace("D.parent/'roslyn_patch04_01/patch04/Workspace.patched.cs'", "D.parent/'patch01/Workspace.patched.cs'").replace("D.parent.parent/'RESUMED_20260909_1413", "D.parents[2]/'RESUMED_20260909_1413")
run=run.replace('864','3072').replace("'measurement':720,'warmup':144","'measurement':2560,'warmup':512")
(D/'run01.py').write_text(run)
analysis=(old/'analyze01.py').read_text().replace('864','3072').replace('720','2560').replace('144,','512,').replace('==30','==80').replace("'forks':3","'forks':8").replace('for fork in [1,2,3]:','for fork in range(1,9):').replace("c['period_us'],30,","c['period_us'],80,")
analysis=analysis.replace("('two',2),('three',2)]","('two',2),('three',2),('rebase',0),('rebase',2)]").replace("('two','three')", "('two','three','rebase')")
analysis=analysis.replace("'mismatches':c['Mismatches']", "'mismatches':c['Mismatches'],'protected_rebases':c['Rebases']").replace("'PreparedOutside','Mismatches']", "'PreparedOutside','Mismatches','Rebases']")
analysis=analysis.replace("'L_count_median'","'protected_full_transform_median'").replace("'W_count_median'","'total_full_transform_median'")
analysis=analysis.replace('Fixed random shuffle placed all three instrumented-original forks first; process order is a possible thermal/JIT/load confound and was not changed after observation. No rerun or causality claim.', 'Eight fixed cyclic Latin-square blocks balance process position. All source arms use the new DLL; rebase performs protected partial-merge work in addition to full transformations. Not a total-work or whole-system optimum claim.')
(D/'analyze01.py').write_text(analysis)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
safe=S/'rebase01_arrivals';safe.mkdir();lib=safe/'lib';lib.mkdir()
for f in (S/'rebase01_semantics/lib').glob('*.dll'):shutil.copy2(f,lib/f.name)
shutil.copy2(H/'Program.cs',safe/'Program.cs');proj='<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net10.0</TargetFramework><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable><LangVersion>preview</LangVersion></PropertyGroup><ItemGroup>'+''.join('<Reference Include="'+f.stem+'"><HintPath>lib/'+f.name+'</HintPath><Private>true</Private></Reference>' for f in sorted(lib.glob('*.dll')))+ '</ItemGroup></Project>\n'
(safe/'ArrivalStudy.csproj').write_text(proj);(H/'ArrivalStudy.csproj').write_text(proj);B=D/'build01';B.mkdir();env=os.environ.copy();env.update({'DOTNET_ROOT':str(C/'dotnet'),'DOTNET_CLI_HOME':str(C/'dotnet_cli_state'),'DOTNET_CLI_TELEMETRY_OPTOUT':'1','DOTNET_NOLOGO':'1','NUGET_PACKAGES':str(C/'nuget_packages')});argv=[str(C/'dotnet/dotnet'),'build',str(safe/'ArrivalStudy.csproj'),'--disable-build-servers','-c','Release']
write(B/'INPUT.json',{'utc':utc(),'argv':argv,'source_sha256':sha(safe/'Program.cs'),'checker_sha256':sha(D/'check01.py'),'process_order_sha256':sha(H/'PROCESS_ORDER.json'),'planned_units':3072,'library_sha256':{x.name:sha(x) for x in lib.glob('*.dll')}});t=time.monotonic()
with (B/'stdout.txt').open('x') as out,(B/'stderr.txt').open('x') as err:result=subprocess.run(argv,cwd=safe,env=env,stdout=out,stderr=err,timeout=120)
write(B/'RESULT.json',{'utc':utc(),'status':'SUCCESS' if result.returncode==0 else 'FAILURE','returncode':result.returncode,'seconds':time.monotonic()-t});print((B/'RESULT.json').read_text());print((B/'stdout.txt').read_text()[-2500:])
if result.returncode==0:
 baseline=S/'rebase01_arrivals_baseline';subprocess.run(['/bin/cp','-cR',str(safe/'bin/Release/net10.0'),str(baseline)],check=True,timeout=30)
 for name in ['Microsoft.CodeAnalysis','Microsoft.CodeAnalysis.CSharp','Microsoft.CodeAnalysis.Workspaces','Microsoft.CodeAnalysis.CSharp.Workspaces']:shutil.copy2(C/f'baseline_bin/{name}/Release/net8.0/{name}.dll',baseline/(name+'.dll'))
