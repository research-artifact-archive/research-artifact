from pathlib import Path
from itertools import permutations
from functools import lru_cache
from datetime import datetime,timezone
import gzip,hashlib,io,json,time,traceback
D=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def prune(points):
 out=[];best=None
 for a,b in sorted(set(points)):
  if best is None or b<best:out.append((a,b));best=b
 return tuple(out)
def dp(w,g,c,edges):
 n=len(w);pred=[0]*n
 for i,j in edges:pred[j]|=1<<i
 @lru_cache(None)
 def rec(mask):
  if not mask:return ((0,0),)
  out=[]
  for i in range(n):
   if not mask>>i&1 or mask&pred[i]:continue
   rem=mask^(1<<i);body=sum(w[j] for j in range(n) if rem>>j&1)
   for a,b in rec(rem):
    out.append((w[i]+g[i]+a,w[i]+g[i]+b))
    out.append((max(w[i]+g[i]+c[i]+a,2*w[i]+g[i]+c[i]+body),max(g[i]+c[i]+b,w[i]+g[i]+c[i])))
  return prune(out)
 f=rec((1<<n)-1);return f,rec.cache_info().currsize
def formula(w,g,c,order,mask):
 H=sum(g)+sum(c[i] for i in range(len(w)) if mask>>i&1)
 W=sum(w)+H;P=H+sum(w[i] for i in range(len(w)) if not mask>>i&1)
 prefix=protected=0
 for i in order:
  prefix+=g[i]+(c[i] if mask>>i&1 else 0)
  if mask>>i&1:W=max(W,sum(w)+w[i]+prefix);P=max(P,w[i]+prefix+protected)
  else:protected+=w[i]
 return W,P
def trace(w,g,c,order,mask,bad):
 W=P=Q=used=0;rows=[]
 for i in order:
  if used:mode='cheap'
  else:mode='cached' if mask>>i&1 else 'fresh'
  outside=inside=entry=cmp=0
  if mode=='fresh':inside=w[i];entry=g[i]
  else:
   outside=w[i]
   if mode=='cached':
    entry=g[i];cmp=c[i]
    if i==bad:inside=w[i];used+=1
  Q+=1;W+=outside+inside+entry+cmp;P+=inside+entry+cmp
  rows.append([i,mode,outside,inside,entry,cmp])
 assert Q==len(w) and used in [0,1]
 assert used==int(bad is not None)
 assert P<=W
 return {'Wt':W,'Pt':P,'Q':Q,'writes':used,'events':rows}
def policies(w,g,c,edges):
 n=len(w);witness={};count=0
 for order in permutations(range(n)):
  pos={i:k for k,i in enumerate(order)}
  if any(pos[i]>=pos[j] for i,j in edges):continue
  for mask in range(1<<n):
   count+=1;p=formula(w,g,c,order,mask);witness.setdefault(p,(order,mask))
 return prune(witness),witness,count
def open_gz(path):
 return io.TextIOWrapper(gzip.GzipFile(filename='',mode='wb',fileobj=path.open('xb'),mtime=0),encoding='utf-8',newline='\n')
def emit(f,x):f.write(json.dumps(x,separators=(',',':'))+'\n')
def main():
 O=D/'run04';O.mkdir();started=time.monotonic()
 fixed=json.loads((D/'INPUT_FIX_RECEIPT04.json').read_text())
 for n,r in fixed['files'].items():assert sha(D/n)==r['sha256'],n
 inputs=json.loads((D/'INPUTS04.json').read_text());fail=[];error=None
 count={'general_inputs':0,'general_dp_states':0,'order_mask_policies':0,'general_paths':0,'embedding_inputs':0,'embedding_dp_inputs':0,'embedding_dp_states':0,'embedding_subset_points':0,'embedding_paths':0,'controls':0}
 start={'utc':datetime.now(timezone.utc).isoformat(),'files':fixed['files'],'counts_fixed':fixed['counts']};(O/'START.json').write_text(json.dumps(start,indent=2)+'\n')
 def require(ok,kind,id,payload):
  if not ok:fail.append(dict(kind=kind,id=id,payload=payload))
 try:
  with open_gz(O/'GENERAL_ROWS.jsonl.gz') as rows,open_gz(O/'PATHS.jsonl.gz') as paths:
   for x in inputs['general']:
    w,g,c,e=x['w'],x['g'],x['c'],x['edges'];front,states=dp(w,g,c,e);direct,witness,plans=policies(w,g,c,e)
    count['general_dp_states']+=states;count['order_mask_policies']+=plans
    require(front==direct,'dp_vs_order_formula',x['id'],{'dp':front,'order':direct})
    scope='all_plans' if x['n']<=4 else 'frontier_witnesses'
    if x['n']<=4:
     iterable=[]
     for order in permutations(range(x['n'])):
      pos={i:k for k,i in enumerate(order)}
      if any(pos[i]>=pos[j] for i,j in e):continue
      for mask in range(1<<x['n']):iterable.append((order,mask,formula(w,g,c,order,mask)))
    else:iterable=[(*witness[p],p) for p in direct]
    for order,mask,p in iterable:
     maxW=maxP=0
     for bad in [None]+[i for i in order if mask>>i&1]:
      t=trace(w,g,c,order,mask,bad);maxW=max(maxW,t['Wt']);maxP=max(maxP,t['Pt']);count['general_paths']+=1
      emit(paths,{'study':'general','input':x['id'],'order':order,'mask':mask,'bad':bad,**t})
     require((maxW,maxP)==p,'formula_vs_paths',x['id'],{'order':order,'mask':mask,'formula':p,'paths':[maxW,maxP]})
    emit(rows,{'input':x['id'],'frontier':front,'formula_frontier':direct,'plans':plans,'path_scope':scope,'witnesses':[{'point':p,'order':witness[p][0],'mask':witness[p][1]} for p in direct]});count['general_inputs']+=1
   for x in inputs['embedding']:
    a,v=x['sizes'],x['values'];m=len(a);w=[a[i]+v[i] for i in range(m)]+[1];g=[1]*m+[max(w for w in [a[i]+v[i] for i in range(m)])];c=a+[1]
    n=m+1;edges=[] if x['topology']=='independent' else [[i,m] for i in range(m)];base=sum(w)+sum(g);pts={}
    for mask in range(1<<m):
     point=(base+sum(a[i] for i in range(m) if mask>>i&1),base-sum(v[i] for i in range(m) if mask>>i&1));pts.setdefault(point,mask)
    expected=prune(pts);count['embedding_subset_points']+=1<<m
    got=None
    if m<=4:
     got,states=dp(w,g,c,edges);count['embedding_dp_inputs']+=1;count['embedding_dp_states']+=states
     require(got==expected,'embedded_entire_frontier',x['id'],{'dp':got,'subset':expected})
    for point in expected:
     mask=pts[point];order=tuple(range(n));f=formula(w,g,c,order,mask)
     require(f==point,'embedded_formula',x['id'],{'formula':f,'subset':point})
     for bad in [None]+[i for i in range(m) if mask>>i&1]:
      t=trace(w,g,c,order,mask,bad);count['embedding_paths']+=1
      require(t['Wt']<=point[0] and t['Pt']<=point[1],'embedded_path',x['id'],{'point':point,'trace':t})
      if bad is None:require((t['Wt'],t['Pt'])==point,'embedded_no_write_attains',x['id'],{'point':point,'trace':t})
      emit(paths,{'study':'embedding','input':x['id'],'order':order,'mask':mask,'bad':bad,**t})
    if x['family']=='powers_two':require(len(expected)==1<<m,'exponential_points',x['id'],{'actual':len(expected),'expected':1<<m})
    emit(rows,{'study':'embedding','input':x['id'],'frontier':expected,'dp_frontier':got,'method_scope':'unrestricted_mode_DP_and_subset_paths' if m<=4 else 'subset_paths_and_analytic_embedding','original_items':m,'topology':x['topology']});count['embedding_inputs']+=1
  controls=[]
  t=trace([3],[1],[1],[0],1,None);controls.append({'id':inputs['controls'][0],'correct':t['Wt'],'altered':t['Wt']-1,'detected':t['Wt']!=t['Wt']-1})
  t=trace([1,3],[1,7],[1,0],[0,1],1,0);controls.append({'id':inputs['controls'][1],'correct':t['Pt'],'altered':t['Pt']+7,'detected':True,'scope':'single mismatch path; complete frontier need not change'})
  t=trace([3],[1],[1],[0],1,None);bad=trace([3],[1],[1],[0],1,0);controls.append({'id':inputs['controls'][2],'correct':[max(t['Wt'],bad['Wt']),max(t['Pt'],bad['Pt'])],'altered':[t['Wt'],t['Pt']],'detected':bad['Wt']>t['Wt']})
  t=trace([6,1],[1,0],[1,1],[0,1],1,None);bad=trace([6,1],[1,0],[1,1],[0,1],1,0);controls.append({'id':inputs['controls'][3],'proposed_no_write_cap':[t['Wt'],t['Pt']],'actual_bad':[bad['Wt'],bad['Pt']],'detected':bad['Wt']>t['Wt'] or bad['Pt']>t['Pt']})
  controls.append({'id':inputs['controls'][4],'Q_failed_plus_completion':2,'n':1,'altered_Q':1,'actual_writes':1,'detected':2>1})
  controls.append({'id':inputs['controls'][5],'actual_stale_prepare_cached_pair':[8,5],'free_prepare_altered_pair':[5,5],'dominating_fresh_pair':[4,4],'detected':8!=5})
  for x in controls:require(x['detected'],'control',x['id'],x);count['controls']+=1
  (O/'CONTROLS.json').write_text(json.dumps(controls,indent=2)+'\n')
 except Exception:
  error=traceback.format_exc();(O/'EXCEPTION.txt').write_text(error)
 result={'status':'SUCCESS' if not fail and not error and count['general_inputs']==fixed['counts']['general'] and count['embedding_inputs']==fixed['counts']['embedding'] and count['controls']==fixed['counts']['controls'] else 'FAILED','counts':count,'failures':fail,'exception':error,'seconds':time.monotonic()-started,'utc':datetime.now(timezone.utc).isoformat(),'inputs_sha256':sha(D/'INPUTS04.json'),'checker_sha256':sha(D/'check04.py')}
 (O/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return 0 if result['status']=='SUCCESS' else 1
if __name__=='__main__':raise SystemExit(main())
