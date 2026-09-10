#!/usr/bin/env python3
from pathlib import Path
import tarfile,subprocess,time,json,datetime,hashlib,difflib
HERE=Path(__file__).resolve().parent;ROOT=Path('/anonymous-author-home/Research/valkey_build_20260910/refresh01');START=time.monotonic()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,x):(HERE/name).write_text(json.dumps(x,indent=2)+'\n')
rec={'status':'RUNNING','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':['make','-j4','MALLOC=libc','BUILD_TLS=no']};save('BUILD_START.json',rec)
try:
 ROOT.mkdir(parents=True,exist_ok=False)
 archive=HERE.parent/'valkey_manifest_01/valkey-source.tar.gz';rec['archive_sha256']=sha(archive)
 with tarfile.open(archive) as tf:
  for m in tf.getmembers():
   if ROOT not in (ROOT/m.name).resolve().parents or m.issym() or m.islnk():raise ValueError('Unsafe archive member')
  tf.extractall(ROOT)
 source=next(ROOT.glob('valkey-*'));rec['source']=str(source)
 originals=HERE/'source_originals';originals.mkdir();patches=[]
 for name in ['sha1.c','sha1.h','script_lua.c']:
  p=source/'src'/name;old=p.read_text();(originals/name).write_text(old);new=old
  if name=='sha1.c':
   marker='void SHA1Transform(uint32_t state[5], const unsigned char buffer[64])\n{'
   assert old.count(marker)==1
   new=new.replace(marker,'static __thread unsigned long long retry_sha1_count = 0;\nunsigned long long RetrySHA1Count(void) { return retry_sha1_count; }\n\n'+marker+'\n    ++retry_sha1_count;')
  if name=='sha1.h':new=new.replace('void SHA1Transform','unsigned long long RetrySHA1Count(void);\n\nvoid SHA1Transform',1)
  if name=='script_lua.c':
   marker='static int luaRedisSha1hexCommand(lua_State *lua) {'
   assert old.count(marker)==1
   new=new.replace(marker,'static int luaRetrySHA1Count(lua_State *lua) {\n    lua_pushnumber(lua, (lua_Number)RetrySHA1Count());\n    return 1;\n}\n\n'+marker)
   marker='    /* server.sha1hex */'
   assert new.count(marker)==1
   new=new.replace(marker,'    lua_pushstring(lua, "retrysha1blocks");\n    lua_pushcfunction(lua, luaRetrySHA1Count);\n    lua_settable(lua, -3);\n\n'+marker)
  p.write_text(new);patches.append(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/src/'+name,tofile='b/src/'+name)))
 (HERE/'INSTRUMENTATION.patch').write_text(''.join(patches));save('SOURCE_MANIFEST.json',{'archive_sha256':sha(archive),'original':{p.name:sha(p) for p in originals.iterdir()},'instrumented':{name:sha(source/'src'/name) for name in ['sha1.c','sha1.h','script_lua.c']},'patch_sha256':sha(HERE/'INSTRUMENTATION.patch'),'behavior':'one thread-local increment per actual compression invocation; read-only diagnostic accessor; no cost-based branch changes'})
 with (HERE/'BUILD_STDOUT.txt').open('x') as out,(HERE/'BUILD_STDERR.txt').open('x') as err:
  result=subprocess.run(rec['command'],cwd=source,stdout=out,stderr=err,timeout=600)
 rec['server_build_returncode']=result.returncode
 if result.returncode:raise RuntimeError('instrumented server build failed')
 wrapper=HERE/'client_hash.c';wrapper.write_text('#include <stdint.h>\n#include "sha1.h"\nunsigned long long RetryHash(const unsigned char *p, uint32_t n, unsigned char *digest) {\n unsigned long long before=RetrySHA1Count(); SHA1_CTX c; SHA1Init(&c); SHA1Update(&c,p,n); SHA1Final(digest,&c); return RetrySHA1Count()-before;\n}\n')
 lib=ROOT/'client_hash.dylib';cmd=['cc','-O2','-dynamiclib','-I'+str(source/'src'),str(source/'src/sha1.c'),str(wrapper),'-o',str(lib)];rec['client_build_command']=cmd
 result=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=60);(HERE/'CLIENT_BUILD_STDOUT.txt').write_text(result.stdout);(HERE/'CLIENT_BUILD_STDERR.txt').write_text(result.stderr);rec['client_build_returncode']=result.returncode
 if result.returncode:raise RuntimeError('client library build failed')
 binary=source/'src/valkey-server';rec.update(status='SUCCESS',binary=str(binary),binary_sha256=sha(binary),library=str(lib),library_sha256=sha(lib),version=subprocess.check_output([binary,'--version'],text=True,timeout=10).strip())
except Exception as ex:
 rec.update(status='TIMEOUT' if isinstance(ex,subprocess.TimeoutExpired) else 'FAILURE',exception=repr(ex))
rec['seconds']=time.monotonic()-START;save('BUILD_RESULT.json',rec);print(json.dumps(rec));raise SystemExit(0 if rec['status']=='SUCCESS' else 1)
