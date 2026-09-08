# Distribution updates

The public release preserves its scientific snapshot and earlier commits. These updates do not add scientific samples, change theorem/proof blocks, or replace historical outcomes.

| Commit | Distribution change |
|---|---|
| `eae2a0efee262368dc56c32189d4af48480bc4d9` | Initial anonymous publication of the frozen version-5 package, preparation provenance, earlier scale histories, and table reconstruction. |
| `e0e011023c0591bbbf422390ad8d29785ad0023f` | Completed the missing reported independent comparisons, charged-acquisition counterexamples, and constructive-gap search. Added theorem/checker navigation and the existing work-cap example. This is the fixed evidence commit cited by the revised paper. |
| `96a5f116c409fd0e9197289a8ffea4ecb3c8d09e` | Added the revised anonymous manuscript and source outside the byte-preserved package. |

The following documentation clarification keeps the same manuscript and scientific payload: the exact range comparison expands a subtree when one front is a run, and chooses the longer subtree when both fronts are subtrees. The code and paper already made this distinction. Historical README working-directory instructions are also clarified at the public entry point.

Author-side reproduction used unauthenticated HTTPS checkouts on the original workstation. All six standard full entry points (`reproduce.py`, `reproduce_extended.py`, `reproduce_oracle.py`, `reproduce_current.py`, `reproduce_latest.py`, and `reproduce_basis.py`) completed successfully. Optional `--with-cp` solver invocations were not included. Saved benchmark policies and complete original outcome partitions were inspected; historical timeout experiments were not rerun. This is not independent third-party artifact evaluation or a fresh performance comparison.
