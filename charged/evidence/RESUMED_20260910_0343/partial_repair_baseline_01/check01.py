from pathlib import Path
from fractions import Fraction as F
from functools import lru_cache
import datetime,hashlib,itertools,json,math,time,traceback
D=Path(__file__).resolve().parent;O=D/'run01';O.mkdir();start=time.monotonic()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def enc(x):return 'infinity' if x==math.inf else str(x)
def div(n,d):return n/d if d else (F(1) if not n else math.inf)
write(O/'INPUT_RECEIPT.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'plan_sha256':sha(D/'PLAN.md'),'script_sha256':sha(Path(__file__)),'status':'FIXED_BEFORE_COMPUTATION','expected_instances':1046,'expected_rows':20920,'input':'all nonempty footprint families m1..3, weights {1,2}^m, q1..4, mu0,1/2,1,2,4','hand_derived_hypotheses_already_observed':True})

def geometry(weights,footprints):
    work={mask:sum(w for j,w in enumerate(weights) if mask>>j&1) for mask in range(1<<len(weights))}
    minimum={0:0};frontier={0}
    while frontier:
        nxt={mask|f for mask in frontier for f in footprints}-minimum.keys()
        cost=1+max(minimum[x] for x in frontier)
        for x in nxt:minimum[x]=cost
        frontier=nxt
    dirty=tuple(sorted(minimum));G=[max(work[x] for x in dirty if minimum[x]<=b) for b in range(4*len(weights)+1)]
    return work,minimum,dirty,G

def solve(weights,footprints,q,mu,tree_check=False):
    work,c,dirty,G=geometry(weights,footprints);m=len(weights)
    ratios={(e,d):div(mu+work[d],mu+G[(e+c[d])//q]) for e in range(q*m+1) for d in dirty if e+c[d]<=q*m}
    actions={}
    @lru_cache(None)
    def v(left,e):
        values=[]
        for d in dirty:
            accept=ratios[e,d];retry=v(left-1,e+c[d]) if left>1 and d else math.inf
            actions[left,e,d]='accept' if accept<=retry else 'retry'
            values.append(min(accept,retry))
        return max(values)
    @lru_cache(None)
    def fixed(left,e):
        return max(fixed(left-1,e+c[d]) if d and left>1 else ratios[e,d] for d in dirty)
    best=v(q,0);retry_value=fixed(q,0)
    profile=max(div(mu+G[max(b-(q-1),0)],mu+G[b//q]) for b in range(q*m+1))
    raw_tree=None
    if tree_check:
        # No e state quotient or memoization: reconstruct each observed history independently.
        def tree(history):
            costs=[]
            for observed in dirty:
                h=history+(observed,);spent=sum(c[x] for x in h)
                a=div(mu+work[observed],mu+G[spent//q])
                b=tree(h) if len(h)<q and observed else math.inf
                costs.append(min(a,b))
            return max(costs)
        raw_tree=tree(())
    return best,retry_value,profile,raw_tree,actions,(work,c,dirty,G)

instances=rows=tree_rows=0;failures=[];strict=0;witnesses=[];zero_rows=0;enum=[]
try:
    with (O/'outcomes.jsonl').open('x') as f:
        for m in [1,2,3]:
            universe=tuple(range(1,1<<m))
            for selected in range(1,1<<len(universe)):
                footprints=tuple(x for j,x in enumerate(universe) if selected>>j&1)
                for weights in itertools.product([1,2],repeat=m):
                    instances+=1
                    for q in [1,2,3,4]:
                        for mu in [F(0),F(1,2),F(1),F(2),F(4)]:
                            if time.monotonic()-start>170:raise TimeoutError('internal 170-second cap')
                            best,retry,formula,tree,actions,geo=solve(weights,footprints,q,mu,m<=2)
                            good=best<=retry and retry==formula and (tree is None or tree==best)
                            if not mu:good=good and best==retry and best<=q;zero_rows+=1
                            if tree is not None:tree_rows+=1
                            row={'m':m,'weights':weights,'footprints':footprints,'q':q,'mu':str(mu),'optimal_competitive_ratio':enc(best),'retry_first_ratio':enc(retry),'retry_profile_formula':enc(formula),'history_tree_ratio':enc(tree) if tree is not None else None,'PASS':bool(good)}
                            if not good:failures.append(row)
                            if best<retry:
                                strict+=1
                                if len(witnesses)<3:witnesses.append(dict(row,policy=[{'left':a,'observable_minimum_spent':b,'dirty':c,'action':x} for (a,b,c),x in sorted(actions.items())]))
                            f.write(json.dumps(row,separators=(',',':'))+'\n');rows+=1
            print(json.dumps({'m_complete':m,'instances':instances,'rows':rows,'strict_improvements':strict,'failures':len(failures),'seconds':time.monotonic()-start}),flush=True)
    # Exhaust all 2^(3+3*3)=4096 deterministic canonical policy trees, with zero-dirty acceptance and final-call repair dominant.
    weights=(1,2);footprints=(1,2);q=3
    for mu in [F(1,2),F(2)]:
        best,_,_,_,_,(work,c,dirty,G)=solve(weights,footprints,q,mu)
        minimum=math.inf;best_bits=[]
        for bits in range(1<<12):
            def cost(history):
                worst=F(0)
                for d in dirty:
                    h=history+(d,);e=sum(c[x] for x in h)
                    index=d-1 if not history else 3+(history[0]-1)*3+(d-1)
                    accept=(d==0 or len(h)==q or ((bits>>index)&1)==0)
                    value=div(mu+work[d],mu+G[e//q]) if accept else cost(h)
                    worst=max(worst,value)
                return worst
            val=cost(())
            if val<minimum:minimum=val;best_bits=[bits]
            elif val==minimum:best_bits.append(bits)
        e={'weights':weights,'footprints':footprints,'q':q,'mu':str(mu),'policies_enumerated':4096,'best':enc(minimum),'compiler':enc(best),'best_policy_count':len(best_bits),'best_policy_first_bits':best_bits[:10],'PASS':minimum==best};enum.append(e)
        if minimum!=best:failures.append(e)
    examples=[]
    for mu in [F(0),F(1,2),F(1),F(2),F(4)]:
        best,retry,formula,tree,actions,geo=solve((1,1,1),(1,2,4),3,mu,True)
        examples.append({'m':3,'weights':[1,1,1],'footprints':[1,2,4],'q':3,'mu':str(mu),'optimal_ratio':enc(best),'retry_ratio':enc(retry),'history_tree':enc(tree),'policy':[{'left':a,'observable_minimum_spent':b,'dirty':c,'action':x} for (a,b,c),x in sorted(actions.items())]})
    controls=[{'name':'mu_zero_threshold_loss_detected','detected':zero_rows==4184}, {'name':'positive_common_cost_does_change_optimum','detected':strict>0}, {'name':'omitting_common_cost_detected','detected':examples[0]['optimal_ratio']!=examples[-1]['optimal_ratio']}, {'name':'fixed_retry_optimal_for_positive_mu_false','detected':any(x['optimal_ratio']!=x['retry_ratio'] for x in examples)}, {'name':'hidden_write_count_not_policy_input','detected':all(set(x)=={'left','observable_minimum_spent','dirty','action'} for y in examples for x in y['policy'])}]
    if not all(x['detected'] for x in controls):failures.append({'control_failure':controls})
    write(O/'WITNESSES.json',witnesses);write(O/'SINGLETON_EXAMPLES.json',examples);write(O/'EXHAUSTIVE_POLICIES.json',enum);write(O/'FAILURES.json',failures)
    write(O/'RECEIPT.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS' if not failures and rows==20920 else 'FAIL','instances':instances,'rows':rows,'history_tree_rows':tree_rows,'zero_mu_rows':zero_rows,'strict_improvement_rows':strict,'exhaustive_policy_runs':enum,'controls':controls,'failures':len(failures),'seconds':time.monotonic()-start,'outputs_sha256':{p.name:sha(p) for p in O.glob('*.json*') if p.name!='RECEIPT.json'},'scope':'finite exact arithmetic exploration, not a native application cost calibration or mechanical proof'})
    print((O/'RECEIPT.json').read_text(),flush=True)
except BaseException as e:
    write(O/'FAILURE_RECEIPT.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'TIMEOUT' if isinstance(e,TimeoutError) else 'ERROR','error':repr(e),'traceback':traceback.format_exc(),'instances':instances,'rows':rows,'failures':failures,'seconds':time.monotonic()-start});raise
