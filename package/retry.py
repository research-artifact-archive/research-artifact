#!/usr/bin/env python3
"""Compile, check, or query the retained retry-policy implementations."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, sys
if not __debug__:raise RuntimeError('assertions-enabled Python is required')
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('portable_retry_dispatch',ROOT/'src/fixed_order_profile_03/dispatch.py')
dispatch=importlib.util.module_from_spec(spec);sys.modules[spec.name]=dispatch;spec.loader.exec_module(dispatch)

def checked(data):
    if data['route']!='persistent_order':
        return dict(scope='GLOBAL_ADAPTIVE_RETRY_GAME',certificate=dispatch.check(data))
    if 'normal_cost' in data:
        assert type(data['normal_cost']) is int and data['normal_cost']==sum(c for c,p in data['input']['cp'])
    report=dispatch.cap_check.check(data)
    assert not report['violations']
    # Shape validation recomputes uniqueness and checks the supplied order.
    scope='GLOBAL_ADAPTIVE_RETRY_GAME' if report['shape']['unique_order'] else 'SUPPLIED_SERIAL_ORDER_ONLY'
    return dict(scope=scope,certificate=report,generation_counters_certified=False)

def read(path):return json.loads(path.read_text())
def write(path,data):
    # Exclusive creation prevents accidental replacement of user inputs/results.
    with path.open('x') as stream:json.dump(data,stream,sort_keys=True,separators=(',',':'));stream.write('\n')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    compile_parser=commands.add_parser('compile',help='compile all budgets and check the result')
    compile_parser.add_argument('--input',type=Path,required=True,help='JSON object with cp [[c,p],...] and edges [[u,v],...]')
    compile_parser.add_argument('--order',type=Path,help='JSON topological-order array; restricts the serial policy class')
    compile_parser.add_argument('--out',type=Path,required=True)
    check_parser=commands.add_parser('check',help='verify every value and stored threshold/action')
    check_parser.add_argument('--artifact',type=Path,required=True)
    query_parser=commands.add_parser('query',help='check, then return residual/total work and the initial action')
    query_parser.add_argument('--artifact',type=Path,required=True)
    query_parser.add_argument('--budgets',type=int,nargs='+',required=True)
    args=parser.parse_args()
    if args.command=='compile':
        case=read(args.input)
        data=dispatch.compile_case(case) if args.order is None else dispatch.persistent.compile_case(case,read(args.order))
        data=json.loads(json.dumps(data,sort_keys=True,separators=(',',':')))
        report=checked(data);write(args.out,data)
        print(json.dumps(dict(**report,artifact_sha256=hashlib.sha256(args.out.read_bytes()).hexdigest(),route=data['route']),sort_keys=True))
        return 0
    data=read(args.artifact);report=checked(data)
    if args.command=='check':print(json.dumps(report,sort_keys=True));return 0
    if any(b<0 for b in args.budgets):raise ValueError('budgets must be nonnegative')
    loaded=dispatch.load(data);n=len(data['input']['cp']);initial=0 if data['route']!='ideal' else (1<<n)-1
    normal=sum(c for c,p in data['input']['cp'])
    results=[]
    for b in args.budgets:
        residual=dispatch.value(loaded,b)
        action=None if n==0 else dispatch.choose(loaded,initial,b)
        results.append(dict(budget=b,residual=residual,total_for_normal_cost_equal_to_c=normal+residual,initial_action=action))
    print(json.dumps(dict(scope=report['scope'],results=results),sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
