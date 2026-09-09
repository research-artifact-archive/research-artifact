from pathlib import Path
import datetime,hashlib,json,random,shutil
D=Path(__file__).resolve().parent;old=D.parent/'roslyn_arrivals_01';H=D/'harness01';H.mkdir()
for name in ['Program.cs','ArrivalStudy.csproj']:shutil.copy2(old/'harness01'/name,H/name)
base=[('baseline',0),('three',2),('two',0),('original',0),('three',0),('two',2)];rng=random.Random(9100450);processes=[]
for block in range(6):
 for position,(mode,r) in enumerate(base[block:]+base[:block],1):
  fork=block+1;seq=len(processes)+1;name=f'p{seq:02d}_b{fork}_pos{position}_{mode}_r{r}.tsv';rows=[]
  for phase,reps in [('warmup',2),('measurement',10)]:
   for rep in range(1,reps+1):
    periods=[0,10,100,1000];rng.shuffle(periods)
    for interval in periods:rows.append([f'b{fork}_{mode}_r{r}_{phase}_{rep}_d{interval}',phase,fork,rep,interval,mode,r])
  (H/name).write_text(''.join('\t'.join(map(str,x))+'\n' for x in rows));processes.append({'sequence':seq,'fork':fork,'block':fork,'position':position,'mode':mode,'r':r,'units':48,'input':name,'sha256':hashlib.sha256((H/name).read_bytes()).hexdigest()})
(H/'PROCESS_ORDER.json').write_text(json.dumps({'seed':9100450,'design':'six cyclic Latin-square blocks','processes':processes,'units':1728,'measurement':1440,'warmup':288},indent=2)+'\n')
checker=(old/'check01.py').read_text().replace('864','1728');(D/'check01.py').write_text(checker)
run=(old/'run01.py').read_text();run=run.replace("assert json.loads((D/'build01/RESULT.json').read_text())['status']=='SUCCESS'","assert json.loads((D.parent/'roslyn_arrivals_01/build01/RESULT.json').read_text())['status']=='SUCCESS'")
run=run.replace('864','1728').replace("'measurement':720,'warmup':144","'measurement':1440,'warmup':288")
run=run.replace("'kind':'AUTHOR_EXPLORATION_FIXED_BEFORE_FIRST_EXECUTION'","'kind':'FIXED_PROCESS_ORDER_VALIDATION_AFTER_EXPLORATION'")
(D/'run01.py').write_text(run)
analysis=(old/'analyze01.py').read_text().replace('864','1728').replace('720','1440').replace('144,','288,').replace('==30','==60').replace("'forks':3","'forks':6").replace('for fork in [1,2,3]:','for fork in [1,2,3,4,5,6]:').replace("c['period_us'],30,","c['period_us'],60,")
analysis=analysis.replace('Fixed random shuffle placed all three instrumented-original forks first; process order is a possible thermal/JIT/load confound and was not changed after observation. No rerun or causality claim.','Six fixed cyclic Latin-square blocks place each arm at each position once. This controls position balance, not all machine/runtime effects; no general causality or tail-bound claim.')
(D/'analyze01.py').write_text(analysis)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(D/'PREDECESSOR_RECEIPT.json').write_text(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'predecessor_report_sha256':sha(old/'REPORT_JA.md'),'predecessor_raw_checker_sha256':sha(old/'run01/check01/RECEIPT.json'),'predecessor_analysis_sha256':sha(old/'analysis01/SUMMARY.json'),'unchanged_harness_sha256':sha(H/'Program.cs'),'checker_delta':'Only fixed total864 replaced by1728; function check(row) and corruption controls byte-identical','new_total':1728,'new_processes':36},indent=2)+'\n')
print(json.dumps({'processes':len(processes),'units':sum(x['units'] for x in processes),'harness_sha256':sha(H/'Program.cs')}))
