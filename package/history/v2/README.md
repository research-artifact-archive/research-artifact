# Retry-policy compiler: extended local reproduction package

This local author draft accompanies *Compiling Optimal Retry Policies for
Dependent Transformations*. It contains the two fixed final DAG evaluations,
restricted hardness check, selected four-job family, B1/B2 implementations and
complete recorded comparisons. It has not been publicly released or accepted by
an artifact evaluation committee. Distribution conditions await author approval.

## Requirements and commands

Use Python3.10+ with assertions enabled. Core, hardness and screened-DP stages use
the standard library; native stages require a JDK17+. The optional CP stages use
OR-Tools9.15.6755. Exact dependency versions are in
`data/extended/b1_constraint_comparator_01/REQUIREMENTS_FREEZE.txt`; install these
in a separate environment if running CP. Runtimes are not bundled. The saved
experiment used Python3.10.9, OpenJDK17.0.19 and an Apple M2 with24GiB memory.

Choose a new output directory for every command:

```sh
python3 -B reproduce_extended.py verify --out /tmp/retry-v2-verify
python3 -B reproduce.py all --out /tmp/retry-v2-core
python3 -B reproduce_extended.py all --out /tmp/retry-v2-extended
python3 -B reproduce_extended.py b1 --with-cp --out /tmp/retry-v2-cp1
python3 -B reproduce_extended.py b2 --with-cp --out /tmp/retry-v2-cp2
```

Both harnesses accept `--java` and `--javac`. `--quick` selects a small known-input
smoke check; it does not reproduce the full counts. Native family replay always
checks its110 selected paths. Use `hardness`, `b1`, `b2`, `bench1`, `bench2` or
`family` to run one extended stage. Every worker imports package-local scientific
sources. The old original experiment drivers are provenance; use these portable
entry points instead of invoking old freeze/run scripts directly.

| Check | Full count | Saved outcome |
|---|---:|---|
| Complete primitive/scalar/serialized policy |4,232 priced DAGs|all success|
| Native final paths |19,640 +4 controls|all success|
| CLIQUE reduction and no-failure certificates |4,306|all success|
| B1 development, per implementation |8,634|all success|
| B2 development, per implementation |4,336|all success|
| Selected four-job native paths |110|all success|

Development replay compares deterministic values, independently scans policies,
and runs the separate scalar oracle. With `--with-cp`, it also invokes the pinned
CP model and checks its policy. The unit cap is3seconds (hardness2seconds), the
stage cap180seconds and the worker cap210seconds. Native compilation/execution
have30/60second limits. Core caps are10seconds per semantic unit/180seconds per
stage, native30/120seconds. Failure, timeout, invalid and unstarted outcomes stay
in each reproduction output; an existing output directory is refused.

`bench1` and `bench2` **scan saved successful policies and check full recorded
status counts**. They do not solve benchmark roots or rerun historical timeouts.
B1 retains312 units: CP78/0, initial subset DP56/22, all-budget53/25, and the later
screened-DP extension68/10 (success/timeout). B2 retains144 units: CP48/0,
screened DP48/0 and all-budget46/2. The all-budget method returns/checks a complete
curve, while CP/DP return a requested-budget policy. All other recorded statuses
and shared-value disagreements are zero. These are authored method probes.

## Evidence and scope

The final semantic grid includes21,160 roots,1,220,680 states,9,239,600 actions and
12,551,856 outcomes. Its584 independent inputs and four dependent preflight
inputs are known regressions. Final native evaluation contains48 authored DAGs,
192 priced roots and two bin layouts; only two roots from one input improve on
the best fixed order, with maximum total-work reduction2.0833%. The later four-job
family is selected after exploration and does not augment that final sample.
Native controls preserve captured parent milestones after live-key writes.

The model requires opaque fixed work, persistent completion and declared guarded
premiums. Java uses actual APIs with authored kernels/schedules. It does not
measure application prevalence, wall-clock benefit or human impact. General
recurrence/reflection and fixed-mode sequencing are attributed in the draft;
solver-independent primitive optimality also applies to CP/DP policies.

`PROVENANCE.json` lists byte-exact copies, exclusions and original hashes.
`provenance-projections/` explicitly contains **derived path substitutions** for
workstation-specific manifests/command receipts; these are not the original
preregistration records. Original scientific records remain unchanged outside
the package. `MANIFEST.json` checks every packaged file. The paper is build26,
authored on September8,2026, with18 body pages and20 total pages.

`EVIDENCE_INDEX.md` maps current claims to included evidence. Older scale/order
search/PRISM/independent-baseline studies and their adverse outcomes remain in the
research records, outside this package's executable scope. This is an extended
core package, not a complete public anonymous submission artifact. Reproduction
is a check of the portable harness and previously observed inputs, never an
increase of scientific sample size. New timings do not repair old missing phase
times or replace old outcomes. The v1 archive is retained separately.

No public license is assigned here. Third-party article PDFs, runtime binaries,
compiled Java classes and assistant transcripts are excluded. Public citations
remain in the draft, including its AI-use disclosure. Final author, rights and
submission approvals remain pending.
