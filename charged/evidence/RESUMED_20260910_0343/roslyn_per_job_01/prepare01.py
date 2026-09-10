from pathlib import Path
import datetime,hashlib,json,random,shutil
D=Path(__file__).resolve().parent;old=D.parent/'roslyn_arrivals_01';H=D/'harness01';H.mkdir()
def replace(s,a,b):
 assert s.count(a)==1,(a[:120],s.count(a));return s.replace(a,b)
s=(old/'harness01/Program.cs').read_text();original=s
s=replace(s,'u.Mode=="original"?-1:u.Mode=="two"?0:1','u.Mode=="original"?-1:u.Mode.EndsWith("two",StringComparison.Ordinal)?0:1')
s=replace(s,'var fgInvoked=new long[32];var fgReturned=new long[32];','var fgInvoked=new long[32];var fgReturned=new long[32];\n  bool perJob=u.Mode.StartsWith("per-job-",StringComparison.Ordinal);var jobCounters=new List<Dictionary<string,long>>();\n  string[] counterNames={"Calls","PreparedOutside","PreparedInside","Mismatches","CheapFailures"};')
s=replace(s,'for(int i=0;i<32;i++){fgInvoked[i]=Stopwatch.GetTimestamp();ws.Change(targetIds[0],ForegroundTexts[i+1]);fgReturned[i]=Stopwatch.GetTimestamp();}',
'''for(int i=0;i<32;i++)
   {
    if(state is not null&&perJob)Set(state,"Remaining",u.R);
    var before=state is null?null:counterNames.ToDictionary(n=>n,n=>(long)Field(state,n)!);
    int remainingBefore=state is null?-1:(int)Field(state,"Remaining")!;
    fgInvoked[i]=Stopwatch.GetTimestamp();ws.Change(targetIds[0],ForegroundTexts[i+1]);fgReturned[i]=Stopwatch.GetTimestamp();
    if(state is not null)
    {
     var delta=counterNames.ToDictionary(n=>n,n=>(long)Field(state,n)!-before![n]);
     delta["index"]=i+1;delta["remaining_before"]=remainingBefore;delta["remaining_after"]=(int)Field(state,"Remaining")!;
     if(delta["Calls"]!=1+delta["CheapFailures"])throw new Exception("per-update call accounting");
     if(perJob&&(delta["CheapFailures"]>u.R||delta["remaining_before"]!=u.R||delta["remaining_after"]!=u.R-delta["CheapFailures"]))throw new Exception("per-update retry scope");
     jobCounters.Add(delta);
    }
   }''')
s=replace(s,'if(u.Mode!="original"&&counters["Calls"]>32+u.R)throw new Exception("call guarantee");','if(u.Mode!="original"&&counters["Calls"]>32+(perJob?32*u.R:u.R))throw new Exception("call guarantee");')
s=replace(s,'result["counters"]=counters;','result["job_counters"]=jobCounters;result["retry_scope"]=perJob?"per-job":u.Mode is "two" or "three"?"shared":"unbounded";\n   result["counters"]=counters;')
(H/'Program.cs').write_text(s)
base=[('baseline',0),('two',2),('per-job-three',1),('original',0),('per-job-two',2),('three',2),('per-job-two',1),('per-job-three',2)];rng=random.Random(9101112);processes=[]
for block in range(8):
 for position,(mode,r) in enumerate(base[block:]+base[:block],1):
  fork=block+1;seq=len(processes)+1;name=f'p{seq:02d}_b{fork}_pos{position}_{mode}_r{r}.tsv';rows=[]
  for phase,reps in [('warmup',2),('measurement',10)]:
   for rep in range(1,reps+1):
    periods=[0,10,100,1000];rng.shuffle(periods)
    for interval in periods:rows.append([f'b{fork}_{mode}_r{r}_{phase}_{rep}_d{interval}',phase,fork,rep,interval,mode,r])
  (H/name).write_text(''.join('\t'.join(map(str,x))+'\n' for x in rows));processes.append(dict(sequence=seq,fork=fork,block=fork,position=position,mode=mode,r=r,units=48,input=name))
(H/'PROCESS_ORDER.json').write_text(json.dumps(dict(seed=9101112,design='eight cyclic Latin-square blocks',processes=processes,units=3072,measurement=2560,warmup=512),indent=2)+'\n')
basecheck=(old/'check01.py').read_text();s=replace(basecheck,'def check(row):','def check(row,resources=True):');s=replace(s,"if row['mode']!='baseline':","if resources and row['mode']!='baseline':")
(D/'semantic_base_check.py').write_text(s)
build=(old/'build01.py').read_text().replace("H=S/'arrivals_harness01'","H=S/'per_job_harness01'").replace("baseline=S/'arrivals_baseline01'","baseline=S/'per_job_baseline01'")
(D/'build01.py').write_text(build)
run=(old/'run01.py').read_text().replace("app=S/'arrivals_harness01/bin/Release/net10.0';baseline=S/'arrivals_baseline01'","app=S/'per_job_harness01/bin/Release/net10.0';baseline=S/'per_job_baseline01'")
run=run.replace('864','3072').replace("'measurement':720,'warmup':144","'measurement':2560,'warmup':512").replace('2700','1200')
run=replace(run,"'kind':'AUTHOR_EXPLORATION_FIXED_BEFORE_FIRST_EXECUTION'","'kind':'FIXED_SHARED_VERSUS_PER_JOB_COMPARISON'")
run=replace(run,"D/'check01.py',D/'harness01/Program.cs'","D/'check01.py',D/'semantic_base_check.py',D/'analyze01.py',D/'harness01/Program.cs'")
run=replace(run,"O=D/'run01';O.mkdir()","assert json.loads((D.parent/'PUBLICATION_06/PUBLIC_REPLAY_COMPLETION01.json').read_text())['status']=='SUCCESS', 'Complete earlier public replay before timed native campaign'\nO=D/'run01';O.mkdir()")
(D/'run01.py').write_text(run)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(D/'PREPARE_RECEIPT.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),prior_program_sha256=hashlib.sha256(original.encode()).hexdigest(),program_sha256=sha(H/'Program.cs'),semantic_checker_delta='only optional resources flag; unchanged semantic comparisons',source_library='existing patch04 exact libraries, unchanged',new_arms=4,planned_processes=64,planned_units=3072),indent=2)+'\n')
print('prepared64processes3072units')
