#!/usr/bin/env python3
"""Infrastructure fixtures, never experimental observations or timing samples."""
from pathlib import Path
import copy, csv, io, json, re, tempfile, unittest
from contextlib import redirect_stdout
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


class ExtendedBudgetTests(unittest.TestCase):
    """Scheduling fixtures use synthetic metadata, never JVM experiments."""
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);(self.root/'raw').mkdir();(self.root/'configs').mkdir()

    def config(self,name):
        return copy.deepcopy(c.common.load_config(c.ROOT/'configs'/(name+'.json')))

    def campaign(self,name,config=None):
        config=self.config(name) if config is None else config
        folder=self.root/'raw'/name;plan=c.common.build_plan(config)
        c.initialize(config,folder,plan)
        return folder,config,plan

    def terminal(self,source,index,status):
        folder,config,plan=source;job=plan['jobs'][index]
        meta=dict(completed=True,status=status,job=job,artifacts={},
                  config_sha256=c.common.file_digest(folder/'config.json')['sha256'],plan_sha256=plan['plan_sha256'])
        c.json_write(folder/'runs'/job['job_id']/'meta.json',meta)
        return meta

    def action(self,source,index):
        folder,config,plan=source
        return c.ext_stage1_action(config,folder,plan,plan['jobs'][index])

    def test_original_six_plans_match_saved_bytes(self):
        before=c.ROOT/'raw/ext-preflight-20260927/original-plans'
        # This optional local integration evidence is not needed in the delta.
        if not before.is_dir():self.skipTest('Pre-edit plan bytes are kept in local preflight evidence')
        for name in ('pilot','rq3','rq4_controlled','rq4_independent','rq4_travel','rq4_hub'):
            config_path=c.ROOT/'configs'/(name+'.json')
            self.assertEqual(config_path.read_bytes(),(before/(name+'.config.json')).read_bytes())
            plan=c.common.build_plan(c.common.load_config(config_path));path=self.root/(name+'.json')
            c.json_write(path,plan);self.assertEqual(path.read_bytes(),(before/(name+'.json')).read_bytes())

    def test_all_ext_counts_order_and_frozen_methods(self):
        names=('ext1_travel_frontier','ext2_rq3_df_cpu','ext3_travel_next','ext4_rq3_df_heap200','ext5_travel_heap200')
        originals={m['id']:m for m in c.common.load_config(c.ROOT/'configs/rq3.json')['methods']}
        for name,count in zip(names,(4,2,5,12,4)):
            config=self.config(name);plan=c.common.build_plan(config)
            self.assertEqual(plan['job_count'],count);self.assertEqual(len({j['job_id'] for j in plan['jobs']}),count)
            self.assertEqual([j['global_order_index'] for j in plan['jobs']],list(range(count)))
            self.assertTrue(all(j['repetition']==1 for j in plan['jobs']))
            self.assertEqual(config['timeout_seconds'],7200)
            for method in config['methods']:self.assertEqual(method,originals[method['id']])
        plan=c.common.build_plan(self.config(names[0]))
        self.assertEqual([j['model_factors']['K'] for j in plan['jobs']],[4,6,8,8])
        plan=c.common.build_plan(self.config(names[3]))
        self.assertEqual([c.cell(j)[:2] for j in plan['jobs']],
            [('railcab','base'),('surveillance','base'),('workflow','base'),('workflow','r1'),('railcab','r1'),
             ('productioncell_arms2','base'),('productioncell_arms2','r1'),('surveillance','r1'),('workflow','r2'),
             ('surveillance','r2'),('productioncell_arms2','r2'),('productioncell_arms2','r2')])
        plan=c.common.build_plan(self.config(names[4]))
        self.assertEqual([j['model_factors']['K'] for j in plan['jobs']],[1,1,4,4])
        for j in plan['jobs']:
            p=j['prerequisites'][0]
            leaves=p.get('any_of',[p])
            for leaf in leaves:
                self.assertEqual(leaf['model_id'],'travel_n06_k01');self.assertEqual(leaf['method_id'],j['method_id'])
            if j['model_factors']['K']==1:self.assertEqual(p['requires'],'not_SUCCESS')
            else:
                self.assertEqual([leaf['campaign'] for leaf in leaves],['ext3_travel_next','ext5_travel_heap200'])
                self.assertTrue(all(leaf['requires']=='SUCCESS' for leaf in leaves))

    def test_sequence_rejects_duplicate_cells_and_unknown_selection(self):
        config=self.config('ext4_rq3_df_heap200')
        config['unit_sequence'].append(config['unit_sequence'][0])
        with self.assertRaisesRegex(ValueError,'duplicate job'):c.common.validate_config(config)
        config=self.config('ext4_rq3_df_heap200');config['unit_sequence'][0]['method_ids']=['unknown']
        with self.assertRaisesRegex(ValueError,'unknown methods'):c.common.validate_config(config)

    def test_options_are_opt_in_and_old_configs_ignore_no_ext_policy(self):
        config=c.common.load_config(c.ROOT/'configs/rq4_travel.json')
        plan=c.common.build_plan(config)
        self.assertIsNone(c.ext_stage1_action(config,self.root/'absent',plan,plan['jobs'][0]))
        config['unit_order']='listed'
        with self.assertRaisesRegex(ValueError,'extended_budget'):c.common.validate_config(config)

    def test_resource_failure_skips_only_larger_same_method(self):
        for status in ('TIMEOUT','OOM'):
            with self.subTest(status=status):
                source=self.campaign('ext1_travel_frontier');self.terminal(source,0,status)
                self.assertEqual(self.action(source,1)[0],'SKIPPED_MONOTONE')
                self.assertIsNone(self.action(source,2));self.assertIsNone(self.action(source,3))

    def test_nonresource_failures_and_skips_are_not_propagated(self):
        source=self.campaign('ext1_travel_frontier')
        for status in ('CRASH','INVALID_INPUT','UNREALIZABLE','SKIPPED_MONOTONE','INTERRUPTED_NOT_RETRIED'):
            self.terminal(source,0,status)
            self.assertIsNone(self.action(source,1),status)

    def test_incomparable_scaling_dimensions_do_not_propagate(self):
        source=self.campaign('ext3_travel_next');self.terminal(source,0,'TIMEOUT')
        # N4/K8 does not dominate N6/K1 in the componentwise order.
        self.assertIsNone(self.action(source,4))

    def test_cross_campaign_requires_opt_in_and_equal_heap_cap(self):
        first=self.campaign('ext1_travel_frontier');self.terminal(first,0,'TIMEOUT')
        current=self.campaign('ext3_travel_next')
        self.assertEqual(self.action(current,0)[0],'SKIPPED_MONOTONE')
        for field,value in [('monotone_sources',[]),('java_heap','200g'),('timeout_seconds',14400)]:
            folder,config,plan=current;changed=copy.deepcopy(config);changed[field]=value
            self.assertIsNone(c.ext_stage1_action(changed,folder,plan,plan['jobs'][0]),field)

    def test_missing_incomplete_and_wrong_status_prerequisite_skip(self):
        current=self.campaign('ext3_travel_next')
        self.assertEqual(json.loads(self.action(current,2)[1])['kind'],'prerequisite_not_met')
        first=self.campaign('ext1_travel_frontier')
        for status in ('TIMEOUT','CRASH','UNREALIZABLE','SKIPPED_MONOTONE'):
            self.terminal(first,2,status);self.assertIsNotNone(self.action(current,2))
        meta=self.terminal(first,2,'SUCCESS');meta['completed']=False
        c.json_write(first[0]/'runs'/first[2]['jobs'][2]['job_id']/'meta.json',meta)
        self.assertIsNotNone(self.action(current,2))

    def test_success_prerequisite_needs_certificate_and_link(self):
        current=self.campaign('ext3_travel_next');first=self.campaign('ext1_travel_frontier')
        self.terminal(first,2,'SUCCESS')
        success=dict(job_id=first[2]['jobs'][2]['job_id'],evaluation_csv_found=True,
                     internal_certificate_check='passed',link_checker='passed')
        with patch.object(c.collector,'collect',return_value=([success],[],{})):
            self.assertIsNone(self.action(current,2))
        success['link_checker']='failed'
        with patch.object(c.collector,'collect',return_value=([success],[],{})):
            self.assertIsNotNone(self.action(current,2))

    def success_rows(self,*sources):
        return [dict(job_id=job['job_id'],evaluation_csv_found=True,internal_certificate_check='passed',link_checker='passed')
                for folder,config,plan in sources for job in plan['jobs']]

    def test_ext5_64g_success_skips_200g_k1_but_runs_k4(self):
        prior=self.campaign('ext3_travel_next');current=self.campaign('ext5_travel_heap200')
        self.terminal(prior,3,'SUCCESS')
        with patch.object(c.collector,'collect',return_value=(self.success_rows(prior),[],{})):
            self.assertIsNotNone(self.action(current,0));self.assertIsNone(self.action(current,2))
        # Other method has no evidence, so its K1 runs but its K4 does not.
        self.assertIsNone(self.action(current,1));self.assertIsNotNone(self.action(current,3))

    def test_ext5_64g_non_success_then_200g_success_permits_k4(self):
        prior=self.campaign('ext3_travel_next');current=self.campaign('ext5_travel_heap200')
        self.terminal(prior,3,'TIMEOUT');self.terminal(prior,4,'OOM')
        self.assertIsNone(self.action(current,0));self.assertIsNone(self.action(current,1))
        self.assertIsNotNone(self.action(current,2));self.assertIsNotNone(self.action(current,3))
        self.terminal(current,0,'SUCCESS')
        with patch.object(c.collector,'collect',return_value=(self.success_rows(current),[],{})):
            self.assertIsNone(self.action(current,2));self.assertIsNotNone(self.action(current,3))

    def test_ext5_200g_resource_failure_keeps_k4_skipped(self):
        prior=self.campaign('ext3_travel_next');current=self.campaign('ext5_travel_heap200')
        self.terminal(prior,3,'TIMEOUT');self.terminal(prior,4,'OOM')
        for failure in ('TIMEOUT','OOM'):
            self.terminal(current,0,failure)
            self.assertIsNotNone(self.action(current,2))
            self.assertIsNone(self.action(current,1)) # Independent DF gate.

    def test_ext5_missing_or_incomplete_prior_permits_k1_with_explicit_reason(self):
        current=self.campaign('ext5_travel_heap200')
        self.assertIsNone(self.action(current,0));self.assertIsNotNone(self.action(current,2))
        observation=c.ext_prerequisite_checks(current[0],current[2]['jobs'][0])[0]
        self.assertTrue(observation['satisfied']);self.assertIsNone(observation['observed_status'])
        self.assertIn('source unavailable',observation['reason'])
        prior=self.campaign('ext3_travel_next');meta=self.terminal(prior,3,'SUCCESS');meta['completed']=False
        c.json_write(prior[0]/'runs'/prior[2]['jobs'][3]['job_id']/'meta.json',meta)
        self.assertIsNone(self.action(current,0));self.assertIsNotNone(self.action(current,2))
        self.assertEqual(c.ext_prerequisite_checks(current[0],current[2]['jobs'][0])[0]['reason'],'incomplete terminal record')

    def test_not_success_does_not_allow_self_or_future_reference(self):
        current=self.campaign('ext5_travel_heap200');job=copy.deepcopy(current[2]['jobs'][0])
        job['prerequisites'][0]['campaign']='ext5_travel_heap200'
        observation=c.ext_prerequisite_checks(current[0],job)[0]
        self.assertFalse(observation['satisfied']);self.assertIn('self/future',observation['reason'])

    def test_or_schema_rejects_empty_or_mixed_boolean_expression(self):
        for bad in ({'any_of':[]},{'any_of':[], 'requires':'SUCCESS'}, {'requires':'not_SUCCESS'}):
            with self.assertRaises(ValueError):c.common.validate_prerequisite(bad)

    def test_tampered_terminal_digest_cannot_satisfy_success_prerequisite(self):
        prior=self.campaign('ext3_travel_next');current=self.campaign('ext5_travel_heap200')
        meta=self.terminal(prior,3,'SUCCESS');meta['config_sha256']='changed'
        c.json_write(prior[0]/'runs'/prior[2]['jobs'][3]['job_id']/'meta.json',meta)
        self.assertIsNone(self.action(current,0))
        self.assertEqual(json.loads(self.action(current,2)[1])['kind'],'prerequisite_not_met')

    def test_stage1_and_resume_never_repeat_terminal_or_skipped_jobs(self):
        name='ext1_travel_frontier';config=self.config(name)
        c.json_write(self.root/'configs'/(name+'.json'),config)
        calls=[]
        def fake_run(cfg,cs,ps,root,folder,job,env):
            self.assertEqual(c.runner.ORDER_ALGORITHM,'listed-units/listed-methods-v1')
            calls.append(job['job_id'])
            meta=dict(completed=True,status='TIMEOUT',job=job,artifacts={},config_sha256=cs,
                      plan_sha256=ps,elapsed_monotonic_seconds=1)
            c.json_write(folder/'runs'/job['job_id']/'meta.json',meta);return meta
        with patch.object(c,'ROOT',self.root),patch.object(c,'preflight',return_value='fixture'),\
             patch.object(c.runner,'run_job',side_effect=fake_run),patch('sys.argv',['campaign.py','--config',name,'--stage','stage1']),redirect_stdout(io.StringIO()):
            c.main();folder=self.root/'raw'/name
            before={p:p.read_bytes() for p in (folder/'runs').glob('*/meta.json')}
            c.main()
        self.assertEqual(len(calls),3) # DF K6 skipped after DF K4 TO; two other methods execute.
        self.assertTrue(all(p.read_bytes()==data for p,data in before.items()))
        self.assertEqual(len(before),4)
        statuses=[json.loads(data)['status'] for data in before.values()]
        self.assertEqual(statuses.count('SKIPPED_MONOTONE'),1)

    def test_ext5_main_records_missing_evidence_and_keeps_four_cell_denominator(self):
        name='ext5_travel_heap200';config=self.config(name)
        c.json_write(self.root/'configs'/(name+'.json'),config);calls=[]
        def fake_run(cfg,cs,ps,root,folder,job,env):
            calls.append(job['job_id'])
            meta=dict(completed=True,status='TIMEOUT',job=job,artifacts={},config_sha256=cs,
                      plan_sha256=ps,elapsed_monotonic_seconds=1)
            c.json_write(folder/'runs'/job['job_id']/'meta.json',meta);return meta
        with patch.object(c,'ROOT',self.root),patch.object(c,'preflight',return_value='fixture'),\
             patch.object(c.runner,'run_job',side_effect=fake_run),patch('sys.argv',['campaign.py','--config',name,'--stage','stage1']),redirect_stdout(io.StringIO()):
            c.main();folder=self.root/'raw'/name
            before={p:p.read_bytes() for p in (folder/'runs').rglob('*.json')};c.main()
        self.assertEqual(len(calls),2)
        self.assertTrue(all(p.read_bytes()==data for p,data in before.items()))
        metas=list((folder/'runs').glob('*/meta.json'));self.assertEqual(len(metas),4)
        observations=list((folder/'runs').glob('*/prerequisites-*.json'));self.assertEqual(len(observations),4)
        for path in observations:
            value=json.loads(path.read_text())
            if 'k01__' in value['job_id']:
                self.assertTrue(value['checks'][0]['satisfied'])
                self.assertIn('source unavailable',value['checks'][0]['reason'])

    def test_published_backend_is_preserved(self):
        config={'backend':'published_mtsa','runner_classpath':'adapter.jar'}
        with patch.object(c,'ORIGINAL_COMMAND',return_value=['java','-cp','original.jar','Runner']):
            cmd=c.command(config,{},Path('/bundle'),Path('out'),Path('transitions'))
        self.assertIn('adapter.jar',cmd[2]);self.assertTrue(cmd[2].endswith('original.jar'))

    def test_driver_retains_old_and_reference_stages(self):
        text=(c.ROOT/'run-all.ps1').read_text()
        for name in ('rq3','rq4_independent','rq4_travel','rq4_hub','legacy_fidelity_published','legacy_fidelity_fork'):
            self.assertRegex(text,re.escape("'"+name+"'")+r"\s*=\s*@\('stage1','stage2','collect'\)")
        for name in ('rq4_controlled','ext1_travel_frontier','ext2_rq3_df_cpu','ext3_travel_next','ext4_rq3_df_heap200','ext5_travel_heap200'):
            self.assertRegex(text,re.escape("'"+name+"'")+r"\s*=\s*@\('stage1','collect'\)")
        wrapper=(c.ROOT/'run-ext.ps1').read_text()
        self.assertIn("'run-all.ps1'",wrapper)
        self.assertNotIn('campaign.py',wrapper)

    def test_initial_preflight_rejects_wrong_frozen_jar_before_probe(self):
        config=self.config('ext1_travel_frontier')
        for relative in [config['classpath']]+[m['path'] for m in config['models']]:
            path=self.root/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('fixture')
        with patch.object(c,'ROOT',self.root),patch.object(c.shutil,'which',return_value='java'),\
             patch.object(c.subprocess,'run') as process,patch.object(c,'memory_bytes',return_value=256*1024**3),\
             patch.object(c.shutil,'disk_usage') as disk:
            process.return_value.stdout='';process.return_value.stderr='openjdk version "17.0.1"'
            disk.return_value.free=100*1024**3
            with self.assertRaisesRegex(RuntimeError,'Fixed synthesis JAR bytes differ'):
                c.preflight(config,self.root/'raw/test')
            self.assertEqual(process.call_count,1) # Mocked java -version only; no process probe.

    def test_skipped_monotone_is_terminal_undecided_without_timing_summary(self):
        r=row(1,'SKIPPED_MONOTONE');job=dict(**{k:r[k] for k in ('job_id','model_id','target_id','method_id','repetition')},jvm_properties={})
        with patch.object(c.collector,'collect',return_value=([r],[],{})):
            raw,summary=c.summarize(dict(repetitions=1),self.root,dict(jobs=[job]))
        self.assertFalse(summary[0]['invalid']);self.assertEqual(raw[0]['decision'],'UNDECIDED')
        self.assertFalse(summary[0]['timing_summary_eligible']);self.assertEqual(summary[0]['solver_time_ms_median'],'')

if __name__=='__main__':unittest.main(verbosity=2)
