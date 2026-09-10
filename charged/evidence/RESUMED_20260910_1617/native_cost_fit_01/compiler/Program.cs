using System.Collections.Concurrent;
using System.Globalization;
using System.Reflection;
using System.Text;
using System.Text.Json;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;
using Microsoft.CodeAnalysis.Host.Mef;
using Microsoft.CodeAnalysis.Text;

sealed class CompilerWorkspace : Workspace
{
    public CompilerWorkspace() : base(MefHostServices.DefaultHost, "CompilerProjectionStudy") { }
    public void Init(SolutionInfo info) => OnSolutionAdded(info);
    public void Change(DocumentId id, string text) => OnDocumentTextChanged(id, SourceText.From(text, Encoding.UTF8), PreservationMode.PreserveIdentity);
    public void Parse(ProjectId id, CSharpParseOptions options) => OnParseOptionsChanged(id, options);
    public void RemoveReference(ProjectId id, ProjectId dependency) => OnProjectReferenceRemoved(id, new ProjectReference(dependency));
    protected override void OnDocumentTextChanged(Document document) { }
}

record Snapshot(string Label, Solution Solution, bool Background, bool Foreground);
static class Program
{
    static readonly BindingFlags Flags = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic;
    static readonly string[] Names = { "FixtureA", "FixtureB", "FixtureC", "FixtureD" };
    static readonly ProjectId[] Pids = Enumerable.Range(1, 4).Select(i => ProjectId.CreateFromSerialized(new Guid(i, 0, 0, new byte[8]))).ToArray();
    static readonly DocumentId[] Dids = Pids.Select((p, i) => DocumentId.CreateFromSerialized(p, new Guid(i + 11, 0, 0, new byte[8]))).ToArray();
    static readonly string[] Paths = { "/fixture/Numbers.cs", "/fixture/Reader.cs", "/fixture/Reader.cs", "/fixture/Spare.cs" };
    static readonly MetadataReference[] Metadata = { MetadataReference.CreateFromFile(typeof(object).Assembly.Location) };
    static readonly CSharpCompilationOptions CompilationOptions = new(OutputKind.DynamicallyLinkedLibrary);
    static CSharpParseOptions ParseOptions(bool alt) => new(LanguageVersion.CSharp12, preprocessorSymbols: alt ? new[] { "ALT" } : Array.Empty<string>());
    static string Scenario = "";
    static bool Warm;
    static string Source(int project, bool background, bool foreground)
    {
        if (project == 0)
            return background && Scenario == "library_type"
                ? "public static class Numbers { public const string Value = \"one\"; }\n"
                : $"public static class Numbers {{ public const int Value = {(background && Scenario == "library_constant" ? 7 : 1)}; }}\n";
        if (project == 3)
            return $"public static class Spare {{ public const int Value = {(background && Scenario == "unrelated_spare" ? 9 : 1)}; }}\n";
        string suffix = foreground ? " + 1" : background && Scenario == "target_writer" ? " - 1" : "";
        string altSuffix = foreground ? " + \"!\"" : "";
        return "public static class Reader {\n#if ALT\n public static string Read() => Numbers.Value" + altSuffix + ";\n#else\n public static int Read() => Numbers.Value" + suffix + ";\n#endif\n}\n";
    }
    static bool Alt(int project, bool background) => project == 1 && background && Scenario == "target_parse";
    static bool HasReference(int project, bool background) => project is 1 or 2 && !(project == 2 && background && Scenario == "linked_reference_removed");
    static object[] Diagnostics(IEnumerable<Diagnostic> diagnostics) => diagnostics.OrderBy(d => d.Id).ThenBy(d => d.Location.SourceSpan.Start).ThenBy(d => d.GetMessage(CultureInfo.InvariantCulture)).Select(d => (object)new
    {
        id = d.Id, severity = d.Severity.ToString(), path = d.Location.SourceTree?.FilePath ?? "", start = d.Location.SourceSpan.Start, length = d.Location.SourceSpan.Length, message = d.GetMessage(CultureInfo.InvariantCulture)
    }).ToArray();
    static object Feature(CSharpCompilation compilation, int project)
    {
        var tree = compilation.SyntaxTrees.Single();
        var access = tree.GetRoot().DescendantNodes().OfType<MemberAccessExpressionSyntax>().FirstOrDefault(x => x.Name.Identifier.ValueText == "Value");
        var model = compilation.GetSemanticModel(tree);
        var symbol = access is null ? null : model.GetSymbolInfo(access).Symbol as IFieldSymbol;
        var constant = access is null ? default : model.GetConstantValue(access);
        var valueField = compilation.GetTypeByMetadataName(project == 0 ? "Numbers" : project == 3 ? "Spare" : "Reader")?.GetMembers("Value").OfType<IFieldSymbol>().SingleOrDefault();
        var method = compilation.GetTypeByMetadataName("Reader")?.GetMembers("Read").OfType<IMethodSymbol>().SingleOrDefault();
        using var bytes = new MemoryStream(); var emitted = compilation.Emit(bytes);
        return new
        {
            assembly = compilation.AssemblyName, diagnostics = Diagnostics(compilation.GetDiagnostics()), emit_success = emitted.Success, emit_diagnostics = Diagnostics(emitted.Diagnostics),
            read_return_type = method?.ReturnType.ToDisplayString(), exported_value_type = valueField?.Type.ToDisplayString(), exported_constant = valueField?.ConstantValue,
            access_symbol_type = symbol?.Type.ToDisplayString(), access_symbol_assembly = symbol?.ContainingAssembly.Name,
            access_has_constant = constant.HasValue, access_constant = constant.HasValue ? constant.Value : null
        };
    }
    static Dictionary<string, object> Oracle(bool background, bool foreground)
    {
        var answer = new Dictionary<string, object>(); var compilations = new CSharpCompilation[4];
        for (int p = 0; p < 4; p++)
        {
            var tree = CSharpSyntaxTree.ParseText(Source(p, background, foreground), ParseOptions(Alt(p, background)), Paths[p]);
            var refs = Metadata.ToList(); if (HasReference(p, background)) refs.Add(compilations[0].ToMetadataReference());
            compilations[p] = CSharpCompilation.Create(Names[p], new[] { tree }, refs, CompilationOptions);
            answer.Add(Names[p], new { source = Source(p, background, foreground), symbols = Alt(p, background) ? new[] { "ALT" } : Array.Empty<string>(), references = HasReference(p, background) ? new[] { "FixtureA" } : Array.Empty<string>(), feature = Feature(compilations[p], p) });
        }
        return answer;
    }
    static Dictionary<string, object> Actual(Solution solution)
    {
        var answer = new Dictionary<string, object>();
        for (int p = 0; p < 4; p++)
        {
            var project = solution.GetProject(Pids[p])!; var document = project.GetDocument(Dids[p])!;
            var compilation = (CSharpCompilation)project.GetCompilationAsync().GetAwaiter().GetResult()!;
            answer.Add(Names[p], new
            {
                source = document.GetTextAsync().GetAwaiter().GetResult().ToString(), symbols = ((CSharpParseOptions)project.ParseOptions!).PreprocessorSymbolNames.Order().ToArray(),
                references = project.ProjectReferences.Select(x => Names[Array.IndexOf(Pids, x.ProjectId)]).Order().ToArray(), feature = Feature(compilation, p)
            });
        }
        return answer;
    }
    static object Projection(Snapshot snapshot)
    {
        var actual = Actual(snapshot.Solution); var expected = Oracle(snapshot.Background, snapshot.Foreground);
        bool valid = JsonSerializer.Serialize(actual) == JsonSerializer.Serialize(expected);
        return new { label = snapshot.Label, background = snapshot.Background, foreground = snapshot.Foreground, status = valid ? "PASS" : "FAIL", actual, expected };
    }
    static void Set(object state, string name, object value) => state.GetType().GetField(name, Flags)!.SetValue(state, value);
    static void Main(string[] args)
    {
        string id = args[0], mode = args[1]; int r = int.Parse(args[2]); Scenario = args[3]; Warm = args[4] == "warm";
        _ = typeof(CSharpCompilation); _ = Assembly.Load("Microsoft.CodeAnalysis.CSharp.Workspaces");
        var snapshots = new List<Snapshot>(); var warmChecks = new List<object>(); var output = new Dictionary<string, object?> { ["id"] = id, ["mode"] = mode, ["r"] = r, ["scenario"] = Scenario, ["cache"] = args[4] };
        int writes = 0; object? state = null;
        var resourceCounts = new Dictionary<string, int>();
        var resourceHookField = typeof(Workspace).GetField("RetryCostHook", BindingFlags.Static | BindingFlags.NonPublic);
        Action<string> resourceHook = name => resourceCounts[name] = resourceCounts.GetValueOrDefault(name) + 1;
        try
        {
            using var workspace = new CompilerWorkspace(); var projects = new List<ProjectInfo>();
            for (int p = 0; p < 4; p++)
            {
                var document = DocumentInfo.Create(Dids[p], System.IO.Path.GetFileName(Paths[p]), loader: TextLoader.From(TextAndVersion.Create(SourceText.From(Source(p, false, false), Encoding.UTF8), VersionStamp.Default, Paths[p])), filePath: Paths[p]);
                projects.Add(ProjectInfo.Create(Pids[p], VersionStamp.Default, Names[p], Names[p], LanguageNames.CSharp, compilationOptions: CompilationOptions, parseOptions: ParseOptions(false), documents: new[] { document }, projectReferences: HasReference(p, false) ? new[] { new ProjectReference(Pids[0]) } : Array.Empty<ProjectReference>(), metadataReferences: Metadata));
            }
            workspace.Init(SolutionInfo.Create(SolutionId.CreateNewId(), VersionStamp.Default, projects: projects));
            void Capture(string label, Solution solution, bool background, bool foreground, bool canWarm)
            {
                var snapshot = new Snapshot(label, solution, background, foreground); snapshots.Add(snapshot);
                if (Warm && canWarm) warmChecks.Add(Projection(snapshot));
            }
            Capture("initial", workspace.CurrentSolution, false, false, true);
            void Background()
            {
                switch (Scenario)
                {
                    case "library_type": case "library_constant": workspace.Change(Dids[0], Source(0, true, false)); break;
                    case "unrelated_spare": workspace.Change(Dids[3], Source(3, true, false)); break;
                    case "target_parse": workspace.Parse(Pids[1], ParseOptions(true)); break;
                    case "linked_reference_removed": workspace.RemoveReference(Pids[2], Pids[0]); break;
                    case "target_writer": workspace.Change(Dids[1], Source(1, true, false)); break;
                    default: throw new ArgumentException("unknown scenario");
                }
                writes++; Capture("background", workspace.CurrentSolution, true, false, true);
            }
            if (mode == "baseline") Background();
            else
            {
                state = Activator.CreateInstance(typeof(Workspace).GetNestedType("DocumentRetryStudyState", BindingFlags.NonPublic)!, true)!;
                Set(state, "OwnerThreadId", Environment.CurrentManagedThreadId); Set(state, "Mode", mode == "original" ? -1 : mode == "two" ? 0 : 1); Set(state, "Remaining", r); Set(state, "AllowPreparedRebase", mode == "rebase");
                Action<string, Solution> hook = (kind, solution) =>
                {
                    if (kind is "kernel_outside_end" or "kernel_inside_end" or "rebase_completed") Capture(kind + "_" + snapshots.Count, solution, writes == 1, true, kind == "kernel_outside_end");
                    if (kind == "before_lock" && writes == 0)
                    {
                        Exception? error = null; var writer = new Thread(() => { try { Background(); } catch (Exception e) { error = e; } });
                        writer.Start(); if (!writer.Join(3000)) throw new TimeoutException("background worker"); if (error is not null) throw error;
                    }
                };
                Set(state, "Hook", hook); typeof(Workspace).GetField("DocumentRetryStudy", Flags)!.SetValue(workspace, state);
            }
            resourceHookField?.SetValue(null, resourceHook);
            try { workspace.Change(Dids[1], Source(1, true, true)); }
            finally { resourceHookField?.SetValue(null, null); }
            output["resource_counts"] = resourceCounts;
            output["resource_hook_present"] = resourceHookField is not null;
            Capture("final", workspace.CurrentSolution, true, true, true);
            var checkedSnapshots = snapshots.Select(Projection).ToArray();
            bool valid = writes == 1 && checkedSnapshots.Concat(warmChecks).All(x => JsonSerializer.SerializeToElement(x).GetProperty("status").GetString() == "PASS");
            var counters = new Dictionary<string, object?>(); if (state is not null) foreach (string name in new[] { "Calls", "PreparedOutside", "PreparedInside", "Mismatches", "CheapFailures", "Rebases" }) counters[name] = state.GetType().GetField(name, Flags)!.GetValue(state);
            output["status"] = valid ? "SUCCESS" : "FAILURE"; output["writes"] = writes; output["snapshots"] = checkedSnapshots; output["warm_checks"] = warmChecks; output["counters"] = counters;
        }
        catch (Exception e) { output["status"] = "ERROR"; output["error"] = e.ToString(); output["writes"] = writes; }
        Console.WriteLine(JsonSerializer.Serialize(output));
    }
}
