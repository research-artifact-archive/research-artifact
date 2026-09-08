"""Exact integer-domain piecewise-affine DAG retry curves.

Profile entry (start, value_at_start, slope_after_start); infinite final segment.
The solver does not loop over budgets or expand slope multiplicities.
"""
from bisect import bisect_right

ZERO = [(0, 0, 0)]

def at(profile, x):
    k=bisect_right([r[0] for r in profile],x)-1
    start,value,slope=profile[k]
    return value+(x-start)*slope

def line_at(profile, x):
    k=bisect_right([r[0] for r in profile],x)-1
    a,v,s=profile[k]
    return v+(x-a)*s,s

def normalize(points, values, tail_slope):
    out=[]
    for k,x in enumerate(points):
        if k+1<len(points):
            width=points[k+1]-x; rise=values[k+1]-values[k]
            assert rise%width==0,(points,values,k)
            slope=rise//width
        else: slope=tail_slope
        if not out or slope!=out[-1][2]: out.append((x,values[k],slope))
    return out

def lower(f,g):
    bounds=sorted({r[0] for r in f}|{r[0] for r in g})
    points=set(bounds)
    for k,lo in enumerate(bounds):
        hi=bounds[k+1] if k+1<len(bounds) else None
        fv,fs=line_at(f,lo); gv,gs=line_at(g,lo)
        difference=fv-gv; slope_difference=fs-gs
        if slope_difference:
            q,rem=divmod(-difference,slope_difference)
            for crossing in {lo+q,lo+q+(rem!=0)}:
                if crossing>=lo and (hi is None or crossing<=hi): points.add(crossing)
    points=sorted(points)
    values=[min(at(f,x),at(g,x)) for x in points]
    return normalize(points,values,min(f[-1][2],g[-1][2]))

def shift_value(f,p): return [(x,v+p,s) for x,v,s in f]

def floor_slopes(f,c):
    result=[]
    for x,v,s in f:
        if s>c: result.append((x,v,s))
        else:
            result.append((x,v,c))
            return result
    raise AssertionError('finite input must have constant tail')

def predecessors(case):
    return [sum(1<<a for a,b in case['edges'] if b==j) for j in range(len(case['cp']))]

def available(s,pred):
    return [j for j,p in enumerate(pred) if s>>j&1 and not p&s]

def compile_case(case):
    cp=case['cp']; n=len(cp); pred=predecessors(case); full=(1<<n)-1
    states={full}; pending=[full]
    while pending:
        s=pending.pop()
        for j in available(s,pred):
            child=s^(1<<j)
            if child not in states: states.add(child); pending.append(child)
    curves={0:ZERO}; actions={}
    for s in sorted(states-{0}):
        avail=available(s,pred); i=min(avail,key=lambda j:(cp[j][0],j))
        protected=None
        for j in avail:
            branch=shift_value(curves[s^(1<<j)],cp[j][1])
            protected=branch if protected is None else lower(protected,branch)
        d=floor_slopes(curves[s^(1<<i)],cp[i][0])
        v=lower(protected,d)
        assert v[0][0:2]==(0,0) and v[-1][2]==0
        assert all(slope>=0 for _,_,slope in v)
        assert all(a[2]>b[2] for a,b in zip(v,v[1:]))
        assert v[-1][1]==sum(p for j,(c,p) in enumerate(cp) if s>>j&1)
        curves[s]=v; actions[s]=dict(available=avail,fast=i)
    return dict(schema='dag-retry-integer-curves-v1',input=case,curves=curves,actions=actions,
                full=full,states=len(states),segments=sum(len(f) for f in curves.values()),
                root_segments=len(curves[full]))

def choose(compiled,s,b):
    curves=compiled['curves'];cp=compiled['input']['cp'];action=compiled['actions'][s]
    j=min(action['available'],key=lambda j:(cp[j][1]+at(curves[s^(1<<j)],b),j))
    protected=cp[j][1]+at(curves[s^(1<<j)],b)
    if protected==at(curves[s],b):return j,'protected'
    return action['fast'],'fast'
