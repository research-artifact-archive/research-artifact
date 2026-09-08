from pathlib import Path
import hashlib,importlib.util,json,sys,time
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent;S=ROOT.parent
sys.path.insert(0,str(S/'fixed_order_profile_02'));import persistent
spec=importlib.util.spec_from_file_location('shared_pipeline_checker',ROOT/'checker.py')
checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)
def write(path,obj):Path(path).write_text(json.dumps(obj,sort_keys=True,separators=(',',':'))+'\n')
unit=json.loads(Path(sys.argv[1]).read_text());out=Path(sys.argv[2]);start=time.perf_counter();phases={}
d=persistent.compile_case(unit['case']);phases['construction']=time.perf_counter()-start
t=time.perf_counter();payload=json.dumps(d,sort_keys=True,separators=(',',':')).encode();(out/'artifact.json').write_bytes(payload)
phases['serialization']=time.perf_counter()-t
write(out/'CONSTRUCTION.json',dict(phases=phases,artifact_bytes=len(payload),artifact_sha256=hashlib.sha256(payload).hexdigest(),route=d['route'],stats=d['stats'],completed_before_full_check=True))
t=time.perf_counter();d=json.loads((out/'artifact.json').read_bytes());phases['reload']=time.perf_counter()-t
write(out/'ROOT_PROFILE.json',checker.shape.profile(d,d['roots'][0]))
t=time.perf_counter();report=checker.check(d);phases['full_check']=time.perf_counter()-t
write(out/'CHECK.json',report);assert not report['violations']
t=time.perf_counter();budgets=[0,1,2,4,16,64,1<<40,1<<80];values=[persistent.value(d,b) for b in budgets]
phases['queries']=time.perf_counter()-t
write(out/'RESULT.json',dict(status='SUCCESS',phases=phases,worker_seconds=time.perf_counter()-start,budgets=budgets,values=values,report=report,
      route=d['route'],artifact_bytes=len(payload),artifact_sha256=hashlib.sha256(payload).hexdigest()))
