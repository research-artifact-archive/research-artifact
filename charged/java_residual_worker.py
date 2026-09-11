"""Reinterpret fixed Java traces using their separately written Python model.
No native executable, new workload population, or timing sample is run here.
"""
from pathlib import Path
import datetime,gzip,hashlib,json,subprocess,sys,time
HERE=Path(__file__).resolve().parent;STAGE=sys.argv[1];OUT=Path(sys.argv[2]);START=time.monotonic()
assert __debug__ and STAGE=='java-residual-filter'
BASE='evidence/RESUMED_20260911_1123/java_residual_filter_01/'
SRC=HERE/BASE;DST=OUT/'fixed';DST.mkdir()
manifest=json.loads((HERE/'PROVENANCE.json').read_text());copied=[]
for row in manifest['files']:
 if not row['path'].startswith(BASE):continue
 data=(HERE/row['path']).read_bytes();assert hashlib.sha256(data).hexdigest()==row['public_sha256'],row['path']
 rel=row['path'][len(BASE):]
 if row.get('storage_encoding')=='gzip':
  data=gzip.decompress(data);assert hashlib.sha256(data).hexdigest()==row['decoded_sha256'];assert rel.endswith('.gz');rel=rel[:-3]
 target=DST/rel;target.parent.mkdir(parents=True,exist_ok=True)
 with target.open('xb') as f:f.write(data)
 copied.append(rel)
assert len(copied)==89
A=OUT/'reinterpreted';A.mkdir()
for n in ['filter.jsonl','native.jsonl','heap.stdout']:
 with(A/n).open('xb') as f:f.write((DST/'attempt02'/n).read_bytes())
for tag,args in [('compare',['compare.py',str(A.resolve())]),('heap',['heap_structure.py','compare',str(A.resolve())])]:
 with(OUT/(tag+'.stdout')).open('xb') as so,(OUT/(tag+'.stderr')).open('xb') as se:
  proc=subprocess.run([sys.executable,'-B',str(DST/args[0])]+args[1:],stdout=so,stderr=se,timeout=80)
 assert proc.returncode==0,(tag,proc.returncode)
for n in ['COMPARISON.json','HEAP_COMPARISON.json']:
 a=json.loads((A/n).read_text());b=json.loads((DST/'attempt02'/n).read_text());assert set(a)==set(b)
 assert a['status']=='SUCCESS'
 for k in a:
  if k!='utc':assert a[k]==b[k],(n,k)
for n in ['filter_reference.jsonl','native_reference.jsonl','PATH_LEDGER.json','ROOT_LEDGER.json','DISCREPANCIES.json','STRICT_WITNESS.json','WORST_W_CURVES.json','HEAP_REFERENCE.json']:
 assert (A/n).read_bytes()==(DST/'attempt02'/n).read_bytes(),n
r={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'SUCCESS','stage':STAGE,'seconds':time.monotonic()-START,'fixed_files_verified':len(copied),'filter_rows':498,'heap_regression_roots':2,'native_roots':48,'native_paths':996,'native_events':31892,'worst_work_equal_coordinates':62,'new_native_invocations':0,'new_timing_samples':0,'new_independent_population':False,'author_reinterpretation':True}
with(OUT/'SUMMARY.json').open('x') as f:json.dump(r,f,indent=2);f.write('\n')
print(json.dumps(r),flush=True)
