# Surveillance-Fleet: not constructed

The unchanged benchmark `Implementation/Experiment/Models/Surveillance_FG.lts` has one aircraft model composed of MISSION and BATTERY_COUNTER. They are separate software/update components sharing the aircraft's actions, not two redundant aircraft. The new endpoint likewise combines NEW_MISSION and NEW_BATTERY_COUNTER.

The proposed two-UAV coverage witness would require a second physical mission/battery plant or a duplication/relabeling of the first. That exceeds the E6 FSP-route requirement to retain the original application plant. Treating the mission and battery components as two UAVs would give a misleading availability interpretation. Therefore this optional family is not generated or measured. This is a read-only suitability assessment, not a losing synthesis result. Source SHA and exact scope are in `source_scope.json`.

The constructed operational-procedure families (Rolling, Canary, DB-Rolling, Policy) provide separate practical evidence. PC2 remains the original-plant experiment. This decision does not change any original model and does not stop the rest of E6.
