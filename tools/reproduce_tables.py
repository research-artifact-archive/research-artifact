#!/usr/bin/env python3
"""Reconstruct paper tables and denominators from retained records, without solvers."""
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path
import argparse
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "package"
SUPPLEMENT = ROOT / "supplement/history"
SOURCES = {}
STATUSES = ("SUCCESS", "FAILURE", "TIMEOUT", "INVALID", "UNSTARTED", "NOT_RUN")


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def read(path, jsonl=False):
    data = path.read_bytes()
    SOURCES[path.relative_to(ROOT).as_posix()] = hashlib.sha256(data).hexdigest()
    return [json.loads(line) for line in data.splitlines() if line] if jsonl else json.loads(data)


def unique(rows, field):
    result = {r[field]: r for r in rows}
    require(len(result) == len(rows), "duplicate unit: " + field)
    return result


def counts(rows):
    result = Counter(r["status"] for r in rows)
    require(set(result) <= set(STATUSES), "unrecognized status")
    return {status: result[status] for status in STATUSES}


def bound_file(path, row, prefix):
    data = path.read_bytes()
    require(len(data) == row[prefix + "_bytes"], "bound file size: " + str(path))
    require(hashlib.sha256(data).hexdigest() == row[prefix + "_sha256"],
            "bound file hash: " + str(path))


def primitive():
    directory = PACKAGE / "data/semantic"
    inputs = unique(read(directory / "INPUTS.json"), "id")
    raw = unique(read(directory / "RAW.jsonl", True), "input_id")
    require(set(inputs) == set(raw) and len(raw) == 4232, "primitive input coverage")
    root_count = 0
    for identity, row in raw.items():
        require(row["status"] == "SUCCESS" and not row["defects"], "primitive adverse unit")
        require([r["b"] for r in row["roots"]] == list(range(5)), "primitive root coverage")
        require(all(r["primitive"] == r["scalar"] == r["serialized"] for r in row["roots"]),
                "primitive root disagreement")
        bound_file(directory / "artifacts" / (identity + ".json"), row, "artifact")
        root_count += len(row["roots"])
    result = {"inputs": len(raw), "roots": root_count, "status": counts(raw.values()),
              "routes": dict(Counter(r["route"] for r in raw.values()))}
    result.update({field: sum(r[field] for r in raw.values())
                   for field in ("states", "actions", "outcomes", "policy_cells")})
    require(root_count == 21160, "primitive root denominator")
    return result


def native_and_table1():
    directory = PACKAGE / "data/native"
    data = read(directory / "INPUTS.json")
    inputs = unique(data["units"], "id")
    raw = unique(read(directory / "RAW.jsonl", True), "id")
    require(set(inputs) == set(raw) and len(raw) == 19644, "native path coverage")
    groups = defaultdict(list)
    kinds = Counter()
    for identity, unit in inputs.items():
        row = raw[identity]
        require(row["status"] == "SUCCESS", "native adverse path: " + identity)
        require(all(row.get(k) == v for k, v in unit["expected"].items()),
                "native observed/expected metadata mismatch: " + identity)
        groups[unit["cell"], unit["kind"]].append(row)
        kinds["parent_postwrite_control" if unit["postwrite"] else unit["kind"]] += 1
    roots = defaultdict(dict)
    for cell in data["cells"]:
        values = {}
        for policy in cell["policies"]:
            rows = groups.pop((cell["id"], policy["kind"]))
            require(len(rows) == policy["units"], "native cell coverage")
            maximum = max(r["cost"] for r in rows)
            require(maximum == policy["expected_max"], "native policy maximum")
            if not cell["control"]:
                require(maximum == policy["target"], "native worst-case witness missing")
            values[policy["kind"]] = maximum
        if not cell["control"]:
            roots[cell["case"], cell["budget"]][cell["layout"]] = values
    require(not groups and len(roots) == 192, "native/table1 root denominator")
    collapsed = {}
    for key, layouts in roots.items():
        require(set(layouts) == {"distinct", "colliding"}, "layout coverage")
        require(layouts["distinct"] == layouts["colliding"], "layout disagreement")
        collapsed[key] = layouts["distinct"]
    math = read(directory / "MATH_VALIDATION.json")
    for row in math["rows"]:
        bound_file(directory / "artifacts" / (row["id"] + ".json"), row, "artifact")
    recorded = read(directory / "COMPARISON_ANALYSIS.json")
    expected = {"fixed": (2, 190, 0), "look_fast": (18, 174, 0),
                "look_protected": (30, 162, 0), "cached": (138, 54, 0)}
    table = {}
    for kind, target in expected.items():
        small = equal = large = 0
        maximum = Fraction(0)
        witnesses = []
        for (case, budget), values in sorted(collapsed.items()):
            own, other = values["hybrid"], values[kind]
            small += own < other
            equal += own == other
            large += own > other
            reduction = Fraction(other - own, other)
            maximum = max(maximum, reduction)
            if kind == "fixed" and own < other:
                scale = 8 * data["cases"][case]["d"]
                require(own % scale == other % scale == 0, "native work scaling")
                witnesses.append({"case": case, "budget": budget,
                                  "hybrid_total": own // scale, "fixed_total": other // scale})
        require((small, equal, large) == target, "Table1 count differs from paper")
        prior = recorded["comparison"][kind]
        require((small, equal, large) == (prior["strict"], prior["equal"], len(prior["worse"])),
                "Table1 retained aggregate mismatch")
        require(abs(float(maximum) - prior["max_reduction"]) < 1e-14, "Table1 reduction mismatch")
        table[kind] = {"smaller": small, "equal": equal, "larger": large,
                       "max_reduction_fraction": str(maximum),
                       "max_reduction_percent": float(100 * maximum)}
        if witnesses:
            table[kind]["witnesses"] = witnesses
    return {"paths": len(raw), "status": counts(raw.values()), "paths_by_kind": dict(kinds),
            "core_roots": len(roots), "core_layout_cells": 384,
            "comparison_scope": "recorded policy outcome paths; not all Java schedules"}, table


def table2():
    configurations = [
        ("B1-original", "b1_constraint_comparator_01", "benchmark01/RAW.jsonl",
         ("cp_sat", "subset_dp", "all_budget"), 78),
        ("B1-screened", "b1_constraint_comparator_01", "screened01/BENCH_RAW.jsonl",
         ("screened_dp",), 78),
        ("B2", "b2_contingent_comparator_01", "benchmark01/RAW.jsonl",
         ("cp_sat", "screened_dp", "all_budget"), 48)]
    histories = {}
    incompletes = []
    values = defaultdict(dict)
    total = 0
    for label, study, filename, methods, denominator in configurations:
        directory = PACKAGE / "data/extended" / study
        inputs = unique(read(directory / "benchmark01/INPUTS.json"), "id")
        rows = read(directory / filename, True)
        keys = {(r["id"], r["method"]) for r in rows}
        require(len(inputs) == denominator, "Table2 input denominator")
        require(len(keys) == len(rows) and keys == {(i, m) for i in inputs for m in methods},
                "Table2 method-unit coverage")
        histories[label] = {m: counts(r for r in rows if r["method"] == m) for m in methods}
        total += len(rows)
        for row in rows:
            if row["status"] == "SUCCESS":
                values[study, row["id"]][row["method"]] = row["value"]
                if row["method"] == "all_budget":
                    bound_file(directory / "benchmark01/units" / row["id"] /
                               "all_budget/controller.json", row, "controller")
            else:
                incompletes.append({"study": label, "id": row["id"],
                                    "method": row["method"], "status": row["status"]})
    require(total == 456, "Table2 historical denominator")
    require(all(len(set(group.values())) == 1 for group in values.values()),
            "requested-budget value disagreement")
    expected = {("B1-original", "cp_sat"): (78, 0), ("B1-original", "subset_dp"): (56, 22),
                ("B1-original", "all_budget"): (53, 25), ("B1-screened", "screened_dp"): (68, 10),
                ("B2", "cp_sat"): (48, 0), ("B2", "screened_dp"): (48, 0),
                ("B2", "all_budget"): (46, 2)}
    for (study, method), pair in expected.items():
        c = histories[study][method]
        require((c["SUCCESS"], c["TIMEOUT"]) == pair and
                sum(c.values()) == sum(pair), "Table2 status differs from paper")
    return {"historical_method_units": total, "displayed_method_units": 378,
            "histories": histories, "incomplete_units": incompletes,
            "requested_budget_value_disagreements": 0,
            "original_benchmarks_or_timeouts_rerun": 0}


def earlier_scale():
    studies = [("dependency_scale_01", "RAW.jsonl", 174),
               ("dependency_hybrid_01", "SCALE_RAW.jsonl", 114),
               ("dependency_hybrid_check_02", "SCALE_RAW.jsonl", 57)]
    result = {}
    for study, filename, denominator in studies:
        rows = read(SUPPLEMENT / study / filename, True)
        keys = {(r["case"], r.get("method", "check")) for r in rows}
        require(len(rows) == len(keys) == denominator, "earlier scale coverage")
        methods = sorted({r.get("method", "check") for r in rows})
        result[study] = {"units": denominator,
            "status_by_method": {m: counts(r for r in rows if r.get("method", "check") == m)
                                 for m in methods},
            "incomplete_units": [{"case": r["case"], "method": r.get("method", "check"),
                                  "status": r["status"], "reason": r.get("reason")}
                                 for r in rows if r["status"] != "SUCCESS"]}
    expected = result["dependency_scale_01"]["status_by_method"]
    require(expected["compile"]["SUCCESS"] == 78 and expected["compile"]["TIMEOUT"] == 9,
            "original scale construction counts")
    require(expected["check"]["SUCCESS"] == 74 and expected["check"]["TIMEOUT"] == 4
            and expected["check"]["NOT_RUN"] == 9, "original scale checking counts")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="include every incomplete unit and source hash")
    args = parser.parse_args()
    result = {"primitive": primitive()}
    result["native"], result["table1"] = native_and_table1()
    result["table2"] = table2()
    result["earlier_scale"] = earlier_scale()
    result.update(success=True, scientific_sample_increase=False,
                  execution_scope="Read-only aggregation and hash checks; no solver or native execution",
                  source_sha256=SOURCES)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("Verified retained records: 4,232 primitive inputs / 21,160 roots; 19,644 native paths.")
        print("Table 1: 192 roots, layout duplicates collapsed after checking equality.")
        for kind, row in result["table1"].items():
            print(f"  {kind}: {row['smaller']}/{row['equal']}/{row['larger']}; "
                  f"max total-work reduction {row['max_reduction_percent']:.2f}%")
        print("Table 2: SUCCESS/TIMEOUT (all other statuses zero); all 456 historical units retained.")
        for study, methods in result["table2"]["histories"].items():
            for method, c in methods.items():
                print(f"  {study} {method}: {c['SUCCESS']}/{c['TIMEOUT']}")
        print("Earlier scale: original 78/9 construction; 74/4/9 checking SUCCESS/TIMEOUT/NOT_RUN.")
        print("Use --json for source hashes, full status partitions, and every incomplete unit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
