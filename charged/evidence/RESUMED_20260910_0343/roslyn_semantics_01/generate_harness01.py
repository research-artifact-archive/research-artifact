from pathlib import Path
import hashlib,json
D=Path(__file__).resolve().parent
s=(D/'PREDECESSOR/harness_repo01/Program.cs').read_text()
def change(a,b):
 global s
 assert s.count(a)==1,(s.count(a),a[:100])
 s=s.replace(a,b)
change('''    public StudyWorkspace() : base(MefHostServices.DefaultHost, "BoundedDocumentRetryStudy")
    {
        _ = RegisterWorkspaceChangedHandler(e => { if(e.Kind==WorkspaceChangeKind.DocumentChanged) Changes.Enqueue(e); });
    }''','''    public readonly ConcurrentQueue<(WorkspaceChangeEventArgs Args, Solution Current)> Immediate = new();
    public StudyWorkspace() : base(MefHostServices.DefaultHost, "BoundedDocumentRetrySemanticsStudy") {}
    public void StartRecording()
    {
        _ = RegisterWorkspaceChangedHandler(e => Changes.Enqueue(e));
        _ = RegisterWorkspaceChangedImmediateHandler(e => Immediate.Enqueue((e, CurrentSolution)));
    }''')
change('''    static string BackgroundBase="";''','''    static string BackgroundBase="";
    static string WriterTargetText(int i)=>TargetTexts[0]+$"\\n// semantics-study interfering target revision {i}\\n";
    static bool Normal(Unit u)=>u.Scenario is "normal" or "spread" or "target_writer" or "linked_writer";
    static bool TargetWriter(Unit u)=>u.Scenario is "target_writer" or "linked_writer";''')
change('''if(!background){int i=Array.IndexOf(TargetTexts,text);if(i<0)throw new Exception("unexpected target text");return i;}''','''if(!background){int i=Array.IndexOf(TargetTexts,text);if(i>=0)return i;for(int j=1;j<32;j++)if(text==WriterTargetText(j))return -100-j;throw new Exception("unexpected target text");}''')
change('''var originals=new Dictionary<DocumentId,SourceText>();''','''var originals=new Dictionary<DocumentId,SourceText>();''')
change('''            work=new BlockingCollection<Action>();writer=new Thread''','''            var initialSolution=ws.CurrentSolution;
            Identity(initialSolution);
            ws.StartRecording();
            var initialVersions=originals.Keys.Where(id=>initialSolution.ContainsDocument(id)).ToDictionary(id=>id,id=>initialSolution.GetDocument(id)!.GetTextVersionAsync().GetAwaiter().GetResult());
            work=new BlockingCollection<Action>();writer=new Thread''')
change('''long started=Stopwatch.GetTimestamp();var done=new TaskCompletionSource''','''long started=Stopwatch.GetTimestamp();var beforeWrite=ws.CurrentSolution;var done=new TaskCompletionSource''')
change('''if(remove)ws.Remove(targetIds[0]);else ws.Change(backgroundId!,SourceText.From(BackgroundText(next),Encoding.UTF8));''','''if(remove)ws.Remove(targetIds[0]);else if(TargetWriter(u))ws.Change(targetIds[u.Scenario=="linked_writer"?1:0],SourceText.From(WriterTargetText(next),Encoding.UTF8));else ws.Change(backgroundId!,SourceText.From(BackgroundText(next),Encoding.UTF8));''')
change('''{"kind",remove?"remove_target":"change_background"},{"write",writes}''','''{"kind",remove?"remove_target":TargetWriter(u)?"change_target":"change_background"},{"before_snapshot",Identity(beforeWrite)},{"write",writes}''')
change('''else if(u.Scenario=="normal"&&writes<u.B)Inject(false);''','''else if(Normal(u)&&writes<u.B&&(u.Scenario!="spread"||writes<job))Inject(false);''')
change('''int jobs=u.Scenario=="normal"?4:1;''','''int jobs=Normal(u)?4:1;''')
change('''int expectedChanges=u.Scenario switch{"normal"=>4*targetIds.Count+writes,"equal_identity"=>targetIds.Count,_=>0};''','''int expectedChanges=Normal(u)?4*targetIds.Count+writes*(TargetWriter(u)?2:1):u.Scenario=="equal_identity"?targetIds.Count:0;
            int expectedEvents=expectedChanges+(u.Scenario=="removed_between"?1:0);''')
change('''if(!SpinWait.SpinUntil(()=>ws.Changes.Count>=expectedChanges,TimeSpan.FromSeconds(3)))''','''if(!SpinWait.SpinUntil(()=>ws.Changes.Count>=expectedEvents,TimeSpan.FromSeconds(3)))''')
change('''var notified=ws.Notifications.ToArray();var changed=ws.Changes.ToArray();''','''var notified=ws.Notifications.ToArray();var allChanged=ws.Changes.ToArray();var immediate=ws.Immediate.ToArray();
            var changed=allChanged.Where(e=>e.Kind==WorkspaceChangeKind.DocumentChanged).ToArray();
            if(allChanged.Length!=expectedEvents||immediate.Length!=expectedEvents)throw new Exception("full event count");
            for(int ei=0;ei<allChanged.Length;ei++)
            {
                var a=allChanged[ei];var b=immediate[ei];
                if(a.Kind!=b.Args.Kind||a.DocumentId!=b.Args.DocumentId||a.ProjectId!=b.Args.ProjectId||!ReferenceEquals(a.OldSolution,b.Args.OldSolution)||!ReferenceEquals(a.NewSolution,b.Args.NewSolution))throw new Exception("queued/immediate payload differs");
                if(!ReferenceEquals(b.Current,b.Args.NewSolution))throw new Exception("immediate event not bound to current publication");
            }
            for(int ni=0;ni<notified.Length;ni++)if(ni>=changed.Length||!ReferenceEquals(notified[ni].Project.Solution,changed[ni].NewSolution))throw new Exception("document notification not bound to event publication");''')
change('''{"version",TextVersion(doc,doc.Id==backgroundId)}});''','''{"version",TextVersion(doc,doc.Id==backgroundId)},{"snapshot",Identity(doc.Project.Solution)}});''')
change('''int finalExpected=u.Scenario=="normal"?4:0;''','''int finalExpected=Normal(u)?4:0;''')
change('''if(finalBackground!=(u.Scenario=="normal"?writes:0))''','''if(finalBackground!=(Normal(u)&&!TargetWriter(u)?writes:0))''')
change('''int wanted=u.Scenario=="normal"?(int)c["job"]!:0;''','''int wanted=Normal(u)?(int)c["job"]!:0;''')
change('''if((int)c["background_version"]! != (int)c["writes_at_return"]!)''','''if((int)c["background_version"]! != (TargetWriter(u)?0:(int)c["writes_at_return"]!))''')
change('''if(u.Scenario=="normal"&&writes!=u.B)''','''if(Normal(u)&&writes!=u.B)''')
change('''if(u.Scenario=="normal"&&state is not null)''','''if((u.Scenario=="normal"||TargetWriter(u))&&state is not null)''')
change('''            result["unchanged_source_documents"]=preserved;''','''            // Validate the atomic publication chain. Linked callbacks share one pair.
            var publicationRows=new List<Dictionary<string,object?>>();
            Solution previous=initialSolution;Solution? groupNew=null;Solution? groupOld=null;
            var groupDocuments=new List<int>();WorkspaceChangeKind groupKind=default;
            void FinishGroup()
            {
                if(groupNew is null||groupOld is null)return;
                int[] before=targetIds.Select(id=>TextVersion(groupOld.GetDocument(id))).ToArray();
                int[] after=targetIds.Select(id=>TextVersion(groupNew.GetDocument(id))).ToArray();
                int beforeBg=TextVersion(groupOld.GetDocument(backgroundId!),true),afterBg=TextVersion(groupNew.GetDocument(backgroundId!),true);
                if(groupKind==WorkspaceChangeKind.DocumentRemoved)
                {
                    if(!groupDocuments.SequenceEqual(new[]{0})||after[0]!=-1||after[1]!=before[1]||beforeBg!=afterBg)throw new Exception("removal publication semantics");
                }
                else if(groupKind==WorkspaceChangeKind.DocumentChanged)
                {
                    if(groupDocuments.SequenceEqual(new[]{-1}))
                    {
                        if(beforeBg==afterBg||!before.SequenceEqual(after))throw new Exception("background publication semantics");
                    }
                    else
                    {
                        int[] expectedOrder=u.Scenario=="linked_writer"&&after[0]<=-101?new[]{1,0}:new[]{0,1};
                        if(!groupDocuments.SequenceEqual(expectedOrder)||after[0]!=after[1]||beforeBg!=afterBg)throw new Exception("linked publication semantics/order");
                        if(after[0]<=-101&&!TargetWriter(u))throw new Exception("unplanned target writer text");
                        if(after[0]>=0&&after[0]>4)throw new Exception("unplanned target request");
                    }
                }
                else throw new Exception("unexpected publication kind");
                publicationRows.Add(new(){{"kind",groupKind.ToString()},{"old",Identity(groupOld)},{"new",Identity(groupNew)},{"documents",groupDocuments.ToArray()},{"old_targets",before},{"new_targets",after},{"old_background",beforeBg},{"new_background",afterBg}});
            }
            foreach(var e in allChanged)
            {
                if(!ReferenceEquals(groupNew,e.NewSolution))
                {
                    FinishGroup();
                    if(!ReferenceEquals(previous,e.OldSolution)||ReferenceEquals(e.OldSolution,e.NewSolution))throw new Exception("publication chain");
                    groupOld=e.OldSolution;groupNew=e.NewSolution;previous=e.NewSolution;groupDocuments=new();groupKind=e.Kind;
                }
                else if(!ReferenceEquals(groupOld,e.OldSolution)||groupKind!=e.Kind)throw new Exception("linked payload pair differs");
                groupDocuments.Add(e.DocumentId==backgroundId?-1:targetIds.IndexOf(e.DocumentId!));
            }
            FinishGroup();
            if(!ReferenceEquals(previous,ws.CurrentSolution))throw new Exception("final solution not last publication");

            // Public snapshot projection: every untouched document and project is checked.
            // Numeric versions are compared only to the same execution's initial untouched state.
            string Meta(Document d)=>JsonSerializer.Serialize(new{d.Name,d.FilePath,d.Folders,d.SourceCodeKind,d.SupportsSyntaxTree,d.SupportsSemanticModel});
            string ProjectMeta(Project p)=>JsonSerializer.Serialize(new{p.Name,p.AssemblyName,p.Language,p.FilePath,p.OutputFilePath,p.OutputRefFilePath,p.DefaultNamespace,parse=p.ParseOptions?.ToString(),compilation=p.CompilationOptions?.ToString(),refs=p.ProjectReferences.Select(r=>new{id=r.ProjectId.Id,r.Aliases,r.EmbedInteropTypes}),metadata=p.MetadataReferences.Select(r=>r.Display),analyzers=p.AnalyzerReferences.Select(r=>r.FullPath)});
            var initialDocMeta=initialVersions.Keys.ToDictionary(id=>id,id=>Meta(initialSolution.GetDocument(id)!));
            var initialProjectMeta=initialSolution.Projects.ToDictionary(p=>p.Id,p=>ProjectMeta(p));
            var untouchedIds=originals.Keys.Where(id=>!targetSet.Contains(id)&&id!=backgroundId).ToArray();
            foreach(var e in allChanged){Identity(e.OldSolution);Identity(e.NewSolution);}
            foreach(var e in immediate)Identity(e.Current);
            Identity(ws.CurrentSolution);
            var projectionRows=new List<Dictionary<string,object?>>();
            var immutableDigest=new Dictionary<Solution,string>(ReferenceEqualityComparer.Instance);
            foreach(var entry in snapshotIds.OrderBy(x=>x.Value).ToArray())
            {
                // Kernel output snapshots may precede publication, but they must preserve unrelated state too.
                var sol=entry.Key;var words=new StringBuilder();int untouched=0;
                if(!sol.ProjectIds.SequenceEqual(initialSolution.ProjectIds))throw new Exception("project membership changed");
                foreach(var project in sol.Projects)
                {
                    if(ProjectMeta(project)!=initialProjectMeta[project.Id])throw new Exception("project metadata changed");
                    var initialProject=initialSolution.GetProject(project.Id)!;
                    if(!ReferenceEquals(project.ParseOptions,initialProject.ParseOptions)||!ReferenceEquals(project.CompilationOptions,initialProject.CompilationOptions))throw new Exception("project options identity changed");
                }
                foreach(var id in untouchedIds)
                {
                    var d=sol.GetDocument(id)??throw new Exception("unrelated document removed");
                    if(!ReferenceEquals(d.GetTextAsync().GetAwaiter().GetResult(),originals[id]))throw new Exception("unrelated text identity");
                    if(d.GetTextVersionAsync().GetAwaiter().GetResult()!=initialVersions[id])throw new Exception("unrelated text version");
                    if(Meta(d)!=initialDocMeta[id])throw new Exception("unrelated metadata");
                    words.Append(id.Id).Append('|').Append(initialDocMeta[id]).Append('|').Append(d.GetTextVersionAsync().GetAwaiter().GetResult()).Append('\\n');untouched++;
                }
                foreach(var id in targetIds.Append(backgroundId!))
                    if(sol.GetDocument(id) is {} d&&Meta(d)!=initialDocMeta[id])throw new Exception("affected metadata changed");
                int memberCount=sol.Projects.Sum(p=>p.DocumentIds.Count);
                if(memberCount!=ordinal-(sol.ContainsDocument(targetIds[0])?0:1))throw new Exception("document membership changed");
                string digest=Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(words.ToString())));
                immutableDigest[sol]=digest;
                projectionRows.Add(new(){{"snapshot",entry.Value},{"targets",targetIds.Select(id=>TextVersion(sol.GetDocument(id))).ToArray()},{"background",TextVersion(sol.GetDocument(backgroundId!),true)},{"documents",memberCount},{"untouched_documents",untouched},{"untouched_projection_sha256",digest}});
            }
            string initialDigest=immutableDigest[initialSolution];
            if(immutableDigest.Values.Any(x=>x!=initialDigest))throw new Exception("untouched snapshot projection differs");
            object Payload(WorkspaceChangeEventArgs e)=>new{kind=e.Kind.ToString(),document=e.DocumentId==backgroundId?-1:targetIds.IndexOf(e.DocumentId!),project=e.ProjectId!.Id,old=Identity(e.OldSolution),@new=Identity(e.NewSolution)};
            result["initial_snapshot"]=Identity(initialSolution);result["final_snapshot"]=Identity(ws.CurrentSolution);
            result["immediate_events"]=immediate.Select(e=>new{payload=Payload(e.Args),current=Identity(e.Current)}).ToArray();
            result["queued_events"]=allChanged.Select(Payload).ToArray();
            result["publications"]=publicationRows;result["snapshot_projections"]=projectionRows;
            result["initial_untouched_projection_sha256"]=initialDigest;
            result["unchanged_source_documents"]=preserved;''')
(D/'harness01/Program.cs').write_text(s)
units=[];number=0
def add(mode,scenario,r,b):
 global number
 number+=1
 units.append('\t'.join(map(str,[f's{number:04d}','semantics',0,0,4,r,b,mode,scenario])))
for mode in ['original','two','three']:
 for r in [0,1,2]:
  for b in range(r+5):add(mode,'normal',r,b)
  for b in range(1,5):add(mode,'spread',r,b)
  for scenario in ['target_writer','linked_writer']:
   for b in dict.fromkeys([1,r+1,r+4]):add(mode,scenario,r,b)
  for scenario in ['noop','equal_identity','missing_required','removed_between']:add(mode,scenario,r,0)
(D/'harness01/UNITS.tsv').write_text('\n'.join(units)+'\n')
baseline=[]
for i,scenario in enumerate(['normal','noop','equal_identity','missing_required']):
 baseline.append('\t'.join(map(str,[f'b{i+1:04d}','semantics-control',0,0,4,0,0,'baseline',scenario])))
(D/'harness01/BASELINE.tsv').write_text('\n'.join(baseline)+'\n')
print(json.dumps({'units':len(units),'baseline_controls':len(baseline),'source_sha256':hashlib.sha256(s.encode()).hexdigest()}))
