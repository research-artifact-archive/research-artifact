from pathlib import Path
from itertools import combinations_with_replacement,product
import json,random
D=Path(__file__).resolve().parent
pairs=list(product([1,2,4],[0,1,3]));general=[]
for n in range(1,5):
 for xs in combinations_with_replacement(pairs,n):general.append(dict(id=f'g{len(general):04}',w=[x[0] for x in xs],g=[x[1] for x in xs],source='complete_multisets'))
rng=random.Random(202609110410)
for _ in range(50):
 xs=[rng.choice(pairs) for _ in range(5)];general.append(dict(id=f'g{len(general):04}',w=[x[0] for x in xs],g=[x[1] for x in xs],source='fixed_seed_five_job'))
uniform=[]
for n in range(1,7):
 for w in combinations_with_replacement([1,2,4,7],n):
  for g in [0,1,2,7]:uniform.append(dict(id=f'u{len(uniform):04}',w=w,guard=g))
subset=[]
for n in range(1,6):
 for a in combinations_with_replacement([1,2,3],n):subset.append(dict(id=f's{len(subset):03}',items=a,targets=list(range(1,sum(a)+1))))
inputs=dict(general=general,uniform=uniform,subset=subset,output_family=list(range(2,10)),controls=['ignore_entry_in_total','ignore_K_in_protection','ascending_work_sort','reuse_zero_guard_item','ignore_Gamma_cap','count_DP_on_heterogeneous_guards','allow_late_selected_job'])
with(D/'INPUTS01.json').open('x') as f:json.dump(inputs,f,indent=2);f.write('\n')
print({k:len(v) for k,v in inputs.items()})
