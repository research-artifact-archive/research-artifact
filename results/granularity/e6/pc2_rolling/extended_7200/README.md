# PC2 separate 7200-second campaign

This is a user-authorized extended-budget series, separate from the immutable v2 1200-second Mac results. The fixed order is Lazy with `contractMerge=transfers`, then Direct-Full with `contractMerge=none`, one trial each, 32g heap and a 7200-second whole-JVM limit. The shared E6 JVM lock serializes both trials. The second row is full exploration of the fine contract; it is not the bulk-transfer variant. Existing timeouts remain timeouts in their original rows.

The E1 JAR, v2 LTS and previously compiled Pc2DiagnosticRunner class are unchanged. Exact-byte copies of the class, Java bridge source and LTS are under `frozen/`; this campaign does not compile another class or build a solver JAR. Static preflight checks hashes and arguments without adding a synthesis trial. The existing endpoint validation remains applicable to the byte-identical input.

The preregistered expectation is merged-transfer LOSS from simultaneous calibration unavailability, and fine Direct-Full WIN consistent with the earlier checked fine Lazy result. These are expectations only. TO, OOM, invalid certificates and contrary completed verdicts remain explicit; absent measurements are never inferred.

An independent Python check will form the old local-plant/controller product and count simultaneous transfer-domain membership. The proposition that no old reachable state enables both domains is a test hypothesis, not a model assumption. Transfer-domain eligibility and post-transfer safety are distinct.

The existing Xeon archive and `run-pc2rolling.ps1` are read-only comparison artifacts. Their JAR, LTS and class bytes are checked against the same fixed evidence. No Xeon machine is operated. To select only the two prior timeout cells in that existing launcher, use `-Cells @('lazy_transfers','direct_full_none')`; its default heap is 200g, so Xeon observations, if supplied, must be separate from these Mac 32g observations.

Run `python3 run.py preflight` once after the DAILY registration is recorded, then `python3 run.py run`. Raw directories and launch/completion metadata are create-only. The original v2/raw, freeze, code/classes and inputs must remain unchanged. Derived tables will retain host, budget, heap and trial identity as separate columns and rows.
