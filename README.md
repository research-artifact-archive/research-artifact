# Resource Contracts for Completing Optimistic Computations

Anonymous research artifact for [manuscript232](paper/main.pdf). The paper asks how much total work a scheduler may spend while retaining a fixed call allowance and optimal protected work at every unknown interference budget. For an arbitrary finite dependency DAG, an exact safety filter permits every completion mode that preserves the residual protection contract. Every caller following the specified immediate-preparation protocol has worst body work within `(3r+2)/(2r+2)` of the best general program satisfying the same simultaneous contract. The factor is sharp over this entire caller class; it is 5/4 for one spare call.

The fixed paper has18 main-text pages, with Data Availability and references on pages19–21. [Its snapshot](paper/SNAPSHOT.json) binds the source/PDF bytes. The [paper guide](paper/README.md) explains the structure and the [evidence map](PAPER_ARTIFACT_MAP.md) connects claims to their fixed studies.

[The arbitrary-DAG approximation](charged/DAG_APPROXIMATION.md) includes the general proof, author audits and the sole fixed finite study:16,263 roots,96,795 budget rows and4,632,516 expanded states, with zero violations. The finite checker does not enumerate the full general-program comparator; the lower bound is analytical. Sharpness is a limiting geometric family, not an empirical performance ratio or a tight factor for minimum-ready scheduling.

[Residual safety](charged/RESIDUAL_SAFETY.md), [general fee separation](charged/CHARGED_GENERAL.md) and [three actual operation prices](charged/THREE_COST_RESIDUAL.md) distinguish body costs from resource charges. The body-only filter needs completed weights and current proposed work; arbitrary future fee premiums can require future information. The [Java component](charged/JAVA_RESIDUAL_FILTER.md) implements the body/common-premium interface with two heaps. All16,267 policy comparisons and all62 Java worst-work comparator coordinates are equal: extra permissions alone did not improve those worst-work values.

Native/source studies retain their narrower scope and adverse results. The cached Linux variant preserves the two-body-attempt bound, while the earlier two-cheap variant permits three. Roslyn does not establish fixed-work transfer and is slower under the stated dense arrivals; writer-maintained Valkey alternatives remain stronger. These results do not establish a natural client needing the combined contract, native latency gains, strong novelty or submission readiness.

## Reproduce

```sh
git clone https://github.com/research-artifact-archive/research-artifact.git
cd research-artifact
git checkout 759160fa128d0f2653d3195ea0d9b2289f4198f8
python3 -B tools/verify_release.py
python3 -B charged/reproduce.py all --out work/all60 --timeout 300
```

Use Python3.10+ with assertions enabled on a POSIX system and a fresh output directory. A fresh unauthenticated acquisition of this immutable evidence commit passed its complete142,751-file inventory and all60 standard stages. The [reproduction receipt](REPRODUCTION_20260911.json) gives the exact scope. The paper publication changes the manuscript and explanatory metadata, with scientific sources, inputs, proofs, traces and replay code unchanged. At the evidence commit, the stored older manuscript is219; manuscript232 is in this later paper publication.

Standard replays use fixed populations and create no new independent workload or timing sample. Optional native rebuild commands are separate. `./reproduce.sh portable` verifies the legacy package. Prior native Java rebuilds remain identified by their original commit; they were not repeated as new measurements for this paper publication.

## Earlier evidence and provenance

The [legacy package](package/README.md), [earlier paper](package/paper/main.pdf), [evidence index](package/EVIDENCE_INDEX.md) and charged study history retain earlier claims, failures, timeouts and populations. Historical section locators refer to their original snapshots. The [earlier root guide](docs/README_BEFORE_UNIT_GUARD.md) and [paper map](docs/PAPER_ARTIFACT_MAP_BEFORE_UNIT_GUARD.md) remain unchanged; their links refer to their original root location.

Licenses, provenance, compression and path projections are described in [NOTICE.md](NOTICE.md), the release manifest and charged/PROVENANCE.json. The [September10 receipt](REPRODUCTION_20260910.json) and prior releases retain preceding checks. Counts overlap across studies. Author reproduction and model-assisted review are not independent certification or an acceptance decision.
