"""Exact Bellman checking on a finite affine partition; no compiler import."""
from bisect import bisect_right
from fractions import Fraction


def affine(profile,b):
    k=bisect_right([x for x,y,s in profile],b)-1
    x,y,s=profile[k]
    return s,y-s*x


def value(profile,b):
    s,k=affine(profile,b);return s*b+k


def check(data):
    jobs=data['input']['jobs'];edges=data['input']['edges'];n=len(jobs)
    assert n>0 and all(len(row)==5 for row in jobs)
    assert all(all(type(x)==int and x>=0 for x in row) and row[0]>0 for row in jobs)
    assert len(set(map(tuple,edges)))==len(edges)
    assert all(0<=i<n and 0<=j<n and i!=j for i,j in edges)
    full=(1<<n)-1;states={full};pending=[full];available={}
    while pending:
        mask=pending.pop()
        avail=[i for i in range(n) if mask>>i&1 and not any(t==i and mask>>h&1 for h,t in edges)]
        assert not mask or avail
        available[mask]=avail
        for i in avail:
            child=mask^(1<<i)
            if child not in states:states.add(child);pending.append(child)
    profiles={int(k):v for k,v in data['curves'].items()}
    assert set(profiles)==states and data['full']==full
    expected_prices=[]
    for w,p,g,v,r in jobs:
        m=min(v,g+r);d=g+r-m;expected_prices.append([w+m,p+d,d,w+p])
    assert [list(row) for row in data['prices']]==expected_prices, 'wrong declared prices'
    assert data['baseline']==sum(row[0] for row in expected_prices), 'wrong baseline'
    assert data['states']==len(states), 'wrong state count'
    encoded_actions={int(k):v for k,v in data['actions'].items()}
    assert set(encoded_actions)==states-{0}, 'wrong action states'
    for mask in states-{0}:
        assert encoded_actions[mask]['available']==available[mask], 'wrong available jobs'
        assert encoded_actions[mask]['fast']==min(available[mask],key=lambda i:(expected_prices[i][0],i)), 'wrong cheapest fast job'
    assert profiles[0] in [[(0,0,0)],[[0,0,0]]]
    for mask,f in profiles.items():
        assert f and f[0][0]==f[0][1]==0 and f[-1][2]==0
        assert all(len(row)==3 and all(type(x)==int and x>=0 for x in row) for row in f)
        for (x,y,s),(xx,yy,ss) in zip(f,f[1:]):
            assert x<xx and y+s*(xx-x)==yy and s>ss
    checks=0;intervals=0
    for mask in sorted(states-{0}):
        own=profiles[mask];bounds={1}
        for x,y,s in own:bounds.update([max(1,x),x+1])
        for i in available[mask]:
            for x,y,s in profiles[mask^(1<<i)]:bounds.update([max(1,x),x+1])
        bounds=sorted(bounds)
        for k,lo in enumerate(bounds):
            hi=bounds[k+1] if k+1<len(bounds) else None
            line_set={affine(own,lo)}
            for i in available[mask]:
                w,p,g,v,r=jobs[i];m=min(v,g+r);d=g+r-m;c=w+m
                child=profiles[mask^(1<<i)]
                slope,intercept=affine(child,lo)
                os,oi=affine(own,lo-1);cs,ci=affine(child,lo-1)
                line_set.update([(slope,intercept+p+d),(slope,intercept),
                                 (os,oi-os+c),(slope,intercept+d),
                                 (cs,ci-cs+d+w+p)])
            lines=sorted(line_set);points={lo}
            if hi is not None:points.add(hi-1)
            for j,(s,a) in enumerate(lines):
                for t,b in lines[j+1:]:
                    if s==t:continue
                    cross=Fraction(b-a,s-t)
                    floor=cross.numerator//cross.denominator
                    for candidate in [floor,floor+1]:
                        if candidate>=lo and (hi is None or candidate<hi):points.add(candidate)
            # Between these points every atomic affine ordering is fixed.
            for budget in sorted(points):
                options=[]
                for i in available[mask]:
                    w,p,g,v,r=jobs[i];m=min(v,g+r);d=g+r-m
                    child=profiles[mask^(1<<i)]
                    cv=value(child,budget)
                    options.extend([p+d+cv,max(cv,w+m+value(own,budget-1)),
                                    max(d+cv,d+w+p+value(child,budget-1))])
                assert value(own,budget)==min(options),('Bellman',mask,budget,value(own,budget),options)
                checks+=1
            if hi is None:assert all(s==0 for s,a in lines),'unbounded last piece must be constant'
            intervals+=1
    basis_checks=0
    if 'bases' in data:
        bases={int(k):{int(d):q for d,q in rows.items()} for k,rows in data['bases'].items()}
        assert set(bases)==states
        for mask,f in profiles.items():
            lines=bases[mask]
            permitted={0}|{d for j,row in enumerate(expected_prices) if mask>>j&1 for d in [row[0],row[3]]}
            assert set(lines)<=permitted and 0 in lines
            assert all(type(q)==int and q>=0 for q in lines.values())
            line_pairs=list(lines.items())
            for k,(lo,y,slope) in enumerate(f):
                hi=f[k+1][0] if k+1<len(f) else None
                all_lines=line_pairs+[(slope,y-slope*lo)]
                points={lo}
                if hi is not None:points.add(hi)
                for j,(s,a) in enumerate(all_lines):
                    for t,b in all_lines[j+1:]:
                        if s==t:continue
                        cross=Fraction(b-a,s-t);floor=cross.numerator//cross.denominator
                        for candidate in [floor,floor+1]:
                            if candidate>=lo and (hi is None or candidate<=hi):points.add(candidate)
                for b in points:
                    assert value(f,b)==min(d*b+q for d,q in lines.items()), ('basis mismatch',mask,b)
                    basis_checks+=1
    return {'states':len(states),'affine_intervals':intervals,'point_checks':checks,
            'basis_point_checks':basis_checks,'routing_prices_baseline_checked':True,
            'domain':'ALL_NONNEGATIVE_INTEGER_BUDGETS_BY_AFFINE_PARTITION',
            'compiler_imported':False}
