import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import signal
import sys
import time
import traceback

HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent/'charged_guaranteed_02'
spec=importlib.util.spec_from_file_location('fixed_charged_primitive',SOURCE/'explore.py')
primitive=importlib.util.module_from_spec(spec);spec.loader.exec_module(primitive)

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,x):
    with (HERE/n).open('x') as f:json.dump(x,f,ensure_ascii=False,indent=2);f.write('\n')
def expiry(*unused):raise TimeoutError('registered diagnostic cap')

def prepare():
    (HERE/'INPUTS.json').write_bytes((SOURCE/'INPUTS.json').read_bytes())
    save('MANIFEST.json',{'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'local_files':{n:sha(HERE/n) for n in ['PLAN.md','study.py','INPUTS.json']},
        'source_file':str(SOURCE/'explore.py'),'source_sha256':sha(SOURCE/'explore.py'),
        'input_count':2114,'budgets':list(range(7)),'previously_observed':True,
        'per_input_seconds':5,'total_seconds':180,'hard_stop_utc':'2026-09-09T05:00:00Z','python':sys.version})
    print('registered2114 observed inputs')

def run():
    m=json.loads((HERE/'MANIFEST.json').read_text())
    for n,h in m['local_files'].items():assert sha(HERE/n)==h
    assert sha(Path(m['source_file']))==m['source_sha256']
    cases=json.loads((HERE/'INPUTS.json').read_text());assert len(cases)==m['input_count']
    signal.signal(signal.SIGALRM,expiry);start=time.monotonic();rows=[];witness=False
    deadline=datetime.datetime.fromisoformat(m['hard_stop_utc'].replace('Z','+00:00')).timestamp()
    save('RUN_STARTED.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'manifest_sha256':sha(HERE/'MANIFEST.json')})
    with (HERE/'RAW.jsonl').open('x') as raw:
        for case in cases:
            row={'id':case['id']};t=time.monotonic();left=min(180-(t-start),deadline-time.time())
            if left<=0:row.update(status='NOT_RUN',reason='total/deadline cap')
            else:
                signal.setitimer(signal.ITIMER_REAL,min(5,left))
                try:
                    graph=primitive.graph(case);values,policy,rank=primitive.solve_validate(graph)
                    n=len(case['jobs']);u=(primitive.U,)*n
                    ready=[i for i in range(n) if not any(j==i for h,j in case['edges'])]
                    cells=[]
                    for i in ready:
                        w,p,g,v,r=case['jobs'][i]
                        l=list(u);l[i]=primitive.L;l=tuple(l)
                        lc=list(u);lc[i]=primitive.LC;lc=tuple(lc)
                        d=list(u);d[i]=primitive.D;d=tuple(d)
                        for b in m['budgets']:
                            root=values[(u,b)];held=values[(l,b)]
                            immediate=min(r+root,w+p+r+values[(d,b)])
                            assert held<=immediate
                            cell={'job':i,'budget':b,'held':held,'immediate':immediate,'strict':held<immediate}
                            if b:
                                previous=min(r+values[(u,b-1)],w+p+r+values[(d,b-1)])
                                acquire=w+g+max(values[(lc,b)],values[(l,b-1)])
                                restricted=w+g+max(values[(lc,b)],previous)
                                assert root<=acquire<=restricted
                                cell.update(root=root,prepare_acquire=acquire,prepare_acquire_immediate=restricted,
                                    root_relevant=acquire==root and restricted>root)
                            cells.append(cell)
                    row.update(status='SUCCESS',eligible=len(cells),structurally_ineligible=7*(n-len(ready)),
                        strict_cells=sum(c['strict'] for c in cells),root_relevant=sum(c.get('root_relevant',False) for c in cells),
                        cells=cells,states=len(values))
                    if row['strict_cells'] and not witness:
                        save('FIRST_STRICT_WITNESS.json',{'input':case,'cells':cells,
                            'source_input_id':case['id'],'classification':'intermediate-state counterexample; root equality not inferred false'})
                        witness=True
                except TimeoutError as e:row.update(status='TIMEOUT',error=str(e))
                except Exception:row.update(status='INVALID',error=traceback.format_exc())
                finally:signal.setitimer(signal.ITIMER_REAL,0)
            row['elapsed_seconds']=time.monotonic()-t;rows.append(row);raw.write(json.dumps(row,separators=(',',':'))+'\n');raw.flush()
    summary={'planned':len(cases),'recorded':len(rows),
        'status_counts':{s:sum(r['status']==s for r in rows) for s in ['SUCCESS','FAILURE','TIMEOUT','INVALID','NOT_RUN']},
        'eligible_cells':sum(r.get('eligible',0) for r in rows),'structurally_ineligible':sum(r.get('structurally_ineligible',0) for r in rows),
        'strict_cells':sum(r.get('strict_cells',0) for r in rows),'strict_inputs':sum(r.get('strict_cells',0)>0 for r in rows),
        'root_relevant_cells':sum(r.get('root_relevant',0) for r in rows),'elapsed_seconds':time.monotonic()-start,
        'raw_sha256':sha(HERE/'RAW.jsonl'),'universal_lemma_established':False}
    save('SUMMARY.json',summary);print(json.dumps(summary,indent=2))

if __name__=='__main__': {'prepare':prepare,'run':run}[sys.argv[1]]()
