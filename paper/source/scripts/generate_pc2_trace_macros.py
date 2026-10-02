#!/usr/bin/env python3
"""Derive trace display macros directly from the preserved PC2 certificate.

Select the minimum initial state, then the lexicographically first saved policy
edge (event, target, original edge index), until a saved goal is reached.
Default mode writes build/generated/pc2-trace-macros.tex; --check writes nothing.
No solver, adapter, network or private trace excerpt is used.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re

from public_evidence import artifact_root

PAPER = Path(__file__).resolve().parents[1]
OUTPUT = PAPER / "build/generated/pc2-trace-macros.tex"
PC2 = "results/granularity/e6/pc2_rolling/"
SOURCES = {
    "certificate": PC2 + "v2/validation/export/lazy_none/certificate.json",
    "physical_audit": PC2 + "v2/validation/physical_certificate_crosscheck.json",
    "plant_probe": PC2 + "v2/preflight/cal_new_plant/transitions.txt",
    "model": PC2 + "v2/inputs/ProductionCell_Arms2_Calibration.lts",
}
CORE_NAMES = ("BeforeTransfers", "AfterFirstTransfer", "AfterFirstCalibration",
              "AfterSecondTransfer", "AfterSecondCalibration")
SELECTION_RULE = "minimum initial state ID; then minimum (event, target, original edge index) until goal"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def event_kind(event):
    for prefix, kind in (("reconfigure_PRODUCTION_CELL_", "transfer"),
                         ("stopOldSpec_", "boundary_stop"),
                         ("startNewSpec_", "boundary_start"),
                         ("in.", "ordinary_arrival"),
                         ("calibrated.", "ordinary_calibration_completion")):
        if event.startswith(prefix):
            return kind
    raise ValueError("No saved-trace classification for event: " + event)


def collect(artifact):
    """Return deterministic TeX and public provenance from saved data only."""
    artifact = Path(artifact).resolve()
    certificate = json.loads((artifact / SOURCES["certificate"]).read_text())
    audit = json.loads((artifact / SOURCES["physical_audit"]).read_text())
    probe = (artifact / SOURCES["plant_probe"]).read_text()
    model = (artifact / SOURCES["model"]).read_text()
    require(certificate["decision"] == "WIN" and audit["status"] == "PASS", "Saved PC2 evidence status changed")
    states = {value["id"]: value for value in certificate["states"]}
    indices = {value["id"]: index for index, value in enumerate(certificate["states"])}
    require(len(states) == len(certificate["states"]), "Duplicate saved state IDs")
    initials = sorted(value["id"] for value in states.values() if value["initial"])
    require(bool(initials), "No saved entry state")
    edges = {}
    for index, (source, event, target) in enumerate(certificate["strategy_edges"]):
        edges.setdefault(source, []).append((event, target, index))
    state = initials[0]
    sequence, selected, seen = [state], [], set()
    while not states[state]["goal"]:
        require(state not in seen, "Repeated state on fixed trace")
        seen.add(state)
        options = sorted(edges.get(state, []), key=lambda row: (row[0], row[1], row[2]))
        require(bool(options), "Missing saved policy successor")
        event, target, index = options[0]
        require(target in states and states[target]["rank"] < states[state]["rank"], "Saved selected edge does not decrease rank")
        selected.append((state, event, target, index))
        sequence.append(target)
        state = target
    require(str(state) in certificate["goal_matches"], "Saved goal has no handover target")
    require(states[state]["rank"] == 0 and not states[state]["pending"], "Saved goal is incomplete")
    calibration = set(audit["calibration_raw_states"])
    probe_calibration = {int(source) for source, body in re.findall(r"Q(\d+)\s*=\s*\((.*?)\)(?:,|\.|\+)", probe, re.S)
                         if "calibrated[1]" in body}
    require(calibration == probe_calibration, "Saved raw calibration classification differs from its probe")
    for sid in sequence:
        actual = states[sid]
        require(actual["safe"], "Unsafe state on selected path")
        require(type(actual["rank"]) is int and actual["rank"] >= 0, "Invalid saved rank")
        require(all(version in {"OLD", "NEW"} for version, raw, observers in actual["physical"]), "Unknown physical version")
        computed = sum(version == "OLD" or raw not in calibration for version, raw, observers in actual["physical"])
        require(computed == actual["physical_operational_arms"] and computed >= 1,
                "Saved path physical classification differs")
        require("update_time:R_CAL_READY:0" in actual["testers"], "Interval tester missing along saved path")
    # The ordinary selected events are arrivals and calibration completions.
    uncommented = re.sub(r"/\*.*?\*/", "", model, flags=re.S)
    for name in ("OldControllableActions", "NewControllableActions", "CalControllableActions"):
        match = re.search(r"set " + name + r" = \{([^}]*)\}", uncommented)
        require(match is not None and "in[" not in match[1] and "calibrated[" not in match[1], "Ordinary UC classification changed")
    kinds = [event_kind(event) for source, event, target, index in selected]
    counts = Counter(kinds)
    require("transfer" in kinds, "Selected path has no transfer focus")
    first = kinds.index("transfer")
    last = max(i for i, kind in enumerate(kinds) if kind in ("transfer", "ordinary_calibration_completion"))
    require(kinds[first:last + 1] == ["transfer", "ordinary_calibration_completion", "transfer", "ordinary_calibration_completion"],
            "Saved focus is no longer transfer/completion/transfer/completion")
    core = sequence[first:last + 2]
    require(len(core) == len(CORE_NAMES), "Unexpected focus-state inventory")
    values, provenance = {}, []

    def add(suffix, value, certificate_pointers, derivation="direct saved field"):
        require(type(value) is int and value >= 0 or isinstance(value, str) and re.fullmatch(r"new-[0-9]+", value), "Unsafe macro value")
        name = "PCTwoTrace" + suffix
        require(name not in values, "Duplicate display macro")
        values[name] = value
        provenance.append({"macro": name, "value": value, "source": SOURCES["certificate"],
                           "certificate_pointers": certificate_pointers, "derivation": derivation})

    state_pointer = lambda sid, field: "/states/" + str(indices[sid]) + "/" + field
    add("Entry", initials[0], [state_pointer(initials[0], "id"), state_pointer(initials[0], "initial")], "minimum initial state ID")
    add("Goal", state, [state_pointer(state, "id"), state_pointer(state, "goal")], "terminal state of the fixed selected path")
    all_edges = ["/strategy_edges/" + str(row[3]) for row in selected]
    add("Events", len(selected), all_edges, "number of selected edges")
    add("InitialRank", states[initials[0]]["rank"], [state_pointer(initials[0], "rank")])
    for name, sid in zip(CORE_NAMES, core):
        add(name + "Rank", states[sid]["rank"], [state_pointer(sid, "rank")])
    add("GoalRank", states[state]["rank"], [state_pointer(state, "rank")])
    add("PrefixEvents", first, all_edges[:first], "number of selected edges before the first transfer")
    add("SuffixEvents", len(selected) - last - 1, all_edges[last + 1:], "number of selected edges after the final transfer or calibration completion")
    for suffix, kind in (("OldStops", "boundary_stop"), ("UCArrivals", "ordinary_arrival"),
                         ("NewStarts", "boundary_start"), ("Transfers", "transfer"),
                         ("UCCalibrations", "ordinary_calibration_completion")):
        add(suffix, counts[kind], [all_edges[i] for i, actual in enumerate(kinds) if actual == kind], "number of selected edges classified as " + kind)
    for name, sid in zip(CORE_NAMES, core):
        add(name + "State", sid, [state_pointer(sid, "id")])
    add("MinimumOperationalArms", min(states[sid]["physical_operational_arms"] for sid in sequence),
        [state_pointer(sid, "physical_operational_arms") for sid in sequence], "minimum saved operational-arm count over the selected path, checked against physical states and the calibration probe")
    add("CoreFirstStep", first + 1, [all_edges[first]], "one-based position of the first transfer in the selected path")
    add("CoreLastStep", last + 1, [all_edges[last]], "one-based position of the last transfer or calibration completion in the selected path")
    add("Target", certificate["goal_matches"][str(state)], ["/goal_matches/" + str(state)])
    require(len(values) == 26, "Unexpected PC2 trace macro inventory")
    lines = ["% Generated by scripts/generate_pc2_trace_macros.py; do not edit display values.",
             "% One deterministic saved path, not a new run or an all-entry proof.",
             "% Selection: " + SELECTION_RULE + ".",
             "% Prefix/suffix counts preserve the events omitted from the four-event focus.",
             "% Source paths below are relative to the public artifact root."]
    for record in provenance:
        lines.append("% " + record["derivation"] + "; source pointers:")
        for pointer in record["certificate_pointers"]:
            lines.append("% " + record["source"] + "#" + pointer)
        lines.append("\\newcommand{\\" + record["macro"] + "}{" + str(record["value"]) + "}")
    report = {"status": "PASS", "macro_count": len(values), "values": values,
              "selection_rule": SELECTION_RULE, "selected_state_ids": sequence,
              "source_files": SOURCES, "source_values": provenance,
              "checks": {"fixed_entry_and_edge_rule_reconstructed": True,
                         "selected_path_edges_and_decreasing_ranks_from_certificate": True,
                         "safe_states_complete_goal_and_handover_target": True,
                         "all_display_values_derived_from_public_certificate": True,
                         "omitted_prefix_and_suffix_preserved": True,
                         "saved_physical_operational_counts_match_state_classification": True,
                         "saved_raw_calibration_classification_matches_probe": True,
                         "ordinary_events_uncontrollable_in_saved_model": True,
                         "source_and_raw_files_read_only": True},
              "scope": "Saved-data display consistency only; no solver, experiment, saved checker or adapter execution."}
    return "\n".join(lines) + "\n", report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--emit-patch", action="store_true")
    parser.add_argument("--artifact-root", type=Path)
    args = parser.parse_args()
    output, report = collect(artifact_root(args.artifact_root))
    if args.check:
        require(OUTPUT.is_file() and OUTPUT.read_bytes() == output.encode(), "PC2 trace macros are missing or stale")
        print(json.dumps({**report, "mode": "check"}, ensure_ascii=False))
        return
    if args.emit_patch:
        require(not OUTPUT.exists(), "--emit-patch only creates a missing output")
        print("*** Begin Patch\n*** Add File: " + str(OUTPUT))
        for line in output.splitlines():
            print("+" + line)
        print("*** End Patch")
        return
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(output)
    print(json.dumps({**report, "mode": "generate"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
