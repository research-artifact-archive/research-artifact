from __future__ import annotations

import importlib.util
from pathlib import Path
import math
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "analysis" / "strong_rank_certificate_core.py"
SPEC = importlib.util.spec_from_file_location("strong_rank_certificate_core", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
CORE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CORE
SPEC.loader.exec_module(CORE)


class TableGame:
    def __init__(self, roots, goals, safe, controllable, table):
        self._roots = tuple(roots)
        self._goals = set(goals)
        self._safe = set(safe)
        self._controllable = set(controllable)
        self._table = dict(table)

    def roots(self):
        return self._roots

    def safe(self, state):
        return state in self._safe

    def goal(self, state):
        return state in self._goals

    def candidates(self, state):
        return sorted(action for source, action in self._table if source == state)

    def post(self, state, action):
        return self._table[(state, action)]

    def controllable(self, action):
        return action in self._controllable

    def state_payload(self, state):
        return {"state": state}

    def action_payload(self, action):
        return {"action": action}

    def action_order_key(self, state, action):
        return (0, action)


class StrongRankCoreTest(unittest.TestCase):
    def test_uncontrollable_requires_every_bucket_and_every_outcome(self):
        game = TableGame(
            roots=["r"], goals=["g"], safe=["r", "a", "g"],
            controllable=[],
            table={
                ("r", "u1"): ("g", "a"),
                ("r", "u2"): ("g",),
                ("a", "u3"): ("g",),
            },
        )
        result = CORE.synthesize_strong_rank(game)
        self.assertTrue(result.is_win)
        ranks = {row.payload["state"]: row.rank
                 for row in result.certificate.states}
        self.assertEqual({"r": 2, "a": 1, "g": 0}, ranks)
        selected = {(bucket.source_key, bucket.action_payload["action"])
                    for bucket in result.certificate.strategy_buckets}
        root_key = CORE.canonical_json({"state": "r"})
        self.assertIn((root_key, "u1"), selected)
        self.assertIn((root_key, "u2"), selected)

    def test_one_controllable_bucket_is_selected_deterministically(self):
        game = TableGame(
            roots=["r"], goals=["g"], safe=["r", "g", "bad"],
            controllable=["a", "b", "z"],
            table={
                ("r", "b"): ("g",),
                ("r", "a"): ("g",),
                ("r", "z"): ("bad",),
            },
        )
        result = CORE.synthesize_strong_rank(game)
        self.assertTrue(result.is_win)
        strategies = result.certificate.strategy_buckets
        self.assertEqual(1, len(strategies))
        selected = next(bucket for bucket in result.certificate.candidate_buckets
                        if bucket.action_key == strategies[0].action_key)
        self.assertEqual("a", selected.action_payload["action"])
        self.assertEqual(3, len(result.certificate.candidate_buckets))
        self.assertNotIn(
            "bad",
            {state.payload["state"] for state in result.certificate.states},
        )

    def test_pending_update_priority_precedes_lexical_normal_action(self):
        game = TableGame(
            roots=["r"], goals=["g"], safe=["r", "g"],
            controllable=["a-normal", "z-pending-update"],
            table={
                ("r", "a-normal"): ("g",),
                ("r", "z-pending-update"): ("g",),
            },
        )
        game.action_order_key = lambda _state, action: (
            0 if action == "z-pending-update" else 1, action)
        result = CORE.synthesize_strong_rank(game)
        self.assertTrue(result.is_win)
        self.assertEqual(
            ["z-pending-update"],
            [bucket.action_payload["action"]
             for bucket in result.certificate.strategy_buckets],
        )

    def test_rank_bound_is_inconclusive_and_never_loss(self):
        game = TableGame(
            roots=["r"], goals=["g"], safe=["r", "a", "g"],
            controllable=["c"],
            table={("r", "c"): ("a",), ("a", "c"): ("g",)},
        )
        result = CORE.synthesize_strong_rank(
            game, CORE.SynthesisLimits(max_rank=1))
        self.assertEqual("INCONCLUSIVE", result.status)
        self.assertEqual("ROOT_NOT_PROVED_WIN_WITHIN_RANK_BOUND", result.reason)
        self.assertFalse(result.to_json()["loss_claimed"])

    def test_unsafe_root_and_deadlock_do_not_become_loss_claims(self):
        for game in (
            TableGame(["r"], [], [], [], {}),
            TableGame(["r"], [], ["r"], [], {}),
        ):
            with self.subTest(game=game):
                result = CORE.synthesize_strong_rank(game)
                self.assertEqual("INCONCLUSIVE", result.status)
                self.assertEqual(
                    "ROOT_NOT_PROVED_WIN_WITHIN_RANK_BOUND",
                    result.reason,
                )
                self.assertFalse(result.to_json()["loss_claimed"])

    def test_state_limit_is_inconclusive(self):
        game = TableGame(
            roots=["r"], goals=["g"], safe=["r", "a", "g"],
            controllable=["c"],
            table={("r", "c"): ("a",), ("a", "c"): ("g",)},
        )
        result = CORE.synthesize_strong_rank(
            game, CORE.SynthesisLimits(max_states=2))
        self.assertEqual("INCONCLUSIVE", result.status)
        self.assertEqual("STATE_LIMIT", result.reason)

    def test_bool_is_rejected_as_exact_rank_bound(self):
        with self.assertRaises(ValueError):
            CORE.SynthesisLimits(max_rank=True)

    def test_nonfinite_timeout_is_rejected(self):
        for value in (math.nan, math.inf, -math.inf, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                CORE.SynthesisLimits(timeout_seconds=value)

    def test_admissible_rank_lower_bound_preserves_minimum_ranks(self):
        game = TableGame(
            roots=["r"], goals=["g"], safe=["r", "a", "g"],
            controllable=["c"],
            table={("r", "c"): ("a",), ("a", "c"): ("g",)},
        )
        lower = {"r": 2, "a": 1, "g": 0}
        game.rank_lower_bound = lambda state: lower[state]
        result = CORE.synthesize_strong_rank(game)
        self.assertTrue(result.is_win)
        self.assertEqual(
            {"r": 2, "a": 1, "g": 0},
            {state.payload["state"]: state.rank
             for state in result.certificate.states},
        )

    def test_invalid_rank_lower_bound_is_rejected(self):
        for value in (True, -1):
            game = TableGame(["r"], [], ["r"], [], {})
            game.rank_lower_bound = lambda _state, result=value: result
            with self.subTest(value=value), self.assertRaisesRegex(
                    ValueError, "lower bound"):
                CORE.synthesize_strong_rank(game)

    def test_duplicate_candidate_is_rejected(self):
        game = TableGame(["r"], ["r"], ["r"], [], {})
        game.candidates = lambda state: ("a", "a")
        with self.assertRaisesRegex(ValueError, "duplicated"):
            CORE.synthesize_strong_rank(game)

    def test_converging_diamond_retains_exact_final_strategy_closure(self):
        game = TableGame(
            roots=["r"], goals=["g"],
            safe=["r", "left", "right", "join", "orphan", "g"],
            controllable=["a", "b"],
            table={
                ("r", "u"): ("left", "right"),
                ("left", "a"): ("join",),
                ("left", "b"): ("orphan",),
                ("right", "a"): ("join",),
                ("join", "a"): ("g",),
                ("orphan", "a"): ("g",),
            },
        )
        result = CORE.synthesize_strong_rank(game)
        self.assertTrue(result.is_win)
        retained = {state.payload["state"]
                    for state in result.certificate.states}
        self.assertEqual({"r", "left", "right", "join", "g"}, retained)
        self.assertNotIn("orphan", retained)


if __name__ == "__main__":
    unittest.main()
