#!/usr/bin/env python3
"""Read-only static sufficient-condition check for R1 under the existing E meaning.

Run with Python 3; no Java, synthesis, or plant-history enumeration is invoked.
Only the requested CSV is written. Historical rs_coverage classifications remain
unchanged. The restricted FSP reader rejects syntax outside this saved cohort.

Proof basis: each source formula is GLOBALLY(guard => NOT event_predicates).
The initially false guard is changed only by actual update commands. Source-
audited namespace/endpoint rules and saved successful input validation imply
that the modeled old endpoint cannot execute those commands. Its guard is
therefore false at entry, irrespective of the entry action-predicate values.
The initial invariant is true. One hotSwapIn resets every action predicate and
leaves the guard false; there are no temporal obligations beyond this invariant.
The reference now has the canonical valuation. Exhaustive transition matching
below identifies its continuation language with compiled boundary state zero.

This is a NEW syntax-restricted sufficient condition, not a rerun or extension
of historical E-prime flags, nor a change to interpretation E. It relies on the
source-audited entry/namespace semantics listed below and on saved exports.
It does not certify physical histories, application intent, or runtime adapters.
"""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import itertools
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
SUBMISSION = (Path(__import__("os").environ["FGDUCS_PACKAGE_ROOT"]) if "FGDUCS_PACKAGE_ROOT" in __import__("os").environ else next(p for p in HERE.parents if (p / "Implementation/Experiment/Models").is_dir())) / "FSE2027_SUBMISSION_20260914"
REPOSITORY = SUBMISSION.parent
RS = SUBMISSION / "experiments/rs_coverage"
EXPORTS = RS / "raw/expanded-predicates"
RUNS = SUBMISSION / "experiments/rq3_xeon/raw/rq3/runs"
MODEL_DIR = REPOSITORY / "Implementation/Experiment/Models"
JAVA = "Implementation/Source Code/maven-root/mtsa/src/main/java/ltsa/updatingControllers/otf/"
SOURCE_BASIS = "; ".join([
    JAVA + "FineGrainedUpdateProblem.java:467-494 (namespace/component alphabets)",
    JAVA + "MtsaRevisedOtfDucsAdapter.java:1795-1827,1896-1937 (normal-only endpoints)",
    JAVA + "MtsaRevisedOtfDucsAdapter.java:1633-1634,2179-2196 (one boundary step)",
    JAVA + "FineGrainedUpdateProblem.java:613-628 (install without another step)",
    JAVA + "SafetyTester.java:70-78 (outside-alphabet stutter)",
])
EXPECTED_COUNTS = {
    "gsm": 1, "industry": 3, "metasocket": 1, "powerplant": 3,
    "productioncell_arms1": 6, "productioncell_arms2": 12,
    "railcab": 7, "surveillance": 7, "workflow": 6,
}
ENTRY = "hotSwapIn"
ERROR = -1
OTHER = "__R1_ENTRY_UNMENTIONED_LABEL__"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def relative(path):
    return (path.relative_to(REPOSITORY).as_posix() if path.is_relative_to(REPOSITORY) else "<OUTPUT>/" + path.relative_to(HERE).as_posix())


def source_text(path):
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"/\*.*?\*/", lambda m: "\n" * m[0].count("\n"), text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def definition(text, kind, name):
    found = list(re.finditer(
        r"(?m)^[ \t]*" + re.escape(kind) + r"[ \t]+" + re.escape(name)
        + r"[ \t]*=[ \t]*([^\n]+)", text))
    require(len(found) == 1, f"Expected one {kind} definition: {name}")
    m = found[0]
    return m[1].strip(), text.count("\n", 0, m.start()) + 1


def split_commas(text):
    depth = 0
    start = 0
    parts = []
    for pos, ch in enumerate(text):
        if ch in "{[(":
            depth += 1
        elif ch in "}])":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append(text[start:pos].strip())
            start = pos + 1
        require(depth >= 0, "Unbalanced action expression")
    require(depth == 0, "Unbalanced action expression")
    parts.append(text[start:].strip())
    return parts


def action_set(expr, text, stack=()):
    expr = expr.strip()
    if expr.startswith("{") and expr.endswith("}"):
        return set().union(*(action_set(p, text, stack)
                             for p in split_commas(expr[1:-1])))
    if re.fullmatch(r"[A-Z][A-Za-z0-9_]*", expr):
        require(expr not in stack, "Cyclic set alias")
        body, _ = definition(text, "set", expr)
        return action_set(body, text, stack + (expr,))
    require(bool(re.fullmatch(r"[a-z][A-Za-z0-9_]*(?:\[\d+\])*(?:\.\d+)*", expr)),
            f"Unsupported action syntax: {expr}")
    return {re.sub(r"\[(\d+)\]", r".\1", expr)}


def source_form(row, text):
    formula, formula_line = definition(text, "ltl_property", row["requirement"])
    match = re.fullmatch(r"\[\]\s*\(\s*([A-Za-z_]\w*)\s*->\s*!\s*(.+)\s*\)", formula)
    require(match is not None, "Not a pure guarded invariant")
    guard_name, forbidden_expr = match[1], match[2].strip()
    assertion = ""
    if re.fullmatch(r"[A-Z]\w*", forbidden_expr):
        assertion, _ = definition(text, "assert", forbidden_expr)
        require(assertion.startswith("(") and assertion.endswith(")"),
                "Unsupported assertion syntax")
        terms = [p.strip() for p in assertion[1:-1].split("||")]
        forbidden = set().union(*(action_set(p, text) for p in terms))
    else:
        forbidden = action_set(forbidden_expr, text)
    guard_definition, guard_line = definition(text, "fluent", guard_name)
    guard_match = re.fullmatch(r"<(.+)>", guard_definition)
    require(guard_match is not None, "Guard must use default false initial value")
    fields = split_commas(guard_match[1])
    require(len(fields) == 2, "Guard must have initiating and terminating sets")
    return dict(formula=formula, formula_line=formula_line,
                assertion=assertion, guard_name=guard_name,
                guard_definition=guard_definition, guard_line=guard_line,
                stop=action_set(fields[0], text),
                start=action_set(fields[1], text), forbidden=forbidden)


def metric(log, key):
    pattern = r"(?m)^.*\[" + re.escape(key) + r"\]\s*:\s*(.+)$"
    found = list(re.finditer(pattern, log))
    require(len(found) == 1, f"Missing/duplicate saved metric: {key}")
    return found[0][1].strip(), log.count("\n", 0, found[0].start()) + 1


def raw_step(row, edges, state, action):
    if state == ERROR:
        return ERROR
    if action not in row["alphabet"]:
        return state
    # This is the existing export/checker convention for a missing local edge.
    return edges.get((state, action), ERROR)


def check_condition(row, spec, update_actions, model_alphabet):
    require(row["initializer_mode"] == "constant_after_hotSwapIn", "Wrong initializer mode")
    require(row["monitor_nonerror_states"] == 2 and row["monitor_initial"] == 0
            and row["boundary_state_after_hotSwapIn"] == 0 and row["error_state"] == ERROR,
            "Wrong monitor/boundary shape")
    fluents = row["referenced_fluents"]
    guards = [f for f in fluents if f["kind"] == "declared_fluent"]
    events = [f for f in fluents if f["kind"] == "event_predicate"]
    require(len(guards) == 1 and events and len(guards) + len(events) == len(fluents),
            "Unsupported observer kinds")
    guard = guards[0]
    require(guard["name"] == spec["guard_name"] and guard["initial_value"] is False,
            "Guard name/initial value mismatch")
    stop, start, forbidden = spec["stop"], spec["start"], spec["forbidden"]
    require(stop and start and forbidden and not stop & start, "Invalid guard/event sets")
    require(set(guard["initiating"]) == stop and set(guard["terminating"]) == start,
            "Source/export guard mismatch")
    require(stop | start <= update_actions, "Guard event outside actual update commands")
    require(ENTRY not in update_actions and not forbidden & (update_actions | {ENTRY}),
            "Forbidden action is not an ordinary event")
    for f in events:
        require(f["initial_value"] is False and f["terminating"] == ["*"]
                and ENTRY not in f["initiating"], "Entry does not reset event observer")
    require(set().union(*(set(f["initiating"]) for f in events)) == forbidden,
            "Source/export forbidden-event mismatch")
    edges = {}
    for source, action, target in row["transitions"]:
        require(source in (0, 1) and target in (ERROR, 0, 1)
                and action != "tau" and action in row["alphabet"], "Malformed visible edge")
        require((source, action) not in edges, "Duplicate/nondeterministic edge")
        edges[source, action] = target
    # Cross-monitor labels plus OTHER cover every finite label class; labels
    # outside the local alphabet stutter, while ERROR is absorbing.
    labels = (set(model_alphabet) | set(row["alphabet"]) | update_actions
              | stop | start | forbidden | {ENTRY, OTHER}) - {"tau"}
    require(OTHER not in set(model_alphabet) | set(row["alphabet"]) | update_actions,
            "OTHER sentinel collides with a real label")
    for state, action in itertools.product((ERROR, 0, 1), sorted(labels)):
        expected = (ERROR if state == ERROR else
                    1 if action in stop else 0 if action in start else
                    ERROR if state == 1 and action in forbidden else state)
        actual = raw_step(row, edges, state, action)
        require(actual == expected,
                f"DFA mismatch at state={state}, label={action}: {actual} != {expected}")
    # All possible entry action-predicate values, not alleged reachable histories.
    # Guard false makes the initial invariant true. After exactly one entry all
    # predicates become false; no previous obligation exists for this pure form.
    valuations = 0
    for values in itertools.product((False, True), repeat=len(events)):
        require(not (False and any(values)), "Initial invariant violated")
        post = [True if ENTRY in f["initiating"] else False
                if ENTRY in f["terminating"] or "*" in f["terminating"] else value
                for f, value in zip(events, values)]
        require(not any(post) and ENTRY not in stop | start,
                "Entry does not establish canonical valuation")
        valuations += 1
    return len(labels), 3 * len(labels), valuations


def negative_checks(row, spec, commands, alphabet):
    cases = []
    def reject(name, mutate):
        bad, changed_spec, changed_commands = copy.deepcopy(row), copy.deepcopy(spec), set(commands)
        mutate(bad, changed_spec, changed_commands)
        try:
            check_condition(bad, changed_spec, changed_commands, alphabet)
        except ValueError:
            cases.append(name)
        else:
            raise AssertionError("Negative check incorrectly passed: " + name)
    reject("initially_true_guard", lambda r, s, c:
           next(f for f in r["referenced_fluents"] if f["kind"] == "declared_fluent")
           .update(initial_value=True))
    reject("guard_event_allowed_before_entry", lambda r, s, c: c.remove(sorted(s["stop"])[0]))
    def bad_entry(r, s, c):
        r["alphabet"].append(ENTRY)
        r["transitions"].extend([[0, ENTRY, 1], [1, ENTRY, 1]])
    reject("entry_changes_guard", bad_entry)
    def missing_local_edge(r, s, c):
        event = sorted(s["forbidden"])[0]
        r["transitions"] = [t for t in r["transitions"] if t[:2] != [0, event]]
    reject("missing_declared_stutter_edge", missing_local_edge)
    def missing_label(r, s, c):
        event = sorted(s["forbidden"])[0]
        r["alphabet"].remove(event)
        r["transitions"] = [t for t in r["transitions"] if t[1] != event]
    reject("missing_forbidden_label", missing_label)
    def bad_error(r, s, c):
        event = sorted(s["forbidden"])[0]
        for t in r["transitions"]:
            if t[:2] == [1, event]:
                t[2] = 1
    reject("forbidden_event_not_rejected", bad_error)
    reject("event_observer_not_reset", lambda r, s, c:
           next(f for f in r["referenced_fluents"] if f["kind"] == "event_predicate")
           .update(terminating=[]))
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "r1-entry-invariant-verification.csv")
    args = parser.parse_args()
    require(args.output.resolve().parent == HERE, "Output must remain in evidence/")
    historical_path = RS / "summary.csv"
    historical_bytes = historical_path.read_bytes()
    historical = {(r["model"], r["target"], r["requirement"]): r
                  for r in csv.DictReader(historical_bytes.decode().splitlines())}
    output = []
    controls = None
    for model, expected_count in EXPECTED_COUNTS.items():
        export_path = EXPORTS / (model + ".json")
        data = json.loads(export_path.read_text())
        source_path = MODEL_DIR / data["source_name"]
        digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
        export_log = (EXPORTS / (model + ".log")).read_text()
        require(f"INPUT_SHA256={digest}" in export_log and "EXIT=0" in export_log,
                "Source/export provenance mismatch")
        run_dir = RUNS / (model + "__r1__rep01__fg_ducs_otf")
        meta = json.loads((run_dir / "meta.json").read_text())
        require(meta["input_model"]["sha256"] == digest, "Source/campaign input mismatch")
        log_path = run_dir / "output.txt"
        log = log_path.read_text()
        valid, validation_line = metric(log, "revised_internal_input_validation")
        require(valid == "passed", "No passed input-validation evidence")
        sequence, sequence_line = metric(log, "revised_update_policy_fixed_sequence")
        commands = set(sequence.split(">"))
        require(len(commands) == len(sequence.split(">")), "Duplicate update sequence labels")
        text = source_text(source_path)
        rows = [r for r in data["requirements"] if r["kind"] == "upd" and r["target"] == "r1"]
        require(len(rows) == expected_count, "Unexpected R1 occurrence count")
        alphabet = set().union(*(set(r["alphabet"]) for r in data["requirements"]))
        for row in rows:
            spec = source_form(row, text)
            labels, checks, valuations = check_condition(row, spec, commands, alphabet)
            previous = historical[model, "r1", row["requirement"]]
            require(previous["rs_E_ah_exact"] == "False"
                    and previous["e_reference_language_available"] == "False"
                    and previous["rs_E_ah_boundary_matches"] == "True",
                    "Unexpected historical classification; review scope explicitly")
            if controls is None:
                controls = negative_checks(row, spec, commands, alphabet)
            output.append(dict(
                model=model, target="r1", requirement=row["requirement"],
                static_entry_invariant_condition="PASS",
                interpretation="existing entry-scoped E; fresh before one hotSwapIn",
                formula=spec["formula"], formula_alias_expansion=spec["assertion"],
                guard=spec["guard_name"], guard_source=spec["guard_definition"],
                guard_initial=False, stop_events=";".join(sorted(spec["stop"])),
                start_events=";".join(sorted(spec["start"])),
                forbidden_ordinary_events=";".join(sorted(spec["forbidden"])),
                actual_update_sequence=sequence, guard_events_in_actual_updates=True,
                input_validation=valid, boundary_state=row["boundary_state_after_hotSwapIn"],
                labels_checked=labels, state_label_pairs_checked=checks,
                arbitrary_entry_predicate_valuations_checked=valuations,
                historical_E_prime_exact=previous["rs_E_ah_exact"],
                historical_reference_language_available=previous["e_reference_language_available"],
                source_path=relative(source_path), source_formula_line=spec["formula_line"],
                source_guard_line=spec["guard_line"], export_path=relative(export_path),
                export_selector="requirements[target=r1,kind=upd,requirement=" + row["requirement"] + "]",
                saved_run_log=relative(log_path), input_validation_line=validation_line,
                update_sequence_line=sequence_line, source_audited_entry_basis=SOURCE_BASIS,
                scope="modeled old endpoint; source-audited namespaces/entry; no plant-history enumeration",
            ))
    require(len(output) == 46, "Expected all 46 R1 occurrences")
    require(historical_path.read_bytes() == historical_bytes, "Historical summary changed")
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(output[0]))
        writer.writeheader()
        writer.writerows(output)
    print("STATIC_ENTRY_INVARIANT_PASS=46/46")
    print("NEGATIVE_CHECKS_REJECTED=" + str(len(controls)) + ": " + ", ".join(controls))
    print("HISTORICAL_E_PRIME_CLASSIFICATION_UNCHANGED")
    print("SOURCE_AUDITED_ENTRY_SEMANTICS_REQUIRED; NOT_A_PHYSICAL_HISTORY_CHECK")
    print("CSV=" + relative(args.output.resolve()))


if __name__ == "__main__":
    main()
