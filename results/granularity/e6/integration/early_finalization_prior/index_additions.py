"""Read-only evidence joins for the requested compact table and larger PC2 budget.

Historical trials are never overwritten, and an unfinished extension is never
promoted to a measured decision. Cell_n is an E4 reference population.
"""
from pathlib import Path
import csv, hashlib, json

E6 = Path(__file__).resolve().parents[1]
JAR = 'ff1e6b176f004ea85f1e99690a90388a6a4d24f44cd8d8e636fcd9337dcf67d5'

def read(path): return json.loads(path.read_text())
def rows(path): return list(csv.DictReader(path.open()))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def source(path): return dict(path=str(path.relative_to(E6)) if path.is_relative_to(E6) else '../'+str(path.relative_to(E6.parent)), sha256=sha(path))
def category(a,b):
    return {('WIN','LOSS'):'witness',('LOSS','LOSS'):'both_loss',('WIN','WIN'):'both_win'}.get((a,b),'unexpected' if a in ('WIN','LOSS') and b in ('WIN','LOSS') else 'incomplete')

def add_cell_reference(records,sources):
    base=E6.parent/'e4_2_corrected'
    audit=read(base/'validation/final_series_audit.json')
    assert audit['status']=='PASS' and not audit['comparison_discrepancies']
    path=base/'summary_wide.csv'; sources.append(source(path))
    for r in rows(path):
        n=int(r['n']); inp=base/f'inputs/cell_n{n:02}.json'
        rec=dict(family='Cell_n',params=f'n={n}',mechanism='M1',contribution='L1;L3',anchor='E4 constructed Cell ring; no operational reproduction claim',location='../e4_2_corrected',population='reference_e4',comparison='transfers',fine_input_sha256=sha(inp),jar_sha256=JAR,cert_checks='E4 E1 certificate/Link and endpoint/frozen-result audit PASS; E6 v3 JSON checker not applicable to the older adapter schema.',loss_reason='One conserved product prevents all stations from being empty simultaneously, so the product transfer is never enabled.',fine_job=f'n{n:02}_none_lazy',merged_job=f'n{n:02}_transfers_lazy',direct_full_job=f'n{n:02}_none_direct_full')
        for prefix,key in [('fine','none_lazy'),('merged','transfers_lazy'),('direct_full','none_direct_full')]:
            rec[prefix+'_decision']=rec[prefix+'_status']=r[key+'_status']
            for target,suffix in [('states','states'),('queries','queries'),('rank','rank'),('loss_certificate_states','losing_region')]:
                rec[prefix+'_'+target]=r[key+'_'+suffix]
            rec[prefix+'_solver_seconds']=''
            raw=read(base/f'raw/series/{rec[prefix+"_job"]}/result.json')
            assert raw['decision']==rec[prefix+'_decision']
            assert str(raw['states_discovered'])==rec[prefix+'_states']
            assert raw['jar_sha256']==JAR
        rec['class']=category(rec['fine_decision'],rec['merged_decision'])
        rec['e1_merge_equivalence']='NOT_GENERATED_SEPARATELY'
        rec['e1_merge_scope']='E1 transfers is the measured coarse contract; boundaries equals none and both equals transfers in E4 singleton-boundary checks.'
        rec['independent_v3']='NOT_APPLICABLE_E4_SCHEMA'
        rec['independent_validation']='PASS'
        rec['independent_validation_scope']='E4 endpoint/measurement/freeze audit; not an E6 v3 certificate-graph audit.'
        rec['independent_validation_report']='../e4_2_corrected/validation/final_series_audit.json'
        records.append(rec)

def attach_pc2_extension(records,sources):
    rec=next(r for r in records if r['family']=='PC2-Rolling')
    for prefix in ('fine','merged','direct_full'):
        rec[prefix+'_host']='mac';rec[prefix+'_timeout_seconds']='1200'
        rec[prefix+'_campaign']='v2'
        rec[prefix+'_original_1200_status']=rec[prefix+'_status']
    path=E6/'pc2_rolling/extended_7200/tables/results.csv'
    if not path.exists(): return
    sources.append(source(path)); cells={r['job_id']:r for r in rows(path)}
    for prefix,key in [('merged','lazy_transfers'),('direct_full','direct_full_none')]:
        cell=cells[key]
        rec[prefix+'_extended_7200_status']=cell['status']
        # A running extension is tracked separately; the last measured 1200 s
        # result remains the comparison status until the new trial terminates.
        if cell['status'] not in ('WIN','LOSS','TO','OOM','ERROR','INVALID_CERTIFICATE','INVALID_INPUT'): continue
        assert cell['jar_sha256']==JAR and cell['input_sha256']==rec['fine_input_sha256']
        rec[prefix+'_host']=cell['host'];rec[prefix+'_timeout_seconds']=cell['timeout_seconds']
        rec[prefix+'_campaign']='extended_7200';rec[prefix+'_raw_directory']='pc2_rolling/'+cell['raw_directory']
        rec[prefix+'_status']=cell['status']
        if prefix=='merged': rec['merged_decision']=cell['status']
        for target,key2 in [('states','states_discovered'),('rank','worst_completion_rank'),('loss_certificate_states','losing_region_states'),('queries','successor_queries'),('solve_and_internal_check_seconds','solve_and_internal_check_seconds')]:
            rec[prefix+'_'+target]=cell.get(key2,'')
            if cell['status'] not in ('WIN','LOSS'): assert not rec[prefix+'_'+target]
        rec[prefix+'_solver_seconds']=''
        if cell['status'] in ('WIN','LOSS'):
            assert cell['validation']=='PASS'
            assert cell['native_certificate_checker']=='passed'
            assert cell['status']!='WIN' or cell['native_link_checker']=='passed'
    rec['class']=category(rec['fine_decision'],rec['merged_decision'])
    if rec['direct_full_status'] in ('WIN','LOSS'):
        assert rec['direct_full_status']==rec['fine_decision'],'PC2 fine Lazy/Full decision disagreement requires investigation'
    rec['contribution']='L1;application_plant' if rec['class']=='witness' else 'application_plant_attempt'
    rec['cert_checks']='E1 fine certificate/Link PASS; FSP independent graph/endpoint audit PASS. Extended native checks are reported per terminal cell; timeout has no decision certificate.'
    if rec['merged_decision']=='LOSS':
        rec['loss_reason']='Simultaneous transfer puts both arms in calibration, violating the operational-arm floor; see extended losing-certificate diagnosis.'

def attach_validation(records,sources):
    paths=['independent/attempt03_strict_original.json','independent/threads_strict_v3.json','independent/canary_controls_strict_v3.json']
    checked={}
    for rel in paths:
        p=E6/rel; report=read(p); assert report['status']=='PASS'
        sources.append(source(p))
        for item in report['audits']:
            assert item['status']=='PASS'
            checked[(item['family'],item['job'])]=rel
    scale='common/independent_checks/rolling_scale_final_review.json'
    sc=read(E6/scale);assert sc['status']=='PASS'
    scjobs={r['job'] for r in sc['checks']};sources.append(source(E6/scale))
    for rec in records:
        family=rec['family']
        if family=='Cell_n': continue
        if family=='PC2-Rolling':
            rec.update(e1_merge_equivalence='NOT_GENERATED_SEPARATELY',e1_merge_scope='Coarse FSP contract uses E1 transfers directly; no independent generated full-Post equality claim.',independent_v3='NOT_APPLICABLE_FSP',independent_validation='PASS_FINE_ONLY',independent_validation_scope='Independent endpoints, finite certificate graph/rank and physical floor for fine WIN; no independent FSP Post reimplementation.',independent_validation_report='pc2_rolling/v2/validation/final_artifact_audit.json')
            continue
        ids=[rec['fine_job'],rec['merged_job'],rec['direct_full_job']]
        if family=='Rolling-scale':
            assert all(job in scjobs for job in ids)
            rec.update(independent_v3='PASS_CERTIFICATE_SCOPE',independent_validation='PASS',independent_validation_scope='v3 Post interpreter on every saved certificate plus independent endpoint and Full formula checks; no full-game Python enumeration.',independent_validation_report=scale)
        else:
            reports=[checked[(rec['location'],job)] for job in ids]
            rec.update(independent_v3='PASS',independent_validation='PASS',independent_validation_scope='Independent complete Post game, strong attractor and strict certificate/rank/initialization checks.',independent_validation_report=';'.join(dict.fromkeys(reports)))
        assert 'generated/E1 Post=PASS' in rec['cert_checks'] or 'generated/E1 Post PASS' in rec['cert_checks']
        rec['e1_merge_equivalence']='PASS'
        rec['e1_merge_scope']=rec['comparison']+'; generated coarse and E1 merge agree in reachable Post and measured counters.'

def attach_threshold(records,sources):
    path=E6/'rolling/v1/tables/threshold.csv'; cells=rows(path);sources.append(source(path))
    for rec in records:
        if rec['family']!='Rolling': continue
        p=dict(a.split('=') for a in rec['params'].split(';'));n,m=int(p['n']),int(p['m'])
        selected=[r for r in cells if (int(r['n']),int(r['m']))==(n,m)]
        assert sorted(int(r['k']) for r in selected)==list(range(1,n+1))
        assert all(r['observed']==('WIN' if int(r['k'])<=n-m else 'LOSS') for r in selected)
        rec['threshold_max_winning_k']=str(n-m);rec['threshold_tested_k_count']=str(len(selected))
        rec['threshold_check']='PASS';rec['threshold_source']='rolling/v1/tables/threshold.csv'

def augment(records,sources):
    add_cell_reference(records,sources)
    attach_pc2_extension(records,sources)
    attach_validation(records,sources)
    attach_threshold(records,sources)
