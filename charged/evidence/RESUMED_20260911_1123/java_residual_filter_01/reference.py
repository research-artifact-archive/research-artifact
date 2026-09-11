"""Independent author-side direct-sort / operational reference, not Java ports.

No imports from the predecessor Python filter. Python integers compute exact
sums; only the explicitly declared Java representability boundary is simulated.
"""
MAX=(1<<63)-1
class BadInput(Exception): pass
class Overflow(Exception): pass

def exact(x):
    if not 0<=x<=MAX: raise Overflow()
    return x

def top(d,k): return sum(sorted(d,reverse=True)[:min(k,len(d))])

def weight(w):
    if w<=0: raise BadInput()

class Reference:
    def __init__(self,d=(),k=0,ell=0):
        if k<0 or ell<0: raise BadInput()
        self.d=[];self.k=k;self.ell=0
        for w in d:
            weight(w);exact(top(self.d+[w],k));self.d.append(w)
        if ell>top(self.d,k): raise BadInput()
        self.ell=ell
    def state(self):
        return dict(k=self.k,ell=self.ell,topSum=top(self.d,self.k),completed=len(self.d),
                    kth=sorted(self.d,reverse=True)[self.k-1] if 0<self.k<=len(self.d) else None)
    def query(self,w):
        weight(w)
        newell=exact(self.ell+w)
        return newell<=exact(top(self.d+[w],self.k))
    def update(self,w,op):
        weight(w)
        if op not in ('MATCH','MISMATCH','FRESH'): raise BadInput()
        nk=exact(self.k+1) if op=='MISMATCH' else self.k
        ne=self.ell if op=='MATCH' else exact(self.ell+w)
        nt=exact(top(self.d+[w],nk))
        if ne>nt: raise BadInput()
        self.d.append(w);self.k=nk;self.ell=ne

def filter_case(c):
    events=[];ce='';ref=None
    try: ref=Reference(c['d'],c['k'],c['ell'])
    except (BadInput,Overflow) as e: ce='ArithmeticException' if isinstance(e,Overflow) else 'IllegalArgumentException'
    if ref is not None:
        for op,w in c['ops']:
            before=ref.state();error='';result=None
            try:
                if op=='Q': result=ref.query(w)
                else: ref.update(w,op)
            except (BadInput,Overflow) as e: error='ArithmeticException' if isinstance(e,Overflow) else 'IllegalArgumentException'
            events.append(dict(op=op,weight=w,before=before,result=result,error=error,after=ref.state()))
    return dict(id=c['id'],constructorError=ce,events=events,final=ref.state() if ref else None)

def signed(x):
    x&=(1<<64)-1
    return x-(1<<64) if x>MAX else x

def kernel(own,parent_outputs,w):
    p=0
    for x in parent_outputs: p=signed(31*p+x['payload'])
    v=own['payload']
    for _ in range(w): v=signed(1664525*v+1013904223+p)
    return v

def mode(policy,failures,r,d,k,ell,w):
    if policy=='allfresh': return 'fresh'
    if failures<r: return 'cheap'
    return 'fresh' if policy=='filter' and ell+w<=top(d+[w],k) else 'cached'

def patterns(c):
    # Exhaust every public comparison branch, not fixed unused-bit schedules.
    def visit(job,failures,d,k,ell,bits):
        if job==len(c['w']):
            yield bits;return
        w=c['w'][job];m=mode(c['policy'],failures,c['r'],d,k,ell,w)
        if m=='fresh':
            yield from visit(job+1,failures,d+[w],k,ell+w,bits)
        else:
            yield from visit(job+1,failures,d+[w],k,ell,bits+'0')
            if m=='cheap': yield from visit(job,failures+1,d,k,ell,bits+'1')
            else: yield from visit(job+1,failures,d+[w],k+1,ell+w,bits+'1')
    return visit(0,0,[],0,0,'')

def native_case(c):
    events=[];live=[];done=[None]*len(c['w']);nextid=0
    W=L=Q=writes=pos=failures=job=0
    d=[];k=ell=0
    def value(job,payload):
        nonlocal nextid
        nextid+=1
        return dict(id=nextid,job=job,payload=payload)
    for i in range(len(done)):
        v=value(i,17*(i+1));live.append(v)
        events.append(dict(kind='initial',job=i,id=v['id'],payload=v['payload']))
    def state():
        if c['policy']!='filter': return None
        return dict(k=k,ell=ell,topSum=top(d,k),completed=len(d),kth=sorted(d,reverse=True)[k-1] if 0<k<=len(d) else None)
    def body(source,parents,protected):
        nonlocal W,L
        i=source['job'];w=c['w'][i]
        out=value(i,kernel(source,parents,w));W+=w
        if protected: L+=w
        events.append(dict(kind='body',job=i,source=source['id'],parents=[p['id'] for p in parents],out=out['id'],payload=out['payload'],weight=w,protected=protected))
        return out
    def write(i,phase):
        nonlocal writes
        old=live[i];out=value(i,signed(3*old['payload']+7));live[i]=out;writes+=1
        events.append(dict(kind='write',job=i,source=old['id'],out=out['id'],payload=out['payload'],phase=phase))
    while job<len(done):
        assert Q<len(done)+c['r']
        w=c['w'][job]
        parents=[done[i] for i in range(len(done)) if c['pred'][job]&(1<<i)]
        assert all(p is not None for p in parents)
        m=mode(c['policy'],failures,c['r'],d,k,ell,w)
        events.append(dict(kind='select',job=job,mode=m,filter=state()))
        match=None
        if m=='fresh': out=body(live[job],parents,True);live[job]=out;success=True
        else:
            capture=live[job];prepared=body(capture,parents,False)
            bad=c['pattern'][pos]=='1';pos+=1
            if bad:
                for _ in range(2 if c['boundary']=='doublewrite' else 1): write(job,'gate')
            current=live[job];match=current['id']==capture['id']
            events.append(dict(kind='compare',mode=m,job=job,captured=capture['id'],current=current['id'],prepared=prepared['id'],match=match))
            success=match or m=='cached'
            out=prepared if match else (body(current,parents,True) if m=='cached' else None)
            if success: live[job]=out
        Q+=1
        if success and job==0 and c['boundary']=='postwrite': write(job,'after-return-before-save')
        if success:
            assert done[job] is None
            done[job]=out;d.append(w)
            if m=='fresh': ell+=w
            elif m=='cached' and not match: ell+=w;k+=1
        else: failures+=1
        events.append(dict(kind='answer',job=job,mode=m,success=success,match=match,saved=out['id'] if out else None,live=live[job]['id'],filter=state()))
        if success: job+=1
    assert pos==len(c['pattern'])
    outputs=lambda xs:[dict(id=x['id'],payload=x['payload']) if x else None for x in xs]
    return dict(id=c['id'],root=c['root'],status='SUCCESS',error='',actualExternalWrites=writes,bodyW=W,bodyL=L,Q=Q,savedOutputs=outputs(done),liveOutputs=outputs(live),writerTerminated=True,events=events)
