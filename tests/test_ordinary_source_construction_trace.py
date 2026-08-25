#!/usr/bin/env python3
"""Mutation tests for the ordinary-source construction trace."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "analysis"
sys.path.insert(0, str(ANALYSIS))

import check_ordinary_source_construction_trace as trace  # noqa: E402


class OrdinarySourceConstructionTraceTest(unittest.TestCase):
    def fixture_root(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        for relative in set(trace.INPUT_PATHS.values()) | {trace.TRACE_REL}:
            source = ROOT / relative
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        return temporary, root

    @staticmethod
    def load(path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def save(path: Path, value: dict) -> None:
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")

    def assert_rejected(self, mutate) -> None:
        temporary, root = self.fixture_root()
        self.addCleanup(temporary.cleanup)
        mutate(root)
        with self.assertRaises(trace.TraceError):
            trace.validate(root, root / trace.TRACE_REL)

    def test_valid_trace(self) -> None:
        result = trace.validate(ROOT, ROOT / trace.TRACE_REL)
        self.assertEqual(result["status"], "PASS")
        self.assertFalse(result["source_to_win_replay"])

    def test_rejects_mutated_source_bytes(self) -> None:
        self.assert_rejected(lambda root: (root / trace.SOURCE_REL).write_bytes((root / trace.SOURCE_REL).read_bytes() + b"\n"))

    def test_rejects_mutated_facts(self) -> None:
        def mutate(root: Path) -> None:
            path = root / trace.INPUT_PATHS["facts"]
            value = self.load(path)
            value["definition"] = "mutated"
            self.save(path, value)
        self.assert_rejected(mutate)

    def test_rejects_mutated_bundle(self) -> None:
        def mutate(root: Path) -> None:
            path = root / trace.INPUT_PATHS["bundle"]
            value = self.load(path)
            value["terminal_product_verified"] = False
            self.save(path, value)
        self.assert_rejected(mutate)

    def test_rejects_missing_sourcein_field(self) -> None:
        def mutate(root: Path) -> None:
            path = root / trace.TRACE_REL
            value = self.load(path)
            value["source_in"].pop()
            self.save(path, value)
        self.assert_rejected(mutate)

    def test_rejects_flipped_stage_predicate(self) -> None:
        def mutate(root: Path) -> None:
            path = root / trace.TRACE_REL
            value = self.load(path)
            value["stage_replay"][0]["predicate_outcomes"][0]["status"] = "FAIL"
            self.save(path, value)
        self.assert_rejected(mutate)

    def test_rejects_missing_y_field(self) -> None:
        def mutate(root: Path) -> None:
            path = root / trace.TRACE_REL
            value = self.load(path)
            value["output_y"].pop()
            self.save(path, value)
        self.assert_rejected(mutate)

    def test_rejects_scope_upgrade_or_missing_theorem_map(self) -> None:
        def mutate(root: Path) -> None:
            path = root / trace.TRACE_REL
            value = self.load(path)
            value["theorem_map"]["source_S1_S7"].pop()
            value["claim_boundary"]["source_to_win_replay"] = True
            self.save(path, value)
        self.assert_rejected(mutate)


if __name__ == "__main__":
    unittest.main()
