from pathlib import Path
import datetime,difflib,hashlib,json,os,signal,subprocess,time
D=Path(__file__).resolve().parent
C=Path('<AUTHOR_HOME>/Research/roslyn_build_20260909')
S=Path('<AUTHOR_HOME>/Research/roslyn_semantics_20260910')
old=C/'source/roslyn-6c4a46a31302167b425d5e0a31ea83c9a9aa1d09'
R=S/'patch04_source';assert not R.exists()
subprocess.run(['/bin/cp','-cR',str(old),str(R)],check=True,timeout=120)
P=R/'src/Workspaces/Core/Portable/Workspace/Workspace.cs'
before=P.read_bytes();assert hashlib.sha256(before).hexdigest()=='a09d193ece3b93d93784b64d99f4874808690b5e7641799bb31cbd635abd6ecb'
s=before.decode('utf-8-sig')
def replace(a,b,count=1):
 global s
 assert s.count(a)==count,(s.count(a),a[:100])
 s=s.replace(a,b)
replace('Func<Solution, TData, bool>? isNoOp = null)', 'Func<Solution, TData, bool>? isNoOp = null,\n        Func<Solution, TData, bool>? mayTransformProtected = null)',2)
replace('            retryStudy,\n            isNoOp);','            retryStudy,\n            isNoOp,\n            mayTransformProtected);')
replace('''            while (true)
            {
                var freshProtected = retryStudy is { Mode: 0, Remaining: 0 };''','''            var forceOutside = false;
            while (true)
            {
                var freshProtected = !forceOutside && retryStudy is { Mode: 0, Remaining: 0 };
                forceOutside = false;''')
replace('''                        oldSolution = _latestSolution;
                        newSolution = Transform(oldSolution, inside: true);''','''                        oldSolution = _latestSolution;
                        // Missing-document error naming may invoke a virtual host method.
                        // Release protection, then run the original transformation on this
                        // same captured snapshot, preserving its exception/catch behavior.
                        if (mayTransformProtected?.Invoke(oldSolution, data) == false)
                        {
                            forceOutside = true;
                            retryStudy?.Step("defer_error_outside", oldSolution);
                            continue;
                        }
                        newSolution = Transform(oldSolution, inside: true);''')
replace('''                        if (retryStudy is { Mode: 1, Remaining: 0 })
                        {
                            newSolution = Transform(oldSolution, inside: true);''','''                        if (retryStudy is { Mode: 1, Remaining: 0 })
                        {
                            if (mayTransformProtected?.Invoke(oldSolution, data) == false)
                            {
                                forceOutside = true;
                                retryStudy.Step("defer_error_outside", oldSolution);
                                continue;
                            }
                            newSolution = Transform(oldSolution, inside: true);''')
replace('''            isNoOp: static (solution, data) => data.isNoOp?.Invoke(solution, data.documentId, data.arg) == true);''','''            isNoOp: static (solution, data) => data.isNoOp?.Invoke(solution, data.documentId, data.arg) == true,
            mayTransformProtected: static (solution, data) => data.getDocumentInSolution(solution, data.documentId) is not null);''')
after=b'\xef\xbb\xbf'+s.encode();P.write_bytes(after)
patch=D/'patch04';patch.mkdir();(patch/'Workspace.patched.cs').write_bytes(after)
upstream=(D.parent.parent/'RESUMED_20260909_1413/roslyn_source_01/patch01/Workspace.original.cs').read_text(encoding='utf-8-sig')
(patch/'Workspace.patch').write_text(''.join(difflib.unified_diff(upstream.splitlines(True),s.splitlines(True),fromfile='a/src/Workspaces/Core/Portable/Workspace/Workspace.cs',tofile='b/src/Workspaces/Core/Portable/Workspace/Workspace.cs')))
(patch/'successor.patch').write_text(''.join(difflib.unified_diff(before.decode('utf-8-sig').splitlines(True),s.splitlines(True),fromfile='patch03',tofile='patch04')))
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
write(patch/'RECEIPT.json',{'utc':utc(),'before_sha256':hashlib.sha256(before).hexdigest(),'after_sha256':sha(P),'parent_failure':'../roslyn_error_reentry_01/run01/SUMMARY.json','reason':'Defer missing-document virtual error naming outside the semaphore on the same snapshot; separate source clone; no general callback safety claim'})
O=D/'build01';O.mkdir();sdk=C/'dotnet';env=os.environ.copy();env.update({'DOTNET_ROOT':str(sdk),'DOTNET_CLI_HOME':str(C/'dotnet_cli_state'),'DOTNET_CLI_TELEMETRY_OPTOUT':'1','DOTNET_NOLOGO':'1','DOTNET_GENERATE_ASPNET_CERTIFICATE':'false','DOTNET_SKIP_FIRST_TIME_EXPERIENCE':'1','NUGET_PACKAGES':str(C/'nuget_packages'),'PATH':str(sdk)+os.pathsep+env.get('PATH','')})
argv=[str(sdk/'dotnet'),'build','src/Workspaces/CSharp/Portable/Microsoft.CodeAnalysis.CSharp.Workspaces.csproj','-c','Release','-f','net8.0','--disable-build-servers','--nologo','-v:minimal','-p:RunAnalyzersDuringBuild=false','-p:EnableSourceControlManagerQueries=false','-p:EnableSourceLink=false','-p:SourceRevisionId=6c4a46a31302167b425d5e0a31ea83c9a9aa1d09']
write(O/'INTENT.json',{'utc':utc(),'argv':argv,'cwd':str(R),'timeout_seconds':600,'workspace_sha256':sha(P),'plan_sha256':sha(D/'PLAN.md')})
t=time.monotonic()
with (O/'stdout.txt').open('x') as out,(O/'stderr.txt').open('x') as err:
 p=subprocess.Popen(argv,cwd=R,env=env,stdout=out,stderr=err,start_new_session=True);write(O/'PROCESS.json',{'pid':p.pid,'pgid':p.pid})
 try:rc=p.wait(timeout=600);status='SUCCESS' if rc==0 else 'FAILURE'
 except subprocess.TimeoutExpired:
  os.killpg(p.pid,signal.SIGTERM)
  try:rc=p.wait(timeout=5)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);rc=p.wait()
  status='TIMEOUT'
result={'utc':utc(),'status':status,'returncode':rc,'seconds':time.monotonic()-t};write(O/'RESULT.json',result);print(json.dumps(result));print((O/'stdout.txt').read_text()[-6000:]);print((O/'stderr.txt').read_text()[-2000:])
