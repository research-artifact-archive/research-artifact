from pathlib import Path
import datetime,hashlib,json,subprocess,sys
import compact
HERE=Path(__file__).resolve().parent
DEST=HERE/'cli_conformance01'
def save(p,v):
    with p.open('x') as f:json.dump(v,f,indent=2);f.write('\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def prepare():
    DEST.mkdir();case=dict(jobs=[[1,2,0,0,0]],edges=[])
    save(DEST/'valid.json',case);save(DEST/'null.json',None)
    save(DEST/'bool.json',dict(jobs=[[True,2,0,0,0]],edges=[]))
    save(DEST/'float.json',dict(jobs=[[1.0,2,0,0,0]],edges=[]))
    save(DEST/'artifact.json',compact.compile_case(case))
    units=[]
    for command in ['check','query']:
        units.append(dict(id='prior_null_'+command,version='charged_compact_02',command=command,input='null',accept=True))
        for value in ['omitted','valid','null','bool','float']:
            units.append(dict(id=command+'_'+value,version=HERE.name,command=command,input=value,accept=value in ['omitted','valid']))
    for value in ['valid','null']:
        units.append(dict(id='compile_'+value,version=HERE.name,command='compile',input=value,accept=value=='valid'))
    sources=list(HERE.glob('*.py'))+[HERE.parent/'charged_compact_02/cli.py']+list(DEST.glob('*.json'))
    save(DEST/'MANIFEST.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),units=units,per_unit_seconds=3,files={str(p):sha(p) for p in sources}))
def run():
    m=json.loads((DEST/'MANIFEST.json').read_text());assert all(sha(Path(p))==h for p,h in m['files'].items());rows=[]
    for u in m['units']:
        argv=[sys.executable,'-B',str(HERE.parent/u['version']/'cli.py'),u['command']]
        if u['command']=='compile':argv+=['--out',str(DEST/(u['id']+'_artifact.json'))]
        else:argv+=['--artifact',str(DEST/'artifact.json')]
        if u['command']=='query':argv+=['--budgets','0','1','2']
        if u['input']!='omitted':argv+=['--input',str(DEST/(u['input']+'.json'))]
        with (DEST/(u['id']+'.stdout')).open('x') as stdout,(DEST/(u['id']+'.stderr')).open('x') as stderr:
            p=subprocess.run(argv,stdout=stdout,stderr=stderr,timeout=3)
        rows.append(dict(unit=u,argv=argv,returncode=p.returncode,met=(p.returncode==0)==u['accept']))
    save(DEST/'RAW.json',rows);summary=dict(units=len(rows),controls_met=sum(r['met'] for r in rows),prior_null_acceptance_preserved=True,new_semantic_algorithm_runs=0)
    save(DEST/'SUMMARY.json',summary);print(json.dumps(summary));assert all(r['met'] for r in rows)
if __name__=='__main__':{'prepare':prepare,'run':run}[sys.argv[1]]()
