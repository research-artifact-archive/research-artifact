# Minimum-ready selection fails even with distinct works

Author mathematical lower bound and checked constructive upper witness. This is an adaptive follow-up to the preserved tied-order search03--06 and ordinary ClaudeCost16 suggestion, followed by the pre-fixed one-root check07. The earlier nine distinct-weight perturbations all gave equality; those results remain unchanged. No general root least-curve theorem, new native measurement, or independent/mechanical certification is claimed.

## Statement and permitted programs

Use the original visible-comparison persistent whole-kernel interface: a ready job costs its positive fixed work every time its pure opaque kernel executes. Preparations may occur early after readiness and records/snapshots may be retained. A record certifies its own input identity and saved immutable parent tuple; copying does not retag it. The writer has a gate before every foreground operation, and an unfinished target admits an identity fresh to all preceding captures/records. Selection after the gate can choose only records already computed before it. Cheap mismatch fails, cached mismatch recomputes protectively and completes, fresh always computes protectively; no guard is retained. Q counts these calls, W all kernel work from the common start, and L protected kernel work. Inspection/local work does not contribute these body charges, but cannot substitute for finite completion.

V_3 contains deterministic causal programs receiving no B, completing with Q<=n+3 against every environment with any finite unconditional write bound, and with L<=Top_(b-3)+ for every b-write-bound environment. Let V_3^min restrict only the target of each cheap/fresh/cached invocation to a minimum-work ready unfinished job. It leaves preparation order, inspections, record storage and all mode/observation choices unrestricted. The minimum-ready rule applies throughout execution, not merely in the cheap phase.

For jobs0,...,5 with works (62,83,15,84,30,31) and edges1→2,3→4,4→5, every P in V_3^min satisfies W_P(7)>=766. The checked unrestricted policy has W_P(7)=752, hence the minimum-ready rule is strictly suboptimal although all works differ. A checked minimum-ready witness attains766. We do not use this separation to assert that752 is an analytically proved unrestricted all-program optimum.

## Lower bound for arbitrary minimum-ready programs

Mandatory work is Omega=305. Sorted top sums are G=(0,84,167,229,260,290,305). Capping and then stopping any concrete prefix with d writes requires L<=G((d-3)+), with indices capped at6. This bound constrains the controller even if it does not know d.

Give no writes until job0 completes. It is the unique minimum ready job. Job1 then is the unique minimum ready target. Force three useful comparisons of job1 to fail with fresh identities. All must be cheap: a protected completion with at most three writes violates L=0. Fresh and already-stale cached completion are forbidden for the same reason. Finite completion forces these useful comparisons despite inspections or early preparations. They cost three distinct invalidated preparations, namely3*83=249 duplicate units, and exhaust the three spare calls.

Every further cheap call is inadmissible: it either already fails or can be made to fail by one additional fresh write in a finite extension. Four failed calls plus six mandatory completing calls require Q>=10>9. The hypothetical extra write is used to exclude such a program, not charged to a different witness.

The next useful cached comparisons are therefore forced, by unique readiness order and the following capped-prefix inequalities:

| Target | Why fresh or already-stale cached completion is forbidden | State after a fresh write at its matching cached comparison |
| --- | --- | --- |
| 1, work83 | 83>G(0)=0 | d=4, L=83 |
| 2, work15 | 83+15=98>G(1)=84 | d=5, L=98 |
| 3, work84 | 98+84=182>G(2)=167 | d=6, L=182 |

Write once at each of these three comparisons. They add duplicate charges83+15+84. Now jobs4 and5 remain. Their combined work is61, and182+61=243>G(3)=229. On the no-more-write continuation, they cannot both complete protectively: fresh and already-stale cached both count as protected. Thus at least one must finish through a matching cached call. Put the seventh write at the first such useful comparison. It adds at least min(30,31)=30 duplicate units.

The writer reserves three initial useful-comparison slots for job1, one subsequent useful cached slot each for jobs1,2,3, and one final useful cached slot among jobs4,5. Each slot is spent at most once, even on off-witness plays. Thus it is unconditionally seven-bounded; no unbounded adversary is merely truncated after observing its result.

At every useful comparison the no-write matching record was already paid. A fresh identity invalidates every available target record, including alternatives selected after the gate. Earlier retired capture identities cannot return; separate jobs and distinct captures give separate computations. Global distinct charging therefore yields

    W >= 305+3*83+83+15+84+30 = 766.

This includes arbitrary early preparations/retained records and all admitted mode choices under the target restriction.

## Constructive upper witness and exact finite checks

WITNESS07_0.json stores full explicit fresh/cheap/cached trees. RESULT07.json records independent operation interpretation, with313 unrestricted and309 minimum-ready complete paths. Both trees obey Q<=9 and attain the protected curve (0,0,0,0,84,167,229,260,290,305) at B0,...,9. The unrestricted W curve is (305,389,473,557,641,721,752,752,781,796); the minimum-ready curve differs only at B7, where it is766. No play has more than9 bad comparisons, so larger write budgets leave the finite tree's maxima unchanged. Every matching/mismatching branch is interpreted for readiness and charges; immediately prepared comparison intervals supply the standard disjoint-write reasoning for arbitrary extra harmless writes.

The unrestricted tree supplies the upper witness needed for the strict separation. The minimum-ready tree plus the preceding all-program lower bound establishes its optimum766 at B7. The complete oracle's single root vector is finite evidence only for general leastness; it is not a proof that every arbitrary DAG root has a least entire curve. This result does not refute minimum-ready normalization confined to the cheap phase, require history-dependent ordering, or establish usefulness in a native client.
