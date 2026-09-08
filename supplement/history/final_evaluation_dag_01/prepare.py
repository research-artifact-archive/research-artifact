"""Materialize final inputs and structural denominators; never solve values."""
from pathlib import Path
import collections,hashlib,itertools,json
import primitive
ROOT=Path(__file__).resolve().parent
def save(name,data):
    with (ROOT/name).open('x') as f:json.dump(data,f,indent=2);f.write('\n')
def key(cp,edges):return json.dumps([cp,sorted(edges)],separators=(',',':'))
def main():
    paths=['dependency_retry_01/INPUTS.json','dependency_curves_01/INPUTS.json',
           'dependency_hybrid_01/SMALL_INPUTS.json','final_evaluation_01/semantic/INPUTS.json',
           'final_evaluation_dag_01/PREFLIGHT_INPUTS.json']
    priors={}
    for path in paths:
        prior=json.loads((ROOT.parent/path).read_text());index=collections.defaultdict(list)
        for row in prior:
            cp=row.get('cp',row.get('jobs'))
            if cp is not None:index[key(cp,row.get('edges',[]))].append(row['id'])
        priors[path]=index
    alphabet=list(itertools.product((1,2),range(4)));cases=[];shapes=[]
    for n in range(1,4):
        possible=list(itertools.combinations(range(n),2))
        for bits in range(1<<len(possible)):
            edges=[edge for k,edge in enumerate(possible) if bits>>k&1]
            g=primitive.graph([(1,0)]*n,edges,4)
            shape=dict(id=f'n{n}-E{bits}',n=n,edges=edges,states=len(g[0]),actions=len(g[1]),
                       outcomes=sum(len(a['edges']) for a in g[1]),price_vectors=len(alphabet)**n)
            shapes.append(shape)
            for cp in itertools.product(alphabet,repeat=n):
                k=key(cp,edges)
                overlaps={path:index[k] for path,index in priors.items() if k in index}
                cases.append(dict(id=f'dag-final-{len(cases):04}',cp=cp,edges=edges,budget=4,
                    shape_id=shape['id'],group='independent_regression' if not edges else 'dependent',
                    prior_exact_inputs=overlaps,expected_structure={x:shape[x] for x in ('states','actions','outcomes')}))
    save('INPUTS.json',cases)
    totals={x:sum(s[x]*s['price_vectors'] for s in shapes) for x in ('states','actions','outcomes')}
    summary=dict(planned_inputs=len(cases),root_values=5*len(cases),shapes=shapes,
                 groups=dict(collections.Counter(c['group'] for c in cases)),structural_totals=totals,
                 overlap_counts={path:sum(path in c['prior_exact_inputs'] for c in cases) for path in paths},
                 overlap_any=sum(bool(c['prior_exact_inputs']) for c in cases),
                 dependent_overlap_any=sum(c['group']=='dependent' and bool(c['prior_exact_inputs']) for c in cases),
                 input_sha256=hashlib.sha256((ROOT/'INPUTS.json').read_bytes()).hexdigest(),
                 value_solving_performed=False,held_out_population=False,
                 provenance='complete author-defined labeled forward-DAG grid; edge-redundant graphs kept as distinct specified inputs')
    save('DENOMINATORS.json',summary);print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
