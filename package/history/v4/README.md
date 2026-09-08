# Retry-policy compiler: local reproduction package v4

This package accompanies author build42 of *Compiling Optimal Retry Policies
for Dependent Transformations*:18 body pages,20 total pages. It extends v3.1
with direct Bellman/policy sweep checking, common-protection-price exploration,
the selected five-job witness and its complete-primitive/Java validation.
It has not been publicly released or accepted by an artifact evaluation committee.

## Run

Use Python3.10+ with assertions enabled, without `-O`. The new Python stages
use the standard library; Java stages need JDK17+. Runtimes are not bundled.
Original experiments used Python3.10.9, with Python3.12.14 for the value-oracle
study, and OpenJDK17.0.19 on an Apple M2 with24GiB memory. Reproduction records
its own runtime and timings.

Run from this directory. Outputs must be new directories outside the package.

```sh
python3 -B reproduce_current.py verify --out /tmp/retry-v4-verify
python3 -B reproduce_current.py all --out /tmp/retry-v4-current
python3 -B reproduce.py all --out /tmp/retry-v4-core
python3 -B reproduce_extended.py all --out /tmp/retry-v4-extended
python3 -B reproduce_oracle.py all --out /tmp/retry-v4-oracle
```

`reproduce_current.py` has individual modes `algebra`, `certificates`,
`sweep_controls`, `sweep_bench`, `exposure1`, `exposure2`, `simplified`,
`uniform_semantic`, and `uniform_native`. `--java`/`--javac` select JDK binaries.
`--quick` reduces large development grids to their first/last16 inputs; it
does not reproduce full counts. Controls, saved benchmark scans and the746
selected native paths remain complete. Use these portable entry points;
historical study drivers retain original workspace and deadline assumptions.

| New replay stage | Full denominator | Original outcome |
|---|---:|---|
| Sweep affine identities, two coverage contracts each |83,125|all agree with integer enumeration|
| Prior complete ideal certificates |1,296|all accepted|
| Correct/malformed certificate controls |1/24|accept/reject|
| Saved larger ideal certificates |36|all accepted|
| First common-price grid |27,105 inputs /220,701 roots|all success,zero strict gaps|
| Expanded common-price grid |66,560 inputs /936,832 roots|all success,7 strict units/30 roots|
| Selected simplification |3,251 unique evaluations|all success;1,054 cached references retained|
| Selected five-job complete-primitive graph |1 input,3,625 states|all checks succeed|
| Selected five-job Java execution |746 paths,50 policy cells|all success|

The exposure stages reconstruct, serialize and check every controller, compare
its hash with the saved artifact, and recompute scalar adaptive/fixed-order
values. They enumerate all topological orders for each known input. The sweep
checker establishes all-budget Bellman values and directly checks attainment
by the stored protection-first policy. It still trusts the mathematical game.

The selected witness has c=(8,2,4,2,6),p=1.5c,edges0→1→3 and B=4. Normal work
is22; adaptive/best-fixed total costs are48/49. Both lookahead rules give49;
cached fallback gives55. Native accounting is24W+36H,192 times abstract cost,
with one common protected-work surcharge. The analytic proof is included.
This is selected evidence, not an independent workload or minimum-five theorem.

New Python replays use a180-second stage cap and210-second worker cap, with
3-second units by default,5 seconds for common-price/simplification cases,
10 seconds for saved curves and20 seconds for the primitive witness. Native
compile/execution limits are30/60 seconds with256MiB Java heap. Every replay
retains failure,timeout,invalid and unstarted statuses. Existing outputs are refused.

## Earlier results and evidence limits

The unchanged core/extended/oracle harnesses replay the earlier fixed final
DAG evaluations, hardness, B1/B2 comparators and requested-value certificates.
Their commands, limits and full denominators are documented in
`history/v3/README.md`. Optional CP modes need OR-Tools9.15.6755; use
`reproduce_extended.py b1 --with-cp` or `b2 --with-cp` with a new `--out`.
Saved benchmark scans preserve every original success/timeout/failure/invalid.
They do not rerun original timeouts or replace original timing comparisons.

The fixed final native sample remains48 authored DAGs/192 priced roots, with
two fixed-order improvements and a maximum2.0833% reduction. Later selected
four-job and common-price witnesses do not enlarge that final sample. Likewise,
the sweep timing probe uses36 previously successful certificates, not a new
end-to-end completion study: old/new check totals14.586/5.933 seconds, cold
16.588/8.090. The requested-value benchmark retains all-budget45/3 versus
oracle32/16 success/timeout counts and supports no oracle advantage.

The first common-price plan contains a mistaken motivation about artificial
extra work. Its exact bytes are retained with `MOTIVATION_CORRECTION.json`.
The native implementation already used weighted protected work before that
plan. Common p/c is a substantive restriction of that existing objective,
without a newly established physical cost model or runtime calibration.

The model requires fixed opaque work, persistent completion, immutable captured
parent outputs, own-input invalidation and guaranteed protection. Inputs and
schedules are authored. Application prevalence, elapsed-time gains and human
impact remain unmeasured. Finite checks and author proof inspections are not
mechanical proofs or independent blind reviews. The paper contains AI disclosure.

`EVIDENCE_INDEX.md` maps the claims. `MANIFEST.json` hashes every file except
itself. `PROVENANCE.json` separates exact copies from literal path substitutions
under `provenance-projections/`; those derivatives are not original pre-result
records. Earlier packages and original research files remain preserved.

This is a local extended package, not a complete public anonymous artifact.
Older scale/order/PRISM/acquisition studies remain in the research workspace
with their adverse results. Replay increases no scientific sample; its times
cannot replace original outcomes. No public license is assigned. Third-party
article PDFs, runtimes, compiled classes and raw assistant transcripts are
excluded. Final author,rights,AI-use and submission approvals remain pending.
