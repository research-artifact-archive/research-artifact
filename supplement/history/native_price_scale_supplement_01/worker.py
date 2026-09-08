import importlib.util,json,resource,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'native_price_scale_01'
spec=importlib.util.spec_from_file_location('prior_scale_worker',OLD/'worker.py')
prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
COMP=prior.COMP
SCREEN=prior.SCREEN

def solve(g):
    if all(p%c==0 for p,c in g['jobs']):
        bound=prior.module(SCREEN,'divisible_bounds').bounds(g)
        return dict(value=sum(g['normal_costs'])+bound['allocation_lower'],divisible_shortcut=True,bellman_cells=0,bound_cells=0)
    return dict(prior.ordered(g,True),divisible_shortcut=False)

def main():
    method,source,dest=sys.argv[1:];start=time.perf_counter();g=json.loads(Path(source).read_text());out=Path(dest)
    row=dict(method=method,status='SUCCESS',controller_output=False)
    try:row.update(solve(g))
    except Exception as e:row.update(status='INVALID',error=repr(e))
    row.update(worker_seconds=time.perf_counter()-start,peak_rss_native=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,peak_rss_units='bytes' if sys.platform=='darwin' else 'KiB')
    (out/'RESULT.json').write_text(json.dumps(row,sort_keys=True)+'\n');print(json.dumps(row,sort_keys=True))
if __name__=='__main__':main()
