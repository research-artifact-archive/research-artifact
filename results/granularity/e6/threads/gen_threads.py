#!/usr/bin/env python3
"""Create-only bounded-queue workers; registered null and negative controls."""
import argparse,itertools,json
from collections import deque
from pathlib import Path


def make(n,b,regime,grouped=False):
    dispatch=['dispatch_'+str(i+1) for i in range(n)]
    finish=['finish_'+str(i+1) for i in range(n)]
    ordinary=['arrival']+dispatch+finish;components=[]
    for i in range(n):
        if i==0:
            states=[f'{s}_q{q}' for s in ('I','B') for q in range(b+1)];edges=[]
            for s in ('I','B'):
                for q in range(b+1):
                    source=f'{s}_q{q}'
                    if q<b:edges.append([source,'arrival',f'{s}_q{q+1}'])
                    elif regime=='saturated_offers':edges.append([source,'arrival',source])
                    if q>0:
                        if s=='I':edges.append([source,dispatch[0],f'B_q{q-1}'])
                        for a in dispatch[1:]:edges.append([source,a,f'{s}_q{q-1}'])
                    if s=='B':edges.append([source,finish[0],f'I_q{q}'])
            lts=dict(states=states,initial='I_q0',edges=edges)
            transfer={f'I_q{q}':[f'I_q{q}'] for q in range(b+1)}
        else:
            lts=dict(states=['I','B'],initial='I',edges=[['I',dispatch[i],'B'],['B',finish[i],'I']]);transfer={'I':['I']}
        components.append(dict(id='worker_'+str(i+1),old=lts,new=json.loads(json.dumps(lts)),
                               transfer_action='ablation.merge.transfers' if grouped else 'rho_'+str(i+1),transfer=transfer))
    # Generate endpoints by the explicit queue/worker transition rule, rather than
    # reusing the independent local-LTS product checker.
    initial=(0,)+(0,)*n;seen={initial};todo=deque([initial]);rawedges=[]
    while todo:
        state=todo.popleft();q,busy=state[0],state[1:];out=[]
        if q<b:out.append(('arrival',(q+1,)+busy))
        elif regime=='saturated_offers':out.append(('arrival',state))
        for i in range(n):
            flags=list(busy)
            if not busy[i] and q>0:
                flags[i]=1;out.append((dispatch[i],(q-1,)+tuple(flags)))
            if busy[i]:
                flags[i]=0;out.append((finish[i],(q,)+tuple(flags)))
        for a,t in out:
            rawedges.append((state,a,t))
            if t not in seen:seen.add(t);todo.append(t)
    order=sorted(seen);names={s:'s'+str(i) for i,s in enumerate(order)}
    def endpoint(tag):
        projection={}
        for state in order:
            q,busy=state[0],state[1:]
            physical=[[tag,('B' if busy[0] else 'I')+f'_q{q}']]+[[tag,'B' if v else 'I'] for v in busy[1:]]
            p=dict(physical=physical,testers={})
            if tag=='NEW':p['goal_id']='load_'+names[state]
            projection[names[state]]=p
        out=dict(lts=dict(states=list(names.values()),initial=names[initial],edges=[[names[s],a,names[t]] for s,a,t in rawedges]),
                 controller=dict(states=['C'],initial='C',edges=[['C',a,'C'] for a in ordinary]),projection=projection)
        if tag=='NEW':out['loadable']=list(names.values())
        return out
    ident=f'threads_n{n:02}_b{b:02}_{regime}_'+('all' if grouped else 'fine')
    data=dict(schema='fg-ducs-witness-v1',id=ident,family='threads',parameters=dict(n=n,B=b,regime=regime,group='all' if grouped else 'fine'),
        ordinary=ordinary,controllable=dispatch,components=components,requirements=[],precedence=[],
        endpoints=dict(old=endpoint('OLD'),new=endpoint('NEW')),
        metadata=dict(expected_decision='WIN' if regime=='backpressure' else 'LOSS',
            mechanism='Quiescence/progress null and negative controls, not an L1 separation witness.',
            queue='Finite queue state is carried by worker 1 and preserved by its idle-only transfer; no extra component transfer is introduced.',
            versions='Old and new use the same scheduling abstraction; only version tags and the fixed transfer domain distinguish them.',
            update_point='Every worker transfers only while idle. All-group requires all workers idle simultaneously.',
            endpoint_scope='Every reachable old endpoint state is an initial snapshot; every reachable new endpoint state is loadable.',
            arrival_semantics='No arrival is enabled at capacity.' if regime=='backpressure' else 'A full queue accepts/drops an offered arrival without changing state; this uncontrollable self-loop permits infinite update obstruction without fairness.',
            source_url='https://www.cs.umd.edu/~mwh/papers/kitsune-journal.pdf',source_doi='10.1145/2629460',
            source_scope='Kitsune motivates per-thread update points and quiescence. Queue, dispatch, and arrival regimes are this explicit finite abstraction, not a reproduction of Kitsune.'))
    if grouped:data['generated_contract_mode']='transfers'
    return data


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=Path(__file__).parent/'v1');args=p.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);(out/'inputs').mkdir()
    jobs=[]
    for n in range(2,7):
        for b in (1,2):
            for regime in ('backpressure','saturated_offers'):
                fine=make(n,b,regime);coarse=make(n,b,regime,True)
                for data in (fine,coarse):
                    with (out/'inputs'/(data['id']+'.json')).open('x') as f:json.dump(data,f,indent=2);f.write('\n')
                base=f'threads_n{n:02}_b{b:02}_{regime}'
                for name,data,merge,solver in [('fine_lazy',fine,'none','lazy'),('e1merged_lazy',fine,'transfers','lazy'),('generated_all_lazy',coarse,'none','lazy'),('fine_df',fine,'none','direct_full')]:
                    job=dict(id=base+'_'+name,input='inputs/'+data['id']+'.json',merge=merge,solver=solver,expected_decision=data['metadata']['expected_decision'],parameters=data['parameters'])
                    if merge=='transfers':job.update(compare_input='inputs/'+coarse['id']+'.json',compare_merge='none')
                    jobs.append(job)
    e6=Path(__file__).resolve().parents[1];rel=str(out.relative_to(e6))
    config=dict(schema='e6-family-run-v1',family='threads',version='v1',heap='32g',timeout_seconds=1200,trials=1,
        start_cutoff='2026-09-30T09:39:00+09:00',deadline='2026-09-30T10:00:00+09:00',jobs=jobs,
        frozen_paths=['threads/gen_threads.py','threads/validate_threads.py','threads/analyze_threads.py','threads/README.md','rolling/validate_endpoints.py','common/witness.schema.json','common/SCHEMA.md'],
        endpoint_checks=[['python3','-B','threads/validate_threads.py',rel]],
        preflight_jobs=['threads_n02_b01_backpressure_fine_lazy','threads_n02_b01_backpressure_e1merged_lazy','threads_n02_b01_saturated_offers_fine_lazy','threads_n02_b01_saturated_offers_e1merged_lazy'],
        analysis_commands=[['python3','-B','threads/analyze_threads.py',rel]])
    with (out/'config.json').open('x') as f:json.dump(config,f,indent=2);f.write('\n')
    print(json.dumps(dict(inputs=40,jobs=len(jobs),out=str(out),create_only=True)))

if __name__=='__main__':main()
