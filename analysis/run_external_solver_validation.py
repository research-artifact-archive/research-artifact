#!/usr/bin/env python3
"""Run the preregistered independent-front-end/PRISM-games validation.

This is deliberately a correctness and interoperability campaign.  It does
not compare PRISM's full-game materialization time with the production OTF
solver's partial exploration time.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

from independent_raw_oracle import (
    ExplicitStrongGame,
    build_explicit_game,
    canonical_json_bytes,
    sha256_bytes,
)


SCHEMA_VERSION = "fse2027-external-solver-validation-v1"
RESULT_PATTERN = re.compile(
    r"^Result:\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?)",
    flags=re.MULTILINE,
)


@dataclass(frozen=True)
class PrismEncoding:
    source: str
    node_count: int
    edge_count: int
    controller_nodes: int
    environment_nodes: int
    action_nodes: int


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--prism-bin", type=Path, required=True)
    parser.add_argument("--prism-archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--semantic-manifest",
        type=Path,
        default=Path("inputs/c1/semantic_boundaries_v2/manifest.json"),
        help="public semantic manifest (default: artifact-relative C1 manifest)",
    )
    parser.add_argument(
        "--java-runs",
        type=Path,
        default=Path("evidence/m6-prism/java_runs.csv"),
        help="public sanitized Direct-Full/FG Java result table",
    )
    return parser.parse_args()


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_registered(root: Path, value: str) -> Path:
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("registered path must be repository-relative: " + value)
    result = (root / relative).resolve()
    result.relative_to(root)
    if not result.is_file() or result.is_symlink():
        raise ValueError("registered regular file is missing: " + str(result))
    return result


def require_hash(path: Path, expected: str, label: str) -> None:
    actual = digest(path)
    if actual != expected:
        raise ValueError(
            "%s SHA-256 mismatch: expected %s, observed %s"
            % (label, expected, actual)
        )


def write_new(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        try:
            path.unlink()
        except OSError:
            pass
        raise


def _state_label(state: object) -> str:
    return repr(state).replace("\\", "\\\\").replace('"', '\\"')


def encode_prism_game(game: ExplicitStrongGame) -> PrismEncoding:
    """Encode the complete strong game as a deterministic-choice SMG."""
    states = sorted(game.states)
    state_node = {state: index + 1 for index, state in enumerate(states)}
    next_node = len(states) + 1
    owners: Dict[int, str] = {0: "environment"}
    edges: Dict[int, List[int]] = {
        0: [state_node[state] for state in sorted(game.initial_states)]
    }
    labels: Dict[int, str] = {0: "all-Q0 environment root"}
    action_nodes = 0

    for state in states:
        node = state_node[state]
        labels[node] = _state_label(state)
        if state in game.goals:
            owners[node] = "controller"
            edges[node] = [node]
            continue
        if state[3]:
            owners[node] = "environment"
            edges[node] = [node]
            continue

        outgoing = game.successors.get(state, {})
        uncontrollable = [
            action
            for action in sorted(outgoing)
            if outgoing[action] and not game.is_controllable(action)
        ]
        if uncontrollable:
            owners[node] = "environment"
            edges[node] = [
                state_node[target]
                for action in uncontrollable
                for target in sorted(outgoing[action])
            ]
            continue

        controllable = [
            action
            for action in sorted(outgoing)
            if outgoing[action] and game.is_controllable(action)
        ]
        if not controllable:
            owners[node] = "environment"
            edges[node] = [node]
            continue

        owners[node] = "controller"
        choices: List[int] = []
        for action in controllable:
            action_node = next_node
            next_node += 1
            action_nodes += 1
            owners[action_node] = "environment"
            labels[action_node] = "choice " + action + " from " + repr(state)
            edges[action_node] = [
                state_node[target] for target in sorted(outgoing[action])
            ]
            choices.append(action_node)
        edges[node] = choices

    if not edges[0]:
        raise ValueError("external game has no initial roots")
    if set(edges) != set(owners) or any(not targets for targets in edges.values()):
        raise ValueError("external game is not total")

    controller_labels: List[str] = []
    environment_labels: List[str] = []
    commands: List[str] = []
    edge_index = 0
    for source in sorted(edges):
        owner = owners[source]
        for target in edges[source]:
            action = ("c" if owner == "controller" else "e") + str(edge_index)
            edge_index += 1
            if owner == "controller":
                controller_labels.append("[" + action + "]")
            else:
                environment_labels.append("[" + action + "]")
            commands.append(
                "  [%s] s=%d -> (s'=%d);" % (action, source, target)
            )

    lines = [
        "// Generated from the independent raw-LTS front-end.",
        "// All transitions are deterministic choices; probabilities are absent.",
        "smg",
        "",
        "player controller",
        "  " + ", ".join(controller_labels),
        "endplayer",
        "",
        "player environment",
        "  " + ", ".join(environment_labels),
        "endplayer",
        "",
        "module fg_ducs_strong_game",
        "  s : [0..%d] init 0;" % (next_node - 1),
    ]
    lines.extend(commands)
    lines.extend(["endmodule", ""])
    goal_nodes = sorted(state_node[state] for state in game.goals)
    goal_expression = (
        " | ".join("s=%d" % node for node in goal_nodes)
        if goal_nodes
        else "false"
    )
    lines.append('label "goal" = %s;' % goal_expression)
    lines.append("")
    for node in sorted(labels):
        lines.append("// node %d: %s" % (node, labels[node]))
    lines.append("")
    return PrismEncoding(
        source="\n".join(lines),
        node_count=next_node,
        edge_count=edge_index,
        controller_nodes=sum(1 for owner in owners.values() if owner == "controller"),
        environment_nodes=sum(1 for owner in owners.values() if owner == "environment"),
        action_nodes=action_nodes,
    )


def java_decisions(path: Path) -> Mapping[str, Mapping[str, str]]:
    observed: Dict[str, Dict[str, str]] = {}
    with path.open("r", encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            if row.get("model_family") != "rq1_semantic_boundary_v2":
                continue
            model_id = str(row.get("model_id", "")).removeprefix("semantic_")
            method = str(row.get("method_id", ""))
            decision = str(row.get("revised_decision", ""))
            if not model_id or not method or decision not in {
                "realizable",
                "unrealizable",
            }:
                raise ValueError("invalid frozen Java decision row")
            methods = observed.setdefault(model_id, {})
            if method in methods:
                raise ValueError("duplicate frozen Java decision")
            methods[method] = decision
    return observed


def checksum_lines(paths: Iterable[Path], base: Path) -> bytes:
    rows = []
    for path in sorted(paths, key=lambda item: item.relative_to(base).as_posix()):
        rows.append("%s  %s" % (digest(path), path.relative_to(base).as_posix()))
    return ("\n".join(rows) + "\n").encode("utf-8")


def main() -> int:
    args = arguments()
    root = repository_root()
    protocol_path = args.protocol.resolve()
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    if protocol.get("schema_version") != "fse2027-m6-validation-protocol-v1":
        raise ValueError("unsupported M6 protocol")
    external = protocol["external_solver"]

    prism_bin = args.prism_bin.resolve()
    prism_archive = args.prism_archive.resolve()
    if not prism_bin.is_file() or not os.access(prism_bin, os.X_OK):
        raise ValueError("PRISM executable is missing")
    require_hash(prism_archive, external["archive_sha256"], "PRISM archive")
    version = subprocess.run(
        [str(prism_bin), "-version"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=30,
    ).stdout.strip()
    if version != "PRISM-games version " + external["version"]:
        raise ValueError("unexpected PRISM-games version: " + version)

    semantic_manifest_path = (
        args.semantic_manifest
        if args.semantic_manifest.is_absolute()
        else root / args.semantic_manifest
    ).resolve()
    java_runs_path = (
        args.java_runs if args.java_runs.is_absolute() else root / args.java_runs
    ).resolve()
    semantic_manifest_path.relative_to(root)
    java_runs_path.relative_to(root)
    if not semantic_manifest_path.is_file() or semantic_manifest_path.is_symlink():
        raise ValueError("public semantic manifest is missing")
    if not java_runs_path.is_file() or java_runs_path.is_symlink():
        raise ValueError("public Java result table is missing")
    require_hash(
        semantic_manifest_path,
        external["semantic_manifest_sha256"],
        "semantic manifest",
    )
    # The protocol's public projection binds the tokenized CSV.  The private
    # pre-sanitization hash is deliberately omitted because it would create a
    # path-prefix crosswalk during double-anonymous review.
    manifest = json.loads(semantic_manifest_path.read_text(encoding="utf-8"))
    records = manifest.get("models")
    if not isinstance(records, list) or len(records) != external["expected_models"]:
        raise ValueError("semantic population differs from registration")
    frozen_java = java_decisions(java_runs_path)
    if sum(len(values) for values in frozen_java.values()) != external[
        "expected_java_decisions"
    ]:
        raise ValueError("Java decision coverage differs from registration")

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    games_dir = output / "games"
    logs_dir = output / "logs"
    games_dir.mkdir()
    logs_dir.mkdir()
    results: List[Dict[str, Any]] = []
    property_text = external["property"]
    failures = 0

    for record in records:
        model_id = str(record.get("id", ""))
        relative = Path(str(record.get("path", "")))
        if not model_id or relative.is_absolute() or ".." in relative.parts:
            raise ValueError("unsafe semantic model registration")
        model_path = (semantic_manifest_path.parent / relative).resolve()
        model_path.relative_to(semantic_manifest_path.parent.resolve())
        require_hash(model_path, str(record.get("sha256", "")), model_id)
        expected = str(record.get("expected_decision", ""))
        started = time.monotonic_ns()
        game = build_explicit_game(model_path)
        encoding = encode_prism_game(game)
        translation_ns = time.monotonic_ns() - started
        model_output = games_dir / (model_id + ".prism")
        write_new(model_output, encoding.source.encode("utf-8"))

        command = [
            str(prism_bin),
            str(model_output),
            "-pf",
            property_text,
            "-explicit",
            "-javamaxmem",
            "2g",
        ]
        solver_started = time.monotonic_ns()
        status = "PASS"
        error = ""
        value: float | None = None
        try:
            completed = subprocess.run(
                command,
                cwd=str(output),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=float(external["timeout_seconds_per_model"]),
                check=False,
            )
            stdout = completed.stdout
            stderr = completed.stderr
            if completed.returncode != 0:
                status = "SOLVER_ERROR"
                error = "exit code %d" % completed.returncode
            else:
                matches = RESULT_PATTERN.findall(stdout)
                if len(matches) != 1:
                    status = "UNPARSEABLE_RESULT"
                    error = "expected one numeric Result line"
                else:
                    value = float(matches[0])
        except subprocess.TimeoutExpired as timeout:
            stdout = timeout.stdout or ""
            stderr = timeout.stderr or ""
            if isinstance(stdout, bytes):
                stdout = stdout.decode("utf-8", errors="replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", errors="replace")
            status = "TIMEOUT"
            error = "external solver timeout"
        solver_ns = time.monotonic_ns() - solver_started
        write_new((logs_dir / (model_id + ".stdout.txt")), stdout.encode("utf-8"))
        write_new((logs_dir / (model_id + ".stderr.txt")), stderr.encode("utf-8"))

        external_decision = ""
        if status == "PASS":
            if value == 1.0:
                external_decision = "realizable"
            elif value == 0.0:
                external_decision = "unrealizable"
            else:
                status = "NON_BINARY_VALUE"
                error = "PRISM result is neither 0 nor 1"
        methods = frozen_java.get(model_id, {})
        if status == "PASS" and set(methods) != {"direct_full", "fg_ducs_otf"}:
            status = "JAVA_COVERAGE_MISMATCH"
            error = "frozen Java methods differ"
        if status == "PASS" and (
            external_decision != expected
            or set(methods.values()) != {expected}
        ):
            status = "DECISION_MISMATCH"
            error = "external, manifest, and Java decisions differ"
        if status != "PASS":
            failures += 1

        results.append(
            {
                "model_id": model_id,
                "model_sha256": digest(model_path),
                "expected_decision": expected,
                "java_decisions": dict(sorted(methods.items())),
                "prism_value": value,
                "external_decision": external_decision,
                "status": status,
                "error": error,
                "raw_game_states": len(game.states),
                "q0_states": len(game.initial_states),
                "goal_states": len(game.goals),
                "prism_nodes": encoding.node_count,
                "prism_edges": encoding.edge_count,
                "prism_controller_nodes": encoding.controller_nodes,
                "prism_environment_nodes": encoding.environment_nodes,
                "prism_action_nodes": encoding.action_nodes,
                "translation_wall_ms": translation_ns / 1_000_000.0,
                "solver_wall_ms": solver_ns / 1_000_000.0,
                "game_file": model_output.relative_to(output).as_posix(),
                "game_sha256": digest(model_output),
                "stdout_file": (logs_dir / (model_id + ".stdout.txt")).relative_to(output).as_posix(),
                "stderr_file": (logs_dir / (model_id + ".stderr.txt")).relative_to(output).as_posix(),
            }
        )

    summary = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if failures == 0 else "FAIL",
        "registered_models": len(records),
        "passed_models": len(records) - failures,
        "failed_models": failures,
        "realizable_models": sum(
            result["expected_decision"] == "realizable" for result in results
        ),
        "unrealizable_models": sum(
            result["expected_decision"] == "unrealizable" for result in results
        ),
        "external_solver": version,
        "property": property_text,
        "prism_archive_sha256": digest(prism_archive),
        "prism_jar_sha256": digest(prism_bin.parent.parent / "lib" / "prism.jar"),
        "protocol_sha256": digest(protocol_path),
        "semantic_manifest_sha256": digest(semantic_manifest_path),
        "java_runs_sha256": digest(java_runs_path),
        "runner_sha256": digest(Path(__file__).resolve()),
        "raw_oracle_sha256": digest(Path(__file__).resolve().with_name("independent_raw_oracle.py")),
        "host": {
            "platform": platform.platform(),
            "python": sys.version,
        },
        "claim_scope": (
            "external decision agreement over the registered independent-raw-"
            "front-end boundary suite; not a performance comparison or held-out "
            "application sample"
        ),
        "models": results,
    }
    summary_path = output / "summary.json"
    write_new(summary_path, canonical_json_bytes(summary))
    files = [path for path in output.rglob("*") if path.is_file()]
    write_new(output / "SHA256SUMS", checksum_lines(files, output))
    print(json.dumps({"status": summary["status"], "output": str(output)}))
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
