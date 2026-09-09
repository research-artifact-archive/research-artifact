"""Isolated replay workers. Saved result counts are never enlarged by these runs."""
from pathlib import Path
import collections,copy,hashlib,importlib.util,itertools,json,os,shutil,subprocess,sys,time

HERE=Path(__file__).resolve().parent
DATA=HERE/'evidence/RESUMED_20260909_0056'
OUT=Path(sys.argv[2])
QUICK='--quick' in sys.argv[3:]

def read(p):return json.loads(p.read_text())
def lines(p):return [json.loads(s) for s in p.read_text().splitlines()]
def save(name,x):
    with (OUT/name).open('x') as f:json.dump(x,f,indent=2);f.write('\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(name,p):
    sys.path.insert(0,str(p.parent))
    spec=importlib.util.spec_from_file_location(name,p);module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module;spec.loader.exec_module(module);return module
def select(rows,n=12):return rows[:n] if QUICK else rows
def indexed(rows):
    result={r['id']:r for r in rows};assert len(result)==len(rows);return result
def accepted(fn,arg):
    try:fn(arg);return True
    except (AssertionError,ValueError,KeyError,IndexError,TypeError):return False

def curves():
    d=DATA/'charged_curves_02';m=load('charged_curve_study',d/'study.py')
    inputs=read(d/'INPUTS.json');old=indexed(lines(d/'RAW.jsonl'));assert len(inputs)==len(old)==3183
    rows=[]
    for case in select(inputs):
        direct=m.compiler.compile_case(case);certificate=m.basis.compile_case(case)
        assert direct['curves']==certificate['curves']
        encoded=json.dumps(certificate,separators=(',',':'));checked=m.checker.check(json.loads(encoded))
        assert hashlib.sha256(encoded.encode()).hexdigest()==old[case['id']]['artifact_sha256']
        rows.append(dict(id=case['id'],status='SUCCESS',check=checked))
    controls=m.controls();assert len(controls)==11 and all(r['status']=='SUCCESS' for r in controls)
    save('RESULTS.json',rows);save('CONTROLS.json',controls)
    return dict(retained_inputs=3183,replayed=len(rows),controls=11,artifact_bytes_match=True)

def native(java=False):
    d=DATA/'charged_callback_recheck_03';m=load('charged_causal_study',d/'study.py')
    old=DATA/'charged_callback_native_01';runs=read(old/'RUNS.json');cases=indexed(read(old/'CASES.json'))
    raw=lines(old/'RAW.jsonl')
    if java:
        java_bin=os.environ.get('JAVA_BIN','java');javac=os.environ.get('JAVAC_BIN','javac')
        version=subprocess.check_output([java_bin,'-version'],stderr=subprocess.STDOUT,text=True)
        assert 'version "17.' in version,'native replay requires Java17'
        target=OUT/'java-input';target.mkdir();classes=OUT/'classes';classes.mkdir()
        for p in old.glob('*.tsv'):shutil.copy2(p,target/p.name)
        shutil.copy2(old/'ChargedCallbacks.java',target/'ChargedCallbacks.java')
        comp=subprocess.run([javac,'--release','17','-d',str(classes),str(target/'ChargedCallbacks.java')],capture_output=True,timeout=30)
        (OUT/'javac.stdout').write_bytes(comp.stdout);(OUT/'javac.stderr').write_bytes(comp.stderr);assert comp.returncode==0
        with (OUT/'NEW_NATIVE_RAW.jsonl').open('xb') as f,(OUT/'java.stderr').open('xb') as e:
            result=subprocess.run([java_bin,'-ea','-cp',str(classes),'ChargedCallbacks',str(target)],stdout=f,stderr=e,timeout=180)
        assert result.returncode==0;raw=lines(OUT/'NEW_NATIVE_RAW.jsonl');save('JAVA_VERSION.json',dict(version=version,source_sha256=sha(target/'ChargedCallbacks.java')))
    rows=indexed(raw);assert len(rows)==len(runs)==3098 and set(rows)=={r['id'] for r in runs}
    chosen=select([r for r in runs if not r['control']])+[r for r in runs if r['control']]
    result_rows=[]
    with (OUT/'VERIFICATION.jsonl').open('x') as f:
        for run in chosen:
            result=m.verify(cases[run['case']],run,rows[run['id']])
            assert result['accepted']==run['expected_accept'],(run['id'],result)
            result.pop('certificate',None);result.update(id=run['id'],expected_accept=run['expected_accept'])
            f.write(json.dumps(result,separators=(',',':'))+'\n');f.flush();result_rows.append(result)
    controls=[]
    for item in read(d/'attempt01/CONTROLS_INPUT.json'):
        result=m.verify(item['case'],item['run'],item['row'])
        assert result['accepted']==item['expected_accept'] and result['status']==item['expected_status']
        if 'expected_layer' in item:assert result['layer']==item['expected_layer'] and result['reason']==item['expected_reason']
        result.pop('certificate',None);controls.append(dict(id=item['id'],result=result))
    # Sequence controls bind the original raw records, not a new concurrent schedule.
    retained=indexed(lines(old/'RAW.jsonl'));target=next(r for r in runs if r['id']=='run-000364')
    sequence=[]
    for item in read(d/'attempt01/SEQUENCE_CONTROLS.json'):
        if item['id'].startswith('constructed_'):
            c,r,row=m.bin_witness('colliding' if item['id']=='constructed_colliding_bin' else 'distinct')
        else:c,r,row=cases[target['case']],target,retained[target['id']]
        program=m.model.build(c,r,row)
        yes=accepted(lambda cert:m.sequence_checker.check(program,cert),item['certificate'])
        assert yes==item['expected_accept'],item['id'];sequence.append(dict(id=item['id'],accepted=yes))
    assert len(controls)==12 and len(sequence)==11
    save('RECORD_CONTROLS.json',controls);save('SEQUENCE_CONTROLS.json',sequence)
    return dict(retained_runs=3098,replayed_records=len(chosen),record_controls=12,sequence_controls=11,new_native_runs=len(raw) if java else 0,scope='Existential source-model microevent ordering; shared translation')

def deephaven():
    reports=[]
    for name,count in [('deephaven_prefix_import_02',216),('deephaven_event_graph_01',12),('deephaven_phase_policy_01',108),('deephaven_key_action_01',36)]:
        d=DATA/name;checker=load(name+'_check',d/'attempt01/sources/check_trace.py')
        raw=lines(d/'attempt01/RAW.jsonl');assert len(indexed(raw))==count
        rows=[checker.check(row) for row in select(raw)]
        controls=[]
        for p in sorted((d/'attempt01').glob('check*/CONTROL_*.json')):
            yes=accepted(checker.check,read(p));assert not yes,(name,p.name)
            controls.append(dict(file=str(p.relative_to(d)),accepted=yes))
        save(name+'.json',dict(results=rows,controls=controls))
        reports.append(dict(study=name,retained=count,replayed=len(rows),controls=len(controls)))
    strict=load('charged_key_strict',DATA/'deephaven_key_action_recheck_02/strict.py')
    raw=lines(DATA/'deephaven_key_action_01/attempt01/RAW.jsonl')
    for row in select(raw):strict.check(row)
    controls=read(DATA/'deephaven_key_action_recheck_02/attempt01/CONTROLS_INPUT.json')
    assert len(controls)==21
    for item in controls:assert accepted(strict.check,item['row'])==item['expected_accept'],item['id']
    return dict(studies=reports,strict_key_records=len(select(raw)),strict_key_controls=21,new_native_runs=0,prefix_aborts_observed=0)

def scale():
    curve=load('charged_scale_curve_checker',DATA/'charged_curves_02/checker.py')
    by_value={};reports=[]
    for name,count in [('charged_compiler_scale_01',224),('charged_compiler_scale_03',144)]:
        d=DATA/name;old=lines(d/'attempt01/RAW.jsonl');units=read(d/'attempt01/UNITS.json')
        assert len(indexed(old))==len(indexed(units))==count
        point=load(name+'_point',d/'point_checker.py');checked=0;scope=collections.Counter()
        for row in old:
            if row['status']!='SUCCESS':continue
            unit=next(x for x in units if x['id']==row['id'])
            assert row['budgets']==unit['budgets']
            result=row['worker_result'];assert result['status']=='SUCCESS' and result['budgets']==row['budgets']
            for b,v in zip(row['budgets'],result['values']):
                key=(row['case_id'],b)
                assert key not in by_value or by_value[key]==v
                by_value[key]=v
            path=d/'attempt01/runs'/row['id']/'CERTIFICATE.json'
            if path.exists() and (not QUICK or checked<8):
                cert=read(path);assert cert['input']==unit['case']
                if row['method']=='ALL':
                    curve.check(cert);vs=[curve.value(cert['curves'][str(cert['full'])],b) for b in row['budgets']]
                else:vs=point.check(cert)['values'];assert cert['budgets']==row['budgets']
                assert vs==result['values'];checked+=1
            scope[result['certificate_scope']]+=1
        reports.append(dict(study=name,retained=count,original_status_counts=dict(collections.Counter(r['status'] for r in old)),certificates_rechecked=checked,output_scopes=dict(scope)))
    d=DATA/'charged_compiler_scale_03';conf=load('charged_scale_conformance',d/'conformance.py')
    inputs=read(DATA/'charged_compiler_scale_01/conformance01/INPUTS.json');assert len(inputs)==76
    conformance=[]
    for item in select(inputs):
        case=item['case'];allbudgets=json.loads(json.dumps(conf.basis.compile_case(case)));conf.checker.check(allbudgets)
        values=[conf.checker.value(allbudgets['curves'][str(allbudgets['full'])],b) for b in conf.BUDGETS]
        points=conf.oracle.solve_many(case,conf.BUDGETS);cert=json.loads(json.dumps(points['artifact']))
        assert values==conf.point_checker.check(cert)['values']==points['values']==conf.direct.solve_many(case,conf.BUDGETS)['values']
        assert values[:4]==conf.generic.solve_many(case,[0,1,2,3])['values']
        conformance.append(dict(id=item['id'],values=values))
    controls=read(d/'conformance01/CONTROLS.json');assert len(controls)==11
    for item in controls:assert accepted(conf.point_checker.check,item['artifact'])==item['expected_accept']
    save('CONFORMANCE.json',conformance)
    return dict(campaigns=reports,shared_saved_values=len(by_value),conformance_inputs=len(conformance),point_controls=11,new_timing_samples=0)

def calibration():
    d=DATA/'charged_api_calibration_01';m=load('charged_calibration_analysis',d/'analyze.py')
    # Reanalyze copies so the exact analysis function cannot overwrite its source output.
    target=OUT/'analysis-input';shutil.copytree(d/'attempt01',target/'attempt01',ignore=shutil.ignore_patterns('ANALYSIS01.json'))
    m.HERE=target;m.main();fresh=read(target/'attempt01/ANALYSIS01.json');old=read(d/'attempt01/ANALYSIS01.json')
    assert fresh==old,'retained calibration analysis differs'
    rows=read(d/'attempt01/RESULTS.json');assert len(rows)==72 and all(r['status']=='SUCCESS' for r in rows)
    samples=sum(sum(len(f) for f in read(d/'attempt01'/r['id']/'JMH.json')[0]['primaryMetric']['rawData']) for r in rows)
    assert samples==720 and all(x['exact_prices_ns']['p']=='0' for x in fresh['fits'].values())
    return dict(cells=72,samples=720,analysis_matches=True,grid_partition=fresh['grid_partition'],strict_by_weight=fresh['strict_by_weight'],new_measurements=0)

def ordering():
    d=DATA/'charged_order_01';m=load('charged_order_replay',d/'study.py')
    inputs=read(d/'INPUTS.json');old=indexed(lines(d/'RAW.jsonl'));catalogues=indexed(lines(d/'ALL_ORDERS.jsonl'));assert len(inputs)==len(old)==len(catalogues)==874
    rows=[]
    for case in select(inputs):
        values,decisions,pred=m.scalar(case);adaptive=values[(1<<len(case['jobs']))-1]
        fixed,witness,catalogue=m.fixed(case,pred)
        assert adaptive==old[case['id']]['adaptive'] and fixed==old[case['id']]['fixed']
        assert json.loads(json.dumps(catalogue))==catalogues[case['id']]['orders']
        rows.append(dict(id=case['id'],adaptive=adaptive,fixed=fixed,orders=len(catalogue)))
    save('ORDER_COMPARISONS.json',rows)
    d=DATA/'charged_common_price_order_01';inputs=read(d/'attempt01/INPUTS.json');old=indexed(lines(d/'attempt01/RAW.jsonl'))
    assert len(inputs)==len(old)==17424
    common=[]
    for item in select(inputs):
        case=item['case'];full=m.compiler.compile_case(case)
        order=old[item['id']]['order'];fixed=dict(jobs=case['jobs'],edges=list(zip(order,order[1:])))
        chain=m.compiler.compile_case(fixed)
        f=full['curves'][full['full']];g=chain['curves'][chain['full']]
        assert json.loads(json.dumps(f))==old[item['id']]['full_profile'] and json.loads(json.dumps(g))==old[item['id']]['ordered_profile']
        assert f==g;common.append(dict(id=item['id'],profiles_equal=True))
    save('COMMON_FINITE_MATCHES.json',common)
    counter=load('charged_known_common_counter',DATA/'charged_common_price_counter_02/check.py')
    results=[]
    for case in read(DATA/'charged_common_price_counter_02/attempt01/INPUTS.json'):
        values=counter.scalar(case,9);ascending=counter.scalar(dict(jobs=case['jobs'],edges=[[0,1],[1,2],[2,3]]),9)
        reverse=counter.scalar(dict(jobs=case['jobs'],edges=[[3,0],[0,1],[1,2]]),9)
        z=case['jobs'][0][0];assert [ascending[1],reverse[1],values[1]]==[6*z,5*z,5*z]
        results.append(dict(id=case['id'],ascending=ascending,alternative=reverse,unrestricted=values))
    save('COMMON_COUNTEREXAMPLE.json',results)
    return dict(retained_order_inputs=874,replayed_order_inputs=len(rows),retained_common_inputs=17424,replayed_common_inputs=len(common),common_counterexample_inputs=2,common_general_ascending_order='REFUTED')

def refutations():
    reports=[];holding_old=indexed(lines(DATA/'charged_guard_holding_01/RAW.jsonl'))
    for name,filename in [('charged_guaranteed_01','explore.py'),('charged_guaranteed_02','explore.py'),('charged_guard_targeted_03','primitive.py')]:
        d=DATA/name;m=load(name+'_primitive',d/filename);inputs=read(d/'INPUTS.json');old=indexed(lines(d/'RAW.jsonl'))
        assert len(inputs)==len(old);rows=[];held_rows=[]
        for case in select(inputs):
            graph=m.graph(case);values,policy,rank=m.solve_validate(graph)
            actual=[values[s] for s in graph[1]];expected=m.macro(case)
            previous=old[case['id']];assert previous['status']=='SUCCESS'
            assert actual==previous['primitive'] and expected==previous['macro']
            rows.append(dict(id=case['id'],primitive=actual,macro=expected))
            if name=='charged_guaranteed_02':
                n=len(case['jobs']);u=(m.U,)*n;ready=[i for i in range(n) if not any(j==i for h,j in case['edges'])];cells=[]
                for i in ready:
                    w,p,g,v,r=case['jobs'][i];l=list(u);l[i]=m.L;l=tuple(l);lc=list(u);lc[i]=m.LC;lc=tuple(lc);done=list(u);done[i]=m.D;done=tuple(done)
                    for b in range(7):
                        root=values[(u,b)];held=values[(l,b)];immediate=min(r+root,w+p+r+values[(done,b)])
                        cell=dict(job=i,budget=b,held=held,immediate=immediate,strict=held<immediate)
                        if b:
                            before=min(r+values[(u,b-1)],w+p+r+values[(done,b-1)])
                            acquire=w+g+max(values[(lc,b)],values[(l,b-1)]);restricted=w+g+max(values[(lc,b)],before)
                            cell.update(root=root,prepare_acquire=acquire,prepare_acquire_immediate=restricted,root_relevant=acquire==root and restricted>root)
                        cells.append(cell)
                assert cells==holding_old[case['id']]['cells'];held_rows.append(dict(id=case['id'],cells=cells))
            if name=='charged_guard_targeted_03':
                clipped=copy.deepcopy(case);mu=exposure=0
                for job in clipped['jobs']:
                    w,p,g,v,r=job;minimum=min(v,g+r)
                    if minimum>0 and p>minimum:mu=max(mu,minimum);exposure+=p-minimum;job[1]=minimum
                flat=m.macro(clipped);assert flat==previous['flat'] and mu==previous['mu'] and exposure==previous['exposure']
                assert all(max(f,h-b*mu)<=v<=h and 0<=h-f<=exposure for b,(v,h,f) in enumerate(zip(actual,expected,flat)))
        save(name+'.json',rows)
        if held_rows:save('HELD_GUARD_CELLS.json',held_rows)
        reports.append(dict(study=name,retained=len(inputs),replayed=len(rows),holding_inputs_replayed=len(held_rows),original_statuses=dict(collections.Counter(r['status'] for r in old.values()))))
    return dict(studies=reports,universal_exposed_guard_equality='UNPROVED')

def main():
    assert __debug__
    start=time.monotonic();name=sys.argv[1]
    result=native(True) if name=='native-java' else globals()[name]()
    result.update(status='SUCCESS',quick=QUICK,seconds=time.monotonic()-start,replay_only=True,new_evaluation_population=False)
    save('SUMMARY.json',result);print(json.dumps(result,indent=2))

if __name__=='__main__':main()
