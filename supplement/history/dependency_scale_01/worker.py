import hashlib,json,pathlib,sys,time,traceback
ROOT=pathlib.Path(__file__).resolve().parent
SOURCE=ROOT.parent/'dependency_curves_01'
sys.path.insert(0,str(SOURCE))
import curves,checker

def fixed_profile(case,mode):
    pred=curves.predecessors(case);s=(1<<len(case['cp']))-1;order=[]
    while s:
        avail=curves.available(s,pred)
        i=min(avail,key=lambda j:(case['cp'][j][0],j)) if mode=='cheap' else min(avail)
        order.append(i);s^=1<<i
    f=curves.ZERO
    for j in reversed(order):
        c,p=case['cp'][j]
        f=curves.lower(curves.shift_value(f,p),curves.floor_slopes(f,c))
    return order,f

def diagnostics(case,root):
    cp=case['cp']; chunks=[]
    for c,p in cp:
        q,r=divmod(p,c)
        if q:chunks.append((c,q))
        if r:chunks.append((r,1))
    chunks.sort(reverse=True)
    orders={mode:fixed_profile(case,mode) for mode in ['cheap','index']}
    out=[]
    for b in case['budgets']:
        left=b;low=0
        for h,m in chunks:
            count=min(left,m);low+=h*count;left-=count
        high=min(sum(p for c,p in cp if c>t)+b*t for t in {0}|{c for c,p in cp})
        v=curves.at(root,b)
        fixed={mode:curves.at(f,b) for mode,(_,f) in orders.items()}
        assert low<=v<=high and all(v<=x for x in fixed.values()),(b,low,v,high,fixed)
        out.append(dict(b=b,value=v,allocation_lower=low,fixed_mode_upper=high,fixed_orders=fixed))
    return dict(values=out,orders={mode:o for mode,(o,_) in orders.items()})

def main():
    method,src,dest=sys.argv[1:];out=pathlib.Path(dest);start=time.perf_counter()
    try:
        if method=='compile':
            case=json.loads(pathlib.Path(src).read_text());compiled=curves.compile_case(case)
            data=json.dumps(compiled,sort_keys=True,separators=(',',':')).encode()
            with (out/'controller.json').open('xb') as f:f.write(data)
            built=time.perf_counter()-start
            root=compiled['curves'][compiled['full']];n=len(case['cp'])
            row=dict(status='SUCCESS',construction_serialization_seconds=built,states=compiled['states'],
                segments=compiled['segments'],root_segments=len(root),positive_root_runs=len(root)-1,
                controller_bytes=len(data),controller_sha256=hashlib.sha256(data).hexdigest(),
                H6='FAIL' if len(root)-1>2*n else 'PASS',root_profile=root,
                diagnostics=diagnostics(case,root))
        elif method=='check':
            data=pathlib.Path(src).read_bytes();compiled=json.loads(data);checked=checker.check(compiled)
            row=dict(status='FAILURE' if checked['violations'] else 'SUCCESS',symbolic=checked,
                controller_sha256=hashlib.sha256(data).hexdigest())
        else:raise ValueError(method)
    except Exception:row=dict(status='INVALID',error=traceback.format_exc())
    row['worker_seconds']=time.perf_counter()-start
    with (out/'RESULT.json').open('x') as f:json.dump(row,f,sort_keys=True);f.write('\n')

if __name__=='__main__':main()
