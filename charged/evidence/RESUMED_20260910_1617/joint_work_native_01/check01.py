"""Independent event replay and exhaustive-order cap calculation; never runs Java."""
import collections,hashlib,itertools,json
from pathlib import Path
D=Path(__file__).resolve().parent
def signed(x):return (x+(1<<63))%(1<<64)-(1<<63)
def cap(c):
    w=c['w'];omega=sum(w)
    if c['policy']=='cached':return omega+max(w),max(w)
    if c['policy']=='fresh':return omega,omega
    values=[]
    for order in itertools.permutations(range(len(w))):
        seen=0;p=0;L=0
        for i in order:
            if c['pred'][i]&seen!=c['pred'][i]:break
            seen|=1<<i
            p+=w[i] if w[i]>c['M'] else 0
            L=max(L,p+(w[i] if w[i]<=c['M'] else 0))
        else:values.append(L)
    return omega+c['M'],min(values)
def replay(c,r):
    assert r['status']=='SUCCESS',(r['status'],r['error'])
    assert r['writer_terminated'] is True
    n=len(c['w']);values={};live={};z={};done={};W=L=Q=0;writes=[];calls=[];miss=False
    active=None;gate_sequence=[];phase=None;comp=None;prepared=None;computed=None;saved=None
    for ev in r['events']:
        kind=ev['kind']
        if kind in ('I','Z'):
            i=ev['job'];v=ev['id'];assert v not in values
            assert ev['payload']==(17*(i+1) if kind=='I' else 101+i)
            values[v]=(i,ev['payload'])
            if kind=='I':
                assert ev['key']==(128*i if c['layout']=='colliding' else i);live[i]=v
            else:z[i]=v
        elif kind=='S':
            assert active is None
            i=ev['job'];pos=len(calls);assert ev['position']==pos and i==c['order'][pos]
            assert all(j in done for j in range(n) if c['pred'][i]>>j&1)
            expected='fresh' if c['policy']=='fresh' or(c['policy']=='lawler' and not miss and c['w'][i]>c['M']) else 'cached'
            assert ev['mode']==expected
            active=ev;gate_sequence=[];comp=prepared=computed=saved=None
        elif kind=='G':
            assert active is not None and ev['position']==active['position']
            gate_sequence.append(ev['phase']);phase=ev['phase']
            assert gate_sequence==['before','gate','after'][:len(gate_sequence)]
        elif kind=='B':
            i=ev['job'];out=ev['out']
            assert (active['position'],i,phase)==(c['k'],c['target'],c['phase'])
            assert ev['thread']=='joint-resource-external-writer' and out not in values
            assert ev['source']==live[i]
            assert ev['payload']==signed(3*values[live[i]][1]+7)
            values[out]=(i,ev['payload']);live[i]=out;writes.append(ev)
        elif kind=='K':
            i=ev['job'];assert active is not None and i==active['job']
            assert ev['source']==live[i]
            expected_parents=[done[j] if c['pred'][i]>>j&1 else -1 for j in range(n)]
            assert ev['parents']==expected_parents
            parent=sum((j+1)*values[done[j]][1] for j in range(n) if c['pred'][i]>>j&1)
            digest=values[ev['source']][1]
            for _ in range(c['w'][i]):digest=signed(1664525*digest+1013904223+parent)
            assert ev['units']==c['w'][i] and ev['digest']==digest
            if c['kernel']=='allocated':
                assert ev['out'] not in values and ev['payload']==digest
                values[ev['out']]=(i,digest)
            else:assert ev['out']==z[i] and ev['payload']==101+i
            W+=c['w'][i]
            if ev['protected']:
                assert phase=='gate';L+=c['w'][i];assert computed is None
                assert active['mode']=='fresh' or(comp is not None and not comp['match'])
                computed=ev['out']
            else:
                assert phase=='before' and active['mode']=='cached' and prepared is None
                prepared=ev
        elif kind=='C':
            assert active['mode']=='cached' and comp is None and phase=='gate'
            i=active['job'];assert ev['job']==i
            assert ev['captured']==prepared['source'] and ev['prepared']==prepared['out'] and ev['current']==live[i]
            assert ev['match']==(ev['captured']==ev['current']);comp=ev
        elif kind=='A':
            assert ev['job']==active['job'] and ev['position']==active['position'] and ev['mode']==active['mode'] and phase=='gate'
            if active['mode']=='fresh':assert comp is None and prepared is None and ev['match'] is None and ev['returned_is_prepared'] is None
            else:
                assert ev['match']==comp['match']
                assert ev['returned_is_prepared']==(ev['out']==prepared['out'])
            expected=prepared['out'] if comp is not None and comp['match'] else computed
            assert ev['out']==expected and expected is not None
            if comp is not None and comp['match']:assert computed is None
            live[ev['job']]=ev['out'];saved=ev['out'];Q+=1
            calls.append(ev)
            if comp is not None and not c['control'] and not comp['match']:miss=True
        elif kind=='D':
            i=ev['job'];assert i==active['job'] and i not in done and saved is not None
            assert gate_sequence==['before','gate','after'] and ev['out']==saved and ev['live']==live[i]
            done[i]=saved;active=None
        else:raise AssertionError(('unknown event',kind))
    assert active is None and Q==n and len(done)==n
    assert len(writes)==(0 if c['phase']=='none' else 1)
    assert (r['Q'],r['W'],r['L'],r['writes'])==(Q,W,L,len(writes))
    assert r['completed']==[done[i] for i in range(n)] and r['live']==[live[i] for i in range(n)]
    cw,cl=cap(c);violation=W>cw or L>cl
    predicted=c['control'] and c['k']==0 and c['target']==0 and c['phase']=='gate'
    assert violation==predicted,(W,L,cw,cl,predicted)
    return dict(id=c['id'],fixture=c['fixture'],policy=c['policy'],M=c['M'],layout=c['layout'],kernel=c['kernel'],control=c['control'],status='EXPECTED_COUNTEREXAMPLE' if violation else 'SUCCESS',Q=Q,W=W,L=L,W_cap=cw,L_cap=cl,violation=violation,trace=[(a['job'],a['mode'],a['match']) for a in calls],same_output_mismatches=sum(a['match'] is False and a['returned_is_prepared'] for a in calls),saved_differs_live=sum(done[i]!=live[i] for i in range(n)))
cases=json.loads((D/'INPUTS.json').read_text());raw=[json.loads(x) for x in (D/'RAW01.jsonl').read_text().splitlines()]
byid={x['id']:x for x in raw};assert len(byid)==len(raw) and set(byid)<=set(c['id'] for c in cases)
results=[]
for c in cases:
    if c['id'] not in byid:results.append(dict(id=c['id'],status='NOT_EXECUTED',control=c['control']));continue
    try:results.append(replay(c,byid[c['id']]))
    except Exception as e:results.append(dict(id=c['id'],status='CHECK_FAILURE',control=c['control'],error=repr(e)))
(D/'CHECK_ROWS01.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in results))
maxima={}
for c,r in zip(cases,results):
    if r['status'] not in ('SUCCESS','EXPECTED_COUNTEREXAMPLE'):continue
    key='|'.join(str(c[k]) for k in ('fixture','policy','M','layout','kernel','control'))
    g=maxima.setdefault(key,dict(count=0,max_W=-1,max_L=-1,W_witness=None,L_witness=None))
    g['count']+=1
    for name in ('W','L'):
        if r[name]>g['max_'+name]:g['max_'+name]=r[name];g[name+'_witness']=c['id']
(D/'MAXIMA01.json').write_text(json.dumps(maxima,indent=2)+'\n')
statuses=dict(collections.Counter(r['status'] for r in results))
summary=dict(status='SUCCESS' if statuses=={'SUCCESS':2124,'EXPECTED_COUNTEREXAMPLE':4} else 'FAILURE',denominator=len(cases),correct_policies=2076,negative_controls=52,statuses=statuses,correct_policy_success=sum(r['status']=='SUCCESS' and not r['control'] for r in results),control_violations=sum(r['status']=='EXPECTED_COUNTEREXAMPLE' for r in results),control_nonviolations=sum(r['status']=='SUCCESS' and r['control'] for r in results),same_output_mismatches=sum(r.get('same_output_mismatches',0) for r in results),saved_differs_live=sum(r.get('saved_differs_live',0) for r in results),hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in D.iterdir() if p.is_file() and p.name not in ('SUMMARY01.json',)})
(D/'SUMMARY01.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
raise SystemExit(summary['status']!='SUCCESS')
