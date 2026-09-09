"""Version2: denominator-bucket search on monotone profiles; exact fallback."""
from bisect import bisect_right
from fractions import Fraction as F
from compact01 import feasible as linear_feasible
from compact01 import check_certificate as linear_check
from compact01 import ratio, policy_accept

def monotone_profile(H,G):
    return (len(H)==len(G) and bool(H) and H[0]==0 and
            all(isinstance(h,int) and h>=0 for h in H) and H==G and
            all(a<=b for a,b in zip(H,H[1:])))

def bucket_feasible(H,G,mu,q,R):
    # The caller has already validated H=G and monotonicity.
    assert q>=1 and R>=1
    e=0;path=[];p,d=R.numerator,R.denominator;m=len(H)-1
    for step in range(q):
        found=None
        for j in range(e//q,(e+m)//q+1):
            first=max(0,q*j-e);last=min(m,q*(j+1)-1-e)
            cutoff=(p*(mu+G[j]))//d-mu
            if H[last]<=cutoff:continue
            found=first if H[first]>cutoff else bisect_right(H,cutoff,first,last+1)
            assert first<=found<=last
            break
        if found is None:
            return True,path,dict(step=step,e=e,reason='all_observations_acceptable')
        k=found
        path.append(dict(step=step,e=e,k=k,numerator=mu+H[k],denominator=mu+G[(e+k)//q]))
        e+=k
    return False,path,dict(step=q,e=e,reason='q_unacceptable_observations')

def feasible(H,G,mu,q,R):
    return (bucket_feasible if monotone_profile(H,G) else linear_feasible)(H,G,mu,q,R)

def compile_profile(H,G,mu,q,total_work):
    assert mu>=0 and total_work>0 and len(H)==len(G)
    assert all(x is None or isinstance(x,int) and 0<=x<=total_work for x in H)
    decide=bucket_feasible if monotone_profile(H,G) else linear_feasible
    U=mu+total_work;lo=F(1);hi=F(U);calls=0
    ok,path,end=decide(H,G,mu,q,lo);calls+=1
    if ok:return dict(ratio=lo,upper_path=path,upper_end=end,lower_path=[],lower_kind='ratio_at_least_one',decisions=calls,bisections=0)
    ok,_,_=decide(H,G,mu,q,hi);calls+=1;assert ok
    lower_path=path;iterations=0
    while hi-lo>=F(1,U*U):
        mid=(hi+lo)/2;ok,path,_=decide(H,G,mu,q,mid);calls+=1;iterations+=1
        if ok:hi=mid
        else:lo=mid;lower_path=path
    finite=[r for x in lower_path if (r:=ratio(x['numerator'],x['denominator'])) is not None]
    assert finite
    best=min(finite);assert lo<best<=hi
    ok,upper_path,upper_end=decide(H,G,mu,q,best);calls+=1;assert ok
    return dict(ratio=best,upper_path=upper_path,upper_end=upper_end,lower_path=lower_path,lower_kind='complete_adversarial_path',decisions=calls,bisections=iterations,isolation_lower=lo,isolation_upper=hi,integer_bound=U)

def check_certificate(H,G,mu,q,total_work,result):
    if not monotone_profile(H,G):return linear_check(H,G,mu,q,total_work,result)
    assert q>=1 and mu>=0 and H[-1]<=total_work
    R=F(result['ratio']);assert R>=1
    if result['lower_kind']=='ratio_at_least_one':assert R==1 and result['lower_path']==[]
    else:
        assert result['lower_kind']=='complete_adversarial_path' and len(result['lower_path'])==q
        e=0;values=[]
        for step,x in enumerate(result['lower_path']):
            k=x['k'];assert isinstance(k,int) and 0<=k<len(H)
            assert x==dict(step=step,e=e,k=k,numerator=mu+H[k],denominator=mu+G[(e+k)//q])
            v=ratio(x['numerator'],x['denominator']);assert v is None or v>=R
            if v is not None:values.append(v)
            e+=k
        assert values and min(values)==R
    def prefix_acceptable(e,limit):
        # Every bucket's last numerator is its maximum. Do not use bisect,
        # integer cutoff division, or the compiler's endpoint decisions.
        at=0
        while at<=limit:
            j=(e+at)//q;last=min(limit,(j+1)*q-e-1)
            if not policy_accept(H[last],last,e,G,mu,q,R):return False
            at=last+1
        return True
    e=0
    assert len(result['upper_path'])<q
    for step,x in enumerate(result['upper_path']):
        k=x['k'];assert isinstance(k,int) and 0<=k<len(H)
        assert x==dict(step=step,e=e,k=k,numerator=mu+H[k],denominator=mu+G[(e+k)//q])
        assert not policy_accept(H[k],k,e,G,mu,q,R)
        assert prefix_acceptable(e,k-1)
        e+=k
    assert result['upper_end']==dict(step=len(result['upper_path']),e=e,reason='all_observations_acceptable')
    assert prefix_acceptable(e,len(H)-1)
    return True
