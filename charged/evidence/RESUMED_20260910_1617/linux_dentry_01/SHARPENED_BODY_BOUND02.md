# A sharper source-event ceiling, derived after matrix01

This is a post-matrix analytical improvement, not a changed preregistration, rerun, revised input, or replacement of the original 3C+2 pass predicate. The fixed protocol, first source, raw log and result remain unchanged.

For a single original __dentry_path loop let v be attempted names, c requested copy bytes, f fault-fill bytes, and s successful slash writes. Initialization/root postambles are outside this body. Every successful iteration has exactly one successful slash, and a failing iteration immediately breaks. Hence **v≤s+1**, which is stronger than bounding v by C+1 independently. Each failing copy fills at most its own requested length, so **f≤c**. Buffer monotonicity gives **c+s≤C**. Therefore

    T = 1+v+c+f+s ≤ 2+c+f+2s ≤ 2+2(c+s) ≤ 2C+2.

This holds for zero-length names, revisited parents, truncation and nofault-copy errors, within the original nonnegative observed-length and valid-buffer assumptions. The root has v=c=f=s=0 and T=1. C=0 can attempt a non-root name once and return overflow at T=2. There is no assertion that every native caller attains 2C+2, or that T counts all native instructions. A full-capacity failed copy would attain the scalar envelope, but it is not an observed matrix01 event and its reachability under a particular valid workload is not established.

Consequently the same conditional single-query candidate proof gives T_total≤(1+min(B,2))(2C+2) and L_T=0 at B≤1, L_T≤2C+2 otherwise. The requested-byte/fill/slash envelope remains 2C. At capacity4096 the sharpened T ceiling is8192, compared with the original12287. This is still loose for the short fixture, and it does not establish a native minimax result or a workload-specific tight bound.

SHARPENED_BOUND_CHECK02.json applies the new inequalities to every retained body record without executing the kernel again. That check is corroboration of the algebra and is explicitly post-outcome. In particular, matrix01 has no fault-fill events and cannot validate that source branch by observation.
