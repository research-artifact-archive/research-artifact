from pathlib import Path
from functools import lru_cache
import collections,datetime,hashlib,json,math,struct,subprocess,sys,time,traceback
ROOT=Path(__file__).resolve().parent;SESSION=ROOT.parent;SOURCE=SESSION/'dependency_curves_01'
sys.path.insert(0,str(SOURCE));import curves
JAVA=Path('/opt/homebrew/opt/openjdk@17/bin/java')
JAVAC=Path('/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin/javac')
KINDS=['dag','fixed','look_fast','look_protected','cached']
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,v):
    with (ROOT/name).open('x') as f:json.dump(v,f,indent=2,sort_keys=True);f.write('\n')
def seq(v):return ','.join(map(str,v)) or '-'

def scalar(case,maxb):
    n=len(case['cp']);pred=[{a for a,b in case['edges'] if b==j} for j in range(n)]
    val=[[0]*(maxb+1) for s in range(1<<n)]
    for b in range(1,maxb+1):
        for s in range(1,1<<n):
            candidates=[]
            for i,(c,p) in enumerate(case['cp']):
                if not s&(1<<i) or any(s&(1<<j) for j in pred[i]):continue
                g=val[s^(1<<i)][b]
                candidates.extend([p+g,max(g,c+val[s][b-1])])
            val[s][b]=min(candidates)
    return val

def topological_orders(case):
    pred=case['pred'];n=len(pred)
    def visit(s,prefix):
        if not s:yield prefix;return
        for i in range(n):
            if s>>i&1 and not s&pred[i]:yield from visit(s^(1<<i),prefix+[i])
    return list(visit((1<<n)-1,[]))

def fixed_function(cp,order):
    @lru_cache(None)
    def v(s,b):
        if not s or not b:return 0
        i=next(i for i in order if s>>i&1);c,p=cp[i];g=v(s^(1<<i),b)
        return min(p+g,max(g,c+v(s,b-1)))
    return v

def policy(case,kind,budget,order):
    cp=case['cp'];n=len(cp);pred=case['pred'];base=case['scalar']
    fixed=fixed_function(cp,order) if kind=='fixed' else None
    def avail(s):return [i for i in range(n) if s>>i&1 and not s&pred[i]]
    @lru_cache(None)
    def upper(s,b):return min(sum(p for i,(c,p) in enumerate(cp) if s>>i&1 and c>t)+b*t for t in {0}|{c for i,(c,p) in enumerate(cp) if s>>i&1})
    @lru_cache(None)
    def cached(s,b):
        if not s or not b:return 0
        return min(q for i in avail(s) for q in (cp[i][1]+cached(s^(1<<i),b),max(cached(s^(1<<i),b),sum(cp[i])+cached(s^(1<<i),b-1))))
    @lru_cache(None)
    def choose(s,b):
        available=avail(s)
        if kind=='dag':
            j=min(available,key=lambda i:(cp[i][1]+base[s^(1<<i)][b],i))
            if cp[j][1]+base[s^(1<<j)][b]==base[s][b]:return j,'P'
            return min(available,key=lambda i:(cp[i][0],i)),'F'
        if kind=='fixed':
            i=next(i for i in order if s>>i&1)
            return i,'P' if cp[i][1]+fixed(s^(1<<i),b)==fixed(s,b) else 'F'
        options=[]
        for i in available:
            c,p=cp[i];rest=s^(1<<i)
            pq=p+(cached(rest,b) if kind=='cached' else upper(rest,b))
            fq=0 if not b else max(cached(rest,b),c+p+cached(rest,b-1)) if kind=='cached' else max(upper(rest,b),c+upper(s,b-1))
            for mode,q in [('P',pq),('C' if kind=='cached' else 'F',fq)]:
                rank=int(mode!='P') if kind=='look_protected' else int(mode=='P')
                options.append((q,rank,c,i,mode))
        _,_,_,i,mode=min(options);return i,mode
    @lru_cache(None)
    def actual(s,b):
        if not s:return 0
        i,mode=choose(s,b);c,p=cp[i];rest=s^(1<<i)
        if mode=='P':return p+actual(rest,b)
        if not b:return actual(rest,b)
        return max(actual(rest,b),c+(p+actual(rest,b-1) if mode=='C' else actual(s,b-1)))
    def paths(s,b,trace='',actions=()):
        if not s:yield trace,list(actions);return
        i,mode=choose(s,b);rest=s^(1<<i)
        if mode=='P':yield from paths(rest,b,trace,actions+((i,'P'),))
        else:
            success,failure=('M','X') if mode=='C' else ('S','F')
            yield from paths(rest,b,trace+success,actions+((i,success),))
            if b:yield from paths(rest if mode=='C' else s,b-1,trace+failure,actions+((i,failure),))
    return actual,paths

def signed(x):return ((x+(1<<31))%(1<<32))-(1<<31)
def fold(a):
    v=0
    for x in a:v=signed(31*v+x)
    return v
def digest(v):return hashlib.sha256(struct.pack('<'+'i'*len(v['a']),*v['a'])).hexdigest()
def expected(case,u):
    live=[dict(a=[17*(i+1)+31*j for j in range(n)],gen=0) for i,n in enumerate(case['lengths'])]
    for v in live:v['seed']=fold(v['a'])
    milestones=[None]*len(live);protected=[0]*len(live);work=writes=failed=0;actions=[];parent_inputs=[]
    def transform(i,v,inside):
        nonlocal work
        parent=0;count=0
        for j in range(len(live)):
            if case['pred'][i]>>j&1:
                assert milestones[j] is not None,('early kernel',i,j)
                parent=signed(31*parent+milestones[j]['seed']);count+=1
        parent_inputs.append(f'{i}:{parent}')
        a=[signed(1664525*x+1013904223+parent) for x in v['a']]
        count+=len(a);work+=count
        if inside:protected[i]+=count
        return dict(a=a,gen=v['gen']+1,seed=fold(a))
    def inject(i,after=False):
        nonlocal writes
        v=live[i];a=[signed(3*x+7) for x in v['a']];live[i]=dict(a=a,gen=v['gen']+1,seed=fold(a));writes+=1
        if after:actions.append(f'{i}:G_AFTER')
    for i,action in u['actions']:
        if action=='P':live[i]=transform(i,live[i],True)
        else:
            before=live[i];prepared=transform(i,before,False)
            if action in ('F','X'):inject(i)
            if action=='F':failed+=1
            elif action=='X':live[i]=transform(i,live[i],True)
            else:live[i]=prepared
        actions.append(f'{i}:{action}')
        if action!='F':
            assert milestones[i] is None;milestones[i]=live[i]
            if u['postwrite'] and i==0:inject(i,True)
    assert all(v is not None for v in milestones) and writes<=u['budget']
    return dict(work=work,protected_by_key=protected,cost=case['d']*work+sum(q*w for q,w in zip(case['weights'],protected)),
        trace=';'.join(actions),parent_inputs=';'.join(parent_inputs),digests=[digest(v) for v in live],
        milestone_digests=[digest(v) for v in milestones],gens=[v['gen'] for v in live],
        milestone_seeds=[v['seed'] for v in milestones],background=writes,public_false=failed)

def prepare():
    old1={c['id']:c for c in json.loads((SESSION/'dependency_retry_01/INPUTS.json').read_text())}
    old2={c['id']:c for c in json.loads((SESSION/'dependency_order_gap_01/INPUTS.json').read_text())}
    selected=[(old1['dag4_14_0'],6),(old2['order_113'],10),(old2['order_037'],7),
              (dict(id='parent_postwrite',cp=[[2,1],[3,2]],edges=[[0,1]]),1)]
    cases={};mathrows=[];(ROOT/'profiles').mkdir()
    for raw,maxb in selected:
        case={k:raw[k] for k in ['id','cp','edges']};case['max_budget']=maxb;case['scale']=8
        n=len(case['cp']);case['pred']=[sum(1<<a for a,b in case['edges'] if b==j) for j in range(n)]
        case['d']=math.lcm(*(c for c,p in case['cp']));case['weights']=[case['d']*p//c for c,p in case['cp']]
        case['lengths']=[8*c-case['pred'][i].bit_count() for i,(c,p) in enumerate(case['cp'])]
        assert all(x>0 for x in case['lengths'])
        case['scalar']=scalar(case,maxb);case['orders']=topological_orders(case)
        compiled=curves.compile_case(case);gaps=[]
        for s,f in compiled['curves'].items():
            for b in range(maxb+1):
                if curves.at(f,b)!=case['scalar'][s][b]:gaps.append([s,b,curves.at(f,b),case['scalar'][s][b]])
        with (ROOT/'profiles'/f"{case['id']}.tsv").open('x') as out:
            for s,f in sorted(compiled['curves'].items()):out.write(str(s)+'\t'+';'.join(':'.join(map(str,row)) for row in f)+'\n')
        row=dict(id=case['id'],states=len(compiled['curves']),scalar_gaps=gaps,root_values=case['scalar'][-1],orders=len(case['orders']))
        mathrows.append(row);cases[case['id']]=case
    save('MATH_VALIDATION.json',dict(created=now(),rows=mathrows,observed_model_inputs=True))
    assert not any(r['scalar_gaps'] for r in mathrows)
    units=[];cells=[]
    for case in cases.values():
        control=case['id']=='parent_postwrite';full=(1<<len(case['cp']))-1
        budgets=[1] if control else sorted({0,1,2,case['max_budget']})
        for b in budgets:
            order_values=[(fixed_function(case['cp'],order)(full,b),order) for order in case['orders']]
            best_value,best_order=min(order_values)
            for layout in ['distinct','colliding']:
                cell=dict(id=f"{case['id']}/b{b}/{layout}",case=case['id'],budget=b,layout=layout,
                    model_optimum=case['scalar'][full][b],best_fixed_value=best_value,best_fixed_order=best_order,control=control,policies=[])
                for kind in ['dag'] if control else KINDS:
                    actual,paths=policy(case,kind,b,best_order);group=[]
                    for k,(outcomes,actions) in enumerate(paths(full,b)):
                        u=dict(id=cell['id']+'/'+kind+f'/path_{k:05d}',case=case['id'],cell=cell['id'],kind=kind,
                            layout=layout,budget=b,order=best_order if kind=='fixed' else [],outcomes=outcomes,actions=actions,postwrite=control)
                        u['expected']=expected(case,u);units.append(u);group.append(u)
                        if control:break
                    target=8*case['d']*(sum(c for c,p in case['cp'])+actual(full,b))
                    if not control:assert max(u['expected']['cost'] for u in group)==target
                    if kind=='dag':assert actual(full,b)==case['scalar'][full][b]
                    if kind=='fixed':assert actual(full,b)==best_value
                    cell['policies'].append(dict(kind=kind,units=len(group),expected_max=max(u['expected']['cost'] for u in group),abstract_worst=actual(full,b),target=target))
                cells.append(cell)
    assert len({u['id'] for u in units})==len(units)
    save('INPUTS.json',dict(created=now(),cases=cases,cells=cells,units=units,final_evaluation=False))
    with (ROOT/'CASES.tsv').open('x') as f:
        for case in cases.values():f.write('\t'.join([case['id'],seq([c for c,p in case['cp']]),seq([p for c,p in case['cp']]),seq(case['pred']),seq(case['lengths']),seq(case['weights']),str(case['d']),'8',f"profiles/{case['id']}.tsv"])+'\n')
    with (ROOT/'INPUTS.tsv').open('x') as f:
        for u in units:f.write('\t'.join([u['id'],u['case'],u['kind'],u['layout'],str(u['budget']),seq(u['order']),u['outcomes'] or '-',str(int(u['postwrite']))])+'\n')
    files=[ROOT/x for x in ['PLAN.md','NativeDag.java','experiment.py','INPUTS.json','CASES.tsv','INPUTS.tsv','MATH_VALIDATION.json']]
    files+=sorted((ROOT/'profiles').glob('*.tsv'))+[SOURCE/'curves.py',SESSION/'dependency_retry_01/INPUTS.json',SESSION/'dependency_order_gap_01/INPUTS.json',SESSION/'dependency_order_gap_01/RAW.jsonl',SESSION/'source_text/openjdk17_runtime/RECEIPT.json']
    version=subprocess.run([str(JAVA),'-version'],capture_output=True,text=True,timeout=10)
    save('MANIFEST.json',dict(created=now(),files=[dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size) for p in files],
        unit_count=len(units),core_cells=24,core_policy_cells=120,control_units=2,java=str(JAVA),javac=str(JAVAC),java_sha256=sha(JAVA),javac_sha256=sha(JAVAC),
        version_stdout=version.stdout,version_stderr=version.stderr,
        compile_argv=[str(JAVAC),'-d',str(ROOT/'classes'),str(ROOT/'NativeDag.java')],
        execute_argv=[str(JAVA),'-Xmx256m','-XX:ActiveProcessorCount=1','-cp',str(ROOT/'classes'),'NativeDag',str(ROOT)],
        compile_timeout_seconds=30,execute_timeout_seconds=120,native_outcomes_observed=False,retry_allowed=False,exclusions=[],final_evaluation=False))
    print(dict(unit_count=len(units),core_cells=24,core_policy_cells=120,control_units=2))

def run():
    m=json.loads((ROOT/'MANIFEST.json').read_text())
    for entry in m['files']:assert sha(Path(entry['path']))==entry['sha256'],entry['path']
    assert datetime.datetime.now(datetime.timezone.utc)<datetime.datetime(2026,9,8,0,50,tzinfo=datetime.timezone.utc)
    save('RUN_STARTED.json',dict(start=now(),manifest_sha256=sha(ROOT/'MANIFEST.json')))
    t=time.monotonic();receipt=dict(start=now(),compile=None,execute=None)
    try:
        c=subprocess.run(m['compile_argv'],capture_output=True,text=True,timeout=30);receipt['compile']=dict(returncode=c.returncode,stdout=c.stdout,stderr=c.stderr)
        if c.returncode:return
        save('CLASS_RECEIPT.json',dict(created=now(),files=[dict(path=str(p),sha256=sha(p)) for p in sorted((ROOT/'classes').glob('*.class'))]))
        with (ROOT/'RAW.jsonl').open('xb') as out,(ROOT/'STDERR.txt').open('xb') as err:
            try:
                p=subprocess.run(m['execute_argv'],stdout=out,stderr=err,timeout=120);receipt['execute']=dict(returncode=p.returncode,timeout=False)
            except subprocess.TimeoutExpired:receipt['execute']=dict(returncode=None,timeout=True)
    except subprocess.TimeoutExpired as e:receipt['compile']=dict(returncode=None,timeout=True,stdout=str(e.stdout),stderr=str(e.stderr))
    finally:
        receipt.update(end=now(),elapsed_seconds=time.monotonic()-t)
        if (ROOT/'RAW.jsonl').exists():receipt['raw_sha256']=sha(ROOT/'RAW.jsonl')
        save('RUN_RECEIPT.json',receipt);print(receipt)

def check():
    data=json.loads((ROOT/'INPUTS.json').read_text());seen=collections.defaultdict(list);parse=[]
    if (ROOT/'RAW.jsonl').exists():
        for index,line in enumerate((ROOT/'RAW.jsonl').read_text().splitlines()):
            try:r=json.loads(line);seen[r['id']].append(r)
            except Exception as e:parse.append(dict(line=index,error=repr(e)))
    counts=collections.Counter();adverse=[];good={}
    for u in data['units']:
        rows=seen.pop(u['id'],[]);issues=[]
        if not rows:status='NOT_RUN'
        elif len(rows)!=1:status='INVALID'
        else:
            row=rows[0];status=row['status'];e=expected(data['cases'][u['case']],u);assert e==u['expected']
            if status=='SUCCESS':
                issues=[dict(field=k,expected=v,actual=row.get(k)) for k,v in e.items() if row.get(k)!=v]
                if issues:status='FAILURE'
                else:good[u['id']]=row
        counts[status]+=1
        if status!='SUCCESS':adverse.append(dict(id=u['id'],status=status,issues=issues,raw=rows))
    comparisons=[];gaps=[]
    groups=collections.defaultdict(list)
    for u in data['units']:groups[u['cell'],u['kind']].append(u)
    for cell in data['cells']:
        row={k:v for k,v in cell.items() if k!='policies'};row['policies']={}
        for p in cell['policies']:
            us=groups[cell['id'],p['kind']];value=max(good[u['id']]['cost'] for u in us) if all(u['id'] in good for u in us) else None
            row['policies'][p['kind']]=dict(actual_max=value,expected_max=p['expected_max'],units=len(us),model_excess=p['abstract_worst'])
            if value is not None and value!=p['expected_max']:gaps.append(dict(cell=cell['id'],kind=p['kind'],actual=value,expected=p['expected_max']))
        comparisons.append(row)
    result=dict(created=now(),denominator=len(data['units']),status=dict(counts),parse_errors=parse,unexpected_ids=list(seen),
        adverse_units=adverse,maximum_disagreements=gaps,comparison=comparisons,raw_sha256=sha(ROOT/'RAW.jsonl') if (ROOT/'RAW.jsonl').exists() else None,final_evaluation=False)
    save('SUMMARY.json',result);print({k:result[k] for k in ['denominator','status','parse_errors','unexpected_ids','maximum_disagreements','raw_sha256']})

if __name__=='__main__':
    try:{'prepare':prepare,'run':run,'check':check}[sys.argv[1]]()
    except Exception:
        if sys.argv[1]=='prepare' and not (ROOT/'PREPARATION_FAILURE.json').exists():save('PREPARATION_FAILURE.json',dict(utc=now(),error=traceback.format_exc()))
        raise
