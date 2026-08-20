#!/usr/bin/env python3

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "analysis"
if str(ANALYSIS) not in sys.path:
    sys.path.insert(0, str(ANALYSIS))

from audit_native_source_dependencies import AuditError, audit  # noqa: E402
from check_native_source_dependencies import ReplayError, compare, load, parse_facts  # noqa: E402


BASE_ID = "productioncell-arms2-base-productioncell-arms-2-fg"
INVALID_ID = "metasocket-base-metasocket-fg"


class NativeSourceDependencyReplayTest(unittest.TestCase):
    def case(self, case_id: str) -> tuple[dict, dict, dict | None, str]:
        replay = ROOT / "evidence/m8r-native-source-dependency-replay/cases" / case_id
        original = ROOT / "evidence/m8q-native-factorization/panel/cases" / case_id
        facts = load(replay / "facts.json")
        record = load(original / "record.json")
        bundle_path = original / "bundle.json"
        bundle = load(bundle_path) if bundle_path.is_file() else None
        stderr = (original / "stderr.txt").read_text(encoding="utf-8")
        return facts, record, bundle, stderr

    def with_pure_loop(self, facts: dict, action: str = "pure.loop") -> dict:
        result = copy.deepcopy(facts)
        result["controllable_actions"] = sorted(set(result["controllable_actions"] + [action]))
        for component in result["components"]:
            for machine in (component["old_machine"], component["new_machine"]):
                action_index = len(machine["alphabet"])
                machine["alphabet"].append(action)
                machine["transitions"].extend(
                    {"source": state, "action_index": action_index, "targets": [state]}
                    for state in range(machine["max_states"])
                )
                machine["transitions"].sort(key=lambda row: (row["source"], row["action_index"]))
        return result

    def test_registered_campaign_recomputes_exactly(self) -> None:
        observed = audit()
        stored = load(ROOT / "evidence/m8r-native-source-dependency-replay/audit.json")
        self.assertEqual(observed, stored)
        self.assertEqual(observed["compiled_facts_replay_pass"], 41)
        self.assertEqual(observed["dependency_receipt_agreement_count"], 35)
        self.assertEqual(observed["component_partition_agreement_count"], 35)
        self.assertEqual(observed["ownerless_gate_agreement_count"], 6)
        self.assertEqual(observed["ordinary_lts_source_replay_count"], 0)
        self.assertEqual(observed["source_to_witness_replay_count"], 0)

    def test_conclusion_field_injection_is_rejected(self) -> None:
        facts, _record, _bundle, _stderr = self.case(BASE_ID)
        facts["factor_status"] = "NONTRIVIAL_SOURCE_NATIVE"
        with self.assertRaises(ReplayError):
            parse_facts(facts)

    def test_duplicate_json_key_is_rejected(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", dir=ROOT) as stream:
            stream.write('{"schema_version":"x","schema_version":"y"}\n')
            stream.flush()
            with self.assertRaises(ReplayError):
                load(Path(stream.name))

    def test_source_name_binding_mutation_is_rejected(self) -> None:
        facts, record, bundle, stderr = self.case(BASE_ID)
        facts["source_name"] = "forged.lts"
        with self.assertRaises(ReplayError):
            compare(facts, record, bundle, stderr)

    def test_source_hash_binding_mutation_is_rejected(self) -> None:
        facts, record, bundle, stderr = self.case(BASE_ID)
        record["sha256"] = "0" * 64
        with self.assertRaises(ReplayError):
            compare(facts, record, bundle, stderr)

    def test_bundle_receipt_omission_is_rejected(self) -> None:
        facts, record, bundle, stderr = self.case(BASE_ID)
        assert bundle is not None
        bundle["dependency_receipts"].pop()
        with self.assertRaises(ReplayError):
            compare(facts, record, bundle, stderr)

    def test_bundle_partition_mutation_is_rejected(self) -> None:
        facts, record, bundle, stderr = self.case(BASE_ID)
        assert bundle is not None
        bundle["component_partition"] = [[0, 1]]
        with self.assertRaises(ReplayError):
            compare(facts, record, bundle, stderr)

    def test_update_action_binding_mutation_is_rejected(self) -> None:
        facts, _record, _bundle, _stderr = self.case(BASE_ID)
        facts["components"][1]["reconfigure_action"] = facts["components"][0]["reconfigure_action"]
        with self.assertRaises(ReplayError):
            parse_facts(facts)

    def test_precedence_cycle_mutation_is_rejected(self) -> None:
        facts, _record, _bundle, _stderr = self.case(BASE_ID)
        progress = facts["protocol"]["progress_actions_in_index_order"]
        facts["protocol"]["precedence"] = [
            {"before": progress[0], "after": progress[1]},
            {"before": progress[1], "after": progress[0]},
        ]
        facts["protocol"]["precedence"].sort(key=lambda row: (row["before"], row["after"]))
        with self.assertRaises(ReplayError):
            parse_facts(facts)

    def test_modal_component_transition_mutation_is_rejected(self) -> None:
        facts, _record, _bundle, _stderr = self.case(BASE_ID)
        machine = facts["components"][0]["old_machine"]
        modal_index = next(index for index, action in enumerate(machine["alphabet"]) if action.endswith("?"))
        machine["transitions"].append({"source": machine["max_states"] - 1, "action_index": modal_index, "targets": [0]})
        machine["transitions"].sort(key=lambda row: (row["source"], row["action_index"]))
        with self.assertRaises(ReplayError):
            parse_facts(facts)

    def test_tester_binding_omission_is_rejected(self) -> None:
        facts, _record, _bundle, _stderr = self.case(BASE_ID)
        key = next(iter(facts["protocol"]["old_safety_to_stop_action"]))
        del facts["protocol"]["old_safety_to_stop_action"][key]
        with self.assertRaises(ReplayError):
            parse_facts(facts)

    def test_observer_nondeterminism_mutation_is_rejected(self) -> None:
        facts, _record, _bundle, _stderr = self.case(BASE_ID)
        machine = next(item for item in facts["observer_machines"] if item["transitions"])
        row = machine["transitions"][0]
        alternative = 1 if row["targets"] != [1] else 0
        row["targets"] = sorted(set(row["targets"] + [alternative]))
        with self.assertRaises(ReplayError):
            parse_facts(facts)

    def test_ownerless_diagnostic_mutation_is_rejected(self) -> None:
        facts, record, bundle, _stderr = self.case(INVALID_ID)
        self.assertIsNone(bundle)
        with self.assertRaises(ReplayError):
            compare(facts, record, None, "NATIVE_FACTOR_INVALID=unrelated\n")

    def test_partial_self_loop_is_a_component_dependency(self) -> None:
        facts, _record, _bundle, _stderr = self.case(BASE_ID)
        facts = self.with_pure_loop(facts)
        baseline = parse_facts(facts)
        self.assertNotIn("pure.loop", {
            row["declaration"] for row in baseline["dependency_receipts"]
            if row["kind"] == "ordinary-action"
        })
        machine = facts["components"][0]["old_machine"]
        action_index = machine["alphabet"].index("pure.loop")
        machine["transitions"] = [
            row for row in machine["transitions"]
            if not (row["source"] == 0 and row["action_index"] == action_index)
        ]
        mutated = parse_facts(facts)
        self.assertIn(
            {"kind": "ordinary-action", "declaration": "pure.loop", "components": [0]},
            mutated["dependency_receipts"],
        )

    def test_ownerless_pure_loop_controllability_is_checked(self) -> None:
        facts, _record, _bundle, _stderr = self.case(BASE_ID)
        facts = self.with_pure_loop(facts)
        self.assertNotIn("pure.loop", parse_facts(facts)["ownerless_obstructions"])
        facts["controllable_actions"].remove("pure.loop")
        self.assertIn("pure.loop", parse_facts(facts)["ownerless_obstructions"])

    def test_claim_boundary_counters_cannot_be_promoted(self) -> None:
        stored = load(ROOT / "evidence/m8r-native-source-dependency-replay/audit.json")
        promoted = copy.deepcopy(stored)
        promoted["ordinary_lts_source_replay_count"] = 41
        expected = audit()
        self.assertNotEqual(promoted, expected)


if __name__ == "__main__":
    unittest.main()
