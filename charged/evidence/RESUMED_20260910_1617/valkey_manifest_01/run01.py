#!/usr/bin/env python3
"""Exploratory native exact-resource correspondence, not timing evaluation."""
from pathlib import Path
from functools import lru_cache
from collections import deque,Counter
import socket,subprocess,tempfile,time,itertools,hashlib,json,datetime,copy,sys,os
HERE=Path(__file__).resolve().parent
START=time.monotonic()
def dump(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def bounded():
 if time.monotonic()-START>600: raise TimeoutError('whole native exploration cap600s')

class Resp:
 def __init__(self,path):
  self.s=socket.socket(socket.AF_UNIX);self.s.settimeout(10);self.s.connect(path);self.f=self.s.makefile('rb');self.count=Counter();self.sent=Counter();self.received=Counter()
 def cmd(self,*args,category='oracle'):
  a=[v if isinstance(v,bytes) else str(v).encode() for v in args]
  raw=b'*'+str(len(a)).encode()+b'\r\n'+b''.join(b'$'+str(len(v)).encode()+b'\r\n'+v+b'\r\n' for v in a)
  self.count[category]+=1;self.sent[category]+=len(raw);self.s.sendall(raw)
  def parse():
   line=self.f.readline();self.received[category]+=len(line)
   if not line:raise EOFError('server connection closed')
   k=line[:1];v=line[1:-2]
   if k==b'+':return v
   if k==b'-':raise RuntimeError(v.decode())
   if k==b':':return int(v)
   if k==b'$':
    n=int(v)
    if n<0:return None
    b=self.f.read(n+2);self.received[category]+=len(b);assert b[-2:]==b'\r\n';return b[:-2]
   if k==b'*':return [parse() for _ in range(int(v))]
   raise ValueError(line)
  return parse()
 def close(self):self.f.close();self.s.close()

def observations(n,foot):
 words={0:()};queue=deque([0])
 while queue:
  m=queue.popleft()
  for f in foot:
   if m|f not in words:words[m|f]=words[m]+(f,);queue.append(m|f)
 return words

def compiler(sizes,words,q,k):
 obs=tuple(sorted(words));cost={m:len(words[m]) for m in obs};damage={m:sum(s for i,s in enumerate(sizes) if m>>i&1) for m in obs};w=max(damage.values());sigma=min(cost[m] for m in obs if damage[m]==w);ceiling=q*sigma
 @lru_cache(None)
 def informed(t,b):
  return max(k+(min(damage[m],informed(t-1,b-cost[m])) if t else damage[m]) for m in obs if cost[m]<=b)
 curve=[informed(q-1,b) for b in range(ceiling+1)]
 @lru_cache(None)
 def theta(t,e):
  return min(max(curve[min(e+cost[m],ceiling)]-k-damage[m],theta(t-1,min(e+cost[m],ceiling))-k if t else float('-inf')) for m in obs)
 actions={}
 for t in range(q):
  for e in range(ceiling+1):
   for m in obs:
    z=min(e+cost[m],ceiling);a=curve[z]-k-damage[m];r=theta(t-1,z)-k if t else float('-inf');actions[f'{t}:{e}:{m}']='r' if r>a else 'a'
 return {'counts':{str(m):cost[m] for m in obs},'actions':actions,'ceiling':ceiling,'curve':curve,'loss':-theta(q-1,0),'damage':damage}

def payload(i,serial,size):return bytes([65+(7*i+serial)%26])*size
def oracle(client,n):
 fields=[f'{kind}:{i+1}' for i in range(n) for kind in ['v','b']];v=client.cmd('HMGET','data',*fields)
 return [(v[2*i].decode(),v[2*i+1]) for i in range(n)]
def result_for(state):return {'versions':[v for v,b in state],'digests':[hashlib.sha1(b).hexdigest() for v,b in state]}

def check_row(row,sizes):
 trace=row['trace'];assert trace and len(trace)<=row['q'];assert row['status']=='SUCCESS'
 total=0
 for j,x in enumerate(trace):
  mask=sum(1<<i for i,(a,b) in enumerate(zip(x['prepared_versions'],x['current_versions'])) if a!=b)
  assert mask==x['returned']['mask']
  assert x['returned']['versions']==x['current_versions']
  action=x['returned']['action'];assert action in ['a','r']
  if action=='r':assert x['published'] is None and j<len(trace)-1 and x['returned']['hash_bytes']==0
  else:
   assert j==len(trace)-1
   expected=sum(s for i,s in enumerate(sizes) if mask>>i&1)
   assert x['returned']['hash_bytes']==expected;total+=expected
   assert x['returned']['result']==x['expected_result']==x['published']
 assert trace[-1]['returned']['action']=='a'
 assert row['L_payload']==total
 assert row['W_payload']==sum(sizes)*len(trace)+total
 assert row['Q_validation']==row['Q_snapshot']==len(trace)
 assert row['Q_wire']==2*len(trace)
 assert row['C']==row['toll']*len(trace)+total

def main():
 build=json.loads((HERE/'BUILD02_RESULT.json').read_text());assert build['status']=='SUCCESS'
 configs=[]
 for sizes in [(8,16),(8,16,24)]:
  n=len(sizes)
  for family in ['singleton','overlap_batch']:
   foot=tuple(1<<i for i in range(n)) if family=='singleton' else ((1,3) if n==2 else (3,6))
   words=observations(n,foot)
   for q,k in itertools.product([1,2,3],[0,8,24]):
    comp=compiler(sizes,words,q,k)
    configs.append({'id':len(configs),'sizes':sizes,'family':family,'footprints':foot,'q':q,'toll':k,'observations':sorted(words),'words':{str(m):v for m,v in words.items()},'sequence_count':len(words)**q,'compiler':comp})
 matrix_count=sum(c['sequence_count']*3 for c in configs)
 outdir=HERE/'run01';outdir.mkdir(exist_ok=False)
 hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),HERE/'step.lua',HERE/'writer.lua',HERE/'full_server.lua']}
 manifest={'recorded_before_native_run_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exploratory':True,'matrix_raw_cases':matrix_count,'configurations':configs,'code_sha256':hashes,'build_binary_sha256':build['binary_sha256'],'planned_modes':['accept','retry','compiled'],'semantic_controls':['large_decimal_versions','same_content_write','repeat_footprint','post_publication_write'],'mutation_controls':['digest','dirty_mask','hash_bytes','reject_publication'],'native_deadline_seconds':600}
 dump(outdir/'INPUT_MANIFEST.json',manifest)
 tmp=tempfile.TemporaryDirectory(prefix='vk0910-',dir='/tmp');sock=tmp.name+'/s'
 log=(outdir/'SERVER_LOG.txt').open('x');proc=None;client=None;errors=[];completed=0;curves={};seen=set();example=None
 rec={'status':'RUNNING','matrix_expected':matrix_count,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 dump(outdir/'START.json',rec)
 try:
  proc=subprocess.Popen([build['binary'],'--port','0','--unixsocket',sock,'--unixsocketperm','700','--save','','--appendonly','no','--protected-mode','yes'],stdout=log,stderr=subprocess.STDOUT)
  for _ in range(100):
   if Path(sock).exists():break
   if proc.poll() is not None:raise RuntimeError('server exited before socket')
   time.sleep(.02)
  client=Resp(sock);assert client.cmd('PING')==b'PONG'
  scripts={name:client.cmd('SCRIPT','LOAD',(HERE/name).read_bytes(),category='script_load').decode() for name in ['step.lua','writer.lua','full_server.lua']}
  def initialize(sizes,base='0'):
   fields=[]
   for i,s in enumerate(sizes):fields += [f'v:{i+1}',base,f'b:{i+1}',payload(i,0,s)]
   client.cmd('HSET','data',*fields,category='setup');client.cmd('DEL','output',category='setup')
  def write(f,sizes,serial,same=False):
   current=oracle(client,len(sizes)) if same else None
   updates=[[i+1,(current[i][1] if same else payload(i,serial,s)).decode()] for i,s in enumerate(sizes) if f>>i&1]
   client.cmd('EVALSHA',scripts['writer.lua'],1,'data',json.dumps({'updates':updates}),category='external_write')
  def case(config,mode,sequence,tag='matrix',base='0',repeat=False,same=False):
   sizes=config['sizes'];q=config['q'];k=config['toll'];comp=config['compiler'];initialize(sizes,base);trace=[];e=0;t=q-1;serial=0;before=client.count.copy();sent=client.sent.copy();recv=client.received.copy()
   for m in sequence:
    fields=[f'{kind}:{i+1}' for i in range(len(sizes)) for kind in ['v','b']];snap=client.cmd('HMGET','data',*fields,category='snapshot');versions=[snap[2*i].decode() for i in range(len(sizes))];digests=[hashlib.sha1(snap[2*i+1]).hexdigest() for i in range(len(sizes))]
    word=config['words'][str(m)]
    for f in word:
     serial+=1;write(f,sizes,serial,same)
     if repeat:serial+=1;write(f,sizes,serial,same)
    request={'sizes':sizes,'mode':mode,'versions':versions,'digests':digests,'t':t,'e':e,'ceiling':comp['ceiling'],'counts':comp['counts'],'actions':comp['actions']}
    raw=client.cmd('EVALSHA',scripts['step.lua'],2,'data','output',json.dumps(request,separators=(',',':')),category='validation');returned=json.loads(raw)
    state=oracle(client,len(sizes));pub=client.cmd('GET','output');published=json.loads(pub) if pub is not None else None
    trace.append({'requested_observation':m,'prepared_versions':versions,'current_versions':[v for v,b in state],'expected_result':result_for(state),'returned':returned,'published':published})
    e=int(returned['next_e'])
    if returned['action']=='a':break
    t=int(returned['next_t'])
   nc={a:client.count[a]-before[a] for a in client.count};qb=nc.get('validation',0);l=sum(x['returned']['hash_bytes'] for x in trace)
   row={'status':'SUCCESS','tag':tag,'configuration':config['id'],'mode':mode,'planned_sequence':sequence,'q':q,'toll':k,'B_used':serial,'Q_validation':qb,'Q_snapshot':nc.get('snapshot',0),'Q_wire':qb+nc.get('snapshot',0),'L_payload':l,'W_payload':sum(sizes)*qb+l,'C':k*qb+l,'trace':trace,'command_counts':nc,'foreground_sent_bytes':sum(client.sent[a]-sent[a] for a in ['validation','snapshot']),'foreground_received_bytes':sum(client.received[a]-recv[a] for a in ['validation','snapshot'])}
   check_row(row,sizes);return row
  with (outdir/'ROWS.jsonl').open('x') as rows:
   for config in configs:
    for mode in ['accept','retry','compiled']:
     native=[None]*(config['compiler']['ceiling']+1)
     for sequence in itertools.product(config['observations'],repeat=config['q']):
      bounded()
      row=case(config,mode,sequence);rows.write(json.dumps(row,separators=(',',':'))+'\n');completed+=1
      seen.add((config['id'],mode,tuple(x['returned']['mask'] for x in row['trace'])))
      if example is None and row['L_payload']>0 and row['Q_validation']>1:example=(row,config['sizes'])
      for b in range(row['B_used'],len(native)):native[b]=max(row['C'],native[b] if native[b] is not None else -1)
     assert all(v is not None for v in native)
     known=config['compiler']['curve'];loss=max(v-k for v,k in zip(native,known))
     curves[f"{config['id']}:{mode}"]={'native_curve':native,'informed_curve':known,'maximum_additive_loss':loss,'compiled_optimum_loss':config['compiler']['loss']}
     if mode=='compiled' and loss!=config['compiler']['loss']:raise AssertionError(('compiled curve loss',config['id'],loss,config['compiler']['loss']))
  dump(outdir/'CURVES.json',curves)
  controls=[];c=next(c for c in configs if c['sizes']==(8,16) and c['family']=='singleton' and c['q']==2 and c['toll']==8)
  for name,options in [('large_decimal_versions',{'base':'922337203685477580899999999999999999'}),('same_content_write',{'same':True}),('repeat_footprint',{'repeat':True})]:controls.append(case(c,'retry',(1,3),tag=name,**options))
  before_pub=client.cmd('GET','output');old=json.loads(before_pub);write(1,c['sizes'],99);assert client.cmd('GET','output')==before_pub and result_for(oracle(client,2))!=old
  controls.append({'tag':'post_publication_write','status':'SUCCESS','published_value_remains_historical_linearization':True})
  dump(outdir/'SEMANTIC_CONTROLS.json',controls)
  assert example is not None
  mutations=[]
  for name in ['digest','dirty_mask','hash_bytes','reject_publication']:
   row,sizes=copy.deepcopy(example)
   if name=='digest':row['trace'][-1]['returned']['result']['digests'][0]='0'*40
   if name=='dirty_mask':row['trace'][-1]['returned']['mask']^=1
   if name=='hash_bytes':row['trace'][-1]['returned']['hash_bytes']+=1
   if name=='reject_publication':row['trace'][0]['published']={'wrong':'publication'}
   rejected=False
   try:check_row(row,sizes)
   except AssertionError:rejected=True
   mutations.append({'name':name,'rejected':rejected});assert rejected
  dump(outdir/'MUTATION_CONTROLS.json',mutations)
  alternatives=[]
  for sizes in [(8,16),(8,16,24)]:
   initialize(sizes);write((1<<len(sizes))-1,sizes,1)
   reply=json.loads(client.cmd('EVALSHA',scripts['full_server.lua'],2,'data','output',len(sizes),category='alternative_validation'));assert reply['result']==result_for(oracle(client,len(sizes)));assert reply['hash_bytes']==sum(sizes)
   alternatives.append({'kind':'all_server_current_publication','sizes':sizes,'Q_validation':1,'Q_snapshot':0,'Q_wire':1,'L_payload':sum(sizes),'W_payload':sum(sizes),'status':'SUCCESS'})
   snap=oracle(client,len(sizes));snapshot_result=result_for(snap);write(1,sizes,2);assert snapshot_result!=result_for(oracle(client,len(sizes)))
   alternatives.append({'kind':'snapshot_return_only','sizes':sizes,'Q_wire':1,'L_payload':0,'W_payload':sum(sizes),'current_version_publication':False,'status':'SUCCESS'})
  dump(outdir/'ALTERNATIVES.json',alternatives)
  rec.update(status='SUCCESS',matrix_success=completed,matrix_failure=0,matrix_timeout=0,matrix_invalid=0,unique_policy_executions=len(seen),native_policy_curves=len(curves),semantic_controls=4,mutation_controls=4,alternatives=4,counts=dict(client.count),sent_bytes=dict(client.sent),received_bytes=dict(client.received))
 except Exception as ex:
  import traceback
  rec.update(status='TIMEOUT' if isinstance(ex,TimeoutError) else 'FAILURE',exception=repr(ex),traceback=traceback.format_exc(),matrix_completed_before_failure=completed,matrix_unexecuted=matrix_count-completed)
 finally:
  if client:
   try:client.close()
   except Exception:pass
  if proc:
   proc.terminate()
   try:proc.wait(timeout=10)
   except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=5)
   rec['server_pid']=proc.pid;rec['server_returncode_after_owned_shutdown']=proc.returncode;rec['server_stopped']=proc.poll() is not None
  log.close();tmp.cleanup();rec['seconds']=time.monotonic()-START;dump(outdir/'COMPLETION.json',rec);print(json.dumps(rec))
 return 0 if rec['status']=='SUCCESS' else 1

if __name__=='__main__':sys.exit(main())
