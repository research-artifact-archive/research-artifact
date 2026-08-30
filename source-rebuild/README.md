# Source rebuild from pinned MTSA

This directory rebuilds the evaluation runtime from the official MTSA
`v1.1.0` source archive without publishing the MTSA source tree or an MTSA
binary.  The upstream archive is downloaded by the reviewer, checked against
its registered size and SHA-256, patched in a temporary work directory, and
built with JDK 17.

The public payload contains:

- full source only for the 145 Java files absent from upstream MTSA;
- a one-line-context unified patch for 39 changed MTSA Java files and the
  current build patch to `pom.xml`;
- a manifest binding every input and resulting file by SHA-256;
- a cross-platform rebuild/checker and the 19-class, 101-test selection.

The overlay is the mechanically complete public projection of the current
difference from the pinned upstream tree. It therefore also contains legacy/UI
branches and compile-time plumbing for the unfinished M9 study. Two private,
unused M9 control-file hash constants are zeroed in this projection because
their originals fingerprint path-bearing files; M9 protocols/results are not
included, `reproduce` never invokes them, and no paper or artifact claim counts
them. This broad compile boundary is not a claim that every included branch was
used in the reported experiments. The manifest binds every included file.

### Legacy syntax compatibility boundary

The registered fixed models contain unselected historical target declarations
using the keyword `selective_fine_grained`. Rewriting those files would change
their registered SHA-256 values. Compatibility source is retained, but every
public smoke and experiment workflow selects `UPDATE_CONTROLLER_OTF_FG`; none
selects a legacy target.

### Inherited O-DUCS route (static inspection only)

The inherited MTSA/DUCS-based implementation retains an `on_the_fly`-only
route: `LTSCompiler` sets `isOTF`, and `UpdatingControllerSynthesizer` selects
`DirectedControllerSynthesisDUC` when `fine_grained` and
`selective_fine_grained` are absent. `revised_on_the_fly` instead dispatches
to `MtsaRevisedOtfDucsAdapter` before the legacy branch. The legacy solver is
included under `added/maven-root/mtsa/src/main/java/MTSTools/ac/ic/doc/mtstools/model/operations/DCS/nonblocking/`;
the parser/dispatcher changes are bound by `OVERLAY_MANIFEST.json`.

The historical target name `UpdCont_OTF` does not itself select an algorithm:
the declaration must be active and its options determine the route. The
inspected historical example declaration is commented out, and this package's
registered workflows select the FG target instead. No O-DUCS synthesis rerun,
working standalone legacy model, or identity with the 2024 experimental
binary is asserted. The 145 added/39 changed Java counts are differences from
MTSA v1.1.0, not a count of this paper's novel contributions or a diff against
O-DUCS 2024. Primary publications are listed in `../UPSTREAM_CITATIONS.md`.

The upstream project does not expose a project-wide `LICENSE` or `COPYING`
file and its README does not state redistribution terms. Reviewers therefore
obtain the pinned upstream code directly from its official server. The authors
have confirmed permission to modify and publish the inherited MTSA/DUCS-based
tool, covering these integration sources and the one-line-context patch;
`../RIGHTS_REVIEW.md` records the author-attested scope. This is not a
project-wide upstream license or clearance of every derived input. The full
MTSA source tree, binary, and packaged dependencies remain omitted. Nested
third-party license files remain in
the official archive and are never copied into this payload. The official
repository and primary MTSA paper are cited in `../UPSTREAM_CITATIONS.md`.

## Run

Set `JAVA_HOME` to a JDK 17 installation.  Maven and Git must be on `PATH`.

macOS/Linux:

```sh
./rebuild.sh
```

Windows PowerShell:

```powershell
.\rebuild.ps1
```

The default run downloads and verifies the 326 MB official archive, applies
and verifies the overlay, builds the JAR, runs all 101 targeted tests, runs a CLI smoke
composition over `GSM_FG.lts`, and runs the source-native two-block
ProductionCell smoke through the structural bundle checker. The script searches for the nine fixed models
in the public artifact layout; `--models PATH` overrides it.  It verifies each
model against its registered SHA-256 before staging and copies every model
byte-for-byte.

For the authors' private release audit only, the registered evaluation runtime
can be supplied without copying it into the public bundle:

```sh
./rebuild.sh --registered-runtime /path/to/registered-mtsa.jar
```

This optional command is a drift detector, not a public release gate. The
registered campaign JAR predates portions of the current source overlay, so a
class mismatch is reported as a diagnostic failure rather than being hidden.
The public claim is instead the clean source rebuild, scoped tests, and both
smokes below; it does not assert byte identity or whole-class semantic
equivalence with a historical campaign JAR.

The public claim is the 101/101 scoped suite, including compact-game tests and
the compiled-facts exporter isolation tests,
plus all nine fixed-model integration cases, the GSM CLI smoke, and the
source-native ProductionCell smoke. The latter constructs the fixed old/new
endpoint products but reports zero mixed-version global-game states/queries;
it remains a producer-verified one-way sufficient-WIN result.

The separate M8r replay invokes the shared MTSA compose path, which parses the
ordinary LTS, compiles safety/LTL declarations, and synthesizes the fixed
old/new controllers. It then exports conclusion-free compiled facts and stops
before fixed-endpoint products, local update games, or a mixed-version update
game. Its Python consumer independently replays only the registered panel's
dependency, partition, and ownerless-event semantics; it is neither a
solver-free frontend nor an ordinary-LTS-to-WIN replay.

The M8s exporter extends that post-frontend boundary with fixed old/new
controller tables, observer bindings, activation sources, and the load selector,
while still excluding endpoint products, dependency partitions, Goal sets, games,
winning regions, strategies, ranks, and certificates. A separate same-author
Python checker uses those conclusion-free facts to semantically verify the two
historical ProductionCell Arms=2 base/R2 certificates, including complete local
Post tables and global load transport. It remains post-outcome, shares the MTSA
ordinary-LTS frontend and fixed-controller synthesis, and is neither source-to-WIN
synthesis nor an independent ordinary-LTS frontend.

## Maintainer regeneration

Maintainer-side regeneration is not needed by reviewers. The public manifest
and root checksums bind this exact overlay.
