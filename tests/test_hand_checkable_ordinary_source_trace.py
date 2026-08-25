#!/usr/bin/env python3

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "analysis"
if str(ANALYSIS) not in sys.path:
    sys.path.insert(0, str(ANALYSIS))

from check_hand_checkable_ordinary_source_trace import (  # noqa: E402
    TRACE_PATH,
    TraceError,
    check,
    load,
    parse_source_text,
)


class HandCheckableOrdinarySourceTraceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.trace = load(TRACE_PATH)

    def assert_rejected(self, trace: dict) -> None:
        with self.assertRaises(TraceError):
            check(trace)

    def test_exact_formal_trace(self) -> None:
        report = check(self.trace)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["global_post_buckets"], 12)
        self.assertEqual(report["relation_pairs"], 4)
        self.assertFalse(report["stored_bundle_is_execution_provenance"])

    def test_source_extra_declaration_rejected(self) -> None:
        source = (ROOT / "inputs/correctness/r09-hand-k02.lts").read_text(encoding="utf-8")
        with self.assertRaises(TraceError):
            parse_source_text(source + "EXTRA=(idle->EXTRA).\n")

    def test_source_owner_mutation_rejected(self) -> None:
        source = (ROOT / "inputs/correctness/r09-hand-k02.lts").read_text(encoding="utf-8")
        with self.assertRaises(TraceError):
            parse_source_text(source.replace("R2={O2@O2", "R2={O1@O1"))

    def test_missing_post_bucket_rejected(self) -> None:
        self.trace["formal_global_game"]["complete_post_table"].pop()
        self.assert_rejected(self.trace)

    def test_nonstuttering_idle_rejected(self) -> None:
        self.trace["formal_global_game"]["complete_post_table"][0]["outcomes"] = ["q10"]
        self.assert_rejected(self.trace)

    def test_relation_pair_omission_rejected(self) -> None:
        self.trace["formal_global_game"]["R_Gamma"].pop()
        self.assert_rejected(self.trace)

    def test_nondecreasing_policy_rank_rejected(self) -> None:
        self.trace["formal_global_game"]["fixed_priority_policy_cases"][0]["rank_sum"] = [2, 2]
        self.assert_rejected(self.trace)

    def test_full_gamma_selector_required(self) -> None:
        self.trace["output_y"]["fields"]["Gamma"]["load_selectors"] = []
        self.assert_rejected(self.trace)

    def test_theorem_number_mapping_error_rejected(self) -> None:
        changed = copy.deepcopy(self.trace)
        changed["theorem_map"]["Theorem_5_3"]["premise_family"] = "S1--S7"
        self.assert_rejected(changed)

    def test_scientific_scope_promotion_rejected(self) -> None:
        self.trace["claim_boundary"]["independent_source_to_win_replay"] = True
        self.assert_rejected(self.trace)


if __name__ == "__main__":
    unittest.main()
