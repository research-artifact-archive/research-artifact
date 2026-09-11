# Recheck: the universal zero-protection contract also bounds early failed calls

This is an additional author argument within the assigned audit. It was identified after the first report draft, which is preserved unchanged as `REPORT_DRAFT01_BEFORE_EARLY_Q_RECHECK.md`. No original derivation is edited. This is not an experiment or an independently certified new theorem.

## Claim and exact premises

Use exactly `V_r`, the positive whole-kernel jobs and completing-call table of frozen I11 manuscript232. At any reachable prefix with `d<=r` actual writes and at least one unfinished job, let `F` be the number of failed cheap calls, including already-stale failures. Then `F<=d`. In particular, every complete execution in `E_B` for `B<=r` has `Q<=n+B`.

The argument requires membership in `V_r`, including `L=0` against every unconditionally `r`-capped environment. It is not true merely from the universal `Q<=n+r` completion promise without optimal protection.

## Continuation contradiction

Suppose such a prefix instead has `F>d`. Its prefix already satisfies `L=0` by the realized-prefix capping lemma. Replay this finite prefix at its recorded gates, then put a fresh own-key identity at every subsequent selected comparison while fewer than `r` writes have been used in total. Put no write at fresh calls. The replay has `d` writes and the continuation is unconditionally capped at total `r`, including off the recorded history; after the cap it writes nothing. This is one environment in `E_r`.

Before the remaining `r-d` writes have been consumed, a completing fresh call or a mismatching cached call would perform positive protected work, contradicting the `L=0` promise in `E_r`. Every selected comparison that receives a fresh write invalidates all retained records and therefore either is an impermissible protected completion or is a failed cheap call. Already-stale cheap calls also consume the call allowance; they do not create an escape. Finite selected operations and completion admissibility prevent infinite inspection/preparation/local-action postponement.

If `d<r`, consuming all remaining writes without any protected completion requires at least `r-d` additional cheap failures. But then the total failed calls is at least `F+(r-d)>r`, incompatible with eventual `n` mandatory completing calls under `Q<=n+r`. The failure cap is exceeded no later than that point, while the environment is still `r`-capped. No unprotected comparison completion can occur before the write supply is exhausted, because its gate receives a fresh identity.

If `d=r`, the assumption already gives `F>r`, immediately incompatible with completion and the call cap. Thus `F>d` is impossible.

For a completed execution with `d_final<=B<=r`, a hypothetical `F_final>d_final` also occurs before its last completing call: all failures precede some remaining completion, and at the prefix immediately after its last failure `d_prefix<=d_final<F_final`. The preceding contradiction applies. Hence `F_final<=d_final<=B` and `Q=n+F_final<=n+B`.

## Effect on DERIVATION02

The maximum-job truncated witness already has `B` useful cheap failures. The preceding bound therefore yields exactly `Q=n+B` on that witness. Its weaker statement `Q>=n+B` remains correct and is sufficient for all monotone and scalar conclusions. However, the claimed possibility of extra stale failures **on that truncated witness after its B useful failures** cannot justify strict inequality under `V_r`.

A program may use a stale failure in a different history when actual writes already provide sufficient slack; the statement above only rules out total failures exceeding actual writes while `d<=r`. Thus it should not be paraphrased as a ban on every stale call. The mistake is importing the larger call-admissible class's possible wasted-call behavior into this particular universally zero-protected prefix.

The user's reported correction can safely remain as the conservative lower inequality. This audit does not validate that the old equality was false. The initial report's wording that the correction was “necessary,” and its unqualified assertion of extra failures after truncation, are withdrawn in the final report. The main joint-objective and sharp-factor conclusions are unaffected.
