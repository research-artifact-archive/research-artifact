from pathlib import Path
import importlib.util,json,hashlib,datetime,time
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('G',D/'greedy_order04.py');G=importlib.util.module_from_spec(spec);spec.loader.exec_module(G);U=G.U
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def freeze():
    inputs=[dict(scale=10,offset=[2,3,5,4,0,1],w=[62,83,15,84,30,31],edges=[[1,2],[3,4],[4,5]],r=3)]
    assert all(len(set(i['w']))==6 for i in inputs)
    with (D/'INPUTS07.json').open('x') as f:f.write(json.dumps(inputs,indent=2)+'\n')
    with (D/'PROTOCOL07.md').open('x') as f:f.write('# Claude-proposed distinct-weight falsifier07\n\nOne new input is fixed before execution, drawn from the preserved ordinary ClaudeCost16 technical answer. Its predicted B7 gap14 is unverified. Use the unchanged full Universal and minimum-ready-order04 recurrences, interpret every returned tree and save all outcomes, including equality, timeout or semantic failure. Limit5s, one execution, no retry. This adaptive one-root follow-up is not a fresh independent population or a general proof. Prior nine equality outcomes stay unchanged. Preserve the code-derived witness even if the hand calculation is wrong; distinguish finite discrepancy from all-program or general structural theorems.\n')
    print('one distinct-weight Claude candidate frozen')

def run():
    inputs=json.loads((D/'INPUTS07.json').read_text());rows=[]
    with (D/'START07.json').open('x') as f:f.write(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),hashes={n:sha(D/n) for n in ['INPUTS07.json','PROTOCOL07.md','claude_candidate07.py','greedy_order04.py']},oracle_sha256=sha(G.OLD)),indent=2)+'\n')
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
            name='WITNESS07_'+str(idx)+'.json'
            with (D/name).open('x') as f:f.write(json.dumps(dict(input=inp,full=ts[0],restricted=ts[1]),indent=2)+'\n')
            row['witness']=name;row['witness_sha256']=sha(D/name)
        except TimeoutError as ex:row.update(status='TIMEOUT',error=str(ex))
        except Exception as ex:row.update(status='FAILURE',error=repr(ex))
        rows.append(row)
    with (D/'RESULT07.json').open('x') as f:f.write(json.dumps(rows,indent=2)+'\n')
    print(json.dumps([{k:r[k] for k in ['index','input','status','full','restricted'] if k in r} for r in rows],indent=2))
if __name__=='__main__':
    import sys
    {'freeze':freeze,'run':run}[sys.argv[1]]()
