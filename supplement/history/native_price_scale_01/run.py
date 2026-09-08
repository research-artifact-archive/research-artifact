from pathlib import Path
import collections,datetime,hashlib,itertools,json,os,platform,random,signal,subprocess,sys,time
import worker
HERE=Path(__file__).resolve().parent
METHODS=['packed','ordered_saturation','screened_ordered']
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(path,v):
    with path.open('x') as f:json.dump(v,f,indent=2,sort_keys=True);f.write('\n')
def prepare():
    rng=random.Random(202609072212);vectors=[];cases=[];units=[]
    (HERE/'inputs').mkdir()
    for family,n in itertools.product(['equal','heterogeneous'],[16,64,256,1024,4096,16384]):
        lengths=[128]*n if family=='equal' else [rng.randint(1,4096) for _ in range(n)]
        for d in [4,2,1]:
            vid=f'{family}/n{n}/alpha1_{d}';vectors.append(dict(id=vid,n=n,family=family,q=1,d=d))
            for B in [1,n//4,n//2,n]:
                cid=vid+f'/B{B}';name=cid.replace('/','_')+'.json';p=HERE/'inputs'/name
                g=dict(jobs=[[w,d*w] for w in lengths],normal_costs=[d*w for w in lengths],budget=B)
                save(p,g);case=dict(id=cid,vector=vid,n=n,family=family,q=1,d=d,budget=B,input=str(p),sha256=sha(p));cases.append(case)
                for method in METHODS:units.append(dict(id=cid+'/'+method,case=cid,method=method,input=str(p)))
    save(HERE/'INPUTS.json',dict(vectors=vectors,cases=cases,units=units))
    r=random.Random(202609072213);checks=[]
    for i in range(128):
        n=r.randint(1,8);d=r.choice([1,2,4]);w=[r.randint(1,50) for _ in range(n)]
        checks.append(dict(id=f'compat{i:03}',jobs=[[x,d*x] for x in w],normal_costs=[d*x for x in w],budget=r.randint(0,n+2)))
    save(HERE/'COMPAT_INPUTS.json',checks)
    files=[HERE/'PLAN.md',HERE/'worker.py',Path(__file__),HERE/'INPUTS.json',HERE/'COMPAT_INPUTS.json',worker.COMP,worker.SCREEN]
    save(HERE/'MANIFEST.json',dict(created=now(),cases=144,vectors=36,units=432,compatibility_inputs=128,
        files=[dict(path=str(p),sha256=sha(p)) for p in files],python=sys.executable,python_version=sys.version,platform=platform.platform(),
        timeout_seconds=6,sampled_rss_cap_bytes=1073741824,rss_poll_seconds=.05,aggregate_timeout_seconds=3600,
        methods=METHODS,final_evaluation=False,exclusions=[],retry_allowed=False))
    print('fixed 36 vectors,144 roots,432 cold units;128 separate compatibility inputs')
def verify():
    m=json.loads((HERE/'MANIFEST.json').read_text())
    for p in m['files']:assert sha(Path(p['path']))==p['sha256']
    for c in json.loads((HERE/'INPUTS.json').read_text())['cases']:assert sha(Path(c['input']))==c['sha256']
    return m

def compatibility():
    verify();comp=worker.module(worker.COMP,'compat_compiler');rows=[]
    for g in json.loads((HERE/'COMPAT_INPUTS.json').read_text()):
        try:
            oracle=worker.exact(g);a=worker.ordered(g,False);b=worker.ordered(g,True);c=comp.compile_controller(g)
            row=dict(id=g['id'],status='SUCCESS',reference=oracle,ordered=a,screened=b,packed=c['value'],agreement=oracle==a['value']==b['value']==c['value'])
        except Exception as e:row=dict(id=g['id'],status='INVALID',error=repr(e))
        rows.append(row)
    result=dict(created=now(),inputs=128,outcomes=dict(collections.Counter(r['status'] for r in rows)),disagreements=sum(r.get('agreement') is False for r in rows),rows=rows)
    save(HERE/'COMPAT_RESULT.json',result);print({k:v for k,v in result.items() if k!='rows'})

def run():
    m=verify();compat=json.loads((HERE/'COMPAT_RESULT.json').read_text());assert compat['outcomes']=={'SUCCESS':128} and compat['disagreements']==0
    inputs=json.loads((HERE/'INPUTS.json').read_text());deadline=datetime.datetime(2026,9,8,0,50,tzinfo=datetime.timezone.utc)
    save(HERE/'RUN_STARTED.json',dict(start=now(),manifest_sha256=sha(HERE/'MANIFEST.json'),parent_pid=os.getpid()))
    started=time.monotonic();counts=collections.Counter();results=[]
    with (HERE/'RAW.jsonl').open('x') as raw:
        for index,u in enumerate(inputs['units']):
            row=dict(**u,index=index,started=now());directory=HERE/'units'/u['id'];directory.mkdir(parents=True)
            if datetime.datetime.now(datetime.timezone.utc)>=deadline or time.monotonic()-started>=m['aggregate_timeout_seconds']:
                row.update(status='NOT_RUN',reason='session_or_campaign_deadline')
            else:
                argv=[m['python'],str(HERE/'worker.py'),u['method'],u['input'],str(directory)]
                save(directory/'COMMAND.json',dict(argv=argv,timeout_seconds=6,rss_cap_bytes=1073741824))
                start=time.monotonic();rss=0;reason=None
                with (directory/'stdout.txt').open('xb') as out,(directory/'stderr.txt').open('xb') as err:
                    proc=subprocess.Popen(argv,stdout=out,stderr=err,start_new_session=True)
                    while proc.poll() is None:
                        if time.monotonic()-start>6:reason='wall_timeout'
                        elif datetime.datetime.now(datetime.timezone.utc)>=deadline:reason='session_deadline'
                        else:
                            ps=subprocess.run(['/bin/ps','-o','rss=','-p',str(proc.pid)],capture_output=True,text=True,timeout=2)
                            try:rss=max(rss,int(ps.stdout.strip())*1024)
                            except ValueError:pass
                            if rss>1073741824:reason='memory_limit'
                        if reason:
                            try:os.killpg(proc.pid,signal.SIGKILL)
                            except ProcessLookupError:pass
                            break
                        time.sleep(.05)
                    code=proc.wait(timeout=5)
                elapsed=time.monotonic()-start
                row.update(cold_seconds=elapsed,exit_code=code,sampled_peak_rss_bytes=rss)
                if reason:row.update(status='FAILURE' if reason=='memory_limit' else 'TIMEOUT',reason=reason)
                elif code or not (directory/'RESULT.json').exists():row.update(status='INVALID',reason='process_or_missing_result')
                else:
                    try:row.update(json.loads((directory/'RESULT.json').read_text()))
                    except Exception as e:row.update(status='INVALID',reason='result_parse',error=repr(e))
            counts[row['status']]+=1;results.append(row);raw.write(json.dumps(row,separators=(',',':'))+'\n');raw.flush()
            if index%24==23:print(json.dumps(dict(completed=index+1,total=len(inputs['units']),outcomes=dict(counts),elapsed=time.monotonic()-started)),flush=True)
    bycase=collections.defaultdict(list)
    for r in results:bycase[r['case']].append(r)
    disagreements=[]
    for case,rs in bycase.items():
        values={r['method']:r['value'] for r in rs if r['status']=='SUCCESS'}
        if len(set(values.values()))>1:disagreements.append(dict(case=case,values=values))
    summary=dict(start=started,end=now(),elapsed_seconds=time.monotonic()-started,planned_units=432,recorded=len(results),
        outcomes=dict(counts),by_method={method:dict(collections.Counter(r['status'] for r in results if r['method']==method)) for method in METHODS},
        disagreements=disagreements,raw_sha256=sha(HERE/'RAW.jsonl'),final_evaluation=False)
    save(HERE/'SUMMARY.json',summary);print(json.dumps(summary,indent=2),flush=True)
if __name__=='__main__':{'prepare':prepare,'compatibility':compatibility,'run':run}[sys.argv[1]]()
