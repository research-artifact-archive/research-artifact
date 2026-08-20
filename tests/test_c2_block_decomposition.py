from __future__ import annotations

import importlib.util
import copy
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "analysis" / "audit_c2_block_decomposition.py"
SPEC = importlib.util.spec_from_file_location("block_audit", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
block_audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(block_audit)


def independent_source(k: int = 2) -> str:
    return (ROOT / f"inputs/c2/inputs/Models/independent_k{k:02d}.lts").read_text(
        encoding="utf-8"
    )


class BlockDecompositionAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cases = block_audit.load_multistate_games(
            ROOT / "inputs/c2/factored-multistate-games.json"
        )
        cls.winning_game = next(game for game, expected in cases if expected == "realizable")
        cls.losing_game = next(game for game, expected in cases if expected == "unrealizable")
        cls.winning_certificate = block_audit.synthesize(cls.winning_game)
        cls.losing_certificate = block_audit.synthesize(cls.losing_game)

    @staticmethod
    def rehash(certificate: dict) -> None:
        certificate["input_game_sha256"] = block_audit.sha256_json(
            block_audit.reconstruct_game(certificate)
        )

    def test_accepts_exact_frame_family(self) -> None:
        result = block_audit.audit_independent_source(independent_source(), 2)
        self.assertEqual(result["block_count"], 2)
        self.assertEqual(result["expected_flat_states"], 4)
        self.assertEqual(result["expected_composed_rank"], 2)

    def test_rejects_incomplete_updating_controller_lists(self) -> None:
        source = (ROOT / "inputs/c2/inputs/Models/independent_k02.lts").read_text(
            encoding="utf-8"
        )
        mutations = (
            "oldEnvironment = {OLD_COMPONENT_1}",
            "newEnvironment = {NEW_COMPONENT_1}",
            "mapRelation = {R_COMPONENT_1_FG}",
        )
        originals = (
            "oldEnvironment = {OLD_COMPONENT_1, OLD_COMPONENT_2}",
            "newEnvironment = {NEW_COMPONENT_1, NEW_COMPONENT_2}",
            "mapRelation = {R_COMPONENT_1_FG, R_COMPONENT_2_FG}",
        )
        for original, mutation in zip(originals, mutations):
            with self.subTest(field=original.split(" = ", 1)[0]):
                with self.assertRaises(block_audit.AuditError):
                    block_audit.audit_independent_source(source.replace(original, mutation), 2)

    def test_rejects_duplicate_updating_controller_member(self) -> None:
        source = independent_source().replace(
            "oldEnvironment = {OLD_COMPONENT_1, OLD_COMPONENT_2}",
            "oldEnvironment = {OLD_COMPONENT_1, OLD_COMPONENT_1, OLD_COMPONENT_2}",
        )
        with self.assertRaises(block_audit.AuditError):
            block_audit.audit_independent_source(source, 2)

    def test_rejects_missing_or_retargeted_update_controller(self) -> None:
        source = independent_source()
        target = "||UPDATE_CONTROLLER_OTF_FG = IndependentFamily."
        for mutation in ("", "||UPDATE_CONTROLLER_OTF_FG = OldEnvironment."):
            with self.subTest(mutation=mutation):
                with self.assertRaises(block_audit.AuditError):
                    block_audit.audit_independent_source(source.replace(target, mutation), 2)

    def test_rejects_cross_block_precedence(self) -> None:
        source = independent_source() + "precedes = {reconfigure_COMPONENT_1 < reconfigure_COMPONENT_2}\n"
        with self.assertRaises(block_audit.AuditError):
            block_audit.audit_independent_source(source, 2)

    def test_rejects_nonstuttering_shared_action(self) -> None:
        source = independent_source().replace(
            "OLD_COMPONENT_1 = (idle -> OLD_COMPONENT_1).",
            "OLD_COMPONENT_1 = (idle -> OLD_COMPONENT_2).",
        )
        with self.assertRaises(block_audit.AuditError):
            block_audit.audit_independent_source(source, 2)

    def test_rejects_uncontrollable_goal_activity(self) -> None:
        source = independent_source().replace(
            "NEW_COMPONENT_1 = (idle -> NEW_COMPONENT_1).",
            "NEW_COMPONENT_1 = (idle -> NEW_COMPONENT_1 | spin -> NEW_COMPONENT_1).",
        )
        with self.assertRaises(block_audit.AuditError):
            block_audit.audit_independent_source(source, 2)

    def test_travel_shared_nonstuttering_is_negative_control(self) -> None:
        source = """
OLD_AGENCY = (agency.succ -> OLD_AGENCY),
OLD_SERVICE = (agency.succ -> OLD_SERVICE_READY),
NEW_AGENCY = (agency.fail -> NEW_AGENCY),
NEW_SERVICE = (agency.fail -> NEW_SERVICE_READY).
"""
        result = block_audit.audit_travel_negative_control(source)
        self.assertFalse(result["passes_independent_family_syntax"])
        self.assertEqual(
            result["shared_nonstuttering_actions"],
            ["agency.fail", "agency.succ"],
        )

    def test_travel_requires_two_coupling_witnesses(self) -> None:
        with self.assertRaises(block_audit.AuditError):
            block_audit.audit_travel_negative_control(
                "OLD_A = (agency.succ -> OLD_B).\n"
            )

    def test_model_id_is_fail_closed(self) -> None:
        self.assertEqual(block_audit.parse_k("independent_k20"), 20)
        with self.assertRaises(block_audit.AuditError):
            block_audit.parse_k("travel_k20")

    def test_rejects_otf_query_census_mutation(self) -> None:
        rows = []
        for k in block_audit.EXPECTED_K:
            for method in block_audit.M8K_METHODS:
                for repetition in range(1, 6):
                    rows.append(
                        {
                            "job_id": f"independent_k{k:02d}-{method}-{repetition}",
                            "model_id": f"independent_k{k:02d}",
                            "method_id": method,
                            "process_status": "SUCCESS",
                            "revised_decision": "realizable",
                            "internal_certificate_check": "passed",
                            "link_checker": "passed",
                            "certificate_states": str(k + 1),
                            "states_discovered": str(k + 1 if method == "fg_ducs_otf" else k),
                            "successor_queries": str(k),
                        }
                    )
        target = next(row for row in rows if row["method_id"] == "fg_ducs_otf")
        target["successor_queries"] = str(int(target["successor_queries"]) + 1)
        with self.assertRaises(block_audit.AuditError):
            block_audit.audit_m8k_rows(rows)

    def test_source_bound_restricted_game_has_flat_equivalent_certificate(self) -> None:
        game = block_audit.independent_local_game("independent_k02", "a" * 64, 2)
        certificate = block_audit.synthesize(game)
        checked = block_audit.check_certificate(certificate)
        flat = block_audit.check_flat_equivalence(certificate)
        executed = block_audit.check_priority_execution(certificate)
        self.assertEqual(checked["decision"], "realizable")
        self.assertEqual(flat["state_count"], 4)
        self.assertEqual(flat["maximum_initial_rank"], 2)
        self.assertEqual(executed["complete_outcome_trace_count"], 1)

    def test_multistate_winning_all_nondeterministic_outcomes_reach_typed_load(self) -> None:
        checked = block_audit.check_certificate(self.winning_certificate)
        flat = block_audit.check_flat_equivalence(self.winning_certificate)
        executed = block_audit.check_priority_execution(self.winning_certificate)
        self.assertEqual(checked["decision"], "realizable")
        self.assertEqual(flat["state_count"], 12)
        self.assertEqual(flat["maximum_initial_rank"], 4)
        self.assertEqual(executed["complete_outcome_trace_count"], 2)
        self.assertEqual(
            {tuple(trace["load_tuple"]) for trace in executed["traces"]},
            {("image-transfer", "image-guard")},
        )

    def test_multistate_losing_cylinder_matches_flat_losing_region(self) -> None:
        checked = block_audit.check_certificate(self.losing_certificate)
        flat = block_audit.check_flat_equivalence(self.losing_certificate)
        self.assertEqual(checked["decision"], "unrealizable")
        self.assertEqual(flat["state_count"], 10)
        self.assertEqual(checked["local_losing_states"], 3)

    def test_semantic_checker_rejects_cross_block_precedence(self) -> None:
        mutated = copy.deepcopy(self.winning_certificate)
        mutated["cross_block_precedence"] = [["transfer.commit", "guard.arm"]]
        self.rehash(mutated)
        with self.assertRaises(block_audit.FactorCertificateError):
            block_audit.check_certificate(mutated)

    def test_semantic_checker_rejects_foreign_coordinate_change(self) -> None:
        mutated = copy.deepcopy(self.winning_certificate)
        mutated["composition"]["post"] = "foreign-coordinate-change"
        self.rehash(mutated)
        with self.assertRaises(block_audit.FactorCertificateError):
            block_audit.check_certificate(mutated)

    def test_semantic_checker_rejects_shared_nonstutter(self) -> None:
        mutated = copy.deepcopy(self.winning_certificate)
        mutated["composition"]["shared_action_post"] = "synchronized_nonstutter"
        self.rehash(mutated)
        with self.assertRaises(block_audit.FactorCertificateError):
            block_audit.check_certificate(mutated)

    def test_semantic_checker_rejects_goal_uncontrollable_loop(self) -> None:
        mutated = copy.deepcopy(self.winning_certificate)
        block = mutated["blocks"][0]
        block["action_annotations"]["goal-spin"] = {
            "controllability": "uncontrollable",
            "kind": "internal",
        }
        block["transitions"].append(
            {"source": "tg", "action": "goal-spin", "targets": ["tg"]}
        )
        self.rehash(mutated)
        with self.assertRaises(block_audit.FactorCertificateError):
            block_audit.check_certificate(mutated)

    def test_semantic_checker_rejects_broken_kappa(self) -> None:
        mutated = copy.deepcopy(self.winning_certificate)
        mutated["blocks"][0]["kappa"]["tg"] = "not-loadable"
        with self.assertRaises(block_audit.FactorCertificateError):
            block_audit.check_certificate(mutated)

    def test_semantic_checker_rejects_omitted_root(self) -> None:
        mutated = copy.deepcopy(self.winning_certificate)
        mutated["blocks"][0]["initial_states"] = []
        self.rehash(mutated)
        with self.assertRaises(block_audit.FactorCertificateError):
            block_audit.check_certificate(mutated)

    def test_semantic_checker_rejects_monitor_projection_drift(self) -> None:
        mutated = copy.deepcopy(self.winning_certificate)
        mutated["blocks"][0]["state_annotations"]["t1"]["monitor"] = "mi"
        self.rehash(mutated)
        with self.assertRaises(block_audit.FactorCertificateError):
            block_audit.check_certificate(mutated)

    def test_semantic_checker_rejects_rank_corruption(self) -> None:
        mutated = copy.deepcopy(self.winning_certificate)
        mutated["blocks"][0]["rank"]["t0"] += 1
        with self.assertRaises(block_audit.FactorCertificateError):
            block_audit.check_certificate(mutated)

    def test_semantic_checker_rejects_unknown_nondeterministic_outcome(self) -> None:
        mutated = copy.deepcopy(self.winning_certificate)
        mutated["blocks"][0]["transitions"][0]["targets"].append("unknown-state")
        self.rehash(mutated)
        with self.assertRaises(block_audit.FactorCertificateError):
            block_audit.check_certificate(mutated)

    def test_semantic_checker_rejects_losing_counterstrategy_omission(self) -> None:
        mutated = copy.deepcopy(self.losing_certificate)
        del mutated["blocks"][0]["losing_counterstrategy"]["r0"]
        with self.assertRaises(block_audit.FactorCertificateError):
            block_audit.check_certificate(mutated)

    def test_semantic_checker_rejects_foreign_monitor_change(self) -> None:
        mutated = copy.deepcopy(self.winning_certificate)
        mutated["blocks"][0]["monitor"]["transitions"].append(
            {"source": "mi", "action": "arm", "target": "ma"}
        )
        self.rehash(mutated)
        with self.assertRaises(block_audit.FactorCertificateError):
            block_audit.check_certificate(mutated)

    def test_semantic_checker_rejects_foreign_rs_change(self) -> None:
        mutated = copy.deepcopy(self.winning_certificate)
        mutated["blocks"][0]["rs_observer"]["transitions"].append(
            {"source": "ri", "action": "arm", "target": "ra"}
        )
        self.rehash(mutated)
        with self.assertRaises(block_audit.FactorCertificateError):
            block_audit.check_certificate(mutated)

    def test_semantic_checker_rejects_shared_stutter_monitor_change(self) -> None:
        mutated = copy.deepcopy(self.winning_certificate)
        mutated["blocks"][0]["monitor"]["transitions"].append(
            {"source": "mi", "action": "idle", "target": "ma"}
        )
        self.rehash(mutated)
        with self.assertRaises(block_audit.FactorCertificateError):
            block_audit.check_certificate(mutated)

    def test_semantic_checker_rejects_shared_stutter_rs_change(self) -> None:
        mutated = copy.deepcopy(self.winning_certificate)
        mutated["blocks"][0]["rs_observer"]["transitions"].append(
            {"source": "ri", "action": "idle", "target": "ra"}
        )
        self.rehash(mutated)
        with self.assertRaises(block_audit.FactorCertificateError):
            block_audit.check_certificate(mutated)

    def test_semantic_checker_rejects_unknown_monitor_action(self) -> None:
        mutated = copy.deepcopy(self.winning_certificate)
        mutated["blocks"][0]["monitor"]["transitions"].append(
            {"source": "mi", "action": "unknown-monitor-action", "target": "ma"}
        )
        self.rehash(mutated)
        with self.assertRaises(block_audit.FactorCertificateError):
            block_audit.check_certificate(mutated)

    def test_semantic_checker_rejects_unknown_rs_action(self) -> None:
        mutated = copy.deepcopy(self.winning_certificate)
        mutated["blocks"][0]["rs_observer"]["transitions"].append(
            {"source": "ri", "action": "unknown-rs-action", "target": "ra"}
        )
        self.rehash(mutated)
        with self.assertRaises(block_audit.FactorCertificateError):
            block_audit.check_certificate(mutated)

    def test_semantic_checker_rejects_unrelated_pending_update_drop(self) -> None:
        mutated = copy.deepcopy(self.winning_certificate)
        block = mutated["blocks"][0]
        block["action_annotations"]["silent-drop"] = {
            "controllability": "controllable", "kind": "transfer"
        }
        block["state_annotations"]["t0"]["pending_actions"].append("silent-drop")
        self.rehash(mutated)
        with self.assertRaises(block_audit.FactorCertificateError):
            block_audit.check_certificate(mutated)

    def test_semantic_checker_rejects_internal_action_pending_drop(self) -> None:
        mutated = copy.deepcopy(self.losing_certificate)
        mutated["blocks"][0]["state_annotations"]["re"]["pending_actions"] = []
        self.rehash(mutated)
        with self.assertRaises(block_audit.FactorCertificateError):
            block_audit.check_certificate(mutated)

    def test_semantic_checker_rejects_initial_pending_update_omission(self) -> None:
        mutated = copy.deepcopy(self.winning_certificate)
        mutated["blocks"][0]["action_annotations"]["latent-update"] = {
            "controllability": "controllable", "kind": "transfer"
        }
        self.rehash(mutated)
        with self.assertRaises(block_audit.FactorCertificateError):
            block_audit.check_certificate(mutated)

    def test_semantic_checker_rejects_internal_action_precedence(self) -> None:
        mutated = copy.deepcopy(self.winning_certificate)
        mutated["blocks"][1]["precedence_edges"].append(["arm", "ready"])
        self.rehash(mutated)
        with self.assertRaises(block_audit.FactorCertificateError):
            block_audit.check_certificate(mutated)

    def test_semantic_checker_rejects_uncontrollable_update_action(self) -> None:
        mutated_game = block_audit.reconstruct_game(copy.deepcopy(self.winning_certificate))
        mutated_game["blocks"][0]["action_annotations"]["prepare"]["controllability"] = "uncontrollable"
        mutated = block_audit.synthesize(mutated_game)
        with self.assertRaises(block_audit.FactorCertificateError):
            block_audit.check_certificate(mutated)


if __name__ == "__main__":
    unittest.main()
