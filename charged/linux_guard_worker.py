"""Reconstruct saved Linux events or recompute the fixed guard-entry formulas."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,time
HERE=Path(__file__).resolve().parent
SOURCE=HERE/'evidence/RESUMED_20260910_1617'
STAGE=sys.argv[1];OUT=Path(sys.argv[2]);BEGIN=time.monotonic()
assert __debug__ and STAGE in ['linux-dentry','guard-entry']
steps=[]
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def copy(folder,names):
    dest=OUT/folder;dest.mkdir(parents=True,exist_ok=True)
    for name in names:shutil.copy2(SOURCE/folder/name,dest/name)
    return dest
def run(label,script):
    start=time.monotonic()
    with(OUT/(label+'.stdout')).open('xb') as out,(OUT/(label+'.stderr')).open('xb') as err:
        p=subprocess.run([sys.executable,'-B',str(script)],stdout=out,stderr=err,timeout=180)
    assert p.returncode==0,(label,p.returncode)
    steps.append(dict(step=label,returncode=p.returncode,seconds=time.monotonic()-start))
def same(folder,name):assert sha(OUT/folder/name)==sha(SOURCE/folder/name),(folder,name)
def compare(folder,name,exclude):
    a=read(OUT/folder/name);b=read(SOURCE/folder/name)
    assert set(a)==set(b),(folder,name,'key set')
    for k in a:
        if k not in exclude:assert a[k]==b[k],(folder,name,k)
if STAGE=='linux-dentry':
    folder='linux_dentry_01'
    d=copy(folder,['INPUTS01.json','INPUTS02.json','KERNEL_MATRIX01.test.log','KERNEL_MATRIX02.test.log','validate_matrix01.py','validate_matrix02.py'])
    for v in ['01','02']:
        run('linux_saved_'+v,d/('validate_matrix'+v+'.py'))
        same(folder,'MATRIX_JOINED'+v+'.json')
        compare(folder,'MATRIX_VALIDATION'+v+'.json',{'utc'})
    same(folder,'MATRIX_COMPARISON02.json')
    copy(folder,['KERNEL_MATRIX03B.test.log','validate_matrix03b.py','MATRIX_JOINED02.json'])
    run('linux_global_attribution',d/'validate_matrix03b.py')
    same(folder,'MATRIX_GLOBAL03B.json')
    compare(folder,'MATRIX_VALIDATION03B.json',{'utc'})
    # Transport/bootstrap failures are retained as failures, not replayed away.
    failed=read(SOURCE/folder/'KERNEL_MATRIX_COMPLETION03.json')
    fix=read(SOURCE/folder/'RUNNER_INSTALL_FIX03B.json')
    assert failed['status']=='INSTALL_FAILURE' and fix['native_executions']==fix['scientific_rows']==0
    a=read(d/'MATRIX_VALIDATION01.json');b=read(d/'MATRIX_VALIDATION02.json')
    assert a['status']==b['status']=='PASS'
    values=dict(original_valid_rows=1536,extended_valid_rows=1920,controls_per_matrix=4,extended_body_records=2878,extended_successful_paths=948,extended_expected_overflows=972,paired_rows=384,guard_reduction_pairs=138,higher_Q_pairs=144,global_attribution_rows=1924,global_writer_sections=1763,extra_global_writer_rows=0,overlapping_populations=True,unobserved_fault_and_allocation_injections=True)
else:
    folder='guard_entry_01'
    d=copy(folder,['check01.py','INPUTS01.json','PROTOCOL01.md','CANDIDATE_PROOF01.md'])
    run('guard_entry_fixed',d/'check01.py')
    same(folder,'ROWS01.jsonl')
    compare(folder,'RESULT01.json',{'utc','seconds'})
    assert read(d/'RESULT01.json')['status']=='PASS'
    values=dict(fixed_inputs=1809,universal_scalar_roots=26874,informed_one_write_cases=1809,boundary_checks=5427,interpreted_policy_paths=86376,scalar_oracle_states=205707)
summary=dict(status='SUCCESS',stage=STAGE,seconds=time.monotonic()-BEGIN,steps=steps,**values,new_native_runs=0,new_timing_samples=0,new_evaluation_population=False,independent_reproduction=False,scope='Exact fixed formulas or saved native event reconstruction; no source proof, native minimax transfer or measured guard-price certification.')
with(OUT/'SUMMARY.json').open('x') as out:json.dump(summary,out,indent=2);out.write('\n')
print(json.dumps(summary),flush=True)
