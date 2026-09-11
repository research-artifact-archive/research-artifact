from pathlib import Path
import json,itertools,hashlib,datetime
from reference import patterns,MAX
P=Path(__file__).resolve().parent

def create(name,body):
    with (P/name).open('x') as f: f.write(body)

seeds=[([],0,0),([100,1],1,1),([7,3],1,6),([2,2],2,4),([3],4,1),([1,7,3],2,8)]
seqs=[[1,3,2],[7,1,2],[2,2,2]]
fcs=[]
for s,(d,k,ell) in enumerate(seeds):
    for t,seq in enumerate(seqs):
        root=f'filter-{s}-{t}'
        for a,actions in enumerate(itertools.product(['MATCH','MISMATCH','FRESH'],repeat=3)):
            ops=[]
            for w,op in zip(seq,actions):
                ops.extend([['Q',q] for q in [w,1,7,80,MAX]])
                ops.append([op,w])
            fcs.append(dict(id=f'{root}-{a}',root=root,d=d,k=k,ell=ell,ops=ops,boundary=False))
boundaries=[
 ('zero',[],0,0,[['Q',0]]),('negative_weight',[],0,0,[['MATCH',-1]]),
 ('negative_k',[],-1,0,[]),('negative_ell',[],0,-1,[]),
 ('nonviable',[2],0,1,[]),('constructor_top_overflow',[MAX,1],2,0,[]),
 ('prospective_top_overflow',[MAX],2,0,[['Q',1],['MATCH',1],['MISMATCH',1]]),
 ('ell_overflow',[MAX],1,MAX,[['Q',1],['FRESH',1],['MISMATCH',1]]),
 ('credit_overflow',[],MAX,0,[['MISMATCH',1]]),
 ('null_outcome',[3],1,0,[['N',1]]),('unsafe_fresh',[],0,0,[['FRESH',1]]),
 ('safe_max',[MAX],1,0,[['Q',MAX],['FRESH',MAX]])]
for label,d,k,ell,ops in boundaries:
    fcs.append(dict(id=f'boundary-{label}',root=f'boundary-{label}',d=d,k=k,ell=ell,ops=ops,boundary=True))
create('FILTER_INPUTS.json',json.dumps(fcs,indent=2)+'\n')
create('FILTER_INPUTS.tsv',''.join('\t'.join([c['id'],','.join(map(str,c['d'])) or '-',str(c['k']),str(c['ell']),';'.join(f'{o}:{w}' for o,w in c['ops']) or '-'])+'\n' for c in fcs))
fixtures=[('single',[2],[0],0),('unsafe-chain',[1,1,10],[0,1,2],0),('independent',[1,3,2],[0,0,0],1),('diamond',[5,1,2,4],[0,1,1,6],1),('ties-chain',[2,2,2],[0,1,2],2),('strict-safe-fresh',[100,1,2,80,80,80],[0,1,2,4,8,16],1)]
roots=[];ncs=[]
for boundary in ['normal','postwrite','doublewrite']:
    for fixture,w,pred,r in fixtures:
        if boundary!='normal' and fixture!='diamond': continue
        for policy in ['filter','allfresh','allcached']:
            for layout in ['distinct','colliding']:
                rid=f'{fixture}-{boundary}-{policy}-{layout}'
                root=dict(root=rid,fixture=fixture,w=w,pred=pred,r=r,policy=policy,layout=layout,boundary=boundary)
                ps=list(patterns(root));roots.append(dict(**root,paths=len(ps)))
                for j,pat in enumerate(ps): ncs.append(dict(**root,id=f'{rid}-{j}',pattern=pat))
create('NATIVE_ROOTS.json',json.dumps(roots,indent=2)+'\n')
create('NATIVE_INPUTS.json',json.dumps(ncs,indent=2)+'\n')
create('NATIVE_INPUTS.tsv',''.join('\t'.join([c['id'],c['root'],c['fixture'],','.join(map(str,c['w'])),','.join(map(str,c['pred'])),str(c['r']),c['policy'],c['layout'],c['boundary'],c['pattern'] or '-'])+'\n' for c in ncs))
create('INPUT_RECEIPT.json',json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),filter_roots=18,filter_scripts=486,boundary_roots=len(boundaries),filter_rows=len(fcs),native_roots=len(roots),native_paths=len(ncs),status='INPUT_GENERATED_NOT_JAVA_RESULT',files={n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in ['PROTOCOL.md','FILTER_INPUTS.json','FILTER_INPUTS.tsv','NATIVE_ROOTS.json','NATIVE_INPUTS.json','NATIVE_INPUTS.tsv']}),indent=2)+'\n')
print(json.loads((P/'INPUT_RECEIPT.json').read_text()))
