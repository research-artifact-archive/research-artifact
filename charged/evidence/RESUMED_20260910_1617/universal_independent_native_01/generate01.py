from pathlib import Path
import itertools,json,hashlib
D=Path(__file__).resolve().parent
fixtures=[('multi'+str(n)+'_'+''.join(map(str,w)),list(w),r) for n in range(1,4) for w in itertools.combinations_with_replacement((1,2,4),n) for r in range(3)]
fixtures += [(name,w,r) for name,w in [('wide6a',[2,4,1,1,2,1]),('wide6b',[2,1,4,3,1,6])] for r in range(3)]
fixtures += [('tree9',[1,2,4,1,2,4,1,2,4],1)]
def patterns(n,r):
 def visit(i,f,s):
  if i==n:yield s;return
  yield from visit(i+1,f,s+'0')
  if f<r:yield from visit(i,f+1,s+'1')
  else:yield from visit(i+1,f,s+'1')
 return list(visit(0,0,''))
rows=[];inputs=[];leaves=0
for name,w,r in fixtures:
 order=sorted(range(len(w)),key=lambda i:(w[i],i));ps=patterns(len(w),r);leaves+=len(ps)
 for layout,kernel,cheap,pattern in itertools.product(('distinct','colliding'),('allocated','canonical'),('replace','validate'),ps):
  cid=f'universal01-{len(rows):05d}';values=[cid,name,','.join(map(str,w)),','.join(['0']*len(w)),','.join(map(str,order)),cheap,r,layout,kernel,pattern]
  rows.append('\t'.join(map(str,values)));inputs.append(dict(id=cid,fixture=name,w=w,pred=[0]*len(w),order=order,cheap=cheap,r=r,layout=layout,kernel=kernel,pattern=pattern))
assert len(fixtures)==64 and leaves==2548 and len(rows)==20384
assert not(D/'RUNS.tsv').exists()
(D/'RUNS.tsv').write_text('\n'.join(rows)+'\n');(D/'INPUTS.json').write_text(json.dumps(inputs,indent=2)+'\n')
print(json.dumps(dict(planned=len(rows),contracts=len(fixtures),outcome_paths=leaves,sha256=hashlib.sha256((D/'RUNS.tsv').read_bytes()).hexdigest())))
