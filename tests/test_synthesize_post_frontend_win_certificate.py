from __future__ import annotations

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "analysis"
sys.path.insert(0, str(SCRIPTS))
MODULE_PATH = SCRIPTS / "synthesize_post_frontend_win_certificate.py"
SPEC = importlib.util.spec_from_file_location(
    "synthesize_post_frontend_win_certificate", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
GENERATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GENERATOR
SPEC.loader.exec_module(GENERATOR)


PC_BASE_IR = (
    ROOT / "evidence" /
    "m8s-post-frontend-contract-certificate" / "cases" /
    "productioncell-arms2-base-productioncell-arms-2-fg" / "facts.json"
)


class GeneratorBoundaryTest(unittest.TestCase):
    def test_strict_ir_loader_binds_unsorted_bytes_without_requiring_lf(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ir.json"
            raw = b'{"z":1,"a":2}'
            path.write_bytes(raw)
            value, loaded = GENERATOR.load_strict(path)
        self.assertEqual({"z": 1, "a": 2}, value)
        self.assertEqual(raw, loaded)

    def test_strict_ir_loader_rejects_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ir.json"
            path.write_bytes(b'{"a":1,"a":2}')
            with self.assertRaisesRegex(GENERATOR.GenerationError,
                                        "invalid strict JSON"):
                GENERATOR.load_strict(path)

    def test_forbidden_conclusion_field_is_rejected_recursively(self):
        with self.assertRaisesRegex(GENERATOR.GenerationError,
                                    "forbidden conclusion field"):
            GENERATOR.reject_ir_conclusions({"nested": [{"strategy": []}]})

    def test_pending_update_order_precedes_lexical_normal_action(self):
        state = GENERATOR.Config((), (), frozenset({"z-update"}))
        game = GENERATOR.ProblemGame(None)
        self.assertLess(
            game.action_order_key(state, "z-update"),
            game.action_order_key(state, "a-normal"),
        )

    def test_inconclusive_document_is_deterministic_and_never_loss(self):
        binding = {
            "sha256": "0" * 64,
            "size": 1,
            "source_name": "x",
            "source_sha256": "1" * 64,
            "definition": "D",
        }
        first = GENERATOR._inconclusive(binding, "STATE_LIMIT", 0)
        second = GENERATOR._inconclusive(binding, "STATE_LIMIT", 0)
        self.assertEqual(
            GENERATOR.canonical_bytes(first.document),
            GENERATOR.canonical_bytes(second.document),
        )
        self.assertEqual("INCONCLUSIVE", first.document["decision"])
        self.assertFalse(first.document["loss_claimed"])
        self.assertNotIn(b"LOSS", GENERATOR.canonical_bytes(first.document))
        self.assertNotIn(b"elapsed", GENERATOR.canonical_bytes(first.document))

    def test_cli_rejects_historical_bundle_argument_as_invalid(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "out.json"
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                status = GENERATOR.main([
                    "--ir", "facts.json", "--output", str(output),
                    "--historical-bundle", "bundle.json",
                ])
        self.assertEqual(3, status)
        self.assertIn("INVALID=invalid arguments", stderr.getvalue())
        self.assertFalse(output.exists())

    def test_pc_base_two_fresh_generations_are_byte_identical(self):
        ir, raw = GENERATOR.load_strict(PC_BASE_IR)
        first = GENERATOR.generate(ir, raw)
        second = GENERATOR.generate(ir, raw)
        first_bytes = GENERATOR.canonical_bytes(first.document)
        second_bytes = GENERATOR.canonical_bytes(second.document)
        self.assertEqual("WIN", first.status)
        self.assertEqual(first_bytes, second_bytes)
        certificate = json.loads(first_bytes)
        self.assertEqual("WIN", certificate["decision"])
        self.assertEqual(
            "BOUNDED_MINIMUM_STRONG_RANK_PENDING_UPDATE_THEN_LEXICAL_V1",
            certificate["generator_boundary"]["algorithm"],
        )
        self.assertNotIn(b"elapsed", first_bytes)
        self.assertNotIn(b"exploration", first_bytes)


if __name__ == "__main__":
    unittest.main()
