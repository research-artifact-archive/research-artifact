"""Independent shape/coverage checks before historical Bellman identity checks.

Does not reconstruct curves or import their constructor. Expects JSON-reloaded
data. Strictly checks controller metadata used by the runtime as well as values.
"""
def integer(x):return type(x) is int

def check(data):
    assert data['schema']=='dag-retry-integer-curves-v1'
    assert data['route']=='ideal'
    case=data['input'];cp=case['cp'];n=len(cp)
    assert all(isinstance(row,list) and len(row)==2 and integer(row[0]) and row[0]>0 and integer(row[1]) and row[1]>=0 for row in cp)
    pred=[set() for _ in cp];seen=set()
    for edge in case['edges']:
        assert isinstance(edge,list) and len(edge)==2 and all(integer(j) and 0<=j<n for j in edge)
        a,b=edge;assert a!=b and (a,b) not in seen
        seen.add((a,b));pred[b].add(a)
    pending=set(range(n));done=set()
    while pending:
        ready={i for i in pending if pred[i]<=done};assert ready,'cycle'
        done|=ready;pending-=ready
    full=(1<<n)-1
    assert integer(data['full']) and data['full']==full
    masks={full};todo=[full]
    def available(mask):return [i for i in range(n) if mask>>i&1 and not any(mask>>a&1 for a in pred[i])]
    while todo:
        mask=todo.pop()
        for i in available(mask):
            child=mask^(1<<i)
            if child not in masks:masks.add(child);todo.append(child)
    assert set(data['curves'])=={str(m) for m in masks}
    assert set(data['actions'])=={str(m) for m in masks-{0}}
    assert integer(data['states']) and data['states']==len(masks)
    segments=0
    for mask in sorted(masks):
        profile=data['curves'][str(mask)]
        assert isinstance(profile,list) and profile
        assert all(isinstance(row,list) and len(row)==3 and all(integer(x) for x in row) for row in profile)
        assert profile[0][:2]==[0,0]
        assert all(x>=0 and value>=0 and slope>=0 for x,value,slope in profile)
        for (x,v,d),(y,w,e) in zip(profile,profile[1:]):
            assert x<y and d>e and v+(y-x)*d==w
        assert profile[-1][2]==0
        assert profile[-1][1]==sum(p for i,(c,p) in enumerate(cp) if mask>>i&1)
        if not mask:assert profile==[[0,0,0]]
        else:
            action=data['actions'][str(mask)];avail=available(mask)
            assert set(action)=={'available','fast'}
            assert isinstance(action['available'],list) and all(integer(i) for i in action['available'])
            assert action['available']==avail
            assert integer(action['fast']) and action['fast']==min(avail,key=lambda i:(cp[i][0],i))
        segments+=len(profile)
    assert integer(data['segments']) and data['segments']==segments
    assert integer(data['root_segments']) and data['root_segments']==len(data['curves'][str(full)])
    return dict(states=len(masks),segments=segments,complete_shape=True)
