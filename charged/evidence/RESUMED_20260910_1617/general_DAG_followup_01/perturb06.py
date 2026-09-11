from pathlib import Path
import importlib.util,json,hashlib,datetime,time
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('G',D/'greedy_order04.py');G=importlib.util.module_from_spec(spec);spec.loader.exec_module(G);U=G.U
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def freeze():
    base=[6,8,1,8,3,3];offsets=[[0,1,2,3,4,5],[5,4,3,2,1,0],[0,5,4,1,3,2]]
    inputs=[dict(scale=k,offset=off,w=[k*a+b for a,b in zip(base,off)],edges=[[1,2],[3,4],[4,5]],r=3) for k in [10,100,1000] for off in offsets]
    assert len(inputs)==9 and all(len(set(i['w']))==6 for i in inputs)
    with (D/'INPUTS06.json').open('x') as f:f.write(json.dumps(inputs,indent=2)+'\n')
    with (D/'PROTOCOL06.md').open('x') as f:f.write('''# Distinct-weight sensitivity06

Adaptive follow-up to the observed tied six-job counterexample05, not a new independent sample claim. Before running, freeze all9 combinations of scales10/100/1000 and three distinct offsets. This tests whether the fixed minimum-ready-order obstruction persists when all works differ and its tie rule is irrelevant. Each graph consists of independent job0, chain1→2 and chain3→4→5, with retry3.

Compare complete Universal and FixedOrder04 Pareto vectors using the frozen code, and independently interpret every returned policy for readiness, Q/W/L and the optimal protected curve. Save all input outcomes and full trees, including equality and timeouts. Five-second per-input limit and no retry. A multiple full-root frontier is a distinct general least-curve counterexample candidate. A finite greedy discrepancy requires analytic reconstruction; no generality or minimality claim follows. Prior records unchanged; no native/human/paid work.
''')
    print('9distinct-weight sensitivity inputs frozen')
def run():
    inputs=json.loads((D/'INPUTS06.json').read_text());rows=[]
    with (D/'START06.json').open('x') as f:f.write(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),hashes={n:sha(D/n) for n in ['INPUTS06.json','PROTOCOL06.md','perturb06.py','greedy_order04.py']},oracle_sha256=sha(G.OLD)),indent=2)+'\n')
    for idx,inp in enumerate(inputs):
        row=dict(index=idx,input=inp);U.DEADLINE=time.monotonic()+5
        try:
            w=inp['w'];r=inp['r'];pred=[0]*6
            for i,j in inp['edges']:pred[j]|=1<<i
            fs=[];ts=[]
            for cls in [U.Universal,G.FixedOrder]:
                front=cls(w,pred,r).solve(63,r,0,0);assert front
                got=[]
                for c,t in front:
                    q=U.interpret(t,w,pred,r);assert q['W']==[sum(w)+v for v in c]
                    assert q['L']==[U.top(w,B-r) for B in range(10)]
                    got.append(q)
                fs.append(got);ts.append([dict(extra=c,tree=t) for c,t in front])
            row.update(status='MULTIPLE_FULL_CURVES' if len(fs[0])>1 else 'COUNTEREXAMPLE' if fs[0][0]['W'] not in [v['W'] for v in fs[1]] else 'EQUAL',full=fs[0],restricted=fs[1])
            if len(fs[0])==1:assert all(all(a<=b for a,b in zip(fs[0][0]['W'],q['W'])) for q in fs[1])
            name='WITNESS06_'+str(idx)+'.json'
            with (D/name).open('x') as f:f.write(json.dumps(dict(input=inp,full=ts[0],restricted=ts[1]),indent=2)+'\n')
            row['witness']=name;row['witness_sha256']=sha(D/name)
        except TimeoutError as ex:row.update(status='TIMEOUT',error=str(ex))
        except Exception as ex:row.update(status='FAILURE',error=repr(ex))
        rows.append(row)
    with (D/'RESULT06.json').open('x') as f:f.write(json.dumps(rows,indent=2)+'\n')
    print(json.dumps([{k:r[k] for k in ['index','input','status','full','restricted'] if k in r} for r in rows],indent=2))
if __name__=='__main__':
    import sys
    {'freeze':freeze,'run':run}[sys.argv[1]]()
