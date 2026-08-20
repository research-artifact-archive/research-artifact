from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "analysis" / "check_residual_soundness.py"
SPEC = importlib.util.spec_from_file_location("residual_check", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
residual_check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(residual_check)


class ResidualSoundnessTest(unittest.TestCase):
    def test_registered_full_sigma_cases(self) -> None:
        report = residual_check.check_manifest(ROOT / "inputs/rs/manifest.json")
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["decision_counts"], {"SOUND": 2, "UNSOUND": 1})
        counterexample = next(
            case for case in report["cases"] if case["id"] == "ordinary_event_counterexample"
        )["counterexample"]
        self.assertEqual(counterexample["activation_prefix"], ["a", "start_r"])
        self.assertEqual(counterexample["continuation"], ["b"])
        conservative = next(
            case for case in report["cases"] if case["id"] == "conservative_initialization"
        )
        self.assertEqual(conservative["residuals_by_xi"], {"X": ["m0"]})

    def test_underapproximating_old_history_is_rejected_or_hides_counterexample(self) -> None:
        fixture = json.loads(
            (ROOT / "inputs/rs/ordinary-event-counterexample.json").read_text(encoding="utf-8")
        )
        mutated = copy.deepcopy(fixture)
        mutated["activation"]["states"].remove("old_after_a")
        mutated["activation"]["old_endpoint_states"].remove("old_after_a")
        mutated["activation"]["states"].remove("update_after_a")
        mutated["activation"]["update_phase_states"].remove("update_after_a")
        mutated["activation"]["transitions"] = [
            edge for edge in mutated["activation"]["transitions"]
            if edge["source"] not in {"old_after_a", "update_after_a"}
            and edge["target"] not in {"old_after_a", "update_after_a"}
        ]
        report = residual_check.check_fixture(mutated)
        self.assertEqual(report["decision"], "SOUND")
        self.assertIsNone(report["counterexample"])

    def test_old_history_edge_cannot_be_relabelled_as_update_phase(self) -> None:
        fixture = json.loads(
            (ROOT / "inputs/rs/ordinary-event-counterexample.json").read_text(encoding="utf-8")
        )
        fixture["activation"]["old_endpoint_states"].remove("old_after_a")
        fixture["activation"]["update_phase_states"].append("old_after_a")
        with self.assertRaises(residual_check.ResidualCheckError):
            residual_check.check_fixture(fixture)

    def test_empty_error_set_is_a_valid_tautological_monitor(self) -> None:
        fixture = json.loads(
            (ROOT / "inputs/rs/conservative-initialization.json").read_text(encoding="utf-8")
        )
        fixture["monitor"]["error_states"] = []
        report = residual_check.check_fixture(fixture)
        self.assertEqual(report["decision"], "SOUND")

    def test_nondeterministic_observer_is_rejected(self) -> None:
        fixture = json.loads(
            (ROOT / "inputs/rs/conservative-initialization.json").read_text(encoding="utf-8")
        )
        fixture["observer"]["transitions"].append(
            {"source": "obs", "event": "a", "target": "obs", "output": []}
        )
        with self.assertRaises(residual_check.ResidualCheckError):
            residual_check.check_fixture(fixture)


if __name__ == "__main__":
    unittest.main()
