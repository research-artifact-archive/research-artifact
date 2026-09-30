#!/usr/bin/env python3
"""Fresh derived tables; retain the separate original and extended budgets."""
import csv, hashlib, json
from pathlib import Path
from datetime import datetime, timezone, timedelta

HERE=Path(__file__).resolve().parent
PC2=HERE.parent

def read(path):
    return json.loads(path.read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def metrics(path):
    if not path.exists():return {}
    lines=path.read_text(errors='replace').splitlines()
    heads=[i for i,s in enumerate(lines) if s.startswith('mode,result,solver_status,verification_status,')]
    if not heads:return {}
    tail=[]
    for line in lines[heads[-1]:]:
        if not line or line.startswith('='):break
        tail.append(line)
    return {r['metric_key']:r['value'] for r in csv.DictReader(tail)}

def collect(base, job, budget, campaign, issues):
    out=base/'raw'/job['id']
    inv=read(out/'invocation.json') if (out/'invocation.json').exists() else {}
    end=read(out/'completion.json') if (out/'completion.json').exists() else None
    d=read(out/'certificate_summary.json') if (out/'certificate_summary.json').exists() else {}
    m=metrics(out/'output.txt')
    status='RUNNING' if inv else 'NOT_STARTED'
    reason='Whole-JVM execution is unfinished.' if inv else 'Fixed predecessor trial has not finished.'
    if (out/'not_run.json').exists():status='NOT_RUN';reason=read(out/'not_run.json')['reason']
    if end:
        if end['timed_out']:status='TO';reason=f'Whole JVM reached the fixed {budget}-second limit; no completed decision is inferred.'
        else:status={0:'WIN',6:'LOSS',5:'OOM',7:'INVALID_CERTIFICATE',8:'INVALID_INPUT'}.get(end['exit_code'],'ERROR');reason=m.get('failure_reason','')
        for name,expected in end.get('files',{}).items():
            if sha(out/name)!=expected:issues.append(f'{campaign}/{job["id"]}: raw hash differs: {name}')
    completed=status in ('WIN','LOSS')
    cell_issues=[]
    if completed:
        if d.get('decision')!=status:cell_issues.append('missing/mismatched certificate diagnostic verdict')
        if m.get('revised_decision')!=('realizable' if status=='WIN' else 'unrealizable'):cell_issues.append('CLI verdict mismatch')
        if m.get('revised_internal_certificate_check')!='passed':cell_issues.append('native certificate checker did not report passed')
        if status=='WIN' and m.get('revised_link_checker')!='passed':cell_issues.append('native Link checker did not report passed')
        for key,metric in [('states_discovered','revised_semantic_states_discovered'),('successor_queries','revised_successor_oracle_calls_cumulative'),('materialized_transitions','revised_materialized_transition_outcomes_cumulative')]:
            if str(d.get(key))!=m.get(metric):cell_issues.append(key+' diagnostic/CLI mismatch')
        key,metric=('worst_completion_rank','revised_worst_completion_rank') if status=='WIN' else ('losing_region_states','revised_losing_region_states')
        if str(d.get(key))!=m.get(metric):cell_issues.append(key+' diagnostic/CLI mismatch')
        if d.get('safe_region_states',0)+d.get('unsafe_region_states',0)!=d.get('certificate_states'):cell_issues.append('certificate partition count mismatch')
        if status=='WIN' and d.get('initial_states_in_region')!=d.get('initial_states'):cell_issues.append('WIN certificate lacks an initial state')
        if status=='LOSS' and not (0<d.get('initial_states_in_region',0)<=d.get('initial_states',0)):cell_issues.append('LOSS certificate lacks a valid losing root')
        reason=d.get('loss_reason','Native E1 certificate and Link checks passed.') if status=='LOSS' else 'Native E1 certificate and Link checks passed.'
        if cell_issues:reason='Completed raw verdict retained, but independent collection detected: '+'; '.join(cell_issues)
    issues.extend(f'{campaign}/{job["id"]}: {x}' for x in cell_issues)
    def count(name):return d.get(name,'') if completed else ''
    def seconds(name):return float(m[name])/1000 if completed and name in m else ''
    return dict(campaign=campaign,host='mac',heap='32g',timeout_seconds=budget,trial=1,
        job_id=job['id'],solver='direct_full' if job['solver']=='direct_full' else 'lazy',merge=job['merge'],
        status=status,raw_diagnostic_decision=d.get('decision',''),expected_decision=job.get('expected_decision',''),
        expectation_check=('PASS' if status==job.get('expected_decision') else 'MISMATCH') if completed and job.get('expected_decision') else 'NOT_APPLICABLE_OR_INCOMPLETE',
        states_discovered=count('states_discovered'),successor_queries=count('successor_queries'),
        materialized_transition_outcomes=count('materialized_transitions'),enabled_buckets='',
        enabled_buckets_availability='Not directly instrumented by the fixed E1 CLI.',
        worst_completion_rank=count('worst_completion_rank'),losing_region_states=count('losing_region_states'),
        certificate_states=count('certificate_states'),safe_region_states=count('safe_region_states'),
        unsafe_region_states=count('unsafe_region_states'),initial_states=count('initial_states'),
        initial_states_in_certificate=count('initial_states_in_region'),
        native_certificate_checker=m.get('revised_internal_certificate_check','') if completed else '',
        native_link_checker=m.get('revised_link_checker','') if completed else '',
        preparation_seconds=seconds('revised_preparation_time'),
        solve_and_internal_check_seconds=seconds('revised_solve_and_internal_check_time'),
        diagnostic_seconds=count('diagnostic_seconds'),whole_jvm_seconds=end['wall_seconds'] if end else '',
        started_at=inv.get('at',''),finished_at=end.get('at','') if end else '',
        input_sha256=inv.get('input_sha256',''),jar_sha256=inv.get('jar_sha256',''),
        exit_code=end['exit_code'] if end else '',raw_directory=str(out.relative_to(PC2)),
        validation='FAIL' if cell_issues else ('PASS' if completed else 'INCOMPLETE'),reason=reason)

def main():
    issues=[]
    manifest=read(HERE/'build/frozen_manifest.json')
    for name,expected in manifest['files'].items():
        if sha(HERE/name)!=expected:issues.append('New frozen file changed: '+name)
    for name,expected in manifest['original_pc2_files'].items():
        if sha(PC2/name)!=expected:issues.append('Original protected file changed: '+name)
    config=read(HERE/'config.json')
    old_jobs=[dict(id='lazy_none',solver='otf',merge='none'),dict(id='lazy_transfers',solver='otf',merge='transfers'),dict(id='direct_full_none',solver='direct_full',merge='none')]
    rows=[collect(PC2/'v2',j,1200,'original_v2',issues) for j in old_jobs]
    new=[collect(HERE,j,7200,'extended_7200',issues) for j in config['jobs']]
    rows+=new
    tables=HERE/'tables';tables.mkdir(exist_ok=True)
    for filename,data in [('results.csv',new),('host_budget_comparison.csv',rows)]:
        with (tables/filename).open('w') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(data)
    # The Xeon plan is separate from observed rows; no execution is claimed here.
    plans=[dict(host='xeon',heap='200g',timeout_seconds=7200,job_id=j['id'],solver=j['solver'],merge=j['merge'],status='NOT_COLLECTED',reason='Existing launcher only; no Xeon operation or imported raw in this campaign.') for j in config['jobs']]
    with (tables/'xeon_plan.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(plans[0]));w.writeheader();w.writerows(plans)
    df=new[1]
    df_consistency=('PASS' if df['status']=='WIN' else 'MISMATCH') if df['status'] in ('WIN','LOSS') else 'INCOMPLETE'
    report=dict(status='FAIL' if issues else 'PASS',at=datetime.now(timezone(timedelta(hours=9))).isoformat(),
        terminal=(HERE/'raw/runner_finished.json').exists(),issues=issues,
        statuses={r['job_id']:r['status'] for r in new},fine_direct_full_vs_original_checked_lazy=df_consistency,
        rows=len(rows),new_trials=len(new),source_sha256=sha(Path(__file__)),
        scope='Fresh comparison of separate host/budget/campaign rows. Internal certificate/Link checks share E1 semantics. Timeout and other unfinished counters are blank. No Xeon measurements inferred.')
    (HERE/'validation').mkdir(exist_ok=True)
    (HERE/'validation/raw_table_audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
