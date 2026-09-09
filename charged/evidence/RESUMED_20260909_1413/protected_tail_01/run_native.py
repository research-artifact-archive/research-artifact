from pathlib import Path
import datetime,hashlib,json,os,signal,subprocess,time
D=Path(__file__).resolve().parent;O=D/'native01';O.mkdir();classes=O/'classes';classes.mkdir();jdk=Path('/opt/homebrew/Cellar/openjdk@17/17.0.19/libexec/openjdk.jdk/Contents/Home/bin')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
write(O/'INPUT_RECEIPT.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':{p.name:sha(p) for p in [D/'NATIVE_INPUTS.json',D/'NATIVE_RUNS.tsv',D/'NATIVE_PLAN.json',D/'TailProbe.java',Path(__file__)]},'java_exe_sha256':sha(jdk/'java'),'javac_exe_sha256':sha(jdk/'javac'),'no_rerun':True})
for label,argv,cap in [('compile',[str(jdk/'javac'),'-d',str(classes),str(D/'TailProbe.java')],30),('native',[str(jdk/'java'),'-cp',str(classes),'TailProbe',str(D/'NATIVE_RUNS.tsv')],180)]:
 out=O/label;out.mkdir();start=time.monotonic();write(out/'INTENT.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':argv,'cap_seconds':cap})
 with (out/'stdout.txt').open('x') as stdout,(out/'stderr.txt').open('x') as stderr:
  p=subprocess.Popen(argv,stdout=stdout,stderr=stderr,start_new_session=True);write(out/'PROCESS.json',{'pid':p.pid,'pgid':p.pid})
  try:rc=p.wait(timeout=cap);status='SUCCESS' if rc==0 else 'FAILURE'
  except subprocess.TimeoutExpired:
   os.killpg(p.pid,signal.SIGTERM)
   try:rc=p.wait(timeout=3)
   except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);rc=p.wait()
   status='TIMEOUT'
 write(out/'RESULT.json',{'status':status,'returncode':rc,'seconds':time.monotonic()-start,'stdout_sha256':sha(out/'stdout.txt'),'stderr_sha256':sha(out/'stderr.txt')});print(label,status,flush=True)
 if status!='SUCCESS':break
