#!/usr/bin/env python3
"""Optional fresh Linux/QEMU reproduction; operates only in its own container."""
from pathlib import Path
import argparse,datetime,hashlib,json,os,shutil,subprocess,sys,time,uuid
HERE=Path(__file__).resolve().parent
SOURCE=HERE/'evidence/RESUMED_20260910_1617/linux_dentry_01'
COMMIT='adc218676eef25575469234709c2d87185ca223a'
ARCHIVE_SHA='8787cc90ca7740ab7c955b6fad83010dc600f14a6d94511b548703e4f0f40caa'
IMAGE='ubuntu:24.04@sha256:224a1869083a311ef3f13648a154ba79832fbef6364d31493642ca03082da254'
INSTALL=r'''
from pathlib import Path
import hashlib,json,shutil
d=Path('/work/native');src=Path('/linuxsrc')
m=json.loads((d/'SOURCE_MANIFEST01.json').read_text())
for row in m['rows']:
 p=src/row['path']
 assert p.stat().st_size==row['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'],row['path']
for name in ['d_path.c','d_path_retry_hooks.h','d_path_retry_test.c','cached_body.c.inc','d_path_retry_inputs.h']:
 shutil.copyfile(d/'implementation03'/name,src/'fs'/name)
f=src/'lib/Kconfig.debug';s=f.read_text();assert 'config D_PATH_KUNIT_TEST' not in s
f.write_text(s+(d/'implementation03/Kconfig.append').read_text())
print(json.dumps(dict(upstream_files_verified=len(m['rows']),installed_source_files=5,kconfig_appended=True)))
'''
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def save(p,v):
    with p.open('x') as f:json.dump(v,f,indent=2);f.write('\n')
def main():
    assert __debug__,'Do not use python -O'
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--archive',type=Path,help='Optional existing exact archive; still hash-checked')
    ap.add_argument('--timeout',type=int,default=3600)
    a=ap.parse_args();assert 60<=a.timeout<=7200
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    assert ',' not in str(out),'Docker bind source must not contain a comma'
    begin=time.monotonic();deadline=begin+a.timeout
    name='dpath-artifact-'+uuid.uuid4().hex[:16]
    steps=[];created=False;status='FAILURE';error=None;code=1
    def run(label,argv,cap,allow_failure=False):
        t=time.monotonic();remaining=max(1,min(cap,int(deadline-t)))
        print(label,flush=True)
        with(out/(label+'.stdout')).open('xb') as stdout,(out/(label+'.stderr')).open('xb') as stderr:
            p=subprocess.run(argv,stdout=stdout,stderr=stderr,timeout=remaining)
        row=dict(step=label,argv=argv,returncode=p.returncode,seconds=time.monotonic()-t)
        steps.append(row)
        if p.returncode and not allow_failure:raise RuntimeError(label+' failed; see saved stderr')
        return p.returncode
    save(out/'START.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='fresh reproduction of existing1924-row population; no new timing study',source_commit=COMMIT,source_archive_sha256=ARCHIVE_SHA,image=IMAGE,container=name,total_cap_seconds=a.timeout,source_driver_sha256=digest(Path(__file__)),host_python=sys.version))
    try:
        # Verify exactly the files used by this optional native reproduction.
        manifest=json.loads((HERE/'PROVENANCE.json').read_text())
        rows={x['path']:x for x in manifest['files']}
        native=out/'native';native.mkdir()
        names=['INPUTS02.json','INPUTS03.json','SOURCE_MANIFEST01.json','kunit_dpath.config','validate_matrix02.py','validate_matrix03b.py','MATRIX_JOINED02.json']
        names += [str(p.relative_to(SOURCE)) for p in sorted((SOURCE/'implementation03').iterdir()) if p.is_file()]
        for rel in names:
            src=SOURCE/rel;key=str(src.relative_to(HERE));row=rows[key]
            assert src.stat().st_size==row['public_bytes'] and digest(src)==row['public_sha256'],key
            dest=native/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
        assert (native/'INPUTS02.json').read_bytes()==(native/'INPUTS03.json').read_bytes()
        archive=out/'linux-v6.12.tar.gz'
        if a.archive:shutil.copyfile(a.archive.resolve(),archive)
        else:run('download',['curl','--fail','--location','--max-time','240','--output',str(archive),'https://codeload.github.com/torvalds/linux/tar.gz/'+COMMIT],245)
        assert digest(archive)==ARCHIVE_SHA,'Linux archive hash mismatch'
        run('docker_version',['docker','version'],30)
        run('image',['docker','pull','--platform','linux/arm64',IMAGE],300)
        run('create',['docker','create','--name',name,'--platform','linux/arm64','--memory','4g','--cpus','2','--pids-limit','512','--security-opt','no-new-privileges','--mount','type=bind,source='+str(out)+',target=/work',IMAGE,'sleep',str(a.timeout)],30)
        created=True
        run('start',['docker','start',name],30)
        run('apt_update',['docker','exec',name,'apt-get','update'],240)
        run('apt_install',['docker','exec','-e','DEBIAN_FRONTEND=noninteractive',name,'apt-get','install','-y','--no-install-recommends','build-essential','bison','flex','bc','libelf-dev','libssl-dev','python3','git','rsync','kmod','ca-certificates','xz-utils','cpio','qemu-system-arm'],600)
        run('packages',['docker','exec',name,'dpkg-query','-W'],30)
        run('directories',['docker','exec',name,'mkdir','/linuxsrc','/build-kunit'],30)
        run('extract',['docker','exec',name,'tar','-xzf','/work/linux-v6.12.tar.gz','--strip-components=1','-C','/linuxsrc'],180)
        run('install',['docker','exec',name,'python3','-c',INSTALL],30)
        argv=['docker','exec','-w','/linuxsrc',name,'python3','-u','tools/testing/kunit/kunit.py','run','--arch=arm64','--cross_compile=','--jobs=2','--timeout=600','--kunitconfig=/work/native/kunit_dpath.config','--build_dir=/build-kunit','--qemu_args=-smp 2 -m 1024','--json=/work/native/KUNIT_MATRIX_RESULT03B.json']
        native_code=run('kernel',argv,3000,True)
        # Copy all available raw outputs even if the guest reports a failure.
        for src,dest in [('/build-kunit/.config','KERNEL_MATRIX03B.config'),('/build-kunit/test.log','KERNEL_MATRIX03B.test.log')]:
            with(native/dest).open('xb') as stdout,(native/(dest+'.stderr')).open('xb') as stderr:
                cp=subprocess.run(['docker','exec',name,'cat',src],stdout=stdout,stderr=stderr,timeout=20)
            steps.append(dict(step='capture_'+dest,returncode=cp.returncode))
        validation_code=run('reconstruct',[sys.executable,'-B',str(native/'validate_matrix03b.py')],180,True)
        if native_code or validation_code:raise RuntimeError('kernel or reconstruction failed; all raw outputs retained')
        validation=json.loads((native/'MATRIX_VALIDATION03B.json').read_text())
        assert validation['status']=='PASS' and validation['planned']==validation['global_records']==validation['reconstructed_rows']==1924
        status='SUCCESS';code=0
    except BaseException as exc:
        error=repr(exc)
        if isinstance(exc,subprocess.TimeoutExpired):status='TIMEOUT'
    finally:
        cleanup=[]
        if created:
            for action in [['docker','stop','--time','2',name],['docker','rm',name]]:
                try:
                    cp=subprocess.run(action,capture_output=True,text=True,timeout=30)
                    cleanup.append(dict(argv=action,returncode=cp.returncode,stdout=cp.stdout,stderr=cp.stderr))
                except Exception as exc:cleanup.append(dict(argv=action,error=repr(exc)))
            if any(x.get('returncode')!=0 for x in cleanup):
                status='CLEANUP_FAILURE';code=1
        save(out/'RESULT.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status=status,error=error,seconds=time.monotonic()-begin,steps=steps,cleanup=cleanup,existing_population=True,new_timing_samples=0,scope='Author-triggered source reproduction, not independent certification or a new sample population'))
    print(json.dumps(dict(status=status,error=error,seconds=time.monotonic()-begin)),flush=True)
    return code
if __name__=='__main__':raise SystemExit(main())
