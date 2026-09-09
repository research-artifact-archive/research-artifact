# Proposed abort fixture rejected before execution

This directory contains staged, unexecuted derivative code, not experimental results or a valid fixed native protocol. No certificates/resources were emitted, and no native test was compiled or run. Its draft caps32,160 and hoped-for null-leaf abort were reviewed before execution in ../DEEPHAVEN_RESOURCE_AUTHOR_REPORT_10.md.

The source review refutes the intended mechanism: leaf directives are removed by linkedDirectiveInvalid before recursive traversal, so switching from ExpandAll to explicit Expand does not reach the desired native consistency check. The tighter source-derived complete/prefix cap would be K32,V128, with only16 recursive node entries. The staged files retain their original draft values as preparation history. They are not used by the checkout or adopted in the paper.

This outcome-informed exploratory proposal is stopped because it cannot answer the missing-abort question. The216 completed cells in deephaven_prefix_import_02 retain zero aborted callbacks. Future early-validation instrumentation would be a deliberate semantic-preserving optimization to test, not evidence that the unchanged fixture naturally exercised native abort paths.
