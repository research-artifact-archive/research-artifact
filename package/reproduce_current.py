#!/usr/bin/env python3
"""Replay known sweep/common-price results with no scientific sample increase."""
from pathlib import Path
import argparse
import collections
import hashlib
import json
import shutil
import subprocess
import sys
import time
import traceback

if not __debug__:raise RuntimeError('assertions-enabled Python is required')
sys.dont_write_bytecode=True
import reproduce_oracle as base

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data/extended'
load=base.load
rows=base.rows
save=base.save
sha=base.sha
module=base.module
roundtrip=base.roundtrip


def source_data(relative):
    path=Path(relative)
    assert not path.is_absolute() and '..' not in path.parts
    if path.parts[0]=='final_evaluation_dag_01':return ROOT/'data/semantic'/Path(*path.parts[1:])
    return DATA/path


def algebra(out,args):
    check=module('sweep_certificate_02/certificate.py')
    d=DATA/'sweep_certificate_02'
    units=rows(d/'ALGEBRA_INPUTS.jsonl')
    expected={r['id']:r for r in rows(d/'run01/algebra/RAW.jsonl')}
    assert len(units)==len(expected)==83125
    def one(u):
        full=check.interval_identity(u['protected'],u['fast'],u['span'])
        chosen=check.interval_identity(u['protected'],u['fast'],u['span'],u['selected_fast'])
        brute=[];selected=[]
        for t in range(u['span']+1):
            protected=[a+d*t for a,d in u['protected']]
            fast=[max(a+d*t,b+e*t) for (a,d),(b,e) in u['fast']]
            brute.append(min(protected+fast))
            selected.append(min(protected+[fast[u['selected_fast']]]))
        assert full['ok']==all(v==0 for v in brute)
        assert chosen['ok']==(all(v>=0 for v in brute) and all(v==0 for v in selected))
        if not full['ok']:assert brute[full['offset']]!=0
        if not chosen['ok']:assert brute[chosen['offset']]<0 or selected[chosen['offset']]!=0
        old=expected[u['id']];assert old['status']=='SUCCESS'
        actual=dict(accepted=full['ok'],selected_accepted=chosen['ok'],
            negative_witness=full.get('offset'),selected_negative_witness=chosen.get('offset'))
        assert actual==old['result']
        return actual
    return base.run_units(out,units,one,args.quick,metadata=dict(known_units=83125,coverage_contracts=2))


def sweep_certificates(out,args,benchmark=False):
    check=module('sweep_certificate_02/certificate.py')
    d=DATA/'sweep_certificate_02'
    units=load(d/('BENCH_INPUTS.json' if benchmark else 'CERTIFICATE_INPUTS.json'))
    count=36 if benchmark else 1296
    assert len(units)==count
    if benchmark:
        original=rows(d/'compare01/RAW.jsonl')
        assert len(original)==72
        assert collections.Counter((r['method'],r['status']) for r in original)=={
            ('previous','SUCCESS'):36,('sweep','SUCCESS'):36}
    def one(u):
        path=source_data(u['path']);assert sha(path)==u['sha256']
        report=check.check(load(path));assert not report['violations']
        assert report['directly_checked_stored_policy_attainment']
        return dict(artifact_sha256=u['sha256'],report=report)
    return base.run_units(out,units,one,False if benchmark else args.quick,limit=10,
        metadata=dict(known_certificates=count,constructor_calls=0,original_timeout_units_rerun=0,
            historical_comparison_units=72 if benchmark else 0))


def sweep_controls(out,args):
    check=module('sweep_certificate_02/certificate.py')
    units=load(DATA/'sweep_certificate_02/CONTROL_INPUTS.json');assert len(units)==25
    assert collections.Counter(u['expected'] for u in units)=={'ACCEPT':1,'REJECT':24}
    def one(u):
        try:accepted=not check.check(roundtrip(u['data']))['violations']
        except (AssertionError,TypeError,ValueError,KeyError,IndexError):accepted=False
        actual='ACCEPT' if accepted else 'REJECT'
        assert actual==u['expected']
        return dict(actual=actual,expected=u['expected'])
    return base.run_units(out,units,one,metadata=dict(valid_controls=1,rejection_controls=24))


def exposure(out,args,version):
    d=DATA/f'critical_exposure_0{version}'
    units=rows(d/'INPUTS.jsonl');old=rows(d/'RAW.jsonl')
    expected={u['id']:u for u in old}
    known_count=27105 if version==1 else 66560
    known_roots=220701 if version==1 else 936832
    assert len(units)==len(old)==len(expected)==known_count
    assert {u['id'] for u in units}==set(expected)
    assert sum(len(u['budgets']) for u in units)==known_roots
    assert collections.Counter(r['status'] for r in old)=={'SUCCESS':known_count}
    assert sum(r['maximum_gap']>0 for r in old)==(0 if version==1 else 7)
    hybrid=module('dependency_hybrid_01/hybrid.py')
    check=module('sweep_certificate_02/certificate.py')
    packed=module('dependency_hybrid_check_02/check.py')
    reference=module('critical_exposure_02/study.py')
    def one(u):
        prior=expected[u['id']]
        path=d/'artifacts'/(u['id']+'.json')
        assert sha(path)==prior['artifact_sha256']
        constructed=hybrid.compile_case(u['case'])
        encoded=json.dumps(constructed,sort_keys=True,separators=(',',':')).encode()
        assert hashlib.sha256(encoded).hexdigest()==prior['artifact_sha256']
        data=json.loads(encoded)
        report=(packed if data['route']=='ordered' else check).check(data)
        assert not report['violations']
        loaded=hybrid.load(data)
        actual=[hybrid.value(loaded,b) for b in u['budgets']]
        scalar,fixed,orders,order_count=reference.finite_reference(u['case'],max(u['budgets']))
        assert actual==scalar==prior['values']
        assert fixed==prior['fixed_values'] and orders==prior['best_fixed_orders']
        assert order_count==prior['topological_orders']
        gaps=[f-v for f,v in zip(fixed,actual)]
        assert gaps==prior['gaps']
        return dict(values=actual,fixed_values=fixed,maximum_gap=max(gaps),
            topological_orders=order_count,artifact_sha256=prior['artifact_sha256'])
    return base.run_units(out,units,one,args.quick,limit=5,
        metadata=dict(known_units=known_count,known_roots=known_roots,original_strict_units=0 if version==1 else 7))


def simplified(out,args):
    d=DATA/'critical_exposure_simplify_01';original=rows(d/'RAW.jsonl')
    counts=collections.Counter(r['status'] for r in original)
    assert counts=={'SUCCESS':3251,'CACHED_REFERENCE':1054,'SELECTED_SUCCESSOR':84}
    units=[r for r in original if r['status']=='SUCCESS']
    reference=module('critical_exposure_02/study.py')
    def one(u):
        x=u['case'];case=dict(cp=[[2*w,x['q']*w] for w in x['work']],edges=x['edges'])
        scalar,fixed,orders,count=reference.finite_reference(case,len(u['values'])-1)
        assert scalar==u['values'] and fixed==u['fixed_values']
        assert orders==u['best_fixed_orders'] and count==u['topological_orders']
        return dict(values=scalar,fixed_values=fixed,topological_orders=count)
    return base.run_units(out,units,one,args.quick,limit=5,
        metadata=dict(original_unique_cases=3251,original_cached_references=1054,original_selected_successors=84))


def uniform_semantic(out,args):
    sys.path.insert(0,str(ROOT/'src/final_evaluation_dag_01'))
    import evaluate_final as reference
    assert Path(reference.__file__).resolve().is_relative_to(ROOT)
    check=module('sweep_certificate_02/certificate.py')
    d=DATA/'critical_exposure_operational_01'
    case=load(d/'CASE.json');old=load(d/'SEMANTIC_RESULT.json')
    def one(u):
        result,encoded=reference.evaluate(u)
        assert result['status']=='SUCCESS' and result['defects']==[]
        assert hashlib.sha256(encoded).hexdigest()==old['artifact_sha256']
        for field in ['roots','states','actions','outcomes','invariant_cells','policy_cells','rank_rounds','route','lemma_checks']:
            assert result[field]==old[field],field
        report=check.check(json.loads(encoded));assert not report['violations']
        assert report==old['policy_sweep']
        return dict(roots=result['roots'],states=result['states'],actions=result['actions'],
            outcomes=result['outcomes'],artifact_sha256=old['artifact_sha256'],policy_sweep=report)
    return base.run_units(out,[case],one,limit=20,metadata=dict(selected_after_gap_exploration=True))


def uniform_native(out,args):
    d=DATA/'critical_exposure_operational_01'
    data=load(d/'NATIVE_INPUTS.json');units=data['units']
    assert len(units)==len({u['id'] for u in units})==746
    assert len(data['cells'])==10 and sum(len(c['policies']) for c in data['cells'])==50
    case=next(iter(data['cases'].values()))
    assert case['d']==24 and case['weights']==[36]*5
    java=args.java or shutil.which('java');javac=args.javac or shutil.which('javac')
    assert java and javac,'JDK17+ is required'
    save(out/'START.json',dict(utc=base.now(),planned_ids=[u['id'] for u in units],
        scientific_sample_increase=False,selected_after_gap_exploration=True,
        compile_seconds=30,execute_seconds=60,java=java,javac=javac))
    for name in ['CASES.tsv','INPUTS.tsv']:shutil.copy2(d/name,out/name)
    shutil.copytree(d/'profiles',out/'profiles');(out/'classes').mkdir()
    source=d/'NativeDagFinal.java';phase={}
    start=time.monotonic()
    try:
        p=subprocess.run([javac,'-d',str(out/'classes'),str(source)],capture_output=True,text=True,timeout=30)
        phase['compile']=dict(exit=p.returncode,timeout=False,stdout=p.stdout,stderr=p.stderr,
            seconds=time.monotonic()-start)
    except subprocess.TimeoutExpired as e:
        phase['compile']=dict(exit=None,timeout=True,stdout=str(e.stdout),stderr=str(e.stderr),
            seconds=time.monotonic()-start)
    save(out/'COMPILE.json',phase['compile'])
    if phase['compile']['exit']==0:
        save(out/'CLASS_HASHES.json',[dict(name=p.name,sha256=sha(p)) for p in sorted((out/'classes').glob('*.class'))])
        start=time.monotonic()
        with (out/'NATIVE_RAW.jsonl').open('xb') as stdout,(out/'STDERR.txt').open('xb') as stderr:
            try:
                p=subprocess.run([java,'-Xmx256m','-XX:ActiveProcessorCount=1','-cp',str(out/'classes'),
                    'NativeDagFinal',str(out)],stdout=stdout,stderr=stderr,timeout=60)
                phase['execute']=dict(exit=p.returncode,timeout=False,seconds=time.monotonic()-start)
            except subprocess.TimeoutExpired:
                phase['execute']=dict(exit=None,timeout=True,seconds=time.monotonic()-start)
    save(out/'PHASES.json',phase)
    dev=module('dependency_native_01/experiment.py')
    observed=collections.defaultdict(list);order=[];parse=[]
    raw=out/'NATIVE_RAW.jsonl'
    if raw.exists():
        for i,line in enumerate(raw.read_text().splitlines()):
            try:
                r=json.loads(line);observed[r['id']].append(r);order.append(r['id'])
            except Exception as e:parse.append(dict(line=i,error=repr(e)))
    good={};counts=collections.Counter();adverse=[]
    with (out/'UNIT_OUTCOMES.jsonl').open('x') as stream:
        for u in units:
            actual=observed.pop(u['id'],[]);issues=[]
            if not actual:status='NOT_RUN'
            elif len(actual)!=1:status='INVALID'
            else:
                r=actual[0];status=r.get('status','INVALID')
                if status not in {'SUCCESS','FAILURE','TIMEOUT','INVALID','NOT_RUN'}:status='INVALID'
                expected=dev.expected(data['cases'][u['case']],u)
                assert expected==u['expected']
                if status=='SUCCESS':
                    issues=[dict(field=k,expected=v,actual=r.get(k)) for k,v in expected.items() if r.get(k)!=v]
                    if issues:status='FAILURE'
                    else:good[u['id']]=r
            row=dict(id=u['id'],status=status,issues=issues)
            counts[status]+=1;stream.write(json.dumps(row,separators=(',',':'))+'\n')
            if status!='SUCCESS':adverse.append(row)
    comparisons=[]
    for cell in data['cells']:
        for policy in cell['policies']:
            ids=[u['id'] for u in units if u['cell']==cell['id'] and u['kind']==policy['kind']]
            actual=max(good[i]['cost'] for i in ids) if all(i in good for i in ids) else None
            comparisons.append(dict(cell=cell['id'],kind=policy['kind'],expected=policy['expected_max'],actual=actual))
    save(out/'POLICY_MAXIMA.json',comparisons)
    correct=all(r['actual']==r['expected'] for r in comparisons)
    success=(counts['SUCCESS']==746 and not parse and not observed and correct
        and order==[u['id'] for u in units] and phase.get('execute',{}).get('exit')==0)
    result=dict(success=success,planned=746,counts=dict(counts),adverse=adverse,parse_errors=parse,
        unexpected_ids=list(observed),raw_order_matches=order==[u['id'] for u in units],
        policy_maxima_match=correct,scientific_sample_increase=False,phases=phase)
    save(out/'SUMMARY.json',result);return result


STAGES=['algebra','certificates','sweep_controls','sweep_bench','exposure1','exposure2',
    'simplified','uniform_semantic','uniform_native']


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=['verify','all']+STAGES)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--quick',action='store_true')
    p.add_argument('--java');p.add_argument('--javac')
    p.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    args=p.parse_args();assert sys.version_info>=(3,10)
    out=args.out.resolve();assert not out.is_relative_to(ROOT),'output must be outside the package'
    functions=dict(algebra=algebra,certificates=sweep_certificates,sweep_controls=sweep_controls,
        sweep_bench=lambda o,a:sweep_certificates(o,a,True),exposure1=lambda o,a:exposure(o,a,1),
        exposure2=lambda o,a:exposure(o,a,2),simplified=simplified,
        uniform_semantic=uniform_semantic,uniform_native=uniform_native)
    if args.worker:
        assert out.is_dir() and not any(out.iterdir())
        try:result=functions[args.mode](out,args)
        except Exception:
            save(out/'HARNESS_ERROR.json',dict(utc=base.now(),error=traceback.format_exc()))
            raise
        return 0 if result['success'] else 1
    verified=base.verify()
    out.mkdir(parents=True,exist_ok=False)
    save(out/'START.json',dict(utc=base.now(),mode=args.mode,verification=verified,quick_smoke=args.quick,
        python=sys.executable,python_version=sys.version,scientific_sample_increase=False))
    stages=STAGES if args.mode=='all' else ([] if args.mode=='verify' else [args.mode])
    results={}
    for stage in stages:
        sub=out/stage;sub.mkdir()
        cmd=[sys.executable,'-B',str(Path(__file__).resolve()),stage,'--out',str(sub),'--worker']
        if args.quick:cmd.append('--quick')
        if args.java:cmd+=['--java',args.java]
        if args.javac:cmd+=['--javac',args.javac]
        with (out/(stage+'-stdout.txt')).open('xb') as stdout,(out/(stage+'-stderr.txt')).open('xb') as stderr:
            try:
                process=subprocess.run(cmd,stdout=stdout,stderr=stderr,timeout=210)
                code=process.returncode
            except subprocess.TimeoutExpired:code=None
        result=load(sub/'SUMMARY.json') if (sub/'SUMMARY.json').exists() else dict(success=False,reason='worker failed or timed out')
        result['process_exit']=code;result['success']=result['success'] and code==0
        results[stage]=result
        print(json.dumps(dict(stage=stage,success=result['success'],counts=result.get('counts'),
            planned=result.get('planned'),process_exit=code)),flush=True)
    result=dict(success=all(r['success'] for r in results.values()),stages=results,scientific_sample_increase=False)
    save(out/'SUMMARY.json',result)
    return 0 if result['success'] else 1


if __name__=='__main__':raise SystemExit(main())
