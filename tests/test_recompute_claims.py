from __future__ import annotations

import copy
import csv
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "analysis"
sys.path.insert(0, str(ANALYSIS))
SPEC = importlib.util.spec_from_file_location(
    "recompute_claims", ANALYSIS / "recompute_claims.py"
)
assert SPEC is not None and SPEC.loader is not None
recompute = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(recompute)


class RecomputeClaimsTest(unittest.TestCase):
    def test_complete_public_recomputation(self) -> None:
        report = recompute.run_all()
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["m8n"]["exact_game_comparisons_rerun"], 43)
        self.assertTrue(report["rs_full_sigma"]["ordinary_event_counterexample_replayed"])
        self.assertEqual(
            report["m8t"]["source_to_supplied_certificate_semantic_verifications"],
            2,
        )
        self.assertEqual(report["m8t"]["unique_controller_pairs"], 1)
        self.assertEqual(report["m8t"]["independent_win_synthesis"], 0)
        self.assertEqual(report["m8t"]["source_to_win_replay"], 0)
        self.assertEqual(
            report["m8u"]["generated_win_certificate_semantic_verifications"],
            3,
        )
        self.assertEqual(report["m8u"]["provenance_clusters"], 2)
        self.assertTrue(report["m8u"]["industry_whole_system_block"])
        self.assertFalse(report["m8u"]["industry_nontrivial_factorization"])
        self.assertEqual(report["m8u"]["historical_outcome_inputs"], 0)
        self.assertEqual(report["m8u"]["supplied_certificate_inputs"], 0)
        self.assertEqual(report["m8u"]["source_to_win_replay"], 0)

    def test_c3_raw_status_mutation_is_rejected(self) -> None:
        source = ROOT / "evidence/m8m-source-anchored/raw_runs.csv"
        with source.open("r", encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
            fieldnames = list(rows[0])
        rows[0]["process_status"] = "UNREALIZABLE"
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "mutated.csv"
            with target.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            with self.assertRaises(recompute.ClaimError):
                recompute.validate_c3_rows(
                    target,
                    "prospective_ardrone_v13_corrected_replay",
                    config_path=ROOT / "evidence/m8m-source-anchored/config.json",
                    plan_path=ROOT / "evidence/m8m-source-anchored/plan.json",
                    expected_runtime="dd494999ffa1d0f4029b5f07988f408182d8a362a77926da436716a7221c751d",
                )

    def test_c2_missing_repetition_is_rejected(self) -> None:
        rows = recompute.read_csv(ROOT / "evidence/m8k-performance/raw_runs.csv")
        with self.assertRaises(recompute.ClaimError):
            recompute.model_median_ratios(rows[:-1], "states_discovered")

    def test_c2_reported_family_statistic_mutation_is_rejected(self) -> None:
        rows = recompute.read_csv(ROOT / "evidence/m8k-performance/raw_runs.csv")
        mutated = copy.deepcopy(rows)
        target = next(row["model_id"] for row in mutated if row["model_family"] == "independent_one_state_reconfiguration")
        changed = 0
        for row in mutated:
            if row["model_id"] == target and row["method_id"] == "fg_ducs_otf" and changed < 3:
                row["states_discovered"] = str(int(row["states_discovered"]) + 1000)
                changed += 1
        with self.assertRaises(recompute.ClaimError):
            recompute.require_c2_paper_statistics(recompute.c2_family_statistics(mutated))

    def test_game_bucket_mutation_is_rejected(self) -> None:
        case = ROOT / "evidence/m8n-game-equivalence/cases/winning__identity"
        left_raw = json.loads((case / "java-independent-game.json").read_text())
        right_raw = json.loads((case / "python-observer-exact-game.json").read_text())
        mutated = copy.deepcopy(right_raw)
        mutated["buckets"][0]["controllable"] = not mutated["buckets"][0]["controllable"]
        left = recompute.load_game_bundle(left_raw)
        with self.assertRaises((ValueError, recompute.NonIsomorphic)):
            right = recompute.load_game_bundle(mutated)
            recompute.compare_games(
                left,
                right,
                maximum_search_nodes=100_000,
                require_typed_state_translation=False,
            )


if __name__ == "__main__":
    unittest.main()
