from pathlib import Path
import hashlib,json,sys,time
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent;S=ROOT.parent
sys.path.insert(0,str(ROOT));import persistent,checker
sys.path.insert(0,str(S/'dependency_hybrid_01'));import hybrid
sys.path.insert(0,str(S/'dependency_hybrid_check_02'));import check as packed
sys.path.insert(0,str(S/'sweep_certificate_02'));import certificate as sweep

def write(path,obj):Path(path).write_text(json.dumps(obj,sort_keys=True,separators=(',',':'))+'\n')
unit=json.loads(Path(sys.argv[1]).read_text());out=Path(sys.argv[2]);method=sys.argv[3]
start=time.perf_counter();case=unit['case'];phases={}
d=(persistent if method=='persistent' else hybrid).compile_case(case)
phases['construction']=time.perf_counter()-start
t=time.perf_counter();payload=json.dumps(d,sort_keys=True,separators=(',',':')).encode();(out/'artifact.json').write_bytes(payload)
phases['serialization']=time.perf_counter()-t
write(out/'CONSTRUCTION.json',dict(phases=phases,artifact_bytes=len(payload),artifact_sha256=hashlib.sha256(payload).hexdigest(),
      route=d['route'],stats=d.get('stats'),completed_before_full_check=True))
t=time.perf_counter();d=json.loads((out/'artifact.json').read_bytes());phases['reload']=time.perf_counter()-t
if method=='persistent':root_profile=checker.profile(d,d['roots'][0])
elif d['route']=='ideal':root_profile=d['curves'][str(d['full'])]
else:
    root_profile=[];x=v=0
    for h,count in d['value_slopes']:root_profile.append([x,v,h]);x+=count;v+=h*count
    root_profile.append([x,v,0])
write(out/'ROOT_PROFILE.json',root_profile)
t=time.perf_counter()
if method=='persistent':report=checker.check(d)
else:report=(packed if d['route']=='ordered' else sweep).check(d)
phases['full_check']=time.perf_counter()-t
write(out/'CHECK.json',report);assert not report['violations']
t=time.perf_counter();budgets=[0,1,2,4,16,64,1<<40,1<<80]
values=[(persistent if method=='persistent' else hybrid).value(d if method=='persistent' else hybrid.load(d),b) for b in budgets]
phases['queries']=time.perf_counter()-t
write(out/'RESULT.json',dict(status='SUCCESS',phases=phases,worker_seconds=time.perf_counter()-start,
      budgets=budgets,values=values,report=report,route=d['route'],artifact_bytes=len(payload),
      artifact_sha256=hashlib.sha256(payload).hexdigest()))

