"""Stage60: exact replay of the frozen arbitrary-DAG universal-caller check."""
from pathlib import Path
import datetime,gzip,hashlib,json,os,shutil,signal,subprocess,sys,time
HERE=Path(__file__).resolve().parent
BASE='evidence/RESUMED_20260911_1123/'
NAMES=['dag_approximation_01','dag_approximation_audit_01']
def sha(data):return hashlib.sha256(data).hexdigest()
def digest(path):return sha(path.read_bytes())
def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as f:json.dump(value,f,indent=2,sort_keys=True);f.write('\n')
def load(path):return json.loads(path.read_text())

def main():
    assert __debug__,'Assertions must remain enabled.'
    stage,out=sys.argv[1],Path(sys.argv[2]).resolve();assert stage=='dag-approximation'
    # Public driver creates OUT. Direct use may create it here, never overwrite.
    if not out.exists():out.mkdir(parents=True)
    assert not list(out.glob('SUMMARY.json'))
    start=time.monotonic();proc=None
    def expired(*args):raise TimeoutError('stage60 replay watchdog')
    signal.signal(signal.SIGALRM,expired);signal.signal(signal.SIGTERM,expired);signal.alarm(295)
    fixed=out/'fixed';fixed.mkdir();mapping={}
    provenance=load(HERE/'PROVENANCE.json')
    for row in provenance['files']:
        if not any(row['path'].startswith(BASE+n+'/') for n in NAMES):continue
        data=(HERE/row['path']).read_bytes();assert len(data)==row['public_bytes'] and sha(data)==row['public_sha256']
        rel=row['path'][len(BASE):]
        if row.get('storage_encoding')=='gzip':
            data=gzip.decompress(data);rel=rel[:-3]
            assert len(data)==row['decoded_bytes'] and sha(data)==row['decoded_sha256']
        target=fixed/rel;assert target.resolve().is_relative_to(fixed)
        target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as f:f.write(data)
        mapping[rel]=row
    projection=load(HERE/'SOURCE_PROJECTION_MAP05.json')
    for row in projection['files']:assert mapping.get(row['relative_path'])==row['provenance_row']
    excluded={row['path']:row for row in projection['excluded']}
    original=fixed/'dag_approximation_01';audit=fixed/'dag_approximation_audit_01'
    expected=load(original/'run01/RESULT.json');initial=load(original/'run01/START.json')
    assert expected['status']=='SUCCESS' and expected['inputs']==initial['inputs']
    references=0
    def bind(rel,expected_hash):
        nonlocal references
        if rel in excluded:assert excluded[rel]['source_sha256']==expected_hash
        else:assert mapping[rel]['source_sha256']==expected_hash,rel
        references+=1
    for name,h in expected['inputs'].items():bind('dag_approximation_01/'+name,h)
    for name,h in expected['outputs'].items():bind('dag_approximation_01/run01/'+name,h)
    manifest=load(audit/'OUTPUT_MANIFEST01.json')
    for name,meta in manifest['files'].items():bind('dag_approximation_audit_01/'+name,meta['sha256'])
    for index in [1,2,3]:
        receipt=load(audit/f'INPUT_RECEIPT0{index}.json')
        for name,meta in receipt['files'].items():bind('dag_approximation_audit_01/inputs01/'+name,meta['sha256'])
        if index>1:bind(f'dag_approximation_audit_01/INPUT_RECEIPT0{index-1}.json',receipt['prior_receipt_sha256'])
        if index==3:bind('dag_approximation_audit_01/PROOF_AUDIT01.md',receipt['own_audit_before_root_proof_read_sha256'])
    save(out/'ORIGINAL_SOURCE_BINDINGS.json',dict(status='SUCCESS',references=references,excluded_manuscript_references_declared=True,excluded=projection['excluded'],original_hashes_not_projected_hashes=True))
    working=out/'working';working.mkdir()
    for name in ['check01.py','FINITE_PROTOCOL01.md','PROOF01.md']:
        shutil.copyfile(original/name,working/name)
    # The original checker already accepts --out and has no absolute deadline.
    # No source adaptation or input-hash substitution is necessary or permitted.
    for name,h in expected['inputs'].items():assert digest(working/name)==h,name
    (out/'ADAPTATIONS.diff').write_text('')
    save(out/'ADAPTATIONS.json',dict(source_changes=[],reason='Original --out interface is portable; original cap300 is retained.',original_sources_preserved_in='fixed/dag_approximation_01',working_hashes={n:digest(working/n) for n in expected['inputs']}))
    argv=[sys.executable,'-B',str(working/'check01.py'),'--out',str(working/'run01'),'--cap','300']
    save(out/'REPLAY_FREEZE.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),stage=stage,argv=argv,source_proof_for_original_run='PROOF01.md',selected_final_proof='PROOF02.md',selected_final_proof_sha256=mapping['dag_approximation_01/PROOF02.md']['source_sha256'],inputs={n:digest(working/n) for n in expected['inputs']},result_comparison_excluded_fields=['elapsed_seconds'],root_population_only=True,replay_only=True,worker_sha256=digest(Path(__file__)),process_timeout_seconds=290,stage_watchdog_seconds=295))
    process_start=time.monotonic();status='NOT_STARTED';code=None
    try:
        with (out/'evaluator.stdout.txt').open('x') as so,(out/'evaluator.stderr.txt').open('x') as se:
            proc=subprocess.Popen(argv,stdout=so,stderr=se,start_new_session=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
            try:code=proc.wait(timeout=290);status='SUCCESS' if code==0 else 'FAILURE'
            except subprocess.TimeoutExpired:
                status='TIMEOUT';os.killpg(proc.pid,signal.SIGTERM)
                try:code=proc.wait(timeout=2)
                except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);code=proc.wait()
    finally:
        if proc is not None and proc.poll() is None:os.killpg(proc.pid,signal.SIGKILL);code=proc.wait()
        save(out/'EVALUATOR_PROCESS_RESULT.json',dict(status=status,returncode=code,seconds=time.monotonic()-process_start,argv=argv))
    assert status=='SUCCESS',(status,code)
    actual=load(working/'run01/RESULT.json')
    assert set(actual)==set(expected)
    assert {k:v for k,v in actual.items() if k!='elapsed_seconds'}=={k:v for k,v in expected.items() if k!='elapsed_seconds'},'RESULT differs beyond elapsed_seconds'
    assert {p.name for p in (working/'run01').iterdir()}=={p.name for p in (original/'run01').iterdir()}
    exact=[]
    for p in sorted((original/'run01').iterdir()):
        if p.name=='RESULT.json':continue
        assert (working/'run01'/p.name).read_bytes()==p.read_bytes(),p.name
        exact.append(p.name)
    # Geometry is compared byte-for-byte above, including exact fractions,
    # integer weights, decimal projections, row order and all limiting gaps.
    for rel,row in mapping.items():
        raw=(fixed/rel).read_bytes();assert sha(raw)==row['projected_source_sha256'],rel
    save(out/'SUMMARY.json',dict(status='SUCCESS',stage=stage,seconds=time.monotonic()-start,roots=actual['roots'],rows=actual['rows'],expanded_states=actual['expanded_states'],geometric_rows=actual['geometric_rows'],violations=actual['violations'],max_finite_ratio=actual['max_finite_ratio'],exact_output_files=exact,result_excluded_fields=['elapsed_seconds'],source_bindings_verified=references,source_adaptations=0,all_fixed_sources_unchanged=True,source_proof='PROOF01.md',adopted_proof='PROOF02.md',replay_only=True,new_exploratory_population=False,new_native_measurements=0))
    signal.alarm(0)
    print(json.dumps(load(out/'SUMMARY.json')),flush=True)
if __name__=='__main__':main()
