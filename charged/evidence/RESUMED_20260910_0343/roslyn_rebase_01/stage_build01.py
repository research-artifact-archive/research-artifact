from pathlib import Path
import datetime,difflib,hashlib,json,os,signal,subprocess,time
D=Path(__file__).resolve().parent;S=Path('<AUTHOR_HOME>/Research/roslyn_semantics_20260910');C=Path('<AUTHOR_HOME>/Research/roslyn_build_20260909');old=S/'patch04_source';R=S/'rebase01_source';assert not R.exists()
subprocess.run(['/bin/cp','-cR',str(old),str(R)],check=True,timeout=120)
P=R/'src/Workspaces/Core/Portable/Workspace/Workspace.cs';before=P.read_bytes();s=before.decode('utf-8-sig')
def replace(a,b,count=1):
 global s
 assert s.count(a)==count,(s.count(a),a[:100]);s=s.replace(a,b)
replace('public long Calls, PreparedOutside, PreparedInside, Mismatches, CheapFailures;', 'public long Calls, PreparedOutside, PreparedInside, Mismatches, CheapFailures, Rebases;\n        public bool AllowPreparedRebase;')
replace('Func<Solution, TData, bool>? mayTransformProtected = null)', 'Func<Solution, TData, bool>? mayTransformProtected = null,\n        Func<Solution, Solution, Solution, TData, Solution?>? tryPreparedRebase = null)',2)
replace('            isNoOp,\n            mayTransformProtected);', '            isNoOp,\n            mayTransformProtected,\n            tryPreparedRebase);')
replace('''                    else if (_latestSolution != oldSolution)
                    {
                        oldSolution = _latestSolution;
                        if (retryStudy is not null) retryStudy.Mismatches++;
                        if (retryStudy is { Mode: 1, Remaining: 0 })''','''                    else if (_latestSolution != oldSolution)
                    {
                        var preparedFrom = oldSolution;
                        oldSolution = _latestSolution;
                        if (retryStudy is not null) retryStudy.Mismatches++;
                        var rebased = retryStudy is { AllowPreparedRebase: true }
                            ? tryPreparedRebase?.Invoke(preparedFrom, newSolution, oldSolution, data)
                            : null;
                        if (rebased is not null)
                        {
                            retryStudy!.Rebases++;
                            retryStudy.Step("rebase_completed", rebased);
                            newSolution = rebased;
                        }
                        else if (retryStudy is { Mode: 1, Remaining: 0 })''')
replace('''            mayTransformProtected: static (solution, data) => data.getDocumentInSolution(solution, data.documentId) is not null);''','''            mayTransformProtected: static (solution, data) => data.getDocumentInSolution(solution, data.documentId) is not null,
            tryPreparedRebase: static (preparedFrom, prepared, latest, data) =>
            {
                // Stronger comparator outside the whole-kernel interface. Identity guards
                // conservatively reject changes to any affected project or link relation.
                if (!data.isCodeDocument || data.updatedDocumentIds.Count == 0 ||
                    preparedFrom.Id != latest.Id || latest.GetDocument(data.documentId) is null)
                    return null;
                var oldRelated = preparedFrom.GetRelatedDocumentIds(data.documentId, includeDifferentLanguages: true);
                var latestRelated = latest.GetRelatedDocumentIds(data.documentId, includeDifferentLanguages: true);
                if (!oldRelated.SequenceEqual(latestRelated))
                    return null;
                foreach (var id in oldRelated.Append(data.documentId))
                {
                    if (!ReferenceEquals(preparedFrom.GetProjectState(id.ProjectId), latest.GetProjectState(id.ProjectId)))
                        return null;
                }
                var merged = latest;
                foreach (var id in data.updatedDocumentIds)
                    merged = merged.WithDocumentContentsFrom(id, prepared.GetRequiredDocument(id).DocumentState);
                return merged;
            });''')
after=b'\xef\xbb\xbf'+s.encode();P.write_bytes(after);out=D/'patch01';out.mkdir();(out/'Workspace.patched.cs').write_bytes(after)
upstream=(D.parent.parent/'RESUMED_20260909_1413/roslyn_source_01/patch01/Workspace.original.cs').read_text(encoding='utf-8-sig')
(out/'Workspace.patch').write_text(''.join(difflib.unified_diff(upstream.splitlines(True),s.splitlines(True),fromfile='a/src/Workspaces/Core/Portable/Workspace/Workspace.cs',tofile='b/src/Workspaces/Core/Portable/Workspace/Workspace.cs')))
(out/'successor.patch').write_text(''.join(difflib.unified_diff(before.decode('utf-8-sig').splitlines(True),s.splitlines(True),fromfile='patch04',tofile='rebase01')))
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
write(out/'RECEIPT.json',{'utc':utc(),'before_sha256':hashlib.sha256(before).hexdigest(),'after_sha256':sha(P),'plan_sha256':sha(D/'PLAN.md'),'source_clone':str(R),'scope':'Conservative opt-in prepared-content merge, additional protected work counted separately'})
O=D/'build01';O.mkdir();sdk=C/'dotnet';env=os.environ.copy();env.update({'DOTNET_ROOT':str(sdk),'DOTNET_CLI_HOME':str(C/'dotnet_cli_state'),'DOTNET_CLI_TELEMETRY_OPTOUT':'1','DOTNET_NOLOGO':'1','DOTNET_GENERATE_ASPNET_CERTIFICATE':'false','DOTNET_SKIP_FIRST_TIME_EXPERIENCE':'1','NUGET_PACKAGES':str(C/'nuget_packages'),'PATH':str(sdk)+os.pathsep+env.get('PATH','')})
argv=[str(sdk/'dotnet'),'build','src/Workspaces/CSharp/Portable/Microsoft.CodeAnalysis.CSharp.Workspaces.csproj','-c','Release','-f','net8.0','--disable-build-servers','--nologo','-v:minimal','-p:RunAnalyzersDuringBuild=false','-p:EnableSourceControlManagerQueries=false','-p:EnableSourceLink=false','-p:SourceRevisionId=6c4a46a31302167b425d5e0a31ea83c9a9aa1d09']
write(O/'INTENT.json',{'utc':utc(),'argv':argv,'cwd':str(R),'timeout_seconds':600,'workspace_sha256':sha(P),'plan_sha256':sha(D/'PLAN.md')});t=time.monotonic()
with (O/'stdout.txt').open('x') as outf,(O/'stderr.txt').open('x') as err:
 proc=subprocess.Popen(argv,cwd=R,env=env,stdout=outf,stderr=err,start_new_session=True);write(O/'PROCESS.json',{'pid':proc.pid,'pgid':proc.pid})
 try:rc=proc.wait(timeout=600);status='SUCCESS' if rc==0 else 'FAILURE'
 except subprocess.TimeoutExpired:
  os.killpg(proc.pid,signal.SIGTERM)
  try:rc=proc.wait(timeout=5)
  except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);rc=proc.wait()
  status='TIMEOUT'
result={'utc':utc(),'status':status,'returncode':rc,'seconds':time.monotonic()-t};write(O/'RESULT.json',result);print(json.dumps(result));print((O/'stdout.txt').read_text()[-5000:]);print((O/'stderr.txt').read_text()[-1500:])
