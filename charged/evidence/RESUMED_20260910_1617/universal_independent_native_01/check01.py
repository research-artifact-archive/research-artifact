"""Read-only source event interpretation; no Java run or diagnostic-policy inputs."""
from pathlib import Path
import json,hashlib,collections
D=Path(__file__).resolve().parent
def signed(x):return (x+(1<<63))%(1<<64)-(1<<63)
def top(w,b):return sum(sorted(w,reverse=True)[:max(0,b)])
def curve(w,r):
    a=sorted(w);n=len(w);Omega=sum(w);ans=[]
    for B in range(n+r+1):
        if B<=r:extra=B*a[-1]
        else:extra=max(r*a[n-m]+sum(a[n-m:]) for m in range(1,min(n,B-r)+1))
        ans.append(Omega+extra)
    return ans

def replay(c,r):
    assert r['status']=='SUCCESS',(r['status'],r['error'])
    assert r['writer_terminated'] is True
    n=len(c['w']);values={};live={};canonical={};done={};calls=[];writes=[];shapes=[]
    W=L=Q=0;failures=0;active=None;phase=None;gates=[];prepared=comp=valid=computed=answer=None
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
            expected='cheap' if failures<c['r'] else 'cached'
            assert ev['mode']==expected
            active=ev;gates=[];prepared=comp=valid=computed=answer=None
        elif kind=='G':
            assert active is not None and ev['position']==active['position']
            gates.append(ev['phase']);phase=ev['phase'];assert gates==['before','gate','after'][:len(gates)]
        elif kind=='B':
            i=ev['job'];v=ev['out'];assert i==active['job'] and phase=='gate' and c['pattern'][active['position']]=='1'
            assert ev['thread']=='universal-external-writer' and v not in values and ev['source']==live[i]
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
            else:assert i not in done and active['mode']=='cheap';failures+=1
            active=None
        else:raise AssertionError(('unknown_event',kind))
    assert active is None and len(done)==n and n<=Q<=n+c['r'] and len(shapes)==2 and shapes[0]==shapes[1]
    assert Q==len(c['pattern'])
    expected_writes=c['pattern'].count('1')
    assert len(writes)==expected_writes and failures<=min(len(writes),c['r'])
    assert (r['Q'],r['W'],r['L'],r['writes'])==(Q,W,L,len(writes))
    assert r['completed']==[done[i] for i in range(n)] and r['live']==[live[i] for i in range(n)]
    Wcap=curve(c['w'],c['r'])[len(writes)];Lcap=top(c['w'],len(writes)-c['r'])
    assert W<=Wcap and L<=Lcap,(W,L,Wcap,Lcap)
    projection=dict(Q=Q,W=W,L=L,writes=len(writes),trace=[(a['job'],a['mode'],a['success']) for a in calls],completed_payloads=[values[done[i]][1] for i in range(n)],live_payloads=[values[live[i]][1] for i in range(n)])
    return dict(id=c['id'],status='SUCCESS',projection=projection,W_cap=Wcap,L_cap=Lcap,cheap_failures=sum(not a['success'] for a in calls),cached_calls=sum(a['mode']=='cached' for a in calls),tree_bin=bool(shapes[0]['tree_bins']),saved_differs_live=sum(done[i]!=live[i] for i in range(n)))

def main():
    import copy
    assert not(D/'SUMMARY01.json').exists()
    cases=json.loads((D/'INPUTS.json').read_text());raw=[];parse=[]
    if(D/'RAW01.jsonl').exists():
        for k,line in enumerate((D/'RAW01.jsonl').open()):
            try:raw.append(json.loads(line))
            except Exception as e:parse.append(dict(line=k,error=repr(e)))
    byid={r['id']:r for r in raw};assert len(byid)==len(raw) and set(byid)<=set(c['id'] for c in cases)
    results=[];groups={};pairs={};pair_errors=[]
    for c in cases:
        if c['id'] not in byid:got=dict(id=c['id'],status='NOT_EXECUTED')
        else:
            try:got=replay(c,byid[c['id']])
            except Exception as e:got=dict(id=c['id'],status='CHECK_FAILURE',error=repr(e))
        results.append(got)
        if got['status']!='SUCCESS':continue
        key='|'.join(str(c[k]) for k in ['fixture','r','layout','kernel','cheap']);n=len(c['w']);H=n+c['r']
        g=groups.setdefault(key,dict(input={k:c[k] for k in ['fixture','w','r','layout','kernel','cheap']},count=0,coordinates=[dict(B=B,W=-1,L=-1,Q=-1) for B in range(H+1)]))
        g['count']+=1
        for B in range(got['projection']['writes'],H+1):
            for name in ['W','L','Q']:
                if got['projection'][name]>g['coordinates'][B][name]:g['coordinates'][B][name]=got['projection'][name];g['coordinates'][B][name+'_witness']=c['id']
        pk='|'.join(str(c[k]) for k in ['fixture','r','layout','kernel','pattern'])
        if pk in pairs:
            if pairs[pk]!=got['projection']:pair_errors.append(dict(key=pk,first=pairs[pk],second=got['projection']))
        else:pairs[pk]=got['projection']
    group_errors=[]
    for key,g in groups.items():
        w=g['input']['w'];r=g['input']['r'];expected=curve(w,r)
        for row in g['coordinates']:
            B=row['B'];want={'W':expected[B],'L':top(w,B-r),'Q':len(w)+min(r,B)};row['expected']=want
            if any(row[k]!=want[k] for k in want):group_errors.append(dict(group=key,row=row))
    mutations=[]
    specifications=[('total_W',None,'W'),('total_L',None,'L'),('total_Q',None,'Q'),('writer_termination',None,'writer_terminated'),('kernel_units','K','units'),('kernel_digest','K','digest'),('writer_thread','B','thread'),('cached_match','C','match'),('completed_return','A','out'),('saved_output','D','out'),('shape_count','SH','shape'),('schedule_pattern',None,'pattern')]
    for label,kind,field in specifications:
        candidates=[c for c in cases if c['id'] in byid and byid[c['id']]['status']=='SUCCESS' and (kind is None or any(e['kind']==kind and(field!='out' or e.get('out') is not None) for e in byid[c['id']]['events']))]
        if not candidates:mutations.append(dict(label=label,status='NO_ELIGIBLE_ROW'));continue
        c=copy.deepcopy(candidates[0]);rawrow=copy.deepcopy(byid[c['id']]);target=next(e for e in rawrow['events'] if e['kind']==kind and(field!='out' or e.get('out') is not None)) if kind else rawrow
        if field=='writer_terminated':target[field]=False
        elif field=='thread':target[field]='incorrect-writer'
        elif field=='match':target[field]=not target[field]
        elif field=='shape':target[field]['node_count']+=1
        elif field=='pattern':c['pattern']=('1' if c['pattern'][0]=='0' else '0')+c['pattern'][1:]
        else:target[field]+=1
        try:replay(c,rawrow);mutations.append(dict(label=label,id=c['id'],status='MISSED_CORRUPTION'))
        except Exception as e:mutations.append(dict(label=label,id=c['id'],status='REJECTED',error=repr(e)))
    (D/'CHECK_ROWS01.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in results))
    (D/'CURVE_MAXIMA01.json').write_text(json.dumps(groups,indent=2)+'\n')
    (D/'MUTATION_RESULTS01.json').write_text(json.dumps(mutations,indent=2)+'\n')
    (D/'CHECK_ERRORS01.json').write_text(json.dumps(dict(parse=parse,pairs=pair_errors,groups=group_errors),indent=2)+'\n')
    statuses=dict(collections.Counter(x['status'] for x in results));mutationstatus=dict(collections.Counter(x['status'] for x in mutations))
    ok=statuses=={'SUCCESS':20384} and len(pairs)==10192 and len(groups)==512 and not(parse or pair_errors or group_errors) and mutationstatus=={'REJECTED':12}
    summary=dict(status='SUCCESS' if ok else 'FAILURE',denominator=len(cases),statuses=statuses,wrapper_pairs=len(pairs),curve_groups=len(groups),budget_coordinates=sum(len(g['coordinates']) for g in groups.values()),cheap_failures=sum(x.get('cheap_failures',0) for x in results),cached_calls=sum(x.get('cached_calls',0) for x in results),tree_bin_executions=sum(x.get('tree_bin',False) for x in results),mutation_statuses=mutationstatus,new_native_runs=20384,new_timing_samples=0,hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in D.iterdir() if p.is_file() and p.name!='SUMMARY01.json'})
    (D/'SUMMARY01.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2));return ok
if __name__=='__main__':raise SystemExit(not main())
