#!/usr/bin/env python3
"""Compile, check and query the charged atomic-call game from the paper."""
import argparse,json,sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'evidence/RESUMED_20260909_0056/charged_curves_02'))
import basis,checker,compiler

def main():
    if not __debug__:raise SystemExit('Assertions must be enabled; do not use python -O.')
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    c=sub.add_parser('compile');c.add_argument('--input',type=Path,required=True);c.add_argument('--out',type=Path,required=True)
    c=sub.add_parser('check');c.add_argument('--artifact',type=Path,required=True)
    c=sub.add_parser('query');c.add_argument('--artifact',type=Path,required=True);c.add_argument('--budgets',type=int,nargs='+',required=True)
    a=p.parse_args()
    if a.command=='compile':
        case=json.loads(a.input.read_text())
        # Check the input independently of the compiler's generated certificate.
        assert type(case)==dict and set(case)>={'jobs','edges'}
        assert type(case['jobs'])==list and case['jobs']
        assert all(type(row)==list and len(row)==5 and all(type(x)==int and x>=0 for x in row) and row[0]>0 for row in case['jobs'])
        n=len(case['jobs']);assert type(case['edges'])==list
        assert all(type(e)==list and len(e)==2 and all(type(x)==int and 0<=x<n for x in e) and e[0]!=e[1] for e in case['edges'])
        assert len(set(map(tuple,case['edges'])))==len(case['edges'])
        data=basis.compile_case(case);encoded=json.dumps(data,separators=(',',':'))+'\n'
        result=checker.check(json.loads(encoded))
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open('x') as f:f.write(encoded)
        print(json.dumps(dict(status='CHECKED',artifact=str(a.out),states=data['states'],baseline=data['baseline'],check=result)))
    else:
        data=json.loads(a.artifact.read_text());result=checker.check(data)
        if a.command=='check':print(json.dumps(dict(status='CHECKED',check=result)))
        else:
            assert all(b>=0 for b in a.budgets)
            data['curves']={int(k):v for k,v in data['curves'].items()}
            data['actions']={int(k):v for k,v in data['actions'].items()}
            rows=[]
            for b in a.budgets:
                excess=compiler.base.at(data['curves'][data['full']],b)
                cost,job,mode=compiler.choose(data,data['full'],b)
                assert cost==excess
                rows.append(dict(budget=b,excess=excess,total=data['baseline']+excess,initial_job=job,initial_mode=mode))
            print(json.dumps(dict(baseline=data['baseline'],queries=rows),indent=2))

if __name__=='__main__':main()
