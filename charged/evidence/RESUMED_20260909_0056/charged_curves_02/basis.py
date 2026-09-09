"""Candidate finite input-slope basis for the charged three-mode game."""
import compiler


def envelope(lines):
    result=None
    for slope,intercept in sorted(lines.items(),reverse=True):
        line=[(0,intercept,slope)]
        result=line if result is None else compiler.base.lower(result,line)
    return result


def merge(*bases):
    result={}
    for basis in bases:
        for d,q in basis.items():result[d]=min(result.get(d,q),q)
    return result


def contact(f,s):
    assert s>0 and f[-1][2]==0
    return max(y-s*x for x,y,d in f)


def insert(lines,f,s):
    shifted={d:q+max(0,s-d) for d,q in lines.items()}
    return merge(shifted,{s:contact(f,s)})


def floor(lines,f,c):
    return merge({d:q for d,q in lines.items() if d>c},{c:contact(f,c)})


def compile_case(case):
    ps=compiler.prices(case['jobs']);n=len(ps);full=(1<<n)-1
    pred=[sum(1<<a for a,b in case['edges'] if b==j) for j in range(n)]
    states={full};pending=[full]
    while pending:
        s=pending.pop();available=compiler.base.available(s,pred)
        assert not s or available
        for i in available:
            child=s^(1<<i)
            if child not in states:states.add(child);pending.append(child)
    curves={0:[(0,0,0)]};bases={0:{0:0}};actions={}
    for mask in sorted(states-{0}):
        available=compiler.base.available(mask,pred);fast=min(available,key=lambda i:(ps[i][0],i))
        clauses=[]
        for i in available:
            c,p,d,s=ps[i];child=mask^(1<<i)
            clauses.append({slope:q+p for slope,q in bases[child].items()})
            clauses.append({slope:q+d for slope,q in insert(bases[child],curves[child],s).items()})
        child=mask^(1<<fast)
        clauses.append(floor(bases[child],curves[child],ps[fast][0]))
        own=merge(*clauses);f=envelope(own)
        permitted={0}|{v for j,(c,p,d,s) in enumerate(ps) if mask>>j&1 for v in [c,s]}
        assert set(own)<=permitted
        assert f[0][0:2]==(0,0) and f[-1][2]==0
        assert f[-1][1]==sum(p for j,(c,p,d,s) in enumerate(ps) if mask>>j&1)
        assert len(f)-1<=2*(len(permitted)-1)
        bases[mask]=own;curves[mask]=f;actions[mask]={'available':available,'fast':fast}
    return {'schema':'experimental-three-mode-input-slope-basis-v1','input':case,
            'prices':ps,'curves':curves,'bases':bases,'actions':actions,'full':full,
            'states':len(states),'baseline':sum(c for c,p,d,s in ps)}
