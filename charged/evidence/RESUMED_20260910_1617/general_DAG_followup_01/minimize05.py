"""Transparent adaptive reduction of the observed greedy-order counterexample."""
from pathlib import Path
import importlib.util,json,hashlib,time,datetime
from collections import Counter
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('restricted04',D/'greedy_order04.py')
G=importlib.util.module_from_spec(spec);spec.loader.exec_module(G);U=G.U
def enc(v):return json.dumps(v,sort_keys=True,separators=(',',':'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def norm(v):return dict(w=list(v['w']),edges=sorted([list(e) for e in v['edges']]),r=v['r'])
def moves(v):
    n=len(v['w'])
    if n>1:
        for cut in range(n):
            order=[i for i in range(n) if i!=cut];pos={i:j for j,i in enumerate(order)}
            yield 'delete_vertex_'+str(cut),dict(w=[v['w'][i] for i in order],edges=[[pos[i],pos[j]] for i,j in v['edges'] if i!=cut and j!=cut],r=v['r'])
    for e in v['edges']:yield 'delete_edge_'+str(e),dict(w=v['w'],edges=[x for x in v['edges'] if x!=e],r=v['r'])
    for i,a in enumerate(v['w']):
        for b in range(1,a):
            w=v['w'].copy();w[i]=b
            yield 'decrease_weight_'+str(i)+'_to_'+str(b),dict(w=w,edges=v['edges'],r=v['r'])
    for r in range(1,v['r']):yield 'decrease_retry_to_'+str(r),dict(w=v['w'],edges=v['edges'],r=r)

def freeze():
    text='''# Adaptive counterexample reduction05

Begin from the exact index470 greedy-order04 counterexample. This is adaptive exploration after observing that result, not a prospective population or independent new instance count. Try, in order, deletion of a vertex with induced-edge relabeling, deletion of an edge, lowering one positive integer work, and lowering positive retry slack. Adopt the first smaller input for which the complete oracle has a least root W vector absent from the fixed minimum-ready-order frontier, then restart. Cache exact repeated inputs and retain a REUSED record pointing to their previous result. Save all attempts, including equality, failure, timeout and non-counterexamples. A broader full-oracle frontier with multiple incomparable curves is a distinct candidate and stops the search for separate analysis.

Use240s total and5s per fresh input, no restart of a timed out input. Independently interpret every returned policy tree for Q/W/L and readiness. The full least vector must dominate restricted vectors. Save every adopted input, both complete and restricted witness trees, and path-derived vectors. A final instance is only irreducible under these ordered successful local reductions; do not claim global minimality. Prior03/04 files are unchanged. A finite candidate still needs an analytic proof; no FSE importance or general theorem follows from the result.
'''
    with (D/'PROTOCOL05.md').open('x') as f:f.write(text)
    source=json.loads((D/'WITNESSES04.json').read_text())[0]
    v=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),initial_input=norm(source['input']),source_index=source['index'],hashes={n:sha(D/n) for n in ['PROTOCOL05.md','WITNESSES04.json','greedy_order04.py','minimize05.py']},oracle_sha256=sha(G.OLD))
    with (D/'INPUT05.json').open('x') as f:f.write(json.dumps(v,indent=2)+'\n')
    print('adaptive reduction frozen')

def run():
    binding=json.loads((D/'INPUT05.json').read_text())
    for n,h in binding['hashes'].items():assert sha(D/n)==h
    assert sha(G.OLD)==binding['oracle_sha256']
    started=time.monotonic();deadline=started+240;cache={};stats=Counter();accepted=[];stop=None;trial=0
    with (D/'START05.json').open('x') as f:f.write(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),binding_sha256=sha(D/'INPUT05.json')),indent=2)+'\n')
    with (D/'TRIALS05.jsonl').open('x') as out:
        def evaluate(inp,reason):
            nonlocal trial,stop
            inp=norm(inp);key=enc(inp);index=trial;trial+=1
            if key in cache:
                prev=cache[key];row=dict(index=index,input=inp,reason=reason,status='REUSED',reuses_trial=prev['index'],prior_status=prev['status'])
                out.write(enc(row)+'\n');out.flush();stats['REUSED']+=1;return prev
            row=dict(index=index,input=inp,reason=reason);w=inp['w'];r=inp['r'];pred=[0]*len(w)
            for i,j in inp['edges']:pred[j]|=1<<i
            U.DEADLINE=min(deadline,time.monotonic()+5)
            try:
                full=U.Universal(w,pred,r).solve((1<<len(w))-1,r,0,0)
                rest=G.FixedOrder(w,pred,r).solve((1<<len(w))-1,r,0,0)
                assert full and rest
                groups=[]
                for front in [full,rest]:
                    got=[]
                    for c,t in front:
                        q=U.interpret(t,w,pred,r);assert q['W']==[sum(w)+x for x in c]
                        assert q['L']==[U.top(w,B-r) for B in range(len(w)+r+1)]
                        got.append(q)
                    groups.append(got)
                if len(full)>1:row['status']='MULTIPLE_FULL_CURVES';stop='multiple_full_curves_require_analysis'
                else:
                    fcurve=groups[0][0]['W']
                    assert all(all(x<=y for x,y in zip(fcurve,a['W'])) for a in groups[1])
                    row['status']='COUNTEREXAMPLE' if all(a['W']!=fcurve for a in groups[1]) else 'EQUAL'
                row.update(full=groups[0],restricted=groups[1])
                if row['status'] in ['COUNTEREXAMPLE','MULTIPLE_FULL_CURVES']:
                    name='WITNESS05_'+str(index)+'.json'
                    with (D/name).open('x') as f:f.write(json.dumps(dict(index=index,input=inp,full=[dict(extra=c,tree=t) for c,t in full],restricted=[dict(extra=c,tree=t) for c,t in rest]),indent=2)+'\n')
                    row['witness']=name;row['witness_sha256']=sha(D/name)
            except TimeoutError as ex:row.update(status='TIMEOUT',error=str(ex))
            except Exception as ex:row.update(status='FAILURE',error=repr(ex));stop='semantic_failure'
            cache[key]=row;stats[row['status']]+=1;out.write(enc(row)+'\n');out.flush();return row
        current=binding['initial_input'];first=evaluate(current,'transport_reconstruction_of_known_input')
        assert first['status']=='COUNTEREXAMPLE'
        accepted.append(first)
        while not stop:
            if time.monotonic()>=deadline:stop='campaign_deadline';break
            changed=False
            for reason,inp in moves(current):
                if time.monotonic()>=deadline:stop='campaign_deadline';break
                row=evaluate(inp,reason)
                if stop:break
                if row['status']=='COUNTEREXAMPLE':current=row['input'];accepted.append(row);changed=True;break
            if not changed:
                if not stop:stop='no_successful_ordered_local_reduction'
                break
    result=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='EXPLORATION_COMPLETE',stop_reason=stop,counts=dict(stats),attempt_records=trial,unique_inputs=len(cache),seconds=time.monotonic()-started,initial_input=binding['initial_input'],final_input=current,adopted=[{k:v[k] for k in ['index','input','full','restricted','witness','witness_sha256']} for v in accepted],trials_sha256=sha(D/'TRIALS05.jsonl'),globally_minimal=False,analytic_proof_pending=True)
    if stats['FAILURE']:result['status']='SEMANTIC_FAILURE'
    with (D/'SUMMARY05.json').open('x') as f:f.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='adopted'},indent=2),flush=True)

if __name__=='__main__':
    import sys
    {'freeze':freeze,'run':run}[sys.argv[1]]()
