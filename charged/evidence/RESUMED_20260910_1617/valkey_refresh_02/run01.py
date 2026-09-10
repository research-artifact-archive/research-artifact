#!/usr/bin/env python3
from pathlib import Path
import importlib.util,ctypes,hashlib,json,datetime,itertools,subprocess,tempfile,time,copy,sys
from collections import Counter
from model import compile_policy
HERE=Path(__file__).resolve().parent;START=time.monotonic()
spec=importlib.util.spec_from_file_location('native01',HERE.parent/'valkey_manifest_01/run01.py');base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def bounded():
 if time.monotonic()-START>600:raise TimeoutError('whole native study cap600s')

def check(row,weights):
 assert row['status']=='SUCCESS'
 P=sum(weights);trace=row['trace'];assert trace and len(trace)<=row['q']
 L=0;outside=0
 for x in row['outside_hashes']:
  assert x['blocks']==(x['bytes']+72)//64;outside+=x['blocks']
 if row['root_action']=='direct':
  assert len(trace)==1 and not row['outside_hashes'] and row['Q_snapshot']==0
  x=trace[0];assert x['returned']['action']=='direct'
  assert x['returned']['result']==x['expected_result']==x['published'];L=P
  if row['instrumented']:assert x['returned']['hash_blocks']==P
 else:
  assert row['Q_snapshot']==1
  for j,x in enumerate(trace):
   mask=sum(1<<i for i,(v,w) in enumerate(zip(x['prepared_versions'],x['current_versions'])) if v!=w)
   assert x['returned']['mask']==mask and x['returned']['versions']==x['current_versions']
   action=x['returned']['action'];assert action in ['a','r']
   if action=='r':
    assert j<len(trace)-1 and x['published'] is None
    ids=[i for i,b in x['returned']['refresh']];assert ids==[i+1 for i in range(len(weights)) if mask>>i&1]
    assert x['next_prepared']==x['expected_result']
    assert x['returned']['hash_bytes']==0
    if row['instrumented']:assert x['returned']['hash_blocks']==0
   else:
    assert j==len(trace)-1;L=sum(w for i,w in enumerate(weights) if mask>>i&1)
    assert x['returned']['result']==x['expected_result']==x['published']
    assert x['returned']['hash_bytes']==sum(64*w-9 for i,w in enumerate(weights) if mask>>i&1)
    if row['instrumented']:assert x['returned']['hash_blocks']==L
  assert trace[-1]['returned']['action']=='a'
 assert row['L']==L and row['W']==outside+L
 assert row['Q_validation']==len(trace) and row['Q_wire']==row['Q_snapshot']+len(trace)
 assert row['Q_wire']<=row['q']+1
 a,b,r=row['coefficients'];assert row['C']==a*row['L']+b*row['W']+r*row['Q_wire']

def normalized(row):
 x=copy.deepcopy(row)
 for k in ['instrumented','server_kind','foreground_sent_bytes','foreground_received_bytes']:x.pop(k,None)
 for y in x['trace']:y['returned'].pop('hash_blocks',None)
 return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def main():
 build=json.loads((HERE/'BUILD_RESULT.json').read_text());original=json.loads((HERE.parent/'valkey_manifest_01/BUILD02_RESULT.json').read_text());assert build['status']==original['status']=='SUCCESS'
 library=ctypes.CDLL(build['library']);f=library.RetryHash;f.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_void_p];f.restype=ctypes.c_ulonglong
 def native_hash(blob,stage,index):
  assert len(blob)<2**32
  src=ctypes.create_string_buffer(blob,len(blob)+1);dest=(ctypes.c_ubyte*20)();blocks=int(f(src,len(blob),dest));digest=bytes(dest).hex()
  assert digest==hashlib.sha1(blob).hexdigest();assert blocks==(len(blob)+72)//64
  return digest,{'stage':stage,'component':index,'bytes':len(blob),'blocks':blocks,'digest':digest}
 configs=[]
 for weights in [(1,2),(1,2,3)]:
  n=len(weights);sizes=tuple(64*w-9 for w in weights)
  for family in ['singleton','overlap_batch']:
   foot=tuple(1<<i for i in range(n)) if family=='singleton' else ((1,3) if n==2 else (3,6));words=base.observations(n,foot)
   for q,coef in itertools.product([1,2,3],[(1,0,0),(1,0,1),(1,1,0),(4,1,1),(1,4,1)]):
    comp=compile_policy(weights,words,q,*coef);configs.append({'id':len(configs),'weights':weights,'sizes':sizes,'family':family,'footprints':foot,'q':q,'coefficients':coef,'words':{str(m):v for m,v in words.items()},'observations':sorted(words),'sequence_count':len(words)**q,'compiler':comp})
 outdir=HERE/'run01';outdir.mkdir(exist_ok=False);matrix_count=sum(c['sequence_count']*3 for c in configs)
 paths=[Path(__file__),HERE/'model.py',HERE/'step.lua',HERE/'full_server.lua',HERE.parent/'valkey_manifest_01/writer.lua',HERE.parent/'valkey_manifest_01/run01.py']
 dump(outdir/'INPUT_MANIFEST.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'per_binary_raw_cases':matrix_count,'binaries':['instrumented','unmodified'],'configurations':configs,'file_hashes':{str(p):sha(p) for p in paths},'build':build,'unmodified':original,'primitive_lengths':[0,1,55,56,63,64,65,119,120,127,128,129,4096],'exploratory':True})
 rec={'status':'RUNNING','matrix_expected_per_binary':matrix_count,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'binaries':{}};dump(outdir/'START.json',rec);hashes={};example=None
 try:
  for kind,binary,measure in [('instrumented',build['binary'],True),('unmodified',original['binary'],False)]:
   tmp=tempfile.TemporaryDirectory(prefix='vkr0910-',dir='/tmp');sock=tmp.name+'/s';log=(outdir/(kind+'_SERVER_LOG.txt')).open('x');proc=None;client=None;done=0;unique=set();curves={};unit={'status':'RUNNING'}
   try:
    proc=subprocess.Popen([binary,'--port','0','--unixsocket',sock,'--unixsocketperm','700','--save','','--appendonly','no','--protected-mode','yes'],stdout=log,stderr=subprocess.STDOUT)
    for _ in range(100):
     if Path(sock).exists():break
     if proc.poll() is not None:raise RuntimeError('server exited')
     time.sleep(.02)
    client=base.Resp(sock);assert client.cmd('PING')==b'PONG'
    scripts={name:client.cmd('SCRIPT','LOAD',p.read_bytes(),category='script_load').decode() for name,p in [('step',HERE/'step.lua'),('full',HERE/'full_server.lua'),('writer',HERE.parent/'valkey_manifest_01/writer.lua')]}
    primitive_script=b"local m=ARGV[2]=='1';local b=m and redis.retrysha1blocks() or 0;local d=redis.sha1hex(ARGV[1]);return {d,m and redis.retrysha1blocks()-b or -1}"
    ps=client.cmd('SCRIPT','LOAD',primitive_script,category='script_load').decode();primitive=[]
    for n in [0,1,55,56,63,64,65,119,120,127,128,129,4096]:
     blob=bytes((i*37+13)%256 for i in range(n));digest,hc=native_hash(blob,'primitive',0);reply=client.cmd('EVALSHA',ps,0,blob,'1' if measure else '0',category='primitive');assert reply[0].decode()==digest
     if measure:assert reply[1]==hc['blocks']
     primitive.append({'bytes':n,'client_count':hc['blocks'],'server_count':reply[1],'hash':digest,'status':'SUCCESS'})
    dump(outdir/(kind+'_PRIMITIVE.json'),primitive)
    def init(c,version='0'):
     args=[]
     for i,s in enumerate(c['sizes']):args += [f'v:{i+1}',version,f'b:{i+1}',base.payload(i,0,s)]
     client.cmd('HSET','data',*args,category='setup');client.cmd('DEL','output',category='setup')
    def write(c,foot,serial):
     updates=[[i+1,base.payload(i,serial,s).decode()] for i,s in enumerate(c['sizes']) if foot>>i&1];client.cmd('EVALSHA',scripts['writer'],1,'data',json.dumps({'updates':updates}),category='external_write')
    def case(c,mode,sequence,tag='matrix',version='0'):
     init(c,version);weights=c['weights'];sizes=c['sizes'];q=c['q'];comp=c['compiler'];initial_direct=mode=='compiled' and comp['root_action']=='direct';root_action='direct' if initial_direct else 'prepare';trace=[];outside=[];t=q-1;e=0;serial=0;before=client.count.copy();sent=client.sent.copy();recv=client.received.copy()
     if not initial_direct:
      fields=[f'{x}:{i+1}' for i in range(len(sizes)) for x in ['v','b']];snap=client.cmd('HMGET','data',*fields,category='snapshot');versions=[snap[2*i].decode() for i in range(len(sizes))];digests=[]
      for i in range(len(sizes)):
       d,hc=native_hash(snap[2*i+1],'initial',i);digests.append(d);outside.append(hc)
     for mask in sequence:
      for foot in c['words'][str(mask)]:serial+=1;write(c,foot,serial)
      if initial_direct:raw=client.cmd('EVALSHA',scripts['full'],2,'data','output',len(sizes),'1' if measure else '0',category='validation')
      else:
       req={'measure':measure,'sizes':sizes,'mode':mode,'versions':versions,'digests':digests,'t':t,'e':e,'ceiling':comp['ceiling'],'counts':comp['counts'],'actions':comp['actions']};raw=client.cmd('EVALSHA',scripts['step'],2,'data','output',json.dumps(req,separators=(',',':')),category='validation')
      reply=json.loads(raw);state=base.oracle(client,len(sizes));pub=client.cmd('GET','output');x={'returned':reply,'current_versions':[v for v,b in state],'expected_result':base.result_for(state),'published':json.loads(pub) if pub is not None else None}
      if not initial_direct:x['prepared_versions']=versions.copy()
      if reply['action']=='r':
       for i,blob in reply['refresh']:
        d,hc=native_hash(blob.encode(),'refresh',i-1);digests[i-1]=d;outside.append(hc)
       versions=reply['versions'];x['next_prepared']={'versions':versions.copy(),'digests':digests.copy()};t=int(reply['next_t']);e=int(reply['next_e'])
      trace.append(x)
      if reply['action']!='r':break
     nc={x:client.count[x]-before[x] for x in client.count};L=sum(weights) if initial_direct else sum(w for i,w in enumerate(weights) if trace[-1]['returned']['mask']>>i&1);W=L+sum(x['blocks'] for x in outside);Q=nc.get('snapshot',0)+nc.get('validation',0);a,b,r=c['coefficients']
     row={'status':'SUCCESS','tag':tag,'server_kind':kind,'instrumented':measure,'configuration':c['id'],'mode':mode,'root_action':root_action,'planned_sequence':sequence,'q':q,'coefficients':c['coefficients'],'B_used':serial,'Q_snapshot':nc.get('snapshot',0),'Q_validation':nc.get('validation',0),'Q_wire':Q,'L':L,'W':W,'C':a*L+b*W+r*Q,'outside_hashes':outside,'trace':trace,'command_counts':nc,'foreground_sent_bytes':sum(client.sent[x]-sent[x] for x in ['snapshot','validation']),'foreground_received_bytes':sum(client.received[x]-recv[x] for x in ['snapshot','validation'])}
     check(row,weights);return row
    with (outdir/(kind+'_ROWS.jsonl')).open('x') as rows:
     for c in configs:
      for mode in ['accept','retry','compiled']:
       curve=[None]*(c['compiler']['ceiling']+1)
       for seq in itertools.product(c['observations'],repeat=c['q']):
        bounded();row=case(c,mode,seq);rows.write(json.dumps(row,separators=(',',':'))+'\n');done+=1
        key=(c['id'],mode,seq);norm=normalized(row)
        if measure:hashes[key]=norm
        else:assert hashes[key]==norm,('unmodified semantic mismatch',key)
        actual=tuple(x['returned'].get('mask','direct') for x in row['trace']);unique.add((c['id'],mode,actual))
        if measure and example is None and len(row['trace'])>1 and row['L']>0:example=(row,c['weights'])
        for B in range(row['B_used'],len(curve)):curve[B]=max(row['C'],curve[B] if curve[B] is not None else -1)
       assert all(x is not None for x in curve);loss=max(v-k for v,k in zip(curve,c['compiler']['curve']));curves[f"{c['id']}:{mode}"]={'native_curve':curve,'informed_curve':c['compiler']['curve'],'regret':loss,'optimum':c['compiler']['loss'],'root_action':c['compiler']['root_action']}
       if mode=='compiled':assert loss==c['compiler']['loss'],('regret mismatch',c['id'],loss,c['compiler']['loss'])
    dump(outdir/(kind+'_CURVES.json'),curves)
    c=next(c for c in configs if c['weights']==(1,2) and c['family']=='singleton' and c['q']==2 and c['coefficients']==(4,1,1));control=case(c,'retry',(1,3),tag='large_decimal_version',version='92233720368547758089999999999999999');dump(outdir/(kind+'_VERSION_CONTROL.json'),control)
    unit.update(status='SUCCESS',matrix_success=done,unique_executions=len(unique),policy_curves=len(curves),primitive_checks=len(primitive),version_controls=1,command_counts=dict(client.count),sent_bytes=dict(client.sent),received_bytes=dict(client.received))
   except Exception as ex:
    import traceback
    unit.update(status='TIMEOUT' if isinstance(ex,TimeoutError) else 'FAILURE',exception=repr(ex),traceback=traceback.format_exc(),completed_before_failure=done,unexecuted=matrix_count-done);raise
   finally:
    if client:
     try:client.close()
     except Exception:pass
    if proc:
     proc.terminate()
     try:proc.wait(timeout=10)
     except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=5)
     unit.update(server_pid=proc.pid,server_stopped=proc.poll() is not None,server_returncode=proc.returncode)
    log.close();tmp.cleanup();rec['binaries'][kind]=unit;dump(outdir/(kind+'_COMPLETION.json'),unit)
  assert example is not None;mutations=[]
  for name in ['native_block_count','returned_digest','refresh_digest','dirty_mask']:
   row,weights=copy.deepcopy(example)
   if name=='native_block_count':row['trace'][-1]['returned']['hash_blocks']+=1
   if name=='returned_digest':row['trace'][-1]['returned']['result']['digests'][0]='0'*40
   if name=='refresh_digest':row['trace'][0]['next_prepared']['digests'][0]='0'*40
   if name=='dirty_mask':row['trace'][-1]['returned']['mask']^=1
   reject=False
   try:check(row,weights)
   except AssertionError:reject=True
   mutations.append({'name':name,'rejected':reject});assert reject
  dump(outdir/'MUTATION_CONTROLS.json',mutations);rec.update(status='SUCCESS',matrix_success=2*matrix_count,semantic_pairs=len(hashes),mutation_controls=4)
 except Exception as ex:
  import traceback
  rec.update(status='TIMEOUT' if isinstance(ex,TimeoutError) else 'FAILURE',exception=repr(ex),traceback=traceback.format_exc())
 rec['seconds']=time.monotonic()-START;dump(outdir/'COMPLETION.json',rec);print(json.dumps(rec));return 0 if rec['status']=='SUCCESS' else 1
if __name__=='__main__':sys.exit(main())
