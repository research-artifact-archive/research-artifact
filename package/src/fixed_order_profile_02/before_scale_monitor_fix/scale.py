"""New sixty-input cold pipeline comparison, no rerun of existing units."""
from pathlib import Path
import collections,datetime,hashlib,importlib.util,json,os,random,signal,subprocess,sys,time,types
import psutil
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent;S=ROOT.parent
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(path,obj):
    with Path(path).open('x') as f:json.dump(obj,f,indent=2,sort_keys=True);f.write('\n')
def prepare():
    out=ROOT/'scale01';out.mkdir();(out/'inputs').mkdir();units=[];rng=random.Random(202609080844)
    for n in [64,512,4096,32768]:
        for pattern in ['increasing','decreasing','local_inversions','sawtooth','random']:
            if pattern in ['increasing','local_inversions']:costs=[11+5*j for j in range(n)]
            elif pattern=='decreasing':costs=[11+5*(n-j) for j in range(n)]
            elif pattern=='sawtooth':costs=[19+(j%17)*13 for j in range(n)]
            else:costs=[rng.randint(11,5*n+11) for _ in range(n)]
            if pattern=='local_inversions':
                for j in range(6,n-1,8):costs[j],costs[j+1]=costs[j+1],costs[j]
            for family in ['SMALL','WIDE_PREMIUM','WIDE_BOTH']:
                cp=[]
                for j,c in enumerate(costs):
                    p=0 if j%13==0 else c*(n+3)+(11*j)%c+1
                    if family=='WIDE_PREMIUM':p=0 if p==0 else (p<<40)+j%29
                    elif family=='WIDE_BOTH':c=(c<<40)+j%7;p=0 if p==0 else (p<<40)+j%29
                    cp.append([c,p])
                ident=f'{pattern}-{n}-{family}'
                u=dict(id=ident,n=n,pattern=pattern,family=family,case=dict(cp=cp,edges=[[j,j+1] for j in range(n-1)]))
                save(out/'inputs'/f'{ident}.json',u);units.append(dict(id=ident,file=f'inputs/{ident}.json'))
    assert len(units)==60
    save(out/'INPUTS.json',units)
    # Materialize the complete imported local source closure without running a solve.
    sys.path.insert(0,str(ROOT));import persistent,checker
    sys.path.insert(0,str(S/'dependency_hybrid_01'));import hybrid
    sys.path.insert(0,str(S/'dependency_hybrid_check_02'));import check as packed
    sys.path.insert(0,str(S/'sweep_certificate_02'));import certificate as sweep
    seen=set();todo=[persistent,checker,hybrid,packed,sweep];paths={ROOT/'scale.py',ROOT/'scale_worker.py',ROOT/'SCALE_PLAN.md',ROOT/'PLAN.md',out/'INPUTS.json'}
    paths.update((out/u['file']) for u in units)
    while todo:
        m=todo.pop()
        if id(m) in seen:continue
        seen.add(id(m));p=getattr(m,'__file__',None)
        if not p:continue
        p=Path(p).resolve()
        if p.suffix!='.py' or not p.is_relative_to(S):continue
        paths.add(p);todo.extend(x for x in vars(m).values() if isinstance(x,types.ModuleType))
    save(out/'MANIFEST.json',dict(utc=now(),inputs=60,units=120,methods=['persistent','current_hybrid'],
        seconds_per_unit=5,rss_bytes=1073741824,poll_seconds=.05,campaign_seconds=660,
        python=sys.executable,python_sha256=sha(sys.executable),python_version=sys.version,
        files=[dict(path=str(p.relative_to(S)),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(paths)]))
    print('Frozen60inputs120units,5s1GiB,660scampaign',flush=True)
def run():
    assert __debug__;out=ROOT/'scale01';m=json.loads((out/'MANIFEST.json').read_text())
    for f in m['files']:assert sha(S/f['path'])==f['sha256']
    assert sha(sys.executable)==m['python_sha256'];(out/'units').mkdir();counts=collections.Counter()
    inputs=json.loads((out/'INPUTS.json').read_text());start=time.monotonic()
    save(out/'START.json',dict(utc=now(),pid=os.getpid(),manifest_sha256=sha(out/'MANIFEST.json')))
    with (out/'RAW.jsonl').open('x') as raw:
        for k,u in enumerate(inputs):
            methods=m['methods'] if k%2==0 else list(reversed(m['methods']))
            for method in methods:
                ident=u['id']+'--'+method;unit=out/'units'/ident;unit.mkdir();row=dict(id=ident,input_id=u['id'],method=method)
                if time.monotonic()-start>=660 or now()>='2026-09-08T01:50:00+00:00':row['status']='NOT_RUN'
                else:
                    argv=[sys.executable,str(ROOT/'scale_worker.py'),str(out/u['file']),str(unit),method]
                    save(unit/'COMMAND.json',dict(argv=argv,utc=now(),seconds=5,rss_bytes=1073741824))
                    before=time.monotonic();peak=0;reason=None
                    with (unit/'stdout.txt').open('wb') as stdout,(unit/'stderr.txt').open('wb') as stderr:
                        process=subprocess.Popen(argv,stdout=stdout,stderr=stderr,start_new_session=True)
                        while process.poll() is None:
                            elapsed=time.monotonic()-before
                            try:peak=max(peak,psutil.Process(process.pid).memory_info().rss)
                            except psutil.Error:pass
                            if elapsed>5 or peak>1073741824 or time.monotonic()-start>660 or now()>='2026-09-08T01:50:00+00:00':
                                reason='RSS_LIMIT' if peak>1073741824 else 'WALL_LIMIT'
                                os.killpg(process.pid,signal.SIGKILL);break
                            time.sleep(.05)
                        code=process.wait()
                    row.update(cold_seconds=time.monotonic()-before,peak_sampled_rss=peak,exit=code,limit_reason=reason)
                    result_path=unit/'RESULT.json'
                    if reason:row['status']='TIMEOUT'
                    elif code==0 and result_path.exists():row.update(json.loads(result_path.read_text()))
                    else:
                        stderr=(unit/'stderr.txt').read_text(errors='replace')
                        row['status']='FAILURE' if 'AssertionError' in stderr else 'INVALID';row['error']=stderr[-4000:]
                    construction=unit/'CONSTRUCTION.json'
                    if construction.exists():row['construction_before_check']=json.loads(construction.read_text())
                counts[(method,row['status'])]+=1;save(unit/'TERMINAL.json',row)
                raw.write(json.dumps(row,sort_keys=True,separators=(',',':'))+'\n');raw.flush()
            print(json.dumps(dict(input=k+1,id=u['id'],counts={f'{a}:{b}':v for (a,b),v in counts.items()})),flush=True)
    # Available root curves are compared even after a timeout; this is not a
    # replacement full-check success for either failed pipeline.
    comparisons=[]
    for u in inputs:
        paths=[out/'units'/(u['id']+'--'+method)/'ROOT_PROFILE.json' for method in m['methods']]
        comparisons.append(dict(input_id=u['id'],both_available=all(p.exists() for p in paths),
             equal=json.loads(paths[0].read_text())==json.loads(paths[1].read_text()) if all(p.exists() for p in paths) else None))
    save(out/'ROOT_COMPARISONS.json',comparisons)
    result=dict(utc=now(),units=120,counts={method:{s:counts[(method,s)] for s in ['SUCCESS','FAILURE','TIMEOUT','INVALID','NOT_RUN']} for method in m['methods']},
        seconds=time.monotonic()-start,raw_sha256=sha(out/'RAW.jsonl'),root_comparison_counts=dict(collections.Counter(str(r['equal']) for r in comparisons)))
    save(out/'SUMMARY.json',result);print(json.dumps(result,indent=2),flush=True)
if __name__=='__main__':{'prepare':prepare,'run':run}[sys.argv[1]]()
