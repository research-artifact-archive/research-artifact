from pathlib import Path
D=Path(__file__).resolve().parent;old=(D.parent/'one_retry_native_01/check01.py').read_text();t=old[:old.index('\ndef main():')]
t=t.replace('failed=False','failures=0').replace("expected='cached' if failed else 'fresh' if c['w'][i]>c['M'] else 'cheap'","expected='cheap' if failures<c['r'] else 'cached'")
t=t.replace("assert (active['position'],i,phase)==(c['k'],c['target'],c['phase'])","assert i==active['job'] and phase=='gate' and c['pattern'][active['position']]=='1'")
t=t.replace('one-retry-external-writer','universal-external-writer').replace('failed=True','failures+=1')
t=t.replace('n<=Q<=n+1','n<=Q<=n+c[\'r\']').replace("expected_writes=0 if c['phase']=='none' or c['k']>=Q else 1","assert Q==len(c['pattern'])\n    expected_writes=c['pattern'].count('1')")
t=t.replace('assert len(writes)==expected_writes and len(writes)<=1','assert len(writes)==expected_writes and failures<=min(len(writes),c[\'r\'])')
t=t.replace("Wcap=sum(c['w'])+c['M'];Lcap=sum(v for v in c['w'] if v>c['M'])","Wcap=curve(c['w'],c['r'])[len(writes)];Lcap=top(c['w'],len(writes)-c['r'])")
t=t.replace("scheduled_write_unissued=c['phase']!='none' and not writes,",'')
assert "c['M']" not in t and "c['phase']" not in t and "c['target']" not in t and "failed=" not in t
helpers='''
def top(w,b):return sum(sorted(w,reverse=True)[:max(0,b)])
def curve(w,r):
    a=sorted(w);n=len(w);Omega=sum(w);ans=[]
    for B in range(n+r+1):
        if B<=r:extra=B*a[-1]
        else:extra=max(r*a[n-m]+sum(a[n-m:]) for m in range(1,min(n,B-r)+1))
        ans.append(Omega+extra)
    return ans
'''
t=t.replace('\ndef replay(c,r):',helpers+'\ndef replay(c,r):')
assert not(D/'check01.py').exists();(D/'check01.py').write_text(t)
