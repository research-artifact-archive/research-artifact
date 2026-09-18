#!/usr/bin/env python3
"""Boundary probes for the revised raw oracle, outside the fixed 92-job cohort."""
import tempfile
import unittest
from pathlib import Path
from rederive_oracle import ROOT, graph, solve

BASE = ROOT / 'Implementation/Experiment/FSE2027/results/macos24-paper-final-20260805g-correctness/inputs/semantic_boundaries_v2/Models/winning__identity.lts'


class RevisedRawOracleTest(unittest.TestCase):
    def model(self, old_body=None, new_body=None):
        text = BASE.read_text()
        if old_body:
            text = text.replace('OLD_COMPONENT = (idle -> OLD_COMPONENT).', old_body)
        if new_body:
            text = text.replace('NEW_COMPONENT = (idle -> NEW_COMPONENT).', new_body)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / 'probe.lts'
        path.write_text(text)
        return path

    def test_new_uncontrollable_loop_changes_win_to_loss(self):
        path = self.model(new_body='NEW_COMPONENT = (idle -> NEW_COMPONENT | u -> NEW_COMPONENT).')
        self.assertEqual(solve(graph(path, revised=False)[0])[0], 'realizable')
        current, rejected = graph(path)
        self.assertEqual(solve(current)[0], 'unrealizable')
        self.assertTrue(rejected)
        self.assertFalse(current.goals)

    def test_old_uncontrollable_loop_removes_transfer_bucket(self):
        path = self.model(old_body='OLD_COMPONENT = (idle -> OLD_COMPONENT | u -> OLD_COMPONENT).')
        prior, _ = graph(path, revised=False)
        current, _ = graph(path)
        root = next(iter(current.initial_states))
        self.assertIn('reconfigure_COMPONENT', prior.successors[root])
        self.assertNotIn('reconfigure_COMPONENT', current.successors[root])
        self.assertIn('u', current.successors[root])
        self.assertEqual(solve(current)[0], 'unrealizable')

    def test_finite_uncontrollable_suffix_reaches_quiescence(self):
        path = self.model(new_body='NEW_COMPONENT = (u -> NEW_QUIET),\nNEW_QUIET = (idle -> NEW_QUIET).')
        current, rejected = graph(path)
        result, rank = solve(current)
        self.assertEqual(result, 'realizable')
        self.assertTrue(rejected)
        self.assertTrue(current.goals)
        self.assertTrue(all(s[1] == ('NEW_QUIET',) for s in current.goals))
        self.assertGreater(max(rank[s] for s in current.initial_states), 1)


if __name__ == '__main__':
    unittest.main()
