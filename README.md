# Resource Contracts for Completing Optimistic Computations

Anonymous research artifact for [manuscript219](paper/main.pdf). The paper asks what total work one completion policy must spend to guarantee both a fixed call allowance and optimal protected work for every unknown interference budget. It then characterizes exactly which completion modes preserve the residual protection contract, what information a safety component can omit, and when extra charges change that answer.

The fixed paper has18 main-text pages and3 reference pages. [Its snapshot](paper/SNAPSHOT.json) binds the source/PDF bytes. [The paper guide](paper/README.md) explains the final structure, and the [evidence map](PAPER_ARTIFACT_MAP.md) connects its claims to reproducible studies.

The main new interface needs only completed weights, observed mismatch count, incurred protection and the proposed current weight. [Residual safety](charged/RESIDUAL_SAFETY.md) supplies the full proof, fee conditions and an indistinguishable-prefix counterexample. [The Java component](charged/JAVA_RESIDUAL_FILTER.md) implements that interface with two linked heaps and includes its original/revised traces. All16,267 new/earlier-filter whole-work comparisons and all62 Java comparator coordinates are equal; additional safe choices do not establish a new worst-work improvement.

The native/source studies preserve narrower correspondence conditions and adverse results: Linux relaxes a two-body-attempt bound to three; Roslyn does not establish fixed-work transfer and is slower under the stated dense arrivals; writer-maintained Valkey alternatives remain stronger. This is an author research artifact, and publication or model review does not establish acceptance or submission readiness.

## Reproduce

```sh
git clone https://github.com/research-artifact-archive/research-artifact.git
cd research-artifact
python3 -B tools/verify_release.py
python3 -B charged/reproduce.py all --out work/all57 --timeout 300
```

Use Python3.10+ with assertions enabled on a POSIX system and a fresh output directory. The57 standard stages verify and reinterpret fixed evidence with the standard library. They create no new independent workload population or timing sample. Optional native rebuild commands, including Java17, are separate and linked from the evidence guides. Check out the immutable evidence commit cited by a particular paper to reproduce that snapshot. Complete public replay and native-rebuild receipts for this release are recorded in [REPRODUCTION_20260911.json](REPRODUCTION_20260911.json), with exact completed and pending scopes.

## Earlier evidence and provenance

The byte-preserved [legacy package](package/README.md), [earlier paper](package/paper/main.pdf), [evidence index](package/EVIDENCE_INDEX.md) and the charged study history retain preceding claims, failures, timeouts and populations. Historical paper/section references in individual study notes refer to their original snapshots. The earlier [root guide](docs/README_BEFORE_UNIT_GUARD.md) and [paper map](docs/PAPER_ARTIFACT_MAP_BEFORE_UNIT_GUARD.md) remain byte-for-byte; their relative links refer to their original repository-root location.

`./reproduce.sh portable` checks the legacy package. It is a separate verification from the57-stage charged replay. Licenses, source provenance, reversible compression and path projections are described in [NOTICE.md](NOTICE.md), the release manifest and charged/PROVENANCE.json. The [September10 reproduction receipt](REPRODUCTION_20260910.json) retains preceding completed checks; the new receipt does not rewrite them. Counts across studies overlap and are not independent samples of software workloads.
