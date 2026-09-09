from pathlib import Path
import collections,datetime,hashlib,json,os,signal,subprocess,time
D=Path(__file__).resolve().parent;O=D/'run01';O.mkdir();start=time.monotonic();deadline=start+300
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
apps=json.loads((D/'APPLICATIONS.json').read_text());planned=[x.split('\t') for x in (D/'UNITS.tsv').read_text().splitlines()];assert len(planned)==96
for label in ['baseline','patched']:
    for name,h in apps['files'][label].items():assert sha(Path(apps[label])/name)==h
C=Path('<AUTHOR_HOME>/Research/roslyn_build_20260909');sdk=C/'dotnet';env=dict(os.environ,DOTNET_ROOT=str(sdk),DOTNET_CLI_HOME=str(O/'dotnet_cli'),DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_NOLOGO='1');env['PATH']=str(sdk)+os.pathsep+env.get('PATH','')
write(O/'INPUT_RECEIPT.json',{'utc':utc(),'status':'FIXED_BEFORE_NATIVE_OUTCOMES','planned':96,'files_sha256':{n:sha(D/n) for n in ['PLAN.md','Program.cs','CompilerStudy.csproj','UNITS.tsv','APPLICATIONS.json','check01.py','run01.py']},'applications':apps,'process_cap_seconds':8,'overall_cap_seconds':300,'scope':'New fixed author compiler projections; no timing comparison or new source population'})
results=[]
for unit in planned:
    identity,mode=unit[:2];folder=O/identity;folder.mkdir();app=Path(apps['baseline' if mode=='baseline' else 'patched']);argv=[str(sdk/'dotnet'),str(app/'CompilerStudy.dll'),*unit]
    write(folder/'INTENT.json',{'utc':utc(),'input':unit,'argv':argv});remaining=deadline-time.monotonic()
    if remaining<=0:
        row={'id':identity,'status':'UNSTARTED','reason':'overall cap exhausted','native_status':'MISSING'}
    else:
        t=time.monotonic();cap=min(8,remaining)
        with (folder/'stdout.jsonl').open('x') as stdout,(folder/'stderr.txt').open('x') as stderr:
            proc=subprocess.Popen(argv,stdout=stdout,stderr=stderr,env=env,cwd=app,start_new_session=True);write(folder/'PROCESS.json',{'pid':proc.pid,'pgid':proc.pid,'cap_seconds':cap})
            try:rc=proc.wait(timeout=cap);status='SUCCESS' if rc==0 else 'FAILURE'
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid,signal.SIGTERM)
                try:rc=proc.wait(timeout=2)
                except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);rc=proc.wait()
                status='TIMEOUT'
        try:raw=[json.loads(x) for x in (folder/'stdout.jsonl').read_text().splitlines()];native=raw[0].get('status','INVALID') if len(raw)==1 else 'INVALID'
        except (json.JSONDecodeError,TypeError):raw=[];native='INVALID'
        row={'id':identity,'status':status,'native_status':native,'returncode':rc,'seconds':time.monotonic()-t,'rows':len(raw),'stdout_sha256':sha(folder/'stdout.jsonl'),'stderr_sha256':sha(folder/'stderr.txt')}
    write(folder/'RESULT.json',row);results.append(row);write(O/'PROGRESS.json',{'completed':len(results),'results':results});print(json.dumps(row),flush=True)
summary={'utc':utc(),'planned':96,'process_statuses':dict(collections.Counter(x['status'] for x in results)),'native_statuses':dict(collections.Counter(x['native_status'] for x in results)),'seconds':time.monotonic()-start,'results':results,'no_exclusions':True,'retry':False};write(O/'SUMMARY.json',summary);print(json.dumps({k:v for k,v in summary.items() if k!='results'}),flush=True)
