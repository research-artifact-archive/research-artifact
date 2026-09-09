using System.Collections.Concurrent;
using System.Diagnostics;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;
using System.Security.Cryptography;
using System.Text.Json;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.Host.Mef;
using Microsoft.CodeAnalysis.Text;

sealed class StudyWorkspace : Workspace
{
    public readonly ConcurrentQueue<Document> Notifications = new();
    public readonly ConcurrentQueue<WorkspaceChangeEventArgs> Changes = new();
    public StudyWorkspace() : base(MefHostServices.DefaultHost, "BoundedDocumentRetryStudy")
    {
        _ = RegisterWorkspaceChangedHandler(e => { if(e.Kind==WorkspaceChangeKind.DocumentChanged) Changes.Enqueue(e); });
    }
    public override bool CanApplyChange(ApplyChangesKind kind) => true;
    public void Initialize(SolutionInfo info) => OnSolutionAdded(info);
    public void Change(DocumentId id,SourceText text) => OnDocumentTextChanged(id,text,PreservationMode.PreserveIdentity);
    public void Remove(DocumentId id) => OnDocumentRemoved(id);
    protected override void OnDocumentTextChanged(Document doc) => Notifications.Enqueue(doc);
}

record Unit(string Id,string Phase,int Fork,int Rep,int Projects,int R,int B,string Mode,string Scenario);
record Trace(string Kind,int Job,int Snapshot,long Ns,int Writes);
record Capture(int Job,int Snapshot,int Writes,Solution Solution);

static class Program
{
    static readonly BindingFlags Flags=BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic;
    static string[] TargetTexts=Array.Empty<string>();
    static string BackgroundBase="";
    static string BackgroundText(int i)=>i==0?BackgroundBase:BackgroundBase+$"\n// retry-study background revision {i}\n";
    static JsonElement Manifest;
    static string ManifestSha="";
    static readonly Dictionary<string,SourceText> SourceTexts=new();
    static void LoadRepository(string manifestPath,string sourceRoot)
    {
        var bytes=File.ReadAllBytes(manifestPath);ManifestSha=Convert.ToHexStringLower(SHA256.HashData(bytes));
        Manifest=JsonDocument.Parse(bytes).RootElement.Clone();
        foreach(var file in Manifest.GetProperty("files").EnumerateObject())
        {
            string path=Path.Combine(sourceRoot,file.Name);byte[] content=File.ReadAllBytes(path);
            if(content.Length!=file.Value.GetProperty("bytes").GetInt64()||Convert.ToHexStringLower(SHA256.HashData(content))!=file.Value.GetProperty("sha256").GetString())throw new Exception("source hash: "+file.Name);
            SourceTexts.Add(file.Name,SourceText.From(File.ReadAllText(path,Encoding.UTF8),Encoding.UTF8));
        }
        string original=SourceTexts[Manifest.GetProperty("target").GetString()!].ToString();
        TargetTexts=Enumerable.Range(0,5).Select(i=>i==0?original:original+$"\n// retry-study target revision {i}\n").ToArray();
        BackgroundBase=SourceTexts[Manifest.GetProperty("background").GetString()!].ToString();
    }
    static long Ns(long ticks)=>(long)(ticks*(1_000_000_000.0/Stopwatch.Frequency));
    static Guid GuidFor(int i)=>new(i,0,0,new byte[]{0,0,0,0,0,0,0,1});
    static VersionStamp Version(int i)=>VersionStamp.Create(new DateTime(2026,9,9,0,0,0,DateTimeKind.Utc).AddSeconds(i));
    static DocumentInfo Info(DocumentId id,string name,string path,SourceText text)
        =>DocumentInfo.Create(id,name,loader:TextLoader.From(TextAndVersion.Create(text,Version(0),path)),filePath:path);
    static int TextVersion(Document? doc,bool background=false)
    {
        if(doc is null)return -1;
        string text=doc.GetTextAsync().GetAwaiter().GetResult().ToString();
        if(!background){int i=Array.IndexOf(TargetTexts,text);if(i<0)throw new Exception("unexpected target text");return i;}
        for(int i=0;i<32;i++)if(text==BackgroundText(i))return i;
        throw new Exception("unexpected background text");
    }
    static object? Field(object state,string name)=>state.GetType().GetField(name,Flags)!.GetValue(state);
    static void Set(object state,string name,object value)=>state.GetType().GetField(name,Flags)!.SetValue(state,value);
    static Dictionary<string,object?> Run(Unit u)
    {
        long wholeStart=Stopwatch.GetTimestamp();
        var result=new Dictionary<string,object?>{{"id",u.Id},{"phase",u.Phase},{"fork",u.Fork},{"rep",u.Rep},{"projects",u.Projects},{"r",u.R},{"B",u.B},{"mode",u.Mode},{"scenario",u.Scenario}};
        string status="SUCCESS",error="",exception="";int writes=0,job=0,opportunities=0;long foregroundStart=0,foregroundTicks=0,writerTicks=0,setupTicks=0;
        StudyWorkspace? ws=null;BlockingCollection<Action>? work=null;Thread? writer=null;object? state=null;
        var trace=new List<Trace>();var captures=new List<Capture>();var snapshotIds=new Dictionary<Solution,int>(ReferenceEqualityComparer.Instance);
        var targetIds=new List<DocumentId>();DocumentId? backgroundId=null;var writerEvents=new List<Dictionary<string,object?>>();
        int Identity(Solution s){if(!snapshotIds.TryGetValue(s,out int id)){id=snapshotIds.Count;snapshotIds.Add(s,id);}return id;}
        try
        {
            ws=new StudyWorkspace();var infos=new List<ProjectInfo>();
            var originals=new Dictionary<DocumentId,SourceText>();
            var projectRows=Manifest.GetProperty("projects").EnumerateArray().ToArray();
            if(u.Projects!=projectRows.Length)throw new Exception("project input mismatch");
            var projectIds=projectRows.ToDictionary(p=>p.GetProperty("project").GetString()!,p=>ProjectId.CreateFromSerialized(GuidFor(1000+p.GetProperty("index").GetInt32())));
            string targetPath=Manifest.GetProperty("target").GetString()!,backgroundPath=Manifest.GetProperty("background").GetString()!;int ordinal=0;
            foreach(var p in projectRows)
            {
                string projectPath=p.GetProperty("project").GetString()!,assembly=p.GetProperty("assembly_name").GetString()!;var pid=projectIds[projectPath];var docs=new List<DocumentInfo>();
                foreach(var entry in p.GetProperty("documents").EnumerateArray())
                {
                    string path=entry.GetString()!;var id=DocumentId.CreateFromSerialized(pid,GuidFor(100000+ordinal++));
                    var text=SourceTexts[path];originals.Add(id,text);docs.Add(Info(id,Path.GetFileName(path),"/repository/"+path,text));
                    if(path==targetPath)targetIds.Add(id);if(path==backgroundPath)backgroundId=id;
                }
                var refs=p.GetProperty("project_references").EnumerateArray().Where(r=>r.GetProperty("in_selected_projects").GetBoolean()&&r.GetProperty("reference_output_assembly").GetString()!="false").Select(r=>new ProjectReference(projectIds[r.GetProperty("path").GetString()!])).ToArray();
                infos.Add(ProjectInfo.Create(pid,Version(0),assembly,assembly,LanguageNames.CSharp,documents:docs,projectReferences:refs,parseOptions:new CSharpParseOptions(LanguageVersion.Preview)));
            }
            if(ordinal!=Manifest.GetProperty("document_occurrences").GetInt32()||targetIds.Count!=2||backgroundId is null)throw new Exception("source membership mismatch");
            result["source_manifest_sha256"]=ManifestSha;result["source_documents"]=ordinal;result["linked_documents"]=targetIds.Count;
            ws.Initialize(SolutionInfo.Create(SolutionId.CreateFromSerialized(GuidFor(1)),Version(0),projects:infos));
            if(u.Scenario=="missing_required")ws.Remove(targetIds[0]);
            // All 4,019 original texts are verified/loaded in setup, identically by mode.
            foreach(var entry in originals)
                if(ws.CurrentSolution.GetDocument(entry.Key) is {} doc&&!ReferenceEquals(doc.GetTextAsync().GetAwaiter().GetResult(),entry.Value))throw new Exception("initial source identity");
            work=new BlockingCollection<Action>();writer=new Thread(()=>{foreach(var action in work.GetConsumingEnumerable())action();}){IsBackground=true,Name="Roslyn-independent-document-writer"};writer.Start();
            void Inject(bool remove)
            {
                long started=Stopwatch.GetTimestamp();var done=new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);int next=writes+1;
                work.Add(()=>{try{if(remove)ws.Remove(targetIds[0]);else ws.Change(backgroundId!,SourceText.From(BackgroundText(next),Encoding.UTF8));done.SetResult();}catch(Exception e){done.SetException(e);}});
                if(!done.Task.Wait(TimeSpan.FromSeconds(3)))throw new TimeoutException("writer join");done.Task.GetAwaiter().GetResult();
                writerTicks+=Stopwatch.GetTimestamp()-started;writes++;
                writerEvents.Add(new(){{"kind",remove?"remove_target":"change_background"},{"write",writes},{"job",job},{"opportunity",opportunities},{"after_snapshot",Identity(ws.CurrentSolution)},{"ns",Ns(Stopwatch.GetTimestamp()-foregroundStart)}});
            }
            if(u.Mode!="baseline")
            {
                Type stateType=typeof(Workspace).GetNestedType("DocumentRetryStudyState",BindingFlags.NonPublic)!;
                state=Activator.CreateInstance(stateType,true)!;Set(state,"OwnerThreadId",Environment.CurrentManagedThreadId);Set(state,"Mode",u.Mode switch{"original"=>-1,"two"=>0,"three"=>1,_=>throw new ArgumentException("mode")});Set(state,"Remaining",u.R);
                Action<string,Solution> hook=(kind,snapshot)=>
                {
                    trace.Add(new(kind,job,Identity(snapshot),Ns(Stopwatch.GetTimestamp()-foregroundStart),writes));
                    if(kind=="before_lock")
                    {
                        opportunities++;
                        if(u.Scenario=="removed_between"&&writes==0)Inject(true);
                        else if(u.Scenario=="normal"&&writes<u.B)Inject(false);
                    }
                    if(kind=="return_changed"||kind=="return_noop")captures.Add(new(job,Identity(snapshot),writes,snapshot));
                };
                Set(state,"Hook",hook);typeof(Workspace).GetField("DocumentRetryStudy",Flags)!.SetValue(ws,state);
            }
            setupTicks=Stopwatch.GetTimestamp()-wholeStart;foregroundStart=Stopwatch.GetTimestamp();
            try
            {
                int jobs=u.Scenario=="normal"?4:1;
                for(job=1;job<=jobs;job++)
                {
                    SourceText requested=u.Scenario=="noop"?ws.CurrentSolution.GetDocument(targetIds[0])!.GetTextAsync().GetAwaiter().GetResult():SourceText.From(TargetTexts[u.Scenario=="equal_identity"?0:job],Encoding.UTF8);
                    ws.Change(targetIds[0],requested);
                    if(u.Mode=="baseline")captures.Add(new(job,Identity(ws.CurrentSolution),writes,ws.CurrentSolution));
                }
            }
            catch(ArgumentException e){exception=e.GetType().Name;if(u.Scenario!="missing_required"&&u.Scenario!="removed_between")throw;}
            finally{foregroundTicks=Stopwatch.GetTimestamp()-foregroundStart;}
            if((u.Scenario=="missing_required"||u.Scenario=="removed_between")&&exception!="ArgumentException")throw new Exception("expected missing-document exception");
            int expectedChanges=u.Scenario switch{"normal"=>4*targetIds.Count+writes,"equal_identity"=>targetIds.Count,_=>0};
            if(!SpinWait.SpinUntil(()=>ws.Changes.Count>=expectedChanges,TimeSpan.FromSeconds(3)))throw new TimeoutException("workspace events");
            var notified=ws.Notifications.ToArray();var changed=ws.Changes.ToArray();
            if(notified.Length!=expectedChanges||changed.Length!=expectedChanges)throw new Exception($"notification count {notified.Length}/{changed.Length}/{expectedChanges}");
            if(!notified.Select(d=>d.Id).SequenceEqual(changed.Select(e=>e.DocumentId)))throw new Exception("notification order");
            var targetSet=targetIds.ToHashSet();var notificationRows=new List<Dictionary<string,object?>>();
            foreach(var doc in notified)notificationRows.Add(new(){{"document",doc.Id==backgroundId?-1:targetIds.IndexOf(doc.Id)},{"version",TextVersion(doc,doc.Id==backgroundId)}});
            var capturedRows=captures.Select(c=>new Dictionary<string,object?>{{"job",c.Job},{"snapshot",c.Snapshot},{"writes_at_return",c.Writes},{"target_versions",targetIds.Select(id=>TextVersion(c.Solution.GetDocument(id))).ToArray()},{"background_version",TextVersion(c.Solution.GetDocument(backgroundId!),true)}}).ToArray();
            int[] finalTargets=targetIds.Select(id=>TextVersion(ws.CurrentSolution.GetDocument(id))).ToArray();int finalBackground=TextVersion(ws.CurrentSolution.GetDocument(backgroundId!),true);
            int finalExpected=u.Scenario=="normal"?4:0;
            for(int i=0;i<finalTargets.Length;i++)if(finalTargets[i]!=(i==0&&(u.Scenario=="missing_required"||u.Scenario=="removed_between")?-1:finalExpected))throw new Exception("final target content");
            if(finalBackground!=(u.Scenario=="normal"?writes:0))throw new Exception("final background content");
            foreach(var c in capturedRows)
            {
                int wanted=u.Scenario=="normal"?(int)c["job"]!:0;
                if(((int[])c["target_versions"]!).Any(x=>x!=wanted))throw new Exception("captured linked contents changed");
                if((int)c["background_version"]! != (int)c["writes_at_return"]!)throw new Exception("captured background changed");
            }
            if(u.Scenario=="normal"&&writes!=u.B)throw new Exception("unrealized planned writer quota");
            var counters=new Dictionary<string,long>();if(state is not null)foreach(string name in new[]{"Calls","PreparedOutside","PreparedInside","Mismatches","CheapFailures"})counters[name]=(long)Field(state,name)!;
            if(u.Scenario=="normal"&&state is not null)
            {
                long f=Math.Min(u.B,u.R);long calls=u.Mode=="original"?4+u.B:4+f;
                long inside=u.Mode switch{"original"=>0,"two"=>u.B>=u.R?4:0,"three"=>Math.Min(Math.Max(u.B-u.R,0),4),_=>throw new Exception("mode")};
                long outside=u.Mode=="original"?4+u.B:u.Mode=="two"&&u.B>=u.R?f:4+f;
                if(counters["Calls"]!=calls||counters["PreparedInside"]!=inside||counters["PreparedOutside"]!=outside||counters["CheapFailures"]!=(u.Mode=="original"?u.B:f))throw new Exception("source resource equation");
            }
            int preserved=0;
            foreach(var entry in originals)
            {
                if(targetSet.Contains(entry.Key)||entry.Key==backgroundId)continue;
                if(!ReferenceEquals(ws.CurrentSolution.GetDocument(entry.Key)!.GetTextAsync().GetAwaiter().GetResult(),entry.Value))throw new Exception("unrelated source text changed");preserved++;
            }
            result["unchanged_source_documents"]=preserved;
            result["counters"]=counters;result["remaining"]=state is null?null:Field(state,"Remaining");result["final_target_versions"]=finalTargets;result["final_background_version"]=finalBackground;result["captures"]=capturedRows;result["notifications"]=notificationRows;result["workspace_event_document_sequence"]=changed.Select(e=>e.DocumentId==backgroundId?-1:targetIds.IndexOf(e.DocumentId!)).ToArray();
        }
        catch(TimeoutException e){status="TIMEOUT";error=e.ToString();}
        catch(ArgumentException e){status="INVALID";error=e.ToString();}
        catch(Exception e){status="FAILURE";error=e.ToString();}
        finally
        {
            if(work is not null)work.CompleteAdding();
            if(writer is not null&&!writer.Join(TimeSpan.FromSeconds(3))){status="TIMEOUT";error+=" writer did not stop";}
            work?.Dispose();ws?.Dispose();
        }
        result["status"]=status;result["error"]=error;result["observed_exception"]=exception;result["actual_writes"]=writes;result["prelock_opportunities"]=opportunities;result["writer_events"]=writerEvents;result["trace"]=trace;result["foreground_ns"]=Ns(foregroundTicks);result["writer_join_ns"]=Ns(writerTicks);result["setup_ns"]=Ns(setupTicks);result["whole_unit_ns"]=Ns(Stopwatch.GetTimestamp()-wholeStart);
        result["gc_collections"]=new[]{GC.CollectionCount(0),GC.CollectionCount(1),GC.CollectionCount(2)};
        return result;
    }
    static void Main(string[] args)
    {
        // Ensure the actual built C# workspace services are discoverable by the standard MEF host.
        _=typeof(CSharpCompilation);_=Assembly.Load("Microsoft.CodeAnalysis.CSharp.Workspaces");
        Console.Error.WriteLine(JsonSerializer.Serialize(new{runtime=RuntimeInformation.FrameworkDescription,architecture=RuntimeInformation.ProcessArchitecture.ToString(),stopwatch_frequency=Stopwatch.Frequency,workspace_assembly=typeof(Workspace).Assembly.Location,workspace_version=typeof(Workspace).Assembly.GetName().Version?.ToString(),server_gc=System.Runtime.GCSettings.IsServerGC}));
        LoadRepository(args[1],args[2]);
        int sequence=0;long start=Stopwatch.GetTimestamp();
        foreach(string line in File.ReadLines(args[0]))
        {
            var x=line.Split('\t');var u=new Unit(x[0],x[1],int.Parse(x[2]),int.Parse(x[3]),int.Parse(x[4]),int.Parse(x[5]),int.Parse(x[6]),x[7],x[8]);var result=Run(u);result["sequence"]=sequence++;result["process_elapsed_ns"]=Ns(Stopwatch.GetTimestamp()-start);Console.WriteLine(JsonSerializer.Serialize(result));Console.Out.Flush();
        }
    }
}
