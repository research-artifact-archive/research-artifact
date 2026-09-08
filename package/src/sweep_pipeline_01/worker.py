from pathlib import Path
import hashlib
import importlib.util
import json
import sys
import time
import traceback

ROOT=Path(__file__).resolve().parent
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);return obj

def main():
    start=time.perf_counter();src,dest=sys.argv[1:];out=Path(dest)
    try:
        assert __debug__;unit=json.loads(Path(src).read_text())
        hybrid=module('pipeline_hybrid',ROOT.parent/'dependency_hybrid_01/hybrid.py')
        packed=module('pipeline_packed',ROOT.parent/'dependency_hybrid_check_02/check.py')
        checker=module('pipeline_sweep',ROOT.parent/'sweep_certificate_02/certificate.py')
        imported=time.perf_counter()-start;t=time.perf_counter()
        data=hybrid.compile_case(unit['case'])
        encoded=json.dumps(data,sort_keys=True,separators=(',',':')).encode()
        (out/'artifact.json').write_bytes(encoded)
        built=time.perf_counter()-t;t=time.perf_counter()
        loaded=json.loads((out/'artifact.json').read_bytes())
        report=(packed if loaded['route']=='ordered' else checker).check(loaded)
        assert not report['violations'],report
        if loaded['route']=='ideal':assert report['directly_checked_stored_policy_attainment']
        parsed=hybrid.load(loaded);values=[hybrid.value(parsed,b) for b in unit['budgets']]
        row=dict(status='SUCCESS',values=values,certificate_report=report,
            artifact_bytes=len(encoded),artifact_sha256=hashlib.sha256(encoded).hexdigest(),
            import_input_seconds=imported,build_serialize_seconds=built,
            reload_check_query_seconds=time.perf_counter()-t,
            route=loaded['route'],scope='ALL_BUDGET_VALUES_AND_POLICY')
    except AssertionError:row=dict(status='FAILURE',error=traceback.format_exc())
    except Exception:row=dict(status='INVALID',error=traceback.format_exc())
    row['cold_worker_seconds']=time.perf_counter()-start
    with (out/'RESULT.json').open('x') as f:json.dump(row,f,sort_keys=True);f.write('\n')

if __name__=='__main__':main()
