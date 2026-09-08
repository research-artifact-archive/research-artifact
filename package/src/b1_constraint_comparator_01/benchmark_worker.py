from pathlib import Path
import hashlib, importlib.util, json, sys, time, traceback
ROOT=Path(__file__).resolve().parent
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);return obj

def main():
    start=time.perf_counter();method,src,dest=sys.argv[1:];out=Path(dest)
    try:
        case=json.loads(Path(src).read_text())['case']
        if method=='cp_sat':
            import comparator
            row=comparator.solve(case,seconds=4)
        elif method=='subset_dp':
            import certificate
            t=time.perf_counter();v,cert,states=certificate.subset_dp(case)
            row=dict(status='SUCCESS',value=v,certificate=cert,states=states,
                     solve_check_seconds=time.perf_counter()-t)
        elif method=='all_budget':
            import certificate
            hybrid=module('bench_hybrid',ROOT.parent/'dependency_hybrid_01/hybrid.py')
            packed=module('bench_packed',ROOT.parent/'dependency_hybrid_check_02/check.py')
            shape=module('bench_shape',ROOT.parent/'final_evaluation_dag_01/structure.py')
            bellman=module('bench_bellman',ROOT.parent/'dependency_curves_01/checker.py')
            t=time.perf_counter();data=hybrid.compile_case(case)
            encoded=json.dumps(data,sort_keys=True,separators=(',',':')).encode()
            (out/'controller.json').write_bytes(encoded)
            built=time.perf_counter()-t;t=time.perf_counter();loaded=json.loads(encoded)
            if data['route']=='ordered':report=packed.check(loaded)
            else:
                structure=shape.check(loaded);report=bellman.check(loaded);report['shape']=structure
            assert not report['violations'],report
            loaded=hybrid.load(loaded);value=hybrid.value(loaded,1)
            cert=[];state=0 if data['route']=='ordered' else loaded['full']
            for _ in case['cp']:
                i,mode=hybrid.choose(loaded,state,1);cert.append([i,'P' if mode=='protected' else 'F'])
                state=state+1 if data['route']=='ordered' else state^(1<<i)
            scan=certificate.scan(case,cert);assert scan['value']==value
            row=dict(status='SUCCESS',value=value,route=data['route'],certificate=cert,
                     all_budget_report=report,certificate_report=scan,
                     build_serialize_seconds=built,load_check_query_seconds=time.perf_counter()-t,
                     controller_bytes=len(encoded),controller_sha256=hashlib.sha256(encoded).hexdigest())
        else:raise ValueError(method)
    except AssertionError:row=dict(status='FAILURE',error=traceback.format_exc())
    except Exception:row=dict(status='INVALID',error=traceback.format_exc())
    row['cold_worker_seconds']=time.perf_counter()-start
    with (out/'RESULT.json').open('x') as f:json.dump(row,f,sort_keys=True);f.write('\n')

if __name__=='__main__':main()
