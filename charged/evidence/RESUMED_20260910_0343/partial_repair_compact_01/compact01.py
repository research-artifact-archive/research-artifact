"""Exact ratio synthesis after minimum-cover/weight profile construction.

No actual write budget enters the returned policy. Integer scaling is exact.
"""
from fractions import Fraction as F
from math import lcm

def scale(weights,mu):
    values=tuple(map(F,weights))+(F(mu),)
    assert values and all(x>0 for x in values[:-1]) and values[-1]>=0
    unit=lcm(*(x.denominator for x in values))
    return tuple(int(x*unit) for x in values[:-1]),int(values[-1]*unit),unit

def geometry(weights,footprints):
    m=len(weights);assert m>0 and footprints and all(0<f<(1<<m) for f in footprints)
    work={d:sum(w for i,w in enumerate(weights) if d>>i&1) for d in range(1<<m)}
    cover={0:0};frontier=[0];cost=0
    while frontier:
        cost+=1;nxt=sorted({d|f for d in frontier for f in footprints}-cover.keys())
        for d in nxt:cover[d]=cost
        frontier=nxt
    H=[None]*(m+1);witness=[None]*(m+1)
    for d,c in sorted(cover.items()):
        if H[c] is None or work[d]>H[c]:H[c]=work[d];witness[c]=d
    G=[];v=0
    for h in H:v=max(v,h or 0);G.append(v)
    return H,G,witness,cover,work

def singleton_profile(weights):
    ordered=sorted(enumerate(weights),key=lambda x:(-x[1],x[0]))
    H=[0]
    for _,w in ordered:H.append(H[-1]+w)
    return H,H[:],[i for i,_ in ordered]

def ratio(num,den):
    if den:return F(num,den)
    return F(1) if num==0 else None

def feasible(H,G,mu,q,R):
    """None ratio is positive/zero = infinity; all comparisons are exact."""
    assert q>=1 and R>=1 and H[0]==G[0]==0
    e=0;path=[];num,den=R.numerator,R.denominator
    for step in range(q):
        found=None
        for k,h in enumerate(H):
            if h is None:continue
            a=mu+h;b=mu+G[(e+k)//q]
            bad=(a*den>num*b) if b else (a>0 or F(1)>R)
            if bad:found=k;break
        if found is None:
            return True,path,dict(step=step,e=e,reason='all_observations_acceptable')
        k=found;a=mu+H[k];b=mu+G[(e+k)//q]
        path.append(dict(step=step,e=e,k=k,numerator=a,denominator=b))
        e+=k
    return False,path,dict(step=q,e=e,reason='q_unacceptable_observations')

def compile_profile(H,G,mu,q,total_work):
    assert mu>=0 and total_work>0 and len(H)==len(G)
    assert all(x is None or isinstance(x,int) and 0<=x<=total_work for x in H)
    U=mu+total_work;lo=F(1);hi=F(U);calls=0
    ok,path,end=feasible(H,G,mu,q,lo);calls+=1
    if ok:return dict(ratio=lo,upper_path=path,upper_end=end,lower_path=[],lower_kind='ratio_at_least_one',decisions=calls,bisections=0)
    ok,_,_=feasible(H,G,mu,q,hi);calls+=1;assert ok
    lower_path=path;iterations=0
    while hi-lo>=F(1,U*U):
        mid=(hi+lo)/2;ok,path,_=feasible(H,G,mu,q,mid);calls+=1;iterations+=1
        if ok:hi=mid
        else:lo=mid;lower_path=path
    candidates=[ratio(x['numerator'],x['denominator']) for x in lower_path]
    finite=[x for x in candidates if x is not None];assert finite
    best=min(finite);assert lo<best<=hi
    ok,upper_path,upper_end=feasible(H,G,mu,q,best);calls+=1;assert ok
    return dict(ratio=best,upper_path=upper_path,upper_end=upper_end,lower_path=lower_path,lower_kind='complete_adversarial_path',decisions=calls,bisections=iterations,isolation_lower=lo,isolation_upper=hi,integer_bound=U)

def policy_accept(weight,least_cost,e,G,mu,q,R):
    b=mu+G[(e+least_cost)//q];a=mu+weight
    return a*R.denominator<=R.numerator*b if b else (a==0 and R>=1)

def check_certificate(H,G,mu,q,total_work,result):
    """Recompute both certificate paths from the supplied input profile."""
    assert len(H)==len(G) and H[0]==0 and G[0]==0
    maximum=0
    for h,g in zip(H,G):
        if h is not None:assert 0<=h<=total_work;maximum=max(maximum,h)
        assert g==maximum
    R=F(result['ratio']);assert R>=1
    if result['lower_kind']=='ratio_at_least_one':assert R==1 and result['lower_path']==[]
    else:
        assert result['lower_kind']=='complete_adversarial_path' and len(result['lower_path'])==q
        e=0;values=[]
        for step,x in enumerate(result['lower_path']):
            k=x['k'];assert 0<=k<len(H) and H[k] is not None
            assert x==dict(step=step,e=e,k=k,numerator=mu+H[k],denominator=mu+G[(e+k)//q])
            value=ratio(x['numerator'],x['denominator']);assert value is None or value>=R
            if value is not None:values.append(value)
            e+=k
        assert values and min(values)==R
    # Upper path must follow the smallest available violating cost, then stop.
    e=0
    for step,x in enumerate(result['upper_path']):
        k=x['k'];assert x==dict(step=step,e=e,k=k,numerator=mu+H[k],denominator=mu+G[(e+k)//q])
        assert not policy_accept(H[k],k,e,G,mu,q,R)
        assert all(policy_accept(h,j,e,G,mu,q,R) for j,h in enumerate(H[:k]) if h is not None)
        e+=k
    assert len(result['upper_path'])<q
    assert result['upper_end']==dict(step=len(result['upper_path']),e=e,reason='all_observations_acceptable')
    assert all(policy_accept(h,k,e,G,mu,q,R) for k,h in enumerate(H) if h is not None)
    return True
