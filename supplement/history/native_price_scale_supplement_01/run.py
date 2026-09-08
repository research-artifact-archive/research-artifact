from pathlib import Path
import collections,datetime,hashlib,json,os,platform,signal,subprocess,sys,time
import worker
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'native_price_scale_01'
METHODS=['divisible_screened_ordered']
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(path,v):
    with path.open('x') as f:json.dump(v,f,indent=2,sort_keys=True);f.write('\n')
def prepare():
    data=json.loads((OLD/'INPUTS.json').read_text())
    prior={r['case']:r['value'] for r in map(json.loads,(OLD/'RAW.jsonl').read_text().splitlines()) if r['method']=='packed' and r['status']=='SUCCESS'}
    data['units']=[dict(id=c['id']+'/'+METHODS[0],case=c['id'],method=METHODS[0],input=c['input'],expected=prior[c['id']]) for c in data['cases']]
    save(HERE/'INPUTS.json',data)
    files=[HERE/'PLAN.md',HERE/'worker.py',Path(__file__),HERE/'INPUTS.json',OLD/'worker.py',worker.COMP,worker.SCREEN,OLD/'INPUTS.json',OLD/'RAW.jsonl',OLD/'SUMMARY.json',OLD/'COMPAT_INPUTS.json',OLD/'COMPAT_RESULT.json']
    save(HERE/'MANIFEST.json',dict(created=now(),cases=144,vectors=36,units=144,compatibility_inputs=128,
        files=[dict(path=str(p),sha256=sha(p)) for p in files],python=sys.executable,python_version=sys.version,platform=platform.platform(),
        timeout_seconds=6,sampled_rss_cap_bytes=1073741824,rss_poll_seconds=.05,aggregate_timeout_seconds=3600,
        methods=METHODS,final_evaluation=False,exclusions=[],retry_allowed=False))
    print('fixed 144 additional changed-method units on known roots')
def verify():
    m=json.loads((HERE/'MANIFEST.json').read_text())
    for p in m['files']:assert sha(Path(p['path']))==p['sha256']
    for c in json.loads((HERE/'INPUTS.json').read_text())['cases']:assert sha(Path(c['input']))==c['sha256']
    return m

def compatibility():
    verify();prior={r['id']:r['reference'] for r in json.loads((OLD/'COMPAT_RESULT.json').read_text())['rows']};rows=[]
    for g in json.loads((OLD/'COMPAT_INPUTS.json').read_text()):
        try:
            result=worker.solve(g);row=dict(id=g['id'],status='SUCCESS',reference=prior[g['id']],result=result,agreement=result['value']==prior[g['id']])
        except Exception as e:row=dict(id=g['id'],status='INVALID',error=repr(e))
        rows.append(row)
    result=dict(created=now(),known_inputs=128,outcomes=dict(collections.Counter(r['status'] for r in rows)),disagreements=sum(r.get('agreement') is False for r in rows),rows=rows)
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
        values['prior_packed']=next(r['expected'] for r in rs)
        if len(set(values.values()))>1:disagreements.append(dict(case=case,values=values))
    summary=dict(start=started,end=now(),elapsed_seconds=time.monotonic()-started,planned_units=144,recorded=len(results),
        outcomes=dict(counts),by_method={method:dict(collections.Counter(r['status'] for r in results if r['method']==method)) for method in METHODS},
        disagreements=disagreements,raw_sha256=sha(HERE/'RAW.jsonl'),final_evaluation=False)
    save(HERE/'SUMMARY.json',summary);print(json.dumps(summary,indent=2),flush=True)
if __name__=='__main__':{'prepare':prepare,'compatibility':compatibility,'run':run}[sys.argv[1]]()
