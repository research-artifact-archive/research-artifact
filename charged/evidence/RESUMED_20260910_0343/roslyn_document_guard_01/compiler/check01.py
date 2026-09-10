from pathlib import Path
import collections,copy,datetime,hashlib,json
D=Path(__file__).resolve().parent
NAMES=['FixtureA','FixtureB','FixtureC','FixtureD']
def require(c,m):
    if not c:raise AssertionError(m)
def source(p,scenario,bg,fg):
    if p==0:return 'public static class Numbers { public const string Value = "one"; }\n' if bg and scenario=='library_type' else 'public static class Numbers { public const int Value = '+str(7 if bg and scenario=='library_constant' else 1)+'; }\n'
    if p==3:return 'public static class Spare { public const int Value = '+str(9 if bg and scenario=='unrelated_spare' else 1)+'; }\n'
    suffix=' + 1' if fg else ' - 1' if bg and scenario=='target_writer' else ''
    alt_suffix=' + "!"' if fg else ''
    return 'public static class Reader {\n#if ALT\n public static string Read() => Numbers.Value'+alt_suffix+';\n#else\n public static int Read() => Numbers.Value'+suffix+';\n#endif\n}\n'
def projection(s,scenario):
    require(s['status']=='PASS','snapshot status');bg=s['background'];fg=s['foreground']
    require(type(bg) is bool and type(fg) is bool,'state flags')
    require(s['actual']==s['expected'],'Workspace/direct compiler mismatch')
    require(list(s['actual'])==NAMES,'project denominator/order')
    value_type='string' if bg and scenario=='library_type' else 'int'
    value='one' if value_type=='string' else 7 if bg and scenario=='library_constant' else 1
    for p,name in enumerate(NAMES):
        actual=s['actual'][name];feature=actual['feature'];alt=p==1 and bg and scenario=='target_parse'
        reference=p in [1,2] and not(p==2 and bg and scenario=='linked_reference_removed')
        require(actual['source']==source(p,scenario,bg,fg),'predeclared source')
        require(actual['symbols']==(['ALT'] if alt else []) and actual['references']==(['FixtureA'] if reference else []),'parse/reference state')
        require(feature['assembly']==name,'compilation assembly')
        if p in [0,3]:
            expected_type=value_type if p==0 else 'int';expected_value=value if p==0 else 9 if bg and scenario=='unrelated_spare' else 1
            require(feature['exported_value_type']==expected_type and feature['exported_constant']==expected_value,'exported field type/constant')
            require(feature['read_return_type'] is None and feature['access_symbol_type'] is None and feature['access_symbol_assembly'] is None and feature['access_has_constant'] is False and feature['access_constant'] is None,'non-reader feature')
            diagnostic_ids=[]
        else:
            return_type='string' if alt else 'int'
            require(feature['read_return_type']==return_type and feature['exported_value_type'] is None and feature['exported_constant'] is None,'Reader declaration')
            require(feature['access_symbol_type']==(value_type if reference else None) and feature['access_symbol_assembly']==('FixtureA' if reference else None),'semantic symbol dependency')
            require(feature['access_has_constant']==reference and feature['access_constant']==(value if reference else None),'semantic constant dependency')
            # These expected C# error classes follow directly from the authored expressions, independently of the Workspace/direct-compiler equality check.
            diagnostic_ids=['CS0103'] if not reference else ['CS0029'] if (return_type=='int' and value_type=='string') or (return_type=='string' and not fg) else []
        require([x['id'] for x in feature['diagnostics']]==diagnostic_ids,'expected C# diagnostics')
        require(all(x['severity']=='Error' for x in feature['diagnostics']),'diagnostic severity')
        require([x['id'] for x in feature['emit_diagnostics']]==diagnostic_ids and feature['emit_success']==(not diagnostic_ids),'emit result')
    return len(s['actual'])
def check(row):
    require(row['status']=='SUCCESS','native unit status');require(row['writes']==1,'single background change')
    scenario=row['scenario'];snapshots=row['snapshots'];labels=[x['label'] for x in snapshots]
    require(len(labels)==len(set(labels)) and labels[0]=='initial' and labels[-1]=='final' and labels.count('background')==1,'snapshot labels/denominator')
    require(snapshots[0]['background']==False and snapshots[0]['foreground']==False,'initial state')
    require(snapshots[-1]['background']==True and snapshots[-1]['foreground']==True,'final state')
    middle=next(s for s in snapshots if s['label']=='background');require(middle['background']==True and middle['foreground']==False,'background state')
    for s in snapshots:projection(s,scenario)
    warm=row['warm_checks']
    if row['cache']=='cold':require(warm==[],'cold cache control')
    else:
        require(row['cache']=='warm' and all(x in [w['label'] for w in warm] for x in ['initial','background','final']),'warm cache denominator')
        for s in warm:
            projection(s,scenario);later=next(x for x in snapshots if x['label']==s['label']);require(s['actual']==later['actual'],'retained warmed snapshot changed')
    mode=row['mode'];r=row['r'];c=row['counters'];eligible=scenario in ['library_type','library_constant','unrelated_spare','linked_reference_removed']
    if mode=='baseline':require(c=={},'unmodified counter control')
    else:
        if mode=='original':expected=[2,2,0,1,1,0]
        elif mode=='two':expected=[1,0,1,0,0,0] if r==0 else [2,1,1,1,1,0]
        elif mode=='rebase' and eligible:expected=[1,1,0,1,0,1]
        else:require(mode in ['three','rebase'],'mode');expected=[1,1,1,1,0,0] if r==0 else [2,2,0,1,1,0]
        require([c[x] for x in ['Calls','PreparedOutside','PreparedInside','Mismatches','CheapFailures','Rebases']]==expected,'fixed one-change resource/eligibility counts')
    return {'snapshots':len(snapshots),'warm_snapshots':len(warm),'project_projections':4*(len(snapshots)+len(warm))}
def controls(sample):
    variants=[]
    def add(name,fn):x=copy.deepcopy(sample);fn(x);variants.append((name,x))
    add('final_diagnostics',lambda x:x['snapshots'][-1]['actual']['FixtureB']['feature']['diagnostics'].clear())
    def shared(x,key,value):
        for side in ['actual','expected']:x['snapshots'][-1][side]['FixtureB']['feature'][key]=value
    add('shared_stale_symbol_type',lambda x:shared(x,'access_symbol_type','int'))
    add('shared_stale_constant',lambda x:shared(x,'access_constant',99))
    add('retained_source',lambda x:x['snapshots'][0]['actual']['FixtureA'].__setitem__('source',''))
    add('write_denominator',lambda x:x.__setitem__('writes',0))
    add('rebase_eligibility',lambda x:x['counters'].__setitem__('Rebases',0))
    add('missing_final',lambda x:x['snapshots'].pop())
    add('duplicate_snapshot',lambda x:x['snapshots'].insert(1,copy.deepcopy(x['snapshots'][0])))
    results=[]
    for name,x in variants:
        try:check(x);detected=False
        except (AssertionError,KeyError,IndexError,TypeError,StopIteration):detected=True
        results.append({'name':name,'detected':detected})
    require(all(x['detected'] for x in results),'undetected corruption');return results
def main():
    O=D/'run01';dest=O/'check01';dest.mkdir();planned=[x.split('\t') for x in (D/'UNITS.tsv').read_text().splitlines()];details=[];rows=[]
    for plan in planned:
        p=O/plan[0]/'stdout.jsonl';raw=[json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []
        row=raw[0] if len(raw)==1 else None;status='INVALID';error='missing/non-single output';counts={}
        if row is not None:
            rows.append(row)
            try:
                require([str(row[k]) for k in ['id','mode','r','scenario','cache']]==plan,'input identity');counts=check(row);status='PASS';error=''
            except Exception as e:status='FAIL';error=type(e).__name__+': '+str(e)
        details.append({'id':plan[0],'status':status,'native_status':row.get('status') if row else 'MISSING','error':error,**counts})
    sample=next((x for x in rows if x['status']=='SUCCESS' and x['mode']=='rebase' and x['r']==0 and x['scenario']=='library_type' and x['cache']=='warm'),None)
    ctrl=controls(sample) if sample else []
    receipt={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS' if len(details)==96 and all(x['status']=='PASS' for x in details) and len(ctrl)==8 else 'FAIL','planned':96,'native_rows':len(rows),'native_statuses':dict(collections.Counter(x['status'] for x in rows)),'checker_statuses':dict(collections.Counter(x['status'] for x in details)),'counts':{k:sum(x.get(k,0) for x in details) for k in ['snapshots','warm_snapshots','project_projections']},'controls':ctrl,'scope':'Finite Workspace versus direct compiler state projections plus independently specified expected types/constants/errors. Shared compiler engine, authored inputs, no full-language or arbitrary-host proof.'}
    (dest/'DETAILS.json').write_text(json.dumps(details,indent=2)+'\n');(dest/'RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
    for x in details:
        if x['status']!='PASS':print(json.dumps(x))
if __name__=='__main__':main()
