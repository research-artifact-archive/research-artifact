from pathlib import Path
import datetime,hashlib,itertools,json,os,random,signal,subprocess,time
D=Path(__file__).resolve().parent;C=Path('<AUTHOR_HOME>/Research/roslyn_build_20260909');app=C/'harness01/bin/Release/net10.0';O=D/'measurement01';O.mkdir()
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
assert json.loads((D/'development01/check02/CHECK_RECEIPT.json').read_text())['status']=='PASS'
assert json.loads((D/'development01/baseline_check01/CHECK_RECEIPT.json').read_text())['status']=='PASS'
plans=[]
for fork in range(1,4):
 rng=random.Random(20260909+fork);rows=[]
 for rep in range(-2,10):
  groups=[(n,r,b) for n in [1,8,64,256] for r in range(3) for b in sorted({0,r,r+1,r+4})];rng.shuffle(groups)
  for n,r,b in groups:
   modes=['original','two','three'];rng.shuffle(modes)
   for mode in modes:rows.append([f'f{fork}-{len(rows):04}','warmup' if rep<0 else 'measure',fork,rep,n,r,b,mode,'normal'])
 p=O/f'FORK{fork}_RUNS.tsv';p.write_text(''.join('\t'.join(map(str,x))+'\n' for x in rows));plans.append(p)
files={str(p.relative_to(D)):sha(p) for p in [D/'MEASUREMENT_PLAN.md',D/'check_native.py',D/'patch02/Workspace.patched.cs',D/'harness01/Program.cs',D/'harness01/RetryStudy.csproj',Path(__file__),*plans]}
write(O/'INPUT_RECEIPT.json',{'utc':utc(),'kind':'FIXED_REPETITIONS_AFTER_OBSERVED_DEVELOPMENT','files':files,'all_app_binaries':{p.name:sha(p) for p in sorted(app.iterdir()) if p.is_file()},'dotnet_host_sha256':sha(C/'dotnet/dotnet'),'measured_units':3960,'warmup_units':792,'fork_count':3,'runtime_target':'net10 driver/net8 source assemblies, exact10RC runtime','no_rerun':True,'per_process_cap_seconds':360})
env=os.environ.copy();env.update({'DOTNET_ROOT':str(C/'dotnet'),'DOTNET_CLI_HOME':str(C/'dotnet_cli_state'),'DOTNET_CLI_TELEMETRY_OPTOUT':'1','DOTNET_NOLOGO':'1'})
for fork,p in enumerate(plans,1):
 out=O/f'fork{fork}';out.mkdir();argv=[str(C/'dotnet/dotnet'),str(app/'RetryStudy.dll'),str(p)];start=time.monotonic();write(out/'INTENT.json',{'utc':utc(),'argv':argv,'cwd':str(app),'timeout_seconds':360})
 with (out/'stdout.jsonl').open('x') as stdout,(out/'stderr.txt').open('x') as stderr:
  child=subprocess.Popen(argv,cwd=app,env=env,stdout=stdout,stderr=stderr,start_new_session=True);write(out/'PROCESS.json',{'pid':child.pid,'pgid':child.pid})
  try:rc=child.wait(timeout=360);status='SUCCESS' if rc==0 else 'FAILURE'
  except subprocess.TimeoutExpired:
   os.killpg(child.pid,signal.SIGTERM)
   try:rc=child.wait(timeout=3)
   except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);rc=child.wait()
   status='TIMEOUT'
 result={'utc':utc(),'status':status,'returncode':rc,'seconds':time.monotonic()-start,'stdout_sha256':sha(out/'stdout.jsonl'),'stderr_sha256':sha(out/'stderr.txt')};write(out/'RESULT.json',result);print(fork,json.dumps(result),flush=True)
 result=subprocess.run(['python3','-B',str(D/'check_native.py'),'--runs',str(p),'--raw',str(out/'stdout.jsonl'),'--out',str(out/'check')],capture_output=True,text=True,timeout=60)
 (out/'checker_stdout.txt').write_text(result.stdout);(out/'checker_stderr.txt').write_text(result.stderr)
 print('check',fork,result.returncode,json.loads((out/'check/CHECK_RECEIPT.json').read_text())['status'] if (out/'check/CHECK_RECEIPT.json').exists() else 'NO_RECEIPT',flush=True)
write(O/'COMPLETION.json',{'utc':utc(),'all_forks_terminal':True,'measured_units':3960,'warmup_units':792})
