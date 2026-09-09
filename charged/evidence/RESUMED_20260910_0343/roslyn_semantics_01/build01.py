from pathlib import Path
import datetime,hashlib,json,os,shutil,signal,subprocess,time
D=Path(__file__).resolve().parent;C=Path('<AUTHOR_HOME>/Research/roslyn_build_20260909')
O=D/'build01';O.mkdir()
safe=Path('<AUTHOR_HOME>/Research/roslyn_semantics_20260910');safe.mkdir()
src=safe/'harness01';src.mkdir()
lib=src/'lib';lib.mkdir()
old=C/'harness_repo01/bin/Release/net10.0'
receipt=json.loads((D/'PREDECESSOR/repository_development01/INPUT_RECEIPT.json').read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for name,digest in receipt['patched_libraries'].items():assert sha(old/(name+'.dll'))==digest,name
for f in old.glob('*.dll'):shutil.copy2(f,lib/f.name)
shutil.copy2(D/'harness01/Program.cs',src/'Program.cs')
proj='''<Project Sdk="Microsoft.NET.Sdk">
<PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net10.0</TargetFramework><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable><LangVersion>preview</LangVersion></PropertyGroup>
<ItemGroup>'''+''.join('<Reference Include="'+f.stem+'"><HintPath>lib/'+f.name+'</HintPath><Private>true</Private></Reference>' for f in sorted(lib.glob('*.dll')) if f.name!='RetryStudy.dll')+'''</ItemGroup></Project>
'''
(src/'SemanticsStudy.csproj').write_text(proj);(D/'harness01/SemanticsStudy.csproj').write_text(proj)
env=os.environ.copy();env.update({'DOTNET_ROOT':str(C/'dotnet'),'DOTNET_CLI_HOME':str(C/'dotnet_cli_state'),'DOTNET_CLI_TELEMETRY_OPTOUT':'1','DOTNET_NOLOGO':'1','NUGET_PACKAGES':str(C/'nuget_packages')})
argv=[str(C/'dotnet/dotnet'),'build',str(src/'SemanticsStudy.csproj'),'--disable-build-servers','-c','Release']
(O/'INPUT.json').write_text(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':argv,'source_sha256':sha(src/'Program.cs'),'library_sha256':{x.name:sha(x) for x in lib.glob('*.dll')}},indent=2)+'\n')
t=time.monotonic()
with (O/'stdout.txt').open('x') as out,(O/'stderr.txt').open('x') as err:
 result=subprocess.run(argv,cwd=src,env=env,stdout=out,stderr=err,timeout=120)
r={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'SUCCESS' if result.returncode==0 else 'FAILURE','returncode':result.returncode,'seconds':time.monotonic()-t,'new_scientific_outcomes':0}
(O/'RESULT.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
print((O/'stdout.txt').read_text()[-6000:])

