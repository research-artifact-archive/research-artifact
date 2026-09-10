"""Replay the one-job whole-kernel deterministic minimax regret comparison."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,time
HERE=Path(__file__).resolve().parent;OUT=Path(sys.argv[2]);SOURCE=HERE/'evidence/RESUMED_20260910_0343/single_job_regret_01'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if not __debug__:raise SystemExit('Assertions must be enabled.')
assert sys.argv[1]=='single-job-regret';start=time.monotonic();dest=OUT/'single_job_regret_01';dest.mkdir()
for name in ['PLAN.md','PROOF_DRAFT.md','run01.py']:shutil.copyfile(SOURCE/name,dest/name)
with (OUT/'recompute.stdout').open('xb') as out,(OUT/'recompute.stderr').open('xb') as err:
 result=subprocess.run([sys.executable,'-B',str(dest/'run01.py')],stdout=out,stderr=err,timeout=120)
assert result.returncode==0,result.returncode
for name in ['INPUTS.json','RAW.jsonl','REGRET.json']:assert sha(dest/'run01'/name)==sha(SOURCE/'run01'/name),name
fresh=json.loads((dest/'run01/SUMMARY.json').read_text());old=json.loads((SOURCE/'run01/SUMMARY.json').read_text());assert set(fresh)==set(old)
for k in fresh:
 if k not in ['utc','seconds','peak_RSS_bytes']:assert fresh[k]==old[k],k
assert fresh['status']=='PASS' and fresh['roots']==11232 and all(x['detected'] for x in fresh['controls'])
summary=dict(status='SUCCESS',stage='single-job-regret',seconds=time.monotonic()-start,replay_only=True,new_native_runs=0,new_timing_samples=0,conditions=fresh['conditions'],root_checks=fresh['roots'],policy_budget_values=fresh['policy_budget_values'],universally_inadmissible_policies_rejected=1404,corruption_controls=4,scope='Recompute finite serial one-job games and policy extrema with exact unchanged rows. The refined operation-level proof separately covers the full deterministic program class, including inspections and retained preparations.')
with (OUT/'SUMMARY.json').open('x') as f:json.dump(summary,f,indent=2);f.write('\n')
print(json.dumps(summary),flush=True)
