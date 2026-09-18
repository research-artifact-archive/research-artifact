#!/usr/bin/env python3
"""Read-only raw checks and display regressions; no synthesis, no solver changes."""
from pathlib import Path
import contextlib, io, json, runpy, tempfile, unittest
from render_fidelity import HERE, classify, collect, csv_bytes, generate

class ReturnedFidelity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.output = Path(cls.temp.name) / 'generated'
        with contextlib.redirect_stdout(io.StringIO()):
            cls.stats = generate(HERE/'raw/xeon', HERE/'bundle_delta/configs', cls.output)
        cls.rows = collect(HERE, HERE/'raw/xeon', HERE/'bundle_delta/configs')

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    def test_full_denominator_and_skips(self):
        self.assertEqual((self.stats['conditions'], self.stats['families']), (21, 8))
        self.assertEqual((self.stats['planned_slots'], self.stats['executed_trials'], self.stats['skipped_slots']), (210, 190, 20))

    def test_decisions_vs_first_trial_sizes(self):
        self.assertEqual((self.stats['published_wins'], self.stats['fork_wins']), (21, 16))
        self.assertEqual((self.stats['size_matches'], self.stats['size_mismatches']), (15, 1))
        self.assertEqual(self.stats['size_variable_tool_conditions'], 4)

    def test_known_exceptions_only(self):
        self.assertEqual((self.stats['parser_nm'], self.stats['instrumentation_nm']), (3, 2))
        row = next(r for r in self.rows if r['model_id']=='gsm_supplied')
        with self.assertRaises(ValueError): classify(row, 'unrelated exception')
        with self.assertRaises(ValueError): classify(row, 'ltsa.lts.LTSException: name already defined  T_NO_UPDATE_WHILE_SEND')

    def test_raw_crash_and_no_censored_medians(self):
        crashed = [r for r in self.rows if r['fork_stage1_status']=='CRASH']
        self.assertEqual(len(crashed), 5)
        for row in crashed:
            self.assertEqual(row['fork_decision'], 'UNDECIDED')
            self.assertEqual(row['fork_elapsed_monotonic_seconds_median'], '')

    def test_original_deployed_collector_bytes(self):
        root = Path(self.temp.name)/'deployed'; root.mkdir()
        (root/'configs').symlink_to(HERE/'bundle_delta/configs', target_is_directory=True)
        (root/'raw').symlink_to(HERE/'raw/xeon', target_is_directory=True)
        old = runpy.run_path(str(HERE/'bundle_delta/scripts/collect_legacy_fidelity.py'))
        self.assertEqual(csv_bytes(old['collect'](root)), csv_bytes(self.rows))
        self.assertEqual((HERE/'raw/xeon/legacy_fidelity_comparison.local.csv').read_bytes(), csv_bytes(self.rows))

    def test_first_trial_scope_and_variation_present(self):
        text = (self.output/'legacy-fidelity-reference.tex').read_text()
        self.assertIn('first-trial states/transitions', text)
        self.assertIn('429/651', text)
        self.assertIn('102/150', text)
        self.assertIn('SIZE-', text)
        self.assertIn('N/M', text)

    def test_different_timing_scopes(self):
        text = (self.output/'legacy-fidelity-resources.tex').read_text()
        self.assertIn('No cross-tool ratios', text)
        self.assertIn('different scopes', text)
        self.assertIn('no median is reported', text)

if __name__ == '__main__': unittest.main(verbosity=2)
