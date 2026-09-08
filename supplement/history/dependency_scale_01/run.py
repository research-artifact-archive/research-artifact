import collections,datetime,hashlib,json,os,pathlib,platform,random,signal,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parent
SOURCE=ROOT.parent/'dependency_curves_01'
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
    with p.open('x') as f:json.dump(v,f,indent=2,sort_keys=True);f.write('\n')

def prepare():
    rng=random.Random(202609080007)
    random_graphs={}
    for w in [4,8]:
        for layers in [4,8]:
            random_graphs[w,layers]=[[l*w+i,(l+1)*w+j] for l in range(layers-1) for i in range(w) for j in range(w) if rng.randrange(2)==0]
    templates=[]
    for n in [8,16,32,64]:templates.append((f'chain_{n}',n,[[i,i+1] for i in range(n-1)]))
    for w in [2,3,4]:
        for length in [4,8,12]:
            templates.append((f'chains_w{w}_l{length}',w*length,[[k*length+j,k*length+j+1] for k in range(w) for j in range(length-1)]))
    for w in [2,4,8]:
        for layers in [4,8]:
            edges=[[l*w+i,(l+1)*w+j] for l in range(layers-1) for i in range(w) for j in range(w)]
            templates.append((f'full_layers_w{w}_l{layers}',w*layers,edges))
    for n in [8,16,24]:
        edges=[[i,j] for i in range(0,n,2) for j in [i-1,i+1] if 0<=j<n]
        templates.append((f'fence_{n}',n,edges))
    for w in [4,8]:
        for layers in [4,8]:templates.append((f'random_layers_w{w}_l{layers}',w*layers,random_graphs[w,layers]))
    for n in [8,12,16]:templates.append((f'independent_{n}',n,[]))
    assert len(templates)==29
    cases=[];(ROOT/'inputs').mkdir()
    for name,n,edges in templates:
        for prices in ['SMALL','WIDE_C','WIDE_P']:
            cp=[]
            for j in range(n):
                if prices=='SMALL':c=rng.randint(1,64);p=rng.randint(0,256)
                elif prices=='WIDE_C':c=rng.randint(1,1<<32);p=rng.randint(0,8*c)
                else:c=rng.randint(1,64);p=rng.randint(1,256)*(1<<40)+rng.randint(0,255)
                cp.append([c,p])
            saturation=sum((p+c-1)//c for c,p in cp)
            case=dict(id=f'{name}_{prices}',template=name,prices=prices,edges=edges,cp=cp,
                      budgets=sorted({0,1,2,n,saturation//2,saturation}))
            save(ROOT/'inputs'/f"{case['id']}.json",case);cases.append(case)
    save(ROOT/'INPUTS.json',cases)
    files=[ROOT/'PLAN.md',ROOT/'worker.py',ROOT/'run.py',ROOT/'INPUTS.json',SOURCE/'curves.py',SOURCE/'checker.py']
    files+=sorted((ROOT/'inputs').glob('*.json'))
    save(ROOT/'MANIFEST.json',dict(created=now(),files=[dict(path=str(p),sha256=sha(p)) for p in files],
        cases=87,units=174,python=sys.executable,python_version=sys.version,platform=platform.platform(),
        cap_seconds=5,rss_cap_bytes=1073741824,rss_poll_seconds=.05,campaign_cap_seconds=600,
        final_evaluation=False,retry_allowed=False,exclusions=[]))
    print('fixed87inputs174units')

def run():
    m=json.loads((ROOT/'MANIFEST.json').read_text())
    for entry in m['files']:assert sha(pathlib.Path(entry['path']))==entry['sha256'],entry['path']
    cases=json.loads((ROOT/'INPUTS.json').read_text());deadline=datetime.datetime(2026,9,8,0,50,tzinfo=datetime.timezone.utc)
    save(ROOT/'RUN_STARTED.json',dict(start=now(),manifest_sha256=sha(ROOT/'MANIFEST.json'),parent_pid=os.getpid()))
    start=time.monotonic();rows=[];counts=collections.Counter()
    with (ROOT/'RAW.jsonl').open('x') as raw:
        for case in cases:
            compile_ok=False
            for method in ['compile','check']:
                directory=ROOT/'units'/case['id']/method;directory.mkdir(parents=True)
                row=dict(case=case['id'],method=method,started=now())
                source=ROOT/'inputs'/f"{case['id']}.json" if method=='compile' else directory.parent/'compile'/'controller.json'
                if method=='check' and not compile_ok:row.update(status='NOT_RUN',reason='compiler_not_successful')
                elif time.monotonic()-start>=600 or datetime.datetime.now(datetime.timezone.utc)>=deadline:
                    row.update(status='NOT_RUN',reason='campaign_or_session_deadline')
                else:
                    argv=[m['python'],str(ROOT/'worker.py'),method,str(source),str(directory)]
                    save(directory/'COMMAND.json',dict(argv=argv,timeout_seconds=5,rss_cap_bytes=1073741824))
                    t=time.monotonic();rss=0;reason=None
                    with (directory/'stdout.txt').open('xb') as out,(directory/'stderr.txt').open('xb') as err:
                        proc=subprocess.Popen(argv,stdout=out,stderr=err,start_new_session=True)
                        while proc.poll() is None:
                            if time.monotonic()-t>=5:reason='wall_timeout'
                            elif time.monotonic()-start>=600 or datetime.datetime.now(datetime.timezone.utc)>=deadline:reason='campaign_or_session_deadline'
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
                    row.update(cold_seconds=time.monotonic()-t,exit_code=code,sampled_peak_rss_bytes=rss)
                    if reason:row.update(status='FAILURE' if reason=='memory_limit' else 'TIMEOUT',reason=reason)
                    elif code or not (directory/'RESULT.json').exists():row.update(status='INVALID',reason='process_or_missing_result')
                    else:
                        try:row.update(json.loads((directory/'RESULT.json').read_text()))
                        except Exception as e:row.update(status='INVALID',reason='result_parse',error=repr(e))
                if method=='compile':compile_ok=row['status']=='SUCCESS'
                counts[row['status']]+=1;rows.append(row);raw.write(json.dumps(row,separators=(',',':'))+'\n');raw.flush()
                if len(rows)%12==0:print(json.dumps(dict(completed=len(rows),total=174,outcomes=dict(counts),elapsed=time.monotonic()-start)),flush=True)
    summary=dict(cases=87,planned_units=174,recorded=len(rows),outcomes=dict(counts),
        by_method={method:dict(collections.Counter(r['status'] for r in rows if r['method']==method)) for method in ['compile','check']},
        H6_violations=[dict(case=r['case'],runs=r['positive_root_runs']) for r in rows if r.get('H6')=='FAIL'],
        maximum_positive_root_runs=max([r.get('positive_root_runs',0) for r in rows]),
        elapsed_seconds=time.monotonic()-start,raw_sha256=sha(ROOT/'RAW.jsonl'),final_evaluation=False)
    save(ROOT/'SUMMARY.json',summary);print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':{'prepare':prepare,'run':run}[sys.argv[1]]()
