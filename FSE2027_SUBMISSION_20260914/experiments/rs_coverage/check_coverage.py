#!/usr/bin/env python3
"""Classify saved monitor/observer exports; never synthesize a controller.

A failed sufficient condition means RS remains untested, not that a benchmark
violates RS. ERROR continues absorbing while observer values keep evolving.
"""
from __future__ import annotations
from collections import deque,defaultdict,Counter
from pathlib import Path
import argparse,csv,hashlib,json,re,subprocess,time

HERE=Path(__file__).resolve().parent
SUBMISSION=HERE.parents[1]
LABELS={'gsm':'GSM','industry':'Industry','metasocket':'MetaSocket','powerplant':'PowerPlant',
 'productioncell_arms1':'PC Arms=1','productioncell_arms2':'PC Arms=2','railcab':'Railcab','surveillance':'Surveillance','workflow':'Workflow'}
ERROR=-1

def csv_write(path,rows):
 fields=list(dict.fromkeys(k for row in rows for k in row))
 with path.open('w',newline='',encoding='utf-8') as out:
  writer=csv.DictWriter(out,fieldnames=fields);writer.writeheader();writer.writerows(rows)

def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as stream:
  for data in iter(lambda:stream.read(1024*1024),b''):h.update(data)
 return h.hexdigest()

def alphabet_for(rows):
 result={'__OTHER__'}
 for row in rows:
  result.update(row['alphabet'])
  for f in row['referenced_fluents']:result.update(f['initiating']);result.update(f['terminating'])
 return sorted((a for a in result if a not in {'tau','*'} and not a.startswith('@')),key=lambda a:(a=='__OTHER__',a))

def monitor_function(row):
 alpha=set(row['alphabet']);edges=defaultdict(set)
 for source,action,target in row['transitions']:
  if action=='tau':raise ValueError('Uneliminated tau transition')
  edges[source,action].add(target)
 if any(len(v)!=1 for v in edges.values()):raise ValueError('Nondeterministic monitor')
 def step(state,action):
  if state==ERROR:return ERROR
  if action not in alpha:return state
  return next(iter(edges[state,action]),ERROR)
 return step

def fluent_step(values,fluents,action):
 return tuple(True if action in f['initiating'] else False if action in f['terminating'] or '*' in f['terminating'] else value
              for value,f in zip(values,fluents))

def path_to(parent,state):
 labels=[]
 while parent[state] is not None:
  state,action=parent[state];labels.append(action)
 return list(reversed(labels))

def explore(row,alphabet,limit=200000):
 step=monitor_function(row);fluents=row['referenced_fluents']
 initial=(row['monitor_initial'],tuple(f['initial_value'] for f in fluents))
 parent={initial:None};queue=deque([initial]);by_value=defaultdict(dict);by_value[initial[1]][initial[0]]=initial
 conflicts=[];edges=0
 while queue:
  state=queue.popleft()
  for action in alphabet:
   successor=(step(state[0],action),fluent_step(state[1],fluents,action));edges+=1
   if successor not in parent:
    if len(parent)>=limit:raise OverflowError('Product-state cap '+str(limit))
    parent[successor]=(state,action);queue.append(successor)
    known=by_value[successor[1]]
    if known and successor[0] not in known:
     other=next(iter(known.values()))
     conflicts.append(dict(fluent_values=list(successor[1]),monitor_states=[other[0],successor[0]],
                           histories=[path_to(parent,other),path_to(parent,successor)]))
    known[successor[0]]=successor
 # Explicitly check the constant UPDATE initializer separately. All possible
 # free prehistories are followed by the declared hotSwapIn observation.
 boundary=row['boundary_state_after_hotSwapIn']
 boundary_bad=[state for state in parent if step(state[0],'hotSwapIn')!=boundary]
 boundary_witness=None
 if boundary_bad:
  state=min(boundary_bad,key=lambda x:len(path_to(parent,x)))
  boundary_witness=dict(history=path_to(parent,state)+['hotSwapIn'],
      history_monitor_state=step(state[0],'hotSwapIn'),constant_initializer=boundary)
 fd=not conflicts
 # A deterministic free product entails an unambiguous NEW lookup on each
 # non-error table entry. UPDATE uses the stronger constant-boundary check.
 def observer_signature(fs):
  return sorted((bool(f['initial_value']),tuple(sorted(f['initiating'])),tuple(sorted(f['terminating']))) for f in fs)
 observer_match=observer_signature(fluents)==observer_signature(row.get('frontend_lookup_fluents',fluents))
 initializer_matches=(fd and observer_match) if row['kind']=='new' else not boundary_bad
 exact=fd and initializer_matches
 witness=conflicts[0] if conflicts else None
 return dict(fluent_determined=fd,initializer_matches=initializer_matches,exact_residual_certified=exact,
     product_states=len(parent),product_edges=edges,reachable_error_pairs=sum(s[0]==ERROR for s in parent),
     conflicting_valuations=sum(len(states)>1 for states in by_value.values()),
     frontend_fluent_extraction_matches_reference=observer_match if row['kind']=='new' else 'NOT_USED_FOR_UPD',
     conflict_witness=witness,boundary_witness=boundary_witness,
     status='EXACT_SUFFICIENT_CONDITION' if exact else 'RS_UNTESTED',
     note=('Free product and actual initializer sufficient check passed.' if exact else
           'Free-product sufficient condition failed; this is not a plant-reachable RS counterexample.'))


def is_update_action(action):
 return action in {'hotSwapIn','hotSwapOut','stopOldSpec','startNewSpec','reconfigure'} or action.startswith(
     ('stopOldSpec_','startNewSpec_','reconfigure_'))

def observer_signature(fluents):
 return sorted((bool(f['initial_value']),tuple(sorted(f['initiating'])),tuple(sorted(f['terminating']))) for f in fluents)

def language_equivalence(row,left,right,alphabet):
 """Compare all finite safety continuations, stronger than one-shot continuations."""
 step=monitor_function(row);initial=(left,right);parent={initial:None};queue=deque([initial])
 while queue:
  pair=queue.popleft()
  if (pair[0]==ERROR)!=(pair[1]==ERROR):return False,path_to(parent,pair)
  if pair[0]==ERROR:continue
  for action in alphabet:
   successor=(step(pair[0],action),step(pair[1],action))
   if successor not in parent:parent[successor]=(pair,action);queue.append(successor)
 return True,None

def one_shot_actions(row,alphabet,observer_only=False):
 """Quotient interchangeable update labels by their complete transition effect.

 Each original label can occur once. A group of k labels therefore has a
 counter 0..k, not an unbounded loop; its canonical witness uses distinct labels.
 Updates stuttering on every monitor state and every valuation can be projected
 away without changing reachable monitor/valuation pairs.
 """
 step=monitor_function(row);fluents=row['referenced_fluents'];groups=defaultdict(list);ordinary=[]
 for action in alphabet:
  if not is_update_action(action):ordinary.append(action);continue
  effect=tuple('T' if action in f['initiating'] else 'F' if action in f['terminating'] or '*' in f['terminating'] else 'I' for f in fluents)
  states=tuple(range(row['monitor_nonerror_states']))
  targets=() if observer_only else tuple(step(state,action) for state in states)
  if all(value=='I' for value in effect) and (observer_only or targets==states):continue
  groups[effect,targets].append(action)
 return ordinary,[sorted(actions) for actions in groups.values()]

def one_shot_successors(ordinary,groups,counts):
 for action in ordinary:yield action,counts
 for i,actions in enumerate(groups):
  if counts[i]<len(actions):
   updated=list(counts);updated[i]+=1
   yield actions[counts[i]],tuple(updated)

def safe_product(row,alphabet,limit=200000,one_shot=True):
 """Keep error frontier entries but never extend an unsafe prefix."""
 step=monitor_function(row);fluents=row['referenced_fluents']
 ordinary,groups=one_shot_actions(row,alphabet) if one_shot else (alphabet,[])
 initial=(row['monitor_initial'],tuple(f['initial_value'] for f in fluents),(0,)*len(groups))
 parent={initial:None};queue=deque([] if initial[0]==ERROR else [initial]);safe=defaultdict(set);errors=set()
 if initial[0]!=ERROR:safe[initial[1]].add(initial[0])
 else:errors.add(initial[1])
 while queue:
  state=queue.popleft()
  for action,counts in one_shot_successors(ordinary,groups,state[2]):
   successor=(step(state[0],action),fluent_step(state[1],fluents,action),counts)
   if successor in parent:continue
   if len(parent)>=limit:raise OverflowError('A product-state cap '+str(limit))
   parent[successor]=(state,action)
   if successor[0]==ERROR:errors.add(successor[1])
   else:safe[successor[1]].add(successor[0]);queue.append(successor)
 return parent,safe,errors

def explore_activation_safe(row,alphabet,limit=200000):
 if row['kind']!='new':return dict(a_status='NOT_APPLICABLE',a_exact_sufficient='NOT_APPLICABLE')
 parent,safe,errors=safe_product(row,alphabet,limit)
 # The actual frontend permits repeated update labels while constructing its
 # table. Reconstruct that stronger domain independently of the one-shot test.
 _,frontend_safe,frontend_errors=safe_product(row,alphabet,limit,one_shot=False)
 observer_match=observer_signature(row['referenced_fluents'])==observer_signature(row.get('frontend_lookup_fluents',[]))
 cache={}
 def equivalent(left,right):
  pair=tuple(sorted((left,right)))
  if pair not in cache:cache[pair]=language_equivalence(row,left,right,alphabet)
  return cache[pair]
 conflicts=[]
 for values,states in safe.items():
  first=min(states)
  for other in sorted(states):
   same,suffix=equivalent(first,other)
   if not same:conflicts.append(dict(values=list(values),states=[first,other],distinguishing_suffix=suffix))
 # A non-error frontend entry is selected from a safe prefix in this universal
 # product. Check every such possible choice, not only the minimum-ID choice.
 # ERROR-priority entries disable activation and are counted separately.
 mismatches=[];lookup={}
 for values,states in frontend_safe.items():
  if values not in frontend_errors:lookup[values]=min(states)
  for state in states:
   for safe_state in safe.get(values,set()):
    same,suffix=equivalent(state,safe_state)
    if not same:mismatches.append(dict(values=list(values),lookup_state=state,safe_state=safe_state,distinguishing_suffix=suffix))
 exact=bool(safe) and observer_match and not conflicts and not mismatches
 return dict(a_status='EXACT_ON_NONEMPTY_SAFE_ACTIVATION_DOMAIN' if exact else 'UNVERIFIED',
   a_exact_sufficient=exact,a_safe_language_determined=not conflicts,a_frontend_observers_match=observer_match,
   a_frontend_rule_matches=observer_match and not mismatches,a_safe_product_states=sum(s[0]!=ERROR for s in parent),
   a_safe_valuations=len(safe),a_error_frontier_valuations=len(errors),
   a_reconstructed_nonerror_lookup_entries=len(lookup),a_reconstructed_error_lookup_entries=len(frontend_errors),
   a_reconstructed_lookup=json.dumps([dict(values=list(v),state=s) for v,s in sorted(lookup.items())],separators=(',',':')),
   a_language_conflict=json.dumps((conflicts+mismatches)[:1],separators=(',',':')),
   a_actual_safe_history_nonempty='NOT_CHECKED_WITHOUT_PLANT',
   a_lookup_evidence='source-rule reconstruction; runtime lookup table not exported',
   a_note='Sufficient only on actual non-error activation entries with nonempty safe-history set; empty safe-history intersections are universal, so inclusion alone is automatic. Full continuation-language equivalence is stronger than one-shot equivalence.')

def explore_entry_scoped(row,alphabet,limit=200000):
 if row['kind']!='upd':return dict(e_status='NOT_APPLICABLE',e_exact_sufficient='NOT_APPLICABLE')
 fluents=row['referenced_fluents'];step=monitor_function(row)
 # Free pre-entry observer histories exclude hotSwapIn; other update labels
 # may each occur once. This intentionally overapproximates actual pre-entry.
 prealphabet=[a for a in alphabet if a!='hotSwapIn']
 ordinary,groups=one_shot_actions(row,prealphabet,observer_only=True)
 initial_values=tuple(f['initial_value'] for f in fluents)
 initial=(initial_values,(0,)*len(groups));parent={initial:None};queue=deque([initial]);representatives={initial_values:initial}
 while queue:
  state=queue.popleft()
  for action,counts in one_shot_successors(ordinary,groups,state[1]):
   successor=(fluent_step(state[0],fluents,action),counts)
   if successor in parent:continue
   if len(parent)>=limit:raise OverflowError('E observer-state cap '+str(limit))
   parent[successor]=(state,action);queue.append(successor);representatives.setdefault(successor[0],successor)
 canonical=fluent_step(initial_values,fluents,'hotSwapIn');different=[]
 for values,state in representatives.items():
  post=fluent_step(values,fluents,'hotSwapIn')
  if post!=canonical:different.append(dict(pre_entry_history=path_to(parent,state),entry_values=list(values),
     post_entry_values=list(post),canonical_post_entry_values=list(canonical),kind='observer_difference_not_language_counterexample'))
 boundary=row['boundary_state_after_hotSwapIn'];actual=step(row['monitor_initial'],'hotSwapIn')
 same,suffix=language_equivalence(row,actual,boundary,alphabet)
 # This equality is a compiled-reset consistency check. The exported DFA has
 # no v-parameter and cannot supply the semantic reference language J(v).
 return dict(e_status='UNVERIFIED_ENTRY_VALUATION_LANGUAGE',e_exact_sufficient=False,
   e_entry_valuations=len(representatives),e_observer_product_states=len(parent),
   e_post_entry_observers_synchronize=not different,e_compiled_boundary_matches=actual==boundary and actual!=ERROR and same,
   e_compiled_boundary_language_matches=same,e_post_entry_observer_difference=json.dumps(different[:1],separators=(',',':')),
   e_reference_language_available=False,e_boundary_distinguishing_suffix=json.dumps(suffix),
   e_note='All one-shot free pre-entry observer valuations enumerated. Observer synchronization and compiled-reset consistency are diagnostics; saved DFA does not expose a valuation-parameterized semantic initializer, so E exactness is unverified.')

def explore_scopes(row,alphabet,limit=200000):
 # Keep the historical H result and columns unchanged; A/E are added columns.
 alphabet=sorted(set(alphabet)|{'hotSwapIn','hotSwapOut'})
 result={}
 for prefix,function in [('a',explore_activation_safe),('e',explore_entry_scoped)]:
  try:result.update(function(row,alphabet,limit))
  except (ValueError,OverflowError) as error:result.update({prefix+'_status':'UNCLASSIFIED',prefix+'_exact_sufficient':False,prefix+'_note':str(error)})
 result.update(rs_A_exact=result['a_exact_sufficient'],rs_E_exact=result['e_exact_sufficient'],
   rs_A_witness=result.get('a_language_conflict','NOT_APPLICABLE'),
   rs_A_note=result.get('a_note','NOT_APPLICABLE'),rs_E_note=result.get('e_note','NOT_APPLICABLE'))
 result['rs_E_witness']=result.get('e_post_entry_observer_difference','NOT_APPLICABLE')
 if result['rs_E_witness']=='[]':result['rs_E_witness']=json.dumps([dict(kind='missing_reference_language',
   reason='Compiled-reset and observer synchronization do not provide a valuation-parameterized semantic initializer.')],separators=(',',':'))
 return result

def read_metrics(path):
 text=path.read_text(errors='replace');lines=text.splitlines()
 header=next((i for i,line in enumerate(lines) if line.startswith('mode,result,solver_status,') and 'metric_key' in line),None)
 metrics={}
 if header is not None:
  for row in csv.DictReader(lines[header:]):
   if (row.get('metric_key') or '').startswith('revised_') and row.get('value') not in (None,''):metrics[row['metric_key']]=row['value']
 match=re.search(r'Loadable new endpoint signatures:\s*(\d+)\s*/\s*(\d+)',text)
 if match:metrics['saved_z_load']=match[1]
 return metrics

def contract_rows(exports,raw_root):
 rows=[]
 for model,data in exports.items():
  for contract in data['contracts']:
   target=contract['target'];found={};sources=[]
   # Saved first-trial outputs from every same-game method: require agreement.
   for method in ('fg_ducs_otf','fg_ducs_otf_eager_controllable','fg_ducs_otf_update_first','direct_full'):
    path=raw_root/'rq3/runs'/f'{model}__{target}__rep01__{method}'/'output.txt'
    if not path.is_file():continue
    metrics=read_metrics(path)
    for k in ('revised_component_count','revised_new_requirement_count','revised_update_requirement_count',
              'revised_transfer_relation_max_fan_out','revised_transfer_relation_nondeterministic_sources',
              'revised_precedence_transitive_edges','saved_z_load'):
     if k in metrics:
      if k in found and found[k]!=metrics[k]:raise ValueError('Saved contract census disagreement '+model+'/'+target+'/'+k)
      found[k]=metrics[k]
    sources.append(str(path.relative_to(raw_root)))
   for key,export_key in [('revised_component_count','components'),('revised_new_requirement_count','new_monitors'),
                          ('revised_update_requirement_count','upd_monitors')]:
    if key in found and int(found[key])!=contract[export_key]:raise ValueError('Parsed/raw census disagreement '+model+'/'+target)
   multi=found.get('revised_transfer_relation_nondeterministic_sources','')
   rows.append(dict(model=model,target=target,components=contract['components'],
     set_valued_transfer=(int(multi)>0) if multi!='' else 'UNMEASURED',nondeterministic_transfer_sources=multi,
     transfer_max_fan_out=found.get('revised_transfer_relation_max_fan_out',''),
     new_monitors=contract['new_monitors'],upd_monitors=contract['upd_monitors'],
     residual_initializers=contract['new_monitors']+contract['upd_monitors'],
     explicit_precedence_edges=contract['explicit_precedence_edges'],
     transitive_precedence_edges=found.get('revised_precedence_transitive_edges',''),
     z_load=found.get('saved_z_load','UNMEASURED'),load_selector=contract['load_selector'],
     census_sources=';'.join(sources),source='read-only AST plus unchanged saved first-trial output'))
 return rows

def tex(s):
 return str(s).replace('_',r'\_').replace('%',r'\%').replace('&',r'\&')

def render(rows,contracts,output):
 output.mkdir(parents=True,exist_ok=True)
 csv_write(output/'rs-requirements.csv',rows);csv_write(output/'contract-coverage.csv',contracts)
 per_model=[]
 for model in LABELS:
  group=[r for r in rows if r['model']==model]
  per_model.append(dict(model=model,requirements=len(group),classified=sum(r['fluent_determined']!='UNCLASSIFIED' for r in group),
   fluent_determined=sum(r['fluent_determined'] is True for r in group),
   initializer_matches=sum(r['initializer_matches'] is True for r in group),
   exact_residual_certified=sum(r['exact_residual_certified'] is True for r in group),
   rs_untested=sum(r['exact_residual_certified'] is not True for r in group),
   new=sum(r['kind']=='new' for r in group),upd=sum(r['kind']=='upd' for r in group),
   a_exact_sufficient=sum(r['a_exact_sufficient'] is True for r in group),
   e_exact_sufficient=sum(r['e_exact_sufficient'] is True for r in group),
   ae_unverified=sum((r['a_exact_sufficient'] if r['kind']=='new' else r['e_exact_sufficient']) is not True for r in group),
   e_observer_sync=sum(r.get('e_post_entry_observers_synchronize') is True for r in group),
   e_reset_consistent=sum(r.get('e_compiled_boundary_matches') is True for r in group)))
 csv_write(output/'rs-model-summary.csv',per_model)
 lines=[r'\noindent\textbf{RS sufficient-condition coverage}\par',
  r'Counts are requirement occurrences over base/R1/R2; repeated new requirements remain in the denominator. '
  r'The independent free product includes absorbing ERROR and evolving fluent values after error. '
  r'A failed sufficient check leaves RS untested and does not establish a reachable contract violation.',
  r'\begin{center}\scriptsize\begin{tabular}{@{}lrrrrrrrr@{}}\toprule',
  r'Model & New / upd & H checked & H FD & H exact & H untested & A exact$^a$ & E exact & A/E unverified\\\midrule']
 for g in per_model:lines.append(f"{LABELS[g['model']]} & {g['new']} / {g['upd']} & {g['classified']} & {g['fluent_determined']} & {g['exact_residual_certified']} & {g['rs_untested']} & {g['a_exact_sufficient']} & {g['e_exact_sufficient']} & {g['ae_unverified']}"+r'\\')
 lines.extend([r'\bottomrule\end{tabular}\end{center}',
  r'FD means that equal reachable fluent valuations determine the same monitor state, including ERROR. '
  r'Exact additionally requires compatibility with the actual initializer: NEW uses its non-error lookup; '
  r'UPD uses a constant monitor state after \texttt{hotSwapIn}. '
  r'Per-requirement state counts, two conflicting histories, and update-boundary checks are in \path{rs-requirements.csv}.',
  r'$^a$A certifies the safe-prefix language condition and the frontend selection rule, conditional on a non-error activation entry and a nonempty actual safe-history set; the latter is not checked without the plant. '
  r'With an empty safe-history set, inclusion is automatic but equality is unproved. '
  r'E enumerates entry-observer valuations and checks reset consistency; the saved DFA has no valuation-parameterized semantic initializer, so these diagnostics do not certify E exactness. '
  r'Update labels occur at most once in the new prefix explorations; continuation-language equivalence is checked over all words, a stronger condition.'])
 (output/'rs-model-table.tex').write_text('\n'.join(lines)+'\n')
 total=len(rows);checked=sum(r['fluent_determined']!='UNCLASSIFIED' for r in rows);fd=sum(r['fluent_determined'] is True for r in rows);exact=sum(r['exact_residual_certified'] is True for r in rows)
 macros={'RSMonitorOccurrences':total,'RSClassifiedOccurrences':checked,'RSFluentDeterminedOccurrences':fd,
         'RSExactOccurrences':exact,'RSUntestedOccurrences':total-exact,'RSUnclassifiedOccurrences':total-checked,
         'RSNewOccurrences':sum(r['kind']=='new' for r in rows),'RSUpdateOccurrences':sum(r['kind']=='upd' for r in rows),
         'RSAExactOccurrences':sum(r['a_exact_sufficient'] is True for r in rows),
         'RSEExactOccurrences':sum(r['e_exact_sufficient'] is True for r in rows),
         'RSAEUnverifiedOccurrences':sum((r['a_exact_sufficient'] if r['kind']=='new' else r['e_exact_sufficient']) is not True for r in rows),
         'RSEObserverSyncOccurrences':sum(r.get('e_post_entry_observers_synchronize') is True for r in rows),
         'RSEResetConsistentOccurrences':sum(r.get('e_compiled_boundary_matches') is True for r in rows)}
 macros.update(RSAExactNew=macros['RSAExactOccurrences'],RSEExactUpd=macros['RSEExactOccurrences'],
   RSUpdOccurrences=macros['RSUpdateOccurrences'],
   RSAUnverifiedNew=macros['RSNewOccurrences']-macros['RSAExactOccurrences'],
   RSEUnverifiedUpd=macros['RSUpdateOccurrences']-macros['RSEExactOccurrences'])
 (output/'rs-counts.tex').write_text('\n'.join('\\providecommand{\\'+k+'}{'+str(v)+'}' for k,v in macros.items())+'\n')
 cl=[r'\noindent\textbf{Benchmark contract coverage}\par',
  r'Each triple is base/R1/R2. Transfer fan-out and loadable endpoint counts come from preserved first-trial outputs; '
  r'component/requirement counts and explicit precedence are cross-checked against the parsed definitions.',
  r'\begin{center}\scriptsize\begin{tabular}{@{}lrrrrl@{}}\toprule',
  r'Model & Components & Multi-target & Initializers & Prec. & $|Z_{\rm load}|$\\\midrule']
 for model in LABELS:
  group=sorted([r for r in contracts if r['model']==model],key=lambda r:('base','r1','r2').index(r['target']))
  def values(k):
   seq=[('Yes' if r[k] is True else 'No' if r[k] is False else '--' if r[k]=='UNMEASURED' else str(r[k])) for r in group]
   return seq[0] if len(set(seq))==1 else '/'.join(seq)
  cl.append(' & '.join([LABELS[model],values('components'),values('set_valued_transfer'),values('residual_initializers'),values('explicit_precedence_edges'),values('z_load')])+r'\\')
 cl.extend([r'\bottomrule\end{tabular}\end{center}',
  r'Multi-target reports whether a transfer source has more than one outcome. Initializers count NEW plus UPD requirements; '
  r'NEW table lookup and UPD constant boundary initialization are distinguished in the RS table. '
  r'PC Arms=2/R2 multi-target status is unmeasured (--): preserved runs do not contain the final transfer census. '
  r'Zero explicit precedence does not mean transition monitors impose no ordering constraints.'])
 (output/'contract-model-table.tex').write_text('\n'.join(cl)+'\n')
 print(json.dumps(macros,sort_keys=True))


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--exports',type=Path,default=HERE/'raw/expanded-predicates')
 p.add_argument('--raw-root',type=Path,default=HERE.parent/'rq3_xeon/raw');p.add_argument('--output',type=Path,default=SUBMISSION/'paper/build/generated')
 p.add_argument('--state-cap',type=int,default=200000);a=p.parse_args()
 exports={};rows=[]
 for model in LABELS:
  path=a.exports/(model+'.json')
  if not path.is_file():raise ValueError('Missing export; enumerate occurrences before marking unclassified: '+model)
  data=json.loads(path.read_text());exports[model]=data;alphabet=alphabet_for(data['requirements'])
  if data['controller_synthesis_performed'] or data['endpoint_products_materialized']:raise ValueError('Wrong export scope')
  for requirement in data['requirements']:
   base=dict(model=model,target=requirement['target'],requirement=requirement['requirement'],kind=requirement['kind'],
    monitor_states=requirement['monitor_nonerror_states']+1,monitor_nonerror_states=requirement['monitor_nonerror_states'],
    fluent_count=len(requirement['referenced_fluents']),fluent_names=';'.join(f['name'] for f in requirement['referenced_fluents']),
    initializer_mode=requirement['initializer_mode'],boundary_state_after_hotSwapIn=requirement['boundary_state_after_hotSwapIn'],
    method='compiled actual monitor plus independent free-product BFS including absorbing ERROR',export_source=path.name)
   try:result=explore(requirement,alphabet,a.state_cap)
   except (ValueError,OverflowError) as error:result=dict(fluent_determined='UNCLASSIFIED',initializer_matches='UNCLASSIFIED',
      exact_residual_certified=False,status='RS_UNTESTED',note=str(error))
   for key in ('conflict_witness','boundary_witness'):
    if key in result:result[key]=json.dumps(result[key],sort_keys=True,separators=(',',':'))
   scopes=explore_scopes(requirement,alphabet,a.state_cap)
   rows.append(dict(base,**result,**scopes))
   print(model,requirement['target'],requirement['kind'],requirement['requirement'],result['status'],result.get('conflict_witness',''),
         scopes.get('a_status'),scopes.get('e_status'))
 contracts=contract_rows(exports,a.raw_root)
 previous=HERE/'summary.csv'
 if previous.exists():
  old=list(csv.DictReader(previous.open()))
  old_h=[{k:v for k,v in r.items() if not k.startswith(('a_','e_','rs_A_','rs_E_'))} for r in old]
  new_h=[{k:'' if r.get(k) is None else str(r[k]) for k in before} for r,before in zip(rows,old_h)]
  if len(old_h)!=len(rows) or old_h!=new_h:raise ValueError('Existing H columns changed; refusing to overwrite summary')
  print('H_COLUMNS_UNCHANGED',len(rows))
 csv_write(HERE/'summary.csv',rows);csv_write(HERE/'contract-coverage.csv',contracts)
 render(rows,contracts,a.output)

if __name__=='__main__':main()
