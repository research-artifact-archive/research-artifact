from pathlib import Path
from collections import Counter
import argparse,copy,datetime,hashlib,json

def read_units(p):
    out={}
    for line in p.read_text().splitlines():
        a=line.split('\t');unit=dict(zip(['id','phase','fork','rep','projects','r','B','mode','scenario'],a))
        for k in ['fork','rep','projects','r','B']:unit[k]=int(unit[k])
        if unit['id'] in out:raise ValueError('duplicate planned id')
        out[unit['id']]=unit
    return out

def normal_trace(x):
    ts=x['trace'];we=x['writer_events'];caps=x['captures'];idx=0;wi=0;current=None;remaining=x['r'];q=out=inside=fail=mismatch=0;kernel_ns={'outside':0,'inside':0};last_ns=-1
    def take(kind,job,snapshot=None):
        nonlocal idx,last_ns
        if idx>=len(ts):raise ValueError('truncated trace:'+kind)
        t=ts[idx];idx+=1
        if t['Kind']!=kind or t['Job']!=job or t['Writes']!=wi:raise ValueError('unexpected trace:'+kind)
        if snapshot is not None and t['Snapshot']!=snapshot:raise ValueError('wrong snapshot:'+kind)
        if type(t['Ns']) is not int or not last_ns<=t['Ns']<=x['foreground_ns']:raise ValueError('trace time')
        last_ns=t['Ns'];return t
    for job in range(1,5):
        while True:
            fresh=x['mode']=='two' and remaining==0
            if current is None:current=ts[idx]['Snapshot']
            prepared_input=None
            if not fresh:
                a=take('kernel_outside_begin',job,current);b=take('kernel_outside_end',job)
                if b['Snapshot']==current:raise ValueError('normal preparation no-op')
                kernel_ns['outside']+=b['Ns']-a['Ns'];out+=1;prepared_input=current
            before=take('before_lock',job,current);q+=1
            if q<=x['B']:
                if wi>=len(we):raise ValueError('missing writer')
                e=we[wi]
                if e['kind']!='change_background' or e['write']!=wi+1 or e['job']!=job or e['opportunity']!=q or e['after_snapshot']==current:raise ValueError('writer transition')
                current=e['after_snapshot'];wi+=1
            enter=take('lock_enter',job,current)
            if q<=x['B'] and not before['Ns']<=we[wi-1]['ns']<=enter['Ns']:raise ValueError('writer chronology')
            if not fresh and prepared_input!=current:
                mismatch+=1
                if not(x['mode']=='three' and remaining==0):
                    take('cheap_failure',job,current);fail+=1
                    if x['mode']!='original':
                        if remaining<=0:raise ValueError('exhausted cheap call')
                        remaining-=1
                    continue
            if fresh or prepared_input!=current:
                a=take('kernel_inside_begin',job,current);b=take('kernel_inside_end',job)
                if b['Snapshot']==current:raise ValueError('normal protected no-op')
                kernel_ns['inside']+=b['Ns']-a['Ns'];inside+=1
            ret=take('return_changed',job)
            if ret['Snapshot']==current:raise ValueError('unchanged publication')
            current=ret['Snapshot'];c=caps[job-1]
            if (c['job'],c['snapshot'],c['writes_at_return'])!=(job,current,wi):raise ValueError('capture/return binding')
            break
    if idx!=len(ts) or wi!=len(we) or wi!=x['B'] or x['prelock_opportunities']!=q:raise ValueError('unused or incomplete trace')
    expected={'Calls':q,'PreparedOutside':out,'PreparedInside':inside,'Mismatches':mismatch,'CheapFailures':fail}
    if expected!=x['counters']:raise ValueError('counters/trace')
    if x['remaining']!=remaining:raise ValueError('remaining slack')
    f=min(x['B'],x['r']);theory={'Calls':4+x['B'] if x['mode']=='original' else 4+f,'PreparedInside':0 if x['mode']=='original' else (4 if x['B']>=x['r'] else 0) if x['mode']=='two' else min(max(x['B']-x['r'],0),4),'PreparedOutside':4+x['B'] if x['mode']=='original' else f if x['mode']=='two' and x['B']>=x['r'] else 4+f,'CheapFailures':x['B'] if x['mode']=='original' else f,'Mismatches':f if x['mode']=='two' else x['B']}
    if expected!=theory:raise ValueError('count equation')
    return kernel_ns

def validate(x):
    errors=[];derived={}
    try:
        if x['status']!='SUCCESS':return [],derived
        n=x['projects'];scenario=x['scenario'];normal=scenario=='normal';removed=scenario in ['missing_required','removed_between']
        for k in ['actual_writes','prelock_opportunities','foreground_ns','writer_join_ns','setup_ns','whole_unit_ns','sequence','process_elapsed_ns']:
            if type(x.get(k)) is not int or x[k]<0:raise ValueError('nonnegative integer:'+k)
        if x['foreground_ns']<x['writer_join_ns'] or x['whole_unit_ns']<x['setup_ns']+x['foreground_ns']:raise ValueError('total timing containment')
        if x['process_elapsed_ns']<x['whole_unit_ns']:raise ValueError('process elapsed')
        if x['observed_exception']!=('ArgumentException' if removed else ''):raise ValueError('exception outcome')
        final=[4 if normal else 0]*n
        if removed:final[0]=-1
        if x['final_target_versions']!=final or x['final_background_version']!=(x['B'] if normal else 0):raise ValueError('final contents')
        if x['actual_writes']!=(x['B'] if normal else 1 if scenario=='removed_between' else 0):raise ValueError('actual writes')
        if len(x['captures'])!=(4 if normal else 0 if removed else 1):raise ValueError('capture count')
        for j,c in enumerate(x['captures'],1):
            if c['job']!=j or c['target_versions']!=[j if normal else 0]*n or c['background_version']!=c['writes_at_return']:raise ValueError('persistent captured output')
        notifications=x['notifications'];events=x['workspace_event_document_sequence']
        if [a['document'] for a in notifications]!=events:raise ValueError('notification/event order')
        if normal:
            at=0;previous=0
            for j,c in enumerate(x['captures'],1):
                for w in range(previous+1,c['writes_at_return']+1):
                    if notifications[at]!={'document':-1,'version':w}:raise ValueError('background notification');at+=1
                block=notifications[at:at+n];at+=n
                if Counter((a['document'],a['version']) for a in block)!=Counter((i,j) for i in range(n)):raise ValueError('linked notification block')
                if block[0]['document']!=0:raise ValueError('primary notification first')
                previous=c['writes_at_return']
            if at!=len(notifications) or previous!=x['B']:raise ValueError('notification denominator')
            if x['mode']!='baseline':derived=normal_trace(x)
        elif scenario=='equal_identity':
            if Counter((a['document'],a['version']) for a in notifications)!=Counter((i,0) for i in range(n)):raise ValueError('equal-identity notification')
        elif notifications:raise ValueError('unexpected notification')
        if not normal and x['mode']!='baseline':
            times=[a['Ns'] for a in x['trace']]
            if times!=sorted(times) or any(type(a) is not int or a<0 or a>x['foreground_ns'] for a in times):raise ValueError('regression trace time')
            k=Counter(a['Kind'] for a in x['trace'])
            for counter,kind in [('Calls','lock_enter'),('PreparedInside','kernel_inside_begin'),('PreparedOutside','kernel_outside_begin'),('CheapFailures','cheap_failure')]:
                if x['counters'][counter]!=k[kind]:raise ValueError('regression counter')
    except (ValueError,KeyError,IndexError,TypeError) as e:errors.append(str(e))
    return errors,derived

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--runs',type=Path,required=True);parser.add_argument('--raw',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args();args.out.mkdir()
    planned=read_units(args.runs);rows=[];parse_errors=[]
    for number,line in enumerate(args.raw.read_text().splitlines(),1):
        try:rows.append(json.loads(line))
        except Exception as e:parse_errors.append({'line':number,'error':str(e)})
    actual={};issues=list(parse_errors);derived=[]
    for x in rows:
        if x['id'] in actual:issues.append({'duplicate':x['id']})
        actual[x['id']]=x
        if x['id'] not in planned:issues.append({'unplanned':x['id']});continue
        if any(x.get(k)!=v for k,v in planned[x['id']].items()):issues.append({'input_binding':x['id']})
        errors,d=validate(x)
        if errors:issues.append({'id':x['id'],'errors':errors})
        derived.append({'id':x['id'],'kernel_intervals_ns':d})
    if [x['sequence'] for x in rows]!=list(range(len(rows))):issues.append({'sequence':'not contiguous'})
    if any(a['process_elapsed_ns']>=b['process_elapsed_ns'] for a,b in zip(rows,rows[1:])):issues.append({'process_chronology':False})
    ledger=[unit|{'status':actual[uid]['status'] if uid in actual else 'INVALID','reason':'' if uid in actual else 'planned unit missing; no replacement'} for uid,unit in planned.items()]
    controls=[];candidates=[x for x in rows if x['scenario']=='normal' and x['mode']=='three' and x['B']>x['r'] and x['status']=='SUCCESS']
    if candidates:
        sample=candidates[0]
        changes=[('call_counter',lambda x:x['counters'].update(Calls=x['counters']['Calls']+1)),('captured_parent_later_version',lambda x:x['captures'][0]['target_versions'].__setitem__(0,4)),('cached_mismatch_input',lambda x:next(t for t in x['trace'] if t['Kind']=='kernel_inside_begin').update(Snapshot=-1)),('missing_notification',lambda x:x['notifications'].pop()),('notification_event_order',lambda x:x['workspace_event_document_sequence'].reverse()),('writer_old_identity',lambda x:x['writer_events'][0].update(after_snapshot=x['trace'][0]['Snapshot'])),('writer_time',lambda x:x['writer_events'][0].update(ns=-1)),('negative_setup',lambda x:x.update(setup_ns=-1)),('false_noop',lambda x:next(t for t in x['trace'] if t['Kind']=='return_changed').update(Kind='return_noop')),('unspent_slack',lambda x:x.update(remaining=99)),('wrong_actual_writes',lambda x:x.update(actual_writes=99))]
        for name,change in changes:
            bad=copy.deepcopy(sample);change(bad);errors,_=validate(bad);controls.append({'name':name,'rejected':bool(errors),'errors':errors})
    counts=Counter(x['status'] for x in ledger);ok=not issues and counts=={'SUCCESS':len(planned)} and all(x['rejected'] for x in controls)
    receipt={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS' if ok else 'FAIL','expected':len(planned),'observed':len(rows),'counts':dict(counts),'issues':issues,'controls':controls,'raw_sha256':hashlib.sha256(args.raw.read_bytes()).hexdigest(),'runs_sha256':hashlib.sha256(args.runs.read_bytes()).hexdigest(),'checker_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'normal_trace_scope':'Source step grammar, current/prepared/write identities, actual writer placement, call and transformation counters, persistent outputs and notification ordering. Conditional on authored source hooks; not arbitrary host safety or complete compiler verification.'}
    for name,data in [('CHECK_RECEIPT.json',receipt),('OUTCOME_LEDGER.json',ledger),('DERIVED.json',derived)]: (args.out/name).write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))

if __name__=='__main__':main()
