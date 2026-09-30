#!/usr/bin/env python3
"""Preregistered secondary-only maintenance protocol with explicit election gap."""
import argparse
import json
from pathlib import Path


def lts(initial, states, edges): return dict(initial=initial, states=states, edges=edges)


def model(m, merged=False):
    n=3
    if m not in (2,3): raise ValueError('Only preregistered m=2,3')
    transfers=['ablation.merge.transfers'] if merged else ['rho_'+str(i) for i in range(1,n+1)]
    serve=['serve_'+str(i) for i in range(1,n+1)]
    ready=['ready_'+str(i) for i in range(1,n+1)]
    elect=['elect_'+str(i) for i in range(1,n+1)]
    steps=['stepdown_'+str(i)+'_'+str(j) for i in range(1,n+1) for j in range(1,n+1) if i!=j]
    ordinary=serve+ready+elect+steps
    components=[]
    for i in range(1,n+1):
        edges=[[q,'serve_'+str(i),q] for q in ('P','S','E')]+[['E','elect_'+str(i),'P']]
        for j in range(1,n+1):
            if i!=j:
                edges += [['P','stepdown_'+str(i)+'_'+str(j),'S'],['S','stepdown_'+str(j)+'_'+str(i),'E']]
        old=lts('P' if i==1 else 'S',['P','S','E'],edges)
        new=lts('P' if i==2 else 'S',['P','S','E','B'],edges+[['B','ready_'+str(i),'S']])
        components.append(dict(id='replica_'+str(i),old=old,new=new,transfer={'S':['B']},
                               transfer_action=transfers[0] if merged else transfers[i-1]))
    changes=[]
    for q in range(m,n+1):
        for action in transfers:
            target=q-(n if merged else 1)
            changes.append([str(q),action,str(target) if target>=m else 'ERROR'])
        for action in ready: changes.append([str(q),action,str(min(q+1,n))])
    tester=dict(initial=str(n),states=[str(q) for q in range(m,n+1)]+['ERROR'],errors=['ERROR'],
                alphabet=ordinary+transfers,changes=changes)
    oldphysical=[['OLD','P' if i==1 else 'S'] for i in range(1,n+1)]
    newphysical=[['NEW','P' if i==2 else 'S'] for i in range(1,n+1)]
    interval=dict(id='ready_budget',role='interval',tester=tester,
                  activation=dict(entries=[dict(physical=oldphysical,tester_state=str(n),residual_state=str(n))]))
    graph=lts('q',['q'],[['q',a,'q'] for a in serve])
    controller=lts('q',['q','alphabet_only'],graph['edges']+[['alphabet_only',a,'alphabet_only'] for a in ordinary if a not in serve])
    endpoints={}
    for version,physical in [('old',oldphysical),('new',newphysical)]:
        projection=dict(physical=physical,testers={})
        if version=='new': projection['goal_id']='replica2_primary'
        endpoints[version]=dict(lts=graph,controller=controller,projection={'q':projection})
        if version=='new':endpoints[version]['loadable']=['q']
    result=dict(schema='fg-ducs-witness-v1',id='db_n3_m'+str(m)+'_'+('all' if merged else 'fine'),
                family='DB-Rolling',parameters=dict(n=n,m=m,k=n if merged else 1),ordinary=ordinary,
                controllable=serve+steps,components=components,requirements=[interval],precedence=[],endpoints=endpoints,
                metadata=dict(mechanism='M1+M2',contribution='L1/L3',
                              expected_decision='WIN' if m==2 and not merged else 'LOSS',
                              source='https://www.mongodb.com/docs/v7.0/tutorial/upgrade-to-enterprise-replica-set/',
                              scope='constructed secondary-only maintenance contract; finite election/rejoin abstraction; no claim of uninterrupted writes'))
    if merged:result['generated_contract_mode']='transfers'
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=Path(__file__).parent/'v2/inputs');args=p.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    for m in (2,3):
        for merged in (False,True):
            data=model(m,merged);path=args.output/(data['id']+'.json');text=json.dumps(data,indent=2)+'\n'
            if path.exists():
                if path.read_text()!=text:raise SystemExit('Refusing changed input '+str(path))
            else:
                with path.open('x') as f:f.write(text)
            print(path)


if __name__=='__main__':main()
