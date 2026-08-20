#!/usr/bin/env python3

from __future__ import annotations

import ast
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "analysis"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import check_productioncell_source_contract_certificate as CHECK  # noqa: E402


SOURCE = ROOT / "Implementation/Experiment/Models/ProductionCell_Arms=2_FG.lts"
BASE = ROOT / (
    "evidence/m8s-post-frontend-contract-certificate/cases/"
    "productioncell-arms2-base-productioncell-arms-2-fg/facts.json"
)
R2 = ROOT / (
    "evidence/m8s-post-frontend-contract-certificate/cases/"
    "productioncell-arms2-r2-productioncell-arms-2-fg/facts.json"
)

SOURCE_SHA256 = "117210fa93185f5a814ad7debbdfcde00720019312c4ef68446a844700084e43"
BASE_FACTS_SHA256 = "a585319ee85d1bd4f21b402c2c9c671b8def43f20a1309c92a6b424a9e74dfd8"
R2_FACTS_SHA256 = "29d701d7cfac3d5c8458043e6d773aa0df4d7234cea3639578aa43382d4f18f3"
BASE_SEMANTIC_SHA256 = "3473643ab4c63ab82a9a05a505c6e8ab47428ae2b62166a8f7814398490661b2"
R2_SEMANTIC_SHA256 = "fdfd4033e3c2421e4a3524e9cf5373d87f7aad5b718e7e9880eb57aab4920ac2"
CONTROLLER_PAIR_SHA256 = "d36b6011661ea5dd3496cb0f086a5de99c494cbb8def8eaf1522e3a7e0c9bd73"
BASE_CLI_REPORT_SHA256 = "017f318ca0b8a8978101100f857ab8eeef5354c3fd20689926a82c5892867211"
R2_CLI_REPORT_SHA256 = "2c0576ca23be2a2d12b2b18d2ec14eb22f4ca16fb2f4e2c2e584b25ed6bbb75e"


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise AssertionError("fixture root is not an object")
    return value


def bridge(raw: bytes, definition: str, facts: dict) -> dict:
    parsed = CHECK.parse_source(raw)
    derived = CHECK.derive_source_contract(parsed, definition)
    return CHECK.compare_ir(parsed, derived, facts)


def rebound(raw: bytes, facts: dict) -> dict:
    value = copy.deepcopy(facts)
    value["source_sha256"] = hashlib.sha256(raw).hexdigest()
    return value


class ProductionCellSourceContractCertificateTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = SOURCE.read_bytes()
        cls.base = load(BASE)
        cls.r2 = load(R2)

    def semantic_mutation(self, old: str, new: str, *, expected_count: int = 1,
                          replace_count: int = 1,
                          definition: str = "UpdCont_OTF_FG",
                          facts: dict | None = None) -> None:
        text = self.raw.decode("utf-8")
        self.assertEqual(text.count(old), expected_count)
        mutated = text.replace(old, new, replace_count).encode("utf-8")
        with self.assertRaises(CHECK.SourceContractError):
            bridge(mutated, definition, rebound(mutated, facts or self.base))

    def test_source_only_derivation_precedes_any_facts_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source_path = Path(directory) / "ProductionCell_Arms=2_FG.lts"
            source_path.write_bytes(self.raw)
            parsed = CHECK.parse_source(source_path.read_bytes())
            base = CHECK.derive_source_contract(parsed, "UpdCont_OTF_FG")
            r2 = CHECK.derive_source_contract(parsed, "UpdCont_OTF_FG_R2")
        self.assertEqual(len(base.old_controller.states), 81)
        self.assertEqual(len(base.old_controller.post), 216)
        self.assertEqual(len(base.new_controller.states), 81)
        self.assertEqual(len(base.new_controller.post), 216)
        self.assertIs(base.selected, parsed.updating["UpdCont_OTF_FG"])
        self.assertEqual(len(r2.selected["transition"]), 24)

    def test_base_and_r2_bind_every_source_sensitive_ir_layer(self) -> None:
        reports = (
            bridge(self.raw, "UpdCont_OTF_FG", self.base),
            bridge(self.raw, "UpdCont_OTF_FG_R2", self.r2),
        )
        self.assertEqual([report["census"]["transition_requirement_machines"]
                          for report in reports], [0, 24])
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(), SOURCE_SHA256)
        self.assertEqual(hashlib.sha256(BASE.read_bytes()).hexdigest(),
                         BASE_FACTS_SHA256)
        self.assertEqual(hashlib.sha256(R2.read_bytes()).hexdigest(),
                         R2_FACTS_SHA256)
        self.assertEqual([report["source_semantic_digest"] for report in reports],
                         [BASE_SEMANTIC_SHA256, R2_SEMANTIC_SHA256])
        self.assertEqual({report["controller_pair_semantic_digest"]
                          for report in reports}, {CONTROLLER_PAIR_SHA256})
        for report in reports:
            self.assertEqual(
                report["status"],
                "SOURCE_TO_POST_FRONTEND_CONTRACT_SEMANTICS_VERIFIED",
            )
            self.assertEqual(report["census"]["components"], 2)
            self.assertEqual(report["census"]["old_controller_states"], 81)
            self.assertEqual(report["census"]["old_controller_edges"], 216)
            self.assertEqual(report["census"]["new_controller_states"], 81)
            self.assertEqual(report["census"]["new_controller_edges"], 216)
            self.assertEqual(report["census"]["old_safety_machines"], 12)
            self.assertEqual(report["census"]["new_safety_machines"], 12)
            self.assertEqual(report["census"]["observers"], 22)
            self.assertEqual(report["census"]["activation_rows"], 152)
            self.assertEqual(report["census"]["activation_error_rows"], 82)
            self.assertEqual(report["census"]["progress_actions"], 26)
            self.assertTrue(report["independent_old_new_controller_synthesis"])
            self.assertFalse(report["independent_win_synthesis"])
            self.assertFalse(report["source_to_win_replay"])

    def test_comment_and_whitespace_change_is_semantically_accepted(self) -> None:
        mutated = ("// source-byte mutation used by the independent bridge\n\n"
                   + self.raw.decode("utf-8").replace(
                       "const N = 2", "const   N   =   2", 1)).encode("utf-8")
        report = bridge(mutated, "UpdCont_OTF_FG", rebound(mutated, self.base))
        baseline = bridge(self.raw, "UpdCont_OTF_FG", self.base)
        self.assertNotEqual(report["source_sha256"], baseline["source_sha256"])
        self.assertEqual(report["source_semantic_digest"],
                         baseline["source_semantic_digest"])

    def test_semantic_reordering_and_state_renaming_are_accepted(self) -> None:
        text = self.raw.decode("utf-8")
        old_arm = (
            "ARM = ( polish[I] -> POLISHED[1]\n"
            "| drill[I] -> DRILLED[1]"
        )
        reordered_arm = (
            "ARM = ( drill[I] -> DRILLED[1]\n"
            "| polish[I] -> POLISHED[1]"
        )
        old_safety = (
            "safety = {\nP_OLD_TOOL_ORDER_1, P_OLD_OUT_IF_FINISHED_1,"
        )
        reordered_safety = (
            "safety = {\nP_OLD_OUT_IF_FINISHED_1, P_OLD_TOOL_ORDER_1,"
        )
        self.assertEqual(text.count(old_arm), 1)
        self.assertEqual(text.count(old_safety), 1)
        first_transfer = (
            "PRODUCTION_CELL_OLD@PRODUCTION_CELL_OLD(1) = "
            "reconfigure_PRODUCTION_CELL_1 -> "
            "PRODUCTION_CELL_NEW@PRODUCTION_CELL_NEW(1),\n"
        )
        second_transfer = (
            "ARM@PRODUCTION_CELL_OLD(1) = reconfigure_PRODUCTION_CELL_1 -> "
            "ARM@PRODUCTION_CELL_NEW(1),\n"
        )
        self.assertEqual(text.count(first_transfer), 1)
        self.assertEqual(text.count(second_transfer), 1)
        reordered_transfer = text.replace(
            first_transfer + second_transfer,
            second_transfer + first_transfer,
            1,
        )
        variants = (
            text.replace(old_arm, reordered_arm, 1),
            text.replace(old_safety, reordered_safety, 1),
            text.replace("TRASHED", "SCRAPPED"),
            reordered_transfer,
            text + ("\nassert UNUSED_A = UNUSED_B\n"
                    "assert UNUSED_B = (!stamp[1])\n"),
        )
        baseline = bridge(self.raw, "UpdCont_OTF_FG", self.base)
        for index, value in enumerate(variants):
            with self.subTest(index=index):
                raw = value.encode("utf-8")
                report = bridge(raw, "UpdCont_OTF_FG", rebound(raw, self.base))
                self.assertEqual(report["source_semantic_digest"],
                                 baseline["source_semantic_digest"])
                self.assertEqual(report["controller_pair_semantic_digest"],
                                 baseline["controller_pair_semantic_digest"])

    def test_component_transfer_fluent_and_formula_mutations_are_rejected(self) -> None:
        mutations = (
            ("| stamp[I] -> TRASHED\n| out[I] -> OUT),",
             "| stamp[I] -> OUT\n| out[I] -> OUT),"),
            ("POLISHED[k]@PRODUCTION_CELL_OLD(1) = reconfigure_PRODUCTION_CELL_1 -> ARM@PRODUCTION_CELL_NEW(1)",
             "POLISHED[k]@PRODUCTION_CELL_OLD(1) = reconfigure_PRODUCTION_CELL_1 -> PAINTED[k]@PRODUCTION_CELL_NEW(1)"),
            ("fluent CleanPending[i:Arms] = <clean[i],{cleanOk[i],cleanNOk[i]}>",
             "fluent CleanPending[i:Arms] = <clean[i],cleanOk[i]>") ,
            ("assert OLD_TOOL_ORDER_1 = ((CleanPending[1] -> Polished[1]) && (PolishPending[1] -> Drilled[1]))",
             "assert OLD_TOOL_ORDER_1 = ((CleanPending[1] -> Polished[1]) || (PolishPending[1] -> Drilled[1]))"),
        )
        for index, (old, new) in enumerate(mutations):
            with self.subTest(index=index):
                self.semantic_mutation(
                    old, new,
                    expected_count=2 if index == 0 else 1,
                )

    def test_environment_controller_and_selected_r2_mutations_are_rejected(self) -> None:
        self.semantic_mutation(
            "controller ||C_DRILL_POLISH_CLEAN = (OLD_ENV)~{DRILL_POLISH_CLEAN}.",
            "controller ||C_DRILL_POLISH_CLEAN = (NEW_ENV)~{DRILL_POLISH_CLEAN}.",
        )
        text = self.raw.decode("utf-8")
        start = text.index("updatingController UpdCont_OTF_FG_R2 = {")
        end = text.index("\n}", start)
        block = text[start:end]
        transition = "transition = R2_StopOldSpec_P_OLD_TOOL_ORDER_1,\n"
        self.assertEqual(block.count(transition), 1)
        mutated = (text[:start] + block.replace(transition, "", 1)
                   + text[end:]).encode("utf-8")
        with self.assertRaises(CHECK.SourceContractError):
            bridge(mutated, "UpdCont_OTF_FG_R2", rebound(mutated, self.r2))
        self.semantic_mutation(
            "nonblocking,\nrevised_on_the_fly,\nfine_grained\n}\n||UPDATE_CONTROLLER_OTF_FG_R2",
            "nonblocking,\non_the_fly,\nfine_grained\n}\n||UPDATE_CONTROLLER_OTF_FG_R2",
            definition="UpdCont_OTF_FG_R2",
            facts=self.r2,
        )

    def test_unknown_duplicate_and_unterminated_source_are_rejected(self) -> None:
        variants = (
            self.raw + b"\nunknownDeclaration X = Y\n",
            self.raw + b"\nconst N = 2\n",
            b"/*" + self.raw,
        )
        for index, raw in enumerate(variants):
            with self.subTest(index=index):
                with self.assertRaises(CHECK.SourceContractError):
                    CHECK.parse_source(raw)

    def test_mtsa_invalid_map_and_trailing_set_syntax_are_rejected(self) -> None:
        text = self.raw.decode("utf-8")
        map_row = (
            "map MAP_PRODUCTION_CELL_1 = {PRODUCTION_CELL_OLD(1), "
            "PRODUCTION_CELL_NEW(1), R_PRODUCTION_CELL(1)}"
        )
        variants = (
            text.replace(map_row,
                         "map MAP_PRODUCTION_CELL_1 = {this is not FSP !!!}", 1),
            text + "\n" + map_row + "\n",
            text.replace("out[Arms]/*,", "out[Arms],/*,", 1),
            text.replace("const N = 2", "const\u2003N = 2", 1),
        )
        for index, value in enumerate(variants):
            with self.subTest(index=index):
                with self.assertRaises(CHECK.SourceContractError):
                    CHECK.parse_source(value.encode("utf-8"))

    def test_duplicate_ir_keys_and_nonfinite_json_are_rejected(self) -> None:
        raw = BASE.read_bytes()
        root_duplicate = raw.replace(
            b"{", b'{"schema_version":"ATTACKER_VALUE",', 1)
        nested_duplicate = raw.replace(
            b'"flags":{', b'"flags":{"fine_grained":false,', 1)
        nonfinite = raw.replace(b'"index":0', b'"index":NaN', 1)
        for index, mutated in enumerate(
                (root_duplicate, nested_duplicate, nonfinite)):
            with self.subTest(index=index):
                with self.assertRaises(CHECK.SourceContractError):
                    CHECK.strict_json_bytes(mutated)

    def test_formula_namespace_and_relation_state_errors_are_fail_closed(self) -> None:
        text = self.raw.decode("utf-8")
        formula_variants = (
            text + "\nltl_property OLD_TOOL_ORDER_1 = [](!stamp[1])\n",
            text + "\nassert P_OLD_TOOL_ORDER_1 = (!stamp[1])\n",
            text + "\nassert UNUSED_UNKNOWN = UnknownThing\n",
            text + "\nltl_property UNUSED_UNKNOWN_P = []UnknownThing\n",
            text + "\nassert UNUSED_PROPERTY_REF = P_OLD_TOOL_ORDER_1\n",
            text + "\nltl_property UNUSED_PROPERTY_REF = []P_OLD_TOOL_ORDER_1\n",
            text + "\nassert UNUSED_CYCLE = UNUSED_CYCLE\n",
            text + ("\nassert UNUSED_CYCLE_A = UNUSED_CYCLE_B\n"
                    "assert UNUSED_CYCLE_B = UNUSED_CYCLE_A\n"),
        )
        for index, value in enumerate(formula_variants):
            with self.subTest(index=index):
                with self.assertRaises(CHECK.SourceContractError):
                    CHECK.parse_source(value.encode("utf-8"))

        old = (
            "ARM@PRODUCTION_CELL_OLD(1) = reconfigure_PRODUCTION_CELL_1 -> "
            "ARM@PRODUCTION_CELL_NEW(1)"
        )
        new = old.replace("ARM@PRODUCTION_CELL_OLD", "MISSING@PRODUCTION_CELL_OLD", 1)
        self.assertEqual(text.count(old), 1)
        mutated = text.replace(old, new, 1).encode("utf-8")
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.lts"
            facts = Path(directory) / "facts.json"
            output = Path(directory) / "output.json"
            source.write_bytes(mutated)
            facts.write_bytes(CHECK.canonical_bytes(rebound(mutated, self.base)))
            self.assertEqual(CHECK.main([
                "--source", str(source), "--definition", "UpdCont_OTF_FG",
                "--ir", str(facts), "--output", str(output),
            ]), 2)
            self.assertFalse(output.exists())

    def test_guard_grouped_outcome_and_source_controllability_mutations_reject(self) -> None:
        mutations = (
            ("when(k==K) {drillOk[I],drillNOk[I]} -> ARM",
             "when(k<K) {drillOk[I],drillNOk[I]} -> ARM"),
            ("{drillOk[I],drillNOk[I]} -> ARM",
             "{drillOk[I],polishNOk[I]} -> ARM"),
            ("stamp[Arms], out[Arms]/*,",
             "stamp[Arms]/*,"),
        )
        for index, (old, new) in enumerate(mutations):
            with self.subTest(index=index):
                self.semantic_mutation(old, new, expected_count=2)

    def test_controller_component_transfer_and_tester_fact_mutations_are_rejected(self) -> None:
        mutations = []
        controller = copy.deepcopy(self.base)
        controller["controllers"]["old"]["required_transitions"][0]["targets"] = [80]
        mutations.append(controller)
        component = copy.deepcopy(self.base)
        component["components"][0]["old_machine"]["transitions"][0]["targets"] = [2]
        mutations.append(component)
        transfer = copy.deepcopy(self.base)
        transfer["components"][0]["transfer_relation"][3]["targets"] = [3]
        mutations.append(transfer)
        tester = copy.deepcopy(self.base)
        tester["old_safety_machines"][0]["transitions"][0]["targets"] = [0]
        mutations.append(tester)
        r2_tester = copy.deepcopy(self.r2)
        r2_tester["transition_requirement_machines"][0]["transitions"][0]["targets"] = [1]
        for index, (definition, facts) in enumerate(
                [("UpdCont_OTF_FG", item) for item in mutations]
                + [("UpdCont_OTF_FG_R2", r2_tester)]):
            with self.subTest(index=index):
                with self.assertRaises(CHECK.SourceContractError):
                    bridge(self.raw, definition, facts)

    def test_observer_activation_protocol_controllability_and_flag_mutations_are_rejected(self) -> None:
        mutations = []
        observer = copy.deepcopy(self.base)
        observer["observer_machines"][0]["transitions"][0]["targets"] = [1]
        observer["observer_registry"][0]["machine"] = copy.deepcopy(
            observer["observer_machines"][0])
        mutations.append(observer)
        activation = copy.deepcopy(self.base)
        activation["new_activation_sources"][0]["mapping_rows"][0]["tester_state"] = 1
        mutations.append(activation)
        protocol = copy.deepcopy(self.base)
        protocol["protocol"]["progress_actions_in_index_order"].remove(
            "reconfigure_PRODUCTION_CELL_1")
        mutations.append(protocol)
        control = copy.deepcopy(self.base)
        control["controllable_actions"].remove("out.1")
        mutations.append(control)
        flags = copy.deepcopy(self.base)
        flags["flags"]["revised_on_the_fly"] = False
        mutations.append(flags)
        for index, facts in enumerate(mutations):
            with self.subTest(index=index):
                with self.assertRaises(CHECK.SourceContractError):
                    bridge(self.raw, "UpdCont_OTF_FG", facts)

    def test_cli_is_deterministic_and_derives_before_opening_ir(self) -> None:
        original_read = Path.read_bytes
        derived = False
        original_derive = CHECK.derive_source_contract

        def traced_derive(*args, **kwargs):
            nonlocal derived
            value = original_derive(*args, **kwargs)
            derived = True
            return value

        def traced_read(path: Path) -> bytes:
            if path == BASE:
                self.assertTrue(derived, "IR was opened before source derivation")
            return original_read(path)

        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.json"
            second = Path(directory) / "second.json"
            with mock.patch.object(CHECK, "derive_source_contract", traced_derive), \
                    mock.patch.object(Path, "read_bytes", traced_read):
                self.assertEqual(CHECK.main([
                    "--source", str(SOURCE), "--definition", "UpdCont_OTF_FG",
                    "--ir", str(BASE), "--output", str(first),
                ]), 0)
            self.assertEqual(CHECK.main([
                "--source", str(SOURCE), "--definition", "UpdCont_OTF_FG",
                "--ir", str(BASE), "--output", str(second),
            ]), 0)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(hashlib.sha256(first.read_bytes()).hexdigest(),
                             BASE_CLI_REPORT_SHA256)
            r2_output = Path(directory) / "r2.json"
            self.assertEqual(CHECK.main([
                "--source", str(SOURCE), "--definition", "UpdCont_OTF_FG_R2",
                "--ir", str(R2), "--output", str(r2_output),
            ]), 0)
            self.assertEqual(hashlib.sha256(r2_output.read_bytes()).hexdigest(),
                             R2_CLI_REPORT_SHA256)

    def test_checker_import_and_dynamic_execution_firewall(self) -> None:
        script = Path(CHECK.__file__).resolve()
        tree = ast.parse(script.read_text(encoding="utf-8"), filename=str(script))
        allowed = {
            "__future__", "argparse", "hashlib", "itertools", "json", "re",
            "sys", "collections", "dataclasses", "pathlib", "typing",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.assertTrue(all(alias.name.split(".")[0] in allowed
                                    for alias in node.names))
            elif isinstance(node, ast.ImportFrom):
                self.assertIn((node.module or "").split(".")[0], allowed)
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                self.assertNotIn(node.func.id,
                                 {"eval", "exec", "compile", "__import__"})


if __name__ == "__main__":
    unittest.main()
