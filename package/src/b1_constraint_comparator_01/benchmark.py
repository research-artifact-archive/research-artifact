from pathlib import Path
import collections,datetime,hashlib,json,os,platform,random,signal,subprocess,sys,time
ROOT=Path(__file__).resolve().parent;DEST=ROOT/'benchmark01'
METHODS=['cp_sat','subset_dp','all_budget']
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,data):
    with p.open('x') as f:json.dump(data,f,indent=2,sort_keys=True);f.write('\n')
def relabel(case,rng):
    n=len(case['cp']);perm=list(range(n));rng.shuffle(perm);cp=[None]*n
    for i,x in enumerate(case['cp']):cp[perm[i]]=x
    return dict(cp=cp,edges=sorted([[perm[u],perm[v]] for u,v in case['edges']]))

def prepare():
    DEST.mkdir();(DEST/'inputs').mkdir();rng=random.Random(202609080441);units=[]
    for n in [8,16,32,64]:
        for shape in ['chain','four_chains','fence','random_layers','independent']:
            if shape=='chain':edges=[[i,i+1] for i in range(n-1)]
            elif shape=='four_chains':
                length=n//4;edges=[[j*length+i,j*length+i+1] for j in range(4) for i in range(length-1)]
            elif shape=='fence':edges=[[i,j] for i in range(0,n,2) for j in [i-1,i+1] if 0<=j<n]
            elif shape=='random_layers':edges=[[l*4+i,(l+1)*4+j] for l in range(n//4-1) for i in range(4) for j in range(4) if rng.randrange(2)==0]
            else:edges=[]
            for prices in ['SMALL','WIDE_C','WIDE_P']:
                cp=[]
                for _ in range(n):
                    if prices=='SMALL':c=rng.randint(1,64);p=rng.randint(0,256)
                    elif prices=='WIDE_C':c=rng.randint(1,1<<32);p=rng.randint(0,8*c)
                    else:c=rng.randint(1,64);p=rng.randint(1,256)*(1<<40)+rng.randint(0,255)
                    cp.append([c,p])
                units.append(dict(id=f'{shape}-{n}-{prices}',group=shape,prices=prices,n=n,budget=1,case=relabel(dict(cp=cp,edges=edges),rng)))
    for n in [6,10,14]:
        for density in [1,2,3]:
            graph=[[u,v] for u in range(n) for v in range(u+1,n) if rng.randrange(4)<density]
            for k in [3,4]:
                ell=k*(k-1)//2;m=len(graph);N=n+1;K=N+m-ell
                if m<ell:case=dict(cp=[[2,1]],edges=[]);K=0
                else:
                    case=dict(cp=[[K+1,1] for _ in range(N)]+[[K-k,1] for _ in graph],
                              edges=[[v,N+j] for j,pair in enumerate(graph) for v in pair])
                units.append(dict(id=f'reduction-n{n}-d{density}-k{k}',group='clique_reduction',prices='UNIT_PREMIUM',n=len(case['cp']),budget=1,source_graph=dict(n=n,edges=graph,k=k),threshold=K,case=relabel(case,rng)))
    assert len(units)==78
    for u in units:save(DEST/'inputs'/(u['id']+'.json'),u)
    save(DEST/'INPUTS.json',units)
    files=[ROOT/x for x in ['BENCHMARK_PLAN.md','benchmark.py','benchmark_worker.py','comparator.py','certificate.py','DEV_MANIFEST.json','DEV_SUMMARY.json','REQUIREMENTS_FREEZE.txt']]
    files += [ROOT.parent/x for x in ['dependency_curves_01/curves.py','dependency_curves_01/checker.py','dependency_hybrid_01/hybrid.py','dependency_hybrid_check_02/check.py','final_evaluation_dag_01/structure.py']]
    files += [DEST/'INPUTS.json']+sorted((DEST/'inputs').glob('*.json'))
    save(DEST/'MANIFEST.json',dict(created=now(),roots=78,units=234,methods=METHODS,python=sys.executable,python_version=sys.version,platform=platform.platform(),cap_seconds=5,cp_solver_seconds=4,rss_cap_bytes=1073741824,poll_seconds=.05,campaign_cap_seconds=1250,files=[dict(path=str(p),sha256=sha(p)) for p in files]))
    print('fixed78roots234coldunits')

def run():
    m=json.loads((DEST/'MANIFEST.json').read_text())
    for f in m['files']:assert sha(f['path'])==f['sha256'],f['path']
    units=json.loads((DEST/'INPUTS.json').read_text());deadline=datetime.datetime(2026,9,8,0,50,tzinfo=datetime.timezone.utc)
    save(DEST/'RUN_STARTED.json',dict(utc=now(),manifest_sha256=sha(DEST/'MANIFEST.json'),pid=os.getpid()))
    start=time.monotonic();counts=collections.defaultdict(collections.Counter);agreements=[]
    with (DEST/'RAW.jsonl').open('x') as raw:
        for index,u in enumerate(units):
            successes={}
            for method in METHODS[index%3:]+METHODS[:index%3]:
                out=DEST/'units'/u['id']/method;out.mkdir(parents=True)
                row=dict(id=u['id'],method=method,group=u['group'],prices=u['prices'],n=u['n'],utc=now())
                if time.monotonic()-start>=1250 or datetime.datetime.now(datetime.timezone.utc)>=deadline:row.update(status='NOT_RUN',reason='campaign_or_session_deadline')
                else:
                    argv=[m['python'],str(ROOT/'benchmark_worker.py'),method,str(DEST/'inputs'/(u['id']+'.json')),str(out)]
                    save(out/'COMMAND.json',dict(argv=argv,wall_seconds=5,rss_cap_bytes=1073741824))
                    before=time.monotonic();rss=0;reason=None
                    with (out/'stdout.txt').open('xb') as stdout,(out/'stderr.txt').open('xb') as stderr:
                        proc=subprocess.Popen(argv,stdout=stdout,stderr=stderr,start_new_session=True)
                        while proc.poll() is None:
                            if time.monotonic()-before>=5:reason='wall_timeout'
                            elif time.monotonic()-start>=1250 or datetime.datetime.now(datetime.timezone.utc)>=deadline:reason='campaign_or_session_deadline'
                            else:
                                q=subprocess.run(['/bin/ps','-o','rss=','-p',str(proc.pid)],capture_output=True,text=True,timeout=2)
                                try:rss=max(rss,int(q.stdout.strip())*1024)
                                except ValueError:pass
                                if rss>1073741824:reason='memory_limit'
                            if reason:
                                try:os.killpg(proc.pid,signal.SIGKILL)
                                except ProcessLookupError:pass
                                break
                            time.sleep(.05)
                        code=proc.wait(timeout=5)
                    row.update(cold_seconds=time.monotonic()-before,exit_code=code,sampled_peak_rss_bytes=rss)
                    result=None
                    if (out/'RESULT.json').exists():
                        try:result=json.loads((out/'RESULT.json').read_text())
                        except Exception as exc:row['parse_error']=repr(exc)
                    if reason:
                        row.update(status='FAILURE' if reason=='memory_limit' else 'TIMEOUT',reason=reason)
                        if result is not None:row['partial_result']=result
                    elif code or result is None:row.update(status='INVALID',reason='process_or_missing_result',partial_result=result)
                    else:row.update(result)
                counts[method][row['status']]+=1
                if row['status']=='SUCCESS':successes[method]=row['value']
                raw.write(json.dumps(row,sort_keys=True,separators=(',',':'))+'\n');raw.flush()
            agreements.append(dict(id=u['id'],exact_values=successes,consistent=len(set(successes.values()))<=1))
            print(json.dumps(dict(completed_roots=index+1,roots=78,latest=u['id'],counts={k:dict(v) for k,v in counts.items()})),flush=True)
    result=dict(utc=now(),roots=78,units=234,counts={k:dict(v) for k,v in counts.items()},seconds=time.monotonic()-start,disagreements=[x for x in agreements if not x['consistent']],raw_sha256=sha(DEST/'RAW.jsonl'))
    save(DEST/'AGREEMENTS.json',agreements);save(DEST/'SUMMARY.json',result);print(json.dumps(result,indent=2))

if __name__=='__main__':{'prepare':prepare,'run':run}[sys.argv[1]]()
