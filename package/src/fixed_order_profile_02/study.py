"""Frozen exploratory semantic checks for persistent arbitrary-order profiles."""
from pathlib import Path
import collections, copy, datetime, hashlib, importlib.util, itertools, json
import os, random, signal, sys, time, traceback, types
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent; S = ROOT.parent
sys.path.insert(0,str(ROOT)); import persistent, checker
sys.path.insert(0,str(S/'dependency_curves_01')); import curves

def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(path,obj):
    with Path(path).open('x') as f: json.dump(obj,f,indent=2,sort_keys=True); f.write('\n')
def chain(cp): return dict(cp=[list(x) for x in cp],edges=[[i,i+1] for i in range(len(cp)-1)])
def alarm(sig,frame): raise TimeoutError('fixed unit/campaign cap')

def prepare():
    out=ROOT/'semantic01';out.mkdir();units=[]
    def add(case,group,order=None,selected=False):
        units.append(dict(id=f'order-{len(units):05}',case=case,group=group,order=order,save_artifact=selected))
    alphabet=list(itertools.product(range(1,4),range(4)))
    for n in range(5):
        for index,cp in enumerate(itertools.product(alphabet,repeat=n)):
            add(chain(cp),'EXHAUSTIVE_GRID',selected=index==0 or (n==4 and index in [137,1891,7123]))
    assert len(units)==22621
    rng=random.Random(202609080841)
    for k in range(256):
        n=2+k%9;cp=[(rng.randint(1,13)*(1<<40)+rng.randrange(1024),
                     0 if (j+k)%11==0 else rng.randint(1,31)*(1<<48)+rng.randrange(1024)) for j in range(n)]
        add(chain(cp),'WIDE_BINARY',selected=k<32)
    for k in range(1024):
        n=5+k%16;cp=[(rng.randint(1,31),rng.randrange(129)) for _ in range(n)]
        add(chain(cp),'LONGER_RANDOM',selected=k<32)
    for k in range(128):
        n=4+k%7;order=list(range(n));rng.shuffle(order)
        cp=[[rng.randint(1,17),rng.randrange(50)] for _ in range(n)]
        edges=[[order[i],order[j]] for i in range(n) for j in range(i+1,n) if rng.random()<.2]
        add(dict(cp=cp,edges=edges),'PRESCRIBED_BRANCHING',order,selected=k<8)
    assert len(units)==24029 and sum(u['save_artifact'] for u in units)==80
    bad=[dict(id='c_zero',case=chain([(0,1)])),dict(id='p_negative',case=chain([(1,-1)])),
         dict(id='c_float',case=chain([(1.0,2)])),dict(id='p_bool',case=chain([(1,True)])),
         dict(id='duplicate_edge',case=dict(cp=[[1,2],[2,3]],edges=[[0,1],[0,1]])),
         dict(id='cycle',case=dict(cp=[[1,2],[2,3]],edges=[[0,1],[1,0]])),
         dict(id='branch_without_order',case=dict(cp=[[1,2],[2,3]],edges=[])),
         dict(id='backward_order',case=chain([(1,2),(2,3)]),order=[1,0]),
         dict(id='duplicate_order',case=chain([(1,2),(2,3)]),order=[0,0]),
         dict(id='out_of_range_edge',case=dict(cp=[[1,2]],edges=[[0,1]])),
         dict(id='bool_edge',case=dict(cp=[[1,2],[2,3]],edges=[[False,1]])),
         dict(id='self_edge',case=dict(cp=[[1,2]],edges=[[0,0]]))]
    mutation_names=['node_cycle','node_area','node_height','node_first','node_last','node_runs',
                    'zero_count','negative_slope','threshold_late','threshold_early',
                    'out_of_range_root','missing_terminal_root','wrong_unique','normal_cost',
                    'unreachable_node','changed_premium','child_root']
    controls=dict(malformed=bad,base_cases=[chain([(2,7)]),chain([(2,7),(7,3),(3,11)]),
         chain([(2,0),(5,13),(1,2),(9,3),(4,19)])],mutations=mutation_names)
    save(out/'INPUTS.json',units);save(out/'CONTROLS.json',controls)
    modules=set();todo=[persistent,checker,curves];seen=set()
    while todo:
        m=todo.pop()
        if id(m) in seen:continue
        seen.add(id(m));p=getattr(m,'__file__',None)
        if not p:continue
        p=Path(p).resolve()
        if p.suffix!='.py' or not p.is_relative_to(S):continue
        modules.add(p);todo.extend(x for x in vars(m).values() if isinstance(x,types.ModuleType))
    paths=modules|{ROOT/'PLAN.md',ROOT/'study.py',out/'INPUTS.json',out/'CONTROLS.json',
       S/'fixed_order_profile_01/PROOF_DRAFT.md',S/'fixed_order_profile_01/PERSISTENT_CONSTRUCTION_AUTHOR_CHECK.md'}
    save(out/'MANIFEST.json',dict(utc=now(),units=len(units),artifacts=80,control_units=63,
        per_unit_seconds=2,campaign_seconds=270,python=sys.executable,python_sha256=sha(sys.executable),
        python_version=sys.version,files=[dict(path=str(p.relative_to(S)),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(paths)]))
    print('Frozen24029semanticunits+63controls,80artifacts',flush=True)

def test_unit(u,out):
    data=persistent.compile_case(u['case'],u['order'])
    encoded=json.dumps(data,sort_keys=True,separators=(',',':')).encode();data=json.loads(encoded)
    digest=hashlib.sha256(encoded).hexdigest()
    if u['save_artifact']:(out/'artifacts'/(u['id']+'.json')).write_bytes(encoded)
    report=checker.check(data);assert not report['violations']
    order=data['order'];cp=[u['case']['cp'][i] for i in order]
    reference=curves.compile_case(chain(cp))
    # Every suffix profile, including infinite tails, agrees byte-for-value
    # with the earlier generic all-budget constructor on its forced chain.
    mask=(1<<len(cp))-1
    for cursor in range(len(cp)+1):
        profile=checker.profile(data,data['roots'][cursor])
        assert profile==[tuple(row) for row in reference['curves'][mask]],(cursor,profile,reference['curves'][mask])
        samples={0,1,2,3,7,12,1<<80}
        samples.update(max(0,x+d) for x,_,_ in profile for d in [-1,0,1])
        for budget in samples:assert persistent.value(data,budget,cursor)==curves.at(profile,budget)
        if cursor<len(cp):mask^=1<<cursor
    table=[[0]*13 for _ in range(len(cp)+1)]
    for cursor in range(len(cp)-1,-1,-1):
        c,p=cp[cursor]
        for b in range(1,13):table[cursor][b]=min(p+table[cursor+1][b],max(table[cursor+1][b],c+table[cursor][b-1]))
        for b in range(13):
            assert persistent.value(data,b,cursor)==table[cursor][b]
            _,mode=persistent.choose(data,cursor,b)
            chosen=p+table[cursor+1][b] if mode=='protected' else (0 if b==0 else max(table[cursor+1][b],c+table[cursor][b-1]))
            assert chosen==table[cursor][b]
    return dict(artifact_sha256=digest,artifact_bytes=len(encoded),jobs=len(cp),
                report=report,stats=data['stats'],scalar_cells=13*(len(cp)+1),
                reference_segments=reference['segments'],restricted_to_supplied_order=not data['unique_topological_order'])

def corrupt(original,name):
    d=copy.deepcopy(original);nodes=d['nodes'];root=d['roots'][0]
    positive=next(k for k,i in enumerate(d['order']) if d['input']['cp'][i][1]>0)
    if name=='node_cycle':nodes[root][2]=root
    elif name.startswith('node_'):
        field={'node_area':6,'node_height':4,'node_first':7,'node_last':8,'node_runs':9}[name];nodes[root][field]+=1
    elif name=='zero_count':nodes[root][1]=0
    elif name=='negative_slope':nodes[root][0]=-1
    elif name=='threshold_late':d['protect_at_budget'][positive]+=1
    elif name=='threshold_early':d['protect_at_budget'][positive]-=1
    elif name=='out_of_range_root':d['roots'][0]=len(nodes)
    elif name=='missing_terminal_root':d['roots'].pop()
    elif name=='wrong_unique':d['unique_topological_order']=not d['unique_topological_order']
    elif name=='normal_cost':d['normal_cost']+=1
    elif name=='unreachable_node':nodes.append(copy.deepcopy(nodes[0]))
    elif name=='changed_premium':d['input']['cp'][d['order'][positive]][1]+=1
    elif name=='child_root':d['roots'][positive]=d['roots'][positive+1]
    else:raise ValueError(name)
    return d

def controls(out):
    spec=json.loads((out/'CONTROLS.json').read_text());rows=[]
    for u in spec['malformed']:
        try:persistent.compile_case(u['case'],u.get('order'));rejected=False
        except (ValueError,AssertionError,TypeError,KeyError):rejected=True
        rows.append(dict(id=u['id'],status='SUCCESS' if rejected else 'FAILURE',expected='REJECT'))
    for k,case in enumerate(spec['base_cases']):
        d=json.loads(json.dumps(persistent.compile_case(case)));assert not checker.check(d)['violations']
        for name in spec['mutations']:
            bad=corrupt(d,name)
            try:result=checker.check(bad);rejected=bool(result['violations'])
            except (AssertionError,ValueError,IndexError,KeyError,TypeError):rejected=True
            rows.append(dict(id=f'base{k}-{name}',status='SUCCESS' if rejected else 'FAILURE',expected='REJECT',
                  supplied_sha256=hashlib.sha256(json.dumps(bad,sort_keys=True).encode()).hexdigest()))
    save(out/'CONTROL_RESULTS.json',rows)
    return collections.Counter(r['status'] for r in rows)

def run():
    assert __debug__;out=ROOT/'semantic01';m=json.loads((out/'MANIFEST.json').read_text())
    for f in m['files']:assert sha(S/f['path'])==f['sha256']
    assert sha(sys.executable)==m['python_sha256'];(out/'artifacts').mkdir()
    units=json.loads((out/'INPUTS.json').read_text());save(out/'START.json',dict(utc=now(),pid=os.getpid(),manifest_sha256=sha(out/'MANIFEST.json')))
    signal.signal(signal.SIGALRM,alarm);start=time.monotonic();counts=collections.Counter();stats=collections.Counter()
    with (out/'RAW.jsonl').open('x') as raw:
        for index,u in enumerate(units):
            before=time.monotonic()
            if before-start>=270 or now()>='2026-09-08T01:50:00+00:00':row=dict(id=u['id'],status='NOT_RUN')
            else:
                signal.setitimer(signal.ITIMER_REAL,min(2,270-(before-start)))
                try:row=dict(id=u['id'],status='SUCCESS',**test_unit(u,out))
                except TimeoutError:row=dict(id=u['id'],status='TIMEOUT',error=traceback.format_exc())
                except AssertionError:row=dict(id=u['id'],status='FAILURE',error=traceback.format_exc())
                except Exception:row=dict(id=u['id'],status='INVALID',error=traceback.format_exc())
                finally:signal.setitimer(signal.ITIMER_REAL,0)
            row['seconds']=time.monotonic()-before;counts[row['status']]+=1
            if row['status']=='SUCCESS':
                for key in ['scalar_cells','reference_segments']:stats[key]+=row[key]
                stats['serialized_nodes']+=row['stats']['serialized_nodes'];stats['allocated_nodes']+=row['stats']['allocated_nodes']
                stats['suffix_profile_entries']+=row['report']['suffix_profile_entries']
            raw.write(json.dumps(row,sort_keys=True,separators=(',',':'))+'\n');raw.flush()
            if (index+1)%4000==0:print(json.dumps(dict(completed=index+1,counts=dict(counts))),flush=True)
    control_counts=controls(out)
    summary=dict(utc=now(),units=len(units),counts={k:counts[k] for k in ['SUCCESS','FAILURE','TIMEOUT','INVALID','NOT_RUN']},
        stats=dict(stats),control_counts=dict(control_counts),seconds=time.monotonic()-start,raw_sha256=sha(out/'RAW.jsonl'))
    save(out/'SUMMARY.json',summary);print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':{'prepare':prepare,'run':run}[sys.argv[1]]()
