from pathlib import Path
import datetime,hashlib,json,time,traceback
from evaluate import evaluate
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,value):
    with (ROOT/name).open('x') as f:json.dump(value,f,indent=2);f.write('\n')
def main():
    inputs=[([],[]),([(1,0)],[]),([(2,3)],[]),([(2,3),(1,2)],[]),
            ([(1,2),(2,3)],[(0,1)]),([(2,3),(1,2)],[(0,1)]),
            ([(1,2),(1,0),(1,3)],[(2,1),(1,0)]),
            ([(2,3),(1,0),(2,1)],[(0,1),(0,2)]),
            ([(1,0),(2,2),(1,3)],[(0,2),(1,2)]),
            ([(2,3),(1,2),(2,0),(1,1)],[(0,1),(0,2),(1,3),(2,3)])]
    inputs=[dict(id=f'preflight-{i:02}',cp=cp,edges=edges,budget=4,provenance='fixed author development fixture') for i,(cp,edges) in enumerate(inputs)]
    save('PREFLIGHT_INPUTS.json',inputs)
    sources=[ROOT/x for x in ['PREFLIGHT_PLAN.md','PREFLIGHT_INPUTS.json','preflight.py','primitive.py','structure.py','evaluate.py']]
    sources += [ROOT.parent/x for x in ['primitive_rmw_01/explore.py','dependency_hybrid_01/hybrid.py','dependency_curves_01/curves.py','dependency_curves_01/checker.py','dependency_hybrid_check_02/check.py']]
    save('PREFLIGHT_MANIFEST.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),files=[dict(path=str(p),sha256=sha(p)) for p in sources],units=len(inputs)))
    start=time.monotonic();rows=[]
    with (ROOT/'PREFLIGHT_RAW.jsonl').open('x') as f:
        for case in inputs:
            try:
                if time.monotonic()-start>=60:row=dict(input_id=case['id'],status='TIMEOUT')
                else:row,_=evaluate(case)
            except Exception:row=dict(input_id=case['id'],status='INVALID',error=traceback.format_exc())
            rows.append(row);f.write(json.dumps(row)+'\n');f.flush()
    summary=dict(outcomes={s:sum(r['status']==s for r in rows) for s in ['SUCCESS','FAILURE','TIMEOUT','INVALID']},elapsed_seconds=time.monotonic()-start,raw_sha256=sha(ROOT/'PREFLIGHT_RAW.jsonl'))
    save('PREFLIGHT_SUMMARY.json',summary);print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
