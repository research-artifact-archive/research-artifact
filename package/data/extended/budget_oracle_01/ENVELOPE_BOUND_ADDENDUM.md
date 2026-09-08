# A tighter supporting-line bound (author derivation)

The previous 12^n(n!)^2 bound remains correct and is used in author build36.
It can be strengthened without changing the FPT classification or implementation.

Every affine segment line of a continuous concave profile extends to a global
majorant on [0,infinity), and some segment line attains the profile at each point.
Thus the minimum of m concave profiles is the lower envelope of the union of all
their supporting lines. Each line's minimizing region is an interval, giving at
most sum_j r_j continuous pieces. Vertical shifts and the concave unbounded D
tail preserve this property; boundedness is not required.

Integer sampling/interpolation adds at most one bridging unit interval per
noninteger breakpoint. Therefore r(integer minimum) <= 2*sum_j r_j. Partial
sequential minima preserve the same integer samples as a direct original-child
minimum, so there is no extra doubling at each fold.

For a k-job residual set, r(h)<=2kR_{k-1}, r(D)<=R_{k-1}, and
r(V)<=2(r(h)+r(D))<=(4k+2)R_{k-1}<=6kR_{k-1}. With R_0=1 this gives
R_n=6^n*n! and total emitted pieces <=12^n*n!. The earlier bit argument applies.

A bounded read-only author helper checked this argument and found it sound.
This is not independent blind review, novelty certification, or a measured speedup.
No new experiment was performed; the current implementation/checker are unchanged.
On the 45 successful all-budget benchmark units, constructor/serialization totals
3.541944792 seconds and reload/check/query 14.659079580 seconds. A faster envelope
constructor alone is therefore not established as the most useful next experiment.
