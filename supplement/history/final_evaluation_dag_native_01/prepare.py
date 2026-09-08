from pathlib import Path
from functools import lru_cache
import collections,datetime,hashlib,json,math,subprocess,sys,time,traceback
ROOT=Path(__file__).resolve().parent;SESSION=ROOT.parent
sys.path.insert(0,str(SESSION/'dependency_native_01'));import experiment as dev
sys.path.insert(0,str(SESSION/'final_evaluation_dag_01'));import evaluate as validation
JAVA=dev.JAVA;JAVAC=dev.JAVAC
KINDS=['hybrid','fixed','look_fast','look_protected','cached']
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,data):
    with (ROOT/name).open('x') as f:json.dump(data,f,indent=2,sort_keys=True);f.write('\n')
def seq(xs):return ','.join(map(str,xs)) or '-'
def hybrid_policy(case,compiled):
    cp=case['cp'];n=len(cp)
    @lru_cache(None)
    def choose(mask,b):
        if compiled['route']=='ordered':
            k=n-mask.bit_count()
            assert mask==sum(1<<j for j in compiled['order'][k:])
            i,mode=validation.hybrid.choose(compiled,k,b)
        else:i,mode=validation.hybrid.choose(compiled,mask,b)
        assert mask>>i&1 and not case['pred'][i]&mask
        return i,'P' if mode=='protected' else 'F'
    @lru_cache(None)
    def actual(mask,b):
        if not mask:return 0
        i,mode=choose(mask,b);child=mask^(1<<i);c,p=cp[i]
        if mode=='P':return p+actual(child,b)
        if not b:return actual(child,b)
        return max(actual(child,b),c+actual(mask,b-1))
    def paths(mask,b,trace='',actions=()):
        if not mask:yield trace,list(actions);return
        i,mode=choose(mask,b);child=mask^(1<<i)
        if mode=='P':yield from paths(child,b,trace,actions+((i,'P'),))
        else:
            yield from paths(child,b,trace+'S',actions+((i,'S'),))
            if b:yield from paths(mask,b-1,trace+'F',actions+((i,'F'),))
    return actual,paths
def main():
    start=time.monotonic()
    for f in json.loads((ROOT/'GENERATOR_MANIFEST.json').read_text())['files']:
        assert sha(Path(f['path']))==f['sha256']
    generated=json.loads((ROOT/'VECTORS.json').read_text())['vectors']
    controls=[dict(id='parent-postwrite-ordered',cp=[[2,1],[3,2]],edges=[[0,1]],expected_route='ordered',regression=True),
              dict(id='parent-postwrite-ideal',cp=[[3,1],[1,2]],edges=[[0,1]],expected_route='ideal',regression=False)]
    cases={};compiled_by_id={};mathrows=[];(ROOT/'profiles').mkdir();(ROOT/'artifacts').mkdir()
    for raw in generated+controls:
        case=dict(raw);n=len(case['cp']);control=raw in controls;case['control']=control
        maxb=1 if control else 4;case['max_budget']=maxb;case['scale']=8
        case['pred']=[sum(1<<a for a,b in case['edges'] if b==j) for j in range(n)]
        case['d']=math.lcm(*(c for c,p in case['cp']))
        case['weights']=[case['d']*p//c for c,p in case['cp']]
        case['lengths']=[8*c-case['pred'][i].bit_count() for i,(c,p) in enumerate(case['cp'])]
        assert all(x>0 for x in case['lengths'])
        case['scalar']=dev.scalar(case,maxb);case['orders']=dev.topological_orders(case)
        input_case=dict(cp=case['cp'],edges=case['edges'])
        encoded=json.dumps(validation.hybrid.compile_case(input_case),sort_keys=True,separators=(',',':')).encode()
        data=json.loads(encoded);assert data['route']==case['expected_route']
        with (ROOT/'artifacts'/(case['id']+'.json')).open('xb') as f:f.write(encoded)
        if data['route']=='ordered':certificate=validation.packed.check(data)
        else:
            shape=validation.structure.check(data);certificate=validation.bellman.check(data);certificate['shape']=shape
        assert not certificate['violations']
        compiled=validation.hybrid.load(data);gaps=[];value_cells=0
        if data['route']=='ordered':
            curve=validation.packed.Curve(data['value_slopes'])
            for k in range(n+1):
                suffix=data['order'][k:];mask=sum(1<<i for i in suffix);premium=sum(case['cp'][i][1] for i in suffix)
                for b in range(maxb+1):
                    value=min(curve.value(b),premium);value_cells+=1
                    if value!=case['scalar'][mask][b]:gaps.append([mask,b,value,case['scalar'][mask][b]])
            with (ROOT/'profiles'/(case['id']+'.tsv')).open('x') as f:
                f.write('ORDER\t'+seq(data['order'])+'\nTHRESHOLDS\t'+seq(data['protect_at_budget'])+'\n')
        else:
            for mask,profile in compiled['curves'].items():
                for b in range(maxb+1):
                    value=validation.bellman.value_slope(profile,b)[0];value_cells+=1
                    if value!=case['scalar'][mask][b]:gaps.append([mask,b,value,case['scalar'][mask][b]])
            with (ROOT/'profiles'/(case['id']+'.tsv')).open('x') as f:
                for mask,profile in sorted(compiled['curves'].items()):f.write(str(mask)+'\t'+';'.join(':'.join(map(str,row)) for row in profile)+'\n')
        mathrows.append(dict(id=case['id'],route=data['route'],value_cells=value_cells,gaps=gaps,
                             root_values=case['scalar'][-1],topological_orders=len(case['orders']),certificate=certificate,
                             artifact_sha256=hashlib.sha256(encoded).hexdigest(),artifact_bytes=len(encoded)))
        cases[case['id']]=case;compiled_by_id[case['id']]=compiled
    save('MATH_VALIDATION.json',dict(utc=now(),rows=mathrows,observed_model_preparation=True,native_outcomes_observed=False))
    assert not any(r['gaps'] for r in mathrows)
    units=[];cells=[]
    for case in cases.values():
        full=(1<<len(case['cp']))-1;control=case['control'];budgets=[1] if control else [0,1,2,4]
        for b in budgets:
            order_values=[(dev.fixed_function(case['cp'],order)(full,b),order) for order in case['orders']]
            best_value,best_order=min(order_values)
            for layout in ('distinct','colliding'):
                cell=dict(id=f"{case['id']}/b{b}/{layout}",case=case['id'],budget=b,layout=layout,
                          route=case['expected_route'],control=control,model_optimum=case['scalar'][full][b],
                          best_fixed_value=best_value,best_fixed_order=best_order,policies=[])
                for kind in ['hybrid'] if control else KINDS:
                    actual,paths=hybrid_policy(case,compiled_by_id[case['id']]) if kind=='hybrid' else dev.policy(case,kind,b,best_order)
                    group=[]
                    for k,(outcomes,actions) in enumerate(paths(full,b)):
                        u=dict(id=cell['id']+'/'+kind+f'/path_{k:05}',case=case['id'],cell=cell['id'],kind=kind,
                               layout=layout,budget=b,order=best_order if kind=='fixed' else [],outcomes=outcomes,actions=actions,postwrite=control)
                        u['expected']=dev.expected(case,u);units.append(u);group.append(u)
                        if control:break
                    target=8*case['d']*(sum(c for c,p in case['cp'])+actual(full,b))
                    if not control:assert max(u['expected']['cost'] for u in group)==target
                    if kind=='hybrid':assert actual(full,b)==case['scalar'][full][b]
                    if kind=='fixed':assert actual(full,b)==best_value
                    cell['policies'].append(dict(kind=kind,units=len(group),expected_max=max(u['expected']['cost'] for u in group),abstract_worst=actual(full,b),target=target))
                cells.append(cell)
    assert len({u['id'] for u in units})==len(units)
    save('INPUTS.json',dict(utc=now(),cases=cases,cells=cells,units=units,final_evaluation=True))
    with (ROOT/'CASES.tsv').open('x') as f:
        for case in cases.values():
            f.write('\t'.join([case['id'],seq([c for c,p in case['cp']]),seq([p for c,p in case['cp']]),seq(case['pred']),seq(case['lengths']),seq(case['weights']),str(case['d']),'8',f"profiles/{case['id']}.tsv"] )+'\n')
    with (ROOT/'INPUTS.tsv').open('x') as f:
        for u in units:f.write('\t'.join([u['id'],u['case'],u['kind'],u['layout'],str(u['budget']),seq(u['order']),u['outcomes'] or '-',str(int(u['postwrite']))])+'\n')
    summary=dict(utc=now(),core_vectors=48,core_priced_roots=192,core_layout_cells=384,core_policy_cells=1920,
                 control_vectors=2,control_units=4,terminal_units=len(units),
                 paths_by_kind=dict(collections.Counter(u['kind'] for u in units)),
                 topological_orders=sum(len(c['orders']) for c in cases.values() if not c['control']),
                 elapsed_seconds=time.monotonic()-start,native_outcomes_observed=False)
    save('PREPARATION_RECEIPT.json',summary);print(json.dumps(summary,indent=2))
if __name__=='__main__':
    try:main()
    except Exception:
        if not (ROOT/'PREPARATION_FAILURE.json').exists():save('PREPARATION_FAILURE.json',dict(utc=now(),error=traceback.format_exc()))
        raise
