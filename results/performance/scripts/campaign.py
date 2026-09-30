#!/usr/bin/env python3
"""Serial staged experiment runner. Terminal failures are never retried."""
from pathlib import Path
import argparse, collections, contextlib, csv, ctypes, json, os, platform, re, shutil, statistics, subprocess, sys, time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Implementation/Experiment/FSE2027/scripts'))
# The extension overrides only the helper module. Other runtime modules fall
# back to the existing bundle's Implementation tree; source checkouts have all
# three under runtime/. No original Implementation file is replaced.
sys.path.insert(0,str(ROOT/'runtime'))
import harness_common as common
import run_experiment as runner
import collect_results as collector

GOOD={'SUCCESS','UNREALIZABLE'}
RESOURCE={'TIMEOUT','OOM'}
HUB_METHODS={'fg_ducs_otf':'fg_otf','direct_full':'direct_full',
             'fg_ducs_otf_eager_controllable':'eager_c','fg_ducs_otf_update_first':'update_first'}
ORIGINAL_COMMAND=runner.build_command

def command(config,job,root,output,transitions):
    if config.get('backend')=='published_mtsa':
        result=ORIGINAL_COMMAND(config,job,root,output,transitions)
        index=result.index('-cp')+1
        result[index]=os.pathsep.join([str(root/config['runner_classpath']),result[index]])
        return result
    if config.get('backend')!='synthetic_hub':return ORIGINAL_COMMAND(config,job,root,output,transitions)
    factors=job['model_factors']
    return [config['java'],'-Xmx'+config['java_heap'],'-cp',str(root/config['classpath']),
            'ltsa.updatingControllers.otf.Fse2027SyntheticBenchmark',
            '--output',str(output),'--seeds',str(factors['seed']),'--sizes','4',
            '--topologies','hub','--profiles',factors['profile'],'--mutations','base',
            '--methods',HUB_METHODS[job['method_id']],
            '--method-order-methods','fg_otf,eager_c,update_first,direct_full',
            '--repetitions','1','--warmups','0','--reference','false',
            '--guided-state-limit','50000','--guided-query-limit','100000',
            '--reference-state-limit','200000','--reference-query-limit','2000000']

runner.build_command=command

def write_csv(path,rows):
    fields=list(dict.fromkeys(key for row in rows for key in row))
    with path.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)

def cell(row):return row['model_id'],row['target_id'],row['method_id']
def json_write(path,value):common.atomic_write_json(path,value)

def summarize(config,folder,plan):
    raw,metrics,_=collector.collect(folder)
    jobs={job['job_id']:job for job in plan['jobs']}
    for row in raw:
        job=jobs[row['job_id']]
        row.update(invalid=False,inconsistent=False,invalid_reason='',expected_mismatch=False)
        status=row['process_status']
        if job['method_id'] in {'legacy_ducs','published_mtsa'} and row.get('output_path'):
            parsed=common.parse_evaluation_file(folder/row['output_path'])
            values={r.get('metric_key'):r.get('value','') for r in parsed['rows']}
            row['output_controller_states']=values.get('output_update_controller_states','')
            row['output_controller_transitions']=values.get('output_update_controller_transitions','')
            row['legacy_peak_state_space_states']=values.get('peak_state_space_states','')
            row['legacy_peak_state_space_transitions']=values.get('peak_state_space_transitions','')
            if config.get('backend')=='published_mtsa':
                row['solver_time_ms']=values.get('published_compile_compose_time_ms','')
                row['compile_compose_time_ms']=values.get('published_compile_compose_time_ms','')
                row['reference_tool']='lab-maintained build of the original DUCS source'
                if status in GOOD and (parsed['errors'] or row.get('solver_status')!={'SUCCESS':'REALIZABLE','UNREALIZABLE':'UNREALIZABLE'}[status]):
                    row['invalid']=True;row['invalid_reason']='published adapter decision/CSV mismatch'

        if config.get('backend')=='synthetic_hub' and row.get('output_path'):
            path=folder/row['output_path']
            if path.is_file():
                try:
                    with path.open(newline='',encoding='utf-8') as f: values=list(csv.DictReader(f))
                    if len(values)==1:
                        v=values[0]
                        row.update(solver_status=v.get('status',''),revised_decision=v.get('decision',''),
                            internal_certificate_check=v.get('certificate_verification_status',''),
                            run_verified=v.get('run_verified',''),link_checker='not_applicable_synthetic_game',
                            solver_time_ms=float(v['solver_time_ns'])/1e6 if v.get('solver_time_ns') else '',
                            states_discovered=v.get('discovered_states',''),states_expanded=v.get('expanded_states',''),
                            successor_queries=v.get('queried_state_action_pairs',''),transition_outcomes=v.get('materialized_transitions',''),
                            certificate_states=v.get('certificate_states',''),
                            output_controller_states=v.get('certificate_states',''),output_controller_transitions=v.get('certificate_transitions',''),
                            expected_mismatch=v.get('decision_matches_expected')=='false')
                        if status=='SUCCESS':
                            if v.get('decision')=='losing':row['process_status']='UNREALIZABLE'
                            elif v.get('decision')!='winning':row['invalid']=True;row['invalid_reason']='synthetic decision absent'
                        if v.get('certificate_valid')!='true' and status in GOOD:
                            row['invalid']=True;row['invalid_reason']='synthetic certificate invalid'
                    elif status in GOOD:row['invalid']=True;row['invalid_reason']='expected one synthetic CSV row'
                except (ValueError,KeyError) as error:
                    row['invalid']=True;row['invalid_reason']='synthetic parse: '+str(error)
        if row['process_status'] in GOOD:
            if config.get('backend')!='synthetic_hub' and not row.get('evaluation_csv_found'):
                row['invalid']=True;row['invalid_reason']='missing evaluation CSV'
            if job['method_id'] not in {'legacy_ducs','published_mtsa'}:
                if row.get('internal_certificate_check')!='passed':
                    row['invalid']=True;row['invalid_reason']='internal certificate check absent or failed'
                if config.get('backend')!='synthetic_hub' and row['process_status']=='SUCCESS' and row.get('link_checker')!='passed':
                    row['invalid']=True;row['invalid_reason']='link check absent or failed'
                if job['jvm_properties'].get('mtsa.revised.otf.independentVerification')=='true' and row.get('run_verified')!='true':
                    row['invalid']=True;row['invalid_reason']='required independent check absent or failed'
        elif row['process_status'] not in RESOURCE|{'NOT_RUN','SKIPPED_MONOTONE','SKIPPED_AFTER_RESOURCE_FAILURE','SKIPPED_AFTER_INVALID_OR_INCONSISTENT','SKIPPED_INELIGIBLE_STAGE1'}:
            row['invalid']=True;row['invalid_reason']='abnormal terminal or interrupted process'
        row['decision']=({'SUCCESS':'WIN','UNREALIZABLE':'LOSS'}.get(row['process_status'],'UNDECIDED'))
    # Same-cell repetition inconsistency and same-problem method disagreement.
    cells=collections.defaultdict(list); instances=collections.defaultdict(list)
    for row in raw:
        cells[cell(row)].append(row)
        if row['method_id'] not in {'legacy_ducs','published_mtsa'}:instances[(row['model_id'],row['target_id'])].append(row)
    for group in list(cells.values())+list(instances.values()):
        decisions={r['decision'] for r in group if r['process_status'] in GOOD and not r['invalid']}
        if len(decisions)>1:
            for row in group:row['inconsistent']=True
    rows=[]
    for key,group in sorted(cells.items()):
        first=next(r for r in group if int(r['repetition'])==1)
        valid=[r for r in group if r['process_status'] in GOOD and not r['invalid'] and not r['inconsistent']]
        target=int(config['repetitions'])
        complete=len(valid)==target and len(group)==target
        row=dict(model_id=key[0],target_id=key[1],method_id=key[2],
                 stage1_status=first['process_status'],stage1_denominator_included=True,
                 eligible_after_stage1=first['process_status'] in GOOD and not first['invalid'] and not first['inconsistent'],
                 planned_total_repetitions=target,completed_valid_repetitions=len(valid),
                 invalid=any(r['invalid'] for r in group),inconsistent=any(r['inconsistent'] for r in group),
                 expected_mismatch=any(r['expected_mismatch'] for r in group),
                 statuses=';'.join(str(r['repetition'])+':'+r['process_status'] for r in group),
                 timing_summary_eligible=complete and target==5,
                 measurement_scope=('published_compile_and_compose' if config.get('backend')=='published_mtsa' else 'solver_only_synthetic' if config.get('backend')=='synthetic_hub' else 'legacy_solve_control_problem' if key[2]=='legacy_ducs' else 'solve_and_internal_check_lts'),
                 structure_repetition=1,states_discovered=first.get('states_discovered',''),
                 successor_queries=first.get('successor_queries',''),transition_outcomes=first.get('transition_outcomes',''),
                 output_policy_states=first.get('output_controller_states',''),output_policy_transitions=first.get('output_controller_transitions',''))
        for metric in ('solver_time_ms','elapsed_monotonic_seconds','peak_rss_bytes'):
            values=[float(r[metric]) for r in valid if r.get(metric) not in ('',None)]
            for label,function in (('median',statistics.median),('min',min),('max',max)):
                row[metric+'_'+label]=function(values) if complete and target==5 and len(values)==5 else ''
        rows.append(row)
    write_csv(folder/'raw_runs.csv',raw)
    if metrics:write_csv(folder/'metrics_long.csv',metrics)
    write_csv(folder/'summary.csv',rows)
    # This table always retains every first-run cell, including resource failures.
    write_csv(folder/'stage1.csv',[r for r in raw if int(r['repetition'])==1])
    return raw,rows

def eligible(row):return row['process_status'] in GOOD and not row['invalid'] and not row['inconsistent']

def next_action(job,raw):
    prior=[r for r in raw if cell(r)==cell(job) and int(r['repetition'])<job['repetition']]
    bad=[r for r in prior if not eligible(r)]
    if bad:
        resource=any(r['process_status'] in RESOURCE or r['process_status']=='SKIPPED_AFTER_RESOURCE_FAILURE' for r in bad)
        return ('SKIPPED_AFTER_RESOURCE_FAILURE' if resource else 'SKIPPED_AFTER_INVALID_OR_INCONSISTENT',
                str([(r['repetition'],r['process_status']) for r in bad]))
    current=next(r for r in raw if r['job_id']==job['job_id'])
    if current['inconsistent']:return 'SKIPPED_AFTER_INVALID_OR_INCONSISTENT','same-problem decision disagreement'
    return None


def completed_ext_evidence(folder, config, plan, job):
    """Read an original terminal record; summaries and skip records are not evidence."""
    path=folder/'runs'/job['job_id']/'meta.json'
    if not path.is_file():return None,'missing terminal record'
    try:
        meta=common.read_json(path)
        if not meta.get('completed'):return None,'incomplete terminal record'
        if meta.get('job')!=job:return None,'terminal job differs from plan'
        if meta.get('config_sha256')!=common.file_digest(folder/'config.json')['sha256']:
            return None,'terminal config digest differs'
        if meta.get('plan_sha256')!=plan['plan_sha256']:return None,'terminal plan digest differs'
        if plan!=common.build_plan(config):return None,'saved plan differs from configuration'
        if meta.get('status')=='SUCCESS':
            rows,_,_=collector.collect(folder)
            row=next(r for r in rows if r['job_id']==job['job_id'])
            if not row.get('evaluation_csv_found') or row.get('internal_certificate_check')!='passed' or row.get('link_checker')!='passed':
                return None,'SUCCESS lacks its certificate/link evidence'
        return meta,None
    except (OSError,ValueError,KeyError,StopIteration,TypeError) as error:
        return None,'unusable terminal evidence: '+type(error).__name__


def ext_source(raw_root, name):
    """Resolve explicitly named ext sources, never an arbitrary filesystem path."""
    if not re.fullmatch(r'ext[1-5]_[a-z0-9_]+',name):return None,'invalid source campaign name'
    folder=raw_root/name
    try:
        config=common.load_config(folder/'config.json');plan=common.read_json(folder/'plan.json')
        if not common.extended_budget(config):return None,'source is not an extended-budget campaign'
        if config['experiment_id']!='fg-ducs-xeon-'+name:return None,'source experiment ID differs'
        return (folder,config,plan),None
    except (OSError,ValueError,KeyError,TypeError) as error:
        return None,'source unavailable: '+type(error).__name__


def prerequisite_observation(folder,job,requirement):
    """Evaluate explicit AND/OR gates using certified SUCCESS only.

    not_SUCCESS means no verified SUCCESS has been observed. Missing/incomplete
    evidence therefore permits its run, with that uncertainty recorded verbatim.
    Self/future references are rejected rather than treated as missing evidence.
    """
    if 'any_of' in requirement:
        observations=[prerequisite_observation(folder,job,child) for child in requirement['any_of']]
        return dict(prerequisite=requirement,satisfied=any(x['satisfied'] for x in observations),any_of=observations)
    source,error=ext_source(folder.parent,requirement['campaign']);evidence=None;invalid_reference=False
    if source:
        sf,sc,sp=source
        matches=[j for j in sp['jobs'] if j['repetition']==1 and
                 cell(j)==(requirement['model_id'],requirement['target_id'],requirement['method_id'])]
        if len(matches)!=1:
            error='prerequisite cell absent or ambiguous';invalid_reference=True
        elif sf==folder and matches[0]['global_order_index']>=job['global_order_index']:
            error='self/future prerequisite reference is not allowed';invalid_reference=True
        else:evidence,error=completed_ext_evidence(sf,sc,sp,matches[0])
    actual=evidence.get('status') if evidence else None
    required=requirement['requires']
    accepted=required if isinstance(required,list) else [required]
    satisfied=(actual!='SUCCESS' if required=='not_SUCCESS' else actual in accepted) and not invalid_reference
    return dict(prerequisite=requirement,observed_status=actual,verified_success=actual=='SUCCESS',
                satisfied=satisfied,reason=error or ('observed verified SUCCESS' if actual=='SUCCESS' else 'observed terminal '+str(actual)))


def ext_prerequisite_checks(folder,job):
    return [prerequisite_observation(folder,job,r) for r in job.get('prerequisites',[])]


def ext_stage1_action(config,folder,plan,job,prerequisite_checks=None):
    """One-shot prerequisites and opt-in resource pruning; no synthesis claim.

    Monotone scheduling compares componentwise N,K and requires at least one
    strict increase, the same method/properties, target, family, heap and cap.
    Only a genuine completed TIMEOUT/OOM can prune; SKIPPED is never propagated.
    """
    if not common.extended_budget(config):return None
    checks=ext_prerequisite_checks(folder,job) if prerequisite_checks is None else prerequisite_checks
    if any(not item['satisfied'] for item in checks):
        return 'SKIPPED_MONOTONE',json.dumps(dict(kind='prerequisite_not_met',checks=checks),sort_keys=True)
    if not config.get('monotone_skip',False):return None
    factors=job.get('model_factors',{})
    if not all(isinstance(factors.get(k),int) and not isinstance(factors.get(k),bool) for k in ('N','K')):return None
    sources=[(folder,config,plan)]
    for name in config.get('monotone_sources',[]):
        source,_=ext_source(folder.parent,name)
        if source:sources.append(source)
    for sf,sc,sp in sources:
        if any(sc.get(k)!=config.get(k) for k in ('java_heap','timeout_seconds','backend','classpath','main_class','transition_output_mode','required_classpath_sha256')):
            continue
        for smaller in sp['jobs']:
            if smaller['repetition']!=1 or smaller['method_id']!=job['method_id'] or smaller['target_id']!=job['target_id']:continue
            if sf==folder and smaller['global_order_index']>=job['global_order_index']:continue
            if smaller.get('model_family')!=job.get('model_family') or smaller['jvm_properties']!=job['jvm_properties']:continue
            before=smaller.get('model_factors',{})
            if {k:v for k,v in before.items() if k not in ('N','K')}!={k:v for k,v in factors.items() if k not in ('N','K')}:continue
            if not all(isinstance(before.get(k),int) and not isinstance(before.get(k),bool) for k in ('N','K')):continue
            if not (all(before[k]<=factors[k] for k in ('N','K')) and any(before[k]<factors[k] for k in ('N','K'))):continue
            evidence,_=completed_ext_evidence(sf,sc,sp,smaller)
            if evidence and evidence['status'] in RESOURCE:
                return 'SKIPPED_MONOTONE',json.dumps(dict(kind='smaller_resource_failure',campaign=sf.name,
                    job_id=smaller['job_id'],status=evidence['status'],smaller_factors=before,current_factors=factors,
                    java_heap=sc['java_heap'],timeout_seconds=sc['timeout_seconds']),sort_keys=True)
    return None

@contextlib.contextmanager
def serial_execution():
    """OS file lock, released on process exit: at most one bundle campaign JVM."""
    directory=ROOT/'raw';directory.mkdir(exist_ok=True)
    with (directory/'campaign.lock').open('a+b') as handle:
        if handle.tell()==0:handle.write(b'0');handle.flush()
        handle.seek(0)
        if os.name=='nt':
            import msvcrt
            try:msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
            except OSError:raise RuntimeError('Another bundle campaign is running')
        else:
            import fcntl
            try:fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
            except OSError:raise RuntimeError('Another bundle campaign is running')
        try:yield
        finally:
            if os.name=='nt':handle.seek(0);msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
            else:fcntl.flock(handle.fileno(),fcntl.LOCK_UN)

def skip(folder,job,status,reason):
    path=folder/'runs'/job['job_id']/'meta.json';path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():return
    json_write(path,dict(completed=True,status=status,job=job,skip_reason=reason,artifacts={}))

def initialize(config,folder,plan):
    folder.mkdir(parents=True,exist_ok=True)
    path=folder/'config.json'
    if path.exists():
        if common.read_json(path)!=config:raise RuntimeError('Campaign config differs; refusing changed-condition resume')
        if common.read_json(folder/'plan.json')!=plan:raise RuntimeError('Campaign plan differs')
    else:json_write(path,config);json_write(folder/'plan.json',plan)
    return str(common.file_digest(path)['sha256'])

def memory_bytes():
    if os.name=='nt':
        class Memory(ctypes.Structure):
            _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(name,ctypes.c_ulonglong) for name in ('total','available','page_total','page_available','virtual_total','virtual_available','extended')]
        value=Memory();value.length=ctypes.sizeof(value)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(value)):raise OSError('GlobalMemoryStatusEx failed')
        return value.total
    return common.physical_memory_bytes()

def preflight(config,folder):
    if not shutil.which(config['java']):raise RuntimeError('Java is not on PATH')
    version=subprocess.run([config['java'],'-version'],capture_output=True,text=True)
    if not re.search(r'version "17[.]',version.stdout+version.stderr):raise RuntimeError('Use the fixed JDK 17 runtime for this campaign')
    ram=memory_bytes()
    if ram is None or ram < config['minimum_physical_memory_gib']*1024**3:raise RuntimeError('Insufficient physical RAM')
    if shutil.disk_usage(ROOT).free < config['minimum_free_disk_gib']*1024**3:raise RuntimeError('Insufficient free disk')
    for path in [config['classpath']]+[model['path'] for model in config['models']]:
        if not (ROOT/path).is_file():raise FileNotFoundError(path)
    if config.get('required_classpath_sha256') and common.sha256_file(ROOT/config['classpath'])!=config['required_classpath_sha256']:
        raise RuntimeError('Fixed synthesis JAR bytes differ')
    if config.get('runner_classpath') and common.sha256_file(ROOT/config['runner_classpath'])!=config['required_runner_sha256']:
        raise RuntimeError('Published adapter bytes differ')
    stamp=time.strftime('%Y%m%d-%H%M%S')
    probe=subprocess.run([sys.executable,str(ROOT/'scripts/process_probe.py'),'--java',config['java'],'--output',str(folder/('process_tree_smoke-'+stamp+'.csv'))],cwd=ROOT)
    if probe.returncode:raise RuntimeError('Process-tree/RSS startup probe failed; no experiments started')
    env=common.environment_manifest(config,ROOT);env['physical_memory_bytes_portable']=ram
    if config.get('runner_classpath'):env['runner_module']=common.file_digest(ROOT/config['runner_classpath'])
    env['model_input_bytes']={model['path']:common.file_digest(ROOT/model['path'])['sha256'] for model in config['models']}
    # Standard raw host metadata; no source/git inspection is needed for this copied bundle.
    env.pop('git_revision_probe',None);env.pop('git_status_probe',None)
    json_write(folder/('environment-'+stamp+'.json'),env)
    previous=folder/'environment.json'
    if previous.exists():
        old=common.read_json(previous)
        for field in ('system','machine','processor','logical_cpu_count','physical_memory_bytes_portable','java_version_probe','python_version','model_input_bytes','runner_module'):
            if old.get(field)!=env.get(field):raise RuntimeError('Execution host/runtime changed: '+field)
        if old.get('classpath',{}).get('sha256')!=env.get('classpath',{}).get('sha256'):
            raise RuntimeError('The campaign JAR bytes changed; refusing a mixed-build resume')
    else:json_write(previous,env)
    return str(common.file_digest(previous)['sha256'])

def main():
    p=argparse.ArgumentParser();p.add_argument('--config',default='rq3');p.add_argument('--stage',choices=['plan','stage1','stage2','collect'],default='stage1');p.add_argument('--output',type=Path)
    a=p.parse_args();config=common.load_config(ROOT/'configs'/(a.config+'.json'))
    folder=(a.output or ROOT/'raw'/a.config).resolve();plan=common.build_plan(config)
    config_sha=initialize(config,folder,plan)
    first=[job for job in plan['jobs'] if job['repetition']==1]
    print(json.dumps(dict(config=a.config,stage1_jobs=len(first),maximum_jobs=len(plan['jobs']),serial=True,timeout_seconds=config['timeout_seconds']),sort_keys=True),flush=True)
    if a.stage=='plan':return
    raw,summary=summarize(config,folder,plan)
    if a.stage=='collect':return
    if a.stage=='stage2' and any(r['process_status']=='NOT_RUN' for r in raw if int(r['repetition'])==1):
        raise RuntimeError('Stage1 has unstarted cells; complete stage1 before stage2')
    env_sha=preflight(config,folder)
    runner.ORDER_ALGORITHM=plan['order_algorithm']
    selected=first if a.stage=='stage1' else [job for job in plan['jobs'] if job['repetition']>1]
    if a.stage=='stage2':
        index={cell(row):row for row in raw if int(row['repetition'])==1}
        permitted=[job for job in selected if eligible(index[cell(job)])]
        json_write(folder/'stage2_plan.json',dict(stage1_denominator=len(first),additional_repetitions=4,eligible_jobs=permitted,
            exclusions=[dict(model_id=k[0],target_id=k[1],method_id=k[2],reason=r['process_status'],invalid=r['invalid'],inconsistent=r['inconsistent']) for k,r in index.items() if not eligible(r)]))
    for job in selected:
        path=folder/'runs'/job['job_id']/'meta.json'
        if path.exists():
            meta=common.read_json(path)
            if not meta.get('completed'):
                meta.update(completed=True,status='INTERRUPTED_NOT_RETRIED');json_write(path,meta)
            continue
        if a.stage=='stage2':
            raw,_=summarize(config,folder,plan)
            action=next_action(job,raw)
            if action:skip(folder,job,*action);continue
        if a.stage=='stage1':
            checks=ext_prerequisite_checks(folder,job) if common.extended_budget(config) else []
            if checks:
                json_write(path.parent/('prerequisites-'+str(time.time_ns())+'.json'),
                           dict(job_id=job['job_id'],checks=checks))
            action=ext_stage1_action(config,folder,plan,job,checks)
            if action:
                print('SKIP '+job['job_id']+' '+action[1],flush=True)
                skip(folder,job,*action);continue
        print('RUN '+job['job_id'],flush=True)
        try:
            result=runner.run_job(config,config_sha,plan['plan_sha256'],ROOT,folder,job,env_sha)
            print('END '+job['job_id']+' '+result['status']+' %.3fs'%result['elapsed_monotonic_seconds'],flush=True)
        except BaseException:
            if path.exists():
                meta=common.read_json(path);meta.update(completed=True,status='INTERRUPTED_NOT_RETRIED');json_write(path,meta)
            summarize(config,folder,plan);raise
    raw,summary=summarize(config,folder,plan)
    if a.stage=='stage1':
        bycell={cell(row):row for row in raw if int(row['repetition'])==1}
        selected=[job for job in plan['jobs'] if job['repetition']>1]
        json_write(folder/'stage2_plan.json',dict(stage1_denominator=len(first),additional_repetitions=4,
            eligible_jobs=[job for job in selected if eligible(bycell[cell(job)])],
            exclusions=[dict(model_id=k[0],target_id=k[1],method_id=k[2],reason=r['process_status'],invalid=r['invalid'],inconsistent=r['inconsistent']) for k,r in bycell.items() if not eligible(r)]))
    print('COUNTS '+json.dumps(dict(collections.Counter(r['process_status'] for r in raw if int(r['repetition'])==1))),flush=True)

if __name__=='__main__':
    with serial_execution():main()
