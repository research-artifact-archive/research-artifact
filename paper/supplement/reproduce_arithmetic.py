"""Replay nine saved algebraic examples in a fresh directory; not a policy oracle."""
from pathlib import Path
import argparse,datetime,hashlib,json,shutil,subprocess,sys,time
p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args()
src=Path(__file__).resolve().parent;dest=Path(a.out).resolve();dest.mkdir(parents=True,exist_ok=False)
start=time.monotonic()
for n in ['check_arithmetic.py','ARITHMETIC_INPUT.json']:shutil.copy2(src/n,dest/n)
with(dest/'stdout.txt').open('x')as out,(dest/'stderr.txt').open('x')as err:
 result=subprocess.run([sys.executable,'-I','-S','-B',str(dest/'check_arithmetic.py')],stdout=out,stderr=err,timeout=30)
ok=result.returncode==0
if ok:
 expected=json.loads((src/'ARITHMETIC_OUTPUT.json').read_text());observed=json.loads((dest/'ARITHMETIC_OUTPUT.json').read_text())
 expected.pop('completed_utc');observed.pop('completed_utc');ok=observed==expected
receipt={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'SUCCESS'if ok else'FAILURE','returncode':result.returncode,'elapsed_seconds':time.monotonic()-start,'comparison':'Every JSON field exactly equal except completed_utc','input_sha256':hashlib.sha256((src/'ARITHMETIC_INPUT.json').read_bytes()).hexdigest(),'original_checker_sha256':hashlib.sha256((src/'check_arithmetic.py').read_bytes()).hexdigest(),'case_count':9,'new_semantic_or_native_samples':0}
(dest/'REPLAY.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2));raise SystemExit(not ok)
