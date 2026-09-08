import json,time
from ortools.sat.python import cp_model
import checker

def solve(case,budget=2,seconds=1):
    start=time.perf_counter();checker.validate(case);assert budget in (1,2)
    cp=case['cp'];n=len(cp);P=sum(p for c,p in cp);model=cp_model.CpModel()
    chunks=[]
    for c,p in cp:
        q,r=divmod(p,c)
        if q:chunks.append((c,q))
        if r:chunks.append((r,1))
    lower=0;left=budget
    for height,count in sorted(chunks,reverse=True):
        used=min(left,count);lower+=height*used;left-=used
    upper,threshold=min((sum(p for c,p in cp if c>t)+budget*t,t) for t in {0}|{c for c,p in cp})
    pred=[set(u for u,v in case['edges'] if v==i) for i in range(n)]
    done=set();hint_order=[]
    while len(done)<n:
        i=min(i for i in range(n) if i not in done and pred[i]<=done)
        hint_order.append(i);done.add(i)
    hint_rank={i:k for k,i in enumerate(hint_order)}
    def spine(tag,active):
        rank=[model.new_int_var(0,n-1,f'{tag}r{i}') for i in range(n)]
        model.add_all_different(rank)
        for u,v in case['edges']:model.add(rank[u]<rank[v])
        before={}
        for i in range(n):
            for j in range(i+1,n):
                bit=model.new_bool_var(f'{tag}b{i}_{j}')
                model.add(rank[i]<rank[j]).only_enforce_if(bit)
                model.add(rank[i]>rank[j]).only_enforce_if(bit.Not())
                before[i,j]=bit;before[j,i]=bit.Not()
        h=[model.new_bool_var(f'{tag}h{i}') for i in range(n)]
        for i,(_,p) in enumerate(cp):
            model.add(h[i]<=active[i])
            if p==0:model.add(h[i]==active[i])
        prefix=[]
        for i in range(n):
            terms=[]
            for j,(_,p) in enumerate(cp):
                if i==j or p==0:continue
                z=model.new_bool_var(f'{tag}z{j}_{i}');b=before[j,i]
                model.add_bool_and([h[j],b]).only_enforce_if(z)
                model.add_bool_or([h[j].Not(),b.Not(),z])
                terms.append(p*z)
            q=model.new_int_var(0,P,f'{tag}q{i}');model.add(q==sum(terms));prefix.append(q)
        K=model.new_int_var(0,P,f'{tag}K');model.add(K>=sum(p*h[i] for i,(_,p) in enumerate(cp)))
        return dict(rank=rank,before=before,h=h,prefix=prefix,K=K,active=active)
    root=spine('r',[1]*n);children={}
    if budget==1:
        for i,(c,p) in enumerate(cp):model.add(root['K']>=root['prefix'][i]+c).only_enforce_if(root['h'][i].Not())
    else:
        for f,(c,p) in enumerate(cp):
            active=[1 if i==f else root['before'][f,i] for i in range(n)]
            child=spine(f'f{f}_',active);children[f]=child
            for i,(ci,pi) in enumerate(cp):
                model.add(child['K']>=child['prefix'][i]+ci).only_enforce_if([active[i],child['h'][i].Not()])
            model.add(root['K']>=root['prefix'][f]+c+child['K']).only_enforce_if(root['h'][f].Not())
    model.add(root['K']>=lower);model.add(root['K']<=upper)
    def hints(node,active_set):
        paid=worst=0
        for i in hint_order:
            model.add_hint(node['rank'][i],hint_rank[i])
            protected=i in active_set and (cp[i][0]>threshold or cp[i][1]==0)
            model.add_hint(node['h'][i],int(protected))
            if protected:paid+=cp[i][1]
            elif i in active_set:worst=max(worst,paid+cp[i][0])
        model.add_hint(node['K'],max(paid,worst))
    if budget==1:hints(root,set(range(n)))
    else:
        for i in range(n):
            model.add_hint(root['rank'][i],hint_rank[i])
            model.add_hint(root['h'][i],int(cp[i][0]>threshold or cp[i][1]==0))
        model.add_hint(root['K'],upper)
        for f in range(n):hints(children[f],{i for i in range(n) if hint_rank[i]>=hint_rank[f]})
    model.minimize(root['K']);build_seconds=time.perf_counter()-start
    solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=seconds
    solver.parameters.num_search_workers=1;solver.parameters.random_seed=20260908
    before=time.perf_counter();status=solver.solve(model);solve_seconds=time.perf_counter()-before
    row=dict(status='INVALID',solver_status=solver.status_name(status),build_seconds=build_seconds,
             solve_seconds=solve_seconds,lower_bound=solver.best_objective_bound,
             solver_stats=solver.response_stats(),solution_info=solver.solution_info(),
             conflicts=solver.num_conflicts,branches=solver.num_branches,
             model_variables=len(model.proto.variables),model_constraints=len(model.proto.constraints),
             allocation_lower=lower,fixed_mode_upper=upper,hint_threshold=threshold)
    before=time.perf_counter()
    if status in (cp_model.OPTIMAL,cp_model.FEASIBLE):
        def extract(node):
            order=sorted(range(n),key=lambda i:solver.value(node['rank'][i]))
            return [[i,'P' if solver.value(node['h'][i]) else 'F'] for i in order if solver.value(node['active'][i])]
        rs=extract(root);artifact=dict(schema='specified-budget-contingent-order-v1',budget=budget,root=rs,
                                      branches={str(i):extract(children[i]) for i,mode in rs if mode=='F'} if budget==2 else {})
        encoded=json.dumps(artifact,sort_keys=True,separators=(',',':')).encode();artifact=json.loads(encoded)
        report=checker.check(case,artifact);v=solver.value(root['K']);assert report['value']<=v
        if status==cp_model.OPTIMAL:assert report['value']==v
        row.update(status='SUCCESS' if status==cp_model.OPTIMAL else 'TIMEOUT',value=report['value'],model_value=v,
                   artifact=artifact,artifact_bytes=len(encoded),certificate_report=report)
    elif status==cp_model.UNKNOWN:row['status']='TIMEOUT'
    elif status==cp_model.INFEASIBLE:row.update(status='FAILURE',reason='all-protected is feasible')
    row['extract_serialize_check_seconds']=time.perf_counter()-before;row['total_seconds']=time.perf_counter()-start
    return row
