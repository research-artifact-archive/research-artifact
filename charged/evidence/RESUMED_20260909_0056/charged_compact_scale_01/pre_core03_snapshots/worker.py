"""Five fixed services, including their full cold serialization/check/query path."""
from pathlib import Path
from bisect import bisect_right
import json,platform,resource,sys,time,traceback

HERE=Path(__file__).resolve().parent
CORE=HERE.parent/'charged_compact_02'

def bind_certificate(method,decoded,case,budgets):
    assert decoded['input']==case,'certificate input differs'
    if method=='PEAK':assert decoded['budgets']==budgets,'budget order differs'

def main(method,input_path,output_path):
    start=time.perf_counter();out=Path(output_path);phases={}
    result=dict(status='FAILURE',method=method,phases=phases)
    try:
        assert __debug__
        if hasattr(sys,'set_int_max_str_digits'):sys.set_int_max_str_digits(0)
        unit=json.loads(Path(input_path).read_text());assert unit['method']==method
        case,budgets=unit['case'],unit['budgets'];n=len(case['jobs'])
        sys.setrecursionlimit(max(10000,4*n+2000))
        phases['input']=time.perf_counter()-start;before=time.perf_counter()
        if method in ('PACK','ALL','ROOT'):
            sys.path.insert(0,str(CORE));import compact,verify
            from runtime import Policy
            phases['method_import']=time.perf_counter()-before;before=time.perf_counter()
            if method=='ROOT':
                jobs,edges=compact.validate(case)
                assert all(p==0 or v>=g+r for w,p,g,v,r in jobs)
                effective=dict(cp=[[w+min(v,g+r) if v<g+r else min(w+g+r,w+p),p+max(0,g+r-v)] for w,p,g,v,r in jobs],edges=edges)
                order=compact.packing.order_if_compatible(effective);assert order is not None
                packed=compact.packing.pack(effective,order)
                artifact=dict(schema='charged-reduced-root-value-only-v1',input=case,baseline=sum(w+min(v,g+r) for w,p,g,v,r in jobs),value_slopes=packed['value_slopes'])
            else:artifact=compact.compile_case(case,force_general=method=='ALL')
            phases['construct']=time.perf_counter()-before;before=time.perf_counter()
            text=json.dumps(artifact,separators=(',',':'));(out/'ARTIFACT.json').write_text(text)
            phases['serialize_write']=time.perf_counter()-before;before=time.perf_counter()
            decoded=verify.loads((out/'ARTIFACT.json').read_text());bind_certificate(method,decoded,case,budgets)
            phases['read_parse']=time.perf_counter()-before;before=time.perf_counter()
            if method=='ROOT':
                ends=[];areas=[];heights=[];length=area=0
                for height,count in decoded['value_slopes']:
                    length+=count;area+=height*count;ends.append(length);areas.append(area);heights.append(height)
                def root(b):
                    i=bisect_right(ends,b)
                    if i==len(ends):return area
                    return (areas[i-1] if i else 0)+heights[i]*(b-(ends[i-1] if i else 0))
                phases['index']=time.perf_counter()-before;before=time.perf_counter()
                values=[root(b) for b in budgets]
                result.update(check=None,stats=dict(root_runs=len(heights)),certificate_scope='REDUCTION_AWARE_ALL_BUDGET_ROOT_VALUE_ONLY_NO_INDEPENDENT_CERTIFICATE')
            else:
                policy=Policy(decoded,case)
                phases['check_and_runtime_index']=time.perf_counter()-before;before=time.perf_counter()
                values=[policy.excess(b) for b in budgets];actions=[policy.choose(b) for b in budgets]
                inner=decoded['backend']
                stats=dict(route=policy.route)
                if method=='PACK':stats.update(cursor_states=n+1,root_runs=len(inner['value_slopes']))
                else:stats.update(states=inner['states'],profile_rows=sum(len(f) for f in inner['curves'].values()),basis_lines=sum(len(b) for b in inner['bases'].values()))
                result.update(check=policy.receipt,stats=stats,initial_actions=actions,certificate_scope='ALL_BUDGET_ORIGINAL_CHARGED_CURSOR_POLICY' if method=='PACK' else 'ALL_BUDGET_ALL_REACHABLE_UNFINISHED_SETS_POLICY')
            phases['query']=time.perf_counter()-before
            result.update(values=values,certificate_bytes=len(text.encode()))
        elif method=='PEAK':
            import oracle,point_checker
            phases['method_import']=time.perf_counter()-before;before=time.perf_counter()
            solved=oracle.solve_many(case,budgets)
            phases['construct']=time.perf_counter()-before;before=time.perf_counter()
            text=json.dumps(solved['artifact'],separators=(',',':'));(out/'ARTIFACT.json').write_text(text)
            phases['serialize_write']=time.perf_counter()-before;before=time.perf_counter()
            decoded=json.loads((out/'ARTIFACT.json').read_text());bind_certificate(method,decoded,case,budgets)
            phases['read_parse']=time.perf_counter()-before;before=time.perf_counter()
            checked=point_checker.check(decoded)
            phases['certificate_check']=time.perf_counter()-before;before=time.perf_counter()
            values=list(decoded['values']);phases['query']=time.perf_counter()-before
            result.update(values=values,certificate_bytes=len(text.encode()),check=checked,stats=solved['stats'],certificate_scope='REQUESTED_ROOT_VALUES')
        else:
            assert method=='DP';import direct
            phases['method_import']=time.perf_counter()-before;before=time.perf_counter()
            solved=direct.solve_many(case,budgets)
            phases['construct']=time.perf_counter()-before;before=time.perf_counter()
            text=json.dumps(solved,separators=(',',':'));(out/'VALUES.json').write_text(text)
            phases['serialize_write']=time.perf_counter()-before;before=time.perf_counter()
            decoded=json.loads((out/'VALUES.json').read_text());phases['read_parse']=time.perf_counter()-before
            result.update(values=decoded['values'],certificate_bytes=len(text.encode()),stats=decoded['stats'],certificate_scope=decoded['certificate_scope'])
        result.update(status='SUCCESS',budgets=budgets,baseline=sum(w+min(v,g+r) for w,p,g,v,r in case['jobs']))
    except Exception:result.update(status='FAILURE',error=traceback.format_exc())
    maximum=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    result.update(internal_seconds=time.perf_counter()-start,process_peak_rss_bytes=maximum if platform.system()=='Darwin' else 1024*maximum)
    with (out/'RESULT.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:result[k] for k in ('status','method','internal_seconds')}))
    if result['status']!='SUCCESS':raise SystemExit(1)

if __name__=='__main__':main(*sys.argv[1:])
