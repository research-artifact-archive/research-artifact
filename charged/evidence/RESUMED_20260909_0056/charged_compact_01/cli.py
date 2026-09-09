#!/usr/bin/env python3
import argparse,json
from pathlib import Path
import compact,verify
from runtime import Policy

def main():
    if not __debug__:raise SystemExit('Assertions must be enabled.')
    p=argparse.ArgumentParser(description='Charged atomic-call policy compiler, with compatible zero-delta specialization.')
    sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('compile');a.add_argument('--input',type=Path,required=True);a.add_argument('--out',type=Path,required=True);a.add_argument('--general',action='store_true')
    for name in ['check','query']:
        a=sub.add_parser(name);a.add_argument('--artifact',type=Path,required=True);a.add_argument('--input',type=Path)
        if name=='query':a.add_argument('--budgets',nargs='+',type=int,required=True)
    a=p.parse_args();case=verify.loads(a.input.read_text()) if a.input else None
    if a.command=='compile':
        data=compact.compile_case(case,a.general);encoded=json.dumps(data,separators=(',',':'))+'\n';loaded=verify.loads(encoded);checked=verify.check(loaded,case)
        a.out.parent.mkdir(parents=True,exist_ok=True)
        with a.out.open('x') as f:f.write(encoded)
        print(json.dumps(dict(route=data['route'],artifact=str(a.out),check=checked),indent=2))
    else:
        data=verify.loads(a.artifact.read_text())
        if a.command=='check':print(json.dumps(verify.check(data,case),indent=2))
        else:
            policy=Policy(data,case)
            print(json.dumps(dict(route=policy.route,entry=policy.entry,baseline=policy.baseline,queries=[dict(budget=b,excess=policy.excess(b),total=policy.total(b),initial=policy.choose(b)) for b in a.budgets]),indent=2))

if __name__=='__main__':main()
