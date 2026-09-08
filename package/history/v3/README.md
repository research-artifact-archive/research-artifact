# Retry-policy compiler: local reproduction package v3

This author draft accompanies *Compiling Optimal Retry Policies for Dependent
Transformations*. It includes paper build36 (18 body pages, 20 total pages), the
two fixed final DAG evaluations, the restricted hardness check, the selected
four-job family, B1/B2 comparisons, and the requested-budget value oracle. It
has not been publicly released or accepted by an artifact evaluation committee.

## Run the checks

Use Python 3.10+ with assertions enabled; do not use `-O`. The core semantic,
hardness, screened-DP, and value-oracle stages use the standard library. Native
stages need a JDK 17+. Optional CP stages need OR-Tools 9.15.6755; the exact
dependency freeze is in
`data/extended/b1_constraint_comparator_01/REQUIREMENTS_FREEZE.txt`.
Runtimes are not bundled. Original core/CP experiments used Python 3.10.9 and
OpenJDK 17.0.19; the oracle benchmark used Python 3.12.14. Recorded experiments
ran on an Apple M2 with 24 GiB memory. Reproduction records its own runtime.

Run from this directory, with a fresh output directory outside the package:

```sh
python3 -B reproduce_oracle.py verify --out /tmp/retry-v3-verify
python3 -B reproduce.py all --out /tmp/retry-v3-core
python3 -B reproduce_extended.py all --out /tmp/retry-v3-extended
python3 -B reproduce_oracle.py all --out /tmp/retry-v3-oracle
python3 -B reproduce_extended.py b1 --with-cp --out /tmp/retry-v3-cp1
python3 -B reproduce_extended.py b2 --with-cp --out /tmp/retry-v3-cp2
```

The original core and extended harnesses are byte-exact v2 copies. They accept
`--java` and `--javac`. The oracle harness has `verify`, `oracle`, `controls`,
`bench`, and `all` modes. `--quick` selects at most 32 known semantic/development
inputs; it does not reproduce full counts. Saved benchmark scans, oracle
controls, and the 110-path native family remain complete with `--quick`.
Use these portable entry points; historical freeze/run drivers remain only as
provenance and may contain old workspace assumptions.

| Check | Full count | Original outcome |
|---|---:|---|
| Complete primitive/scalar/serialized policy | 4,232 priced DAGs | all success |
| Final native paths and controls | 19,640 + 4 | all success |
| CLIQUE reduction and no-failure certificates | 4,306 | all success |
| B1 development, per implementation | 8,634 | all success |
| B2 development, per implementation | 4,336 | all success |
| Selected four-job native paths | 110 | all success |
| Shared-query oracle | 4,337 inputs / 21,685 roots | all success |
| Oracle certificate/schema controls | 1 valid / 29 malformed or disabled-assertion controls | accept / reject |

The oracle replay serializes and reloads each constructed certificate, checks it
with a separate checker, and compares every requested value to the preserved
development reference. It certifies requested values, with no complete policy
claim. The verifier relies on the concavity, compatible-order, and bound
theorems stated in the paper. Finite checks do not establish those theorems.

`bench` scans all 77 saved successful oracle/all-budget certificates and checks
all 96 recorded outcomes on 48 inputs: all-budget 45 successes / 3 timeouts;
requested values 32 / 16. All 192 jointly obtained values agree. The scan never
calls a benchmark constructor or reruns a timeout. All-budget certificates cover
values and policies for every budget; requested-value certificates have narrower
scope. Original joint-success cold totals are 5.217 / 5.613 seconds, respectively;
the comparison establishes no oracle advantage.

Extended `bench1` and `bench2` likewise scan saved successful policies and retain
all original statuses. B1 retains 312 units: CP 78/0, initial subset DP 56/22,
all-budget 53/25, later screened DP 68/10 (success/timeout). B2 retains 144:
CP 48/0, screened DP 48/0, all-budget 46/2. All other original statuses and
shared-value disagreements are zero. These are authored method probes.

Oracle replay uses a 3-second unit limit (saved benchmark scans: 10 seconds),
180-second stage limit and 210-second worker limit. Extended stages use
3/180/210 seconds (hardness units: 2 seconds); native family compilation and
execution use 30/60 seconds. Core semantic limits are 10/180 seconds; core
native compilation/execution use 30/120 seconds. Failure, timeout, invalid and
unstarted outcomes remain recorded. An existing output directory is refused.

## Evidence and limits

The fixed final semantic grid covers 21,160 roots, 1,220,680 states, 9,239,600
actions and 12,551,856 outcomes. Its 584 independent inputs and four dependent
preflight inputs are known regressions. Native evaluation uses 48 authored DAGs,
192 priced roots and two bin layouts. Two roots from one input improve on the
best fixed order, with maximum total-work reduction 2.0833%. The later four-job
family was selected after exploration and does not enlarge that final sample.

The model requires fixed opaque work, persistent completion, captured immutable
parent milestones, and declared guaranteed guarded premiums. Java uses actual
APIs with authored kernels and schedules. It does not establish application
prevalence, elapsed-time benefit, or human impact. Primary scholarly attribution
and the paper's AI-use disclosure remain in the draft.

`EVIDENCE_INDEX.md` maps claims to records. `MANIFEST.json` covers every packaged
file except itself. `PROVENANCE.json` distinguishes exact copies from derived
path substitutions under `provenance-projections/`; those projections are not
original preregistrations. Original research records remain unchanged. The old
v2 root documents are retained under `history/v2/` and describe that older
package. The v1 and v2 archives remain separately preserved.

This is an extended local package, not a complete public anonymous submission
artifact. Older scale/order searches, independent PRISM/AND-OR/bounds studies,
and early acquisition counterexamples remain in the research workspace,
including adverse outcomes. Reproduction checks previously observed inputs and
the portable harness; its sample increase is zero. New reproduction timings
cannot replace original outcomes or missing original phase times.

No public license is assigned. Article PDFs, runtime binaries, compiled Java
classes and raw assistant transcripts are excluded. Final author, rights,
AI-use, and submission approvals remain pending.
