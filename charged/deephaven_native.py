#!/usr/bin/env python3
"""Rebuild the fixed-schema Deephaven studies from the pinned upstream archive.

Deephaven and the modified engine source use the included Deephaven Community
License1.0. This entry point accepts no arbitrary input-table schema.
"""
from pathlib import Path,PurePosixPath
import argparse,datetime,hashlib,importlib.util,json,os,posixpath,shutil,signal,subprocess,sys,tarfile,time,traceback,urllib.request,xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
DATA=HERE/'evidence/RESUMED_20260909_0056'
REV='6367313a319b79437d4d2116c77836ad56d5138d'
ARCHIVE_SHA='b748965bdf42c66092a99b919115592c125ef584832b4e428e236bfc6b30bd1f'
URL='https://codeload.github.com/deephaven/deephaven-core/tar.gz/'+REV
STUDIES={
 'prefix':('deephaven_prefix_import_02','TestRetryPrefixImport','RETRY_PREFIX',216,'retry-prefix-import'),
 'event':('deephaven_event_graph_01','TestRetryEventGraph','RETRY_EVENT_GRAPH',12,'retry-event-import'),
 'phase':('deephaven_phase_policy_01','TestRetryPhasePolicy','RETRY_PHASE',108,None),
 'key':('deephaven_key_action_01','TestRetryKeyAction','RETRY_KEY_ACTION',36,'retry-event-import')}

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):
    with p.open('x') as f:json.dump(x,f,indent=2);f.write('\n')
def load(name,p):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def extract(archive,dest):
    assert sha(archive)==ARCHIVE_SHA,'pinned archive hash differs'
    root='deephaven-core-'+REV
    with tarfile.open(archive,'r:gz') as tar:
        members=tar.getmembers();names={m.name.rstrip('/') for m in members}
        for m in members:
            parts=PurePosixPath(m.name).parts
            assert parts and parts[0]==root and '..' not in parts and not m.name.startswith('/')
            assert m.isdir() or m.isfile() or m.issym(),'unexpected special archive member'
            if m.issym():
                target=posixpath.normpath(posixpath.join(posixpath.dirname(m.name),m.linkname))
                assert target.startswith(root+'/') and target in names,'external or dangling archive link'
        tar.extractall(dest)
    return dest/root
def run_one(key,checkout,output,java,cache,timeout):
    folder,cls,prefix,count,resources=STUDIES[key];source=DATA/folder/'attempt01/sources';output.mkdir()
    base=checkout/'engine/table/src/main/java/io/deephaven/engine/table/impl'
    mapping={'ConstructSnapshot.java':base/'remote/ConstructSnapshot.java','RetryStudyHooks.java':base/'remote/RetryStudyHooks.java','HierarchicalTableImpl.java':base/'hierarchical/HierarchicalTableImpl.java',cls+'.java':checkout/'engine/table/src/test/java/io/deephaven/engine/table/impl'/(cls+'.java')}
    for name,target in mapping.items():
        assert (source/name).is_file();shutil.copy2(source/name,target)
    profiles=[]
    if resources:
        target=checkout/'engine/table/src/test/resources'/resources;target.mkdir(parents=True,exist_ok=True)
        for p in source.glob('profile_*.txt'):
            shutil.copy2(p,target/p.name);profiles.append(dict(name=p.name,sha256=sha(p)))
        assert profiles
    argv=[str(java),'-classpath','gradle/wrapper/gradle-wrapper.jar','org.gradle.wrapper.GradleWrapperMain','--no-daemon','--no-scan','--max-workers=2','--gradle-user-home',str(cache),'-PmaxHeapSize=2g',':engine-table:testOutOfBand','--tests','io.deephaven.engine.table.impl.'+cls]
    start=time.time();save(output/'INPUT.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),revision=REV,argv=argv,cwd=str(checkout),denominator=count,timeout_seconds=timeout,sources=[dict(name=k,sha256=sha(v)) for k,v in mapping.items()],profiles=profiles,reproduction=True,new_evaluation_population=False))
    with (output/'BUILD.log').open('xb') as log:
        p=subprocess.Popen(argv,cwd=checkout,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        save(output/'PROCESS.json',dict(pid=p.pid,pgid=p.pid))
        try:code=p.wait(timeout=timeout);status='SUCCESS' if code==0 else 'FAILURE'
        except subprocess.TimeoutExpired:
            status='TIMEOUT';os.killpg(p.pid,signal.SIGTERM)
            try:code=p.wait(timeout=3)
            except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);code=p.wait()
    result=dict(status=status,returncode=code,seconds=time.time()-start,denominator=count)
    xml=checkout/('engine/table/build/test-results/testOutOfBand/TEST-io.deephaven.engine.table.impl.'+cls+'.xml')
    try:
        if xml.exists() and xml.stat().st_mtime>=start:
            shutil.copy2(xml,output/'TEST.xml');root=ET.parse(xml).getroot()
            result['junit']={k:root.get(k) for k in ['tests','failures','errors','skipped']}
            rows=[json.loads(line[len(prefix)+1:]) for line in (root.findtext('system-out') or '').splitlines() if line.startswith(prefix+' ')]
            with (output/'RAW.jsonl').open('x') as f:
                for row in rows:f.write(json.dumps(row,separators=(',',':'))+'\n')
            result['observed']=len(rows)
            retained=[json.loads(line) for line in (DATA/folder/'attempt01/RAW.jsonl').read_text().splitlines()]
            assert len(rows)==count and len({r['id'] for r in rows})==count and {r['id'] for r in rows}=={r['id'] for r in retained}
            checker=load(key+'_checker',source/'check_trace.py');checks=[checker.check(row) for row in rows]
            if key=='key':
                strict=load('native_key_strict',DATA/'deephaven_key_action_recheck_02/strict.py')
                for row in rows:strict.check(row)
                result['strict_records']=len(rows)
            save(output/'CHECKS.json',checks);result['checked']=len(checks);result['raw_sha256']=sha(output/'RAW.jsonl')
        else:result['fresh_result']=False
    except Exception:
        result.update(status='CHECK_FAILURE',error=traceback.format_exc())
    save(output/'RESULT.json',result)
    assert result['status']=='SUCCESS' and result.get('checked')==count,result
    return result
def main():
    assert __debug__
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('study',choices=['all']+list(STUDIES))
    p.add_argument('--out',type=Path,required=True);p.add_argument('--java',required=True,type=Path)
    p.add_argument('--archive',type=Path);p.add_argument('--gradle-cache',type=Path);p.add_argument('--timeout',type=int,default=900)
    a=p.parse_args();a.out=a.out.resolve();a.java=a.java.resolve();a.out.mkdir(parents=True,exist_ok=False)
    version=subprocess.check_output([str(a.java),'-version'],stderr=subprocess.STDOUT,text=True)
    assert 'version "21.' in version,'the pinned build requires JDK21'
    archive=a.out/'source.tar.gz'
    if a.archive:shutil.copy2(a.archive,archive)
    else:
        with urllib.request.urlopen(URL,timeout=120) as response,archive.open('xb') as f:shutil.copyfileobj(response,f)
    save(a.out/'SOURCE_RECEIPT.json',dict(url=URL,revision=REV,expected_sha256=ARCHIVE_SHA,actual_sha256=sha(archive),java_version=version,driver_sha256=sha(Path(__file__)),license='Deephaven Community License1.0',schema_scope='fixed study fixtures'))
    checkout=extract(archive,a.out/'checkout');cache=a.gradle_cache.resolve() if a.gradle_cache else a.out/'gradle-home'
    results=[]
    for key in STUDIES if a.study=='all' else [a.study]:
        result=run_one(key,checkout,a.out/key,a.java,cache,a.timeout);results.append(dict(study=key,**result));print(json.dumps(dict(study=key,status=result['status'],records=result['checked'])),flush=True)
    save(a.out/'RESULT.json',dict(status='SUCCESS',studies=results,new_evaluation_population=False))

if __name__=='__main__':main()
