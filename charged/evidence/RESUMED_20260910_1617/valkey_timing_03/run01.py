#!/usr/bin/env python3
from pathlib import Path
import sys,importlib.util,ctypes,json,hashlib,subprocess,socket,tempfile,time,threading,random,datetime,platform,traceback
HERE=Path(__file__).resolve().parent;START=time.monotonic()
sys.path.insert(0,str(HERE.parent/'valkey_refresh_02'));from model import compile_policy
spec=importlib.util.spec_from_file_location('native_base',HERE.parent/'valkey_manifest_01/run01.py');base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def bounded():
 if time.monotonic()-START>900:raise TimeoutError('overall cap900seconds')

class Probe:
 def __init__(self,path):
  self.client=base.Resp(path);self.client.s.settimeout(2);self.stop=threading.Event();self.go=threading.Event();self.samples=[];self.errors=[];self.thread=threading.Thread(target=self.loop,daemon=True)
 def loop(self):
  try:
   self.go.wait();due=time.perf_counter()
   while not self.stop.is_set():
    if self.stop.wait(max(0,due-time.perf_counter())):break
    a=time.perf_counter_ns();v=self.client.cmd('PING');b=time.perf_counter_ns();assert v==b'PONG';self.samples.append({'start_ns':a,'end_ns':b,'rtt_ns':b-a});due=max(due+.002,time.perf_counter())
  except Exception as e:self.errors.append(repr(e))
 def close(self):
  self.stop.set();self.go.set();self.thread.join(timeout=3)
  alive=self.thread.is_alive()
  if not alive:self.client.close()
  return alive

def main():
 build=json.loads((HERE/'BUILD_RESULT.json').read_text());server=json.loads((HERE.parent/'valkey_manifest_01/BUILD02_RESULT.json').read_text());assert build['status']==server['status']=='SUCCESS'
 lib=ctypes.CDLL(build['library']);f=lib.PlainHash;f.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_void_p];f.restype=None
 def transform(blob):
  t=time.perf_counter_ns();src=ctypes.create_string_buffer(blob,len(blob)+1);dst=(ctypes.c_ubyte*20)();a=time.perf_counter_ns();f(src,len(blob),dst);b=time.perf_counter_ns();digest=bytes(dst).hex();return digest,b-a,time.perf_counter_ns()-t
 words={m:tuple(1<<i for i in range(3) if m>>i&1) for m in range(8)};rng=random.Random(20260910);cells=[];compile_start=time.perf_counter_ns()
 for scale in [4096,16384,65536]:
  for co in [(1,0,1),(1,1,0),(4,1,1),(1,4,1)]:
   coef=(co[0],co[1],co[2]*scale);weights=(scale,2*scale,3*scale);comp=compile_policy(weights,words,3,*coef)
   for scenario in ['none','small_once','large_once','all_once']:
    cells.append({'id':len(cells),'scale':scale,'weights':weights,'sizes':[64*w-9 for w in weights],'coefficient_template':co,'coefficients':coef,'scenario':scenario,'compiler':comp})
 compile_ns=time.perf_counter_ns()-compile_start;rng.shuffle(cells);schedule=[]
 for c in cells:
  for block in range(-1,8):
   modes=['direct','accept','retry','compiled'];rng.shuffle(modes)
   for mode in modes:schedule.append({'cell':c['id'],'block':block,'mode':mode,'warmup':block<0})
 out=HERE/'run01';out.mkdir(exist_ok=False)
 hardware={}
 for name in ['machdep.cpu.brand_string','hw.logicalcpu','hw.memsize']:
  r=subprocess.run(['sysctl','-n',name],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=5);hardware[name]=r.stdout.strip() if r.returncode==0 else r.stderr.strip()
 sources=[Path(__file__),HERE/'step_resp.lua',HERE/'full_resp.lua',HERE/'plain_client.c',HERE.parent/'valkey_refresh_02/model.py',HERE.parent/'valkey_manifest_01/writer.lua',HERE.parent/'valkey_manifest_01/run01.py']
 dump(out/'INPUT_MANIFEST.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exploratory':True,'cells':cells,'schedule':schedule,'measured_requests':1536,'warmup_requests':192,'smoke_requests':16,'files':{str(p):sha(p) for p in sources},'server':server,'client_build':build,'compiler_total_ns':compile_ns,'hardware':hardware,'platform':platform.platform(),'probe_intended_period_ms':2,'probe_one_outstanding':True,'actual_probe_gaps_reported':True})
 rec={'status':'RUNNING','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'expected_measured':1536,'expected_warmup':192,'completed_measured':0,'completed_warmup':0,'failures':0};dump(out/'START.json',rec)
 tmp=tempfile.TemporaryDirectory(prefix='vkt0910-',dir='/tmp');sock=tmp.name+'/s';proc=None;client=None;writer=None;log=(out/'SERVER_LOG.txt').open('x');current_cell=None;cellmap={c['id']:c for c in cells};payload_cache={}
 try:
  cmd=[server['binary'],'--port','0','--unixsocket',sock,'--unixsocketperm','700','--save','','--appendonly','no','--protected-mode','yes','--slowlog-log-slower-than','0','--slowlog-max-len','2048'];rec['server_command']=cmd
  proc=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT)
  for _ in range(100):
   if Path(sock).exists():break
   if proc.poll() is not None:raise RuntimeError('server exited before socket')
   time.sleep(.02)
  client=base.Resp(sock);writer=base.Resp(sock);client.s.settimeout(15);writer.s.settimeout(15);assert client.cmd('PING')==b'PONG'
  scripts={name:client.cmd('SCRIPT','LOAD',path.read_bytes(),category='script_load').decode() for name,path in [('step',HERE/'step_resp.lua'),('full',HERE/'full_resp.lua'),('writer',HERE.parent/'valkey_manifest_01/writer.lua')]}
  def payloads(c):
   key=(c['scale'],c['scenario'])
   if key not in payload_cache:
    initial=[base.payload(i,0,s) for i,s in enumerate(c['sizes'])];indices=[] if c['scenario']=='none' else [0] if c['scenario']=='small_once' else [2] if c['scenario']=='large_once' else [0,1,2];updated=initial.copy();requests=[];versions=['0']*3
    for serial,i in enumerate(indices,1):
     updated[i]=base.payload(i,serial,c['sizes'][i]);versions[i]='1';requests.append(json.dumps({'updates':[[i+1,updated[i].decode()]]},separators=(',',':')))
    expected={'versions':versions,'digests':[hashlib.sha1(b).hexdigest() for b in updated]};payload_cache[key]=(initial,updated,requests,expected)
   return payload_cache[key]
  def case(c,mode,block,warmup=False,smoke=False):
   bounded();initial,updated,requests,expected=payloads(c);args=[]
   for i,b in enumerate(initial):args += [f'v:{i+1}','0',f'b:{i+1}',b]
   client.cmd('HSET','data',*args,category='setup');client.cmd('DEL','output',category='setup');client.cmd('SLOWLOG','RESET',category='setup')
   probe=Probe(sock);probe.thread.start();before=client.count.copy();sent=client.sent.copy();recv=client.received.copy();commands=[];writer_ns=[];trace=[];outside=0;core_ns=0;step_ns=0;root='direct' if mode=='direct' or (mode=='compiled' and c['compiler']['root_action']=='direct') else 'prepare';t=2;e=0;status='SUCCESS';error=None;started=time.perf_counter_ns();probe.go.set();ended=None
   def call(category,*cmd):
    a=time.perf_counter_ns();v=client.cmd(*cmd,category=category);b=time.perf_counter_ns();commands.append({'kind':category,'start_ns':a-started,'end_ns':b-started,'roundtrip_ns':b-a});return v
   try:
    if root=='prepare':
     fields=[f'{x}:{i+1}' for i in range(3) for x in ['v','b']];snap=call('snapshot','HMGET','data',*fields);versions=[snap[2*i].decode() for i in range(3)];digests=[]
     for i in range(3):
      d,a,b=transform(snap[2*i+1]);digests.append(d);outside+=c['weights'][i];core_ns+=a;step_ns+=b
    for request in requests:
     a=time.perf_counter_ns();writer.cmd('EVALSHA',scripts['writer'],1,'data',request,category='external_write');writer_ns.append(time.perf_counter_ns()-a)
    for attempt in range(3):
     if root=='direct':
      raw=call('validation','EVALSHA',scripts['full'],2,'data','output',3);assert raw[0]==2;result={'versions':[v.decode() for v in raw[1]],'digests':[d.decode() for d in raw[2]]};L=sum(c['weights']);trace.append({'action':'direct'});break
     req={'sizes':c['sizes'],'mode':mode,'versions':versions,'digests':digests,'t':t,'e':e,'ceiling':c['compiler']['ceiling'],'counts':c['compiler']['counts'],'actions':c['compiler']['actions']};encoded=json.dumps(req,separators=(',',':'));raw=call('validation','EVALSHA',scripts['step'],2,'data','output',encoded)
     if raw[0]==0:
      _,mask,e,t,vs,refresh=raw;trace.append({'action':'r','mask':mask,'refresh_bytes':sum(len(b) for i,b in refresh)});versions=[v.decode() for v in vs]
      for i,blob in refresh:
       d,a,b=transform(blob);digests[i-1]=d;outside+=c['weights'][i-1];core_ns+=a;step_ns+=b
     else:
      assert raw[0]==1;_,mask,e,vs,ds=raw;result={'versions':[v.decode() for v in vs],'digests':[d.decode() for d in ds]};L=sum(w for i,w in enumerate(c['weights']) if mask>>i&1);trace.append({'action':'a','mask':mask});break
    else:raise AssertionError('cap exhausted without completion')
    ended=time.perf_counter_ns()
    if ended-started>15_000_000_000:raise TimeoutError('request cap15seconds')
   except Exception as ex:
    ended=time.perf_counter_ns();status='TIMEOUT' if isinstance(ex,(TimeoutError,socket.timeout)) else 'FAILURE';error=repr(ex)
   finally:
    alive=probe.close()
   if alive or probe.errors:status='FAILURE';error='probe:'+repr({'alive':alive,'errors':probe.errors})
   nsnapshot=client.count['snapshot']-before['snapshot'];nvalidation=client.count['validation']-before['validation'];Q=nsnapshot+nvalidation;wire_sent=sum(client.sent[x]-sent[x] for x in ['snapshot','validation']);wire_recv=sum(client.received[x]-recv[x] for x in ['snapshot','validation'])
   logs=client.cmd('SLOWLOG','GET',2048);foreground_server=[];writer_server=[]
   for entry in logs:
    argv=entry[3]
    if not argv:continue
    name=argv[0].upper();duration=int(entry[2])*1000
    if (name==b'EVALSHA' and argv[1].decode() in [scripts['step'],scripts['full']]) or (name==b'HMGET' and len(argv)==8 and argv[1]==b'data'):
     foreground_server.append({'command':name.decode(),'duration_ns':duration,'slowlog_id':entry[0]})
    elif name==b'EVALSHA' and argv[1].decode()==scripts['writer']:writer_server.append(duration)
   samples=[{'start_ns':x['start_ns']-started,'end_ns':x['end_ns']-started,'rtt_ns':x['rtt_ns']} for x in probe.samples if started<=x['start_ns']<=ended]
   row={'status':status,'error':error,'cell':c['id'],'scale':c['scale'],'coefficient_template':c['coefficient_template'],'coefficients':c['coefficients'],'scenario':c['scenario'],'policy':mode,'root_action':root,'block':block,'warmup':warmup,'smoke':smoke,'foreground_ns':ended-started,'client_core_hash_ns':core_ns,'client_hash_step_ns':step_ns,'commands':commands,'server_foreground_commands':foreground_server,'max_foreground_server_command_ns':max([x['duration_ns'] for x in foreground_server],default=0),'sum_foreground_server_command_ns':sum(x['duration_ns'] for x in foreground_server),'writer_roundtrip_ns':writer_ns,'writer_server_ns':writer_server,'ping_samples':samples,'ping_count':len(samples),'ping_max_ns':max([x['rtt_ns'] for x in samples],default=None),'Q_snapshot':nsnapshot,'Q_validation':nvalidation,'Q_wire':Q,'wire_sent_bytes':wire_sent,'wire_received_bytes':wire_recv,'external_writes':len(requests),'trace':trace}
   if status=='SUCCESS':
    actual=base.oracle(client,3);pub=json.loads(client.cmd('GET','output'))
    try:
     assert result==pub==expected
     assert all(v==expected['versions'][i] and b==updated[i] for i,(v,b) in enumerate(actual))
     assert nvalidation<=3 and Q<=4 and len(foreground_server)==Q
     assert trace[-1]['action'] in ['a','direct']
     assert len(writer_server)==len(requests)
     W=outside+L;a,b,r=c['coefficients'];row.update(L=L,W=W,C=a*L+b*W+r*Q,expected_version_digest=expected)
    except Exception as ex:row.update(status='FAILURE',error=repr(ex))
   return row
  smoke=[]
  for scenario in ['none','small_once','large_once','all_once']:
   c={'id':-1,'scale':1,'weights':(1,2,3),'sizes':[55,119,183],'coefficient_template':(4,1,1),'coefficients':(4,1,1),'scenario':scenario,'compiler':compile_policy((1,2,3),words,3,4,1,1)}
   for mode in ['direct','accept','retry','compiled']:
    row=case(c,mode,-2,smoke=True);smoke.append(row)
    if row['status']!='SUCCESS':dump(out/'SMOKE.json',smoke);raise AssertionError('smoke failed:'+repr(row['error']))
  dump(out/'SMOKE.json',smoke)
  with (out/'ROWS.jsonl').open('x') as stream:
   for task in schedule:
    row=case(cellmap[task['cell']],task['mode'],task['block'],warmup=task['warmup']);stream.write(json.dumps(row,separators=(',',':'))+'\n');stream.flush()
    rec['completed_warmup' if task['warmup'] else 'completed_measured']+=1
    if row['status']!='SUCCESS':rec['failures']+=1
    if rec['completed_measured']%128==0 and not task['warmup']:
     dump(out/'PROGRESS.json',rec);print(json.dumps({'progress':rec['completed_measured'],'failures':rec['failures'],'seconds':time.monotonic()-START}),flush=True)
  rec['status']='SUCCESS' if rec['failures']==0 else 'FAILURE'
 except Exception as ex:rec.update(status='TIMEOUT' if isinstance(ex,TimeoutError) else 'FAILURE',exception=repr(ex),traceback=traceback.format_exc())
 finally:
  if client:
   try:client.close()
   except Exception:pass
  if writer:
   try:writer.close()
   except Exception:pass
  if proc:
   proc.terminate()
   try:proc.wait(timeout=10)
   except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=5)
   rec.update(server_pid=proc.pid,server_stopped=proc.poll() is not None,server_returncode=proc.returncode)
  log.close();tmp.cleanup();rec['seconds']=time.monotonic()-START;dump(out/'COMPLETION.json',rec);print(json.dumps(rec))
 return 0 if rec['status']=='SUCCESS' else 1
if __name__=='__main__':sys.exit(main())
