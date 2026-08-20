# FG-DUCS evaluation artifact

This is the local Git handoff directory for the anonymous FG-DUCS paper. It
contains the public inputs, recorded observations, game bundles, analysis
code, tests, and current source overlay needed to audit the paper's current
claims. Publishing, authentication, remote creation, rights approval,
and release creation are intentionally left to the authors.

## Quick start

Python 3.10 or newer is sufficient for the offline integrity, science, scan,
and regression checks:

```sh
./reproduce.sh
```

On Windows PowerShell:

```powershell
.\reproduce.ps1
```

The default `portable` mode runs integrity, anonymity/secret scanning, 188
regression and mutation tests, and raw-to-claim analysis. It works in a normal
reviewer clone with an `origin` remote. The modes `integrity` (alias `verify`),
`scan`, `test`, and `analyze` can be run separately. `handoff` (alias `full`)
adds the publisher-only requirements of a clean, no-remote, no-tag, one-root-
commit Git repository.

`analyze` reparses the 41 C1 LTS inputs, recomputes all C2 model-median ratios
from 200 raw rows, reruns 43 exact game comparisons, re-solves four C3 games,
checks the typed full-alphabet RS product and its counterexample word, checks the
typed handoff graph and traces, freshly executes 500 deterministic atomic
handoff races at one selected Goal boundary, and reruns the M8o restricted
typed-game synthesis, independent certificate consumption, nine flat-product
cross-checks, twenty-one factor mutations, and frozen census audit. It also
runs M8p from three unpartitioned complete typed tables, independently checks
their maximum two-block partitions, projected local solves, rank-sum/kappa or
losing-cylinder witnesses and direct-flat decisions, checks ten controlled obstruction tables,
and reruns a diagnostic 43-bundle coordinate screen grouped into ten C1
semantic families. Finally, it audits the post-outcome frozen M8q panel of 23
ordinary-LTS files, 41 source-definition cells, and ten provenance clusters.
For every one of the 35 successful cells it freshly checks the serialized
producer witness; six fail closed as invalid/inconclusive, 33 yield only one
block, and the ProductionCell Arms=2 base/R2 pair yields the two one-way
refined-WIN witnesses. The ordinary-LTS-to-bundle Java producer remains the
translation TCB, so this is structural consistency rather than an independent
source-semantic replay. A separate M8r audit feeds the same 41 definitions
through a conclusion-free compiled-facts exporter and independently recomputes
the dependency receipts and component partitions for the 35 successful cells,
plus the ownerless-event gate for all six rejected cells. That exporter still
shares ordinary-LTS parsing, safety/LTL compilation, composition, and fixed
old/new controller synthesis with MTSA; ordinary-LTS source replay and
source-to-WIN replay therefore both remain zero. It does not relabel a failed or timed-out
job. The M8s audit then checks the two historical ProductionCell base/R2
winning certificates from a stricter conclusion-free post-frontend contract
IR. Its separate same-author Python implementation reconstructs the 126/137
fixed endpoints and, across the supplied certificate rank domains, all 4,774
candidate buckets and 2,682 outcomes, rank/strategy
obligations, quiet Goal product, observer/activation relations, and global load
transport. It remains post-outcome, shares the ordinary-LTS frontend and fixed
controller synthesis, covers one provenance cluster, and performs neither
independent source parsing nor independent WIN synthesis. A machine-readable
M8t bridge narrows that remaining source/controller boundary for the same two
cells: before reading the M8s facts, a separate same-author standard-library
Python implementation parses a deliberately bounded registered ProductionCell
MTSA/LTS profile, independently reconstructs and synthesizes the common old/new
controller pair (81 states and 216 edges on each side), and checks every
source-sensitive M8s fact. The unchanged M8s checker then rechecks the supplied
historical certificates. Thus two composed source-to-supplied-certificate
semantic checks pass, but this is not a general MTSA frontend, certificate or
WIN generation, source-to-WIN replay, historical-runtime reproduction,
held-out/third-party evidence, or a second provenance cluster. The M8u panel
then removes the supplied-certificate input at the post-frontend boundary:
a same-author generator receives only conclusion-free IR and fixed resource
bounds, runs twice per cell, and emits byte-identical fresh WIN certificates
for all three fixed cells. A separate process that imports neither the
generator nor its rank core semantically checks all 3/3 certificates and their
terminal transport. The ProductionCell base/R2 cells are the two nontrivial
two-block results; Industry is one whole-system block. The panel spans two
sources and two provenance clusters, but remains post-outcome and calibrated,
shares MTSA parsing, fixed old/new controller synthesis, and the existing
post-frontend semantic adapter, and provides no general or independent
raw-source frontend, independent controller synthesis, source-to-WIN replay,
native contract, held-out, third-party, or production evidence. A machine-readable
report can also be retained with:

```sh
python3 -I -S -B analysis/recompute_claims.py \
  --output "${TMPDIR:-/tmp}/fg-ducs-reproduction-report.json"
```

## Evidence boundary

- `inputs/c1/`: the 41 semantic inputs and five contract-gate inputs.
- `inputs/c2/`: the eight independent and twelve Travel Agency inputs.
- `inputs/c3/`: the positive/negative ARDrone author adaptation and manifest.
- `inputs/rs/`, `evidence/rs-full-sigma/`: three post-outcome theorem-linked
  residual-soundness fixtures for supplied full-alphabet activation graphs that
  include old-endpoint history, including an ordinary-event counterexample. Exactness is externally asserted
  but not checked; these are not prospective, native, or third-party evidence.
- `evidence/m6-prism/`: 41 translated games, 82 solver logs, and the recorded
  PRISM-games 3.2.4 decisions. The PRISM binary is not redistributed.
- `evidence/m8k-correctness/`: 92 raw rows and the independent raw-LTS oracle.
- `evidence/m8k-performance/`: 200 raw rows, registered audit, and the metric
  rows bound into the M8o restricted factor/certificate and census audit.
- `evidence/m8m-source-anchored/`: one author-created ARDrone adaptation,
  original-frozen and post-outcome raw observations, two external game pairs,
  a typed handoff bundle, and explicit limitations. This is not a native
  third-party FG-DUCS contract or production deployment.
- `evidence/m8n-game-equivalence/`: all 43 exact-game comparisons. The checker
  is author-implemented, post-outcome, and not held out.
- `evidence/m8o-block-decomposition/`: post-hoc source-bound one-state
  extraction plus explicit typed local games, generated rank-sum/kappa or
  losing-cylinder certificates, independent consumption, flat-product
  cross-checks, a Travel shared-nonstutter screen, and frozen-census evidence.
  The two multistate cases exercise monitors, RS projections, precedence,
  nondeterministic outcomes, handover, winning and losing. This is not a
  general partition-discovery algorithm, arbitrary-LTS parser, prospective
  study, native integration, or evidence that the semantic product is linear.
- `inputs/c2/typed-partition-fixtures.json`,
  `evidence/m8p-partition-discovery/`: three post-outcome unpartitioned typed
  flat tables, ten controlled obstruction tables, a maximum-block producer,
  independently implemented exhaustive consumer, projected local-game witness
  producer/consumer, and the coordinate-relative
  43-bundle diagnostic. The exact result is relative to supplied atoms and a
  complete typed table. The diagnostic makes zero typed-factorability claims and
  assumes complete/correct typed dependency declarations; it is not an
  arbitrary-LTS atom inference, prevalence study, native parser, or
  third-party/held-out evidence.
- `evidence/m8q-native-factorization/`: a post-outcome outcome-complete panel
  over 23 ordinary-LTS files, 41 source-definition cells, and ten provenance
  clusters, plus focused ProductionCell Arms=2 base/R1/R2 bundles. The Java
  producer runs before constructing the mixed-version global update game, but
  it does construct the fixed old/new endpoint products. It conservatively
  finds two blocks and producer-verifies a one-way quiet-terminal WIN for base
  and R2; R1 remains one block. Those two positives are one source and one
  provenance cluster. The Python consumer checks serialized rank, policy,
  Goal payload, observer relation, selector, and handover consistency, but does
  not replay the ordinary LTS; source translation remains a stated TCB.
  The focused base/R1/R2 bundles are separate measurements from the panel
  cells; their decisions and structural censuses agree, while timing fields
  and therefore file hashes may differ.
- `evidence/m8r-native-source-dependency-replay/`: a post-outcome replay over
  the same 23 files/41 definitions/ten clusters. A Java exporter that has no
  direct factorizer, bundle, adapter, or update-game-solver dependency emits
  compiled declaration facts only; a Python implementation independently
  reconstructs component nonidentity, tester/observer effects, update-owner
  closure, precedence, partition, and the ownerless gate. The 35 available
  producer receipts/partitions agree exactly; all six rejection decisions agree,
  and each producer diagnostic belongs to the replayed obstruction set. The
  shared compose path nevertheless synthesizes the fixed old/new controllers,
  so this is panel-bounded post-frontend replay—not parser-only, solver-free,
  ordinary-LTS-to-bundle, or source-to-WIN evidence.
- `evidence/m8s-post-frontend-contract-certificate/`: a stricter
  conclusion-free contract-IR replay for the two historical ProductionCell
  Arms=2 base/R2 winning certificates. A separate standard-library Python
  implementation checks the fixed endpoints, every candidate and complete Post
  on the supplied certificate rank domains, rank and retained strategy, quiet
  terminal product, activation/observer relations,
  137 load selectors, and terminal kappa assembly. The two targets are one
  already-known source/provenance cluster, the observation JAR is not the
  historical M8q JAR and does not reproduce that historical or a transitive
  runtime closure, and the shared parser plus fixed-controller synthesis remain
  TCB; independent source parsing, WIN synthesis, and source-to-WIN
  replay all remain zero.
- `evidence/m8t-productioncell-source-contract-certificate/`: two composed
  checks for the same ProductionCell base/R2 cells. A bounded registered-source
  checker derives the source semantic closure before opening the M8s facts,
  independently synthesizes the same unique old/new controller pair twice,
  and checks components, transfers, 24+24 safety machines, 22 observers per
  execution, 152 activation rows per execution (82 ERROR), protocol,
  controllability, and load facts. The unchanged M8s checker then verifies the
  supplied historical rank/strategy/Post/transport evidence. This is
  same-author, post-outcome evidence from one source and one cluster; the
  checker runtime is not transitively frozen, and general parsing, independent
  WIN/certificate generation, source-to-WIN replay, held-out, third-party, and
  production counts remain zero.
- `evidence/m8u-post-frontend-generated-win-panel/`: three fresh generated
  WIN certificates and separate semantic checks for ProductionCell base/R2
  and Industry, with 54 evidence files and a 53-entry nested checksum. The
  protocol records two fresh facts exports and two fresh generations per cell,
  generation seals before checker execution, 3/3 verified certificates,
  15,049 candidate buckets, 6,319 outcomes, 622 ranked states, and 778 strategy
  buckets. ProductionCell contributes the two nontrivial factorizations;
  Industry is a whole-system one-block check. The generator receives no
  historical outcome or supplied certificate input. This is same-author,
  post-outcome, calibrated C4 support with shared frontend/controller and
  checker-adapter boundaries, not general source-to-WIN, C5, native,
  held-out, third-party, or production evidence.
- `analysis/recompute_claims.py`: the raw/input/bundle-to-claim entry point.
- `evidence/SANITIZATION.md`: public path-tokenization and seal boundary.
- `protocols/`: protocols needed to interpret the included evidence.
- `source-rebuild/`: hash-bound author-side overlay for a pinned MTSA source
  archive. It excludes the full upstream tree and binary; M9 source is
  compile-only and no M9 workflow or claim is executed.
- `THEORY_SUPPLEMENT.md`: assumptions, counterexample, proof construction, and
  complexity boundary for independent-block composition.

The unfinished one-shot M9 panel remains excluded: no M9 workflow or claim is
executed. M8q is a separate source-native, pre-mixed-game study over the
published FG-DUCS inputs and is not a third-party or production deployment.

## Rebuild and smoke boundary

Offline `portable` checks are complete without Java or network access. To
rebuild the current proposal runtime, follow `source-rebuild/README.md`; it
requires JDK 17, Maven, Git, network access, and the pinned upstream archive.
The rebuild tool verifies the archive, applies the hash-bound overlay in a
temporary directory, runs its scoped tests, and keeps products outside the
immutable payload.

The recorded M8k, M8m, M8n, M8q, and PRISM observations are bound to their
campaign-specific historical runtime hashes. M8u uses the current M8s
observation JAR, which is not the historical M8q JAR and is not a transitive
runtime freeze. The current public source overlay is separately rebuildable and
was checked with 101 tests and an integration smoke. It is not claimed to be
byte-identical to any historical JAR. The
offline analyzer instead rechecks decisions and claims from the public LTS,
CSV, and serialized-game evidence. See `CLAIM_EVIDENCE_MAP.md` for the exact
boundary.

Reviewers who separately obtain PRISM-games 3.2.4 may rerun the 41-case
external-solver campaign. The frozen protocol is provenance; the command below
uses public relative inputs and writes outside the checkout:

```sh
python3 -I -S -B analysis/run_external_solver_validation.py \
  --protocol protocols/m6-external-prism-v1.json \
  --prism-bin /path/to/prism-games/bin/prism \
  --prism-archive /path/to/prism-games-3.2.4-mac64-arm.tar.gz \
  --output "${TMPDIR:-/tmp}/fg-ducs-prism-rerun"
```

The registered observations were made on macOS. Linux and Windows commands are
replication paths, not claimed observations. A future public release should be
cloned on those platforms and rerun before adding platform-specific claims.

The standalone report command above writes outside the checkout. Writing an
unlisted file inside the checkout intentionally makes the integrity and Git
handoff gates fail.

## Manual publication checklist

1. Resolve every `PENDING` row in `RIGHTS_REVIEW.md`; review `LICENSE`, `NOTICE`,
   and `source-rebuild/OVERLAY_MANIFEST.json` against the authors' actual rights.
2. Replace every `PENDING` rights decision with a neutral resolved status,
   regenerate `SHA256SUMS`, then run `./reproduce.sh handoff`. The publisher
   gate intentionally fails while any row remains pending.
3. Clone once normally and once with `core.autocrlf=true`; run `portable` in both.
4. Create a new anonymous, non-fork repository with no personal profile links.
5. Add the remote and push manually. Do not reuse a personal authenticated
   session during heavy double-anonymous review.
6. In a logged-out session, clone and rerun `portable` before putting the URL in
   the paper.

Do not replace the neutral root commit with personal author metadata during
double-anonymous review. If files change before publication, run
`python3 tools/prepare_release.py`, rerun every gate, and create a reviewed
anonymous release commit.
