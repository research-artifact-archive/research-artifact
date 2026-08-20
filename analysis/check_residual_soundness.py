#!/usr/bin/env python3
"""Check FG-DUCS residual soundness on finite full-alphabet products.

The checker implements Proposition RS from the paper for a supplied finite
activation-prefix graph, deterministic observation transducer, and requirement
monitor.  It types ordinary/update alphabets, forces observer and monitor
totality on their exact union, and permits epsilon only at the hot-swap
boundary.  The graph's exactness with respect to all old-endpoint and update
prefixes remains an external obligation.  For every reached activation
configuration the checker tests language inclusion from the declared
initialization into each history residual and returns an activation prefix
plus continuation word when inclusion fails.  Exactness means both no missing
and no spurious concrete activation prefixes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict, deque
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]


class ResidualCheckError(RuntimeError):
    """The input is malformed or contradicts its registered expectation."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ResidualCheckError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ResidualCheckError(f"invalid JSON: {path}") from error
    require(isinstance(value, dict), f"JSON root must be an object: {path}")
    return value


def string_set(value: Any, label: str, *, nonempty: bool = True) -> set[str]:
    require(isinstance(value, list), f"{label} must be a list")
    require(all(isinstance(item, str) and item for item in value), f"{label} has a non-string item")
    require(len(value) == len(set(value)), f"{label} has duplicates")
    require(not nonempty or bool(value), f"{label} must be nonempty")
    return set(value)


def transition_table(
    records: Any,
    states: set[str],
    alphabet: Sequence[str],
    label: str,
) -> dict[tuple[str, str], str]:
    require(isinstance(records, list), f"{label}.transitions must be a list")
    table: dict[tuple[str, str], str] = {}
    for index, record in enumerate(records):
        require(isinstance(record, dict), f"{label}.transitions[{index}] must be an object")
        source, symbol, target = record.get("source"), record.get("symbol"), record.get("target")
        require(source in states and target in states, f"{label} transition has an unknown state")
        require(symbol in alphabet, f"{label} transition has an unknown symbol")
        key = (source, symbol)
        require(key not in table, f"{label} is nondeterministic at {key}")
        table[key] = target
    expected = {(state, symbol) for state in states for symbol in alphabet}
    require(set(table) == expected, f"{label} transition table is not total")
    return table


def reconstruct_activation(
    node: tuple[str, str, str],
    parent: Mapping[
        tuple[str, str, str],
        tuple[tuple[str, str, str], str | None, tuple[str, ...]] | None,
    ],
) -> tuple[list[str], list[str]]:
    event_chunks: list[str] = []
    output_chunks: list[tuple[str, ...]] = []
    cursor = node
    while parent[cursor] is not None:
        previous, event, output = parent[cursor]  # type: ignore[misc]
        if event is not None:
            event_chunks.append(event)
        output_chunks.append(output)
        cursor = previous
    events = list(reversed(event_chunks))
    outputs: list[str] = []
    for chunk in reversed(output_chunks):
        outputs.extend(chunk)
    return events, outputs


def inclusion_counterexample(
    left: str,
    right: str,
    alphabet: Sequence[str],
    monitor: Mapping[tuple[str, str], str],
    errors: set[str],
) -> list[str] | None:
    start = (left, right)
    queue = deque([start])
    parent: dict[tuple[str, str], tuple[tuple[str, str], str] | None] = {start: None}
    losing: tuple[str, str] | None = start if left not in errors and right in errors else None
    while queue and losing is None:
        current = queue.popleft()
        for symbol in alphabet:
            successor = (monitor[(current[0], symbol)], monitor[(current[1], symbol)])
            if successor in parent:
                continue
            parent[successor] = (current, symbol)
            if successor[0] not in errors and successor[1] in errors:
                losing = successor
                break
            queue.append(successor)
    if losing is None:
        return None
    word: list[str] = []
    cursor = losing
    while parent[cursor] is not None:
        previous, symbol = parent[cursor]  # type: ignore[misc]
        word.append(symbol)
        cursor = previous
    return list(reversed(word))


def check_fixture(raw: Mapping[str, Any]) -> dict[str, Any]:
    require(raw.get("schema_version") == "fg-ducs-rs-fixture-v3", "unknown fixture schema")
    sigma_n_list = raw.get("sigma_n")
    sigma_u_list = raw.get("sigma_u")
    sigma_n = string_set(sigma_n_list, "sigma_n", nonempty=False)
    sigma_u = string_set(sigma_u_list, "sigma_u", nonempty=False)
    require(sigma_n.isdisjoint(sigma_u), "ordinary and update alphabets overlap")
    assert isinstance(sigma_n_list, list) and isinstance(sigma_u_list, list)
    sigma_list = [*sigma_n_list, *sigma_u_list]
    sigma = sigma_n | sigma_u

    activation = raw.get("activation")
    require(isinstance(activation, dict), "activation must be an object")
    require(
        activation.get("graph_relation") == "exact",
        "activation graph must carry an externally justified exactness assertion",
    )
    a_states = string_set(activation.get("states"), "activation.states")
    a_initial = string_set(activation.get("initial_states"), "activation.initial_states")
    old_states = string_set(activation.get("old_endpoint_states"), "activation.old_endpoint_states")
    post_states = string_set(activation.get("update_phase_states"), "activation.update_phase_states")
    require(old_states.isdisjoint(post_states) and old_states | post_states == a_states,
            "activation phase partition differs from its state set")
    require(a_initial <= old_states, "activation initial state is not an old-endpoint state")
    accepting_raw = activation.get("accepting")
    require(isinstance(accepting_raw, list) and accepting_raw, "activation.accepting must be nonempty")
    accepting: dict[str, str] = {}
    for record in accepting_raw:
        require(isinstance(record, dict), "activation accepting record must be an object")
        state, xi = record.get("state"), record.get("xi")
        require(state in post_states and isinstance(xi, str) and xi, "invalid activation accepting record")
        require(state not in accepting, "activation state has two accepting types")
        accepting[state] = xi
    requirement_kind = activation.get("requirement_kind")
    activation_event = activation.get("activation_event")
    require(requirement_kind in {"new", "update"}, "unknown activation requirement kind")
    if requirement_kind == "new":
        require(activation_event in sigma_u, "new-requirement activation event is not an update event")
    else:
        require(activation_event is None, "update requirement activates only at hotSwapIn")
    a_outgoing: dict[str, list[tuple[str | None, str]]] = defaultdict(list)
    transitions = activation.get("transitions")
    require(isinstance(transitions, list), "activation.transitions must be a list")
    seen_activation_edges: set[tuple[str, str | None, str]] = set()
    hot_swap_sources: set[str] = set()
    for record in transitions:
        require(isinstance(record, dict), "activation transition must be an object")
        source, event, target = record.get("source"), record.get("event"), record.get("target")
        boundary = record.get("boundary")
        require(source in a_states and target in a_states, "activation transition has an unknown state")
        require(event is None or event in sigma, "activation transition omits a full-sigma event")
        if event is None:
            require(boundary == "hotSwapIn", "epsilon activation edge is not the hot-swap boundary")
            require(source in old_states and target in post_states,
                    "hot-swap boundary does not cross from old endpoint to update phase")
            require(source not in hot_swap_sources, "old-endpoint state has two hot-swap boundaries")
            hot_swap_sources.add(source)
        else:
            require(boundary is None, "ordinary/update edge has a boundary annotation")
            if source in old_states:
                require(event in sigma_n and target in old_states,
                        "old-endpoint edge is not an ordinary in-phase event")
            else:
                require(source in post_states and target in post_states,
                        "update-phase event crosses an activation phase boundary")
        edge = (source, event, target)
        require(edge not in seen_activation_edges, "duplicate activation transition")
        seen_activation_edges.add(edge)
        a_outgoing[source].append((event, target))
    require(hot_swap_sources == old_states,
            "each reachable old-endpoint state needs exactly one hotSwapIn edge")
    require(not any(a_outgoing[state] for state in accepting), "accepting activation states must be terminal")
    incoming_accepting = [
        (source, event, target)
        for source, outgoing in a_outgoing.items()
        for event, target in outgoing
        if target in accepting
    ]
    require(incoming_accepting, "accepting activation states have no incoming edges")
    if requirement_kind == "new":
        require(
            all(target not in accepting for source in old_states for _, target in a_outgoing[source]),
            "new requirement activates at hotSwapIn instead of its start event",
        )
        require(
            all(event == activation_event for _, event, _ in incoming_accepting),
            "new-requirement acceptance is not entered by its start event",
        )
        require(
            all(
                target in accepting
                for source, outgoing in a_outgoing.items()
                for event, target in outgoing
                if event == activation_event
            ),
            "activation event occurs before the first activation point",
        )
    else:
        require(
            all(source in old_states and event is None for source, event, _ in incoming_accepting),
            "update requirement must activate immediately after hotSwapIn",
        )
        require(
            all(
                target in accepting
                for source in old_states
                for event, target in a_outgoing[source]
                if event is None
            ),
            "every old-endpoint state must activate the update requirement at hotSwapIn",
        )

    graph_reachable = set(a_initial)
    graph_queue = deque(sorted(a_initial))
    while graph_queue:
        source = graph_queue.popleft()
        for _, target in a_outgoing[source]:
            if target not in graph_reachable:
                graph_reachable.add(target)
                graph_queue.append(target)
    require(graph_reachable == a_states, "activation graph contains an unreachable state")

    observer = raw.get("observer")
    require(isinstance(observer, dict), "observer must be an object")
    o_states = string_set(observer.get("states"), "observer.states")
    o_initial = observer.get("initial_state")
    require(o_initial in o_states, "observer initial state is unknown")

    monitor_raw = raw.get("monitor")
    require(isinstance(monitor_raw, dict), "monitor must be an object")
    m_states = string_set(monitor_raw.get("states"), "monitor.states")
    m_initial = monitor_raw.get("initial_state")
    require(m_initial in m_states, "monitor initial state is unknown")
    m_alphabet_list = monitor_raw.get("alphabet")
    m_alphabet = string_set(m_alphabet_list, "monitor.alphabet", nonempty=False)
    assert isinstance(m_alphabet_list, list)
    require(m_alphabet == sigma, "monitor alphabet must equal full sigma")
    errors = string_set(monitor_raw.get("error_states"), "monitor.error_states", nonempty=False)
    require(errors <= m_states, "monitor error state is unknown")
    require(m_initial not in errors, "monitor initial state must be non-error")
    monitor = transition_table(
        monitor_raw.get("transitions"), m_states, m_alphabet_list, "monitor"
    )
    require(
        all(monitor[(state, symbol)] in errors for state in errors for symbol in m_alphabet_list),
        "monitor error states must be absorbing",
    )

    observer_records = observer.get("transitions")
    require(isinstance(observer_records, list), "observer.transitions must be a list")
    observer_table: dict[tuple[str, str], tuple[str, tuple[str, ...]]] = {}
    for record in observer_records:
        require(isinstance(record, dict), "observer transition must be an object")
        source, event, target = record.get("source"), record.get("event"), record.get("target")
        output = record.get("output")
        require(source in o_states and target in o_states, "observer transition has an unknown state")
        require(event in sigma, "observer transition has an unknown full-sigma event")
        require(isinstance(output, list) and all(symbol in m_alphabet for symbol in output), "invalid observer output")
        key = (source, event)
        require(key not in observer_table, f"observer is nondeterministic at {key}")
        observer_table[key] = (target, tuple(output))
    require(
        set(observer_table) == {(state, event) for state in o_states for event in sigma_list},
        "observer transition table is not total on sigma",
    )
    if requirement_kind == "new":
        require(
            all(
                observer_table[(state, str(activation_event))][1] == (activation_event,)
                for state in o_states
            ),
            "observer must retain the new-requirement activation event",
        )

    iota = raw.get("iota")
    require(isinstance(iota, dict), "iota must be an object")
    accepted_xi = set(accepting.values())
    require(set(iota) == accepted_xi, "iota domain differs from accepting activation types")
    require(all(state in m_states - errors for state in iota.values()), "iota must select non-error states")

    start_nodes = [(state, o_initial, m_initial) for state in sorted(a_initial)]
    queue = deque(start_nodes)
    parent: dict[
        tuple[str, str, str],
        tuple[tuple[str, str, str], str | None, tuple[str, ...]] | None,
    ] = {node: None for node in start_nodes}
    residual_paths: dict[tuple[str, str], tuple[list[str], list[str]]] = {}
    reached_accepting_states: set[str] = set()
    reached_accepting_product_nodes: set[tuple[str, str, str]] = set()
    while queue:
        node = queue.popleft()
        a_state, o_state, m_state = node
        if a_state in accepting:
            reached_accepting_states.add(a_state)
            reached_accepting_product_nodes.add(node)
            residual_paths.setdefault(
                (accepting[a_state], m_state), reconstruct_activation(node, parent)
            )
            continue
        for event, a_target in a_outgoing[a_state]:
            if event is None:
                o_target, output, m_target = o_state, (), m_state
            else:
                o_target, output = observer_table[(o_state, event)]
                m_target = m_state
                for symbol in output:
                    m_target = monitor[(m_target, symbol)]
            successor = (a_target, o_target, m_target)
            if successor not in parent:
                parent[successor] = (node, event, output)
                queue.append(successor)
    require(reached_accepting_states == set(accepting), "an accepting activation state is unreachable")

    counterexample: dict[str, Any] | None = None
    inclusions = 0
    residuals_by_xi: dict[str, list[str]] = defaultdict(list)
    for (xi, residual), (events, observed) in sorted(residual_paths.items()):
        inclusions += 1
        residuals_by_xi[xi].append(residual)
        continuation = inclusion_counterexample(str(iota[xi]), residual, sigma_list, monitor, errors)
        if continuation is not None and counterexample is None:
            counterexample = {
                "xi": xi,
                "declared_initialization": iota[xi],
                "history_residual": residual,
                "activation_prefix": events,
                "observed_prefix": observed,
                "continuation": continuation,
            }
    return {
        "decision": "SOUND" if counterexample is None else "UNSOUND",
        "activation_product_states": len(parent),
        "accepting_generator_states": len(reached_accepting_states),
        "accepting_product_states": len(reached_accepting_product_nodes),
        "distinct_history_residuals": len(residual_paths),
        "inclusions_checked": inclusions,
        "residuals_by_xi": dict(sorted((key, sorted(value)) for key, value in residuals_by_xi.items())),
        "counterexample": counterexample,
    }


def check_manifest(manifest_path: Path) -> dict[str, Any]:
    manifest = load_object(manifest_path)
    require(manifest.get("schema_version") == "fg-ducs-rs-manifest-v3", "unknown manifest schema")
    cases = manifest.get("cases")
    require(isinstance(cases, list) and cases, "manifest cases must be nonempty")
    identifiers: set[str] = set()
    results: list[dict[str, Any]] = []
    for record in cases:
        require(isinstance(record, dict), "manifest case must be an object")
        identifier, relative_text = record.get("id"), record.get("path")
        require(isinstance(identifier, str) and identifier and identifier not in identifiers, "invalid case id")
        identifiers.add(identifier)
        require(isinstance(relative_text, str), f"invalid path for {identifier}")
        relative = PurePosixPath(relative_text)
        require(not relative.is_absolute() and ".." not in relative.parts, f"unsafe path for {identifier}")
        path = ROOT / relative
        require(path.is_file() and not path.is_symlink(), f"missing fixture for {identifier}")
        require(path.stat().st_size == record.get("bytes"), f"byte count differs for {identifier}")
        require(sha256_file(path) == record.get("sha256"), f"hash differs for {identifier}")
        result = check_fixture(load_object(path))
        require(result["decision"] == record.get("expected_decision"), f"decision differs for {identifier}")
        expected_counterexample = record.get("expected_counterexample")
        if expected_counterexample is not None:
            require(result["counterexample"] is not None, f"counterexample missing for {identifier}")
            for field in ("activation_prefix", "observed_prefix", "continuation"):
                require(
                    result["counterexample"].get(field) == expected_counterexample.get(field),
                    f"counterexample {field} differs for {identifier}",
                )
        elif result["counterexample"] is not None:
            raise ResidualCheckError(f"unexpected counterexample for {identifier}")
        results.append({"id": identifier, **result})
    counts = {decision: sum(item["decision"] == decision for item in results) for decision in ("SOUND", "UNSOUND")}
    return {
        "schema_version": "fg-ducs-rs-audit-v3",
        "status": "PASS",
        "alphabet_partition_checked": True,
        "full_sigma_observer_monitor_total": True,
        "activation_graph_exactness": "external_asserted_not_verified",
        "case_count": len(results),
        "decision_counts": counts,
        "cases": results,
    }


def parse_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, help="write JSON here; default is stdout; use '-' for stdout")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    arguments = parse_arguments(argv)
    try:
        report = check_manifest(arguments.manifest.resolve())
        payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        if arguments.output is None or str(arguments.output) == "-":
            print(payload, end="")
        else:
            arguments.output.write_text(payload, encoding="utf-8")
        return 0
    except (ResidualCheckError, OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
