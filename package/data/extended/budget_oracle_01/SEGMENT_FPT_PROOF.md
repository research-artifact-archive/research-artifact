# Price-independent segment bound and FPT all-budget compilation

Author-side mathematical derivation, checked against the current curve code.
The accompanying SEGMENT_FPT_AUTHOR_RAW.json is a read-only author helper's
assessment, not independent blind review or a mechanical proof. This argument
uses the established concavity/reflection specialization and does not claim
that the reflected recurrence itself is new.

Let r(f) count maximal affine pieces of the linear interpolant of the integer
samples, including its infinite final piece. For m profiles f_j, their common
continuous partition has at most sum_j r(f_j) intervals. The lower envelope of
m lines on one interval has at most m pieces: a given line is minimal on the
intersection of half intervals, hence on an interval. Across all intervals the
continuous envelope has L <= m sum_j r(f_j) pieces. Sampling at integers and
linearly interpolating introduces at most one extra bridging unit interval
per noninteger breakpoint, hence at most 2L-1 pieces. Therefore

    r(min_j f_j on integers) <= 2m sum_j r(f_j).

This bounds each intermediate protected envelope directly by the original
children. Sequential binary minima give the same integer samples; normalization
retains their unique maximal affine representation. One must not multiply the
binary bound at each fold and pretend the resulting larger bound is necessary.

For a residual set of size k, put R_0=1. Every child has at most R_{k-1} pieces.
The protected envelope h has at most 2k^2 R_{k-1} pieces. The slope-floor profile
D retains a prefix of its child g and replaces the rest with one segment, so
r(D) <= R_{k-1}. A final binary minimum gives

    r(V) <= 4(r(h)+r(D)) <= 12 k^2 R_{k-1}.

Thus R_k=12^k(k!)^2 suffices. There are at most 2^n root-reachable upsets, and
K <= 24^n(n!)^2 bounds the total emitted pieces. This is deliberately loose;
it proves neither a linear root bound nor good practical behavior for large n.

For bit costs, put P=sum_i p_i and C=max(1,max_i c_i), with C=1 for the empty
input. Classical separable lower bounds attain P by sum_i ceil(p_i/c_i)<=P;
the always-protected upper bound is P. Completed V curves therefore saturate
by P. Their nonnegative anchor values, slopes, starts and integer line
intercepts are bounded by P. Intercepts are nonnegative by concavity and a
nonnegative origin, and do not exceed the value at the segment start.
Shifted children and their partial lower envelopes are likewise nonnegative,
concave and bounded by the residual premium sum.

The intermediate D has an unbounded positive tail. Its starts and anchor values
are inherited from g, and its slopes are at most max(P,C). If its new tail
starts at tau, its intercept g(tau)-c*tau is nonnegative because all earlier
slopes exceed c, and is at most P. Thus every line passed to lower has an
integer intercept in [0,P]. A nonparallel crossing x=(a2-a1)/(s1-s2) has |x|<=P;
nonnegative rounded candidates also lie at most P. Evaluated intermediate
values need O(log(P+1)+log(C+1)) bits, including the unbounded-tail line at these
finite coordinates. No rational denominators propagate between minima.
The case P=0 is the single zero segment throughout.

The compiler's binary minimum and normalization are polynomial in their
encoded profile lengths. Enumerating upsets and all action identities adds
at most 2^n times a polynomial in n. The structural checker enumerates the same
upsets and pieces. The Bellman checker refines O(nR_n) intervals per upset with
O(n^2) affine crossings per interval and evaluates encoded profiles at those
points. Finite intervals and the previous-budget shift keep checked coordinates
at most P+1; all candidate slopes are zero on the final infinite interval.
Consequently construction, serialization and these checks on emitted
certificates take f(n)*poly(lambda) bit time for binary input length lambda.
A loose profile-operation bound is 2^n*poly(n)*R_n^2 times polynomial bit cost.
For arbitrary supplied certificates, verification must also charge their
input length; this claim is not a size-independent promise for malicious files.

Scope: the all-budget compiler/checker, not scalar/primitive evaluation harnesses.
The separate point oracle has an unmemoized call bound involving
(n+2*ceil(log2(B+1))+3)^n; that bound is polynomial in log B for fixed n but is
not by itself FPT in n under the uniform f(n)*poly(lambda) definition.
