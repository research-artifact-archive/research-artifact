#!/usr/bin/env python3
"""Check the saved source-inspection record against public saved evidence.

This is a record-consistency checker, NOT a general FSP parser or an independent
implementation of the serial transfer preservation proposition's UC predicates. The two local classifications
in summary.csv are source-inspection judgments, supported by exact source quotes
and explicit witnesses. This command reads files only; it runs no synthesis.
"""
import argparse
import csv
import json
from pathlib import Path
import re


def require(condition, detail):
    if not condition:
        raise ValueError(detail)


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--record-root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    root, record = args.artifact_root.resolve(), args.record_root.resolve()
    rows = read_csv(record / "summary.csv")
    sizes = read_csv(root / "results/contract-sizes/contract-sizes.csv")
    comparisons = read_csv(root / "results/ablation/tables/e1_comparison.csv")
    expected_models = {r["model"] for r in sizes}
    require(len(rows) == 9 and {r["model_id"] for r in rows} == expected_models,
            "The record must contain all nine inherited inputs exactly once")
    require(len(comparisons) == 54 and {r["target_id"] for r in comparisons} == {"base", "r1"},
            "Saved comparison denominator is not 54 Base/R1 rows")
    selected = [r for r in comparisons if r["merge"] == "transfers"]
    require(len(selected) == 18, "Expected 18 transfer-only comparisons")
    monitor_count = 0
    for row in rows:
        model = row["model_id"]
        require(row["method"] == "source_inspection", "Method must remain source_inspection")
        require(row["targets_in_saved_comparison"] == "Base;R1", "R2 must remain excluded")
        base = next(r for r in sizes if r["model"] == model and r["target"] == "base")
        require(row["components"] == base["components"] and
                row["declared_transfer_pairs"] == base["declared_transfer_pairs"],
                model + ": source-size record differs")
        for target in ("base", "r1"):
            saved = next(r for r in selected if r["model_id"] == model and r["target_id"] == target)
            require(row[target + "_fine"] == saved["original_decision"] and
                    row[target + "_transfer_merged"] == saved["decision"],
                    model + ": saved outcomes differ")
            require(not saved["validation_errors"], model + ": retained comparison reports validation errors")
        export = json.loads((root / row["public_saved_monitor_export"]).read_text())
        monitors = [r for r in export["requirements"] if r["target"] in ("base", "r1")]
        monitor_count += len(monitors)
        require(all(not any(a.startswith("reconfigure") for a in r["alphabet"]) for r in monitors),
                model + ": a saved NEW/UPD monitor observes a transfer label")
        contracts = [c for c in export["contracts"] if c["target"] in ("base", "r1")]
        require(len(contracts) == 2 and all(c["explicit_precedence_edges"] == 0 for c in contracts),
                model + ": saved Base/R1 precedence differs")
    quoted = 0
    for line in (record / "raw/stdout.txt").read_text().splitlines():
        match = re.fullmatch(r"(tool/models/[^:]+):(\d+): (.*)", line)
        if match:
            path, number, content = match.groups()
            actual = (root / path).read_text().splitlines()[int(number) - 1]
            require(actual == content, path + ": quoted source line differs: " + number)
            quoted += 1
    require(quoted > 300, "Expected the complete retained local source excerpts")
    require(monitor_count == 138, "Expected 138 Base/R1 NEW/UPD monitor occurrences")
    positives = [r for r in rows if r["base_r1_transfer_only_full_premises"] == "SATISFIED_BY_SOURCE_INSPECTION"]
    require(len(positives) == 6, "Expected six positive source-inspection families")
    decisions = [(r[t + "_fine"], r[t + "_transfer_merged"]) for r in positives for t in ("base", "r1")]
    require(decisions.count(("WIN", "WIN")) == 11 and decisions.count(("LOSS", "LOSS")) == 1,
            "Positive subset must retain eleven WIN/WIN and one LOSS/LOSS")
    print("PASS: nine source-inspection rows match saved counts and all 18 transfer-only outcomes.")
    print("PASS: 138 Base/R1 NEW/UPD monitor occurrences omit transfer labels; all 18 precedence counts are zero.")
    print("PASS: " + str(quoted) + " exact local-source lines match the public inputs.")
    print("SCOPE: local UC judgments remain source inspection, not an independently executed FSP semantics check.")
    print("SCOPE: serial transfer preservation proposition is merged WIN => fine WIN; 12/18 satisfy its source-inspected premises (11 WIN/WIN, Industry/R1 LOSS/LOSS).")
    print("SCOPE: six transfer-only comparisons fail a local UC premise; 36 boundary/both comparisons and R2 full applicability are excluded.")


if __name__ == "__main__":
    main()
