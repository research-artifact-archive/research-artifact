from pathlib import Path
import json,sys,datetime
from reference import filter_case
P=Path(__file__).resolve().parent
if sys.argv[1]=='generate':
    roots=[dict(id='heap-ascending-promote',d=list(range(1,66)),k=0,ell=0,ops=[x for w in range(1,66) for x in [('Q',w),('MISMATCH',w)]]),dict(id='heap-replace-promote',d=list(range(65,0,-1)),k=33,ell=0,ops=[x for w in range(66,131) for x in [('Q',w),('MATCH',w)]]+[x for w in range(3,68) for x in [('Q',w),('MISMATCH',w)]])]
    with (P/'HEAP_STRUCTURE_INPUTS.json').open('x') as f: json.dump(roots,f,indent=2);f.write('\n')
    with (P/'HEAP_STRUCTURE_INPUTS.tsv').open('x') as f:
        for c in roots: f.write('\t'.join([c['id'],','.join(map(str,c['d'])),str(c['k']),str(c['ell']),';'.join(f'{o}:{w}' for o,w in c['ops'])])+'\n')
else:
    A=Path(sys.argv[2]);roots=json.loads((P/'HEAP_STRUCTURE_INPUTS.json').read_text())
    expected=[filter_case(c) for c in roots]
    actual=[json.loads(line) for line in (A/'heap.stdout').read_text().splitlines()]
    result=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='SUCCESS' if actual==expected else 'FAILURE',roots=2,queries=195,updates=195,observed_rows=len(actual),discrepant_ids=[e['id'] for e,a in zip(expected,actual) if e!=a])
    with (A/'HEAP_COMPARISON.json').open('x') as f: json.dump(result,f,indent=2);f.write('\n')
    with (A/'HEAP_REFERENCE.json').open('x') as f: json.dump(expected,f,indent=2);f.write('\n')
    print(json.dumps(result))
    sys.exit(0 if actual==expected else 1)
