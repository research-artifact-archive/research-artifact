from pathlib import Path
import collections,copy,datetime,hashlib,json,signal,sys,time,traceback
import comparator,checker
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(name,data):
    with (ROOT/name).open('x') as f:json.dump(data,f,indent=2,sort_keys=True);f.write('\n')
def generate():
    units=[]
    for u in json.loads((ROOT.parent/'final_evaluation_dag_01/INPUTS.json').read_text()):
        units.append(dict(id='semantic-'+u['id'],group='known_semantic',case=dict(cp=u['cp'],edges=u['edges'])))
    for u in json.loads((ROOT.parent/'b1_constraint_comparator_01/DEV_INPUTS.json').read_text()):
        if u['group']=='new_authored_relabel':units.append(dict(id=u['id'],group='known_relabel',case=u['case']))
    for k in [1,2,7,101,1<<40]:
        units.append(dict(id=f'family-{k}',group='selected_family',case=dict(cp=[[3*k,2*k],[7*k,2*k],[5*k,6*k],[k,2*k]],edges=[[0,1],[0,2],[1,3]])))
    for name,case in [('empty',dict(cp=[],edges=[])),('zero-premium',dict(cp=[[1,0],[3,0]],edges=[[0,1]])),('repeat-failure',dict(cp=[[1,3]],edges=[]))]:
        units.append(dict(id=name,group='explicit_control',case=case))
    assert len(units)==4336;save('DEV_INPUTS.json',units)
    files=[ROOT/x for x in ['PLAN_PROOF.md','comparator.py','checker.py','develop.py','DEV_INPUTS.json']]
    files += [ROOT.parent/x for x in ['final_evaluation_dag_01/INPUTS.json','b1_constraint_comparator_01/DEV_INPUTS.json','b1_constraint_comparator_01/REQUIREMENTS_FREEZE.txt','b1_constraint_comparator_01/B2_AUTHOR_PROOF_CHECK_RAW.json']]
    save('DEV_MANIFEST.json',dict(utc=now(),units=len(units),runtime=sys.executable,files=[dict(path=str(p),sha256=sha(p)) for p in files]));print('frozen',len(units),'B2developmentunits')
def alarm(sig,frame):raise TimeoutError('fixed development cap')
def run():
    m=json.loads((ROOT/'DEV_MANIFEST.json').read_text())
    for f in m['files']:assert sha(f['path'])==f['sha256'],f['path']
    save('DEV_STARTED.json',dict(utc=now(),manifest_sha256=sha(ROOT/'DEV_MANIFEST.json')))
    repeated=dict(schema='specified-budget-contingent-order-v1',budget=2,root=[[0,'F']],branches={'0':[[0,'F']]})
    assert checker.check(dict(cp=[[1,3]],edges=[]),repeated)['value']==2
    chain=dict(schema='specified-budget-contingent-order-v1',budget=2,root=[[0,'F'],[1,'F']],branches={'0':[[0,'F'],[1,'F']],'1':[[1,'F']]})
    cc=dict(cp=[[2,4],[3,5]],edges=[[0,1]]);assert checker.check(cc,chain)['value']==6
    mutants=[]
    x=copy.deepcopy(chain);x['branches']['0']=[[1,'F']];mutants.append(x)
    x=copy.deepcopy(chain);x['branches']['0'].reverse();mutants.append(x)
    x=copy.deepcopy(chain);x['branches']['1']=[[0,'F'],[1,'F']];mutants.append(x)
    x=copy.deepcopy(chain);del x['branches']['0'];mutants.append(x)
    results=[]
    for j,x in enumerate(mutants):
        try:checker.check(cc,x)
        except AssertionError:results.append(dict(id=j,status='REJECTED'))
        else:raise AssertionError(('accepted malformed',x))
    save('CONTROL_RAW.json',dict(repeated_failure_value=2,chain_value=6,mutants=results))
    units=json.loads((ROOT/'DEV_INPUTS.json').read_text());start=time.monotonic();counts=collections.Counter();groups=collections.defaultdict(collections.Counter)
    signal.signal(signal.SIGALRM,alarm)
    with (ROOT/'DEV_RAW.jsonl').open('x') as raw:
        for u in units:
            before=time.monotonic();left=180-(before-start)
            if left<=0:row=dict(id=u['id'],group=u['group'],status='NOT_RUN')
            else:
                signal.setitimer(signal.ITIMER_REAL,min(3,left))
                try:
                    row=dict(id=u['id'],group=u['group'],**comparator.solve(u['case'],budget=2,seconds=1))
                    if row['status']=='SUCCESS':
                        value,states=checker.scalar(u['case'],2);row.update(scalar_value=value,scalar_states=states)
                        assert row['value']==value,(row,value)
                except AssertionError:row=dict(id=u['id'],group=u['group'],status='FAILURE',error=traceback.format_exc())
                except TimeoutError:row=dict(id=u['id'],group=u['group'],status='TIMEOUT',error=traceback.format_exc())
                except Exception:row=dict(id=u['id'],group=u['group'],status='INVALID',error=traceback.format_exc())
                finally:signal.setitimer(signal.ITIMER_REAL,0)
            row['unit_seconds']=time.monotonic()-before;counts[row['status']]+=1;groups[u['group']][row['status']]+=1
            raw.write(json.dumps(row,sort_keys=True,separators=(',',':'))+'\n');raw.flush()
    summary=dict(utc=now(),units=len(units),counts=dict(counts),groups={k:dict(v) for k,v in groups.items()},seconds=time.monotonic()-start,raw_sha256=sha(ROOT/'DEV_RAW.jsonl'))
    save('DEV_SUMMARY.json',summary);print(json.dumps(summary,indent=2))
if __name__=='__main__':{'generate':generate,'run':run}[sys.argv[1]]()
