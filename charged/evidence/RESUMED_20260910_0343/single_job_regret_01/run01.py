from pathlib import Path
from functools import lru_cache
import datetime,hashlib,json,time,resource

HERE=Path(__file__).resolve().parent

def informed_game(w,k,b,remaining_calls):
    @lru_cache(None)
    def visit(b,c):
        if c==0:return float('inf')
        # Nature may spend no write or one fresh write after the mode is chosen.
        fresh=k+w
        cached=max([k]+([k+w] if b else []))
        cheap=max([k]+([k+visit(b-1,c-1)] if b else []))
        return min(fresh,cached,cheap)
    return visit(b,remaining_calls)

def policy_paths(w,k,cheap_failures,finish,b):
    # Enumerate terminal paths; no closed-form cost formula is used here.
    paths=[]
    def visit(f,left,cost,calls,used):
        if f==cheap_failures:
            if finish=='fresh':paths.append((cost+k+w,calls+1,used,'fresh'))
            elif finish=='cached':
                paths.append((cost+k,calls+1,used,'cached-match'))
                if left:paths.append((cost+k+w,calls+1,used+1,'cached-mismatch'))
            elif finish=='cheap-invalid':
                paths.append((cost+k,calls+1,used,'cheap-match'))
                if left:paths.append((float('inf'),calls+1,used+1,'noncompletion'))
            else:raise ValueError(finish)
            return
        paths.append((cost+k,calls+1,used,'cheap-match'))
        if left:visit(f+1,left-1,cost+k,calls+1,used+1)
    visit(0,b,0,0,0)
    return paths

def informed_formula(w,k,b,r):return k+min(b*k,w) if b<=r else k+w
def regret_formula(w,k,r):return min(max(w-k,0),r*k)

def validate(root,w,k,r):
    b=root['B']
    if root['known']!=informed_formula(w,k,b,r):return False
    for row in root['policies']:
        paths=policy_paths(w,k,row['cheap_failures'],row['finish'],b)
        if row['cost']!=max(p[0] for p in paths):return False
        if row['calls']!=max(p[1] for p in paths) or row['calls']>r+1:return False
    return True

def main():
    start=time.monotonic();out=HERE/'run01';out.mkdir()
    inputs=[dict(w=w,kappa=k,r=r,budgets=list(range(r+4))) for w in range(1,13) for k in range(13) for r in range(9)]
    (out/'INPUTS.json').write_text(json.dumps(inputs,separators=(',',':'))+'\n')
    names=['PLAN.md','PROOF_DRAFT.md','run01.py','run01/INPUTS.json']
    receipt=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),files=[dict(path=n,bytes=(HERE/n).stat().st_size,sha256=hashlib.sha256((HERE/n).read_bytes()).hexdigest()) for n in names],cap_seconds=120)
    (out/'INPUT_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
    totals=dict(SUCCESS=0,FAILURE=0,TIMEOUT=0,INVALID=0);failures=[];regret_rows=[];policy_values=0;invalid_policies=0;control_source=None
    with (out/'RAW.jsonl').open('x') as raw:
        for number,input in enumerate(inputs):
            w,k,r=input['w'],input['kappa'],input['r'];by_policy={(t,a):[] for t in range(r+1) for a in ['cached','fresh']}
            roots=[]
            for b in input['budgets']:
                row=dict(input=number,B=b,known=informed_game(w,k,b,r+1),policies=[])
                for (t,a),vec in by_policy.items():
                    paths=policy_paths(w,k,t,a,b);cost=max(p[0] for p in paths);vec.append(cost)
                    row['policies'].append(dict(cheap_failures=t,finish=a,cost=cost,calls=max(p[1] for p in paths),witness_writes=min(p[2] for p in paths if p[0]==cost)))
                    policy_values+=1
                if time.monotonic()-start>120:status='TIMEOUT'
                else:status='SUCCESS' if validate(row,w,k,r) else 'FAILURE'
                row['status']=status;totals[status]+=1;roots.append(row);raw.write(json.dumps(row,separators=(',',':'))+'\n')
                if status!='SUCCESS':failures.append(dict(input=number,B=b,status=status))
                if (w,k,r,b)==(5,1,2,3):control_source=(row,w,k,r)
            known=[row['known'] for row in roots]
            regrets={key:max(c-v for c,v in zip(vec,known)) for key,vec in by_policy.items()}
            optimum=min(regrets.values());expected=regret_formula(w,k,r)
            if optimum!=expected:failures.append(dict(input=number,kind='regret',observed=optimum,expected=expected))
            chosen=(0,'cached') if max(w-k,0)<=r*k else (r,'cached')
            if regrets[chosen]!=optimum:failures.append(dict(input=number,kind='selected-policy',chosen=chosen))
            invalid=policy_paths(w,k,r,'cheap-invalid',r+1)
            rejected=any(p[3]=='noncompletion' for p in invalid);assert rejected;invalid_policies+=1
            regret_rows.append(dict(input=number,w=w,kappa=k,r=r,minimax_regret=optimum,expected=expected,chosen=chosen,all_policy_regrets=[dict(cheap_failures=t,finish=a,regret=v,witness_B=[b for b,c,z in zip(input['budgets'],by_policy[(t,a)],known) if c-z==v]) for (t,a),v in regrets.items()],always_cheap_rejected_as_universally_inadmissible=rejected))
    # Corrupt independently checked outputs; retain each detected control.
    source,w,k,r=control_source;controls=[]
    for kind in ['comparator','policy-cost','call-cap']:
        row=json.loads(json.dumps(source))
        if kind=='comparator':row['known']+=1
        elif kind=='policy-cost':row['policies'][0]['cost']+=1
        else:row['policies'][0]['calls']=r+2
        controls.append(dict(kind=kind,detected=not validate(row,w,k,r)))
    row=next(x for x in regret_rows if (x['w'],x['kappa'],x['r'])==(5,1,2))
    controls.append(dict(kind='claimed-regret',detected=row['minimax_regret']+1!=min(x['regret'] for x in row['all_policy_regrets'])))
    if not all(x['detected'] for x in controls):failures.append(dict(kind='control'))
    (out/'REGRET.json').write_text(json.dumps(regret_rows,separators=(',',':'))+'\n')
    summary=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='PASS' if not failures else 'FAIL',conditions=len(inputs),roots=sum(totals.values()),statuses=totals,policy_budget_values=policy_values,universally_inadmissible_always_cheap_policies_rejected=invalid_policies,controls=controls,failures=failures,seconds=time.monotonic()-start,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,new_native_runs=0,scope='Finite complete serial fresh-preparation one-job policy class; the general-program minimax claim requires the separate operation-level proof. All budgets beyond r are saturated for these policies and comparator.')
    (out/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2));return not failures

if __name__=='__main__':raise SystemExit(0 if main() else 1)
