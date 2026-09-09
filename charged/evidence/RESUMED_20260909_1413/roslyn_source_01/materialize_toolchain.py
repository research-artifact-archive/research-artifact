from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import urllib.request,json,hashlib,tarfile,datetime,time
D=Path(__file__).resolve().parent;selection=json.loads((D/'SDK_SELECTION.json').read_text());sdk=selection['sdk_exact_matches'][0];commit=json.loads((D/'RELEASE_SOURCE_SELECTION.json').read_text())['repository']['commit'];jobs=[('sdk',sdk['url'],D/'sdk.tar.gz'),('source',f'https://codeload.github.com/dotnet/roslyn/tar.gz/{commit}',D/'roslyn.tar.gz')]
plan={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'phase':'DEPENDENCY_PREPARATION','jobs':[{'kind':k,'url':u,'output':str(p)} for k,u,p in jobs],'sdk_sha512':sdk['hash'],'source_commit':commit,'system_install':False,'new_scientific_outcomes':0,'max_download_seconds':300}
with (D/'TOOLCHAIN_MATERIALIZATION_PLAN.json').open('x') as f:json.dump(plan,f,indent=2);f.write('\n')
def fetch(job):
 k,u,p=job;started=time.monotonic();r={'kind':k,'url':u}
 try:
  with urllib.request.urlopen(u,timeout=45) as src,p.open('xb') as out:
   while True:
    b=src.read(1<<20)
    if not b:break
    out.write(b)
    if time.monotonic()-started>300:raise TimeoutError('download cap300s')
  raw=p.read_bytes();r.update({'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'sha512':hashlib.sha512(raw).hexdigest()})
  if k=='sdk':assert r['sha512']==sdk['hash'],'official SDK digest mismatch'
  dest=D/('dotnet' if k=='sdk' else 'source');dest.mkdir()
  with tarfile.open(p,'r:gz') as t:
   for m in t.getmembers():
    target=(dest/m.name).resolve()
    if not target.is_relative_to(dest.resolve()):raise ValueError('unsafe tar path')
    if m.isdev():raise ValueError('device entry')
    if m.issym() or m.islnk():
     targetlink=(target.parent/m.linkname).resolve() if m.issym() else (dest/m.linkname).resolve()
     if not targetlink.is_relative_to(dest.resolve()):raise ValueError('unsafe tar link')
   t.extractall(dest)
  r.update({'status':'SUCCESS','destination':str(dest)})
 except Exception as e:r.update({'status':'FAILURE','error':repr(e)})
 r['seconds']=time.monotonic()-started;return r
with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(fetch,jobs))
with (D/'TOOLCHAIN_MATERIALIZATION_RESULT.json').open('x') as f:json.dump({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'results':results,'execution_performed':False},f,indent=2);f.write('\n')
print(json.dumps(results))
