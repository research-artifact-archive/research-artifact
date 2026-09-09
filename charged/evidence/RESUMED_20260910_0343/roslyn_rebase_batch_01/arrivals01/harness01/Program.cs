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

sealed class ArrivalWorkspace : Workspace
{
 public long Epoch;
 public readonly ConcurrentQueue<Document> Notifications=new();
 public readonly ConcurrentQueue<WorkspaceChangeEventArgs> Changes=new();
 public readonly ConcurrentQueue<(WorkspaceChangeEventArgs Args,Solution Current,long Tick)> Immediate=new();
 public ArrivalWorkspace():base(MefHostServices.DefaultHost,"IndependentArrivalRetryStudy"){}
 public void Initialize(SolutionInfo info)=>OnSolutionAdded(info);
 public void Change(DocumentId id,SourceText text)=>OnDocumentTextChanged(id,text,PreservationMode.PreserveIdentity);
 public void StartRecording(){_=RegisterWorkspaceChangedHandler(e=>Changes.Enqueue(e));_=RegisterWorkspaceChangedImmediateHandler(e=>Immediate.Enqueue((e,CurrentSolution,Stopwatch.GetTimestamp())));}
 protected override void OnDocumentTextChanged(Document doc)=>Notifications.Enqueue(doc);
}
record Unit(string Id,string Phase,int Fork,int Rep,int PeriodUs,string Mode,int R);
sealed class RequestTimes{public long Intended,Enqueued,Invoked,Returned;}
static class Program
{
    static readonly BindingFlags Flags=BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic;
    static string[] TargetTexts=Array.Empty<string>();
    static string BackgroundBase="";
    static string WriterTargetText(int i)=>TargetTexts[0]+$"\n// semantics-study interfering target revision {i}\n";
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
        TargetTexts=Enumerable.Range(0,33).Select(i=>i==0?original:original+$"\n// retry-study target revision {i}\n").ToArray();
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
        if(!background){int i=Array.IndexOf(TargetTexts,text);if(i>=0)return i;for(int j=1;j<32;j++)if(text==WriterTargetText(j))return -100-j;throw new Exception("unexpected target text");}
        for(int i=0;i<32;i++)if(text==BackgroundText(i))return i;
        throw new Exception("unexpected background text");
    }
    static object? Field(object state,string name)=>state.GetType().GetField(name,Flags)!.GetValue(state);
    static void Set(object state,string name,object value)=>state.GetType().GetField(name,Flags)!.SetValue(state,value);

 static SourceText[] ForegroundTexts=Array.Empty<SourceText>(),BackgroundTexts=Array.Empty<SourceText>();
 static readonly Dictionary<SourceText,int> FgVersions=new(ReferenceEqualityComparer.Instance),BgVersions=new(ReferenceEqualityComparer.Instance);
 static int Projection(Solution sol,DocumentId id,bool bg=false)
 {
  var text=sol.GetDocument(id)!.GetTextAsync().GetAwaiter().GetResult();
  if(!(bg?BgVersions:FgVersions).TryGetValue(text,out int v))throw new Exception("unrecognized source text identity");return v;
 }
 static string Meta(Document d)=>JsonSerializer.Serialize(new{d.Name,d.FilePath,d.Folders,d.SourceCodeKind});
 static void Until(long tick)
 {
  while(true){long left=tick-Stopwatch.GetTimestamp();if(left<=0)return;if(left>Stopwatch.Frequency/500)Thread.Sleep(1);else Thread.SpinWait(32);}
 }
 static Dictionary<string,object?> Run(Unit u)
 {
  var result=new Dictionary<string,object?>{{"timing_hook_enabled",true},{"id",u.Id},{"phase",u.Phase},{"fork",u.Fork},{"rep",u.Rep},{"period_us",u.PeriodUs},{"mode",u.Mode},{"r",u.R},{"jobs",32},{"requested_writes",64},{"hook_enabled",false}};
  long wholeStart=Stopwatch.GetTimestamp(),epoch=0,fgStart=0,fgEnd=0,setup=0;string status="SUCCESS",error="";
  ArrivalWorkspace? ws=null;BlockingCollection<int>? queue=null;Thread? producer=null,worker=null;object? state=null;
  using var ready=new CountdownEvent(2);using var start=new ManualResetEventSlim(false);
  var stop=new CancellationTokenSource();var errors=new ConcurrentQueue<Exception>();
  var requests=Enumerable.Range(0,64).Select(_=>new RequestTimes()).ToArray();
  var fgInvoked=new long[32];var fgReturned=new long[32];
  var observedPhases=new List<(string Name,long Tick)>();
  var targetIds=new List<DocumentId>();DocumentId? backgroundId=null;
  try
  {
            ws=new ArrivalWorkspace();var infos=new List<ProjectInfo>();
            var originals=new Dictionary<DocumentId,SourceText>();
            var projectRows=Manifest.GetProperty("projects").EnumerateArray().ToArray();
            if(4!=projectRows.Length)throw new Exception("project input mismatch");
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

   foreach(var entry in originals)if(!ReferenceEquals(ws.CurrentSolution.GetDocument(entry.Key)!.GetTextAsync().GetAwaiter().GetResult(),entry.Value))throw new Exception("initial identity");
   var initial=ws.CurrentSolution;
   var initialVersions=originals.Keys.ToDictionary(id=>id,id=>initial.GetDocument(id)!.GetTextVersionAsync().GetAwaiter().GetResult());
   var initialMeta=originals.Keys.ToDictionary(id=>id,id=>Meta(initial.GetDocument(id)!));
   ws.StartRecording();
   if(u.Mode!="baseline")
   {
    state=Activator.CreateInstance(typeof(Workspace).GetNestedType("DocumentRetryStudyState",BindingFlags.NonPublic)!,true)!;
    Set(state,"OwnerThreadId",Environment.CurrentManagedThreadId);Set(state,"Mode",u.Mode=="original"?-1:u.Mode=="two"?0:1);Set(state,"Remaining",u.R);Set(state,"AllowPreparedRebase",(u.Mode=="rebase"||u.Mode=="batch"));
    Set(state,"Hook",new Action<string,Solution>((name,snapshot)=>observedPhases.Add((name,Stopwatch.GetTimestamp()))));
    typeof(Workspace).GetField("DocumentRetryStudy",Flags)!.SetValue(ws,state);
   }
   queue=new BlockingCollection<int>();
   worker=new Thread(()=>{try{ready.Signal();start.Wait(stop.Token);foreach(int i in queue.GetConsumingEnumerable(stop.Token)){requests[i].Invoked=Stopwatch.GetTimestamp();ws.Change(backgroundId!,BackgroundTexts[i+1]);requests[i].Returned=Stopwatch.GetTimestamp();}}catch(Exception e){errors.Enqueue(e);}}){IsBackground=true,Name="IndependentArrivalWorker"};
   producer=new Thread(()=>{try{ready.Signal();start.Wait(stop.Token);for(int i=0;i<64;i++){long intended=epoch+(long)(i*u.PeriodUs*(Stopwatch.Frequency/1_000_000.0));requests[i].Intended=intended;Until(intended);stop.Token.ThrowIfCancellationRequested();requests[i].Enqueued=Stopwatch.GetTimestamp();queue.Add(i,stop.Token);}}catch(Exception e){errors.Enqueue(e);}finally{queue.CompleteAdding();}}){IsBackground=true,Name="IndependentArrivalProducer"};
   worker.Start();producer.Start();if(!ready.Wait(TimeSpan.FromSeconds(3)))throw new TimeoutException("thread readiness");
   setup=Stopwatch.GetTimestamp()-wholeStart;epoch=Stopwatch.GetTimestamp()+Stopwatch.Frequency/1000;ws.Epoch=epoch;start.Set();Until(epoch);
   int[] gcBefore={GC.CollectionCount(0),GC.CollectionCount(1),GC.CollectionCount(2)};
   fgStart=Stopwatch.GetTimestamp();
   for(int i=0;i<32;i++){fgInvoked[i]=Stopwatch.GetTimestamp();ws.Change(targetIds[0],ForegroundTexts[i+1]);fgReturned[i]=Stopwatch.GetTimestamp();}
   fgEnd=Stopwatch.GetTimestamp();
   result["foreground_gc_collections"]=new[]{GC.CollectionCount(0)-gcBefore[0],GC.CollectionCount(1)-gcBefore[1],GC.CollectionCount(2)-gcBefore[2]};
   if(!producer.Join(TimeSpan.FromSeconds(3))||!worker.Join(TimeSpan.FromSeconds(3)))throw new TimeoutException("producer/worker completion");
   if(errors.TryDequeue(out var e))throw new Exception("worker/producer exception",e);
   if(!SpinWait.SpinUntil(()=>ws.Changes.Count>=128,TimeSpan.FromSeconds(3)))throw new TimeoutException("queued events");
   var changes=ws.Changes.ToArray();var immediate=ws.Immediate.ToArray();var notified=ws.Notifications.ToArray();
   if(changes.Length!=128||immediate.Length!=128||notified.Length!=128)throw new Exception("event denominator");
   for(int i=0;i<128;i++)
   {
    var a=changes[i];var b=immediate[i];
    if(a.Kind!=WorkspaceChangeKind.DocumentChanged||a.DocumentId!=b.Args.DocumentId||!ReferenceEquals(a.OldSolution,b.Args.OldSolution)||!ReferenceEquals(a.NewSolution,b.Args.NewSolution)||!ReferenceEquals(b.Current,a.NewSolution))throw new Exception("event payload identity");
    if(notified[i].Id!=a.DocumentId||!ReferenceEquals(notified[i].Project.Solution,a.NewSolution))throw new Exception("notification binding");
   }
   var ids=new Dictionary<Solution,int>(ReferenceEqualityComparer.Instance);int Identity(Solution s){if(!ids.TryGetValue(s,out int id)){id=ids.Count;ids.Add(s,id);}return id;}
   Identity(initial);Solution previous=initial;int fgVersion=0,bgVersion=0,eventIndex=0,bDuring=0;
   var publications=new List<object>();var fgPubs=new long[32];var bgPubs=new long[64];var snapshotRows=new List<object>();
   while(eventIndex<128)
   {
    var first=changes[eventIndex];long pubTick=immediate[eventIndex].Tick;
    if(!ReferenceEquals(previous,first.OldSolution)||ReferenceEquals(first.OldSolution,first.NewSolution))throw new Exception("publication chain");
    bool isBackground=first.DocumentId==backgroundId;
    int oldF0=Projection(first.OldSolution,targetIds[0]),oldF1=Projection(first.OldSolution,targetIds[1]),oldBg=Projection(first.OldSolution,backgroundId!,true);
    int newF0=Projection(first.NewSolution,targetIds[0]),newF1=Projection(first.NewSolution,targetIds[1]),newBg=Projection(first.NewSolution,backgroundId!,true);
    if(oldF0!=fgVersion||oldF1!=fgVersion||oldBg!=bgVersion||newF0!=newF1)throw new Exception("old/new projection");
    if(isBackground)
    {
     if(newF0!=fgVersion||newBg!=bgVersion+1)throw new Exception("background transition");
     if(pubTick<requests[bgVersion].Invoked||pubTick>requests[bgVersion].Returned)throw new Exception("background linearization interval");
     bgPubs[bgVersion]=pubTick;bgVersion++;if(pubTick>=fgStart&&pubTick<=fgEnd)bDuring++;eventIndex++;
    }
    else
    {
     if(first.DocumentId!=targetIds[0]||newF0!=fgVersion+1||newBg!=bgVersion)throw new Exception("foreground transition");
     if(eventIndex+1>=128||changes[eventIndex+1].DocumentId!=targetIds[1]||!ReferenceEquals(first.OldSolution,changes[eventIndex+1].OldSolution)||!ReferenceEquals(first.NewSolution,changes[eventIndex+1].NewSolution))throw new Exception("linked event ordering");
     if(pubTick<fgInvoked[fgVersion]||pubTick>fgReturned[fgVersion])throw new Exception("foreground linearization interval");
     fgPubs[fgVersion]=pubTick;fgVersion++;eventIndex+=2;
    }
    publications.Add(new{kind=isBackground?"background":"foreground",old=Identity(first.OldSolution),@new=Identity(first.NewSolution),old_foreground=oldF0,new_foreground=newF0,old_background=oldBg,new_background=newBg,published_ns=Ns(pubTick-epoch),documents=isBackground?new[]{-1}:new[]{0,1}});
    previous=first.NewSolution;
   }
   if(fgVersion!=32||bgVersion!=64||!ReferenceEquals(previous,ws.CurrentSolution))throw new Exception("final publication denominator");
   foreach(var entry in ids.OrderBy(x=>x.Value))
   {
    int f0=Projection(entry.Key,targetIds[0]),f1=Projection(entry.Key,targetIds[1]),b=Projection(entry.Key,backgroundId!,true);
    if(f0!=f1)throw new Exception("retained linked snapshot");
    snapshotRows.Add(new{snapshot=entry.Value,foreground=f0,background=b});
   }
   int untouched=0;
   foreach(var entry in originals)
   {
    var doc=ws.CurrentSolution.GetDocument(entry.Key)!;if(Meta(doc)!=initialMeta[entry.Key])throw new Exception("final metadata");
    if(targetIds.Contains(entry.Key)||entry.Key==backgroundId)continue;
    if(!ReferenceEquals(doc.GetTextAsync().GetAwaiter().GetResult(),entry.Value)||doc.GetTextVersionAsync().GetAwaiter().GetResult()!=initialVersions[entry.Key])throw new Exception("unrelated identity/version");untouched++;
   }
   var counters=new Dictionary<string,long>();
   if(state is not null)
   {
    foreach(string name in new[]{"Calls","PreparedOutside","PreparedInside","Mismatches","CheapFailures","Rebases"})counters[name]=(long)Field(state,name)!;
    if(counters["Calls"]!=32+counters["CheapFailures"]||counters["CheapFailures"]>bDuring)throw new Exception("call/failure accounting");
    if(u.Mode!="original"&&counters["Calls"]>32+u.R)throw new Exception("call guarantee");
    if((u.Mode=="three"||(u.Mode=="rebase"||u.Mode=="batch"))&&counters["PreparedInside"]>Math.Min(Math.Max(bDuring-u.R,0),32))throw new Exception("protected-count guarantee");
    if(u.Mode=="original"&&counters["PreparedInside"]!=0)throw new Exception("original protected work");
   }
   result["counters"]=counters;result["actual_writes_during_foreground"]=bDuring;result["actual_writes_total"]=bgVersion;result["foreground_publications"]=fgVersion;result["events"]=128;result["untouched_documents"]=untouched;result["initial_snapshot"]=0;result["final_snapshot"]=Identity(ws.CurrentSolution);result["publications"]=publications;result["retained_snapshots"]=snapshotRows;
   result["writer_requests"]=requests.Select((v,i)=>new{index=i+1,intended_ns=Ns(v.Intended-epoch),enqueued_ns=Ns(v.Enqueued-epoch),invoked_ns=Ns(v.Invoked-epoch),published_ns=Ns(bgPubs[i]-epoch),returned_ns=Ns(v.Returned-epoch)}).ToArray();
   result["foreground_requests"]=fgInvoked.Select((v,i)=>new{index=i+1,invoked_ns=Ns(v-epoch),published_ns=Ns(fgPubs[i]-epoch),returned_ns=Ns(fgReturned[i]-epoch)}).ToArray();
  }
  catch(TimeoutException e){status="TIMEOUT";error=e.ToString();}
  catch(ArgumentException e){status="INVALID";error=e.ToString();}
  catch(Exception e){status="FAILURE";error=e.ToString();}
  finally
  {
   stop.Cancel();start.Set();bool stopped=(producer is null||producer.Join(TimeSpan.FromSeconds(3)))&&(worker is null||worker.Join(TimeSpan.FromSeconds(3)));
   if(!stopped){status="TIMEOUT";error+=" child thread did not terminate";}else{queue?.Dispose();ws?.Dispose();}
   stop.Dispose();
  }
  result["status"]=status;result["error"]=error;result["foreground_start_ns"]=Ns(fgStart-epoch);result["foreground_end_ns"]=Ns(fgEnd-epoch);result["foreground_ns"]=Ns(fgEnd-fgStart);result["setup_ns"]=Ns(setup);result["whole_unit_ns"]=Ns(Stopwatch.GetTimestamp()-wholeStart);result["observed_phases"]=observedPhases.Select(x=>new{name=x.Name,at_ns=Ns(x.Tick-epoch)}).ToArray();
  return result;
 }
 static void Main(string[] args)
 {
  _=typeof(CSharpCompilation);_=Assembly.Load("Microsoft.CodeAnalysis.CSharp.Workspaces");long processStart=Stopwatch.GetTimestamp();
  LoadRepository(args[1],args[2]);
  ForegroundTexts=TargetTexts.Select(t=>SourceText.From(t,Encoding.UTF8)).ToArray();BackgroundTexts=Enumerable.Range(0,65).Select(i=>SourceText.From(BackgroundText(i),Encoding.UTF8)).ToArray();
  ForegroundTexts[0]=SourceTexts[Manifest.GetProperty("target").GetString()!];BackgroundTexts[0]=SourceTexts[Manifest.GetProperty("background").GetString()!];
  for(int i=0;i<ForegroundTexts.Length;i++)FgVersions.Add(ForegroundTexts[i],i);for(int i=0;i<BackgroundTexts.Length;i++)BgVersions.Add(BackgroundTexts[i],i);
  Console.Error.WriteLine(JsonSerializer.Serialize(new{runtime=RuntimeInformation.FrameworkDescription,architecture=RuntimeInformation.ProcessArchitecture.ToString(),workspace_assembly=typeof(Workspace).Assembly.Location,manifest_sha256=ManifestSha,stopwatch_frequency=Stopwatch.Frequency,input_materialization_ns=Ns(Stopwatch.GetTimestamp()-processStart),source_files=SourceTexts.Count,foreground_texts=ForegroundTexts.Length,background_texts=BackgroundTexts.Length}));
  int sequence=0;foreach(var line in File.ReadLines(args[0])){var x=line.Split('\t');var u=new Unit(x[0],x[1],int.Parse(x[2]),int.Parse(x[3]),int.Parse(x[4]),x[5],int.Parse(x[6]));var r=Run(u);r["sequence"]=sequence++;r["process_elapsed_ns"]=Ns(Stopwatch.GetTimestamp()-processStart);Console.WriteLine(JsonSerializer.Serialize(r));Console.Out.Flush();}
 }
}
