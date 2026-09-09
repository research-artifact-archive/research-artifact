from pathlib import Path
import datetime,hashlib,json,os,shutil,subprocess
P=Path(__file__).resolve().parent
S=Path('<AUTHOR_HOME>/Research/roslyn_semantics_20260910/compiler_projection01');S.mkdir()
N=Path('<AUTHOR_HOME>/Research/roslyn_semantics_20260910/public_extended_native01')
patched=N/'harness_repo01/bin/Release/net10.0';lib=S/'lib';lib.mkdir();names=[]
for p in sorted(patched.glob('*.dll')):
    if p.name=='RetryStudy.dll':continue
    shutil.copyfile(p,lib/p.name);names.append(p.stem)
project='<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net10.0</TargetFramework><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable><LangVersion>preview</LangVersion></PropertyGroup><ItemGroup>'+''.join('<Reference Include="'+n+'"><HintPath>lib/'+n+'.dll</HintPath><Private>true</Private></Reference>' for n in names)+'</ItemGroup></Project>\n'
(P/'CompilerStudy.csproj').write_text(project);shutil.copyfile(P/'Program.cs',S/'Program.cs');(S/'CompilerStudy.csproj').write_text(project)
inputs=[]
for scenario in ['library_type','library_constant','unrelated_spare','target_parse','linked_reference_removed','target_writer']:
    for mode,r in [('baseline',0),('original',0),('two',0),('three',0),('rebase',0),('two',1),('three',1),('rebase',1)]:
        for cache in ['cold','warm']:inputs.append([f'u{len(inputs)+1:03d}',mode,str(r),scenario,cache])
assert len(inputs)==96
(P/'UNITS.tsv').write_text('\n'.join('\t'.join(x) for x in inputs)+'\n');O=P/'build01';O.mkdir()
C=Path('<AUTHOR_HOME>/Research/roslyn_build_20260909')
env=dict(os.environ,DOTNET_ROOT=str(C/'dotnet'),DOTNET_CLI_HOME=str(S/'dotnet_cli'),DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_NOLOGO='1',NUGET_PACKAGES=str(C/'nuget_packages'));env['PATH']=str(C/'dotnet')+os.pathsep+env.get('PATH','')
argv=[str(C/'dotnet/dotnet'),'build',str(S/'CompilerStudy.csproj'),'-c','Release','--disable-build-servers','--nologo','-v:minimal']
(O/'INTENT.json').write_text(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':argv,'source_sha256':hashlib.sha256((P/'Program.cs').read_bytes()).hexdigest(),'cap_seconds':60},indent=2)+'\n')
r=subprocess.run(argv,env=env,cwd=S,capture_output=True,timeout=60)
(O/'stdout.txt').write_bytes(r.stdout);(O/'stderr.txt').write_bytes(r.stderr);(O/'RESULT.json').write_text(json.dumps({'status':'SUCCESS' if r.returncode==0 else 'FAILURE','returncode':r.returncode},indent=2)+'\n')
print(r.stdout.decode()[-3500:]);print(r.stderr.decode()[-1500:]);assert r.returncode==0
app=S/'bin/Release/net10.0';baseline=S/'baseline';shutil.copytree(app,baseline)
for n in ['Microsoft.CodeAnalysis','Microsoft.CodeAnalysis.CSharp','Microsoft.CodeAnalysis.Workspaces','Microsoft.CodeAnalysis.CSharp.Workspaces']:
    shutil.copyfile(N/'baseline_app'/(n+'.dll'),baseline/(n+'.dll'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
binding={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'patched':str(app),'baseline':str(baseline),'files':{label:{p.name:sha(p) for p in sorted(folder.iterdir()) if p.is_file()} for label,folder in [('patched',app),('baseline',baseline)]}}
(P/'APPLICATIONS.json').write_text(json.dumps(binding,indent=2)+'\n')
