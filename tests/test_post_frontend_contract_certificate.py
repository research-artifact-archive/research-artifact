#!/usr/bin/env python3

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "analysis"
if str(ANALYSIS) not in sys.path:
    sys.path.insert(0, str(ANALYSIS))

import check_post_frontend_contract_certificate as CHECK  # noqa: E402
from audit_post_frontend_contract_certificate import audit  # noqa: E402
from run_post_frontend_contract_certificate import (  # noqa: E402
    CampaignError, load, verify_historical_case, verify_protocol,
)


BASE = ROOT / (
    "evidence/m8s-post-frontend-contract-certificate/cases/"
    "productioncell-arms2-base-productioncell-arms-2-fg"
)
BASE_BUNDLE = ROOT / (
    "evidence/m8q-native-factorization/panel/cases/"
    "productioncell-arms2-base-productioncell-arms-2-fg/bundle.json"
)
PROTOCOL = ROOT / "protocols/post_frontend_contract_certificate_v1_20260814.json"


class _TinyProblem:
    block = (0,)

    def __init__(self, state: CHECK.Config, *, safe: bool) -> None:
        self.roots = frozenset({state})
        self._safe = safe

    def structurally_valid(self, _state: CHECK.Config) -> bool:
        return True

    def safe(self, _state: CHECK.Config) -> bool:
        return self._safe

    def goal_payload(self, _state: CHECK.Config):
        return None

    def candidates(self, _state: CHECK.Config):
        return ("a",)

    def post(self, state: CHECK.Config, _action: str):
        return frozenset({state})

    def is_controllable(self, _action: str) -> bool:
        return True


def _tiny_local(*, safe: bool, duplicate_target: bool = False) -> dict:
    state = CHECK.Config(
        (CHECK.Tagged("OLD", CHECK.Local(0)),), (), frozenset()
    )
    target = CHECK.bundle_config_key(state)
    targets = [target, target] if duplicate_target else [target]
    return {
        "block_index": 0,
        "components": [0],
        "decision": "realizable",
        "full_goal_count": 0,
        "quiet_terminal_count": 0,
        "full_goal_uncontrollable_actions": [],
        "solver_discovered_states": 0,
        "solver_successor_queries": 0,
        "solver_outcomes": 0,
        "certificate_initial_count": 1,
        "certificate_rank_count": 1,
        "certificate_strategy_source_count": 1,
        "certificate_strategy_bucket_count": 1,
        "certificate_goal_match_count": 0,
        "independent_certificate_valid": True,
        "independent_certificate_basis": "independent_certificate_proof",
        "independent_certificate_states": 1,
        "independent_certificate_queries": 1,
        "independent_certificate_outcomes": 1,
        "independent_certificate_elapsed_ms": 0,
        "proof": {
            "schema_version": "fg-ducs-local-rank-proof-v1",
            "semantic_basis": "independent_fine_grained_semantics",
            "root_state_ids": ["q00000000"],
            "states": [{
                "physical": [{
                    "version": "OLD", "raw_state": 0,
                    "observer_states": [],
                }],
                "active_testers": {}, "pending_actions": [],
                "id": "q00000000", "rank": 1, "safe": safe,
                "goal": False, "goal_signature_id": None,
                "goal_signature": None,
            }],
            "candidate_buckets": [{
                "source": "q00000000", "action": "a",
                "controllable": True, "update": False,
                "target_keys": targets,
            }],
            "strategy_buckets": [{
                "source": "q00000000", "action": "a",
                "target_state_ids": ["q00000000"],
            }],
        },
    }


class PostFrontendContractCertificateTest(unittest.TestCase):

    def facts(self) -> dict:
        return load(BASE / "facts.json")

    def test_registered_two_case_audit_recomputes_exactly(self) -> None:
        observed = audit()
        stored = load(ROOT / "evidence/m8s-post-frontend-contract-certificate/audit.json")
        self.assertEqual(observed, stored)
        self.assertEqual(
            observed["post_frontend_contract_ir_to_winning_certificate_semantic_verification"],
            2,
        )
        self.assertEqual(observed["totals"]["candidate_buckets"], 4774)
        self.assertEqual(observed["independent_raw_source_frontend"], 0)
        self.assertEqual(observed["independent_win_synthesis"], 0)
        self.assertEqual(observed["source_to_win_replay"], 0)

    def test_conclusion_protocol_and_compact_machine_mutations_are_rejected(self) -> None:
        mutations = []

        injected = self.facts()
        injected["proof"] = {"winning": True}
        mutations.append(injected)

        progress = self.facts()
        progress["protocol"]["progress_actions_in_index_order"].remove(
            "reconfigure_PRODUCTION_CELL_1"
        )
        mutations.append(progress)

        observer = self.facts()
        observer["observer_machines"][0]["transitions"][0]["targets"] = [
            1 - observer["observer_machines"][0]["transitions"][0]["targets"][0]
        ]
        mutations.append(observer)

        initial = self.facts()
        initial["components"][0]["old_machine"]["initial_state"] = 1
        mutations.append(initial)

        tau = self.facts()
        tester = next(machine for machine in tau["old_safety_machines"]
                      if machine["max_states"] > 1 and "tau" in machine["alphabet"])
        tau_index = tester["alphabet"].index("tau")
        tester["transitions"].append({
            "source": 1, "action_index": tau_index, "targets": [1],
        })
        tester["transitions"].sort(key=lambda row: (
            row["source"], row["action_index"]
        ))
        mutations.append(tau)

        for index, mutated in enumerate(mutations):
            with self.subTest(index=index):
                with self.assertRaises(CHECK.CheckError):
                    CHECK.parse_contract(mutated)

    def test_open_ir_and_contradictory_bundle_envelopes_are_rejected(self) -> None:
        numeric_flags = self.facts()
        numeric_flags["flags"]["on_the_fly"] = 1

        component_conclusion = self.facts()
        component_conclusion["components"][0]["producer_winning_status"] = "WIN"

        transfer_order = self.facts()
        transfer_order["components"][0]["transfer_relation"][:2] = reversed(
            transfer_order["components"][0]["transfer_relation"][:2]
        )
        for index, mutated in enumerate(
                (numeric_flags, component_conclusion, transfer_order)):
            with self.subTest(ir=index):
                with self.assertRaises(CHECK.CheckError):
                    CHECK.parse_contract(mutated)

        baseline_bundle = load(BASE_BUNDLE)
        bundle_mutations = []
        extra = copy.deepcopy(baseline_bundle)
        extra["unexpected_root_field"] = True
        bundle_mutations.append(extra)
        status = copy.deepcopy(baseline_bundle)
        status["solve_status"] = "PRODUCER_REPORTED_LOSS"
        bundle_mutations.append(status)
        numeric = copy.deepcopy(baseline_bundle)
        numeric["old_endpoint_state_count"] = 126.0
        bundle_mutations.append(numeric)
        local = copy.deepcopy(baseline_bundle)
        local["locals"][0]["independent_certificate_valid"] = False
        bundle_mutations.append(local)
        query_census = copy.deepcopy(baseline_bundle)
        query_census["locals"][0]["independent_certificate_queries"] = 0
        bundle_mutations.append(query_census)
        receipt = copy.deepcopy(baseline_bundle)
        receipt["dependency_receipts"][0]["declaration"] = "forged-declaration"
        bundle_mutations.append(receipt)
        terminal = copy.deepcopy(baseline_bundle)
        terminal["transport"]["terminal_assemblies"][0][
            "controller_state"] = 79.0
        bundle_mutations.append(terminal)
        for index, mutated in enumerate(bundle_mutations):
            with self.subTest(bundle=index):
                with self.assertRaises(CHECK.CheckError):
                    CHECK.verify(self.facts(), mutated)

    def test_protocol_denominator_claim_and_historical_record_are_bound(self) -> None:
        protocol = load(PROTOCOL)
        panel_records = verify_protocol(protocol)

        claim = copy.deepcopy(protocol)
        claim["claim_boundary"]["held_out_cases"] = 1
        with self.assertRaises(CampaignError):
            verify_protocol(claim)

        denominator = copy.deepcopy(protocol)
        denominator["cases"][1]["cluster"] = "forged-cluster"
        with self.assertRaises(CampaignError):
            verify_protocol(denominator)

        historical = copy.deepcopy(protocol["cases"][0])
        historical["condition"] = "forged-condition"
        with self.assertRaises(CampaignError):
            verify_historical_case(historical, protocol, panel_records)

    def test_endpoint_distinguishes_observer_only_from_environment_actions(self) -> None:
        contract = CHECK.parse_contract(self.facts())
        components = CHECK.global_components(contract)
        self.assertEqual(len(CHECK.build_endpoint(
            contract, components, contract.old_testers, "OLD"
        )), 126)
        mutated = copy.copy(contract)
        old = contract.controllers["OLD"]
        post = dict(old.post)
        self.assertIn((0, "in.1"), post)
        del post[(0, "in.1")]
        mutated.controllers = dict(contract.controllers)
        mutated.controllers["OLD"] = CHECK.Machine(
            old.name, old.initial, old.states, old.alphabet, post
        )
        with self.assertRaisesRegex(CHECK.CheckError, "uncontrollable"):
            CHECK.build_endpoint(
                mutated, components, contract.old_testers, "OLD"
            )

    def test_ownerless_normal_action_must_be_controllable_pure_stutter(self) -> None:
        contract = CHECK.parse_contract(self.facts())
        mutated = copy.copy(contract)
        mutated.normal = frozenset(set(contract.normal) | {"ownerless"})
        with self.assertRaisesRegex(CHECK.CheckError, "ownerless normal event"):
            CHECK.dependency_partition(mutated)

        allowed = copy.copy(mutated)
        allowed.controllable_normal = frozenset(
            set(contract.controllable_normal) | {"ownerless"}
        )
        partition, owners, _updates = CHECK.dependency_partition(allowed)
        self.assertEqual(partition, [[0], [1]])
        self.assertEqual(owners["ownerless"], frozenset())

    def test_unsafe_rank_state_and_duplicate_target_are_rejected(self) -> None:
        unsafe = _tiny_local(safe=False)
        state = CHECK.parse_config_payload({
            "physical": unsafe["proof"]["states"][0]["physical"],
            "active_testers": {}, "pending_actions": [],
        }, "tiny")
        with self.assertRaisesRegex(CHECK.CheckError, "unsafe"):
            CHECK.verify_local(_TinyProblem(state, safe=False), unsafe, 0)

        duplicate = _tiny_local(safe=True, duplicate_target=True)
        with self.assertRaisesRegex(CHECK.CheckError, "duplicates"):
            CHECK.verify_local(_TinyProblem(state, safe=True), duplicate, 0)


if __name__ == "__main__":
    unittest.main()
