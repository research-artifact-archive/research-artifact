#!/usr/bin/env python3
"""Aggregate preserved E6 comparisons for the paper; never run a solver.

Run from paper/source: python3 -B scripts/generate_rq2_family_table.py --check
Default mode writes only figures/rq2_family_counts.tex and build/table_source_check.json.
--emit-patch emits those two generated files as an apply_patch-compatible patch.
The source index, population definitions and existing macros remain read-only.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import re

from public_evidence import E6, artifact_root


PAPER = Path(__file__).resolve().parents[1]
TABLE = PAPER / "figures/rq2_family_counts.tex"
REPORT = PAPER / "build/table_source_check.json"
MAIN_POPULATIONS = {"core", "operational_control", "application_plant_attempt"}
CLASSES = ("witness", "both_loss", "both_win", "incomplete")
FAMILIES = ("Rolling", "Canary", "Policy", "DB-Rolling", "Rolling+Audit", "Threads", "PC2-Rolling")
ALL_FAMILIES = (*FAMILIES, "Cell_n")
LABELS = {"Threads": "Threads (control)", "Cell_n": r"Cell$_n$ (reference)"}
EXPECTED_THREADS = Counter({"both_win": 10, "both_loss": 10})
TOTAL_MACROS = {
    "pairs": "VThreeESixMainPairs",
    "witness": "VThreeESixWitness",
    "both_loss": "VThreeESixBothLoss",
    "both_win": "VThreeESixBothWin",
    "incomplete": "VThreeESixIncomplete",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def macro_values(path):
    return dict(re.findall(r"\\newcommand\{\\([A-Za-z]+)\}\{([^{}]*)\}", path.read_text()))


def classify(row):
    pair = (row["fine_decision"], row["merged_decision"])
    known = {("WIN", "LOSS"): "witness", ("LOSS", "LOSS"): "both_loss", ("WIN", "WIN"): "both_win"}
    if pair in known:
        return known[pair]
    require(any(value not in {"WIN", "LOSS"} for value in pair), "Unexpected completed decision pair: " + str(pair))
    return "incomplete"


def counts(rows):
    counter = Counter(row["class"] for row in rows)
    require(not (set(counter) - set(CLASSES)), "Unexpected comparison class")
    return {"pairs": len(rows), **{name: counter[name] for name in CLASSES}}


def parameter_domains(main, reference, threads_readme):
    """Compact domains are exact summaries of the preserved parameter tuples."""
    require(re.search(r"queue\s+capacity\s+B\s*=\s*1,\s*2", threads_readme.read_text()),
            "Threads source no longer identifies B as queue capacity 1,2")
    domains = {}

    def tuples(family, keys):
        rows = reference if family == "Cell_n" else [r for r in main if r["family"] == family]
        mode = "boundaries" if family == "Policy" else "transfers"
        require(all(row["comparison"] == mode for row in rows), "Comparison mode changed: " + family)
        parsed = [dict(item.split("=", 1) for item in row["params"].split(";")) for row in rows]
        require(all(set(row) == set(keys) for row in parsed), "Parameter keys changed: " + family)
        values = {tuple(row[key] if key == "regime" else int(row[key]) for key in keys) for row in parsed}
        require(len(values) == len(rows), "Duplicate parameter tuple: " + family)
        domains[family] = {"keys": list(keys), "tuples": [list(v) for v in sorted(values)], "comparison": mode}
        return values

    def span(values):
        values = sorted(set(values))
        require(values == list(range(values[0], values[-1] + 1)), "A displayed range contains untested values")
        return str(values[0]) if len(values) == 1 else str(values[0]) + r"\ldots" + str(values[-1])

    for family in ("Rolling", "Canary"):
        values = tuples(family, ("n", "m"))
        ns = {n for n, _ in values}
        require(values == {(n, m) for n in ns for m in range(1, n)}, "Incomplete n/m triangular grid: " + family)
        domains[family]["tex"] = "$n=" + span(ns) + r",\ 1\le m<n$"

    values = tuples("Policy", ("rule_pairs",))
    require(len(values) == 1, "Policy domain is no longer a singleton")
    domains["Policy"]["tex"] = str(next(iter(values))[0]) + " rule pairs"

    values = tuples("DB-Rolling", ("n", "m"))
    ns, floors = {n for n, _ in values}, {m for _, m in values}
    require(values == {(n, m) for n in ns for m in floors}, "DB-Rolling domain is not a product")
    domains["DB-Rolling"]["tex"] = "$n=" + span(ns) + r",\ m=" + ",".join(map(str, sorted(floors))) + "$"

    values = tuples("Rolling+Audit", ("n", "m", "audit_pairs"))
    require(len(values) == 1, "Rolling+Audit domain is no longer a singleton")
    n, m, audits = next(iter(values))
    domains["Rolling+Audit"]["tex"] = f"$n={n},\\ m={m}$; {audits} audit pair"

    values = tuples("Threads", ("n", "B", "regime"))
    ns, capacities = {n for n, _, _ in values}, {capacity for _, capacity, _ in values}
    regimes = {"backpressure", "saturated_offers"}
    require(capacities == {1, 2}, "Threads capacities disagree with the registered source")
    require(values == {(n, capacity, regime) for n in ns for capacity in capacities for regime in regimes},
            "Incomplete Threads n/capacity/regime grid")
    domains["Threads"]["tex"] = "$n=" + span(ns) + "$; queue " + ",".join(map(str, sorted(capacities)))
    domains["Threads"]["B_meaning"] = "queue capacity, confirmed by threads/README.md Registered model"

    values = tuples("PC2-Rolling", ("arms", "ready_floor"))
    require(len(values) == 1, "PC2-Rolling domain is no longer a singleton")
    arms, floor = next(iter(values))
    domains["PC2-Rolling"]["tex"] = f"{arms} arms; floor {floor}"

    values = tuples("Cell_n", ("n",))
    domains["Cell_n"]["tex"] = "$n=" + span(n for n, in values) + "$"
    return domains


def collect(artifact):
    artifact = Path(artifact).resolve()
    evidence = artifact / E6
    index_path = evidence / "results_index.csv"
    audit_path = evidence / "rolling_audit/v1/summary.csv"
    threads_readme = evidence / "threads/README.md"
    local_macros = PAPER / "build/generated/base-v3-evidence-macros.tex"
    expected_threads = EXPECTED_THREADS
    index = read_rows(index_path)
    keys = [(row["family"], row["params"], row["comparison"]) for row in index]
    require(len(keys) == len(set(keys)), "Duplicate comparison identity in E6 index")
    for row in index:
        require(row["class"] == classify(row), "Saved class disagrees with fine/merged decisions: " + str(row["family"]))
    main = [row for row in index if row["population"] in MAIN_POPULATIONS]
    require({row["family"] for row in main} == set(FAMILIES), "Main E6 family inventory changed")
    families = {family: counts([row for row in main if row["family"] == family]) for family in FAMILIES}
    total = counts(main)
    local = macro_values(local_macros)
    verified_macros = {}
    for key, macro in TOTAL_MACROS.items():
        require(str(total[key]) == local.get(macro), "Aggregated total differs from existing macro: " + macro)
        verified_macros[macro] = total[key]

    canary = [row for row in main if row["family"] == "Canary"]
    canary_macro = "VThreeESixCanaryPairs"
    require(local.get(canary_macro) == str(len(canary)), "Canary population differs from existing macro")
    require(all(row["class"] == "witness" for row in canary), "A main Canary comparison is not a witness")
    verified_macros[canary_macro] = len(canary)

    thread_rows = [row for row in index if row["family"] == "Threads"]
    require(all(row["population"] == "operational_control" for row in thread_rows), "Threads control population changed")
    require(Counter(row["class"] for row in thread_rows) == expected_threads, "Threads outcomes differ from declared control counts")
    for row in thread_rows:
        expected = "both_win" if "regime=backpressure" in row["params"] else "both_loss" if "regime=saturated_offers" in row["params"] else None
        require(expected == row["class"], "Threads regime/result mapping changed")

    audit = {row["job_id"]: row for row in read_rows(audit_path)}
    for job, result in {"fine_none_lazy": "WIN", "fine_transfers_lazy": "LOSS", "fine_boundaries_lazy": "WIN", "generated_boundaries_lazy": "WIN"}.items():
        require(audit[job]["status"] == audit[job]["decision"] == result, "Audit control changed: " + job)
    audit_rows = [row for row in main if row["family"] == "Rolling+Audit"]
    require(len(audit_rows) == 1 and audit_rows[0]["comparison"] == "transfers" and audit_rows[0]["class"] == "witness", "Audit main population is not the saved transfer comparison")

    pc = [row for row in main if row["family"] == "PC2-Rolling"]
    require(len(pc) == 1 and pc[0]["class"] == "incomplete" and pc[0]["fine_decision"] == "WIN", "PC2 pair changed")
    pc_timeout_fields = ("merged_decision", "merged_status", "direct_full_status", "merged_extended_7200_status", "direct_full_extended_7200_status", "xeon_merged_status", "xeon_direct_full_status")
    require(all(pc[0][field] == "TO" for field in pc_timeout_fields), "PC2 timeout must remain unresolved, not LOSS")

    reference = [row for row in index if row["population"] == "reference_e4"]
    require(reference and {row["family"] for row in reference} == {"Cell_n"}, "E4 reference inventory changed")
    require(all(row["class"] == "witness" for row in reference), "Cell_n reference outcomes changed")
    require(not any(row["family"] == "Cell_n" for row in main), "E4 Cell_n leaked into main total")
    excluded = {}
    for population in sorted({row["population"] for row in index} - MAIN_POPULATIONS):
        excluded[population] = counts([row for row in index if row["population"] == population])
    require(set(excluded) == {"scale_extension", "assumption_control", "reference_e4"}, "Unrecognized excluded population")
    require(len(index) == total["pairs"] + sum(group["pairs"] for group in excluded.values()), "Population accounting does not exhaust index")

    domains = parameter_domains(main, reference, threads_readme)
    table = render_table(families, counts(reference), domains)
    report = {
        "kind": "presentation_aggregation_of_preserved_rows_not_new_evidence",
        "status": "PASS",
        "document": "FG-DUCS paper",
        "generator": "scripts/generate_rq2_family_table.py",
        "table": "figures/rq2_family_counts.tex",
        "readme": {
            "generate": "python3 -B scripts/generate_rq2_family_table.py",
            "check": "python3 -B scripts/generate_rq2_family_table.py --check",
            "emit_patch": "python3 -B scripts/generate_rq2_family_table.py --emit-patch",
            "artifact_root": "Public artifact root, found among script ancestors or supplied with --artifact-root.",
            "write_scope": "Only the new figure and this JSON; --check writes nothing.",
            "unit": "One saved fine/merged comparison per results_index.csv row, not a trial, application or independent operational case."
        },
        "sources": {
            "population_definition": "paper/source/scripts/generate_rq2_family_table.py#MAIN_POPULATIONS",
            "threads_control_definition": "paper/source/scripts/generate_rq2_family_table.py#EXPECTED_THREADS",
            "results_index": "results/granularity/e6/results_index.csv",
            "audit_boundary_check": "results/granularity/e6/rolling_audit/v1/summary.csv",
            "threads_queue_capacity_definition": "results/granularity/e6/threads/README.md#registered-model",
            "existing_macros": "paper/source/build/generated/base-v3-evidence-macros.tex",
            "family_labels": "Preserved all eight family/control labels; Cell_n displayed separately from the main total. The paper explains the mechanisms."
        },
        "population_filter": sorted(MAIN_POPULATIONS),
        "all_index_comparisons": len(index),
        "main_counts": total,
        "main_family_counts": families,
        "parameter_domains": domains,
        "separate_e4_reference": {"family": "Cell_n", "included_in_main": False, **counts(reference)},
        "excluded_population_counts": excluded,
        "verified_existing_macros": verified_macros,
        "checks": {
            "declared_population_filter": sorted(MAIN_POPULATIONS),
            "unique_comparison_identities": True,
            "classes_match_saved_decisions": True,
            "family_sums_match_existing_total_macros": True,
            "all_eight_family_control_rows_preserved": len(families) + 1 == len(ALL_FAMILIES),
            "canary_count_and_all_witnesses": {"pairs": len(canary), "witness": len(canary)},
            "threads_control_counts_and_regimes": dict(expected_threads),
            "audit_transfer_pair_counted_boundary_WIN_separate": True,
            "pc2_incomplete_timeout_fields": {field: pc[0][field] for field in pc_timeout_fields},
            "e4_reference_excluded_from_main_total": True,
            "all_table_numeric_cells_generated": True,
            "parameter_domains_exactly_cover_saved_tuples": True,
            "policy_boundary_other_transfer_modes_preserved": True,
            "threads_B_confirmed_as_queue_capacity": True,
        },
        "limits": [
            "Existing rows are aggregated; no experiments, new solver decisions, retiming or new validation evidence are added.",
            "TO remains incomplete despite the separately reported PC2 obstruction; this script does not re-prove it.",
            "Audit boundary WIN is checked from its preserved summary and does not add a comparison to the main population.",
            "No inference about prevalence or operational effectiveness; no timing or host data are pooled.",
            "The generator only updates this table and its provenance; main.tex and supplements are not edited."
        ]
    }
    return table, report


def render_table(families, reference, domains):
    mechanisms = {
        "Rolling": "Readiness during startup",
        "Canary": "Failure reports and recovery",
        "Policy": "Audit overlap; role exclusion",
        "DB-Rolling": "Role-gated replacement",
        "Rolling+Audit": "Readiness and audit overlap",
        "Threads": "Backpressure or persistent arrival",
        "PC2-Rolling": "Availability during calibration",
        "Cell_n": "Empty-station transfer guards",
    }
    lines = [
        "% Generated by scripts/generate_rq2_family_table.py; do not edit numeric cells.",
        r"\begin{table}[!htbp]",
        r"\caption{Granularity mechanisms, parameter sweeps and controls. Each pair compares fine and merged contracts of one model: Policy merges boundaries, other rows merge transfers. Counts are comparisons, not independent applications. The main total excludes Cell.}",
        r"\label{tab:rq2-family-counts}",
        r"\centering\small",
        r"\begin{tabular}{@{}lp{.30\linewidth}rrrrr@{}}\toprule",
        r"Family / control & Mechanism and parameters & Pairs & \shortstack{WIN /\\LOSS} & \shortstack{LOSS /\\LOSS} & \shortstack{WIN /\\WIN} & Inc.\\\midrule",
        r"\multicolumn{7}{@{}l}{\emph{Constructed families and parameter sweeps}}\\",
    ]
    for family in FAMILIES:
        if family in {"Threads", "PC2-Rolling"}:
            heading = "Quiescence control" if family == "Threads" else "Source-derived attempt"
            lines.extend([r"\midrule", r"\multicolumn{7}{@{}l}{\emph{" + heading + r"}}\\"])
        values = families[family]
        description = mechanisms[family] + r".\newline " + domains[family]["tex"]
        lines.append(" & ".join([LABELS.get(family, family), description, *[str(values[key]) for key in ("pairs", *CLASSES)]]) + r"\\")
    lines.extend([
        r"\midrule",
        " & ".join([r"Main total", "", *["\\" + TOTAL_MACROS[key] + "{}" for key in ("pairs", *CLASSES)]]) + r"\\",
        r"\midrule",
        " & ".join([LABELS["Cell_n"], mechanisms["Cell_n"] + r".\newline " + domains["Cell_n"]["tex"], *[str(reference[key]) for key in ("pairs", *CLASSES)]]) + r"\\\bottomrule",
        r"\end{tabular}",
        r"\par\smallskip\raggedright\small Outcomes read fine / merged; Inc. is unresolved. PC2's merged solver remains TO, not LOSS. Rolling and Canary share a capacity obstruction: their sweeps supply "
        + str(families["Rolling"]["witness"] + families["Canary"]["witness"])
        + r" of the \VThreeESixWitness{} WIN/LOSS pairs.",
        r"$n$ counts replicas/workers/stations. Canary bounds reported failures by $n-m$; otherwise $m$ is an availability floor. Threads varies queue capacity 1,2 under both arrival regimes. Rolling+Audit's boundary merge remains WIN and adds no pair here.",
        r"\end{table}",
        "",
    ])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--check", action="store_true", help="Recompute and verify both generated files without writing")
    modes.add_argument("--emit-patch", action="store_true", help="Emit new generated outputs for apply_patch; never overwrite")
    parser.add_argument("--artifact-root", type=Path)
    args = parser.parse_args()
    artifact = artifact_root(args.artifact_root)
    table, report = collect(artifact.resolve())
    if args.check:
        require(TABLE.is_file() and TABLE.read_text() == table, "Generated family table is missing or stale")
        require(REPORT.is_file(), "Generated provenance JSON is missing")
        saved = json.loads(REPORT.read_text())
        require(bool(saved.pop("generated_at_utc", None)), "Missing generation timestamp")
        require(saved == report, "Generated provenance/check JSON is stale")
        print(json.dumps({"status": "PASS", "mode": "check", "main_counts": report["main_counts"], "family_rows": len(ALL_FAMILIES), "e4_reference_pairs": report["separate_e4_reference"]["pairs"]}))
        return
    report["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
    outputs = {TABLE: table, REPORT: json.dumps(report, ensure_ascii=False, indent=2) + "\n"}
    if args.emit_patch:
        require(all(not path.exists() for path in outputs), "--emit-patch only creates new outputs; an output already exists")
        print("*** Begin Patch")
        for path, content in outputs.items():
            print("*** Add File: " + str(path))
            for line in content.splitlines():
                print("+" + line)
        print("*** End Patch")
        return
    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    print(json.dumps({"status": "PASS", "mode": "generate", "main_counts": report["main_counts"]}))


if __name__ == "__main__":
    main()
