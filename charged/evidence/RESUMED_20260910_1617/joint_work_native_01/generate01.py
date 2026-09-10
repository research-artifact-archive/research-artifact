"""Generate the complete fixed native input matrix, without executing Java."""
import itertools,json,hashlib
from pathlib import Path
D=Path(__file__).resolve().parent
fixtures=[('singleton',[8],[0]),('chain8_16',[8,16],[0,1]),('chain16_8',[8,16],[2,0]),('independent8_16',[8,16],[0,0]),('fork',[1,2,4],[0,0,3]),('tied',[2,2,1],[0,0,0])]
def lawler(w,pred,M):
    left=set(range(len(w))); reverse=[]
    while left:
        sinks=[i for i in left if all(not(pred[j]>>i&1) for j in left)]
        i=min(sinks,key=lambda i:(w[i] if w[i]<=M else 0,i))
        reverse.append(i);left.remove(i)
    return reverse[::-1]
def first_topo(pred):
    todo=set(range(len(pred)));out=[]
    while todo:
        i=min(i for i in todo if all(not(pred[i]>>j&1) for j in todo))
        todo.remove(i);out.append(i)
    return out
rows=[];manifest=[]
for control in (False,True):
    for name,w,pred in fixtures:
        if control and name not in ('chain8_16','independent8_16'):continue
        policies=[('lawler',8)] if control else [('lawler',M) for M in sorted({0,*w})]+[('cached',-1),('fresh',-1)]
        schedules=[(-1,-1,'none')]+list(itertools.product(range(len(w)),range(len(w)),('before','gate','after')))
        for (policy,M),layout,kernel,(k,j,phase) in itertools.product(policies,('distinct','colliding'),('canonical',) if control else ('allocated','canonical'),schedules):
            order=lawler(w,pred,M) if policy=='lawler' else first_topo(pred)
            cid=f'joint01-{len(rows):04d}'
            values=[cid,name,','.join(map(str,w)),','.join(map(str,pred)),','.join(map(str,order)),policy,M,layout,kernel,k,j,phase,str(control).lower()]
            rows.append('\t'.join(map(str,values)))
            manifest.append(dict(id=cid,fixture=name,w=w,pred=pred,order=order,policy=policy,M=M,layout=layout,kernel=kernel,k=k,target=j,phase=phase,control=control))
assert len(rows)==2128 and sum(x['control'] for x in manifest)==52
for name,count in [('singleton',64),('chain8_16',260),('chain16_8',260),('independent8_16',260),('fork',672),('tied',560)]:
    assert sum(x['fixture']==name and not x['control'] for x in manifest)==count
(D/'RUNS.tsv').write_text('\n'.join(rows)+'\n')
(D/'INPUTS.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'total':len(rows),'correct_policies':2076,'negative_controls':52,'sha256':hashlib.sha256((D/'RUNS.tsv').read_bytes()).hexdigest()}))
