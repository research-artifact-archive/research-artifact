#!/usr/bin/env python3
"""Infrastructure fixtures, never experimental observations or timing samples."""
from pathlib import Path
import copy, csv, tempfile, unittest
from unittest.mock import patch
import campaign as c

def row(rep,status='SUCCESS',method='fg_ducs_otf'):
    return dict(job_id='m__base__rep%02d__%s'%(rep,method),model_id='m',target_id='base',method_id=method,
        repetition=rep,process_status=status,invalid=False,inconsistent=False,
        internal_certificate_check='passed',link_checker='passed',run_verified='false',
        evaluation_csv_found=True,elapsed_monotonic_seconds=str(rep),solver_time_ms=str(rep*10),peak_rss_bytes=str(rep*100))

class OrchestrationTests(unittest.TestCase):
    def test_resource_failure_stops_unstarted_repetitions(self):
        for failure in ('TIMEOUT','OOM'):
            rows=[row(1),row(2,failure),row(3,'NOT_RUN'),row(4,'NOT_RUN'),row(5,'NOT_RUN')]
            for job in rows[2:]:self.assertEqual(c.next_action(job,rows)[0],'SKIPPED_AFTER_RESOURCE_FAILURE')

    def test_stage1_resource_failure_excludes_all_four(self):
        rows=[row(1,'OOM')]+[row(rep,'NOT_RUN') for rep in range(2,6)]
        for job in rows[1:]:self.assertEqual(c.next_action(job,rows)[0],'SKIPPED_AFTER_RESOURCE_FAILURE')

    def test_invalid_or_disagreement_excludes(self):
        for field in ('invalid','inconsistent'):
            rows=[row(1),row(2,'NOT_RUN')];rows[0][field]=True
            self.assertEqual(c.next_action(rows[1],rows)[0],'SKIPPED_AFTER_INVALID_OR_INCONSISTENT')

    def aggregate(self,rows):
        config=dict(repetitions=5,backend='lts');plan=dict(jobs=[dict(**{k:r[k] for k in ('job_id','model_id','target_id','method_id','repetition')},jvm_properties={}) for r in rows])
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(c.collector,'collect',return_value=(copy.deepcopy(rows),[],{})):
                return c.summarize(config,Path(temp),plan)

    def test_five_consistent_completions_only_have_statistics(self):
        _,summary=self.aggregate([row(rep) for rep in range(1,6)])
        self.assertTrue(summary[0]['timing_summary_eligible']);self.assertEqual(summary[0]['solver_time_ms_median'],30)
        _,summary=self.aggregate([row(1),row(2,'TIMEOUT')]+[row(rep,'SKIPPED_AFTER_RESOURCE_FAILURE') for rep in range(3,6)])
        self.assertFalse(summary[0]['timing_summary_eligible']);self.assertEqual(summary[0]['solver_time_ms_median'],'')

    def test_decision_disagreement_and_checker_failure_are_explicit(self):
        rows=[row(rep) for rep in range(1,6)];rows[2]['process_status']='UNREALIZABLE'
        raw,summary=self.aggregate(rows)
        self.assertTrue(summary[0]['inconsistent']);self.assertEqual(summary[0]['solver_time_ms_median'],'')
        rows=[row(rep) for rep in range(1,6)];rows[2]['internal_certificate_check']='failed'
        raw,summary=self.aggregate(rows)
        self.assertTrue(raw[2]['invalid']);self.assertTrue(summary[0]['invalid']);self.assertEqual(summary[0]['solver_time_ms_median'],'')

    def test_legacy_decision_difference_is_context_only(self):
        rows=[row(rep) for rep in range(1,6)]+[row(rep,'UNREALIZABLE','legacy_ducs') for rep in range(1,6)]
        _,summary=self.aggregate(rows)
        self.assertTrue(all(not r['inconsistent'] for r in summary))

    def test_same_problem_method_disagreement_is_explicit(self):
        rows=[row(rep) for rep in range(1,6)]+[row(rep,'UNREALIZABLE','direct_full') for rep in range(1,6)]
        _,summary=self.aggregate(rows)
        self.assertTrue(all(r['inconsistent'] for r in summary))

    def test_old_hub_expected_winning_does_not_invalidate_checked_loss(self):
        r=row(1);r['output_path']='hub.csv'
        value=dict(status='unexpected_decision',decision='losing',certificate_valid='true',
                   certificate_verification_status='passed',decision_matches_expected='false',solver_time_ns='1000')
        job=dict(**{k:r[k] for k in ('job_id','model_id','target_id','method_id','repetition')},jvm_properties={})
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)
            with (path/'hub.csv').open('w',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=list(value));writer.writeheader();writer.writerow(value)
            with patch.object(c.collector,'collect',return_value=([r],[],{})):
                raw,summary=c.summarize(dict(repetitions=1,backend='synthetic_hub'),path,dict(jobs=[job]))
            self.assertEqual(raw[0]['process_status'],'UNREALIZABLE');self.assertFalse(raw[0]['invalid']);self.assertTrue(raw[0]['expected_mismatch'])

    def test_skipping_writes_terminal_rows_without_overwriting(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);job=row(3,'NOT_RUN')
            c.skip(folder,job,'SKIPPED_AFTER_RESOURCE_FAILURE','OOM at repetition 2')
            path=folder/'runs'/job['job_id']/'meta.json';before=path.read_bytes()
            c.skip(folder,job,'SUCCESS','must not overwrite');self.assertEqual(path.read_bytes(),before)

if __name__=='__main__':unittest.main(verbosity=2)
