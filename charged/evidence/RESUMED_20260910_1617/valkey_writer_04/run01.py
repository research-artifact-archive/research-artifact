#!/usr/bin/env python3
from pathlib import Path
from functools import lru_cache
import sys,importlib.util,ctypes,json,hashlib,subprocess,tempfile,time,random,datetime,platform,traceback,socket
HERE=Path(__file__).resolve().parent;START=time.monotonic()
sys.path.insert(0,str(HERE.parent/'valkey_refresh_02'));from model import compile_policy
spec=importlib.util.spec_from_file_location('base',HERE.parent/'valkey_manifest_01/run01.py');base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def bounded():
    if time.monotonic()-START>600:raise TimeoutError('whole study cap600s')

def main():
    build=json.loads((HERE.parent/'valkey_timing_03/BUILD_RESULT.json').read_text());server=json.loads((HERE.parent/'valkey_manifest_01/BUILD02_RESULT.json').read_text())
    assert build['status']==server['status']=='SUCCESS'
    lib=ctypes.CDLL(build['library']);fn=lib.PlainHash;fn.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_void_p];fn.restype=None
    def transform(blob):
        a=time.perf_counter_ns();src=ctypes.create_string_buffer(blob,len(blob)+1);dst=(ctypes.c_ubyte*20)();b=time.perf_counter_ns();fn(src,len(blob),dst);c=time.perf_counter_ns();d=bytes(dst).hex()
        return d,c-b,time.perf_counter_ns()-a
    words={m:tuple(1<<i for i in range(3) if m>>i&1) for m in range(8)};rng=random.Random(202609101804);cells=[]
    for scale in [4096,16384]:
        for R in [1,8]:
            for scenario in ['none','small_each','all_first','all_each']:
                weights=[scale,2*scale,3*scale];cells.append({'id':len(cells),'scale':scale,'R':R,'scenario':scenario,'weights':weights,'sizes':[64*w-9 for w in weights],'compiler':compile_policy(weights,words,3,4,1,scale)})
    rng.shuffle(cells);schedule=[]
    for c in cells:
        for block in range(-1,6):
            modes=['direct','compiled','maintained'];rng.shuffle(modes)
            for mode in modes:schedule.append({'cell':c['id'],'block':block,'policy':mode,'warmup':block<0})
    out=HERE/'run01';out.mkdir(exist_ok=False)
    paths=[Path(__file__),HERE/'writer_resp.lua',HERE/'cached_publish.lua',HERE/'PLAN.md',HERE.parent/'valkey_timing_03/step_resp.lua',HERE.parent/'valkey_timing_03/full_resp.lua',HERE.parent/'valkey_refresh_02/model.py',HERE.parent/'valkey_manifest_01/run01.py']
    hardware={}
    for name in ['machdep.cpu.brand_string','hw.logicalcpu','hw.memsize']:
        p=subprocess.run(['sysctl','-n',name],capture_output=True,text=True,timeout=5);hardware[name]=p.stdout.strip() if p.returncode==0 else p.stderr.strip()
    dump(out/'INPUT_MANIFEST.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exploratory':True,'cells':cells,'schedule':schedule,'expected_measured':288,'expected_warmup':48,'expected_smoke':12,'source_hashes':{str(p):sha(p) for p in paths},'server':server,'client_library':build,'hardware':hardware,'platform':platform.platform()})
    rec={'status':'RUNNING','expected_measured':288,'expected_warmup':48,'completed_measured':0,'completed_warmup':0,'completed_smoke':0,'failures':0};dump(out/'START.json',rec)
    tmp=tempfile.TemporaryDirectory(prefix='vkw0910-',dir='/tmp');sock=tmp.name+'/s';proc=None;client=None;log=(out/'SERVER_LOG.txt').open('x');cellmap={c['id']:c for c in cells}
    try:
        command=[server['binary'],'--port','0','--unixsocket',sock,'--unixsocketperm','700','--save','','--appendonly','no','--protected-mode','yes','--slowlog-log-slower-than','0','--slowlog-max-len','4096'];rec['server_command']=command
        proc=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
        for _ in range(100):
            if Path(sock).exists():break
            if proc.poll() is not None:raise RuntimeError('server stopped before readiness')
            time.sleep(.02)
        client=base.Resp(sock);client.s.settimeout(15);assert client.cmd('PING')==b'PONG'
        scripts={name:client.cmd('SCRIPT','LOAD',p.read_bytes(),category='script_load').decode() for name,p in [('writer',HERE/'writer_resp.lua'),('cached',HERE/'cached_publish.lua'),('step',HERE.parent/'valkey_timing_03/step_resp.lua'),('full',HERE.parent/'valkey_timing_03/full_resp.lua')]}
        @lru_cache(maxsize=1)
        def data(scale,R,scenario):
            sizes=[64*scale*i-9 for i in [1,2,3]];initial=[base.payload(i,0,s) for i,s in enumerate(sizes)];current=initial.copy();versions=[0]*3;reads=[];serial=0
            for r in range(R):
                ids=[] if scenario=='none' else [0] if scenario=='small_each' else [0,1,2] if scenario=='all_each' or r==0 else []
                updates=[]
                for i in ids:
                    serial+=1;blob=base.payload(i,serial,sizes[i]);current[i]=blob;versions[i]+=1;updates.append((i,blob,str(versions[i])))
                reads.append({'updates':updates,'expected':{'versions':[str(x) for x in versions],'digests':[hashlib.sha1(b).hexdigest() for b in current]}})
            return initial,reads,current
        def case(c,mode,block,smoke=False):
            bounded();initial,reads,final=data(c['scale'],c['R'],c['scenario']);args=[]
            for i,blob in enumerate(initial):args += [f'v:{i+1}','0',f'b:{i+1}',blob]
            a=time.perf_counter_ns();client.cmd('DEL','data','output',category='setup');client.cmd('HSET','data',*args,category='setup');setup_ns=time.perf_counter_ns()-a
            client.cmd('SLOWLOG','RESET',category='setup');before=client.count.copy();sent=client.sent.copy();recv=client.received.copy()
            events=[];outputs=[];L=0;readerW=0;writerW=0;initialW=0;status='SUCCESS';error=None;started=time.perf_counter_ns();ended=None;build_ns=0;initial_hash_ns=0;reader_hash_ns=0;writer_hash_ns=0
            def call(kind,*argv):
                a=time.perf_counter_ns();v=client.cmd(*argv,category=kind);b=time.perf_counter_ns();events.append({'kind':kind,'start_ns':a-started,'end_ns':b-started,'roundtrip_ns':b-a});return v
            try:
                if mode=='maintained':
                    a=time.perf_counter_ns();fields=[]
                    for i,blob in enumerate(initial):
                        d,core,whole=transform(blob);initial_hash_ns+=whole;initialW+=c['weights'][i];fields += [f'd:{i+1}',d]
                    call('maintenance_build','HSET','data',*fields);build_ns=time.perf_counter_ns()-a
                for r,entry in enumerate(reads):
                    read_start=time.perf_counter_ns();read_hash=0;writer_events=[];policy_trace=[];t=2;e=0;localL=0;localW=0
                    if mode=='compiled':
                        fields=[f'{k}:{i+1}' for i in range(3) for k in ['v','b']];snap=call('reader_snapshot','HMGET','data',*fields);versions=[snap[2*i].decode() for i in range(3)];digests=[]
                        for i in range(3):
                            d,core,whole=transform(snap[2*i+1]);digests.append(d);read_hash+=whole;localW+=c['weights'][i]
                    for i,blob,expectedv in entry['updates']:
                        a=time.perf_counter_ns();work=0;hashns=0;extra=[]
                        if mode=='maintained':
                            d,core,hashns=transform(blob);extra=[d];work=c['weights'][i];writerW+=work;writer_hash_ns+=hashns
                        actualv=call('writer','EVALSHA',scripts['writer'],1,'data','maintained' if mode=='maintained' else 'base',i+1,blob,*extra)
                        assert actualv.decode()==expectedv
                        writer_events.append({'component':i,'work':work,'hash_ns':hashns,'operation_ns':time.perf_counter_ns()-a})
                    for attempt in range(3):
                        if mode in ['direct','maintained']:
                            raw=call('reader_validation','EVALSHA',scripts['full' if mode=='direct' else 'cached'],2,'data','output',3);assert raw[0]==(2 if mode=='direct' else 3);result={'versions':[x.decode() for x in raw[1]],'digests':[x.decode() for x in raw[2]]};localL=sum(c['weights']) if mode=='direct' else 0;localW+=localL;policy_trace.append({'action':mode});break
                        req={'sizes':c['sizes'],'mode':'compiled','versions':versions,'digests':digests,'t':t,'e':e,'ceiling':c['compiler']['ceiling'],'counts':c['compiler']['counts'],'actions':c['compiler']['actions']};raw=call('reader_validation','EVALSHA',scripts['step'],2,'data','output',json.dumps(req,separators=(',',':')))
                        if raw[0]==0:
                            _,mask,e,t,vs,refresh=raw;policy_trace.append({'action':'r','mask':mask});versions=[x.decode() for x in vs]
                            for i,blob in refresh:
                                d,core,whole=transform(blob);digests[i-1]=d;read_hash+=whole;localW+=c['weights'][i-1]
                        else:
                            assert raw[0]==1;_,mask,e,vs,ds=raw;result={'versions':[x.decode() for x in vs],'digests':[x.decode() for x in ds]};localL=sum(w for i,w in enumerate(c['weights']) if mask>>i&1);localW+=localL;policy_trace.append({'action':'a','mask':mask});break
                    else:raise AssertionError('reader failed to complete in3validation calls')
                    read_end=time.perf_counter_ns();outputs.append({'read':r,'result':result,'expected':entry['expected'],'L':localL,'W':localW,'hash_ns':read_hash,'writer_operations':writer_events,'latency_with_writers_ns':read_end-read_start,'trace':policy_trace});L+=localL;readerW+=localW;reader_hash_ns+=read_hash
                ended=time.perf_counter_ns()
            except Exception as e:
                ended=time.perf_counter_ns();status='TIMEOUT' if isinstance(e,(TimeoutError,socket.timeout)) else 'FAILURE';error=repr(e)
            categories=['maintenance_build','writer','reader_snapshot','reader_validation'];counts={k:client.count[k]-before[k] for k in categories};wire={k:{'sent':client.sent[k]-sent[k],'received':client.received[k]-recv[k]} for k in categories}
            logs=client.cmd('SLOWLOG','GET',4096);server_events=[]
            for entry in logs:
                argv=entry[3];kind=None
                if argv and argv[0].upper()==b'EVALSHA':
                    name=next((k for k,v in scripts.items() if len(argv)>1 and argv[1].decode()==v),None)
                    if name is not None:kind='writer' if name=='writer' else 'reader_validation'
                elif argv and argv[0].upper()==b'HMGET' and len(argv)==8 and argv[1]==b'data':kind='reader_snapshot'
                elif argv and argv[0].upper()==b'HSET' and len(argv)==8 and argv[1]==b'data' and argv[2]==b'd:1':kind='maintenance_build'
                if kind is not None:server_events.append({'kind':kind,'duration_ns':int(entry[2])*1000,'slowlog_id':entry[0]})
            totalW=readerW+writerW+initialW;P=sum(c['weights']);updateW=sum(c['weights'][i] for r in reads for i,_,_ in r['updates']);reader_core=sum(x['roundtrip_ns'] for x in events if x['kind'].startswith('reader_'))+reader_hash_ns
            row={'cell':c['id'],'scale':c['scale'],'R':c['R'],'scenario':c['scenario'],'policy':mode,'block':block,'warmup':block<0 and not smoke,'smoke':smoke,'status':status,'error':error,'mixed_trace_ns':ended-started,'common_setup_ns':setup_ns,'maintenance_build_ns':build_ns,'initial_hash_ns':initial_hash_ns,'writer_hash_ns':writer_hash_ns,'reader_hash_ns':reader_hash_ns,'reader_command_plus_hash_ns':reader_core,'L_reader':L,'W_reader':readerW,'W_writer':writerW,'W_initial':initialW,'W_total':totalW,'update_weight':updateW,'P':P,'commands':counts,'wire':wire,'total_wire_bytes':sum(v['sent']+v['received'] for v in wire.values()),'events':events,'server_events':server_events,'max_any_server_ns':max([x['duration_ns'] for x in server_events],default=0),'sum_any_server_ns':sum(x['duration_ns'] for x in server_events),'reader_outputs':outputs}
            if status=='SUCCESS':
                try:
                    assert all(r['result']==r['expected'] for r in outputs);assert len(outputs)==c['R']
                    actual=base.oracle(client,3);pub=json.loads(client.cmd('GET','output'));assert pub==reads[-1]['expected'];assert all(v==reads[-1]['expected']['versions'][i] and b==final[i] for i,(v,b) in enumerate(actual))
                    assert counts['reader_validation']<=3*c['R'] and counts['reader_validation']+counts['reader_snapshot']<=4*c['R']
                    assert len(server_events)==sum(counts.values()),(len(server_events),counts)
                    assert counts['writer']==sum(len(r['updates']) for r in reads)
                    if mode=='direct':assert totalW==c['R']*P and L==totalW
                    elif mode=='maintained':assert totalW==P+updateW and readerW==L==0
                    else:assert writerW==initialW==0 and c['compiler']['root_action']=='prepare'
                except Exception as e:row.update(status='FAILURE',error=repr(e))
            return row
        smoke=[]
        for scenario in ['none','small_each','all_first','all_each']:
            c={'id':-1,'scale':1,'R':1,'scenario':scenario,'weights':[1,2,3],'sizes':[55,119,183],'compiler':compile_policy([1,2,3],words,3,4,1,1)}
            for mode in ['direct','compiled','maintained']:
                row=case(c,mode,-2,smoke=True);smoke.append(row);rec['completed_smoke']+=1
                if row['status']!='SUCCESS':dump(out/'SMOKE.json',smoke);raise AssertionError('smoke failed:'+str(row['error']))
        dump(out/'SMOKE.json',smoke)
        with (out/'ROWS.jsonl').open('x') as stream:
            for task in schedule:
                row=case(cellmap[task['cell']],task['policy'],task['block']);stream.write(json.dumps(row,separators=(',',':'))+'\n');stream.flush();rec['completed_warmup' if task['warmup'] else 'completed_measured']+=1
                if row['status']!='SUCCESS':rec['failures']+=1
                if rec['completed_measured']%36==0 and not task['warmup']:dump(out/'PROGRESS.json',rec);print(json.dumps({'measured':rec['completed_measured'],'failures':rec['failures'],'seconds':time.monotonic()-START}),flush=True)
        rec['status']='SUCCESS' if rec['failures']==0 else 'FAILURE'
    except Exception as e:rec.update(status='TIMEOUT' if isinstance(e,TimeoutError) else 'FAILURE',exception=repr(e),traceback=traceback.format_exc())
    finally:
        if client:
            try:client.close()
            except Exception:pass
        if proc:
            proc.terminate()
            try:proc.wait(timeout=10)
            except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=5)
            rec.update(server_pid=proc.pid,server_stopped=proc.poll() is not None,server_returncode=proc.returncode)
        log.close();tmp.cleanup();rec['seconds']=time.monotonic()-START;dump(out/'COMPLETION.json',rec);print(json.dumps(rec))
    return 0 if rec['status']=='SUCCESS' else 1
if __name__=='__main__':raise SystemExit(main())
