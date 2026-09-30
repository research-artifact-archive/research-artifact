#!/usr/bin/env python3
"""Temporary infrastructure fixtures; these are not experimental observations."""
import copy
import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import analyze_ext as a


class ExtendedAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.raw = self.root / "raw"; self.raw.mkdir()
        self.configs = self.root / "configs"; self.configs.mkdir()
        self.name = "ext1_fixture"
        self.job = dict(job_id="m__base__rep01__direct_full", model_id="m", target_id="base",
                        method_id="direct_full", repetition=1, global_order_index=0)
        self.config = dict(repetitions=1, java_heap="64g", timeout_seconds=7200)
        (self.configs / (self.name + ".json")).write_text("{}")
        self.folder = self.raw / self.name
        self.run = self.folder / "runs" / self.job["job_id"]
        self.run.mkdir(parents=True)

    def meta(self, status="SUCCESS", **extra):
        meta = dict(job=self.job, completed=True, status=status,
                    elapsed_monotonic_seconds=20, peak_rss_bytes=2 * 1024**3,
                    timeout_seconds=7200, classpath={"sha256": a.JAR_SHA},
                    command=["java", "-Xmx64g"], artifacts={"output": "runs\\" + self.job["job_id"] + "\\output.txt"})
        meta.update(extra)
        (self.run / "meta.json").write_text(json.dumps(meta))
        (self.run / "output.txt").write_text("fixture")

    def baseline(self, **extra):
        row = dict(model_id="m", target_id="base", method_id="fg_ducs_otf", stage1_status="SUCCESS",
                   timing_summary_eligible=True, planned_total_repetitions=5, completed_valid_repetitions=5,
                   invalid=False, inconsistent=False, elapsed_monotonic_seconds_median=4,
                   solver_time_ms_median=2000)
        row.update(extra)
        folder = self.raw / "rq3"; folder.mkdir(exist_ok=True)
        with (folder / "summary.csv").open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(row)); writer.writeheader(); writer.writerow(row)

    def rows(self, result="SUCCESS", certificate="passed"):
        with patch.object(a.common, "load_config", return_value=self.config), \
             patch.object(a.common, "build_plan", return_value={"jobs": [self.job]}), \
             patch.object(a.common, "parse_evaluation_file", return_value={"found": True, "errors": []}), \
             patch.object(a.common, "output_summary", return_value=dict(evaluation_result=result,
                         solver_time_ms="6000", states_discovered="17", internal_certificate_check=certificate,
                         link_checker="passed")):
            return a.build_rows(self.raw, self.configs)

    def test_missing_return_is_not_zero_or_timeout(self):
        self.baseline()
        row = self.rows()[0]
        self.assertEqual(row["status"], "NOT_RUN")
        self.assertEqual(row["elapsed_seconds"], "")
        self.assertEqual(row["single_over_lazy_fixed_elapsed_ratio"], "")

    def test_distinct_timer_scopes_and_windows_paths(self):
        self.meta(); self.baseline()
        row = self.rows()[0]
        self.assertTrue(row["valid_decision"])
        self.assertEqual(row["single_over_lazy_fixed_elapsed_ratio"], 5)
        self.assertEqual(row["single_over_lazy_fixed_solver_ratio"], 3)
        self.assertEqual(row["peak_rss_gib"], 2)
        self.assertEqual(row["states_discovered"], 17)

    def test_resource_failure_and_skip_never_gain_ratio(self):
        self.baseline()
        for status in ("TIMEOUT", "OOM", "SKIPPED_MONOTONE", "INTERRUPTED_NOT_RETRIED"):
            self.meta(status)
            row = self.rows()[0]
            self.assertEqual(row["status"], status)
            self.assertEqual(row["single_over_lazy_fixed_elapsed_ratio"], "")

    def test_partial_or_inconsistent_baseline_has_no_median_ratio(self):
        self.meta()
        for extra in ({"completed_valid_repetitions": 4}, {"inconsistent": True}, {"timing_summary_eligible": False}):
            self.baseline(**extra)
            self.assertEqual(self.rows()[0]["single_over_lazy_fixed_elapsed_ratio"], "")

    def test_valid_loss_can_be_compared_but_disagreement_cannot(self):
        self.meta("UNREALIZABLE"); self.baseline(stage1_status="UNREALIZABLE")
        self.assertEqual(self.rows(result="UNREALIZABLE")[0]["single_over_lazy_fixed_elapsed_ratio"], 5)
        self.baseline()
        row = self.rows(result="UNREALIZABLE")[0]
        self.assertIs(row["decision_agreement"], False)
        self.assertEqual(row["single_over_lazy_fixed_elapsed_ratio"], "")

    def test_provenance_or_checker_failures_preserve_status_and_hide_ratio(self):
        self.baseline()
        for extra in ({"classpath": {"sha256": "wrong"}}, {"timeout_seconds": 1200}, {"command": ["java", "-Xmx200g"]}):
            self.meta(**extra)
            row = self.rows()[0]
            self.assertEqual(row["status"], "SUCCESS")
            self.assertFalse(row["valid_decision"])
            self.assertEqual(row["single_over_lazy_fixed_elapsed_ratio"], "")
        self.meta()
        self.assertFalse(self.rows(certificate="failed")[0]["valid_decision"])
        self.assertFalse(self.rows(result="UNREALIZABLE")[0]["valid_decision"])

    def test_wrong_job_or_escaping_artifact_is_rejected(self):
        self.meta(job={**self.job, "method_id": "fg_ducs_otf"})
        with self.assertRaisesRegex(ValueError, "identity"):
            self.rows()
        self.meta(artifacts={"output": "../other/output.txt"})
        with self.assertRaisesRegex(ValueError, "leaves"):
            self.rows()

    def test_in_progress_is_incomplete_not_a_valid_success(self):
        self.meta(completed=False); self.baseline()
        row = self.rows()[0]
        self.assertEqual(row["status"], "INCOMPLETE")
        self.assertFalse(row["valid_decision"])

    def test_render_retains_all_statuses_and_does_not_mutate_input(self):
        self.meta("SKIPPED_MONOTONE", skip_reason="smaller configuration timed out")
        rows = self.rows(); before = copy.deepcopy(rows)
        evidence = {p: p.read_bytes() for p in self.raw.rglob("*") if p.is_file()}
        result = a.render(rows, self.root / "generated")
        self.assertEqual(result["statuses"], {"SKIPPED_MONOTONE": 1})
        self.assertEqual(rows, before)
        self.assertEqual(evidence, {p: p.read_bytes() for p in self.raw.rglob("*") if p.is_file()})
        self.assertIn("SKIPPED_MONOTONE", (self.root / "generated/ext-budget.csv").read_text())
        self.assertIn("SKIPPED\\_MONOTONE", (self.root / "generated/ext-budget.tex").read_text())
        self.assertIn(r"\providecommand{\ExtBudgetSkipped}{1}", (self.root / "generated/ext-budget-macros.tex").read_text())

    def test_prose_uses_checked_single_trial_wall_time_not_solver_time(self):
        self.meta(); rows = self.rows()
        row = rows[0]
        row.update(campaign="ext2_rq3_df_cpu", model_id="industry", target_id="r1",
                   elapsed_seconds=1695.2248, solver_seconds=1693.3275, states_discovered=110825,
                   status="UNREALIZABLE")
        macros = a.report_macros(rows)
        self.assertEqual(macros["ExtIndustryDFSeconds"], "1{,}695")
        self.assertEqual(macros["ExtIndustryDFStates"], "110{,}825")
        self.assertEqual(macros["ExtBudgetLosses"], 1)
        self.assertEqual(macros["ExtTravelFourEightLazySeconds"], "--")
        row["valid_decision"] = False
        self.assertEqual(a.report_macros(rows)["ExtIndustryDFSeconds"], "--")
        self.assertEqual(a.report_macros(rows)["ExtBudgetLosses"], 0)

    def test_unresolved_fixed_baselines_are_not_decision_matches(self):
        self.meta(); template = self.rows()[0]
        rows = [{**template, "model_id": f"m{i}", "decision_agreement": True if i < 5 else ""}
                for i in range(8)]
        macros = a.report_macros(rows)
        self.assertEqual(macros["ExtFixedComparable"], 5)
        self.assertEqual(macros["ExtFixedMatches"], 5)
        self.assertEqual(macros["ExtFixedUncompared"], 3)

    def test_resource_bounds_use_all_matched_cells_and_round_outwards(self):
        self.meta("TIMEOUT"); template = self.rows()[0]
        template.update(campaign="ext4_rq3_df_heap200", heap="200g", method_fixed_status="TIMEOUT",
                        lazy_fixed_solver_median_seconds=37.0656, lazy_fixed_peak_rss_median_gib=7.362209)
        rows = [{**template, "model_id": "m1", "peak_rss_gib": 159.4118},
                {**template, "model_id": "m2", "peak_rss_gib": 212.5252}]
        macros = a.report_macros(rows)
        self.assertEqual(macros["ExtDFHeapTimeoutRSSMin"], "159")
        self.assertEqual(macros["ExtDFHeapTimeoutRSSMax"], "213")
        self.assertEqual(macros["ExtLazyHeapPairs"], 2)
        self.assertEqual(macros["ExtLazyHeapSolverUpper"], "37.1")
        self.assertEqual(macros["ExtLazyHeapRSSUpper"], "7.4")
        self.assertEqual(macros["ExtDFBothUnresolved"], 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
