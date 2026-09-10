from pathlib import Path
import hashlib,json,datetime,time
from collections import Counter
D=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def nd(pairs):
    out=[];floor=float('inf')
    for W,L in sorted(set(pairs)):
        if L<floor:out.append([W,L]);floor=L
    return out
def main():
    assert not(D/'ONE_WRITE_ROWS03.jsonl').exists()
    src=D/'ROWS01.jsonl';assert sha(src)=='5f4dd8376ee94b92fad8c6530174d747ff2e09ca67faa71d1ddfca30fc717e59'
    start=time.monotonic();stats=Counter();count=Counter();fail=[]
    with(D/'ONE_WRITE_ROWS03.jsonl').open('x') as out:
        for line in src.open():
            old=json.loads(line)
            if old['B']!=1 or old['r'] not in (1,2):continue
            row={'input':old['input'],'r':old['r'],'B':1,'archived_status':old['status']}
            try:
                assert old['status']=='SUCCESS'
                w=old['input']['w'];omega=sum(w);thresholds=[[omega+M,sum(v for v in w if v>M)] for M in sorted({0,*w})];front=nd(map(tuple,thresholds))
                row.update(thresholds=thresholds,formula_frontier=front,archived_immediate=old['immediate'],archived_retained=old['retained'])
                assert front==old['immediate']==old['retained'],('frontier_mismatch',row)
                row['status']='SUCCESS'
            except Exception as e:row.update(status='FAILURE',error=repr(e));fail.append(row.copy())
            stats[row['status']]+=1;count[old['r']]+=1;out.write(json.dumps(row)+'\n')
    assert sum(stats.values())==10842 and count=={1:5421,2:5421}
    (D/'ONE_WRITE_FAILURES03.json').write_text(json.dumps(fail,indent=2)+'\n')
    summary={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'SUCCESS' if stats=={'SUCCESS':10842} else 'FAILURE','counts':dict(stats),'by_r':dict(count),'seconds':time.monotonic()-start,'new_scientific_executions':0,'retrospective_analysis':True,'hashes':{f:sha(D/f) for f in ['ONE_WRITE_RETRY03.md','one_write03.py','ROWS01.jsonl','ONE_WRITE_ROWS03.jsonl','ONE_WRITE_FAILURES03.json']}}
    (D/'ONE_WRITE_SUMMARY03.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2));return summary['status']=='SUCCESS'
if __name__=='__main__':raise SystemExit(not main())
