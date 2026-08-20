from __future__ import annotations

import copy
import ast
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "analysis"
sys.path.insert(0, str(SCRIPTS))
import check_generated_post_frontend_win_certificate as CHECK  # noqa: E402


SEM = CHECK.SEM


class TinyProblem:
    def __init__(self, *, controllable=None):
        self.block = (0,)
        self.r = SEM.Config((SEM.Tagged("NEW", SEM.Local(0)),), (), frozenset())
        self.a = SEM.Config((SEM.Tagged("NEW", SEM.Local(1)),), (), frozenset())
        self.g = SEM.Config((SEM.Tagged("NEW", SEM.Local(2)),), (), frozenset())
        self.outside = SEM.Config(
            (SEM.Tagged("NEW", SEM.Local(3)),), (), frozenset())
        self.roots = frozenset({self.r})
        self._states = {self.r, self.a, self.g}
        self._valid_states = self._states | {self.outside}
        self._controllable = set(
            {"empty-c", "outside-c"} if controllable is None
            else controllable)
        self._table = {
            (self.r, "empty-c"): frozenset(),
            (self.r, "outside-c"): frozenset({self.outside}),
            (self.r, "u1"): frozenset({self.a, self.g}),
            (self.r, "u2"): frozenset({self.g}),
            (self.a, "u3"): frozenset({self.g}),
        }
        goal = (self.g.physical, self.g.testers)
        self.full_goals = frozenset({goal})
        self.quiet_goals = frozenset({goal})
        self.full_goal_uc = frozenset()

    def structurally_valid(self, state):
        return state in self._valid_states

    def safe(self, state):
        return state in self._states

    def goal_payload(self, state):
        payload = (state.physical, state.testers)
        return payload if payload in self.quiet_goals else None

    def candidates(self, state):
        return sorted(action for source, action in self._table if source == state)

    def post(self, state, action):
        return self._table.get((state, action), frozenset())

    def is_controllable(self, action):
        return action in self._controllable


def local_certificate(problem: TinyProblem):
    states = sorted(problem._states, key=SEM.config_key)
    identifiers = {state: f"q{offset:08d}"
                   for offset, state in enumerate(states)}
    ranks = {problem.r: 2, problem.a: 1, problem.g: 0}
    state_rows = [{
        "id": identifiers[state],
        "payload": SEM.config_payload(state),
        "rank": ranks[state],
        "safe": True,
        "goal": state == problem.g,
    } for state in states]
    candidates = []
    for state in states:
        for action in problem.candidates(state):
            candidates.append({
                "source": identifiers[state],
                "action": action,
                "controllable": problem.is_controllable(action),
                "update": False,
                "target_keys": sorted(
                    SEM.bundle_config_key(target)
                    for target in problem.post(state, action)),
            })
    selected = {
        problem.r: ["u1", "u2"],
        problem.a: ["u3"],
        problem.g: [],
    }
    strategies = []
    for state in states:
        for action in selected[state]:
            strategies.append({
                "source": identifiers[state],
                "action": action,
                "target_state_ids": sorted(
                    identifiers[target]
                    for target in problem.post(state, action)),
            })
    goal_payload = {
        "id": "goal-00000000",
        "physical": SEM.config_payload(problem.g)["physical"],
        "new_requirement_states": {},
    }
    return {
        "block_index": 0,
        "components": [0],
        "root_state_ids": [identifiers[problem.r]],
        "states": state_rows,
        "candidate_buckets": candidates,
        "strategy_buckets": strategies,
        "goal_payloads": [goal_payload],
        "quiet_goal_keys": [SEM.goal_payload_key(
            (problem.g.physical, problem.g.testers))],
    }


class GeneratedLocalCertificateTest(unittest.TestCase):
    def setUp(self):
        self.problem = TinyProblem()
        self.local = local_certificate(self.problem)

    def verify(self, value=None):
        return CHECK.verify_local(
            self.problem, self.local if value is None else value, 0)

    def test_accepts_complete_uc_all_rank_domain(self):
        checked = self.verify()
        self.assertEqual(3, checked.counts["rank_states"])
        self.assertEqual(5, checked.counts["candidate_buckets"])
        self.assertEqual(1, checked.counts["goal_payloads"])
        self.assertNotIn(self.problem.outside, checked.state_ids)

    def test_rejects_extra_key_and_bool_as_rank(self):
        mutated = copy.deepcopy(self.local)
        mutated["states"][0]["extra"] = 0
        with self.assertRaisesRegex(CHECK.CheckError, "key census"):
            self.verify(mutated)
        mutated = copy.deepcopy(self.local)
        mutated["states"][0]["rank"] = True
        with self.assertRaisesRegex(CHECK.CheckError, "exact integer"):
            self.verify(mutated)

    def test_rejects_forged_safe_goal_controllability_and_quiet_goal(self):
        mutations = []
        safe = copy.deepcopy(self.local)
        safe["states"][0]["safe"] = False
        mutations.append((safe, "Safe differs"))
        goal = copy.deepcopy(self.local)
        goal["states"][0]["goal"] = True
        mutations.append((goal, "Goal differs"))
        control = copy.deepcopy(self.local)
        next(row for row in control["candidate_buckets"]
             if row["action"] == "u1")["controllable"] = True
        mutations.append((control, "controllability differs"))
        quiet = copy.deepcopy(self.local)
        quiet["quiet_goal_keys"] = []
        mutations.append((quiet, "quiet Goal key census"))
        for value, message in mutations:
            with self.subTest(message=message), self.assertRaisesRegex(
                    CHECK.CheckError, message):
                self.verify(value)

    def test_rejects_missing_empty_candidate_bucket(self):
        mutated = copy.deepcopy(self.local)
        mutated["candidate_buckets"] = [
            row for row in mutated["candidate_buckets"]
            if row["action"] != "empty-c"
        ]
        with self.assertRaisesRegex(CHECK.CheckError, "candidate action census"):
            self.verify(mutated)

    def test_rejects_omitted_nondeterministic_successor(self):
        mutated = copy.deepcopy(self.local)
        bucket = next(row for row in mutated["candidate_buckets"]
                      if row["action"] == "u1")
        bucket["target_keys"].pop()
        with self.assertRaisesRegex(CHECK.CheckError, "candidate Post differs"):
            self.verify(mutated)

    def test_rejects_omitted_uncontrollable_bucket(self):
        mutated = copy.deepcopy(self.local)
        mutated["strategy_buckets"] = [
            row for row in mutated["strategy_buckets"]
            if not (row["source"] == "q00000000" and row["action"] == "u2")
        ]
        with self.assertRaisesRegex(CHECK.CheckError, "every enabled UC"):
            self.verify(mutated)

    def test_rejects_non_decreasing_rank(self):
        mutated = copy.deepcopy(self.local)
        state = next(row for row in mutated["states"]
                     if row["id"] == "q00000001")
        state["rank"] = 2
        with self.assertRaisesRegex(CHECK.CheckError, "strictly decrease"):
            self.verify(mutated)

    def test_rejects_root_omission_and_extra_rank_state(self):
        mutated = copy.deepcopy(self.local)
        mutated["root_state_ids"] = []
        with self.assertRaisesRegex(CHECK.CheckError, "local roots differ"):
            self.verify(mutated)
        mutated = copy.deepcopy(self.local)
        unreachable = copy.deepcopy(mutated["states"][1])
        unreachable["id"] = "q99999999"
        unreachable["payload"]["physical"][0]["raw_state"] = 99
        mutated["states"].append(unreachable)
        with self.assertRaisesRegex(CHECK.CheckError,
                                    "structurally invalid|canonically enumerate"):
            self.verify(mutated)

    def test_rejects_two_controls_when_uc_is_absent(self):
        problem = TinyProblem(controllable={
            "empty-c", "outside-c", "u1", "u2", "u3"})
        local = local_certificate(problem)
        with self.assertRaisesRegex(CHECK.CheckError, "exactly one enabled C"):
            CHECK.verify_local(problem, local, 0)


class GeneratedActivationAndJsonTest(unittest.TestCase):
    def activation_fixture(self):
        observer_machine = SEM.Machine(
            "observer", 0, (0, 1), ("tick",), {
                (0, "tick"): frozenset({1}),
                (1, "tick"): frozenset({1}),
            })
        tester_machine = SEM.Machine("tester", 0, (0, 1), (), {})
        global_observer = SEM.Observer(
            "obs", 0, "Obs", observer_machine, frozenset({"tick"}))
        local_observer = SEM.Observer(
            "obs", 0, "Obs", observer_machine, frozenset({"tick"}))
        tester = SEM.Tester(
            "new-0", "New", "new", tester_machine, frozenset(),
            "start", -1)
        source = SEM.Activation(
            "OBSERVER_MAPPING", (0,), {(0,): 0, (1,): 1})
        contract = SimpleNamespace(
            observers=[global_observer], activations={"new-0": source},
            normal=frozenset({"tick"}))
        problem = SimpleNamespace(
            observers=[local_observer], new_testers=[tester])
        endpoint = SEM.Endpoint(0, (SEM.Local(0, (0,)),), ())
        rows = [{
            "block_index": 0,
            "tester_id": "new-0",
            "global_observer_indices": [0],
            "pairs": [
                {"global": [0], "local": [0],
                 "global_residual": 0, "local_residual": 0},
                {"global": [1], "local": [1],
                 "global_residual": 1, "local_residual": 1},
            ],
        }]
        return contract, [problem], [endpoint], rows

    def test_recomputes_activation_closure_and_residual(self):
        contract, problems, endpoints, rows = self.activation_fixture()
        report = CHECK.verify_activation_relations(
            contract, problems, endpoints, rows)
        self.assertEqual(1, report["activation_testers"])
        self.assertEqual(2, report["activation_relation_pairs"])
        mutated = copy.deepcopy(rows)
        mutated[0]["pairs"][1]["local_residual"] = 0
        with self.assertRaisesRegex(CHECK.CheckError, "source iota"):
            CHECK.verify_activation_relations(
                contract, problems, endpoints, mutated)

    def test_strict_loader_rejects_duplicate_key_and_noncanonical_certificate(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "value.json"
            path.write_text('{"a":1,"a":2}\n', encoding="utf-8")
            with self.assertRaisesRegex(CHECK.CheckError, "invalid strict JSON"):
                CHECK.load_strict(path, canonical=False)
            path.write_text('{"b":1, "a":2}\n', encoding="utf-8")
            with self.assertRaisesRegex(CHECK.CheckError, "not canonical JSON"):
                CHECK.load_strict(path, canonical=True)

    def test_checker_imports_no_generator_or_rank_core(self):
        source = (SCRIPTS /
                  "check_generated_post_frontend_win_certificate.py").read_text(
                      encoding="utf-8")
        tree = ast.parse(source)
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imported.add(node.module)
        self.assertNotIn("synthesize_post_frontend_win_certificate", imported)
        self.assertNotIn("strong_rank_certificate_core", imported)


if __name__ == "__main__":
    unittest.main()
