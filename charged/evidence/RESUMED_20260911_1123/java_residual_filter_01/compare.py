from pathlib import Path
import json,sys,datetime,collections,hashlib
from reference import filter_case,native_case,top
P=Path(__file__).resolve().parent
A=Path(sys.argv[1]).resolve()

def save(name,obj):
    with (A/name).open('x') as f: json.dump(obj,f,indent=2);f.write('\n')

def read_lines(name):
    rows=[];bad=[]
    p=A/name
    if not p.exists(): return rows,[dict(kind='missing_file',name=name)]
    for i,line in enumerate(p.read_text().splitlines()):
        try: rows.append(json.loads(line))
        except Exception as e: bad.append(dict(kind='invalid_json',name=name,line=i+1,error=str(e)))
    return rows,bad

def differences(a,b,path=''):
    if type(a)!=type(b): return [dict(path=path,expected=a,actual=b)]
    if isinstance(a,dict):
        if a.keys()!=b.keys(): return [dict(path=path,expected_keys=list(a),actual_keys=list(b))]
        out=[]
        for k in a: out.extend(differences(a[k],b[k],path+'/'+k))
        return out
    if isinstance(a,list):
        if len(a)!=len(b): return [dict(path=path,expected_length=len(a),actual_length=len(b))]
        out=[]
        for i,(x,y) in enumerate(zip(a,b)): out.extend(differences(x,y,path+'/'+str(i)))
        return out
    return [] if a==b else [dict(path=path,expected=a,actual=b)]

fcs=json.loads((P/'FILTER_INPUTS.json').read_text())
ncs=json.loads((P/'NATIVE_INPUTS.json').read_text())
roots=json.loads((P/'NATIVE_ROOTS.json').read_text())
fr,fi=read_lines('filter.jsonl');nr,ni=read_lines('native.jsonl')
issues=fi+ni
results={};all_ledger=[];native_by_root=collections.defaultdict(list)
for kind,cases,actual,oracle in [('filter',fcs,fr,filter_case),('native',ncs,nr,native_case)]:
    byid={}
    for row in actual:
        id=row.get('id')
        if id in byid: issues.append(dict(kind='duplicate_id',suite=kind,id=id))
        byid[id]=row
    counts=collections.Counter()
    with (A/f'{kind}_reference.jsonl').open('x') as refout:
        for c in cases:
            e=oracle(c);refout.write(json.dumps(e,separators=(',',':'))+'\n')
            a=byid.pop(c['id'],None)
            if a is None: status='NOT_EXECUTED';diff=[]
            else:
                diff=differences(e,a)
                status=a.get('status','SUCCESS')
                if diff:
                    issues.append(dict(kind='trace_mismatch',suite=kind,id=c['id'],differences=diff))
                    if status=='SUCCESS': status='FAILURE'
            counts[status]+=1
            all_ledger.append(dict(suite=kind,id=c['id'],root=c['root'],status=status))
            if kind=='native' and a is not None: native_by_root[c['root']].append(a)
    for id in byid: issues.append(dict(kind='unexpected_id',suite=kind,id=id))
    results[kind]=dict(planned=len(cases),observed=len(actual),statuses=dict(counts))
# Rejections are expected API outcomes, not discarded executions.
filter_rejections=collections.Counter()
unsafe_fresh=0;atomic_failures=[];query_count=update_count=0
for row in fr:
    if row['constructorError']: filter_rejections['constructor_'+row['constructorError']]+=1
    for e in row['events']:
        if e['op']=='Q': query_count+=1
        else: update_count+=1
        if e['error']:
            filter_rejections[e['error']]+=1
            if e['op']=='FRESH' and e['error']=='IllegalArgumentException': unsafe_fresh+=1
            if e['before']!=e['after']: atomic_failures.append(dict(id=row['id'],event=e))
issues.extend(dict(kind='non_atomic_rejection',**x) for x in atomic_failures)

invariant_issues=[];strict=[];postwrite_checked=doublewrite_checked=0
for c in ncs:
    rows=[x for x in native_by_root[c['root']] if x['id']==c['id']]
    if not rows or rows[0].get('status')!='SUCCESS': continue
    a=rows[0]
    if a['Q']>len(c['w'])+c['r']: invariant_issues.append(dict(id=c['id'],kind='Q_bound'))
    if c['policy']!='allfresh' and a['bodyL']>top(c['w'],max(a['actualExternalWrites']-c['r'],0)):
        invariant_issues.append(dict(id=c['id'],kind='L_bound'))
    if c['boundary']=='postwrite':
        postwrite_checked+=1
        if a['savedOutputs'][0]==a['liveOutputs'][0]: invariant_issues.append(dict(id=c['id'],kind='postwrite_not_distinct'))
    if c['boundary']=='doublewrite':
        doublewrite_checked+=1
        bad=sum(e['kind']=='compare' and not e['match'] for e in a['events'])
        if a['actualExternalWrites']!=2*bad: invariant_issues.append(dict(id=c['id'],kind='actual_writes_not_double'))
    if c['fixture']=='strict-safe-fresh' and c['policy']=='filter':
        for e in a['events']:
            if e['kind']=='select' and e['job']==2 and e['filter']['k']==1 and e['filter']['ell']==1:
                old_lhs=1+sum(c['w'][2:]);old_rhs=top(c['w'],2)
                strict.append(dict(id=c['id'],pattern=c['pattern'],event=e,old_whole_suffix_lhs=old_lhs,old_whole_suffix_rhs=old_rhs,old_refuses=old_lhs>old_rhs))
                if e['mode']!='fresh' or not old_lhs>old_rhs: invariant_issues.append(dict(id=c['id'],kind='strict_witness_absent'))
if not strict: invariant_issues.append(dict(kind='no_strict_witness'))
issues.extend(invariant_issues)

curves=[]
for root in roots:
    if root['boundary']!='normal' or root['policy']!='filter': continue
    rid=root['root'];baseline=rid.replace('-filter-','-allcached-')
    left=native_by_root[rid];right=native_by_root[baseline]
    for b in range(len(root['w'])+root['r']+1):
        l=[x['bodyW'] for x in left if x['status']=='SUCCESS' and x['actualExternalWrites']<=b]
        r=[x['bodyW'] for x in right if x['status']=='SUCCESS' and x['actualExternalWrites']<=b]
        lm=max(l) if l else None;rm=max(r) if r else None
        curves.append(dict(root=rid,B=b,filteredWorstW=lm,allcachedWorstW=rm))
        if lm is None or rm is None or lm>rm: issues.append(dict(kind='worst_W_domination',coordinate=curves[-1]))
root_ledger=[]
for root in roots:
    entries=[x for x in all_ledger if x['suite']=='native' and x['root']==root['root']]
    root_ledger.append(dict(root=root['root'],planned=root['paths'],observed=len(native_by_root[root['root']]),statuses=dict(collections.Counter(x['status'] for x in entries))))
save('PATH_LEDGER.json',all_ledger);save('ROOT_LEDGER.json',root_ledger)
save('DISCREPANCIES.json',issues);save('STRICT_WITNESS.json',strict);save('WORST_W_CURVES.json',curves)
summary=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='SUCCESS' if not issues and all(x['statuses']=={'SUCCESS':x['planned']} for x in results.values()) else 'FAILURE',suites=results,filter_roots=18,filter_boundary_roots=12,native_roots=len(roots),filter_queries=query_count,filter_updates=update_count,expected_rejections=dict(filter_rejections),unsafe_fresh_rejections=unsafe_fresh,atomic_rejection_failures=len(atomic_failures),native_event_count=sum(len(x['events']) for x in nr),strict_witness_paths=len(strict),postwrite_paths=postwrite_checked,doublewrite_paths=doublewrite_checked,worst_W_coordinates=len(curves),worst_W_equal=sum(x['filteredWorstW']==x['allcachedWorstW'] for x in curves),discrepancies=len(issues),not_blind_review=True,actual_client_evidence=False,latency_evidence=False,finite_test_proves_JMM=False)
save('COMPARISON.json',summary)
print(json.dumps(summary,indent=2))
sys.exit(0 if summary['status']=='SUCCESS' else 1)
