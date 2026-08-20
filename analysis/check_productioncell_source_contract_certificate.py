#!/usr/bin/env python3
"""Bounded registered MTSA/LTS source to post-frontend contract bridge.

This checker is deliberately independent of MTSA and of the M8s exporter.  It
parses the registered ProductionCell FSP/LTS profile, reconstructs the raw
component machines, interprets the safety formulas, synthesizes the maximal
deadlock-free safety supervisors, and only then opens the conclusion-free M8s
IR.  State numbers emitted by MTSA are treated as opaque: comparisons use
rooted action-labelled graph isomorphism.

The accepted language is intentionally small.  Every non-comment top-level
declaration must be consumed, and unsupported syntax is rejected instead of
being ignored.  This is not a general LTSA/MTSA frontend and it does not
synthesize WIN or a certificate.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import re
import sys
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


REPORT_SCHEMA = "fg-ducs-productioncell-source-contract-bridge-report-v1"
SUPPORTED_DEFINITIONS = frozenset({"UpdCont_OTF_FG", "UpdCont_OTF_FG_R2"})
BAD = object()
IR_ROOT_KEYS = {
    "schema_version", "evidence_scope", "source_name", "source_sha256",
    "definition", "flags", "controllable_actions", "components",
    "old_safety_machines", "new_safety_machines",
    "transition_requirement_machines", "observer_machines", "protocol",
    "shared_mtsa_frontend", "independent_source_frontend",
    "old_new_controller_synthesis_performed", "source_to_witness_replay",
    "fixed_endpoint_products_materialized", "local_update_games_materialized",
    "global_mixed_game_materialized", "conclusion_fields_present",
    "extraction_stage", "controllers", "observer_registry",
    "new_activation_sources", "load_selector", "boundary_actions",
    "physical_closure_materialized", "activation_relations_materialized",
    "goal_signatures_materialized", "dependency_partition_materialized",
    "winning_certificate_materialized",
}


class SourceContractError(RuntimeError):
    """The source, IR, or their semantic cross-link is invalid."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SourceContractError(message)


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def strict_json_bytes(raw: bytes) -> dict[str, Any]:
    """Load one JSON object without last-key-wins or non-finite numbers."""
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            require(key not in result, f"duplicate JSON key: {key}")
            result[key] = value
        return result

    try:
        value = json.loads(
            raw.decode("utf-8"), object_pairs_hook=unique_object,
            parse_constant=lambda token: (_ for _ in ()).throw(
                ValueError(token)),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise SourceContractError("IR is not strict JSON") from error
    require(type(value) is dict, "IR root is not an object")
    return value


def _strip_comments(source: str) -> str:
    """Remove comments while retaining newlines and rejecting nesting."""
    out: list[str] = []
    index = 0
    block = False
    while index < len(source):
        if block:
            if source.startswith("/*", index):
                raise SourceContractError("nested block comment is unsupported")
            if source.startswith("*/", index):
                out.extend("  ")
                index += 2
                block = False
            else:
                out.append("\n" if source[index] == "\n" else " ")
                index += 1
            continue
        if source.startswith("/*", index):
            out.extend("  ")
            index += 2
            block = True
            continue
        if source.startswith("//", index):
            while index < len(source) and source[index] != "\n":
                out.append(" ")
                index += 1
            continue
        if source.startswith("*/", index):
            raise SourceContractError("unmatched block-comment terminator")
        out.append(source[index])
        index += 1
    require(not block, "unterminated block comment")
    return "".join(out)


@dataclass(frozen=True)
class Declaration:
    kind: str
    name: str
    text: str


_SINGLE_PREFIXES = (
    "const ", "range ", "set ", "map ", "fluent ", "assert ",
    "ltl_property ", "||", "controller ||",
)


def _declaration_name(line: str) -> tuple[str, str]:
    value = line.strip()
    patterns = (
        ("const", r"const\s+([A-Za-z_][A-Za-z0-9_]*)"),
        ("range", r"range\s+([A-Za-z_][A-Za-z0-9_]*)"),
        ("set", r"set\s+([A-Za-z_][A-Za-z0-9_]*)"),
        ("map", r"map\s+([A-Za-z_][A-Za-z0-9_]*)"),
        ("fluent", r"fluent\s+([A-Za-z_][A-Za-z0-9_]*)"),
        ("assert", r"assert\s+([A-Za-z_][A-Za-z0-9_]*)"),
        ("ltl_property", r"ltl_property\s+([A-Za-z_][A-Za-z0-9_]*)"),
        ("controllerSpec", r"controllerSpec\s+([A-Za-z_][A-Za-z0-9_]*)"),
        ("updatingController", r"updatingController\s+([A-Za-z_][A-Za-z0-9_]*)"),
        ("relation", r"relation\s+([A-Za-z_][A-Za-z0-9_]*)"),
        ("controller", r"controller\s+\|\|([A-Za-z_][A-Za-z0-9_]*)"),
        ("composition", r"\|\|([A-Za-z_][A-Za-z0-9_]*)"),
    )
    for kind, pattern in patterns:
        match = re.match(pattern, value)
        if match:
            return kind, match.group(1)
    process = re.match(r"(PRODUCTION_CELL_(?:OLD|NEW))\s*\(", value)
    if process:
        return "process", process.group(1)
    raise SourceContractError("unsupported top-level declaration: " + value[:80])


def split_declarations(clean: str) -> tuple[Declaration, ...]:
    """Consume every nonblank line into one bounded-profile declaration."""
    lines = clean.splitlines(keepends=True)
    result: list[Declaration] = []
    index = 0
    while index < len(lines):
        if not lines[index].strip():
            index += 1
            continue
        line = lines[index]
        kind, name = _declaration_name(line)
        collected = [line]
        if kind == "process":
            while not collected[-1].rstrip().endswith("."):
                index += 1
                require(index < len(lines), f"unterminated process {name}")
                collected.append(lines[index])
        elif kind in {"relation", "controllerSpec", "updatingController"}:
            depth = line.count("{") - line.count("}")
            require(depth >= 0, f"unbalanced declaration {name}")
            while depth:
                index += 1
                require(index < len(lines), f"unterminated declaration {name}")
                collected.append(lines[index])
                depth += lines[index].count("{") - lines[index].count("}")
                require(depth >= 0, f"unbalanced declaration {name}")
        else:
            require(any(line.lstrip().startswith(prefix)
                        for prefix in _SINGLE_PREFIXES),
                    f"unsupported single-line declaration {name}")
        text = "".join(collected).strip()
        result.append(Declaration(kind, name, text))
        index += 1
    require(bool(result), "source contains no declarations")
    return tuple(result)


_TOKEN = re.compile(
    r"[ \t\r\n]*(?:(->|==|\.\.|\|\||&&|\[\])|"
    r"([A-Za-z_][A-Za-z0-9_]*)|([0-9]+)|"
    r"([()\[\]{},|.=:+<>!~@]))"
)


def tokens(text: str) -> list[str]:
    result: list[str] = []
    position = 0
    while position < len(text):
        match = _TOKEN.match(text, position)
        if not match:
            if text[position:].strip() == "":
                break
            raise SourceContractError(
                f"unsupported token near {text[position:position + 40]!r}"
            )
        result.append(next(value for value in match.groups() if value is not None))
        position = match.end()
    return result


class Cursor:
    def __init__(self, values: Sequence[str], label: str) -> None:
        self.values = list(values)
        self.index = 0
        self.label = label

    def peek(self) -> str | None:
        return self.values[self.index] if self.index < len(self.values) else None

    def take(self, expected: str | None = None) -> str:
        require(self.index < len(self.values), f"unexpected end of {self.label}")
        value = self.values[self.index]
        if expected is not None:
            require(value == expected,
                    f"expected {expected!r} in {self.label}, found {value!r}")
        self.index += 1
        return value

    def done(self) -> None:
        require(self.index == len(self.values),
                f"unconsumed tokens in {self.label}: {self.values[self.index:self.index+8]}")


def _identifier(value: str, label: str) -> str:
    require(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value) is not None,
            f"invalid identifier in {label}: {value}")
    return value


def _source_reference(value: str, label: str) -> str:
    """Parse a declaration reference such as ``P`` or ``P(1)`` exactly."""
    cursor = Cursor(tokens(value), label)
    name = _identifier(cursor.take(), label)
    arguments: list[str] = []
    if cursor.peek() == "(":
        cursor.take("(")
        while True:
            argument = cursor.take()
            require(argument.isdigit()
                    or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", argument),
                    f"invalid reference argument in {label}")
            arguments.append(argument)
            if cursor.peek() != ",":
                break
            cursor.take(",")
        cursor.take(")")
    cursor.done()
    return name + ("(" + ",".join(arguments) + ")" if arguments else "")


def _split_top_level(text: str, delimiter: str = ",") -> list[str]:
    result: list[str] = []
    depth = {"(": 0, "[": 0, "{": 0}
    matching = {")": "(", "]": "[", "}": "{"}
    start = 0
    for index, char in enumerate(text):
        if char in depth:
            depth[char] += 1
        elif char in matching:
            opener = matching[char]
            depth[opener] -= 1
            require(depth[opener] >= 0, "unbalanced delimiter")
        elif char == delimiter and all(value == 0 for value in depth.values()):
            result.append(text[start:index].strip())
            start = index + 1
    require(all(value == 0 for value in depth.values()), "unbalanced delimiter")
    result.append(text[start:].strip())
    require(bool(result) and all(value for value in result),
            "empty item in delimited source construct")
    return result


def parse_constants(declarations: Sequence[Declaration]) -> dict[str, int]:
    result: dict[str, int] = {}
    for declaration in declarations:
        if declaration.kind != "const":
            continue
        match = re.fullmatch(r"const\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([0-9]+)",
                             declaration.text)
        require(match is not None, f"unsupported const: {declaration.text}")
        name, raw = match.groups()
        require(name not in result, f"duplicate const {name}")
        result[name] = int(raw)
    require(result.get("N") == 2 and result.get("K") == 1,
            "registered profile requires N=2 and K=1")
    return result


def parse_ranges(declarations: Sequence[Declaration],
                 constants: Mapping[str, int]) -> dict[str, tuple[int, ...]]:
    result: dict[str, tuple[int, ...]] = {}
    for declaration in declarations:
        if declaration.kind != "range":
            continue
        match = re.fullmatch(
            r"range\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*"
            r"([0-9]+|[A-Za-z_][A-Za-z0-9_]*)\.\."
            r"([0-9]+|[A-Za-z_][A-Za-z0-9_]*)", declaration.text)
        require(match is not None, f"unsupported range: {declaration.text}")
        name, left, right = match.groups()
        def integer(token: str) -> int:
            if token.isdigit():
                return int(token)
            require(token in constants, f"range references unknown const {token}")
            return constants[token]
        low, high = integer(left), integer(right)
        require(0 <= low <= high <= 16, f"range {name} leaves bounded profile")
        require(name not in result, f"duplicate range {name}")
        result[name] = tuple(range(low, high + 1))
    require(result == {"Arms": (1, 2), "Stages": (1,)},
            "registered range census differs")
    return result


def _action(cursor: Cursor, env: Mapping[str, int]) -> str:
    name = _identifier(cursor.take(), cursor.label)
    indices: list[int] = []
    while cursor.peek() == "[":
        cursor.take("[")
        token = cursor.take()
        if token.isdigit():
            value = int(token)
        else:
            require(token in env, f"unknown action index {token}")
            value = env[token]
        cursor.take("]")
        indices.append(value)
    return name + "".join(f".{value}" for value in indices)


def parse_sets(declarations: Sequence[Declaration],
               ranges: Mapping[str, tuple[int, ...]]) -> dict[str, frozenset[str]]:
    raw: dict[str, list[str]] = {}
    for declaration in declarations:
        if declaration.kind != "set":
            continue
        match = re.fullmatch(r"set\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\{(.*)\}",
                             declaration.text, flags=re.DOTALL)
        require(match is not None, f"unsupported set: {declaration.text}")
        name, body = match.groups()
        require(name not in raw, f"duplicate set {name}")
        raw[name] = _split_top_level(body)
    resolved: dict[str, frozenset[str]] = {}

    def expand_item(item: str, stack: tuple[str, ...]) -> set[str]:
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", item) and item in raw:
            return set(resolve(item, stack))
        cursor = Cursor(tokens(item), f"set item {item}")
        name = _identifier(cursor.take(), cursor.label)
        dimensions: list[tuple[int, ...]] = []
        while cursor.peek() == "[":
            cursor.take("[")
            range_name = _identifier(cursor.take(), cursor.label)
            cursor.take("]")
            require(range_name in ranges, f"unknown set range {range_name}")
            dimensions.append(ranges[range_name])
        cursor.done()
        if not dimensions:
            return {name}
        return {
            name + "".join(f".{value}" for value in values)
            for values in itertools.product(*dimensions)
        }

    def resolve(name: str, stack: tuple[str, ...] = ()) -> frozenset[str]:
        if name in resolved:
            return resolved[name]
        require(name in raw and name not in stack, f"unknown or cyclic set {name}")
        values: set[str] = set()
        for item in raw[name]:
            values.update(expand_item(item, stack + (name,)))
        resolved[name] = frozenset(values)
        return resolved[name]

    for name in raw:
        resolve(name)
    return resolved


def parse_maps(declarations: Sequence[Declaration]) -> dict[str, tuple[str, ...]]:
    """Parse the positional MTSA component-map declarations exactly.

    A map is not a decorative LTSA declaration: its three positions bind the
    old process, new process, and transfer relation.  The bounded profile uses
    two maps and MAP_ENV composes both of them.  Consuming only the braces (as
    the first prototype did) would allow invalid or duplicate map definitions
    to cross the claimed source-frontend boundary.
    """
    result: dict[str, tuple[str, ...]] = {}
    pattern = re.compile(
        r"map\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\{(.*)\}",
        flags=re.DOTALL,
    )
    for declaration in declarations:
        if declaration.kind != "map":
            continue
        match = pattern.fullmatch(declaration.text)
        require(match is not None, f"unsupported map {declaration.name}")
        name, body = match.groups()
        require(name not in result, f"duplicate map {name}")
        result[name] = tuple(
            _source_reference(item, f"map {name}")
            for item in _split_top_level(body)
        )
    require(result == {
        "MAP_PRODUCTION_CELL_1": (
            "PRODUCTION_CELL_OLD(1)", "PRODUCTION_CELL_NEW(1)",
            "R_PRODUCTION_CELL(1)",
        ),
        "MAP_PRODUCTION_CELL_2": (
            "PRODUCTION_CELL_OLD(2)", "PRODUCTION_CELL_NEW(2)",
            "R_PRODUCTION_CELL(2)",
        ),
    }, "registered component-map binding differs")
    return result


@dataclass(frozen=True)
class Choice:
    guard: tuple[str, str, str] | None
    actions: tuple[tuple[str, tuple[str, ...]], ...]
    target: tuple[str, tuple[str, ...]]


@dataclass(frozen=True)
class StateSpec:
    name: str
    parameter: tuple[str, str] | None
    choices: tuple[Choice, ...]


@dataclass(frozen=True)
class ProcessSpec:
    name: str
    parameter: tuple[str, int]
    states: tuple[StateSpec, ...]


def _indexed_symbol(cursor: Cursor) -> tuple[str, tuple[str, ...]]:
    name = _identifier(cursor.take(), cursor.label)
    indices: list[str] = []
    while cursor.peek() == "[":
        cursor.take("[")
        expression = cursor.take()
        require(expression.isdigit()
                or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", expression),
                f"invalid index in {cursor.label}")
        if cursor.peek() == "+":
            cursor.take("+")
            expression += "+" + cursor.take()
        cursor.take("]")
        indices.append(expression)
    return name, tuple(indices)


def parse_process(declaration: Declaration) -> ProcessSpec:
    cursor = Cursor(tokens(declaration.text), f"process {declaration.name}")
    root = _identifier(cursor.take(), cursor.label)
    require(root == declaration.name, "process root name differs")
    cursor.take("(")
    parameter = _identifier(cursor.take(), cursor.label)
    cursor.take("=")
    default = int(cursor.take())
    cursor.take(")")
    cursor.take("=")
    specs: list[StateSpec] = []

    def parse_body(name: str, local_parameter: tuple[str, str] | None) -> StateSpec:
        cursor.take("(")
        choices: list[Choice] = []
        while True:
            guard: tuple[str, str, str] | None = None
            if cursor.peek() == "when":
                cursor.take("when")
                cursor.take("(")
                left = cursor.take()
                operator = cursor.take()
                require(operator in {"<", "=="}, "unsupported process guard")
                right = cursor.take()
                cursor.take(")")
                guard = (left, operator, right)
            action_rows: list[tuple[str, tuple[str, ...]]] = []
            if cursor.peek() == "{":
                cursor.take("{")
                while True:
                    action_rows.append(_indexed_symbol(cursor))
                    if cursor.peek() != ",":
                        break
                    cursor.take(",")
                cursor.take("}")
            else:
                action_rows.append(_indexed_symbol(cursor))
            cursor.take("->")
            target = _indexed_symbol(cursor)
            choices.append(Choice(guard, tuple(action_rows), target))
            if cursor.peek() != "|":
                break
            cursor.take("|")
        cursor.take(")")
        return StateSpec(name, local_parameter, tuple(choices))

    specs.append(parse_body(root, None))
    while cursor.peek() == ",":
        cursor.take(",")
        name = _identifier(cursor.take(), cursor.label)
        local: tuple[str, str] | None = None
        if cursor.peek() == "[":
            cursor.take("[")
            variable = _identifier(cursor.take(), cursor.label)
            cursor.take(":")
            domain = _identifier(cursor.take(), cursor.label)
            cursor.take("]")
            local = (variable, domain)
        cursor.take("=")
        specs.append(parse_body(name, local))
    cursor.take(".")
    cursor.done()
    require(len({spec.name for spec in specs}) == len(specs),
            f"duplicate local state in {root}")
    return ProcessSpec(root, (parameter, default), tuple(specs))


@dataclass(frozen=True)
class SourceGraph:
    initial: str
    states: frozenset[str]
    alphabet: frozenset[str]
    post: Mapping[tuple[str, str], tuple[str, ...]]


@dataclass(frozen=True)
class TransferRow:
    old_state: str
    old_owner: str
    action: str
    new_state: str
    new_owner: str


def _integer_expr(value: str, env: Mapping[str, int],
                  constants: Mapping[str, int]) -> int:
    if "+" in value:
        left, right = value.split("+", 1)
        return _integer_expr(left, env, constants) + _integer_expr(right, env, constants)
    if value.isdigit():
        return int(value)
    require(value in env or value in constants, f"unknown integer expression {value}")
    return env[value] if value in env else constants[value]


def instantiate_process(spec: ProcessSpec, argument: int,
                        constants: Mapping[str, int],
                        ranges: Mapping[str, tuple[int, ...]]) -> SourceGraph:
    root_parameter, _default = spec.parameter
    base_env = {root_parameter: argument}
    variants: dict[str, tuple[StateSpec, dict[str, int]]] = {}
    for state in spec.states:
        if state.parameter is None:
            key = state.name
            require(key not in variants, f"duplicate process state {key}")
            variants[key] = (state, dict(base_env))
        else:
            variable, domain = state.parameter
            require(domain in ranges, f"unknown local process range {domain}")
            for value in ranges[domain]:
                key = f"{state.name}[{value}]"
                env = dict(base_env)
                env[variable] = value
                require(key not in variants, f"duplicate process state {key}")
                variants[key] = (state, env)

    post: dict[tuple[str, str], list[str]] = {}
    for state_key, (state, env) in variants.items():
        for choice in state.choices:
            if choice.guard is not None:
                left, operator, right = choice.guard
                lv = _integer_expr(left, env, constants)
                rv = _integer_expr(right, env, constants)
                if not (lv < rv if operator == "<" else lv == rv):
                    continue
            target_name, target_indices = choice.target
            if target_indices:
                values = [_integer_expr(value, env, constants)
                          for value in target_indices]
                target = target_name + "".join(f"[{value}]" for value in values)
            else:
                target = target_name
            require(target in variants, f"process target is unknown: {target}")
            for action_name, action_indices in choice.actions:
                values = [_integer_expr(value, env, constants)
                          for value in action_indices]
                action = action_name + "".join(f".{value}" for value in values)
                post.setdefault((state_key, action), []).append(target)
    initial = spec.name
    require(initial in variants, f"process initial state is absent: {initial}")
    reached = {initial}
    queue = deque([initial])
    while queue:
        state = queue.popleft()
        for (source, _action), targets in post.items():
            if source != state:
                continue
            for target in targets:
                if target not in reached:
                    reached.add(target)
                    queue.append(target)
    require(reached == set(variants),
            f"process contains unreachable declared state(s): {sorted(set(variants)-reached)}")
    frozen = {key: tuple(dict.fromkeys(targets)) for key, targets in post.items()}
    return SourceGraph(initial, frozenset(reached),
                       frozenset(action for _state, action in frozen), frozen)


def _owner_reference(cursor: Cursor, env: Mapping[str, int]) -> str:
    name = _identifier(cursor.take(), cursor.label)
    cursor.take("(")
    argument = cursor.take()
    value = _integer_expr(argument, env, {})
    cursor.take(")")
    return f"{name}({value})"


def parse_relations(declarations: Sequence[Declaration],
                    constants: Mapping[str, int],
                    ranges: Mapping[str, tuple[int, ...]]) -> dict[str, tuple[TransferRow, ...]]:
    result: dict[str, tuple[TransferRow, ...]] = {}
    pattern = re.compile(
        r"relation\s+([A-Za-z_][A-Za-z0-9_]*)"
        r"(?:\(([A-Za-z_][A-Za-z0-9_]*)\))?\s*=\s*\{(.*)\}",
        flags=re.DOTALL)
    for declaration in declarations:
        if declaration.kind != "relation":
            continue
        match = pattern.fullmatch(declaration.text)
        require(match is not None, f"unsupported relation {declaration.name}")
        name, header_variable, body = match.groups()
        rows: list[TransferRow] = []
        header_envs = ([{header_variable: value} for value in ranges["Arms"]]
                       if header_variable else [{}])
        for raw_row in _split_top_level(body):
            base_cursor = Cursor(tokens(raw_row), f"relation {name}")
            loop_variable: str | None = None
            loop_values: tuple[int, ...] = (0,)
            if base_cursor.peek() == "forall":
                base_cursor.take("forall")
                base_cursor.take("[")
                loop_variable = _identifier(base_cursor.take(), base_cursor.label)
                base_cursor.take(":")
                low = base_cursor.take()
                base_cursor.take("..")
                high = base_cursor.take()
                base_cursor.take("]")
                low_value = _integer_expr(low, {}, constants)
                high_value = _integer_expr(high, {}, constants)
                require(0 <= low_value <= high_value <= 16,
                        f"relation loop leaves bounded profile: {name}")
                loop_values = tuple(range(low_value, high_value + 1))
            remainder = base_cursor.values[base_cursor.index:]
            for header_env in header_envs:
                for loop_value in loop_values:
                    env = dict(header_env)
                    if loop_variable is not None:
                        env[loop_variable] = loop_value
                    cursor = Cursor(remainder, f"relation {name} row")
                    old_name, old_indices = _indexed_symbol(cursor)
                    old_state = old_name + "".join(
                        f"[{_integer_expr(value, env, constants)}]"
                        for value in old_indices)
                    cursor.take("@")
                    old_owner = _owner_reference(cursor, env)
                    cursor.take("=")
                    action_name, action_indices = _indexed_symbol(cursor)
                    action = action_name + "".join(
                        f".{_integer_expr(value, env, constants)}"
                        for value in action_indices)
                    cursor.take("->")
                    new_name, new_indices = _indexed_symbol(cursor)
                    new_state = new_name + "".join(
                        f"[{_integer_expr(value, env, constants)}]"
                        for value in new_indices)
                    cursor.take("@")
                    new_owner = _owner_reference(cursor, env)
                    cursor.done()
                    rows.append(TransferRow(old_state, old_owner, action,
                                            new_state, new_owner))
        require(name not in result and rows and len(rows) == len(set(rows)),
                f"invalid or duplicate relation {name}")
        result[name] = tuple(rows)
    require({"R_PRODUCTION_CELL_1_FG", "R_PRODUCTION_CELL_2_FG"} <= set(result),
            "registered concrete relations are missing")
    return result


@dataclass(frozen=True)
class Fluent:
    name: str
    initiators: frozenset[str]
    terminators: frozenset[str]

    def step(self, active: bool, action: str) -> bool:
        if action in self.initiators:
            return True
        if action in self.terminators:
            return False
        return active


def _expand_action_term(text: str, env: Mapping[str, int],
                        sets: Mapping[str, frozenset[str]]) -> frozenset[str]:
    value = text.strip()
    if value.startswith("{"):
        require(value.endswith("}"), "unterminated action set")
        parts = _split_top_level(value[1:-1])
        result: set[str] = set()
        for part in parts:
            result.update(_expand_action_term(part, env, sets))
        return frozenset(result)
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value) and value in sets:
        return sets[value]
    cursor = Cursor(tokens(value), f"action term {value}")
    action = _action(cursor, env)
    cursor.done()
    return frozenset({action})


def parse_fluents(declarations: Sequence[Declaration],
                  ranges: Mapping[str, tuple[int, ...]],
                  sets: Mapping[str, frozenset[str]]) -> dict[str, Fluent]:
    result: dict[str, Fluent] = {}
    pattern = re.compile(
        r"fluent\s+([A-Za-z_][A-Za-z0-9_]*)"
        r"(?:\[([A-Za-z_][A-Za-z0-9_]*):([A-Za-z_][A-Za-z0-9_]*)\])?"
        r"\s*=\s*<(.*)>$", flags=re.DOTALL)
    for declaration in declarations:
        if declaration.kind != "fluent":
            continue
        match = pattern.fullmatch(declaration.text)
        require(match is not None, f"unsupported fluent: {declaration.text}")
        base, variable, domain, body = match.groups()
        parts = _split_top_level(body)
        require(len(parts) == 2, f"fluent {base} must have initiator/terminator")
        environments: list[dict[str, int]]
        if variable is None:
            environments = [{}]
        else:
            require(domain in ranges, f"unknown fluent range {domain}")
            environments = [{variable: value} for value in ranges[domain]]
        for env in environments:
            name = base + (f".{env[variable]}" if variable is not None else "")
            require(name not in result, f"duplicate fluent {name}")
            initiators = _expand_action_term(parts[0], env, sets)
            terminators = _expand_action_term(parts[1], env, sets)
            require(initiators and terminators and not (initiators & terminators),
                    f"invalid fluent event partition: {name}")
            result[name] = Fluent(name, initiators, terminators)
    return result


@dataclass(frozen=True)
class Expr:
    kind: str
    value: str | None = None
    left: "Expr | None" = None
    right: "Expr | None" = None


class FormulaParser:
    def __init__(self, text: str, env: Mapping[str, int]) -> None:
        self.cursor = Cursor(tokens(text), "formula")
        self.env = env

    def parse(self) -> Expr:
        result = self.implication()
        self.cursor.done()
        return result

    def implication(self) -> Expr:
        left = self.disjunction()
        if self.cursor.peek() == "->":
            self.cursor.take("->")
            return Expr("implies", left=left, right=self.implication())
        return left

    def disjunction(self) -> Expr:
        value = self.conjunction()
        while self.cursor.peek() == "||":
            self.cursor.take("||")
            value = Expr("or", left=value, right=self.conjunction())
        return value

    def conjunction(self) -> Expr:
        value = self.unary()
        while self.cursor.peek() == "&&":
            self.cursor.take("&&")
            value = Expr("and", left=value, right=self.unary())
        return value

    def unary(self) -> Expr:
        if self.cursor.peek() == "!":
            self.cursor.take("!")
            return Expr("not", left=self.unary())
        if self.cursor.peek() == "(":
            self.cursor.take("(")
            value = self.implication()
            self.cursor.take(")")
            return value
        if self.cursor.peek() == "{":
            self.cursor.take("{")
            values: list[Expr] = []
            while True:
                values.append(Expr("ref", value=_action(self.cursor, self.env)))
                if self.cursor.peek() != ",":
                    break
                self.cursor.take(",")
            self.cursor.take("}")
            value = values[0]
            for item in values[1:]:
                value = Expr("or", left=value, right=item)
            return value
        return Expr("ref", value=_action(self.cursor, self.env))


@dataclass(frozen=True)
class FormulaDecl:
    name: str
    expressions: tuple[Expr, ...]
    globally: bool


def parse_formulas(declarations: Sequence[Declaration],
                   ranges: Mapping[str, tuple[int, ...]]) -> tuple[
                       dict[str, FormulaDecl], dict[str, FormulaDecl]]:
    assertions: dict[str, FormulaDecl] = {}
    properties: dict[str, FormulaDecl] = {}
    counts: dict[tuple[str, str], int] = {}
    for declaration in declarations:
        if declaration.kind not in {"assert", "ltl_property"}:
            continue
        prefix = "assert" if declaration.kind == "assert" else "ltl_property"
        match = re.fullmatch(
            prefix + r"\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)",
            declaration.text, flags=re.DOTALL)
        require(match is not None, f"unsupported {prefix}: {declaration.text}")
        name, body = match.groups()
        globally = False
        if declaration.kind == "ltl_property":
            require(body.startswith("[]"), f"property is not globally scoped: {name}")
            body = body[2:].strip()
            globally = True
        environments = [{}]
        quantifier = re.fullmatch(
            r"forall\[([A-Za-z_][A-Za-z0-9_]*):"
            r"([A-Za-z_][A-Za-z0-9_]*)\]\s*(.*)", body, flags=re.DOTALL)
        if quantifier:
            variable, domain, body = quantifier.groups()
            require(domain in ranges, f"formula references unknown range {domain}")
            environments = [{variable: value} for value in ranges[domain]]
        expressions = tuple(FormulaParser(body, env).parse() for env in environments)
        target = assertions if declaration.kind == "assert" else properties
        row = FormulaDecl(name, expressions, globally)
        counts[(declaration.kind, name)] = counts.get((declaration.kind, name), 0) + 1
        if name in target:
            raise SourceContractError(f"duplicate formula {name}")
        else:
            target[name] = row
    require(all(count == 1 for count in counts.values()),
            "formula declaration multiplicity differs from registered source")
    return assertions, properties


def expr_refs(expr: Expr) -> frozenset[str]:
    if expr.kind == "ref":
        require(expr.value is not None, "reference is empty")
        return frozenset({expr.value})
    result: set[str] = set()
    if expr.left is not None:
        result.update(expr_refs(expr.left))
    if expr.right is not None:
        result.update(expr_refs(expr.right))
    return frozenset(result)


def eval_expr(expr: Expr, values: Mapping[str, bool], action: str) -> bool:
    if expr.kind == "ref":
        require(expr.value is not None, "reference is empty")
        return values[expr.value] if expr.value in values else expr.value == action
    if expr.kind == "not":
        require(expr.left is not None, "not operand is empty")
        return not eval_expr(expr.left, values, action)
    require(expr.left is not None and expr.right is not None,
            f"binary expression is incomplete: {expr.kind}")
    left = eval_expr(expr.left, values, action)
    right = eval_expr(expr.right, values, action)
    if expr.kind == "and":
        return left and right
    if expr.kind == "or":
        return left or right
    if expr.kind == "implies":
        return (not left) or right
    raise SourceContractError(f"unknown formula operator {expr.kind}")


def validate_formula_namespace(
    assertions: Mapping[str, FormulaDecl],
    properties: Mapping[str, FormulaDecl],
    fluents: Mapping[str, Fluent],
    known_events: frozenset[str],
) -> None:
    """Validate every formula, including declarations outside the selection.

    MTSA shares the assertion/property name space and resolves all formula
    references while loading the source.  Checking only the selected goals
    would let an invalid, unused formula pass the independent frontend even
    though the native frontend rejects the same bytes.
    """
    require(not (set(assertions) & set(properties)),
            "assertion/property names share a duplicate")
    assertion_names = set(assertions)
    fluent_names = set(fluents)
    dependencies: dict[str, frozenset[str]] = {}
    for group_name, group in (("assertion", assertions),
                              ("property", properties)):
        for name, row in group.items():
            refs = set().union(*(set(expr_refs(expr))
                                 for expr in row.expressions))
            unresolved = refs - fluent_names - assertion_names - set(known_events)
            require(not unresolved,
                    f"{group_name} {name} has undefined reference(s): "
                    f"{sorted(unresolved)}")
            if group_name == "assertion":
                dependencies[name] = frozenset(refs & assertion_names)

    visiting: set[str] = set()
    complete: set[str] = set()

    def visit(name: str) -> None:
        require(name not in visiting, f"cyclic assertion reference: {name}")
        if name in complete:
            return
        visiting.add(name)
        for dependency in dependencies[name]:
            visit(dependency)
        visiting.remove(name)
        complete.add(name)

    for name in dependencies:
        visit(name)


def parse_controller_specs(declarations: Sequence[Declaration]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for declaration in declarations:
        if declaration.kind != "controllerSpec":
            continue
        match = re.fullmatch(
            r"controllerSpec\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\{(.*)\}",
            declaration.text, flags=re.DOTALL)
        require(match is not None, f"unsupported controllerSpec {declaration.name}")
        name, body = match.groups()
        safety = re.search(r"safety\s*=\s*\{(.*?)\}", body, flags=re.DOTALL)
        controllable = re.search(r"controllable\s*=\s*\{(.*?)\}", body,
                                 flags=re.DOTALL)
        require(safety is not None and controllable is not None,
                f"controllerSpec fields are missing: {name}")
        residue = body
        for found in sorted((safety, controllable), key=lambda item: item.start(), reverse=True):
            residue = residue[:found.start()] + residue[found.end():]
        require(not residue.strip(), f"unsupported controllerSpec field: {name}")
        requirements = tuple(_identifier(item.strip(), name)
                             for item in _split_top_level(safety.group(1)))
        controls = tuple(_identifier(item.strip(), name)
                         for item in _split_top_level(controllable.group(1)))
        require(name not in result and requirements
                and len(requirements) == len(set(requirements))
                and len(controls) == 1,
                f"invalid controllerSpec {name}")
        result[name] = {"safety": requirements, "controllable": controls[0]}
    require(set(result) == {"DRILL_POLISH_CLEAN", "CLEAN_PAINT_DRILL"},
            "controllerSpec census differs")
    return result


def parse_updating_controllers(declarations: Sequence[Declaration]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for declaration in declarations:
        if declaration.kind != "updatingController":
            continue
        match = re.fullmatch(
            r"updatingController\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\{(.*)\}",
            declaration.text, flags=re.DOTALL)
        require(match is not None, f"unsupported updatingController {declaration.name}")
        name, body = match.groups()
        rows = _split_top_level(body)
        fields: dict[str, Any] = {}
        transitions: list[str] = []
        flags: list[str] = []
        for row in rows:
            if "=" not in row:
                flags.append(_identifier(row.strip(), name))
                continue
            key, value = row.split("=", 1)
            key = _identifier(key.strip(), name)
            value = value.strip()
            if key == "transition":
                transitions.append(_identifier(value, name))
                continue
            require(key not in fields, f"duplicate field {key} in {name}")
            if value.startswith("{"):
                require(value.endswith("}"), f"unterminated field {key}")
                fields[key] = tuple(_source_reference(item.strip(), name)
                                    for item in _split_top_level(value[1:-1]))
            else:
                fields[key] = _source_reference(value, name)
        require(len(flags) == len(set(flags)), f"duplicate flag in {name}")
        fields["transition"] = tuple(transitions)
        fields["flags"] = tuple(flags)
        require(len(transitions) == len(set(transitions)),
                f"duplicate transition requirement in {name}")
        require(name not in result, f"duplicate updatingController {name}")
        result[name] = fields
    require(SUPPORTED_DEFINITIONS <= set(result),
            "registered updating-controller definitions are missing")
    return result


def validate_composition_bindings(
    declarations: Sequence[Declaration],
    updating: Mapping[str, Mapping[str, Any]],
) -> dict[str, tuple[str, str]]:
    controllers: dict[str, tuple[str, str]] = {}
    compositions = {declaration.name: declaration.text
                    for declaration in declarations
                    if declaration.kind == "composition"}
    require(len(compositions) == sum(declaration.kind == "composition"
                                     for declaration in declarations),
            "duplicate composition declaration")
    for declaration in declarations:
        if declaration.kind != "controller":
            continue
        cursor = Cursor(tokens(declaration.text), f"controller {declaration.name}")
        cursor.take("controller")
        cursor.take("||")
        name = _identifier(cursor.take(), cursor.label)
        cursor.take("=")
        cursor.take("(")
        environment = _identifier(cursor.take(), cursor.label)
        cursor.take(")")
        cursor.take("~")
        cursor.take("{")
        specification = _identifier(cursor.take(), cursor.label)
        cursor.take("}")
        cursor.take(".")
        cursor.done()
        require(name not in controllers, f"duplicate controller declaration {name}")
        controllers[name] = (environment, specification)
    require(controllers == {
        "C_DRILL_POLISH_CLEAN": ("OLD_ENV", "DRILL_POLISH_CLEAN"),
        "C_CLEAN_PAINT_DRILL": ("NEW_ENV", "CLEAN_PAINT_DRILL"),
    }, "fixed controller environment/specification binding differs")

    def exact_tokens(name: str, expected: str) -> None:
        require(name in compositions and tokens(compositions[name]) == tokens(expected),
                f"composition binding differs: {name}")

    exact_tokens("OLD_ENV",
                 "||OLD_ENV=(forall[i:Arms] PRODUCTION_CELL_OLD(i)).")
    exact_tokens("NEW_ENV",
                 "||NEW_ENV=(forall[i:Arms] PRODUCTION_CELL_NEW(i)).")
    exact_tokens("MAP_ENV",
                 "||MAP_ENV=(MAP_PRODUCTION_CELL_1 || MAP_PRODUCTION_CELL_2).")
    exact_tokens("DrillPolishClean",
                 "||DrillPolishClean=(C_DRILL_POLISH_CLEAN || OLD_ENV).")
    exact_tokens("CleanPaintDrill",
                 "||CleanPaintDrill=(C_CLEAN_PAINT_DRILL || NEW_ENV).")
    update_compositions = {
        name: text for name, text in compositions.items()
        if name.startswith("UPDATE_CONTROLLER_")
    }
    require(len(update_compositions) == len(updating),
            "updating-controller composition census differs")
    for name, text in update_compositions.items():
        match = re.fullmatch(
            r"\|\|([A-Za-z_][A-Za-z0-9_]*)\s*=\s*"
            r"([A-Za-z_][A-Za-z0-9_]*)\s*\.", text)
        require(match is not None, f"unsupported update composition {name}")
        _left, target = match.groups()
        expected_target = "UpdCont_" + name.removeprefix("UPDATE_CONTROLLER_")
        require(target == expected_target and target in updating,
                f"update composition target differs: {name}")
    require(set(compositions) == {
        "OLD_ENV", "NEW_ENV", "MAP_ENV", "DrillPolishClean", "CleanPaintDrill",
        *update_compositions,
    }, "unexpected composition in bounded source profile")
    return controllers


def resolve_property(name: str, properties: Mapping[str, FormulaDecl],
                     assertions: Mapping[str, FormulaDecl]) -> Expr:
    require(name in properties, f"controller references unknown property {name}")
    row = properties[name]
    require(row.globally and len(row.expressions) == 1,
            f"selected property is not a scalar safety formula: {name}")
    expr = row.expressions[0]
    if expr.kind == "ref" and expr.value in assertions:
        assertion = assertions[expr.value]
        require(len(assertion.expressions) == 1,
                f"selected assertion is not scalar: {expr.value}")
        return assertion.expressions[0]
    return expr


@dataclass(frozen=True)
class ControlledGraph:
    initial: Any
    states: frozenset[Any]
    alphabet: frozenset[str]
    post: Mapping[tuple[Any, str], tuple[Any, ...]]


@dataclass(frozen=True)
class FormulaMachine:
    initial: int
    states: frozenset[int]
    alphabet: frozenset[str]
    post: Mapping[tuple[int, str], tuple[int | object, ...]]
    fluent_names: tuple[str, ...]
    valuation_state: Mapping[tuple[bool, ...], int]


def compile_formula_machine(expr: Expr,
                            fluents: Mapping[str, Fluent]) -> FormulaMachine:
    refs = set(expr_refs(expr))
    fluent_names = tuple(sorted(refs & set(fluents)))
    event_names = refs - set(fluent_names)
    alphabet = set(event_names)
    for name in fluent_names:
        alphabet.update(fluents[name].initiators)
        alphabet.update(fluents[name].terminators)
    require(bool(alphabet), "formula has no observable alphabet")
    initial_valuation = tuple(False for _ in fluent_names)
    reached = {initial_valuation}
    queue = deque([initial_valuation])
    raw_post: dict[tuple[tuple[bool, ...], str], tuple[bool, ...] | object] = {}
    while queue:
        valuation = queue.popleft()
        values = dict(zip(fluent_names, valuation))
        for action in sorted(alphabet):
            stepped = {
                name: fluents[name].step(values[name], action)
                for name in fluent_names
            }
            if not eval_expr(expr, stepped, action):
                raw_post[(valuation, action)] = BAD
                continue
            target = tuple(stepped[name] for name in fluent_names)
            raw_post[(valuation, action)] = target
            if target not in reached:
                reached.add(target)
                queue.append(target)

    # Deterministic bisimulation/DFA minimization.  ERROR is a distinguished
    # sink outside the serialized safe-state census.
    partitions: list[frozenset[tuple[bool, ...]]] = [frozenset(reached)]
    while True:
        block_of = {value: index for index, block in enumerate(partitions)
                    for value in block}
        refined: list[frozenset[tuple[bool, ...]]] = []
        for block in partitions:
            groups: dict[tuple[int, ...], set[tuple[bool, ...]]] = {}
            for value in block:
                signature: list[int] = []
                for action in sorted(alphabet):
                    target = raw_post[(value, action)]
                    signature.append(-1 if target is BAD else block_of[target])
                groups.setdefault(tuple(signature), set()).add(value)
            refined.extend(frozenset(group) for _signature, group
                           in sorted(groups.items(), key=lambda item: item[0]))
        if set(refined) == set(partitions):
            partitions = refined
            break
        partitions = refined
    initial_block = next(index for index, block in enumerate(partitions)
                         if initial_valuation in block)
    # Give the initial quotient state id 0 and then BFS ids.  The ids are only
    # internal; the MTSA side is still compared by graph isomorphism.
    block_of = {value: index for index, block in enumerate(partitions)
                for value in block}
    block_post: dict[tuple[int, str], int | object] = {}
    for index, block in enumerate(partitions):
        representative = next(iter(block))
        for action in sorted(alphabet):
            target = raw_post[(representative, action)]
            block_post[(index, action)] = BAD if target is BAD else block_of[target]
    order = [initial_block]
    seen = {initial_block}
    pending = deque([initial_block])
    while pending:
        state = pending.popleft()
        for action in sorted(alphabet):
            target = block_post[(state, action)]
            if target is not BAD and target not in seen:
                seen.add(target)
                order.append(target)
                pending.append(target)
    require(seen == set(range(len(partitions))),
            "minimized formula machine contains an unreachable state")
    renumber = {old: new for new, old in enumerate(order)}
    post: dict[tuple[int, str], tuple[int | object, ...]] = {}
    for old, new in renumber.items():
        for action in sorted(alphabet):
            target = block_post[(old, action)]
            post[(new, action)] = (BAD if target is BAD else renumber[target],)
    valuation_state = {
        value: renumber[block_of[value]] for value in reached
    }
    return FormulaMachine(0, frozenset(range(len(partitions))),
                          frozenset(alphabet), post, fluent_names,
                          valuation_state)


def synthesize_component(graph: SourceGraph, requirements: Sequence[Expr],
                         fluents: Mapping[str, Fluent],
                         controllable: frozenset[str]) -> ControlledGraph:
    refs = set().union(*(set(expr_refs(expr)) for expr in requirements))
    fluent_names = tuple(sorted(refs & set(fluents)))
    event_names = refs - set(fluent_names)
    require(event_names <= set(graph.alphabet),
            f"safety formula event leaves component alphabet: {sorted(event_names-set(graph.alphabet))}")
    for fluent_name in fluent_names:
        relevant = fluents[fluent_name].initiators | fluents[fluent_name].terminators
        require(relevant <= set(graph.alphabet),
                f"safety fluent leaves component alphabet: {fluent_name}")
    initial = (graph.initial, tuple(False for _ in fluent_names))
    discovered = {initial}
    queue = deque([initial])
    raw_post: dict[tuple[Any, str], tuple[Any, ...] | object] = {}
    while queue:
        state, bits = queue.popleft()
        values = dict(zip(fluent_names, bits))
        for action in sorted(graph.alphabet):
            targets = graph.post.get((state, action), ())
            if not targets:
                continue
            stepped = {
                name: fluents[name].step(values[name], action)
                for name in fluent_names
            }
            if not all(eval_expr(expr, stepped, action) for expr in requirements):
                raw_post[((state, bits), action)] = BAD
                continue
            next_states = tuple((target, tuple(stepped[name] for name in fluent_names))
                                for target in targets)
            raw_post[((state, bits), action)] = next_states
            for target in next_states:
                if target not in discovered:
                    discovered.add(target)
                    queue.append(target)
    winning = set(discovered)
    while True:
        removed: set[Any] = set()
        for state in winning:
            enabled = False
            for action in graph.alphabet:
                targets = raw_post.get((state, action))
                if targets is None:
                    continue
                if targets is BAD:
                    if action not in controllable:
                        removed.add(state)
                        break
                    continue
                assert isinstance(targets, tuple)
                inside = set(targets) <= winning
                if action not in controllable and not inside:
                    removed.add(state)
                    break
                enabled = enabled or inside
            else:
                if not enabled:
                    removed.add(state)
        if not removed:
            break
        winning.difference_update(removed)
    require(initial in winning, "source-derived safety supervisor is unrealizable")
    reachable = {initial}
    queue = deque([initial])
    post: dict[tuple[Any, str], tuple[Any, ...]] = {}
    while queue:
        state = queue.popleft()
        enabled = False
        for action in sorted(graph.alphabet):
            targets = raw_post.get((state, action))
            if targets is None or targets is BAD:
                continue
            assert isinstance(targets, tuple)
            if set(targets) <= winning:
                enabled = True
                post[(state, action)] = targets
                for target in targets:
                    if target not in reachable:
                        reachable.add(target)
                        queue.append(target)
        require(enabled, "source-derived controller contains a deadlock")
    return ControlledGraph(initial, frozenset(reachable), graph.alphabet, post)


def product_controllers(controllers: Sequence[ControlledGraph]) -> ControlledGraph:
    require(bool(controllers), "controller product is empty")
    initial = tuple(controller.initial for controller in controllers)
    alphabet = frozenset().union(*(controller.alphabet for controller in controllers))
    reached = {initial}
    queue = deque([initial])
    post: dict[tuple[Any, str], tuple[Any, ...]] = {}
    while queue:
        state = queue.popleft()
        for action in sorted(alphabet):
            choices: list[tuple[Any, ...]] = []
            participant = False
            blocked = False
            for controller, local in zip(controllers, state):
                if action in controller.alphabet:
                    participant = True
                    targets = controller.post.get((local, action), ())
                    if not targets:
                        blocked = True
                        break
                    choices.append(targets)
                else:
                    choices.append((local,))
            if not participant or blocked:
                continue
            targets = tuple(itertools.product(*choices))
            post[(state, action)] = targets
            for target in targets:
                if target not in reached:
                    reached.add(target)
                    queue.append(target)
    return ControlledGraph(initial, frozenset(reached), alphabet, post)


def _json_object(value: Any, label: str) -> dict[str, Any]:
    require(type(value) is dict, f"{label} is not an object")
    return value


def _json_array(value: Any, label: str) -> list[Any]:
    require(type(value) is list, f"{label} is not an array")
    return value


def observed_compact_machine(value: Any, label: str) -> tuple[
        int, frozenset[int], frozenset[str], dict[tuple[int, str], tuple[int, ...]]]:
    row = _json_object(value, label)
    require(set(row) == {"name", "max_states", "alphabet", "transitions",
                         "initial_state"}, f"{label} key census differs")
    maximum = row["max_states"]
    initial = row["initial_state"]
    require(type(maximum) is int and maximum > 0 and initial == 0,
            f"{label} state declaration differs")
    alphabet_rows = _json_array(row["alphabet"], f"{label}.alphabet")
    require(all(type(item) is str for item in alphabet_rows),
            f"{label} alphabet is invalid")
    alphabet = frozenset(alphabet_rows)
    require(len(alphabet) == len(alphabet_rows), f"{label} repeats an action")
    post: dict[tuple[int, str], tuple[int, ...]] = {}
    for raw in _json_array(row["transitions"], f"{label}.transitions"):
        edge = _json_object(raw, f"{label}.edge")
        require(set(edge) == {"source", "action_index", "targets"},
                f"{label} edge key census differs")
        source, action_index = edge["source"], edge["action_index"]
        targets = edge["targets"]
        require(type(source) is int and 0 <= source < maximum
                and type(action_index) is int and 0 <= action_index < len(alphabet_rows)
                and type(targets) is list and targets
                and all(type(target) is int and -1 <= target < maximum
                        for target in targets), f"{label} edge leaves domain")
        key = (source, alphabet_rows[action_index])
        require(key not in post, f"{label} repeats an edge")
        post[key] = tuple(targets)
    return initial, frozenset(range(maximum)), alphabet, post


def observed_controller(value: Any, label: str) -> tuple[
        int, frozenset[int], frozenset[str], dict[tuple[int, str], tuple[int, ...]]]:
    row = _json_object(value, label)
    require(set(row) == {"initial_state", "states", "actions",
                         "required_transitions", "maybe_transition_count"},
            f"{label} key census differs")
    require(row["maybe_transition_count"] == 0,
            f"{label} contains MAYBE transitions")
    states_rows = _json_array(row["states"], f"{label}.states")
    actions_rows = _json_array(row["actions"], f"{label}.actions")
    require(all(type(value) is int for value in states_rows)
            and len(states_rows) == len(set(states_rows))
            and all(type(value) is str for value in actions_rows)
            and actions_rows == sorted(set(actions_rows)),
            f"{label} state/action census is invalid")
    states, actions = frozenset(states_rows), frozenset(actions_rows)
    initial = row["initial_state"]
    require(type(initial) is int and initial in states, f"{label} initial differs")
    post: dict[tuple[int, str], tuple[int, ...]] = {}
    for raw in _json_array(row["required_transitions"], f"{label}.edges"):
        edge = _json_object(raw, f"{label}.edge")
        require(set(edge) == {"source", "action", "targets"},
                f"{label} edge key census differs")
        source, action, targets = edge["source"], edge["action"], edge["targets"]
        require(type(source) is int and source in states and type(action) is str
                and action in actions and type(targets) is list and targets
                and all(type(target) is int and target in states for target in targets),
                f"{label} edge leaves domain")
        key = (source, action)
        require(key not in post, f"{label} repeats an edge")
        post[key] = tuple(targets)
    return initial, states, actions, post


def rooted_deterministic_isomorphism(
    expected_initial: Any,
    expected_states: Iterable[Any],
    expected_post: Mapping[tuple[Any, str], Sequence[Any]],
    observed_initial: int,
    observed_states: Iterable[int],
    observed_post: Mapping[tuple[int, str], Sequence[int]],
    actions: Iterable[str],
    label: str,
) -> dict[Any, int]:
    expected_set, observed_set = set(expected_states), set(observed_states)
    require(len(expected_set) == len(observed_set), f"{label} state census differs")
    forward = {expected_initial: observed_initial}
    reverse = {observed_initial: expected_initial}
    queue = deque([(expected_initial, observed_initial)])
    while queue:
        left, right = queue.popleft()
        for action in sorted(set(actions)):
            left_targets = tuple(expected_post.get((left, action), ()))
            right_targets = tuple(observed_post.get((right, action), ()))
            require(len(left_targets) == len(right_targets),
                    f"{label} enabled action/outcome census differs: {action}")
            require(len(left_targets) <= 1,
                    f"{label} leaves deterministic registered profile")
            if not left_targets:
                continue
            left_target, right_target = left_targets[0], right_targets[0]
            if left_target in forward:
                require(forward[left_target] == right_target,
                        f"{label} rooted graph mapping conflicts")
            elif right_target in reverse:
                raise SourceContractError(f"{label} rooted graph is not injective")
            else:
                forward[left_target] = right_target
                reverse[right_target] = left_target
                queue.append((left_target, right_target))
    require(set(forward) == expected_set and set(reverse) == observed_set,
            f"{label} graph contains unreachable states")
    return forward


def rooted_formula_isomorphism(
    expected: FormulaMachine,
    observed_initial: int,
    observed_states: frozenset[int],
    observed_post: Mapping[tuple[int, str], Sequence[int]],
    label: str,
) -> dict[int, int]:
    require(len(expected.states) == len(observed_states),
            f"{label} state census differs")
    forward = {expected.initial: observed_initial}
    reverse = {observed_initial: expected.initial}
    queue = deque([(expected.initial, observed_initial)])
    while queue:
        left, right = queue.popleft()
        for action in sorted(expected.alphabet):
            left_targets = expected.post.get((left, action), ())
            right_targets = tuple(observed_post.get((right, action), ()))
            require(len(left_targets) == 1 and len(right_targets) == 1,
                    f"{label} transition is incomplete: {action}")
            left_target, right_target = left_targets[0], right_targets[0]
            if left_target is BAD:
                require(right_target == -1, f"{label} ERROR target differs")
                continue
            require(type(left_target) is int and right_target != -1,
                    f"{label} safe/error partition differs")
            if left_target in forward:
                require(forward[left_target] == right_target,
                        f"{label} rooted graph mapping conflicts")
            elif right_target in reverse:
                raise SourceContractError(f"{label} rooted graph is not injective")
            else:
                forward[left_target] = right_target
                reverse[right_target] = left_target
                queue.append((left_target, right_target))
    require(set(forward) == set(expected.states)
            and set(reverse) == set(observed_states),
            f"{label} contains an unreachable state")
    return forward


def compare_formula_machine(expr: Expr, source_fluents: Mapping[str, Fluent],
                            raw_machine: Any, expected_name: str,
                            label: str) -> tuple[FormulaMachine, dict[int, int]]:
    row = _json_object(raw_machine, label)
    require(row.get("name") == expected_name, f"{label} name differs")
    initial, states, alphabet, post = observed_compact_machine(row, label)
    expected = compile_formula_machine(expr, source_fluents)
    require(alphabet == set(expected.alphabet) | {"tau"},
            f"{label} alphabet differs from source formula")
    require(all((state, "tau") not in post for state in states),
            f"{label} contains a tau transition")
    mapping = rooted_formula_isomorphism(expected, initial, states, post, label)
    return expected, mapping


@dataclass(frozen=True)
class ParsedSource:
    raw_sha256: str
    declarations: tuple[Declaration, ...]
    constants: Mapping[str, int]
    ranges: Mapping[str, tuple[int, ...]]
    sets: Mapping[str, frozenset[str]]
    maps: Mapping[str, tuple[str, ...]]
    process_specs: Mapping[str, ProcessSpec]
    relations: Mapping[str, tuple[TransferRow, ...]]
    fluents: Mapping[str, Fluent]
    assertions: Mapping[str, FormulaDecl]
    properties: Mapping[str, FormulaDecl]
    controller_specs: Mapping[str, Mapping[str, Any]]
    updating: Mapping[str, Mapping[str, Any]]


def parse_source(raw: bytes) -> ParsedSource:
    try:
        source = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise SourceContractError("source is not UTF-8") from error
    clean = _strip_comments(source)
    require(all(ord(character) < 128 for character in clean)
            and all(not character.isspace()
                    or character in " \t\r\n" for character in clean),
            "non-ASCII or unsupported whitespace outside comments")
    declarations = split_declarations(clean)
    constants = parse_constants(declarations)
    ranges = parse_ranges(declarations, constants)
    sets = parse_sets(declarations, ranges)
    maps = parse_maps(declarations)
    process_declarations = [declaration for declaration in declarations
                            if declaration.kind == "process"]
    require(len(process_declarations) == 2
            and len({declaration.name for declaration in process_declarations}) == 2,
            "process declaration census/uniqueness differs")
    process_specs = {declaration.name: parse_process(declaration)
                     for declaration in process_declarations}
    require(set(process_specs) == {"PRODUCTION_CELL_OLD", "PRODUCTION_CELL_NEW"},
            "process root census differs")
    relations = parse_relations(declarations, constants, ranges)
    fluents = parse_fluents(declarations, ranges, sets)
    assertions, properties = parse_formulas(declarations, ranges)
    known_events = frozenset(set().union(*sets.values()))
    validate_formula_namespace(assertions, properties, fluents, known_events)
    specs = parse_controller_specs(declarations)
    updating = parse_updating_controllers(declarations)
    validate_composition_bindings(declarations, updating)
    # All remaining declaration kinds are deliberately syntax checked here.
    for declaration in declarations:
        if declaration.kind in {"composition", "controller"}:
            require(declaration.text.endswith("."),
                    f"unterminated composition {declaration.name}")
        elif declaration.kind == "relation":
            require(declaration.text.endswith("}"),
                    f"unterminated relation {declaration.name}")
    return ParsedSource(sha256_bytes(raw), declarations, constants, ranges, sets,
                        maps, process_specs, relations, fluents, assertions,
                        properties, specs, updating)


def _machine_graph_from_source(source: ParsedSource, version: str,
                               arm: int) -> SourceGraph:
    return instantiate_process(source.process_specs[f"PRODUCTION_CELL_{version}"],
                               arm, source.constants, source.ranges)


def _requirements_for_spec(source: ParsedSource, spec_name: str,
                           arm: int) -> tuple[Expr, ...]:
    names = source.controller_specs[spec_name]["safety"]
    selected: list[Expr] = []
    for name in names:
        refs = expr_refs(resolve_property(name, source.properties, source.assertions))
        indices = {
            int(match.group(1)) for ref in refs
            if (match := re.search(r"\.([0-9]+)$", ref)) is not None
        }
        require(len(indices) == 1, f"safety property is not component-local: {name}")
        if indices == {arm}:
            selected.append(resolve_property(name, source.properties, source.assertions))
    require(len(selected) == 6, f"component {arm} safety requirement census differs")
    return tuple(selected)


def derive_controllers(source: ParsedSource) -> tuple[
        Mapping[int, SourceGraph], Mapping[int, SourceGraph],
        ControlledGraph, ControlledGraph]:
    old_graphs = {arm: _machine_graph_from_source(source, "OLD", arm)
                  for arm in source.ranges["Arms"]}
    new_graphs = {arm: _machine_graph_from_source(source, "NEW", arm)
                  for arm in source.ranges["Arms"]}
    old_control_name = source.controller_specs["DRILL_POLISH_CLEAN"]["controllable"]
    new_control_name = source.controller_specs["CLEAN_PAINT_DRILL"]["controllable"]
    require(old_control_name in source.sets and new_control_name in source.sets,
            "controller controllable set is unknown")
    old_local = [
        synthesize_component(old_graphs[arm],
                             _requirements_for_spec(source, "DRILL_POLISH_CLEAN", arm),
                             source.fluents, source.sets[old_control_name])
        for arm in source.ranges["Arms"]
    ]
    new_local = [
        synthesize_component(new_graphs[arm],
                             _requirements_for_spec(source, "CLEAN_PAINT_DRILL", arm),
                             source.fluents, source.sets[new_control_name])
        for arm in source.ranges["Arms"]
    ]
    return old_graphs, new_graphs, product_controllers(old_local), product_controllers(new_local)


@dataclass(frozen=True)
class DerivedSourceContract:
    definition: str
    selected: Mapping[str, Any]
    old_graphs: Mapping[int, SourceGraph]
    new_graphs: Mapping[int, SourceGraph]
    old_controller: ControlledGraph
    new_controller: ControlledGraph


def derive_source_contract(source: ParsedSource,
                           definition: str) -> DerivedSourceContract:
    require(definition in SUPPORTED_DEFINITIONS, "unsupported selected definition")
    require(definition in source.updating,
            "selected updating-controller definition is absent")
    selected = source.updating[definition]
    expected_keys = {
        "oldController", "newController", "oldEnvironment", "newEnvironment",
        "mapRelation", "oldGoal", "newGoal", "transition", "flags",
    }
    require(set(selected) == expected_keys,
            f"selected updating-controller field census differs: {definition}")
    require(selected["oldController"] == "C_DRILL_POLISH_CLEAN"
            and selected["newController"] == "C_CLEAN_PAINT_DRILL"
            and selected["oldGoal"] == "DRILL_POLISH_CLEAN"
            and selected["newGoal"] == "CLEAN_PAINT_DRILL",
            "selected controller/goal binding differs")
    require(selected["oldEnvironment"] ==
            ("PRODUCTION_CELL_OLD(1)", "PRODUCTION_CELL_OLD(2)")
            and selected["newEnvironment"] ==
            ("PRODUCTION_CELL_NEW(1)", "PRODUCTION_CELL_NEW(2)")
            and selected["mapRelation"] ==
            ("R_PRODUCTION_CELL_1_FG", "R_PRODUCTION_CELL_2_FG"),
            "selected environment/relation binding differs")
    require(selected["flags"] ==
            ("nonblocking", "revised_on_the_fly", "fine_grained"),
            "selected update semantics flags differ")
    expected_transitions: tuple[str, ...]
    if definition == "UpdCont_OTF_FG":
        expected_transitions = ()
    else:
        expected_transitions = tuple(
            name for name in (
                *("R2_StopOldSpec_" + requirement
                  for requirement in source.controller_specs["DRILL_POLISH_CLEAN"]["safety"]),
                *("R2_StartNewSpec_" + requirement
                  for requirement in source.controller_specs["CLEAN_PAINT_DRILL"]["safety"]),
            )
        )
    require(len(selected["transition"]) == len(expected_transitions)
            and set(selected["transition"]) == set(expected_transitions),
            "selected transition-requirement census differs")
    for name in expected_transitions:
        require(name in source.properties,
                f"selected transition property is absent: {name}")
    old_graphs, new_graphs, old_controller, new_controller = derive_controllers(source)
    return DerivedSourceContract(definition, selected, old_graphs, new_graphs,
                                 old_controller, new_controller)


def _canonical_graph_payload(graph: ControlledGraph | SourceGraph) -> dict[str, Any]:
    order = [graph.initial]
    identifiers = {graph.initial: 0}
    queue = deque([graph.initial])
    edges: list[dict[str, Any]] = []
    while queue:
        state = queue.popleft()
        for action in sorted(graph.alphabet):
            targets = tuple(graph.post.get((state, action), ()))
            if not targets:
                continue
            target_ids: list[int] = []
            for target in targets:
                if target not in identifiers:
                    identifiers[target] = len(order)
                    order.append(target)
                    queue.append(target)
                target_ids.append(identifiers[target])
            edges.append({"source": identifiers[state], "action": action,
                          "targets": target_ids})
    require(len(order) == len(graph.states), "derived graph contains unreachable states")
    return {"states": len(order), "actions": sorted(graph.alphabet), "edges": edges}


def _canonical_graph_state_ids(
    graph: ControlledGraph | SourceGraph,
) -> dict[Any, int]:
    """Give reachable states rename-invariant BFS identifiers."""
    identifiers = {graph.initial: 0}
    queue = deque([graph.initial])
    while queue:
        state = queue.popleft()
        for action in sorted(graph.alphabet):
            for target in graph.post.get((state, action), ()):
                if target not in identifiers:
                    identifiers[target] = len(identifiers)
                    queue.append(target)
    require(len(identifiers) == len(graph.states),
            "derived graph contains unreachable states")
    return identifiers


def _formula_payload(machine: FormulaMachine) -> dict[str, Any]:
    rows = []
    for state in sorted(machine.states):
        for action in sorted(machine.alphabet):
            target = machine.post[(state, action)][0]
            rows.append({"source": state, "action": action,
                         "target": -1 if target is BAD else target})
    return {"states": len(machine.states), "actions": sorted(machine.alphabet),
            "edges": rows}


def _compare_component(source_graph: SourceGraph, raw_machine: Any,
                       label: str) -> tuple[dict[str, int], dict[str, Any]]:
    initial, states, alphabet, post = observed_compact_machine(raw_machine, label)
    expected_alphabet = ({"tau", "tau?"} | set(source_graph.alphabet)
                         | {action + "?" for action in source_graph.alphabet})
    require(alphabet == expected_alphabet,
            f"{label} raw/modal alphabet differs from source")
    require(all(action in source_graph.alphabet for _state, action in post),
            f"{label} contains a tau/modal transition")
    mapping = rooted_deterministic_isomorphism(
        source_graph.initial, source_graph.states, source_graph.post,
        initial, states, post, source_graph.alphabet, label)
    return mapping, _canonical_graph_payload(source_graph)


def _compare_formula_group(source: ParsedSource, ir: Mapping[str, Any],
                           field: str, names: Sequence[str]) -> tuple[
                               dict[str, tuple[FormulaMachine, dict[int, int]]],
                               list[dict[str, Any]]]:
    rows = _json_array(ir.get(field), field)
    observed_names = [
        _json_object(row, f"{field}[{index}]").get("name")
        for index, row in enumerate(rows)
    ]
    require(observed_names == sorted(names) and len(observed_names) == len(set(names)),
            f"{field} name/order census differs")
    result: dict[str, tuple[FormulaMachine, dict[int, int]]] = {}
    payload: list[dict[str, Any]] = []
    for index, (name, row) in enumerate(zip(observed_names, rows)):
        expr = resolve_property(name, source.properties, source.assertions)
        machine, mapping = compare_formula_machine(
            expr, source.fluents, row, name, f"{field}[{index}]")
        result[name] = (machine, mapping)
        payload.append({"name": name, "machine": _formula_payload(machine)})
    return result, payload


def compare_observers_and_activation(
    source: ParsedSource,
    ir: Mapping[str, Any],
    new_requirements: Sequence[str],
    new_machines: Mapping[str, tuple[FormulaMachine, dict[int, int]]],
    normal_actions: frozenset[str],
    progress: Sequence[str],
) -> dict[str, Any]:
    formulas = {
        name: resolve_property(name, source.properties, source.assertions)
        for name in new_requirements
    }
    all_refs = set().union(*(set(expr_refs(expr)) for expr in formulas.values()))
    fluent_observers = all_refs & set(source.fluents)
    event_observers = all_refs - set(source.fluents)
    expected_names = sorted(
        set(fluent_observers) | {action + "_a" for action in event_observers})
    universe = frozenset(set(normal_actions) | set(progress)
                         | {"hotSwapIn", "hotSwapOut"})
    raw_observers = _json_array(ir.get("observer_machines"), "observer_machines")
    registry = _json_array(ir.get("observer_registry"), "observer_registry")
    require(len(raw_observers) == len(registry) == len(expected_names),
            "observer/registry census differs from source")
    observer_maps: dict[str, dict[bool, int]] = {}
    observer_payload: list[dict[str, Any]] = []

    def expected_target(name: str, value: bool, action: str) -> bool:
        if name in source.fluents:
            return source.fluents[name].step(value, action)
        require(name.endswith("_a"), f"unknown source observer {name}")
        return action == name[:-2]

    for index, name in enumerate(expected_names):
        row = _json_object(registry[index], f"observer_registry[{index}]")
        require(set(row) == {"id", "index", "name", "machine"}
                and row["id"] == f"observer:{name}:{index}"
                and row["index"] == index and row["name"] == name,
                f"observer registry binding differs: {name}")
        require(row["machine"] == raw_observers[index],
                f"observer registry/machine copy differs: {name}")
        machine = _json_object(raw_observers[index], f"observer {name}")
        require(machine.get("name") == name, f"observer name differs: {name}")
        initial, states, alphabet, post = observed_compact_machine(
            machine, f"observer {name}")
        require(states == {0, 1} and alphabet == universe,
                f"observer domain/alphabet differs: {name}")
        expected_post = {
            (value, action): (expected_target(name, value, action),)
            for value in (False, True) for action in universe
        }
        mapping = rooted_deterministic_isomorphism(
            False, {False, True}, expected_post, initial, states, post,
            universe, f"observer {name}")
        observer_maps[name] = mapping
        observer_payload.append({
            "name": name,
            "false_state": mapping[False], "true_state": mapping[True],
            "alphabet_count": len(universe),
        })

    activations = _json_array(ir.get("new_activation_sources"),
                              "new_activation_sources")
    sorted_requirements = sorted(new_requirements)
    require(len(activations) == len(sorted_requirements),
            "activation source census differs")
    activation_payload: list[dict[str, Any]] = []
    total_rows = 0
    total_errors = 0
    name_to_index = {name: index for index, name in enumerate(expected_names)}
    for ordinal, requirement in enumerate(sorted_requirements):
        row = _json_object(activations[ordinal], f"activation[{ordinal}]")
        require(set(row) == {"new_requirement_id", "safety_machine", "mode",
                             "ordered_observer_indices", "ordered_observer_ids",
                             "mapping_rows"},
                f"activation[{ordinal}] key census differs")
        require(row["new_requirement_id"] == f"new:{requirement}:{ordinal}"
                and row["safety_machine"] == requirement
                and row["mode"] == "OBSERVER_MAPPING",
                f"activation identity/mode differs: {requirement}")
        expr = formulas[requirement]
        refs = set(expr_refs(expr))
        property_names = sorted(
            (ref if ref in source.fluents else ref + "_a") for ref in refs)
        indices = [name_to_index[name] for name in property_names]
        ids = [f"observer:{name}:{name_to_index[name]}" for name in property_names]
        require(row["ordered_observer_indices"] == indices
                and row["ordered_observer_ids"] == ids,
                f"activation observer binding differs: {requirement}")

        initial_tuple = tuple(False for _ in property_names)
        reachable = {initial_tuple}
        queue = deque([initial_tuple])

        def values_for(state: tuple[bool, ...]) -> dict[str, bool]:
            return {
                ref: state[property_names.index(
                    ref if ref in source.fluents else ref + "_a")]
                for ref in refs
            }

        while queue:
            state = queue.popleft()
            for action in sorted(universe):
                target = tuple(expected_target(name, value, action)
                               for name, value in zip(property_names, state))
                if target not in reachable:
                    reachable.add(target)
                    # MTSA's safety-state map retains the first violating
                    # observer tuple as ERROR, but ERROR has no outgoing
                    # language.  Do not close tuples beyond that boundary.
                    if eval_expr(expr, values_for(target), action):
                        queue.append(target)
        formula_machine, tester_mapping = new_machines[requirement]
        expected_rows: list[dict[str, Any]] = []
        for state in sorted(reachable):
            values = values_for(state)
            active_events = sorted(ref for ref in refs - set(source.fluents)
                                   if values[ref])
            require(len(active_events) <= 1,
                    f"event observers overlap in reachable tuple: {requirement}")
            action = active_events[0] if active_events else "__no_current_event__"
            if not eval_expr(expr, values, action):
                tester_state = -1
            else:
                valuation = tuple(values[name]
                                  for name in formula_machine.fluent_names)
                require(valuation in formula_machine.valuation_state,
                        f"activation valuation is outside compiled tester: {requirement}")
                tester_state = tester_mapping[
                    formula_machine.valuation_state[valuation]]
            observed_tuple = [
                observer_maps[name][value]
                for name, value in zip(property_names, state)
            ]
            expected_rows.append({"observer_state_tuple": observed_tuple,
                                  "tester_state": tester_state})
        expected_rows.sort(key=lambda item: item["observer_state_tuple"])
        if row["mapping_rows"] != expected_rows:
            observed_rows = row["mapping_rows"]
            mismatch = next((index for index, pair in enumerate(
                itertools.zip_longest(observed_rows, expected_rows))
                if pair[0] != pair[1]), None)
            raise SourceContractError(
                f"activation mapping semantics differ: {requirement}; "
                f"observed={len(observed_rows)}, expected={len(expected_rows)}, "
                f"first={mismatch}, "
                f"observed_row={observed_rows[mismatch] if mismatch is not None and mismatch < len(observed_rows) else None}, "
                f"expected_row={expected_rows[mismatch] if mismatch is not None and mismatch < len(expected_rows) else None}"
            )
        error_count = sum(item["tester_state"] == -1 for item in expected_rows)
        total_rows += len(expected_rows)
        total_errors += error_count
        activation_payload.append({
            "requirement": requirement,
            "observers": property_names,
            "mapping_rows": len(expected_rows),
            "error_rows": error_count,
        })
    return {
        "observer_count": len(expected_names),
        "activation_row_count": total_rows,
        "activation_error_count": total_errors,
        "payload": {
            "universe_actions": sorted(universe),
            "observers": observer_payload,
            "activations": activation_payload,
        },
    }


def compare_ir(source: ParsedSource, derived: DerivedSourceContract,
               ir: Mapping[str, Any]) -> dict[str, Any]:
    require(set(ir) == IR_ROOT_KEYS, "IR root key census differs")
    require(ir.get("schema_version") == "fg-ducs-post-frontend-contract-facts-v1"
            and ir.get("evidence_scope") ==
            "shared_mtsa_post_frontend_conclusion_free_contract",
            "IR schema/evidence scope differs")
    require(ir.get("source_name") == "ProductionCell_Arms=2_FG.lts"
            and ir.get("source_sha256") == source.raw_sha256
            and ir.get("definition") == derived.definition,
            "IR source/definition binding differs")
    require(ir.get("flags") == {
        "on_the_fly": True, "revised_on_the_fly": True,
        "fine_grained": True, "selective": False,
        "direct_transfer_relations": True,
    }, "IR update-semantics flags differ")
    require(ir.get("shared_mtsa_frontend") is True
            and ir.get("independent_source_frontend") is False
            and ir.get("old_new_controller_synthesis_performed") is True
            and ir.get("source_to_witness_replay") is False,
            "IR producer provenance boundary differs")
    require(ir.get("extraction_stage") ==
            "AFTER_FIXED_ENDPOINT_CONTROLLER_SYNTHESIS_BEFORE_ENDPOINT_PRODUCT",
            "IR extraction stage differs")
    for key in (
        "fixed_endpoint_products_materialized", "local_update_games_materialized",
        "global_mixed_game_materialized", "conclusion_fields_present",
        "physical_closure_materialized", "activation_relations_materialized",
        "goal_signatures_materialized", "dependency_partition_materialized",
        "winning_certificate_materialized",
    ):
        require(ir.get(key) is False, f"IR conclusion boundary differs: {key}")

    component_rows = _json_array(ir.get("components"), "components")
    require(len(component_rows) == 2, "IR component census differs")
    component_payload: list[dict[str, Any]] = []
    reconfigure_actions: list[str] = []
    for index, arm in enumerate(source.ranges["Arms"]):
        row = _json_object(component_rows[index], f"component[{index}]")
        require(set(row) == {"index", "old_machine", "new_machine",
                             "transfer_relation", "transfer_has_action_sequence",
                             "reconfigure_action"},
                f"component[{index}] key census differs")
        require(row["index"] == index and row["transfer_has_action_sequence"] is False,
                f"component[{index}] declaration differs")
        old_map, old_payload = _compare_component(
            derived.old_graphs[arm], row["old_machine"], f"component[{index}].old")
        new_map, new_payload = _compare_component(
            derived.new_graphs[arm], row["new_machine"], f"component[{index}].new")
        relation_name = derived.selected["mapRelation"][index]
        relation = source.relations[relation_name]
        expected_owner_old = derived.selected["oldEnvironment"][index]
        expected_owner_new = derived.selected["newEnvironment"][index]
        require(all(item.old_owner == expected_owner_old
                    and item.new_owner == expected_owner_new for item in relation),
                f"component[{index}] relation owner differs")
        actions = {item.action for item in relation}
        require(len(actions) == 1, f"component[{index}] relation action differs")
        reconfigure = next(iter(actions))
        require(row["reconfigure_action"] == reconfigure,
                f"component[{index}] reconfigure binding differs")
        require(all(item.old_state in old_map and item.new_state in new_map
                    for item in relation),
                f"component[{index}] relation references an unknown state")
        expected_transfer = {
            old_map[item.old_state]: (new_map[item.new_state],)
            for item in relation
        }
        require(len(expected_transfer) == len(relation),
                f"component[{index}] transfer repeats a source")
        observed_transfer: dict[int, tuple[int, ...]] = {}
        for raw in _json_array(row["transfer_relation"],
                               f"component[{index}].transfer"):
            edge = _json_object(raw, "transfer row")
            require(set(edge) == {"source", "targets"}
                    and type(edge["source"]) is int
                    and type(edge["targets"]) is list
                    and edge["targets"]
                    and all(type(target) is int for target in edge["targets"]),
                    f"component[{index}] transfer row differs")
            require(edge["source"] not in observed_transfer,
                    f"component[{index}] repeats a transfer source")
            observed_transfer[edge["source"]] = tuple(edge["targets"])
        require(observed_transfer == expected_transfer,
                f"component[{index}] transfer semantics differ from source")
        reconfigure_actions.append(reconfigure)
        old_canonical = _canonical_graph_state_ids(derived.old_graphs[arm])
        new_canonical = _canonical_graph_state_ids(derived.new_graphs[arm])
        canonical_transfer = [
            {"old": old_canonical[item.old_state], "action": item.action,
             "new": new_canonical[item.new_state]} for item in relation
        ]
        canonical_transfer.sort(
            key=lambda item: (item["old"], item["action"], item["new"]))
        component_payload.append({
            "arm": arm, "old": old_payload, "new": new_payload,
            "transfer": canonical_transfer,
        })

    controller_rows = _json_object(ir.get("controllers"), "controllers")
    require(set(controller_rows) == {"old", "new"},
            "controller role census differs")
    controller_payload: dict[str, Any] = {}
    for role, graph in (("old", derived.old_controller),
                        ("new", derived.new_controller)):
        initial, states, actions, post = observed_controller(
            controller_rows[role], f"{role} controller")
        expected_actions = set(graph.alphabet) | {"tau"}
        require(actions == expected_actions,
                f"{role} controller alphabet differs from source synthesis")
        require(all(action in graph.alphabet for _state, action in post),
                f"{role} controller contains a tau/non-source edge")
        rooted_deterministic_isomorphism(
            graph.initial, graph.states, graph.post, initial, states, post,
            graph.alphabet, f"{role} controller")
        controller_payload[role] = _canonical_graph_payload(graph)

    old_requirements = source.controller_specs["DRILL_POLISH_CLEAN"]["safety"]
    new_requirements = source.controller_specs["CLEAN_PAINT_DRILL"]["safety"]
    old_machines, old_formula_payload = _compare_formula_group(
        source, ir, "old_safety_machines", old_requirements)
    new_machines, new_formula_payload = _compare_formula_group(
        source, ir, "new_safety_machines", new_requirements)
    transition_names = tuple(derived.selected["transition"])
    transition_machines, transition_formula_payload = _compare_formula_group(
        source, ir, "transition_requirement_machines", transition_names)

    old_stop = {name: "stopOldSpec_" + name for name in old_requirements}
    new_start = {name: "startNewSpec_" + name for name in new_requirements}
    progress = tuple(old_stop[name] for name in old_requirements) + tuple(
        new_start[name] for name in new_requirements) + tuple(reconfigure_actions)
    protocol = _json_object(ir.get("protocol"), "protocol")
    require(set(protocol) == {
        "progress_actions_in_index_order", "stop_old_actions",
        "reconfigure_actions", "start_new_actions",
        "old_safety_to_stop_action", "new_safety_to_start_action",
        "action_to_mapping_indices", "precedence",
    }, "protocol key census differs")
    observed_progress = protocol["progress_actions_in_index_order"]
    require(type(observed_progress) is list
            and all(type(action) is str for action in observed_progress)
            and len(observed_progress) == len(set(observed_progress))
            and set(observed_progress) == set(progress)
            and protocol["stop_old_actions"] == sorted(old_stop.values())
            and protocol["reconfigure_actions"] == sorted(reconfigure_actions)
            and protocol["start_new_actions"] == sorted(new_start.values())
            and protocol["old_safety_to_stop_action"] == old_stop
            and protocol["new_safety_to_start_action"] == new_start
            and protocol["precedence"] == [],
            "protocol action/binding semantics differ from source")
    require(protocol["action_to_mapping_indices"] == [
        {"action": reconfigure_actions[index], "mapping_indices": [index]}
        for index in range(2)
    ], "protocol relation/action mapping differs from source")
    old_control = source.sets[
        source.controller_specs["DRILL_POLISH_CLEAN"]["controllable"]]
    new_control = source.sets[
        source.controller_specs["CLEAN_PAINT_DRILL"]["controllable"]]
    expected_controllable = sorted(
        set(old_control) | set(new_control) | set(progress) | {"hotSwapOut"})
    require(ir.get("controllable_actions") == expected_controllable,
            "IR controllable action census differs from source")
    require(ir.get("boundary_actions") == {
        "hot_swap_in": "hotSwapIn", "hot_swap_out": "hotSwapOut"},
        "IR boundary actions differ")
    require(ir.get("load_selector") == {
        "mode": "ALL_REACHABLE", "reachable_indices": []},
        "IR load selector differs from selected source profile")

    semantic_payload = {
        "profile": "productioncell-arms2-bounded-source-v1",
        "definition": derived.definition,
        "components": component_payload,
        "controllers": controller_payload,
        "old_safety": old_formula_payload,
        "new_safety": new_formula_payload,
        "transition_requirements": transition_formula_payload,
        "protocol": {
            "progress": sorted(progress), "old_stop": old_stop,
            "new_start": new_start, "reconfigure": sorted(reconfigure_actions),
        },
    }
    # The observer/activation comparison below is intentionally mandatory;
    # these fields are not delegated to the already-supplied IR.
    observer_summary = compare_observers_and_activation(
        source, ir, new_requirements, new_machines,
        frozenset(set(derived.old_controller.alphabet)
                  | set(derived.new_controller.alphabet)), progress)
    semantic_payload["observer_activation"] = observer_summary["payload"]
    semantic_digest = sha256_bytes(canonical_bytes(semantic_payload))
    controller_pair_digest = sha256_bytes(canonical_bytes(controller_payload))
    return {
        "schema_version": REPORT_SCHEMA,
        "status": "SOURCE_TO_POST_FRONTEND_CONTRACT_SEMANTICS_VERIFIED",
        "profile": "productioncell-arms2-bounded-source-v1",
        "source_name": "ProductionCell_Arms=2_FG.lts",
        "source_sha256": source.raw_sha256,
        "definition": derived.definition,
        "source_semantic_digest": semantic_digest,
        "controller_pair_semantic_digest": controller_pair_digest,
        "bounded_registered_mtsa_lts_frontend_replay": True,
        "independent_old_new_controller_synthesis": True,
        "independent_controller_pair_synthesis_count": 1,
        "source_to_post_frontend_contract_semantic_agreement": True,
        "independent_win_synthesis": False,
        "source_to_win_replay": False,
        "certificate_supplied_downstream": True,
        "verified_fields": [
            "components", "transfer_relations", "old_safety_machines",
            "new_safety_machines", "transition_requirement_machines",
            "observer_machines", "observer_registry", "new_activation_sources",
            "controllers", "protocol", "controllable_actions", "flags",
            "boundary_actions", "load_selector",
        ],
        "census": {
            "components": 2,
            "old_controller_states": len(derived.old_controller.states),
            "old_controller_edges": len(derived.old_controller.post),
            "new_controller_states": len(derived.new_controller.states),
            "new_controller_edges": len(derived.new_controller.post),
            "old_safety_machines": len(old_machines),
            "new_safety_machines": len(new_machines),
            "transition_requirement_machines": len(transition_machines),
            "observers": observer_summary["observer_count"],
            "activation_rows": observer_summary["activation_row_count"],
            "activation_error_rows": observer_summary["activation_error_count"],
            "progress_actions": len(progress),
        },
        "claim_boundary": {
            "bounded_registered_source_profile": True,
            "general_mtsa_frontend": False,
            "same_author_implementation": True,
            "post_outcome": True,
            "one_source": True,
            "one_provenance_cluster": True,
            "transitive_runtime_frozen": False,
            "held_out": False,
            "third_party": False,
            "production": False,
        },
    }


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--definition", required=True, choices=sorted(SUPPORTED_DEFINITIONS))
    parser.add_argument("--ir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    try:
        raw = args.source.read_bytes()
        source = parse_source(raw)
        # This closed derivation deliberately completes before the IR path is
        # opened.  A facts-informed parser or controller replay cannot cross
        # this boundary accidentally.
        derived = derive_source_contract(source, args.definition)
        ir_raw = args.ir.read_bytes()
        ir = strict_json_bytes(ir_raw)
        report = compare_ir(source, derived, ir)
        report["ir_sha256"] = sha256_bytes(ir_raw)
        args.output.write_bytes(canonical_bytes(report))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError,
            SourceContractError) as error:
        print("SOURCE_CONTRACT_INVALID=" + str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
