#!/usr/bin/env python3
"""Replay retained fixed-order, paired-chain and pipeline evidence. No new sample."""
from pathlib import Path
import argparse, collections, hashlib, importlib.util, json, subprocess, sys, traceback
if not __debug__:raise RuntimeError('assertions-enabled Python is required')
sys.dont_write_bytecode=True
import reproduce_oracle as base
ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data/extended'
load=base.load;rows=base.rows;save=base.save;sha=base.sha

def module(relative):
    path=ROOT/'src'/relative
    name='portable_latest_'+hashlib.sha256(relative.encode()).hexdigest()[:16]
    spec=importlib.util.spec_from_file_location(name,path);result=importlib.util.module_from_spec(spec)
    sys.modules[name]=result;spec.loader.exec_module(result)
    assert Path(result.__file__).resolve().is_relative_to(ROOT)
    return result

def source(relative):
    path=DATA/relative
    if not path.exists():
        mapping={r['logical_package_path']:r for r in load(ROOT/'ALIASES.json')}
        row=mapping[str(path.relative_to(ROOT))];path=ROOT/row['canonical_package_path']
        assert sha(path)==row['sha256'] and path.stat().st_size==row['bytes']
    return path

def fixed(out,args):
    study=module('fixed_order_profile_02/study.py')
    units=load(source('fixed_order_profile_02/semantic01/INPUTS.json'))
    old={r['id']:r for r in rows(source('fixed_order_profile_02/semantic01/RAW.jsonl'))}
    assert len(units)==len(old)==24029 and {r['status'] for r in old.values()}=={'SUCCESS'}
    (out/'artifacts').mkdir()
    def one(u):
        actual=study.test_unit(u,out)
        expected={k:v for k,v in old[u['id']].items() if k not in ['id','status','seconds']}
        assert actual==expected
        return actual
    return base.run_units(out,units,one,args.quick,metadata=dict(known_units=24029,known_scalar_cells=1659762))

def fixed_controls(out,args):
    study=module('fixed_order_profile_02/study.py')
    spec=source('fixed_order_profile_02/semantic01/CONTROLS.json')
    (out/'CONTROLS.json').write_bytes(spec.read_bytes())
    counts=study.controls(out)
    actual=load(out/'CONTROL_RESULTS.json');expected=load(source('fixed_order_profile_02/semantic01/CONTROL_RESULTS.json'))
    assert actual==expected and counts=={'SUCCESS':63}
    result=dict(success=True,planned=63,counts=dict(counts),scientific_sample_increase=False)
    save(out/'SUMMARY.json',result);return result

def shared(out,args):
    study=module('fixed_order_profile_03/study.py')
    units=load(source('fixed_order_profile_03/semantic01/INPUTS.json'))
    controls=load(source('fixed_order_profile_02/semantic01/CONTROLS.json'))
    adversarial=load(source('fixed_order_profile_03/semantic01/ADVERSARIAL_INPUTS.json'))
    original=rows(source('fixed_order_profile_03/semantic01/RAW.jsonl'))
    work=[dict(kind='KNOWN',unit=u) for u in units]
    work += [dict(kind='OLD_CORRUPT',unit=dict(case=c,mutation=m)) for c in controls['base_cases'] for m in controls['mutations']]
    work += [dict(kind='ADVERSARIAL',unit=u) for u in adversarial]
    assert len(work)==len(original)==44838 and {r['status'] for r in original}=={'SUCCESS'}
    for k,u in enumerate(work):u['id']=str(k)
    def one(row):
        u=row['unit'];kind=row['kind'];prior=original[int(row['id'])];assert prior['kind']==kind
        if kind=='KNOWN':
            encoded=json.dumps(study.compiler.compile_case(u['case'],u['order']),sort_keys=True,separators=(',',':')).encode()
            digest=hashlib.sha256(encoded).hexdigest();d=json.loads(encoded);report=study.check.check(d)
            assert digest==prior['artifact_sha256'] and report==prior['report'] and not report['violations']
            return dict(artifact_sha256=digest,report=report)
        if kind=='OLD_CORRUPT':
            d=base.roundtrip(study.compiler.compile_case(u['case']))
            ok,detail=study.accepted(study.oldstudy.corrupt(d,u['mutation']))
            assert not ok and detail==prior['detail']
            return dict(accepted=ok,detail=detail)
        actual=study.adversarial(u)
        assert actual=={k:v for k,v in prior.items() if k not in ['id','kind','status','seconds']}
        return actual
    return base.run_units(out,work,one,args.quick,metadata=dict(known_units=24029,prior_corruptions=51,new_adversarial_inputs=20758))

def paired(out,args):
    study=module('paired_chain_hardness_01/check.py');study.ROOT=out;(out/'artifacts').mkdir()
    units=load(source('paired_chain_hardness_01/INPUTS.json'))
    original={r['id']:r for r in rows(source('paired_chain_hardness_01/RAW.jsonl'))}
    assert len(units)==len(original)==19786
    def one(u):
        actual=study.unit(u);prior=original[u['id']];assert prior['status']=='SUCCESS'
        assert actual=={k:v for k,v in prior.items() if k not in ['id','status','seconds']}
        assert actual['value']==3*u['D']+(not actual['source_partition'])
        return actual
    return base.run_units(out,units,one,args.quick,metadata=dict(known_units=19786,positive=9102,negative=10684))

def integration(out,args):
    study=module('dispatch_integration_01/study.py')
    inp=load(source('dispatch_integration_01/INPUTS.json'));original=load(source('dispatch_integration_01/RAW.json'))
    units=[dict(id=str(i),row=r) for i,r in enumerate(original)];assert len(units)==15
    def one(u):
        row=u['row'];kind,key=row['kind'],row['key']
        actual=study.correct(inp['cases'][key],inp['expected_routes'][key],inp['budgets']) if kind=='CASE' else study.control(key,inp['cases']) if kind=='CONTROL' else study.slow(key)
        assert row['status']=='SUCCESS' and actual==row['result']
        return actual
    return base.run_units(out,units,one,metadata=dict(known_units=15))

def scale(out,args):
    check=module('fixed_order_profile_03/checker.py');compiler=module('fixed_order_profile_02/persistent.py')
    old=rows(source('fixed_order_profile_02/scale01/RAW.jsonl'))
    current=rows(source('fixed_order_profile_03/scale01/RAW.jsonl'))
    assert len(old)==120 and len(current)==60
    counts={m:dict(collections.Counter(r['status'] for r in old if r['method']==m)) for m in ['persistent','current_hybrid']}
    assert counts=={'persistent':{'SUCCESS':42,'TIMEOUT':18},'current_hybrid':{'SUCCESS':36,'TIMEOUT':24}}
    assert collections.Counter(r['status'] for r in current)=={'SUCCESS':54,'TIMEOUT':6}
    prior={r['input_id']:r for r in old if r['method']=='persistent'}
    for r in current:
        path=source('fixed_order_profile_03/scale01/units/'+r['id']+'/artifact.json')
        assert sha(path)==r['construction_before_check']['artifact_sha256']==prior[r['id']]['construction_before_check']['artifact_sha256']
    save(out/'HISTORICAL_COUNTS.json',dict(previous=counts,current={'SUCCESS':54,'TIMEOUT':6},all_60_artifact_hashes_equal=True,timeout_units_rerun=0))
    units=[dict(id=r['id'],row=r) for r in current if r['status']=='SUCCESS']
    def one(u):
        r=u['row'];d=load(source('fixed_order_profile_03/scale01/units/'+r['id']+'/artifact.json'))
        report=check.check(d);assert report==r['report'] and not report['violations']
        values=[compiler.value(d,b) for b in r['budgets']];assert values==r['values']
        return dict(values=values,report=report,artifact_sha256=r['artifact_sha256'])
    return base.run_units(out,units,one,limit=20,metadata=dict(saved_successes=54,all_retained_outcomes=180,benchmark_constructors_called=0,original_timeout_units_rerun=0))

def pipeline(out,args):
    check=module('sweep_certificate_02/certificate.py');packed=module('dependency_hybrid_check_02/check.py')
    hybrid=module('dependency_hybrid_01/hybrid.py')
    original=rows(source('sweep_pipeline_01/run01/RAW.jsonl'));assert len(original)==48
    assert collections.Counter(r['status'] for r in original)=={'SUCCESS':45,'TIMEOUT':3}
    save(out/'HISTORICAL_COUNTS.json',dict(SUCCESS=45,TIMEOUT=3,FAILURE=0,INVALID=0,NOT_RUN=0,timeout_units_rerun=0))
    units=[dict(id=r['id'],row=r) for r in original if r['status']=='SUCCESS']
    def one(u):
        r=u['row'];path=source('sweep_pipeline_01/run01/units/'+r['id']+'/artifact.json')
        assert sha(path)==r['artifact_sha256'];d=load(path)
        report=(packed if d['route']=='ordered' else check).check(d);assert not report['violations']
        values=[hybrid.value(hybrid.load(d),b) for b in r['budgets']];assert values==r['values']
        return dict(values=values,report=report,artifact_sha256=r['artifact_sha256'])
    return base.run_units(out,units,one,limit=15,metadata=dict(saved_successes=45,historical_units=48,benchmark_constructors_called=0,original_timeout_units_rerun=0))

STAGES=['fixed','fixed_controls','shared','paired','integration','scale','pipeline']
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['verify','all']+STAGES)
    parser.add_argument('--out',type=Path,required=True);parser.add_argument('--quick',action='store_true')
    parser.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args();assert sys.version_info>=(3,10)
    out=args.out.resolve();assert not out.is_relative_to(ROOT),'output must be outside package'
    functions=dict(fixed=fixed,fixed_controls=fixed_controls,shared=shared,paired=paired,integration=integration,scale=scale,pipeline=pipeline)
    if args.worker:
        assert out.is_dir() and not any(out.iterdir())
        try:result=functions[args.mode](out,args)
        except Exception:
            save(out/'HARNESS_ERROR.json',dict(utc=base.now(),error=traceback.format_exc()));raise
        return 0 if result['success'] else 1
    verified=base.verify();out.mkdir(parents=True,exist_ok=False)
    save(out/'START.json',dict(utc=base.now(),mode=args.mode,verification=verified,quick_smoke=args.quick,python=sys.executable,scientific_sample_increase=False))
    results={}
    for stage in STAGES if args.mode=='all' else ([] if args.mode=='verify' else [args.mode]):
        sub=out/stage;sub.mkdir();cmd=[sys.executable,'-B',str(Path(__file__).resolve()),stage,'--out',str(sub),'--worker']
        if args.quick:cmd.append('--quick')
        with (out/(stage+'-stdout.txt')).open('xb') as stdout,(out/(stage+'-stderr.txt')).open('xb') as stderr:
            try:code=subprocess.run(cmd,stdout=stdout,stderr=stderr,timeout=210).returncode
            except subprocess.TimeoutExpired:code=None
        result=load(sub/'SUMMARY.json') if (sub/'SUMMARY.json').exists() else dict(success=False,reason='worker failed or timed out')
        result['process_exit']=code;result['success']=result['success'] and code==0;results[stage]=result
        print(json.dumps(dict(stage=stage,success=result['success'],counts=result.get('counts'),planned=result.get('planned'),process_exit=code)),flush=True)
    result=dict(success=all(r['success'] for r in results.values()),stages=results,scientific_sample_increase=False)
    save(out/'SUMMARY.json',result);return 0 if result['success'] else 1
if __name__=='__main__':raise SystemExit(main())
