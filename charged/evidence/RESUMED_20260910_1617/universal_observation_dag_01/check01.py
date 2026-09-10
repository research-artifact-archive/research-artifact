from pathlib import Path
from functools import lru_cache
from collections import Counter
import datetime,gzip,hashlib,importlib.util,io,json,time
D=Path(__file__).resolve().parent
OLD=D.parent/'joint_work_general_r_01/unknown02.py'
spec=importlib.util.spec_from_file_location('visible_oracle',OLD);U=importlib.util.module_from_spec(spec);spec.loader.exec_module(U)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def enc(v):return json.dumps(v,sort_keys=True,separators=(',',':'))

class Erased:
    """Canonical cheap-prefix choices; every hidden cached child is shared."""
    def __init__(self,w,pred,r):
        self.w=w;self.pred=pred;self.H=len(w)+r;self.visits=0
        self.solve=lru_cache(None)(self._solve)
    def _solve(self,S,a):
        U.bounded();self.visits+=1
        if not S:return (((0,)*(self.H+1),('done',)),)
        front={}
        def offer(c,t):
            if any(all(x<=y for x,y in zip(old,c)) for old in front):return
            for old in [old for old in front if all(x<=y for x,y in zip(c,old))]:del front[old]
            front[c]=t
        for i,w in enumerate(self.w):
            if not S>>i&1 or self.pred[i]&S:continue
            R=S^(1<<i)
            if a:
                for c0,t0 in self.solve(R,a):
                    for c1,t1 in self.solve(S,a-1):
                        c=(c0[0],)+tuple(max(c0[k],w+c1[k-1]) for k in range(1,self.H+1))
                        offer(c,('cheap',i,t0,t1))
            else:
                for child,tree in self.solve(R,0):
                    c=(child[0],)+tuple(max(child[k],w+child[k-1]) for k in range(1,self.H+1))
                    offer(c,('cached',i,tree,tree))
        return tuple(sorted(front.items()))

def explicit(r,visible,control=None):
    order=(3,0,1,2)
    def build(pos,f,zcheap,Abad,Ubad):
        if pos==4:return ('done',)
        i=order[pos]
        if visible and i==2 and Abad and Ubad and (zcheap or control=='omit_Z_cheap_premise'):
            t=('fresh',i,('done',))
            return ('extra_prepare',i,t) if control=='prepare_before_fresh' else t
        if f<r:
            return ('cheap',i,build(pos+1,f,zcheap or i==3,Abad,Ubad),build(pos,f+1,zcheap,Abad,Ubad))
        good=build(pos+1,f,zcheap,Abad,Ubad)
        bad=build(pos+1,f,zcheap,Abad or i==0,Ubad or i==1)
        return ('cached',i,good,bad if visible else good)
    return build(0,0,False,False,False)

def direct_paths(tree,w,pred,r,tag,out=None):
    H=len(w)+r;Wmax=[-1]*(H+1);Lmax=[-1]*(H+1);Qmax=[-1]*(H+1);count=0;violations=[];witness=[None]*(H+1)
    def walk(t,done,d,q,W,L,events):
        nonlocal count
        U.bounded();mode=t[0]
        if mode=='done':
            assert done==(1<<len(w))-1
            row=dict(tag=tag,d=d,Q=q,W=W,L=L,events=events)
            if q>H or L>U.top(w,d-r):violations.append(row)
            count+=1
            if out:out.write(enc(row)+'\n')
            for b in range(d,H+1):
                if W>Wmax[b]:Wmax[b]=W;witness[b]=row
                Lmax[b]=max(Lmax[b],L);Qmax[b]=max(Qmax[b],q)
            return
        i=t[1];v=w[i];assert not done>>i&1 and pred[i]&done==pred[i]
        if mode=='extra_prepare':walk(t[2],done,d,q,W+v,L,events+[('prepare_discarded',i)])
        elif mode=='fresh':walk(t[2],done|1<<i,d,q+1,W+v,L+v,events+[('fresh',i)])
        else:
            assert mode in ('cheap','cached')
            prep=events+[('prepare',i)]
            walk(t[2],done|1<<i,d,q+1,W+v,L,prep+[(mode,i,'match')])
            if mode=='cheap':walk(t[3],done,d+1,q+1,W+v,L,prep+[(mode,i,'failure')])
            else:walk(t[3],done|1<<i,d+1,q+1,W+2*v,L+v,prep+[(mode,i,'mismatch')])
    walk(tree,0,0,0,0,0,[])
    return dict(W=Wmax,L=Lmax,Q=Qmax,paths=count,contract_violations=violations,W_witnesses=witness)

def erased_action_conflict(tree):
    """For the stated constant-output own-gate model, hide cached flags."""
    choices={};conflicts=[]
    def visit(t,history):
        if t[0]=='done':action=('done',)
        else:action=tuple(t[:2])
        key=enc(history)
        if key in choices and choices[key]!=action:
            if not conflicts:conflicts.append(dict(visible_history=history,first_action=choices[key],second_action=action))
        choices[key]=action
        mode=t[0]
        if mode=='done':return
        i=t[1]
        if mode=='fresh':visit(t[2],history+[('fresh',i,'constant_output')])
        elif mode=='cheap':
            visit(t[2],history+[('prepare',i),('cheap',i,True)])
            visit(t[3],history+[('prepare',i),('cheap',i,False)])
        elif mode=='cached':
            common=history+[('prepare',i),('cached',i,'constant_output')]
            visit(t[2],common);visit(t[3],common)
        else:raise AssertionError(mode)
    visit(tree,[]);return conflicts

def freeze():
    inputs=[dict(M=M,r=r,w=[M,1,1,2],edges=[[0,1],[1,2]],family_condition=M>=3 and r*(M-2)>=3) for M in range(2,9) for r in range(1,5)]
    assert len(inputs)==28
    with (D/'INPUTS01.json').open('x') as f:f.write(json.dumps(inputs,indent=2)+'\n')
    print('28 observation-family roots frozen')

def run():
    inputs=json.loads((D/'INPUTS01.json').read_text());start=time.monotonic();deadline=start+300
    receipt=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),planned=len(inputs),family_roots=sum(x['family_condition'] for x in inputs),hashes={n:sha(D/n) for n in ['INPUTS01.json','PROTOCOL01.md','DRAFT01.md','check01.py']},visible_oracle_sha256=sha(OLD),new_native_runs=0)
    with (D/'START01.json').open('x') as f:f.write(json.dumps(receipt,indent=2)+'\n')
    counts=Counter();rows=[];trees=[];totalpaths=0
    raw=(D/'PATHS01.jsonl.gz').open('xb');z=gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0);out=io.TextIOWrapper(z,encoding='utf-8',newline='\n')
    for idx,inp in enumerate(inputs):
        row=dict(index=idx,input=inp)
        if time.monotonic()>=deadline:row.update(status='NOT_EXECUTED')
        else:
            U.DEADLINE=min(deadline,time.monotonic()+10)
            try:
                w=inp['w'];r=inp['r'];M=inp['M'];pred=[0,1,2,0];H=4+r;omega=sum(w);C=omega+(r+1)*M
                expectedV=[omega+B*M if B<=r+1 else C+1 for B in range(H+1)]
                expectedE=[omega+B*M if B<=r+1 else C+1 if B==r+2 else C+2 for B in range(H+1)]
                vtree=explicit(r,True);etree=explicit(r,False)
                gotV=direct_paths(vtree,w,pred,r,'explicit_visible_'+str(idx),out)
                gotE=direct_paths(etree,w,pred,r,'explicit_erased_'+str(idx),out)
                for tree,got in [(vtree,gotV),(etree,gotE)]:
                    check=U.interpret(tree,w,pred,r)
                    assert got['W']==check['W'] and got['L']==check['L'] and got['paths']==check['paths']
                    assert not got['contract_violations']
                    assert got['L']==[U.top(w,B-r) for B in range(H+1)]
                vfront=U.Universal(w,pred,r).solve(15,r,0,0)
                efront=Erased(w,pred,r).solve(15,r)
                vcurves=[];ecurves=[]
                for name,front,curves in [('visible_oracle',vfront,vcurves),('canonical_erased',efront,ecurves)]:
                    assert front
                    for c,t in front:
                        got=direct_paths(t,w,pred,r,name+'_'+str(idx),out)
                        assert not got['contract_violations']
                        assert got['W']==[omega+x for x in c]
                        assert got['L']==[U.top(w,B-r) for B in range(H+1)]
                        curves.append(got['W']);totalpaths+=got['paths']
                        if name=='canonical_erased':assert not erased_action_conflict(t)
                conflicts=erased_action_conflict(vtree);assert conflicts and not erased_action_conflict(etree)
                if inp['family_condition']:
                    assert gotV['W']==expectedV and gotE['W']==expectedE
                    assert vcurves==[expectedV] and ecurves==[expectedE]
                row.update(status='SUCCESS',visible_explicit=gotV,erased_explicit=gotE,visible_oracle=vcurves,canonical_erased=ecurves,formula_visible=expectedV if inp['family_condition'] else None,formula_erased=expectedE if inp['family_condition'] else None,visible_policy_requires_flag=conflicts)
                totalpaths+=gotV['paths']+gotE['paths']
                if M==5 and r==1:trees.append(dict(input=inp,visible=vtree,erased=etree,visible_oracle=vfront,canonical_erased=efront))
            except TimeoutError as ex:row.update(status='TIMEOUT',error=str(ex))
            except Exception as ex:row.update(status='FAILURE',error=repr(ex))
        counts[row['status']]+=1;rows.append(row)
    U.DEADLINE=min(deadline,time.monotonic()+10)
    controls=[]
    for name in ['omit_Z_cheap_premise','prepare_before_fresh']:
        got=direct_paths(explicit(1,True,name),[5,1,1,2],[0,1,2,0],1,'negative_'+name,out)
        if name=='omit_Z_cheap_premise':detected=bool(got['contract_violations'])
        else:detected=any(got['W'][b]>[9,14,19,20,20,20][b] for b in range(6))
        controls.append(dict(control=name,detected=detected,result=got));totalpaths+=got['paths']
    out.close();raw.close()
    for name,value in [('ROWS01.json',rows),('TREES01.json',trees),('NEGATIVE_CONTROLS01.json',controls)]:
        with (D/name).open('x') as f:f.write(json.dumps(value,indent=2)+'\n')
    result=dict(receipt,ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='SUCCESS' if counts=={'SUCCESS':28} and all(x['detected'] for x in controls) else 'FAILURE',counts=dict(counts),interpreted_paths=totalpaths,negative_controls=len(controls),negative_controls_detected=sum(x['detected'] for x in controls),seconds=time.monotonic()-start,outputs={n:sha(D/n) for n in ['ROWS01.json','TREES01.json','NEGATIVE_CONTROLS01.json','PATHS01.jsonl.gz']},all_program_erased_proof_from_code=False)
    with (D/'SUMMARY01.json').open('x') as f:f.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2),flush=True)
    return result['status']=='SUCCESS'
if __name__=='__main__':
    import sys
    if sys.argv[1]=='freeze':freeze()
    else:raise SystemExit(not run())
