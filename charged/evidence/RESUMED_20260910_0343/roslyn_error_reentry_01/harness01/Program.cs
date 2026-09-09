using System.Reflection;
using System.Text.Json;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.Host.Mef;
using Microsoft.CodeAnalysis.Text;

sealed class ErrorWorkspace:Workspace
{
 public DocumentId Background=null!;
 public bool Enabled;
 public int NameCalls,Notifications;
 public ErrorWorkspace():base(MefHostServices.DefaultHost,"MissingDocumentErrorReentryStudy"){}
 public void Init(SolutionInfo info)=>OnSolutionAdded(info);
 public void Change(DocumentId id,string text)=>OnDocumentTextChanged(id,SourceText.From(text),PreservationMode.PreserveIdentity);
 public void Remove(DocumentId id)=>OnDocumentRemoved(id);
 protected override void OnDocumentTextChanged(Document doc){Notifications++;}
 protected override string GetDocumentName(DocumentId id)
 {
  Console.Error.WriteLine(JsonSerializer.Serialize(new{event_kind="get_name_enter",enabled=Enabled,thread=Environment.CurrentManagedThreadId}));
  if(Enabled&&NameCalls++==0)
  {
   Change(Background,"background revised from the error-name hook");
   Console.Error.WriteLine(JsonSerializer.Serialize(new{event_kind="get_name_nested_update_returned"}));
  }
  return "missing document";
 }
}
static class Program
{
 static BindingFlags Flags=BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic;
 static void Set(object x,string name,object value)=>x.GetType().GetField(name,Flags)!.SetValue(x,value);
 static object? Get(object x,string name)=>x.GetType().GetField(name,Flags)!.GetValue(x);
 static void Main(string[] args)
 {
  string mode=args[0],scenario=args[2];int r=int.Parse(args[1]);
  _=typeof(CSharpCompilation);_=Assembly.Load("Microsoft.CodeAnalysis.CSharp.Workspaces");
  using var ws=new ErrorWorkspace();
  var pid=ProjectId.CreateNewId();var target=DocumentId.CreateNewId(pid);var background=DocumentId.CreateNewId(pid);ws.Background=background;
  DocumentInfo Doc(DocumentId id,string name)=>DocumentInfo.Create(id,name,loader:TextLoader.From(TextAndVersion.Create(SourceText.From("initial "+name),VersionStamp.Default)),filePath:"/fixture/"+name);
  ws.Init(SolutionInfo.Create(SolutionId.CreateNewId(),VersionStamp.Default,projects:new[]{ProjectInfo.Create(pid,VersionStamp.Default,"p","p",LanguageNames.CSharp,documents:new[]{Doc(target,"target.cs"),Doc(background,"background.cs")})}));
  if(scenario=="missing_before")ws.Remove(target);
  object? state=null;bool removed=false;
  if(mode!="baseline")
  {
   state=Activator.CreateInstance(typeof(Workspace).GetNestedType("DocumentRetryStudyState",BindingFlags.NonPublic)!,true)!;
   Set(state,"OwnerThreadId",Environment.CurrentManagedThreadId);Set(state,"Mode",mode=="original"?-1:mode=="two"?0:1);Set(state,"Remaining",r);
   Action<string,Solution> hook=(kind,sol)=>{
    Console.Error.WriteLine(JsonSerializer.Serialize(new{event_kind="source_step",kind,target_present=sol.ContainsDocument(target),thread=Environment.CurrentManagedThreadId}));
    if(kind=="before_lock"&&scenario=="removed_between"&&!removed)
    {
     removed=true;Exception? error=null;var writer=new Thread(()=>{try{ws.Remove(target);}catch(Exception e){error=e;}});
     writer.Start();if(!writer.Join(1000))throw new TimeoutException("removal writer");if(error is not null)throw error;
     Console.Error.WriteLine(JsonSerializer.Serialize(new{event_kind="removal_returned"}));
    }
   };
   Set(state,"Hook",hook);typeof(Workspace).GetField("DocumentRetryStudy",Flags)!.SetValue(ws,state);
  }
  ws.Enabled=true;
  Console.Error.WriteLine(JsonSerializer.Serialize(new{event_kind="outer_start",mode,r,scenario,assembly=typeof(Workspace).Assembly.Location}));
  string observed="NONE";
  try{ws.Change(target,"foreground revision");}
  catch(ArgumentException){observed="ArgumentException";}
  string bg=ws.CurrentSolution.GetDocument(background)!.GetTextAsync().GetAwaiter().GetResult().ToString();
  bool valid=observed=="ArgumentException"&&!ws.CurrentSolution.ContainsDocument(target)&&bg=="background revised from the error-name hook"&&ws.NameCalls==1&&ws.Notifications==1;
  var counters=new Dictionary<string,object?>();if(state is not null)foreach(var name in new[]{"Calls","PreparedOutside","PreparedInside","Mismatches","CheapFailures"})counters[name]=Get(state,name);
  Console.WriteLine(JsonSerializer.Serialize(new{mode,r,scenario,status=valid?"SUCCESS":"FAILURE",observed_exception=observed,name_calls=ws.NameCalls,notifications=ws.Notifications,target_present=ws.CurrentSolution.ContainsDocument(target),background=bg,counters}));
 }
}

