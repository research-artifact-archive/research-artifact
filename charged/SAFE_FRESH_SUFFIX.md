# A safe replacement of an all-cached suffix

This newer supplement is outside the unchanged manuscript216. The [analytic proof](evidence/RESUMED_20260910_1617/safe_fresh_suffix_01/PROOF01.md) gives a sufficient transformation on any finite DAG of positive-work, persistent whole-kernel jobs, in the visible comparison-flag model. Every cheap/cached call captures the current identity and immediately prepares from it. No hidden write budget is observed.

After the same cheap phase, let k count observed cached mismatches, ell be protected completed work, and Omega be unfinished work. Fresh is allowed only if both ell+w_i<=Top_k and ell+Omega<=Top_(k+1). Otherwise immediate cached completion is safe. A forward invariant proves the same least protected-work curve and call cap; replaying the identical cheap prefix, including harmless writes, proves worst total body work never exceeds all-cached continuation. Independent-job least work curves are preserved by the existing lower bound. This does not claim least total work on arbitrary DAGs. The two guards preserve protection; the work comparison itself does not need them.

A compact min/max-ready instance uses priority queues, three scalars and sorted weight prefix sums, without compiling a policy tree. Its operation counts are analytic; no native timing improvement is measured. Stage55 `safe-fresh-suffix` replays the [fixed protocol](evidence/RESUMED_20260910_1617/safe_fresh_suffix_01/PROTOCOL01.md), comparing every stable output byte-for-byte and checking the unchanged separate interpreter.

All714 paired roots and22,583 paths are retained. Of these,711 small roots overlap earlier studies; two are previously observed positive examples; one is a deliberately constructed safety control. Only the two preselected examples improve strictly, and the other712 have equal work curves. On the six-job root, B7 work decreases from782 to752; on the four-job observation root the final plateau decreases from21 to20. These are not independent or representative populations. A faulty control omitting the second guard produces L12>Top_2=11 on a chain with works1,1,10.

The [raw outcomes](evidence/RESUMED_20260910_1617/safe_fresh_suffix_01/ROWS01.json), [all paths](evidence/RESUMED_20260910_1617/safe_fresh_suffix_01/PATHS01.jsonl), [strict cases](evidence/RESUMED_20260910_1617/safe_fresh_suffix_01/STRICT01.json), and [unsafe control](evidence/RESUMED_20260910_1617/safe_fresh_suffix_01/CONTROL01.json) support finite corroboration, not the proof or unrestricted optimality. The particular six-job rule followed ordinary-model author consultation; the general invariant and work argument were developed separately. No independent formal certification, native run, human outcome, acceptance verdict or manuscript adoption is claimed.

Run from the release root:

```sh
python3 -B charged/reproduce.py safe-fresh-suffix --out work/safe-suffix --timeout 300
python3 -B charged/reproduce.py all --out work/all55 --timeout 300
```
