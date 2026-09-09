from pathlib import Path
import datetime,hashlib,json,os,shutil,subprocess,time
D=Path(__file__).resolve().parent;old=D.parent/'roslyn_semantics_01';C=Path('<AUTHOR_HOME>/Research/roslyn_build_20260909');S=Path('<AUTHOR_HOME>/Research/roslyn_semantics_20260910');R=S/'rebase01_source'
assert json.loads((D/'build01/RESULT.json').read_text())['status']=='SUCCESS'
H=D/'semantics01';H.mkdir();h=H/'harness01';h.mkdir();shutil.copy2(D/'PLAN.md',H/'PLAN.md')
s=(old/'harness01/Program.cs').read_text()
a='"three"=>1,_=>throw new ArgumentException("mode")';assert a in s;s=s.replace(a,'"three"=>1,"rebase"=>1,_=>throw new ArgumentException("mode")')
a='Set(state,"Remaining",u.R);';assert a in s;s=s.replace(a,a+'Set(state,"AllowPreparedRebase",u.Mode=="rebase");')
a='else if(Normal(u)&&writes<u.B&&(u.Scenario!="spread"||writes<job))Inject(false);';assert a in s
s=s.replace(a,'''else if(Normal(u)&&writes<u.B&&(u.Scenario!="spread"||writes<job))
                        {
                            int count=u.Mode=="rebase"&&u.Scenario=="normal"&&opportunities==1?Math.Max(1,u.B-3):1;
                            for(int wi=0;wi<count;wi++)Inject(false);
                        }''')
s=s.replace('"Mismatches","CheapFailures"}', '"Mismatches","CheapFailures","Rebases"}')
a='''                long f=Math.Min(u.B,u.R);long calls=u.Mode=="original"?4+u.B:4+f;
                long inside=u.Mode switch{"original"=>0,"two"=>u.B>=u.R?4:0,"three"=>Math.Min(Math.Max(u.B-u.R,0),4),_=>throw new Exception("mode")};
                long outside=u.Mode=="original"?4+u.B:u.Mode=="two"&&u.B>=u.R?f:4+f;
                if(counters["Calls"]!=calls||counters["PreparedInside"]!=inside||counters["PreparedOutside"]!=outside||counters["CheapFailures"]!=(u.Mode=="original"?u.B:f))throw new Exception("source resource equation");'''
b='''                bool backgroundRebase=u.Mode=="rebase"&&!TargetWriter(u);
                long f=backgroundRebase?0:Math.Min(u.B,u.R);long calls=u.Mode=="original"?4+u.B:4+f;
                long inside=backgroundRebase?0:u.Mode switch{"original"=>0,"two"=>u.B>=u.R?4:0,"three" or "rebase"=>Math.Min(Math.Max(u.B-u.R,0),4),_=>throw new Exception("mode")};
                long outside=u.Mode=="original"?4+u.B:u.Mode=="two"&&u.B>=u.R?f:4+f;
                if(counters["Calls"]!=calls||counters["PreparedInside"]!=inside||counters["PreparedOutside"]!=outside||counters["CheapFailures"]!=(u.Mode=="original"?u.B:f))throw new Exception("source resource equation");
                if(counters["Rebases"]!=(backgroundRebase?Math.Min(u.B,4):0))throw new Exception("rebase resource equation");'''
assert a in s;s=s.replace(a,b);(h/'Program.cs').write_text(s)
rows=(old/'harness01/UNITS.tsv').read_text().splitlines();new=[]
for line in rows:
 parts=line.split('\t')
 if parts[7]=='three':parts[0]='rb'+str(len(new)+1).zfill(4);parts[7]='rebase';new.append('\t'.join(parts))
assert len(new)==58;(h/'UNITS.tsv').write_text('\n'.join(rows+new)+'\n');shutil.copy2(old/'harness01/BASELINE.tsv',h/'BASELINE.tsv')
check=(old/'check01.py').read_text()
check=check.replace("('CheapFailures','cheap_failure')", "('CheapFailures','cheap_failure'),('Rebases','rebase_completed')")
a="  if normal:\n   require(counters['Calls']==4+counters['CheapFailures'],'calls from publications/failures')";assert a in check
b="""  require(counters['Rebases']==0 if row['mode']!='rebase' or target_writer else counters['Rebases']>=0,'rebase eligibility')
  if normal:
   if row['mode'] in ('three','rebase'):
    require(counters['Mismatches']==counters['CheapFailures']+counters['PreparedInside']+counters['Rebases'],'mismatch partition')
   require(counters['Calls']==4+counters['CheapFailures'],'calls from publications/failures')"""
check=check.replace(a,b)
a=" controls=mutation_controls(candidate) if candidate else []";assert a in check
b=""" controls=mutation_controls(candidate) if candidate else []
 rebase_candidate=next((r for r in allrows if r['mode']=='rebase' and r['scenario']=='normal' and r['B']==1 and r['status']=='SUCCESS'),None)
 if rebase_candidate:
  corrupt=copy.deepcopy(rebase_candidate);corrupt['counters']['Rebases']+=1
  try:check(corrupt);detected=False
  except (AssertionError,KeyError,IndexError,TypeError):detected=True
  controls.append({'control':'rebase_trace_count','detected':detected})
 target_candidate=next((r for r in allrows if r['mode']=='rebase' and r['scenario']=='target_writer' and r['B']==1 and r['r']==0 and r['status']=='SUCCESS'),None)
 if target_candidate:
  corrupt=copy.deepcopy(target_candidate);corrupt['counters']['Rebases']=1;corrupt['counters']['PreparedInside']-=1
  victim=next(t for t in corrupt['trace'] if t['Kind']=='kernel_inside_begin');victim['Kind']='rebase_completed'
  try:check(corrupt);detected=False
  except (AssertionError,KeyError,IndexError,TypeError):detected=True
  controls.append({'control':'same_target_rebase_ineligible','detected':detected})
 require(len(controls)==12 and all(x['detected'] for x in controls),'complete corruption controls')"""
check=check.replace(a,b);(H/'check01.py').write_text(check)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
safe=S/'rebase01_semantics';safe.mkdir();lib=safe/'lib';lib.mkdir()
for f in (S/'harness01/lib').glob('*.dll'):shutil.copy2(f,lib/f.name)
for name in ['Microsoft.CodeAnalysis','Microsoft.CodeAnalysis.CSharp','Microsoft.CodeAnalysis.Workspaces','Microsoft.CodeAnalysis.CSharp.Workspaces']:shutil.copy2(R/f'artifacts/bin/{name}/Release/net8.0/{name}.dll',lib/(name+'.dll'))
shutil.copy2(h/'Program.cs',safe/'Program.cs');shutil.copy2(old/'harness01/SemanticsStudy.csproj',safe/'SemanticsStudy.csproj');shutil.copy2(safe/'SemanticsStudy.csproj',h/'SemanticsStudy.csproj')
O=H/'build01';O.mkdir();env=os.environ.copy();env.update({'DOTNET_ROOT':str(C/'dotnet'),'DOTNET_CLI_HOME':str(C/'dotnet_cli_state'),'DOTNET_CLI_TELEMETRY_OPTOUT':'1','DOTNET_NOLOGO':'1','NUGET_PACKAGES':str(C/'nuget_packages')});argv=[str(C/'dotnet/dotnet'),'build',str(safe/'SemanticsStudy.csproj'),'--disable-build-servers','-c','Release']
write(O/'INPUT.json',{'utc':utc(),'argv':argv,'source_sha256':sha(safe/'Program.cs'),'checker_sha256':sha(H/'check01.py'),'units_sha256':sha(h/'UNITS.tsv'),'planned_units':232,'baseline_controls':4,'library_sha256':{x.name:sha(x) for x in lib.glob('*.dll')}});t=time.monotonic()
with (O/'stdout.txt').open('x') as out,(O/'stderr.txt').open('x') as err:result=subprocess.run(argv,cwd=safe,env=env,stdout=out,stderr=err,timeout=120)
write(O/'RESULT.json',{'utc':utc(),'status':'SUCCESS' if result.returncode==0 else 'FAILURE','returncode':result.returncode,'seconds':time.monotonic()-t,'new_scientific_outcomes':0});print((O/'RESULT.json').read_text());print((O/'stdout.txt').read_text()[-3500:])
