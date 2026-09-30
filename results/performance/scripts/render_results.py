#!/usr/bin/env python3
"""Read saved campaign summaries; generate publication fragments without running jobs.

Default mode emits pending placeholders. Pilot output must use a separate directory.
Neither experiment configuration nor raw observations are modified.
"""
from __future__ import annotations
from pathlib import Path
import argparse, csv, hashlib, json, math, re, statistics
from datetime import datetime

HERE=Path(__file__).resolve().parents[1]
SUBMISSION=HERE.parents[1]
METHODS=('fg_ducs_otf','fg_ducs_otf_eager_controllable','fg_ducs_otf_update_first','direct_full','legacy_ducs')
LABELS=('FG lazy','Eager','Update-first','Direct-Full','Legacy')
MODEL_LABELS={'gsm':'GSM','industry':'Industry','metasocket':'MetaSocket','powerplant':'PowerPlant',
    'productioncell_arms1':'PC Arms=1','productioncell_arms2':'PC Arms=2','railcab':'Railcab',
    'surveillance':'Surveillance','workflow':'Workflow'}
GOOD={'SUCCESS','UNREALIZABLE'}
SKIPS={'SKIPPED_AFTER_RESOURCE_FAILURE','SKIPPED_AFTER_INVALID_OR_INCONSISTENT','SKIPPED_INELIGIBLE_STAGE1'}
TERMINAL=GOOD|SKIPS|{'TIMEOUT','OOM','SPAWN_ERROR','NO_COMPOSITION','NO_TRANSITION_OUTPUT',
    'CRASH','INVALID_CERTIFICATE','INVALID_INPUT','VERIFICATION_INCONCLUSIVE','USAGE_ERROR',
    'SIGNALLED','UNKNOWN_EXIT','HARNESS_ERROR','INTERRUPTED_NOT_RETRIED'}
METRICS=(('states_discovered','Discovered states (first trial)',1),
    ('successor_queries','Successor queries (first trial)',1),
    ('transition_outcomes','Transition outcomes (first trial)',1),
    ('solver_time_ms','Solver time (seconds; five complete trials)',.001),
    ('peak_rss_bytes','Sampled peak RSS (GiB; five complete trials)',1/(1024**3)),
    ('output_policy_states','Output policy states (first trial)',1),
    ('output_policy_transitions','Output policy transitions (first trial)',1))

def read_csv(path):
    with path.open(newline='',encoding='utf-8-sig') as stream:return list(csv.DictReader(stream))
def write_csv(path,rows):
    fields=list(dict.fromkeys(key for row in rows for key in row))
    with path.open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(rows)
def truth(value):return str(value).lower()=='true'
def key(row):return row['model_id'],row['target_id'],row['method_id']
def number(value):
    try:
        result=float(value)
        return result if math.isfinite(result) else None
    except (TypeError,ValueError):return None
def tex(value):
    return ''.join({'\\':r'\textbackslash{}','_':r'\_','%':r'\%','&':r'\&','#':r'\#','{':r'\{','}':r'\}','~':r'\textasciitilde{}','^':r'\textasciicircum{}'}.get(c,c) for c in str(value))
def statuses(row):
    result={}
    for item in row.get('statuses','').split(';'):
        if ':' in item:
            rep,status=item.split(':',1)
            if rep.isdigit():result[int(rep)]=status
    return result
def complete_five(row):
    values=statuses(row)
    return (truth(row.get('timing_summary_eligible')) and not truth(row.get('invalid'))
            and not truth(row.get('inconsistent')) and row.get('completed_valid_repetitions') in ('5',5)
            and set(values)==set(range(1,6)) and len(set(values.values()))==1
            and all(status in GOOD for status in values.values()))
def triple(row,metric,scale=1):
    if not complete_five(row):return None
    values=tuple(number(row.get(metric+'_'+suffix)) for suffix in ('median','min','max'))
    if any(value is None for value in values):return None
    median,lo,hi=values
    if lo<0 or not lo<=median<=hi:raise ValueError('Invalid min/median/max for '+str(key(row))+' '+metric)
    return tuple(value*scale for value in values)
def structural(row,metric):
    if row.get('stage1_status') not in GOOD or truth(row.get('invalid')) or truth(row.get('inconsistent')):return None
    return number(row.get(metric))
def compact(value):
    if value==0:return '0'
    if abs(value)>=10000 or abs(value)<.001:return '%.2g'%value
    if abs(value)>=1000:return '%.0f'%value
    return ('%.3g'%value)
def range_cell(top,bottom):
    """Supplement-only range layout; manuscript cells always occupy one line."""
    return r'\begin{tabular}[c]{@{}c@{}}'+top+r'\\[-3pt]'+bottom+r'\end{tabular}'

def relative_width(row,metric='solver_time_ms',scale=.001):
    value=triple(row,metric,scale)
    if value is None:return None
    median,lo,hi=value
    return (hi-lo)/median if median else (math.inf if hi>lo else 0.)

def wide_range(row,metric='solver_time_ms',scale=.001):
    width=relative_width(row,metric,scale)
    return width is not None and width>.1 and not math.isclose(width,.1,rel_tol=1e-12)

def capture_cap(row):
    return (row.get('method_id')=='legacy_ducs' and row.get('stage1_status')=='CRASH'
            and row.get('display_censor_reason')=='author_capture_cap')

def mark_capture_caps(campaign):
    """Annotate display copies only after inspecting the saved capture exception."""
    initial={key(row):row for row in campaign.initial}
    for row in campaign.rows:
        row.pop('display_censor_reason',None)
        if row.get('method_id')!='legacy_ducs' or row.get('stage1_status')!='CRASH':continue
        job=initial[key(row)]['job_id']
        path=campaign.path/'runs'/job/'stderr.txt'
        evidence=path.read_text(errors='replace') if path.is_file() else ''
        if all(token in evidence for token in (
                'MTS exceeds the registered finite resource profile',
                'M9MtsSnapshot.requireResourceCensus',
                'M9MtsSnapshot.capturePass(M9MtsSnapshot.java:77)',
                'UpdatingControllerSafetySynthesizer')):
            row['display_censor_reason']='author_capture_cap'

def failure_codes(row):
    values=list(statuses(row).values()) or [row.get('stage1_status','NOT_RUN')]
    if truth(row.get('inconsistent')) or len(set(values)&GOOD)>1:return ['INC']
    codes=[]
    if 'TIMEOUT' in values or 'SKIPPED_AFTER_RESOURCE_FAILURE' in values and 'OOM' not in values:codes.append('TO')
    if 'OOM' in values:codes.append('OOM')
    if 'CRASH' in values:codes.append('N/M' if capture_cap(row) else 'CRASH')
    if 'INTERRUPTED_NOT_RETRIED' in values:codes.append('INTERRUPTED')
    if truth(row.get('invalid')) and not codes:codes.append('INV')
    unusual=[v for v in values if v not in GOOD|SKIPS|{'NOT_RUN','TIMEOUT','OOM','CRASH','INTERRUPTED_NOT_RETRIED'}]
    if unusual:codes.append('OTHER')
    if not codes and any(v=='NOT_RUN' for v in values):codes.append('P')
    return codes

def job_key(row):return key(row)+(int(row['repetition']),)

def planned_keys(config):
    """The full denominator, including repetitions later explicitly skipped."""
    return {(model['id'],target,method,rep)
            for model in config['models']
            for target in model.get('target_ids',[t['id'] for t in config['targets']])
            for method in model.get('method_ids',[m['id'] for m in config['methods']])
            for rep in range(1,int(model.get('repetitions',config['repetitions']))+1)}

def unique_index(rows,identity,label):
    result={identity(row):row for row in rows}
    if len(result)!=len(rows):raise ValueError('Duplicate '+label)
    return result

def strict_statuses(row):
    result={}
    for item in row.get('statuses','').split(';'):
        match=re.fullmatch(r'([1-9][0-9]*):([A-Z_]+)',item)
        if match is None or int(match[1]) in result:raise ValueError('Malformed/repeated summary repetition: '+str(key(row)))
        result[int(match[1])]=match[2]
    return result

def same_number(left,right):
    left,right=number(left),number(right)
    return left is None and right is None or (left is not None and right is not None and math.isclose(left,right,rel_tol=1e-9,abs_tol=1e-9))

def require_complete(campaign,expected_config=None):
    """Accept completed collection evidence, without trusting timestamps/flags alone."""
    path=campaign.path;expected=planned_keys(expected_config or campaign.config)
    if not expected or planned_keys(campaign.config)!=expected:raise ValueError('Returned config differs from the full campaign denominator')
    required=['plan.json','raw_runs.csv','summary.csv','stage1.csv']
    if any(rep>1 for *_,rep in expected):required.append('stage2_plan.json')
    missing=[name for name in required if not (path/name).is_file()]
    if missing:raise ValueError('Incomplete campaign: missing '+', '.join(missing))
    plan=json.loads((path/'plan.json').read_text())
    jobs=unique_index(plan['jobs'],job_key,'planned job')
    if set(jobs)!=expected or int(plan['job_count'])!=len(expected):raise ValueError('Full plan/config job mismatch')
    if len({job['job_id'] for job in jobs.values()})!=len(jobs):raise ValueError('Duplicate planned job_id')
    raw=unique_index(read_csv(path/'raw_runs.csv'),job_key,'raw repetition')
    initial=unique_index(campaign.initial,key,'stage1 cell');summary=unique_index(campaign.rows,key,'summary cell')
    cells={identity[:3] for identity in expected}
    if set(raw)!=expected or set(initial)!=cells or set(summary)!=cells:raise ValueError('Incomplete campaign: missing or extra cells/repetitions')
    for identity,row in raw.items():
        job=jobs[identity];status=row['process_status']
        if status not in TERMINAL or not truth(row.get('completed')):raise ValueError('Nonterminal raw repetition: '+str(identity)+' '+status)
        job_id=job['job_id']
        if row.get('job_id')!=job_id or '/' in job_id or '\\' in job_id or job_id in {'.','..'}:raise ValueError('Raw/plan job identity mismatch')
        meta_path=path/'runs'/job_id/'meta.json'
        if not meta_path.is_file():raise ValueError('Incomplete campaign: missing run metadata '+job_id)
        meta=json.loads(meta_path.read_text())
        # The synthetic adapter maps a successful process with decision=losing
        # to UNREALIZABLE. Other backends preserve the process status exactly.
        mapped_hub=(campaign.config.get('backend')=='synthetic_hub' and meta.get('status')=='SUCCESS'
                    and status=='UNREALIZABLE' and row.get('revised_decision')=='losing')
        if meta.get('completed') is not True or (meta.get('status')!=status and not mapped_hub):raise ValueError('Incomplete/stale run metadata: '+job_id)
        if meta.get('job',{}).get('job_id')!=job_id or job_key(meta['job'])!=identity:raise ValueError('Run metadata/plan identity mismatch: '+job_id)
        if status in SKIPS and (identity[3]==1 or not meta.get('skip_reason')):raise ValueError('Skip lacks a later-repetition reason: '+job_id)
        prior=[raw[k] for k in expected if k[:3]==identity[:3] and k[3]<identity[3]]
        if status=='SKIPPED_AFTER_RESOURCE_FAILURE' and not any(r['process_status'] in {'OOM','TIMEOUT'} for r in prior):raise ValueError('Resource skip has no preceding resource failure: '+job_id)
        if status in {'SKIPPED_AFTER_INVALID_OR_INCONSISTENT','SKIPPED_INELIGIBLE_STAGE1'} and not any(
                r['process_status'] not in GOOD or truth(r.get('invalid')) or truth(r.get('inconsistent')) for r in prior):raise ValueError('Invalid/inconsistent skip lacks preceding evidence: '+job_id)
    for identity,row in summary.items():
        group=[raw[k] for k in sorted(expected) if k[:3]==identity]
        first=raw[identity+(1,)];saved_statuses=strict_statuses(row)
        if saved_statuses!={int(r['repetition']):r['process_status'] for r in group}:raise ValueError('Stale summary statuses: '+str(identity))
        if row.get('stage1_status')!=first['process_status'] or initial[identity]!=first:raise ValueError('Stale stage1 collection: '+str(identity))
        if int(row['planned_total_repetitions'])!=len(group) or not truth(row.get('stage1_denominator_included')):raise ValueError('Summary denominator mismatch: '+str(identity))
        valid=[r for r in group if r['process_status'] in GOOD and not truth(r.get('invalid')) and not truth(r.get('inconsistent'))]
        flags={flag:any(truth(r.get(flag)) for r in group) for flag in ('invalid','inconsistent')}
        if any(truth(row.get(flag))!=value for flag,value in flags.items()) or int(row['completed_valid_repetitions'])!=len(valid):raise ValueError('Stale summary validity counts: '+str(identity))
        complete=len(valid)==len(group)==5
        if truth(row.get('timing_summary_eligible'))!=complete:raise ValueError('Stale timing eligibility: '+str(identity))
        for metric in ('solver_time_ms','elapsed_monotonic_seconds','peak_rss_bytes'):
            values=[number(r.get(metric)) for r in valid]
            values=[] if any(value is None for value in values) else values
            for suffix,function in (('median',statistics.median),('min',min),('max',max)):
                expected_value=function(values) if complete and len(values)==5 else None
                if not same_number(row.get(metric+'_'+suffix),expected_value):raise ValueError('Stale summary metric '+metric+' '+str(identity))
        for metric,source in (('states_discovered','states_discovered'),('successor_queries','successor_queries'),
                              ('transition_outcomes','transition_outcomes'),('output_policy_states','output_controller_states'),
                              ('output_policy_transitions','output_controller_transitions')):
            if not same_number(row.get(metric),first.get(source)):raise ValueError('Stale structural summary '+metric+' '+str(identity))
    if campaign.plan:
        if int(campaign.plan['stage1_denominator'])!=len(cells):raise ValueError('Stage2 denominator mismatch')
        eligible=unique_index(campaign.plan['eligible_jobs'],job_key,'stage2 eligible repetition')
        excluded=unique_index(campaign.plan['exclusions'],key,'stage2 exclusion')
        eligible_cells={k[:3] for k in eligible}
        later={k for k in expected if k[3]>1}
        if later and int(campaign.plan['additional_repetitions'])!=max(k[3] for k in expected)-1:raise ValueError('Stage2 repetition count mismatch')
        if set(eligible)!={k for k in later if k[:3] in eligible_cells} or not set(eligible)<=later:raise ValueError('Incomplete stage2 eligible plan')
        if later and (eligible_cells&set(excluded) or eligible_cells|set(excluded)!=cells):raise ValueError('Stage2 eligible/excluded partition mismatch')
        for identity,job in eligible.items():
            if job['job_id']!=jobs[identity]['job_id'] or initial[identity[:3]]['process_status'] not in GOOD:raise ValueError('Stage2 eligible job mismatch')
        for identity,exclusion in excluded.items():
            if identity not in cells or exclusion['reason']!=initial[identity]['process_status']:raise ValueError('Stage2 exclusion mismatch')
            # A resumed stage2 may newly exclude a previously eligible cell
            # after a decision disagreement. Its already completed trials stay.
            if exclusion['reason'] not in GOOD and any(raw[k]['process_status'] not in SKIPS for k in later if k[:3]==identity):raise ValueError('Excluded cell has an unaccounted later trial')
    return True

class Campaign:
    def __init__(self,path,mode,expected_config=None):
        self.path=path;self.rows=[];self.initial=[];self.plan={};self.config={}
        if path is None or not path.exists():return
        if mode=='xeon':
            config_path=path/'config.json';environment_path=path/'environment.json'
            if not config_path.is_file() or not environment_path.is_file():raise ValueError('Xeon input lacks config/environment: '+str(path))
            self.config=json.loads(config_path.read_text())
            environment=json.loads(environment_path.read_text())
            if (environment.get('system')!='Windows' or self.config.get('java_heap')!='64g'
                or self.config.get('timeout_seconds')!=1200 or 'pilot' in self.config.get('experiment_id','').lower()):
                raise ValueError('Input is not the fixed Windows 64g/1200s campaign: '+str(path))
        for name,attribute in (('summary.csv','rows'),('stage1.csv','initial')):
            if (path/name).is_file():setattr(self,attribute,read_csv(path/name))
        if (path/'stage2_plan.json').is_file():self.plan=json.loads((path/'stage2_plan.json').read_text())
        if len({key(row) for row in self.rows})!=len(self.rows):raise ValueError('Duplicate summary cells: '+str(path))
        bykey={key(row):row for row in self.initial}
        for row in self.rows:
            if key(row) in bykey and row.get('stage1_status')!=bykey[key(row)].get('process_status'):
                raise ValueError('summary/stage1 status disagreement: '+str(key(row)))
        self.index={key(row):row for row in self.rows}
        if mode=='xeon':
            require_complete(self,expected_config)
            mark_capture_caps(self)

def optional_xeon(path,expected_config):
    """An incomplete RQ4 return contributes pending cells, never partial numbers."""
    try:return Campaign(path,'xeon',expected_config)
    except (ValueError,OSError,KeyError,TypeError) as error:
        result=Campaign(None,'xeon');result.pending_reason=str(error)
        print('RQ4 pending ('+path.name+'): '+str(error))
        return result

def pending(model,target,method):
    return dict(model_id=model,target_id=target,method_id=method,stage1_status='NOT_RUN',statuses='1:NOT_RUN',
                invalid='False',inconsistent='False',completed_valid_repetitions='0',timing_summary_eligible='False')

# These are the two pre-authorized follow-ups, not a general best-of-runs selector.
SUPPLEMENTS={
    'pc':('rq3_supplement_pc_arms2_r2_fg_3600',('productioncell_arms2','r2','fg_ducs_otf'),3600,1,'TIMEOUT'),
    'workflow':('rq3_supplement_workflow_r2_direct_full',('workflow','r2','direct_full'),1200,5,'INTERRUPTED_NOT_RETRIED')}
FROZEN_JAR_SHA256='fbdc25f58d5441ed906d408a94b7414c9d9c3ed35e2ebce22d9751729967ba07'

def digest_file(path):
    value=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):value.update(block)
    return value.hexdigest()

def host_profile(environment):
    """Compare stable recorded host/runtime facts, not dates or free disk space."""
    probe=environment['windows_cim_probe']
    if probe['exit_code']!=0:raise ValueError('Missing successful Windows CIM probe')
    cim=json.loads(probe['stdout']);os=cim['operating_system']
    profile={field:environment[field] for field in ('system','machine','processor','logical_cpu_count',
        'physical_memory_bytes_portable','java_version_probe','python_version')}
    profile.update(cpu=cim['cpu'],computer=cim['computer'],os={f:os[f] for f in ('Caption','Version','BuildNumber')})
    power=environment['windows_power_plan_probe']
    guid=re.search(r'[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}',power['stdout'],re.I)
    if power['exit_code']!=0 or guid is None:raise ValueError('Missing Windows power-plan identity')
    profile['power_plan_guid']=guid[0].lower()
    if profile['system']!='Windows' or 'W-2265' not in profile['cpu']['Name']:
        raise ValueError('Follow-up is not the recorded Xeon host profile')
    return profile

def check_returned_artifacts(folder,meta):
    if set(meta.get('artifact_digests',{}))!=set(meta.get('artifacts',{})) or not meta.get('artifact_digests'):
        raise ValueError('Missing returned artifact digests')
    for name,expected in meta['artifact_digests'].items():
        path=(folder/meta['artifacts'][name].replace('\\','/')).resolve()
        if not path.is_relative_to(folder.resolve()):raise ValueError('Artifact path escapes campaign')
        if path.is_file()!=expected['exists']:raise ValueError('Artifact existence mismatch: '+name)
        if expected['exists'] and (path.stat().st_size!=expected['bytes'] or digest_file(path)!=expected['sha256']):
            raise ValueError('Artifact digest mismatch: '+name)

def check_environment_identity(path,environment,source_sha256):
    """Verify original bytes, or explicitly validate distribution redaction provenance.

    The latter establishes the declared personal-path transformation only; the
    redacted file cannot independently authenticate the unavailable source bytes.
    """
    if digest_file(path)==source_sha256:return 'source_bytes_verified'
    note=environment.get('distribution_redaction')
    allowed={'python_executable','java_executable','java_home'}
    if (environment.get('system')!='Windows' or not isinstance(note,dict)
        or set(note)!={'source_sha256','changed_fields','kind'}
        or note.get('kind')!='personal_paths_only'
        or not isinstance(source_sha256,str) or re.fullmatch(r'[0-9a-f]{64}',source_sha256) is None
        or note.get('source_sha256')!=source_sha256):
        raise ValueError('Execution environment digest/redaction provenance mismatch')
    changed=note['changed_fields']
    if (not isinstance(changed,list) or not changed or any(not isinstance(field,str) for field in changed)
        or len(changed)!=len(set(changed)) or not set(changed)<=allowed):
        raise ValueError('Environment redaction contains non-permitted or duplicate fields')
    if any(not isinstance(environment.get(field),str) or '<USER_HOME>' not in environment[field] for field in changed):
        raise ValueError('Environment redaction field lacks the personal-path marker')
    marked={field for field,value in environment.items() if field!='distribution_redaction'
            and '<USER_HOME>' in json.dumps(value)}
    if marked!=set(changed):raise ValueError('Environment redaction markers differ from declared fields')
    return 'distribution_personal_path_redaction'

def check_execution_record(folder,config,environment,meta,job,raw,*,interrupted=False):
    """Cross-check saved execution evidence; never infer timeout from elapsed time."""
    if meta['job']!=job:raise ValueError('Full plan/metadata job differs')
    if meta['config_sha256']!=digest_file(folder/'config.json'):raise ValueError('Execution config digest mismatch')
    plan=json.loads((folder/'plan.json').read_text());claimed=plan.pop('plan_sha256')
    actual=hashlib.sha256(json.dumps(plan,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if claimed!=actual or meta['plan_sha256']!=claimed:raise ValueError('Execution plan digest mismatch')
    environment_verification=check_environment_identity(folder/'environment.json',environment,
        meta['execution_environment_fingerprint_sha256'])
    jar=meta['classpath']
    if jar!=environment['classpath'] or jar.get('sha256')!=FROZEN_JAR_SHA256 or not jar.get('exists'):
        raise ValueError('Frozen JAR identity differs')
    if meta['input_model']['sha256']!=environment['model_input_bytes'][job['model_path']]:
        raise ValueError('Input model identity differs')
    command=meta['command'];properties={arg.split('=',1)[0][2:]:arg.split('=',1)[1] for arg in command if arg.startswith('-D') and '=' in arg}
    expected_properties=dict(job['jvm_properties'],**{'java.awt.headless':'true','mtsa.build.commit':'jar-sha256-'+FROZEN_JAR_SHA256})
    if properties!=expected_properties or command.count('-Xmx'+config['java_heap'])!=1:
        raise ValueError('JVM command properties/heap differ')
    for flag,value in (('--target',job['target_name']),('--transition-output',config['transition_output_mode'])):
        if command[command.index(flag)+1]!=value:raise ValueError('JVM command '+flag+' differs')
    for flag,value in (('-cp',config['classpath']),('--lts',job['model_path'])):
        if not command[command.index(flag)+1].replace('\\','/').endswith('/'+value):raise ValueError('JVM input path differs')
    if config['main_class'] not in command or meta['timeout_seconds']!=config['timeout_seconds']:
        raise ValueError('Runner/cap differs')
    if interrupted:
        if meta['status']!='INTERRUPTED_NOT_RETRIED':raise ValueError('Expected original interrupted record')
        return environment_verification
    check_returned_artifacts(folder,meta)
    if meta['status']!='TIMEOUT' or meta.get('timed_out') is not True or not meta.get('timeout_termination_action'):
        raise ValueError('AD follow-up lacks recorded timeout termination')
    if datetime.fromisoformat(meta['finished_utc'])<datetime.fromisoformat(meta['started_utc']):
        raise ValueError('Execution dates are reversed')
    for field in ('elapsed_monotonic_seconds','peak_rss_bytes'):
        if number(meta[field]) is None or not same_number(meta[field],raw[field]):raise ValueError('Raw/metadata metric differs: '+field)
    if meta['rss_measurement_kind']!='windows_process_working_set' or meta['rss_measurement_status']!='measured':
        raise ValueError('Unexpected RSS measurement scope')
    return environment_verification

def provenance_record(folder,config,meta,original_id,role,profile,environment_verification='not_applicable_skipped'):
    job=meta['job'];rss=number(meta.get('peak_rss_bytes'))
    return dict(role=role,campaign=folder.name,config_source=folder.name+'/config.json',
        job_id=job['job_id'],model_id=job['model_id'],target_id=job['target_id'],method_id=job['method_id'],
        repetition=job['repetition'],planned_repetitions=config['repetitions'],
        original_record='rq3/runs/'+original_id+'/meta.json',
        source_meta=folder.name+'/runs/'+job['job_id']+'/meta.json',
        status=meta['status'],started_utc=meta.get('started_utc',''),finished_utc=meta.get('finished_utc',''),
        timeout_seconds=config['timeout_seconds'],java_heap=config['java_heap'],
        elapsed_monotonic_seconds=meta.get('elapsed_monotonic_seconds',''),
        peak_rss_bytes=meta.get('peak_rss_bytes',''),peak_rss_gib=rss/(1024**3) if rss is not None else '',
        rss_measurement_kind=meta.get('rss_measurement_kind',''),skip_reason=meta.get('skip_reason',''),
        timing_median_eligible=False,jar_sha256=meta.get('classpath',{}).get('sha256',''),
        input_sha256=meta.get('input_model',{}).get('sha256',''),
        host_cpu=profile['cpu']['Name'],logical_cpu_count=profile['logical_cpu_count'],
        physical_memory_bytes=profile['physical_memory_bytes_portable'],os_version=profile['os']['Version'],
        environment_verification=environment_verification,
        environment_source_sha256=meta.get('execution_environment_fingerprint_sha256',''),
        heap_occupancy_measured=False)

def integrate_supplementary(campaign,input_root):
    """Validate AD evidence, then annotate display copies without replacing raw fields."""
    folders=[input_root/spec[0] for spec in SUPPLEMENTS.values()]
    if not any(path.exists() for path in folders):return
    if not all(path.is_dir() for path in folders):raise ValueError('Incomplete AD return: both authorized campaigns are required')
    original_env=json.loads((campaign.path/'environment.json').read_text());profile=host_profile(original_env)
    original_jobs={job_key(j):j for j in json.loads((campaign.path/'plan.json').read_text())['jobs']}
    records={}
    for label,(name,identity,cap,repetitions,original_status) in SUPPLEMENTS.items():
        folder=input_root/name;config=json.loads((folder/'config.json').read_text())
        expected=json.loads((HERE.parent/'rq3_supplement/configs'/(name+'.json')).read_text())
        if config!=expected or config['timeout_seconds']!=cap or config['repetitions']!=repetitions or config['java_heap']!='64g':
            raise ValueError('Follow-up configuration differs from the authorized setting')
        follow=Campaign(folder,'read-only-follow-up');follow.config=config
        require_complete(follow,expected)  # Also accepts a single planned trial; no median is eligible.
        env=json.loads((folder/'environment.json').read_text())
        if host_profile(env)!=profile:raise ValueError('Follow-up host/runtime differs from original RQ3')
        original=campaign.index[identity]
        if original['stage1_status']!=original_status:raise ValueError('AD original status differs')
        if set(follow.index)!={identity}:raise ValueError('AD follow-up must retain its single authorized cell')
        sequence=statuses(follow.rows[0])
        if sequence!={rep:'TIMEOUT' if rep==1 else 'SKIPPED_AFTER_RESOURCE_FAILURE' for rep in range(1,repetitions+1)}:
            raise ValueError('AD return differs from the one-time timeout and explicit skip record')
        for field in ('backend','classpath','main_class','java_heap','parallel_trials','rss_poll_interval_seconds','transition_output_mode'):
            if config[field]!=campaign.config[field]:raise ValueError('Original/follow-up execution setting differs: '+field)
        old_job=original_jobs[identity+(1,)];old_meta=json.loads((campaign.path/'runs'/old_job['job_id']/'meta.json').read_text())
        old_raw=next(row for row in campaign.initial if key(row)==identity)
        old_verification=check_execution_record(campaign.path,campaign.config,original_env,old_meta,old_job,old_raw,
                               interrupted=original_status=='INTERRUPTED_NOT_RETRIED')
        records[label]=dict(original=provenance_record(campaign.path,campaign.config,old_meta,old_job['job_id'],'original',profile,old_verification),followup=[])
        plan=json.loads((folder/'plan.json').read_text());raw={job_key(row):row for row in read_csv(folder/'raw_runs.csv')}
        for job in plan['jobs']:
            meta=json.loads((folder/'runs'/job['job_id']/'meta.json').read_text())
            environment_verification='not_applicable_skipped'
            for field in ('model_path','target_name','jvm_properties'):
                if job[field]!=old_job[field]:raise ValueError('Original/follow-up job differs: '+field)
            if job['repetition']==1:
                environment_verification=check_execution_record(folder,config,env,meta,job,raw[job_key(job)])
                if meta['input_model']!=old_meta['input_model']:raise ValueError('Original/follow-up input bytes differ')
            records[label]['followup'].append(provenance_record(folder,config,meta,old_job['job_id'],'supplementary',profile,environment_verification))
        print('Validated AD '+name+': '+str(sequence)+'; original '+original_status+' retained; no timing median')
    # Apply only after BOTH returns pass every gate. Original statuses/counts stay available.
    campaign.supplementary=records
    row=campaign.index[SUPPLEMENTS['workflow'][1]]
    row['ad_effective_status']='TIMEOUT';row['ad_source_campaign']=SUPPLEMENTS['workflow'][0]
    row['ad_original_status']=row['stage1_status']

def effective_status(row):
    if (key(row)==SUPPLEMENTS['workflow'][1] and row.get('stage1_status')=='INTERRUPTED_NOT_RETRIED'
        and row.get('ad_effective_status')=='TIMEOUT' and row.get('ad_source_campaign')==SUPPLEMENTS['workflow'][0]):
        return 'TIMEOUT'
    return row.get('stage1_status','NOT_RUN')

def render_supplementary_returned(campaign,output):
    rows=[record for value in campaign.supplementary.values() for record in [value['original'],*value['followup']]]
    write_csv(output/'rq3-supplementary-provenance.csv',rows)
    lines=[r'\noindent\textbf{Authorized RQ3 follow-ups: original and returned records}\par',
        r'Workflow/R2 Direct-Full uses the pre-authorized same-setting replacement for its table status ($\mathrm{TO}^{\ddagger}$). '
        r'The original operational interruption remains below. PC Arms=2/R2 retains its original 1,200 s TO; '
        r'the 3,600 s single trial is a separate sensitivity check. Neither follow-up supplies a median or performance ratio.',
        r'\begingroup\scriptsize\begin{longtable}{@{}p{.21\linewidth}p{.73\linewidth}@{}}\toprule Field & Recorded value\\\midrule\endhead']
    for row in rows:
        if row['status'] in SKIPS:continue
        label=MODEL_LABELS[row['model_id']]+'/'+row['target_id'].upper()+'; '+row['method_id']+'; '+row['role']
        fields=[('Record',label),('Campaign / config',row['campaign']+' / config.json'),
            ('Start / end (UTC)',(row['started_utc'] or 'not recorded')+' / '+(row['finished_utc'] or 'not recorded')),
            ('Cap / heap / status',str(row['timeout_seconds'])+' s / '+row['java_heap']+' / '+row['status']),
            ('Elapsed / peak RSS',('not recorded' if row['elapsed_monotonic_seconds']=='' else f"{row['elapsed_monotonic_seconds']:.4f} s")+' / '+
                ('not recorded' if row['peak_rss_gib']=='' else f"{row['peak_rss_gib']:.4f} GiB (process working set)")),
            ('Original association',row['original_record'])]
        for field,value in fields:lines.append(tex(field)+' & '+tex(value)+r'\\')
        lines.append(r'\addlinespace[4pt]')
    lines.extend([r'\bottomrule\end{longtable}\endgroup',
        r'After repetition 1 times out, Workflow repetitions 2--5 have status \path{SKIPPED_AFTER_RESOURCE_FAILURE}; '
        r'all five planned slots are retained in the generated provenance CSV. The PC follow-up planned one trial.',
        r'Returned artifact digests and saved configuration/plan identities are verified. '
        r'Input bytes, frozen JAR identity, JVM arguments, and stable host/runtime facts match the original records. '
        r'The PC follow-up changes only the time cap and repetition count. All use the Xeon W-2265, 24 logical CPUs, '
        r'Windows 10 build 19045, Temurin 17.0.20.1, and a 64 GiB heap cap.',
        r'Peak RSS is sampled Windows process working-set memory. '
        r'Heap occupancy was not recorded; the limiting resource remains unidentified. '
        r'The recorded elapsed duration includes timeout termination overhead. The interrupted original has no recorded end time or RSS.'])
    if any(row['environment_verification']=='distribution_personal_path_redaction' for row in rows):
        lines.append(r'\par The distributed environment files carry a personal-path redaction annotation '
            r'linked to the source digest recorded in each execution. Allowed fields are the Python/Java executable '
            r'and Java home paths. This checks the declared redaction provenance; '
            r'the unavailable original environment bytes are not reverified from the distributed copy.')
    (output/'rq3-supplementary-provenance.tex').write_text('\n'.join(lines)+'\n')
    (output/'rq3-supplementary-footnote.tex').write_text(supplementary_footnote(campaign)+'\n')
    pc=campaign.supplementary['pc']['followup'][0];wf=campaign.supplementary['workflow']['followup'][0]
    df=[row for row in campaign.rows if row['method_id']=='direct_full']
    macros={'ADDirectFullWins':str(sum(effective_status(row)=='SUCCESS' for row in df)),
        'ADDirectFullTimeouts':str(sum(effective_status(row)=='TIMEOUT' for row in df)),
        'ADWorkflowCapSeconds':str(wf['timeout_seconds']),'ADWorkflowElapsedSeconds':f"{wf['elapsed_monotonic_seconds']:.1f}",
        'ADWorkflowPeakRSSGiB':f"{wf['peak_rss_gib']:.1f}",'ADPCCapSeconds':str(pc['timeout_seconds']),
        'ADPCElapsedSeconds':f"{pc['elapsed_monotonic_seconds']:.1f}",'ADPCPeakRSSGiB':f"{pc['peak_rss_gib']:.1f}"}
    (output/'rq3-ad-numbers.tex').write_text('% Derived from validated returned raw; elapsed/RSS are single-trial references, not medians.\n'+
        '\n'.join('\\providecommand{\\'+name+'}{'+value+'}' for name,value in macros.items())+'\n')
    (output/'rq3-ad-summary.tex').write_text(
        r'The authorized same-setting Workflow/R2 Direct-Full replacement timed out at \ADWorkflowCapSeconds{} s; '
        r'its original operational interruption remains in S4. The separate \ADPCCapSeconds{} s PC Arms=2/R2 FG trial '
        r'also timed out, with peak process RSS \ADPCPeakRSSGiB{} GiB under the 64 GiB heap cap. '
        r'Neither follow-up contributes a timing median.'+'\n')

def cell_text(row,metric='solver_time_ms',scale=.001,show_range=False):
    if effective_status(row)!=row.get('stage1_status'):return r'TO$^{\ddagger}$'
    codes=failure_codes(row)
    initial=row.get('stage1_status','NOT_RUN')
    if initial=='TIMEOUT':return 'TO'
    if initial=='OOM':return 'OOM'
    if initial=='CRASH':return 'N/M' if capture_cap(row) else 'CRASH'
    if initial=='INTERRUPTED_NOT_RETRIED':return 'INTERRUPTED'
    if 'INC' in codes or 'INV' in codes:return codes[0]
    if initial not in GOOD:return 'P' if initial=='NOT_RUN' else 'OTHER'
    decision='W' if initial=='SUCCESS' else 'L'
    if metric in ('solver_time_ms','peak_rss_bytes'):
        value=triple(row,metric,scale)
        if value is not None:
            median,lo,hi=value
            return (range_cell(decision+' '+compact(median),r'\mbox{['+compact(lo)+', '+compact(hi)+']}') if show_range
                    else decision+' '+compact(median)+(r'$^{\dagger}$' if wide_range(row,metric,scale) else ''))
        count=min(int(row.get('completed_valid_repetitions','0')),sum(status in GOOD for status in statuses(row).values()))
        suffix='/'.join(code for code in codes if code!='P')
        return decision+' ('+str(count)+'/5; '+(suffix or 'pending')+')'
    value=structural(row,metric)
    return compact(value*scale) if value is not None else '--'

def supplementary_tag(model,target,method):
    return {('productioncell_arms2','r2','fg_ducs_otf'):'a',
            ('workflow','r2','direct_full'):'b'}.get((model,target,method),'')

def supplementary_footnote(campaign=None):
    if getattr(campaign,'supplementary',None):
        pc=campaign.supplementary['pc']['followup'][0]
        return (r'\par{\scriptsize $^{a}$ The separate '+f"{pc['timeout_seconds']:,.0f}"+
                r' s single trial also timed out (peak process RSS '+f"{pc['peak_rss_gib']:.1f}"+
                r' GiB; 64 GiB heap cap). $^{\ddagger}$ The original trial was operationally interrupted; '
                r'the pre-authorized same-setting replacement timed out at 1,200 s. '
                r'Both records remain in Supplement~S4. RSS does not establish heap saturation.}')
    return (r'\par{\scriptsize $^{a}$ Separate 3,600 s, single-run FG follow-up: pending. '
            r'$^{b}$ Separate five-trial Direct-Full follow-up: pending. '
            r'Original TO/INTERRUPTED statuses are retained; provenance in Supplement~S4.}')

def render_supplementary_pending(campaign,output,input_root):
    """Display preparation only: returned follow-ups never overwrite RQ3 cells."""
    if getattr(campaign,'supplementary',None):
        return render_supplementary_returned(campaign,output)
    config_dir=HERE.parent/'rq3_supplement/configs';rows=[]
    index={key(row):row for row in getattr(campaign,'rows',[])}
    for name in ('rq3_supplement_pc_arms2_r2_fg_3600','rq3_supplement_workflow_r2_direct_full'):
        config=json.loads((config_dir/(name+'.json')).read_text())
        model=config['models'][0];target=model.get('target_ids',[t['id'] for t in config['targets']])[0];method=model['method_ids'][0]
        original=index.get((model['id'],target,method),pending(model['id'],target,method))
        returned=(input_root/name).exists()
        rows.append(dict(tag=supplementary_tag(model['id'],target,method),campaign=name,
            model_id=model['id'],target_id=target,method_id=method,
            original_status=original['stage1_status'],java_heap=config['java_heap'],
            timeout_seconds=config['timeout_seconds'],planned_repetitions=config['repetitions'],
            evidence='pending validated integration' if returned else 'pending; raw not returned',
            measured_decision='',measured_seconds='',
            config_source='experiments/rq3_supplement/configs/'+name+'.json'))
    lines=[r'\noindent\textbf{Separate RQ3 follow-ups (pending)}\par\smallskip',
           r'\begingroup\scriptsize\setlength{\tabcolsep}{4pt}\begin{tabular}{@{}llllll@{}}',
           r'\toprule Ref. & Instance / method & Original & Heap / cap & Trials & Return \\ \midrule']
    for row in rows:
        label=MODEL_LABELS.get(row['model_id'],row['model_id'])+'/'+row['target_id'].upper()+' / '+('FG' if row['method_id']=='fg_ducs_otf' else 'DF')
        initial='TO' if row['original_status']=='TIMEOUT' else 'INTERRUPTED' if row['original_status']=='INTERRUPTED_NOT_RETRIED' else row['original_status']
        lines.append(' & '.join(map(tex,[row['tag'],label,initial,row['java_heap']+' / '+str(row['timeout_seconds'])+' s',row['planned_repetitions'],'pending']))+r'\\')
    lines.extend([r'\bottomrule\end{tabular}\endgroup',r'\par\smallskip The original 1,200 s campaign is unchanged. '
        r'These separately configured follow-ups contribute no measurements before completed-return validation. '
        r'The single 3,600 s trial cannot contribute a five-run median.'])
    for row in rows:lines.append(r'\par\scriptsize '+tex(row['tag'])+r': \texttt{'+tex(row['campaign'])+'}.')
    (output/'rq3-supplementary-provenance.tex').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    (output/'rq3-supplementary-footnote.tex').write_text(supplementary_footnote()+'\n',encoding='utf-8')
    write_csv(output/'rq3-supplementary-provenance.csv',rows)

def table(rows,config,metric='solver_time_ms',scale=.001,show_range=False):
    index={key(row):row for row in rows};lines=[r'\begingroup\scriptsize\setlength{\tabcolsep}{3pt}',
        r'\begin{tabular}{@{}llccccc@{}}',r'\toprule',
        'Model & Req. & '+' & '.join(LABELS)+r'\\',r'\midrule']
    for model in config['models']:
        for i,target in enumerate(config['targets']):
            label=MODEL_LABELS.get(model['id'],model['id']) if i==0 else ''
            cells=[cell_text(index.get((model['id'],target['id'],method),pending(model['id'],target['id'],method)),metric,scale,show_range) for method in METHODS]
            if not show_range and metric=='solver_time_ms':
                for j,method in enumerate(METHODS):
                    tag=supplementary_tag(model['id'],target['id'],method)
                    if tag and r'\ddagger' not in cells[j]:cells[j]+=r'\textsuperscript{'+tag+'}'
            lines.append(tex(label)+' & '+tex(target['id'].upper())+' & '+' & '.join(cells)+r'\\')
        lines.append(r'\addlinespace[2pt]')
    lines.extend([r'\bottomrule',r'\end{tabular}\endgroup'])
    return '\n'.join(lines)+'\n'

def render_rq3(campaign,mode,output,config):
    rows=getattr(campaign,'rows',[])
    heading={'placeholder':'Xeon results pending; no measurements shown.',
             'pilot':'MAC PILOT ONLY: 15 first trials; other cells are unmeasured placeholders.',
             'fixture':'SYNTHETIC TYPESETTING FIXTURE: no experimental observations.',
             'xeon':'Windows Xeon campaign; all 27 instances and five methods retained.'}[mode]
    note=('W/L: first-trial winning/losing decision. Time is in seconds; a median [min, max] appears only for five valid, '
          'consistent completed trials in Supplement S4. The main table shows medians only. W/L (n/5) has no timing estimate. TO: timeout; OOM: out of memory; '
          'CRASH: process exception; INTERRUPTED: operational interruption, not retried. '
          'P: pending/unmeasured; INV: invalid input/check failure; INC: inconsistent decisions; OTHER: another saved status. '
          'Legacy has its native semantics and is a reference, not an atomic-bulk comparator.')
    unusual=sorted({status for row in rows for status in statuses(row).values() if status not in GOOD|SKIPS|{'NOT_RUN','TIMEOUT','OOM','CRASH','INTERRUPTED_NOT_RETRIED'}})
    if unusual:note+=' Other saved statuses: '+', '.join(unusual)+'.'
    if getattr(campaign,'plan',{}):
        note+=' Saved stage-2 plan: '+str(campaign.plan.get('stage1_denominator','?'))+' first-stage cells; '+str(len(campaign.plan.get('eligible_jobs',[])))+' eligible additional jobs.'
    if mode=='xeon':
        note=('W/L: winning/losing. Seconds: median only for five valid, consistent completions; ranges in S4. '
              'TO: 1,200 s timeout; OOM: out of memory. N/M (capture cap): author-side M9MtsSnapshot instrumentation '
              'stops before synthesis at its fixed 250,000-state cap; no evidence of Legacy capability or solver failure. '
              'Original operational interruptions are retained in S4. Legacy uses native semantics. '
              'Other incomplete groups show statuses, without medians.')
    range_note=r' $\dagger$: $(\max-\min)/\mathrm{median}>10\%$ (also a zero median with a positive range); see Supplement~S4.'
    heading_tex='' if mode=='xeon' else r'\noindent\textbf{'+tex(heading)+r'}\par\smallskip'+'\n'
    fragment=heading_tex+table(rows,config)+r'\par\smallskip{\scriptsize '+tex(note)+range_note+r'}'+supplementary_footnote(campaign)+'\n'
    (output/'rq3-table.tex').write_text(fragment,encoding='utf-8')
    supplement=[r'\noindent\textbf{'+tex(heading)+r'}\par']
    for metric,label,scale in METRICS:
        supplement.extend([r'\clearpage\noindent\textbf{'+tex(label)+r'}\par\smallskip',table(rows,config,metric,scale,show_range=True)])
    supplement.append(r'\par{\scriptsize '+tex(note.replace('median only','median [min, max]'))+r'}')
    (output/'rq3-supplement.tex').write_text('\n'.join(supplement)+'\n',encoding='utf-8')
    normalized=[]
    index={key(row):row for row in rows}
    for model in config['models']:
        for target in config['targets']:
            for method in METHODS:
                source=index.get((model['id'],target['id'],method),pending(model['id'],target['id'],method))
                row=dict(source);row['source_mode']=mode;row['display_complete_five']=complete_five(source)
                row['effective_stage1_status']=effective_status(source)
                # Never export a suspect supplied median as a publication value.
                for metric,_,scale in METRICS:
                    if metric in ('solver_time_ms','peak_rss_bytes'):
                        value=triple(source,metric,scale)
                        for suffix,x in zip(('median','min','max'),value or ('','','')):row['display_'+metric+'_'+suffix]=x
                normalized.append(row)
    write_csv(output/'rq3-cells.csv',normalized)

def censored_pairs(campaign):
    """Single censored JVM attempts versus completed FG elapsed medians.

    The cap covers process startup, frontend, solving and checking. Dividing it
    by solver-only time is a descriptive quotient, NOT a solver speedup bound.
    No Direct-Full median is inferred from its one timed-out trial.
    """
    rows=[]
    for fg in campaign.rows:
        if fg['method_id']!='fg_ducs_otf':continue
        df=campaign.index[fg['model_id'],fg['target_id'],'direct_full']
        elapsed=triple(fg,'elapsed_monotonic_seconds')
        solver=triple(fg,'solver_time_ms',.001)
        if effective_status(df)!='TIMEOUT' or elapsed is None or elapsed[0]<=0:continue
        cap=float(campaign.config['timeout_seconds'])
        rows.append(dict(model_id=fg['model_id'],target_id=fg['target_id'],
            df_status=effective_status(df),original_df_status=df['stage1_status'],
            df_source_campaign=df.get('ad_source_campaign','rq3'),df_cap_seconds=cap,
            fg_status=fg['stage1_status'],fg_elapsed_median_seconds=elapsed[0],
            fg_solver_median_seconds=solver[0] if solver else '',
            censored_attempt_over_fg_elapsed_median_lower_bound=cap/elapsed[0],
            cap_over_fg_solver_median_descriptive_only=cap/solver[0] if solver and solver[0]>0 else '',
            df_solver_ratio_lower_bound='',df_median_inferred=False))
    return rows


def render_evaluation_details(campaign,output):
    """Additional display columns from existing validated measurements only."""
    rows=censored_pairs(campaign)
    write_csv(output/'rq3-censored-comparisons.csv',rows)
    lines=[r'\clearpage\noindent\textbf{Censored JVM attempts and elapsed time}\par',
        r'The 1,200 s cap covers the whole JVM invocation, including startup, frontend and endpoints, solving, checks and output. '
        r'For each Direct-Full timeout with five consistent FG completions, $b=1200/\operatorname{median}(t_{\rm FG,elapsed})$ '
        r'is a lower bound on that censored attempt relative to the FG elapsed median, not a Direct-Full median or a solver-only speedup. '
        r'The last column records the $1200/\operatorname{median}(t_{\rm FG,solver})$ quotient for transparency; '
        r'it has no solver-time lower-bound interpretation because the cap includes non-solver work. Displayed bounds are rounded downward.',
        r'\begin{longtable}{@{}llrrrr@{}}\toprule',
        r'Model & Target & FG elapsed (s) & FG solver (s) & $b$ ($\geq$) & Cap/solver\\\midrule\endhead']
    for row in rows:
        lines.append(tex(MODEL_LABELS[row['model_id']])+' & '+tex(row['target_id'])+' & '+
            ' & '.join(f"{(math.floor(row[field]*100)/100 if field=='censored_attempt_over_fg_elapsed_median_lower_bound' else row[field]):.2f}" for field in ('fg_elapsed_median_seconds','fg_solver_median_seconds',
                'censored_attempt_over_fg_elapsed_median_lower_bound','cap_over_fg_solver_median_descriptive_only'))+r'\\')
    lines.extend([r'\bottomrule\end{longtable}',
        r'Workflow/R2 uses the authorized supplementary attempt; the original operational interruption remains in the provenance table. '
        r'Industry/R1 compares an unresolved attempt with a completed LOSS decision. The table measures time to decide the supplied game, not time to return a controller.',
        r'\clearpage\noindent\textbf{Total JVM elapsed seconds: five-run median [min, max]}\par',
        table(campaign.rows,campaign.config,'elapsed_monotonic_seconds',1,show_range=True),
        r'Incomplete cells retain their original display statuses and receive no timing estimate. '
        r'Elapsed time is measured by the harness monotonic clock; timeout termination overhead is excluded from the conservative 1,200 s numerator above.'])
    (output/'rq3-evaluation-details.tex').write_text('\n'.join(lines)+'\n')
    bounds=[row['censored_attempt_over_fg_elapsed_median_lower_bound'] for row in rows]
    macros={'CensoredPairs':str(len(rows)),
        'CensoredBoundMin':f'{math.floor(min(bounds)*100)/100:.2f}' if bounds else '0',
        'CensoredBoundMax':f'{math.floor(max(bounds)*100)/100:.2f}' if bounds else '0'}
    (output/'rq3-censored-stats.tex').write_text('% Derived elapsed-time bounds, never solver-only bounds.\n'+
        '\n'.join('\\newcommand{\\'+key+'}{'+value+'}' for key,value in macros.items())+'\n')


def scaling_rows(campaign,config):
    index={key(row):row for row in getattr(campaign,'rows',[])};rows=[]
    for model in config['models']:
        for method in METHODS[:4]:
            row=dict(index.get((model['id'],'base',method),pending(model['id'],'base',method)))
            factors=model['factors']
            row.update(K=factors.get('K',''),N=factors.get('N',''),family=model['family'],
                       profile=factors.get('profile',''),seed=factors.get('seed',''))
            if getattr(campaign,'pending_reason',''):row['campaign_pending_reason']=campaign.pending_reason
            rows.append(row)
    return rows

def typesetting_fixture(config):
    """All 135 completed cells; synthetic values exercise range/number widths."""
    result=Campaign(None,'fixture');result.rows=[];result.plan={}
    seconds=(0,.001,.01,.1,1,12.345,123.456,999.123,1199)
    for model in config['models']:
        for target in config['targets']:
            for method in METHODS:
                i=len(result.rows);median=seconds[i%len(seconds)]
                lo=max(0,median-.001);hi=min(1200,median+.001)
                row=dict(model_id=model['id'],target_id=target['id'],method_id=method,stage1_status='SUCCESS',
                    statuses=';'.join(str(rep)+':SUCCESS' for rep in range(1,6)),planned_total_repetitions=5,
                    completed_valid_repetitions=5,timing_summary_eligible=True,invalid=False,inconsistent=False,
                    states_discovered=(i+1)*12345,successor_queries=(i+1)*98765,transition_outcomes=(i+1)*87654,
                    output_policy_states=(i+1)*11,output_policy_transitions=(i+1)*13,
                    solver_time_ms_median=median*1000,solver_time_ms_min=lo*1000,solver_time_ms_max=hi*1000,
                    peak_rss_bytes_median=(i+1)*1234567,peak_rss_bytes_min=(i+1)*1200000,peak_rss_bytes_max=(i+1)*1250000,
                    source_kind='synthetic_typesetting_fixture_not_an_observation')
                result.rows.append(row)
    return result

def render_scaling(independent,travel,mode,output,hub=()):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':7,'axes.titlesize':7.5,
                         'axes.labelsize':7,'xtick.labelsize':6.8,'ytick.labelsize':6.8,'pdf.fonttype':42,'ps.fonttype':42})
    colors=['#0072B2','#D55E00','#009E73','#CC79A7'];markers=['o','s','^','D']
    data=independent+travel+list(hub)
    panels=[('Independent',independent)]+[('Travel N='+str(n),[row for row in travel if row['N']==n]) for n in (1,2,4,6,8,12)]
    mode_label={'placeholder':'XEON DATA PENDING','pilot':'MAC PILOT ONLY — NO XEON RESULTS','xeon':'WINDOWS XEON RESULTS','fixture':'SYNTHETIC TEST FIXTURE'}[mode]
    for metric,label,filename in (('states_discovered','Discovered states (first trial)','rq4-states-vs-k'),
                                  ('solver_time_ms','Solver time (s); median [min, max]','rq4-time-vs-k')):
        # Match the manuscript's ~139 mm text width: no downscaling of 7 pt text.
        fig,axes=plt.subplots(2,4,figsize=(5.48,2.9))
        fig.subplots_adjust(left=.085,right=.99,bottom=.22,top=.87,hspace=.7,wspace=.6)
        for ax,(title,rows) in zip(axes.flat,panels):
            grid=sorted({int(row['K']) for row in rows});has_data=False;has_zero=False
            for mi,method in enumerate(METHODS[:4]):
                lookup={int(row['K']):row for row in rows if row['method_id']==method}
                y=[];valid=[]
                for k in grid:
                    row=lookup[k]
                    value=structural(row,metric) if metric=='states_discovered' else triple(row,metric,.001)
                    if value is not None and (value if metric=='states_discovered' else value[0])>=0:
                        y.append(value if metric=='states_discovered' else value[0]);valid.append((k,value));has_data=True
                        has_zero=has_zero or (value if metric=='states_discovered' else value[0])==0
                    else:y.append(float('nan'))
                ax.plot(grid,y,color=colors[mi],marker=markers[mi],ms=3,lw=.9,
                        markerfacecolor='none',label=LABELS[mi])
                if metric=='solver_time_ms' and valid:
                    ax.errorbar([x[0] for x in valid],[x[1][0] for x in valid],
                        yerr=[[x[1][0]-x[1][1] for x in valid],[x[1][2]-x[1][0] for x in valid]],
                        color=colors[mi],fmt='none',capsize=2,lw=.7)
                for k in grid:
                    row=lookup[k];codes=failure_codes(row)
                    adverse=[code for code in codes if code!='P']
                    if adverse:
                        glyph='+' if 'OOM' in adverse else '×' if 'TO' in adverse else '!'
                        ax.text(k,.035+mi*.063,glyph,transform=ax.get_xaxis_transform(),color=colors[mi],
                                fontsize=7,ha='center',va='bottom',bbox=dict(facecolor='white',alpha=.8,edgecolor='none',pad=.1))
                    elif metric=='solver_time_ms' and row.get('stage1_status') in GOOD and not complete_five(row):
                        ax.text(k,.035+mi*.063,'P',transform=ax.get_xaxis_transform(),color=colors[mi],fontsize=6.5,ha='center')
            ax.set_title(title);ax.set_xlabel('K');ax.grid(True,axis='y',alpha=.18,lw=.5)
            if grid:ax.set_xlim(min(grid)-.7,max(grid)+.7);ax.set_xticks(sorted(set([min(grid),8,max(grid)])))
            if has_data:
                if has_zero:ax.set_yscale('symlog',linthresh=.001 if metric=='solver_time_ms' else 1)
                else:ax.set_yscale('log')
            else:
                ax.set_yticks([]);ax.text(.5,.55,'Data pending' if all(row.get('stage1_status')=='NOT_RUN' for row in rows) else 'No complete\nmeasurements',transform=ax.transAxes,ha='center',fontsize=7,color='.4')
        # The eighth panel retains every seed/profile/method, using a small
        # deterministic horizontal offset only to distinguish overlapping points.
        ax=axes.flat[-1];profiles=('u0','u_local','u_cross');has_data=False
        for pi,profile in enumerate(profiles):
            seeds=sorted({int(row['seed']) for row in hub if row['profile']==profile})
            for mi,method in enumerate(METHODS[:4]):
                lookup={int(row['seed']):row for row in hub
                        if row['profile']==profile and row['method_id']==method}
                for si,seed in enumerate(seeds):
                    row=lookup[seed]
                    x=pi+(mi-1.5)*.16+(si-(len(seeds)-1)/2)*.003
                    value=structural(row,metric) if metric=='states_discovered' else triple(row,metric,.001)
                    if value is not None:
                        y=value if metric=='states_discovered' else value[0]
                        has_data=True
                        ax.plot(x,y,marker=markers[mi],color=colors[mi],ms=1.8,
                                markerfacecolor='none',alpha=.7)
                        if metric=='solver_time_ms':
                            ax.errorbar(x,y,yerr=[[y-value[1]],[value[2]-y]],
                                        fmt='none',color=colors[mi],lw=.35,alpha=.4)
                    else:
                        codes=failure_codes(row)
                        glyph='+' if 'OOM' in codes else '×' if 'TO' in codes else 'P' if 'P' in codes else '!'
                        ax.text(x,.035+mi*.063,glyph,transform=ax.get_xaxis_transform(),
                                color=colors[mi],fontsize=6,ha='center')
        ax.set_title('Hub n=4');ax.set_xlabel('UC profile')
        ax.set_xticks(range(3),['0','local','cross']);ax.set_xlim(-.45,2.45)
        ax.grid(True,axis='y',alpha=.18,lw=.5)
        if has_data:ax.set_yscale('log')
        else:
            ax.set_yticks([]);ax.text(.5,.55,'Data pending',transform=ax.transAxes,ha='center',fontsize=7,color='.4')
        handles=[Line2D([0],[0],color=colors[i],marker=markers[i],lw=1,markersize=4,label=LABELS[i]) for i in range(4)]
        fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.5,.025),
                   frameon=False,fontsize=7,ncol=4,columnspacing=1.2)
        fig.text(.5,.006,'× TO; + OOM; ! invalid / inconsistent / other; P: incomplete. Gaps remain unconnected.',
                 ha='center',fontsize=6)
        fig.suptitle((mode_label+'\n' if mode!='xeon' else '')+label,fontsize=8)
        fig.savefig(output/(filename+'.pdf'),metadata={'Creator':'FG-DUCS result renderer','Author':''})
        fig.savefig(output/(filename+'-full.pdf'),metadata={'Creator':'FG-DUCS result renderer','Author':''})
        fig.savefig(output/(filename+'.png'),dpi=180)
        plt.close(fig)
    render_scaling_combined(independent,travel,mode,output,hub)
    normalized=[]
    for row in data:
        result=dict(row);result['source_mode']=mode;result['display_states']=structural(row,'states_discovered')
        value=triple(row,'solver_time_ms',.001)
        for suffix,x in zip(('median','min','max'),value or ('','','')):result['display_solver_seconds_'+suffix]=x
        normalized.append(result)
    write_csv(output/'rq4-points.csv',normalized)

def status_symbol(row):
    """One display symbol, preserving per-method outcomes in every Travel cell."""
    if complete_five(row):return 'W' if row['stage1_status']=='SUCCESS' else 'L'
    codes=failure_codes(row)
    if 'INC' in codes or 'INV' in codes:return '!'
    if 'OOM' in codes:return 'O'
    if 'TO' in codes:return 'T'
    if codes==['P'] or row.get('stage1_status')=='NOT_RUN':return 'P'
    return '!' if any(code!='P' for code in codes) else 'P'

def travel_status_cells(rows):
    """An ordered 48-cell view; no method is collapsed into a shared status."""
    index={(int(row['N']),int(row['K']),row['method_id']):row for row in rows}
    result=[]
    for n in sorted({identity[0] for identity in index}):
        for k in sorted({identity[1] for identity in index if identity[0]==n}):
            group=[index[(n,k,method)] for method in METHODS[:4]]
            result.append(dict(N=n,K=k,symbols=''.join(status_symbol(row) for row in group),
                **{method+'_status':row.get('statuses','') for method,row in zip(METHODS[:4],group)}))
    return result

def render_scaling_combined(independent,travel,mode,output,hub=()):
    """Two metric rows plus the full Travel status grid at native paper width."""
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.ticker import LogLocator,NullFormatter,FuncFormatter
    colors=['#0072B2','#D55E00','#009E73','#CC79A7'];markers=['o','s','^','D']
    fig=plt.figure(figsize=(139/25.4,3.9))
    layout=fig.add_gridspec(3,5,height_ratios=[1,1,1.04],left=.087,right=.99,
                          top=.92,bottom=.15,hspace=.65,wspace=.67)
    groups=[('Independent',independent)]+[('Travel N='+str(n),[r for r in travel if int(r['N'])==n]) for n in (1,2,4)]+[('Hub n=4',list(hub))]
    for ri,metric in enumerate(('states_discovered','solver_time_ms')):
        for ci,(title,rows) in enumerate(groups):
            ax=fig.add_subplot(layout[ri,ci]);has_data=False;has_zero=False
            if ci==4:
                profiles=('u0','u_local','u_cross')
                for pi,profile in enumerate(profiles):
                    seeds=sorted({int(row['seed']) for row in rows if row['profile']==profile})
                    for mi,method in enumerate(METHODS[:4]):
                        lookup={int(row['seed']):row for row in rows if row['profile']==profile and row['method_id']==method}
                        for si,seed in enumerate(seeds):
                            row=lookup[seed];x=pi+(mi-1.5)*.16+(si-(len(seeds)-1)/2)*.003
                            value=structural(row,metric) if ri==0 else triple(row,metric,.001)
                            if value is not None:
                                y=value if ri==0 else value[0];has_data=True;has_zero=has_zero or y==0
                                ax.plot(x,y,marker=markers[mi],color=colors[mi],ms=1.8,markerfacecolor='none',alpha=.7)
                                if ri:ax.errorbar(x,y,yerr=[[y-value[1]],[value[2]-y]],fmt='none',color=colors[mi],lw=.35,alpha=.4)
                            else:
                                glyph=status_symbol(row);ax.text(x,.04+mi*.10,glyph,transform=ax.get_xaxis_transform(),color=colors[mi],fontsize=7,ha='center')
                ax.set_xticks(range(3),['0','L','X']);ax.set_xlim(-.5,2.5)
                if ri:ax.set_xlabel('UC profile',fontsize=7,labelpad=1)
            else:
                grid=sorted({int(row['K']) for row in rows})
                for mi,method in enumerate(METHODS[:4]):
                    lookup={int(row['K']):row for row in rows if row['method_id']==method};ys=[];valid=[]
                    for k in grid:
                        row=lookup[k];value=structural(row,metric) if ri==0 else triple(row,metric,.001)
                        if value is not None:
                            y=value if ri==0 else value[0];ys.append(y);valid.append((k,value));has_data=True;has_zero=has_zero or y==0
                        else:ys.append(float('nan'))
                    ax.plot(grid,ys,color=colors[mi],marker=markers[mi],ms=2.4,lw=.8,markerfacecolor='none')
                    if ri and valid:
                        ax.errorbar([x[0] for x in valid],[x[1][0] for x in valid],
                            yerr=[[x[1][0]-x[1][1] for x in valid],[x[1][2]-x[1][0] for x in valid]],color=colors[mi],fmt='none',capsize=1.3,lw=.6)
                if grid:ax.set_xticks(sorted(set([min(grid),8,max(grid)])));ax.set_xlim(min(grid)-.7,max(grid)+.7)
                if ri:ax.set_xlabel('K',fontsize=7,labelpad=1)
            if ri==0:ax.set_title(title,fontsize=7,pad=4)
            ax.tick_params(axis='both',labelsize=7,pad=1,length=2)
            ax.grid(True,axis='y',alpha=.18,lw=.5)
            if has_data:
                if has_zero:ax.set_yscale('symlog',linthresh=.001 if ri else 1)
                else:
                    ax.set_yscale('log')
                    lo,hi=ax.get_ylim();exponents=list(range(math.ceil(math.log10(lo)),math.floor(math.log10(hi))+1))
                    if len(exponents)>3:exponents=[exponents[0],exponents[len(exponents)//2],exponents[-1]]
                    if exponents:ax.set_yticks([10.**value for value in exponents])
                    else:
                        ticks=LogLocator(base=10,subs=(1,2,5)).tick_values(lo,hi)
                        ax.set_yticks([value for value in ticks if lo<=value<=hi])
                        ax.yaxis.set_major_formatter(FuncFormatter(lambda value,pos:compact(value)))
                    ax.yaxis.set_minor_formatter(NullFormatter())
            else:
                ax.set_yticks([]);ax.text(.5,.55,'Pending',transform=ax.transAxes,ha='center',fontsize=7,color='.4')
    fig.text(.008,.805,'States',rotation=90,va='center',fontsize=7)
    fig.text(.008,.53,'Time (s)',rotation=90,va='center',fontsize=7)
    cells=travel_status_cells(travel);ks=sorted({r['K'] for r in cells});ns=sorted({r['N'] for r in cells})
    ax=fig.add_subplot(layout[2,:]);ax.set_title('Travel status: all 48 settings, four methods per cell',fontsize=7,pad=4)
    for cell in cells:
        xi=ks.index(cell['K']);yi=ns.index(cell['N'])
        for mi,symbol in enumerate(cell['symbols']):
            ax.text(xi+(mi-1.5)*.17,yi,symbol,ha='center',va='center',fontfamily='DejaVu Sans Mono',fontsize=7,color=colors[mi])
    ax.set_xticks(range(len(ks)),[str(k) for k in ks]);ax.set_yticks(range(len(ns)),[str(n) for n in ns]);ax.set_ylabel('N',fontsize=7,labelpad=4)
    ax.set_xlim(-.5,len(ks)-.5);ax.set_ylim(len(ns)-.5,-.5);ax.tick_params(axis='both',labelsize=7,length=0,pad=2)
    ax.set_xlabel('K',fontsize=7,labelpad=0)
    for x in range(len(ks)+1):ax.axvline(x-.5,color='.82',lw=.45)
    for y in range(len(ns)+1):ax.axhline(y-.5,color='.82',lw=.45)
    handles=[Line2D([0],[0],color=colors[i],marker=markers[i],lw=1,ms=3,label=LABELS[i]) for i in range(4)]
    fig.legend(handles=handles,loc='upper center',bbox_to_anchor=(.54,1),frameon=False,fontsize=7,ncol=4,columnspacing=1,handletextpad=.4)
    fig.text(.5,.052,'Grid order: FG / Eager / Update-first / DF. W/L: five-run completion; T: timeout;',ha='center',fontsize=7)
    fig.text(.5,.023,'O: OOM; !: other adverse status; P: pending. Hub UC: 0 / L (local) / X (cross).',ha='center',fontsize=7)
    if mode!='xeon':fig.text(.5,.975,{'placeholder':'DATA PENDING','pilot':'MAC PILOT ONLY','fixture':'SYNTHETIC FIXTURE'}[mode],ha='center',fontsize=7,color='#9b2226')
    fig.savefig(output/'rq4-scaling-combined.pdf',metadata={'Creator':'FG-DUCS result renderer','Author':''})
    fig.savefig(output/'rq4-scaling-combined.png',dpi=220)
    plt.close(fig)
    write_csv(output/'rq4-travel-status-grid.csv',cells)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=['placeholder','pilot','fixture','xeon'],default='placeholder')
    parser.add_argument('--input-root',type=Path,default=HERE/'raw')
    parser.add_argument('--output',type=Path,default=SUBMISSION/'paper/build/generated')
    args=parser.parse_args();output=args.output.resolve()
    if args.mode=='pilot' and 'pilot' not in output.parts:raise ValueError('Pilot output must be in a dedicated pilot directory')
    if args.mode=='fixture' and 'fixture' not in output.parts:raise ValueError('Synthetic output must be in a dedicated fixture directory')
    output.mkdir(parents=True,exist_ok=True)
    load=lambda name:json.loads((HERE/'configs'/(name+'.json')).read_text())
    if args.mode=='placeholder':rq3=ind=travel=hub=Campaign(None,args.mode)
    elif args.mode=='fixture':rq3=typesetting_fixture(load('rq3'));ind=travel=hub=Campaign(None,args.mode)
    elif args.mode=='pilot':
        rq3=Campaign(args.input_root/'pilot',args.mode);ind=travel=hub=Campaign(None,args.mode)
        if len(rq3.initial)!=15:raise ValueError('Expected the fixed 15-job pilot')
    else:
        rq3=Campaign(args.input_root/'rq3',args.mode,load('rq3'))
        if not rq3.rows:raise ValueError('No RQ3 Xeon summary found; use placeholder mode before data return')
        integrate_supplementary(rq3,args.input_root)
        ind=optional_xeon(args.input_root/'rq4_independent',load('rq4_independent'))
        travel=optional_xeon(args.input_root/'rq4_travel',load('rq4_travel'))
        hub=optional_xeon(args.input_root/'rq4_hub',load('rq4_hub'))
    render_rq3(rq3,args.mode,output,load('rq3'))
    if args.mode=='xeon':render_evaluation_details(rq3,output)
    render_supplementary_pending(rq3,output,args.input_root)
    render_scaling(scaling_rows(ind,load('rq4_independent')),scaling_rows(travel,load('rq4_travel')),
                   args.mode,output,scaling_rows(hub,load('rq4_hub')))
    print('Generated '+args.mode+' figures/tables in '+str(output))

if __name__=='__main__':main()
