"""Exact additive-excess synthesis relative to a supplied correct profile."""

def feasible(H,G,q,delta):
    e=0;path=[]
    for step in range(q):
        k=next((k for k,h in enumerate(H) if h is not None and h-G[(e+k)//q]>delta),None)
        if k is None:return True,path,dict(step=step,e=e)
        path.append(dict(step=step,e=e,k=k,excess=H[k]-G[(e+k)//q]))
        e+=k
    return False,path,dict(step=q,e=e)

def compile_profile(H,G,q,W):
    assert q>=1 and H[0]==G[0]==0 and W>0
    lo=-1;hi=W;calls=0
    ok,lower,_=feasible(H,G,q,lo);assert not ok;calls+=1
    ok,_,_=feasible(H,G,q,hi);assert ok;calls+=1
    while hi-lo>1:
        mid=(lo+hi)//2;ok,path,_=feasible(H,G,q,mid);calls+=1
        if ok:hi=mid
        else:lo=mid;lower=path
    ok,upper,end=feasible(H,G,q,hi);calls+=1;assert ok
    return dict(delta=hi,lower_path=lower,upper_path=upper,upper_end=end,decisions=calls)

def check_certificate(H,G,q,W,result):
    assert q>=1 and W>0 and len(H)==len(G) and H[0]==G[0]==0
    maximum=0
    for h,g in zip(H,G):
        if h is not None:assert isinstance(h,int) and 0<=h<=W;maximum=max(maximum,h)
        assert g==maximum
    delta=result['delta'];assert isinstance(delta,int) and 0<=delta<=W
    assert len(result['lower_path'])==q
    e=0;values=[]
    for step,x in enumerate(result['lower_path']):
        k=x['k'];assert 0<=k<len(H) and H[k] is not None
        v=H[k]-G[(e+k)//q]
        assert x==dict(step=step,e=e,k=k,excess=v) and v>=delta
        values.append(v);e+=k
    assert min(values)==delta
    assert len(result['upper_path'])<q;e=0
    for step,x in enumerate(result['upper_path']):
        k=x['k'];assert 0<=k<len(H) and H[k] is not None
        v=H[k]-G[(e+k)//q]
        assert x==dict(step=step,e=e,k=k,excess=v) and v>delta
        assert all(h-G[(e+j)//q]<=delta for j,h in enumerate(H[:k]) if h is not None)
        e+=k
    assert result['upper_end']==dict(step=len(result['upper_path']),e=e)
    assert all(h-G[(e+k)//q]<=delta for k,h in enumerate(H) if h is not None)
    return True
