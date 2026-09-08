# Common-ratio adaptive-order witness

This author derivation explains the selected result without enumerating twenty
orders. A read-only author helper proposed the argument; the parent checked its
recurrences and lower-bound cases. It is not a mechanical or blind proof audit.

Let c=(8,2,4,2,6), p=3c/2, E={0→1,1→3}, and B=4. All following values exclude
normal work22. Put T={0,1,3,4}. Once0 completes, order1,3,4 is cost-compatible
and optimal for all budgets. The fixed-order recurrence is

    R[p,c](f)(0)=0
    R[p,c](f)(b)=min(p+f(b), max(f(b),c+R[p,c](f)(b-1))).

It gives the following values at budgets0,1,2,3,4:

| Residual/order | 0 | 1 | 2 | 3 | 4 |
|---|---:|---:|---:|---:|---:|
| Chain0,1,3: C |0|8|16|18|18|
| Optimal1,3,4: H |0|6|9|11|13|
| Fixed0,1,3,4: R[12,8]H |0|8|16|23|25|
| Fixed4,0,1,3: R[9,6]C |0|8|16|22|27|
| Adaptive T |0|8|16|22|25|

For T, the only ready jobs are0 and4. At budget3, its protected0/protected4/
fast0/fast4 action values are23,27,24,22; at budget4 they are25,27,30,28.
The earlier entries follow the same recurrence. Thus success of job2 with
remaining budget4 calls for protecting0, while remaining budget3 calls for
fast4 before0.

An adaptive policy first runs2 fast until success, then optimally handles T.
If2 fails k times, k=0..4, its excess is

    4k+V(T,4-k) = (25,26,24,20,16).

This proves V(J,4)≤26. Subset monotonicity gives V(J,3)≥V(T,3)=22, so initial
fast choices0,2,4 have lower bounds30,26,28. Initial protected choices have
lower bounds28,31,27: removing0 leaves the cost-compatible set{1,2,3,4}, whose
budget4 value is16; removing2 leaves T with value25; removing4 retains chain C
with value18. Every initial action therefore costs at least26, proving equality.

Now restrict to an initially fixed completion order of retry macros, while
allowing modes to adapt. Orders beginning0 cost at least28; those beginning4
cost at least27. If an order begins2, its next job is0 or4.

* If4 follows2, Nature can let2 complete with no failure, leaving the unique
  suffix4,0,1,3 at budget4 with value27. Protecting2 adds nonnegative premium.
* If0 follows2, every suffix beginning0 at budget3 costs at least23: immediate
  protection costs at least12+H(3)=23; fast0's failure costs at least8+V(T,2)=24.
  Immediate protection of2 costs at least6+V(T,4)=31. If2 is first tried fast,
  Nature fails it once, then permits its completion without further failures.
  The suffix starts with budget3, so this branch costs at least4+23=27.
  Protecting2 after that failure can only add a nonnegative cost.

Order2,4,0,1,3 attains27. Its child profile increments through budget4 are
8,8,6,5, all at least c2=4. The suffix-deficit identity therefore leaves these
values unchanged when prefixing2. Hence F(J,4)=27, and total values are48/49.

Uniform positive scaling preserves these recurrences and choices; integer
scalings give an infinite family with the same relative gap1/49. This proves
existence with five jobs, not minimality under common pricing or a maximum gap.

The 3,625-state complete-primitive graph and746 native paths are separate
selected checks recorded alongside this derivation. Common p/c restricts the
existing declared weighted-work metric; it does not calibrate elapsed time.
