using System.Collections.Concurrent;
using System.Diagnostics;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;
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
        WorkspaceChanged += (_,e) => { if(e.Kind==WorkspaceChangeKind.DocumentChanged) Changes.Enqueue(e); };
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
    static readonly string[] TargetTexts=Enumerable.Range(0,5).Select(i=>$"class Target {{ public int Version => {i}; }}\n").ToArray();
    static string BackgroundText(int i)=>$"class Other {{ public int Version => {i}; }}\n";
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
            ws=new StudyWorkspace();var infos=new List<ProjectInfo>();SourceText initial=SourceText.From(TargetTexts[0],Encoding.UTF8);
            for(int i=0;i<u.Projects;i++)
            {
                var pid=ProjectId.CreateFromSerialized(GuidFor(1000+i),$"P{i}");var tid=DocumentId.CreateFromSerialized(pid,GuidFor(100000+i),$"T{i}");targetIds.Add(tid);
                var docs=new List<DocumentInfo>{Info(tid,"Target.cs","/authored/shared/Target.cs",initial)};
                if(i==0){backgroundId=DocumentId.CreateFromSerialized(pid,GuidFor(999999),"background");docs.Add(Info(backgroundId,"Other.cs","/authored/independent/Other.cs",SourceText.From(BackgroundText(0),Encoding.UTF8)));}
                infos.Add(ProjectInfo.Create(pid,Version(0),$"Project{i}",$"Assembly{i}",LanguageNames.CSharp,documents:docs,parseOptions:new CSharpParseOptions(LanguageVersion.CSharp12)));
            }
            ws.Initialize(SolutionInfo.Create(SolutionId.CreateFromSerialized(GuidFor(1)),Version(0),projects:infos));
            if(u.Scenario=="missing_required")ws.Remove(targetIds[0]);
            // Force initial SourceText loading before all measured foreground work, identically by mode.
            foreach(var id in targetIds)if(ws.CurrentSolution.GetDocument(id) is {} doc)_=doc.GetTextAsync().GetAwaiter().GetResult();
            _=ws.CurrentSolution.GetDocument(backgroundId!)!.GetTextAsync().GetAwaiter().GetResult();
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
            int expectedChanges=u.Scenario switch{"normal"=>4*u.Projects+writes,"equal_identity"=>u.Projects,_=>0};
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
                if((int)c["background_version"]!=(int)c["writes_at_return"])throw new Exception("captured background changed");
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
        int sequence=0;long start=Stopwatch.GetTimestamp();
        foreach(string line in File.ReadLines(args[0]))
        {
            var x=line.Split('\t');var u=new Unit(x[0],x[1],int.Parse(x[2]),int.Parse(x[3]),int.Parse(x[4]),int.Parse(x[5]),int.Parse(x[6]),x[7],x[8]);var result=Run(u);result["sequence"]=sequence++;result["process_elapsed_ns"]=Ns(Stopwatch.GetTimestamp()-start);Console.WriteLine(JsonSerializer.Serialize(result));Console.Out.Flush();
        }
    }
}
