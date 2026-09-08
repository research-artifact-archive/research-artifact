from pathlib import Path
import datetime,hashlib,json,subprocess,sys
import prepare
ROOT=Path(__file__).resolve().parent;SESSION=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    assert not sys.flags.optimize and not (ROOT/'RAW.jsonl').exists()
    for f in json.loads((ROOT/'GENERATOR_MANIFEST.json').read_text())['files']:assert sha(Path(f['path']))==f['sha256']
    sources=[ROOT/p for p in ['PLAN.md','generate.py','prepare.py','freeze.py','run.py','NativeDagFinal.java',
             'GENERATOR_MANIFEST.json','VECTORS.json','MATH_VALIDATION.json','INPUTS.json','CASES.tsv','INPUTS.tsv','PREPARATION_RECEIPT.json']]
    sources+=sorted((ROOT/'artifacts').glob('*.json'))+sorted((ROOT/'profiles').glob('*.tsv'))
    sources+=[SESSION/p for p in ['dependency_native_01/experiment.py','dependency_native_01/NativeDag.java','dependency_native_01/INPUTS.json',
              'final_evaluation_dag_01/evaluate.py','final_evaluation_dag_01/structure.py','final_evaluation_dag_01/primitive.py',
              'primitive_rmw_01/explore.py','dependency_hybrid_01/hybrid.py','dependency_hybrid_check_02/check.py',
              'dependency_curves_01/curves.py','dependency_curves_01/checker.py','source_text/openjdk17_runtime/RECEIPT.json']]
    version=subprocess.run([str(prepare.JAVA),'-version'],capture_output=True,text=True,timeout=10)
    data=json.loads((ROOT/'INPUTS.json').read_text())
    manifest=dict(utc=prepare.now(),files=[dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size) for p in sources],
        unit_count=len(data['units']),core_cells=384,core_policy_cells=1920,control_units=4,
        java=str(prepare.JAVA),javac=str(prepare.JAVAC),java_sha256=sha(prepare.JAVA),javac_sha256=sha(prepare.JAVAC),
        python=sys.executable,python_sha256=sha(Path(sys.executable)),python_version=sys.version,
        version_stdout=version.stdout,version_stderr=version.stderr,
        compile_argv=[str(prepare.JAVAC),'-d',str(ROOT/'classes'),str(ROOT/'NativeDagFinal.java')],
        execute_argv=[str(prepare.JAVA),'-Xmx256m','-XX:ActiveProcessorCount=1','-cp',str(ROOT/'classes'),'NativeDagFinal',str(ROOT)],
        compile_timeout_seconds=30,execute_timeout_seconds=120,native_outcomes_observed=False,
        retry_allowed=False,exclusions=[],final_evaluation=True)
    prepare.save('MANIFEST.json',manifest)
    print(dict(files=len(sources),units=len(data['units']),manifest_sha256=sha(ROOT/'MANIFEST.json')))
if __name__=='__main__':main()
