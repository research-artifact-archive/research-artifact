from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "analysis"
if str(ANALYSIS) not in sys.path:
    sys.path.insert(0, str(ANALYSIS))

import audit_typed_partition_discovery as audit
import check_discovered_witness as witness_consumer
import check_typed_partition_certificate as consumer
import discover_typed_partition as producer
import screen_complete_game_factorability as screen
import synthesize_discovered_witness as witness_producer


class TypedPartitionDiscoveryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture_path = ROOT / "inputs/c2/typed-partition-fixtures.json"
        cls.fixtures = json.loads(cls.fixture_path.read_text(encoding="utf-8"))
        cls.positives = {case["id"]: case for case in cls.fixtures["positive_cases"]}
        cls.obstructions = {case["id"]: case for case in cls.fixtures["obstruction_cases"]}
        cls.base = cls.positives["multistate-winning-nondeterministic-handover"]
        cls.base_certificate = producer.discover(cls.base)

    def test_all_registered_cases_pass_independent_audit(self) -> None:
        summary, bundle, coordinate_screen = audit.run(ROOT, self.fixture_path)
        self.assertEqual(summary["status"], "PASS")
        self.assertEqual(summary["positive_factored_count"], 3)
        self.assertEqual(summary["obstruction_case_count"], 10)
        self.assertEqual(summary["independent_certificate_pass_count"], 13)
        self.assertEqual(summary["independent_transport_pass_count"], 3)
        self.assertEqual(summary["transport_direct_flat_agreement_count"], 3)
        self.assertEqual(
            summary["positive_maximum_partition_counts"],
            {identifier: 1 for identifier in sorted(self.positives)},
        )
        self.assertEqual(bundle["case_count"], 13)
        self.assertEqual(coordinate_screen["case_count"], 43)

    def test_discovers_maximum_two_block_partition_without_block_field(self) -> None:
        self.assertNotIn("blocks", self.base)
        certificate = self.base_certificate
        self.assertEqual(certificate["result"], "FACTORED")
        self.assertEqual(certificate["maximum_block_count"], 2)
        self.assertEqual(certificate["maximum_partition_count"], 1)
        self.assertGreater(len(certificate["mandatory_units"]), certificate["maximum_block_count"])
        self.assertGreater(audit.declared_support_unit_count(self.base), certificate["maximum_block_count"])
        self.assertGreater(certificate["evaluated_partition_count"], 1)
        report = consumer.check(self.base, certificate, max_atoms=12)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["maximum_block_count"], 2)

    def test_three_nonisomorphic_positives_include_winning_losing_and_multiroot(self) -> None:
        decisions = {case["provenance"]["expected_decision"] for case in self.positives.values()}
        self.assertEqual(decisions, {"realizable", "unrealizable"})
        multiroot = self.positives["multiroot-uncontrollable-progress"]
        self.assertEqual(sum(state["initial"] for state in multiroot["states"]), 4)
        for case in self.positives.values():
            self.assertEqual(producer.discover(case)["maximum_block_count"], 2)

    def test_ten_controlled_obstructions_are_not_misclassified_as_factored(self) -> None:
        results = {identifier: producer.discover(case)["result"] for identifier, case in self.obstructions.items()}
        self.assertEqual(sum(value == "NON_FACTORABLE" for value in results.values()), 9)
        self.assertEqual(sum(value == "INELIGIBLE" for value in results.values()), 1)
        self.assertNotIn("FACTORED", results.values())

    def test_consumer_rejects_maximum_count_and_selected_partition_tampering(self) -> None:
        mutations = []
        first = copy.deepcopy(self.base_certificate)
        first["maximum_block_count"] = 1
        mutations.append(first)
        second = copy.deepcopy(self.base_certificate)
        second["maximum_partition_count"] = 2
        mutations.append(second)
        boolean = copy.deepcopy(self.base_certificate)
        boolean["maximum_partition_count"] = True
        mutations.append(boolean)
        third = copy.deepcopy(self.base_certificate)
        third["selected_partition"] = [list(producer.TypedFlatGame(self.base).atoms)]
        mutations.append(third)
        for index, mutation in enumerate(mutations):
            with self.subTest(index=index), self.assertRaises(consumer.CertificateError):
                consumer.check(self.base, mutation, max_atoms=12)

    def test_consumer_rejects_cut_ledger_and_action_assignment_tampering(self) -> None:
        ledger = copy.deepcopy(self.base_certificate)
        ledger["root_cut_ledger"][0]["status"] = (
            "PASS" if ledger["root_cut_ledger"][0]["status"] == "FAIL" else "FAIL"
        )
        ledger_boolean = copy.deepcopy(self.base_certificate)
        ledger_boolean["root_cut_ledger"][0]["obstruction"]["expected_count"] = True
        assignment = copy.deepcopy(self.base_certificate)
        assignment["action_assignment"]["prepare"] = "<shared-stutter>"
        for mutation in (ledger, ledger_boolean, assignment):
            with self.assertRaises(consumer.CertificateError):
                consumer.check(self.base, mutation, max_atoms=12)

    def test_consumer_rejects_input_hash_and_mandatory_unit_tampering(self) -> None:
        digest = copy.deepcopy(self.base_certificate)
        digest["input_game_sha256"] = "0" * 64
        units = copy.deepcopy(self.base_certificate)
        units["mandatory_units"] = [list(producer.TypedFlatGame(self.base).atoms)]
        evaluated = copy.deepcopy(self.base_certificate)
        evaluated["evaluated_partition_count"] += 1
        ineligible_game = self.obstructions["obstruction-goal-uc-activity"]
        ineligible = producer.discover(ineligible_game)
        ineligible_scope = copy.deepcopy(ineligible)
        ineligible_scope["scope"] = "unchecked"
        for game, mutation in (
            (self.base, digest),
            (self.base, units),
            (self.base, evaluated),
            (ineligible_game, ineligible_scope),
        ):
            with self.assertRaises(consumer.CertificateError):
                consumer.check(game, mutation, max_atoms=12)

    def test_schema_rejects_partial_valuation_and_terminalized_semantics(self) -> None:
        partial = copy.deepcopy(self.base)
        partial["states"][0]["valuation"].pop(next(iter(partial["states"][0]["valuation"])))
        terminalized = copy.deepcopy(self.base)
        terminalized["semantics"] = "terminalized-goal-post"
        delimiter = copy.deepcopy(self.base)
        old = delimiter["atoms"][0]["id"]
        delimiter["atoms"][0]["id"] = old + ",reserved"
        for record in delimiter["states"] + delimiter["load_states"]:
            record["valuation"][old + ",reserved"] = record["valuation"].pop(old)
        for action in delimiter["actions"]:
            action["subjects"] = [old + ",reserved" if atom == old else atom for atom in action["subjects"]]
        for dependency in delimiter["dependencies"]:
            dependency["atoms"] = [old + ",reserved" if atom == old else atom for atom in dependency["atoms"]]
        for mutation in (partial, terminalized, delimiter):
            with self.assertRaises(producer.DiscoveryError):
                producer.discover(mutation)

    def test_json_scalar_sorts_do_not_collapse_and_nonfinite_numbers_are_rejected(self) -> None:
        collision = {
            "schema_version": producer.GAME_SCHEMA,
            "id": "bool-number-collision",
            "semantics": producer.SEMANTICS,
            "atoms": [
                {"id": "component:a", "kind": "component"},
                {"id": "component:b", "kind": "component"},
            ],
            "actions": [{
                "id": "idle", "controllability": "controllable",
                "kind": "shared_stutter", "subjects": [], "pending_atom": None,
            }],
            "states": [
                {"id": "q0", "valuation": {"component:a": True, "component:b": 0}, "initial": True, "safe": True, "goal": True},
                {"id": "q1", "valuation": {"component:a": 1, "component:b": 1}, "initial": True, "safe": True, "goal": True},
            ],
            "buckets": [
                {"source": "q0", "action": "idle", "targets": ["q0"]},
                {"source": "q1", "action": "idle", "targets": ["q1"]},
            ],
            "load_states": [
                {"id": "z0", "valuation": {"component:a": True, "component:b": 0}},
                {"id": "z1", "valuation": {"component:a": 1, "component:b": 1}},
            ],
            "handover_relation": [
                {"goal": "q0", "load": "z0"}, {"goal": "q1", "load": "z1"},
            ],
            "dependencies": [],
            "provenance": {"classification": "controlled scalar-sort regression"},
        }
        certificate = producer.discover(collision)
        self.assertEqual(certificate["result"], "NON_FACTORABLE")
        self.assertEqual(certificate["maximum_block_count"], 1)
        self.assertEqual(consumer.check(collision, certificate, max_atoms=2)["status"], "PASS")

        nonfinite = copy.deepcopy(collision)
        nonfinite["states"][0]["valuation"]["component:a"] = float("nan")
        with self.assertRaises(producer.DiscoveryError):
            producer.discover(nonfinite)
        with self.assertRaises(consumer.CertificateError):
            consumer.IndependentTable(nonfinite)
        nonfinite_metadata = copy.deepcopy(collision)
        nonfinite_metadata["provenance"]["invalid_number"] = float("inf")
        with self.assertRaises(producer.DiscoveryError):
            producer.discover(nonfinite_metadata)

    def test_update_actions_and_pending_atoms_are_bijective(self) -> None:
        alias = copy.deepcopy(self.base)
        original = next(action for action in alias["actions"] if action["id"] == "prepare")
        duplicate = copy.deepcopy(original)
        duplicate["id"] = "prepare-alias"
        alias["actions"].append(duplicate)
        for bucket in list(alias["buckets"]):
            if bucket["action"] == "prepare":
                copy_bucket = copy.deepcopy(bucket)
                copy_bucket["action"] = "prepare-alias"
                alias["buckets"].append(copy_bucket)
        with self.assertRaises(producer.DiscoveryError):
            producer.discover(alias)
        with self.assertRaises(consumer.CertificateError):
            consumer.IndependentTable(alias)

    def test_shared_stutter_must_be_global_including_goal_and_unsafe(self) -> None:
        mutation = copy.deepcopy(self.base)
        goal = next(state["id"] for state in mutation["states"] if state["goal"])
        mutation["buckets"] = [
            bucket for bucket in mutation["buckets"]
            if not (bucket["source"] == goal and bucket["action"] == "idle")
        ]
        certificate = producer.discover(mutation)
        self.assertEqual(certificate["result"], "INELIGIBLE")
        self.assertEqual(certificate["ineligibility_obstruction"]["kind"], "SHARED_NOT_GLOBAL_PURE_STUTTER")

    def test_order_permutations_preserve_discovery_result(self) -> None:
        mutation = copy.deepcopy(self.base)
        for field in ("atoms", "actions", "states", "buckets", "load_states", "handover_relation", "dependencies"):
            mutation[field].reverse()
        observed = producer.discover(mutation)
        self.assertEqual(observed["result"], self.base_certificate["result"])
        self.assertEqual(observed["maximum_block_count"], self.base_certificate["maximum_block_count"])
        self.assertEqual(observed["selected_partition"], self.base_certificate["selected_partition"])

    def test_partition_budget_exhaustion_is_inconclusive_not_nonfactorable(self) -> None:
        with self.assertRaisesRegex(producer.DiscoveryError, "inconclusive"):
            producer.discover(self.base, partition_limit=0)
        with self.assertRaisesRegex(producer.DiscoveryError, "inconclusive"):
            producer.discover(self.base, maximum_partition_count=0)
        mutation = copy.deepcopy(self.obstructions["obstruction-foreign-enabledness"])
        mutation["atoms"].append({"id": "aux:free", "kind": "auxiliary"})
        for state in mutation["states"]:
            state["valuation"]["aux:free"] = "constant"
        for load in mutation["load_states"]:
            load["valuation"]["aux:free"] = "constant"
        with self.assertRaisesRegex(producer.DiscoveryError, "inconclusive"):
            producer.discover(mutation, partition_limit=0)

    def test_coordinate_screen_keeps_family_denominator_and_zero_typed_positive(self) -> None:
        report = screen.run(ROOT)
        self.assertEqual(report["c1_semantic_family_count"], 10)
        self.assertEqual(report["case_count"], 43)
        self.assertEqual(report["nontrivial_typed_positive_claim_count"], 0)
        self.assertEqual(
            report["classifications"],
            {
                "MISSING_CARTESIAN_TUPLE": 13,
                "RECTANGULAR_BUT_GOAL_EMPTY": 4,
                "SINGLE_SUPPORT_COMPONENT": 26,
            },
        )

    def test_consumer_has_no_import_of_producer_module(self) -> None:
        source = (ANALYSIS / "check_typed_partition_certificate.py").read_text(encoding="utf-8")
        self.assertNotIn("import discover_typed_partition", source)
        self.assertNotIn("from discover_typed_partition", source)

    def test_discovered_partitions_transport_winning_and_losing_witnesses(self) -> None:
        observed = {}
        for identifier, game in self.positives.items():
            partition = producer.discover(game)
            witness = witness_producer.synthesize(game, partition)
            report = witness_consumer.check(game, partition, witness)
            self.assertEqual(report["status"], "PASS")
            self.assertTrue(report["direct_flat_decision_agrees"])
            observed[identifier] = report["decision"]
        self.assertEqual(sum(value == "realizable" for value in observed.values()), 2)
        self.assertEqual(sum(value == "unrealizable" for value in observed.values()), 1)

    def test_transport_witness_survives_json_round_trip(self) -> None:
        partition = producer.discover(self.base)
        witness = witness_producer.synthesize(self.base, partition)
        serialized = json.loads(json.dumps(witness, ensure_ascii=False, sort_keys=True))
        report = witness_consumer.check(self.base, partition, serialized)
        self.assertEqual(report["status"], "PASS")
        self.assertTrue(report["direct_flat_decision_agrees"])

    def test_partition_certificates_survive_json_round_trip(self) -> None:
        cases = (
            self.base,
            self.obstructions["obstruction-goal-uc-activity"],
        )
        for game in cases:
            certificate = producer.discover(game)
            serialized = json.loads(json.dumps(certificate, ensure_ascii=False, sort_keys=True))
            report = consumer.check(game, serialized, max_atoms=12)
            self.assertEqual(report["status"], "PASS")

    def test_isolated_cli_round_trip_for_factored_ineligible_and_transport(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            cases = {
                "factored": self.base,
                "ineligible": self.obstructions["obstruction-goal-uc-activity"],
            }
            for name, game in cases.items():
                game_path = out / f"{name}-game.json"
                cert_path = out / f"{name}-certificate.json"
                game_path.write_text(json.dumps(game, ensure_ascii=False) + "\n", encoding="utf-8")
                subprocess.run(
                    [sys.executable, "-I", "-S", "-B", str(ANALYSIS / "discover_typed_partition.py"), str(game_path), "--output", str(cert_path)],
                    check=True, capture_output=True, text=True,
                )
                subprocess.run(
                    [sys.executable, "-I", "-S", "-B", str(ANALYSIS / "check_typed_partition_certificate.py"), str(game_path), str(cert_path)],
                    check=True, capture_output=True, text=True,
                )
            witness_path = out / "witness.json"
            subprocess.run(
                [sys.executable, "-I", "-S", "-B", str(ANALYSIS / "synthesize_discovered_witness.py"), str(out / "factored-game.json"), str(out / "factored-certificate.json"), "--output", str(witness_path)],
                check=True, capture_output=True, text=True,
            )
            result = subprocess.run(
                [sys.executable, "-I", "-S", "-B", str(ANALYSIS / "check_discovered_witness.py"), str(out / "factored-game.json"), str(out / "factored-certificate.json"), str(witness_path)],
                check=True, capture_output=True, text=True,
            )
            self.assertEqual(json.loads(result.stdout)["status"], "PASS")

    def test_transport_consumer_rejects_rank_kappa_and_cylinder_tampering(self) -> None:
        winning = self.positives["multistate-winning-nondeterministic-handover"]
        winning_partition = producer.discover(winning)
        winning_witness = witness_producer.synthesize(winning, winning_partition)
        rank = copy.deepcopy(winning_witness)
        rank_state = next(iter(rank["global_witness"]["global_rank"]))
        rank["global_witness"]["global_rank"][rank_state] += 1
        rank_boolean = copy.deepcopy(winning_witness)
        rank_one = next(
            state for state, value in rank_boolean["global_witness"]["global_rank"].items()
            if type(value) is int and value == 1
        )
        rank_boolean["global_witness"]["global_rank"][rank_one] = True
        kappa = copy.deepcopy(winning_witness)
        kappa["global_witness"]["global_kappa"].clear()
        losing = self.positives["multistate-losing-monitor-outcome"]
        losing_partition = producer.discover(losing)
        losing_witness = witness_producer.synthesize(losing, losing_partition)
        cylinder = copy.deepcopy(losing_witness)
        cylinder["global_witness"]["losing_cylinder"] = []
        for game, partition, mutation in (
            (winning, winning_partition, rank),
            (winning, winning_partition, rank_boolean),
            (winning, winning_partition, kappa),
            (losing, losing_partition, cylinder),
        ):
            with self.assertRaises(witness_consumer.TransportError):
                witness_consumer.check(game, partition, mutation)

    def test_transport_consumer_does_not_import_discovery_or_witness_producer(self) -> None:
        source = (ANALYSIS / "check_discovered_witness.py").read_text(encoding="utf-8")
        self.assertNotIn("import discover_typed_partition", source)
        self.assertNotIn("from discover_typed_partition", source)
        self.assertNotIn("import synthesize_discovered_witness", source)
        self.assertNotIn("from synthesize_discovered_witness", source)


if __name__ == "__main__":
    unittest.main()
