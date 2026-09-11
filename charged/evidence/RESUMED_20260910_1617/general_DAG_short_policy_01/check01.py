from pathlib import Path
import datetime,hashlib,importlib.util,json,time
D=Path(__file__).resolve().parent
W=(62,83,15,84,30,31); EDGES=((1,2),(3,4),(4,5)); R=3
PRED=[0]*6
for i,j in EDGES:PRED[j]|=1<<i
TOP=[sum(sorted(W,reverse=True)[:k]) for k in range(7)]
def cap(d):return TOP[min(6,max(0,d-R))]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(name,v):
 with (D/name).open('x') as f:f.write(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def build(S=63,f=0,d=0,L=0,special=False,control=False):
 if time.monotonic()>DEADLINE:raise TimeoutError('10s fixed limit')
 if not S:return ('done',)
 ready=[i for i in range(6) if S>>i&1 and not PRED[i]&S]
 if f<R:i=min(ready,key=lambda i:W[i]);mode='cheap'
 elif special:
  i=next(i for i in (3,4,5,1,2) if S>>i&1)
  assert i in ready
  mode='fresh' if (i in (1,2) or control) and L+W[i]<=cap(d) else 'cached'
 else:i=min(ready,key=lambda i:W[i]);mode='cached'
 if mode=='fresh':return (mode,i,build(S^(1<<i),f,d,L+W[i],special,control))
 good=build(S^(1<<i),f,d,L,special,control)
 if mode=='cheap':bad=build(S,f+1,d+1,L,special or (f==2 and i==1),control)
 else:bad=build(S^(1<<i),f,d+1,L+W[i],special,control)
 return (mode,i,good,bad)
def inspect(tree):
 rows=[];violations=[]
 def walk(t,C,d,Q,total,locked,trace):
  if time.monotonic()>DEADLINE:raise TimeoutError('10s fixed limit')
  if locked>cap(d):violations.append(dict(kind='prefix_protection',d=d,L=locked,cap=cap(d),trace=trace))
  if t[0]=='done':
   assert C==63
   rows.append(dict(d=d,Q=Q,W=total,L=locked,trace=trace));return
  mode,i=t[:2];assert not C>>i&1 and PRED[i]&C==PRED[i]
  for bad in ([False] if mode=='fresh' else [False,True]):
   completed=not(mode=='cheap' and bad);nextC=C|(1<<i) if completed else C
   addW=W[i]*(2 if mode=='cached' and bad else 1);addL=W[i] if mode=='fresh' or mode=='cached' and bad else 0
   state=dict(mode=mode,job=i,outcome='bad' if bad else 'fresh' if mode=='fresh' else 'match',d=d+int(bad),Q=Q+1,W=total+addW,L=locked+addL)
   walk(t[3 if bad else 2],nextC,d+int(bad),Q+1,total+addW,locked+addL,trace+[state])
 walk(tree,0,0,0,0,0,[])
 wc=[max(x['W'] for x in rows if x['d']<=b) for b in range(10)]
 lc=[max(x['L'] for x in rows if x['d']<=b) for b in range(10)]
 return dict(W=wc,L=lc,paths=len(rows),maximum_Q=max(x['Q'] for x in rows),prefix_violations=violations),rows
if __name__=='__main__':
 start=time.monotonic();DEADLINE=start+10
 old=D.parent/'joint_work_general_r_01/unknown02.py';spec=importlib.util.spec_from_file_location('U',old);U=importlib.util.module_from_spec(spec);spec.loader.exec_module(U);U.DEADLINE=DEADLINE
 put('START01.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),input=dict(w=W,edges=EDGES,r=R),hashes={p.name:sha(p) for p in [Path(__file__),D/'PROTOCOL01.md',old]},reference_sha256=sha(D.parent/'general_DAG_followup_01/RESULT07.json'),cap_seconds=10))
 out=[]
 try:
  for control in (False,True):
   name='control' if control else 'candidate';tree=build(control=control);got,rows=inspect(tree)
   put(name+'_TREE01.json',tree)
   with (D/(name+'_PATHS01.jsonl')).open('x') as f:
    for row in rows:f.write(json.dumps(row,separators=(',',':'))+'\n')
   try:other=U.interpret(tree,W,PRED,R);agreement=all(other[k]==got[k] for k in ['W','L','paths','maximum_Q'])
   except Exception as e:other=dict(error=repr(e));agreement=False
   got.update(name=name,independent_interpreter=other,interpreter_agreement=agreement,B7_maximizer=next(x for x in rows if x['d']<=7 and x['W']==got['W'][7]),expected_work_bound_satisfied=got['W'][7]<=752)
   out.append(got)
   if not control:assert agreement and got['maximum_Q']<=9 and not got['prefix_violations'] and got['L']==[cap(b) for b in range(10)] and got['W'][7]==752
  status='SUCCESS' if not out[1]['expected_work_bound_satisfied'] else 'NEGATIVE_CONTROL_NOT_DETECTED'
 except Exception as e:status='TIMEOUT' if isinstance(e,TimeoutError) else 'FAILURE';out.append(dict(error=repr(e)))
 ref=json.loads((D.parent/'general_DAG_followup_01/RESULT07.json').read_text())[0]['full'][0]['W']
 put('SUMMARY01.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status=status,policies=out,reference_curve=ref,retrospective_curve_equality=bool(out and out[0].get('W')==ref),seconds=time.monotonic()-start,new_independent_inputs=0,new_native_measurements=0,all_program_unrestricted_optimality_claim=False))
 print(json.dumps(dict(status=status,policies=[{k:v for k,v in x.items() if k not in ['B7_maximizer','prefix_violations','independent_interpreter']} for x in out]),indent=2));raise SystemExit(status!='SUCCESS')
