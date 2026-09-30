#!/usr/bin/env python3
"""Count declared contract sizes from the nine saved LTS inputs; never run Java.

Only the explicit syntax used by these inputs is supported. Unsupported syntax,
duplicate transfer pairs, or disagreement with the saved frontend exports fails.
T counts declared source/target pairs after literal forall expansion, BEFORE
observer augmentation or state minimization. U counts transfer + stop + start
labels; interval requirements add monitors, not further boundary commands.

Usage: python3 -B generate_contract_sizes.py [--check | --self-test]
The default output directory is this script's directory. --check compares the
existing generated CSV/TeX without writing. Input paths can be supplied to make
the script usable independently of the repository layout.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import tempfile
import unittest
from collections import Counter
from pathlib import Path

MODELS = (
    ("gsm", "GSM", "GSM"),
    ("industry", "Industry", "Industry"),
    ("metasocket", "MetaSocket", "MetaSocket"),
    ("powerplant", "PowerPlant", "PowerPlant"),
    ("productioncell_arms1", "PC Arms=1", "PCOne"),
    ("productioncell_arms2", "PC Arms=2", "PCTwo"),
    ("railcab", "Railcab", "Railcab"),
    ("surveillance", "Surveillance", "Surveillance"),
    ("workflow", "Workflow", "Workflow"),
)
TARGETS = ("base", "r1", "r2")
NAME = r"[A-Za-z_][A-Za-z_0-9]*"
REFERENCE = NAME + r"(?:\[[0-9]+\])?@" + NAME + r"(?:\([0-9]+\))?"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def uncomment(text):
    # Preserve line numbers for source references in the generated CSV.
    return re.sub(r"//[^\n]*|/\*.*?\*/",
                  lambda m: re.sub(r"[^\n]", " ", m[0]), text, flags=re.S)


def braced(text, opening):
    require(text[opening] == "{", "Expected opening brace")
    depth = 0
    for i in range(opening, len(text)):
        depth += (text[i] == "{") - (text[i] == "}")
        if depth == 0:
            return text[opening + 1:i]
    raise ValueError("Unclosed brace")


def declaration(text, kind, name):
    matches = list(re.finditer(r"\b" + kind + r"\s+" + re.escape(name)
                              + r"\s*=\s*\{", text))
    require(len(matches) == 1, f"Expected one {kind} {name}")
    m = matches[0]
    return braced(text, m.end() - 1), text[:m.start()].count("\n") + 1


def split_items(text):
    result = []; start = 0; stack = []
    matching = {")": "(", "]": "[", "}": "{"}
    for i, c in enumerate(text):
        if c in "([{":
            stack.append(c)
        elif c in ")]}":
            require(bool(stack) and stack.pop() == matching[c], "Unbalanced list")
        elif c == "," and not stack:
            result.append(text[start:i].strip()); start = i + 1
    require(not stack, "Unbalanced list")
    result.append(text[start:].strip())
    require(all(result), "Empty list item")
    return result


def list_field(text, name):
    matches = list(re.finditer(r"\b" + re.escape(name) + r"\s*=\s*\{", text))
    require(len(matches) == 1, f"Expected one list field {name}")
    values = split_items(braced(text, matches[0].end() - 1))
    require(len(values) == len(set(values)), f"Duplicate {name} item")
    return values


def single_field(text, name):
    values = re.findall(r"\b" + re.escape(name) + r"\s*=\s*(" + NAME + r")\b", text)
    require(len(values) == 1, f"Expected one scalar field {name}")
    return values[0]


def explicit_set(text, name):
    block, _ = declaration(text, "set", name)
    values = split_items(block)
    require(all(re.fullmatch(NAME, x) for x in values), f"Unsupported set {name}")
    require(len(values) == len(set(values)), f"Duplicate set item in {name}")
    return set(values)


def expand_relation(block, constants):
    pairs = set(); actions = set(); sources = Counter(); endpoints = set()
    for item in split_items(block):
        prefix = re.match(r"forall\s*\[(" + NAME + r")\s*:\s*(\d+|" + NAME
                          + r")\s*\.\.\s*(\d+|" + NAME + r")\]\s*", item)
        expanded = [item]
        if prefix:
            variable, lower, upper = prefix.groups()
            def value(token):
                require(token.isdigit() or token in constants, f"Unknown bound {token}")
                return int(token) if token.isdigit() else constants[token]
            lo, hi = value(lower), value(upper)
            require(0 <= lo <= hi, "Invalid forall range")
            body = item[prefix.end():]
            require("[" + variable + "]" in body, "Unused forall variable")
            expanded = [body.replace("[" + variable + "]", "[" + str(i) + "]")
                        for i in range(lo, hi + 1)]
        for edge in expanded:
            m = re.fullmatch(r"\s*(" + REFERENCE + r")\s*=\s*(" + NAME
                             + r")\s*->\s*(" + REFERENCE + r")\s*", edge)
            require(m is not None, f"Unsupported transfer syntax: {edge}")
            source, action, target = m.groups()
            require((source, target) not in pairs, "Duplicate declared transfer pair")
            pairs.add((source, target)); actions.add(action); sources[source] += 1
            endpoints.add((source.split("@", 1)[1], target.split("@", 1)[1]))
    require(len(actions) == len(endpoints) == 1, "Relation must pair one component and command")
    return dict(pairs=pairs, actions=actions, endpoints=endpoints,
                branching_sources=sum(n > 1 for n in sources.values()),
                max_fanout=max(sources.values()))


def parse_model(model, source_name, original, export):
    text = uncomment(original)
    constants = dict((name, int(value)) for name, value in
                     re.findall(r"^\s*const\s+(" + NAME + r")\s*=\s*(\d+)\s*$", text, re.M))
    contracts = {c["target"]: c for c in export["contracts"]}
    require(set(contracts) == set(TARGETS), f"Unexpected targets in {model}")
    rows = []
    for target in TARGETS:
        saved = contracts[target]
        block, line = declaration(text, "updatingController", saved["definition"])
        old = list_field(block, "oldEnvironment"); new = list_field(block, "newEnvironment")
        maps = list_field(block, "mapRelation")
        require(len(old) == len(new) == len(maps) == saved["components"], "Component count mismatch")
        require(set(maps) == set(saved["map_relations"]), "Map declarations differ from saved frontend")
        old_goal = single_field(block, "oldGoal"); new_goal = single_field(block, "newGoal")
        old_spec, old_line = declaration(text, "controllerSpec", old_goal)
        new_spec, new_line = declaration(text, "controllerSpec", new_goal)
        old_reqs = list_field(old_spec, "safety"); new_reqs = list_field(new_spec, "safety")
        require(all(re.fullmatch(NAME, x) for x in old_reqs + new_reqs), "Unsupported safety declaration")
        interval = re.findall(r"\btransition\s*=\s*(" + NAME + r")\s*,", block)
        require(len(interval) == len(set(interval)), "Duplicate interval declaration")
        require(len(new_reqs) == saved["new_monitors"] and len(interval) == saved["upd_monitors"],
                "Requirement counts differ from saved frontend")
        for kind, names in (("new", new_reqs), ("upd", interval)):
            actual = {r["requirement"] for r in export["requirements"]
                      if r["target"] == target and r["kind"] == kind}
            require(set(names) == actual, "Requirement names differ from saved frontend")
        relations = []; relation_lines = []; transfer_actions = set(); endpoints = set()
        for name in maps:
            rel, rel_line = declaration(text, "relation", name)
            parsed = expand_relation(rel, constants)
            relations.append(parsed); relation_lines.append(f"{name}:{rel_line}")
            require(not (transfer_actions & parsed["actions"]), "Shared transfer command")
            transfer_actions.update(parsed["actions"]); endpoints.update(parsed["endpoints"])
        require({a for a, b in endpoints} == set(old) and {b for a, b in endpoints} == set(new),
                "Relation endpoints differ from paired environments")
        stops = {"stopOldSpec_" + r for r in old_reqs}
        starts = {"startNewSpec_" + r for r in new_reqs}
        require(stops == explicit_set(text, "StopOldSpecActions"), "Stop command set mismatch")
        require(starts == explicit_set(text, "StartNewSpecActions"), "Start command set mismatch")
        require(transfer_actions == explicit_set(text, "ReconfigureActions"), "Transfer command set mismatch")
        require(not (stops & starts or starts & transfer_actions or stops & transfer_actions),
                "Boundary and transfer command names overlap")
        rows.append(dict(model=model, target=target, components=len(old),
                         declared_transfer_pairs=sum(len(r["pairs"]) for r in relations),
                         transfer_commands=len(transfer_actions), old_requirements=len(old_reqs),
                         new_requirements=len(new_reqs), interval_requirements=len(interval),
                         update_commands=len(stops | starts | transfer_actions),
                         branching_transfer_sources=sum(r["branching_sources"] for r in relations),
                         maximum_transfer_fanout=max(r["max_fanout"] for r in relations),
                         source_name=source_name, definition=saved["definition"], definition_line=line,
                         old_goal_line=old_line, new_goal_line=new_line,
                         relation_lines=";".join(relation_lines),
                         frontend_crosscheck="MATCH"))
    same = ("components", "declared_transfer_pairs", "transfer_commands", "old_requirements",
            "new_requirements", "update_commands", "branching_transfer_sources", "maximum_transfer_fanout")
    require(all(len({r[k] for r in rows}) == 1 for k in same), "Size varies across targets unexpectedly")
    return rows


def outputs(rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader(); writer.writerows(rows)
    macros = ["% Generated from saved LTS declarations, cross-checked against saved frontend exports."]
    table = [r"\begin{table}[!htbp]", r"\centering\small",
             r"\caption{Declared contract sizes of the nine adapted inputs.}",
             r"\label{tab:contract-size}", r"\begin{tabular}{@{}lrrrrr@{}}\toprule",
             r"Input & $C$ & $T$ & $U$ & Old/New & Interval B/R1/R2\\\midrule"]
    by = {(r["model"], r["target"]): r for r in rows}
    for model, label, stem in MODELS:
        row = by[model, "base"]; prefix = "Contract" + stem
        fields = {"Components": "components", "TransferPairs": "declared_transfer_pairs",
                  "Updates": "update_commands", "Old": "old_requirements", "New": "new_requirements"}
        for suffix, key in fields.items():
            macros.append("\\providecommand{\\" + prefix + suffix + "}{" + str(row[key]) + "}")
        for target, suffix in zip(TARGETS, ("Base", "ROne", "RTwo")):
            macros.append("\\providecommand{\\" + prefix + suffix + "}{"
                          + str(by[model, target]["interval_requirements"]) + "}")
        command = lambda suffix: "\\" + prefix + suffix
        table.append(" & ".join([label, command("Components"), command("TransferPairs"), command("Updates"),
                                  command("Old") + "/" + command("New"),
                                  "/".join(command(s) for s in ("Base", "ROne", "RTwo"))]) + r"\\")
    table += [r"\bottomrule\end{tabular}", r"\par\smallskip\footnotesize",
              r"$C$: component pairs; $T$: declared local source--target transfer pairs, after expanding finite ranges and before observer augmentation; $U$: transfer, old-stop and new-start commands. Counts are shared across Base/R1/R2 except interval requirements. These are input-description counts, not reachable-game sizes. Only Railcab has a branching declared transfer source (two outcomes).",
              r"\end{table}"]
    return {"contract-sizes.csv": stream.getvalue(),
            "contract-size-macros.tex": "\n".join(macros) + "\n",
            "contract-size-table.tex": "\n".join(table) + "\n"}


def input_paths(script, models=None, exports=None):
    """Resolve research and packaged layouts independently of the working directory."""
    ancestors = Path(script).resolve().parents
    if models is None:
        models = next((p / "Implementation/Experiment/Models" for p in ancestors
                       if (p / "Implementation/Experiment/Models").is_dir()), None)
    if exports is None:
        exports = next((p / "experiments/rs_coverage/raw/expanded-predicates" for p in ancestors
                        if (p / "experiments/rs_coverage/raw/expanded-predicates").is_dir()), None)
    require(models is not None and exports is not None,
            "Supply --models-root and --saved-export-root outside the packaged/research layout")
    require(models.is_dir() and exports.is_dir(), "Contract input directories must exist")
    return models, exports


class ParserChecks(unittest.TestCase):
    def test_input_paths_ignore_working_directory_and_package_root_name(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "arbitrary-package-name"
            models = root / "Implementation/Experiment/Models"
            submission = root / "FSE2027_SUBMISSION_20260914"
            exports = submission / "experiments/rs_coverage/raw/expanded-predicates"
            models.mkdir(parents=True); exports.mkdir(parents=True)
            for module in ("experiments/contract_sizes", "paper/materials/expression_20260927/evidence"):
                script = submission / module / "generate_contract_sizes.py"
                self.assertEqual(input_paths(script), (models.resolve(), exports.resolve()))

    def test_explicit_inputs_work_outside_layout_and_missing_input_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            models, exports = root / "models", root / "exports"
            models.mkdir(); exports.mkdir()
            self.assertEqual(input_paths(root / "standalone.py", models, exports), (models, exports))
            with self.assertRaisesRegex(ValueError, "Supply --models-root"):
                input_paths(root / "standalone.py")

    def test_nested_braces_and_comment_lines(self):
        text = "// not a definition\ncontrollerSpec X = {safety={P,Q}\ncontrollable={a}}"
        block, line = declaration(uncomment(text), "controllerSpec", "X")
        self.assertEqual(line, 2); self.assertEqual(list_field(block, "safety"), ["P", "Q"])

    def test_forall_inclusive_and_many_to_one(self):
        r = expand_relation("forall [k:1..K] A[k]@OLD(1)=rho->B@NEW(1)", {"K": 3})
        self.assertEqual(len(r["pairs"]), 3); self.assertEqual(r["branching_sources"], 0)

    def test_branching_source_has_two_pairs(self):
        r = expand_relation("A@OLD=rho->B@NEW,A@OLD=rho->C@NEW", {})
        self.assertEqual((len(r["pairs"]), r["branching_sources"], r["max_fanout"]), (2, 1, 2))

    def test_duplicate_pair_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            expand_relation("A@OLD=rho->B@NEW,A@OLD=rho->B@NEW", {})

    def test_chained_transfer_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            expand_relation("A@OLD=rho->ordinary->B@NEW", {})

    def test_unknown_range_and_mixed_component_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unknown"):
            expand_relation("forall [k:1..K] A[k]@OLD=rho->B@NEW", {})
        with self.assertRaisesRegex(ValueError, "one component"):
            expand_relation("A@OLD=rho->B@NEW,A@OTHER=rho->B@NEW", {})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models-root", type=Path)
    parser.add_argument("--saved-export-root", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ParserChecks))
        return 0 if result.wasSuccessful() else 1
    models, exports = input_paths(__file__, args.models_root, args.saved_export_root)
    rows = []
    for model, _, _ in MODELS:
        export = json.loads((exports / (model + ".json")).read_text(encoding="utf-8"))
        name = export["source_name"]
        require(Path(name).name == name, "Export source must be a filename")
        rows.extend(parse_model(model, name, (models / name).read_text(encoding="utf-8"), export))
    require(len(rows) == 27, "Expected all nine models and three variants")
    for filename, content in outputs(rows).items():
        path = args.output_dir / filename
        if args.check:
            require(path.read_text(encoding="utf-8") == content, f"Generated file differs: {filename}")
        else:
            args.output_dir.mkdir(parents=True, exist_ok=True)
            with path.open("x", encoding="utf-8", newline="") as output:
                output.write(content)
    print("PASS: 27 source contracts agree with saved frontend C/NEW/UPD/relation declarations.")
    print("PASS: finite transfer ranges expanded; declared pair counts and all update labels checked.")
    for model, _, _ in MODELS:
        r = next(r for r in rows if r["model"] == model)
        print(f"{model}: C={r['components']} T={r['declared_transfer_pairs']} U={r['update_commands']}")
    print("PASS: generated files " + ("match byte-for-byte" if args.check else "created without overwriting") + ".")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
