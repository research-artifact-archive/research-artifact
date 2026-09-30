#!/usr/bin/env python3
"""Independent local-product endpoints and explicit queue/transfer domain census."""
import hashlib,importlib.util,itertools,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
E6=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('endpoint_product',E6/'rolling/validate_endpoints.py');product=importlib.util.module_from_spec(spec);spec.loader.exec_module(product)


def main():
    family=Path(sys.argv[1]).resolve();records=[];models={}
    for path in sorted((family/'inputs').glob('*.json')):
        d=json.loads(path.read_text());n,b,regime=(d['parameters'][k] for k in ('n','B','regime'));group=d['parameters']['group']
        assert n in range(2,7) and b in (1,2) and regime in ('backpressure','saturated_offers')
        assert len(d['components'])==n and d['requirements']==[] and d['precedence']==[]
        assert d['ordinary']==['arrival']+[f'dispatch_{i}' for i in range(1,n+1)]+[f'finish_{i}' for i in range(1,n+1)]
        assert d['controllable']==[f'dispatch_{i}' for i in range(1,n+1)]
        census=[]
        for i,c in enumerate(d['components']):
            assert c['old']==c['new'],'Version abstraction must be identical.'
            states=c['old']['states'];edges=set(map(tuple,c['old']['edges']))
            expected=set()
            if i==0:
                assert set(states)=={f'{s}_q{q}' for s in ('I','B') for q in range(b+1)} and c['old']['initial']=='I_q0'
                for s in ('I','B'):
                    for q in range(b+1):
                        src=f'{s}_q{q}'
                        if q<b:expected.add((src,'arrival',f'{s}_q{q+1}'))
                        elif regime=='saturated_offers':expected.add((src,'arrival',src))
                        if s=='B':expected.add((src,'finish_1',f'I_q{q}'))
                        if q:
                            if s=='I':expected.add((src,'dispatch_1',f'B_q{q-1}'))
                            for j in range(2,n+1):expected.add((src,f'dispatch_{j}',f'{s}_q{q-1}'))
                assert c['transfer']=={f'I_q{q}':[f'I_q{q}'] for q in range(b+1)}
            else:
                assert set(states)=={'I','B'} and c['old']['initial']=='I'
                expected={('I',f'dispatch_{i+1}','B'),('B',f'finish_{i+1}','I')};assert c['transfer']=={'I':['I']}
            assert edges==expected and len(edges)==len(c['old']['edges'])
            assert c['transfer_action']==('ablation.merge.transfers' if group=='all' else f'rho_{i+1}')
            census.append(dict(component=c['id'],local_states=len(states),transfer_domain=len(c['transfer']),pairs=sum(len(x) for x in c['transfer'].values())))
        assert d.get('generated_contract_mode')==('transfers' if group=='all' else None)
        old,new=product.validate(d,'old'),product.validate(d,'new')
        expected_states=(b+1)*2**n
        assert old['projected_states']==new['projected_states']==expected_states
        assert set(d['endpoints']['new']['loadable'])==set(d['endpoints']['new']['lts']['states'])
        assert len(d['endpoints']['old']['projection'])==expected_states
        for version in ('old','new'):
            endpoint=d['endpoints'][version]
            assert {a for _,a,_ in endpoint['controller']['edges']}==set(d['ordinary'])
        models[(n,b,regime,group)]=d
        records.append(dict(input=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),old=old,new=new,components=census,
                            full_queue_uncontrollable_self_loop=(regime=='saturated_offers')))
    assert len(records)==40
    for n in range(2,7):
        for b in (1,2):
            for regime in ('backpressure','saturated_offers'):
                fine=models[n,b,regime,'fine'];all_=models[n,b,regime,'all']
                assert all(fine[k]==all_[k] for k in ('ordinary','controllable','requirements','precedence','endpoints'))
                for a,z in zip(fine['components'],all_['components']):assert all(a[k]==z[k] for k in ('id','old','new','transfer'))
    try:import jsonschema
    except ImportError:jsonschema=None
    if jsonschema:
        schema=json.loads((E6/'common/witness.schema.json').read_text())
        for d in models.values():jsonschema.Draft202012Validator(schema).validate(d)
    out=family/(sys.argv[2] if len(sys.argv)>2 else 'validation/endpoint_products.json');out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('x') as f:json.dump(dict(status='PASS',inputs=40,endpoint_products=80,json_schema_checked=jsonschema is not None,records=records),f,indent=2);f.write('\n')
    print(json.dumps(dict(status='PASS',inputs=40,endpoint_products=80,json_schema_checked=jsonschema is not None)))

if __name__=='__main__':main()
