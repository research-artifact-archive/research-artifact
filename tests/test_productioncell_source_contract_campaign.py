#!/usr/bin/env python3

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "analysis"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from audit_productioncell_source_contract_certificate import (  # noqa: E402
    _record_check, audit, verify_evidence_census,
)
from run_productioncell_source_contract_certificate import (  # noqa: E402
    CLAIM_BOUNDARY, CampaignError, load, sha256, validate_chain,
    validate_downstream_report, validate_source_report, verify_protocol,
)


PROTOCOL = ROOT / "protocols/productioncell_source_contract_certificate_v1_20260814.json"
EVIDENCE = ROOT / "evidence/m8t-productioncell-source-contract-certificate"


class ProductionCellSourceContractCampaignTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.protocol = load(PROTOCOL)
        cls.cases = verify_protocol(cls.protocol)

    def reports(self, case: dict) -> tuple[dict, bytes, dict, bytes]:
        root = EVIDENCE / "cases" / case["case_id"]
        source_path = root / "source-report.json"
        downstream_path = root / "downstream-report.json"
        return (load(source_path), source_path.read_bytes(),
                load(downstream_path), downstream_path.read_bytes())

    def test_registered_audit_recomputes_exactly(self) -> None:
        observed = audit(PROTOCOL, EVIDENCE)
        stored = load(EVIDENCE / "audit.json")
        self.assertEqual(observed, stored)
        self.assertEqual(
            observed["source_to_supplied_certificate_semantic_verification"], 2)
        self.assertEqual(observed["unique_independent_controller_pairs"], 1)
        self.assertEqual(observed["unique_source_semantic_contracts"], 2)
        self.assertEqual(observed["source_census"]["activation_error_rows"], 164)
        self.assertEqual(
            observed["supplied_certificate_census"]["candidate_buckets"], 4774)
        self.assertEqual(observed["independent_win_synthesis"], 0)
        self.assertEqual(observed["source_to_win_replay"], 0)

    def test_protocol_derives_one_source_cluster_and_controller_pair(self) -> None:
        self.assertEqual(self.protocol["claim_boundary"], CLAIM_BOUNDARY)
        self.assertEqual(len({
            (case["source"]["path"], case["source"]["sha256"])
            for case in self.cases
        }), 1)
        pairs = set()
        semantics = set()
        for case in self.cases:
            source, source_raw, downstream, downstream_raw = self.reports(case)
            validate_source_report(case, source, source_raw)
            validate_downstream_report(case, downstream, downstream_raw)
            validate_chain(case, source, downstream)
            pairs.add(source["controller_pair_semantic_digest"])
            semantics.add(source["source_semantic_digest"])
        self.assertEqual(len(pairs), 1)
        self.assertEqual(len(semantics), 2)

    def test_claim_denominator_route_and_registered_hash_mutations_reject(self) -> None:
        mutations = []
        claim = copy.deepcopy(self.protocol)
        claim["claim_boundary"]["independent_win_synthesis"] = True
        mutations.append(claim)
        denominator = copy.deepcopy(self.protocol)
        denominator["denominator"]["source_files"] = 2
        mutations.append(denominator)
        route = copy.deepcopy(self.protocol)
        route["cases"][0]["definition"] = "UpdCont_OTF_FG_R2"
        mutations.append(route)
        digest = copy.deepcopy(self.protocol)
        digest["cases"][0]["facts"]["sha256"] = "0" * 64
        mutations.append(digest)
        registered = copy.deepcopy(self.protocol)
        registered["registered_files"]["source_checker"]["sha256"] = "0" * 64
        mutations.append(registered)
        for index, value in enumerate(mutations):
            with self.subTest(index=index):
                with self.assertRaises(CampaignError):
                    verify_protocol(value)

    def test_source_facts_and_downstream_chain_mutations_reject(self) -> None:
        case = self.cases[0]
        source, source_raw, downstream, downstream_raw = self.reports(case)

        source_mutations = []
        facts = copy.deepcopy(source)
        facts["ir_sha256"] = "0" * 64
        source_mutations.append(facts)
        controller = copy.deepcopy(source)
        controller["controller_pair_semantic_digest"] = "0" * 64
        source_mutations.append(controller)
        boundary = copy.deepcopy(source)
        boundary["independent_win_synthesis"] = True
        source_mutations.append(boundary)
        for index, value in enumerate(source_mutations):
            with self.subTest(source=index):
                with self.assertRaises(CampaignError):
                    validate_source_report(case, value, source_raw)

        downstream_mutations = []
        status = copy.deepcopy(downstream)
        status["status"] = "LOSS"
        downstream_mutations.append(status)
        win = copy.deepcopy(downstream)
        win["independent_win_synthesis"] = True
        downstream_mutations.append(win)
        for index, value in enumerate(downstream_mutations):
            with self.subTest(downstream=index):
                with self.assertRaises(CampaignError):
                    validate_downstream_report(case, value, downstream_raw)

        crossed = copy.deepcopy(source)
        crossed["definition"] = self.cases[1]["definition"]
        with self.assertRaises(CampaignError):
            validate_chain(case, crossed, downstream)

    def test_m8s_facts_and_reports_are_reused_byte_exactly(self) -> None:
        for case in self.cases:
            with self.subTest(case=case["case_id"]):
                record = load(EVIDENCE / "cases" / case["case_id"] / "record.json")
                self.assertEqual(record["facts_sha256"], case["facts"]["sha256"])
                self.assertEqual(record["downstream_report_sha256"],
                                 case["m8s_report"]["sha256"])
                self.assertEqual(
                    sha256(ROOT / case["m8s_report"]["path"]),
                    case["m8s_report"]["sha256"],
                )
                self.assertFalse(record["independent_win_synthesis"])
                self.assertFalse(record["source_to_win_replay"])

    def test_record_paths_digests_logs_and_evidence_census_are_exact(self) -> None:
        case = self.cases[0]
        source, source_raw, _downstream, downstream_raw = self.reports(case)
        case_root = EVIDENCE / "cases" / case["case_id"]
        record = load(case_root / "record.json")
        _record_check(case, record, source, source_raw, downstream_raw, case_root)

        mutations = []
        extra = copy.deepcopy(record)
        extra["unexpected"] = True
        mutations.append(extra)
        for field in ("source_path", "facts_path", "source_report_path",
                      "source_semantic_digest", "controller_pair_semantic_digest"):
            value = copy.deepcopy(record)
            value[field] = "0" * 64 if field.endswith("digest") else "forged/path"
            mutations.append(value)
        for index, value in enumerate(mutations):
            with self.subTest(record=index):
                with self.assertRaises(CampaignError):
                    _record_check(case, value, source, source_raw,
                                  downstream_raw, case_root)

        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            for prefix in ("source-checker", "downstream-checker"):
                for stream in ("stdout", "stderr"):
                    (temporary / f"{prefix}.{stream}.txt").write_bytes(b"")
            _record_check(case, record, source, source_raw,
                          downstream_raw, temporary)
            (temporary / "source-checker.stderr.txt").write_bytes(b"unexpected")
            with self.assertRaises(CampaignError):
                _record_check(case, record, source, source_raw,
                              downstream_raw, temporary)

        verify_evidence_census(EVIDENCE,
                               [item["case_id"] for item in self.cases])
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            (temporary / "summary.json").write_bytes(b"{}")
            for item in self.cases:
                root = temporary / "cases" / item["case_id"]
                root.mkdir(parents=True)
                for name in (
                    "source-report.json", "downstream-report.json", "record.json",
                    "source-checker.stdout.txt", "source-checker.stderr.txt",
                    "downstream-checker.stdout.txt", "downstream-checker.stderr.txt",
                ):
                    (root / name).write_bytes(b"")
            verify_evidence_census(
                temporary, [item["case_id"] for item in self.cases])
            with tempfile.TemporaryDirectory() as parent:
                alias = Path(parent) / "evidence-alias"
                alias.symlink_to(temporary, target_is_directory=True)
                with self.assertRaises(CampaignError):
                    verify_evidence_census(
                        alias, [item["case_id"] for item in self.cases])
            (temporary / "unexpected.txt").write_bytes(b"")
            with self.assertRaises(CampaignError):
                verify_evidence_census(
                    temporary, [item["case_id"] for item in self.cases])

    def test_protocol_and_stored_json_are_canonical(self) -> None:
        # The human-authored protocol is strict JSON but intentionally pretty
        # printed.  Machine-produced evidence is canonical byte-for-byte.
        paths = [EVIDENCE / "summary.json", EVIDENCE / "audit.json"]
        for case in self.cases:
            root = EVIDENCE / "cases" / case["case_id"]
            paths.extend((root / "source-report.json",
                          root / "downstream-report.json", root / "record.json"))
        for path in paths:
            with self.subTest(path=path.name):
                value = json.loads(path.read_text(encoding="utf-8"))
                expected = (json.dumps(value, sort_keys=True,
                                       separators=(",", ":"), ensure_ascii=False)
                            + "\n").encode("utf-8")
                self.assertEqual(path.read_bytes(), expected)


if __name__ == "__main__":
    unittest.main()
