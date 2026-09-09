"""Fixed compact-policy native study; full paths, original-price oracle, source-model checks."""
from pathlib import Path
import copy,datetime,hashlib,json,os,random,signal,subprocess,sys,time,traceback
import fixed_policy,unrestricted_reference,causal,model,sequence_checker

HERE=Path(__file__).resolve().parent
DEST=HERE/'attempt01'
CORE=HERE.parent/'charged_compact_03'
JAVA=Path('/opt/homebrew/opt/openjdk@17/bin/java')
JAVAC=Path('/opt/homebrew/opt/openjdk@17/bin/javac')
STOP=datetime.datetime(2026,9,9,4,50,tzinfo=datetime.timezone.utc).timestamp()
PARAMS=dict(seed=202609090841,old_cases='all original36 native cases screened by p*delta and compatible edges; retain all screening rows',fresh_seeded=16,
    budgets=[0,1,2,3],layouts=['distinct','colliding'],concurrent_budget=3,concurrent_seeds=[11,23],price_limit=1000000,
    manual_cases=[dict(id='mixed-positive-delta-parent',jobs=[[2,0,1,1,2],[3,2,1,4,1],[4,0,3,1,2]],edges=[[0,1],[0,2]]),
                  dict(id='mixed-cached-parent',jobs=[[1,1,1,3,1],[1,0,1,2,3]],edges=[[0,1]]),
                  dict(id='zero-effective-premium',jobs=[[2,0,1,3,1],[3,0,0,0,0]],edges=[[0,1]]),
                  dict(id='common-fee-separation',jobs=[[1,1,1,2,1],[2,2,1,2,1]],edges=[[0,1]])],
    parser_controls=['unchanged','reverse_order','baseline','root_mass','duplicate_schema','nonpositive_run','wrong_schema','price_limit','zero_premium'],
    parser_errors={'reverse_order':'non-topological order','baseline':'baseline mismatch','root_mass':'root premium mass','duplicate_schema':'duplicate or malformed compact row','nonpositive_run':'run ordering','wrong_schema':'compact schema','price_limit':'bounded native price domain'},
    record_controls=['unchanged_cf','wrong_failure_epoch','failed_output_as_completed','wrong_fee','wrong_ceiling','wrong_selected_mode','under_counted_write','wrong_writer_seed'],
    record_reason_prefixes={'wrong_failure_epoch':'','failed_output_as_completed':'','wrong_fee':"('fee accounting',",'wrong_ceiling':"('bound',",'wrong_selected_mode':'','under_counted_write':'','wrong_writer_seed':'writer Random sequence differs'},
    sequence_controls=['unchanged','missing_step','duplicate_step','wrong_raw_binding','wrong_input_binding'])

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(p,x):
    with p.open('x') as f:json.dump(x,f,indent=2);f.write('\n')
def write(p,s):
    with p.open('x') as f:f.write(s)
def tprices(jobs):return [w+min(v,g+r) if v<g+r else min(w+g+r,w+p) for w,p,g,v,r in jobs]
def eligible(case):
    prices=all(p==0 or v>=g+r for w,p,g,v,r in case['jobs']);t=tprices(case['jobs'])
    compatible=all(t[u]<=t[v] for u,v in case['edges'])
    return prices,compatible
def freeze():
    DEST.mkdir()
    sources=list(HERE.glob('*.py'))+list(HERE.glob('*.java'))+[HERE/'PLAN.md',HERE/'CHECKER_SOURCE_BINDING.json']
    sources+=list(CORE.glob('*.py'))+list((CORE/'inherited').rglob('*.py'))
    sources+=[HERE.parent/'charged_callback_native_01/CASES.json']
    sources+=[HERE.parent/'charged_curves_02'/name for name in ['basis.py','compiler.py','checker.py']]
    sources+=[HERE.parent.parent/'RESUMED_20260907_1942/dependency_curves_01/curves.py']
    save(DEST/'PARAMETERS.json',dict(utc=utc(),parameters=PARAMS,sources={str(p):sha(p) for p in sources},native_execution=0))

def prepare():
    m=json.loads((DEST/'PARAMETERS.json').read_text());assert m['parameters']==PARAMS
    assert all(sha(Path(p))==h for p,h in m['sources'].items())
    # This study does not overlap the serial cold comparison.
    assert (HERE.parent/'charged_compact_scale_01/attempt01/SUMMARY.json').exists()
    sys.path.insert(0,str(CORE));import compact,verify
    old=json.loads((HERE.parent/'charged_callback_native_01/CASES.json').read_text());cases=[];screen=[]
    for source in old:
        a,b=eligible(source);screen.append(dict(id=source['id'],price_eligible=a,edge_compatible=b,selected=a and b))
        if a and b:cases.append(dict(id=source['id'],jobs=source['jobs'],edges=source['edges'],provenance='previously observed native input'))
    assert len(old)==36 and len(cases)==6
    for case in PARAMS['manual_cases']:cases.append(dict(**case,provenance='author-constructed mixed/zero/common-fee fixture'))
    rng=random.Random(PARAMS['seed'])
    for z in range(16):
        n=2+z%4;jobs=[]
        for i in range(n):
            w=1+rng.randrange(9);g=1+rng.randrange(4);r=rng.randrange(4);k=g+r
            p=1+rng.randrange(9) if i%2==0 else 0
            v=k+rng.randrange(4) if i%2==0 else rng.randrange(k)
            jobs.append([w,p,g,v,r])
        ids=list(range(n));rng.shuffle(ids);cost=tprices(jobs);order=sorted(ids,key=lambda i:cost[i])
        edges=[[order[i],order[j]] for i in range(n) for j in range(i+1,n) if rng.random()<.35]
        cases.append(dict(id=f'new-mixed-{z:03d}',jobs=jobs,edges=edges,provenance='seeded fresh authored input; not held-out application population'))
    assert len(cases)==26 and len({c['id'] for c in cases})==26
    case_lines=[];builds=[];runs=[];run_lines=[]
    for case in cases:
        pure=dict(jobs=case['jobs'],edges=case['edges']);verify.validate_input(pure)
        assert all(all(x<=1000000 for x in row) for row in case['jobs']) and eligible(case)==(True,True)
        artifact=verify.loads(json.dumps(compact.compile_case(pure)));check=verify.check(artifact,pure)
        assert artifact['route']=='compatible_reduced';case['order']=artifact['backend']['order']
        name='compact_'+case['id']+'.tsv';case['transport']=name
        encoded='schema\tcharged-root-cap-tsv-v1\norder\t'+','.join(map(str,case['order']))+'\nruns\t'+(';'.join(':'.join(map(str,r)) for r in artifact['backend']['value_slopes']) or '-')+'\nbaseline\t'+str(artifact['baseline'])+'\n'
        write(DEST/name,encoded);save(DEST/('artifact_'+case['id']+'.json'),artifact)
        cols=[','.join(str(row[k]) for row in case['jobs']) for k in range(5)]
        pred=[sum(1<<u for u,v in case['edges'] if v==i) for i in range(len(case['jobs']))]
        case_lines.append('\t'.join([case['id']]+cols+[','.join(map(str,pred)),name]))
        f,choose,paths=fixed_policy.ordinary(case);ref,_,_=unrestricted_reference.ordinary(case);full=(1<<len(case['jobs']))-1
        expected=[f(full,b) for b in PARAMS['budgets']];assert expected==[ref(full,b) for b in PARAMS['budgets']]
        builds.append(dict(id=case['id'],check=check,scalar_values=expected,artifact_sha256=sha(DEST/('artifact_'+case['id']+'.json')),transport_sha256=sha(DEST/name)))
    def add(case,layout,kind,b,outcomes,seed=0,mutant='none',trace=None,cost=None,control=False):
        rid=f'compact-run-{len(runs):06d}'
        r=dict(id=rid,case=case['id'],layout=layout,kind=kind,budget=b,outcomes=outcomes,seed=seed,mutant=mutant,control=control,expected_accept=mutant=='none')
        if trace is not None:r.update(expected_trace=trace,expected_cost=8*cost)
        runs.append(r);run_lines.append('\t'.join(map(str,[rid,case['id'],layout,kind,b,outcomes or '-',seed,mutant])))
    for case in cases:
        f,choose,paths=fixed_policy.ordinary(case);full=(1<<len(case['jobs']))-1;baseline=sum(w+min(v,g+r) for w,p,g,v,r in case['jobs'])
        for b in PARAMS['budgets']:
            possibilities=list(paths(full,b));assert max(cost for path,trace,cost in possibilities)==baseline+f(full,b)
            for layout in PARAMS['layouts']:
                for path,trace,cost in possibilities:add(case,layout,'replay',b,path,trace=trace,cost=cost)
        for layout in PARAMS['layouts']:
            for seed in PARAMS['concurrent_seeds']:add(case,layout,'concurrent',3,'',seed)
    case_map={c['id']:c for c in cases}
    for name,kind,b,layout,mutant_name in [('mixed-positive-delta-parent','postwrite',1,'colliding','live_parent'),('mixed-cached-parent','replay',0,'distinct','skip_conditional_fee')]:
        case=case_map[name];full=(1<<len(case['jobs']))-1;path=next(p for p,t,c in fixed_policy.ordinary(case)[2](full,b) if 'F' not in p)
        for mutant in ['none',mutant_name]:add(case,layout,kind,b,path,mutant=mutant,control=True)
    cf=next(r for r in runs if r['case']=='mixed-cached-parent' and r['layout']=='distinct' and r['kind']=='replay' and r['budget']==1 and r['outcomes']=='FS' and not r['control'])
    concurrent=next(r for r in runs if r['case']=='mixed-cached-parent' and r['layout']=='distinct' and r['kind']=='concurrent' and r['seed']==11)
    wrong_seed=next(x for x in range(100) if model.writer_jobs(x,2,3)!=model.writer_jobs(11,2,3))
    save(DEST/'CONTROL_TARGETS.json',dict(cached_failure=cf['id'],concurrent=concurrent['id'],wrong_seed=wrong_seed))
    write(DEST/'CASES.tsv','\n'.join(case_lines)+'\n');write(DEST/'RUNS.tsv','\n'.join(run_lines)+'\n')
    save(DEST/'CASES.json',cases);save(DEST/'RUNS.json',runs);save(DEST/'SCREENING.json',screen);save(DEST/'BUILD_CHECKS.json',builds)
    parser_units=[]
    for name in PARAMS['parser_controls']:
        target=case_map['zero-effective-premium' if name=='zero_premium' else 'common-fee-separation']
        line=next(line for line in case_lines if line.startswith(target['id']+'\t'))
        blob=(DEST/target['transport']).read_text();fields=blob.splitlines()
        if name=='reverse_order':fields[1]='order\t'+','.join(map(str,reversed(target['order'])))
        elif name=='baseline':fields[3]='baseline\t'+str(int(fields[3].split('\t')[1])+1)
        elif name=='root_mass':fields[2]='runs\t-'
        elif name=='duplicate_schema':fields.append(fields[0])
        elif name=='nonpositive_run':fields[2]='runs\t0:1'
        elif name=='wrong_schema':fields[0]='schema\twrong'
        elif name=='price_limit':
            columns=line.split('\t');values=columns[1].split(',');values[0]='1000001';columns[1]=','.join(values);line='\t'.join(columns)
        directory=DEST/'parser_inputs'/name;directory.mkdir(parents=True)
        write(directory/'CASES.tsv',line+'\n');write(directory/target['transport'],'\n'.join(fields)+'\n');write(directory/'RUNS.tsv','')
        parser_units.append(dict(id=name,directory=str(directory),expected_accept=name in ['unchanged','zero_premium']))
    save(DEST/'PARSER_UNITS.json',parser_units)
    sources={str(p):sha(p) for p in list(HERE.glob('*.py'))+list(HERE.glob('*.java'))+[HERE/'PLAN.md',HERE/'CHECKER_SOURCE_BINDING.json']}
    sources.update(m['sources']);sources.update({str(p.resolve()):sha(p.resolve()) for p in [JAVA,JAVAC,Path(sys.executable)]})
    materialized={str(p):sha(p) for p in DEST.rglob('*') if p.is_file()}
    manifest=dict(utc=utc(),cases=26,previous_native_cases=6,fresh_manual_cases=4,fresh_seeded_cases=16,screened_old=36,old_structurally_inapplicable=30,
        runs=len(runs),replay_runs=sum(r['kind']=='replay' and not r['control'] for r in runs),concurrent_runs=104,native_controls=4,replay_cells=26*4*2,
        sources=sources,materialized=materialized,parameters=PARAMS,java_version=subprocess.check_output([str(JAVA),'-version'],stderr=subprocess.STDOUT,text=True),
        compile_argv=[str(JAVAC),'-d',str(DEST/'classes'),str(HERE/'CompactChargedCallbacks.java')],run_argv=[str(JAVA),'-cp',str(DEST/'classes'),'CompactChargedCallbacks',str(DEST)],
        native_seconds=180,check_seconds=300,check_parent_seconds=320,parser_seconds_each=3,absolute_stop_utc='2026-09-09T04:50:00Z',per_search_seconds=2,per_search_pc_states=100000)
    save(DEST/'MANIFEST.json',manifest);print(json.dumps({k:manifest[k] for k in ['cases','runs','replay_runs','concurrent_runs','native_controls','replay_cells']}))

def execute():
    m=json.loads((DEST/'MANIFEST.json').read_text())
    assert all(sha(Path(p))==h for section in ['sources','materialized'] for p,h in m[section].items())
    save(DEST/'RUN_STARTED.json',dict(utc=utc(),manifest_sha256=sha(DEST/'MANIFEST.json')))
    start=time.monotonic();p=subprocess.run(m['compile_argv'],capture_output=True,text=True,timeout=30)
    write(DEST/'COMPILE.stdout',p.stdout);write(DEST/'COMPILE.stderr',p.stderr)
    save(DEST/'COMPILE_RECEIPT.json',dict(returncode=p.returncode,seconds=time.monotonic()-start,classes={str(p):sha(p) for p in (DEST/'classes').glob('*.class')}))
    if p.returncode:save(DEST/'EXECUTION_RECEIPT.json',dict(status='COMPILE_FAILURE',native_started=False));return
    cap=min(180,STOP-time.time());assert cap>0;start=time.monotonic()
    with (DEST/'RAW.jsonl').open('x') as stdout,(DEST/'RUN.stderr').open('x') as stderr:
        p=subprocess.Popen(m['run_argv'],stdout=stdout,stderr=stderr,start_new_session=True)
        try:code=p.wait(timeout=cap);status='COMPLETED' if code==0 else 'FAILURE'
        except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);code=p.wait();status='TIMEOUT'
    save(DEST/'EXECUTION_RECEIPT.json',dict(status=status,native_started=True,returncode=code,seconds=time.monotonic()-start,raw_sha256=sha(DEST/'RAW.jsonl')))
    print(json.dumps(dict(status=status,returncode=code)))

def controls(cases,runs,raw,certificates,start):
    targets=json.loads((DEST/'CONTROL_TARGETS.json').read_text());runmap={r['id']:r for r in runs};record_controls=[]
    for name in PARAMS['record_controls']:
        rid=targets['concurrent' if name=='wrong_writer_seed' else 'cached_failure'];r=copy.deepcopy(runmap[rid]);row=copy.deepcopy(raw.get(rid))
        if row is None or row.get('status')!='SUCCESS' or rid not in certificates or time.monotonic()-start>=300 or time.time()>=STOP:
            record_controls.append(dict(id=name,status='NOT_RUN',met=False,reason='fixed source run lacks a successful checked causal certificate, or cutoff; no replacement target'));continue
        if name=='wrong_failure_epoch':row['failures'][0][1]+=1
        elif name=='failed_output_as_completed':row['completed'][0]=next(e['id'] for e in row['events'] if e['kind']=='K' and e['job']==0 and not e['inside'])
        elif name=='wrong_fee':row['cost']-=8
        elif name=='wrong_ceiling':row['ceiling']+=8
        elif name=='wrong_selected_mode':row['trace'][0]='0:P'
        elif name=='under_counted_write':row['writes']-=1
        elif name=='wrong_writer_seed':r['seed']=targets['wrong_seed']
        result=causal.verify(cases[r['case']],r,row);expected=name=='unchanged_cf'
        expected_status='FEASIBLE' if expected else 'REJECTED';expected_layer=None if expected else 'source_model' if name=='wrong_writer_seed' else 'fixed_policy_and_static'
        met=result['accepted']==expected and result['status']==expected_status
        if not expected:
            prefix=PARAMS['record_reason_prefixes'][name];reason=result.get('reason')
            met=met and result.get('layer')==expected_layer and (reason=='' if prefix=='' else isinstance(reason,str) and reason.startswith(prefix))
        record_controls.append(dict(id=name,run=r,row=row,expected_accept=expected,expected_status=expected_status,expected_layer=expected_layer,result=result,met=met))
    save(DEST/'RECORD_CONTROLS.json',record_controls)
    sequence_controls=[];rid=targets['cached_failure'];certificate=certificates.get(rid)
    for name in PARAMS['sequence_controls']:
        if certificate is None or time.monotonic()-start>=300 or time.time()>=STOP:
            sequence_controls.append(dict(id=name,status='NOT_RUN',met=False));continue
        r=runmap[rid];program=model.build(cases[r['case']],r,raw[rid]);cert=copy.deepcopy(certificate)
        if name=='missing_step':cert['order'].pop()
        elif name=='duplicate_step':cert['order'].insert(0,cert['order'][0])
        elif name=='wrong_raw_binding':cert['raw_sha256']='0'*64
        elif name=='wrong_input_binding':cert['input_sha256']='0'*64
        try:sequence_checker.check(program,cert);accepted=True;error=None
        except AssertionError:accepted=False;error=traceback.format_exc()
        except Exception:accepted=None;error=traceback.format_exc()
        sequence_controls.append(dict(id=name,expected_accept=name=='unchanged',accepted=accepted,met=accepted==(name=='unchanged'),error=error,certificate=cert))
    save(DEST/'SEQUENCE_CONTROLS.json',sequence_controls)
    parser_controls=[]
    for unit in json.loads((DEST/'PARSER_UNITS.json').read_text()):
        if not (DEST/'classes/CompactChargedCallbacks.class').exists() or time.monotonic()-start>=300 or time.time()>=STOP:
            parser_controls.append(dict(id=unit['id'],status='NOT_RUN',met=False));continue
        argv=[str(JAVA),'-cp',str(DEST/'classes'),'CompactChargedCallbacks',unit['directory']]
        with (DEST/('parser_'+unit['id']+'.stdout')).open('x') as out,(DEST/('parser_'+unit['id']+'.stderr')).open('x') as err:
            try:p=subprocess.run(argv,stdout=out,stderr=err,timeout=min(3,STOP-time.time()));accepted=p.returncode==0;code=p.returncode
            except subprocess.TimeoutExpired:accepted=None;code=None
        stderr=(DEST/('parser_'+unit['id']+'.stderr')).read_text();stdout=(DEST/('parser_'+unit['id']+'.stdout')).read_text()
        if unit['expected_accept']:met=code==0 and not stdout and not stderr;expected_error=None
        else:
            expected_error='Exception in thread "main" java.lang.IllegalArgumentException: '+PARAMS['parser_errors'][unit['id']]
            met=code==1 and bool(stderr.splitlines()) and stderr.splitlines()[0]==expected_error and not stdout
        parser_controls.append(dict(id=unit['id'],expected_accept=unit['expected_accept'],expected_error=expected_error,accepted=accepted,returncode=code,argv=argv,met=met))
    save(DEST/'PARSER_CONTROLS.json',parser_controls)
    return record_controls,sequence_controls,parser_controls

def check_worker():
    m=json.loads((DEST/'MANIFEST.json').read_text())
    assert all(sha(Path(p))==h for section in ['sources','materialized'] for p,h in m[section].items())
    runs=json.loads((DEST/'RUNS.json').read_text());cases={c['id']:c for c in json.loads((DEST/'CASES.json').read_text())}
    raw={};parse_errors=[];unknown=[];duplicates=[];allowed={r['id'] for r in runs}
    if (DEST/'RAW.jsonl').exists():
        for line_no,line in enumerate((DEST/'RAW.jsonl').read_text().splitlines(),1):
            try:row=json.loads(line);rid=row['id']
            except Exception:parse_errors.append(dict(line=line_no,text=line,error=traceback.format_exc()));continue
            if rid not in allowed:unknown.append(row);continue
            if rid in raw:duplicates.append(row);continue
            raw[rid]=row
    save(DEST/'RAW_INPUT_CHECK.json',dict(parse_errors=parse_errors,unknown_rows=unknown,duplicate_rows=duplicates,recorded=len(raw),planned=len(runs)))
    save(DEST/'CHECK_STARTED.json',dict(utc=utc(),raw_sha256=sha(DEST/'RAW.jsonl') if (DEST/'RAW.jsonl').exists() else None))
    start=time.monotonic();results=[];certificates={};groups={};expected_groups={}
    for r in runs:
        if r['kind']=='replay' and not r['control']:
            key=(r['case'],r['budget'],r['layout']);expected_groups[key]=expected_groups.get(key,0)+1
    with (DEST/'VERIFICATION.jsonl').open('x') as output,(DEST/'CERTIFICATES.jsonl').open('x') as certs:
        for i,r in enumerate(runs):
            row=raw.get(r['id'])
            if row is None or time.monotonic()-start>=300 or time.time()>=STOP:
                result=dict(status='NOT_RUN',accepted=None,reason='missing native output or check cutoff')
            elif row['status']!='SUCCESS':result=dict(status=row['status'],accepted=None,reason=row.get('error'))
            else:result=causal.verify(cases[r['case']],r,row)
            if 'certificate' in result:
                cert=result.pop('certificate');certificates[r['id']]=cert
                certs.write(json.dumps(dict(id=r['id'],certificate=cert),separators=(',',':'))+'\n');certs.flush();result['certificate_sha256']=model.digest(cert)
            met=result['accepted']==r['expected_accept'] and row is not None and row['status']=='SUCCESS'
            terminal='SUCCESS' if met else result['status'] if result['status'] in ['TIMEOUT','INVALID','NOT_RUN'] else 'FAILURE'
            result.update(id=r['id'],control=r['control'],expected_accept=r['expected_accept'],met=met,terminal=terminal)
            if not met and not (DEST/'FIRST_ADVERSE.json').exists():save(DEST/'FIRST_ADVERSE.json',dict(case=cases[r['case']],run=r,row=row,result=result))
            if not r['control'] and met and r['kind']=='replay':
                key=(r['case'],r['budget'],r['layout']);g=groups.setdefault(key,dict(count=0,maximum=0,ceiling=result['static']['ceiling']));g['count']+=1;g['maximum']=max(g['maximum'],result['static']['cost'])
            results.append(result);output.write(json.dumps(result,separators=(',',':'))+'\n');output.flush()
            if (i+1)%500==0:print(json.dumps(dict(done=i+1,total=len(runs),adverse=sum(not r['met'] for r in results))),flush=True)
    rc,sc,pc=controls(cases,runs,raw,certificates,start)
    group_rows=[dict(case=key[0],budget=key[1],layout=key[2],expected_count=count,observed=groups.get(key),met=key in groups and groups[key]['count']==count and groups[key]['maximum']==groups[key]['ceiling']) for key,count in expected_groups.items()]
    save(DEST/'REPLAY_GROUPS.json',group_rows)
    from collections import Counter
    primary=[r for r in results if not r['control']];native_controls=[r for r in results if r['control']]
    summary=dict(cases=26,planned=len(runs),recorded=len(raw),primary=len(primary),primary_statuses=dict(Counter(r['terminal'] for r in primary)),native_controls=len(native_controls),native_controls_met=sum(r['met'] for r in native_controls),
        replay_cells=len(group_rows),replay_cells_met=sum(r['met'] for r in group_rows),record_controls=len(rc),record_controls_met=sum(r['met'] for r in rc),sequence_controls=len(sc),sequence_controls_met=sum(r['met'] for r in sc),parser_controls=len(pc),parser_controls_met=sum(r['met'] for r in pc),
        raw_input_integrity=not(parse_errors or unknown or duplicates),source_model_states_max=max((r.get('search_states',0) for r in results),default=0),seconds=time.monotonic()-start,
        raw_sha256=sha(DEST/'RAW.jsonl') if (DEST/'RAW.jsonl').exists() else None,verification_sha256=sha(DEST/'VERIFICATION.jsonl'),certificates_sha256=sha(DEST/'CERTIFICATES.jsonl'),
        scope='Authored n<=5 bounded-price Java fixture; compact policy path replay and existential ordering in fixed source model, not all Java schedules or production timing.')
    save(DEST/'SUMMARY.json',summary);print(json.dumps(summary,indent=2),flush=True)

def check():
    cap=min(320,STOP-time.time());assert cap>0
    with (DEST/'CHECK.stdout').open('x') as out,(DEST/'CHECK.stderr').open('x') as err:
        p=subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),'check_worker'],stdout=out,stderr=err,start_new_session=True)
        try:code=p.wait(timeout=cap);status='COMPLETED' if code==0 else 'FAILURE'
        except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);code=p.wait();status='TIMEOUT'
    save(DEST/'CHECK_PROCESS.json',dict(status=status,returncode=code))
    if (DEST/'SUMMARY.json').exists():print((DEST/'SUMMARY.json').read_text())
    else:print((DEST/'CHECK.stderr').read_text())

if __name__=='__main__':{'freeze':freeze,'prepare':prepare,'execute':execute,'check':check,'check_worker':check_worker}[sys.argv[1]]()
