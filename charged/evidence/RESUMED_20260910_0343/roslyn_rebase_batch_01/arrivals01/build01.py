from pathlib import Path
import datetime,hashlib,json,os,shutil,subprocess,time
D=Path(__file__).resolve().parent;S=Path('/external/roslyn-semantics');C=Path('/external/roslyn-toolchain');native=S/'batch_rebase_native01';O=D/'build01';O.mkdir();start=time.monotonic()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(n,x):
 with (O/n).open('x') as f:json.dump(x,f,indent=2);f.write('\n')
r=json.loads((native/'SUMMARY.json').read_text());assert r['status']=='SUCCESS' and r['semantic_units']==236 and len(r['reentry'])==23 and r['compiler_projection_receipt']['status']=='PASS'
assert r['patch_sha256']==sha(D.parent/'patch01/Workspace.patched.cs')
project=S/'batch_rebase_arrivals01';project.mkdir();(project/'lib').mkdir()
for name in ['Program.cs','ArrivalStudy.csproj']:shutil.copyfile(D/'harness01'/name,project/name)
for p in (native/'harness_repo01/bin/Release/net10.0').glob('*.dll'):shutil.copyfile(p,project/'lib'/p.name)
env=dict(os.environ,DOTNET_ROOT=str(C/'dotnet'),DOTNET_CLI_HOME=str(project/'dotnet_cli'),DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_NOLOGO='1',NUGET_PACKAGES=str(C/'nuget_packages'));argv=[str(C/'dotnet/dotnet'),'build',str(project/'ArrivalStudy.csproj'),'-c','Release','--disable-build-servers','--nologo','-v:minimal']
put('INTENT.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),argv=argv,source_sha256=sha(D/'harness01/Program.cs'),plan_sha256=sha(D/'PLAN.md'),native_summary_sha256=sha(native/'SUMMARY.json'),cap=180))
r=subprocess.run(argv,env=env,cwd=project,capture_output=True,timeout=180);(O/'stdout.txt').write_bytes(r.stdout);(O/'stderr.txt').write_bytes(r.stderr)
if r.returncode:
 put('RESULT.json',dict(status='FAILURE',returncode=r.returncode,seconds=time.monotonic()-start));raise SystemExit(r.returncode)
app=project/'bin/Release/net10.0';old=S/'batch_rebase_arrivals01_sequential';shutil.copytree(app,old)
oldsource=S/'public_extended_native02/harness_repo01/bin/Release/net10.0'
for name in ['Microsoft.CodeAnalysis','Microsoft.CodeAnalysis.CSharp','Microsoft.CodeAnalysis.Workspaces','Microsoft.CodeAnalysis.CSharp.Workspaces']:shutil.copyfile(oldsource/(name+'.dll'),old/(name+'.dll'))
put('RESULT.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='SUCCESS',returncode=r.returncode,seconds=time.monotonic()-start,batch_app=str(app),sequential_app=str(old),harness_sha256=sha(app/'ArrivalStudy.dll'),applications={label:{p.name:sha(p) for p in folder.glob('*.dll')} for label,folder in [('batch',app),('sequential',old)]}))
print('SUCCESS',time.monotonic()-start,flush=True)
