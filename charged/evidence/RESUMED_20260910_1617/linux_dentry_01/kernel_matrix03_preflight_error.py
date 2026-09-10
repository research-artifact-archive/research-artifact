from pathlib import Path
import subprocess, time, datetime, json, hashlib
D=Path(__file__).resolve().parent
name='fse-dentry-kunit-20360910-2347'
start=time.monotonic()
def h(p): return hashlib.sha256(p.read_bytes()).hexdigest()
argv=['docker','exec','-w','/linuxsrc',name,'python3','-u','tools/testing/kunit/kunit.py','run','--arch=arm64','--cross_compile=','--jobs=2','--timeout=600','--kunitconfig=/work/kunit_dpath.config','--build_dir=/build-kunit','--qemu_args=-smp 2 -m 1034','--json=/work/KUNIT_MATRIX_RESULT03.json']
paths=[D/'INPUTS03.json',D/'PROTOCOL03.md',D/'SOURCE_REFINEMENT01.md',D/'SHARPENED_BODY_BOUND03.md',D/'kunit_dpath.config',Path(__file__).resolve(),D/'patch_source01.py',D/'validate_matrix03.py',D/'validate_matrix02.py']+sorted((D/'implementation03').iterdir())
row=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),argv=argv,wall_cap_seconds=3600,guest_cap_seconds=600,inputs=[dict(path=str(p.relative_to(D)),bytes=p.stat().st_size,sha256=h(p)) for p in paths],planned_valid=1920,planned_controls=4,purpose='third source execution for global writer attribution; unchanged existing population')
with(D/'KERNEL_MATRIX_START03.json').open('x') as f: json.dump(row,f,indent=2);f.write('\n')
install=r'''
from pathlib import Path
import hashlib,shutil,json
d=Path('/work'); source=Path('/linuxsrc')
assert (source/'fs/d_path_retry_test.c').read_bytes()==(d/'implementation02/d_path_retry_test.c').read_bytes(),'predecessor test source mismatch'
for file in ['d_path.c','d_path_retry_hooks.h','d_path_retry_test.c','cached_body.c.inc','d_path_retry_inputs.h']:
    shutil.copyfile(d/'implementation03'/file,source/'fs'/file)
assert 'config D_PATH_KUNIT_TEST' in (source/'lib/Kconfig.debug').read_text()
Path('/build-kunit/test.log').unlink(missing_ok=True)
print(json.dumps({'installed_files':5,'existing_kconfig_preserved':True}))
'''
with(D/'KERNEL_INSTALL03.stdout').open('xb') as out,(D/'KERNEL_INSTALL03.stderr').open('xb') as err:
    p=subprocess.run(['docker','exec',name,'python3','-c',install],stdout=out,stderr=err,timeout=30)
if p.returncode:
    status='INSTALL_FAILURE';code=p.returncode
else:
    with(D/'KERNEL_MATRIX03.stdout').open('xb') as out,(D/'KERNEL_MATRIX03.stderr').open('xb') as err:
        try:
            p=subprocess.run(argv,stdout=out,stderr=err,timeout=3600)
            status='SUCCESS' if p.returncode==0 else 'FAILURE';code=p.returncode
        except subprocess.TimeoutExpired:
            status='TIMEOUT';code=None
            subprocess.run(['docker','stop','--time','2',name],capture_output=True,timeout=20)
for source,outfile in [('/build-kunit/.config','KERNEL_MATRIX03.config'),('/build-kunit/test.log','KERNEL_MATRIX03.test.log')]:
    with(D/outfile).open('xb') as out:
        r=subprocess.run(['docker','exec',name,'cat',source],stdout=out,stderr=subprocess.PIPE,timeout=20)
        if r.returncode:(D/(outfile+'.missing')).write_bytes(r.stderr)
receipt=dict(start_utc=row['utc'],end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status=status,returncode=code,seconds=time.monotonic()-start)
receipt['outputs']=[dict(path=p.name,bytes=p.stat().st_size,sha256=h(p)) for p in sorted(D.glob('KERNEL_MATRIX03.*'))]
with(D/'KERNEL_MATRIX_COMPLETION03.json').open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
print(json.dumps(receipt,indent=2))
raise SystemExit(status!='SUCCESS')
