#!/usr/bin/env python3
"""Read extended-budget returns without modifying raw evidence.

Each planned cell remains visible. Ratios require a checked, completed single
trial and the same decision from all five fixed-budget Lazy trials. JVM elapsed
time and solver time are separate; resource failures yield no timing ratio.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "runtime"))
sys.path.insert(1, str(HERE / "Implementation/Experiment/FSE2027/scripts"))
import harness_common as common

GOOD = {"SUCCESS", "UNREALIZABLE"}
JAR_SHA = "fbdc25f58d5441ed906d408a94b7414c9d9c3ed35e2ebce22d9751729967ba07"
LABELS = {"fg_ducs_otf": "Lazy", "direct_full": "DF",
          "fg_ducs_otf_eager_controllable": "Eager",
          "fg_ducs_otf_update_first": "Update-first"}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def truth(value):
    return str(value).lower() == "true"


def number(value):
    if value in (None, ""):
        return None
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ValueError("Invalid nonnegative measurement: " + str(value))
    return result


def csv_rows(path):
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def relative_file(folder, value):
    path = (folder / str(value).replace("\\", "/")).resolve()
    if not path.is_relative_to(folder.resolve()):
        raise ValueError("Artifact path leaves its campaign")
    return path


def valid_baseline(row):
    if not row or row.get("stage1_status") not in GOOD:
        return False
    return (truth(row.get("timing_summary_eligible"))
            and str(row.get("completed_valid_repetitions")) == "5"
            and str(row.get("planned_total_repetitions")) == "5"
            and not truth(row.get("invalid")) and not truth(row.get("inconsistent")))


def read_trial(folder, job, config):
    """Inspect meta and evaluation output even before collect has been run."""
    path = folder / "runs" / job["job_id"] / "meta.json"
    data = dict(status="NOT_RUN", valid_decision=False, validation_reason="",
                elapsed_seconds="", peak_rss_bytes="", peak_rss_gib="",
                solver_seconds="", states_discovered="", started_utc="", finished_utc="",
                skip_reason="", meta_sha256="", output_sha256="", classpath_sha256="")
    if not path.exists():
        return data
    raw = path.read_bytes()
    meta = json.loads(raw)
    data["meta_sha256"] = hashlib.sha256(raw).hexdigest()
    for key in ("job_id", "model_id", "target_id", "method_id", "repetition"):
        if str(meta.get("job", {}).get(key)) != str(job[key]):
            raise ValueError(f"{path}: job identity mismatch: {key}")
    data["status"] = meta.get("status", "INCOMPLETE") if meta.get("completed") else "INCOMPLETE"
    data["skip_reason"] = meta.get("skip_reason", "")
    for key in ("started_utc", "finished_utc"):
        data[key] = meta.get(key, "")
    for source, dest in (("elapsed_monotonic_seconds", "elapsed_seconds"),
                         ("peak_rss_bytes", "peak_rss_bytes")):
        value = number(meta.get(source))
        if value is not None:
            data[dest] = value
    if data["peak_rss_bytes"] != "":
        data["peak_rss_gib"] = data["peak_rss_bytes"] / 1024 ** 3
    errors = []
    cap = number(meta.get("timeout_seconds"))
    if cap is not None and cap != float(config["timeout_seconds"]):
        errors.append("recorded timeout differs from config")
    jar = meta.get("classpath", {}).get("sha256", "")
    data["classpath_sha256"] = jar
    if jar and jar != JAR_SHA:
        errors.append("experimental JAR digest differs")
    command = meta.get("command", [])
    if command and "-Xmx" + config["java_heap"] not in command:
        errors.append("recorded heap differs from config")
    output = meta.get("artifacts", {}).get("output", "")
    parsed = None
    if output:
        output_path = relative_file(folder, output)
        if output_path.is_file():
            data["output_sha256"] = hashlib.sha256(output_path.read_bytes()).hexdigest()
            expected = meta.get("artifact_digests", {}).get("output", {}).get("sha256")
            if expected and expected != data["output_sha256"]:
                errors.append("evaluation output digest mismatch")
            parsed = common.parse_evaluation_file(output_path)
            metrics = common.output_summary(parsed)
            solver_ms = number(metrics.get("solver_time_ms"))
            if solver_ms is not None:
                data["solver_seconds"] = solver_ms / 1000
            states = number(metrics.get("states_discovered"))
            if states is not None:
                if not states.is_integer():
                    raise ValueError("Discovered states must be integral")
                data["states_discovered"] = int(states)
    if data["status"] in GOOD:
        if not jar or cap is None or not command:
            errors.append("execution provenance is incomplete")
        if not parsed or not parsed["found"] or parsed["errors"]:
            errors.append("evaluation CSV absent or invalid")
        else:
            metrics = common.output_summary(parsed)
            if metrics.get("evaluation_result") != data["status"]:
                errors.append("process status and evaluation decision differ")
            if metrics.get("internal_certificate_check") != "passed":
                errors.append("certificate check did not pass")
            if data["status"] == "SUCCESS" and metrics.get("link_checker") != "passed":
                errors.append("Link check did not pass")
        data["valid_decision"] = not errors
    data["validation_reason"] = "; ".join(errors)
    return data


def build_rows(raw_root, config_root):
    baselines = {}
    for name in ("rq3", "rq4_travel"):
        for row in csv_rows(raw_root / name / "summary.csv"):
            if row["method_id"] == "fg_ducs_otf":
                key = (row["model_id"], row["target_id"])
                if key in baselines:
                    raise ValueError("Duplicate baseline cell " + str(key))
                baselines[key] = (name, row)
    rows = []
    paths = sorted(config_root.glob("ext[1-5]_*.json"))
    if not paths:
        raise ValueError("No extended-budget configurations found")
    for path in paths:
        config = common.load_config(path)
        if int(config["repetitions"]) != 1:
            raise ValueError("Extended trials must have one repetition")
        folder = raw_root / path.stem
        if (folder / "config.json").exists():
            recorded = read_json(folder / "config.json")
            for key in ("models", "methods", "targets", "java_heap", "timeout_seconds", "repetitions", "master_seed"):
                if recorded[key] != config[key]:
                    raise ValueError(f"{path.stem}: saved config differs: {key}")
        plan = common.build_plan(config)
        if (folder / "plan.json").exists() and read_json(folder / "plan.json") != plan:
            raise ValueError(path.stem + ": saved plan differs")
        for job in plan["jobs"]:
            row = dict(campaign=path.stem, order=job["global_order_index"],
                       job_id=job["job_id"], model_id=job["model_id"], target_id=job["target_id"],
                       method_id=job["method_id"], heap=config["java_heap"],
                       budget_seconds=config["timeout_seconds"], trials=1,
                       prerequisites=json.dumps(job.get("prerequisites", []), sort_keys=True),
                       **read_trial(folder, job, config))
            name, base = baselines.get((row["model_id"], row["target_id"]), ("", {}))
            row.update(lazy_fixed_source=name + "/summary.csv" if name else "",
                       lazy_fixed_status=base.get("stage1_status", ""),
                       lazy_fixed_elapsed_median_seconds="", lazy_fixed_solver_median_seconds="",
                       single_over_lazy_fixed_elapsed_ratio="", single_over_lazy_fixed_solver_ratio="",
                       decision_agreement="", ratio_note="requires checked matching decisions and five valid baseline trials")
            if valid_baseline(base):
                wall = number(base.get("elapsed_monotonic_seconds_median"))
                solver = number(base.get("solver_time_ms_median"))
                row["lazy_fixed_elapsed_median_seconds"] = "" if wall is None else wall
                row["lazy_fixed_solver_median_seconds"] = "" if solver is None else solver / 1000
                if row["valid_decision"]:
                    same = row["status"] == base["stage1_status"]
                    row["decision_agreement"] = same
                    if same:
                        for measurement, baseline, dest in (
                            ("elapsed_seconds", "lazy_fixed_elapsed_median_seconds", "single_over_lazy_fixed_elapsed_ratio"),
                            ("solver_seconds", "lazy_fixed_solver_median_seconds", "single_over_lazy_fixed_solver_ratio")):
                            if row[measurement] != "" and row[baseline] not in ("", 0):
                                row[dest] = row[measurement] / row[baseline]
                        row["ratio_note"] = "single extended trial / fixed-budget five-run Lazy median; scopes kept separate"
                    else:
                        row["ratio_note"] = "decision disagreement; no ratio"
            rows.append(row)
    return rows


def tex(value):
    replacements = {"\\": r"\textbackslash{}", "_": r"\_", "%": r"\%", "&": r"\&",
                    "#": r"\#", "{": r"\{", "}": r"\}", "$": r"\$"}
    return "".join(replacements.get(ch, ch) for ch in str(value))


def display(value):
    if value == "":
        return "--"
    return f"{value:.3g}" if isinstance(value, float) else tex(value)


def cell_label(row):
    model = row["model_id"]
    match = re.fullmatch(r"travel_n(\d+)_k(\d+)", model)
    if match:
        label = f"Travel({int(match[1])},{int(match[2])})"
    else:
        label = {"productioncell_arms1": "PC1", "productioncell_arms2": "PC2",
                 "industry": "Industry", "railcab": "Railcab", "surveillance": "Surveillance",
                 "workflow": "Workflow"}.get(model, model)
    return label + "/" + row["target_id"] + " [" + row["campaign"].split("_")[0] + "]"


def render(rows, output):
    output.mkdir(parents=True, exist_ok=True)
    with (output / "ext-budget.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    counts = Counter(row["status"] for row in rows)
    macros = {"ExtBudgetPlanned": len(rows), "ExtBudgetChecked": sum(r["valid_decision"] for r in rows),
              "ExtBudgetTimeout": counts["TIMEOUT"], "ExtBudgetOOM": counts["OOM"],
              "ExtBudgetSkipped": counts["SKIPPED_MONOTONE"],
              "ExtBudgetPending": counts["NOT_RUN"] + counts["INCOMPLETE"],
              "ExtBudgetReceived": sum(r["status"] not in {"NOT_RUN", "INCOMPLETE"} for r in rows)}
    macro_text = "% Generated from extended-budget configs and returned evidence.\n" + "\n".join(
        rf"\providecommand{{\{key}}}{{{value}}}" for key, value in macros.items()) + "\n"
    (output / "ext-budget-macros.tex").write_text(macro_text)
    lines = [macro_text, r"\begingroup\scriptsize\setlength{\tabcolsep}{3pt}",
             r"\begin{longtable}{@{}llrrrrrrr@{}}",
             r"\caption{Extended-budget single trials (separate from the fixed-budget campaign).}\label{tab:ext-budget}\\",
             r"\toprule Cell / campaign & Method & GiB & Cap (s) & Status & JVM (s) & RSS (GiB) & States & Ratio\\\midrule\endhead"]
    for row in rows:
        status = f"TO({row['budget_seconds']})" if row["status"] == "TIMEOUT" else row["status"]
        if row["validation_reason"]:
            status += "!"
        values = [tex(cell_label(row)), tex(LABELS[row["method_id"]]), tex(row["heap"].removesuffix("g")),
                  display(row["budget_seconds"]), tex(status)]
        values.extend(display(row[key]) for key in ("elapsed_seconds", "peak_rss_gib", "states_discovered",
                                                    "single_over_lazy_fixed_elapsed_ratio"))
        lines.append(" & ".join(values) + r"\\")
    lines += [r"\bottomrule\end{longtable}\endgroup",
              r"Each row has one planned trial. NOT\_RUN/INCOMPLETE means no completed return; -- means unmeasured or ineligible, never zero. "
              r"SKIPPED\_MONOTONE records a scheduling exclusion, not a measured resource failure or an inferred losing decision; reasons are in the CSV. "
              r"! marks a provenance/check failure; the raw status is retained. "
              r"The ratio uses total JVM elapsed time divided by the same cell's fixed-budget, five-valid-trial Lazy median (1,200 s, 64 GiB), "
              r"only for matching checked decisions. The CSV separately reports solver-time ratios; timeouts have no ratio. "
              r"An extended trial is never treated as a five-run median. RSS measures process memory, not heap occupancy."]
    (output / "ext-budget.tex").write_text("\n".join(lines) + "\n")
    return dict(planned=len(rows), statuses=dict(counts), macros=macros)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=HERE / "raw")
    parser.add_argument("--config-root", type=Path, default=HERE / "configs")
    default = HERE.parents[1] / "paper/build/generated" if HERE.parent.name == "experiments" else HERE / "analysis/ext"
    parser.add_argument("--output", type=Path, default=default)
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(args.input_root.resolve()):
        parser.error("Generated output must be outside the raw input directory")
    rows = build_rows(args.input_root, args.config_root)
    print(json.dumps(render(rows, args.output), sort_keys=True))


if __name__ == "__main__":
    main()
