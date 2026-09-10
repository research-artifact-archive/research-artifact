from pathlib import Path
import subprocess,sys,shutil,json,re,hashlib,datetime
D=Path(__file__).resolve().parent
out=D/'reconstruction03';out.mkdir()
for name in ['INPUTS02.json','validate_matrix02.py']:shutil.copy2(D/name,out/name)
shutil.copy2(D/'KERNEL_MATRIX03.test.log',out/'KERNEL_MATRIX02.test.log')
with(D/'RECONSTRUCTION03.stdout').open('xb') as stdout,(D/'RECONSTRUCTION03.stderr').open('xb') as stderr:
    p=subprocess.run([sys.executable,'-B',str(out/'validate_matrix02.py')],stdout=stdout,stderr=stderr,timeout=180)
errors=[]
def check(ok,kind,**detail):
    if not ok:errors.append(dict(kind=kind,**detail))
check(p.returncode==0,'original_obligation_reconstruction',returncode=p.returncode)
raw=(D/'KERNEL_MATRIX03.test.log').read_text();records=[]
for line_number,line in enumerate(raw.splitlines(),1):
    m=re.search(r'\bDPGLOBAL (\{.*)$',line)
    if m:
        try:records.append(json.loads(m.group(1)))
        except Exception as e:errors.append(dict(kind='parse',line=line_number,error=repr(e)))
lookup={x['id']:x for x in records}
check(len(records)==len(lookup)==1924 and set(lookup)==set(range(1924)),'denominator',count=len(records),unique=len(lookup),missing=sorted(set(range(1924))-set(lookup)))
current=json.loads((out/'MATRIX_JOINED02.json').read_text()) if (out/'MATRIX_JOINED02.json').exists() else []
prior=json.loads((D/'MATRIX_JOINED02.json').read_text());old={x['input']['id']:x for x in prior}
for j in current:
    i=j['input']['id'];g=lookup.get(i)
    if not g:continue
    valid=g['begin']%2==g['end']%2==0 and g['end']>=g['begin'] and (g['end']-g['begin'])//2==g['global_writes']==g['designated_writes']==j['row']['B']
    check(valid and g['valid']==1,'global_attribution',id=i,record=g)
    check(j==old.get(i),'predecessor_event_equality',id=i)
result=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='PASS' if not errors else 'FAIL',planned=1924,global_records=len(records),reconstructed_rows=len(current),valid_rows=sum(not x['input']['control'] for x in current),controls=sum(x['input']['control'] for x in current),all_samples_even_nonwrapping=all(g['begin']%2==g['end']%2==0 and g['end']>=g['begin'] for g in records),total_global_sections=sum(g['global_writes'] for g in records),total_designated_sections=sum(g['designated_writes'] for g in records),extra_global_writer_rows=sum(g['global_writes']!=g['designated_writes'] for g in records),raw_sha256=hashlib.sha256((D/'KERNEL_MATRIX03.test.log').read_bytes()).hexdigest(),reconstructed_joined_sha256=hashlib.sha256((out/'MATRIX_JOINED02.json').read_bytes()).hexdigest() if (out/'MATRIX_JOINED02.json').exists() else None,prior_joined_sha256=hashlib.sha256((D/'MATRIX_JOINED02.json').read_bytes()).hexdigest(),errors=errors,scope='Bracketing global rename_lock writer count and unchanged source-event comparison. Same population; no new time/performance or whole-filesystem claim.')
with(D/'MATRIX_GLOBAL03.json').open('x') as f:json.dump(records,f,indent=2);f.write('\n')
with(D/'MATRIX_VALIDATION03.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(result,indent=2));raise SystemExit(bool(errors))
