from pathlib import Path
import collections, datetime, hashlib, json, random, signal, sys, time, traceback
import comparator, certificate

ROOT = Path(__file__).resolve().parent
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(name, data):
    with (ROOT / name).open('x') as f: json.dump(data, f, indent=2, sort_keys=True); f.write('\n')


def generate():
    units = []
    for u in json.loads((ROOT.parent/'final_evaluation_dag_01/INPUTS.json').read_text()):
        units.append(dict(id='semantic-'+u['id'], group='known_semantic', case=dict(cp=u['cp'],edges=u['edges'])))
    for u in json.loads((ROOT.parent/'dag_hardness_01/INPUTS.json').read_text()):
        units.append(dict(id='reduction-'+u['id'], group='known_reduction', case=u['case']))
    rng = random.Random(202609080435)
    for n in (4,5,6,7):
        for j in range(24):
            cp = [[rng.randint(1,100), rng.choice([0,rng.randint(1,200),(1<<40)+rng.randint(0,100)])] for _ in range(n)]
            edges = [[u,v] for u in range(n) for v in range(u+1,n) if rng.randrange(3)==0]
            perm = list(range(n)); rng.shuffle(perm)
            labeled = [None]*n
            for i,x in enumerate(cp): labeled[perm[i]]=x
            case = dict(cp=labeled,edges=sorted([[perm[u],perm[v]] for u,v in edges]))
            units.append(dict(id=f'new-n{n}-{j:02}',group='new_authored_relabel',case=case))
    assert len(units)==8634
    fixtures = [
        dict(id='interior-fast',case=dict(cp=[[20,10],[1,2]],edges=[]),starts=[0,5],protected=[1,0],K=10),
        dict(id='interior-fast-chain',case=dict(cp=[[20,10],[1,2],[2,1]],edges=[[1,2]]),starts=[0,4,6],protected=[1,0,0],K=10),
        dict(id='interior-zero-protected',case=dict(cp=[[20,10],[1,0],[2,1]],edges=[[1,2]]),starts=[0,4,6],protected=[1,1,0],K=10),
        dict(id='end-start-tie',case=dict(cp=[[30,4],[1,2],[30,5]],edges=[[0,1],[1,2]]),starts=[0,4,4],protected=[1,0,1],K=9)]
    save('DEV_INPUTS.json',units); save('EXTRACTION_INPUTS.json',fixtures)
    files = [ROOT/x for x in ['DEVELOPMENT_PLAN.md','PLAN_DRAFT.md','comparator.py','certificate.py','develop.py','DEV_INPUTS.json','EXTRACTION_INPUTS.json','REQUIREMENTS_FREEZE.txt']]
    files += [ROOT.parent/x/'INPUTS.json' for x in ['final_evaluation_dag_01','dag_hardness_01']]
    save('DEV_MANIFEST.json',dict(utc=now(),units=len(units),fixtures=len(fixtures),runtime=sys.executable,files=[dict(path=str(p),sha256=sha(p)) for p in files]))
    print('frozen',len(units),'semantic development units and',len(fixtures),'extraction fixtures')


def alarm(sig, frame): raise TimeoutError('fixed development cap')


def run():
    manifest=json.loads((ROOT/'DEV_MANIFEST.json').read_text())
    for f in manifest['files']: assert sha(f['path'])==f['sha256'], f['path']
    save('DEV_STARTED.json',dict(utc=now(),manifest_sha256=sha(ROOT/'DEV_MANIFEST.json')))
    fixture_rows=[]
    for f in json.loads((ROOT/'EXTRACTION_INPUTS.json').read_text()):
        order=comparator.extract(f['case'],f['starts'],f['protected'])
        report=certificate.scan(f['case'],order)
        assert report['value']<=f['K']
        fixture_rows.append(dict(id=f['id'],status='SUCCESS',certificate=order,report=report))
    case=dict(cp=[[1,1],[1,1]],edges=[[0,1]])
    mutants=[[[1,'F'],[0,'P']],[[0,'F'],[0,'P']],[[0,'F']],[[0,'Q'],[1,'P']]]
    for j,m in enumerate(mutants):
        try: certificate.scan(case,m)
        except AssertionError: fixture_rows.append(dict(id=f'malformed-{j}',status='REJECTED'))
        else: raise AssertionError(('accepted malformed',m))
    save('EXTRACTION_CONTROL_RAW.json',fixture_rows)
    units=json.loads((ROOT/'DEV_INPUTS.json').read_text()); start=time.monotonic()
    counts=collections.Counter();groups=collections.defaultdict(collections.Counter)
    signal.signal(signal.SIGALRM,alarm)
    with (ROOT/'DEV_RAW.jsonl').open('x') as raw:
        for u in units:
            before=time.monotonic();left=180-(before-start)
            if left<=0: row=dict(id=u['id'],group=u['group'],status='NOT_RUN',reason='campaign cap')
            else:
                signal.setitimer(signal.ITIMER_REAL,min(3,left))
                try:
                    row=dict(id=u['id'],group=u['group'],**comparator.solve(u['case'],seconds=1))
                    if row['status']=='SUCCESS':
                        v,cert,states=certificate.subset_dp(u['case'])
                        row.update(dp_value=v,dp_states=states,dp_certificate=cert)
                        assert row['value']==v,(row,v)
                except AssertionError: row=dict(id=u['id'],group=u['group'],status='FAILURE',error=traceback.format_exc())
                except TimeoutError: row=dict(id=u['id'],group=u['group'],status='TIMEOUT',error=traceback.format_exc())
                except Exception: row=dict(id=u['id'],group=u['group'],status='INVALID',error=traceback.format_exc())
                finally: signal.setitimer(signal.ITIMER_REAL,0)
            row['unit_seconds']=time.monotonic()-before
            counts[row['status']]+=1;groups[u['group']][row['status']]+=1
            raw.write(json.dumps(row,sort_keys=True,separators=(',',':'))+'\n');raw.flush()
    result=dict(utc=now(),units=len(units),status_counts=dict(counts),groups={k:dict(v) for k,v in groups.items()},seconds=time.monotonic()-start,raw_sha256=sha(ROOT/'DEV_RAW.jsonl'))
    save('DEV_SUMMARY.json',result); print(json.dumps(result,indent=2))

if __name__=='__main__': {'generate':generate,'run':run}[sys.argv[1]]()
