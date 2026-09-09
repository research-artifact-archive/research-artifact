"""Fixed suffix-certificate equations and semantic traces; no new timing measurements."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,time,os
HERE=Path(__file__).resolve().parent;OUT=Path(sys.argv[2]);BASE=HERE/'evidence/RESUMED_20260909_1413';D=BASE/'protected_suffix_02'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def run(argv,cap):
 r=subprocess.run(argv,capture_output=True,text=True,timeout=cap)
 assert r.returncode==0,(argv,r.stdout[-1500:],r.stderr[-1500:]);return r
native=sys.argv[1]=='protected-suffix-java';started=time.monotonic();freshroot=OUT/'fresh';fresh=freshroot/'protected_suffix_02';fresh.mkdir(parents=True);prior=freshroot/'protected_tail_01';prior.mkdir();shutil.copyfile(BASE/'protected_tail_01/study.py',prior/'study.py')
for name in ['study.py','INPUTS.json','check_native.py','NATIVE_INPUTS.json']:shutil.copyfile(D/name,fresh/name)
if not native:
 run([sys.executable,'-B',str(fresh/'study.py')],240);a,b=read(fresh/'SUMMARY.json'),read(D/'SUMMARY.json')
 assert a['status']=='SUCCESS' and a['roots']==209408 and a['cases']==6544 and a['counts']==b['counts'] and a['comparisons']==b['comparisons']
 assert sha(fresh/'RESULTS.jsonl')==sha(D/'RESULTS.jsonl')
 f=fresh/'feasibility_oracle01';f.mkdir()
 for name in ['study.py','INPUTS.json']:shutil.copyfile(D/'feasibility_oracle01'/name,f/name)
 run([sys.executable,'-B',str(f/'study.py')],180);a,b=read(f/'SUMMARY.json'),read(D/'feasibility_oracle01/SUMMARY.json')
 assert a['status']=='SUCCESS' and a['states']==665500 and a['comparisons']==1331000 and a['feasible']==b['feasible']
 assert sha(f/'RESULTS.jsonl')==sha(D/'feasibility_oracle01/RESULTS.jsonl');raw=D/'native01/native/stdout.txt'
else:
 classes=OUT/'classes';classes.mkdir();run([os.environ.get('JAVAC_BIN','javac'),'--release','17','-d',str(classes),str(D/'SuffixProbe.java')],60)
 r=run([os.environ.get('JAVA_BIN','java'),'-cp',str(classes),'SuffixProbe',str(D/'NATIVE_RUNS.tsv')],180);raw=OUT/'native.jsonl';raw.write_text(r.stdout)
 assert sha(raw)==sha(D/'native01/native/stdout.txt')
run([sys.executable,'-B',str(fresh/'check_native.py'),'--raw',str(raw),'--out',str(OUT/'native-check')],90)
c=read(OUT/'native-check/CHECK_RECEIPT.json');assert c['status']=='PASS' and c['expected_units']==20594 and c['observed_units']==20594 and c['groups']==384 and len(c['controls'])==8
assert sha(OUT/'native-check/MAXIMA.json')==sha(D/'native01/check01/MAXIMA.json')
s=dict(status='SUCCESS',stage=sys.argv[1],seconds=time.monotonic()-started,policy_roots=0 if native else 209408,feasibility_states=0 if native else 665500,native_paths=20594,groups=384,controls=8,relative_to_alltail={'better':1,'worse':3,'tie':209404},replay_only=True,new_evaluation_samples=0,general_W_optimality=False,scope='New native executions of fixed paths; byte-identical raw' if native else 'Exact original policy/feasibility equations and all saved native paths')
(OUT/'SUMMARY.json').write_text(json.dumps(s,indent=2)+'\n');print(json.dumps(s),flush=True)
