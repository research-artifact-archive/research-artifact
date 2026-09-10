# First actual-Linux matrix: results and scope

Linux v6.12 (adc218676eef25575469234709c2d87185ca223a), ARM64, two guest CPUs, QEMU TCG. Kernel configuration enables lock dependency checking and atomic-sleep diagnostics. The fixed matrix ran once at 2026-09-11 00:29 JST. Build/config/guest execution took 19.830 seconds total; KUnit reports 10.284 seconds running the guest. These times describe experimental cost only.

All **1,536 valid rows** returned the expected full path or ENAMETOOLONG: 760 successful paths and 776 expected overflows. All **four deliberately defective candidate variants** were detected. The unfiltered serial log contains all 1,540 rows and 2,068 individual traversal records. Offline recomputation of fixture paths, hashes, returned offsets, actual writer counts, all counter sums and every resource predicate reports no discrepancy. There are no scanned kernel lock/RCU/panic diagnostics. The longest structured record is 473 characters. The full log SHA-256 is da8f2861cb4866a730caccba35511a9b2b3f420c23b07fd7ab96afc3939ba7ec.

The four defects have distinct witnesses: accepting the second buffer without checking its sequence returns a stale path after two writes; reusing the first sequence returns the correct path but performs protected traversal work after only one in-call write; omitting buffer restoration retains an obsolete overflow after the path shrinks; and returning unvalidated overflow rejects a legal '/aaaa' path after a mixed '/bb/aaaa' traversal. None is a claim about a bug in unmodified Linux.

## Concrete policy difference

For initial '/driver/cache/entry/leaf', capacity 4096, a write after the first traversal moves the query to '/alternate'. Both upstream and cached fallback have Q=2 and T=41. Upstream has L_T=12; cached fallback has L_T=0. Both acquire the exclusive-reader lock once. Thus the removed work is the traversal inside that lock, not the lock acquisition or all protected instructions. The always-locked policy has T=L_T=12 and Q=1, exhibiting a different resource tradeoff.

With a second write requested before the final protected operation, both upstream and cached fallback experience B=2 and return the original longer path. Upstream has (T,L_T)=(58,29); cached fallback has (70,29). The extra outside traversal then increases total work without reducing protected traversal work. This adverse result is retained. Always-locked and snapshot finish before this schedule's second hook, so they have B=1; their values must not be compared as if they had the same two-write execution.

The comparison is not restricted to related writes: 192 valid rows include actual unrelated global writer sections. These invalidate the real rename sequence and consume the B used in the bounds, even though the returned path stays the same. This exposes false-positive invalidation rather than assuming a per-path version counter.

## Stronger snapshot operation and boundary cases

Snapshot64 preallocates 3,584 bytes at capacity 4096 and uses actual `take_dentry_name_snapshot`/`release_dentry_name_snapshot`. On the short first-write case it materializes with T=12 and L_T=0, but additionally performs one protected snapshot step, one dentry-lock snapshot operation, and ten protected inline-copy bytes. In the clean long-name family it snapshots four components with 40 protected inline-copy bytes and three external-name reference increments, followed by three releases outside. Those costs are separate from its body-only L_T. It is a stronger interface outside the paper's whole-kernel lower-bound class, so the matrix supports no optimality claim against it.

Five snapshot rows exhaust its 64-slot workspace and use the specified protected-body fallback. For the clean 80-component path, body T=L_T=401 is accompanied by 65 protected capture steps, 64 discarded snapshots and 256 protected inline-copy bytes. All references are released. This finite-workspace fallback is part of this comparison implementation, not a lower bound against an arbitrarily sized immutable-snapshot implementation.

There is no observed nofault-copy failure and no injected allocation failure. Copy-fault and allocation-failure fallback branches are source obligations, not tested coverage. Paths, names and writer schedules are author fixtures on actual kernel dentries; the matrix does not measure workload frequency, deployed filesystems, native contention, elapsed speedup or application SLA. Read-only source inspection of writer participation and snapshot lifetime is being completed separately; matrix agreement alone is not proof for every Linux caller.

## What transfers to the theory

SOURCE_REFINEMENT01.md establishes a conditional single-job upper-bound refinement for the participating-writer source scope. With C=capacity−1, T counts one traversal invocation plus attempted names, requested-copy bytes, fault-fill bytes and successful slashes, and each traversal has T≤3C+2. Cached fallback gives Q≤2, at most 1+min(B,2) traversals, and L_T=0 for B≤1. These are chosen source-event resources; waiting, RCU, guard instructions, metadata and postambles remain outside T. The generic ceiling 12,287 for capacity 4096 is much larger than the short-path observations; it is not a tight native cost calibration.

Linux returns a private path buffer without updating the live dentry graph. It therefore does not instantiate the paper's entire persistent-update/observation contract, and no whole-program minimax lower bound, multi-job frontier or output-erasure theorem is transferred. The concrete result is a bounded source traversal and a tested change in where traversal work occurs. Whether that scope supplies sufficient practical importance for the full paper remains an independent assessment.

Files: PROTOCOL01.md, INPUTS01.json, implementation01/, SOURCE_PATCH_RECEIPT01.json, KERNEL_MATRIX_START01.json, KERNEL_MATRIX_COMPLETION01.json, KERNEL_MATRIX01.test.log, MATRIX_VALIDATION01.json and MATRIX_JOINED01.json. The original code, full source archive and infrastructure receipts are retained. No scientific row was rerun or excluded.
