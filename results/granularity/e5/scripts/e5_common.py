"""E5-only readers: old campaign helpers are imported read-only."""
from __future__ import annotations
import sys
sys.dont_write_bytecode = True
import csv, io, json, re
from pathlib import Path
HERE=Path(__file__).resolve().parent
E5=HERE.parent
SUBMISSION=E5.parents[2]
ROOT=SUBMISSION.parent
sys.path.insert(0,str(SUBMISSION/'experiments/ablation_20260928/scripts'))
from ablation_common import read_json,write_json,sha256,csv_write,extract_output,read_trial as old_trial
from run_ablation import run_trial,execution_lock,remaining,utc_now
CONFIG=E5/'configs/e5_mac.json'
RAW=E5/'raw'
ATTEMPT='single_1200s'
LABELS=dict(gsm='GSM',industry='Industry',metasocket='MetaSocket',powerplant='PowerPlant',productioncell_arms1='PC1',productioncell_arms2='PC2',railcab='Railcab',surveillance='Surveillance',workflow='Workflow')
EXTRA={'transfer_domain':'revised_transfer_domain','components_json':'revised_transfer_domain_components','original_pairs':'revised_transfer_domain_original_pairs','retained_pairs':'revised_transfer_domain_retained_pairs','original_domain_states':'revised_transfer_domain_original_domain_states','retained_domain_states':'revised_transfer_domain_retained_domain_states','losing_certificate_summary':'revised_losing_certificate_summary'}
COUNT_FIELDS=('original_pairs','retained_pairs','original_domain_states','retained_domain_states','original_physical_pairs','retained_physical_pairs','original_physical_domain_states','retained_physical_domain_states')
EXTRA.update({k:'revised_transfer_domain_'+k for k in COUNT_FIELDS})
EXTRA['loss_diagnostic_time_ms']='revised_losing_certificate_diagnostic_time'
VARIANTS={'otf':'revised_otf_ducs_direct_v1','direct_full':'revised_direct_full_v1'}

def jobs(config):
    # Both Lazy methods for each pair first; every DF method only after all 36 Lazy.
    for methods in (config['methods'][:2],config['methods'][2:]):
        for model in config['models']:
            for target in config['targets']:
                for method in methods:
                    yield dict(job_id=f"{model['id']}__{target['id']}__rep01__{method['id']}",model_id=model['id'],model_path=model['path'],target_id=target['id'],target_name='UPDATE_CONTROLLER_OTF_FG'+target['suffix'],method_id=method['id'],merge=method['merge'],solver=method['solver'],repetition=1,jvm_properties=method['jvm_properties'])

def metrics(path):
    if not path.is_file(): return {}
    lines=path.read_text(errors='replace').splitlines()
    marker='================ EVALUATION DATA CSV ================'
    if sum(x.strip()==marker for x in lines)!=1:return {}
    block=[]
    for line in lines[next(i for i,x in enumerate(lines) if x.strip()==marker)+1:]:
        if line.strip()=='================ EVALUATION SUMMARY ================':break
        if line.strip() and not re.fullmatch(r'=+',line.strip()):block.append(line)
    return {r['metric_key']:r['value'] for r in csv.DictReader(io.StringIO('\n'.join(block))) if r.get('metric_key')}

def trial(job):
    path=RAW/ATTEMPT/'runs'/job['job_id']/'meta.json'
    data=extract_output(path.parent/'output.txt')
    data.update({x:'' for x in EXTRA})
    data.update(meta_path=str(path.relative_to(ROOT)),status='NOT_RUN',reason='Not started.')
    if not path.is_file():
        data.update(decision='NOT_RUN',validation_errors='')
        if (RAW/'deadline_reached.json').exists():data.update(status='NOT_RUN_DEADLINE',decision='NOT_RUN_DEADLINE',reason='Not started before the predeclared 15:39 JST cutoff.')
        return data
    meta=read_json(path);status=meta.get('status','INCOMPLETE')
    if not meta.get('completed'):status='RUNNING'
    values=metrics(path.parent/'output.txt')
    for key,metric in EXTRA.items():data[key]=values.get(metric,'')
    data.update(status=status,jar_sha256=meta.get('jar_sha256',''),source_commit=meta.get('source_commit',''),input_sha256=meta.get('input_sha256',''),timeout_seconds=meta.get('timeout_seconds',''),heap=meta.get('java_heap',''),elapsed_seconds=meta.get('elapsed_monotonic_seconds',''),started_utc=meta.get('started_utc',''),finished_utc=meta.get('finished_utc',''))
    errors=[data['validation_errors']] if data['validation_errors'] and status in ('SUCCESS','UNREALIZABLE') else []
    if meta.get('job')!=job:errors.append('metadata job differs from fixed schedule')
    if meta.get('timeout_seconds')!=1200 or meta.get('java_heap')!='32g':errors.append('budget/heap mismatch')
    manifest=read_json(RAW/'series_manifest.json')
    if meta.get('jar_sha256')!=manifest['jar']['jar_sha256'] or meta.get('source_commit')!=manifest['jar']['source_commit']:errors.append('source/JAR metadata mismatch')
    expected_input=next(x['copy_sha256'] for x in manifest['inputs'] if x['model_id']==job['model_id'])
    if meta.get('input_sha256')!=expected_input:errors.append('input hash mismatch')
    command=meta.get('command',[])
    if '--target' not in command or command[command.index('--target')+1]!=job['target_name']:errors.append('command target mismatch')
    if '--lts' not in command or command[command.index('--lts')+1]!=job['model_path']:errors.append('command input mismatch')
    if meta.get('completed'):
        for stem,digest in meta.get('artifact_digests',{}).items():
            file=path.parent/(stem+'.txt')
            if not file.is_file() or sha256(file)!=digest['sha256']:errors.append('artifact digest mismatch: '+stem)
    if status in ('SUCCESS','UNREALIZABLE'):
        # Keep raw numeric data even when validation finds a defect; classification excludes INVALID.
        expected='WIN' if status=='SUCCESS' else 'LOSS'
        if data['decision']!=expected:errors.append('exit/decision mismatch')
        if data['internal_certificate_check']!='passed':errors.append('internal checker not passed')
        if expected=='WIN' and data['link_checker']!='passed':errors.append('link checker not passed')
        if data['solver_variant']!=VARIANTS[job['solver']]:errors.append('solver variant mismatch')
        if data['contract_merge']!=job['merge']:errors.append('merge mismatch')
        if data['transfer_domain']!='initial':errors.append('transfer domain mismatch')
        for prop,value in job['jvm_properties'].items():
            if '-D'+prop+'='+value not in meta['command']:errors.append('command property mismatch: '+prop)
        try:
            components=json.loads(data['components_json'])
            for key in COUNT_FIELDS:
                if sum(int(c[key]) for c in components)!=int(data[key]):errors.append('component total mismatch: '+key)
            if any(int(c['retained_pairs'])>int(c['original_pairs']) or int(c['retained_physical_domain_states'])>1 for c in components):errors.append('invalid restriction counts')
        except (ValueError,KeyError,TypeError):errors.append('component metrics malformed')
        if expected=='LOSS':
            try:
                evidence=json.loads(data['losing_certificate_summary'])
                if evidence['region_states']!=int(data['losing_region_states']):errors.append('LOSS region metric/summary mismatch')
                if evidence['safe_region_states']+evidence['unsafe_region_states']!=evidence['region_states']:errors.append('LOSS safe/unsafe count mismatch')
                if not 0<evidence['losing_initial_states']<=evidence['initial_states']:errors.append('LOSS initial count invalid')
                if len(evidence['initial_examples'])>evidence['initial_examples_limit'] or evidence['initial_examples_limit']!=3:errors.append('LOSS sample limit mismatch')
                for example in evidence['initial_examples']:
                    for bucket in example.get('enabled_action_buckets',[]):
                        if not 0<=bucket['outcomes_in_certificate_region']<=bucket['outcomes']:errors.append('LOSS outcome count invalid')
            except (ValueError,TypeError,KeyError):errors.append('missing or malformed losing certificate summary')
        data['reason']=('Checked winning policy; reported rank is its finite completion bound.' if expected=='WIN' else 'Checked losing certificate over discovered states: '+data['losing_certificate_summary'])
        if errors:data['decision']='INVALID'
    else:
        data['decision']='TO' if status=='TIMEOUT' else status
        for key in ('states_discovered','buckets','successor_queries','solver_seconds','solver_time_ms','worst_completion_rank','losing_region_states'):data[key]=''
        data['reason']='The single 1,200 s trial timed out; no completed-game measurements are substituted.' if status=='TIMEOUT' else 'Trial status: '+status+'.'
        err=path.parent/'stderr.txt'
        if status not in ('TIMEOUT','RUNNING') and err.exists():data['reason']+=' '+err.read_text(errors='replace')[-1500:].replace('\n',' ')
    data['validation_errors']='; '.join(errors)
    return data

def baseline_rows():
    result={}
    with (SUBMISSION/'experiments/ablation_20260928/tables/e1_comparison.csv').open() as f:
        for row in csv.DictReader(f):
            key=(row['model_id'],row['target_id'])
            if key in result:continue
            path=SUBMISSION/row['original_meta'];old=old_trial(path)
            result[key]=dict(original_decision=old['decision'],original_states=old['states_discovered'],original_queries=old['successor_queries'],original_rank=old['worst_completion_rank'],original_losing_region=old['losing_region_states'],original_meta=str(path.relative_to(ROOT)),original_jar_sha256=old['jar_sha256'],original_input_sha256=old['input_sha256'],original_validation_errors=old['validation_errors'])
    return result

def tex(value):
    return str(value).replace('_',r'\_').replace('&',r'\&').replace('%',r'\%')
