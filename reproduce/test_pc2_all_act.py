"""Adverse static-check fixtures on copied saved inputs; no synthesis or build."""
import copy
import importlib.util
import itertools
import json
from pathlib import Path
import unittest

REPOSITORY = Path(__file__).resolve().parents[1]
import check_pc2_all_act as m
CHECKER = Path(m.__file__)
ORIGINAL = json.loads((REPOSITORY / m.PUBLIC_CERTIFICATE).read_text())
SOURCE = (REPOSITORY / m.PUBLIC_SOURCE).read_text()


class SavedPC2AllAct(unittest.TestCase):
    def setUp(self):
        self.data = copy.deepcopy(ORIGINAL)
        self.source = SOURCE
        self.states = {s['id']: s for s in self.data['states']}

    def rejected(self):
        with self.assertRaises(ValueError):
            m.analyze(self.data, self.source)

    def test_saved_source_graph_and_handover(self):
        result = m.analyze(self.data, self.source)
        self.assertEqual(result['observer_interpretation']['source_observer_edges_checked'], 870)
        self.assertEqual(len(result['active_obligations']), 13)
        self.assertTrue(result['handover']['linked_endpoint_physical_observers_and_new_monitors_equal'])
        self.assertEqual(result['old_prefix_and_calibration']['old_requests'], 0)
        saved = json.loads((REPOSITORY / 'results/pc2-all-active-obligations.json').read_text())
        self.assertEqual(json.loads(json.dumps(result)), saved)

    def test_boolean_semantics_all_truth_values(self):
        for a, b, c in itertools.product((False, True), repeat=3):
            values = {'a.1': a, 'b.1': b, 'c.1': c}
            for expression, expected in [
                ('a[1] -> b[1]', (not a) or b),
                ('!a[1] || b[1] && c[1]', (not a) or (b and c)),
                ('a[1] -> b[1] -> c[1]', (not a) or (not b) or c),
                ('(a[1] -> b[1]) -> c[1]', not ((not a) or b) or c),
            ]:
                self.assertEqual(m.evaluate(m.expression_tree(expression), values), expected)

    def test_unknown_or_temporal_expression_rejected(self):
        for text in ['[]a[1]', 'a[1] &&', 'a[1])', '(a[1]', 'a[1] U b[1]', 'a[3]']:
            with self.subTest(expression=text), self.assertRaises(ValueError):
                m.expression_tree(text)

    def test_duplicate_state(self):
        self.data['states'].append(copy.deepcopy(self.data['states'][0])); self.rejected()

    def test_duplicate_edge(self):
        self.data['strategy_edges'].append(self.data['strategy_edges'][0][:]); self.rejected()

    def test_non_win(self):
        self.data['decision'] = 'LOSE'; self.rejected()

    def test_unsafe_flag(self):
        self.states[20]['safe'] = False; self.rejected()

    def test_invalid_rank(self):
        self.states[20]['rank'] = True; self.rejected()

    def test_rank_not_decreasing(self):
        self.states[20]['rank'] = 12; self.rejected()

    def test_wrong_goal(self):
        self.states[8]['goal'] = True; self.rejected()

    def test_non_goal_deadlock(self):
        edge = next(e for e in self.data['strategy_edges'] if e[0] == 20)
        edge[0] = 21; self.rejected()

    def test_domain_escape(self):
        self.data['strategy_edges'][0][2] = -1; self.rejected()

    def test_entry_on_chain(self):
        original = next(s for s in self.states.values() if s['initial'])
        original['initial'] = False; self.states[20]['initial'] = True; self.rejected()

    def test_start_order(self):
        first, second = [e for e in self.data['strategy_edges'] if e[0] in (20, 19)]
        first[1], second[1] = second[1], first[1]; self.rejected()

    def test_ordinary_edge_in_suffix(self):
        next(e for e in self.data['strategy_edges'] if e[0] == 19)[1] = 'out.1'; self.rejected()

    def test_transfer_edge_in_suffix(self):
        next(e for e in self.data['strategy_edges'] if e[0] == 19)[1] = 'reconfigure_PRODUCTION_CELL_1'; self.rejected()

    def test_start_bypass(self):
        next(e for e in self.data['strategy_edges'] if e[0] == 21 and e[2] == 20)[2] = 19; self.rejected()

    def test_wrong_chain_observer(self):
        self.states[19]['physical'][0][2][4] = 1; self.rejected()

    def test_wrong_chain_component(self):
        self.states[19]['physical'][1][1] = 0; self.rejected()

    def test_wrong_monitor_value(self):
        self.states[19]['testers']['new:P_AVOID_STAMPING_1:0'] = 1; self.rejected()

    def test_wrong_monitor_identity(self):
        self.states[19]['testers']['new:P_AVOID_STAMPING_2:0'] = self.states[19]['testers'].pop('new:P_AVOID_STAMPING_1:0'); self.rejected()

    def test_pending_command_not_removed(self):
        self.states[19]['pending'].insert(0, 'startNewSpec_P_AVOID_STAMPING_1'); self.rejected()

    def test_old_monitor_on_chain(self):
        self.states[20]['testers']['old:unexpected:0'] = 0; self.rejected()

    def test_calibration_request_policy(self):
        next(e for e in self.data['strategy_edges'] if e[1] == 'calibrated.2')[1] = 'beginCalibration.2'; self.rejected()

    def test_calibration_entry_nonzero(self):
        next(s for s in self.states.values() if s['initial'])['physical'][0][2][0] = 1; self.rejected()

    def test_old_prefix_request(self):
        pre_ids = {i for i, s in enumerate(self.data['linked_state_descriptions']) if s.startswith('PRE(')}
        next(e for e in self.data['linked_edges'] if e[0] in pre_ids and e[2] in pre_ids)[1] = 'beginCalibration.1'; self.rejected()

    def test_old_initial_observer_nonzero(self):
        self.data['linked_state_descriptions'][0] = self.data['linked_state_descriptions'][0].replace('0@[0, 0,', '0@[1, 0,', 1); self.rejected()

    def test_hot_swap_link_missing(self):
        next(e for e in self.data['linked_edges'] if e[1] == 'hotSwapIn')[1] = 'notHotSwap'; self.rejected()

    def test_old_source_request(self):
        self.source = self.source.replace('PRODUCTION_CELL_OLD(I=1) = (in[I] -> ARM)', 'PRODUCTION_CELL_OLD(I=1) = (beginCalibration[I] -> ARM)'); self.rejected()

    def test_calibration_fluent_initial_true(self):
        self.source = self.source.replace('fluent Calibrating[i:Arms] = <beginCalibration[i],calibrated[i]>', 'fluent Calibrating[i:Arms] = <beginCalibration[i],calibrated[i]> initially 1'); self.rejected()

    def test_calibration_fluent_wrong_initiator(self):
        self.source = self.source.replace('fluent Calibrating[i:Arms] = <beginCalibration[i],calibrated[i]>', 'fluent Calibrating[i:Arms] = <in[i],calibrated[i]>'); self.rejected()

    def test_new_spec_requirement_missing(self):
        self.source = self.source.replace('safety = {\nP_CAL_AVAILABILITY,', 'safety = {\n'); self.rejected()

    def test_invariant_changed_even_if_zero_still_satisfies(self):
        self.source = self.source.replace('assert CLEAN_ONCE_1 = (clean[1] -> !Cleaned[1])', 'assert CLEAN_ONCE_1 = (clean[1] -> Cleaned[1])'); self.rejected()

    def test_invariant_false_at_zero(self):
        self.source = self.source.replace('assert AVOID_STAMPING_1 = (!stamp[1])', 'assert AVOID_STAMPING_1 = (stamp[1])'); self.rejected()

    def test_duplicate_source_invariant(self):
        self.source += '\nltl_property P_CAL_AVAILABILITY = [](!Calibrating[1] || !Calibrating[2])\n'; self.rejected()

    def test_wrong_handover_id(self):
        self.data['goal_matches']['7'] = 'new-00000010'; self.rejected()

    def test_wrong_linked_endpoint_alignment(self):
        mid = self.data['linked_state_descriptions'].index(m.mid_description(self.states[8]))
        target = next(b for a, e, b in self.data['linked_edges'] if a == mid and e == m.CHAIN[-1][1])
        self.data['linked_state_descriptions'][target] = self.data['linked_state_descriptions'][target].replace('new:P_PAINT_ONCE_2:12=0', 'new:P_PAINT_ONCE_2:12=1'); self.rejected()

    def test_stored_check_failure(self):
        self.data['link_checker'] = 'FAIL'; self.rejected()


if __name__ == '__main__':
    unittest.main()
