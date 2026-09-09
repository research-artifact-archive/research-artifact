"""Inherited immutable-value/cost checks, with an explicit policy-oracle parameter."""
def signed(n):return (n+2**31)%2**32-2**31
def fold(a):
    s=0
    for x in a:s=signed(31*s+x)
    return s

def verify_run(case,run,row,oracle):
    assert row['status']=='SUCCESS',row['status']
    n=len(case['jobs']);pred=[{a for a,b in case['edges'] if b==i} for i in range(n)]
    values={};done={};epochs=set();protect=[0]*n;kernel_count=[0]*n;work=0
    for event in row['events']:
        kind=event['kind'];i=event['job'];ident=event['id'];assert 0<=i<n
        if kind=='D':
            assert i not in done and pred[i]<=done.keys() and ident in values
            assert values[ident]['job']==i and values[ident]['kind']=='K'
            done[i]=ident;continue
        assert ident not in values
        if kind=='I':
            length=8*case['jobs'][i][0]-len(pred[i]);a=[17*(i+1)+31*k for k in range(length)];bg=0
        else:
            src=values[event['source']];assert src['job']==i
            if kind=='B':
                a=[signed(3*x+7) for x in src['a']];bg=src['bg']+1;assert event['epoch']==bg
                assert (i,bg) not in epochs;epochs.add((i,bg))
            elif kind=='K':
                assert pred[i]<=done.keys();parents=event['parents'];assert len(parents)==n
                parent=0
                for j in range(n):
                    if j in pred[i]:
                        assert parents[j]==done[j],('captured parent',i,j,parents[j],done[j])
                        parent=signed(31*parent+values[parents[j]]['seed'])
                    else:assert parents[j]==-1
                a=[signed(1664525*x+1013904223+parent) for x in src['a']];bg=src['bg'];work+=len(pred[i])+len(a)
                protect[i]+=int(event['inside']);kernel_count[i]+=1
            else:raise AssertionError(('event kind',kind))
        seed=fold(a);assert seed==event['seed'],('wrong value',kind,i,ident)
        values[ident]={'a':a,'seed':seed,'bg':bg,'job':i,'kind':kind}
    assert len(done)==n and row['completed']==[done[i] for i in range(n)]
    assert all(ident in values and values[ident]['job']==i for i,ident in enumerate(row['live']))
    assert row['writes']==len(epochs)<=run['budget']
    if run['kind']=='concurrent':assert row['writes']==run['budget']
    failures=[tuple(x) for x in row['failures']]
    assert len(failures)==len(set(failures)) and set(failures)<=epochs
    callbacks=[0]*n;conditionals=[0]*n;expected_kernels=[0]*n;expected_protected=[0]*n
    mask=(1<<n)-1;b=run['budget'];allowance=int(case['policy'].split('-')[1]);f,choose,paths=oracle(case)
    for a in row['trace']:
        si,act=a.split(':');i=int(si);j,mode=choose(mask,allowance);assert i==j
        w,p,g,v,r=case['jobs'][i]
        if act=='P':
            assert mode==2;callbacks[i]+=1;expected_kernels[i]+=1;expected_protected[i]+=1;mask^=1<<i
        else:
            code,outcome=act;assert code==('C' if mode==0 else ('V' if v<=g+r else 'A'))
            assert outcome in ['S','F'];expected_kernels[i]+=1
            if code=='V':conditionals[i]+=1
            else:callbacks[i]+=1
            if outcome=='F':
                assert b>0;b-=1
                if code=='C':expected_kernels[i]+=1;expected_protected[i]+=1
                else:allowance-=1;assert allowance>=0
            if outcome=='S' or code=='C':mask^=1<<i
    assert mask==0 and len(failures)==run['budget']-b
    assert kernel_count==expected_kernels and protect==expected_protected
    assert row['work']==work and row['protected_calls']==protect and row['callbacks']==callbacks and row['conditionals']==conditionals
    cost=work+8*sum(p*protect[i]+(g+r)*callbacks[i]+v*conditionals[i] for i,(w,p,g,v,r) in enumerate(case['jobs']))
    assert row['cost']==cost,('fee accounting',row['cost'],cost)
    ceiling=8*(sum(w+min(v,g+r) for w,p,g,v,r in case['jobs'])+f((1<<n)-1,run['budget'],int(case['policy'].split('-')[1])))
    assert row['ceiling']==ceiling and cost<=ceiling,('bound',cost,ceiling)
    if 'expected_trace' in run:assert row['trace']==run['expected_trace'] and cost==run['expected_cost']
    return {'cost':cost,'ceiling':ceiling,'failures':len(failures),'writes':row['writes'],'kernel_calls':sum(kernel_count)}
