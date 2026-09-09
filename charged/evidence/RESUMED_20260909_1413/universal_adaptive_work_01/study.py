from pathlib import Path
from functools import lru_cache
import json,time,hashlib,datetime
D=Path(__file__).resolve().parent;inp=json.loads((D/'OBSERVED_INPUTS.json').read_text());started=time.monotonic();records=[];counts={x:0 for x in ['SUCCESS','FAILURE','TIMEOUT','INVALID']};first=[]
for c in inp['cases']:
    n=len(c['works']);w=c['works'];pred=[0]*n
    for u,v in c['edges']:pred[v]|=1<<u
    def ready(S):return [i for i in range(n) if (S>>i)&1 and not pred[i]&S]
    @lru_cache(None)
    def best(S,b,t):
        if not S or not b:return 0
        if not t:return sum(sorted([w[i] for i in range(n) if S>>i&1],reverse=True)[:b])
        return min(max(best(S^(1<<i),b,t),w[i]+best(S,b-1,t-1)) for i in ready(S))
    @lru_cache(None)
    def greedy(S,b,t):
        if not S or not b:return 0
        if not t:return sum(sorted([w[i] for i in range(n) if S>>i&1],reverse=True)[:b])
        i=min(ready(S),key=lambda i:(w[i],i))
        return max(greedy(S^(1<<i),b,t),w[i]+greedy(S,b-1,t-1))
    for b in inp['budgets']:
        for t in inp['slacks']:
            rec={'case':c['id'],'b':b,'r':t}
            if time.monotonic()-started>90:rec['status']='TIMEOUT'
            else:
                try:
                    x=best((1<<n)-1,b,t);g=greedy((1<<n)-1,b,t);rec.update({'adaptive_excess':x,'greedy_excess':g,'status':'SUCCESS' if x==g else 'FAILURE'})
                except Exception as e:rec.update({'status':'INVALID','error':repr(e)})
            counts[rec['status']]+=1;records.append(rec)
            if rec['status']!='SUCCESS' and len(first)<20:first.append({'input':c,'result':rec})
with (D/'RESULTS.jsonl').open('x') as f:
    for rec in records:f.write(json.dumps(rec,separators=(',',':'))+'\n')
sumry={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'cases':len(inp['cases']),'roots':len(records),'counts':counts,'seconds':time.monotonic()-started,'status':'SUCCESS' if counts['SUCCESS']==len(records) else 'NON_SUCCESS','first_adverse':first,'results_sha256':hashlib.sha256((D/'RESULTS.jsonl').read_bytes()).hexdigest(),'scope':'Authored finite global-threshold family comparison only; no proof or all-program/native conclusion'}
with (D/'SUMMARY.json').open('x') as f:json.dump(sumry,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(sumry,ensure_ascii=False))
