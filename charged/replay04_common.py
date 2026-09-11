"""Small shared verifier for the two fixed-population replays (Python >=3.10)."""
from pathlib import Path
import datetime, difflib, gzip, hashlib, json, os, signal, subprocess, sys, time
HERE=Path(__file__).resolve().parent
BASE='evidence/RESUMED_20260911_1123/'

def sha(data): return hashlib.sha256(data).hexdigest()
def digest(path): return sha(path.read_bytes())
def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as f: json.dump(value,f,indent=2,sort_keys=True); f.write('\n')
def rows(): return json.loads((HERE/'PROVENANCE.json').read_text())['files']
def unpack(out,names):
    mapping={}
    for row in rows():
        if not any(row['path'].startswith(BASE+n+'/') for n in names): continue
        data=(HERE/row['path']).read_bytes()
        assert sha(data)==row['public_sha256'],row['path']
        rel=row['path'][len(BASE):]
        if row.get('storage_encoding')=='gzip':
            data=gzip.decompress(data)
            assert len(data)==row['decoded_bytes'] and sha(data)==row['decoded_sha256']
            rel=rel[:-3]
        if row.get('native_gzip_decoded_sha256'):
            assert sha(gzip.decompress(data))==row['native_gzip_decoded_sha256']
        target=out/rel; target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as f: f.write(data)
        mapping[rel]=row
    assert mapping
    save(out/'PUBLIC_PROJECTION_MAP.json',mapping)
    return mapping

def check_freeze(root,mapping,directory,name='FREEZE.json'):
    freeze=json.loads((root/directory/name).read_text())
    for rel,meta in freeze['files'].items():
        expected=meta['sha256'] if isinstance(meta,dict) else meta
        row=mapping[directory+'/'+rel]
        assert row['source_sha256']==expected,(directory,rel,'original source binding')
    if directory.startswith('charged_general_filter_check_01/'):
        for rel,expected in freeze.get('sources',{}).items():
            assert mapping['charged_general_01/'+rel]['source_sha256']==expected,('parent source',rel)
        for rel,expected in freeze.get('predecessor_hashes',{}).items():
            assert mapping['charged_general_filter_check_01/attempt01/'+rel]['source_sha256']==expected,('predecessor',rel)
    return freeze

def check_general_history(root,mapping):
    references=0
    for n in [1,2,3]:
        record=json.loads((root/f'charged_dag_boundary_01/run0{n}/START.json').read_text())
        for name,expected in record['sha256'].items():
            rel='charged_dag_boundary_01/'+name if n==3 else name
            assert mapping[rel]['source_sha256']==expected,('historical DAG source',rel)
            references+=1
    for attempt,families in [('attempt01',['initial','policies','named','invalid','streams']),('attempt02',['streams'])]:
        prefix='charged_general_filter_check_01/'+attempt+'/'
        for family in families:
            receipt=json.loads((root/(prefix+family+'_RECEIPT.json')).read_text())
            for name,field in [('FREEZE.json','freeze_sha256'),(family+'_RAW.jsonl','raw_sha256'),(family+'_FAILURES.jsonl','failures_sha256')]:
                assert mapping[prefix+name]['source_sha256']==receipt[field],('historical filter source',prefix+name)
                references+=1
    save(root/'HISTORICAL_BINDINGS_CHECK.json',dict(status='SUCCESS',original_sha256_references_checked=references,meaning='Hashes bind original-source rows; anonymous projected receipt bytes are not claimed to have original hashes.'))

def edit(path,before,after,log):
    text=path.read_text(); assert text.count(before)==1,(path.name,before)
    revised=text.replace(before,after)
    original=log/(path.name+'.before'); original.parent.mkdir(parents=True,exist_ok=True)
    with original.open('x') as f:f.write(text)
    diff=''.join(difflib.unified_diff(text.splitlines(True),revised.splitlines(True),fromfile=path.name+'.public-original',tofile=path.name+'.replay'))
    with (log/(path.name+'.diff')).open('x') as f:f.write(diff)
    path.write_text(revised)
    save(log/(path.name+'.json'),dict(original_sha256=sha(text.encode()),replay_sha256=sha(revised.encode()),reason='fresh-working-copy replay adaptation; historical receipt not altered'))

def run(command,log,timeout=170):
    start=time.monotonic();log.mkdir(parents=True,exist_ok=False)
    save(log/'COMMAND.json',dict(argv=command,timeout_seconds=timeout,replay_only=True))
    with (log/'stdout.txt').open('x') as so,(log/'stderr.txt').open('x') as se:
        proc=subprocess.Popen(command,stdout=so,stderr=se,start_new_session=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
        try:
            code=proc.wait(timeout=timeout); status='SUCCESS' if code==0 else 'FAILURE'
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid,signal.SIGTERM)
            try:code=proc.wait(timeout=2)
            except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);code=proc.wait()
            status='TIMEOUT'
        except BaseException:
            if proc.poll() is None:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
            raise
    row=dict(status=status,returncode=code,seconds=time.monotonic()-start,argv=command)
    save(log/'RESULT.json',row)
    assert status=='SUCCESS',row
    return row

def arm(seconds=175):
    assert __debug__,'Assertions must be enabled.'
    def expired(*args):raise TimeoutError('bounded public replay deadline')
    signal.signal(signal.SIGTERM,expired)
    signal.signal(signal.SIGALRM,expired);signal.alarm(seconds)
