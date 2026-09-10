from pathlib import Path
from collections import Counter
import json,hashlib,datetime

D=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
rows=json.loads((D/'MATRIX_JOINED02.json').read_text());byid={x['input']['id']:x for x in rows}
paired=json.loads((D/'MATRIX_COMPARISON02.json').read_text())['pairs'];assert len(paired)==384
global_rows={x['id']:x for x in json.loads((D/'MATRIX_GLOBAL03B.json').read_text())}
source=D/'implementation03/cached_body.c.inc';text=source.read_text()
assert 'static char *dpath_cached_raw' in text and 'static char *dpath_two_cheap_raw' in text
results=[];groups=Counter()
for pair in paired:
 answer={'cached_id':pair['cached_id'],'two_cheap_id':pair['new_id'],'B':pair['B'],'new_native_samples':0}
 for label,identity in [('cached',pair['cached_id']),('two_cheap',pair['new_id'])]:
  x=byid[identity];assert not x['input']['control'] and x['row']['status']=='SUCCESS'
  assert global_rows[identity]['global_writes']==x['row']['B']==pair['B']
  R=x['aux']['rcu'];G=x['aux']['guards'];Q=x['row']['Q'];assert R in [1,2] and G in [0,1]
  assert Q==R+(G if label=='two_cheap' else 0)
  assert label!='cached' or G==R-1
  counts={'rcu_read_lock':R,'rcu_read_unlock':R,'read_seqbegin':R,'read_seqretry':R,'read_seqlock_excl':G,'read_sequnlock_excl':G}
  answer[label]={'public_invocations':1,'logical_Q':Q,'named_source_primitives':counts,'primitive_sum':sum(counts.values()),'body_invocations':x['row']['bodies'],'body_T':x['row']['T'],'protected_body_T':x['row']['L_T'],'guards':G,'output_error':x['row']['error']}
  assert sum(counts.values())==4*R+2*G
 a,b=answer['cached'],answer['two_cheap']
 assert a['body_T']==b['body_T'] and a['protected_body_T']==b['protected_body_T'] and a['output_error']==b['output_error']
 assert b['primitive_sum']<=a['primitive_sum']
 groups[(pair['B'],a['logical_Q'],b['logical_Q'],a['primitive_sum'],b['primitive_sum'],a['guards'],b['guards'])]+=1
 results.append(answer)
with (D/'Q_SENSITIVITY04_ROWS.json').open('x') as f:json.dump(results,f,indent=2);f.write('\n')
receipt={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'SUCCESS','posthoc_descriptive_reconstruction':True,'pairs':len(results),'groups':[dict(B=k[0],cached_Q=k[1],two_cheap_Q=k[2],cached_primitive_sum=k[3],two_cheap_primitive_sum=k[4],cached_guards=k[5],two_cheap_guards=k[6],pairs=v) for k,v in sorted(groups.items())],'each_public_invocation_count':1,'maximum_logical_Q':{'cached':max(x['cached']['logical_Q'] for x in results),'two_cheap':max(x['two_cheap']['logical_Q'] for x in results)},'maximum_named_primitive_sum':{'cached':max(x['cached']['primitive_sum'] for x in results),'two_cheap':max(x['two_cheap']['primitive_sum'] for x in results)},'new_native_runs':0,'new_timing_samples':0,'source_derivation':'implementation03/cached_body.c.inc lines3--44 and65--99; count named source boundaries only, not internal spin iterations/machine calls','files':{name:sha(D/name) for name in ['MATRIX_JOINED02.json','MATRIX_COMPARISON02.json','MATRIX_GLOBAL03B.json','implementation03/cached_body.c.inc','Q_SENSITIVITY04_PLAN.md','q_sensitivity04.py','Q_SENSITIVITY04_ROWS.json']}}
with (D/'Q_SENSITIVITY04_RECEIPT.json').open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
print(json.dumps(receipt,indent=2))
