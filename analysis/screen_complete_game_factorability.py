#!/usr/bin/env python3
"""Coordinate-relative factorability screen for the 43 public v1 bundles.

This is deliberately *not* the typed partition-discovery algorithm.  The v1
bundle stores physical state as an opaque Java string and omits action owners,
RS/load/handover/precedence declarations, and preterminal Goal Post.  The
screen parses only the fixed public serialization, forms conservative support
components from coordinates co-changed by an outcome, and reports Cartesian
closure obstructions.  It cannot establish typed block-factorability or an
application-population rate.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence


SCHEMA = "fg-ducs-v1-bundle-coordinate-screen-v1"
BUNDLE_SCHEMA = "fse2027-independent-strong-game-bundle-v1"


class ScreenError(RuntimeError):
    pass


def need(condition: bool, message: str) -> None:
    if not condition:
        raise ScreenError(message)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ScreenError(f"invalid JSON: {path}") from error
    need(isinstance(value, dict), f"JSON root is not an object: {path}")
    return value


def split_vector(text: str) -> list[str]:
    need(text.startswith("[") and text.endswith("]"), f"physical vector has an unknown serialization: {text!r}")
    body = text[1:-1]
    if not body:
        return []
    result: list[str] = []
    start = 0
    round_depth = square_depth = 0
    for index, character in enumerate(body):
        if character == "(":
            round_depth += 1
        elif character == ")":
            round_depth -= 1
        elif character == "[":
            square_depth += 1
        elif character == "]":
            square_depth -= 1
        elif character == "," and round_depth == 0 and square_depth == 0:
            result.append(body[start:index].strip())
            start = index + 1
        need(round_depth >= 0 and square_depth >= 0, "physical vector brackets are unbalanced")
    need(round_depth == 0 and square_depth == 0, "physical vector brackets are unbalanced")
    result.append(body[start:].strip())
    need(all(result), "physical vector has an empty component")
    return result


def game_path(root: Path, identifier: str) -> Path:
    if identifier in {"ardrone_semantic_positive", "ardrone_semantic_negative"}:
        return root / "evidence/m8m-source-anchored/external/cases" / identifier / "java-independent-game.json"
    return root / "evidence/m8n-game-equivalence/cases" / identifier / "java-independent-game.json"


def valuations(bundle: Mapping[str, Any]) -> tuple[list[str], dict[str, tuple[Any, ...]]]:
    states = bundle.get("states")
    need(isinstance(states, list) and states, "bundle states differ")
    tester_ids = sorted({key for state in states for key in state.get("active_testers", {})})
    pending_ids = sorted({action for state in states for action in state.get("pending_actions", [])})
    physical_vectors = [split_vector(state.get("physical")) for state in states]
    sizes = {len(vector) for vector in physical_vectors}
    need(len(sizes) == 1, "physical vector arity differs inside one bundle")
    physical_count = next(iter(sizes))
    coordinates = (
        [f"physical[{index}]" for index in range(physical_count)]
        + [f"tester:{identifier}" for identifier in tester_ids]
        + [f"pending:{action}" for action in pending_ids]
    )
    values: dict[str, tuple[Any, ...]] = {}
    for state, physical in zip(states, physical_vectors):
        identifier = state.get("id")
        testers = state.get("active_testers")
        pending = state.get("pending_actions")
        need(isinstance(identifier, str) and identifier not in values, "bundle state id differs")
        need(isinstance(testers, dict) and isinstance(pending, list), "bundle state projection differs")
        values[identifier] = tuple(
            list(physical)
            + [testers.get(name, "<BOT>") for name in tester_ids]
            + [action in pending for action in pending_ids]
        )
    return coordinates, values


def screen(identifier: str, bundle: Mapping[str, Any], sha256: str) -> dict[str, Any]:
    need(bundle.get("schema_version") == BUNDLE_SCHEMA, f"bundle schema differs: {identifier}")
    coordinates, values = valuations(bundle)
    varying = [
        index for index, _coordinate in enumerate(coordinates)
        if len({vector[index] for vector in values.values()}) > 1
    ]
    parent = {index: index for index in varying}

    def root(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def merge(left: int, right: int) -> None:
        a, b = root(left), root(right)
        if a != b:
            parent[max(a, b)] = min(a, b)

    buckets = bundle.get("buckets")
    need(isinstance(buckets, list), "bundle buckets differ")
    first_multi_change: dict[str, Any] | None = None
    bucket_count = 0
    edge_count = 0
    for bucket in buckets:
        need(isinstance(bucket, dict) and set(bucket) == {"source", "action", "controllable", "targets"}, "bundle bucket record differs")
        source, action, targets = bucket["source"], bucket["action"], bucket["targets"]
        need(source in values and isinstance(action, str) and type(bucket["controllable"]) is bool, "bundle bucket typing differs")
        need(isinstance(targets, list) and targets and set(targets) <= set(values), "bundle targets differ")
        bucket_count += 1
        edge_count += len(targets)
        for target in targets:
            changed = [index for index in varying if values[source][index] != values[target][index]]
            for index in changed[1:]:
                merge(changed[0], index)
            if len(changed) > 1 and (
                first_multi_change is None
                or (identifier.startswith("ardrone_") and action == "batteryUse" and first_multi_change["action"] != "batteryUse")
            ):
                first_multi_change = {
                    "source": source,
                    "action": action,
                    "target": target,
                    "changed_coordinates": [coordinates[index] for index in changed],
                    "before": [values[source][index] for index in changed],
                    "after": [values[target][index] for index in changed],
                }

    components: dict[int, list[int]] = {}
    for index in varying:
        components.setdefault(root(index), []).append(index)
    blocks = sorted((tuple(indices) for indices in components.values()), key=lambda item: item)
    domains = [
        {tuple(vector[index] for index in block) for vector in values.values()}
        for block in blocks
    ]
    observed = {
        tuple(tuple(vector[index] for index in block) for block in blocks)
        for vector in values.values()
    }
    expected_count = 1
    for domain in domains:
        expected_count *= len(domain)
    missing = None
    if expected_count != len(observed):
        for candidate in itertools.product(*(sorted(domain, key=repr) for domain in domains)):
            if candidate not in observed:
                missing = candidate
                break
    goal_count = len(bundle.get("goal_state_ids", []))
    if len(blocks) <= 1:
        classification = "SINGLE_SUPPORT_COMPONENT"
    elif expected_count != len(observed):
        classification = "MISSING_CARTESIAN_TUPLE"
    elif goal_count == 0:
        classification = "RECTANGULAR_BUT_GOAL_EMPTY"
    else:
        classification = "UNTYPED_CANDIDATE_ONLY"
    return {
        "id": identifier,
        "bundle_sha256": sha256,
        "state_count": len(values),
        "bucket_count": bucket_count,
        "outcome_edge_count": edge_count,
        "goal_count": goal_count,
        "coordinate_count": len(coordinates),
        "varying_coordinate_count": len(varying),
        "support_component_count": len(blocks),
        "support_components": [[coordinates[index] for index in block] for block in blocks],
        "expected_cartesian_state_count": expected_count,
        "classification": classification,
        "missing_projection_tuple": missing,
        "first_multi_coordinate_change": first_multi_change,
    }


def run(root: Path) -> dict[str, Any]:
    summary_path = root / "evidence/m8n-game-equivalence/summary.json"
    summary = load(summary_path)
    cases = summary.get("cases")
    need(isinstance(cases, list) and len(cases) == summary.get("case_count") == 43, "M8n case census differs")
    records = []
    for case in cases:
        identifier = case.get("id")
        expected_sha = case.get("java_game_sha256")
        need(isinstance(identifier, str) and isinstance(expected_sha, str), "M8n case identity differs")
        path = game_path(root, identifier)
        actual_sha = digest(path)
        need(actual_sha == expected_sha, f"M8n game hash differs: {identifier}")
        records.append(screen(identifier, load(path), actual_sha))

    classifications = Counter(record["classification"] for record in records)
    c1 = [record for record in records if not record["id"].startswith("ardrone_")]
    c3 = [record for record in records if record["id"].startswith("ardrone_")]
    family_records: dict[str, list[dict[str, Any]]] = {}
    for record in c1:
        family_records.setdefault(record["id"].split("__", 1)[0], []).append(record)
    family_summary = {
        family: {
            "variant_count": len(items),
            "classifications": dict(sorted(Counter(item["classification"] for item in items).items())),
            "state_counts": sorted({item["state_count"] for item in items}),
        }
        for family, items in sorted(family_records.items())
    }
    return {
        "schema_version": SCHEMA,
        "status": "PASS",
        "analysis_class": "coordinate-relative conservative diagnostic; not typed block-factorability",
        "input_summary_sha256": digest(summary_path),
        "case_count": len(records),
        "c1_case_count": len(c1),
        "c1_semantic_family_count": len(family_summary),
        "c3_author_adaptation_case_count": len(c3),
        "totals": {
            "states": sum(record["state_count"] for record in records),
            "buckets": sum(record["bucket_count"] for record in records),
            "outcome_edges": sum(record["outcome_edge_count"] for record in records),
        },
        "classifications": dict(sorted(classifications.items())),
        "nontrivial_typed_positive_claim_count": 0,
        "family_summary": family_summary,
        "cases": records,
        "limitations": [
            "physical coordinates are parsed from a fixed Java toString representation",
            "co-change support is conservative and ignores exotic state recodings",
            "v1 omits action owner/kind, full requirement/RS typing, precedence, Z_load and handover",
            "v1 omits preterminal Goal and unsafe Post buckets",
            "41 C1 cases are variants of ten semantic families, not independent applications",
            "the two C3 cases are author adaptations, not native third-party contracts",
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report = run(args.artifact_root.resolve())
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8", newline="\n")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
