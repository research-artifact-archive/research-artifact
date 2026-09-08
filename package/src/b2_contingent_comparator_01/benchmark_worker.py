from pathlib import Path
import hashlib,importlib.util,json,sys,time,traceback
ROOT=Path(__file__).resolve().parent
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);return obj
def main():
    start=time.perf_counter();method,src,dest=sys.argv[1:];out=Path(dest)
    try:
        case=json.loads(Path(src).read_text())['case']
        if method=='cp_sat':
            import comparator
            row=comparator.solve(case,2,4)
            if 'artifact' in row:
                (out/'policy.json').write_text(json.dumps(row['artifact'],sort_keys=True,separators=(',',':'))+'\n')
        elif method=='screened_dp':
            import screened_dp,policy_checker
            row=screened_dp.solve(case,2);encoded=json.dumps(row['artifact'],sort_keys=True,separators=(',',':')).encode()
            (out/'policy.json').write_bytes(encoded);report=policy_checker.check(case,json.loads(encoded))
            assert report['value']==row['value'];row.update(artifact_bytes=len(encoded),certificate_report=report)
        elif method=='all_budget':
            import checker as contingent
            hybrid=module('b2bench_hybrid',ROOT.parent/'dependency_hybrid_01/hybrid.py')
            packed=module('b2bench_packed',ROOT.parent/'dependency_hybrid_check_02/check.py')
            shape=module('b2bench_shape',ROOT.parent/'final_evaluation_dag_01/structure.py')
            bellman=module('b2bench_bellman',ROOT.parent/'dependency_curves_01/checker.py')
            t=time.perf_counter();data=hybrid.compile_case(case);encoded=json.dumps(data,sort_keys=True,separators=(',',':')).encode();(out/'controller.json').write_bytes(encoded)
            built=time.perf_counter()-t;t=time.perf_counter();loaded=json.loads(encoded)
            if data['route']=='ordered':report=packed.check(loaded)
            else:
                structure=shape.check(loaded);report=bellman.check(loaded);report['shape']=structure
            assert not report['violations'],report
            loaded=hybrid.load(loaded);value=hybrid.value(loaded,2);n=len(case['cp'])
            def spine(state,b):
                result=[];before={}
                while state<n if data['route']=='ordered' else bool(state):
                    i,mode=hybrid.choose(loaded,state,b);before[i]=state;result.append([i,'P' if mode=='protected' else 'F'])
                    state=state+1 if data['route']=='ordered' else state^(1<<i)
                return result,before
            rs,states=spine(0 if data['route']=='ordered' else loaded['full'],2)
            policy=dict(schema='specified-budget-contingent-order-v1',budget=2,root=rs,branches={str(i):spine(states[i],1)[0] for i,mode in rs if mode=='F'})
            pe=json.dumps(policy,sort_keys=True,separators=(',',':')).encode();(out/'policy.json').write_bytes(pe)
            pr=contingent.check(case,json.loads(pe));assert pr['value']==value
            row=dict(status='SUCCESS',value=value,route=data['route'],all_budget_report=report,certificate_report=pr,
                     controller_bytes=len(encoded),controller_sha256=hashlib.sha256(encoded).hexdigest(),
                     artifact_bytes=len(pe),build_serialize_seconds=built,load_check_query_extract_seconds=time.perf_counter()-t)
        else:raise ValueError(method)
    except AssertionError:row=dict(status='FAILURE',error=traceback.format_exc())
    except Exception:row=dict(status='INVALID',error=traceback.format_exc())
    row['cold_worker_seconds']=time.perf_counter()-start
    with (out/'RESULT.json').open('x') as f:json.dump(row,f,sort_keys=True);f.write('\n')
if __name__=='__main__':main()
