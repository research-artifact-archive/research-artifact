"""Recompute compact partial-repair certificates; preserve all original timings."""
from pathlib import Path
import datetime,hashlib,json,shutil,subprocess,sys,time
HERE=Path(__file__).resolve().parent;OUT=Path(sys.argv[2]);BASE=HERE/'evidence/RESUMED_20260910_0343'

def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):
    with p.open('x') as f:json.dump(x,f,indent=2);f.write('\n')
def run(dest,name,cap=180):
    r=subprocess.run([sys.executable,'-B',str(dest/name)],capture_output=True,text=True,timeout=cap)
    (OUT/(name+'.stdout')).write_text(r.stdout);(OUT/(name+'.stderr')).write_text(r.stderr)
    assert r.returncode==0,(name,r.returncode,r.stdout[-2000:],r.stderr[-2000:])
def same_receipt(new,old,ignored):
    assert set(new)==set(old)
    for k in old:
        if k not in ignored:assert new[k]==old[k],k

if not __debug__:raise SystemExit('Assertions must be enabled.')
assert sys.argv[1]=='partial-compact';start=time.monotonic()
source=BASE/'partial_repair_compact_01';dest=OUT/'partial_repair_compact_01';dest.mkdir()
prior=OUT/'partial_repair_baseline_01/run01';prior.mkdir(parents=True)
shutil.copyfile(BASE/'partial_repair_baseline_01/run01/outcomes.jsonl',prior/'outcomes.jsonl')
for p in source.iterdir():
    if p.is_file() and p.suffix in ['.py','.md']:shutil.copyfile(p,dest/p.name)
for folder in ['scale01','scale02']:shutil.copytree(source/folder,dest/folder)

for name,folder,files in [
    ('check01.py','run01',['outcomes.jsonl','EXAMPLE.json','FAILURES.json']),
    ('extra01.py','extra01',['OUTCOMES.json','FAILURES.json']),
    ('monotone_check01.py','monotone_check01',['OUTCOMES.jsonl','THRESHOLDS.json','CONTROLS.json','FAILURES.json'])]:
    run(dest,name)
    new=read(dest/folder/'RECEIPT.json');old=read(source/folder/'RECEIPT.json')
    same_receipt(new,old,{'utc','seconds'});assert new['status']=='PASS'
    for file in files:assert sha(dest/folder/file)==sha(source/folder/file),(folder,file)

for name,folder,files in [
    ('analyze_scale01.py','scale_analysis01',['PAIRS.json']),
    ('analyze_scale02.py','scale_analysis02',['VERSION_COMPARISONS.json','OLD_DP_COMPARISONS.json','STATUS_CHANGES.json'])]:
    run(dest,name)
    new=read(dest/folder/'SUMMARY.json');old=read(source/folder/'SUMMARY.json')
    same_receipt(new,old,{'utc','analysis_seconds'});assert new['status']=='PASS'
    for file in files:assert sha(dest/folder/file)==sha(source/folder/file),(folder,file)

a=read(dest/'scale01/RECEIPT.json');b=read(dest/'scale02/RECEIPT.json')
assert a['planned']==216 and a['statuses']=={'SUCCESS':210,'TIMEOUT':6}
assert b['planned']==168 and b['statuses']=={'SUCCESS':168}
summary=dict(status='SUCCESS',stage='partial-compact',seconds=time.monotonic()-start,
    initial_dp_rows=20920,extra_rational_rows=108,version2_regression_rows=21028,
    version2_threshold_decisions=1600,version2_controls=10,
    initial_scale_units=216,initial_scale_success=210,retained_timeouts=6,
    changed_version_scale_units=168,changed_version_success=168,
    original_scale_certificates_rechecked=166,changed_scale_certificates_checked_by_both_versions=168,
    old_profiledp_ratio_agreements=44,replay_only=True,quick=False,new_timing_samples=0,
    scope='Recomputed exact small-study outcomes and every saved scale certificate. Version1 failures remain immutable; version2 is a documented algorithm change. No native partial-cost calibration or literature-priority certification.')
write(OUT/'SUMMARY.json',summary);print(json.dumps(summary),flush=True)
