# The Total-Work Cost of Bounded Retry Guarantees

Anonymous research artifact for the [stored manuscript](paper/main.pdf), fixed manuscript216. Its exact source/PDF hashes and18-body/20-total-page snapshot are in [paper/SNAPSHOT.json](paper/SNAPSHOT.json). The model now has explicit state, action effects/observations/charges and a two-branch worked example. Proposition8 incorporates the [four-job unknown-budget observation boundary](charged/OBSERVATION_DAG.md): strict erasure can raise least total work from20 to21 with the same optimal protection curve. The [full-program](charged/FULL_PROGRAM_PROOF.md) and [conditional Java](charged/JAVA_INTERFACE_PROOF.md) proofs state their premises explicitly.

Its immutable evidence commit `b719eb7a6514d7f3a47f2a3af21e43b4ffd4699f` passed the complete public inventory and all53 standard stages in a fresh unauthenticated acquisition. This paper/guide update adds no scientific sample. Publication, replay and model review are author activities, not independent certification or acceptance evidence.

The research asks how cheap validation, protected recomputation and cached guarded completion trade total work against protected work under bounded completion calls. Its guarantees require the specified persistent-job, observation and charging interfaces. It does not infer costs, a write budget, a caller SLA or contract compliance from arbitrary concurrent code.

The newer [distinct-order supplement](charged/SHORT_ORDER_POLICY.md) proves that minimum-ready targets on every call can require at least766 work while a short explicit policy uses752, with the same universal Q/L guarantees. Its427-path candidate and421-path premature-fresh control concern one already-observed root. Stage54 replays the fixed root and short policy; the stored manuscript216 and its cited53-stage evidence are unchanged.

## Start here

* [Paper-to-evidence map](PAPER_ARTIFACT_MAP.md): current mathematical and source obligations, with replay stages.
* [Unknown-budget observation boundary](charged/OBSERVATION_DAG.md): complete forward-coupling proof, exact policy curves and strict interface premises.
* [Guard and call accounting](charged/RESOURCE_ACCOUNTING.md): independent comparison-free joint caps, common-price greedy construction and the alternative atomic mismatch call weight.
* [Unit guards and precedence](charged/UNIT_GUARD_DAG.md): strong joint-cap hardness despite polynomial frontier size; full proof, inherited scheduling attribution, fixed positive/negative checks and fees on every call.
* [Research lineage](charged/RESEARCH_LINEAGE.md): earlier results, corrections and preserved failures. The older [charged overview](charged/README.md) retains the full extension history.

## Reproduce

```sh
git clone https://github.com/research-artifact-archive/research-artifact.git
cd research-artifact
python3 -B tools/verify_release.py
python3 -B charged/reproduce.py all --out work/all54 --timeout 300
```

Use Python3.10+ with assertions enabled on a POSIX system. Always choose a new output directory. The54 standard stages verify and replay fixed evidence using the standard library; they do not rerun native timing campaigns as new samples. To reproduce a particular paper, check out its cited immutable evidence commit first. Individual stage commands and optional native rebuilds are linked from the map. This archive contains overlapping study populations, and its file or replay counts are not research sample sizes.

The [September10 reproduction receipt](REPRODUCTION_20260910.json) records completed local/public replays and their scope. A successful replay preserves earlier failures and timeouts as recorded outcomes. Native Java, Linux and Roslyn studies expose both positive witnesses and transfer limits; the Valkey comparator and cost-fit failures remain in the archive. No human evaluation is included.

## Earlier package and provenance

The byte-preserved `package/` tree, its [older paper](package/paper/main.pdf), [usage](package/README.md) and [evidence index](package/EVIDENCE_INDEX.md) describe previous research versions. Their claims and sample counts retain their original scope. `./reproduce.sh portable` verifies that legacy package; it is not the54-stage charged replay above. Licenses, rights and source provenance are in [NOTICE.md](NOTICE.md) and the accompanying manifests.

The preceding [root guide](docs/README_BEFORE_UNIT_GUARD.md) and [paper map](docs/PAPER_ARTIFACT_MAP_BEFORE_UNIT_GUARD.md) are preserved byte-for-byte for history. Their relative links refer to their original repository-root location. This new entry page replaces their obsolete titles and long chronological appendices without altering the scientific payload.
