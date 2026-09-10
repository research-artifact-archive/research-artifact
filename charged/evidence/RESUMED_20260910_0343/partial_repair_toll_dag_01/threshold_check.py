"""Independent full-observation checker; does not import the constructor."""
from functools import lru_cache
from itertools import product

def check_certificate(c):
    assert c['schema']=='repair-toll-common-policy-v1'
    jobs=c['jobs'];n=len(jobs);r=c['retries'];k=c['toll'];full=(1<<n)-1
    assert isinstance(r,int) and r>=0 and k>0
    observations=[];sigmas=[];totals=[]
    for j in jobs:
        weights=j['weights'];fs=j['footprints'];m=len(weights)
        assert all(w>0 for w in weights) and all(0<f<(1<<m) for f in fs)
        unions={0:0}
        for count in range(1,m+1):
            for word in product(fs,repeat=count):
                union=0
                for f in word:union|=f
                unions.setdefault(union,count)
        obs=[dict(mask=d,c=count,w=sum(w for q,w in enumerate(weights) if d>>q&1)) for d,count in sorted(unions.items())]
        g=[max(o['w'] for o in obs if o['c']<=b) for b in range(m+1)]
        sigma=next(i for i,w in enumerate(g) if w==g[-1])
        assert obs==j['observations'] and g==j['G'] and sigma==j['sigma'] and g[-1]==j['W']
        observations.append(obs);sigmas.append(sigma);totals.append(g[-1])
    E=sum(sigmas)+r*max(sigmas)
    assert c['ceiling']==E and c['root']==[full,r,0]
    pred=[{a for a,b in c['edges'] if b==i} for i in range(n)]
    def ready(s):return [i for i in range(n) if s>>i&1 and not any(s>>a&1 for a in pred[i])]
    @lru_cache(None)
    def V(s,b,t):
        if not s:return 0
        options=[]
        for i in ready(s):
            environment=[]
            for o in observations[i]:
                if o['c']>b:continue
                choices=[o['w']+V(s&~(1<<i),b-o['c'],t)]
                if t:choices.append(V(s,b-o['c'],t-1))
                environment.append(k+min(choices))
            options.append(max(environment))
        return min(options)
    actual=[V(full,b,r) for b in range(E+2)]
    assert c['curve']==actual and actual[E]==actual[-1]==n*k+sum(totals)
    rows={tuple(row['state']):row for row in c['thresholds']}
    assert len(rows)==len(c['thresholds'])
    for (s,t,e),row in rows.items():
        assert 0<=s<=full and 0<=t<=r and 0<=e<=E
        if not s:
            assert row['value']==actual[e] and row['job'] is None
            continue
        candidates={}
        for i in ready(s):
            possibilities=[]
            for o in observations[i]:
                nxt=min(E,e+o['c'])
                accept=rows[s&~(1<<i),t,nxt]['value']-k-o['w']
                choices=[accept]
                if t:choices.append(rows[s,t-1,nxt]['value']-k)
                possibilities.append(max(choices))
            candidates[i]=min(possibilities)
        assert row['value']==max(candidates.values())
        assert row['job'] in candidates and candidates[row['job']]==row['value']
    margin=rows[full,r,0]['value']
    return dict(status='PASS',root_margin=margin,common_optimum_exists=margin>=0,checked_thresholds=len(rows),known_states=V.cache_info().currsize,full_observations=sum(len(x) for x in observations))
