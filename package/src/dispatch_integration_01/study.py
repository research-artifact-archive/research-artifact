from pathlib import Path
from functools import lru_cache
import collections,copy,datetime,hashlib,importlib.util,json,os,signal,sys,time,traceback,types
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent;S=ROOT.parent
spec=importlib.util.spec_from_file_location('retry_dispatch_integration',S/'fixed_order_profile_03/dispatch.py')
dispatch=importlib.util.module_from_spec(spec);spec.loader.exec_module(dispatch)
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(name,obj):
    with (ROOT/name).open('x') as f:json.dump(obj,f,indent=2,sort_keys=True);f.write('\n')
def prepare():
    cases=[dict(cp=[],edges=[]),dict(cp=[[1,2]],edges=[]),dict(cp=[[3,2],[1,4]],edges=[[0,1]]),
           dict(cp=[[3,2],[1,4],[2,1]],edges=[[0,1]])]
    save('INPUTS.json',dict(cases=cases,expected_routes=['ordered','ordered','persistent_order','ideal'],budgets=list(range(13)),
      controls=['bool_normal_cost','root_runs','serialized_nodes','allocated_negative','branching_prescribed_as_global','uncertified_generation_counter'],slow_family_k=[8,16,32,64,128]))
    paths={ROOT/'PLAN.md',ROOT/'study.py',ROOT/'INPUTS.json'};seen=set();todo=[dispatch]
    while todo:
        m=todo.pop()
        if id(m) in seen:continue
        seen.add(id(m));p=getattr(m,'__file__',None)
        if not p:continue
        p=Path(p).resolve()
        if p.suffix!='.py' or not p.is_relative_to(S):continue
        paths.add(p);todo.extend(x for x in vars(m).values() if isinstance(x,types.ModuleType))
    save('MANIFEST.json',dict(utc=now(),units=15,python=sys.executable,python_sha256=sha(sys.executable),seconds_per_unit=5,campaign_seconds=60,
          files=[dict(path=str(p.relative_to(S)),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(paths)]))
    print('Frozen15units',flush=True)
def policy_value(data,budget):
    n=len(data['input']['cp']);ordered=data['route']!='ideal';initial=0 if ordered else (1<<n)-1
    @lru_cache(None)
    def value(state,b):
        if (state==n if ordered else state==0):return 0
        j,mode=dispatch.choose(data,state,b);c,p=data['input']['cp'][j]
        if ordered:done=set(data['order'][:state]);nxt=state+1
        else:done={k for k in range(n) if not state>>k&1};nxt=state^(1<<j)
        assert j not in done and all(a in done for a,z in data['input']['edges'] if z==j)
        if mode=='protected':return p+value(nxt,b)
        assert mode=='fast'
        return value(nxt,b) if b==0 else max(value(nxt,b),c+value(state,b-1))
    return value(initial,budget)
def correct(case,route,budgets):
    d=dispatch.compile_case(case);encoded=json.dumps(d,sort_keys=True,separators=(',',':')).encode();d=json.loads(encoded)
    assert d['route']==route;report=dispatch.check(d);assert not report['violations']
    ref=dispatch.prior.curves.compile_case(case);d=dispatch.load(d)
    for b in budgets:assert dispatch.value(d,b)==dispatch.prior.curves.at(ref['curves'][ref['full']],b)==policy_value(d,b)
    return dict(route=route,artifact_sha256=hashlib.sha256(encoded).hexdigest(),report=report,budgets=len(budgets))
def control(name,cases):
    if name=='bool_normal_cost':d=json.loads(json.dumps(dispatch.compile_case(cases[1])));d['normal_cost']=True
    elif name=='branching_prescribed_as_global':d=json.loads(json.dumps(dispatch.persistent.compile_case(cases[3],[0,1,2])))
    else:
        d=json.loads(json.dumps(dispatch.compile_case(cases[2])))
        if name=='root_runs':d['stats']['root_runs']+=1
        elif name=='serialized_nodes':d['stats']['serialized_nodes']+=1
        elif name=='allocated_negative':d['stats']['allocated_nodes']=-1
        elif name=='uncertified_generation_counter':d['stats']['allocated_nodes']+=100000
        else:raise ValueError(name)
    try:report=dispatch.check(d);accepted=not report['violations']
    except (AssertionError,ValueError,TypeError,KeyError):accepted=False;report=None
    expected=name=='uncertified_generation_counter';assert accepted==expected
    if expected:assert report['generation_counters_not_certified']==['allocated_nodes','construction_steps']
    return dict(accepted=accepted,expected_accept=expected,report=report)
def slow(k):
    cp=[[1,0] for _ in range(k)]+[[i,i] for i in range(1,k+1)];case=dict(cp=cp,edges=[[j,j+1] for j in range(2*k-1)])
    d=json.loads(json.dumps(dispatch.persistent.compile_case(case)));nodes=d['nodes'];root=d['roots'][k];memo={}
    def clone(index):
        if index==-1:return -1
        if index in memo:return memo[index]
        row=list(nodes[index]);row[2]=clone(row[2]);row[3]=clone(row[3]);result=len(nodes);nodes.append(row);memo[index]=result;return result
    other=clone(root)
    for cursor in range(k):d['roots'][cursor]=root if cursor%2==0 else other
    # Auxiliary constructor counters are not evidence of this altered tree's
    # generation; cap checker ignores them and validates actual node structure.
    report=dispatch.cap_check.check(d);assert not report['violations']
    return dict(k=k,nodes=len(nodes),report=report,generated_by_02=False,
         artifact_sha256=hashlib.sha256(json.dumps(d,sort_keys=True).encode()).hexdigest())
def alarm(sig,frame):raise TimeoutError('fixed integration cap')
def run():
    assert __debug__;m=json.loads((ROOT/'MANIFEST.json').read_text())
    for f in m['files']:assert sha(S/f['path'])==f['sha256']
    assert sha(sys.executable)==m['python_sha256'];inp=json.loads((ROOT/'INPUTS.json').read_text())
    work=[('CASE',i) for i in range(4)]+[('CONTROL',n) for n in inp['controls']]+[('SLOW_VALID',k) for k in inp['slow_family_k']]
    save('START.json',dict(utc=now(),pid=os.getpid(),manifest_sha256=sha(ROOT/'MANIFEST.json')))
    start=time.monotonic();signal.signal(signal.SIGALRM,alarm);counts=collections.Counter();rows=[]
    for kind,key in work:
        before=time.monotonic();row=dict(kind=kind,key=key)
        if before-start>60 or now()>='2026-09-08T01:50:00+00:00':row['status']='NOT_RUN'
        else:
            signal.setitimer(signal.ITIMER_REAL,min(5,60-(before-start)))
            try:
                result=correct(inp['cases'][key],inp['expected_routes'][key],inp['budgets']) if kind=='CASE' else control(key,inp['cases']) if kind=='CONTROL' else slow(key)
                row.update(status='SUCCESS',result=result)
            except TimeoutError:row.update(status='TIMEOUT',error=traceback.format_exc())
            except AssertionError:row.update(status='FAILURE',error=traceback.format_exc())
            except Exception:row.update(status='INVALID',error=traceback.format_exc())
            finally:signal.setitimer(signal.ITIMER_REAL,0)
        row['seconds']=time.monotonic()-before;rows.append(row);counts[row['status']]+=1
    save('RAW.json',rows);save('SUMMARY.json',dict(utc=now(),units=len(rows),counts=dict(counts),seconds=time.monotonic()-start,raw_sha256=sha(ROOT/'RAW.json')))
    print(json.dumps(json.loads((ROOT/'SUMMARY.json').read_text()),indent=2))
if __name__=='__main__':{'prepare':prepare,'run':run}[sys.argv[1]]()
