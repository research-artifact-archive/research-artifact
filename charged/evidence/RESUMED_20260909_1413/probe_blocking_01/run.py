from pathlib import Path
import datetime,hashlib,itertools,json,os,platform,signal,subprocess,time

D=Path(__file__).resolve().parent
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def child(argv,label,timeout):
    out=D/label;out.mkdir();start=time.monotonic()
    write(out/'INTENT.json',{'utc':utc(),'argv':argv,'cwd':str(D),'timeout_seconds':timeout})
    with (out/'stdout.jsonl').open('x') as stdout,(out/'stderr.txt').open('x') as stderr:
        p=subprocess.Popen(argv,cwd=D,stdout=stdout,stderr=stderr,start_new_session=True)
        write(out/'PROCESS.json',{'pid':p.pid,'pgid':p.pid,'argv':argv})
        try:rc=p.wait(timeout=timeout);status='SUCCESS' if rc==0 else 'FAILURE'
        except subprocess.TimeoutExpired:
            os.killpg(p.pid,signal.SIGTERM)
            try:rc=p.wait(timeout=3)
            except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);rc=p.wait()
            status='TIMEOUT'
    receipt={'utc':utc(),'status':status,'returncode':rc,'seconds':time.monotonic()-start,'stdout_sha256':sha(out/'stdout.jsonl'),'stderr_sha256':sha(out/'stderr.txt')}
    write(out/'RESULT.json',receipt);print(label,json.dumps(receipt),flush=True)
    return receipt

def main():
    write(D/'INPUT_RECEIPT.json',{'utc':utc(),'kind':'FIXED_BEFORE_FIRST_TIMING_EXECUTION','files':{x:sha(D/x) for x in ['PLAN.md','ProbeBlocking.java','run.py']},'platform':platform.platform(),'machine':platform.machine(),'python':platform.python_version(),'measurement_units':4320,'measurement_pairs':2160,'measurement_probes':17280,'warmup_units':1440,'no_retries':True,'process_cap_seconds':360})
    compile_result=child(['javac','-d','classes','ProbeBlocking.java'],'compile',60)
    if compile_result['status']!='SUCCESS':return
    write(D/'CLASSES.json',{str(p.relative_to(D)):sha(p) for p in sorted((D/'classes').glob('*.class'))})
    java=['java','-Xms512m','-Xmx512m','-XX:+AlwaysPreTouch','-cp','classes','ProbeBlocking']
    smoke=child(java+['0','0','1'],'smoke',60)
    rows=[json.loads(x) for x in (D/'smoke/stdout.jsonl').read_text().splitlines()]
    smoke_pass=smoke['status']=='SUCCESS' and len(rows)==48 and all(x['status']=='SUCCESS' for x in rows)
    write(D/'SMOKE_CHECK.json',{'utc':utc(),'expected':48,'observed':len(rows),'all_semantic_success':smoke_pass,'measurement_data':False})
    if not smoke_pass:return
    for fork in range(1,4):
        units=[{'fork':fork,'phase':phase,'rep':rep,'scale':s,'r':r,'layout':b,'policy':p} for phase,reps in [('warmup',range(-10,0)),('measure',range(30))] for rep in reps for s,r,b,p in itertools.product([64,2048,65536,2097152],range(3),['same_bin','disjoint_bin'],['two','three'])]
        write(D/f'FORK{fork}_UNITS.json',units)
    for fork in range(1,4):child(java+[str(fork),'10','30'],f'fork{fork}',360)
    write(D/'COMPLETION.json',{'utc':utc(),'forks':3,'planned_measurement_units':4320,'planned_warmup_units':1440,'scientific_summary':'Pending independent raw checker; no result excluded or repeated.'})

if __name__=='__main__':main()
