#!/usr/bin/env python3
"""Validate extraction against existing first-trial raw and run timeout boundaries."""
from __future__ import annotations

import csv
import os
import tempfile
import time
import unittest
from pathlib import Path

import ablation_common as common
import run_ablation as runner

HERE = Path(__file__).resolve().parents[1]
XEON = HERE.parent / 'rq3_xeon'


class AblationChecks(unittest.TestCase):
    def test_old_first_trial_extraction_matches_collected_csv(self):
        checked = 0
        with (XEON / 'raw/rq3/stage1.csv').open(newline='') as stream:
            for saved in csv.DictReader(stream):
                if saved['method_id'] not in {'fg_ducs_otf', 'fg_ducs_otf_eager_controllable', 'direct_full'}:
                    continue
                trial = common.read_trial(XEON / 'raw/rq3/runs' / saved['job_id'] / 'meta.json')
                if saved['process_status'] in {'SUCCESS', 'UNREALIZABLE'}:
                    self.assertEqual(trial['decision'], saved['decision'], saved['job_id'])
                    self.assertEqual(trial['states_discovered'], saved['states_discovered'], saved['job_id'])
                    self.assertEqual(trial['successor_queries'], saved['successor_queries'], saved['job_id'])
                    self.assertEqual(trial['validation_errors'], '', saved['job_id'])
                    checked += 1
                elif saved['process_status'] == 'TIMEOUT':
                    self.assertEqual(trial['decision'], 'TO')
                    self.assertEqual(trial['states_discovered'], '')
        self.assertGreater(checked, 50)

    def test_exact_plans(self):
        e2 = list(common.planned_jobs(common.read_json(HERE / 'configs/e2_mac.json')))
        e1 = list(common.planned_jobs(common.read_json(HERE / 'configs/e1_mac.json')))
        xeon = list(common.planned_jobs(common.read_json(XEON / 'configs/abl_e2_ucpruned.json')))
        self.assertEqual(len(e2), 27)
        self.assertEqual(len(e1), 54)
        self.assertEqual(e2, xeon)
        self.assertEqual({j['target_id'] for j in e1}, {'base', 'r1'})
        self.assertEqual({j['merge'] for j in e1}, {'transfers', 'boundaries', 'both'})

    def test_extended_budget_state_only(self):
        from analyze_ablation import analyze_e2
        analyze_e2()
        with (HERE / 'tables/e2_comparison.csv').open(newline='') as stream:
            rows = list(csv.DictReader(stream))
        ext = [r for r in rows if r['df_states_source'] == 'extended_budget_single_trial']
        self.assertEqual(len(ext), 4)
        for row in ext:
            self.assertEqual(row['df_fixed_decision'], 'TO')
            self.assertEqual(row['df_queries'], '')
            self.assertEqual(float(row['df_states_timeout_seconds']), 7200)
        reference = [r for r in rows if r['reference_only'] == 'True']
        self.assertEqual(len(reference), 2)
        self.assertTrue(all(r['ucpruned_decision'] == 'NOT_PLANNED' for r in reference))

    def test_timeout_preserves_attempt_and_shared_lock(self):
        with tempfile.TemporaryDirectory(dir=HERE) as temporary:
            root = Path(temporary)
            executable = root / 'fake-java'
            executable.write_text('#!/usr/bin/env python3\nimport time\ntime.sleep(20)\n')
            executable.chmod(0o755)
            (root / 'input.lts').write_text('fixture')
            config = dict(java=str(executable), java_heap='32g', classpath='fixture.jar', main_class='Fixture', platform='mac')
            job = dict(job_id='fixture', model_path='input.lts', target_name='FIXTURE', jvm_properties={})
            provenance = dict(jar_sha256='fixture', source_commit='fixture')
            campaign = root / 'raw'
            before = time.monotonic()
            result = runner.run_trial(config, job, 0.1, 'test_timeout', campaign, root, provenance)
            self.assertEqual(result['decision'], 'TO')
            self.assertLess(time.monotonic() - before, 7)
            meta = campaign / 'test_timeout/runs/fixture/meta.json'
            original = meta.read_bytes()
            runner.run_trial(config, job, 0.1, 'test_timeout', campaign, root, provenance)
            self.assertEqual(meta.read_bytes(), original, 'existing attempt was overwritten')
            with runner.execution_lock(root / 'shared.lock'):
                with self.assertRaises(RuntimeError):
                    with runner.execution_lock(root / 'shared.lock'):
                        pass

    def test_invalid_certificate_is_not_a_decision(self):
        fixture = XEON / 'raw/rq3/runs/gsm__base__rep01__fg_ducs_otf'
        with tempfile.TemporaryDirectory(dir=HERE) as temporary:
            root = Path(temporary)
            meta = common.read_json(fixture / 'meta.json')
            text = (fixture / 'output.txt').read_text()
            text = text.replace('revised_internal_certificate_check,Internal certificate check,passed',
                                'revised_internal_certificate_check,Internal certificate check,failed')
            # A changed output is independently rejected by its preserved digest.
            (root / 'output.txt').write_text(text + '\nmodified\n')
            common.write_json(root / 'meta.json', meta)
            result = common.read_trial(root / 'meta.json')
            self.assertEqual(result['decision'], 'INVALID')
            self.assertIn('digest mismatch', result['validation_errors'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
