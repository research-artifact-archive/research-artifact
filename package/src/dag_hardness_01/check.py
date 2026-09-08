from pathlib import Path
from functools import lru_cache
import collections, datetime, hashlib, itertools, json, signal, sys, time, traceback

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'final_evaluation_dag_01'))
import evaluate as validation


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(name,value):
    with (ROOT/name).open('x') as f:json.dump(value,f,indent=2,sort_keys=True);f.write('\n')


def transform(n,edges,k):
    ell=k*(k-1)//2
    if len(edges)<ell:
        return dict(cp=[[2,1]],edges=[]),0,True
    N=n+1;m=len(edges);K=N+m-ell
    cp=[[K+1,1] for _ in range(N)]+[[K-k,1] for _ in edges]
    dag=[[v,N+j] for j,pair in enumerate(edges) for v in pair]
    assert K>k and all(c>0 and p==1 for c,p in cp)
    return dict(cp=cp,edges=dag),K,False


def generate():
    units=[]
    for n in range(2,6):
        possible=list(itertools.combinations(range(n),2))
        for mask in range(1<<len(possible)):
            edges=[list(e) for j,e in enumerate(possible) if mask>>j&1]
            for k in range(2,n+1):
                case,K,trivial=transform(n,edges,k)
                units.append(dict(id=f'n{n}-g{mask:04}-k{k}',original_n=n,graph_mask=mask,
                                  original_edges=edges,k=k,case=case,threshold=K,trivial_negative=trivial,
                                  compiler_selected=n<=4 or mask%64==0))
    assert len(units)==4306
    save('INPUTS.json',units)
    modules={Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None)
             and Path(m.__file__).suffix=='.py' and str(ROOT.parent) in str(Path(m.__file__).resolve())}
    modules.update([ROOT/'check.py',ROOT/'PLAN.md',ROOT/'PROOF_DRAFT.md',ROOT/'INPUTS.json'])
    manifest=dict(utc=now(),units=len(units),trivial_negative=sum(u['trivial_negative'] for u in units),
                  nontrivial=sum(not u['trivial_negative'] for u in units),
                  compiler_selected=sum(u['compiler_selected'] for u in units),
                  unit_seconds=2,total_seconds=180,files=[dict(path=str(p),sha256=sha(p)) for p in sorted(modules)])
    save('MANIFEST.json',manifest)
    print(json.dumps({k:v for k,v in manifest.items() if k!='files'},indent=2))


def solve(case):
    cp=case['cp'];n=len(cp)
    pred=[sum(1<<u for u,v in case['edges'] if v==i) for i in range(n)]
    decisions={}
    @lru_cache(None)
    def value(mask):
        if not mask:return 0
        actions=[]
        for i,(c,p) in enumerate(cp):
            if mask>>i&1 and not pred[i]&mask:
                child=value(mask^(1<<i))
                actions.extend([(p+child,i,'P'),(max(child,c),i,'F')])
        best=min(actions)
        decisions[mask]=best
        return best[0]
    full=(1<<n)-1;v=value(full);mask=full;certificate=[]
    while mask:
        _,i,mode=decisions[mask]
        certificate.append([i,mode]);mask^=1<<i
    return v,certificate,value.cache_info().currsize


def certificate_value(case,certificate):
    n=len(case['cp']);done=set();paid=0;worst=0
    assert len(certificate)==n
    for i,mode in certificate:
        assert 0<=i<n and i not in done
        assert all(u in done for u,v in case['edges'] if v==i)
        c,p=case['cp'][i]
        if mode=='P':paid+=p
        elif mode=='F':worst=max(worst,paid+c)
        else:raise AssertionError(mode)
        done.add(i)
    assert len(done)==n
    return max(worst,paid)


def check_unit(unit):
    edges={tuple(e) for e in unit['original_edges']};k=unit['k'];n=unit['original_n']
    witnesses=[list(xs) for xs in itertools.combinations(range(n),k)
               if all(e in edges for e in itertools.combinations(xs,2))]
    v,certificate,states=solve(unit['case'])
    scan=certificate_value(unit['case'],certificate)
    assert scan==v,(scan,v)
    assert (v<=unit['threshold'])==bool(witnesses),(unit,v,witnesses)
    constructed=None
    if witnesses:
        clique=set(witnesses[0]);N=n+1
        chosen=[N+j for j,e in enumerate(unit['original_edges']) if set(e)<=clique]
        order=[[x,'P'] for x in sorted(clique)]+[[e,'F'] for e in chosen]
        order+=[[x,'P'] for x in range(N) if x not in clique]
        order+=[[N+j,'P'] for j in range(len(unit['original_edges'])) if N+j not in chosen]
        q=certificate_value(unit['case'],order)
        assert q<=unit['threshold'],(q,unit['threshold'])
        constructed=dict(certificate=order,value=q)
    compiled_report=None
    if unit['compiler_selected']:
        data=validation.hybrid.compile_case(unit['case'])
        encoded=json.dumps(data,sort_keys=True,separators=(',',':')).encode()
        data=json.loads(encoded)
        if data['route']=='ordered':report=validation.packed.check(data)
        else:
            shape=validation.structure.check(data)
            report=validation.bellman.check(data);report['shape']=shape
        assert not report['violations'],report
        loaded=validation.hybrid.load(data)
        cv=validation.hybrid.value(loaded,1)
        assert cv==v,(cv,v)
        compiled_report=dict(route=data['route'],certificate=report,bytes=len(encoded),
                             sha256=hashlib.sha256(encoded).hexdigest(),value=cv)
    return dict(status='SUCCESS',value=v,threshold=unit['threshold'],clique=bool(witnesses),
                clique_witnesses=witnesses,states=states,normal=sum(c for c,p in unit['case']['cp']),
                certificate=certificate,certificate_value=scan,constructed=constructed,
                compiler_check=compiled_report if compiled_report else 'NOT_SELECTED_BY_PREDECLARED_RULE')


def alarm(sig,frame):raise TimeoutError('fixed unit/campaign cap')


def run():
    manifest=json.loads((ROOT/'MANIFEST.json').read_text())
    for f in manifest['files']:assert sha(f['path'])==f['sha256'],f['path']
    units=json.loads((ROOT/'INPUTS.json').read_text())
    save('RUN_STARTED.json',dict(utc=now(),manifest_sha256=sha(ROOT/'MANIFEST.json')))
    start=time.monotonic();counts=collections.Counter();stats=collections.Counter()
    signal.signal(signal.SIGALRM,alarm)
    with (ROOT/'RAW.jsonl').open('x') as raw:
        for unit in units:
            t=time.monotonic()
            if t-start>=180:row=dict(id=unit['id'],status='NOT_RUN',reason='campaign cap')
            else:
                signal.setitimer(signal.ITIMER_REAL,min(2,180-(t-start)))
                try:row=dict(id=unit['id'],**check_unit(unit))
                except AssertionError:row=dict(id=unit['id'],status='FAILURE',error=traceback.format_exc())
                except TimeoutError:row=dict(id=unit['id'],status='TIMEOUT',error=traceback.format_exc())
                except Exception:row=dict(id=unit['id'],status='INVALID',error=traceback.format_exc())
                finally:signal.setitimer(signal.ITIMER_REAL,0)
            row['seconds']=time.monotonic()-t;counts[row['status']]+=1
            if row['status']=='SUCCESS':
                stats['states']+=row['states'];stats['positive' if row['clique'] else 'negative']+=1
                stats['compiler_checked']+=unit['compiler_selected']
                stats['trivial_negative']+=unit['trivial_negative']
            raw.write(json.dumps(row,separators=(',',':'))+'\n');raw.flush()
    result=dict(utc=now(),units=len(units),status_counts={s:counts[s] for s in
                ['SUCCESS','FAILURE','TIMEOUT','INVALID','NOT_RUN']},stats=dict(stats),
                seconds=time.monotonic()-start,raw_sha256=sha(ROOT/'RAW.jsonl'))
    save('SUMMARY.json',result);print(json.dumps(result,indent=2))


if __name__=='__main__':{'generate':generate,'run':run}[sys.argv[1]]()
