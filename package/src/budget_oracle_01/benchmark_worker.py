"""One cold six-budget workload; outputs have explicitly different scopes."""
from pathlib import Path
import hashlib,importlib.util,json,sys,time,traceback
ROOT=Path(__file__).resolve().parent
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);return obj
def main():
    start=time.perf_counter();method,src,dest=sys.argv[1:];out=Path(dest)
    try:
        assert __debug__;unit=json.loads(Path(src).read_text());case=unit['case'];budgets=unit['budgets']
        if method=='requested_values':
            oracle=module('bench_requested_oracle',ROOT/'oracle_session_hardened.py')
            checker=module('bench_requested_checker',ROOT/'values_certificate_hardened.py')
            t=time.perf_counter();solved=oracle.solve_many(case,budgets);data=solved['artifact']
        elif method=='all_budget':
            hybrid=module('bench_allbudget_hybrid',ROOT.parent/'dependency_hybrid_01/hybrid.py')
            packed=module('bench_allbudget_packed',ROOT.parent/'dependency_hybrid_check_02/check.py')
            shape=module('bench_allbudget_shape',ROOT.parent/'final_evaluation_dag_01/structure.py')
            bellman=module('bench_allbudget_bellman',ROOT.parent/'dependency_curves_01/checker.py')
            t=time.perf_counter();data=hybrid.compile_case(case)
        else:raise ValueError(method)
        encoded=json.dumps(data,sort_keys=True,separators=(',',':')).encode();(out/'artifact.json').write_bytes(encoded)
        built=time.perf_counter()-t;t=time.perf_counter();loaded=json.loads((out/'artifact.json').read_bytes())
        if method=='requested_values':
            report=checker.check(loaded);values=report['values'];assert values==solved['values']
            extra=dict(stats=solved['stats'],query_stats=solved['query_stats'],scope='REQUESTED_ROOT_VALUES')
        else:
            if loaded['route']=='ordered':report=packed.check(loaded)
            else:
                structure=shape.check(loaded);report=bellman.check(loaded);report['shape']=structure
            assert not report['violations'],report
            loaded=hybrid.load(loaded);values=[hybrid.value(loaded,b) for b in budgets]
            extra=dict(route=loaded['route'],scope='ALL_BUDGET_VALUES_AND_POLICY')
        row=dict(status='SUCCESS',values=values,certificate_report=report,artifact_bytes=len(encoded),artifact_sha256=hashlib.sha256(encoded).hexdigest(),
                 build_serialize_seconds=built,reload_check_query_seconds=time.perf_counter()-t,**extra)
    except AssertionError:row=dict(status='FAILURE',error=traceback.format_exc())
    except Exception:row=dict(status='INVALID',error=traceback.format_exc())
    row['cold_worker_seconds']=time.perf_counter()-start
    with (out/'RESULT.json').open('x') as f:json.dump(row,f,sort_keys=True);f.write('\n')
if __name__=='__main__':main()
