#!/usr/bin/env python3
"""Replay retained supporting-line basis checks; no scientific sample increase."""
from pathlib import Path
import argparse,importlib.util,json,subprocess,sys,traceback
if not __debug__:raise RuntimeError('assertions-enabled Python is required')
sys.dont_write_bytecode=True
import reproduce_oracle as base
ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data/extended/linear_slope_bound_01'
def module():
    spec=importlib.util.spec_from_file_location('portable_slope_basis',ROOT/'src/linear_slope_bound_01/study.py')
    result=importlib.util.module_from_spec(spec);sys.modules[spec.name]=result;spec.loader.exec_module(result);return result
def replay(out,args,kind):
    study=module();original={r['id']:r for r in base.rows(DATA/'run01/RAW.jsonl') if r['kind']==kind}
    if kind=='ALGEBRA':units=base.load(DATA/'run01/ALGEBRA_INPUTS.json')
    elif kind=='CERTIFICATE':units=base.load(DATA/'run01/CERTIFICATE_INPUTS.json')
    elif kind=='TIGHT':units=[dict(id=f'tight-{n:02}',n=n) for n in range(1,65)]
    else:units=[dict(id=k) for k in ['continuous_max','bridge_not_input_cost']]
    expected={'ALGEBRA':17656,'CERTIFICATE':4355,'TIGHT':64,'CONTROL':2}
    assert len(units)==len(original)==expected[kind]
    def one(u):
        if kind=='ALGEBRA':actual=study.algebra(u)
        elif kind=='CERTIFICATE':
            path=DATA/u['path'];assert base.sha(path)==u['sha256'];actual=study.artifact(base.load(path))
        elif kind=='TIGHT':actual=study.tight(u['n'])
        else:actual=study.control(u['id'])
        actual=base.roundtrip(actual)  # Compare the saved JSON representation, including tuple/list normalization.
        prior=original[u['id']];assert prior['status']=='SUCCESS' and actual==prior['result']
        return actual
    return base.run_units(out,units,one,args.quick,limit=20,metadata=dict(known_units=expected[kind],
        original_timeout_units_rerun=0,prior_outcome_upgrades=0,
        certificate_scope='BASIS_PROPERTY_ONLY_NOT_NEW_BELLMAN_CERTIFICATION'))
STAGES={'algebra':'ALGEBRA','certificates':'CERTIFICATE','tight':'TIGHT','controls':'CONTROL'}
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['verify','all',*STAGES])
    parser.add_argument('--out',type=Path,required=True);parser.add_argument('--quick',action='store_true')
    parser.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args();out=args.out.resolve();assert not out.is_relative_to(ROOT)
    if args.worker:
        assert out.is_dir() and not any(out.iterdir())
        try:result=replay(out,args,STAGES[args.mode])
        except Exception:
            base.save(out/'HARNESS_ERROR.json',dict(error=traceback.format_exc()));raise
        return 0 if result['success'] else 1
    verified=base.verify();out.mkdir(parents=True,exist_ok=False)
    base.save(out/'START.json',dict(utc=base.now(),verification=verified,scientific_sample_increase=False))
    results={}
    for name in STAGES if args.mode=='all' else ([] if args.mode=='verify' else [args.mode]):
        sub=out/name;sub.mkdir();cmd=[sys.executable,'-B',str(Path(__file__).resolve()),name,'--out',str(sub),'--worker']
        if args.quick:cmd.append('--quick')
        with (out/(name+'-stdout.txt')).open('xb') as stdout,(out/(name+'-stderr.txt')).open('xb') as stderr:
            try:code=subprocess.run(cmd,stdout=stdout,stderr=stderr,timeout=210).returncode
            except subprocess.TimeoutExpired:code=None
        result=base.load(sub/'SUMMARY.json') if (sub/'SUMMARY.json').exists() else dict(success=False,reason='worker failed or timed out')
        result['process_exit']=code;result['success']=result['success'] and code==0;results[name]=result
        print(json.dumps(dict(stage=name,success=result['success'],counts=result.get('counts'),planned=result.get('planned'),process_exit=code)),flush=True)
    result=dict(success=all(r['success'] for r in results.values()),stages=results,scientific_sample_increase=False)
    base.save(out/'SUMMARY.json',result);return 0 if result['success'] else 1
if __name__=='__main__':raise SystemExit(main())
