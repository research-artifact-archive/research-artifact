from pathlib import Path
import collections,datetime,hashlib,itertools,json,os,platform,random,signal,subprocess,sys,time
import worker
HERE=Path(__file__).resolve().parent
METHODS=['packed','full_andor','prism_explicit_phase','prism_mtbdd_phase','prism_mtbdd_objects']
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
    with p.open('x') as f:json.dump(v,f,indent=2,sort_keys=True);f.write('\n')
def prepare():
    (HERE/'inputs').mkdir();rng=random.Random(202609072222);vectors=[];cases=[];units=[]
    prior=json.loads((worker.GRAPH.parent/'INPUTS.json').read_text());known={tuple(map(tuple,g['jobs'])) for g in prior}
    oracle=worker.module(worker.GRAPH,'unrestricted_oracle')
    for family,n in itertools.product(['equal','heterogeneous'],[2,3,4,5,6,8]):
        lengths=[16]*n if family=='equal' else [rng.randint(1,64) for _ in range(n)];jobs=[(2*w,w) for w in lengths]
        vid=f'{family}/n{n}';vectors.append(dict(id=vid,jobs=jobs,overlaps_prior_guard_vector=tuple(jobs) in known))
        for B in ([0,1,2] if family=='equal' and n in (4,8) else [1,2]):
            cid=vid+f'/B{B}';path=HERE/'inputs'/(cid.replace('/','_')+'.json')
            expected=sum(w for w,p in jobs)+oracle.h16(jobs,B)[B][-1]
            case=dict(id=cid,vector=vid,family=family,n=n,jobs=jobs,budget=B,expected=expected)
            save(path,case);case.update(input=str(path),sha256=sha(path));cases.append(case)
            for method in METHODS:units.append(dict(id=cid+'/'+method,case=cid,method=method,input=str(path),expected=expected))
    save(HERE/'INPUTS.json',dict(vectors=vectors,cases=cases,units=units))
    files=[HERE/'PLAN.md',HERE/'worker.py',Path(__file__),HERE/'INPUTS.json',worker.GRAPH,worker.GRAPH.parent.parent/'primitive_rmw_01/explore.py',worker.CODEC,worker.COMP,worker.PRISM]
    save(HERE/'MANIFEST.json',dict(created=now(),vectors=12,roots=26,units=130,methods=METHODS,
        files=[dict(path=str(p),sha256=sha(p)) for p in files],python=sys.executable,python_version=sys.version,platform=platform.platform(),
        wall_timeout_seconds=8,aggregate_rss_cap_bytes=1073741824,poll_seconds=.05,overall_seconds=3600,
        prism_env=worker.ENV,final_evaluation=False,exclusions=[],retry_allowed=False))
    print('fixed 12 priced vectors/26 roots/130 units; prior-vector matches',sum(v['overlaps_prior_guard_vector'] for v in vectors))
def run():
    m=json.loads((HERE/'MANIFEST.json').read_text());data=json.loads((HERE/'INPUTS.json').read_text())
    for p in m['files']:assert sha(Path(p['path']))==p['sha256']
    for c in data['cases']:assert sha(Path(c['input']))==c['sha256']
    deadline=datetime.datetime(2026,9,8,0,50,tzinfo=datetime.timezone.utc)
    save(HERE/'RUN_STARTED.json',dict(utc=now(),parent_pid=os.getpid(),manifest_sha256=sha(HERE/'MANIFEST.json')))
    started=time.monotonic();rows=[];counts=collections.Counter()
    with (HERE/'RAW.jsonl').open('x') as raw:
        for index,u in enumerate(data['units']):
            row=dict(**u,index=index,start=now());dest=HERE/'units'/u['id'];dest.mkdir(parents=True)
            if datetime.datetime.now(datetime.timezone.utc)>=deadline or time.monotonic()-started>=3600:
                row.update(status='NOT_RUN',reason='session_or_campaign_deadline')
            else:
                argv=[m['python'],str(HERE/'worker.py'),u['method'],u['input'],str(dest)]
                save(dest/'COMMAND.json',dict(argv=argv,wall_timeout_seconds=8,aggregate_rss_cap_bytes=1073741824))
                proc=None;reason=None;peak=0;start=time.monotonic()
                try:
                    with (dest/'stdout.txt').open('xb') as so,(dest/'stderr.txt').open('xb') as se:
                        proc=subprocess.Popen(argv,stdout=so,stderr=se,start_new_session=True)
                        while proc.poll() is None:
                            if time.monotonic()-start>=8:reason='wall_timeout'
                            elif datetime.datetime.now(datetime.timezone.utc)>=deadline:reason='session_deadline'
                            else:
                                ps=subprocess.run(['/bin/ps','-axo','pid=,pgid=,rss='],capture_output=True,text=True,timeout=2)
                                group=0
                                for line in ps.stdout.splitlines():
                                    pid,pgid,rss=map(int,line.split())
                                    if pgid==proc.pid:group+=rss*1024
                                peak=max(peak,group)
                                if peak>1073741824:reason='memory_limit'
                            if reason:break
                            time.sleep(.05)
                        if proc.poll() is None:os.killpg(proc.pid,signal.SIGKILL)
                        code=proc.wait(timeout=5)
                    row.update(exit_code=code,cold_seconds=time.monotonic()-start,sampled_group_peak_rss_bytes=peak)
                    if reason:row.update(status='FAILURE' if reason=='memory_limit' else 'TIMEOUT',reason=reason)
                    elif code or not (dest/'RESULT.json').exists():row.update(status='INVALID',reason='process_or_missing_result')
                    else:row.update(json.loads((dest/'RESULT.json').read_text()))
                except Exception as e:row.update(status='INVALID',reason='orchestration_error',error=repr(e),cold_seconds=time.monotonic()-start)
                finally:
                    if proc is not None and proc.poll() is None:
                        try:os.killpg(proc.pid,signal.SIGKILL)
                        except ProcessLookupError:pass
                        proc.wait(timeout=5)
                if row['status']=='SUCCESS':row['agreement']=row.get('value')==u['expected']
            rows.append(row);counts[row['status']]+=1;raw.write(json.dumps(row,separators=(',',':'))+'\n');raw.flush()
            print(json.dumps(dict(completed=index+1,total=130,id=u['id'],status=row['status'],outcomes=dict(counts),elapsed=time.monotonic()-started)),flush=True)
    summary=dict(end=now(),elapsed_seconds=time.monotonic()-started,planned=130,recorded=len(rows),outcomes=dict(counts),
        by_method={method:dict(collections.Counter(r['status'] for r in rows if r['method']==method)) for method in METHODS},
        disagreements=[r for r in rows if r.get('agreement') is False],raw_sha256=sha(HERE/'RAW.jsonl'),final_evaluation=False)
    save(HERE/'SUMMARY.json',summary);print(json.dumps(summary,indent=2))
if __name__=='__main__':{'prepare':prepare,'run':run}[sys.argv[1]]()
