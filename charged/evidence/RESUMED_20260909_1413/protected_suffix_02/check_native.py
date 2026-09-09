from pathlib import Path
from collections import Counter,defaultdict
import argparse,copy,hashlib,json,sys
from study import vectors,tail
D=Path(__file__).resolve().parent

def check(row,unit):
 w=unit['works'];n=len(w);done=set();outputs=[0]*n;versions=[0]*n;t=unit['r'];h=ell=0;at=W=L=0;prefix=[0]
 for value in sorted(w,reverse=True):prefix.append(prefix[-1]+value)
 pred=[[] for _ in w]
 for u,v in unit['edges']:pred[v].append(u)
 for x in pred:x.sort()
 def kernel(job,inside,version):
  nonlocal at,W,L
  k=row['kernels'][at];at+=1;parents=[outputs[x] for x in pred[job]]
  assert (k['job'],k['inside'],k['input_version'],k['parents'],k['iterations'])==(job,inside,version,parents,w[job]),'kernel input/iteration'
  mask=(1<<64)-1;value=17+31*job+104729*version
  for parent in parents:value^=parent&mask
  for _ in range(w[job]):value=((((value<<13)&mask)|(value>>51))*6364136223846793005+1442695040888963407)&mask
  if value>>63:value-=1<<64
  assert k['output']==value,'kernel output';W+=w[job];L+=w[job] if inside else 0;return value
 assert row['status']=='SUCCESS' and row['error']=='','native status'
 for field in ['id','case','r','budget_tag','policy','path']:assert row[field]==unit[field],'input binding'
 assert len(row['calls'])==len(unit['path']),'path length'
 for call,letter in zip(row['calls'],unit['path']):
  remaining=set(range(n))-done;ready=[i for i in remaining if all(p in done for p in pred[i])];i=min(ready,key=lambda i:(w[i],i))
  suffix=sorted([w[j] for j in remaining if j!=i],reverse=True);sums=[0]
  for x in suffix:sums.append(sums[-1]+x)
  safe=all(ell+w[i]+x<=prefix[min(h+k,n)] for k,x in enumerate(sums))
  mode='cheap' if t else 'fresh' if unit['policy']=='tail' and ell+sum(w[j] for j in remaining)<=prefix[min(h,n)] or unit['policy']=='certificate' and safe else 'cached'
  assert (call['job'],call['mode'],call['outcome'])==(i,mode,letter),'selector/job/outcome'
  assert (letter=='P')==(mode=='fresh'),'fresh path'
  value=kernel(i,False,versions[i]) if mode!='fresh' else None
  if letter=='F':versions[i]+=1
  if mode=='fresh' or mode=='cached' and letter=='F':value=kernel(i,True,versions[i]);ell+=w[i]
  failed=mode=='cheap' and letter=='F';assert call['input_version']==versions[i] and call['completed']==(not failed),'version/completion'
  if failed:assert call['output'] is None;t-=1
  else:assert call['output']==value;outputs[i]=value;done.add(i)
  if mode=='cached' and letter=='F':h+=1
 assert done==set(range(n)) and at==len(row['kernels']) and row['final_outputs']==outputs,'final/unused kernel'
 assert (row['W'],row['L'],row['Q'],row['writes'])==(W,L,len(row['calls']),unit['path'].count('F')),'resource counter'
 assert row['writes']<=unit['budget_tag'] and row['Q']<=n+unit['r'],'resource bound'
 return (W,L,len(row['calls']))

def main():
 p=argparse.ArgumentParser();p.add_argument('--raw',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir();units=json.loads((D/'NATIVE_INPUTS.json').read_text());raw=[json.loads(x) for x in a.raw.read_text().splitlines()];by={x['id']:x for x in raw};issues=[];groups=defaultdict(list)
 if len(raw)!=len(units) or len(by)!=len(raw):issues.append('denominator/duplicate')
 if [x['sequence'] for x in raw]!=list(range(len(raw))):issues.append('sequence')
 for unit in units:
  row=by.get(unit['id'])
  if row is None:issues.append({'id':unit['id'],'missing':True});continue
  try:value=check(row,unit);groups[(unit['case'],unit['r'],unit['budget_tag'],unit['policy'])].append(value)
  except (AssertionError,KeyError,IndexError,TypeError,ValueError) as e:issues.append({'id':unit['id'],'error':str(e)})
 maxima=[]
 for key,values in sorted(groups.items()):
  u=next(x for x in units if (x['case'],x['r'],x['budget_tag'],x['policy'])==key);actual=tuple(max(x[j] for x in values) for j in range(3));expected=vectors(u['works'],u['edges'],u['budget_tag'],u['r']) if u['policy']=='certificate' else tail.vectors(u['works'],u['edges'],u['budget_tag'],u['r'],u['policy']=='tail')
  if actual!=expected:issues.append({'group':key,'actual':actual,'expected':expected})
  maxima.append({'case':key[0],'r':key[1],'B':key[2],'policy':key[3],'paths':len(values),'maxima':actual,'expected':expected})
 # Test corruption rejection on a valid output containing both parent use and protected kernels.
 selected=next(u for u in units if u['case']=='counter-chain' and u['r']==1 and u['budget_tag']==4 and u['policy']=='tail' and 'P' in u['path']);sample=by[selected['id']];check(sample,selected)
 mutations=[('W',lambda x:x.update(W=x['W']+1)),('L',lambda x:x.update(L=x['L']+1)),('Q',lambda x:x.update(Q=x['Q']+1)),('writes',lambda x:x.update(writes=99)),('kernel_output',lambda x:x['kernels'][0].update(output=0)),('captured_parent',lambda x:next(k for k in x['kernels'] if k['parents'])['parents'].__setitem__(0,0)),('wrong_fresh_guard',lambda x:next(c for c in x['calls'] if c['mode']=='fresh').update(mode='cached')),('final_output',lambda x:x['final_outputs'].__setitem__(0,0))];controls=[]
 for name,change in mutations:
  bad=copy.deepcopy(sample);change(bad);rejected=False
  try:check(bad,selected)
  except (AssertionError,KeyError,IndexError,TypeError,ValueError):rejected=True
  controls.append({'name':name,'rejected':rejected})
  if not rejected:issues.append({'accepted_corruption':name})
 result={'status':'PASS' if not issues and len(maxima)==384 else 'FAIL','expected_units':len(units),'observed_units':len(raw),'native_statuses':dict(Counter(x['status'] for x in raw)),'groups':len(maxima),'controls':controls,'issues':issues,'raw_sha256':hashlib.sha256(a.raw.read_bytes()).hexdigest(),'checker_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'checker_timing':'Authored before this native execution, extending the already observed previous checker; not independent protocol certification.'}
 for name,data in [('CHECK_RECEIPT.json',result),('MAXIMA.json',maxima)]: (a.out/name).write_text(json.dumps(data,indent=2)+'\n')
 print(json.dumps(result,indent=2));print(json.dumps([x for x in maxima if x['case']=='counter-chain' and x['r']==1 and x['B']==4]))
if __name__=='__main__':main()
