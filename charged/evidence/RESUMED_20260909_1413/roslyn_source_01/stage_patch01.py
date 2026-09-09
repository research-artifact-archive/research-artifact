from pathlib import Path
import datetime,difflib,hashlib,json,subprocess
D=Path(__file__).resolve().parent;C=Path('<AUTHOR_HOME>/Research/roslyn_build_20260909');R=C/'source/roslyn-6c4a46a31302167b425d5e0a31ea83c9a9aa1d09';P=R/'src/Workspaces/Core/Portable/Workspace/Workspace.cs';O=D/'patch01';O.mkdir()
assert json.loads((D/'baseline_build02/RESULT.json').read_text())['status']=='SUCCESS'
before=P.read_bytes();assert hashlib.sha256(before).hexdigest()=='c12c88c275dba6fd96a708f039f9001be85d513bf823d760ba006e8b53c5c61a'
(O/'Workspace.original.cs').write_bytes(before)
subprocess.run(['/bin/cp','-cR',str(R/'artifacts/bin'),str(C/'baseline_bin')],check=True,timeout=60)
s=before.decode('utf-8-sig')
def replace(a,b):
 global s
 assert s.count(a)==1,(s.count(a),a[:80]);s=s.replace(a,b)
replace('    private readonly SemaphoreSlim _serializationLock = new(initialCount: 1);','''    private readonly SemaphoreSlim _serializationLock = new(initialCount: 1);

    // Author research instrumentation. Only explicit SourceText updates on OwnerThreadId opt in.
    // Other updates retain the original path. This is not an upstream public API.
    internal sealed class DocumentRetryStudyState
    {
        public int OwnerThreadId;
        public int Mode; // -1 original optimistic; 0 two modes; 1 cached completion
        public int Remaining;
        public long Calls, PreparedOutside, PreparedInside, Mismatches, CheapFailures;
        public Action<string, Solution>? Hook;
        public void Step(string name, Solution snapshot) => Hook?.Invoke(name, snapshot);
    }

    internal DocumentRetryStudyState? DocumentRetryStudy;

    private DocumentRetryStudyState? CurrentDocumentRetryStudy
        => DocumentRetryStudy?.OwnerThreadId == Environment.CurrentManagedThreadId ? DocumentRetryStudy : null;''')
replace('''        Action<Solution, Solution, TData>? onAfterUpdate = null)
    {
#pragma warning disable CA2012''','''        Action<Solution, Solution, TData>? onAfterUpdate = null,
        DocumentRetryStudyState? retryStudy = null)
    {
#pragma warning disable CA2012''')
replace('''            onAfterUpdate,
            CancellationToken.None);

        return valueTask.VerifyCompleted("Task must have completed synchronously as we passed 'useAsync: false' to SetCurrentSolutionAsync");
#pragma warning restore CA2012 // Use ValueTasks correctly
    }

    /// <inheritdoc''','''            onAfterUpdate,
            CancellationToken.None,
            retryStudy);

        return valueTask.VerifyCompleted("Task must have completed synchronously as we passed 'useAsync: false' to SetCurrentSolutionAsync");
#pragma warning restore CA2012 // Use ValueTasks correctly
    }

    /// <inheritdoc''')
replace('''        CancellationToken cancellationToken)
    {
        Contract.ThrowIfNull(transformation);''','''        CancellationToken cancellationToken,
        DocumentRetryStudyState? retryStudy = null)
    {
        Contract.ThrowIfNull(transformation);
        if (retryStudy is not null && (retryStudy.Mode < -1 || retryStudy.Mode > 1 || retryStudy.Remaining < 0))
            throw new ArgumentOutOfRangeException(nameof(retryStudy));

        Solution Transform(Solution input, bool inside)
        {
            if (retryStudy is not null)
            {
                if (inside) retryStudy.PreparedInside++; else retryStudy.PreparedOutside++;
                retryStudy.Step(inside ? "kernel_inside_begin" : "kernel_outside_begin", input);
            }
            var result = transformation(input, data);
            retryStudy?.Step(inside ? "kernel_inside_end" : "kernel_outside_end", result);
            return result;
        }''')
replace('''            while (true)
            {
                // Run the transformation outside of the lock as it should not be making any state changes to us.
                var newSolution = transformation(oldSolution, data);

                // if it did nothing, then no need to proceed.
                if (oldSolution == newSolution)
                    return (oldSolution, newSolution);

                // Now, take the lock and try to update our internal state.
                using (useAsync ? await _serializationLock.DisposableWaitAsync(cancellationToken).ConfigureAwait(false) : _serializationLock.DisposableWait(cancellationToken))
                {
                    if (_latestSolution != oldSolution)
                    {
                        // something else snuck in and wrote to _latestSolution. Restart and try again.
                        oldSolution = _latestSolution;
                        continue;
                    }

                    newSolution = newSolution.WithNewWorkspaceFrom(oldSolution);''','''            while (true)
            {
                var freshProtected = retryStudy is { Mode: 0, Remaining: 0 };
                // The ordinary path still transforms outside protection. The scoped two-mode
                // path defers that transformation until after acquiring the source semaphore.
                var newSolution = freshProtected ? oldSolution : Transform(oldSolution, inside: false);

                // Preserve the original early no-op behavior.
                if (!freshProtected && oldSolution == newSolution)
                {
                    retryStudy?.Step("return_noop", newSolution);
                    return (oldSolution, newSolution);
                }

                retryStudy?.Step("before_lock", oldSolution);
                using (useAsync ? await _serializationLock.DisposableWaitAsync(cancellationToken).ConfigureAwait(false) : _serializationLock.DisposableWait(cancellationToken))
                {
                    if (retryStudy is not null) retryStudy.Calls++;
                    retryStudy?.Step("lock_enter", _latestSolution);
                    if (freshProtected)
                    {
                        oldSolution = _latestSolution;
                        newSolution = Transform(oldSolution, inside: true);
                    }
                    else if (_latestSolution != oldSolution)
                    {
                        oldSolution = _latestSolution;
                        if (retryStudy is not null) retryStudy.Mismatches++;
                        if (retryStudy is { Mode: 1, Remaining: 0 })
                        {
                            newSolution = Transform(oldSolution, inside: true);
                        }
                        else
                        {
                            if (retryStudy is not null)
                            {
                                retryStudy.CheapFailures++;
                                if (retryStudy.Mode >= 0) retryStudy.Remaining--;
                                retryStudy.Step("cheap_failure", oldSolution);
                            }
                            continue;
                        }
                    }

                    // Recomputing against the latest snapshot may itself be a no-op.
                    if (oldSolution == newSolution)
                    {
                        retryStudy?.Step("return_noop", newSolution);
                        return (oldSolution, newSolution);
                    }

                    newSolution = newSolution.WithNewWorkspaceFrom(oldSolution);''')
replace('''                    onAfterUpdate?.Invoke(oldSolution, newSolution, data);
                    return (oldSolution, newSolution);''','''                    onAfterUpdate?.Invoke(oldSolution, newSolution, data);
                    retryStudy?.Step("return_changed", newSolution);
                    return (oldSolution, newSolution);''')
replace('''            WorkspaceChangeKind.DocumentChanged,
            isCodeDocument: true,
            requireDocumentPresent);
    }

    /// <summary>
    /// Call this method when the text of an additional document''','''            WorkspaceChangeKind.DocumentChanged,
            isCodeDocument: true,
            requireDocumentPresent,
            retryStudy: CurrentDocumentRetryStudy);
    }

    /// <summary>
    /// Call this method when the text of an additional document''')
replace('''        bool isCodeDocument,
        bool requireDocumentPresent)
    {
        // Data that is updated''','''        bool isCodeDocument,
        bool requireDocumentPresent,
        DocumentRetryStudyState? retryStudy = null)
    {
        // Data that is updated''')
replace('''                        documentId: updatedDocumentInfo);
                }
            });''','''                        documentId: updatedDocumentInfo);
                }
            },
            retryStudy: retryStudy);''')
after=b'\xef\xbb\xbf'+s.encode();P.write_bytes(after);(O/'Workspace.patched.cs').write_bytes(after)
(O/'Workspace.patch').write_text(''.join(difflib.unified_diff(before.decode('utf-8-sig').splitlines(True),s.splitlines(True),fromfile='a/src/Workspaces/Core/Portable/Workspace/Workspace.cs',tofile='b/src/Workspaces/Core/Portable/Workspace/Workspace.cs')))
(O/'RECEIPT.json').write_text(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'before_sha256':hashlib.sha256(before).hexdigest(),'after_sha256':hashlib.sha256(after).hexdigest(),'source_files_changed':1,'baseline_build':'baseline_build02','baseline_binaries':str(C/'baseline_bin'),'scope':'Author prototype, SourceText-only explicit owner-thread context; not production-ready; no measurements yet'},indent=2)+'\n')
print(json.dumps({'patched_file':str(P),'bytes':len(after),'sha256':hashlib.sha256(after).hexdigest()}))
