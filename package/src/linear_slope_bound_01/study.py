from pathlib import Path
from fractions import Fraction
import collections,datetime,hashlib,importlib.util,itertools,json,os,signal,sys,time,traceback,types
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent;S=ROOT.parent
spec=importlib.util.spec_from_file_location('slope_bound_oldhybrid',S/'dependency_hybrid_01/hybrid.py')
hybrid=importlib.util.module_from_spec(spec);spec.loader.exec_module(hybrid)
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(path,data):
    with Path(path).open('x') as f:json.dump(data,f,indent=2,sort_keys=True);f.write('\n')
def rows(path):return [json.loads(x) for x in Path(path).read_text().splitlines()]

def basis(profile,costs):
    assert profile and profile[0][0]==profile[0][1]==0 and profile[-1][2]==0
    allowed=sorted({0,*costs});assert all(type(c) is int and c>=0 for c in allowed)
    for k,(x,v,r) in enumerate(profile):
        assert all(type(z) is int and z>=0 for z in [x,v,r])
        if k:
            a,b,s=profile[k-1]
            assert x>a and s>r and b+(x-a)*s==v
    lines=[(max(v-c*x for x,v,r in profile),c) for c in allowed]
    assert all(0<=a<=profile[-1][1] for a,c in lines)
    intervals=0;positions=0
    for k,(x,v,r) in enumerate(profile):
        if k==len(profile)-1:
            assert any(c==0 and a==v for a,c in lines)
            continue
        span=profile[k+1][0]-x
        whole=False;zeros=set()
        for a,c in lines:
            intercept=a+c*x-v;slope=c-r
            assert min(intercept,intercept+slope*(span-1))>=0
            if slope==0:
                whole|=intercept==0
            elif (-intercept)%slope==0:
                offset=(-intercept)//slope
                if 0<=offset<span:zeros.add(offset)
        if not whole and len(zeros)!=span:
            missing=0
            for z in sorted(zeros):
                if z==missing:missing+=1
                elif z>missing:break
            b=x+missing
            raise AssertionError(dict(kind='basis_gap',budget=b,candidate=v+r*missing,
                supporting_min=min(a+c*b for a,c in lines),profile=profile,allowed=allowed))
        intervals+=1;positions+=span
    d=len(allowed)-1
    assert len(profile)-1<=2*d,(len(profile)-1,d)
    return dict(positive_runs=len(profile)-1,distinct_positive_costs=d,
        supporting_lines=lines,finite_intervals=intervals,finite_positions=positions)

def packed_profile(data):
    profile=[];x=v=0
    for h,m in data['value_slopes']:
        profile.append([x,v,h]);x+=m;v+=h*m
    profile.append([x,v,0]);return profile

def artifact(data):
    cp=data['input']['cp'];n=len(cp)
    if data.get('route')=='ordered':
        profile=packed_profile(data);result=basis(profile,[c for c,p in cp])
        assert profile[-1][1]==sum(p for c,p in cp)
        return dict(curves=1,segments=len(profile),positive_runs=result['positive_runs'],
            max_positive_runs=result['positive_runs'],basis_lines=len(result['supporting_lines']))
    assert data.get('route','ideal')=='ideal'
    total=positive=largest=count=line_count=0;bound=0
    for mask,profile in data['curves'].items():
        mask=int(mask);jobs=[j for j in range(n) if mask>>j&1]
        result=basis(profile,[cp[j][0] for j in jobs])
        assert profile[-1][1]==sum(cp[j][1] for j in jobs)
        count+=1;total+=len(profile);positive+=result['positive_runs']
        largest=max(largest,result['positive_runs']);line_count+=len(result['supporting_lines']);bound+=2*len(jobs)+1
    assert total<=bound<=(n+1)*2**n
    return dict(curves=count,segments=total,positive_runs=positive,max_positive_runs=largest,basis_lines=line_count)

def algebra(u):
    lines=u['lines'];P=u['constant'];g=[min(a+c*b for a,c in lines) for b in range(P+3)]
    assert g[0]==0 and g[-2:]==[P,P]
    results=[]
    for c in range(1,7):
        A=max(value-c*b for b,value in enumerate(g));D=[0]
        for b in range(1,len(g)):D.append(D[-1]+max(c,g[b]-g[b-1]))
        lifted=[(A,c)]+[(a,s) for a,s in lines if s>c]
        observed=[min(a+s*b for a,s in lifted) for b in range(len(g))]
        assert observed==D,(u,c,A,observed,D)
        assert D[-1]==c*(len(g)-1)+A
        assert all(a+s*(len(g)-1)>=D[-1] for a,s in lifted)
        results.append(dict(c=c,integer_intercept=A,tail_slope=c))
    return dict(floor_cells=len(results),budgets=len(g),results=results)

def tight(n):
    case=dict(cp=[[3**k,5*3**(k-1)] for k in range(1,n+1)],edges=[[k,k+1] for k in range(n-1)])
    data=hybrid.compile_case(case);assert data['route']=='ordered'
    expected=[[s,1] for k in range(n,0,-1) for s in [3**k,2*3**(k-1)]]
    assert data['value_slopes']==expected and len(expected)==2*n
    result=artifact(data)
    return dict(n=n,positive_runs=2*n,result=result,
        artifact_sha256=hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest())

def control(kind):
    if kind=='continuous_max':
        integer=max(min(3*b,5)-2*b for b in range(5))
        continuous=Fraction(5)-2*Fraction(5,3)
        correct=min(6,4+integer);wrong=min(Fraction(6),4+continuous)
        assert integer==1 and continuous==Fraction(5,3) and correct==5 and wrong==Fraction(17,3)
        return dict(integer_intercept=integer,continuous_intercept=str(continuous),correct=correct,wrong=str(wrong))
    assert kind=='bridge_not_input_cost'
    profile=[[0,0,3],[1,3,2],[2,5,0]];result=basis(profile,[3])
    assert 2 not in {0,3} and result['positive_runs']==2
    return dict(non_input_marginal=2,basis=result)

def prepare():
    out=ROOT/'run01';out.mkdir();(out/'input_artifacts').mkdir()
    algebra_inputs=[]
    for constant in range(9):
        for coefficients in itertools.product([None,*range(7)],repeat=4):
            lines=[[constant,0]]+[[a,c] for c,a in enumerate(coefficients,1) if a is not None]
            if min(a for a,c in lines)!=0:continue
            algebra_inputs.append(dict(id=f'line-{len(algebra_inputs):05}',constant=constant,lines=lines))
    assert len(algebra_inputs)==17656
    save(out/'ALGEBRA_INPUTS.json',algebra_inputs)
    paths=sorted((S/'final_evaluation_dag_01/artifacts').glob('*.json'))
    assert len(paths)==4232
    old=sorted((S/'dependency_scale_01/units').glob('*/compile/controller.json'));assert len(old)==78
    oracle=sorted((S/'budget_oracle_01/benchmark01/units').glob('*/all_budget/artifact.json'));assert len(oracle)==45
    paths+=old+oracle;registry=[]
    for k,path in enumerate(paths):
        dest=out/'input_artifacts'/f'certificate-{k:04}.json';data=path.read_bytes()
        with dest.open('xb') as f:f.write(data)
        registry.append(dict(id=f'certificate-{k:04}',original_source=str(path.relative_to(S)),
            path=str(dest.relative_to(ROOT)),sha256=sha(path),bytes=len(data),
            scope='POST_HOC_BASIS_PROPERTY_ONLY_NO_PRIOR_OUTCOME_UPGRADE'))
    save(out/'CERTIFICATE_INPUTS.json',registry)
    save(out/'OTHER_INPUTS.json',dict(tight_n=list(range(1,65)),controls=['continuous_max','bridge_not_input_cost']))
    todo=[hybrid];seen=set();sources={ROOT/'study.py',ROOT/'PLAN.md',ROOT/'PROOF_DRAFT.md'}
    while todo:
        m=todo.pop()
        if id(m) in seen:continue
        seen.add(id(m));path=getattr(m,'__file__',None)
        if not path:continue
        path=Path(path).resolve()
        if path.suffix!='.py' or not path.is_relative_to(S):continue
        sources.add(path);todo.extend(x for x in vars(m).values() if isinstance(x,types.ModuleType))
    sources.update([out/'ALGEBRA_INPUTS.json',out/'CERTIFICATE_INPUTS.json',out/'OTHER_INPUTS.json'])
    sources.update(out/'input_artifacts'/f'{u["id"]}.json' for u in registry)
    save(out/'MANIFEST.json',dict(utc=now(),algebra_units=17656,algebra_floor_cells=105936,
        existing_artifact_units=len(registry),tight_units=64,controls=2,total_units=22077,
        per_unit_seconds=20,campaign_seconds=300,python=sys.executable,python_sha256=sha(sys.executable),
        files=[dict(path=str(p.relative_to(S)),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(sources)]))
    print('frozen22077units,105936floorcells,4355existingartifacts',flush=True)

def alarm(sig,frame):raise TimeoutError('fixed basis check cap')
def run():
    assert __debug__;out=ROOT/'run01';manifest=json.loads((out/'MANIFEST.json').read_text())
    for f in manifest['files']:assert sha(S/f['path'])==f['sha256']
    assert sha(sys.executable)==manifest['python_sha256']
    work=[('ALGEBRA',u) for u in json.loads((out/'ALGEBRA_INPUTS.json').read_text())]
    work += [('CERTIFICATE',u) for u in json.loads((out/'CERTIFICATE_INPUTS.json').read_text())]
    work += [('TIGHT',dict(id=f'tight-{n:02}',n=n)) for n in range(1,65)]
    work += [('CONTROL',dict(id=k)) for k in ['continuous_max','bridge_not_input_cost']]
    assert len(work)==manifest['total_units']
    save(out/'START.json',dict(utc=now(),pid=os.getpid(),manifest_sha256=sha(out/'MANIFEST.json')))
    signal.signal(signal.SIGALRM,alarm);start=time.monotonic();counts=collections.Counter();totals=collections.Counter()
    with (out/'RAW.jsonl').open('x') as raw:
        for index,(kind,u) in enumerate(work):
            before=time.monotonic();row=dict(id=u['id'],kind=kind)
            if before-start>=300 or now()>='2026-09-08T01:50:00+00:00':row['status']='NOT_RUN'
            else:
                signal.setitimer(signal.ITIMER_REAL,min(20,300-(before-start)))
                try:
                    if kind=='ALGEBRA':result=algebra(u)
                    elif kind=='CERTIFICATE':
                        path=ROOT/u['path'];assert sha(path)==u['sha256'];result=artifact(json.loads(path.read_text()))
                    elif kind=='TIGHT':result=tight(u['n'])
                    else:result=control(u['id'])
                    row.update(status='SUCCESS',result=result)
                    if kind=='ALGEBRA':totals['floor_cells']+=result['floor_cells']
                    if kind=='CERTIFICATE':
                        for k in ['curves','segments','positive_runs','basis_lines']:totals[k]+=result[k]
                except TimeoutError:row.update(status='TIMEOUT',error=traceback.format_exc())
                except AssertionError:row.update(status='FAILURE',error=traceback.format_exc())
                except Exception:row.update(status='INVALID',error=traceback.format_exc())
                finally:signal.setitimer(signal.ITIMER_REAL,0)
            row['seconds']=time.monotonic()-before;counts[kind,row['status']]+=1
            raw.write(json.dumps(row,sort_keys=True,separators=(',',':'))+'\n');raw.flush()
            if (index+1)%5000==0:print(index+1,dict((a+':'+b,n) for (a,b),n in counts.items()),flush=True)
    result=dict(utc=now(),units=len(work),seconds=time.monotonic()-start,
        counts={kind:{s:counts[kind,s] for s in ['SUCCESS','FAILURE','TIMEOUT','INVALID','NOT_RUN']} for kind in ['ALGEBRA','CERTIFICATE','TIGHT','CONTROL']},
        totals=dict(totals),raw_sha256=sha(out/'RAW.jsonl'),old_timeouts_rerun=0,prior_outcome_upgrades=0)
    save(out/'SUMMARY.json',result);print(json.dumps(result,indent=2),flush=True)
if __name__=='__main__':{'prepare':prepare,'run':run}[sys.argv[1]]()
