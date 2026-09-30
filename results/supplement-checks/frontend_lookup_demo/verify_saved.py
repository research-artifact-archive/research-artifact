#!/usr/bin/env python3
"""Read-only independent Python reconstruction of actual frontend NEW tables.

Inputs are the saved Java export and the pre-existing rs_coverage exports/CSV.
No Java execution, FG synthesis, physical tuples, or ActivationSpec expansion.
"""
from collections import Counter, defaultdict, deque
from copy import deepcopy
import csv
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(__import__("os").environ["FGDUCS_PACKAGE_ROOT"]) if "FGDUCS_PACKAGE_ROOT" in __import__("os").environ else next(p for p in HERE.parents if (p / "Implementation/Experiment/Models").is_dir())
RS = ROOT / "FSE2027_SUBMISSION_20260914/experiments/rs_coverage"
ERROR = -1


def signature(f):
    return bool(f["initial_value"]), tuple(sorted(f["initiating"])), tuple(sorted(f["terminating"]))


def truth(index, fluent):
    if index not in (0, 1):
        raise ValueError("Observer index is not 0/1")
    return bool(fluent["initial_value"]) if index == 0 else not bool(fluent["initial_value"])


def advance(values, fluents, event):
    return tuple(True if event in f["initiating"] else
                 False if event in f["terminating"] or "*" in f["terminating"] else v
                 for v, f in zip(values, fluents))


def monitor_step(row):
    alpha = set(row["alphabet"])
    edges = defaultdict(set)
    for source, event, target in row["transitions"]:
        if event == "tau":
            raise ValueError("Uneliminated tau transition")
        edges[source, event].add(target)
    if any(len(v) != 1 for v in edges.values()):
        raise ValueError("Monitor is not deterministic")
    def step(state, event):
        if state == ERROR:
            return ERROR
        if event not in alpha:
            return state
        return next(iter(edges[state, event]), ERROR)
    return step


def equivalent(row, left, right, alphabet):
    step = monitor_step(row)
    queue = deque([(left, right)])
    seen = {(left, right)}
    while queue:
        left, right = queue.popleft()
        if (left == ERROR) != (right == ERROR):
            return False
        if left == ERROR:
            continue
        for event in alphabet:
            pair = step(left, event), step(right, event)
            if pair not in seen:
                seen.add(pair)
                queue.append(pair)
    return True


def reconstruct(row, fluents, alphabet):
    """Explore safe prefixes and their first ERROR frontier, with repeated labels.

    Enumerate semantic Boolean values, not exported observer-state transitions.
    Any ERROR-frontier occurrence wins over a safe occurrence for the same key.
    Only language-equivalent safe states may share a key; choose minimum ID.
    """
    step = monitor_step(row)
    initial = row["monitor_initial"], tuple(bool(f["initial_value"]) for f in fluents)
    queue = deque([initial])
    seen = {initial}
    safe = defaultdict(set)
    errors = set()
    safe[initial[1]].add(initial[0])
    while queue:
        state, values = queue.popleft()
        for event in alphabet:
            successor = step(state, event), advance(values, fluents, event)
            if successor[0] == ERROR:
                errors.add(successor[1])
            else:
                safe[successor[1]].add(successor[0])
                if successor not in seen:
                    seen.add(successor)
                    if len(seen) > 200000:
                        raise ValueError("Independent product state cap exceeded")
                    queue.append(successor)
    table = {}
    equivalence_checks = 0
    for values in sorted(set(safe) | errors):
        if values in errors:
            table[values] = ERROR
            continue
        states = sorted(safe[values])
        for other in states[1:]:
            equivalence_checks += 1
            if not equivalent(row, states[0], other, alphabet):
                raise ValueError("Language-distinct safe states share a key")
        table[values] = min(states)
    return table, dict(safe_product_pairs=len(seen), error_frontier_keys=len(errors),
                       safe_and_error_keys=len(set(safe) & errors),
                       nontrivial_equivalence_checks=equivalence_checks)


def reference_alphabet(requirements):
    result = {"__OTHER__"}
    for row in requirements:
        result.update(row["alphabet"])
        for f in row["referenced_fluents"]:
            result.update(f["initiating"])
            result.update(f["terminating"])
    return sorted(a for a in result if a not in {"tau", "*"} and not a.startswith("@"))


def normalized_table(actual):
    columns = actual["observers_in_actual_column_order"]
    result = {}
    for entry in actual["actual_lookup_entries"]:
        key = entry["observer_state_indices"]
        if len(key) != len(columns):
            raise ValueError("Table key arity differs from actual column count")
        values = tuple(truth(index, column) for index, column in zip(key, columns))
        if values in result:
            raise ValueError("Duplicate actual table key")
        target = entry["monitor_state"]
        if target != ERROR and target not in range(actual["monitor"]["nonerror_states"]):
            raise ValueError("Invalid monitor-state target")
        result[values] = target
    if actual["actual_lookup_entry_count"] != len(result):
        raise ValueError("Saved actual entry count differs")
    return result


def as_entries(table):
    return [dict(values=list(values), state=state) for values, state in sorted(table.items())]


def assert_equal(left, right, what):
    if left != right:
        raise ValueError(what)


def check_requirement(actual, saved, reference_alpha, previous):
    monitor = actual["monitor"]
    assert_equal((monitor["nonerror_states"], monitor["initial_state"], monitor["error_state"]),
                 (saved["monitor_nonerror_states"], saved["monitor_initial"], saved["error_state"]), "Monitor-state convention differs")
    assert_equal(set(monitor["alphabet"]), set(saved["alphabet"]), "Monitor alphabet differs")
    assert_equal(set(map(tuple, monitor["transitions"])), set(map(tuple, saved["transitions"])), "Saved monitor transitions differ")
    columns = actual["observers_in_actual_column_order"]
    named = {f["name"]: f for f in saved["frontend_lookup_fluents"]}
    assert_equal(len(named), len(columns), "Observer column count differs")
    assert_equal(set(named), {c["name"] for c in columns}, "Observer column names differ")
    fluents = [named[c["name"]] for c in columns]
    assert_equal(Counter(map(signature, fluents)), Counter(map(signature, saved["referenced_fluents"])), "Frontend/reference fluent semantics differ")
    alpha = set(columns[0]["alphabet"])
    transition_count = 0
    for column, fluent in zip(columns, fluents):
        assert_equal(signature(column), signature(fluent), "Actual/source fluent definition differs")
        assert_equal(set(column["alphabet"]), alpha, "Observer alphabets differ within one table")
        assert_equal((column["nonerror_states"], column["initial_state"]), (2, 0), "Unexpected observer state convention")
        expected = set()
        for state in (0, 1):
            value = truth(state, fluent)
            for event in alpha:
                next_value = advance((value,), (fluent,), event)[0]
                next_index = 0 if next_value == bool(fluent["initial_value"]) else 1
                expected.add((state, event, next_index))
        assert_equal(set(map(tuple, column["transitions"])), expected, "Actual observer transition differs from source semantics")
        assert_equal(len(column["transitions"]), len(expected), "Duplicate observer transition")
        transition_count += len(expected)
    if "tau" in alpha or any(a.endswith("?") for a in alpha):
        raise ValueError("Unexpected unclean frontend alphabet")
    actual_table = normalized_table(actual)
    expected_table, stats = reconstruct(saved, fluents, sorted(alpha))
    assert_equal(actual_table, expected_table, "Actual full lookup table differs from independent reconstruction")
    # Independently repeat over the pre-existing checker's broader/model-wide
    # alphabet and referenced-fluent order; compare both its CSV and this table.
    ref_fluents = saved["referenced_fluents"]
    ref_table, ref_stats = reconstruct(saved, ref_fluents, reference_alpha)
    ref_nonerror = {v: s for v, s in ref_table.items() if s != ERROR}
    csv_nonerror = {tuple(e["values"]): e["state"] for e in json.loads(previous["a_reconstructed_lookup"])}
    assert_equal(ref_nonerror, csv_nonerror, "Pre-existing CSV reconstructed nonerror entries differ")
    assert_equal(sum(s == ERROR for s in ref_table.values()), int(previous["a_reconstructed_error_lookup_entries"]), "Pre-existing CSV ERROR count differs")
    unused = list(range(len(ref_fluents)))
    positions = []
    for fluent in fluents:
        i = next(i for i in unused if signature(ref_fluents[i]) == signature(fluent))
        unused.remove(i)
        positions.append(i)
    reordered_ref = {tuple(values[i] for i in positions): state for values, state in ref_table.items()}
    assert_equal(actual_table, reordered_ref, "Actual/reference-alphabet full tables differ")
    return dict(actual_entries=len(actual_table), nonerror_entries=sum(s != ERROR for s in actual_table.values()),
                error_entries=sum(s == ERROR for s in actual_table.values()), observer_columns=len(columns),
                initially_true_columns=sum(bool(f["initial_value"]) for f in columns),
                observer_transitions_checked=transition_count, actual_alphabet_size=len(alpha),
                reference_alphabet_size=len(reference_alpha),
                actual_only_labels=sorted(alpha - set(reference_alpha)),
                reference_only_labels=sorted(set(reference_alpha) - alpha),
                column_names=[c["name"] for c in columns], reference_positions_for_actual_columns=positions,
                normalized_actual_table=as_entries(actual_table), independent_table=as_entries(expected_table),
                source_rule_product=stats, reference_alphabet_product=ref_stats,
                actual_table_exact_match=True, previous_csv_nonerror_exact_match=True,
                reference_alphabet_full_table_exact_match=True)


def negative_checks(fixtures):
    results = []
    def test(name, fixture, mutation):
        actual, saved, alpha, previous = deepcopy(fixture)
        mutation(actual)
        try:
            check_requirement(actual, saved, alpha, previous)
        except (ValueError, StopIteration) as exc:
            results.append(dict(name=name, detected=True, reason=str(exc)))
        else:
            results.append(dict(name=name, detected=False))
    first = next(f for f in fixtures if any(e["monitor_state"] == ERROR for e in f[0]["actual_lookup_entries"]))
    def change_safe(a):
        next(e for e in a["actual_lookup_entries"] if e["monitor_state"] != ERROR)["monitor_state"] = ERROR
    def suppress_error(a):
        next(e for e in a["actual_lookup_entries"] if e["monitor_state"] == ERROR)["monitor_state"] = 0
    def remove_key(a):
        a["actual_lookup_entries"].pop()
        a["actual_lookup_entry_count"] -= 1
    def omit_transition(a):
        a["observers_in_actual_column_order"][0]["transitions"].pop()
    test("replace_safe_table_entry_with_ERROR", first, change_safe)
    test("replace_ERROR_table_entry_with_safe_state", first, suppress_error)
    test("delete_actual_key_with_consistent_count", first, remove_key)
    test("omit_one_observer_state_event_transition", first, omit_transition)
    swapped = False
    for fixture in fixtures:
        if len(fixture[0]["observers_in_actual_column_order"]) < 2:
            continue
        changed = deepcopy(fixture[0])
        changed["observers_in_actual_column_order"][0], changed["observers_in_actual_column_order"][1] = changed["observers_in_actual_column_order"][1], changed["observers_in_actual_column_order"][0]
        try:
            check_requirement(changed, *fixture[1:])
        except ValueError as exc:
            results.append(dict(name="swap_actual_columns_without_permuting_keys", detected=True,
                                requirement=fixture[0]["requirement"], reason=str(exc)))
            swapped = True
            break
    if not swapped:
        raise ValueError("Could not instantiate a meaningful column-swap negative check")
    # No exported application observer is initially true. Exercise normalization
    # explicitly on a synthetic saved-table unit, not as new Java evidence.
    true_f = dict(name="F", initial_value=True, initiating=["on"], terminating=["off"])
    synthetic = dict(observers_in_actual_column_order=[true_f], monitor=dict(nonerror_states=1),
                     actual_lookup_entry_count=2, actual_lookup_entries=[
                         dict(observer_state_indices=[0], monitor_state=0),
                         dict(observer_state_indices=[1], monitor_state=ERROR)])
    assert_equal(normalized_table(synthetic), {(True,): 0, (False,): ERROR}, "Initially-true normalization unit failed")
    broken = deepcopy(synthetic)
    broken["observers_in_actual_column_order"][0]["initial_value"] = False
    results.append(dict(name="initially_true_zero_index_misread_as_false_synthetic_unit",
                        detected=normalized_table(broken) != normalized_table(synthetic),
                        scope="Python normalization unit only; zero true-initial observers in the 27 Java exports"))
    # The saved application tables have no valuation shared by safe and ERROR
    # prefixes. Check ERROR precedence on a separate explicit Python unit.
    priority_row = dict(monitor_initial=0, alphabet=["safe", "bad"], transitions=[
        [0, "safe", 1], [0, "bad", ERROR], [1, "safe", 1], [1, "bad", 1]])
    inert = dict(name="F", initial_value=False, initiating=[], terminating=[])
    priority_table, priority_stats = reconstruct(priority_row, [inert], ["safe", "bad"])
    assert_equal(priority_stats["safe_and_error_keys"], 1, "ERROR-priority unit does not exercise overlap")
    assert_equal(priority_table, {(False,): ERROR}, "ERROR-priority reconstruction unit failed")
    results.append(dict(name="safe_over_ERROR_priority_synthetic_unit",
                        detected=priority_table != {(False,): 0},
                        scope="Python reconstruction unit only; no safe/ERROR key overlap in the 27 Java exports"))
    if not all(r["detected"] for r in results):
        raise ValueError("A negative check was not detected")
    return results


def main():
    runs = list(csv.DictReader((HERE / "run_summary.csv").open()))
    previous_rows = list(csv.DictReader((RS / "summary.csv").open()))
    previous = {(r["model"], r["target"], r["requirement"]): r for r in previous_rows if r["kind"] == "new"}
    details, summaries, fixtures = [], [], []
    for run in runs:
        folder = HERE / "runs" / run["case"]
        if run["status"] != "EXPORTED":
            summaries.append(dict(case=run["case"], model=run["model"], target=run["target"], requirement="", status=run["status"]))
            continue
        actual = json.loads((folder / "lookup.json").read_text())
        meta = json.loads((folder / "meta.json").read_text())
        assert meta["attempt"] == 1 and meta["exit_code"] == 0
        assert not actual["fg_solver_executed"] and not actual["physical_closure_or_activation_spec_requested"]
        assert actual["endpoint_controller_synthesis_performed"]
        for name, facts in meta["saved_files"].items():
            assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == facts["sha256"]
        saved = json.loads((RS / "raw/expanded-predicates" / (run["model"] + ".json")).read_text())
        alpha = reference_alphabet(saved["requirements"])
        requirements = {r["requirement"]: r for r in saved["requirements"] if r["kind"] == "new" and r["target"] == run["target"]}
        assert set(requirements) == {r["requirement"] for r in actual["requirements"]}
        assert len(requirements) == len(actual["requirements"])
        for row in actual["requirements"]:
            key = run["model"], run["target"], row["requirement"]
            summary = dict(case=run["case"], model=run["model"], target=run["target"], requirement=row["requirement"])
            fixture = row, requirements[row["requirement"]], alpha, previous[key]
            try:
                result = check_requirement(*fixture)
                details.append(dict(**summary, status="MATCH", **result))
                for field in ("actual_entries", "nonerror_entries", "error_entries", "observer_columns", "initially_true_columns", "observer_transitions_checked", "actual_alphabet_size", "reference_alphabet_size"):
                    summary[field] = result[field]
                summary["status"] = "MATCH"
                fixtures.append(fixture)
            except Exception as exc:
                summary["status"] = "MISMATCH_OR_CHECK_ERROR"
                summary["reason"] = type(exc).__name__ + ": " + str(exc)
                details.append(summary.copy())
            summaries.append(summary)
    fields = list(dict.fromkeys(k for row in summaries for k in row))
    with (HERE / "lookup_check_summary.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(summaries)
    mismatches = [r for r in summaries if r["status"] != "MATCH"]
    negatives = negative_checks(fixtures) if fixtures else []
    (HERE / "negative_checks.json").write_text(json.dumps(negatives, indent=2) + "\n")
    totals = dict(java_targets=len(runs), java_exports=sum(r["status"] == "EXPORTED" for r in runs),
                  expected_new_requirements=len(previous), checked_requirements=len(summaries),
                  exact_matches=len(summaries) - len(mismatches), mismatches=mismatches,
                  negative_checks_passed=sum(r["detected"] for r in negatives),
                  actual_table_entries=sum(r.get("actual_entries", 0) for r in summaries),
                  nonerror_entries=sum(r.get("nonerror_entries", 0) for r in summaries),
                  error_entries=sum(r.get("error_entries", 0) for r in summaries),
                  observer_columns=sum(r.get("observer_columns", 0) for r in summaries),
                  initially_true_columns=sum(r.get("initially_true_columns", 0) for r in summaries),
                  observer_transitions_checked=sum(r.get("observer_transitions_checked", 0) for r in summaries),
                  all_required_targets_present=len(summaries) == len(previous) and not mismatches,
                  interpretation="Fresh frontend NEW SafetyStateMapping only; not physical initializer/ActivationSpec/history verification")
    (HERE / "verification_details.json").write_text(json.dumps(dict(totals=totals, requirements=details), indent=2) + "\n")
    print(json.dumps(totals, indent=2))
    if mismatches or len(summaries) != len(previous):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
