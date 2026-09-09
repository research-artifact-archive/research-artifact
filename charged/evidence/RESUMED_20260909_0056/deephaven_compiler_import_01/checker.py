"""Full Bellman identity on all integer budgets, from serialized curves only.

No imports from curve construction. Each interval is cut at every pairwise
affine crossing, including floor/ceiling integer neighbors. This checker and
the compiler share the input contract; they are not independent theorem proofs.
"""
import itertools

def value_slope(profile,b):
    selected=profile[0]
    for piece in profile:
        if piece[0]>b:break
        selected=piece
    start,value,slope=selected
    return value+(b-start)*slope,slope

def check(compiled):
    curves={int(k):v for k,v in compiled['curves'].items()}; case=compiled['input'];cp=case['cp']
    pred=[{a for a,b in case['edges'] if b==j} for j in range(len(cp))]
    violations=[]; interval_count=0; evaluation_count=0
    assert curves[0]==[[0,0,0]],curves[0]
    for s,profile in sorted(curves.items()):
        if not s:continue
        avail=[j for j in range(len(cp)) if s&(1<<j) and not any(s&(1<<a) for a in pred[j])]
        if value_slope(profile,0)[0]!=0:violations.append(dict(s=s,b=0,kind='zero boundary'))
        boundaries={1}
        for x,_,_ in profile:
            if x>=1:boundaries.add(x)
            boundaries.add(x+1)
        for j in avail:
            for x,_,_ in curves[s^(1<<j)]:
                if x>=1:boundaries.add(x)
        boundaries=sorted(boundaries)
        for index,lo in enumerate(boundaries):
            hi=boundaries[index+1] if index+1<len(boundaries) else None
            lines=[value_slope(profile,lo)]
            oldv,olds=value_slope(profile,lo-1)
            for j in avail:
                v,sl=value_slope(curves[s^(1<<j)],lo)
                lines.extend([(v+cp[j][1],sl),(v,sl),(oldv+cp[j][0],olds)])
            points={lo}
            if hi is not None:points.add(hi)
            else:assert all(slope==0 for _,slope in lines),('tail not constant',s,lines)
            for (u,du),(v,dv) in itertools.combinations(lines,2):
                if du==dv:continue
                # root b=lo+(v-u)/(du-dv), represented with exact integers.
                numerator=v-u; denominator=du-dv
                if denominator<0:numerator=-numerator;denominator=-denominator
                below=numerator//denominator
                above=-((-numerator)//denominator)
                for b in (lo+below,lo+above):
                    if b>=lo and (hi is None or b<=hi):points.add(b)
            for b in sorted(points):
                own=value_slope(profile,b)[0]; prior=value_slope(profile,b-1)[0]
                options=[]
                for j in avail:
                    child=value_slope(curves[s^(1<<j)],b)[0]
                    options.extend([cp[j][1]+child,max(child,cp[j][0]+prior)])
                exact=min(options)
                if own!=exact:violations.append(dict(s=s,b=b,value=own,bellman=exact,kind='identity'))
            interval_count+=1;evaluation_count+=len(points)
    return dict(violations=violations,checked_states=len(curves),intervals=interval_count,
                evaluated_integer_points=evaluation_count,domain='ALL_NONNEGATIVE_INTEGER_BUDGETS_BY_AFFINE_PARTITION')
