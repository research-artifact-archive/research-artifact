import hashlib
import json
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def prefix_value(runs,b):
    total=0
    for height,count in runs:
        used=min(b,count);total+=height*used;b-=used
        if not b:break
    return total
def compile_controller(g):
    n=len(g['jobs']);order=sorted(range(n),key=lambda i:(g['jobs'][i][1],g['jobs'][i][0],i));thresholds=[0]*n;runs=[];length=0
    assert isinstance(g['budget'],int) and g['budget']>=0
    assert all(isinstance(p,int) and p>=0 and isinstance(c,int) and c>0 for p,c in g['jobs'])
    def append(height,count):
        nonlocal length
        if count==0:return
        assert height>0 and count>0
        if runs and runs[-1][0]==height:runs[-1][1]+=count
        else:
            assert not runs or runs[-1][0]>height
            runs.append([height,count])
        length+=count
    for k in range(n-1,-1,-1):
        p,c=g['jobs'][order[k]]
        if p==0:thresholds[k]=0;continue
        original_p=p
        if runs and runs[-1][0]<c:
            r,count=runs.pop();assert count==1;length-=1
            pay=min(p,c-r);append(r+pay,1);p-=pay
            if p==0:thresholds[k]=length;continue
        whole,rem=divmod(p,c);append(c,whole)
        if rem:append(rem,1)
        thresholds[k]=length
    base=sum(g['normal_costs'])
    return dict(schema='h16-threshold-cursor-v1',input_sha256=hashlib.sha256(canonical(g)).hexdigest(),order=order,protect_at_budget=thresholds,value_slopes=runs,normal_cost=base,value=base+prefix_value(runs,g['budget']),runtime_synthesis_calls=0)
