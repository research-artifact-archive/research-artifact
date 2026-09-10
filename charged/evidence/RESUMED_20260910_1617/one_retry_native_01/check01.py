"""Read-only source event interpretation; no Java run or diagnostic-policy inputs."""
from pathlib import Path
import json,hashlib,collections
D=Path(__file__).resolve().parent
def signed(x):return (x+(1<<63))%(1<<64)-(1<<63)
def replay(c,r):
    assert r['status']=='SUCCESS',(r['status'],r['error'])
    assert r['writer_terminated'] is True
    n=len(c['w']);values={};live={};canonical={};done={};calls=[];writes=[];shapes=[]
    W=L=Q=0;failed=False;active=None;phase=None;gates=[];prepared=comp=valid=computed=answer=None
    for ev in r['events']:
        kind=ev['kind']
        if kind in ('I','Z'):
            i=ev['job'];v=ev['id'];assert active is None and v not in values and not calls
            assert ev['payload']==(17*(i+1) if kind=='I' else 101+i)
            values[v]=(i,ev['payload'])
            if kind=='I':assert ev['key']==(128*i if c['layout']=='colliding' else i);live[i]=v
            else:canonical[i]=v
        elif kind=='SH':
            assert active is None and ev['phase']==('start' if not shapes else 'end')
            sh=ev['shape'];assert sh['capacity']==128 and sh['node_count']==n
            expected_tree=c['fixture']=='tree9' and c['layout']=='colliding'
            assert sh['tree_bins']==int(expected_tree)
            assert sum(x['nodes'] for x in sh['bins'])==n
            assert all(x['class']=='java.util.concurrent.ConcurrentHashMap$'+('TreeBin' if expected_tree else 'Node') for x in sh['bins'])
            if c['layout']=='colliding':assert len(sh['bins'])==1 and sh['bins'][0]['slot']==0
            else:assert sorted(x['slot'] for x in sh['bins'])==list(range(n))
            shapes.append(sh)
        elif kind=='S':
            assert active is None and len(shapes)==1
            i=ev['job'];assert ev['position']==len(calls) and i==c['order'][len(done)]
            assert all(j in done for j in range(n) if c['pred'][i]>>j&1)
            expected='cached' if failed else 'fresh' if c['w'][i]>c['M'] else 'cheap'
            assert ev['mode']==expected
            active=ev;gates=[];prepared=comp=valid=computed=answer=None
        elif kind=='G':
            assert active is not None and ev['position']==active['position']
            gates.append(ev['phase']);phase=ev['phase'];assert gates==['before','gate','after'][:len(gates)]
        elif kind=='B':
            i=ev['job'];v=ev['out'];assert (active['position'],i,phase)==(c['k'],c['target'],c['phase'])
            assert ev['thread']=='one-retry-external-writer' and v not in values and ev['source']==live[i]
            assert ev['payload']==signed(3*values[live[i]][1]+7)
            values[v]=(i,ev['payload']);live[i]=v;writes.append(ev)
        elif kind=='K':
            i=ev['job'];assert active is not None and i==active['job'] and ev['source']==live[i]
            parents=[done[j] if c['pred'][i]>>j&1 else -1 for j in range(n)]
            assert ev['parents']==parents
            parent=sum((j+1)*values[done[j]][1] for j in range(n) if c['pred'][i]>>j&1)
            digest=values[ev['source']][1]
            for _ in range(c['w'][i]):digest=signed(1664525*digest+1013904223+parent)
            assert ev['units']==c['w'][i] and ev['digest']==digest
            if c['kernel']=='allocated':assert ev['out'] not in values and ev['payload']==digest;values[ev['out']]=(i,digest)
            else:assert ev['out']==canonical[i] and ev['payload']==101+i
            W+=c['w'][i]
            if ev['protected']:
                assert phase=='gate' and computed is None
                assert active['mode']=='fresh' or(active['mode']=='cached' and comp is not None and not comp['match'])
                L+=c['w'][i];computed=ev['out']
            else:
                assert phase=='before' and active['mode'] in ('cheap','cached') and prepared is None
                prepared=ev
        elif kind in ('C','V'):
            assert active is not None and phase=='gate' and prepared is not None
            i=active['job'];assert ev['job']==i and ev['captured']==prepared['source'] and ev['prepared']==prepared['out'] and ev['current']==live[i]
            match=ev['captured']==ev['current']
            if kind=='C':assert active['mode']=='cached' and comp is None and ev['match']==match;comp=ev
            else:assert active['mode']=='cheap' and valid is None and ev['wrapper']==c['cheap'] and ev['success']==match;valid=ev
        elif kind=='A':
            assert answer is None and phase=='gate' and ev['position']==active['position'] and ev['job']==active['job'] and ev['mode']==active['mode']
            mode=active['mode'];i=active['job']
            if mode=='fresh':assert prepared is None and comp is None and valid is None;success=True;out=computed
            elif mode=='cheap':
                assert valid is not None and comp is None and computed is None
                success=valid['success'];out=prepared['out'] if success else None
            else:
                assert comp is not None and valid is None
                success=True;out=prepared['out'] if comp['match'] else computed
                if comp['match']:assert computed is None
            assert ev['success']==success and ev['out']==out
            if success:assert out is not None;live[i]=out
            assert ev['live']==live[i]
            answer=ev;Q+=1;calls.append(ev)
        elif kind=='D':
            i=ev['job'];assert answer is not None and answer['success'] and i==active['job'] and i not in done
            assert gates==['before','gate','after'] and ev['out']==answer['out'] and ev['live']==live[i]
            done[i]=ev['out']
        elif kind=='X':
            assert answer is not None and gates==['before','gate','after']
            i=active['job'];assert ev['job']==i and ev['position']==active['position'] and ev['success']==answer['success'] and ev['live']==live[i]
            if ev['success']:assert done.get(i)==answer['out']
            else:assert i not in done and active['mode']=='cheap';failed=True
            active=None
        else:raise AssertionError(('unknown_event',kind))
    assert active is None and len(done)==n and n<=Q<=n+1 and len(shapes)==2 and shapes[0]==shapes[1]
    expected_writes=0 if c['phase']=='none' or c['k']>=Q else 1
    assert len(writes)==expected_writes and len(writes)<=1
    assert (r['Q'],r['W'],r['L'],r['writes'])==(Q,W,L,len(writes))
    assert r['completed']==[done[i] for i in range(n)] and r['live']==[live[i] for i in range(n)]
    Wcap=sum(c['w'])+c['M'];Lcap=sum(v for v in c['w'] if v>c['M'])
    assert W<=Wcap and L<=Lcap,(W,L,Wcap,Lcap)
    projection=dict(Q=Q,W=W,L=L,writes=len(writes),trace=[(a['job'],a['mode'],a['success']) for a in calls],completed_payloads=[values[done[i]][1] for i in range(n)],live_payloads=[values[live[i]][1] for i in range(n)])
    return dict(id=c['id'],status='SUCCESS',projection=projection,W_cap=Wcap,L_cap=Lcap,cheap_failures=sum(not a['success'] for a in calls),cached_calls=sum(a['mode']=='cached' for a in calls),tree_bin=bool(shapes[0]['tree_bins']),scheduled_write_unissued=c['phase']!='none' and not writes,saved_differs_live=sum(done[i]!=live[i] for i in range(n)))

def main():
    assert not(D/'SUMMARY01.json').exists()
    cases=json.loads((D/'INPUTS.json').read_text());raw=[];parse_errors=[]
    if(D/'RAW01.jsonl').exists():
        for k,line in enumerate((D/'RAW01.jsonl').open()):
            try:raw.append(json.loads(line))
            except Exception as e:parse_errors.append(dict(line=k,error=repr(e)))
    byid={x['id']:x for x in raw};assert len(byid)==len(raw) and set(byid)<=set(c['id'] for c in cases)
    results=[]
    for c in cases:
        if c['id'] not in byid:results.append(dict(id=c['id'],status='NOT_EXECUTED'));continue
        try:results.append(replay(c,byid[c['id']]))
        except Exception as e:results.append(dict(id=c['id'],status='CHECK_FAILURE',error=repr(e)))
    maxima={};paired={};pair_errors=[]
    for c,r in zip(cases,results):
        if r['status']!='SUCCESS':continue
        key='|'.join(str(c[k]) for k in ('fixture','M','layout','kernel','cheap'))
        g=maxima.setdefault(key,dict(count=0,max_Q=-1,max_W=-1,max_L=-1,expected_Q=len(c['w'])+int(c['M']>0),expected_W=r['W_cap'],expected_L=r['L_cap']))
        g['count']+=1
        for k in ('Q','W','L'):
            if r['projection'][k]>g['max_'+k]:g['max_'+k]=r['projection'][k];g[k+'_witness']=c['id']
        pkey='|'.join(str(c[k]) for k in ('fixture','M','layout','kernel','k','target','phase'))
        if pkey in paired:
            if paired[pkey]!=r['projection']:pair_errors.append(dict(input=pkey,first=paired[pkey],second=r['projection']))
        else:paired[pkey]=r['projection']
    max_errors={key:g for key,g in maxima.items() if any(g['max_'+k]!=g['expected_'+k] for k in ('Q','W','L'))}
    (D/'CHECK_ROWS01.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in results))
    (D/'MAXIMA01.json').write_text(json.dumps(maxima,indent=2)+'\n')
    (D/'CHECK_ERRORS01.json').write_text(json.dumps(dict(parse=parse_errors,pairs=pair_errors,maxima=max_errors),indent=2)+'\n')
    statuses=dict(collections.Counter(r['status'] for r in results))
    success=statuses=={'SUCCESS':12224} and not parse_errors and not pair_errors and not max_errors and len(paired)==6112 and len(maxima)==176
    summary=dict(status='SUCCESS' if success else 'FAILURE',denominator=len(cases),statuses=statuses,wrapper_pairs=len(paired),groups=len(maxima),cheap_failures=sum(r.get('cheap_failures',0) for r in results),cached_calls=sum(r.get('cached_calls',0) for r in results),tree_bin_executions=sum(r.get('tree_bin',False) for r in results),unissued_late_writes=sum(r.get('scheduled_write_unissued',False) for r in results),saved_differs_live=sum(r.get('saved_differs_live',0) for r in results),new_native_runs=12224,new_timing_samples=0,hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in D.iterdir() if p.is_file() and p.name!='SUMMARY01.json'})
    (D/'SUMMARY01.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2));return success
if __name__=='__main__':raise SystemExit(not main())
