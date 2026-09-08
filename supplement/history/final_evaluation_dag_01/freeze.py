from pathlib import Path
import datetime,hashlib,json,platform,sys
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    assert not sys.flags.optimize
    assert not (ROOT/'RAW.jsonl').exists() and not (ROOT/'RUN_STARTED.json').exists()
    for name in ('PREFLIGHT_MANIFEST.json','CONTROL_MANIFEST.json','LEMMA_PREFLIGHT_MANIFEST.json'):
        for item in json.loads((ROOT/name).read_text())['files']:
            assert sha(Path(item['path']))==item['sha256'],item['path']
    local=['PLAN.md','PLAN_DRAFT.md','INPUTS.json','DENOMINATORS.json','prepare.py','freeze.py','run.py',
           'primitive.py','structure.py','evaluate.py','evaluate_final.py','lemmas.py',
           'PREFLIGHT_PLAN.md','preflight.py','PREFLIGHT_INPUTS.json','PREFLIGHT_MANIFEST.json','PREFLIGHT_RAW.jsonl','PREFLIGHT_SUMMARY.json',
           'controls.py','CONTROL_INPUTS.json','CONTROL_MANIFEST.json','CONTROL_RAW.json','CONTROL_SUMMARY.json',
           'LEMMA_PREFLIGHT_MANIFEST.json','LEMMA_PREFLIGHT_RAW.json','AUTHOR_CHECK_RAW.json','DEVELOPMENT_DISPOSITION.md']
    imported=['primitive_rmw_01/explore.py','dependency_hybrid_01/hybrid.py','dependency_curves_01/curves.py',
              'dependency_curves_01/checker.py','dependency_hybrid_check_02/check.py',
              'dependency_retry_01/INPUTS.json','dependency_curves_01/INPUTS.json',
              'dependency_hybrid_01/SMALL_INPUTS.json','final_evaluation_01/semantic/INPUTS.json']
    files=[ROOT/p for p in local]+[ROOT.parent/p for p in imported]
    record=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                files=[dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p)) for p in files],
                python=sys.executable,python_sha256=sha(Path(sys.executable)),python_version=sys.version,
                platform=platform.platform(),assertions_enabled=True,per_unit_seconds=10,
                total_soft_seconds=180,unit_count=4232,root_count=21160,
                final_evaluation=True,retry=False,exclusions=[],value_results_previously_observed='exact overlaps in INPUTS.json; whole final corpus not run')
    with (ROOT/'MANIFEST.json').open('x') as f:json.dump(record,f,indent=2);f.write('\n')
    print(json.dumps(dict(manifest_sha256=sha(ROOT/'MANIFEST.json'),files=len(files),units=4232)))
if __name__=='__main__':main()
