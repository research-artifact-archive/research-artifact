from pathlib import Path
import datetime,json
D=Path(__file__).resolve().parent
cases=[{'id':'counter-chain','works':[2,4,1,1],'edges':[[0,1],[1,2],[2,3]]},{'id':'counter-independent','works':[2,4,1,1],'edges':[]},{'id':'counter-diamond','works':[2,4,1,1],'edges':[[0,1],[0,2],[1,3],[2,3]]},{'id':'increasing-chain','works':[1,2,3,5],'edges':[[0,1],[1,2],[2,3]]}]
rows=[]
for case in cases:
 w=case['works'];n=len(w);pred=[0]*n
 for u,v in case['edges']:pred[v]|=1<<u
 prefix=[0]
 for wi in sorted(w,reverse=True):prefix.append(prefix[-1]+wi)
 for r in range(3):
  for B in range(6):
   for policy in ['threshold','tail']:
    def generate(S,b,t,h,ell,path):
     if not S:
      rows.append({'id':f'u{len(rows):05}','case':case['id'],'works':w,'edges':case['edges'],'r':r,'budget_tag':B,'policy':policy,'path':path});return
     i=min((i for i in range(n) if S>>i&1 and not pred[i]&S),key=lambda i:(w[i],i));T=S^(1<<i)
     if not t and policy=='tail' and ell+sum(w[j] for j in range(n) if S>>j&1)<=prefix[min(h,n)]:generate(T,b,t,h,ell+w[i],path+'P')
     else:
      generate(T,b,t,h,ell,path+'M')
      if b:
       if t:generate(S,b-1,t-1,h,ell,path+'F')
       else:generate(T,b-1,0,h+1,ell+w[i],path+'F')
    generate((1<<n)-1,B,r,0,0,'')
(D/'NATIVE_INPUTS.json').write_text(json.dumps(rows,indent=2)+'\n')
(D/'NATIVE_RUNS.tsv').write_text(''.join('\t'.join([x['id'],x['case'],','.join(map(str,x['works'])),';'.join(f'{u}-{v}' for u,v in x['edges']),str(x['r']),str(x['budget_tag']),x['policy'],x['path']])+'\n' for x in rows))
(D/'NATIVE_PLAN.json').write_text(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'kind':'FIXED_NATIVE_TRACE_DENOMINATOR_BEFORE_JVM_OUTCOMES','units':len(rows),'groups':4*3*6*2,'cases':cases,'slacks':[0,1,2],'budget_tags':list(range(6)),'writer':'Separate joined writer thread changes current own-input identity immediately before chosen mismatching compare. Budget/path remain outside selector; first and later failures cost actual new writes.','observed_input':'Author chain counterexample already known; other variants constructed after equation study. Not held out.','work':'Selected iterations of deterministic pure kernel; parent mixing/allocation/callback overhead excluded.','checks':'Every complete branch and native counted W,L,Q maximum, actual versions, pure outputs and captured parent values. No timing claims.','no_exclusion':True,'no_retry':True,'process_cap_seconds':180,'scientific_limits':'Bounded authored native scripts, not all host schedules; source/game correlation retained.'},indent=2)+'\n');print(len(rows))
