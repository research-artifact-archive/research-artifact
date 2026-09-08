#!/usr/bin/env python3
"""Portable reproduction harness; saved scientific sources/results are unchanged."""
from pathlib import Path
import argparse,collections,datetime,hashlib,importlib,json,os,platform,shutil,signal,subprocess,sys,time,traceback
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(path,value):
    with path.open('x') as f:json.dump(value,f,indent=2,sort_keys=True);f.write('\n')
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def verify():
    m=json.loads((ROOT/'MANIFEST.json').read_text())
    for row in m['files']:
        p=ROOT/row['path'];assert not p.is_symlink() and p.is_file()
        assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],row['path']
    return dict(files=len(m['files']),manifest_sha256=sha(ROOT/'MANIFEST.json'))
def module(directory,name):
    sys.path.insert(0,str(ROOT/'src'/directory))
    m=importlib.import_module(name)
    assert Path(m.__file__).resolve().is_relative_to(ROOT)
    return m
def deadline(signum,frame):raise TimeoutError('per-input limit')
def semantic(out,quick):
    directory=out/'semantic';directory.mkdir();m=module('final_evaluation_dag_01','evaluate_final')
    for imported in [m.original,m.original.primitive,m.original.hybrid,m.original.bellman,m.original.packed,m.original.structure,m.lemmas,m.original.primitive.reuse]:
        assert Path(imported.__file__).resolve().is_relative_to(ROOT),imported.__file__
    inputs=json.loads((ROOT/'data/semantic/INPUTS.json').read_text())
    recorded=[json.loads(x) for x in (ROOT/'data/semantic/RAW.jsonl').read_text().splitlines()]
    assert [c['id'] for c in inputs]==[r['input_id'] for r in recorded]
    if quick:
        selected=[];seen=set()
        for case,row in zip(inputs,recorded):
            key=(case['shape_id'],row['route'])
            if key not in seen:selected.append((case,row));seen.add(key)
    else:selected=list(zip(inputs,recorded))
    save(directory/'START.json',dict(utc=now(),input_ids=[c['id'] for c,_ in selected],quick_smoke=quick,previously_observed_inputs=True,per_case_seconds=10,total_seconds=180))
    fields=['status','roots','defects','states','actions','outcomes','invariant_cells','policy_cells','rank_rounds','route','certificate','artifact_bytes','artifact_sha256','lemma_checks']
    signal.signal(signal.SIGALRM,deadline);start=time.perf_counter();counts=collections.Counter()
    with (directory/'RAW.jsonl').open('x') as f:
        for k,(case,expected) in enumerate(selected):
            row=dict(input_id=case['id'])
            if time.perf_counter()-start>=180:row.update(status='NOT_RUN',reason='stage deadline')
            else:
                try:
                    signal.alarm(10);actual,encoded=m.evaluate(case)
                    mismatches={field:dict(expected=expected.get(field),actual=actual.get(field)) for field in fields if actual.get(field)!=expected.get(field)}
                    row.update(status='FAILURE' if mismatches else 'SUCCESS',mismatches=mismatches,actual=actual)
                except TimeoutError:row.update(status='TIMEOUT')
                except AssertionError:row.update(status='FAILURE',error=traceback.format_exc())
                except Exception:row.update(status='INVALID',error=traceback.format_exc())
                finally:signal.alarm(0)
            counts[row['status']]+=1;f.write(json.dumps(row,separators=(',',':'))+'\n');f.flush()
            if (k+1)%512==0:print(json.dumps(dict(stage='semantic',completed=k+1,total=len(selected),outcomes=dict(counts))),flush=True)
    result=dict(planned=len(selected),outcomes=dict(counts),elapsed_seconds=time.perf_counter()-start,all_numerical_fields_match=counts['SUCCESS']==len(selected),quick_smoke=quick)
    save(directory/'SUMMARY.json',result);return result
def native(out,quick,java,javac):
    directory=out/'native';directory.mkdir();data=json.loads((ROOT/'data/native/INPUTS.json').read_text())
    expected=data['units'];selected_cases={'native-final-00','native-final-08','parent-postwrite-ordered','parent-postwrite-ideal'}
    if quick:expected=[u for u in expected if u['case'] in selected_cases]
    expected_ids={u['id'] for u in expected}
    for name in ('CASES.tsv',):shutil.copy2(ROOT/'data/native'/name,directory/name)
    shutil.copytree(ROOT/'data/native/profiles',directory/'profiles')
    lines=(ROOT/'data/native/INPUTS.tsv').read_text().splitlines()
    with (directory/'INPUTS.tsv').open('x') as f:
        for line in lines:
            if line.split('\t',1)[0] in expected_ids:f.write(line+'\n')
    java=java or shutil.which('java');javac=javac or shutil.which('javac')
    if not java or not javac:raise RuntimeError('Java and javac required; use --java/--javac if outside PATH')
    source=ROOT/'src/final_evaluation_dag_native_01/NativeDagFinal.java'
    save(directory/'START.json',dict(utc=now(),planned=len(expected),quick_smoke=quick,java_executable_sha256=sha(Path(java)),javac_executable_sha256=sha(Path(javac)),compile_cap_seconds=30,execute_cap_seconds=120))
    times={};receipt={};t=time.perf_counter()
    try:
        c=subprocess.run([javac,'-d',str(directory/'classes'),str(source)],capture_output=True,text=True,timeout=30)
        receipt['compile']=dict(exit=c.returncode,stdout=c.stdout,stderr=c.stderr)
    except subprocess.TimeoutExpired:receipt['compile']=dict(exit=None,timeout=True)
    times['compile_seconds']=time.perf_counter()-t
    if receipt['compile'].get('exit')==0:
        t=time.perf_counter()
        with (directory/'RAW.jsonl').open('xb') as f,(directory/'STDERR.txt').open('xb') as err:
            try:
                p=subprocess.run([java,'-Xmx256m','-XX:ActiveProcessorCount=1','-cp',str(directory/'classes'),'NativeDagFinal',str(directory)],stdout=f,stderr=err,timeout=120)
                receipt['execute']=dict(exit=p.returncode,timeout=False)
            except subprocess.TimeoutExpired:receipt['execute']=dict(exit=None,timeout=True)
        times['execute_seconds']=time.perf_counter()-t
    save(directory/'PROCESS_RECEIPT.json',dict(process=receipt,times=times))
    t=time.perf_counter();dev=module('dependency_native_01','experiment')
    observed=collections.defaultdict(list);parse=[]
    raw_path=directory/'RAW.jsonl'
    if raw_path.exists():
        for line_no,line in enumerate(raw_path.read_text().splitlines(),1):
            try:
                row=json.loads(line);observed[row['id']].append(row)
            except Exception as e:parse.append(dict(line=line_no,error=repr(e)))
    counts=collections.Counter();adverse=[];good={}
    for unit in expected:
        rows=observed.pop(unit['id'],[]);issues=[]
        if not rows:status='NOT_RUN'
        elif len(rows)!=1:status='INVALID'
        else:
            row=rows[0];status=row['status']
            reconstructed=dev.expected(data['cases'][unit['case']],unit)
            assert reconstructed==unit['expected']
            if status=='SUCCESS':
                issues=[dict(field=k,expected=v,actual=row.get(k)) for k,v in reconstructed.items() if row.get(k)!=v]
                if issues:status='FAILURE'
                else:good[unit['id']]=row
        counts[status]+=1
        if status!='SUCCESS':adverse.append(dict(id=unit['id'],status=status,issues=issues,raw=rows))
    groups=collections.defaultdict(list)
    for u in expected:groups[u['cell'],u['kind']].append(u)
    maximum_issues=[]
    for cell in data['cells']:
        for policy in cell['policies']:
            units=groups[cell['id'],policy['kind']]
            if not units:continue
            if all(u['id'] in good for u in units):
                actual=max(good[u['id']]['cost'] for u in units)
                if actual!=policy['expected_max']:maximum_issues.append(dict(cell=cell['id'],policy=policy['kind'],actual=actual,expected=policy['expected_max']))
    times['checking_seconds']=time.perf_counter()-t
    result=dict(planned=len(expected),outcomes=dict(counts),parse_errors=parse,unexpected_ids=list(observed),adverse=adverse,maximum_issues=maximum_issues,times=times,process=receipt,quick_smoke=quick)
    result['all_numerical_fields_match']=counts['SUCCESS']==len(expected) and not(parse or observed or maximum_issues) and receipt.get('execute',{}).get('exit')==0
    save(directory/'SUMMARY.json',result);return result
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['verify','semantic','native','all'])
    parser.add_argument('--out',type=Path,required=True,help='New output directory; existing directories are refused')
    parser.add_argument('--quick',action='store_true',help='Small known-input smoke test; not full reproduction')
    parser.add_argument('--java');parser.add_argument('--javac');args=parser.parse_args()
    assert sys.version_info>=(3,10) and not sys.flags.optimize,'Python3.10+ with assertions enabled is required'
    verified=verify();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    save(out/'START.json',dict(utc=now(),mode=args.mode,quick=args.quick,verification=verified,python_version=sys.version,platform=platform.platform(),scientific_sample_increase=False))
    result={}
    if args.mode in ('semantic','all'):result['semantic']=semantic(out,args.quick)
    if args.mode in ('native','all'):result['native']=native(out,args.quick,args.java,args.javac)
    success=all(r['all_numerical_fields_match'] for r in result.values())
    save(out/'SUMMARY.json',dict(utc=now(),success=success,results=result,scientific_sample_increase=False))
    print(json.dumps(dict(success=success,results={k:{a:v for a,v in r.items() if a in ('planned','outcomes','elapsed_seconds','times','all_numerical_fields_match')} for k,r in result.items()}),indent=2))
    return 0 if success else 1
if __name__=='__main__':raise SystemExit(main())
