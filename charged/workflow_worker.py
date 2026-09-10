"""Replay fixed workflow equations/certificates and saved arrival count analysis."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,time
HERE=Path(__file__).resolve().parent;BASE=HERE/'evidence/RESUMED_20260910_0343';OUT=Path(sys.argv[2])
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(script,label,cap=180):
    with (OUT/(label+'.stdout')).open('xb') as stdout,(OUT/(label+'.stderr')).open('xb') as stderr:
        r=subprocess.run([sys.executable,'-B',str(script)],stdout=stdout,stderr=stderr,timeout=cap)
    assert r.returncode==0,(label,r.returncode)
def copy_files(source,dest,names):
    dest.mkdir(parents=True)
    for name in names:shutil.copyfile(source/name,dest/name)
def same_json(a,b,ignored=()):
    a=read(a);b=read(b);assert set(a)==set(b)
    for key in a:
        if key not in ignored:assert a[key]==b[key],key
def workflow():
    unpriced=BASE/'partial_repair_dag_01';fresh=OUT/'unpriced'
    copy_files(unpriced,fresh,['run01.py','PLAN.md','PROOF.md'])
    run(fresh/'run01.py','unpriced')
    for name in ['INPUTS.json','RAW.jsonl']:
        assert sha(fresh/'run01'/name)==sha(unpriced/'run01'/name),name
    same_json(fresh/'run01/SUMMARY.json',unpriced/'run01/SUMMARY.json',{'utc','seconds'})
    a=read(fresh/'run01/SUMMARY.json');assert a['status']=='PASS' and a['all_units']==8960

    charged=BASE/'partial_repair_toll_dag_01';dest=OUT/'charged'
    names=['run02.py','PLAN.md','PROOF.md','THRESHOLD_CERTIFICATE_PROOF.md','HISTORY_COUNT_CORRECTION.md','THRESHOLD_VALIDATION_PLAN.md','threshold_compile.py','threshold_check.py','validate_threshold01.py']
    copy_files(charged,dest,names);run(dest/'run02.py','toll')
    for name in ['INPUTS.json','RAW.jsonl']:
        assert sha(dest/'run02'/name)==sha(charged/'run02'/name),name
    same_json(dest/'run02/SUMMARY.json',charged/'run02/SUMMARY.json',{'utc','seconds'})
    b=read(dest/'run02/SUMMARY.json');assert b['status']=='PASS' and b['all_units']==37248
    run(dest/'validate_threshold01.py','threshold')
    new=dest/'threshold_validation01';old=charged/'threshold_validation01'
    for p in old.glob('*.json*'):
        if p.name not in ['SUMMARY.json','INPUT_RECEIPT.json']:
            assert sha(new/p.name)==sha(p),p.name
    same_json(new/'SUMMARY.json',old/'SUMMARY.json',{'utc','seconds','peak_RSS_bytes'})
    c=read(new/'SUMMARY.json');assert c['status']=='PASS' and c['statuses']=={'SUCCESS':37368}
    return dict(unpriced_conditions=8960,unpriced_common_policy_searches=6208,positive_toll_conditions=37248,positive_toll_budget_roots=216282,threshold_checks=37368,new_threshold_profile_cases=120,exported_certificate_checks=123,executable_paths=sum(x['terminal_paths'] for x in c['executable_policy_checks']),source_counts=[a,b,c],scope='Fresh arithmetic replay of authored finite games and certificate checks; no native executions, new empirical population or independent-third-party claim. Initial platform failure and all corrected proof notes remain preserved.')
def arrival_budget():
    parent=OUT/'arrivals';analysis=parent/'arrival_budget_analysis_01'
    copy_files(BASE/'arrival_budget_analysis_01',analysis,['analyze01.py','PLAN.md'])
    relatives=['roslyn_arrivals_01','roslyn_arrivals_balanced_01','roslyn_rebase_01/arrivals01','roslyn_rebase_batch_01/arrivals01']
    for relative in relatives:
        source=BASE/relative;target=parent/relative
        (target/'run01/check01').mkdir(parents=True)
        shutil.copyfile(source/'run01/check01/RECEIPT.json',target/'run01/check01/RECEIPT.json')
        for p in sorted((source/'run01').glob('p*/stdout.jsonl')):
            dest=target/'run01'/p.parent.name/p.name;dest.parent.mkdir();shutil.copyfile(p,dest)
    source=BASE/'roslyn_rebase_batch_01/arrivals01/analysis01/SUMMARY.json';target=parent/'roslyn_rebase_batch_01/arrivals01/analysis01/SUMMARY.json'
    target.parent.mkdir();shutil.copyfile(source,target)
    run(analysis/'analyze01.py','arrival_budget')
    old=BASE/'arrival_budget_analysis_01/run01';new=analysis/'run01'
    for name in ['UNITS.json','CHECKS.json','CELLS.tsv']:assert sha(new/name)==sha(old/name),name
    same_json(new/'SUMMARY.json',old/'SUMMARY.json',{'utc','seconds','original_batch_pair_source_sha256'})
    d=read(new/'SUMMARY.json');assert d['status']=='PASS' and d['all_units']==7392
    return dict(saved_arrival_units=7392,measured=6160,warmup=1232,controls=len(d['controls']),reconstructed_cells=len(d['cells']),scope='Post-outcome analysis of unchanged arrival records; each actual foreground-period write count and count bound is reconstructed. No new timing runs, common controlled write budget or causal delay inference.')
if not __debug__:raise SystemExit('Assertions must be enabled.')
start=time.monotonic();stage=sys.argv[1]
result={'workflow-repair':workflow,'arrival-budget':arrival_budget}[stage]()
summary=dict(status='SUCCESS',stage=stage,seconds=time.monotonic()-start,replay_only=True,new_native_runs=0,new_timing_samples=0,**result)
with (OUT/'SUMMARY.json').open('x') as f:json.dump(summary,f,indent=2);f.write('\n')
print(json.dumps(summary),flush=True)
