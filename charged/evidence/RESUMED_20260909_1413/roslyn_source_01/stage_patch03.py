from pathlib import Path
import datetime,difflib,hashlib,json
D=Path(__file__).resolve().parent;C=Path('<AUTHOR_HOME>/Research/roslyn_build_20260909');P=C/'source/roslyn-6c4a46a31302167b425d5e0a31ea83c9a9aa1d09/src/Workspaces/Core/Portable/Workspace/Workspace.cs';O=D/'patch03';O.mkdir()
before=P.read_bytes();assert before==(D/'patch02/Workspace.patched.cs').read_bytes();s=before.decode('utf-8-sig')
def replace(a,b):
 global s
 assert s.count(a)==1,(s.count(a),a[:100]);s=s.replace(a,b)
replace('''        DocumentRetryStudyState? retryStudy = null)
    {
#pragma warning disable CA2012''','''        DocumentRetryStudyState? retryStudy = null,
        Func<Solution, TData, bool>? isNoOp = null)
    {
#pragma warning disable CA2012''')
replace('''            CancellationToken.None,
            retryStudy);''','''            CancellationToken.None,
            retryStudy,
            isNoOp);''')
replace('''        DocumentRetryStudyState? retryStudy = null)
    {
        Contract.ThrowIfNull(transformation);''','''        DocumentRetryStudyState? retryStudy = null,
        Func<Solution, TData, bool>? isNoOp = null)
    {
        Contract.ThrowIfNull(transformation);''')
replace('''                var freshProtected = retryStudy is { Mode: 0, Remaining: 0 };
                // The ordinary path''','''                var freshProtected = retryStudy is { Mode: 0, Remaining: 0 };
                // Preserve the source's known same-text no-op without reacquiring the
                // non-reentrant semaphore from a notification callback. This predicate is
                // supplied only by the SourceText path, after EnsureEventListeners above.
                if (freshProtected && isNoOp?.Invoke(oldSolution, data) == true)
                {
                    retryStudy?.Step("return_noop", oldSolution);
                    return (oldSolution, oldSolution);
                }
                // The ordinary path''')
replace('''            retryStudy: CurrentDocumentRetryStudy);''','''            retryStudy: CurrentDocumentRetryStudy,
            isNoOp: static (solution, id, textAndMode) =>
                (textAndMode.mode == PreservationMode.PreserveIdentity || textAndMode.mode == PreservationMode.PreserveValue) &&
                solution.GetDocument(id) is { } document && document.TryGetText(out var oldText) &&
                ReferenceEquals(oldText, textAndMode.newText));''')
replace('''        DocumentRetryStudyState? retryStudy = null)
    {
        // Data that is updated''','''        DocumentRetryStudyState? retryStudy = null,
        Func<Solution, DocumentId, TArg, bool>? isNoOp = null)
    {
        // Data that is updated''')
replace('''data: (@this: this, documentId, arg, getDocumentInSolution, updateSolutionWithText, changeKind, isCodeDocument, requireDocumentPresent, updatedDocumentIds),''','''data: (@this: this, documentId, arg, getDocumentInSolution, updateSolutionWithText, changeKind, isCodeDocument, requireDocumentPresent, updatedDocumentIds, isNoOp),''')
replace('''            retryStudy: retryStudy);''','''            retryStudy: retryStudy,
            isNoOp: static (solution, data) => data.isNoOp?.Invoke(solution, data.documentId, data.arg) == true);''')
after=b'\xef\xbb\xbf'+s.encode();P.write_bytes(after);(O/'Workspace.patched.cs').write_bytes(after)
original=(D/'patch01/Workspace.original.cs').read_text(encoding='utf-8-sig')
(O/'Workspace.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),s.splitlines(True),fromfile='a/src/Workspaces/Core/Portable/Workspace/Workspace.cs',tofile='b/src/Workspaces/Core/Portable/Workspace/Workspace.cs')))
(O/'RECEIPT.json').write_text(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'before_sha256':hashlib.sha256(before).hexdigest(),'after_sha256':hashlib.sha256(after).hexdigest(),'reason':'Observed patch02 two-mode same-SourceText callback reentry TIMEOUT; baseline/original/three succeeded. Restore a source-derived same-text predicate before two-mode protected acquisition, inside original listener/catch ordering.','source_basis':'SolutionState.WithDocumentText cached TryGetText/reference equality guard at lines994-999; valid PreservationMode only. Missing/not-cached/invalid inputs fall through.','old_failure':'reentry_outcomes01/two/RESULT.json','normal_old_measurements':'measurement01, immutable DLL snapshot measurement01_app','new_input_to_selector':'None: predicate certifies a semantic no-op, not B/weights/timing/exhaustion','scope':'Does not establish arbitrary reentrant-host safety; keeps variable/lazy work and VersionStamp side effects outside fixed-work correspondence'},indent=2)+'\n')
print(json.dumps({'patch03_sha256':hashlib.sha256(after).hexdigest(),'bytes':len(after)}))
