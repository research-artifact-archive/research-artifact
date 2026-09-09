from pathlib import Path
from collections import defaultdict,Counter
import datetime,hashlib,json,os,subprocess,time
D=Path(__file__).resolve().parent;C=Path('<AUTHOR_HOME>/Research/roslyn_build_20260909');R=C/'source/roslyn-6c4a46a31302167b425d5e0a31ea83c9a9aa1d09';O=D/'repository_inputs01';O.mkdir()
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
projects=['src/Compilers/Core/Portable/Microsoft.CodeAnalysis.csproj','src/Compilers/CSharp/Portable/Microsoft.CodeAnalysis.CSharp.csproj','src/Workspaces/Core/Portable/Microsoft.CodeAnalysis.Workspaces.csproj','src/Workspaces/CSharp/Portable/Microsoft.CodeAnalysis.CSharp.Workspaces.csproj']
write(O/'INTENT.json',{'utc':utc(),'kind':'REPOSITORY_DERIVED_WORKSPACE_INPUT_MATERIALIZATION','source_revision':'6c4a46a31302167b425d5e0a31ea83c9a9aa1d09','projects':projects,'selection_before_any_workspace_execution':'Use all unique existing .cs Compile items inside source tree, excluding artifacts-generated paths. Record every excluded/missing/external item and reason. Select target with greatest cross-project multiplicity, then largest file bytes, then lexical path. Select a different file appearing in exactly one project by greatest bytes then lexical path as background. Retain all evaluated project references; only references within these four projects are represented in the authored Workspace. This is a source-item projection, not a compiled or editor-loaded solution.','target_and_background_outcomes_not_observed':True,'no_build_targets':True})
env=os.environ.copy();env.update({'DOTNET_ROOT':str(C/'dotnet'),'DOTNET_CLI_HOME':str(C/'dotnet_cli_state'),'DOTNET_CLI_TELEMETRY_OPTOUT':'1','DOTNET_NOLOGO':'1','NUGET_PACKAGES':str(C/'nuget_packages')})
material=[];exclusions=[];occurrences=defaultdict(list);all_files={};receipts=[]
for index,project in enumerate(projects):
 out=O/f'project{index}';out.mkdir();argv=[str(C/'dotnet/dotnet'),'msbuild',project,'-nologo','-getItem:Compile,ProjectReference','-getProperty:AssemblyName,TargetFramework','-p:TargetFramework=net8.0','-p:NetRoslynSourceBuild=net8.0','-p:EnableSourceControlManagerQueries=false','-p:EnableSourceLink=false','-p:SourceRevisionId=6c4a46a31302167b425d5e0a31ea83c9a9aa1d09'];start=time.monotonic()
 write(out/'INTENT.json',{'utc':utc(),'argv':argv,'cwd':str(R),'timeout_seconds':90})
 try:run=subprocess.run(argv,cwd=R,env=env,capture_output=True,timeout=90);rc=run.returncode;stdout=run.stdout;stderr=run.stderr;status='SUCCESS' if rc==0 else 'FAILURE'
 except subprocess.TimeoutExpired as e:rc=None;stdout=e.stdout or b'';stderr=e.stderr or b'';status='TIMEOUT'
 (out/'stdout.json').write_bytes(stdout);(out/'stderr.txt').write_bytes(stderr);receipt={'utc':utc(),'status':status,'returncode':rc,'seconds':time.monotonic()-start,'stdout_sha256':sha(out/'stdout.json'),'stderr_sha256':sha(out/'stderr.txt')};write(out/'RESULT.json',receipt);receipts.append(receipt)
 if status!='SUCCESS':continue
 data=json.loads(stdout);kept=[];seen=set()
 for item in data['Items']['Compile']:
  p=Path(item['FullPath']);reason=None
  try:relative=p.relative_to(R).as_posix()
  except ValueError:relative=str(p);reason='external_to_source_root'
  if reason is None and ('artifacts' in p.relative_to(R).parts):reason='generated_artifact_source'
  if reason is None and p.suffix.lower()!='.cs':reason='not_csharp'
  if reason is None and not p.is_file():reason='missing_evaluated_item'
  if reason is None and relative in seen:reason='duplicate_item_in_project'
  if reason is not None:exclusions.append({'project':index,'path':relative,'reason':reason});continue
  seen.add(relative);kept.append(relative);occurrences[relative].append(index)
  if relative not in all_files:all_files[relative]={'sha256':sha(p),'bytes':p.stat().st_size}
 refs=[]
 for item in data['Items']['ProjectReference']:
  p=Path(item['FullPath']);rel=p.relative_to(R).as_posix() if p.is_relative_to(R) else str(p)
  refs.append({'path':rel,'in_selected_projects':rel in projects,'reference_output_assembly':item.get('ReferenceOutputAssembly','')})
 material.append({'index':index,'project':project,'assembly_name':data['Properties']['AssemblyName'],'target_framework':data['Properties']['TargetFramework'],'documents':sorted(kept),'project_references':refs})
if len(material)!=4:
 write(O/'MATERIALIZATION_RESULT.json',{'utc':utc(),'status':'FAILURE','project_results':receipts});raise SystemExit('project evaluation incomplete')
ordered=sorted(all_files,key=lambda p:(-len(occurrences[p]),-all_files[p]['bytes'],p));target=next(p for p in ordered if len(occurrences[p])>1)
background=next(p for p in sorted(all_files,key=lambda p:(-all_files[p]['bytes'],p)) if len(occurrences[p])==1 and p!=target)
manifest={'source_revision':'6c4a46a31302167b425d5e0a31ea83c9a9aa1d09','source_root_at_materialization':str(R),'projects':material,'files':all_files,'target':target,'target_projects':occurrences[target],'background':background,'background_project':occurrences[background][0],'unique_files':len(all_files),'document_occurrences':sum(len(x['documents']) for x in material),'excluded_items':exclusions,'input_scope':'Four-project evaluated existing non-generated C# source-item projection. Includes current author Workspace.cs patch as a document; this file is excluded from target/background candidates if implementation changes before freeze.'}
# Do not let the retry implementation itself become the manipulated input text.
forbidden='src/Workspaces/Core/Portable/Workspace/Workspace.cs'
if target==forbidden or background==forbidden:raise RuntimeError('selection would modify the research implementation text')
write(O/'MANIFEST.json',manifest);write(O/'MATERIALIZATION_RESULT.json',{'utc':utc(),'status':'SUCCESS','projects':4,'unique_files':len(all_files),'document_occurrences':manifest['document_occurrences'],'target':target,'target_multiplicity':len(occurrences[target]),'target_bytes':all_files[target]['bytes'],'background':background,'background_bytes':all_files[background]['bytes'],'exclusion_reasons':dict(Counter(x['reason'] for x in exclusions)),'manifest_sha256':sha(O/'MANIFEST.json')});print(json.dumps(json.loads((O/'MATERIALIZATION_RESULT.json').read_text()),indent=2))
