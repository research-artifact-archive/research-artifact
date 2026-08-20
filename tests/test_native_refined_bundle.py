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

from check_native_refined_bundle import BundleError, check  # noqa: E402


EVIDENCE = ROOT / "evidence/m8q-native-factorization/results"


def load(name: str) -> dict:
    return json.loads((EVIDENCE / name).read_text(encoding="utf-8"))


def serialized_state_key(state: dict) -> str:
    return json.dumps(
        {key: state[key] for key in ("physical", "active_testers", "pending_actions")},
        ensure_ascii=False,
        separators=(",", ":"),
    )


def rewrite_state_target_keys(local: dict, old_keys: dict[str, str]) -> None:
    rewritten = {
        old_keys[state["id"]]: serialized_state_key(state)
        for state in local["proof"]["states"]
    }
    for bucket in local["proof"]["candidate_buckets"]:
        bucket["target_keys"] = sorted(rewritten.get(key, key) for key in bucket["target_keys"])


class NativeRefinedBundleTest(unittest.TestCase):
    def assert_rejected(self, value: dict) -> None:
        with self.assertRaises(BundleError):
            check(value)

    def test_registered_results(self) -> None:
        base = check(load("productioncell-arms2-base.json"))
        r1 = check(load("productioncell-arms2-r1.json"))
        r2 = check(load("productioncell-arms2-r2.json"))
        self.assertEqual(base["solve_status"], "STRUCTURALLY_CHECKED_PRODUCER_WITNESS")
        self.assertEqual(r1["factor_status"], "TRIVIAL_ONE_BLOCK")
        self.assertEqual(r2["solve_status"], "STRUCTURALLY_CHECKED_PRODUCER_WITNESS")

    def test_rank_boolean_rejected(self) -> None:
        value = load("productioncell-arms2-base.json")
        value["locals"][0]["proof"]["states"][0]["rank"] = True
        self.assert_rejected(value)

    def test_root_census_mismatch_rejected(self) -> None:
        value = load("productioncell-arms2-base.json")
        value["locals"][0]["proof"]["root_state_ids"].pop()
        self.assert_rejected(value)

    def test_strategy_target_corruption_rejected(self) -> None:
        value = load("productioncell-arms2-base.json")
        buckets = value["locals"][0]["proof"]["strategy_buckets"]
        bucket = buckets[0]
        bucket["target_state_ids"] = [value["locals"][0]["proof"]["states"][0]["id"]]
        self.assert_rejected(value)

    def test_candidate_strategy_mismatch_rejected(self) -> None:
        value = load("productioncell-arms2-base.json")
        chosen = value["locals"][0]["proof"]["strategy_buckets"][0]
        candidate = next(
            item for item in value["locals"][0]["proof"]["candidate_buckets"]
            if item["source"] == chosen["source"] and item["action"] == chosen["action"]
        )
        candidate["target_keys"] = []
        self.assert_rejected(value)

    def test_action_control_context_mismatch_rejected(self) -> None:
        value = load("productioncell-arms2-base.json")
        bucket = next(item for item in value["locals"][0]["proof"]["candidate_buckets"] if item["target_keys"] and not item["controllable"])
        bucket["controllable"] = True
        self.assert_rejected(value)

    def test_goal_signature_tester_mutation_rejected(self) -> None:
        value = load("productioncell-arms2-r2.json")
        state = next(item for item in value["locals"][0]["proof"]["states"] if item["goal"])
        key = next(iter(state["goal_signature"]["new_requirement_states"]))
        state["goal_signature"]["new_requirement_states"][key] += 1
        self.assert_rejected(value)

    def test_observer_extra_fibre_rejected(self) -> None:
        value = load("productioncell-arms2-base.json")
        relation = value["transport"]["observer_relations"][0]
        assembly = value["transport"]["terminal_assemblies"][0]
        goal_id = assembly["local_goal_signature_ids"][0]
        goal_state = next(item for item in value["locals"][0]["proof"]["states"] if item["goal_signature_id"] == goal_id)
        local = goal_state["goal_signature"]["physical"][0]["observer_states"]
        original = next(item for item in relation["pairs"] if item["local"] == local)
        added = copy.deepcopy(original)
        added["global"][0] = 1 - added["global"][0]
        relation["pairs"].append(added)
        value["transport"]["observer_relation_pair_count"] += 1
        self.assert_rejected(value)

    def test_nonterminal_observer_fibre_omission_rejected(self) -> None:
        value = load("productioncell-arms2-base.json")
        local = value["locals"][0]
        goal_vectors = {
            tuple(state["physical"][0]["observer_states"])
            for state in local["proof"]["states"] if state["goal"]
        }
        state = next(
            state for state in local["proof"]["states"]
            if not state["goal"] and tuple(state["physical"][0]["observer_states"]) not in goal_vectors
        )
        vector = state["physical"][0]["observer_states"]
        relation = value["transport"]["observer_relations"][0]
        removed = [pair for pair in relation["pairs"] if pair["local"] == vector]
        self.assertTrue(removed)
        relation["pairs"] = [pair for pair in relation["pairs"] if pair["local"] != vector]
        value["transport"]["observer_relation_pair_count"] -= len(removed)
        self.assert_rejected(value)

    def test_unseen_nonterminal_observer_memory_rejected(self) -> None:
        value = load("productioncell-arms2-base.json")
        local = value["locals"][0]
        state = next(
            state for state in local["proof"]["states"]
            if not state["goal"] and state["physical"][0]["observer_states"]
        )
        old_key = json.dumps(
            {key: state[key] for key in ("physical", "active_testers", "pending_actions")},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        state["physical"][0]["observer_states"][0] = 999
        new_key = json.dumps(
            {key: state[key] for key in ("physical", "active_testers", "pending_actions")},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        for bucket in local["proof"]["candidate_buckets"]:
            bucket["target_keys"] = sorted(new_key if key == old_key else key for key in bucket["target_keys"])
        self.assert_rejected(value)

    def test_terminal_observer_mutation_rejected(self) -> None:
        value = load("productioncell-arms2-base.json")
        value["transport"]["terminal_assemblies"][0]["global_observer_states"][0] = 1
        self.assert_rejected(value)

    def test_selector_removal_rejected(self) -> None:
        value = load("productioncell-arms2-base.json")
        endpoint = value["transport"]["terminal_assemblies"][0]["endpoint_id"]
        value["transport"]["load_selectors"] = [item for item in value["transport"]["load_selectors"] if item["endpoint_id"] != endpoint]
        value["transport"]["load_selector_signature_count"] -= 1
        value["transport"]["load_selector_endpoint_count"] -= 1
        self.assert_rejected(value)

    def test_nonterminal_selector_removal_rejected(self) -> None:
        value = load("productioncell-arms2-base.json")
        terminal_endpoint = value["transport"]["terminal_assemblies"][0]["endpoint_id"]
        remove = next(item for item in value["transport"]["load_selectors"] if item["endpoint_id"] != terminal_endpoint)
        value["transport"]["load_selectors"].remove(remove)
        value["transport"]["load_selector_signature_count"] -= 1
        value["transport"]["load_selector_endpoint_count"] -= 1
        self.assert_rejected(value)

    def test_empty_terminal_assembly_rejected(self) -> None:
        value = load("productioncell-arms2-base.json")
        value["transport"]["terminal_assemblies"] = []
        value["transport"]["certificate_terminal_tuple_count"] = 0
        value["transport"]["terminal_observer_fiber_count"] = 0
        self.assert_rejected(value)

    def test_coherent_new_tester_omission_rejected(self) -> None:
        value = load("productioncell-arms2-r2.json")
        state = next(item for item in value["locals"][0]["proof"]["states"] if item["goal"])
        tester = next(iter(state["goal_signature"]["new_requirement_states"]))
        del state["goal_signature"]["new_requirement_states"][tester]
        for selector in value["transport"]["load_selectors"]:
            selector["tester_states"].pop(tester, None)
        self.assert_rejected(value)

    def test_goal_pending_action_rejected(self) -> None:
        value = load("productioncell-arms2-base.json")
        state = next(item for item in value["locals"][0]["proof"]["states"] if item["goal"])
        state["pending_actions"] = ["bogus-update"]
        self.assert_rejected(value)

    def test_candidate_update_kind_rejected(self) -> None:
        value = load("productioncell-arms2-base.json")
        bucket = value["locals"][0]["proof"]["candidate_buckets"][0]
        bucket["update"] = not bucket["update"]
        self.assert_rejected(value)

    def test_observer_relation_overlap_rejected(self) -> None:
        value = load("productioncell-arms2-base.json")
        value["transport"]["observer_relations"][1]["global_observer_indices"][0] = value["transport"]["observer_relations"][0]["global_observer_indices"][0]
        self.assert_rejected(value)

    def test_unknown_dependency_kind_rejected(self) -> None:
        value = load("productioncell-arms2-base.json")
        value["dependency_receipts"][0]["kind"] = "unknown"
        self.assert_rejected(value)

    def test_duplicate_tester_phase_source_ordinal_rejected(self) -> None:
        value = load("productioncell-arms2-r2.json")
        local = value["locals"][0]
        old_keys = {state["id"]: serialized_state_key(state) for state in local["proof"]["states"]}
        state = next(
            item for item in local["proof"]["states"]
            if not item["goal"] and item["active_testers"]
        )
        tester, residual = next(iter(state["active_testers"].items()))
        phase, remainder = tester.split(":", 1)
        source, ordinal = remainder.rsplit(":", 1)
        state["active_testers"][f"{phase}:{source}:{int(ordinal) + 1000}"] = residual
        rewrite_state_target_keys(local, old_keys)
        self.assert_rejected(value)

    def test_cross_block_action_and_tester_aliases_rejected(self) -> None:
        with self.subTest("action"):
            value = load("productioncell-arms2-base.json")
            local = value["locals"][1]
            for bucket in local["proof"]["candidate_buckets"]:
                if bucket["action"] == "clean.2":
                    bucket["action"] = "clean.1"
            for bucket in local["proof"]["strategy_buckets"]:
                if bucket["action"] == "clean.2":
                    bucket["action"] = "clean.1"
            receipt = next(
                item for item in value["dependency_receipts"]
                if item["kind"] == "ordinary-action"
                and item["declaration"] == "clean.2"
                and item["components"] == [1]
            )
            receipt["declaration"] = "clean.1"
            self.assert_rejected(value)

        with self.subTest("tester"):
            value = load("productioncell-arms2-base.json")
            local = value["locals"][1]
            old_keys = {state["id"]: serialized_state_key(state) for state in local["proof"]["states"]}
            old_source = "P_OLD_TOOL_ORDER_2"
            new_source = "P_OLD_TOOL_ORDER_1"
            for state in local["proof"]["states"]:
                renamed = {}
                for tester, residual in state["active_testers"].items():
                    phase, remainder = tester.split(":", 1)
                    source, ordinal = remainder.rsplit(":", 1)
                    if source == old_source:
                        source = new_source
                    renamed[f"{phase}:{source}:{ordinal}"] = residual
                state["active_testers"] = renamed
            rewrite_state_target_keys(local, old_keys)
            receipt = next(
                item for item in value["dependency_receipts"]
                if item["kind"] == "tester"
                and item["declaration"] == old_source
                and item["components"] == [1]
            )
            receipt["declaration"] = new_source
            self.assert_rejected(value)

    def test_reordered_semantic_state_clone_rejected(self) -> None:
        value = load("productioncell-arms2-r2.json")
        local = value["locals"][0]
        original = next(
            state for state in local["proof"]["states"]
            if state["goal"] and len(state["active_testers"]) > 1
        )
        clone = copy.deepcopy(original)
        clone["id"] = original["id"] + "-reordered-clone"
        clone["active_testers"] = dict(reversed(list(clone["active_testers"].items())))
        local["proof"]["states"].append(clone)
        local["certificate_rank_count"] += 1
        local["independent_certificate_states"] += 1
        self.assert_rejected(value)

    def test_kappa_endpoint_swap_rejected(self) -> None:
        value = load("productioncell-arms2-base.json")
        value["transport"]["terminal_assemblies"][0]["endpoint_id"] = "new-99999999"
        self.assert_rejected(value)

    def test_dependency_duplicate_rejected(self) -> None:
        value = load("productioncell-arms2-base.json")
        value["dependency_receipts"].append(copy.deepcopy(value["dependency_receipts"][0]))
        self.assert_rejected(value)

    def test_dependency_cross_block_mutation_rejected(self) -> None:
        value = load("productioncell-arms2-base.json")
        value["dependency_receipts"][0]["components"] = [0, 1]
        self.assert_rejected(value)

    def test_global_mixed_counter_rejected(self) -> None:
        value = load("productioncell-arms2-base.json")
        value["global_mixed_state_count"] = 1
        self.assert_rejected(value)

    def test_goal_first_policy_rejected(self) -> None:
        value = load("productioncell-arms2-base.json")
        value["arbiter"]["original_goal_preempts_local_progress"] = False
        self.assert_rejected(value)

    def test_status_promotion_rejected(self) -> None:
        value = load("productioncell-arms2-base.json")
        value["solve_status"] = "EXACT_WIN"
        self.assert_rejected(value)

    def test_trivial_counter_corruption_rejected(self) -> None:
        value = load("productioncell-arms2-r1.json")
        value["local_solver_discovered_states_sum"] = 999
        self.assert_rejected(value)


if __name__ == "__main__":
    unittest.main()
