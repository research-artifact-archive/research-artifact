from pathlib import Path
import collections
import copy
import csv
import datetime
import hashlib
import json
import math
import statistics
import time

D = Path(__file__).resolve().parent
P = D.parent
CAMPAIGNS = [
    ("initial", "roslyn_arrivals_01", 864),
    ("balanced", "roslyn_arrivals_balanced_01", 1728),
    ("rebase", "roslyn_rebase_01/arrivals01", 3072),
    ("batch", "roslyn_rebase_batch_01/arrivals01", 1728),
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    with path.open("x") as handle:
        json.dump(value, handle, indent=2)
        handle.write("\n")


def require(condition, label):
    if not condition:
        raise AssertionError(label)


def p95(values):
    ordered = sorted(values)
    return ordered[math.ceil(0.95 * len(ordered)) - 1]


def stats(values):
    return dict(n=len(values), min=min(values), median=statistics.median(values),
                p95_nearest_rank=p95(values), max=max(values))


def spans(row):
    opened = None
    result = []
    last = row["foreground_start_ns"]
    phases = row["observed_phases"]
    require(row["timing_hook_enabled"] is True, "phase observer declaration")
    for item in phases:
        tick, name = item["at_ns"], item["name"]
        require(last <= tick <= row["foreground_end_ns"], "phase chronology/range")
        last = tick
        if name == "lock_enter":
            require(opened is None, "nested observed lock")
            opened = tick
        elif name in ("cheap_failure", "return_changed"):
            require(opened is not None, "missing observed entry")
            result.append((opened, tick))
            opened = None
    require(opened is None and len(result) == row["counters"]["Calls"], "span/call count")
    require(all(a[1] <= b[0] for a, b in zip(result, result[1:])), "overlapping foreground spans")
    for request in row["writer_requests"]:
        require(not any(a < request["published_ns"] < b for a, b in result),
                "background publication within observed protected span")
    return result


def extract(row, campaign):
    require(row["status"] == "SUCCESS", "native status")
    fg_start, fg_end = row["foreground_start_ns"], row["foreground_end_ns"]
    bg = row["writer_requests"]
    pubs = [p for p in row["publications"] if p["kind"] == "background"]
    require(len(bg) == len(pubs) == row["actual_writes_total"] == 64, "writer denominator")
    require(row["jobs"] == row["foreground_publications"] == 32, "job denominator")
    require(fg_end - fg_start == row["foreground_ns"], "foreground duration")
    require([x["published_ns"] for x in bg] == [x["published_ns"] for x in pubs], "publication binding")
    for x in bg:
        require(x["intended_ns"] <= x["enqueued_ns"] <= x["invoked_ns"] <= x["published_ns"] <= x["returned_ns"], "background timeline")
    b_fg = sum(fg_start <= x["published_ns"] <= fg_end for x in pubs)
    require(b_fg == row["actual_writes_during_foreground"], "foreground write count")
    before = sum(x["published_ns"] < fg_start for x in pubs)
    after = sum(x["published_ns"] > fg_end for x in pubs)
    require(before + b_fg + after == 64, "writer partition")
    c = row["counters"]
    inside_bound = min(max(b_fg - row["r"], 0), 32)
    if row["mode"] != "baseline":
        require(c["Calls"] == 32 + c["CheapFailures"] and c["CheapFailures"] <= b_fg, "call accounting")
        if row["mode"] != "original":
            require(c["Calls"] <= 32 + row["r"], "call cap")
        if row["mode"] in ("three", "rebase", "batch"):
            require(0 <= c["PreparedInside"] <= inside_bound, "protected count bound")
    value = dict(campaign=campaign, id=row["id"], phase=row["phase"], mode=row["mode"],
                 r=row["r"], period_us=row["period_us"], fork=row["fork"], rep=row["rep"],
                 B_fg=b_fg, writes_before_foreground=before, writes_after_foreground=after,
                 three_mode_inside_bound=inside_bound, full_inside=c.get("PreparedInside"),
                 cheap_failures=c.get("CheapFailures"), calls=c.get("Calls"),
                 mismatches=c.get("Mismatches"), rebases=c.get("Rebases", 0) if c else None,
                 foreground_us=row["foreground_ns"] / 1000,
                 background_e2e_p95_us=p95([x["returned_ns"] - x["intended_ns"] for x in bg]) / 1000,
                 background_service_p95_us=p95([x["returned_ns"] - x["invoked_ns"] for x in bg]) / 1000)
    if campaign == "batch":
        intervals = spans(row)
        overlap = [sum(max(0, min(b, x["returned_ns"]) - max(a, x["invoked_ns"]))
                       for a, b in intervals) for x in bg]
        value.update(observed_protected_us=sum(b-a for a, b in intervals) / 1000,
                     bg_service_overlap_total_us=sum(overlap) / 1000,
                     bg_requests_with_observed_overlap=sum(v > 0 for v in overlap))
    return value


def rank(values):
    ordered = sorted(range(len(values)), key=lambda i: values[i])
    result = [0.0] * len(values)
    start = 0
    while start < len(values):
        end = start + 1
        while end < len(values) and values[ordered[end]] == values[ordered[start]]:
            end += 1
        for index in ordered[start:end]:
            result[index] = (start + end - 1) / 2
        start = end
    return result


def spearman(x, y):
    x, y = rank(x), rank(y)
    mx, my = statistics.mean(x), statistics.mean(y)
    numerator = sum((a-mx)*(b-my) for a, b in zip(x, y))
    denominator = math.sqrt(sum((a-mx)**2 for a in x) * sum((b-my)**2 for b in y))
    return None if denominator == 0 else numerator / denominator


def main():
    start = time.monotonic()
    out = D / "run01"
    out.mkdir()
    inputs = []
    for label, relative, expected in CAMPAIGNS:
        folder = P / relative
        receipt = folder / "run01/check01/RECEIPT.json"
        require(json.loads(receipt.read_text())["status"] == "PASS", "prior source check")
        files = sorted((folder / "run01").glob("p*/stdout.jsonl"))
        inputs.append(dict(campaign=label, relative=relative, expected_units=expected,
                           checker_receipt_sha256=sha(receipt),
                           files=[dict(path=str(p.relative_to(P)), sha256=sha(p)) for p in files]))
    write(out / "INPUT_RECEIPT.json", dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
          scope="POST_OUTCOME_DESCRIPTIVE_ANALYSIS_OF_EXISTING_EXECUTIONS", campaigns=inputs,
          source_sha256=sha(Path(__file__)), plan_sha256=sha(D / "PLAN.md"), expected_all_units=7392))
    values, outcomes = [], []
    samples = {}
    for spec in inputs:
        count = 0
        for item in spec["files"]:
            path = P / item["path"]
            for line_no, line in enumerate(path.read_text().splitlines(), 1):
                row = json.loads(line)
                count += 1
                try:
                    value = extract(row, spec["campaign"])
                    values.append(value)
                    status, error = "PASS", None
                    if spec["campaign"] == "batch" and row["mode"] == "three":
                        samples.setdefault("three", row)
                except Exception as exc:
                    status, error = "FAIL", repr(exc)
                outcomes.append(dict(campaign=spec["campaign"], source=item["path"],
                                     line=line_no, id=row.get("id"), phase=row.get("phase"),
                                     native_status=row.get("status"), status=status, error=error))
        require(count == spec["expected_units"], "retained campaign count")
    groups = collections.defaultdict(list)
    for v in values:
        groups[tuple(v[k] for k in ["campaign", "phase", "mode", "r", "period_us"])].append(v)
    cells = []
    for key, group in sorted(groups.items()):
        cell = dict(zip(["campaign", "phase", "mode", "r", "period_us"], key))
        cell.update(units=len(group), B_fg=stats([v["B_fg"] for v in group]),
                    B_fg_histogram=dict(sorted(collections.Counter(v["B_fg"] for v in group).items())),
                    B_fg_below_r=sum(v["B_fg"] < v["r"] for v in group),
                    B_fg_r_through_r_plus31=sum(v["r"] <= v["B_fg"] < v["r"]+32 for v in group),
                    B_fg_at_least_r_plus32=sum(v["B_fg"] >= v["r"]+32 for v in group))
        cell["metrics"] = {k: stats([v[k] for v in group]) for k in
                           ["full_inside", "cheap_failures", "calls", "mismatches", "rebases", "three_mode_inside_bound",
                            "foreground_us", "background_e2e_p95_us", "background_service_p95_us",
                            "observed_protected_us", "bg_service_overlap_total_us", "bg_requests_with_observed_overlap"]
                           if k in group[0] and group[0][k] is not None}
        if cell["campaign"] == "batch" and cell["phase"] == "measurement":
            cell["descriptive_spearman"] = {k: spearman([v["observed_protected_us"] for v in group],
                                                       [v[k] for v in group]) for k in
                                              ["background_e2e_p95_us", "foreground_us"]}
        cells.append(cell)
    controls = []
    sample = samples["three"]
    mutations = [
        ("incorrect_B_fg", lambda x: x.update(actual_writes_during_foreground=999)),
        ("publication_timestamp", lambda x: x["writer_requests"][0].update(published_ns=-999)),
        ("excessive_inside", lambda x: x["counters"].update(PreparedInside=33)),
        ("missing_lock_entry", lambda x: x["observed_phases"].remove(next(p for p in x["observed_phases"] if p["name"] == "lock_enter"))),
        ("phase_outside_foreground", lambda x: x["observed_phases"][0].update(at_ns=-999)),
    ]
    for name, change in mutations:
        altered = copy.deepcopy(sample)
        change(altered)
        try:
            extract(altered, "batch")
            detected = False
        except Exception:
            detected = True
        controls.append(dict(name=name, detected=detected))
    paired_source = P / "roslyn_rebase_batch_01/arrivals01/analysis01/SUMMARY.json"
    paired = json.loads(paired_source.read_text())
    status = "PASS" if len(outcomes) == len(values) == 7392 and all(x["detected"] for x in controls) else "FAIL"
    write(out / "UNITS.json", values)
    write(out / "CHECKS.json", outcomes)
    with (out / "CELLS.tsv").open("x") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(["campaign", "phase", "mode", "r", "period_us", "n", "B_min", "B_median", "B_max", "B_below_r_plus32", "inside_median", "bound_median", "Q_median", "FG_us", "BG_p95_us"])
        for c in cells:
            metric = lambda k: c["metrics"].get(k, {}).get("median", "NA")
            writer.writerow([c[k] for k in ["campaign", "phase", "mode", "r", "period_us"]] +
                            [c["units"], c["B_fg"]["min"], c["B_fg"]["median"], c["B_fg"]["max"],
                             c["units"]-c["B_fg_at_least_r_plus32"], metric("full_inside"),
                             metric("three_mode_inside_bound"), metric("calls"), metric("foreground_us"), metric("background_e2e_p95_us")])
    result = dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), status=status,
                  seconds=time.monotonic()-start, all_units=len(outcomes), usable_units=len(values),
                  check_statuses=dict(collections.Counter(x["status"] for x in outcomes)),
                  phase_counts=dict(collections.Counter(x["phase"] for x in outcomes)),
                  controls=controls, cells=cells,
                  original_batch_pair_source_sha256=sha(paired_source),
                  original_batch_vs_rebase=[x for x in paired["comparisons"] if x["against"] == "rebase"],
                  new_native_runs=0, new_timing_samples=0,
                  scope="Post-outcome descriptive timelines and source count bounds; no causal or worst-time inference. Observed protected spans exclude acquisition/release.")
    write(out / "SUMMARY.json", result)
    print(json.dumps({k: v for k, v in result.items() if k not in ["cells", "original_batch_vs_rebase"]}), flush=True)
    require(status == "PASS", "analysis outcome")


if __name__ == "__main__":
    main()
