#!/usr/bin/env python3
"""Replay known successful checks and scan retained benchmarks; no sample increase."""
from pathlib import Path
import argparse,collections,datetime,hashlib,importlib,json,os,shutil,signal,subprocess,sys,time,traceback
ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data/extended'
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(path,value):
 with path.open('x') as f:json.dump(value,f,indent=2,sort_keys=True);f.write('\n')
def load(path):return json.loads(path.read_text())
def rows(path):return [json.loads(s) for s in path.read_text().splitlines()]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def verify():
 m=load(ROOT/'MANIFEST.json');listed=set()
 for r in m['files']:
  p=ROOT/r['path'];assert not p.is_symlink() and p.is_file(),r['path']
  assert p.stat().st_size==r['bytes'] and sha(p)==r['sha256'],r['path'];listed.add(r['path'])
 actual={str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p != ROOT/'MANIFEST.json'}
 assert actual==listed,dict(unlisted=sorted(actual-listed),missing=sorted(listed-actual))
 return dict(files=len(listed),manifest_sha256=sha(ROOT/'MANIFEST.json'))
def module(directory,name):
 sys.path.insert(0,str(ROOT/'src'/directory));m=importlib.import_module(name)
 assert Path(m.__file__).resolve().is_relative_to(ROOT),m.__file__
 return m
def alarm(sig,frame):raise TimeoutError('fixed reproduction limit')
def roundtrip(value):return json.loads(json.dumps(value,sort_keys=True,separators=(',',':')))
def run_units(out,units,fn,quick,limit=3,stage_limit=180):
 if quick:units=units[:16]+units[-16:] if len(units)>32 else units
 save(out/'START.json',dict(utc=now(),planned_ids=[u['id'] for u in units],known_successful_inputs=True,quick_smoke=quick,unit_seconds=limit,stage_seconds=stage_limit,scientific_sample_increase=False))
 counts=collections.Counter();start=time.monotonic();signal.signal(signal.SIGALRM,alarm)
 with (out/'RAW.jsonl').open('x') as f:
  for k,u in enumerate(units):
   before=time.monotonic();left=stage_limit-(before-start)
   if left<=0:r=dict(id=u['id'],status='NOT_RUN')
   else:
    signal.setitimer(signal.ITIMER_REAL,min(limit,left))
    try:r=dict(id=u['id'],status='SUCCESS',result=fn(u))
    except TimeoutError:r=dict(id=u['id'],status='TIMEOUT',error=traceback.format_exc())
    except AssertionError:r=dict(id=u['id'],status='FAILURE',error=traceback.format_exc())
    except Exception:r=dict(id=u['id'],status='INVALID',error=traceback.format_exc())
    finally:signal.setitimer(signal.ITIMER_REAL,0)
   r['seconds']=time.monotonic()-before;counts[r['status']]+=1;f.write(json.dumps(r,separators=(',',':'))+'\n');f.flush()
   if (k+1)%1000==0:print(json.dumps(dict(completed=k+1,planned=len(units),counts=dict(counts))),flush=True)
 result=dict(planned=len(units),counts=dict(counts),success=counts['SUCCESS']==len(units),seconds=time.monotonic()-start,quick_smoke=quick,scientific_sample_increase=False)
 save(out/'SUMMARY.json',result);return result
def hardness(out,args):
 m=module('dag_hardness_01','check');d=DATA/'dag_hardness_01';units=load(d/'INPUTS.json');expected={r['id']:r for r in rows(d/'RAW.jsonl')}
 def one(u):
  actual=m.check_unit(u);e=expected[u['id']];assert e['status']=='SUCCESS'
  for field,value in actual.items():assert value==e[field],(field,value,e[field])
  return actual
 return run_units(out,units,one,args.quick,limit=2)
def compare(out,args,b):
 name=f'b{b}_'+('constraint_comparator_01' if b==1 else 'contingent_comparator_01');d=DATA/name
 dp=module(name,'screened_dp');checker=module(name,'certificate' if b==1 else 'checker')
 policy=checker if b==1 else module(name,'policy_checker')
 cp=module(name,'comparator') if args.with_cp else None
 if cp:
  import ortools
  assert ortools.__version__=='9.15.6755',ortools.__version__
 units=load(d/'DEV_INPUTS.json');expected={r['id']:r['value'] for r in rows(d/'DEV_RAW.jsonl')}
 def one(u):
  case=u['case'];r=dp.solve(case) if b==1 else dp.solve(case,b)
  assert r['status']=='SUCCESS';artifact=roundtrip(r['certificate' if b==1 else 'artifact'])
  scan=policy.scan(case,artifact) if b==1 else policy.check(case,artifact)
  assert scan['value']==r['value']==expected[u['id']]
  scalar=checker.subset_dp(case)[0] if b==1 else checker.scalar(case,b)[0]
  assert scalar==r['value']
  result=dict(value=r['value'],policy=artifact,scanner=scan,dp_stats=r['stats'],scalar=scalar)
  if cp:
   cr=cp.solve(case,seconds=1) if b==1 else cp.solve(case,budget=b,seconds=1)
   assert cr['status']=='SUCCESS' and cr['value']==scalar,cr
   ca=roundtrip(cr['certificate' if b==1 else 'artifact'])
   cs=checker.scan(case,ca) if b==1 else checker.check(case,ca)
   assert cs['value']==scalar
   result['cp']=dict(value=cr['value'],solver_status=cr['solver_status'],policy=ca,scanner=cs)
  return result
 return run_units(out,units,one,args.quick)
def benchmarks(out,args,b):
 name=f'b{b}_'+('constraint_comparator_01' if b==1 else 'contingent_comparator_01');d=DATA/name
 checker=module(name,'certificate' if b==1 else 'checker');policy=checker if b==1 else module(name,'policy_checker')
 cases={u['id']:u['case'] for u in load(d/'benchmark01/INPUTS.json')};raw=rows(d/'benchmark01/RAW.jsonl')
 if b==1:raw+=rows(d/'screened01/BENCH_RAW.jsonl')
 counts=collections.Counter((r['method'],r['status']) for r in raw);scanned=collections.Counter();output=[]
 expected={1:{'cp_sat':(78,0),'subset_dp':(56,22),'all_budget':(53,25),'screened_dp':(68,10)},2:{'cp_sat':(48,0),'screened_dp':(48,0),'all_budget':(46,2)}}[b]
 assert len(raw)==(312 if b==1 else 144)
 assert {(r['id'],r['method']) for r in raw}=={(i,m) for i in cases for m in expected}
 for method,(success,timeout) in expected.items():
  assert counts[method,'SUCCESS']==success and counts[method,'TIMEOUT']==timeout
  assert sum(v for (m,s),v in counts.items() if m==method)==success+timeout
 for r in raw:
  if r['status']!='SUCCESS':continue
  case=cases[r['id']]
  if b==1:scan=checker.scan(case,roundtrip(r['certificate']))
  else:
   a=roundtrip(r['artifact']) if 'artifact' in r else load(d/'benchmark01/units'/r['id']/r['method']/'policy.json');scan=(policy if a['schema']=='specified-budget-screened-policy-v1' else checker).check(case,a)
  assert scan['value']==r['value'],r['id'];scanned[r['method']]+=1
  output.append(dict(id=r['id'],method=r['method'],value=scan['value']))
 save(out/'SCANNED.json',output);result=dict(success=True,records=len(raw),historical_counts={m:{s:counts[m,s] for s in ['SUCCESS','TIMEOUT']} for m in expected},successful_policies_scanned=dict(scanned),timeout_units_rerun=0,scientific_sample_increase=False)
 save(out/'SUMMARY.json',result);return result
def family(out,args):
 d=DATA/'adaptivity_family_operational_01';data=load(d/'NATIVE_INPUTS.json');units=data['units'];assert len(units)==110
 java=args.java or shutil.which('java');javac=args.javac or shutil.which('javac');assert java and javac,'JDK required'
 save(out/'START.json',dict(utc=now(),planned=110,selected_after_gap_exploration=True,scientific_sample_increase=False,compile_seconds=30,execute_seconds=60))
 for n in ['CASES.tsv','INPUTS.tsv']:shutil.copy2(d/n,out/n)
 shutil.copytree(d/'profiles',out/'profiles');source=ROOT/'src/adaptivity_family_operational_01/NativeDagFinal.java'
 # Java source is data because its suffix is not Python; retain exact copied bytes.
 if not source.exists():source=d/'NativeDagFinal.java'
 times={};t=time.monotonic();p=subprocess.run([javac,'-d',str(out/'classes'),str(source)],capture_output=True,text=True,timeout=30)
 times['compile_seconds']=time.monotonic()-t;save(out/'COMPILE.json',dict(exit=p.returncode,stdout=p.stdout,stderr=p.stderr));assert p.returncode==0
 t=time.monotonic()
 with (out/'RAW.jsonl').open('xb') as f,(out/'STDERR.txt').open('xb') as err:
  p=subprocess.run([java,'-Xmx256m','-XX:ActiveProcessorCount=1','-cp',str(out/'classes'),'NativeDagFinal',str(out)],stdout=f,stderr=err,timeout=60)
 times['execution_seconds']=time.monotonic()-t;assert p.returncode==0
 dev=module('dependency_native_01','experiment');observed=rows(out/'RAW.jsonl');ids=[r['id'] for r in observed]
 assert len(ids)==len(set(ids))==110;observed={r['id']:r for r in observed};assert set(observed)=={u['id'] for u in units}
 t=time.monotonic();groups=collections.defaultdict(list)
 for u in units:
  r=observed[u['id']];assert r['status']=='SUCCESS';e=dev.expected(data['cases'][u['case']],u);assert e==u['expected']
  for k,v in e.items():assert r[k]==v,(u['id'],k)
  groups[u['cell'],u['kind']].append(r['cost'])
 for c in data['cells']:
  for policy in c['policies']:assert max(groups[c['id'],policy['kind']])==policy['expected_max']
 times['checking_seconds']=time.monotonic()-t;result=dict(success=True,planned=110,counts={'SUCCESS':110},times=times,scientific_sample_increase=False);save(out/'SUMMARY.json',result);return result
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['verify','hardness','b1','b2','bench1','bench2','family','all']);p.add_argument('--out',type=Path,required=True);p.add_argument('--quick',action='store_true');p.add_argument('--with-cp',action='store_true');p.add_argument('--java');p.add_argument('--javac');p.add_argument('--worker',action='store_true',help=argparse.SUPPRESS);args=p.parse_args()
 assert sys.version_info>=(3,10) and not sys.flags.optimize
 out=args.out.resolve()
 if args.worker:
  assert out.is_dir() and not any(out.iterdir());f={'hardness':hardness,'b1':lambda o,a:compare(o,a,1),'b2':lambda o,a:compare(o,a,2),'bench1':lambda o,a:benchmarks(o,a,1),'bench2':lambda o,a:benchmarks(o,a,2),'family':family}[args.mode]
  try:result=f(out,args)
  except Exception:save(out/'HARNESS_ERROR.json',dict(utc=now(),error=traceback.format_exc()));raise
  return 0 if result['success'] else 1
 verified=verify();out.mkdir(parents=True,exist_ok=False);save(out/'START.json',dict(utc=now(),mode=args.mode,verification=verified,with_cp=args.with_cp,quick_smoke=args.quick,python_version=sys.version,scientific_sample_increase=False))
 stages=['hardness','b1','b2','bench1','bench2','family'] if args.mode=='all' else ([] if args.mode=='verify' else [args.mode]);results={}
 for stage in stages:
  sub=out/stage;sub.mkdir();cmd=[sys.executable,'-B',str(Path(__file__).resolve()),stage,'--out',str(sub),'--worker']
  for flag in ['quick','with_cp']:
   if getattr(args,flag):cmd.append('--'+flag.replace('_','-'))
  for flag in ['java','javac']:
   if getattr(args,flag):cmd+=['--'+flag,getattr(args,flag)]
  with (out/(stage+'-stdout.txt')).open('xb') as stdout,(out/(stage+'-stderr.txt')).open('xb') as stderr:
   try:r=subprocess.run(cmd,stdout=stdout,stderr=stderr,timeout=210);code=r.returncode
   except subprocess.TimeoutExpired:code=None
  result=load(sub/'SUMMARY.json') if (sub/'SUMMARY.json').exists() else dict(success=False,reason='worker failed or timed out')
  result['process_exit']=code;result['success']=result['success'] and code==0;results[stage]=result;print(json.dumps(dict(stage=stage,**result)),flush=True)
 result=dict(success=all(r['success'] for r in results.values()),stages=results,scientific_sample_increase=False);save(out/'SUMMARY.json',result);return 0 if result['success'] else 1
if __name__=='__main__':raise SystemExit(main())
