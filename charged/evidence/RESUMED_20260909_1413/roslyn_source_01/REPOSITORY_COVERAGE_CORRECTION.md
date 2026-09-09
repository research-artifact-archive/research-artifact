# Post-outcome coverage clarification; no source rerun

Author-side read-only check identified description gaps; no observed incorrect source outcome or count equation. Preserve all plans/checker receipts exactly, including their over-broad scope wording. This supplement corrects interpretation:

- The native harness checks all 4,016 untouched **SourceText object references**, not metadata, document versions or project state. The Python checker verifies the reported denominator.
- Notification Document text content and asynchronous event document count/order are checked. WorkspaceChangeEventArgs.OldSolution/NewSolution payloads are not recorded or checked. Do not claim complete event-payload correctness.
- Q counts foreground semaphore admissions; B background-writer admissions are excluded. Fixed first-B-prelock-opportunity scheduling yields equal writer totals across modes, not identical intermediate observations/interleavings: original may finish multiple failures before a target publication while capped modes advance earlier.
- Four repository and sixteen authored-grid unmodified-library controls have B=0 and no source trace/mutation reconstruction. Their prior generic normal_trace_scope wording overstates actual baseline coverage. They establish quiet semantic smoke behavior only.
- Pristine source loading, hash verification and target-comment string preparation precede whole-unit timing. Foreground timing includes target SourceText creation, hooks, and synchronous writer waiting; background strings/SourceText are created on the writer. Whole-unit timing additionally includes workspace setup, full identity checks, event waiting and disposal. No whole-process timing benefit is inferred.

The fixed measurement plan was written before observations. These are explicit post-outcome clarifications, not revised preregistration. The main paper uses the narrower descriptions. Full native event-payload/reentrant-host equivalence remains unestablished.
