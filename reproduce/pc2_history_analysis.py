"""Source-fluent replay and history reachability over six saved PC2 exports.

Pure text input and JSON-compatible result. No generator, solver, compiler,
subprocess, timing run, or filesystem mutation is invoked.
"""
from collections import Counter, defaultdict, deque
import json
import re
START='startNewSpec_P_NEW_OUT_IF_FINISHED_1'
TESTER='new:P_NEW_OUT_IF_FINISHED_1:7'
def normalized(a):return re.sub(r'\[([0-9]+)\]',r'.\1',a)
def parse_graph(text):
 n=int(re.search(r'States:\s*(\d+)',text)[1]);g={}
 for s,body in re.findall(r'Q(\d+)\s*=\s*\((.*?)\)(?:,|\.|\+)',text,re.S):
  edges={}
  for expr,d in re.findall(r'([^|]+?)\s*->\s*Q(\d+)',body):
   expr=expr.strip();m=re.fullmatch(r'\{([^}]+)\}(.*)',expr)
   actions=[a.strip()+m[2] for a in m[1].split(',')] if m else [expr]
   for a in actions:
    a=normalized(a);assert a not in edges;edges[a]=int(d)
  g[int(s)]=edges
 assert len(g)==n and set(g)==set(range(n))
 return g

def parse_testers(t):
 if not t:return {}
 pairs=[x.split('=') for x in t.split(', ')];assert all(len(x)==2 for x in pairs)
 return {k:int(v) for k,v in pairs}

def parse_pre(t):
 m=re.fullmatch(r'PRE\((\d+):\[(.*)\]:\{(.*)\}\)',t);assert m,t
 physical=[]
 for mm in re.finditer(r'(\d+)(?:@\[([0-9, ]*)\])?',m[2]):
  physical.append(['OLD',int(mm[1]),[] if mm[2] is None else [int(x) for x in mm[2].split(', ') if x]])
 assert len(physical)==2 and len(physical[0][2])==24 and physical[1][2]==[],t
 return {'controller':int(m[1]),'physical':physical,'testers':parse_testers(m[3])}

def mid_description(s):
 physical=', '.join(v+'('+str(q)+('@['+', '.join(map(str,obs))+']' if obs else '')+')' for v,q,obs in s['physical'])
 return 'MID((['+physical+'], {'+', '.join(k+'='+str(v) for k,v in s['testers'].items())+'}, ['+', '.join(s['pending'])+']))'

def signature(physical,testers):return json.dumps([physical,testers],sort_keys=True)
def adjacency(edges):
 g=defaultdict(list)
 for a,e,b in edges:g[a].append((e,b))
 for a in g:g[a].sort()
 return g

def shortest(g,start,goal=None,edge_ok=lambda a,e,b:True):
 parent={start:None};todo=deque([start])
 while todo:
  a=todo.popleft()
  if goal is not None and a==goal:break
  for e,b in g.get(a,[]):
   if edge_ok(a,e,b) and b not in parent:parent[b]=(a,e);todo.append(b)
 return parent

def path_to(parent,target):
 if target not in parent:return None
 edges=[];q=target
 while parent[q] is not None:
  p,e=parent[q];edges.append([p,e,q]);q=p
 return list(reversed(edges))

def actions(edges):return [e for _,e,_ in edges]

def analyze(texts, source_files):
 data=json.loads(texts['certificate']);source=texts['input']
 nodes={s['id']:s for s in data['states']};assert len(nodes)==len(data['states'])
 entries=sorted(s['id'] for s in nodes.values() if s['initial'])
 policy=data['strategy_edges'];pg=adjacency(policy)
 start_edges=[e for e in policy if e[1]==START]
 assert data['decision']=='WIN' and len(nodes)==381 and len(policy)==522 and len(entries)==126
 assert start_edges==[[13,START,12]]
 reachable=set()
 for q in entries:reachable.update(shortest(pg,q))
 assert reachable==set(nodes)
 assert all(nodes[a]['rank']>nodes[b]['rank'] for a,e,b in policy)

 # Reconstruct the ordinary observer names from the selected new safety
 # formulas. The source declares these seven fluent families; the five event
 # propositions have a one-event truth value. Names are ordered as the stored
 # registry, then this interpretation is checked against EVERY saved edge.
 names=['Calibrating','CleanPending','Cleaned','DrillPending','Drilled','PaintPending','Painted']
 registry=[]
 for name in names:
  m=re.search(r'^fluent '+name+r'\[i:Arms\] = <([^\n]+)>\s*$',source,re.M);assert m,name
  # There is exactly one top-level separator between initiating and terminating actions.
  depth=0;parts=[];start=0
  for i,c in enumerate(m[1]):
   if c=='{':depth+=1
   elif c=='}':depth-=1
   elif c==',' and depth==0:parts.append(m[1][start:i]);start=i+1
  parts.append(m[1][start:]);assert len(parts)==2
  for arm in [1,2]:
   sets=[]
   for part in parts:sets.append([normalized(a.strip().replace('[i]',f'[{arm}]')) for a in part.strip('{}').split(',')])
   registry.append({'name':f'{name}.{arm}','kind':'declared_fluent','initial':0,'set':sets[0],'reset':sets[1]})
 for event in ['clean','drill','out','paint','stamp']:
  for arm in [1,2]:registry.append({'name':f'{event}.{arm}','kind':'event_proposition','initial':0,'set':[f'{event}.{arm}'],'reset':['other ordinary event']})
 assert len(registry)==24
 assert re.search(r'^const N = 2$',source,re.M) and re.search(r'^const K = 1$',source,re.M)
 old_process=source.split('//Old Model\n',1)[1].split('//New Model',1)[0].strip()
 new_process=source.split('//New Model\n',1)[1].split('||OLD_ENV',1)[0].strip()
 transformed=old_process.replace('PRODUCTION_CELL_OLD','PRODUCTION_CELL_NEW').replace('POLISHED','PAINTED').replace('polish','paint')
 assert re.sub(r'\s+','',transformed)==re.sub(r'\s+','',new_process),'Old/New ordinary source process correspondence'
 transfer_pairs=[('PRODUCTION_CELL_OLD','CAL_INITIAL'),('ARM','CAL_ARM'),('OUT','CAL_OUT'),('TRASHED','CAL_TRASHED'),('DRILLED[k]','CAL_DRILLED[k]'),('POLISHED[k]','CAL_ARM'),('CLEANED[k]','CAL_CLEANED[k]')]
 for arm in [1,2]:
  rel=source.split(f'relation R_PRODUCTION_CELL_{arm}_CAL = {{',1)[1].split('}',1)[0]
  assert rel.count(' -> ')==7
  for old_name,new_name in transfer_pairs:
   needle=f'{old_name}@PRODUCTION_CELL_OLD({arm}) = reconfigure_PRODUCTION_CELL_{arm} -> {new_name}@PRODUCTION_CELL_NEW_CAL({arm})'
   assert rel.count(needle)==1,needle
 assert 'assert NEW_OUT_IF_FINISHED_1 = (out[1] -> (Drilled[1] && Cleaned[1] && Painted[1]))' in source
 assert 'ltl_property P_NEW_OUT_IF_FINISHED_1 = []NEW_OUT_IF_FINISHED_1' in source
 relevant={name:next(i for i,r in enumerate(registry) if r['name']==name) for name in ['Drilled.1','Cleaned.1','Painted.1']}
 def ordinary(e):return re.fullmatch(r'\w+\.[12](?:\.\d+)?',e) is not None
 def obs_step(v,e):
  result=list(v)
  if not ordinary(e):return result
  for i,r in enumerate(registry):
   if r['kind']=='event_proposition':result[i]=int(e in r['set'])
   elif e in r['set']:result[i]=1
   elif e in r['reset']:result[i]=0
  return result
 def bad(v,e):return e=='out.1' and not all(v[i] for i in relevant.values())
 def replay(word):
  v=[0]*24;bad_events=[]
  for pos,e in enumerate(word,1):
   if bad(v,e):bad_events.append({'event_index_1based':pos,'event':e,'Drilled':v[relevant['Drilled.1']],'Cleaned':v[relevant['Cleaned.1']],'Painted':v[relevant['Painted.1']]})
   v=obs_step(v,e)
  return v,bad_events

 linked=data['linked_state_descriptions'];ledges=data['linked_edges']
 pre={i:parse_pre(t) for i,t in enumerate(linked) if t.startswith('PRE(')}
 assert len(pre)==126
 pre_edges=[e for e in ledges if e[0] in pre and e[2] in pre]
 old_graph=adjacency(pre_edges)
 old_initials=[i for i,p in pre.items() if p['controller']==0 and p['physical']==[['OLD',0,[0]*24],['OLD',0,[]]] and all(v==0 for v in p['testers'].values())]
 assert len(old_initials)==1;old_initial=old_initials[0]
 old_paths=shortest(old_graph,old_initial);assert set(old_paths)==set(pre)
 old_safe_paths=shortest(old_graph,old_initial,edge_ok=lambda a,e,b:not bad(pre[a]['physical'][0][2],e))
 controller=parse_graph(texts['old_controller']);base=parse_graph(texts['ordinary_new_plant']);cal=parse_graph(texts['calibration_new_plant'])
 old_plant={q:{e.replace('paint','polish'):t for e,t in edges.items()} for q,edges in base.items()}
 assert len(controller)==81
 # Map ordinary NEW states using graph isomorphism after erasing calibration.
 iso={0:0};todo=deque([0])
 while todo:
  q=todo.popleft();dest={e:t for e,t in cal[iso[q]].items() if not e.startswith('beginCalibration')}
  assert set(dest)==set(base[q])
  for e,t in base[q].items():
   if t in iso:assert iso[t]==dest[e]
   else:iso[t]=dest[e];todo.append(t)
 assert len(iso)==7
 def canonical_step(physical,e):
  result=json.loads(json.dumps(physical))
  if ordinary(e):
   arm=int(e.split('.')[1])-1;local=e.replace('.'+str(arm+1),'.1',1);v,q,_=physical[arm];plant=old_plant if v=='OLD' else cal
   assert local in plant[q],('ordinary physical edge',physical,e)
   result[arm][1]=plant[q][local];result[0][2]=obs_step(physical[0][2],e)
  elif e.startswith('reconfigure_PRODUCTION_CELL_'):
   arm=int(e[-1])-1;v,q,obs=physical[arm];assert v=='OLD'
   ordinary_destination=1 if q==3 else q # OLD polishing transfers to NEW ARM, as declared.
   new_operational=iso[ordinary_destination]
   result[arm]=['NEW',cal[new_operational]['beginCalibration.1'],obs]
  return result
 # Raw local state numbers differ between arms. Derive a canonical source-
 # process state along ALL saved paths and verify path-independent agreement;
 # never equate arm-2 raw numbers with arm-1 numbers.
 canonical_pre={old_initial:[['OLD',0,[0]*24],['OLD',0,[]]]};todo=deque([old_initial])
 while todo:
  a=todo.popleft()
  for e,b in old_graph.get(a,[]):
   expect=canonical_step(canonical_pre[a],e)
   assert expect[0][2]==pre[b]['physical'][0][2] and pre[b]['physical'][1][2]==[],('old observer edge',a,e,b)
   if b in canonical_pre:assert canonical_pre[b]==expect,('old source-process path inconsistency',a,e,b)
   else:canonical_pre[b]=expect;todo.append(b)
 assert set(canonical_pre)==set(pre)
 old_raw_maps=[{},{}]
 for p in pre:
  for arm in [0,1]:
   raw=pre[p]['physical'][arm][1];semantic=canonical_pre[p][arm][1]
   if raw in old_raw_maps[arm]:assert old_raw_maps[arm][raw]==semantic
   else:old_raw_maps[arm][raw]=semantic
 for arm in [0,1]:assert len(set(old_raw_maps[arm].values()))==len(old_raw_maps[arm])
 for a,e,b in pre_edges:
  assert controller[pre[a]['controller']].get(e)==pre[b]['controller'],('old controller edge',a,e,b)
  assert canonical_step(canonical_pre[a],e)==canonical_pre[b]
 canonical_policy={}
 for q in entries:
  physical=nodes[q]['physical']
  canonical_policy[q]=[[v,old_raw_maps[arm][raw],obs] for arm,(v,raw,obs) in enumerate(physical)]
 todo=deque(entries)
 while todo:
  a=todo.popleft()
  for e,b in pg.get(a,[]):
   expect=canonical_step(canonical_policy[a],e)
   assert expect[0][2]==nodes[b]['physical'][0][2] and nodes[b]['physical'][1][2]==[],('policy observer edge',a,e,b)
   assert [x[0] for x in expect]==[x[0] for x in nodes[b]['physical']],('policy version edge',a,e,b)
   if b in canonical_policy:assert canonical_policy[b]==expect,('policy source-process path inconsistency',a,e,b)
   else:canonical_policy[b]=expect;todo.append(b)
 assert set(canonical_policy)==set(nodes)
 new_raw_maps=[{},{}]
 for q in nodes:
  for arm in [0,1]:
   version,raw,obs=nodes[q]['physical'][arm];semantic=canonical_policy[q][arm][1]
   mapping=old_raw_maps[arm] if version=='OLD' else new_raw_maps[arm]
   if raw in mapping:assert mapping[raw]==semantic,('raw local state meaning changed',q,arm,raw)
   else:mapping[raw]=semantic
 for mapping in old_raw_maps+new_raw_maps:assert len(set(mapping.values()))==len(mapping)
 for a,e,b in policy:assert canonical_step(canonical_policy[a],e)==canonical_policy[b]
 # Each saved old prefix is replayed from initial false fluents, not justified
 # merely by the certificate safe flag.
 for p in pre:
  v,_=replay(actions(path_to(old_paths,p)));assert v==pre[p]['physical'][0][2]
 pre_by_sig={signature(p['physical'],p['testers']):i for i,p in pre.items()};assert len(pre_by_sig)==len(pre)
 mid_indices={t:i for i,t in enumerate(linked) if t.startswith('MID(')}
 assert len(mid_indices)==380
 cert_to_link={q:mid_indices[mid_description(s)] for q,s in nodes.items() if not s['goal']}
 link_edge_set={tuple(e) for e in ledges}
 for a,e,b in policy:
  if not nodes[b]['goal']:assert (cert_to_link[a],e,cert_to_link[b]) in link_edge_set
 entry_pre={}
 for q in entries:
  s=nodes[q];old_testers={k:v for k,v in s['testers'].items() if k.startswith('old:')}
  p=pre_by_sig[signature(s['physical'],old_testers)];assert (p,'hotSwapIn',cert_to_link[q]) in link_edge_set
  entry_pre[q]=p
 assert set(entry_pre.values())==set(pre)
 source_id,_,target_id=start_edges[0]
 assert TESTER not in nodes[source_id]['testers'] and nodes[target_id]['testers'][TESTER]==0
 assert nodes[source_id]['physical']==nodes[target_id]['physical']
 assert nodes[source_id]['physical']==[['NEW',1,[0]*24],['NEW',1,[]]]
 assert START in nodes[source_id]['pending'] and START not in nodes[target_id]['pending']
 assert len(nodes[target_id]['pending'])==len(nodes[source_id]['pending'])-1
 records=[]
 for q in entries:
  p=entry_pre[q]
  old_path=path_to(old_paths,p)
  suffix=path_to(shortest(pg,q),source_id);assert suffix is not None
  full=actions(old_path)+['hotSwapIn']+actions(suffix)+[START]
  vector,violations=replay(full);assert vector==nodes[target_id]['physical'][0][2]
  old_safe=path_to(old_safe_paths,p)
  suffix_safe=path_to(shortest(pg,q,edge_ok=lambda a,e,b:not bad(nodes[a]['physical'][0][2],e)),source_id)
  safe_exists=old_safe is not None and suffix_safe is not None
  witness=None
  if safe_exists:
   word=actions(old_safe)+['hotSwapIn']+actions(suffix_safe)+[START]
   vv,bb=replay(word);assert not bb and vv==vector and word.count(START)==1
   witness={'old_graph_edges':old_safe,'hot_swap_edge':[p,'hotSwapIn',cert_to_link[q]],'policy_edges':suffix_safe+[[source_id,START,target_id]],'events':word,'events_count':len(word),'ordinary_events_count':sum(map(ordinary,word)),'nonempty':bool(word)}
  records.append({'entry_state':q,'old_linked_state':p,'old_controller_state':pre[p]['controller'],
      'entry_physical':nodes[q]['physical'],
      'reaches_start_in_saved_policy':True,'safe_old_prefix_exists':old_safe is not None,'safe_policy_prefix_exists':suffix_safe is not None,
      'activation_safe_joined_history_exists':safe_exists,'safe_witness':witness,
      'shortest_unrestricted_witness':{'old_graph_edges':old_path,'hot_swap_edge':[p,'hotSwapIn',cert_to_link[q]],'policy_edges':suffix+[[source_id,START,target_id]],'events':full,'events_count':len(full),'ordinary_events_count':sum(map(ordinary,full)),'target_requirement_violations':violations,'safe_for_target_requirement':not violations},
      'failure_reasons':([] if old_safe is not None else ['Every saved old-endpoint path to this exact entry tuple already violates the target new requirement.'])+([] if suffix_safe is not None else ['Every saved-policy prefix from this entry to the target start violates the target new requirement.'])})

 # Product with a single violation bit checks existence of unsafe histories in
 # the already saved PRE graph, including cycles. This does not synthesize a
 # policy or evaluate a new benchmark/model.
 product=defaultdict(list)
 for a,e,b in pre_edges:
  for flag in [False,True]:product[(a,flag)].append((e,(b,flag or bad(pre[a]['physical'][0][2],e))))
 bad_old_paths=shortest(product,(old_initial,False))
 bad_old_witness=path_to(bad_old_paths,(old_initial,True))
 assert bad_old_witness is not None
 bad_old_word=actions(bad_old_witness)
 canonical_entry=next(q for q,p in entry_pre.items() if p==old_initial)
 canonical_suffix=path_to(shortest(pg,canonical_entry),source_id)
 bad_word=bad_old_word+['hotSwapIn']+actions(canonical_suffix)+[START]
 final_obs,bad_list=replay(bad_word);assert bad_list and final_obs==[0]*24
 safe_rows=[r for r in records if r['activation_safe_joined_history_exists']]
 assert safe_rows and len(start_edges)==1
 diagnostics=texts['saved_diagnostics']
 guard=int(re.search(r'Activation guard states for new:P_NEW_OUT_IF_FINISHED_1:7 \[revised_new_requirement_7_activation_guard_states\] : (\d+) states',diagnostics)[1])
 reported_reached=int(re.search(r'Reached start states for new:P_NEW_OUT_IF_FINISHED_1:7 \[revised_new_requirement_7_reached_start_states\] : (\d+) states',diagnostics)[1]);assert reported_reached==len(start_edges)
 safe_counts=Counter((r['safe_old_prefix_exists'],r['safe_policy_prefix_exists']) for r in records)
 # Independent count: set fixed points over retained edge lists, rather than
 # the per-entry BFS/path constructors used above. Keep explicit cut witnesses
 # for negative results in both the old and saved-policy portions.
 old_fixed={old_initial}
 while True:
  more=old_fixed|{b for a,e,b in pre_edges if a in old_fixed and not bad(pre[a]['physical'][0][2],e)}
  if more==old_fixed:break
  old_fixed=more
 suffix_fixed={source_id}
 while True:
  more=suffix_fixed|{a for a,e,b in policy if b in suffix_fixed and not bad(nodes[a]['physical'][0][2],e)}
  if more==suffix_fixed:break
  suffix_fixed=more
 independent_safe_entries={q for q in entries if entry_pre[q] in old_fixed and q in suffix_fixed}
 assert old_fixed==set(old_safe_paths)
 assert independent_safe_entries=={r['entry_state'] for r in safe_rows}
 assert {q for q in entries if q in suffix_fixed}=={r['entry_state'] for r in records if r['safe_policy_prefix_exists']}
 old_cut=[e for e in pre_edges if e[0] in old_fixed and e[2] not in old_fixed]
 suffix_cut=[e for e in policy if e[0] not in suffix_fixed and e[2] in suffix_fixed]
 assert all(bad(pre[a]['physical'][0][2],e) for a,e,b in old_cut)
 assert all(bad(nodes[a]['physical'][0][2],e) for a,e,b in suffix_cut)
 ancestors={source_id}
 while True:
  more=ancestors|{a for a,e,b in policy if b in ancestors}
  if more==ancestors:break
  ancestors=more
 assert set(entries)<=ancestors
 assert all(TESTER not in nodes[q]['testers'] for q in ancestors)
 assert all(TESTER not in p['testers'] for p in pre.values())
 leaves={q for q in nodes if not pg.get(q)};goals={q for q,s in nodes.items() if s['goal']}
 assert leaves==goals=={7}
 without_start=adjacency([e for e in policy if e[1]!=START])
 assert all(not (set(shortest(without_start,q))&goals) for q in entries)
 # The unsafe old cycle returns to the identical initial PRE tuple. Appending
 # it to ANY old-prefix/policy witness preserves its endpoint while retaining
 # a past target violation. Thus even a positive existential row is not an
 # all-history-safety claim.
 assert bad_old_witness[0][0]==(old_initial,False) and bad_old_witness[-1][2]==(old_initial,True)
 for r in records:
  w=bad_old_word+r['shortest_unrestricted_witness']['events'];vv,bb=replay(w)
  assert bb and vv==[0]*24
 independent={
  'method':'Independent forward fixed point for safe old prefixes and reverse fixed point for safe policy prefixes over saved edge lists; cross-checked with all per-entry BFS/path results.',
  'status':'PASS','safe_old_PRE_nodes':len(old_fixed),'safe_policy_ancestor_nodes':len(suffix_fixed),
  'safe_joined_entry_ids':sorted(independent_safe_entries),
  'no_safe_old_prefix_entry_ids':sorted(q for q in entries if entry_pre[q] not in old_fixed),
  'no_safe_policy_prefix_entry_ids':sorted(q for q in entries if q not in suffix_fixed),
  'old_safe_reachability_cut_edges':old_cut,'policy_safe_reverse_reachability_cut_edges':suffix_cut,
  'all_cut_edges_violate_target_requirement':True,
  'policy_ancestors_of_target_start':len(ancestors),
  'target_monitor_inactive_at_every_pre_start_policy_ancestor':True,
  'all_maximal_saved_policy_runs_reach_unique_goal':True,
  'no_entry_can_reach_goal_while_avoiding_target_start':True,
  'all_126_entries_can_also_reach_same_tuple_with_an_unsafe_full_history':True}
 report={
  'status':'COMPLETE_WITH_PRESERVED_UNSAFE_HISTORY_RESULTS',
  'scope':'One selected new requirement in one already saved validation policy; explicit old-start/policy-prefix history analysis, not a solver or timing experiment.',
  'requirement':{'name':'P_NEW_OUT_IF_FINISHED_1','formula':'G(out.1 -> (Drilled.1 and Cleaned.1 and Painted.1))','initial_fluents':{'Drilled.1':False,'Cleaned.1':False,'Painted.1':False}},
  'source_files':source_files,
  'available_sources':{'old_controller_states':len(controller),'old_controller_edges':sum(map(len,controller.values())),'saved_PRE_states':len(pre),'saved_PRE_edges':len(pre_edges),'saved_policy_states':len(nodes),'saved_policy_edges':len(policy),'saved_policy_entries':len(entries),'saved_linked_states':len(linked),'saved_linked_edges':len(ledges)},
  'reachability_and_source_checks':{'all_saved_PRE_nodes_reachable_from_declared_old_initial':True,'all_saved_policy_nodes_reachable_from_entries':True,'all_saved_policy_edges_strictly_decrease_rank':True,'old_controller_raw_edges_checked':len(pre_edges),'old_physical_observer_edges_checked':len(pre_edges),'policy_physical_observer_edges_checked':len(policy),'exact_entry_to_PRE_tuple_and_old_monitor_matches':len(entries),'old_hotSwap_and_non_goal_policy_edges_present_in_linked_graph':True,'all_saved_inputs_unchanged':True,'certificate_safe_flags_used_to_establish_history_safety':False},
  'raw_state_interpretation':{'old_raw_to_canonical_by_arm':old_raw_maps,'new_raw_to_canonical_by_arm':new_raw_maps,'scope':'Maps are recovered and checked along every saved PRE/policy edge; source-process state is path-independent. Unvisited local states are not claimed to be covered.'},
  'observer_interpretation':{'registry':registry,'relevant_indices':relevant,'validation':'Source-declared fluent updates and event-proposition updates replayed over every stored PRE/policy edge and from the initial tuple; equality is checked against all 24 stored observer coordinates. This is not an independent verification of the original compiler/lookup implementation.'},
  'H_domain':{'definition':'H_A(xi) is the set of histories formed by any path from the saved old initial PRE state to an exact old entry, hotSwapIn, and a prefix of the saved policy ending with exactly one target start; they must end at xi and contain no violation of the target requirement. Other update commands stutter for the three target fluents.','checked_domain':'Distinct physical source tuples of this target start in this saved policy only.','reachable_start_edges':start_edges,'distinct_reached_physical_tuples':1,'source_and_target_physical':nodes[source_id]['physical'],'installed_monitor_state':nodes[target_id]['testers'][TESTER],'reported_full_initializer_guard_states':guard,'full_initializer_domain_tuple_list_saved_here':False,'full_initializer_domain_nonemptiness_claimed':False},
  'summary':{'reached_start_sites':len(start_edges),'sites_with_nonempty_activation_safe_H':1,'sites_with_empty_activation_safe_H':0,'entries_with_unrestricted_model_history_to_start':len(records),'entries_with_activation_safe_joined_history':len(safe_rows),'entries_without_activation_safe_joined_history':len(records)-len(safe_rows),'entries_with_safe_old_prefix':sum(r['safe_old_prefix_exists'] for r in records),'entries_with_safe_policy_prefix':sum(r['safe_policy_prefix_exists'] for r in records),'entry_partition':[{'safe_old_prefix':k[0],'safe_policy_prefix':k[1],'entries':v} for k,v in sorted(safe_counts.items())],'all_entry_origins_have_activation_safe_history':all(r['activation_safe_joined_history_exists'] for r in records)},
  'independent_crosscheck':independent,
  'interpretation':{'all_entry_runs_use_same_activation_tuple_in_this_saved_policy':True,'all_entry_origins_have_some_activation_safe_full_prefix':False,'negative_rows_are_active_lifetime_safety_counterexamples':False,'reason':'The target new requirement is inactive in PRE and every saved-policy ancestor before its unique start. The 87 negative origins are failures of full-prefix activation-safe history compatibility, not violations while this new monitor is active. The 39 positive origins provide existential safe histories only; an old cycle gives unsafe full histories for every one of the 126 origins as well.'},
  'entries':records,
  'same_activation_tuple_unsafe_history':{'old_graph_product_path':bad_old_witness,'canonical_entry':canonical_entry,'policy_edges':canonical_suffix+[[source_id,START,target_id]],'events':bad_word,'target_requirement_violations':bad_list,'final_observers':final_obs,'same_physical_activation_tuple_as_safe_witness':True,'consequence':'The same reached activation tuple admits histories with past target-requirement violations. Activation-safe H deliberately excludes them; H does not cover every real-model history from old initial.'},
  'limitations':[
   'These are explicit histories in the saved compiled old-endpoint and policy graphs, with source-fluent and plant replay; they are not physical execution histories or independent frontend verification.',
   'One reached start site is not the full initializer domain: the saved diagnostics report '+str(guard)+' guard tuples, whose complete membership is not reconstructed here.',
   'Nonempty H at the one reached tuple is an existential result. Failure to give a safe joined history for an entry is retained and must not be hidden by the positive witness from another entry.',
   'Safety is checked for the selected new OUT requirement over the full old-plus-update prefix. It does not establish safe histories for all 13 PC2 new requirements, all 138 reported occurrences, or all intended application requirements.',
   'Matching final fluent values supports the residual-language argument only for activation-safe histories. It does not erase a past violation or establish adequacy of choosing activation-safe rather than history-inclusive scope.',
   'The certificate export supplies the saved policy closure. This analysis cannot prove that an omitted outcome is absent from the original frontend semantics.'
  ],
  'execution':{'new_solver_executed':False,'new_experiment_executed':False,'input_regenerated':False,'jvm_or_compiler_executed':False,'manuscript_modified':False}
 }
 return report
