from pathlib import Path
import collections,copy,datetime,hashlib,json,signal,sys,time,traceback
import screened_dp,policy_checker
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(name,data):
    with (ROOT/name).open('x') as f:json.dump(data,f,indent=2,sort_keys=True);f.write('\n')
def freeze():
    files=[ROOT/x for x in ['SCREENED_PLAN.md','screened_dp.py','policy_checker.py','screened_develop.py','checker.py','DEV_INPUTS.json','DEV_RAW.jsonl']]
    save('SCREENED_MANIFEST.json',dict(utc=now(),units=4336,files=[dict(path=str(p),sha256=sha(p)) for p in files]))
def alarm(sig,frame):raise TimeoutError('fixed cap')
def run():
    m=json.loads((ROOT/'SCREENED_MANIFEST.json').read_text())
    for f in m['files']:assert sha(f['path'])==f['sha256'],f['path']
    save('SCREENED_STARTED.json',dict(utc=now()))
    case=dict(cp=[[1,3]],edges=[])
    valid=dict(schema='specified-budget-screened-policy-v1',budget=2,root='1:2',nodes={'1:2':dict(kind='fixed',mask=1,budget=2,order=[0],modes=[['F','F']])})
    assert policy_checker.check(case,valid)['value']==2
    mutants=[]
    x=copy.deepcopy(valid);x['nodes']['1:2']['kind']='zero';mutants.append(x)
    x=copy.deepcopy(valid);x['nodes']['1:2']['order']=[0,0];mutants.append(x)
    x=copy.deepcopy(valid);x['nodes']['1:2']['modes']=[['X','F']];mutants.append(x)
    x=copy.deepcopy(valid);x['nodes']['1:2']=dict(kind='choice',mask=1,budget=2,job=0,mode='F',success='0:2',failure='0:1');x['nodes']['0:2']=dict(kind='zero',mask=0,budget=2);mutants.append(x)
    controls=[]
    for j,x in enumerate(mutants):
        try:policy_checker.check(case,x)
        except AssertionError:controls.append(dict(id=j,status='REJECTED'))
        else:raise AssertionError(('accepted malformed',x))
    save('SCREENED_CONTROLS.json',controls)
    inputs=json.loads((ROOT/'DEV_INPUTS.json').read_text());expected={r['id']:r['value'] for r in map(json.loads,(ROOT/'DEV_RAW.jsonl').read_text().splitlines())};start=time.monotonic();counts=collections.Counter();signal.signal(signal.SIGALRM,alarm)
    with (ROOT/'SCREENED_RAW.jsonl').open('x') as raw:
        for u in inputs:
            before=time.monotonic();left=180-(before-start)
            if left<=0:row=dict(id=u['id'],status='NOT_RUN')
            else:
                signal.setitimer(signal.ITIMER_REAL,min(3,left))
                try:
                    row=dict(id=u['id'],**screened_dp.solve(u['case'],2));encoded=json.dumps(row['artifact'],sort_keys=True,separators=(',',':')).encode();report=policy_checker.check(u['case'],json.loads(encoded));row.update(certificate_report=report,artifact_bytes=len(encoded))
                    assert row['value']==report['value']==expected[u['id']],(row,expected[u['id']])
                except AssertionError:row=dict(id=u['id'],status='FAILURE',error=traceback.format_exc())
                except TimeoutError:row=dict(id=u['id'],status='TIMEOUT',error=traceback.format_exc())
                except Exception:row=dict(id=u['id'],status='INVALID',error=traceback.format_exc())
                finally:signal.setitimer(signal.ITIMER_REAL,0)
            row['seconds']=time.monotonic()-before;counts[row['status']]+=1;raw.write(json.dumps(row,separators=(',',':'))+'\n');raw.flush()
    s=dict(utc=now(),units=len(inputs),counts=dict(counts),seconds=time.monotonic()-start,raw_sha256=sha(ROOT/'SCREENED_RAW.jsonl'));save('SCREENED_SUMMARY.json',s);print(json.dumps(s,indent=2))
if __name__=='__main__':{'freeze':freeze,'run':run}[sys.argv[1]]()
