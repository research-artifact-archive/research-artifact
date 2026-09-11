"""Stage58: execute fixed DAG evaluators and every filter input, preserving timeout history."""
from pathlib import Path
import collections, concurrent.futures, gzip, importlib.util, json, shutil, sys, time
from replay04_common import *
NAMES=['charged_dag_boundary_01','charged_general_01','charged_general_proof_audit_01','charged_general_filter_check_01','charged_residual_01','residual_safety_01']

def filter_part(root,out,stream):
    arm(170)
    a=root/'charged_general_filter_check_01/attempt01'
    work=out/'code';work.mkdir(parents=True)
    selected=root/'charged_general_filter_check_01/attempt02' if stream else a
    for name in ['checker.py','reference.py','target_filter01.py']:
        shutil.copyfile(selected/name,work/name)
    # The complete stream replay uses the already frozen attempt02 snapshot-copy
    # optimization on ALL original stream inputs. Target and assertions unchanged.
    if stream:
        diff=''.join(difflib.unified_diff((a/'checker.py').read_text().splitlines(True),(work/'checker.py').read_text().splitlines(True),fromfile='attempt01/checker.py',tofile='replay/attempt02-checker.py'))
        (out/'HARNESS_DIFF.patch').write_text(diff)
        shutil.copyfile(a/'checker.py',out/'checker_attempt01_original.py')
    save(out/'EXECUTION_FREEZE.json',dict(files={n:digest(work/n) for n in ['checker.py','reference.py','target_filter01.py']},inputs_sha256=digest(a/'inputs.jsonl'),families=['streams'] if stream else ['initial','policies','named','invalid'],replay_only=True,original_timeout_replaced=False))
    sys.path.insert(0,str(work))
    from checker import Checker
    spec=importlib.util.spec_from_file_location('target',work/'target_filter01.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    cases=[json.loads(line) for line in (a/'inputs.jsonl').open()]
    output={}
    for family in (['streams'] if stream else ['initial','policies','named','invalid']):
        raw=out/(family+'_RAW.jsonl')
        with raw.open('x') as f:
            c=Checker(module.ChargedFilter,str(work/'target_filter01.py'),f)
            for case in cases:
                if case['family']==family:c.execute(case)
        output[family]=dict(counts=dict(c.counts),operation_maxima=dict(c.operation_maxima),raw_sha256=digest(raw))
        if not stream:
            original=json.loads((a/(family+'_RECEIPT.json')).read_text())
            assert original['status']=='PASS'
            assert output[family]['counts']==original['counts']
            assert output[family]['operation_maxima']==original['operation_maxima']
            assert output[family]['raw_sha256']==digest(a/(family+'_RAW.jsonl'))
    if stream:
        source={};overlap=0
        for attempt in ['attempt01','attempt02']:
            for line in (root/'charged_general_filter_check_01'/attempt/'streams_RAW.jsonl').open():
                row=json.loads(line);key=(row['id'],row['phase'],row.get('index'))
                if key in source:
                    assert source[key]==row,(key,'overlap changed')
                    overlap+=row['phase']=='step'
                source[key]=row
        fresh={}
        for line in (out/'streams_RAW.jsonl').open():
            row=json.loads(line);key=(row['id'],row['phase'],row.get('index'))
            assert key not in fresh;fresh[key]=row
        assert fresh==source,'fresh full stream rows differ from frozen union'
        assert overlap==2638
        assert c.counts['inputs_completed']==39 and c.counts['stream_steps']==20478
        assert json.loads((a/'streams_RECEIPT.json').read_text())['status']=='TIMEOUT'
        output['coverage']=dict(series=39,unique_steps=20478,historical_overlapping_steps=overlap,all_rows_equal=True,retained_attempt01_timeout=True)
    save(out/'RESULT.json',dict(status='SUCCESS',families=output,replay_only=True))

def dag_part(root,out):
    arm(170)
    src=root/'charged_dag_boundary_01';work=out/'code';work.mkdir(parents=True)
    for p in src.iterdir():
        if p.is_file():shutil.copyfile(p,work/p.name)
    # Existing scientific dependencies are copied from verified public rows.
    for d in ['charged_residual_01','residual_safety_01']:
        shutil.copytree(root/d,out/d)
    cutoff='end=min(start+120,start+max(0,datetime.datetime(2026,9,11,4,18,tzinfo=datetime.timezone.utc).timestamp()-time.time()))'
    results={}
    for i in [1,2,3]:
        code=work/f'check0{i}.py'
        edit(code,cutoff,'end=start+120',out/f'adaptations0{i}')
        save(out/f'EXECUTION_FREEZE0{i}.json',dict(script_sha256=digest(code),inputs='unchanged fixed generator population',timeout_seconds=120,replay_only=True))
        run([sys.executable,'-B',str(code)],out/f'process0{i}',timeout=125)
        fixed=src/f'run0{i}';new=work/f'run0{i}'
        summary=json.loads((new/'SUMMARY.json').read_text());stored=json.loads((fixed/'SUMMARY.json').read_text())
        for key in stored:
            if key not in ['seconds','finished_utc']:assert summary[key]==stored[key],(i,key)
        for p in fixed.iterdir():
            if p.name in ['START.json','SUMMARY.json']:continue
            fresh=(new/p.name).read_bytes();old=p.read_bytes()
            if p.name.endswith('.gz'):fresh=gzip.decompress(fresh);old=gzip.decompress(old)
            assert fresh==old,(i,p.name,'all deterministic raw bytes')
        results[f'run0{i}']=summary
    save(out/'RESULT.json',dict(status='SUCCESS',runs=results,all_deterministic_raw_equal=True,replay_only=True))

def main():
    if sys.argv[1].startswith('_'):
        part,root,out=sys.argv[1],Path(sys.argv[2]).resolve(),Path(sys.argv[3]).resolve()
        if part=='_dag':dag_part(root,out)
        else:filter_part(root,out,part=='_streams')
        return
    stage,out=sys.argv[1],Path(sys.argv[2]).resolve();assert stage=='charged-general';arm(175);start=time.monotonic()
    root=out/'fixed';root.mkdir();mapping=unpack(root,NAMES)
    for attempt in ['attempt01','attempt02']:
        check_freeze(root,mapping,'charged_general_filter_check_01/'+attempt)
    check_general_history(root,mapping)
    save(out/'REPLAY_PROTOCOL.json',dict(stage=stage,parts=['dag','initial-four','all-streams'],deadline_seconds=175,original_270s_attempt_not_repeated=True,replay_not_new_attempt=True))
    tasks=[('_dag','dag'),('_families','families'),('_streams','streams')]
    results=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        pending=[executor.submit(run,[sys.executable,'-B',str(Path(__file__).resolve()),part,str(root),str(out/name)],out/(name+'-process'),170) for part,name in tasks]
        for future in pending:results.append(future.result())
    save(out/'SUMMARY.json',dict(status='SUCCESS',stage=stage,seconds=time.monotonic()-start,dag_games=[13104,117728,12288],initial_states=42260,initial_queries=192540,initial_actions=577620,policy_prefixes=20655,policy_leaves=13341,stream_series=39,stream_unique_steps=20478,historical_overlap_steps=2638,retained_timeouts=1,all_deterministic_raw_equal=True,replay_only=True,new_native_measurements=0,new_evaluation_population=False,processes=results))
if __name__=='__main__':main()
