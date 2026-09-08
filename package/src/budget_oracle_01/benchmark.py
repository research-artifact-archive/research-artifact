from pathlib import Path
import collections,datetime,hashlib,json,os,platform,random,signal,subprocess,sys,time
ROOT=Path(__file__).resolve().parent;DEST=ROOT/'benchmark01';METHODS=['requested_values','all_budget']
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,data):
    with p.open('x') as f:json.dump(data,f,indent=2,sort_keys=True);f.write('\n')
def relabel(cp,edges,rng):
    perm=list(range(len(cp)));rng.shuffle(perm);new=[None]*len(cp)
    for i,x in enumerate(cp):new[perm[i]]=x
    return dict(cp=new,edges=sorted([[perm[u],perm[v]] for u,v in edges]))
def prepare():
    DEST.mkdir();(DEST/'inputs').mkdir();rng=random.Random(202609080619);units=[]
    for group in ['chain','four_disjoint_chains','fence','four_wide_layers']:
        for n in [4,8,16,32]:
            if group=='chain':edges=[[i,i+1] for i in range(n-1)]
            elif group=='four_disjoint_chains':edges=[[i,i+4] for i in range(n-4)]
            elif group=='fence':edges=[[i,j] for i in range(0,n,2) for j in [i-1,i+1] if 0<=j<n]
            else:edges=[[4*l+i,4*(l+1)+j] for l in range(n//4-1) for i in range(4) for j in range(4)]
            base=[[rng.randint(1,24),rng.randint(0,48)] for _ in range(n)]
            for prices in ['SMALL','WIDE_PREMIUM','WIDE_PRICES']:
                cp=[]
                for c,p in base:
                    if prices=='WIDE_PREMIUM':p=p*(1<<32)+rng.randrange(1024) if p else 0
                    elif prices=='WIDE_PRICES':c=c*(1<<32)+rng.randrange(1024);p=p*(1<<32)+rng.randrange(1024) if p else 0
                    cp.append([c,p])
                sat=sum((p+c-1)//c for c,p in cp);budgets=[1,2,8,max(1,sat//4),max(1,sat//2),max(1,sat)]
                units.append(dict(id=f'{group}-{n}-{prices}',group=group,prices=prices,n=n,budgets=budgets,saturation_bound=sat,case=relabel(cp,edges,rng)))
    assert len(units)==48
    for u in units:save(DEST/'inputs'/(u['id']+'.json'),u)
    save(DEST/'INPUTS.json',units)
    files=[ROOT/x for x in ['BENCHMARK_PLAN.md','benchmark.py','benchmark_worker.py','oracle_session_hardened.py','values_certificate_hardened.py','HARDENING_MANIFEST.json','HARDENING_RAW.json']]
    files += [ROOT.parent/x for x in ['dependency_curves_01/curves.py','dependency_curves_01/checker.py','dependency_hybrid_01/hybrid.py','dependency_hybrid_check_02/check.py','final_evaluation_dag_01/structure.py']]
    files += [DEST/'INPUTS.json']+sorted((DEST/'inputs').glob('*.json'))
    save(DEST/'MANIFEST.json',dict(utc=now(),roots=48,units=96,methods=METHODS,python=sys.executable,python_sha256=sha(sys.executable),python_version=sys.version,platform=platform.platform(),cap_seconds=5,rss_cap_bytes=1073741824,rss_sample_seconds=.05,campaign_seconds=540,files=[dict(path=str(p),sha256=sha(p)) for p in files]));print('fixed48roots96coldunits')
def run():
    m=json.loads((DEST/'MANIFEST.json').read_text())
    for f in m['files']:assert sha(f['path'])==f['sha256'],f['path']
    assert sha(m['python'])==m['python_sha256']
    units=json.loads((DEST/'INPUTS.json').read_text());save(DEST/'RUN_STARTED.json',dict(utc=now(),pid=os.getpid(),manifest_sha256=sha(DEST/'MANIFEST.json')))
    start=time.monotonic();counts=collections.defaultdict(collections.Counter);agreements=[]
    with (DEST/'RAW.jsonl').open('x') as raw:
        for index,u in enumerate(units):
            successes={}
            for method in METHODS[index%2:]+METHODS[:index%2]:
                out=DEST/'units'/u['id']/method;out.mkdir(parents=True);row=dict(id=u['id'],method=method,group=u['group'],prices=u['prices'],n=u['n'],budgets=u['budgets'])
                if time.monotonic()-start>=540 or datetime.datetime.now(datetime.timezone.utc)>=datetime.datetime(2026,9,8,0,50,tzinfo=datetime.timezone.utc):row.update(status='NOT_RUN',reason='campaign_or_session_deadline')
                else:
                    argv=[m['python'],str(ROOT/'benchmark_worker.py'),method,str(DEST/'inputs'/(u['id']+'.json')),str(out)];save(out/'COMMAND.json',dict(argv=argv,wall_seconds=5,rss_bytes=1073741824));before=time.monotonic();rss=0;reason=None
                    with (out/'stdout.txt').open('xb') as stdout,(out/'stderr.txt').open('xb') as stderr:
                        p=subprocess.Popen(argv,stdout=stdout,stderr=stderr,start_new_session=True)
                        while p.poll() is None:
                            if time.monotonic()-before>=5:reason='wall_timeout'
                            elif time.monotonic()-start>=540:reason='campaign_cap'
                            else:
                                q=subprocess.run(['/bin/ps','-o','rss=','-p',str(p.pid)],capture_output=True,text=True,timeout=2)
                                try:rss=max(rss,int(q.stdout.strip())*1024)
                                except ValueError:pass
                                if rss>1073741824:reason='memory_limit'
                            if reason:
                                try:os.killpg(p.pid,signal.SIGKILL)
                                except ProcessLookupError:pass
                                break
                            time.sleep(.05)
                        code=p.wait(timeout=5)
                    row.update(cold_seconds=time.monotonic()-before,exit_code=code,sampled_peak_rss_bytes=rss);result=None
                    if (out/'RESULT.json').exists():
                        try:result=json.loads((out/'RESULT.json').read_text())
                        except Exception as exc:row['parse_error']=repr(exc)
                    if reason:
                        row.update(status='FAILURE' if reason=='memory_limit' else 'TIMEOUT',reason=reason)
                        if result is not None:row['partial_result']=result
                    elif code or result is None:row.update(status='INVALID',reason='process_or_missing_result',partial_result=result)
                    else:row.update(result)
                counts[method][row['status']]+=1
                if row['status']=='SUCCESS':successes[method]=row['values']
                raw.write(json.dumps(row,sort_keys=True,separators=(',',':'))+'\n');raw.flush()
            agreements.append(dict(id=u['id'],exact_values=successes,consistent=len({tuple(v) for v in successes.values()})<=1))
            print(json.dumps(dict(completed_roots=index+1,counts={k:dict(v) for k,v in counts.items()})),flush=True)
    s=dict(utc=now(),roots=48,units=96,counts={k:dict(v) for k,v in counts.items()},seconds=time.monotonic()-start,disagreements=[x for x in agreements if not x['consistent']],raw_sha256=sha(DEST/'RAW.jsonl'));save(DEST/'AGREEMENTS.json',agreements);save(DEST/'SUMMARY.json',s);print(json.dumps(s,indent=2))
if __name__=='__main__':{'prepare':prepare,'run':run}[sys.argv[1]]()
