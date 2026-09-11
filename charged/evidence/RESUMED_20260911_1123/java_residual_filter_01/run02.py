from pathlib import Path
import datetime,hashlib,json,subprocess,sys,os,signal,time
P=Path(__file__).resolve().parent
A=P/'attempt02';A.mkdir()
J=Path('/opt/homebrew/Cellar/openjdk@17/17.0.19/libexec/openjdk.jdk/Contents/Home')
D=P.parent
sources=[P/x for x in ['PROTOCOL.md','ResidualFilter.java','Json.java','FilterDriver.java','NativeIntegration.java','reference.py','generate_inputs.py','compare.py','run02.py','REVISION02.md','heap_structure.py','HEAP_STRUCTURE_INPUTS.json','HEAP_STRUCTURE_INPUTS.tsv','v2/ResidualFilter.java','FILTER_INPUTS.json','FILTER_INPUTS.tsv','NATIVE_ROOTS.json','NATIVE_INPUTS.json','NATIVE_INPUTS.tsv','INPUT_RECEIPT.json']]
sources += [D/'residual_safety_01/PROOF02.md',D/'residual_safety_01/online_filter.py',D/'charged_residual_01/PROOF03.md',D.parent/'RESUMED_20260910_1617/universal_independent_native_01/UniversalCallbacks.java',J/'lib/src.zip',J/'bin/java',J/'bin/javac']
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
freeze=dict(utc=now(),status='FROZEN_BEFORE_COMPILATION_AND_JAVA_EXECUTION',files=[dict(path=str(x),sha256=sha(x),bytes=x.stat().st_size) for x in sources])
(A/'FREEZE.json').write_text(json.dumps(freeze,indent=2)+'\n')
(A/'classes').mkdir()
records=[]
absolute_deadline=datetime.datetime(2026,9,11,3,53,tzinfo=datetime.timezone.utc)
started=time.monotonic()
def execute(label,cmd,max_s):
    left=(absolute_deadline-datetime.datetime.now(datetime.timezone.utc)).total_seconds()
    timeout=min(max_s,360-(time.monotonic()-started),left)
    record=dict(label=label,command=cmd,started_utc=now(),max_seconds=max_s)
    if timeout<=0:
        record.update(status='NOT_EXECUTED',reason='supervisor deadline');records.append(record);return False
    with (A/(label+'.jsonl' if label in ['filter','native'] else label+'.stdout')).open('x') as out,(A/(label+'.stderr')).open('x') as err:
        proc=subprocess.Popen(cmd,cwd=P,stdout=out,stderr=err,start_new_session=True)
        record['pid']=proc.pid
        try:
            code=proc.wait(timeout=timeout);record.update(status='SUCCESS' if code==0 else 'FAILURE',returncode=code)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid,signal.SIGKILL);proc.wait();record.update(status='TIMEOUT',returncode=proc.returncode)
    record['finished_utc']=now();record['owned_child_reaped']=True;records.append(record)
    (A/(label+'_RECEIPT.json')).write_text(json.dumps(record,indent=2)+'\n')
    return record['status']=='SUCCESS'
execute('java_version',[str(J/'bin/java'),'-version'],10)
compiled=execute('compile',[str(J/'bin/javac'),'--release','17','-Xlint:all','-d',str(A/'classes')]+[str(P/x) for x in ['v2/ResidualFilter.java','Json.java','FilterDriver.java','NativeIntegration.java']],30)
if compiled:
    execute('filter',[str(J/'bin/java'),'-cp',str(A/'classes'),'FilterDriver',str(P/'FILTER_INPUTS.tsv')],60)
    execute('native',[str(J/'bin/java'),'-cp',str(A/'classes'),'NativeIntegration',str(P/'NATIVE_INPUTS.tsv')],120)
execute('comparison',[sys.executable,'-B',str(P/'compare.py'),str(A)],120)
if compiled:
    execute('heap',[str(J/'bin/java'),'-cp',str(A/'classes'),'FilterDriver',str(P/'HEAP_STRUCTURE_INPUTS.tsv')],60)
    execute('heap_comparison',[sys.executable,'-B',str(P/'heap_structure.py'),'compare',str(A)],60)
receipt=dict(finished_utc=now(),status='SUCCESS' if all(r['status']=='SUCCESS' for r in records) else 'FAILURE',processes=records,owned_live_children=0,freeze_sha256=sha(A/'FREEZE.json'))
(A/'RUN_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
