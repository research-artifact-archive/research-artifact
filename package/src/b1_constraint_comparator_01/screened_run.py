from pathlib import Path
import collections,datetime,hashlib,json,os,signal,subprocess,sys,time,traceback
import screened_dp
ROOT=Path(__file__).resolve().parent;DEST=ROOT/'screened01'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(p,data):
    with p.open('x') as f:json.dump(data,f,indent=2,sort_keys=True);f.write('\n')
def freeze():
    DEST.mkdir();files=[ROOT/x for x in ['screened_dp.py','screened_worker.py','screened_run.py','certificate.py','SCREENED_PLAN.md','DEV_INPUTS.json','DEV_RAW.jsonl','benchmark01/INPUTS.json','benchmark01/RAW.jsonl']]
    save(DEST/'MANIFEST.json',dict(utc=now(),python=sys.executable,development_units=8634,benchmark_units=78,files=[dict(path=str(p),sha256=sha(p)) for p in files]))
def alarm(sig,frame):raise TimeoutError('fixed conformance cap')
def check_manifest():
    m=json.loads((DEST/'MANIFEST.json').read_text())
    for f in m['files']:assert sha(f['path'])==f['sha256'],f['path']
    return m
def conform():
    check_manifest();save(DEST/'CONFORM_STARTED.json',dict(utc=now()))
    units=json.loads((ROOT/'DEV_INPUTS.json').read_text());expected={r['id']:r['value'] for r in map(json.loads,(ROOT/'DEV_RAW.jsonl').read_text().splitlines())}
    start=time.monotonic();counts=collections.Counter();signal.signal(signal.SIGALRM,alarm)
    with (DEST/'CONFORM_RAW.jsonl').open('x') as raw:
        for u in units:
            before=time.monotonic();left=180-(before-start)
            if left<=0:row=dict(id=u['id'],status='NOT_RUN')
            else:
                signal.setitimer(signal.ITIMER_REAL,min(3,left))
                try:
                    row=dict(id=u['id'],**screened_dp.solve(u['case']));assert row['value']==expected[u['id']],(row,expected[u['id']])
                except AssertionError:row=dict(id=u['id'],status='FAILURE',error=traceback.format_exc())
                except TimeoutError:row=dict(id=u['id'],status='TIMEOUT',error=traceback.format_exc())
                except Exception:row=dict(id=u['id'],status='INVALID',error=traceback.format_exc())
                finally:signal.setitimer(signal.ITIMER_REAL,0)
            row['seconds']=time.monotonic()-before;counts[row['status']]+=1;raw.write(json.dumps(row,separators=(',',':'))+'\n');raw.flush()
    s=dict(utc=now(),units=len(units),counts=dict(counts),seconds=time.monotonic()-start,raw_sha256=sha(DEST/'CONFORM_RAW.jsonl'));save(DEST/'CONFORM_SUMMARY.json',s);print(json.dumps(s,indent=2))
def benchmark():
    m=check_manifest();s=json.loads((DEST/'CONFORM_SUMMARY.json').read_text());assert s['counts']=={'SUCCESS':8634}
    save(DEST/'BENCH_STARTED.json',dict(utc=now(),pid=os.getpid()))
    units=json.loads((ROOT/'benchmark01/INPUTS.json').read_text());expected={r['id']:r['value'] for r in map(json.loads,(ROOT/'benchmark01/RAW.jsonl').read_text().splitlines()) if r['method']=='cp_sat' and r['status']=='SUCCESS'}
    start=time.monotonic();counts=collections.Counter();disagreements=[]
    with (DEST/'BENCH_RAW.jsonl').open('x') as raw:
        for u in units:
            out=DEST/'units'/u['id'];out.mkdir(parents=True);row=dict(id=u['id'],method='screened_dp',group=u['group'],prices=u['prices'],n=u['n'])
            if time.monotonic()-start>=420 or datetime.datetime.now(datetime.timezone.utc)>=datetime.datetime(2026,9,8,0,50,tzinfo=datetime.timezone.utc):row.update(status='NOT_RUN',reason='campaign_or_session_deadline')
            else:
                argv=[m['python'],str(ROOT/'screened_worker.py'),str(ROOT/'benchmark01/inputs'/(u['id']+'.json')),str(out)];save(out/'COMMAND.json',dict(argv=argv,seconds=5,rss_bytes=1073741824));before=time.monotonic();rss=0;reason=None
                with (out/'stdout.txt').open('xb') as stdout,(out/'stderr.txt').open('xb') as stderr:
                    p=subprocess.Popen(argv,stdout=stdout,stderr=stderr,start_new_session=True)
                    while p.poll() is None:
                        if time.monotonic()-before>=5:reason='wall_timeout'
                        else:
                            q=subprocess.run(['/bin/ps','-o','rss=','-p',str(p.pid)],capture_output=True,text=True,timeout=2)
                            try:rss=max(rss,int(q.stdout.strip())*1024)
                            except ValueError:pass
                            if rss>1073741824:reason='memory_limit'
                        if reason:
                            try:os.killpg(p.pid,signal.SIGKILL)
                            except ProcessLookupError:pass
                            break
                        time.sleep(.05)
                    code=p.wait(timeout=5)
                row.update(cold_seconds=time.monotonic()-before,exit_code=code,sampled_peak_rss_bytes=rss)
                if reason:row.update(status='FAILURE' if reason=='memory_limit' else 'TIMEOUT',reason=reason)
                elif code or not (out/'RESULT.json').exists():row.update(status='INVALID',reason='process_or_missing_result')
                else:row.update(json.loads((out/'RESULT.json').read_text()))
            if row['status']=='SUCCESS' and row['value']!=expected[u['id']]:disagreements.append(dict(id=u['id'],screened=row['value'],cp_sat=expected[u['id']]))
            counts[row['status']]+=1;raw.write(json.dumps(row,separators=(',',':'))+'\n');raw.flush()
    s=dict(utc=now(),units=len(units),counts=dict(counts),seconds=time.monotonic()-start,disagreements=disagreements,raw_sha256=sha(DEST/'BENCH_RAW.jsonl'));save(DEST/'BENCH_SUMMARY.json',s);print(json.dumps(s,indent=2))
if __name__=='__main__':{'freeze':freeze,'conform':conform,'benchmark':benchmark}[sys.argv[1]]()
