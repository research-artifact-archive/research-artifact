"""Structural population freeze only; never evaluates a cost or candidate formula."""
import hashlib
import itertools
import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parent
TYPES = [('Z',0,0,0), ('E',2,2,2), ('N0',2,0,2), ('N1',3,1,4),
         ('T',2,2,3), ('P0',0,2,2), ('P1',1,2,3), ('P2',2,4,4)]

def dump(path, value):
    with path.open('x') as out:
        json.dump(value, out, separators=(',',':'), sort_keys=True)
        out.write('\n')

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    if (BASE / 'FREEZE01.json').exists():
        raise RuntimeError('freeze already exists; no overwrite')
    catalog, graphs, graph_counts = {}, [], {}
    for n in range(4):
        pairs = [(i,j) for i in range(n) for j in range(n) if i != j]
        graph_counts[str(n)] = 0
        for emask in range(1 << len(pairs)):
            edges = [list(e) for at,e in enumerate(pairs) if emask >> at & 1]
            reach = [[False]*n for _ in range(n)]
            for i,j in edges:
                reach[i][j] = True
            for mid in range(n):
                for i in range(n):
                    for j in range(n):
                        reach[i][j] |= reach[i][mid] and reach[mid][j]
            if any(reach[i][i] for i in range(n)):
                continue
            gid = len(graphs)
            graph_counts[str(n)] += 1
            pred = [sum(1 << i for i,j in edges if j == target) for target in range(n)]
            ideals = [d for d in range(1 << n)
                      if all(not (d >> j & 1) or pred[j] & d == pred[j] for j in range(n))]
            graph = dict(id=gid,n=n,edges=edges,ideals=ideals)
            graphs.append(graph)
            for d in sorted(ideals, key=lambda d: (-d.bit_count(),d)):
                cid = f'{gid}:{d}'
                ready = [i for i in range(n) if not (d >> i & 1) and pred[i] & d == pred[i]]
                policies = []
                if not ready:
                    assert d == (1 << n)-1
                    policies.append(dict(root=['T'],leaves=[[]]))
                for i in ready:
                    children = catalog[f'{gid}:{d | (1 << i)}']['policies']
                    for x,child in enumerate(children):
                        policies.append(dict(root=['F',i,x],
                            leaves=[[[i,'F']]+p for p in child['leaves']]))
                    for x,match in enumerate(children):
                        for y,bad in enumerate(children):
                            policies.append(dict(root=['C',i,x,y],leaves=
                                [[[i,'M']]+p for p in match['leaves']] +
                                [[[i,'B']]+p for p in bad['leaves']]))
                signatures = [tuple(p['root']) for p in policies]
                assert len(set(signatures)) == len(signatures)
                for p in policies:
                    for trace in p['leaves']:
                        state = d
                        for i,outcome in trace:
                            assert outcome in ('F','M','B')
                            assert not state >> i & 1 and pred[i] & state == pred[i]
                            state |= 1 << i
                        assert state == (1 << n)-1
                catalog[cid] = dict(graph=gid,n=n,D=d,ready=ready,policies=policies)
    assert graph_counts == {'0':1,'1':1,'2':3,'3':25}
    dump(BASE/'catalog01.json',catalog)
    dump(BASE/'graphs01.json',graphs)
    count = policy_count = leaf_count = mode_count = 0
    by_n = {}
    with (BASE/'population01.jsonl').open('x') as out:
        for graph in graphs:
            n, gid = graph['n'], graph['id']
            for assignment in itertools.product(range(len(TYPES)), repeat=n):
                costs = [list(TYPES[x][1:]) for x in assignment]
                for d in graph['ideals']:
                    cid = f'{gid}:{d}'
                    cat = catalog[cid]
                    for k in range(d.bit_count()+1):
                        row = dict(id=count,catalog=cid,types=list(assignment),costs=costs,k=k)
                        out.write(json.dumps(row,separators=(',',':'))+'\n')
                        count += 1
                        by_n[str(n)] = by_n.get(str(n),0)+1
                        policy_count += len(cat['policies'])
                        leaf_count += sum(len(p['leaves']) for p in cat['policies'])
                        mode_count += 2*len(cat['ready'])
    expected = dict(games=count,policies=policy_count,leaves=leaf_count,modes=mode_count,
                    games_by_n=by_n,graphs_by_n=graph_counts,price_types=TYPES)
    dump(BASE/'DENOMINATOR01.json',expected)
    source_paths = {
        'source_PROOF02.md':BASE.parent/'charged_general_01/PROOF02.md',
        'source_THREE_COSTS_HYPOTHESIS03.md':BASE.parent/'charged_general_01/THREE_COSTS_HYPOTHESIS03.md',
        'source_filter01.py':BASE.parent/'charged_general_01/filter01.py',
        'source_FULLY_CHARGED_PROOF05.md':BASE.parent.parent/'RESUMED_20260910_1617/charged_comparison_01/FULLY_CHARGED_PROOF05.md'
    }
    origins = {}
    for name,path in source_paths.items():
        data = path.read_bytes()
        with (BASE/name).open('xb') as out:
            out.write(data)
        origins[name] = str(path)
    names = ['PLAN01.md','freeze01.py','actual_oracle01.py','candidate_compare01.py','run01.py',
             'catalog01.json','graphs01.json','population01.jsonl','DENOMINATOR01.json'] + list(source_paths)
    manifest = dict(phase='FROZEN_BEFORE_OUTCOME_EXECUTION',
        frozen_at_utc=datetime.now(timezone.utc).isoformat(),expected=expected,source_origins=origins,
        files={name:dict(sha256=digest(BASE/name),bytes=(BASE/name).stat().st_size) for name in names})
    dump(BASE/'FREEZE01.json',manifest)
    print(json.dumps(dict(freeze_sha256=digest(BASE/'FREEZE01.json'),**expected),sort_keys=True))

if __name__ == '__main__':
    main()
