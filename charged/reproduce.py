#!/usr/bin/env python3
"""Bounded replay into a new directory; original measurements remain immutable."""
import argparse,datetime,gzip,hashlib,json,os,signal,subprocess,sys,time
from pathlib import Path

HERE=Path(__file__).resolve().parent
COMPACT_STAGES=['compact','compact-native','compact-scale']
RESOURCE_STAGES=['price-bounds','resource-frontier','resource-vector','resource-frontier-native','budget-blind']
STAGES=['curves','native','deephaven','scale','calibration','ordering','refutations']+COMPACT_STAGES+RESOURCE_STAGES+['universal-work','universal-order','adaptive-work','probe-blocking','roslyn-source','protected-tail','protected-suffix','roslyn-semantics','roslyn-reentry','roslyn-arrivals','partial-repair','roslyn-compilation','partial-compact','partial-objectives','roslyn-batch','roslyn-document-guard','workflow-repair','arrival-budget','cap-contracts','roslyn-per-job','single-job-regret','workflow-regret','source-cost-boundaries','joint-work','general-retry','one-retry-native','universal-independent','universal-independent-native','linux-dentry','guard-entry','charged-comparison','fully-charged-one-write','linux-counting','guard-only-joint','uniform-guard','double-counted-mismatch','unit-guard-dag','universal-observation-dag','short-order-policy','safe-fresh-suffix','residual-safety','java-residual-filter','charged-general','three-cost-residual','dag-approximation']

def save(p,x):
    with p.open('x') as f:json.dump(x,f,indent=2);f.write('\n')
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def verify():
    m=json.loads((HERE/'PROVENANCE.json').read_text())
    seen=set()
    for row in m['files']:
        p=HERE/row['path'];assert p.resolve().is_relative_to(HERE.resolve()) and row['path'] not in seen
        assert p.is_file() and p.stat().st_size==row['public_bytes'] and digest(p)==row['public_sha256'],row['path']
        if row.get('storage_encoding')=='gzip':
            hasher=hashlib.sha256();size=0
            with gzip.open(p,'rb') as f:
                for block in iter(lambda:f.read(1048576),b''):
                    hasher.update(block);size+=len(block)
                    assert size<=row['decoded_bytes'],row['path']
            assert size==row['decoded_bytes'] and hasher.hexdigest()==row['decoded_sha256'],row['path']
        seen.add(row['path'])
    return len(seen)

def main():
    if not __debug__:raise SystemExit('Assertions must be enabled; do not use python -O.')
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage',choices=['verify','all','protected-suffix-java','protected-tail-java','native-java','compact-native-java','resource-vector-java','resource-frontier-java','budget-blind-java']+STAGES)
    p.add_argument('--out',type=Path);p.add_argument('--quick',action='store_true');p.add_argument('--timeout',type=int,default=300)
    a=p.parse_args();count=verify()
    if a.stage=='verify':print(json.dumps(dict(status='VERIFIED',files=count)));return
    if a.out is None:p.error('--out is required for a replay')
    if a.timeout<1:p.error('--timeout must be positive')
    a.out.mkdir(parents=True,exist_ok=False)
    stages=STAGES if a.stage=='all' else [a.stage]
    save(a.out/'REPLAY_INPUT.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),stage=a.stage,quick=a.quick,timeout_per_stage=a.timeout,python=sys.version,executable=sys.executable,source_manifest_sha256=digest(HERE/'PROVENANCE.json'),worker_sha256=digest(HERE/'worker.py'),compact_worker_sha256=digest(HERE/'compact_worker.py'),resource_worker_sha256=digest(HERE/'resource_worker.py'),universal_work_worker_sha256=digest(HERE/'universal_work_worker.py'),universal_order_worker_sha256=digest(HERE/'universal_order_worker.py'),bounded_source_worker_sha256=digest(HERE/'bounded_source_worker.py'),suffix_worker_sha256=digest(HERE/'suffix_worker.py'),semantics_partial_worker_sha256=digest(HERE/'semantics_partial_worker.py'),partial_compact_worker_sha256=digest(HERE/'partial_compact_worker.py'),objectives_batch_worker_sha256=digest(HERE/'objectives_batch_worker.py'),document_guard_worker_sha256=digest(HERE/'document_guard_worker.py'),workflow_worker_sha256=digest(HERE/'workflow_worker.py'),cap_contracts_worker_sha256=digest(HERE/'cap_contracts_worker.py'),regret_worker_sha256=digest(HERE/'regret_worker.py'),workflow_regret_worker_sha256=digest(HERE/'workflow_regret_worker.py'),source_cost_worker_sha256=digest(HERE/'source_cost_worker.py'),joint_work_worker_sha256=digest(HERE/'joint_work_worker.py'),general_retry_worker_sha256=digest(HERE/'general_retry_worker.py'),universal_independent_worker_sha256=digest(HERE/'universal_independent_worker.py'),linux_guard_worker_sha256=digest(HERE/'linux_guard_worker.py'),charged_comparison_worker_sha256=digest(HERE/'charged_comparison_worker.py'),resource_accounting_worker_sha256=digest(HERE/'resource_accounting_worker.py'),unit_guard_worker_sha256=digest(HERE/'unit_guard_worker.py'),observation_dag_worker_sha256=digest(HERE/'observation_dag_worker.py'),short_order_worker_sha256=digest(HERE/'short_order_worker.py'),safe_suffix_worker_sha256=digest(HERE/'safe_suffix_worker.py'),residual_worker_sha256=digest(HERE/'residual_worker.py'),java_residual_worker_sha256=digest(HERE/'java_residual_worker.py'),charged_general_worker_sha256=digest(HERE/'charged_general_worker.py'),three_cost_residual_worker_sha256=digest(HERE/'three_cost_residual_worker.py'),replay04_common_sha256=digest(HERE/'replay04_common.py'),dag_approximation_worker_sha256=digest(HERE/'dag_approximation_worker.py'),driver_sha256=digest(Path(__file__)),replay_only=True,new_evaluation_population=False))
    results=[]
    for stage in stages:
        output=a.out/stage;output.mkdir()
        worker='dag_approximation_worker.py' if stage=='dag-approximation' else 'charged_general_worker.py' if stage=='charged-general' else 'three_cost_residual_worker.py' if stage=='three-cost-residual' else 'java_residual_worker.py' if stage=='java-residual-filter' else 'residual_worker.py' if stage=='residual-safety' else 'safe_suffix_worker.py' if stage=='safe-fresh-suffix' else 'short_order_worker.py' if stage=='short-order-policy' else 'observation_dag_worker.py' if stage=='universal-observation-dag' else 'unit_guard_worker.py' if stage=='unit-guard-dag' else 'resource_accounting_worker.py' if stage in ['guard-only-joint','uniform-guard','double-counted-mismatch'] else 'charged_comparison_worker.py' if stage in ['charged-comparison','fully-charged-one-write','linux-counting'] else 'linux_guard_worker.py' if stage in ['linux-dentry','guard-entry'] else 'universal_independent_worker.py' if stage in ['universal-independent','universal-independent-native'] else 'general_retry_worker.py' if stage in ['general-retry','one-retry-native'] else 'joint_work_worker.py' if stage=='joint-work' else 'source_cost_worker.py' if stage=='source-cost-boundaries' else 'workflow_regret_worker.py' if stage=='workflow-regret' else 'regret_worker.py' if stage=='single-job-regret' else 'cap_contracts_worker.py' if stage in ['cap-contracts','roslyn-per-job'] else 'workflow_worker.py' if stage in ['workflow-repair','arrival-budget'] else 'document_guard_worker.py' if stage=='roslyn-document-guard' else 'objectives_batch_worker.py' if stage in ['partial-objectives','roslyn-batch'] else 'partial_compact_worker.py' if stage=='partial-compact' else 'semantics_partial_worker.py' if stage in ['roslyn-semantics','roslyn-reentry','roslyn-arrivals','partial-repair','roslyn-compilation'] else 'suffix_worker.py' if stage in ['protected-suffix','protected-suffix-java'] else 'bounded_source_worker.py' if stage in ['adaptive-work','probe-blocking','roslyn-source','protected-tail','protected-tail-java'] else 'universal_order_worker.py' if stage=='universal-order' else 'universal_work_worker.py' if stage=='universal-work' else 'resource_worker.py' if stage in RESOURCE_STAGES+['resource-vector-java','resource-frontier-java','budget-blind-java'] else 'compact_worker.py' if stage in COMPACT_STAGES+['compact-native-java'] else 'worker.py'
        argv=[sys.executable,'-B',str(HERE/worker),stage,str(output)]
        if a.quick:argv.append('--quick')
        start=time.monotonic()
        with (output/'stdout.txt').open('xb') as stdout,(output/'stderr.txt').open('xb') as stderr:
            proc=subprocess.Popen(argv,stdout=stdout,stderr=stderr,start_new_session=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE="1"))
            try:code=proc.wait(timeout=a.timeout);status='SUCCESS' if code==0 else 'FAILURE'
            except subprocess.TimeoutExpired:
                status='TIMEOUT';os.killpg(proc.pid,signal.SIGTERM)
                try:code=proc.wait(timeout=2)
                except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);code=proc.wait()
        row=dict(stage=stage,status=status,returncode=code,seconds=time.monotonic()-start,argv=argv)
        if (output/'SUMMARY.json').exists():row['summary']=json.loads((output/'SUMMARY.json').read_text())
        save(output/'PROCESS_RESULT.json',row);results.append(row)
        print(json.dumps(dict(stage=stage,status=status,seconds=row['seconds'])),flush=True)
    save(a.out/'REPLAY_RESULT.json',dict(status='SUCCESS' if all(r['status']=='SUCCESS' for r in results) else 'FAILURE',stages=results,replay_only=True))
    raise SystemExit(0 if all(r['status']=='SUCCESS' for r in results) else 1)

if __name__=='__main__':main()
