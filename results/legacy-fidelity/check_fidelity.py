#!/usr/bin/env python3
"""Non-experiment fixtures: plan, adapter CSV, classpath, and failure preservation."""
from pathlib import Path
import copy,csv,json,os,sys,tempfile,unittest
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'bundle_delta/scripts'))
import campaign as c
sys.path.insert(0,str(HERE))
import collect_legacy_fidelity as compare

def row(rep,status='SUCCESS'):
    return dict(job_id='m__target__rep%02d__published_mtsa'%rep,model_id='m',target_id='target',method_id='published_mtsa',repetition=rep,process_status=status,output_path='output.txt',evaluation_csv_found=True,solver_status='REALIZABLE' if status=='SUCCESS' else 'UNREALIZABLE',elapsed_monotonic_seconds=str(rep),peak_rss_bytes=str(rep*100))
class Tests(unittest.TestCase):
    def aggregate(self,rows,decision='REALIZABLE'):
        plan=dict(jobs=[dict(**{k:r[k] for k in ['job_id','model_id','target_id','method_id','repetition']},jvm_properties={}) for r in rows])
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'output.txt').write_text('================ EVALUATION DATA CSV ================\nmetric_key,value,mode,result,solver_status\npublished_compile_compose_time_ms,25,published_mtsa,'+decision+','+decision+'\noutput_update_controller_states,2312,published_mtsa,'+decision+','+decision+'\n================ EVALUATION SUMMARY ================\n')
            with patch.object(c.collector,'collect',return_value=(copy.deepcopy(rows),[],{})):
                return c.summarize(dict(repetitions=5,backend='published_mtsa'),p,plan)
    def test_registered_denominators_and_methods(self):
        for tool in ['published','fork']:
            cfg=c.common.load_config(HERE/'bundle_delta/configs'/('legacy_fidelity_'+tool+'.json'));plan=c.common.build_plan(cfg)
            self.assertEqual(len(plan['jobs']),105);self.assertEqual(sum(j['repetition']==1 for j in plan['jobs']),21)
            self.assertEqual({j['method_id'] for j in plan['jobs']},{'published_mtsa' if tool=='published' else 'legacy_ducs'})
            self.assertEqual(sum(m['family']=='MetaSocket' for m in cfg['models']),8)
    def test_published_has_no_fabricated_fg_checker_requirement(self):
        raw,summary=self.aggregate([row(i) for i in range(1,6)])
        self.assertTrue(all(not r['invalid'] for r in raw));self.assertTrue(summary[0]['timing_summary_eligible']);self.assertEqual(summary[0]['solver_time_ms_median'],25)
    def test_published_decision_mismatch_invalid(self):
        rows=[row(i) for i in range(1,6)];rows[0]['solver_status']='UNREALIZABLE'
        raw,summary=self.aggregate(rows);self.assertTrue(raw[0]['invalid']);self.assertFalse(summary[0]['timing_summary_eligible'])
    def test_timeout_after_success_has_no_success_only_median(self):
        raw,s=self.aggregate([row(1),row(2,'TIMEOUT')]+[row(i,'SKIPPED_AFTER_RESOURCE_FAILURE') for i in range(3,6)])
        self.assertFalse(s[0]['timing_summary_eligible']);self.assertEqual(s[0]['solver_time_ms_median'],'')
    def test_windows_classpath_separator_and_argument_boundaries(self):
        cfg=c.common.load_config(HERE/'bundle_delta/configs/legacy_fidelity_published.json');job=c.common.build_plan(cfg)['jobs'][0]
        with patch.object(c.os,'pathsep',';'):
            args=c.command(cfg,job,HERE/'bundle_delta',Path('out space.txt'),Path('trans space.txt'))
        value=args[args.index('-cp')+1];self.assertEqual(value.count(';'),1);self.assertIn('original-mtsa',value);self.assertIn('published-mtsa-runner',value)
        self.assertEqual(args[args.index('--output')+1],str(Path('out space.txt').resolve()))
    def test_empty_conditions_not_invented(self):
        with (HERE/'inputs.csv').open(newline='') as f:rows=list(csv.DictReader(f))
        missing=[r for r in rows if r['missing_reason']];self.assertEqual({r['model'] for r in missing},{'MetaSocket','PowerPlant'});self.assertEqual(len(missing),4)
        for r in rows:
            if not r['missing_reason']:self.assertEqual(int(r['fluent_reset_lines_changed']),3 if r['tool']=='fork' else 0)
    def test_reference_comparison_preserves_all_pending_cells(self):
        rows=compare.collect(HERE/'bundle_delta');self.assertEqual(len(rows),21);self.assertTrue(all(r['decision_agreement']=='UNDECIDED' for r in rows))
if __name__=='__main__':unittest.main(verbosity=2)
