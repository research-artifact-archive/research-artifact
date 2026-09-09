"""Experimental charged three-mode compiler; primitive normalization unproved."""
import importlib.util
from pathlib import Path

SOURCE=Path(__file__).resolve().parents[2]/'RESUMED_20260907_1942/dependency_curves_01/curves.py'
spec=importlib.util.spec_from_file_location('inherited_integer_curve_ops',SOURCE)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)


def prices(jobs):
    out=[]
    for w,p,g,v,r in jobs:
        assert w>0 and min(p,g,v,r)>=0
        m=min(v,g+r);d=g+r-m
        out.append((w+m,p+d,d,w+p))
    return out


def insert_slope(f,s):
    assert f[0][0:2] in [(0,0),[0,0]] and s>0
    runs=[(row[2],f[k+1][0]-row[0]) for k,row in enumerate(f[:-1])]
    result=[];inserted=False
    def append(slope,count):
        if result and result[-1][0]==slope:
            result[-1]=(slope,result[-1][1]+count)
        else:result.append((slope,count))
    for slope,count in runs:
        if not inserted and slope<s:append(s,1);inserted=True
        append(slope,count)
    if not inserted:append(s,1)
    profile=[];x=y=0
    for slope,count in result:
        profile.append((x,y,slope));x+=count;y+=slope*count
    profile.append((x,y,0))
    return profile


def compile_case(case):
    ps=prices(case['jobs']);n=len(ps);full=(1<<n)-1
    pred=[sum(1<<a for a,b in case['edges'] if b==j) for j in range(n)]
    assert len(set(map(tuple,case['edges'])))==len(case['edges'])
    states={full};pending=[full]
    while pending:
        s=pending.pop();available=base.available(s,pred)
        assert not s or available, 'cyclic dependency graph'
        for j in available:
            child=s^(1<<j)
            if child not in states:states.add(child);pending.append(child)
    curves={0:base.ZERO};actions={}
    for s in sorted(states-{0}):
        available=base.available(s,pred);fast=min(available,key=lambda j:(ps[j][0],j))
        h=None
        for j in available:
            c,p,d,insert=ps[j];f=curves[s^(1<<j)]
            for branch in [base.shift_value(f,p),base.shift_value(insert_slope(f,insert),d)]:
                h=branch if h is None else base.lower(h,branch)
        curve=base.lower(h,base.floor_slopes(curves[s^(1<<fast)],ps[fast][0]))
        assert curve[0][0:2]==(0,0) and curve[-1][2]==0
        assert all(a[2]>b[2]>=0 for a,b in zip(curve,curve[1:]))
        assert curve[-1][1]==sum(p for j,(c,p,d,t) in enumerate(ps) if s>>j&1)
        curves[s]=curve;actions[s]={'available':available,'fast':fast}
    return {'schema':'experimental-three-mode-curves-v1','input':case,'prices':ps,
            'curves':curves,'actions':actions,'full':full,'states':len(states),
            'baseline':sum(c for c,p,d,t in ps)}


def choose(compiled,s,b):
    profiles=compiled['curves'];ps=compiled['prices'];options=[]
    for j in compiled['actions'][s]['available']:
        c,p,d,t=ps[j];child=profiles[s^(1<<j)];normal=base.at(child,b)
        options.append((p+normal,j,'protected'))
        options.append((normal if b==0 else max(normal,c+base.at(profiles[s],b-1)),j,'fast'))
        options.append((d+normal if b==0 else max(d+normal,d+t+base.at(child,b-1)),j,'cached_callback'))
    return min(options)
