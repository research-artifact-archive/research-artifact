import itertools,json,hashlib
from pathlib import Path
D=Path(__file__).resolve().parent
fixtures=[('singleton',[8],[0]),('chain8_16',[8,16],[0,1]),('chain16_8',[8,16],[2,0]),('independent8_16',[8,16],[0,0]),('fork',[1,2,4],[0,0,3]),('tied',[2,2,1],[0,0,0]),('tree9',[1,2,4,1,2,4,1,2,4],[0]+[1<<i for i in range(8)])]
def first_topo(pred):
    todo=set(range(len(pred)));out=[]
    while todo:
        i=min(i for i in todo if all(not(pred[i]>>j&1) for j in todo));todo.remove(i);out.append(i)
    return out
rows=[];manifest=[]
for name,w,pred in fixtures:
    order=first_topo(pred);schedules=[(-1,-1,'none')]+list(itertools.product(range(len(w)+1),range(len(w)),('before','gate','after')))
    for M,layout,kernel,cheap,(k,j,phase) in itertools.product(sorted({0,*w}),('distinct','colliding'),('allocated','canonical'),('replace','validate'),schedules):
        cid=f'oneretry01-{len(rows):05d}'
        values=[cid,name,','.join(map(str,w)),','.join(map(str,pred)),','.join(map(str,order)),cheap,M,layout,kernel,k,j,phase]
        rows.append('\t'.join(map(str,values)))
        manifest.append(dict(id=cid,fixture=name,w=w,pred=pred,order=order,cheap=cheap,M=M,layout=layout,kernel=kernel,k=k,target=j,phase=phase))
assert len(rows)==12224
for name,count in [('singleton',112),('chain8_16',456),('chain16_8',456),('independent8_16',456),('fork',1184),('tied',888),('tree9',8672)]:assert sum(c['fixture']==name for c in manifest)==count
assert not(D/'RUNS.tsv').exists()
(D/'RUNS.tsv').write_text('\n'.join(rows)+'\n');(D/'INPUTS.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'total':len(rows),'sha256':hashlib.sha256((D/'RUNS.tsv').read_bytes()).hexdigest()}))
