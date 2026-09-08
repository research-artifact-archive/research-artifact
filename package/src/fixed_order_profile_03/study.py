from pathlib import Path
import collections,datetime,hashlib,importlib.util,itertools,json,os,signal,sys,time,traceback,types
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent;S=ROOT.parent;OLD=S/'fixed_order_profile_02'
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m;spec.loader.exec_module(m);return m
compiler=module('prescribed_persistent',OLD/'persistent.py')
check=module('shared_cap_check',ROOT/'checker.py')
oldstudy=module('prescribed_oldstudy',OLD/'study.py')
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(path,obj):
    with Path(path).open('x') as f:json.dump(obj,f,indent=2,sort_keys=True);f.write('\n')
def alarm(sig,frame):raise TimeoutError('fixed cap')
def parts(total,maximum=None):
    if total==0:yield [];return
    for first in range(min(total,total if maximum is None else maximum),0,-1):
        for suffix in parts(total-first,first):yield [first]+suffix
def prepare():
    out=ROOT/'semantic01';out.mkdir()
    units=json.loads((OLD/'semantic01/INPUTS.json').read_text());save(out/'INPUTS.json',units)
    controls=[]
    for c in range(1,7):
        for p in range(1,13):
            for slopes in parts(p):
                for t in range(p+3):
                    controls.append(dict(kind='ONE_JOB_PARTITION',c=c,p=p,slopes=slopes,threshold=t))
    controls.extend([dict(kind='PREFIX_FORGERY',forged=x) for x in [False,True]])
    controls.extend([dict(kind='SUFFIX_FORGERY',forged=x) for x in [False,True]])
    save(out/'ADVERSARIAL_INPUTS.json',controls)
    todo=[compiler,check,oldstudy];seen=set();paths={ROOT/'PROOF_DRAFT.md',ROOT/'PLAN.md',ROOT/'study.py',out/'INPUTS.json',out/'ADVERSARIAL_INPUTS.json',OLD/'semantic01/RAW.jsonl',OLD/'semantic01/CONTROLS.json'}
    while todo:
        m=todo.pop()
        if id(m) in seen:continue
        seen.add(id(m));p=getattr(m,'__file__',None)
        if not p:continue
        p=Path(p).resolve()
        if p.suffix!='.py' or not p.is_relative_to(S):continue
        paths.add(p);todo.extend(x for x in vars(m).values() if isinstance(x,types.ModuleType))
    save(out/'MANIFEST.json',dict(utc=now(),existing_inputs=len(units),prior_corruptions=51,adversarial_inputs=len(controls),
        seconds_per_unit=2,campaign_seconds=180,python=sys.executable,python_sha256=sha(sys.executable),python_version=sys.version,
        files=[dict(path=str(p.relative_to(S)),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(paths)]))
    print('Frozen',len(units),'known inputs,51oldcorruptions,',len(controls),'newadversarialcertificates',flush=True)

def artifact_from_profiles(case,profiles,thresholds):
    # Independent balanced tree materialization; deliberately NO sharing.
    # This exercises exact comparison when subtree identities cannot shortcut.
    nodes=[]
    def build(runs):
        if not runs:return -1
        k=len(runs)//2;left=build(runs[:k]);right=build(runs[k+1:]);h,count=runs[k]
        a=None if left==-1 else nodes[left];b=None if right==-1 else nodes[right]
        row=[h,count,left,right,1+max(0 if a is None else a[4],0 if b is None else b[4]),
          count+(0 if a is None else a[5])+(0 if b is None else b[5]),
          h*count+(0 if a is None else a[6])+(0 if b is None else b[6]),
          h if a is None else a[7],h if b is None else b[8],1+(0 if a is None else a[9])+(0 if b is None else b[9])]
        index=len(nodes);nodes.append(row);return index
    roots=[build(profile) for profile in profiles];n=len(case['cp'])
    return dict(schema='retry-persistent-order-v1',route='persistent_order',input=case,order=list(range(n)),
       unique_topological_order=True,normal_cost=sum(c for c,p in case['cp']),nodes=nodes,roots=roots,protect_at_budget=thresholds)
def accepted(data,checker=check):
    try:result=checker.check(data);return not result['violations'],result
    except (AssertionError,ValueError,KeyError,IndexError,TypeError) as e:return False,dict(rejected=type(e).__name__,detail=str(e))
def adversarial(u):
    if u['kind']=='ONE_JOB_PARTITION':
        c,p,t=u['c'],u['p'],u['threshold'];runs=[(h,len(list(group))) for h,group in itertools.groupby(u['slopes'])]
        d=artifact_from_profiles(dict(cp=[[c,p]],edges=[]),[runs,[]],[t])
        expected=t==(p+c-1)//c and all(sum(u['slopes'][:b])==min(p,b*c) for b in range(p+1))
    else:
        basecp=[[1,1],[3,3],[6,6],[8,8],[10,10]]
        front=[1,5] if u['kind']=='PREFIX_FORGERY' else [11,1]
        cp=[front]+basecp;case=dict(cp=cp,edges=[[i,i+1] for i in range(len(cp)-1)])
        reference=compiler.compile_case(case);profiles=[]
        for root in reference['roots']:
            f=check.shape.profile(reference,root)
            profiles.append([(h,f[k+1][0]-x) for k,(x,_,h) in enumerate(f[:-1])])
        if u['forged']:
            # Old subtree slopes 10,8,6,3,1: replace interior 6,3 by 5,4,
            # preserving length, mass, strict order, first and last slopes.
            runs=profiles[0];found6=found3=False
            for k,(h,m) in enumerate(runs):
                if h==6:assert m==1;runs[k]=(5,m);found6=True
                elif h==3:assert m==1;runs[k]=(4,m);found3=True
            assert found6 and found3
        d=artifact_from_profiles(case,profiles,reference['protect_at_budget']);expected=not u['forged']
    observed,detail=accepted(d)
    # Direct Bellman checker is a second independent oracle for these newly
    # forged trees; preserve both outcomes rather than trusting expectations.
    direct,direct_detail=accepted(d,check.shape)
    assert observed==expected==direct,(u,expected,observed,direct,detail,direct_detail)
    return dict(expected_accept=expected,accepted=observed,direct_bellman_accept=direct,
        supplied_sha256=hashlib.sha256(json.dumps(d,sort_keys=True).encode()).hexdigest(),detail=detail)
def run():
    assert __debug__;out=ROOT/'semantic01';m=json.loads((out/'MANIFEST.json').read_text())
    for r in m['files']:assert sha(S/r['path'])==r['sha256']
    assert sha(sys.executable)==m['python_sha256']
    units=json.loads((out/'INPUTS.json').read_text());previous={r['id']:r for r in map(json.loads,(OLD/'semantic01/RAW.jsonl').read_text().splitlines())}
    old_controls=json.loads((OLD/'semantic01/CONTROLS.json').read_text())
    extra=json.loads((out/'ADVERSARIAL_INPUTS.json').read_text());work=[('KNOWN',u) for u in units]
    work += [('OLD_CORRUPT',dict(case=case,mutation=name)) for case in old_controls['base_cases'] for name in old_controls['mutations']]
    work += [('ADVERSARIAL',u) for u in extra]
    save(out/'START.json',dict(utc=now(),pid=os.getpid(),manifest_sha256=sha(out/'MANIFEST.json')))
    signal.signal(signal.SIGALRM,alarm);start=time.monotonic();counts=collections.Counter();accepted_counts=collections.Counter();stats=collections.Counter()
    with (out/'RAW.jsonl').open('x') as raw:
        for index,(kind,u) in enumerate(work):
            before=time.monotonic();row=dict(id=index,kind=kind)
            if before-start>=180 or now()>='2026-09-08T01:50:00+00:00':row['status']='NOT_RUN'
            else:
                signal.setitimer(signal.ITIMER_REAL,min(2,180-(before-start)))
                try:
                    if kind=='KNOWN':
                        data=compiler.compile_case(u['case'],u['order']);encoded=json.dumps(data,sort_keys=True,separators=(',',':')).encode()
                        digest=hashlib.sha256(encoded).hexdigest();assert digest==previous[u['id']]['artifact_sha256']
                        d=json.loads(encoded);result=check.check(d);assert not result['violations']
                        row.update(source_id=u['id'],artifact_sha256=digest,report=result)
                        stats.update(result['counts'])
                    elif kind=='OLD_CORRUPT':
                        d=json.loads(json.dumps(compiler.compile_case(u['case'])));bad=oldstudy.corrupt(d,u['mutation']);ok,detail=accepted(bad)
                        assert not ok;row.update(expected_accept=False,accepted=ok,detail=detail)
                    else:row.update(adversarial(u))
                    row['status']='SUCCESS'
                except TimeoutError:row.update(status='TIMEOUT',error=traceback.format_exc())
                except AssertionError:row.update(status='FAILURE',error=traceback.format_exc())
                except Exception:row.update(status='INVALID',error=traceback.format_exc())
                finally:signal.setitimer(signal.ITIMER_REAL,0)
            row['seconds']=time.monotonic()-before;counts[(kind,row['status'])]+=1
            if row['status']=='SUCCESS' and 'accepted' in row:accepted_counts[(kind,str(row['accepted']))]+=1
            raw.write(json.dumps(row,sort_keys=True,separators=(',',':'))+'\n');raw.flush()
            if (index+1)%10000==0:print(index+1,dict((a+':'+b,n) for (a,b),n in counts.items()),flush=True)
    summary=dict(utc=now(),units=len(work),counts={kind:{s:counts[(kind,s)] for s in ['SUCCESS','FAILURE','TIMEOUT','INVALID','NOT_RUN']} for kind in ['KNOWN','OLD_CORRUPT','ADVERSARIAL']},
       accepted_counts={a+':'+b:n for (a,b),n in accepted_counts.items()},known_traversal_totals=dict(stats),seconds=time.monotonic()-start,raw_sha256=sha(out/'RAW.jsonl'))
    save(out/'SUMMARY.json',summary);print(json.dumps(summary,indent=2),flush=True)
if __name__=='__main__':{'prepare':prepare,'run':run}[sys.argv[1]]()
