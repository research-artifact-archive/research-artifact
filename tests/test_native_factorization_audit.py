#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "analysis"
if str(ANALYSIS) not in sys.path:
    sys.path.insert(0, str(ANALYSIS))

import audit_native_factorization as native_audit  # noqa: E402
from audit_native_factorization import AuditError, audit  # noqa: E402


class NativeFactorizationAuditTest(unittest.TestCase):
    def test_registered_panel_and_focused_evidence(self) -> None:
        observed = audit()
        stored = json.loads(
            (ROOT / "evidence/m8q-native-factorization/summary.json").read_text(encoding="utf-8")
        )
        self.assertEqual(observed, stored)
        self.assertEqual(observed["target_cells"], 41)
        self.assertEqual(observed["producer_verified_refined_win_cells"], 2)
        self.assertEqual(observed["producer_verified_refined_win_clusters"], 1)
        self.assertEqual(
            observed["refined_local_solver_sums"]["arms2-r2"],
            {"states": 127174, "queries": 831356, "outcomes": 294632},
        )
        self.assertIn("producer remains TCB", observed["claim_boundary"])

    def test_legacy_timeout_record_is_fail_closed(self) -> None:
        baseline = json.loads(
            (ROOT / "evidence/m8q-native-factorization/legacy-productioncell-baseline.json").read_text(encoding="utf-8")
        )
        row = next(
            item for item in baseline["rows"]
            if item["target_id"] == "r2" and item["method_id"] == "fg_ducs_otf"
        )
        row["timed_out"] = "False"
        original = native_audit.BASELINE
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", dir=ROOT) as stream:
            json.dump(baseline, stream)
            stream.flush()
            native_audit.BASELINE = Path(stream.name)
            try:
                with self.assertRaises(AuditError):
                    native_audit.verify_baseline()
            finally:
                native_audit.BASELINE = original


if __name__ == "__main__":
    unittest.main()
