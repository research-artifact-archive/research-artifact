"""Recompute finite cost studies and analyze complete saved native observations."""
from pathlib import Path
import collections,hashlib,json,shutil,subprocess,sys,time

HERE=Path(__file__).resolve().parent
SOURCE=HERE/'evidence/RESUMED_20260910_1617'
OUT=Path(sys.argv[2])
assert __debug__ and sys.argv[1]=='source-cost-boundaries'
started=time.monotonic();steps=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def rows(p):return [json.loads(x) for x in p.read_text().splitlines()]
def copy(src,dst):dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
def run(label,argv):
    t=time.monotonic()
    with (OUT/(label+'.stdout')).open('xb') as so,(OUT/(label+'.stderr')).open('xb') as se:
        p=subprocess.run(argv,stdout=so,stderr=se,timeout=240)
    assert p.returncode==0,(label,p.returncode)
    steps.append({'step':label,'seconds':time.monotonic()-t,'returncode':p.returncode})
def same_json(a,b,skip=()):
    x=read(a);y=read(b)
    assert set(x)==set(y),(a,'keys')
    assert {k:v for k,v in x.items() if k not in skip}=={k:v for k,v in y.items() if k not in skip},a

for folder,files in [
    ('general_cost_01',['SINGLE_JOB_RESULTS.json','HETEROGENEOUS_ROWS.jsonl']),
    ('optional_preparation_01',['ROWS.jsonl','ERRORS.json','FORMULA_GAPS.json','OLD_REGRET_BOUND_COUNTEREXAMPLES.json','S_MONOTONICITY_COUNTEREXAMPLES.json','NATIVE_SCALAR_FIXTURE.json'])]:
    src=SOURCE/folder;dst=OUT/folder;copy(src/'check01.py',dst/'check01.py')
    run(folder,[sys.executable,'-B',str(dst/'check01.py')])
    for f in files:assert sha(dst/f)==sha(src/f),(folder,f)
    same_json(dst/'RESULT.json',src/'RESULT.json',{'utc','seconds','script_sha256'})

src=SOURCE/'valkey_refresh_02';dst=OUT/'valkey_refresh_02'
for f in ['oracle01.py','model.py','ORACLE_PLAN.md']:copy(src/f,dst/f)
run('full_policy_vector_oracle',[sys.executable,'-B',str(dst/'oracle01.py')])
assert sha(src/'oracle_run01/ROWS.jsonl')==sha(dst/'oracle_run01/ROWS.jsonl')
same_json(dst/'oracle_run01/RESULT.json',src/'oracle_run01/RESULT.json',{'seconds'})
assert read(dst/'oracle_run01/RESULT.json')['completed']==756

# A native row is replayed as recorded evidence, never as a new execution.
native_counts={}
for folder,prefixes,expected in [('valkey_manifest_01',[''],7119),('valkey_refresh_02',['instrumented_','unmodified_'],11865)]:
    src=SOURCE/folder/'run01';manifest=read(src/'INPUT_MANIFEST.json')
    configs={c['id']:c for c in manifest['configurations']}
    curves_by_binary=[]
    for prefix in prefixes:
        data=rows(src/(prefix+'ROWS.jsonl'));assert len(data)==expected
        groups=collections.defaultdict(list)
        for a in data:
            assert a['status']=='SUCCESS' and 1<=a['Q_validation']<=a['q']
            assert a['Q_wire']==a['Q_snapshot']+a['Q_validation']
            c=configs[a['configuration']]
            for t in a['trace']:
                if t['returned']['action'] in {'a','direct'}:
                    assert t['published']==t['expected_result']==t['returned']['result']
            if folder=='valkey_refresh_02':
                alpha,beta,rho=a['coefficients']
                assert a['C']==alpha*a['L']+beta*a['W']+rho*a['Q_wire']
                assert a['W']==a['L']+sum(x['blocks'] for x in a['outside_hashes'])
            groups[(a['configuration'],a['mode'])].append(a)
        old=read(src/(prefix+'CURVES.json'));derived={}
        for key,value in old.items():
            config,mode=key.split(':');g=groups[(int(config),mode)]
            curve=[max(a['C'] for a in g if a['B_used']<=b) for b in range(len(value['native_curve']))]
            assert curve==value['native_curve'],(prefix,key)
            derived[key]=curve
            if folder=='valkey_refresh_02':
                loss=max(a-b for a,b in zip(curve,value['informed_curve']))
                assert loss==value['regret']
                if mode=='compiled':assert loss==value['optimum']
        curves_by_binary.append(derived);native_counts[folder+'/'+prefix]=len(data)
    if len(curves_by_binary)==2:assert curves_by_binary[0]==curves_by_binary[1]

# Recompute all cell/block ratios, including unfavorable outcomes.
for folder,script,measured,warmup in [('valkey_timing_03','analyze01.py',1536,192),('valkey_writer_04','analysis01.py',288,48)]:
    src=SOURCE/folder;dst=OUT/folder
    copy(src/script,dst/script)
    for f in ['ROWS.jsonl','INPUT_MANIFEST.json','COMPLETION.json']:copy(src/'run01'/f,dst/'run01'/f)
    data=rows(src/'run01/ROWS.jsonl')
    assert len(data)==measured+warmup and all(a['status']=='SUCCESS' for a in data)
    assert sum(not a['warmup'] for a in data)==measured
    assert len({(a['cell'],a['block'],a['policy']) for a in data})==len(data)
    run(folder,[sys.executable,'-B',str(dst/script)])
    for f in ['ALL_CELL_SUMMARY.json','PAIRED_COMPARISONS.json']:assert read(src/'run01'/f)==read(dst/'run01'/f),(folder,f)
    same_json(dst/'run01/ANALYSIS_RECEIPT.json',src/'run01/ANALYSIS_RECEIPT.json',{'seconds','analysis_sha256'})

writer=rows(SOURCE/'valkey_writer_04/run01/ROWS.jsonl')
for a in writer:
    P=a['P'];R=a['R'];s=a['scale'];scenario=a['scenario'];mode=a['policy']
    U={'none':0,'small_each':R*s,'all_first':P,'all_each':R*P}[scenario]
    assert P==6*s and a['update_weight']==U
    assert len(a['reader_outputs'])==R
    assert all(x['result']==x['expected'] for x in a['reader_outputs'])
    assert a['W_reader']==sum(x['W'] for x in a['reader_outputs'])
    assert a['L_reader']==sum(x['L'] for x in a['reader_outputs'])
    assert a['W_total']==a['W_reader']+a['W_writer']+a['W_initial']
    assert a['total_wire_bytes']==sum(x['sent']+x['received'] for x in a['wire'].values())
    if mode=='direct':assert (a['W_total'],a['L_reader'],a['W_initial'],a['W_writer'])==(R*P,R*P,0,0)
    elif mode=='maintained':assert (a['W_total'],a['L_reader'],a['W_initial'],a['W_writer'])==(P+U,0,P,U)
    else:
        assert mode=='compiled' and a['W_total']==R*P+U
        assert a['L_reader']==(R*s if scenario=='small_each' else 0)
    for x in a['events']:assert x['end_ns']-x['start_ns']==x['roundtrip_ns']

paired=read(OUT/'valkey_writer_04/run01/PAIRED_COMPARISONS.json')
comp=[x for x in paired if x['denominator']=='compiled']
assert len(comp)==16 and all(x['mixed_trace_ns']['all_six_less'] for x in comp)
assert all(x['total_wire_bytes']['all_six_less'] for x in comp)
assert sum(x['max_any_server_ns']['paired_geometric_ratio']>1 for x in comp)==2
summary={'status':'SUCCESS','stage':'source-cost-boundaries','seconds':time.monotonic()-started,
    'steps':steps,'finite_general_conditions':1536,'optional_preparation_conditions':405,'vector_oracle_conditions':756,
    'native_rows_reanalyzed':native_counts,'timing03_measured':1536,'writer04_measured':288,
    'writer04_all_cells':16,'compiled_comparison_faster_all_six_blocks':16,'compiled_comparison_less_wire_all_six_blocks':16,
    'compiled_comparison_max_server_geometric_ratio_worse_cells':2,
    'new_native_runs':0,'new_timing_samples':0,'independent_application_count':0,
    'scope':'Author-side exact finite recomputation and saved-native result/resource/denominator analysis. Java source proof is not mechanically verified by this replay.'}
with (OUT/'SUMMARY.json').open('x') as f:json.dump(summary,f,indent=2);f.write('\n')
print(json.dumps(summary),flush=True)
