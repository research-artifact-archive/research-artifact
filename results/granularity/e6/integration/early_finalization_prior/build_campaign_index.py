#!/usr/bin/env python3
"""Extend the checked core index with every preregistered pair, including failures.

This reads existing raw/summary outputs. It never runs a solver or fills a
measurement from an expected decision, formula, or independent design check.
"""
from pathlib import Path
import argparse, csv, hashlib, json, subprocess, sys
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo
from index_additions import augment

E6=Path(__file__).resolve().parents[1]
OUT=E6/'integration'
JAR='ff1e6b176f004ea85f1e99690a90388a6a4d24f44cd8d8e636fcd9337dcf67d5'

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path): return json.loads(path.read_text())
def csv_rows(path): return list(csv.DictReader(path.open()))
def atomic_json(path,value):
    tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(value,indent=2)+'\n');tmp.replace(path)
def atomic_csv(path,rows):
    fields=list(dict.fromkeys(k for row in rows for k in row))
    tmp=path.with_suffix(path.suffix+'.tmp')
    with tmp.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    tmp.replace(path)
def category(fine,merged):
    return {('WIN','LOSS'):'witness',('LOSS','LOSS'):'both_loss',('WIN','WIN'):'both_win'}.get((fine,merged),'unexpected' if fine in ('WIN','LOSS') and merged in ('WIN','LOSS') else 'incomplete')

def standard_rows(family,sources):
    """Validate completed CSV cells against immutable artifacts, retain other status."""
    base=E6/family;config=read(base/'config.json');manifest=read(base/'build/frozen_manifest.json')
    path=base/'summary.csv';rows={r['job_id']:r for r in csv_rows(path)} if path.exists() else {}
    if path.exists():sources.append(dict(path=str(path.relative_to(E6)),sha256=sha(path)))
    result={}
    for job in manifest['schedule']:
        row=rows.get(job['id'],dict(job_id=job['id'],decision='NOT_RUN',status='NOT_RUN'))
        assert not row.get('validation_errors'),(family,job['id'],row.get('validation_errors'))
        d=row['decision'];data=None
        if d in ('WIN','LOSS'):
            assert row['jar_sha256']==JAR
            inp=base/job['input'];assert sha(inp)==row['input_sha256']==manifest['files'][str(inp.relative_to(E6))]
            raw=base/row['result_file'];data=read(raw)
            assert data['certificate_sha256']==sha(raw.parent/'certificate.json')
            for key in ('decision','states_discovered','successor_queries'):
                assert str(data[key])==row[key],(family,job['id'],key)
            assert data['certificate_checker']==data['endpoint_checker']=='PASS'
            assert d!='WIN' or data['link_checker']=='PASS'
        else:
            for key in ('states_discovered','worst_completion_rank','losing_region_states','solver_seconds'):
                assert not row.get(key),(family,job['id'],'uncompleted metric',key)
        result[job['id']]=(row,data)
    return result,config

def pair_record(family,params,location,population,mechanism,contribution,anchor,rows,ids,reason):
    (fine,fr),(merged,mr),(df,dr),(generated,gr)=[rows[i] for i in ids]
    decisions=(fine['decision'],merged['decision']);merge_check='NOT_COMPLETE'
    if mr and gr:
        for key in ('decision','states_discovered','successor_queries','worst_completion_rank','losing_region_states'):
            assert merged.get(key)==generated.get(key),(family,params,key)
        eq=mr.get('game_equivalence') or gr.get('game_equivalence')
        assert eq and eq['status']=='PASS',(family,params,'Post equality')
        merge_check='PASS'
    if fr and dr:assert fine['decision']==df['decision'],(family,params,'Lazy/Full')
    base=E6/location;preflight=base/'validation/preflight.json'
    endpoint=read(preflight)['status'] if preflight.exists() else 'NOT_RUN'
    rec=dict(family=family,params=params,mechanism=mechanism,contribution=contribution,anchor=anchor,
             fine_decision=decisions[0],merged_decision=decisions[1],**{'class':category(*decisions)},
             cert_checks=f'E1 fine={"PASS" if fr else fine["decision"]}; merged={"PASS" if mr else merged["decision"]}; WIN Link checked with each completed WIN; endpoint preflight={endpoint}; generated/E1 Post={merge_check}',
             location=location,comparison='transfers',population=population,
             fine_job=ids[0],merged_job=ids[1],direct_full_job=ids[2],generated_job=ids[3],
             fine_status=fine['status'],merged_status=merged['status'],direct_full_status=df['status'],generated_status=generated['status'],
             fine_input_sha256=fine.get('input_sha256',''),jar_sha256=JAR,
             loss_reason=reason if 'LOSS' in decisions else '',preregistered_mechanism=reason)
    for prefix,row in [('fine',fine),('merged',merged),('direct_full',df)]:
        for dst,src in [('states','states_discovered'),('rank','worst_completion_rank'),('loss_certificate_states','losing_region_states'),('queries','successor_queries'),('solver_seconds','solver_seconds')]:
            rec[prefix+'_'+dst]=row.get(src,'')
    return rec

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--final',action='store_true');args=ap.parse_args()
    if args.final:
        assert datetime.now(ZoneInfo('Asia/Tokyo'))>=datetime(2026,9,30,10,0,tzinfo=ZoneInfo('Asia/Tokyo')),'Final report is reserved for the requested real deadline'
        assert (E6/'pc2_rolling/extended_7200/build/final_tables_ready.json').exists(),'Authorized PC2 extension and final native tables must be resolved first'
    subprocess.run([sys.executable,'-B',str(OUT/'build_handoff.py')],check=True,stdout=subprocess.DEVNULL)
    core=csv_rows(OUT/'core_results_index.csv');sources=read(OUT/'core_status.json')['sources'];records=[]
    for row in core:
        row.update(population='core',fine_status=row['fine_decision'],merged_status=row['merged_decision'],direct_full_status=row['fine_decision'])
        records.append(row)
    specs=[('threads/v1','Threads','operational_control','M1','UC_progress_control','https://doi.org/10.1145/2629460'),
           ('rolling_scale/v1','Rolling-scale','scale_extension','M2','L3','https://kubernetes.io/docs/concepts/workloads/controllers/deployment/'),
           ('canary_controls/v1','Canary-controls','assumption_control','M3','L2_assumption_control','https://www.crowdstrike.com/en-us/blog/falcon-content-update-preliminary-post-incident-report/')]
    for location,family,population,mechanism,contribution,anchor in specs:
        rows,config=standard_rows(location,sources)
        for job in config['jobs']:
            if not job['id'].endswith('_fine_lazy'):continue
            prefix=job['id'][:-len('_fine_lazy')];p=job['parameters']
            if family=='Threads':
                ids=[prefix+'_fine_lazy',prefix+'_e1merged_lazy',prefix+'_fine_df',prefix+'_generated_all_lazy']
                params=f'n={p["n"]};B={p["B"]};regime={p["regime"]}'
                reason='Saturated offers enable an ordinary UC action in every physical state, preventing every update and every UC-quiescent goal.' if p['regime']=='saturated_offers' else 'Stopping dispatch lets busy workers finish while the bounded queue fills and preserves queued work, permitting simultaneous idle update; no granularity witness is expected.'
            else:
                ids=[prefix+'_fine_lazy',prefix+'_merged_lazy',prefix+'_fine_df',prefix+'_all_lazy']
                params=f'n={p["n"]};m={p["m"]}'
                if family=='Canary-controls':
                    params+=';control='+p['control']
                    reason='A possible broken outcome has no recovery path to the all-healthy endpoint.' if p['control']=='no_recovery' else 'Removing the broken transfer outcome permits both fine and simultaneous completion.'
                else:reason='The product transfer puts every replica in booting, violating the positive ready floor.'
            records.append(pair_record(family,params,location,population,mechanism,contribution,anchor,rows,ids,reason))
    pc=E6/'pc2_rolling/v2/tables/results.csv';pcrows={r['job_id']:r for r in csv_rows(pc)} if pc.exists() else {}
    pcsummary=E6/'pc2_rolling/v2/validation/raw_table_audit.json'
    if pc.exists():
        assert read(pcsummary)['status']=='PASS';sources.append(dict(path=str(pc.relative_to(E6)),sha256=sha(pc)))
    fine=pcrows.get('lazy_none',{'status':'NOT_RUN'});merged=pcrows.get('lazy_transfers',{'status':'NOT_RUN'});df=pcrows.get('direct_full_none',{'status':'NOT_RUN'})
    rec=dict(family='PC2-Rolling',params='arms=2;ready_floor=1',mechanism='M2',contribution='application_plant_attempt',anchor='https://www.universal-robots.com/manuals/EN/HTML/SW5_19/Content/prod-rck/rck-resetting-the-calibration.htm',fine_decision=fine['status'],merged_decision=merged['status'],**{'class':category(fine['status'],merged['status'])},cert_checks='See pc2_rolling/v2/validation and separate validation_export; timeout has no checked decision or certificate.',location='pc2_rolling/v2',comparison='transfers',population='application_plant_attempt',fine_job='lazy_none',merged_job='lazy_transfers',direct_full_job='direct_full_none',fine_status=fine['status'],merged_status=merged['status'],direct_full_status=df['status'],fine_input_sha256=fine.get('input_sha256',''),jar_sha256=JAR,loss_reason='',preregistered_mechanism='Joint replacement initializes both arms as calibrating, violating the availability monitor; this argument is not a measured LOSS when the cell times out.')
    for prefix,row in [('fine',fine),('merged',merged),('direct_full',df)]:
        for dst,src in [('states','states_discovered'),('rank','worst_completion_rank'),('loss_certificate_states','losing_region_states'),('queries','successor_queries')]:rec[prefix+'_'+dst]=row.get(src,'')
        # PC2 fixed CLI combines solve/check time: deliberately not copied into solver_seconds.
        rec[prefix+'_solver_seconds']='';rec[prefix+'_solve_and_internal_check_seconds']=row.get('solve_and_internal_check_seconds','')
    records.append(rec)
    augment(records,sources)
    atomic_csv(E6/'results_index.csv',records)
    populations={p:{key:sum(r['class']==key for r in records if r['population']==p) for key in ('witness','both_loss','both_win','incomplete','unexpected')} for p in dict.fromkeys(r['population'] for r in records)}
    main=[r for r in records if r['population'] in ('core','operational_control','application_plant_attempt')]
    summary=dict(status='FINAL_WITH_LIMITATIONS' if args.final else 'INTERIM',generated_at=datetime.now(ZoneInfo('Asia/Tokyo')).isoformat(),indexed_pairs=len(records),main_pair_counts={key:sum(r['class']==key for r in main) for key in ('witness','both_loss','both_win','incomplete','unexpected')},by_population=populations,sources=sources,counting='Core plus Threads controls and PC2 attempt form main comparisons. Scale, Canary assumption controls, and nine E4 Cell_n reference comparisons are separate populations. A terminal PC2 extended-budget result is used once with explicit host/budget/campaign; original 1200 s statuses are retained. Incomplete cells never enter a measured decision category. E4 references add no E6 trials; original E1/E5 and retained earlier versions are not counted.')
    atomic_json(OUT/'status.json',summary)
    trial_counts=[]
    for family in ('rolling/v1','canary/v1','policy/v2','db_rolling/v2','rolling_audit/v1','threads/v1','rolling_scale/v1','canary_controls/v1','pc2_rolling/v2','pc2_rolling/extended_7200'):
        path=E6/family/('tables/results.csv' if family.startswith('pc2') else 'summary.csv')
        cells=csv_rows(path);counts=Counter(c.get('decision',c.get('status')) for c in cells)
        statuses=('WIN','LOSS','TO','OOM','ERROR','INVALID_CERTIFICATE','INVALID_INPUT','NOT_RUN','NOT_STARTED','RUNNING')
        assert set(counts)<=set(statuses),(family,counts)
        if args.final: assert not (counts['RUNNING'] or counts['NOT_STARTED']),(family,counts)
        trial_counts.append(dict(family=family,trials=len(cells),**{k:counts[k] for k in statuses},summary_sha256=sha(path)))
    atomic_csv(OUT/'all_registered_run_counts.csv',trial_counts)
    summary['registered_trial_counts']={k:sum(r[k] for r in trial_counts) for k in ('trials',*statuses)}
    summary['original_nine_series_trials']=sum(r['trials'] for r in trial_counts if r['family']!='pc2_rolling/extended_7200')
    summary['pc2_extension_trials']=2
    atomic_json(OUT/'status.json',summary)
    def tex(value):return str(value).replace('&',r'\&').replace('_',r'\_').replace('%',r'\%')
    selections=[('Rolling','n=2;m=1','Rolling','$n=2,m=1$'),
                ('Rolling','n=6;m=1','Rolling','$n=6,m=1$'),
                ('Canary','n=2;m=1','Canary','$n=2,m=1$'),
                ('Canary','n=6;m=1','Canary','$n=6,m=1$'),
                ('Policy','rule_pairs=2','Policy','2 rule pairs'),
                ('DB-Rolling','n=3;m=2','DB-Rolling','$n=3,m=2$'),
                ('DB-Rolling','n=3;m=3','DB-Rolling','$n=3,m=3$'),
                ('Rolling+Audit','n=2;m=1;audit_pairs=1','Rolling+Audit','$n=2,m=1$'),
                ('Threads','n=6;B=2;regime=backpressure','Threads: backpressure','$n=6,B=2$'),
                ('Threads','n=6;B=2;regime=saturated_offers','Threads: saturated','$n=6,B=2$'),
                ('PC2-Rolling','arms=2;ready_floor=1','PC2-Rolling','2 arms')]
    lines=[r'% Measured cells only; unfinished statuses are displayed, never replaced by predictions.',r'\begin{tabular}{llrrrrl}',r'\toprule',r'Family & Parameters & Lazy & Full & Merged & Rank & Fine / merged \\',r'\midrule']
    for family,params,label,display in selections:
        row=next(r for r in records if r['family']==family and r['params']==params)
        cells=[tex(label),display]
        for prefix in ('fine','direct_full','merged'):
            cells.append(row.get(prefix+'_states','') or tex(row.get(prefix+'_status','NR')))
        cells.extend([row.get('fine_rank','') or '--',tex(row['fine_decision'])+' / '+tex(row['merged_decision'])])
        lines.append(' & '.join(cells)+r' \\')
    lines += [r'\bottomrule',r'\end{tabular}',r'% Lazy, Full, and Merged columns report discovered states. Rank is the returned fine Lazy bound.',r'% Policy uses boundaries merge; other rows use transfers. Timeouts retain their explicit source budget in results_index.csv.',r'% PC2 original/extended/host rows remain separate in pc2_rolling/extended_7200/tables/host_budget_comparison.csv. Scale and assumption controls have separate tables.']
    (OUT/'main_comparison_extended.tex').write_text('\n'.join(lines)+'\n')
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
