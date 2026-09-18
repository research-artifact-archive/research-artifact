#!/usr/bin/env python3
"""Regression tests of publication censoring and source separation; no solver runs."""
from pathlib import Path
import copy,csv,json,tempfile,unittest,statistics,shutil
import render_results as r

def complete():
    return dict(model_id='gsm',target_id='base',method_id='fg_ducs_otf',stage1_status='SUCCESS',
                statuses=';'.join(str(i)+':SUCCESS' for i in range(1,6)),completed_valid_repetitions='5',
                timing_summary_eligible='True',invalid='False',inconsistent='False',
                solver_time_ms_median='20',solver_time_ms_min='10',solver_time_ms_max='30',states_discovered='12')

def saved_campaign(path,sequence=('SUCCESS',)*5):
    """Synthetic collection evidence; no benchmark observations or JVM runs."""
    config=dict(java_heap='64g',timeout_seconds=1200,experiment_id='synthetic-render-gate',repetitions=5,
                models=[dict(id='gsm')],targets=[dict(id='base')],methods=[dict(id='fg_ducs_otf')])
    jobs=[];raw=[]
    for rep,status in enumerate(sequence,1):
        job=dict(model_id='gsm',target_id='base',method_id='fg_ducs_otf',repetition=rep,job_id='gsm__base__rep%02d__fg_ducs_otf'%rep)
        jobs.append(job);terminal=status in r.TERMINAL
        invalid=status not in r.GOOD|r.SKIPS|{'TIMEOUT','OOM','NOT_RUN'}
        row=dict(job,process_status=status,completed=terminal,invalid=invalid,inconsistent=False,
                 solver_time_ms=rep*10 if status in r.GOOD else '',elapsed_monotonic_seconds=rep/10,
                 peak_rss_bytes=rep*1024,states_discovered=12,successor_queries=14,transition_outcomes=13,
                 output_controller_states=8,output_controller_transitions=7)
        raw.append(row);folder=path/'runs'/job['job_id'];folder.mkdir(parents=True)
        (folder/'meta.json').write_text(json.dumps(dict(completed=terminal,status=status,job=job,skip_reason='preceding terminal failure' if status in r.SKIPS else '')))
    valid=[row for row in raw if row['process_status'] in r.GOOD and not row['invalid']]
    row=dict(complete(),stage1_status=sequence[0],stage1_denominator_included=True,planned_total_repetitions=5,
             completed_valid_repetitions=len(valid),invalid=any(x['invalid'] for x in raw),inconsistent=False,
             statuses=';'.join(str(i)+':'+s for i,s in enumerate(sequence,1)),timing_summary_eligible=len(valid)==5,
             successor_queries=14,transition_outcomes=13,output_policy_states=8,output_policy_transitions=7)
    for metric in ('solver_time_ms','elapsed_monotonic_seconds','peak_rss_bytes'):
        for suffix,function in (('median',statistics.median),('min',min),('max',max)):
            row[metric+'_'+suffix]=function([v[metric] for v in valid]) if len(valid)==5 else ''
    for name,value in [('config.json',config),('environment.json',dict(system='Windows')),
                       ('plan.json',dict(jobs=jobs,job_count=5)),
                       ('stage2_plan.json',dict(stage1_denominator=1,additional_repetitions=4,
                         eligible_jobs=jobs[1:] if sequence[0] in r.GOOD else [],
                         exclusions=[] if sequence[0] in r.GOOD else [dict(model_id='gsm',target_id='base',method_id='fg_ducs_otf',reason=sequence[0])]))]:
        (path/name).write_text(json.dumps(value))
    r.write_csv(path/'raw_runs.csv',raw);r.write_csv(path/'stage1.csv',raw[:1]);r.write_csv(path/'summary.csv',[row])
    return config

class RenderingTests(unittest.TestCase):
    def test_censored_comparison_uses_elapsed_not_solver_and_no_df_median(self):
        from types import SimpleNamespace
        fg=complete();fg.update(elapsed_monotonic_seconds_median='2',elapsed_monotonic_seconds_min='1',elapsed_monotonic_seconds_max='3')
        df=dict(fg,method_id='direct_full',stage1_status='TIMEOUT',statuses='1:TIMEOUT')
        c=SimpleNamespace(rows=[fg,df],index={r.key(fg):fg,r.key(df):df},config={'timeout_seconds':1200})
        pair=r.censored_pairs(c)[0]
        self.assertEqual(pair['censored_attempt_over_fg_elapsed_median_lower_bound'],600)
        self.assertEqual(pair['cap_over_fg_solver_median_descriptive_only'],60000)
        self.assertEqual(pair['df_solver_ratio_lower_bound'],'')
        self.assertFalse(pair['df_median_inferred'])
        fg['completed_valid_repetitions']='4';self.assertEqual(r.censored_pairs(c),[])

    def test_environment_original_digest_and_declared_path_redaction_have_distinct_scope(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'environment.json'
            env=dict(system='Windows',python_executable=r'C:\ExampleHome\Python\python.exe',java_home=r'C:\Java')
            path.write_text(json.dumps(env));source=r.digest_file(path)
            self.assertEqual(r.check_environment_identity(path,env,source),'source_bytes_verified')
            env['python_executable']=r'<USER_HOME>\Python\python.exe'
            env['distribution_redaction']=dict(source_sha256=source,kind='personal_paths_only',changed_fields=['python_executable'])
            path.write_text(json.dumps(env))
            self.assertNotEqual(r.digest_file(path),source)
            self.assertEqual(r.check_environment_identity(path,env,source),'distribution_personal_path_redaction')

    def test_environment_redaction_bad_source_kind_fields_or_markers_rejected(self):
        for issue in ('missing','source','kind','nonallowed','empty','duplicate','not_list','nonstr_field','no_marker','undeclared_marker','nonwindows'):
            with self.subTest(issue=issue),tempfile.TemporaryDirectory() as temp:
                path=Path(temp)/'environment.json';source='a'*64
                env=dict(system='Windows',python_executable=r'<USER_HOME>\Python\python.exe',
                    distribution_redaction=dict(source_sha256=source,kind='personal_paths_only',changed_fields=['python_executable']))
                note=env['distribution_redaction']
                if issue=='missing':env.pop('distribution_redaction')
                elif issue=='source':note['source_sha256']='b'*64
                elif issue=='kind':note['kind']='arbitrary_changes'
                elif issue=='nonallowed':note['changed_fields']=['processor'];env['processor']='<USER_HOME>'
                elif issue=='empty':note['changed_fields']=[]
                elif issue=='duplicate':note['changed_fields']*=2
                elif issue=='not_list':note['changed_fields']='python_executable'
                elif issue=='nonstr_field':note['changed_fields']=[{}]
                elif issue=='no_marker':env['python_executable']=r'C:\Python\python.exe'
                elif issue=='undeclared_marker':env['java_home']='<USER_HOME>'
                else:env['system']='Darwin'
                path.write_text(json.dumps(env))
                with self.assertRaises(ValueError):r.check_environment_identity(path,env,source)

    @unittest.skipUnless(all((r.HERE/'raw'/s[0]/'summary.csv').is_file() for s in r.SUPPLEMENTS.values()),'AD return not distributed')
    def test_ad_redacted_distribution_executes_gate_and_marks_provenance_without_new_medians(self):
        c=r.Campaign(r.HERE/'raw/rq3','xeon',json.loads((r.HERE/'configs/rq3.json').read_text()))
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);original=root/'rq3';original.mkdir()
            for name in ('config.json','plan.json','environment.json'):shutil.copyfile(c.path/name,original/name)
            for spec in r.SUPPLEMENTS.values():
                job=next(row['job_id'] for row in c.initial if r.key(row)==spec[1])
                shutil.copytree(c.path/'runs'/job,original/'runs'/job)
                shutil.copytree(r.HERE/'raw'/spec[0],root/spec[0])
            for folder in (original,*(root/s[0] for s in r.SUPPLEMENTS.values())):
                path=folder/'environment.json';source=r.digest_file(path);env=json.loads(path.read_text())
                # Also permits running this test within an already anonymized artifact.
                source=env.get('distribution_redaction',{}).get('source_sha256',source)
                env['python_executable']=r'<USER_HOME>\Python\python.exe'
                env['distribution_redaction']=dict(source_sha256=source,changed_fields=['python_executable'],kind='personal_paths_only')
                path.write_text(json.dumps(env))
            c.path=original;r.integrate_supplementary(c,root)
            r.render_supplementary_returned(c,root)
            rows=r.read_csv(root/'rq3-supplementary-provenance.csv')
            measured=[row for row in rows if row['status'] not in r.SKIPS]
            self.assertEqual(len(measured),4)
            self.assertTrue(all(row['environment_verification']=='distribution_personal_path_redaction' for row in measured))
            self.assertTrue(all(row['timing_median_eligible']=='False' for row in rows))
            self.assertIn('original environment bytes are not reverified',(root/'rq3-supplementary-provenance.tex').read_text())
            self.assertEqual(r.cell_text(c.index['workflow','r2','direct_full']),r'TO$^{\ddagger}$')

    def test_ad_status_overlay_is_confined_to_authorized_interrupted_cell(self):
        row=dict(complete(),model_id='workflow',target_id='r2',method_id='direct_full',
            stage1_status='INTERRUPTED_NOT_RETRIED',statuses='1:INTERRUPTED_NOT_RETRIED',
            ad_effective_status='TIMEOUT',ad_source_campaign=r.SUPPLEMENTS['workflow'][0])
        self.assertEqual(r.effective_status(row),'TIMEOUT');self.assertEqual(r.cell_text(row),r'TO$^{\ddagger}$')
        self.assertEqual(row['stage1_status'],'INTERRUPTED_NOT_RETRIED')
        self.assertIsNone(r.triple(row,'solver_time_ms'))
        for changed in (dict(method_id='legacy_ducs'),dict(model_id='gsm'),dict(stage1_status='CRASH'),dict(ad_source_campaign='unapproved')):
            other=dict(row,**changed);self.assertEqual(r.effective_status(other),other['stage1_status'])

    def test_ad_artifact_digest_rejects_modified_output_and_escape(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp);(path/'output.txt').write_text('recorded output')
            meta=dict(artifacts=dict(output='output.txt'),artifact_digests=dict(output=dict(exists=True,
                bytes=(path/'output.txt').stat().st_size,sha256=r.digest_file(path/'output.txt'))))
            r.check_returned_artifacts(path,meta)
            (path/'output.txt').write_text('changed output')
            with self.assertRaisesRegex(ValueError,'digest'):r.check_returned_artifacts(path,meta)
            meta['artifacts']['output']='../output.txt'
            with self.assertRaisesRegex(ValueError,'escapes'):r.check_returned_artifacts(path,meta)

    @unittest.skipUnless(all((r.HERE/'raw'/s[0]/'summary.csv').is_file() for s in r.SUPPLEMENTS.values()),'AD return not distributed')
    def test_ad_real_returns_preserve_135_original_cells_and_legacy_and_suppress_medians(self):
        c=r.Campaign(r.HERE/'raw/rq3','xeon',json.loads((r.HERE/'configs/rq3.json').read_text()))
        before=copy.deepcopy(c.rows);r.integrate_supplementary(c,r.HERE/'raw')
        self.assertEqual(len(c.rows),135)
        for old,new in zip(before,c.rows):self.assertEqual(old,{k:v for k,v in new.items() if not k.startswith('ad_')})
        df=[row for row in c.rows if row['method_id']=='direct_full']
        self.assertEqual(sum(r.effective_status(x)=='SUCCESS' for x in df),14)
        self.assertEqual(sum(r.effective_status(x)=='TIMEOUT' for x in df),13)
        self.assertEqual(sum(x['stage1_status']=='INTERRUPTED_NOT_RETRIED' for x in df),1)
        for spec in r.SUPPLEMENTS.values():
            self.assertIsNone(r.triple(c.index[spec[1]],'solver_time_ms'))
            self.assertIsNone(r.triple(c.index[spec[1]],'peak_rss_bytes'))
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp);r.render_supplementary_returned(c,out);r.render_rq3(c,'xeon',out,c.config)
            rows=r.read_csv(out/'rq3-supplementary-provenance.csv')
            self.assertEqual(len(rows),8);self.assertEqual(sum(x['status']=='SKIPPED_AFTER_RESOURCE_FAILURE' for x in rows),4)
            self.assertTrue(all(x['timing_median_eligible']=='False' for x in rows))
            self.assertTrue(all(x['heap_occupancy_measured']=='False' for x in rows))
            old=next(x for x in rows if x['status']=='INTERRUPTED_NOT_RETRIED')
            self.assertEqual(old['finished_utc'],'');self.assertEqual(old['peak_rss_bytes'],'')
            macros=(out/'rq3-ad-numbers.tex').read_text();self.assertIn(r'\ADDirectFullTimeouts}{13}',macros)
            self.assertIn(r'\ADPCPeakRSSGiB}{67.1}',macros)
            table=(out/'rq3-table.tex').read_text();self.assertEqual(table.count(r'TO$^{\ddagger}$'),1)
            self.assertNotIn('pending',r.supplementary_footnote(c));self.assertNotIn('TO$^{\\ddagger}$\\textsuperscript{b}',table)

    @unittest.skipUnless((r.HERE/'raw/rq3/environment.json').is_file(),'Xeon return not distributed')
    def test_ad_host_profile_ignores_volatile_values_not_runtime_or_cpu(self):
        env=json.loads((r.HERE/'raw/rq3/environment.json').read_text());other=copy.deepcopy(env)
        other['free_disk_bytes']=1;data=json.loads(other['windows_cim_probe']['stdout'])
        data['operating_system']['LocalDateTime']='different';data['local_disks']['FreeSpace']=1
        other['windows_cim_probe']['stdout']=json.dumps(data)
        self.assertEqual(r.host_profile(env),r.host_profile(other))
        other['python_version']='different';self.assertNotEqual(r.host_profile(env),r.host_profile(other))
        data['cpu']['Name']='different';other['windows_cim_probe']['stdout']=json.dumps(data)
        with self.assertRaisesRegex(ValueError,'Xeon'):r.host_profile(other)

    @unittest.skipUnless(all((r.HERE/'raw'/s[0]/'summary.csv').is_file() for s in r.SUPPLEMENTS.values()),'AD return not distributed')
    def test_ad_partial_changed_settings_or_evidence_rejected_without_overlay(self):
        for problem in ('missing_return','missing_skip','config','jar','input','command','output'):
            with self.subTest(problem=problem),tempfile.TemporaryDirectory() as temp:
                root=Path(temp)
                for spec in r.SUPPLEMENTS.values():shutil.copytree(r.HERE/'raw'/spec[0],root/spec[0])
                folder=root/r.SUPPLEMENTS['workflow'][0]
                meta_path=folder/'runs/workflow__r2__rep01__direct_full/meta.json'
                if problem=='missing_return':shutil.rmtree(folder)
                elif problem=='missing_skip':(folder/'runs/workflow__r2__rep05__direct_full/meta.json').unlink()
                elif problem=='config':
                    path=folder/'config.json';value=json.loads(path.read_text());value['java_heap']='32g';path.write_text(json.dumps(value))
                elif problem=='output':(meta_path.parent/'output.txt').write_text('tampered output')
                else:
                    value=json.loads(meta_path.read_text())
                    if problem=='jar':value['classpath']['sha256']='0'*64
                    elif problem=='input':value['input_model']['sha256']='0'*64
                    else:value['command'].append('-Dunapproved=change')
                    meta_path.write_text(json.dumps(value))
                c=r.Campaign(r.HERE/'raw/rq3','xeon',json.loads((r.HERE/'configs/rq3.json').read_text()))
                with self.assertRaises(ValueError):r.integrate_supplementary(c,root)
                self.assertEqual(r.effective_status(c.index['workflow','r2','direct_full']),'INTERRUPTED_NOT_RETRIED')
                self.assertFalse(hasattr(c,'supplementary'))

    def test_hub_keeps_each_seed_profile_method_without_inventing_k(self):
        config=dict(models=[dict(id=f'hub_s{s}_{p}',family='n4_hub',
                    factors=dict(seed=s,profile=p)) for s in (1,2) for p in ('u0','u_local','u_cross')])
        campaign=r.Campaign(None,'placeholder')
        campaign.rows=[dict(complete(),model_id='hub_s1_u0')]
        rows=r.scaling_rows(campaign,config)
        self.assertEqual(len(rows),24)
        self.assertEqual(len({r.key(x) for x in rows}),24)
        self.assertTrue(all(x['K']=='' for x in rows))
        self.assertEqual(sum(r.complete_five(x) for x in rows),1)
        self.assertEqual(sum(x['stage1_status']=='NOT_RUN' for x in rows),23)

    def test_absent_structure_is_not_a_measured_equal_pair(self):
        from analyze_results import scaling_statistics
        c=r.Campaign(None,'placeholder')
        c.config=dict(models=[dict(id='gsm',factors=dict(K=1,N=1))])
        c.rows=[dict(complete(),method_id=m,states_discovered='',
                     successor_queries='',transition_outcomes='') for m in r.METHODS[:4]]
        c.index={r.key(x):x for x in c.rows}
        result,_=scaling_statistics(c)
        self.assertEqual(result['lazy_update_first_measured_structure_pairs'],0)
        self.assertIsNone(result['fg_over_df_states_max'])

    def test_capture_cap_requires_saved_evidence_and_keeps_raw_status(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp);job='industry__r1__rep01__legacy_ducs'
            folder=path/'runs'/job;folder.mkdir(parents=True)
            row=complete();row.update(model_id='industry',target_id='r1',method_id='legacy_ducs',
                stage1_status='CRASH',statuses='1:CRASH',invalid='True')
            campaign=r.Campaign(None,'xeon');campaign.path=path;campaign.rows=[row]
            campaign.initial=[dict(row,job_id=job)]
            (folder/'stderr.txt').write_text('unrelated solver exception')
            r.mark_capture_caps(campaign);self.assertEqual(r.cell_text(row),'CRASH')
            (folder/'stderr.txt').write_text('MTS exceeds the registered finite resource profile\n'
                'M9MtsSnapshot.requireResourceCensus\nM9MtsSnapshot.capturePass(M9MtsSnapshot.java:77)\n'
                'UpdatingControllerSafetySynthesizer')
            r.mark_capture_caps(campaign)
            self.assertEqual(row['stage1_status'],'CRASH');self.assertEqual(row['statuses'],'1:CRASH')
            self.assertEqual('N/M',r.cell_text(row))
            self.assertEqual(r.failure_codes(row),['N/M'])
            self.assertIsNone(r.triple(row,'solver_time_ms'))
            row['method_id']='direct_full';self.assertEqual(r.cell_text(row),'CRASH')
    def test_crash_and_operational_interruption_remain_distinct(self):
        for status,label in [('CRASH','CRASH'),('INTERRUPTED_NOT_RETRIED','INTERRUPTED')]:
            row=complete();row.update(stage1_status=status,invalid='True',timing_summary_eligible='False',
                completed_valid_repetitions='0',statuses='1:'+status+';2:SKIPPED_INELIGIBLE_STAGE1')
            self.assertEqual(r.cell_text(row),label)
            self.assertIsNone(r.triple(row,'solver_time_ms'))
    def test_five_consistent_runs_show_main_median_and_supplement_range(self):
        row=complete();self.assertEqual(r.triple(row,'solver_time_ms',.001),(.02,.01,.03))
        self.assertEqual(r.cell_text(row),r'W 0.02$^{\dagger}$')
        self.assertNotIn('[',r.cell_text(row));self.assertIn(r'\mbox{[0.01, 0.03]}',r.cell_text(row,show_range=True))
    def test_stale_median_is_suppressed_after_resource_failure(self):
        for failure in ('TIMEOUT','OOM'):
            row=complete();row['statuses']='1:SUCCESS;2:'+failure+';3:SKIPPED_AFTER_RESOURCE_FAILURE;4:SKIPPED_AFTER_RESOURCE_FAILURE;5:SKIPPED_AFTER_RESOURCE_FAILURE'
            self.assertIsNone(r.triple(row,'solver_time_ms'));self.assertNotIn('0.02',r.cell_text(row))
            self.assertIn('TO' if failure=='TIMEOUT' else 'OOM',r.cell_text(row))
    def test_invalid_and_inconsistent_rows_never_display_metrics(self):
        for flag,code in (('invalid','INV'),('inconsistent','INC')):
            row=complete();row[flag]='True'
            self.assertIsNone(r.triple(row,'solver_time_ms'));self.assertIsNone(r.structural(row,'states_discovered'));self.assertEqual(r.cell_text(row),code)
    def test_mixed_decisions_cannot_be_complete_case(self):
        row=complete();row['statuses']='1:SUCCESS;2:UNREALIZABLE;3:SUCCESS;4:SUCCESS;5:SUCCESS'
        self.assertFalse(r.complete_five(row));self.assertEqual(r.cell_text(row),'INC')
    def test_measured_zero_time_is_retained(self):
        row=complete();row.update(solver_time_ms_median='0',solver_time_ms_min='0',solver_time_ms_max='1')
        self.assertEqual(r.triple(row,'solver_time_ms',.001),(0,0,.001))
    def test_missing_and_zero_are_distinct(self):
        row=complete();row['states_discovered']='';self.assertEqual(r.cell_text(row,'states_discovered',1),'--')
        row['states_discovered']='0';self.assertEqual(r.cell_text(row,'states_discovered',1),'0')
    def test_summary_stage1_conflict_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp);row=complete();r.write_csv(path/'summary.csv',[row]);r.write_csv(path/'stage1.csv',[dict(model_id='gsm',target_id='base',method_id='fg_ducs_otf',process_status='OOM')])
            with self.assertRaises(ValueError):r.Campaign(path,'pilot')
    def test_pilot_cannot_be_read_as_xeon(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp);(path/'config.json').write_text(json.dumps(dict(java_heap='4g',timeout_seconds=60,experiment_id='pilot')))
            (path/'environment.json').write_text(json.dumps(dict(system='Darwin')))
            with self.assertRaises(ValueError):r.Campaign(path,'xeon')
    def test_bad_range_is_rejected(self):
        row=complete();row['solver_time_ms_min']='25'
        with self.assertRaises(ValueError):r.triple(row,'solver_time_ms')
    def test_typesetting_fixture_keeps_all_135_completed_cells(self):
        config=json.loads((r.HERE/'configs/rq3.json').read_text())
        rows=r.typesetting_fixture(config).rows
        self.assertEqual(len(rows),135)
        self.assertTrue(all(r.complete_five(row) for row in rows))
        self.assertTrue(all(row['source_kind']=='synthetic_typesetting_fixture_not_an_observation' for row in rows))
        for data in (rows,[]):
            table=r.table(data,config);lines=[line for line in table.splitlines() if ' & ' in line][1:]
            self.assertEqual(len(lines),27);self.assertTrue(all(line.count(' & ')==6 for line in lines))
            self.assertNotIn(r'\shortstack',table);self.assertNotIn(r'\strut',table)
        self.assertEqual(r.table(rows,config,show_range=True).count(r'\mbox{['),135)
    def test_pending_and_numeric_main_cells_are_one_line(self):
        for row in (complete(),r.pending('gsm','base','fg_ducs_otf')):
            cell=r.cell_text(row)
            self.assertNotIn(r'\\',cell);self.assertNotIn(r'\shortstack',cell)
        self.assertEqual(r.compact(1199),'1199')
        self.assertEqual(r.cell_text(r.pending('gsm','base','fg_ducs_otf')),'P')
    def test_relative_range_marker_strict_threshold_and_zero_median(self):
        row=complete();row.update(solver_time_ms_min='19',solver_time_ms_max='21')
        self.assertAlmostEqual(r.relative_width(row),.1);self.assertFalse(r.wide_range(row))
        row['solver_time_ms_max']='21.0001';self.assertTrue(r.wide_range(row))
        row.update(solver_time_ms_median='0',solver_time_ms_min='0',solver_time_ms_max='0')
        self.assertFalse(r.wide_range(row));row['solver_time_ms_max']='1';self.assertTrue(r.wide_range(row))
    def test_travel_grid_keeps_all_48_cells_and_all_four_distinct_statuses(self):
        config=json.loads((r.HERE/'configs/rq4_travel.json').read_text())
        rows=r.scaling_rows(r.Campaign(None,'placeholder'),config)
        group=[row for row in rows if row['N']==4 and row['K']==4]
        self.assertEqual(len(group),4)
        for row,status in zip(group,('SUCCESS','TIMEOUT','OOM','CRASH')):
            row.update(stage1_status=status,statuses=';'.join(str(i)+':'+status for i in range(1,6)),
                       completed_valid_repetitions='5' if status=='SUCCESS' else '0',timing_summary_eligible=status=='SUCCESS')
        grid=r.travel_status_cells(rows)
        self.assertEqual(len(grid),48);self.assertEqual(sum(len(x['symbols']) for x in grid),192)
        self.assertEqual(next(x['symbols'] for x in grid if x['N']==4 and x['K']==4),'WTO!')
        self.assertEqual({x['N'] for x in grid},{1,2,4,6,8,12})
    def test_supplementary_pending_keeps_original_status_and_no_measurements(self):
        c=r.Campaign(None,'placeholder')
        c.rows=[dict(complete(),model_id='productioncell_arms2',target_id='r2',stage1_status='TIMEOUT'),
                dict(complete(),model_id='workflow',target_id='r2',method_id='direct_full',stage1_status='INTERRUPTED_NOT_RETRIED')]
        before=json.dumps(c.rows,sort_keys=True)
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp);r.render_supplementary_pending(c,path,path/'unreturned')
            rows=r.read_csv(path/'rq3-supplementary-provenance.csv')
            self.assertEqual({row['original_status'] for row in rows},{'TIMEOUT','INTERRUPTED_NOT_RETRIED'})
            self.assertEqual({row['timeout_seconds'] for row in rows},{'1200','3600'})
            self.assertTrue(all(row['measured_seconds']==row['measured_decision']=='' for row in rows))
            text=(path/'rq3-supplementary-provenance.tex').read_text();self.assertIn('TO',text);self.assertIn('INTERRUPTED',text)
        self.assertEqual(json.dumps(c.rows,sort_keys=True),before)
    def test_completed_collection_is_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp);config=saved_campaign(path)
            campaign=r.Campaign(path,'xeon',config)
            self.assertEqual(r.triple(campaign.rows[0],'solver_time_ms',.001),(.03,.01,.05))
    def test_returned_subset_cannot_replace_fixed_denominator(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp);expected=saved_campaign(path);expected['models'].append(dict(id='another_model'))
            with self.assertRaisesRegex(ValueError,'denominator'):r.Campaign(path,'xeon',expected)
    def test_partial_collection_is_rejected_and_optional_rq4_is_pending(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp);config=saved_campaign(path,('SUCCESS','SUCCESS','NOT_RUN','NOT_RUN','NOT_RUN'))
            with self.assertRaisesRegex(ValueError,'Nonterminal'):r.Campaign(path,'xeon',config)
            pending=r.optional_xeon(path,config)
            self.assertEqual(pending.rows,[]);self.assertIn('Nonterminal',pending.pending_reason)
    def test_resource_failure_then_explicit_skips_is_complete(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp);config=saved_campaign(path,('SUCCESS','SUCCESS','OOM','SKIPPED_AFTER_RESOURCE_FAILURE','SKIPPED_AFTER_RESOURCE_FAILURE'))
            campaign=r.Campaign(path,'xeon',config)
            self.assertIsNone(r.triple(campaign.rows[0],'solver_time_ms'));self.assertIn('OOM',r.cell_text(campaign.rows[0]))
    def test_initial_resource_or_crash_with_skips_preserves_adverse_status(self):
        for status,skip in [('TIMEOUT','SKIPPED_AFTER_RESOURCE_FAILURE'),('CRASH','SKIPPED_AFTER_INVALID_OR_INCONSISTENT')]:
            with self.subTest(status=status),tempfile.TemporaryDirectory() as temp:
                path=Path(temp);config=saved_campaign(path,(status,)+(skip,)*4)
                campaign=r.Campaign(path,'xeon',config)
                self.assertEqual(campaign.rows[0]['stage1_status'],status)
                self.assertIsNone(r.triple(campaign.rows[0],'solver_time_ms'))
    def test_missing_repetition_or_eligible_job_is_rejected(self):
        for source in ('raw_runs.csv','stage2_plan.json','plan.json'):
            with self.subTest(source=source),tempfile.TemporaryDirectory() as temp:
                path=Path(temp);config=saved_campaign(path)
                if source.endswith('.csv'):r.write_csv(path/source,r.read_csv(path/source)[:-1])
                else:
                    data=json.loads((path/source).read_text());field='eligible_jobs' if source.startswith('stage2') else 'jobs';data[field].pop();(path/source).write_text(json.dumps(data))
                with self.assertRaises(ValueError):r.Campaign(path,'xeon',config)
    def test_stale_summary_status_count_or_metric_is_rejected(self):
        for field,value in [('statuses','1:SUCCESS;2:SUCCESS;3:SUCCESS;4:SUCCESS;5:NOT_RUN'),('completed_valid_repetitions','4'),('solver_time_ms_median','99')]:
            with self.subTest(field=field),tempfile.TemporaryDirectory() as temp:
                path=Path(temp);config=saved_campaign(path);rows=r.read_csv(path/'summary.csv');rows[0][field]=value;r.write_csv(path/'summary.csv',rows)
                with self.assertRaisesRegex(ValueError,'Stale'):r.Campaign(path,'xeon',config)
    def test_unfinished_meta_and_unsupported_resource_skip_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp);config=saved_campaign(path);meta_path=next((path/'runs').glob('*/meta.json'))
            meta=json.loads(meta_path.read_text());meta['completed']=False;meta_path.write_text(json.dumps(meta))
            with self.assertRaisesRegex(ValueError,'metadata'):r.Campaign(path,'xeon',config)
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp);config=saved_campaign(path,('SUCCESS',)+('SKIPPED_AFTER_RESOURCE_FAILURE',)*4)
            with self.assertRaisesRegex(ValueError,'preceding resource failure'):r.Campaign(path,'xeon',config)

if __name__=='__main__':unittest.main(verbosity=2)
