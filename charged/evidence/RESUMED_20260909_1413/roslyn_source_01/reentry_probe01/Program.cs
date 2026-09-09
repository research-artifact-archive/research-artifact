using System.Reflection;
using System.Text;
using System.Text.Json;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.Host.Mef;
using Microsoft.CodeAnalysis.Text;

sealed class ReentryWorkspace : Workspace
{
    public int Notifications,Reentries;private bool entered;
    public ReentryWorkspace() : base(MefHostServices.DefaultHost,"SameTextReentryProbe") {}
    public void Initialize(SolutionInfo info)=>OnSolutionAdded(info);
    public void Change(DocumentId id,SourceText text)=>OnDocumentTextChanged(id,text,PreservationMode.PreserveIdentity);
    protected override void OnDocumentTextChanged(Document document)
    {
        Notifications++;
        if(!entered)
        {
            entered=true;var same=document.GetTextAsync().GetAwaiter().GetResult();
            Console.WriteLine(JsonSerializer.Serialize(new{phase="before_same_text_reentry",notifications=Notifications}));Console.Out.Flush();
            Change(document.Id,same);Reentries++;
        }
    }
}

static class Program
{
    static void Main(string[] args)
    {
        _=typeof(CSharpCompilation);_=Assembly.Load("Microsoft.CodeAnalysis.CSharp.Workspaces");
        using var ws=new ReentryWorkspace();var p=ProjectId.CreateFromSerialized(new Guid("00000001-0000-0000-0000-000000000001"));var d=DocumentId.CreateFromSerialized(p,new Guid("00000002-0000-0000-0000-000000000001"));
        var old=SourceText.From("class Target {}\n",Encoding.UTF8);var doc=DocumentInfo.Create(d,"Target.cs",loader:TextLoader.From(TextAndVersion.Create(old,VersionStamp.Create())),filePath:"/authored/Target.cs");
        ws.Initialize(SolutionInfo.Create(SolutionId.CreateNewId(),VersionStamp.Create(),projects:new[]{ProjectInfo.Create(p,VersionStamp.Create(),"P","P",LanguageNames.CSharp,documents:new[]{doc})}));
        _=ws.CurrentSolution.GetDocument(d)!.GetTextAsync().GetAwaiter().GetResult();
        object? state=null;var flags=BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance;
        if(args[0]!="baseline")
        {
            var type=typeof(Workspace).GetNestedType("DocumentRetryStudyState",BindingFlags.NonPublic)!;state=Activator.CreateInstance(type,true)!;
            type.GetField("OwnerThreadId",flags)!.SetValue(state,Environment.CurrentManagedThreadId);
            type.GetField("Mode",flags)!.SetValue(state,args[0] switch{"original"=>-1,"two"=>0,"three"=>1,_=>throw new Exception("mode")});
            type.GetField("Remaining",flags)!.SetValue(state,0);typeof(Workspace).GetField("DocumentRetryStudy",flags)!.SetValue(ws,state);
        }
        var next=SourceText.From("class Target { int x; }\n",Encoding.UTF8);ws.Change(d,next);
        bool ok=ws.Notifications==1&&ws.Reentries==1&&ReferenceEquals(next,ws.CurrentSolution.GetDocument(d)!.GetTextAsync().GetAwaiter().GetResult());
        Console.WriteLine(JsonSerializer.Serialize(new{phase="terminal",status=ok?"SUCCESS":"FAILURE",mode=args[0],notifications=ws.Notifications,completed_reentries=ws.Reentries,calls=state is null?null:state.GetType().GetField("Calls",flags)!.GetValue(state),same_text_identity=ok,workspace_assembly=typeof(Workspace).Assembly.Location}));
    }
}
