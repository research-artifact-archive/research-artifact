#!/usr/bin/env python3
"""Safety and evidence-classification tests; no synthesis or saved input edits."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import quickstart as q


class QuickstartTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'package'
        self.root.mkdir()
        self.out = Path(self.temp.name) / 'output'

    def runner(self):
        return q.Quickstart(self.root, self.out)

    def test_existing_output_is_rejected_without_overwriting(self):
        self.out.mkdir()
        sentinel = self.out / 'quickstart-report.md'
        sentinel.write_text('preserved report')
        with self.assertRaises(FileExistsError):
            self.runner()
        self.assertEqual(sentinel.read_text(), 'preserved report')

    def test_copy_is_independent_and_original_mutation_is_detected(self):
        original = self.root / 'evidence.json'
        original.write_text('original')
        runner = self.runner()
        copied = runner.copy(Path('evidence.json'))
        copied.write_text('checker output')
        self.assertEqual(original.read_text(), 'original')
        self.assertIn('1 checked', runner.originals_unchanged())
        original.write_text('unexpected external edit')
        with self.assertRaisesRegex(ValueError, 'preserved input'):
            runner.originals_unchanged()

    def test_comparison_checks_denominator_duplicates_and_values(self):
        expected = [{'id': 'a', 'decision': 'WIN'}, {'id': 'b', 'decision': 'LOSS'}]
        self.assertEqual(q.compare_rows(expected[::-1], expected, ('id',)), 2)
        for bad in (expected[:1], [expected[0], expected[0]],
                    [expected[0], {'id': 'b', 'decision': 'WIN'}]):
            with self.assertRaises(ValueError):
                q.compare_rows(bad, expected, ('id',))

    def test_archive_absence_is_skip_but_corruption_is_failure(self):
        data = self.root / 'raw/a.json'
        data.parent.mkdir()
        data.write_text('{}')
        record = {'path': 'raw/a.json', 'bytes': data.stat().st_size, 'sha256': q.digest(data)}
        (self.root / 'result-assets.json').write_text(json.dumps({'files': [record]}))
        runner = self.runner()
        self.assertEqual(runner.archived([Path('raw')]), 1)
        data.unlink()
        with self.assertRaises(q.Unavailable):
            runner.archived([Path('raw')])
        data.write_text('{"changed": true}')
        with self.assertRaisesRegex(ValueError, 'archive identity'):
            runner.archived([Path('raw')])

    def test_path_escape_and_external_symlink_are_rejected(self):
        runner = self.runner()
        for path in ('../outside', str(self.out)):
            with self.assertRaises(ValueError):
                runner.copy(Path(path))
        outside = Path(self.temp.name) / 'secret'
        outside.write_text('outside')
        (self.root / 'link').symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'escapes'):
            runner.copy(Path('link'))

    def test_report_keeps_skip_and_failure_distinct(self):
        runner = self.runner()
        def missing():
            raise q.Unavailable('not restored')
        def bad():
            raise ValueError('wrong evidence')
        with contextlib.redirect_stdout(io.StringIO()):
            runner.action('ok', 'Checked claim', '1', lambda: '1')
            runner.action('skip', 'Unavailable claim', '2', missing)
            runner.action('bad', 'Contradicted claim', '3', bad)
            exit_code = runner.finish()
        self.assertEqual(exit_code, 1)
        report = json.loads((self.out / 'quickstart-report.json').read_text())
        self.assertEqual([r['status'] for r in report['checks']], ['PASS', 'SKIP', 'FAIL'])
        self.assertEqual(report['status'], 'FAIL')

    def test_timeout_preserves_partial_output_and_failure_log(self):
        runner = self.runner()
        with patch.object(q.subprocess, 'run', side_effect=subprocess.TimeoutExpired('python', 300, output=b'partial evidence')):
            with self.assertRaisesRegex(RuntimeError, 'TIMEOUT'):
                runner.command('timed', runner.work / 'script.py')
        log = (runner.logs / 'timed.log').read_text()
        self.assertIn('partial evidence', log)
        self.assertIn('EXIT: TIMEOUT', log)


if __name__ == '__main__':
    unittest.main()
