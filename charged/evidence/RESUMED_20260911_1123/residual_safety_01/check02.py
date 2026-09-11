import gzip, hashlib, itertools, json, random, time
from pathlib import Path
from online_filter import ResidualFilter
P=Path(__file__).resolve().parent
out=P/'check02'
out.mkdir(exist_ok=False)
start=time.time()
inputs={p.name: {'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in (P/'PROTOCOL02.md',P/'PROOF02.md',P/'online_filter.py',P/'check02.py')}
(out/'INPUTS.json').write_text(json.dumps(inputs,indent=2)+'\n')
(out/'START.json').write_text(json.dumps({'unix':start,'timeout_seconds':60})+'\n')
counts={k:0 for k in ['states','queries','allowed_actions','rejected_fresh','invalid_initial','stream_steps','invalid_arguments']}
errors=[]
def top(a,k): return sum(sorted(a,reverse=True)[:k])
def snap(f):return (f.k,f.protected,tuple(f.high),tuple(f.low),f.top_sum,f.completed_count)
def check(f,a,k,ell,context):
    expect=(k,ell,sorted(a),top(a,k),len(a),min(k,len(a)))
    actual=(f.k,f.protected,sorted(f.high+[-x for x in f.low]),f.top_sum,f.completed_count,len(f.high))
    if actual!=expect or (f.high and f.low and min(f.high)<max(-x for x in f.low)):
        errors.append({'context':context,'expected':expect,'actual':actual})
    if len(errors)>100:raise RuntimeError('100 discrepancies')
    if time.time()-start>60:raise TimeoutError('fixed60seconds')
def rejected(call,f=None):
    before=snap(f) if f else None
    try:call()
    except ValueError:pass
    else:errors.append({'not_rejected':counts.copy()})
    if f and snap(f)!=before:errors.append({'mutated_on_rejection':counts.copy()})
with gzip.open(out/'EXHAUSTIVE.jsonl.gz','wt') as raw:
  for n in range(5):
    for a in itertools.product((1,3,7),repeat=n):
      for k in range(n+3):
        cap=top(a,k)
        rejected(lambda:ResidualFilter(a,k,cap+1));counts['invalid_initial']+=1
        for ell in range(cap+1):
          f=ResidualFilter(a,k,ell);counts['states']+=1;check(f,a,k,ell,counts.copy())
          for w in (1,2,3,6,7,8,50):
            expected_cap=top(a+(w,),k);allow=ell+w<=expected_cap;before=snap(f)
            actual=(f.prospective_top(w),f.permits_fresh(w));counts['queries']+=1
            if actual!=(expected_cap,allow) or snap(f)!=before:errors.append({'query':counts.copy(),'actual':actual,'expected':(expected_cap,allow)})
            raw.write(json.dumps({'D':a,'k':k,'ell':ell,'w':w,'cap':expected_cap,'fresh':allow})+'\n')
            for outcome in ('fresh','match','mismatch'):
              g=ResidualFilter(a,k,ell)
              if outcome=='fresh' and not allow:
                rejected(lambda:g.complete(w,outcome),g);counts['rejected_fresh']+=1;continue
              g.complete(w,outcome);counts['allowed_actions']+=1
              check(g,a+(w,),k+(outcome=='mismatch'),ell+(w if outcome!='match' else 0),(counts.copy(),outcome))
rng=random.Random(202609111146)
with gzip.open(out/'STREAMS.jsonl.gz','wt') as raw:
 for sid in range(240):
  a=[rng.choice((1,2,7,31,100,10000)) for _ in range(sid%11)]
  k=rng.randrange(len(a)+3);ell=rng.randrange(top(a,k)+1);f=ResidualFilter(a,k,ell)
  raw.write(json.dumps({'stream':sid,'initial':{'D':a,'k':k,'ell':ell}})+'\n')
  for step in range(200):
   w=rng.choice((1,2,7,31,100,10000));cap=top(a+[w],k);allow=ell+w<=cap
   if (f.prospective_top(w),f.permits_fresh(w))!=(cap,allow):errors.append({'stream_query':(sid,step)})
   outcome=rng.choice(['match','mismatch']+(['fresh'] if allow else []))
   f.complete(w,outcome);a.append(w);k+=(outcome=='mismatch');ell+=(w if outcome!='match' else 0)
   check(f,a,k,ell,('stream',sid,step));counts['stream_steps']+=1
   raw.write(json.dumps({'stream':sid,'step':step,'w':w,'outcome':outcome,'k':k,'ell':ell,'top':f.top_sum})+'\n')
f=ResidualFilter()
for w in (0,-1,1.5,True):
 for call in (lambda w=w:f.permits_fresh(w),lambda w=w:f.complete(w,'match')):
  rejected(call,f);counts['invalid_arguments']+=1
for k,ell in ((-1,0),(0.5,0),(0,-1),(0,0.5)):
 rejected(lambda k=k,ell=ell:ResidualFilter((),k,ell));counts['invalid_arguments']+=1
for outcome in ('unknown','fresh'):
 rejected(lambda outcome=outcome:f.complete(1,outcome),f);counts['invalid_arguments']+=1
(out/'DISCREPANCIES.json').write_text(json.dumps(errors,indent=2)+'\n')
summary={'status':'SUCCESS' if not errors else 'FAIL','counts':counts,'discrepancies':len(errors),'elapsed_seconds':time.time()-start,'scope':'author data-structure implementation check, not general proof/native evaluation'}
(out/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
