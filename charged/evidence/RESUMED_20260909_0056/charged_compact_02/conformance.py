from pathlib import Path
import copy,datetime,hashlib,json,os,signal,subprocess,sys,time,traceback
import compact,verify
from runtime import Policy

HERE=Path(__file__).resolve().parent
DEST=HERE/'conformance01'
STOP=datetime.datetime(2026,9,9,4,50,tzinfo=datetime.timezone.utc).timestamp()
CONTROL_IDS=['unchanged_compact','original_baseline','effective_price','lost_original_edge','wrong_order','threshold','root_area','positive_delta','entry_tag','bool_entry','external_input','unchanged_general','general_alias','general_price','general_input','duplicate_json','cyclic_input','wrong_runtime_tag','cached_failure_transition','protected_failure','external_bool','external_float','backend_bool_edge','backend_float_edge','unchanged_mixed','mixed_wrong_t','mixed_wrong_P','mixed_noneligible','mixed_runtime_caps']

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):
    with p.open('x') as f:json.dump(x,f,indent=2);f.write('\n')
def prepare():
    inputs=json.loads((DEST/'INPUTS.json').read_text());assert len(inputs)==19485
    paths=list(HERE.glob('*.py'))+list((HERE/'inherited').rglob('*.py'))+[HERE/'PLAN.md',DEST/'INPUTS.json',DEST/'INPUT_BINDING.json']
    paths+=[HERE.parent/'charged_curves_02'/x for x in ['compiler.py','basis.py','checker.py']]
    paths.append(HERE.parent.parent/'RESUMED_20260907_1942/dependency_curves_01/curves.py')
    save(DEST/'MANIFEST.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),inputs=len(inputs),controls=CONTROL_IDS,control_base=dict(jobs=[[3,2,0,0,0],[1,1,1,3,1]],edges=[]),control_compatible_chain=dict(jobs=[[1,1,0,2,2],[2,2,0,2,2]],edges=[[0,1]]),control_general=dict(jobs=[[w,w,0,5,6] for w in [1,1,1,2]],edges=[]),sources={str(p):sha(p) for p in paths},per_input_seconds=5,campaign_seconds=300,parent_seconds=320,policy_budgets=list(range(5)),all_inputs_previously_observed=False,previously_observed_inputs=15727,fresh_inputs=3758))

def profile(data):
    if data['route']=='charged_all_ideals':return [tuple(r) for r in data['backend']['curves'][str(data['backend']['full'])]]
    rows=[];x=y=0
    for slope,count in data['backend']['value_slopes']:rows.append((x,y,slope));x+=count;y+=slope*count
    rows.append((x,y,0));return rows

def policy_check(policy):
    from functools import lru_cache
    branches=0
    @lru_cache(None)
    def worst(kind,x,b):
        nonlocal branches
        state=dict(kind=kind,value=x);chosen=policy.choose(b,state)
        if chosen is None:return 0
        i=chosen['job'];mode=chosen['mode'];w,p,g,v,r=policy.jobs[i]
        expected_call='fresh_callback' if mode=='protected' else 'cached_callback' if mode=='cached' else 'conditional_commit' if v<=g+r else 'validation_callback'
        assert chosen['call']==expected_call
        outcomes=['success']+(['failure'] if b and mode!='protected' else [])
        totals=[]
        for outcome in outcomes:
            actual=policy.advance(b,state,mode,outcome)
            completed=mode in ('cached','protected') or outcome=='success'
            nx=x if not completed else x+1 if kind=='cursor' else x^(1<<i)
            nb=b-(outcome=='failure')
            paid=w+p+g+r if mode=='protected' else w+min(v,g+r) if mode=='cheap' else w+g+r+(w+p if outcome=='failure' else 0)
            assert actual==dict(state=dict(kind=kind,value=nx),budget=nb,charged_cost=paid,completed_job=i if completed else None)
            totals.append(paid+worst(kind,nx,nb));branches+=1
        result=max(totals);assert result==policy.total(b,state)
        return result
    result=[worst(policy.entry['kind'],policy.entry['value'],b) for b in range(5)]
    return result,branches

def controls():
    m=json.loads((DEST/'MANIFEST.json').read_text());base=m['control_base'];chain=m['control_compatible_chain'];general=m['control_general']
    good=verify.loads(json.dumps(compact.compile_case(base)));ordered=verify.loads(json.dumps(compact.compile_case(chain)));full=verify.loads(json.dumps(compact.compile_case(general)))
    typed_case=dict(jobs=[[1,2,0,0,0],[2,3,0,0,0]],edges=[[0,1]])
    typed=verify.loads(json.dumps(compact.compile_case(typed_case,force_general=True)))
    mixed=verify.loads(json.dumps(compact.compile_case(dict(jobs=[[1,0,0,5,10]],edges=[]))))
    results=[]
    for name in CONTROL_IDS:
        artifact=copy.deepcopy(full if name.startswith('general_') or name=='unchanged_general' else ordered if name in ('lost_original_edge','wrong_order') else good)
        expected=name in ['unchanged_compact','unchanged_general','cached_failure_transition']
        external=None
        if name in ('external_bool','external_float','backend_bool_edge','backend_float_edge'):
            artifact=copy.deepcopy(typed);external=copy.deepcopy(typed_case)
            if name=='external_bool':external['jobs'][0][0]=True
            elif name=='external_float':external['jobs'][0][0]=1.0
            elif name=='backend_bool_edge':artifact['backend']['input']['edges']=[[False,True]]
            else:artifact['backend']['input']['edges']=[[0,1.0]]
        if name.startswith('mixed_') or name=='unchanged_mixed':
            artifact=copy.deepcopy(mixed);expected=name in ('unchanged_mixed','mixed_runtime_caps')
            if name=='mixed_wrong_t':artifact['backend']['input']['cp'][0][0]=1
            elif name=='mixed_wrong_P':artifact['backend']['input']['cp'][0][1]=0
            elif name=='mixed_noneligible':artifact['input']['jobs'][0][1]=1
        if name=='original_baseline':artifact['baseline']+=1
        elif name=='effective_price':artifact['backend']['input']['cp'][0][0]+=1
        elif name=='lost_original_edge':artifact['backend']['input']['edges']=[]
        elif name=='wrong_order':artifact['backend']['order'].reverse()
        elif name=='threshold':artifact['backend']['protect_at_budget'][0]+=1
        elif name=='root_area':artifact['backend']['value_slopes'][0][1]+=1
        elif name=='positive_delta':artifact['input']['jobs'][1][3]=0
        elif name=='entry_tag':artifact['entry']['kind']='mask'
        elif name=='bool_entry':artifact['entry']['value']=False
        elif name=='external_input':external=copy.deepcopy(base);external['jobs'][0][0]+=1
        elif name=='general_alias':artifact['backend']['curves']['01']=copy.deepcopy(artifact['backend']['curves']['1'])
        elif name=='general_price':artifact['backend']['prices'][0][0]+=1
        elif name=='general_input':artifact['backend']['input']['jobs'][0][0]+=1
        try:
            if name=='mixed_runtime_caps':
                policy=Policy(artifact);assert policy.total(0)==6 and policy.total(1)==11 and policy.premium_caps==(5,0)
            elif name=='duplicate_json':verify.loads('{"x":1,"x":2}')
            elif name=='cyclic_input':compact.compile_case(dict(jobs=chain['jobs'],edges=[[0,1],[1,0]]))
            elif name in ('wrong_runtime_tag','cached_failure_transition','protected_failure'):
                policy=Policy(artifact)
                if name=='wrong_runtime_tag':policy.choose(1,dict(kind='mask',value=0))
                elif name=='protected_failure':policy.advance(100,policy.entry,'protected','failure')
                else:
                    first=policy.choose(1);assert first['mode']=='cached' and first['job']==1
                    next_state=policy.advance(1,policy.entry,'cached','failure')
                    assert next_state['state']==dict(kind='cursor',value=1) and next_state['budget']==0 and next_state['completed_job']==1
                    assert next_state['charged_cost']+policy.total(0,next_state['state'])==8
            else:verify.check(artifact,external)
            actual=True;error=None
        except Exception:actual=False;error=traceback.format_exc()
        results.append(dict(id=name,expected_accept=expected,accepted=actual,met=expected==actual,artifact=artifact,error=error))
    return results

def worker():
    m=json.loads((DEST/'MANIFEST.json').read_text());assert all(sha(Path(p))==h for p,h in m['sources'].items())
    save(DEST/'RUN_STARTED.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),manifest_sha256=sha(DEST/'MANIFEST.json')))
    base=compact.general_constructor().compiler;started=time.monotonic();rows=[]
    def expiry(*args):raise TimeoutError('fixed limit')
    signal.signal(signal.SIGALRM,expiry)
    with (DEST/'RAW.jsonl').open('x') as raw:
        for item in json.loads((DEST/'INPUTS.json').read_text()):
            left=min(300-(time.monotonic()-started),STOP-time.time());row=dict(id=item['id'])
            if left<=0:row['status']='NOT_RUN'
            else:
                signal.setitimer(signal.ITIMER_REAL,min(5,left))
                try:
                    case=item['case'];artifact=verify.loads(json.dumps(compact.compile_case(case)));checked=verify.check(artifact,case)
                    reference=base.compile_case(case);assert profile(artifact)==reference['curves'][reference['full']]
                    policy=Policy(artifact,case);costs,branches=policy_check(policy)
                    assert costs==[artifact['baseline']+base.base.at(reference['curves'][reference['full']],b) for b in range(5)]
                    row.update(status='SUCCESS',route=artifact['route'],whole_profile=profile(artifact),policy_totals=costs,policy_branches=branches,check=checked)
                except TimeoutError as e:row.update(status='TIMEOUT',error=str(e))
                except Exception:row.update(status='FAILURE',error=traceback.format_exc())
                finally:signal.setitimer(signal.ITIMER_REAL,0)
            rows.append(row);raw.write(json.dumps(row,separators=(',',':'))+'\n');raw.flush()
            if row['status']!='SUCCESS' and not (DEST/'FIRST_ADVERSE.json').exists():save(DEST/'FIRST_ADVERSE.json',dict(input=item,result=row))
    controls_rows=controls();save(DEST/'CONTROLS.json',controls_rows)
    summary=dict(inputs=len(rows),statuses={s:sum(r['status']==s for r in rows) for s in ['SUCCESS','FAILURE','TIMEOUT','NOT_RUN']},routes={s:sum(r.get('route')==s for r in rows) for s in ['compatible_reduced','charged_all_ideals']},policy_branches=sum(r.get('policy_branches',0) for r in rows),controls=len(controls_rows),controls_met=sum(r['met'] for r in controls_rows),seconds=time.monotonic()-started,author_constructed_population=True,previously_observed_inputs=15727)
    save(DEST/'SUMMARY.json',summary);print(json.dumps(summary,indent=2))
def run():
    with (DEST/'stdout.txt').open('xb') as f,(DEST/'stderr.txt').open('xb') as e:
        p=subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),'worker'],stdout=f,stderr=e,start_new_session=True)
        try:code=p.wait(timeout=min(320,STOP-time.time()))
        except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);code=p.wait()
    save(DEST/'PROCESS.json',dict(returncode=code))
    if (DEST/'SUMMARY.json').exists():print((DEST/'SUMMARY.json').read_text())
    else:raise RuntimeError('no completed summary')

if __name__=='__main__':{'prepare':prepare,'worker':worker,'run':run}[sys.argv[1]]()
