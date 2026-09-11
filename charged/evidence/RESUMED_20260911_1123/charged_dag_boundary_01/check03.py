from pathlib import Path
from itertools import combinations, product
import datetime, gzip, hashlib, json, os, time, traceback

P=Path(__file__).resolve().parent;O=P/'run03';O.mkdir(exist_ok=False)
def stamp():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def write(name,x):(O/name).write_text(json.dumps(x,indent=2)+'\n')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def subset_top(values,k):
    return max(sum(values[i] for i in inds) for inds in combinations(range(len(values)),min(k,len(values))))
def ready(done,edges):
    return [i for i in range(4) if i not in done and all(a in done for a,b in edges if b==i)]
def all_trees(done,edges):
    if len(done)==4:return [None]
    ans=[]
    for i in ready(done,edges):
        children=all_trees(done|{i},edges)
        ans.extend((i,'F',child) for child in children)
        ans.extend((i,'C',good,bad) for good,bad in product(children,repeat=2))
    return ans
def skeleton(tree,trace=()):
    if tree is None:return [trace]
    i,mode=tree[:2]
    if mode=='F':return skeleton(tree[2],trace+((i,'F','none'),))
    return skeleton(tree[2],trace+((i,'C','match'),))+skeleton(tree[3],trace+((i,'C','bad'),))
def all_cached(done,edges):
    if len(done)==4:return None
    i=min(ready(done,edges));child=all_cached(done|{i},edges)
    return (i,'C',child,child)
def evaluate(trace,p,q):
    cost=sum(p[i] if mode=='F' else q[i] if result=='bad' else 0 for i,mode,result in trace)
    writes=sum(result=='bad' for _,_,result in trace)
    return {'cost':cost,'writes':writes}

old_inputs=json.loads((P/'run01/INPUTS.json').read_text())
inputs=[x for x in old_inputs if x['family']=='heterogeneous' and len(x['p'])==4]
assert len(inputs)==4096
graph_list=inputs[0]['graphs'];assert len(graph_list)==3
trees=[all_trees({0,1},edges) for edges in graph_list]
paths=[[skeleton(tree) for tree in group] for group in trees]
allcache_paths=[skeleton(all_cached(set(),es)) for es in graph_list]
assert sorted(map(len,trees))==[6,6,12]
assert sum(len(leaves) for group in paths for leaves in group)*len(inputs)==245760
write('INPUTS.json',inputs);write('POLICY_TREES.json',{'graphs':graph_list,'trees':trees,'leaf_skeletons':paths,'all_cached_paths':allcache_paths})
sources=[P/'PROTOCOL01.md',P/'PROTOCOL02.md',P/'HYPOTHESIS02.md',Path(__file__),O/'INPUTS.json',O/'POLICY_TREES.json']+[P/'run01'/x for x in ['INPUTS.json','STATES.jsonl.gz','COMPARISONS.json','SUMMARY.json']]
write('START.json',{'utc':stamp(),'pid':os.getpid(),'planned_graph_cost_cases':12288,'planned_complete_policies':98304,'planned_policy_leaf_paths':245760,'planned_threshold_leaf_checks':737280,'planned_initial_allcached_paths':196608,'timeout_seconds':120,'sha256':{str(x.relative_to(P)):digest(x) for x in sources}})
start=time.monotonic();end=min(start+120,start+max(0,datetime.datetime(2026,9,11,4,18,tzinfo=datetime.timezone.utc).timestamp()-time.time()))
expected={}
with gzip.open(P/'run01/STATES.jsonl.gz','rt') as f:
    for line in f:
        row=json.loads(line)
        if 576<=row['input']<4672 and row['D']==3:
            expected[row['input'],row['graph'],row['k']]=row['V']
errors=[];statuses=[];results=[]
counts={'cases':0,'policies':0,'policy_leaf_paths':0,'threshold_leaf_checks':0,'initial_allcached_paths':0,'safe_initial_fresh_policies':0,'safe_initial_fresh_paths':0,'rejected_current_fresh_cases':0,'threshold_disagreements':0,'candidate_disagreements':0,'dag_differences':0}
with gzip.open(O/'ALL_POLICY_PATHS.jsonl.gz','wt') as raw,gzip.open(O/'ALL_INITIAL_PATHS.jsonl.gz','wt') as initial:
 for inp in inputs:
    p=inp['p'];q=[a+b for a,b in zip(p,inp['h'])];g=[subset_top(q,k) for k in range(7)];per_graph=[]
    for gi,edges in enumerate(graph_list):
        if time.monotonic()>end:
            statuses.append({'input':inp['id'],'graph':gi,'status':'UNEXECUTED_AFTER_TIMEOUT'});continue
        try:
            tree_values=[];leaf_values=[]
            for ti,leaves in enumerate(paths[gi]):
                leaf_rows=[evaluate(trace,p,q) for trace in leaves]
                capacities=[[g[k+row['writes']]-row['cost'] for row in leaf_rows] for k in range(3)]
                limits=[min(vals) for vals in capacities]
                witnesses=[vals.index(min(vals)) for vals in capacities]
                record={'input':inp['id'],'graph':gi,'policy':ti,'leaves':leaf_rows,'leaf_capacities_by_k':capacities,'policy_thresholds':limits,'minimizing_leaf_by_k':witnesses,'current_fresh_safe':q[0]+p[1]<=limits[1]}
                raw.write(json.dumps(record,separators=(',',':'))+'\n')
                tree_values.append(limits);leaf_values.append(leaf_rows)
                counts['policies']+=1;counts['policy_leaf_paths']+=len(leaves);counts['threshold_leaf_checks']+=3*len(leaves)
            best=[max(v[k] for v in tree_values) for k in range(3)]
            for k in range(3):
                if best[k]!=expected[inp['id'],gi,k]:
                    errors.append({'kind':'threshold_disagreement','input':inp['id'],'graph':gi,'k':k,'independent':best[k],'DP':expected[inp['id'],gi,k]});counts['threshold_disagreements']+=1
                candidate=subset_top(q[:2]+inp['h'][2:],k)
                if candidate!=best[k]:
                    errors.append({'kind':'CANDIDATE_FALSIFIER','input':inp['id'],'graph':gi,'k':k,'independent':best[k],'candidate':candidate});counts['candidate_disagreements']+=1
            cached_rows=[evaluate(trace,p,q) for trace in allcache_paths[gi]]
            for row in cached_rows:
                if row['cost']>g[row['writes']]:errors.append({'kind':'initial_cached_violation','input':inp['id'],'graph':gi,'leaf':row})
            assert all(trace[0][0]==0 and trace[0][1]=='C' for trace in allcache_paths[gi])
            assert any(trace[0][2]=='bad' and row['writes']==1 for trace,row in zip(allcache_paths[gi],cached_rows))
            initial.write(json.dumps({'input':inp['id'],'graph':gi,'kind':'all_cached','leaves':cached_rows},separators=(',',':'))+'\n');counts['initial_allcached_paths']+=len(cached_rows)
            fresh_safe=q[0]+p[1]<=best[1]
            chosen=None
            if fresh_safe:
                chosen=next(ti for ti,vals in enumerate(tree_values) if q[0]+p[1]<=vals[1])
                root_tree=(0,'C',all_cached({0},edges),(1,'F',trees[gi][chosen]))
                full_paths=skeleton(root_tree);full_rows=[evaluate(trace,p,q) for trace in full_paths]
                for row in full_rows:
                    if row['cost']>g[row['writes']]:errors.append({'kind':'initial_fresh_violation','input':inp['id'],'graph':gi,'leaf':row})
                initial.write(json.dumps({'input':inp['id'],'graph':gi,'kind':'safe_initial_fresh','suffix_policy':chosen,'traces':full_paths,'leaves':full_rows},separators=(',',':'))+'\n')
                counts['safe_initial_fresh_policies']+=1;counts['safe_initial_fresh_paths']+=len(full_paths)
            else:
                counts['rejected_current_fresh_cases']+=1
                assert all(any(q[0]+p[1]+row['cost']>g[1+row['writes']] for row in leaves) for leaves in leaf_values)
            rec={'input':inp['id'],'graph':gi,'best_thresholds':best,'fresh_safe':fresh_safe,'chosen_suffix_policy':chosen}
            results.append(rec);per_graph.append(rec);statuses.append({'input':inp['id'],'graph':gi,'status':'SUCCESS'});counts['cases']+=1
        except Exception:
            err={'input':inp['id'],'graph':gi,'status':'EXCEPTION','traceback':traceback.format_exc()};errors.append(err);statuses.append(err)
    if len(per_graph)==3 and (len({tuple(x['best_thresholds']) for x in per_graph})>1 or len({x['fresh_safe'] for x in per_graph})>1):counts['dag_differences']+=1
write('RESULTS.json',results);write('STATUSES.json',statuses);write('ERRORS.json',errors)
summary={'status':'SUCCESS' if not errors and counts['cases']==12288 else 'FAILURE_OR_INCOMPLETE','counts':counts,'errors':len(errors),'seconds':time.monotonic()-start,'finished_utc':stamp(),'general_DAG_theorem_adopted':False,'native_measurements':0}
write('SUMMARY.json',summary);print(json.dumps(summary,indent=2))
