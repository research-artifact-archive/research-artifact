#!/usr/bin/env python3

from __future__ import annotations

import copy
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "analysis"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import audit_post_frontend_generated_win_panel as AUDIT  # noqa: E402
import run_post_frontend_generated_win_panel as RUN  # noqa: E402


ZERO = "0" * 64
EVIDENCE = ROOT / "evidence/m8u-post-frontend-generated-win-panel"


def protocol_fixture() -> dict:
    files = {}
    for role, path in RUN.REGISTERED_PATHS.items():
        files[role] = {
            "path": path,
            "sha256": RUN.FIXED_REGISTERED_HASHES.get(role, ZERO),
        }
    return {
        "schema_version": RUN.PROTOCOL_SCHEMA,
        "date": "2026-08-15",
        "campaign_id": RUN.CAMPAIGN_ID,
        "denominator": copy.deepcopy(RUN.DENOMINATOR),
        "claim_boundary": copy.deepcopy(RUN.CLAIM_BOUNDARY),
        "registered_files": files,
        "runtime": {
            "observation_jar_sha256":
                RUN.RUNTIME_BINDING["observation_jar_sha256"],
            "historical_m8q_jar_sha256":
                RUN.RUNTIME_BINDING["historical_m8q_jar_sha256"],
            "facts_runner_class": RUN.FACTS_CLASS,
            "class_entries": copy.deepcopy(
                RUN.RUNTIME_BINDING["class_entries"]),
            "heap": "16g",
            "facts_timeout_seconds": 120,
            "generator_timeout_seconds": 660,
            "checker_timeout_seconds": 600,
            "audit_timeout_seconds": 1200,
            "observation_current_source_only": True,
            "historical_runtime_reproduced": False,
            "transitive_runtime_closure_frozen": False,
            "python_isolated_flags": ["-I", "-S", "-B"],
        },
        "limits": copy.deepcopy(RUN.LIMITS),
        "cases": [{
            "case_id": case_id,
            "condition": RUN.EXPECTED_CASES[case_id]["condition"],
            "cluster": RUN.EXPECTED_CASES[case_id]["cluster"],
            "definition": RUN.EXPECTED_CASES[case_id]["definition"],
            "source": {
                "path": RUN.EXPECTED_CASES[case_id]["source_path"],
                "sha256": RUN.EXPECTED_CASES[case_id]["source_sha256"],
            },
            "expected_ir": {
                "schema": RUN.IR_SCHEMA,
                "stage": RUN.IR_STAGE,
                "sha256": RUN.EXPECTED_CASES[case_id]["ir_sha256"],
                "bytes": RUN.EXPECTED_CASES[case_id]["ir_bytes"],
            },
        } for case_id in RUN.EXPECTED_CASE_ORDER],
        "scientific_input_firewall": copy.deepcopy(RUN.FIREWALL),
        "failure_taxonomy": list(RUN.FAILURE_TAXONOMY),
    }


def minimal_report(case: dict, ir: bytes) -> dict:
    result = {key: None for key in RUN.CHECK_REPORT_KEYS}
    result.update({
        "schema_version": RUN.CHECK_REPORT_SCHEMA,
        "status": RUN.CHECK_STATUS,
        "source_name": "ProductionCell_Arms=2_FG.lts",
        "source_sha256": case["source"]["sha256"],
        "definition": case["definition"],
        "ir_exact_byte_sha256": RUN.sha256_bytes(ir),
        "ir_exact_byte_size": len(ir),
        "component_partition": [[0], [1]],
        "whole_system_block": False,
        "nontrivial_factorization": True,
        "locals": [], "totals": {}, "transport": {},
        "claim_boundary": copy.deepcopy(RUN.CHECK_CLAIM_BOUNDARY),
        "semantic_digest_sha256": ZERO,
    })
    return result


def minimal_certificate(case: dict, ir: bytes) -> dict:
    return {
        "schema_version": RUN.CERTIFICATE_SCHEMA,
        "generator_boundary": copy.deepcopy(RUN.GENERATOR_BOUNDARY),
        "ir_binding": {
            "sha256": RUN.sha256_bytes(ir),
            "size": len(ir),
            "source_name": "ProductionCell_Arms=2_FG.lts",
            "source_sha256": case["source"]["sha256"],
            "definition": case["definition"],
        },
        "decision": "WIN",
        "component_partition": [[0], [1]],
        "endpoints": {},
        "locals": [],
        "transport": {},
    }


class ProtocolAndFirewallTest(unittest.TestCase):
    def test_exact_three_case_protocol_and_no_outcome_inputs(self) -> None:
        protocol = protocol_fixture()
        cases = RUN.verify_protocol(protocol, verify_files=False)
        self.assertEqual(list(RUN.EXPECTED_CASE_ORDER),
                         [row["case_id"] for row in cases])
        self.assertEqual(0, protocol["denominator"]["historical_outcome_inputs"])
        self.assertEqual(0, protocol["denominator"]["supplied_certificate_inputs"])
        self.assertEqual(850438, sum(
            row["expected_ir"]["bytes"] for row in cases))

    def test_protocol_rejects_conclusion_and_denominator_mutations(self) -> None:
        mutations = []
        extra = protocol_fixture()
        extra["cases"][0]["expected_decision"] = "WIN"
        mutations.append(extra)
        history = protocol_fixture()
        history["denominator"]["historical_outcome_inputs"] = 1
        mutations.append(history)
        supplied = protocol_fixture()
        supplied["claim_boundary"]["supplied_certificate_inputs"] = 1
        mutations.append(supplied)
        rank = protocol_fixture()
        rank["limits"]["max_rank"] = 33
        mutations.append(rank)
        order = protocol_fixture()
        order["cases"].reverse()
        mutations.append(order)
        path = protocol_fixture()
        path["registered_files"]["generator"]["path"] = (
            "evidence/forbidden-historical-outcome/summary.json")
        mutations.append(path)
        for index, value in enumerate(mutations):
            with self.subTest(index=index), self.assertRaises(RUN.CampaignError):
                RUN.verify_protocol(value, verify_files=False)

    def test_static_import_firewall_accepts_declared_split_and_rejects_crossing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            generator = root / "generator.py"
            core = root / "core.py"
            checker = root / "checker.py"
            adapter = root / "adapter.py"
            generator.write_text("import json\nimport strong_rank_certificate_core\n",
                                 encoding="utf-8")
            core.write_text("import json\n", encoding="utf-8")
            checker.write_text(
                "import json\nimport check_post_frontend_contract_certificate\n",
                encoding="utf-8")
            adapter.write_text("import json\n", encoding="utf-8")
            RUN.verify_import_firewall(generator, core, checker, adapter)

            generator.write_text(
                "import strong_rank_certificate_core\n"
                "import check_generated_post_frontend_win_certificate\n",
                encoding="utf-8")
            with self.assertRaisesRegex(RUN.CampaignError, "imports a checker"):
                RUN.verify_import_firewall(generator, core, checker)

            generator.write_text(
                "import strong_rank_certificate_core\n__import__(\"json\")\n",
                encoding="utf-8")
            with self.assertRaisesRegex(RUN.CampaignError, "dynamic"):
                RUN.verify_import_firewall(generator, core, checker)

            generator.write_text("import strong_rank_certificate_core\n",
                                 encoding="utf-8")
            adapter.write_text("import strong_rank_certificate_core\n",
                               encoding="utf-8")
            with self.assertRaisesRegex(RUN.CampaignError, "semantic adapter"):
                RUN.verify_import_firewall(generator, core, checker, adapter)

    def test_registered_generator_checker_firewall(self) -> None:
        RUN.verify_import_firewall(
            SCRIPTS / "synthesize_post_frontend_win_certificate.py",
            SCRIPTS / "strong_rank_certificate_core.py",
            SCRIPTS / "check_generated_post_frontend_win_certificate.py",
            SCRIPTS / "check_post_frontend_contract_certificate.py",
        )

    def test_generator_invalid_input_has_no_result_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ir = root / "invalid.json"
            output = root / "generated.json"
            ir.write_bytes(b'{"schema_version":"forbidden"}\n')
            completed = subprocess.run(RUN._generator_command(
                sys.executable,
                SCRIPTS / "synthesize_post_frontend_win_certificate.py",
                ir, output, RUN.LIMITS),
               cwd=root, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
               stderr=subprocess.PIPE, timeout=10, check=False)
            self.assertEqual(3, completed.returncode)
            self.assertFalse(output.exists())
            self.assertEqual(b"", completed.stdout)
            self.assertIn(b"POST_FRONTEND_WIN_SYNTHESIS_INVALID=",
                          completed.stderr)

    def test_checker_isolated_bootstrap_resolves_only_copied_adapter_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checker = root / "check_generated_post_frontend_win_certificate.py"
            adapter = root / "check_post_frontend_contract_certificate.py"
            checker.write_bytes((SCRIPTS / checker.name).read_bytes())
            adapter.write_bytes((SCRIPTS / adapter.name).read_bytes())
            ir = root / "invalid-ir.json"
            certificate = root / "invalid-certificate.json"
            output = root / "report.json"
            ir.write_bytes(b"{}\n")
            certificate.write_bytes(b"{}\n")
            completed = subprocess.run(
                RUN._isolated_module_prefix(sys.executable, checker) + [
                    "--ir", str(ir), "--certificate", str(certificate),
                    "--output", str(output),
                ], cwd=root, stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=10, check=False)
            self.assertEqual(2, completed.returncode)
            self.assertFalse(output.exists())
            self.assertIn(
                b"GENERATED_POST_FRONTEND_WIN_CERTIFICATE_INVALID=",
                completed.stdout)
            self.assertEqual(b"", completed.stderr)

    def test_jar_class_entry_hashes_are_recomputed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            jar = Path(directory) / "observation.jar"
            name = "ltsa/lts/NativePostFrontendContractFactsRunner.class"
            raw = b"synthetic-class-bytes"
            with zipfile.ZipFile(jar, "w") as archive:
                archive.writestr(name, raw)
            RUN.verify_jar_class_entries(
                jar, {name: RUN.sha256_bytes(raw)})
            with self.assertRaisesRegex(RUN.CampaignError, "hash differs"):
                RUN.verify_jar_class_entries(jar, {name: ZERO})
            with self.assertRaisesRegex(RUN.CampaignError, "census differs"):
                RUN.verify_jar_class_entries(
                    jar, {"ltsa/lts/Missing.class": ZERO})

    def test_relative_campaign_paths_are_frozen_before_child_cwds(self) -> None:
        protocol = protocol_fixture()
        case = protocol["cases"][0]
        with tempfile.TemporaryDirectory() as directory:
            caller = Path(directory)
            inputs = caller / "inputs"
            results = caller / "results"
            binaries = caller / "bin"
            inputs.mkdir()
            results.mkdir()
            binaries.mkdir()
            protocol_path = inputs / "protocol.json"
            jar = inputs / "observation.jar"
            executable = binaries / "tool"
            protocol_path.write_bytes(RUN.canonical(protocol))
            jar.write_bytes(b"synthetic-jar")
            executable.write_bytes(b"#!/bin/sh\nexit 0\n")
            executable.chmod(0o755)
            audit_script = SCRIPTS / "audit_post_frontend_generated_win_panel.py"
            observed: dict[str, Path | str] = {}

            def fake_case(_case, frozen_protocol, _protocol, _case_dir,
                          _work, frozen_jar, java, python):
                observed.update({
                    "protocol": frozen_protocol,
                    "jar": frozen_jar,
                    "java": java,
                    "python": python,
                })
                return {"case_id": _case["case_id"]}

            def fake_invoke(command, _timeout, _cwd):
                self.assertTrue(Path(command[0]).is_absolute())
                frozen_protocol = Path(
                    command[command.index("--protocol") + 1])
                frozen_evidence = Path(
                    command[command.index("--evidence") + 1])
                self.assertTrue(frozen_protocol.is_absolute())
                self.assertTrue(frozen_evidence.is_absolute())
                if "--prepublish" in command:
                    audit_path = Path(command[command.index("--output") + 1])
                    audit_path.write_bytes(RUN.canonical({"status": "PASS"}))
                    return RUN.Invocation(0, False, 1, b"", b"")
                audit_path = Path(command[command.index("--expected") + 1])
                return RUN.Invocation(
                    0, False, 1, audit_path.read_bytes(), b"")

            previous = Path.cwd()
            try:
                os.chdir(caller)
                with mock.patch.object(RUN, "verify_protocol",
                                       return_value=[case]), \
                        mock.patch.object(
                            RUN, "sha256",
                            return_value=RUN.RUNTIME_BINDING[
                                "observation_jar_sha256"]), \
                        mock.patch.object(RUN, "verify_jar_class_entries"), \
                        mock.patch.object(RUN, "registered_path",
                                          return_value=audit_script), \
                        mock.patch.object(RUN, "run_case",
                                          side_effect=fake_case), \
                        mock.patch.object(RUN, "build_summary",
                                          return_value={"records": []}), \
                        mock.patch.object(RUN, "invoke",
                                          side_effect=fake_invoke):
                    result = RUN.run(
                        Path("inputs/protocol.json"),
                        Path("inputs/observation.jar"),
                        Path("results/evidence"),
                        "bin/tool", "bin/tool")
            finally:
                os.chdir(previous)

            self.assertEqual({"records": []}, result)
            physical_caller = caller.resolve()
            self.assertEqual(physical_caller / "inputs/protocol.json",
                             observed["protocol"])
            self.assertEqual(physical_caller / "inputs/observation.jar",
                             observed["jar"])
            self.assertEqual(str(physical_caller / "bin/tool"),
                             observed["java"])
            self.assertEqual(str(physical_caller / "bin/tool"),
                             observed["python"])
            self.assertTrue((results / "evidence").is_dir())


class ClassificationSealAndCleanupTest(unittest.TestCase):
    def invocation(self, code: int, *, timeout: bool = False,
                   stderr: bytes = b"") -> RUN.Invocation:
        return RUN.Invocation(code, timeout, 1, b"", stderr)

    def test_failure_taxonomy_never_infers_loss(self) -> None:
        success = RUN.canonical({
            "schema_version": RUN.CERTIFICATE_SCHEMA, "decision": "WIN",
        })
        self.assertEqual("SUCCESS_WIN", RUN.classify_generation(
            [self.invocation(0), self.invocation(0)],
            [success, success])[0])
        for reason, expected in (
            ("ROOT_NOT_PROVED_WIN_WITHIN_RANK_BOUND", "INCONCLUSIVE_RANK_BOUND"),
            ("STATE_LIMIT", "INCONCLUSIVE_STATE_LIMIT"),
            ("CANDIDATE_BUCKET_LIMIT", "INCONCLUSIVE_BUCKET_LIMIT"),
            ("OUTCOME_LIMIT", "INCONCLUSIVE_OUTCOME_LIMIT"),
            ("TIMEOUT", "INCONCLUSIVE_TIMEOUT"),
            ("MEMORY_EXHAUSTED", "INCONCLUSIVE_OOM"),
        ):
            raw = RUN.canonical({
                "schema_version":
                    "fg-ducs-post-frontend-win-synthesis-inconclusive-v1",
                "decision": "INCONCLUSIVE", "reason": reason,
                "loss_claimed": False,
            })
            with self.subTest(reason=reason):
                marker = (
                    "POST_FRONTEND_WIN_SYNTHESIS_INCONCLUSIVE=" + reason + "\n"
                ).encode("utf-8")
                status = RUN.classify_generation(
                    [self.invocation(2, stderr=marker),
                     self.invocation(2, stderr=marker)], [raw, raw])[0]
                self.assertEqual(expected, status)
                self.assertNotIn("LOSS", status)
        oom_marker = b"POST_FRONTEND_WIN_SYNTHESIS_INCONCLUSIVE=MEMORY_EXHAUSTED\n"
        oom = RUN.classify_generation(
            [self.invocation(2, stderr=oom_marker),
             self.invocation(2, stderr=oom_marker)], [b"", b""])[0]
        self.assertEqual("INCONCLUSIVE_OOM", oom)
        malformed = RUN.classify_generation(
            [self.invocation(2, stderr=oom_marker),
             self.invocation(2, stderr=oom_marker)], [b"not-json", b"not-json"])[0]
        self.assertEqual("ERROR_CRASH", malformed)
        timeout = RUN.classify_generation(
            [self.invocation(-15, timeout=True),
             self.invocation(-15, timeout=True)], [b"", b""])[0]
        self.assertEqual("INCONCLUSIVE_TIMEOUT", timeout)

    def test_success_document_is_exact_and_bound_to_ir(self) -> None:
        case = protocol_fixture()["cases"][0]
        ir = b"synthetic-ir\n"
        certificate = minimal_certificate(case, ir)
        RUN.validate_generation_document(certificate, case, ir)
        for field, value in (("historical_outcome", "WIN"),
                             ("certificate_path", "old.json")):
            changed = copy.deepcopy(certificate)
            changed[field] = value
            with self.subTest(field=field), self.assertRaisesRegex(
                    RUN.CampaignError, "key census"):
                RUN.validate_generation_document(changed, case, ir)
        rebound = copy.deepcopy(certificate)
        rebound["ir_binding"]["sha256"] = ZERO
        with self.assertRaisesRegex(RUN.CampaignError, "IR binding"):
            RUN.validate_generation_document(rebound, case, ir)

    def test_seal_binds_both_outputs_and_excludes_checker(self) -> None:
        protocol = protocol_fixture()
        case = protocol["cases"][0]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "protocol.json"
            path.write_bytes(RUN.canonical(protocol))
            invocations = [self.invocation(0), self.invocation(0)]
            outputs = [b"certificate\n", b"certificate\n"]
            seal = RUN.build_generation_seal(
                case, path, protocol, b"ir\n", outputs, invocations,
                "SUCCESS_WIN", "GENERATED_STRONG_WIN_CERTIFICATE")
            self.assertFalse(seal["checker_started"])
            self.assertEqual("generation-seal", seal["phase_order"][-1])
            self.assertNotIn("checker_report_sha256", seal)
            self.assertEqual(RUN.sha256_bytes(outputs[0]),
                             seal["generation_output_sha256"])
            changed = RUN.build_generation_seal(
                case, path, protocol, b"ir\n", [b"changed", outputs[1]],
                invocations, "ERROR_CRASH", "NONDETERMINISTIC")
            self.assertNotEqual(RUN.canonical(seal), RUN.canonical(changed))

    def test_atomic_campaign_removes_partial_scratch_on_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            output = parent / "evidence"

            def fail(scratch: Path):
                (scratch / "partial").write_bytes(b"partial")
                raise RUN.CampaignError("synthetic failure")

            with self.assertRaisesRegex(RUN.CampaignError, "synthetic"):
                RUN.atomic_campaign(output, fail)
            self.assertFalse(output.exists())
            self.assertEqual([], list(parent.iterdir()))

    def test_fixed_evidence_census_rejects_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "cases").mkdir()
            for case_id in RUN.EXPECTED_CASE_ORDER:
                case = root / "cases" / case_id
                case.mkdir()
                for name in RUN.CASE_FILES:
                    (case / name).write_bytes(b"")
            (root / "summary.json").write_bytes(b"{}\n")
            AUDIT.verify_evidence_census(
                root, RUN.EXPECTED_CASE_ORDER, prepublish=True)
            missing = root / "cases" / RUN.EXPECTED_CASE_ORDER[0] / "record.json"
            missing.unlink()
            with self.assertRaisesRegex(AUDIT.AuditError, "census"):
                AUDIT.verify_evidence_census(
                    root, RUN.EXPECTED_CASE_ORDER, prepublish=True)


class RunnerOrderTest(unittest.TestCase):
    def test_run_case_writes_seal_before_checker_is_called(self) -> None:
        protocol = protocol_fixture()
        case = protocol["cases"][0]
        ir = b"synthetic-ir\n"
        certificate = RUN.canonical(minimal_certificate(case, ir))
        invocation = RUN.Invocation(0, False, 1, b"", b"")
        events: list[str] = []

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            protocol_path = root / "protocol.json"
            protocol_path.write_bytes(RUN.canonical(protocol))
            case_dir = root / "case"
            work = root / "work"
            work.mkdir()

            def fake_facts(_case, directory, _work, _jar, _java, _protocol):
                for prefix in ("facts", "facts-repeat"):
                    (directory / f"{prefix}.json").write_bytes(ir)
                    (directory / f"{prefix}.stdout.txt").write_bytes(b"")
                    (directory / f"{prefix}.stderr.txt").write_bytes(b"")
                receipt = invocation.receipt(ir)
                return [receipt, receipt], ir

            def fake_generators(_case, directory, _work, _python, _generator,
                                _core, _protocol, _ir):
                events.append("generators")
                for name in ("generated-output.json",
                             "generated-output-repeat.json"):
                    (directory / name).write_bytes(certificate)
                for prefix in ("generator", "generator-repeat"):
                    (directory / f"{prefix}.stdout.txt").write_bytes(b"")
                    (directory / f"{prefix}.stderr.txt").write_bytes(b"")
                receipt = invocation.receipt(certificate)
                return [receipt, receipt], [invocation, invocation], [
                    certificate, certificate]

            def fake_checker(_case, directory, _work, _python, _checker,
                             _adapter, _protocol, _ir, _certificate):
                seal = directory / "generation-seal.json"
                self.assertTrue(seal.is_file())
                self.assertFalse(RUN.load(seal)["checker_started"])
                events.append("checker")
                report = minimal_report(case, ir)
                raw = RUN.canonical(report)
                (directory / "checker-report.json").write_bytes(raw)
                (directory / "checker.stdout.txt").write_bytes(b"")
                (directory / "checker.stderr.txt").write_bytes(b"")
                return report, invocation, raw

            with mock.patch.object(RUN, "registered_path", return_value=root), \
                    mock.patch.object(RUN, "_run_facts", side_effect=fake_facts), \
                    mock.patch.object(RUN, "_run_generators",
                                      side_effect=fake_generators), \
                    mock.patch.object(RUN, "_run_checker", side_effect=fake_checker):
                record = RUN.run_case(
                    case, protocol_path, protocol, case_dir, work,
                    root, "java", sys.executable)
            self.assertEqual(["generators", "checker"], events)
            self.assertTrue(record["seal_written_before_checker"])
            self.assertEqual("SUCCESS_WIN", record["status"])
            self.assertEqual(RUN.CASE_FILES,
                             {path.name for path in case_dir.iterdir()})


@unittest.skipUnless(RUN.DEFAULT_PROTOCOL.is_file() and EVIDENCE.is_dir(),
                     "registered M8u protocol/evidence not installed yet")
class RegisteredIntegrationTest(unittest.TestCase):
    def test_registered_evidence_reaudits_exactly(self) -> None:
        observed = AUDIT.audit(RUN.DEFAULT_PROTOCOL, EVIDENCE)
        stored = RUN.load(EVIDENCE / "audit.json")
        self.assertEqual(stored, observed)
        self.assertEqual(54, observed["expected_final_evidence_files"])
        self.assertEqual(0, observed["historical_outcome_inputs"])
        self.assertEqual(0, observed["supplied_certificate_inputs"])


if __name__ == "__main__":
    unittest.main()
