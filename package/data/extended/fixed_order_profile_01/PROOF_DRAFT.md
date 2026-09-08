# Fixed-order encoded profiles: author mathematical derivation

This is a corollary of the inherited concave cap formula, not a novelty or
implementation-performance claim. A bounded read-only author helper checked
the argument; no experiment or implementation has yet been run for this design.

For a suffix f with f(0)=0, nonnegative decreasing integer slopes s_b and a
constant final tail, let A_b=sum_{j<=b}(c-s_j)_+. Then Rf(b)=f(b)+min(p,A_b).
For p>0, let a be the first b with s_b<c and t the first b with A_b>=p.
Both exist. New slopes are s_b before a, c for a<=b<t,
s_t+p-A_{t-1} at b=t, and s_b after t. The crossing slope is in (s_t,c]; exact
divisibility merges it into the plateau. For p=0, Rf=f and threshold is zero.

The modification begins at an existing slope-run boundary. At its end an old
run can split, but that run survives only in the unchanged suffix. Retained
original pieces contribute at most r(f), while plateau and crossing contribute
at most two. Thus r(Rf)<=r(f)+2 including the zero tail. The increase by two is
possible: slopes 2,2,2,1,0,... with c=5,p=4 become 5,3,2,1,0,....
Hence a length-k suffix has at most2k+1 pieces; all suffixes total <=(n+1)^2.

A streaming constructor copies runs with slope>=c, then consumes premium through
runs h<c with deficit capacity m(c-h). At the crossing run, divmod(remaining,c-h)
gives full plateau length and at most one partial step. Copy the untouched
remainder and merge equals. Cost per suffix is O(r(f)) arithmetic operations,
thus O(n²) total, independent of numerical price/B. Price bit lengths remain
costs. Root, order and thresholds have O(n) entries; all suffix certificates O(n²).

Protection is strictly suboptimal before t and attains the value thereafter,
without sorted costs. This verifies the threshold rule for a prescribed retry
macro order. For a chain the order is forced; a new restriction theorem for
arbitrary retained-preparation programs with prescribed commit order is NOT
established. The sorted-cost shared-root suffix-cap identity cannot be reused.

A separate O(n²) checker can stream the merged boundaries of v(b), f(b),
v(b-1), and the threshold. Each interval has only four affine expressions in
v(b)=min(p+f(b),max(f(b),c+v(b-1))), hence constantly many crossings. Check floor/
ceiling neighbors/endpoints, tail, shape and selected threshold action. Streaming
cost is O(r(v)+r(f)) per suffix. Arbitrary certificates also charge supplied length.

Current generic curve/lookup/check routines repeatedly scan profiles and do not
establish this O(n²) implementation bound. This document describes an unimplemented
streaming specialization. Existing research records and adverse outcomes remain.
