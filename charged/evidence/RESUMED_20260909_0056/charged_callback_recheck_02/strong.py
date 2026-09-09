"""Additional bindings for immutable saved charged native traces."""
from pathlib import Path
import importlib.util

OLD=Path(__file__).resolve().parent.parent/'charged_callback_native_01'
spec=importlib.util.spec_from_file_location('charged_saved_native_checker',OLD/'study.py')
legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)

def verify_run(case,run,row):
    result=legacy.verify_run(case,run,row)
    events=row['events'];n=len(case['jobs']);meta={};initial={};foreground=[];publications={i:[] for i in range(n)}
    for index,e in enumerate(events):
        kind=e['kind'];i=e['job'];ident=e['id']
        if kind=='D':
            foreground.append((index,e));continue
        if kind=='I':
            assert i not in initial
            initial[i]=ident;bg=0
        else:
            assert e['source'] in meta
            source=meta[e['source']];assert source['job']==i
            bg=source['bg']+(kind=='B')
            if kind=='B':
                assert e['epoch']==bg
                publications[i].append(dict(source=e['source'],id=ident,kind='B',index=index,bg=bg))
            else:
                assert kind=='K';foreground.append((index,e))
        assert ident not in meta
        meta[ident]=dict(job=i,bg=bg,kind=kind,index=index,event=e)
    assert set(initial)==set(range(n))
    position=0;derived_failures=[];failure_records=[];completed=set();attempts=[]
    def take(kind,job,inside=None):
        nonlocal position
        assert position<len(foreground),('missing foreground event',kind,job)
        index,e=foreground[position];position+=1
        assert e['kind']==kind and e['job']==job,('foreground phase',kind,job,index,e)
        if inside is not None:assert e['inside'] is inside,('protection placement',job,index,e)
        return index,e
    for ordinal,label in enumerate(row['trace']):
        si,act=label.split(':');i=int(si);assert i not in completed
        outside=None;inside=None
        if act=='P':
            ki,output=take('K',i,True)
        else:
            code,outcome=act
            oi,outside=take('K',i,False)
            if code=='C' and outcome=='F':
                ki,inside=take('K',i,True);output=inside
                assert meta[inside['source']]['bg']>meta[outside['source']]['bg'],('cached failed recomputation epoch',i)
            else:ki,output=oi,outside
            if outcome=='F':
                before=outside['source'];epoch=meta[before]['bg']+1
                derived_failures.append((i,epoch))
                # B is logged inside its compute before publication; it must precede
                # the recomputing kernel or the next completed foreground kernel.
                anchor=ki if inside is not None else (foreground[position][0] if position<len(foreground) else len(events))
                failure_records.append(dict(job=i,before=before,epoch=epoch,anchor=anchor,attempt=ordinal))
        succeeds=act=='P' or act[1]=='S' or act[0]=='C'
        if succeeds:
            di,done=take('D',i)
            assert done['id']==output['id'],('exact successful output',i,done['id'],output['id'])
            completed.add(i)
            publications[i].append(dict(source=output['source'],id=output['id'],kind='D',index=di,bg=meta[output['id']]['bg']))
        attempts.append(dict(ordinal=ordinal,job=i,act=act,output=output['id'],succeeds=succeeds))
    assert position==len(foreground),('unmatched foreground events',position,len(foreground))
    assert len(completed)==n
    assert [tuple(x) for x in row['failures']]==derived_failures,('attempt failure binding',row['failures'],derived_failures)
    assert len(derived_failures)==len(set(derived_failures))
    successors={};chain_positions={};published=set()
    for i in range(n):
        next_by_source={}
        for pub in publications[i]:
            assert pub['source'] not in next_by_source,('forked publication chain',i,pub['source'])
            next_by_source[pub['source']]=pub
        current=initial[i];seen={current};chain_positions[current]=0;published.add(current)
        while current in next_by_source:
            pub=next_by_source[current];successors[current]=pub
            nxt=pub['id'];assert nxt not in seen,('publication cycle',i)
            assert meta[nxt]['job']==i
            chain_positions[nxt]=len(seen);seen.add(nxt);published.add(nxt);current=nxt
        assert len(seen)==len(publications[i])+1,('disconnected publication chain',i)
        assert row['live'][i]==current,('final live publication',i,row['live'][i],current)
    for e in events:
        if e['kind']=='K':assert e['source'] in published,('kernel source never published',e['id'],e['source'])
    for fail in failure_records:
        pub=successors.get(fail['before'])
        assert pub is not None and pub['kind']=='B',('failure input not superseded by write',fail)
        assert meta[pub['id']]['job']==fail['job'] and pub['bg']==fail['epoch'],('wrong write identity',fail,pub)
        assert pub['index']<fail['anchor'],('write after failure continuation',fail,pub)
    result.update(exact_completion_outputs_checked=True,per_key_publication_chains_checked=True,
                  per_attempt_write_witnesses_checked=True,foreground_attempts=len(attempts),
                  scope='Logged API argument/output bindings; causality uses stated source/API semantics, not absent timestamps')
    return result
