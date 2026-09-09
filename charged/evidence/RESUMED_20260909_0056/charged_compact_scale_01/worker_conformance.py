"""Pre-timing pipeline check on two observed compact cases, all five services."""
from pathlib import Path
import datetime,hashlib,json,subprocess,sys
HERE=Path(__file__).resolve().parent
DEST=HERE/'worker_conformance01'
METHODS=['PACK','ROOT','ALL','PEAK','DP']
def save(p,v):
    with p.open('x') as f:json.dump(v,f,indent=2);f.write('\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def prepare():
    DEST.mkdir()
    cases=[dict(jobs=[[3,2,0,0,0],[1,1,1,3,1]],edges=[]),dict(jobs=[[1,0,0,5,10],[2,3,1,3,1]],edges=[])]
    sources=list(HERE.glob('*.py'))+list((HERE.parent/'charged_compact_02').glob('*.py'))
    save(DEST/'MANIFEST.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),cases=cases,methods=METHODS,budgets=[0,1,2,3,8,1<<32],per_unit_seconds=5,files={str(p):sha(p) for p in sources},main_case_execution=0,previously_observed_cases=True))
def run():
    m=json.loads((DEST/'MANIFEST.json').read_text());assert all(sha(Path(p))==h for p,h in m['files'].items())
    rows=[]
    for i,case in enumerate(m['cases']):
        for method in METHODS:
            out=DEST/f'{i}_{method}';out.mkdir();input_path=out/'INPUT.json'
            save(input_path,dict(method=method,case=case,budgets=m['budgets']))
            with (out/'stdout.txt').open('x') as stdout,(out/'stderr.txt').open('x') as stderr:
                process=subprocess.run([sys.executable,'-B',str(HERE/'worker.py'),method,str(input_path),str(out)],stdout=stdout,stderr=stderr,timeout=5)
            result=json.loads((out/'RESULT.json').read_text());rows.append(dict(case=i,method=method,returncode=process.returncode,result=result))
    save(DEST/'RAW.json',rows)
    summary=dict(units=len(rows),successful=sum(r['returncode']==0 and r['result']['status']=='SUCCESS' for r in rows),value_groups={str(i):[r['result'].get('values') for r in rows if r['case']==i] for i in range(len(m['cases']))})
    summary['all_values_match']=all(all(v==group[0] for v in group) for group in summary['value_groups'].values())
    save(DEST/'SUMMARY.json',summary);print(json.dumps(summary,indent=2))
    assert summary['successful']==10 and summary['all_values_match']
if __name__=='__main__':{'prepare':prepare,'run':run}[sys.argv[1]]()
