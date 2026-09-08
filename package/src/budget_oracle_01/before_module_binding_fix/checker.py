"""Independent point-value certificate checker; uses the proved DAG concavity law."""
from pathlib import Path
import importlib.util
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('packed_root_certificate_checker',ROOT.parent/'dependency_hybrid_check_02/check.py')
packed_checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(packed_checker)

def validate(case):
    assert type(case) is dict and set(case)=={'cp','edges'}
    cp=case['cp'];assert type(cp) is list;n=len(cp)
    assert all(type(row) is list and len(row)==2 and type(row[0]) is int and row[0]>0 and type(row[1]) is int and row[1]>=0 for row in cp)
    assert type(case['edges']) is list;pred=[set() for _ in cp];seen=set()
    for row in case['edges']:
        assert type(row) is list and len(row)==2;u,v=row
        assert type(u) is int and type(v) is int and 0<=u<n and 0<=v<n and u!=v and (u,v) not in seen
        seen.add((u,v));pred[v].add(u)
    done=set()
    while len(done)<n:
        ready={i for i in range(n) if i not in done and pred[i]<=done};assert ready,'cycle';done|=ready
    return pred

def check(artifact):
    assert type(artifact) is dict and set(artifact)=={'schema','input','budget','root','root_value','nodes','packed'}
    assert artifact['schema']=='dag-budget-value-certificate-v1';case=artifact['input'];pred=validate(case);cp=case['cp'];n=len(cp);full=(1<<n)-1
    B=artifact['budget'];assert type(B) is int and B>=0
    nodes=artifact['nodes'];packs=artifact['packed'];assert type(nodes) is dict and type(packs) is dict
    assert artifact['root']==f'{full}:{B}';assert type(artifact['root_value']) is int
    visited={};pack_curves={};used_packs=set();kinds={}
    def get(mask,b):
        name=f'{mask}:{b}'
        if name in visited:return visited[name]
        assert name in nodes,name;node=nodes[name]
        assert type(node) is dict and node['mask']==mask and type(node['mask']) is int and node['budget']==b and type(node['budget']) is int
        assert 0<=mask<=full and 0<=b<=B
        jobs={i for i in range(n) if mask>>i&1};done=set(range(n))-jobs
        assert all(pred[i]<=done for i in done),'unfinished set is not an upset'
        val=node['value'];kind=node['kind'];assert type(val) is int and val>=0
        allowed={'mask','budget','value','kind'}
        if kind=='zero':assert not mask or not b;expected=0
        elif kind=='bound':
            allowed.add('threshold');assert mask and b;t=node['threshold'];assert type(t) is int and t>=0
            chunks=[]
            for i in jobs:
                cost,premium=cp[i];q,r=divmod(premium,cost)
                if q:chunks.append((cost,q))
                if r:chunks.append((r,1))
            remain=b;lower=0
            for cost,count in sorted(chunks,reverse=True):
                used=min(count,remain);lower+=used*cost;remain-=used
            upper=sum(cp[i][1] for i in jobs if cp[i][0]>t)+b*t
            assert lower==upper;expected=lower
        elif kind=='packed':
            assert mask and b;packed_key=str(mask);assert packed_key in packs;used_packs.add(packed_key)
            if packed_key not in pack_curves:
                ordered=sorted(jobs);index={i:j for j,i in enumerate(ordered)}
                sub=dict(cp=[cp[i] for i in ordered],edges=[[index[u],index[v]] for u,v in case['edges'] if u in jobs and v in jobs])
                data=packs[packed_key];assert data['input']==sub and data['route']=='ordered'
                report=packed_checker.check(data);assert not report['violations'],report
                pack_curves[packed_key]=packed_checker.Curve(data['value_slopes'])
            expected=pack_curves[packed_key].value(b)
        elif kind=='peak':
            allowed|={'job','peak'};assert mask and b
            available=[i for i in sorted(jobs) if pred[i]<=done]
            i=node['job'];k=node['peak'];assert type(i) is int and i==min(available,key=lambda j:(cp[j][0],j));assert type(k) is int and 0<=k<=b
            child=mask^(1<<i);cost=cp[i][0];g=get(child,k)
            if k:assert g-get(child,k-1)>=cost
            if k<b:assert get(child,k+1)-g<=cost
            protected=min(cp[j][1]+get(mask^(1<<j),b) for j in available)
            expected=min(protected,g+cost*(b-k))
        else:raise AssertionError(('kind',kind))
        assert set(node)==allowed and val==expected,(name,val,expected);visited[name]=val;kinds[kind]=kinds.get(kind,0)+1;return val
    result=get(full,B);assert result==artifact['root_value'];assert set(visited)==set(nodes),'extraneous nodes';assert used_packs==set(packs),'extraneous packed data'
    return dict(value=result,nodes=len(visited),packed_masks=len(used_packs),kinds=kinds,certificate_scope='REQUESTED_ROOT_VALUE',relies_on='DAG concavity theorem and inherited allocation/fixed-protection bounds')
