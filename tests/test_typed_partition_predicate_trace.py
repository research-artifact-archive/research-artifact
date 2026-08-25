#!/usr/bin/env python3
"""Tests for the complete M8p predicate trace."""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "analysis"
sys.path.insert(0, str(ANALYSIS))

import trace_typed_partition_predicate as trace  # noqa: E402
import discover_typed_partition as producer  # noqa: E402
import check_typed_partition_certificate as independent_consumer  # noqa: E402


class PredicateTraceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.path = ROOT / "inputs/c2/typed-partition-predicate-example.json"
        cls.game = json.loads(cls.path.read_text(encoding="utf-8"))

    def test_complete_two_unit_trace(self) -> None:
        report = trace.generate(self.game)
        self.assertEqual(report["unit_partition_count"], 2)
        self.assertEqual(report["first_accepted_block_count"], 2)
        self.assertTrue(report["all_accepted_candidates_transport_ready"])
        self.assertTrue(all(row["accepted"] for row in report["partitions"]))
        two = next(row for row in report["partitions"] if row["block_count"] == 2)
        self.assertTrue(all(two["conjuncts"].values()))
        self.assertEqual(len(two["derived_local_games"]), 2)
        self.assertEqual(
            sorted(len(game["states"]) for game in two["derived_local_games"]),
            [2, 2],
        )
        self.assertEqual(len(two["cartesian_context_rows"]), 8)
        self.assertEqual(len(two["shared_stutter_rows"]), 4)
        self.assertTrue(all(row["context_present"] for row in two["cartesian_context_rows"]))

        certificate = producer.discover(self.game)
        checked = independent_consumer.check(self.game, certificate, max_atoms=8)
        self.assertEqual(checked["status"], "PASS")
        self.assertEqual(
            checked["maximum_block_count"],
            report["first_accepted_block_count"],
        )

    def test_foreign_context_enabledness_is_not_omitted(self) -> None:
        mutated = copy.deepcopy(self.game)
        mutated["buckets"] = [
            row
            for row in mutated["buckets"]
            if not (row["source"] == "q01" and row["action"] == "advance-a")
        ]
        report = trace.generate(mutated)
        two = next(row for row in report["partitions"] if row["block_count"] == 2)
        self.assertFalse(two["conjuncts"]["context_independent_complete_post"])
        self.assertFalse(two["accepted"])
        self.assertEqual(report["first_accepted_block_count"], 1)

    def test_foreign_frame_change_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.game)
        row = next(
            item
            for item in mutated["buckets"]
            if item["source"] == "q00" and item["action"] == "advance-a"
        )
        row["targets"] = ["q11"]
        report = trace.generate(mutated)
        two = next(row for row in report["partitions"] if row["block_count"] == 2)
        self.assertFalse(two["conjuncts"]["foreign_frame"])
        self.assertFalse(two["accepted"])

    def test_correlated_roots_are_a_declared_stricter_boundary(self) -> None:
        mutated = copy.deepcopy(self.game)
        next(row for row in mutated["states"] if row["id"] == "q11")["initial"] = False
        report = trace.generate(mutated)
        two = next(row for row in report["partitions"] if row["block_count"] == 2)
        self.assertFalse(two["conjuncts"]["root_rectangular"])
        self.assertFalse(two["accepted"])
        self.assertEqual(report["first_accepted_block_count"], 1)
        self.assertIn("strictly broader", report["root_boundary"])


if __name__ == "__main__":
    unittest.main()
