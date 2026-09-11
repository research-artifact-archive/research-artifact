"""Replay fixed residual-safety studies; no new population or native timing."""
from pathlib import Path
import gzip,hashlib,importlib.util,io,json,shutil,subprocess,sys,tarfile,time

HERE=Path(__file__).resolve().parent;STAGE=sys.argv[1];OUT=Path(sys.argv[2]);START=time.monotonic()
assert __debug__ and STAGE=='residual-safety'
SESSION='RESUMED_20260911_1123';PREVIOUS='RESUMED_20260910_1617'
SRC=HERE/'evidence'/SESSION;DST=OUT/'replay'/SESSION;DST.mkdir(parents=True)
stable=[]
def sha(b):return hashlib.sha256(b).hexdigest()
def original(p):
 if p.is_file():return gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes()
 z=Path(str(p)+'.gz');assert z.is_file(),p;return gzip.decompress(z.read_bytes())
def read(p):return json.loads(original(p))
def copied(relative):
 dest=DST/relative;dest.parent.mkdir(parents=True,exist_ok=True)
 with dest.open('xb') as f:f.write(original(SRC/relative))
 return dest
def equal(a,b,label):
 x,y=original(a),original(b);assert x==y,label;stable.append({'path':label,'decoded_bytes':len(x),'sha256':sha(x)})
def run(path,label,cap):
 with (OUT/(label+'.stdout')).open('xb') as so,(OUT/(label+'.stderr')).open('xb') as se:
  p=subprocess.run([sys.executable,'-B',str(path)],stdout=so,stderr=se,timeout=cap)
 assert p.returncode==0,(label,p.returncode)
def summary(a,b,ignored):
 x,y=read(a),read(b);assert set(x)==set(y),(a,'keys')
 for k in x:
  if k not in ignored:assert x[k]==y[k],(a,k)
 assert x['status']=='SUCCESS'

for n in ['check01.py','PROTOCOL01.md','HYPOTHESIS01.md','check02.py','PROTOCOL02.md','PROOF02.md','online_filter.py','check03.py','PROTOCOL03.md']:
 copied('residual_safety_01/'+n)
a=SRC/'residual_safety_01';b=DST/'residual_safety_01'
fixed=read(a/'START01.json')
for n,h in fixed['hashes'].items():assert sha(original(a/n))==h,n
run(b/'check01.py','body493',305)
for n in ['INPUTS01.json','ROOTS01.json','STATES01.jsonl','DISCREPANCIES01.json','CONTROL_COUNTS01.json','STRICT_SF01.json','WITNESS01.json']:
 equal(a/n,b/n,'body/'+n)
summary(a/'SUMMARY01.json',b/'SUMMARY01.json',{'utc','seconds'})
run(b/'check02.py','heap',65)
for n in ['INPUTS.json','EXHAUSTIVE.jsonl.gz','STREAMS.jsonl.gz','DISCREPANCIES.json']:
 equal(a/'check02'/n,b/'check02'/n,'heap/'+n)
summary(a/'check02/SUMMARY.json',b/'check02/SUMMARY.json',{'elapsed_seconds'})

# Recreate the relative module layout without changing any scientific source.
for rel in ['joint_work_general_r_01/unknown02.py','safe_fresh_suffix_01/check01.py']:
 dest=OUT/'replay'/PREVIOUS/rel;dest.parent.mkdir(parents=True,exist_ok=True)
 with dest.open('xb') as f:f.write(original(HERE/'evidence'/PREVIOUS/rel))
run(b/'check03.py','whole16267',95)
for n in ['INPUTS.json','PATHS.jsonl.gz','TREES.jsonl.gz','ROWS.json','DISCREPANCIES.json','DIFFERENCES.json']:
 equal(a/'check03'/n,b/'check03'/n,'whole/'+n)
summary(a/'check03/SUMMARY.json',b/'check03/SUMMARY.json',{'seconds'})

for n in ['check01.py','PROTOCOL01.md','HYPOTHESIS01.md','HYPOTHESIS02_UNIFORM_AND_PAIR.md']:
 copied('charged_residual_01/'+n)
a=SRC/'charged_residual_01/check01';b=DST/'charged_residual_01/check01'
run(b.parent/'check01.py','charged16266',65)
for n in ['INPUTS.json','ROOTS.json','STATES.jsonl.gz','FIXTURES.json','TRACES.json','DISCREPANCIES.json']:
 equal(a/n,b/n,'charged/'+n)
summary(a/'SUMMARY.json',b/'SUMMARY.json',{'seconds'})

# Recompute the explicitly retrospective split, without altering the original population.
counts={k:0 for k in ['physical_states','physical_actions','physical_strict_fresh','surplus_states','surplus_actions','surplus_strict_fresh']}
with (DST/'residual_safety_01/STATES01.jsonl').open() as f:
 for line in f:
  x=json.loads(line);tag='physical' if x['k']<=bin(x['mask']).count('1') else 'surplus'
  counts[tag+'_states']+=1;counts[tag+'_actions']+=2*len(x['actions'])
  counts[tag+'_strict_fresh']+=sum(x['safe'] and q['fresh'] and not q['previous_SF'] for q in x['actions'])
assert counts==read(SRC/'residual_safety_01/PHYSICAL_DOMAIN_REANALYSIS01.json')['counts']

# Safely unpack the author's complete adverse search and call only its scientific functions.
arc=SRC/'whole_curve_obstruction_01.tar.gz';members=read(SRC/'whole_curve_obstruction_01.members.json')['members'];wanted={x['path']:x for x in members}
arch=DST/'whole_curve_obstruction_01';arch.mkdir()
with tarfile.open(arc,'r:gz') as tf:
 seen=set()
 for m in tf.getmembers():
  assert m.isfile() and m.name in wanted and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts,m.name
  assert m.name not in seen;seen.add(m.name);data=tf.extractfile(m).read();row=wanted[m.name]
  assert len(data)==row['public_bytes'] and sha(data)==row['public_sha256'],m.name
  target=arch/m.name;target.parent.mkdir(parents=True,exist_ok=True)
  with target.open('xb') as f:f.write(data)
 assert seen==set(wanted)
spec=importlib.util.spec_from_file_location('fixed_obstruction',arch/'study.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
obstruction=[];deadline=time.monotonic()+90
for tag in ['01','02']:
 cases=read(arch/('INPUTS'+tag+'.json'))['cases'];fixedrows=[json.loads(x) for x in (arch/('run'+tag)/'RESULTS.jsonl').read_text().splitlines()]
 assert len(cases)==len(fixedrows)
 paths=0;front={}
 with (OUT/('obstruction'+tag+'.jsonl')).open('x') as stream:
  for case,old in zip(cases,fixedrows):
   result,packet=mod.solve(case,deadline);checks=mod.interpret(packet,deadline)
   assert old['status']=='SUCCESS' and old['case']==case
   expected=read(arch/('run'+tag)/(case['id']+'.json'));assert json.loads(json.dumps(packet))==expected,case['id']
   assert checks==old['path_checks'],case['id']
   for k,v in result.items():assert old[k]==v,(case['id'],k)
   paths+=sum(x['paths'] for x in checks);front[str(result['front_size'])]=front.get(str(result['front_size']),0)+1
   stream.write(json.dumps({'id':case['id'],'status':'SUCCESS','paths':sum(x['paths'] for x in checks)},separators=(',',':'))+'\n')
 oldsum=read(arch/('run'+tag)/'SUMMARY.json');assert paths==oldsum['interpreted_paths'] and front==oldsum['front_sizes']
 obstruction.append({'fixed_cases':len(cases),'paths':paths,'front_sizes':front})

r={'status':'SUCCESS','stage':STAGE,'seconds':time.monotonic()-START,'body_roots':493,'body_states':158463,'body_actions':303534,'physical_reanalysis':counts,'heap_states':8355,'whole_curve_roots':16267,'whole_curve_paths':1565245,'whole_curve_new_vs_previous_equal':16267,'charged_roots':16266,'charged_physical_uniform_states':379647,'obstruction':obstruction,'stable_decoded_outputs':stable,'new_native_runs':0,'new_timing_samples':0,'new_independent_inputs':0,'independent_reproduction':False,'benchmark_optimality_claim':False}
with(OUT/'SUMMARY.json').open('x') as f:json.dump(r,f,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in r.items() if k!='stable_decoded_outputs'}),flush=True)
