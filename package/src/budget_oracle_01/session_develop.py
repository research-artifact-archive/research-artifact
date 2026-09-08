from pathlib import Path
import collections,copy,datetime,hashlib,json,signal,sys,time,traceback
import oracle_session,values_certificate
ROOT=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(name,data):
 with (ROOT/name).open('x') as f:json.dump(data,f,indent=2,sort_keys=True);f.write('\n')
def freeze():
 paths=[ROOT/x for x in ['SESSION_EXTENSION_PLAN.md','oracle_session.py','values_certificate.py','session_develop.py','INPUTS.json','RAW.jsonl']]
 paths+=[Path(oracle_session.hybrid.__file__),Path(oracle_session.hybrid.curves.__file__),Path(values_certificate.packed_checker.__file__)]
 save('SESSION_MANIFEST.json',dict(utc=now(),units=4337,roots=21685,files=[dict(path=str(p.resolve()),sha256=sha(p)) for p in paths]))
def alarm(sig,frame):raise TimeoutError('fixed session conformance cap')
def run():
 m=json.loads((ROOT/'SESSION_MANIFEST.json').read_text())
 for f in m['files']:assert sha(f['path'])==f['sha256'],f['path']
 save('SESSION_STARTED.json',dict(utc=now()))
 units=json.loads((ROOT/'INPUTS.json').read_text());old={r['id']:r for r in map(json.loads,(ROOT/'RAW.jsonl').read_text().splitlines())};counts=collections.Counter();roots=0;start=time.monotonic();signal.signal(signal.SIGALRM,alarm)
 with (ROOT/'SESSION_RAW.jsonl').open('x') as raw:
  for u in units:
   before=time.monotonic();left=180-(before-start)
   if left<=0:r=dict(id=u['id'],status='NOT_RUN')
   else:
    signal.setitimer(signal.ITIMER_REAL,min(5,left))
    try:
     got=oracle_session.solve_many(u['case'],u['budgets']);encoded=json.dumps(got['artifact'],sort_keys=True,separators=(',',':')).encode();report=values_certificate.check(json.loads(encoded));prior=old[u['id']];assert prior['status']=='SUCCESS'
     assert got['values']==report['values']==[x['value'] for x in prior['roots']]
     r=dict(id=u['id'],status='SUCCESS',values=got['values'],certificate=report,artifact_bytes=len(encoded),artifact_sha256=hashlib.sha256(encoded).hexdigest(),stats=got['stats'],query_stats=got['query_stats']);roots+=len(u['budgets'])
    except AssertionError:r=dict(id=u['id'],status='FAILURE',error=traceback.format_exc())
    except TimeoutError:r=dict(id=u['id'],status='TIMEOUT',error=traceback.format_exc())
    except Exception:r=dict(id=u['id'],status='INVALID',error=traceback.format_exc())
    finally:signal.setitimer(signal.ITIMER_REAL,0)
   r['seconds']=time.monotonic()-before;counts[r['status']]+=1;raw.write(json.dumps(r,separators=(',',':'))+'\n');raw.flush()
 case=dict(cp=[[3,2],[7,2],[5,6],[1,2]],edges=[[0,1],[0,2],[1,3]]);a=oracle_session.solve_many(case,[0,1,2,4,2])['artifact'];assert values_certificate.check(a)['values']==[0,5,8,12,8]
 controls=[]
 for ident,change in [('missing-value',lambda x:x['values'].pop()),('changed-value',lambda x:x['values'].__setitem__(2,99)),('new-budget',lambda x:x['budgets'].__setitem__(0,999)),('extra-key',lambda x:x.update(unchecked=True)),('missing-node',lambda x:x['nodes'].pop(next(iter(x['nodes']))))]:
  x=copy.deepcopy(a);change(x);controls.append(dict(id=ident,artifact=x))
 save('SESSION_CONTROL_INPUTS.json',controls);results=[]
 for u in controls:
  try:values_certificate.check(u['artifact'])
  except (AssertionError,ValueError,KeyError,TypeError):results.append(dict(id=u['id'],status='REJECTED'))
  else:results.append(dict(id=u['id'],status='ACCEPTED_INVALID'))
 save('SESSION_CONTROLS.json',results);assert all(x['status']=='REJECTED' for x in results)
 s=dict(utc=now(),units=len(units),roots=roots,counts=dict(counts),controls_rejected=len(results),seconds=time.monotonic()-start,raw_sha256=sha(ROOT/'SESSION_RAW.jsonl'));save('SESSION_SUMMARY.json',s);print(json.dumps(s,indent=2))
if __name__=='__main__':{'freeze':freeze,'run':run}[sys.argv[1]]()
