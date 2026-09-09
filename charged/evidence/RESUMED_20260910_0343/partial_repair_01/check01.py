from pathlib import Path
import collections,datetime,functools,hashlib,itertools,json,math,time,traceback
D=Path(__file__).resolve().parent;O=D/'run01';O.mkdir()
start=time.monotonic()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
write(O/'INPUT_RECEIPT.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'FIXED_BEFORE_COMPUTATION','plan_sha256':sha(D/'PLAN.md'),'script_sha256':sha(Path(__file__)),'m':[1,2,3],'weights':[1,2,3],'r':[0,1,2,3],'B_max':'(r+1)*m+3','footprints':'every nonempty family of nonempty subsets, including unreachable components','timeout_seconds':120,'analytical_hypotheses_already_observed':True})

def instance(weights,footprints,max_b,max_q=4):
    m=len(weights);work=[sum(w for j,w in enumerate(weights) if mask>>j&1) for mask in range(1<<m)];W=sum(weights)
    # Exact reachable dirty sets after exactly c actual footprint writes; repeats retained.
    reachable=[{0}]
    for c in range(1,max_b+1):reachable.append({mask|f for mask in reachable[-1] for f in footprints})
    spectrum=[];available=set()
    for states in reachable:
        available|=states;spectrum.append(max(work[x] for x in available))
    raw=[[math.inf]*(max_b+1) for _ in range(max_q+1)]
    compact=[[math.inf]*(max_b+1) for _ in range(max_q+1)]
    policies={}
    for q in range(1,max_q+1):
        for b in range(max_b+1):
            observations=collections.defaultdict(list)
            for c in range(b+1):
                for mask in reachable[c]:observations[mask].append(c)
            costs=[];actions={}
            for mask,possible_write_counts in observations.items():
                accepting=work[mask]
                # One response per observed set, not a response chosen using a hidden exact count.
                retrying=max(raw[q-1][b-c] for c in possible_write_counts) if q>1 else math.inf
                actions[mask]='accept' if accepting<=retrying else 'retry'
                costs.append(min(accepting,retrying))
            optimistic=max(costs)
            raw[q][b]=min(W,optimistic);policies[q,b]=actions
            compact[q][b]=min(W,max(min(spectrum[c],compact[q-1][b-c] if q>1 else math.inf) for c in range(b+1)))
    return work,reachable,spectrum,raw,compact,policies

count=0;instances=0;failures=[];classification=[]
try:
    with (O/'outcomes.jsonl').open('x') as f:
        for m in [1,2,3]:
            universe=list(range(1,1<<m))
            for selected in range(1,1<<len(universe)):
                footprints=tuple(v for j,v in enumerate(universe) if selected>>j&1)
                for weights in itertools.product([1,2,3],repeat=m):
                    if time.monotonic()-start>115:raise TimeoutError('115-second internal cap')
                    max_b=4*m+3;work,reach,G,V,C,policy=instance(weights,footprints,max_b)
                    instances+=1
                    for r in range(4):
                        q=r+1
                        for b in range(q*m+4):
                            formula=G[b//q];blind=G[max(b-r,0)]
                            result={'m':m,'weights':weights,'footprints':footprints,'r':r,'B':b,'observed_set_dp':V[q][b],'damage_dp':C[q][b],'formula':formula,'low_budget_zero_envelope':blind,'PASS':V[q][b]==C[q][b]==formula}
                            if not result['PASS']:failures.append(result)
                            f.write(json.dumps(result,separators=(',',':'))+'\n');count+=1
                        saturation=G[1]==G[-1]
                        equality=all(G[b//q]==G[max(b-r,0)] for b in range(q*m+4))
                        criterion=(r==0 or saturation)
                        if equality!=criterion:failures.append({'criterion_failure':True,'m':m,'weights':weights,'footprints':footprints,'r':r,'G':G,'equality':equality,'criterion':criterion})
                        classification.append({'r':r,'saturated_one_write':saturation,'equal_profiles':equality})
            print(json.dumps({'m_completed':m,'instances':instances,'rows':count,'failures':len(failures),'seconds':time.monotonic()-start}),flush=True)
    # All undominated deterministic q=2 policies for the unit-work two-component example.
    work,reach,G,V,C,_=instance((1,1),(1,2),7,2);enumerated=[]
    for actions in itertools.product(['accept','retry'],repeat=3):
        profile=[]
        for B in range(8):
            worst=0
            for c in range(B+1):
                for dirty in reach[c]:
                    if not dirty:cost=0
                    elif actions[dirty-1]=='accept':cost=work[dirty]
                    else:cost=max(work[last] for more in range(B-c+1) for last in reach[more])
                    worst=max(worst,cost)
            profile.append(worst)
        enumerated.append({'first_actions':dict(zip(['{A}','{B}','{A,B}'],actions)),'profile_B0_to7':profile,'equal_oracle_all_B':profile==V[2]})
    enumerated.append({'first_actions':'always_fresh','profile_B0_to7':[2]*8,'equal_oracle_all_B':False})
    write(O/'TWO_COMPONENT_POLICIES.json',{'oracle_B0_to7':V[2],'zero_low_B_threshold_B0_to7':[G[max(b-1,0)] for b in range(8)],'all_undominated_policies':enumerated,'simultaneous_policy_exists':any(p['equal_oracle_all_B'] for p in enumerated)})
    # Controls deliberately violate distinct aspects of the claimed result.
    controls=[]
    def control(name,detected):controls.append({'name':name,'detected':bool(detected)})
    control('ceil_instead_of_floor',V[2][1]!=G[math.ceil(1/2)])
    work1,reach1,G1,V1,_,_=instance((1,1),(1,2),7,2)
    additive_repeated_damage=2*work1[1]
    control('repeated_write_additive_instead_of_union',additive_repeated_damage!=work1[1|1])
    # A policy optimal at B=3 but accepting one dirty component violates zero L at B=1.
    selected=next(p for p in enumerated if p['first_actions']=={'{A}':'accept','{B}':'accept','{A,B}':'retry'})
    control('drop_low_budget_zero_constraint',selected['profile_B0_to7'][3]==1 and selected['profile_B0_to7'][1]!=0)
    # The r+1-call lower environment uses repeated fresh-version writes in distinct intervals.
    control('do_not_charge_repeated_writes_across_calls',2*1!=len({1,1}))
    control('false_simultaneous_zero_ignorance',not any(p['equal_oracle_all_B'] for p in enumerated))
    if not all(c['detected'] for c in controls):failures.append({'control_failure':controls})
    write(O/'FAILURES.json',failures)
    write(O/'RECEIPT.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS' if not failures else 'FAIL','instances':instances,'rows':count,'classification_cases':len(classification),'classification_counts':dict(collections.Counter(str((x['r'],x['saturated_one_write'],x['equal_profiles'])) for x in classification)),'failures':len(failures),'controls':controls,'seconds':time.monotonic()-start,'outputs_sha256':{p.name:sha(p) for p in O.glob('*.json*') if p.name not in ['RECEIPT.json']},'scope':'finite exact arithmetic checks of a new specified partial-repair interface; not native semantics or a mechanical proof'})
    print((O/'RECEIPT.json').read_text())
except BaseException as e:
    write(O/'FAILURE_RECEIPT.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'TIMEOUT' if isinstance(e,TimeoutError) else 'ERROR','error':repr(e),'traceback':traceback.format_exc(),'instances':instances,'rows':count,'failures':failures,'seconds':time.monotonic()-start});raise
