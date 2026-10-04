#!/usr/bin/env python3
"""Finite analysis of existing NEW source formulas and saved monitor exports.

No Java, solver, performance trial, input mutation, or manuscript generation.
The restricted source reader fails closed on syntax outside the grammar below.
Source propositions and fluent event sets are interpreted independently of the
saved DFA.  Only the DFA transition relation is read from the monitor exports.
The alphabet includes all saved frontend observer labels and one fresh OTHER
representative.  Thus update labels may repeat; these are free words, not plant
histories or one-shot executions.  Physical decoding/activation is out of scope.
"""
from __future__ import annotations

import argparse
from collections import Counter, deque
from copy import deepcopy
import csv
import json
from pathlib import Path
import re


ERROR = -1
OTHER = "__C72_UNMENTIONED_EVENT__"
EXPECTED = {"gsm": 1, "industry": 3, "metasocket": 1, "powerplant": 3,
            "productioncell_arms1": 6, "productioncell_arms2": 12,
            "railcab": 7, "surveillance": 7, "workflow": 6}


class Unsupported(ValueError):
    pass


def need(test, message):
    if not test:
        raise Unsupported(message)


def split_top(text, separator):
    depth = 0
    parts, start = [], 0
    for i, char in enumerate(text):
        if char in "{[(":
            depth += 1
        elif char in "}])":
            depth -= 1
        elif char == separator and depth == 0:
            parts.append(text[start:i].strip())
            start = i + 1
        need(depth >= 0, "Unbalanced grouping: " + text)
    need(depth == 0, "Unbalanced grouping: " + text)
    parts.append(text[start:].strip())
    return parts


def canonical(atom):
    return re.sub(r"\[(\d+)\]", r".\1", atom)


class Source:
    def __init__(self, path):
        self.path = path
        text = path.read_text()
        text = re.sub(r"/\*.*?\*/", lambda m: "\n" * m[0].count("\n"), text, flags=re.S)
        self.text = re.sub(r"//[^\n]*", "", text)

    def definition(self, kind, name):
        pat = r"(?m)^[ \t]*" + kind + r"[ \t]+" + re.escape(name) + r"[ \t]*=[ \t]*"
        matches = list(re.finditer(pat, self.text))
        need(len(matches) == 1, f"Expected one {kind} {name}, found {len(matches)}")
        match = matches[0]
        tail = self.text[match.end():]
        parts = []
        for line in tail.splitlines():
            parts.append(line)
            body = " ".join(parts).strip()
            balances = [body.count(a) - body.count(b) for a, b in [("(", ")"), ("[", "]"), ("{", "}")]]
            if kind == "fluent":
                balances.append(body.count("<") - body.count(">"))
            need(all(x >= 0 for x in balances), "Unbalanced definition: " + name)
            if all(x == 0 for x in balances):
                return body, self.text.count("\n", 0, match.start()) + 1
        raise Unsupported("Unterminated definition: " + name)

    def integer(self, expr, bindings=None, trail=()):
        bindings = bindings or {}
        expr = expr.strip()
        if re.fullmatch(r"\d+", expr):
            return int(expr)
        if expr in bindings:
            return bindings[expr]
        need(re.fullmatch(r"[A-Z]\w*", expr) is not None and expr not in trail,
             "Unsupported integer expression: " + expr)
        body, _ = self.definition("const", expr)
        return self.integer(body, bindings, trail + (expr,))

    def indices(self, expr, bindings=None, trail=()):
        expr = expr.strip()
        if ".." in expr:
            parts = expr.split("..")
            need(len(parts) == 2, "Unsupported range: " + expr)
            lo, hi = (self.integer(x, bindings) for x in parts)
            need(0 <= lo <= hi <= 10000, "Invalid or excessive range: " + expr)
            return list(range(lo, hi + 1))
        if re.fullmatch(r"[A-Z]\w*", expr) and re.search(r"(?m)^\s*range\s+" + re.escape(expr) + r"\s*=", self.text):
            need(expr not in trail, "Cyclic range: " + expr)
            body, _ = self.definition("range", expr)
            return self.indices(body, bindings, trail + (expr,))
        return [self.integer(expr, bindings)]

    def actions(self, expr, bindings=None, trail=()):
        expr = expr.strip()
        differences = split_top(expr, "\\")
        if len(differences) > 1:
            result = self.actions(differences[0], bindings, trail)
            for part in differences[1:]:
                result -= self.actions(part, bindings, trail)
            return result
        if expr.startswith("{") and expr.endswith("}"):
            return set().union(*(self.actions(p, bindings, trail) for p in split_top(expr[1:-1], ",")))
        if re.fullmatch(r"[A-Z]\w*", expr):
            need(expr not in trail, "Cyclic set alias: " + expr)
            body, _ = self.definition("set", expr)
            return self.actions(body, bindings, trail + (expr,))
        match = re.fullmatch(r"([a-z]\w*(?:\.[A-Za-z0-9_]+)*)(\[[^\]]+\])*", expr)
        need(match is not None, "Unsupported event/set expression: " + expr)
        base = re.match(r"[a-z]\w*(?:\.[A-Za-z0-9_]+)*", expr)[0]
        labels = [base]
        for group in re.findall(r"\[([^\]]+)\]", expr[len(base):]):
            labels = [a + "." + str(i) for a in labels for i in self.indices(group, bindings)]
        return set(labels)

    def fluent(self, atom):
        if atom[0].islower():
            events = self.actions(atom)
            need(len(events) == 1, "An action proposition must name one event: " + atom)
            return dict(name=canonical(atom), initial_value=False, initiating=sorted(events),
                        terminating=["*"], kind="event_predicate", source_atom=atom)
        match = re.fullmatch(r"([A-Z]\w*)((?:\[\d+\])*)", atom)
        need(match is not None, "Unsupported fluent atom: " + atom)
        base, actual = match[1], [int(x) for x in re.findall(r"\[(\d+)\]", match[2])]
        names = re.findall(r"(?m)^\s*fluent\s+(" + re.escape(base) + r"(?:\[[^\]]+\])*)\s*=", self.text)
        need(len(names) == 1, "Missing/ambiguous fluent declaration: " + atom)
        declared = names[0]
        params = re.findall(r"\[([^\]]+)\]", declared[len(base):])
        need(len(params) == len(actual), "Fluent arity mismatch: " + atom)
        bindings = {}
        for param, value in zip(params, actual):
            parts = param.split(":")
            need(len(parts) == 2 and re.fullmatch(r"[a-z]\w*", parts[0]) is not None,
                 "Unsupported fluent parameter: " + param)
            need(value in self.indices(parts[1]), "Fluent index outside declared range: " + atom)
            bindings[parts[0]] = value
        body, line = self.definition("fluent", declared)
        parsed = re.fullmatch(r"<(.+)>\s*(?:initially\s+([01]))?", body)
        need(parsed is not None, "Unsupported fluent body: " + body)
        terms = split_top(parsed[1], ",")
        need(len(terms) == 2, "Expected initiating and terminating sets: " + body)
        initiating, terminating = (self.actions(x, bindings) for x in terms)
        need(not (initiating & terminating), "Overlapping fluent event sets: " + atom)
        return dict(name=canonical(atom), initial_value=parsed[2] == "1",
                    initiating=sorted(initiating), terminating=sorted(terminating),
                    kind="declared_fluent", source_atom=atom, source_line=line,
                    source_definition=body)


class Formula:
    token = re.compile(r"\s*(->|&&|\|\||[!()]|[A-Za-z_]\w*(?:\.[A-Za-z0-9_]+)*(?:\[\d+\])*)")

    def __init__(self, source, text, trail=()):
        self.source, self.trail, self.tokens, self.i = source, trail, [], 0
        pos = 0
        while pos < len(text.rstrip()):
            match = self.token.match(text, pos)
            need(match is not None, "Unsupported formula syntax near: " + text[pos:])
            self.tokens.append(match[1])
            pos = match.end()
        self.ast = self.implication()
        need(self.i == len(self.tokens), "Trailing formula tokens: " + str(self.tokens[self.i:]))

    def eat(self, token):
        if self.i < len(self.tokens) and self.tokens[self.i] == token:
            self.i += 1
            return True
        return False

    def implication(self):
        left = self.disjunction()
        return ("implies", left, self.implication()) if self.eat("->") else left

    def disjunction(self):
        result = self.conjunction()
        while self.eat("||"):
            result = ("or", result, self.conjunction())
        return result

    def conjunction(self):
        result = self.unary()
        while self.eat("&&"):
            result = ("and", result, self.unary())
        return result

    def unary(self):
        if self.eat("!"):
            return ("not", self.unary())
        if self.eat("("):
            result = self.implication()
            need(self.eat(")"), "Missing closing parenthesis")
            return result
        need(self.i < len(self.tokens), "Missing formula operand")
        atom = self.tokens[self.i]
        self.i += 1
        need(re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z0-9_]+)*(?:\[\d+\])*", atom) is not None,
             "Invalid formula atom: " + atom)
        if re.search(r"(?m)^\s*assert\s+" + re.escape(atom) + r"\s*=", self.source.text):
            need(atom not in self.trail, "Cyclic assertion alias: " + atom)
            body, _ = self.source.definition("assert", atom)
            return Formula(self.source, body, self.trail + (atom,)).ast
        return ("atom", atom)


def atoms(ast):
    if ast[0] == "atom":
        return {ast[1]}
    return set().union(*(atoms(child) for child in ast[1:]))


def evaluate(ast, values):
    op = ast[0]
    if op == "atom":
        return values[canonical(ast[1])]
    if op == "not":
        return not evaluate(ast[1], values)
    left, right = evaluate(ast[1], values), evaluate(ast[2], values)
    if op == "and":
        return left and right
    if op == "or":
        return left or right
    if op == "implies":
        return not left or right
    raise Unsupported("Unknown formula operation: " + op)


def semantic_signature(f):
    return bool(f["initial_value"]), tuple(sorted(f["initiating"])), tuple(sorted(f["terminating"]))


def advance(values, fluents, event):
    return tuple(True if event in f["initiating"] else
                 False if event in f["terminating"] or "*" in f["terminating"] else value
                 for value, f in zip(values, fluents))


def monitor(row):
    alpha = set(row["alphabet"])
    edges = {}
    need(row["monitor_initial"] != ERROR, "Initially ERROR monitor")
    need(row["monitor_initial"] in range(row["monitor_nonerror_states"]), "Invalid initial monitor state")
    need(row["error_state"] == ERROR, "Unexpected ERROR-state convention")
    for source, event, target in row["transitions"]:
        need(event != "tau", "Uneliminated tau transition")
        need(event in alpha, "DFA transition outside declared alphabet")
        need(source in range(row["monitor_nonerror_states"]) or source == ERROR, "Invalid source state")
        need(target in range(row["monitor_nonerror_states"]) or target == ERROR, "Invalid target state")
        need((source, event) not in edges or edges[source, event] == target, "Nondeterministic DFA")
        if source == ERROR:
            need(target == ERROR, "Nonabsorbing ERROR")
        edges[source, event] = target
    def step(state, event):
        # Export decoding: outside alphabet -> stutter; a missing transition
        # inside the alphabet -> ERROR.  ERROR absorbs every subsequent label.
        return ERROR if state == ERROR else state if event not in alpha else edges.get((state, event), ERROR)
    return step


def path(parent, pair):
    result = []
    while parent[pair] is not None:
        pair, event = parent[pair]
        result.append(event)
    return list(reversed(result))


def analyze(source, row, actual, old_csv):
    body, line = source.definition("ltl_property", row["requirement"])
    need(body.startswith("[]"), "Not a global invariant: " + body)
    formula = Formula(source, body[2:].strip()).ast
    source_fluents = {canonical(atom): source.fluent(atom) for atom in sorted(atoms(formula))}
    references = row["referenced_fluents"]
    need(set(source_fluents) == {canonical(f["name"]) for f in references}, "Source/export proposition sets differ")
    fluents = [source_fluents[canonical(f["name"])] for f in references]
    need(len(fluents) == len(source_fluents), "Duplicate exported proposition")
    for parsed, saved in zip(fluents, references):
        need(semantic_signature(parsed) == semantic_signature(saved), "Source/export observer semantics differ: " + parsed["name"])
        need(parsed["kind"] == saved["kind"], "Source/export atom kind differs: " + parsed["name"])
    need(Counter(semantic_signature(f) for f in fluents) ==
         Counter(semantic_signature(f) for f in actual["observers_in_actual_column_order"]),
         "Source/actual observer semantics differ")
    actual_monitor = actual["monitor"]
    need((actual_monitor["initial_state"], actual_monitor["nonerror_states"], actual_monitor["error_state"]) ==
         (row["monitor_initial"], row["monitor_nonerror_states"], ERROR), "Actual/export monitor states differ")
    need(set(actual_monitor["alphabet"]) == set(row["alphabet"]) and
         set(map(tuple, actual_monitor["transitions"])) == set(map(tuple, row["transitions"])),
         "Actual/export monitor transitions differ")
    alpha = set(row["alphabet"]) - {"tau"}
    for f in fluents:
        alpha.update(f["initiating"])
        alpha.update(set(f["terminating"]) - {"*"})
    for column in actual["observers_in_actual_column_order"]:
        need("tau" not in column["alphabet"], "Unexpected tau in actual observer alphabet")
        alpha.update(column["alphabet"])
    need(OTHER not in alpha, "OTHER representative collides with named event")
    alpha.add(OTHER)
    alpha = sorted(alpha)
    step = monitor(row)
    def phi(values):
        return evaluate(formula, {f["name"]: value for f, value in zip(fluents, values)})
    initial = row["monitor_initial"], tuple(f["initial_value"] for f in fluents)
    parent, queue, mismatches, transitions = {initial: None}, deque([initial]), [], 0
    current_formula_failures = 0
    rejected_steps = 0
    outside_alphabet_steps = 0
    if not phi(initial[1]):
        mismatches.append(dict(kind="initial_formula_false", values=list(initial[1])))
    while queue:
        state, values = pair = queue.popleft()
        if not phi(values):
            current_formula_failures += 1
            mismatches.append(dict(kind="current_formula_false", prefix=path(parent, pair),
                                   monitor_state=state, values=list(values)))
        for event in alpha:
            new_values, target = advance(values, fluents, event), step(state, event)
            transitions += 1
            truth = phi(new_values)
            rejected_steps += target == ERROR
            outside_alphabet_steps += event not in row["alphabet"]
            if (target == ERROR) != (not truth):
                mismatches.append(dict(kind="error_iff_formula_failed", prefix=path(parent, pair), event=event,
                                       monitor_state=state, values=list(values), next_state=target,
                                       next_values=list(new_values), next_formula=truth))
            successor = target, new_values
            if target != ERROR and successor not in parent:
                need(len(parent) < 200000, "Safe product exceeds explicit analysis cap")
                parent[successor] = pair, event
                queue.append(successor)
    need(all(step(ERROR, event) == ERROR for event in alpha), "Nonabsorbing decoded ERROR")
    cells = json.loads(old_csv["a_reconstructed_lookup"])
    for cell in cells:
        pair = cell["state"], tuple(cell["values"])
        if pair not in parent or not phi(pair[1]):
            mismatches.append(dict(kind="saved_nonerror_cell_not_safe_source_pair", cell=cell,
                                   pair_reached=pair in parent, formula=phi(pair[1])))
    return dict(status="PASS" if not mismatches else "MISMATCH", source_property_line=line,
                source_formula=body, expanded_formula_ast=formula, source_fluents=fluents,
                initial_monitor_nonerror=initial[0] != ERROR,
                initial_formula=phi(initial[1]), empty_prefix_checked=True,
                current_formula_pairs_checked=len(parent), current_formula_failures=current_formula_failures,
                safe_product_pairs=len(parent), alphabet=alpha,
                transitions_checked=transitions, saved_nonerror_cells=len(cells),
                rejected_steps=rejected_steps, outside_alphabet_stutter_steps=outside_alphabet_steps,
                error_absorption="Required by export decoding; every stored ERROR edge is checked to target ERROR",
                other_representative=dict(label=OTHER, named_events_covered=len(alpha)-1,
                    justification="Every other unnamed event stutters in the DFA and declared fluents and resets implicit action predicates; all named DFA/source/observer events are explicit"),
                mismatch_count=len(mismatches), mismatches=mismatches,
                induction_scope="DFA-safe reachable product; every label and first ERROR frontier; finite free words",
                monitor_structure=dict(initial=row["monitor_initial"], states=row["monitor_nonerror_states"],
                                       alphabet=sorted(row["alphabet"]), transitions=sorted(row["transitions"])))


def analysis_controls(root):
    """Small in-memory parser/negative controls, not additional model runs."""
    source = Source(root / "tool/models/GSM_FG.lts")
    ast = Formula(source, "a -> b && !c || d").ast
    for mask in range(16):
        a, b, c, d = (bool(mask & (1 << i)) for i in range(4))
        need(evaluate(ast, dict(a=a, b=b, c=c, d=d)) == ((not a) or (b and not c) or d),
             "Boolean precedence control failed")
    rejected = []
    for text in ("[]a", "<>a", "X(a)", "a U b", "a <-> b"):
        try:
            Formula(source, text)
        except Unsupported:
            rejected.append(text)
    need(len(rejected) == 5, "Unsupported temporal syntax was accepted")
    surveillance = Source(root / "tool/models/Surveillance_FG.lts")
    need(surveillance.actions("{AlphabetNew}\\{EnergyConsumingActionsNew}") ==
         {"return2base", "takeoff", "scan.val.0", "scan.val.1", "pictureOk.0", "pictureOk.1", "lowBattery"},
         "Source set-alias/difference/range control failed")
    export = json.loads((root / "results/initialization/raw/expanded-predicates/gsm.json").read_text())
    row = next(r for r in export["requirements"] if r["kind"] == "new" and r["target"] == "base")
    actual = json.loads((root / "results/supplement-checks/frontend_lookup_demo/runs/gsm__base/lookup.json").read_text())["requirements"][0]
    old_rows = csv.DictReader((root / "results/initialization/summary.csv").open())
    old = next(r for r in old_rows if r["model"] == "gsm" and r["target"] == "base" and r["kind"] == "new")
    false_accept, fa_actual = deepcopy(row), deepcopy(actual)
    false_accept["transitions"] = [[s, a, 0 if a == "decode.2" else t] for s, a, t in row["transitions"]]
    fa_actual["monitor"]["transitions"] = deepcopy(false_accept["transitions"])
    accept_result = analyze(source, false_accept, fa_actual, old)
    need(any(x["kind"] == "error_iff_formula_failed" and x["next_formula"] is False
             for x in accept_result["mismatches"]), "False-accepting DFA mutation was not detected")
    false_reject, fr_actual = deepcopy(row), deepcopy(actual)
    false_reject["alphabet"] = row["alphabet"] + ["receive"]
    false_reject["transitions"] = row["transitions"] + [[0, "receive", ERROR]]
    fr_actual["monitor"]["alphabet"] = deepcopy(false_reject["alphabet"])
    fr_actual["monitor"]["transitions"] = deepcopy(false_reject["transitions"])
    reject_result = analyze(source, false_reject, fr_actual, old)
    need(any(x["kind"] == "error_iff_formula_failed" and x["next_formula"] is True
             for x in reject_result["mismatches"]), "False-rejecting DFA mutation was not detected")
    return dict(boolean_truth_assignments=16, unsupported_temporal_forms_rejected=rejected,
                source_set_difference_range="PASS", false_accepting_DFA_detected=True,
                false_rejecting_DFA_detected=True, scope="In-memory controls; no input files modified")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--csv", type=Path, help="Optional new per-occurrence CSV summary")
    args = parser.parse_args()
    root, output = args.artifact_root.resolve(), args.output.resolve()
    need(not output.exists(), "Choose a new JSON output file")
    csv_output = args.csv.resolve() if args.csv else None
    need(csv_output is None or (not csv_output.exists() and csv_output != output), "Choose a distinct new CSV output file")
    controls = analysis_controls(root)
    old_rows = list(csv.DictReader((root / "results/initialization/summary.csv").open()))
    old = {(r["model"], r["target"], r["requirement"]): r for r in old_rows if r["kind"] == "new"}
    reports, groups = [], {}
    for model, count in EXPECTED.items():
        exports = json.loads((root / "results/initialization/raw/expanded-predicates" / (model + ".json")).read_text())
        source_path = root / "tool/models" / exports["source_name"]
        source = Source(source_path)
        rows = [r for r in exports["requirements"] if r["kind"] == "new"]
        need(Counter(r["target"] for r in rows) == Counter(dict.fromkeys(("base", "r1", "r2"), count)),
             "Unexpected variant population: " + model)
        for row in rows:
            target, name = row["target"], row["requirement"]
            actual_path = root / "results/supplement-checks/frontend_lookup_demo/runs" / (model + "__" + target) / "lookup.json"
            actual_rows = json.loads(actual_path.read_text())["requirements"]
            selected = [r for r in actual_rows if r["requirement"] == name]
            need(len(selected) == 1, "Missing/duplicate actual monitor: " + name)
            item = dict(model=model, target=target, requirement=name,
                        source_path=source_path.relative_to(root).as_posix(),
                        saved_monitor_path=f"results/initialization/raw/expanded-predicates/{model}.json",
                        actual_lookup_path=actual_path.relative_to(root).as_posix())
            try:
                item.update(analyze(source, row, selected[0], old[model, target, name]))
            except Unsupported as exc:
                item.update(status="UNSUPPORTED_OR_INPUT_INCONSISTENCY", reason=str(exc))
            reports.append(item)
            groups.setdefault((model, name), []).append(item)
    group_rows = []
    for (model, name), rows in groups.items():
        structures = [json.dumps({k: r.get(k) for k in ("expanded_formula_ast", "source_fluents", "monitor_structure")}, sort_keys=True) for r in rows]
        group_rows.append(dict(model=model, requirement=name, variants=[r["target"] for r in rows],
                               all_pass=all(r["status"] == "PASS" for r in rows),
                               identical_source_and_monitor_structure=len(set(structures)) == 1))
    totals = dict(requirement_occurrences=len(reports), model_requirement_groups=len(groups),
                  counts_by_status=dict(Counter(r["status"] for r in reports)),
                  source_and_monitor_identical_three_variant_groups=sum(r["identical_source_and_monitor_structure"] for r in group_rows),
                  safe_product_pairs=sum(r.get("safe_product_pairs", 0) for r in reports),
                  transitions_checked=sum(r.get("transitions_checked", 0) for r in reports),
                  saved_nonerror_cells=sum(r.get("saved_nonerror_cells", 0) for r in reports),
                  mismatch_count=sum(r.get("mismatch_count", 0) for r in reports))
    payload = dict(status="PASS" if totals["counts_by_status"] == {"PASS": 138} else "INCOMPLETE_OR_MISMATCH",
                   analysis_kind="Static finite semantic analysis of saved source and monitors; no synthesis or performance experiment",
                   scope="Finite induction for these 138 saved NEW monitor objects and checked alphabets, including empty prefix and first error; not correctness of the general FSP compiler",
                   parser_independence="Self-contained restricted source parser and Boolean evaluator; imports no existing checker/parser",
                   monitor_decoding=dict(outside_alphabet="self-loop", missing_in_alphabet_transition="ERROR",
                       error="absorbing", tau="Reserved alphabet placeholder only; any tau transition is rejected",
                       source_basis=["tool/source/mtsa/src/main/java/ltsa/updatingControllers/otf/MtsaRevisedOtfDucsAdapter.java:1670-1765",
                                     "tool/source/mtsa/src/main/java/ltsa/updatingControllers/otf/SafetyTester.java:70-101"]),
                   other_class_basis="All named DFA alphabet and source initiating/terminating events plus saved observer alphabets are enumerated; one fresh label represents the complement under the stated update rules",
                   induction_basis="The nonerror initial pair satisfies phi. Every DFA-safe reachable pair satisfies phi. On every represented label the next state is ERROR iff the next source valuation falsifies phi; otherwise the successor pair is explored. Absorbing ERROR retains any earlier violation.",
                   controls=controls,
                   not_checked=["plant history feasibility", "physical state decoding", "actual activation key/fallback",
                                "runtime adapter conformance", "arbitrary FSP/compiler correctness"],
                   counting_note="138 variant occurrences of 46 model/requirement groups, with repeated/related formulas; not independent applications",
                   column_definitions=dict(safe_product_pairs="Reachable nonerror (monitor state, source observer valuation) pairs for this occurrence",
                       transitions_checked="Every safe product pair times every named label plus OTHER; includes transitions to ERROR",
                       saved_nonerror_cells="Entries from the saved reconstructed lookup whose exact (m,v) pair is reachable and satisfies phi",
                       current_formula_failures="Reachable nonerror pairs where the independently evaluated source phi is false",
                       mismatch_count="All recorded initial/current/one-step/lookup inconsistencies; not independent failing cases"),
                   totals=totals, groups=group_rows, requirements=reports)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n")
    if csv_output is not None:
        csv_output.parent.mkdir(parents=True, exist_ok=True)
        fields = ["model", "target", "requirement", "status", "source_path", "source_property_line",
                  "initial_monitor_nonerror", "initial_formula", "empty_prefix_checked", "safe_product_pairs",
                  "current_formula_pairs_checked", "current_formula_failures", "transitions_checked",
                  "saved_nonerror_cells", "rejected_steps", "outside_alphabet_stutter_steps", "mismatch_count", "reason"]
        with csv_output.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(reports)
    print(json.dumps(dict(status=payload["status"], totals=totals,
                         issues=[{k: r[k] for k in ("model", "target", "requirement", "status", "reason", "mismatches") if k in r}
                                 for r in reports if r["status"] != "PASS"]), indent=2))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
