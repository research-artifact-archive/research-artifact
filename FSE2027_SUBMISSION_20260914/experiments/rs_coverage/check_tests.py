#!/usr/bin/env python3
"""Small semantic controls for the RS classifier; no synthesis or JVM execution."""
import copy,csv,json,tempfile,unittest
from pathlib import Path
import check_coverage as c

def example(restore=False,kind='new',initial=False):
 f=dict(name='p',initial_value=initial,initiating=['restore'] if initial else ['bad'],
        terminating=['bad'] if initial else ['restore'] if restore else [])
 return dict(monitor_initial=0,monitor_nonerror_states=1,alphabet=['bad','restore'],
   transitions=[[0,'bad',-1],[0,'restore',0]],referenced_fluents=[f],kind=kind,boundary_state_after_hotSwapIn=0)

class CoverageTests(unittest.TestCase):
 def test_nonerror_single_state_is_not_sufficient_when_error_and_fluent_restore(self):
  row=example(restore=True);result=c.explore(row,['bad','restore'])
  self.assertFalse(result['fluent_determined']);self.assertFalse(result['exact_residual_certified'])
  self.assertEqual(result['conflict_witness']['histories'],[[],['bad','restore']])
  self.assertEqual(result['conflict_witness']['monitor_states'],[0,-1])
 def test_monotone_bad_fluent_passes_new_exact_sufficient_condition(self):
  result=c.explore(example(),['bad','restore'])
  self.assertTrue(result['fluent_determined']);self.assertTrue(result['initializer_matches'])
  self.assertTrue(result['exact_residual_certified']);self.assertEqual(result['reachable_error_pairs'],1)
 def test_constant_update_initializer_is_not_implied_by_fluent_determination(self):
  result=c.explore(example(kind='upd'),['bad','restore','hotSwapIn'])
  self.assertTrue(result['fluent_determined']);self.assertFalse(result['initializer_matches'])
  self.assertFalse(result['exact_residual_certified']);self.assertEqual(result['boundary_witness']['constant_initializer'],0)
 def test_universal_update_monitor_can_pass_both_checks(self):
  row=example(kind='upd');row['transitions']=[[0,'bad',0],[0,'restore',0]]
  result=c.explore(row,['bad','restore','hotSwapIn'])
  self.assertTrue(result['fluent_determined']);self.assertTrue(result['exact_residual_certified'])
 def test_initially_true_state_is_preserved_before_false_then_restoration(self):
  result=c.explore(example(initial=True),['bad','restore'])
  self.assertEqual(result['conflict_witness']['fluent_values'],[True]);self.assertFalse(result['fluent_determined'])
 def test_distinct_nonerror_states_with_same_fluent_value_are_rejected(self):
  row=example();row.update(monitor_nonerror_states=2,referenced_fluents=[],transitions=[[0,'bad',1],[1,'bad',1],[0,'restore',0],[1,'restore',0]])
  result=c.explore(row,['bad','restore']);self.assertFalse(result['fluent_determined'])
  self.assertEqual(result['conflict_witness']['monitor_states'],[0,1])
 def test_lookup_observer_disagreement_blocks_exact_even_if_reference_is_determined(self):
  row=example();row['frontend_lookup_fluents']=[]
  result=c.explore(row,['bad','restore']);self.assertTrue(result['fluent_determined'])
  self.assertFalse(result['frontend_fluent_extraction_matches_reference']);self.assertFalse(result['exact_residual_certified'])
 def test_cap_and_nondeterminism_cannot_be_reported_as_proof(self):
  with self.assertRaises(OverflowError):c.explore(example(),['bad','restore'],limit=1)
  row=example();row['transitions'].append([0,'bad',0])
  with self.assertRaises(ValueError):c.explore(row,['bad','restore'])
 def test_all_saved_counterexamples_replay_to_equal_values_and_unequal_states(self):
  count=0
  for path in sorted((c.HERE/'raw/expanded-predicates').glob('*.json')):
   data=json.loads(path.read_text());alphabet=c.alphabet_for(data['requirements'])
   for row in data['requirements']:
    result=c.explore(row,alphabet);w=result['conflict_witness'];self.assertIsNotNone(w)
    final=[];step=c.monitor_function(row)
    for history in w['histories']:
     state=row['monitor_initial'];values=tuple(f['initial_value'] for f in row['referenced_fluents'])
     for action in history:
      self.assertNotEqual(action,'__OTHER__');state=step(state,action);values=c.fluent_step(values,row['referenced_fluents'],action)
     final.append((state,values))
    self.assertEqual(final[0][1],final[1][1]);self.assertNotEqual(final[0][0],final[1][0]);self.assertIn(-1,[x[0] for x in final]);count+=1
  self.assertEqual(count,273)
 def test_saved_contract_census_parses_actual_csv_header(self):
  with tempfile.TemporaryDirectory() as temp:
   p=Path(temp)/'output.txt';p.write_text('Loadable new endpoint signatures: 7 / 9\nmode,result,solver_status,metric_key,value\na,SUCCESS,realizable,revised_component_count,3\nnon CSV text\n')
   result=c.read_metrics(p);self.assertEqual(result['revised_component_count'],'3');self.assertEqual(result['saved_z_load'],'7')

 def test_a_discards_error_suffix_but_preserves_h_counterexample(self):
  row=example(restore=True);row['frontend_lookup_fluents']=copy.deepcopy(row['referenced_fluents'])
  self.assertFalse(c.explore(row,['bad','restore'])['fluent_determined'])
  result=c.explore_activation_safe(row,['bad','restore'])
  self.assertTrue(result['a_exact_sufficient']);self.assertEqual(result['a_actual_safe_history_nonempty'],'NOT_CHECKED_WITHOUT_PLANT')
 def test_a_uses_language_equivalence_not_state_identity(self):
  row=example();row.update(monitor_nonerror_states=2,referenced_fluents=[],frontend_lookup_fluents=[],
    transitions=[[0,'bad',1],[1,'bad',1],[0,'restore',0],[1,'restore',1]])
  self.assertFalse(c.explore(row,['bad','restore'])['fluent_determined'])
  self.assertTrue(c.explore_activation_safe(row,['bad','restore'])['a_exact_sufficient'])
 def test_a_distinguishing_continuation_rejects_language_mismatch(self):
  row=example();row.update(monitor_nonerror_states=2,referenced_fluents=[],frontend_lookup_fluents=[],
    transitions=[[0,'bad',1],[1,'bad',1],[0,'restore',0],[1,'restore',-1]])
  same,suffix=c.language_equivalence(row,0,1,['bad','restore'])
  self.assertFalse(same);self.assertEqual(suffix,['restore'])
  result=c.explore_activation_safe(row,['bad','restore']);self.assertFalse(result['a_exact_sufficient'])
 def test_a_frontend_observer_mismatch_is_not_certified(self):
  row=example();row['frontend_lookup_fluents']=[]
  self.assertFalse(c.explore_activation_safe(row,['bad','restore'])['a_exact_sufficient'])
 def test_a_empty_safe_domain_and_error_priority_do_not_prove_nonemptiness(self):
  row=example();row['monitor_initial']=-1
  result=c.explore_activation_safe(row,['bad','restore']);self.assertFalse(result['a_exact_sufficient']);self.assertEqual(result['a_safe_valuations'],0)
  row=example();row.update(referenced_fluents=[],frontend_lookup_fluents=[])
  result=c.explore_activation_safe(row,['bad','restore'])
  self.assertEqual(result['a_reconstructed_nonerror_lookup_entries'],0)
  self.assertEqual(result['a_actual_safe_history_nonempty'],'NOT_CHECKED_WITHOUT_PLANT')
 def test_one_shot_groups_preserve_distinct_labels_and_do_not_repeat(self):
  row=example();row.update(referenced_fluents=[],frontend_lookup_fluents=[],monitor_nonerror_states=3,
    alphabet=['reconfigure_a','reconfigure_b'],transitions=[[0,'reconfigure_a',1],[0,'reconfigure_b',1],
    [1,'reconfigure_a',2],[1,'reconfigure_b',2],[2,'reconfigure_a',-1],[2,'reconfigure_b',-1]])
  parent,safe,errors=c.safe_product(row,row['alphabet'])
  self.assertFalse(errors);self.assertEqual(safe[()],{0,1,2})
  paths=[c.path_to(parent,s) for s in parent if s[0]==2]
  self.assertEqual(paths,[['reconfigure_a','reconfigure_b']])
  self.assertTrue(c.safe_product(row,row['alphabet'],one_shot=False)[2])
 def test_e_observer_sync_and_compiled_reset_do_not_certify_entry_language(self):
  row=example(kind='upd');row['referenced_fluents'][0]['terminating']=['hotSwapIn'];row['alphabet'].append('hotSwapIn');row['transitions'].append([0,'hotSwapIn',0])
  result=c.explore_entry_scoped(row,['bad','restore','hotSwapIn'])
  self.assertTrue(result['e_post_entry_observers_synchronize']);self.assertTrue(result['e_compiled_boundary_matches'])
  self.assertFalse(result['e_exact_sufficient']);self.assertFalse(result['e_reference_language_available'])
 def test_e_preserves_observer_difference_without_claiming_language_counterexample(self):
  row=example(kind='upd');row['referenced_fluents'][0].update(initiating=['stopOldSpec_A'],terminating=['startNewSpec_A'])
  result=c.explore_entry_scoped(row,['hotSwapIn','stopOldSpec_A','startNewSpec_A'])
  self.assertFalse(result['e_post_entry_observers_synchronize']);w=json.loads(result['e_post_entry_observer_difference'])[0]
  self.assertEqual(w['pre_entry_history'],['stopOldSpec_A']);self.assertEqual(w['kind'],'observer_difference_not_language_counterexample')
 def test_e_checks_exported_boundary_and_never_counts_preentry_begin_twice(self):
  row=example(kind='upd');row.update(boundary_state_after_hotSwapIn=-1)
  result=c.explore_entry_scoped(row,['bad','hotSwapIn'])
  self.assertFalse(result['e_compiled_boundary_matches'])
  for w in json.loads(result['e_post_entry_observer_difference']):self.assertNotIn('hotSwapIn',w['pre_entry_history'])
 def test_saved_a_e_cohort_and_one_shot_observer_witnesses(self):
  a=e=sync=reset=0
  for path in sorted((c.HERE/'raw/expanded-predicates').glob('*.json')):
   data=json.loads(path.read_text());alphabet=c.alphabet_for(data['requirements'])
   for row in data['requirements']:
    result=c.explore_scopes(row,alphabet)
    self.assertEqual(result['rs_A_exact'],result['a_exact_sufficient']);self.assertEqual(result['rs_E_exact'],result['e_exact_sufficient'])
    a+=result['a_exact_sufficient'] is True;e+=result['e_exact_sufficient'] is True
    sync+=result.get('e_post_entry_observers_synchronize') is True;reset+=result.get('e_compiled_boundary_matches') is True
    for w in json.loads(result.get('e_post_entry_observer_difference','[]')):
     updates=[x for x in w['pre_entry_history'] if c.is_update_action(x)]
     self.assertEqual(len(updates),len(set(updates)));self.assertNotIn('hotSwapIn',updates)
  self.assertEqual((a,e,sync,reset),(138,0,89,135))

if __name__=='__main__':unittest.main(verbosity=2)
