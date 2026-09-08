from pathlib import Path
import collections, datetime, hashlib, json, math, shutil, subprocess, sys, time

ROOT = Path(__file__).resolve().parent
SESSION = ROOT.parent
sys.path.insert(0,str(SESSION/'final_evaluation_dag_native_01'))
import prepare as prior


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(name,data):
    with (ROOT/name).open('x') as f: json.dump(data,f,indent=2,sort_keys=True);f.write('\n')


def prepare():
    start=time.monotonic()
    case=dict(id='selected-family-k1',cp=[[3,2],[7,2],[5,6],[1,2]],
              edges=[[0,1],[0,2],[1,3]],expected_route='ideal',control=False,max_budget=4,scale=8)
    n=len(case['cp']);full=(1<<n)-1
    case['pred']=[sum(1<<u for u,v in case['edges'] if v==i) for i in range(n)]
    case['d']=math.lcm(*(c for c,p in case['cp']))
    case['weights']=[case['d']*p//c for c,p in case['cp']]
    case['lengths']=[8*c-case['pred'][i].bit_count() for i,(c,p) in enumerate(case['cp'])]
    assert all(case['d']*p==c*q for (c,p),q in zip(case['cp'],case['weights']))
    case['scalar']=prior.dev.scalar(case,4)
    case['orders']=prior.dev.topological_orders(case)
    data=json.loads((ROOT/'ARTIFACT.json').read_bytes())
    assert data['input']==dict(cp=case['cp'],edges=case['edges'])
    compiled=prior.validation.hybrid.load(data)
    assert compiled['route']=='ideal'
    (ROOT/'profiles').mkdir();(ROOT/'classes').mkdir()
    profile=ROOT/'profiles'/'selected-family-k1.tsv'
    with profile.open('x') as f:
        for mask,curve in sorted(compiled['curves'].items()):
            f.write(str(mask)+'\t'+';'.join(':'.join(map(str,row)) for row in curve)+'\n')
    units=[];cells=[]
    for b in (0,1,2,4):
        fixed,best_order=min((prior.dev.fixed_function(case['cp'],order)(full,b),order) for order in case['orders'])
        for layout in ('distinct','colliding'):
            cell=dict(id=f'family/b{b}/{layout}',case=case['id'],budget=b,layout=layout,
                      best_fixed_value=fixed,best_fixed_order=best_order,policies=[])
            for kind in prior.KINDS:
                actual,paths=prior.hybrid_policy(case,compiled) if kind=='hybrid' else prior.dev.policy(case,kind,b,best_order)
                group=[]
                for k,(outcomes,actions) in enumerate(paths(full,b)):
                    unit=dict(id=cell['id']+'/'+kind+f'/path_{k:05d}',case=case['id'],cell=cell['id'],kind=kind,
                              layout=layout,budget=b,order=best_order if kind=='fixed' else [],
                              outcomes=outcomes,actions=actions,postwrite=False)
                    unit['expected']=prior.dev.expected(case,unit)
                    group.append(unit);units.append(unit)
                target=8*case['d']*(sum(c for c,p in case['cp'])+actual(full,b))
                assert max(u['expected']['cost'] for u in group)==target
                cell['policies'].append(dict(kind=kind,units=len(group),expected_max=target,excess=actual(full,b)))
            cells.append(cell)
    assert len({u['id'] for u in units})==len(units)
    save('NATIVE_INPUTS.json',dict(cases={case['id']:case},cells=cells,units=units,selected_validation=True,final_evaluation=False))
    with (ROOT/'CASES.tsv').open('x') as f:
        f.write('\t'.join([case['id'],prior.seq([c for c,p in case['cp']]),prior.seq([p for c,p in case['cp']]),
                prior.seq(case['pred']),prior.seq(case['lengths']),prior.seq(case['weights']),str(case['d']),'8',
                'profiles/selected-family-k1.tsv'])+'\n')
    with (ROOT/'INPUTS.tsv').open('x') as f:
        for u in units:f.write('\t'.join([u['id'],u['case'],u['kind'],u['layout'],str(u['budget']),
                              prior.seq(u['order']),u['outcomes'] or '-','0'])+'\n')
    source=SESSION/'final_evaluation_dag_native_01'/'NativeDagFinal.java'
    shutil.copy2(source,ROOT/source.name)
    sources={Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None)
             and Path(m.__file__).suffix=='.py' and str(SESSION) in str(Path(m.__file__).resolve())}
    sources.update([Path(__file__).resolve(),ROOT/'PLAN.md',ROOT/'NATIVE_INPUTS.json',ROOT/'CASES.tsv',
                    ROOT/'INPUTS.tsv',ROOT/'ARTIFACT.json',ROOT/'NativeDagFinal.java',profile])
    save('NATIVE_MANIFEST.json',dict(utc=now(),selected_after_model_values=True,native_outcomes_observed=False,
        files=[dict(path=str(p),sha256=sha(p)) for p in sorted(sources)],
        java=str(prior.JAVA),javac=str(prior.JAVAC),java_sha256=sha(prior.JAVA),javac_sha256=sha(prior.JAVAC),
        compile_argv=[str(prior.JAVAC),'-d',str(ROOT/'classes'),str(ROOT/'NativeDagFinal.java')],
        execute_argv=[str(prior.JAVA),'-Xmx256m','-cp',str(ROOT/'classes'),'NativeDagFinal',str(ROOT)],
        compile_timeout=30,execute_timeout=60,check_timeout=30,units=len(units),roots=4,layouts=8,policy_cells=40,
        paths_by_kind=dict(collections.Counter(u['kind'] for u in units)),
        topological_orders=len(case['orders']),preparation_seconds=time.monotonic()-start))
    print(json.dumps(dict(units=len(units),policy_cells=40,paths_by_kind=dict(collections.Counter(u['kind'] for u in units)))))


def run():
    manifest=json.loads((ROOT/'NATIVE_MANIFEST.json').read_text())
    for r in manifest['files']:assert sha(r['path'])==r['sha256'],r['path']
    assert sha(manifest['java'])==manifest['java_sha256'] and sha(manifest['javac'])==manifest['javac_sha256']
    save('NATIVE_RUN_STARTED.json',dict(utc=now(),manifest_sha256=sha(ROOT/'NATIVE_MANIFEST.json')))
    receipt=dict(start=now());start=time.monotonic()
    try:
        t=time.monotonic()
        try:
            result=subprocess.run(manifest['compile_argv'],capture_output=True,text=True,timeout=30)
            receipt['compile']=dict(returncode=result.returncode,stdout=result.stdout,stderr=result.stderr,
                                    timeout=False,seconds=time.monotonic()-t)
        except subprocess.TimeoutExpired as e:
            receipt['compile']=dict(returncode=None,timeout=True,stdout=str(e.stdout),stderr=str(e.stderr),seconds=time.monotonic()-t)
            return
        if result.returncode:return
        save('CLASS_RECEIPT.json',dict(files=[dict(path=str(p),sha256=sha(p)) for p in sorted((ROOT/'classes').glob('*.class'))]))
        with (ROOT/'NATIVE_RAW.jsonl').open('xb') as out,(ROOT/'NATIVE_STDERR.txt').open('xb') as err:
            t=time.monotonic()
            try:
                result=subprocess.run(manifest['execute_argv'],stdout=out,stderr=err,timeout=60)
                receipt['execute']=dict(returncode=result.returncode,timeout=False,seconds=time.monotonic()-t)
            except subprocess.TimeoutExpired:
                receipt['execute']=dict(returncode=None,timeout=True,seconds=time.monotonic()-t)
    finally:
        receipt.update(end=now(),seconds=time.monotonic()-start)
        save('NATIVE_RUN_RECEIPT.json',receipt);print(json.dumps(receipt,indent=2))


def check():
    start=time.monotonic();data=json.loads((ROOT/'NATIVE_INPUTS.json').read_text())
    seen=collections.defaultdict(list);parse=[];raw_order=[]
    for k,line in enumerate((ROOT/'NATIVE_RAW.jsonl').read_text().splitlines()):
        try:r=json.loads(line);seen[r['id']].append(r);raw_order.append(r['id'])
        except Exception as e:parse.append(dict(line=k,error=repr(e)))
    counts=collections.Counter();adverse=[];good={}
    for u in data['units']:
        rows=seen.pop(u['id'],[]);issues=[]
        if not rows:status='NOT_RUN'
        elif len(rows)!=1:status='INVALID'
        else:
            r=rows[0];status=r['status']
            expected=prior.dev.expected(data['cases'][u['case']],u)
            assert expected==u['expected']
            if status=='SUCCESS':
                issues=[dict(field=k,expected=v,actual=r.get(k)) for k,v in expected.items() if r.get(k)!=v]
                if issues:status='FAILURE'
                else:good[u['id']]=r
        counts[status]+=1
        if status!='SUCCESS':adverse.append(dict(id=u['id'],status=status,issues=issues,raw=rows))
    comparisons=[];gaps=[]
    for cell in data['cells']:
        row=dict(id=cell['id'],budget=cell['budget'],layout=cell['layout'],policies={})
        for p in cell['policies']:
            ids=[u['id'] for u in data['units'] if u['cell']==cell['id'] and u['kind']==p['kind']]
            actual=max(good[i]['cost'] for i in ids) if all(i in good for i in ids) else None
            row['policies'][p['kind']]=dict(actual_max=actual,expected_max=p['expected_max'],abstract_excess=p['excess'],units=len(ids))
            if actual is not None and actual!=p['expected_max']:gaps.append([cell['id'],p['kind'],actual,p['expected_max']])
        comparisons.append(row)
    report=dict(utc=now(),denominator=len(data['units']),status_counts=dict(counts),adverse=adverse,
                parse_errors=parse,unexpected=list(seen),raw_order_matches=raw_order==[u['id'] for u in data['units']],
                max_disagreements=gaps,comparisons=comparisons,selected_validation=True,final_evaluation=False,
                seconds=time.monotonic()-start,raw_sha256=sha(ROOT/'NATIVE_RAW.jsonl'))
    save('NATIVE_SUMMARY.json',report)
    print(json.dumps({k:v for k,v in report.items() if k!='comparisons'},indent=2))


if __name__=='__main__':{'prepare':prepare,'run':run,'check':check}[sys.argv[1]]()
