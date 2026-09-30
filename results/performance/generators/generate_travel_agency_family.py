#!/usr/bin/env python3
"""Generate provenance-bound Travel Agency FG-DUCS benchmark instances.

The canonical input is MTSA's checked-in Travel Agency OTF-DCS benchmark.
This generator does *not* claim that its outputs are the original benchmark or
are trace equivalent, bisimilar, or semantically equivalent to it.  It makes a
documented FG-DUCS adaptation of selected structural features.  In particular,
the source's unreserved and reserved service branches become the old and new
endpoints, respectively; ``agency.request`` and ``query[i]`` change from
uncontrollable source events to controllable admissions; the source monitor
processes are omitted; and component transfer is allowed only at idle
(quiescent) states.  Canonical-source hashing binds provenance, not equivalence.

Generation is byte deterministic.  It verifies the reviewed canonical-source
digest and refuses to overwrite either a different generated file or an
unregistered ``.lts`` file in the destination model directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple


SCHEMA_VERSION = "fse2027-travel-agency-fg-ducs-family-v1"
GENERATOR_ID = "travel-agency-derived-fg-ducs-v1"
TARGET = "UPDATE_CONTROLLER_OTF_FG"
AUTOMATICA_DOI = "10.1016/j.automatica.2022.110731"
CANONICAL_SOURCE_PATH = (
    "Implementation/Source Code/maven-root/mtsa/src/main/resources/examples/"
    "ControllerSynthesis/OnTheFly/DirectorForNonBlocking/TravelAgency.lts"
)
CANONICAL_SOURCE_SHA256 = (
    "774b2a31d1dce865b5405ea4babe1dbdf3f6dca0857b9bd887f519c1aab86d77"
)
CANONICAL_SOURCE_BYTES = 4218
DEFAULT_INSTANCES: Tuple[Tuple[int, int], ...] = (
    (1, 1),
    (2, 2),
    (3, 4),
    (4, 6),
)
MAX_AMENITIES = 12
MAX_PROTOCOL_STEP_CHOICES = 20


def repository_root() -> Path:
    return Path(__file__).resolve().parents[4]


def inside(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def validate_factors(amenities: int, protocol_steps: int) -> None:
    if amenities < 1 or amenities > MAX_AMENITIES:
        raise ValueError(
            "amenities N must be between 1 and %d" % MAX_AMENITIES
        )
    if protocol_steps < 1 or protocol_steps > MAX_PROTOCOL_STEP_CHOICES:
        raise ValueError(
            "protocol steps K must be between 1 and %d"
            % MAX_PROTOCOL_STEP_CHOICES
        )


def parse_instances(value: str) -> List[Tuple[int, int]]:
    """Parse a strictly sorted ``N:K,N:K`` instance list."""
    parsed: List[Tuple[int, int]] = []
    try:
        for token in value.split(","):
            parts = token.strip().split(":")
            if len(parts) != 2:
                raise ValueError
            instance = (int(parts[0]), int(parts[1]))
            validate_factors(*instance)
            parsed.append(instance)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "instances must be comma-separated N:K pairs within the supported "
            "ranges"
        ) from error
    if not parsed or parsed != sorted(set(parsed)):
        raise argparse.ArgumentTypeError(
            "instances must be nonempty, unique, and lexicographically increasing"
        )
    return parsed


def comma_join(items: Iterable[str]) -> str:
    return ", ".join(items)


def choice_lines(transitions: Sequence[str], indent: str = "    ") -> List[str]:
    if not transitions:
        raise ValueError("an FSP choice must contain at least one transition")
    lines = []
    for index, transition in enumerate(transitions):
        suffix = " |" if index + 1 < len(transitions) else ""
        lines.append(indent + transition + suffix)
    return lines


def action(scalar: str, amenity: int) -> str:
    return "%s[%d]" % (scalar, amenity)


def step_action(amenity: int, step: int) -> str:
    return "steps[%d][%d]" % (amenity, step)


def service_name(version: str, amenity: int) -> str:
    return "%s_SERVICE_%02d" % (version, amenity)


def render_agency(version: str, amenities: int) -> List[str]:
    root = "%s_AGENCY" % version
    processing = root + "_PROCESSING"
    transitions = [
        "agency.succ -> %s" % root,
        "agency.fail -> %s" % root,
    ]
    transitions.extend(
        "%s -> %s" % (action("query", amenity), processing)
        for amenity in range(amenities)
    )
    lines = [
        "%s = (agency.request -> %s)," % (root, processing),
        "%s = (" % processing,
    ]
    lines.extend(choice_lines(transitions))
    lines.append(").")
    return lines


def render_selection_states(
    version: str,
    amenity: int,
    protocol_steps: int,
    booking: str,
) -> List[str]:
    """Render the source model's ``steps`` choice and repeated ``select``."""
    prefix = "%s_SERVICE_%02d_SELECT" % (version, amenity)
    lines: List[str] = []
    for remaining in range(1, protocol_steps):
        destination = booking if remaining == 1 else "%s_%02d" % (
            prefix,
            remaining - 1,
        )
        lines.append(
            "%s_%02d = (%s -> %s),"
            % (
                prefix,
                remaining,
                action("select", amenity),
                destination,
            )
        )
    return lines


def render_service(
    version: str,
    amenity: int,
    amenities: int,
    protocol_steps: int,
) -> List[str]:
    root = service_name(version, amenity)
    query_state = root + "_QUERY"
    booking = root + "_BOOKING"
    chain = root + "_CHAIN"
    terminal = root + ("_DIRECT" if version == "OLD" else "_RESERVE")
    steps = []
    for count in range(protocol_steps):
        destination = (
            booking
            if count == 0
            else "%s_SELECT_%02d" % (root, count)
        )
        steps.append(
            "%s -> %s" % (step_action(amenity, count), destination)
        )

    lines = [
        "%s = (" % root,
    ]
    lines.extend(
        choice_lines(
            [
                "agency.succ -> %s" % root,
                "agency.fail -> %s" % root,
                "%s -> %s" % (action("query", amenity), query_state),
            ]
        )
    )
    lines.extend(
        [
            "),",
            "%s = (" % query_state,
            "    %s -> %s -> %s |"
            % (
                action("unavailable", amenity),
                action("query.fail", amenity),
                root,
            ),
            "    %s -> (" % action("available", amenity),
        ]
    )
    lines.extend(choice_lines(steps, indent="        "))
    lines.extend(["    )", "),"])
    lines.extend(
        render_selection_states(
            version,
            amenity,
            protocol_steps,
            booking,
        )
    )

    branch_action = action(
        "uncommitted" if version == "OLD" else "committed",
        amenity,
    )
    branch_destination = terminal if amenity + 1 == amenities else chain
    lines.append(
        "%s = (%s -> %s)," % (booking, branch_action, branch_destination)
    )
    if amenity + 1 < amenities:
        lines.append(
            "%s = (%s -> %s),"
            % (chain, action("query", amenity + 1), terminal)
        )

    terminal_transitions = [
        "agency.succ -> %s" % root,
        "agency.fail -> %s" % root,
        "%s -> %s" % (action("cancel", amenity), root),
    ]
    if version == "OLD":
        terminal_transitions.append(
            "%s -> ("
            "%s -> %s | "
            "%s -> %s)"
            % (
                action("purchase", amenity),
                action("purchase.succ", amenity),
                root,
                action("purchase.fail", amenity),
                root,
            )
        )
    else:
        terminal_transitions.append(
            "%s -> %s -> %s"
            % (
                action("purchase", amenity),
                action("purchase.succ", amenity),
                root,
            )
        )
    lines.append("%s = (" % terminal)
    lines.extend(choice_lines(terminal_transitions))
    lines.append(").")
    return lines


def controllable_actions(amenities: int) -> List[str]:
    actions = ["agency.request", "agency.succ", "agency.fail"]
    for amenity in range(amenities):
        actions.extend(
            action(name, amenity)
            for name in ("query", "cancel", "purchase")
        )
    return actions


def uncontrollable_completion_actions(
    amenities: int,
    protocol_steps: int,
) -> List[str]:
    actions: List[str] = []
    for amenity in range(amenities):
        actions.extend(
            action(name, amenity)
            for name in (
                "unavailable",
                "query.fail",
                "available",
                "select",
                "uncommitted",
                "committed",
                "purchase.succ",
                "purchase.fail",
            )
        )
        actions.extend(
            step_action(amenity, count)
            for count in range(protocol_steps)
        )
    return actions


def verify_uncontrollable_drain_acyclic(protocol_steps: int) -> Dict[str, Any]:
    """Prove the generated Service's uncontrollable-only subgraph is a DAG.

    Nodes abstract the control locations emitted by ``render_service``;
    edges retain only actions outside ``ControllableActions``.  In a parallel
    product, every such transition strictly decreases the sum of these local
    longest-path ranks, so synchronization cannot introduce an
    uncontrollable cycle.
    """

    validate_factors(1, protocol_steps)
    graph: Dict[str, List[str]] = {
        "root": [],
        "query": ["unavailable_followup", "available_choice"],
        "unavailable_followup": ["root"],
        "available_choice": ["booking"]
        + ["select_%02d" % count for count in range(1, protocol_steps)],
        "booking": ["terminal_or_chain"],
        "terminal_or_chain": [],
    }
    for count in range(1, protocol_steps):
        graph["select_%02d" % count] = [
            "booking" if count == 1 else "select_%02d" % (count - 1)
        ]

    visiting = set()
    ranks: Dict[str, int] = {}

    def rank(node: str) -> int:
        if node in visiting:
            raise ValueError(
                "generated Travel Agency has an uncontrollable cycle"
            )
        if node in ranks:
            return ranks[node]
        visiting.add(node)
        successors = graph[node]
        value = 0 if not successors else 1 + max(rank(item) for item in successors)
        visiting.remove(node)
        ranks[node] = value
        return value

    for node in graph:
        rank(node)
    expected_bound = protocol_steps + 2
    if ranks["query"] != expected_bound:
        raise ValueError("unexpected uncontrollable drain-rank construction")
    return {
        "result": "acyclic",
        "proof": "strict_decrease_of_sum_of_local_longest_path_ranks",
        "maximum_uncontrollable_burst": expected_bound,
        "abstract_nodes": len(graph),
        "abstract_edges": sum(len(values) for values in graph.values()),
    }


def render_model(amenities: int, protocol_steps: int) -> str:
    """Render one concrete N-by-K FG-DUCS instance."""
    validate_factors(amenities, protocol_steps)
    old_components = ["OLD_AGENCY"] + [
        service_name("OLD", amenity) for amenity in range(amenities)
    ]
    new_components = ["NEW_AGENCY"] + [
        service_name("NEW", amenity) for amenity in range(amenities)
    ]
    relations = ["R_AGENCY_FG"] + [
        "R_SERVICE_%02d_FG" % amenity for amenity in range(amenities)
    ]

    lines = [
        "/*****************************************************************************",
        " * Generated by %s; do not edit." % GENERATOR_ID,
        " *",
        " * DERIVED ADAPTATION, NOT THE ORIGINAL TRAVEL AGENCY BENCHMARK.",
        " * Canonical source: %s" % CANONICAL_SOURCE_PATH,
        " * Canonical SHA-256: %s" % CANONICAL_SOURCE_SHA256,
        " * OTF-DCS publication DOI: %s" % AUTOMATICA_DOI,
        " *",
        " * Preserved: Agency/Service orchestration, N amenities, the K-way",
        " * steps choice followed by repeated select actions, reservation/direct",
        " * purchase branches, nonblocking endpoint synthesis, and uncontrollable",
        " * service completions.",
        " * Adapted: the direct branch is the old endpoint; the reservation branch",
        " * is the new endpoint; agency.request and query[i] are controllable",
        " * admission actions so an update can stop new work; every component can",
        " * transfer only from its idle state.  The source monitors are not reused.",
        " * Consequently, the source controllability partition is NOT preserved.",
        " * The source hash binds provenance only; no trace, bisimulation, or other",
        " * semantic equivalence to the original benchmark is claimed.",
        " *****************************************************************************/",
        "",
        "const Amenities = %d" % amenities,
        "const Steps = %d" % protocol_steps,
        "",
        "set ControllableActions = {%s}"
        % comma_join(controllable_actions(amenities)),
        "set UncontrollableCompletions = {%s}"
        % comma_join(
            uncontrollable_completion_actions(amenities, protocol_steps)
        ),
        "",
        "// Old endpoint: direct purchase without reservation.",
    ]
    lines.extend(render_agency("OLD", amenities))
    lines.append("")
    for amenity in range(amenities):
        lines.extend(
            render_service("OLD", amenity, amenities, protocol_steps)
        )
        lines.append("")
    lines.append("||OldEnvironment = (%s)." % " || ".join(old_components))
    lines.extend(["", "// New endpoint: reservation before purchase."])
    lines.extend(render_agency("NEW", amenities))
    lines.append("")
    for amenity in range(amenities):
        lines.extend(
            render_service("NEW", amenity, amenities, protocol_steps)
        )
        lines.append("")
    lines.append("||NewEnvironment = (%s)." % " || ".join(new_components))
    lines.extend(
        [
            "",
            "// Quiescent-only component transfer: no in-flight state is mapped.",
            "relation R_AGENCY_FG = {",
            "    OLD_AGENCY@OLD_AGENCY = reconfigure_AGENCY "
            "-> NEW_AGENCY@NEW_AGENCY",
            "}",
        ]
    )
    for amenity in range(amenities):
        old_name = service_name("OLD", amenity)
        new_name = service_name("NEW", amenity)
        lines.extend(
            [
                "",
                "relation R_SERVICE_%02d_FG = {" % amenity,
                "    %s@%s = reconfigure_SERVICE_%02d -> %s@%s"
                % (old_name, old_name, amenity, new_name, new_name),
                "}",
            ]
        )
    endpoint_spec = [
        "    controllable = {ControllableActions}",
        "    marking = {agency.succ, agency.fail}",
        "    nonblocking",
    ]
    lines.extend(["", "controllerSpec OldSpec = {"])
    lines.extend(endpoint_spec)
    lines.extend(
        [
            "}",
            "controller ||OldController = OldEnvironment~{OldSpec}.",
            "",
            "controllerSpec NewSpec = {",
        ]
    )
    lines.extend(endpoint_spec)
    lines.extend(
        [
            "}",
            "controller ||NewController = NewEnvironment~{NewSpec}.",
            "",
            "updatingController TravelAgencyDerivedUpdate = {",
            "    oldController = OldController,",
            "    newController = NewController,",
            "    oldEnvironment = {%s}," % comma_join(old_components),
            "    newEnvironment = {%s}," % comma_join(new_components),
            "    mapRelation = {%s}," % comma_join(relations),
            "    oldGoal = OldSpec,",
            "    newGoal = NewSpec,",
            "    nonblocking,",
            "    revised_on_the_fly,",
            "    fine_grained",
            "}",
            "||%s = TravelAgencyDerivedUpdate." % TARGET,
            "",
        ]
    )
    return "\n".join(lines)


def atomic_write_exact(path: Path, payload: bytes) -> None:
    if path.exists():
        if not path.is_file() or path.is_symlink():
            raise ValueError("unsafe existing generated path: " + str(path))
        if path.read_bytes() != payload:
            raise ValueError(
                "existing generated file differs; choose a new output directory: "
                + str(path)
            )
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=path.name + ".",
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise


def canonical_source_record(workspace: Path) -> Dict[str, Any]:
    source = workspace / CANONICAL_SOURCE_PATH
    if not source.is_file() or source.is_symlink():
        raise ValueError("canonical Travel Agency source is missing: " + str(source))
    payload = source.read_bytes()
    observed_hash = sha256_bytes(payload)
    if observed_hash != CANONICAL_SOURCE_SHA256:
        raise ValueError(
            "canonical Travel Agency source digest changed: expected %s, observed %s"
            % (CANONICAL_SOURCE_SHA256, observed_hash)
        )
    if len(payload) != CANONICAL_SOURCE_BYTES:
        raise ValueError(
            "canonical Travel Agency source byte count changed: expected %d, "
            "observed %d" % (CANONICAL_SOURCE_BYTES, len(payload))
        )
    return {
        "path": CANONICAL_SOURCE_PATH,
        "bytes": len(payload),
        "sha256": observed_hash,
        "publication": {
            "title": "On-the-Fly Informed Search of Non-Blocking Directed Controllers",
            "venue": "Automatica 147 (2023) 110731",
            "doi": AUTOMATICA_DOI,
        },
    }


def prepare(
    output_directory: Path,
    instances: Sequence[Tuple[int, int]],
    root: Path | None = None,
) -> Dict[str, Any]:
    workspace = repository_root() if root is None else root.resolve()
    output_directory = output_directory.resolve()
    normalized = [(int(n), int(k)) for n, k in instances]
    if not normalized or normalized != sorted(set(normalized)):
        raise ValueError(
            "instances must be nonempty, unique, and lexicographically increasing"
        )
    for instance in normalized:
        validate_factors(*instance)
    if not inside(output_directory, workspace):
        raise ValueError("output directory must be inside the repository")

    source_record = canonical_source_record(workspace)
    models_directory = output_directory / "Models"
    expected_names = {
        "travel_agency_n%02d_k%02d.lts" % instance
        for instance in normalized
    }
    if models_directory.exists():
        extras = sorted(
            path.name
            for path in models_directory.glob("*.lts")
            if path.name not in expected_names
        )
        if extras:
            raise ValueError(
                "generated model directory contains unregistered .lts files: "
                + ", ".join(extras)
            )

    payloads: Dict[Path, bytes] = {}
    model_records: List[Dict[str, Any]] = []
    for amenities, protocol_steps in normalized:
        filename = "travel_agency_n%02d_k%02d.lts" % (
            amenities,
            protocol_steps,
        )
        path = models_directory / filename
        payload = render_model(amenities, protocol_steps).encode("utf-8")
        payloads[path] = payload
        completion_count = len(
            uncontrollable_completion_actions(amenities, protocol_steps)
        )
        drain_check = verify_uncontrollable_drain_acyclic(protocol_steps)
        model_records.append(
            {
                "id": "travel_agency_n%02d_k%02d"
                % (amenities, protocol_steps),
                "path": path.relative_to(output_directory).as_posix(),
                "bytes": len(payload),
                "sha256": sha256_bytes(payload),
                "target": TARGET,
                "family": "travel_agency_derived_fg_ducs",
                "expected_decision": "realizable",
                "decision_oracle": (
                    "constructive_all_q0_drain_to_quiescence_then_transfer"
                ),
                "factors": {
                    "amenities_n": amenities,
                    "protocol_step_choices_k": protocol_steps,
                    "maximum_repeated_select_actions": protocol_steps - 1,
                    "updated_components": amenities + 1,
                    "quiescent_transfer_relations": amenities + 1,
                    "quiescent_transfer_entries": amenities + 1,
                    "uncontrollable_completion_labels": completion_count,
                    "old_service_protocol": "direct_purchase_without_reservation",
                    "new_service_protocol": "reservation_before_purchase",
                    "expected_decision": "realizable",
                    "decision_oracle": (
                        "constructive_all_q0_drain_to_quiescence_then_transfer"
                    ),
                    "uncontrollable_drain_check": drain_check,
                },
            }
        )

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "generator_id": GENERATOR_ID,
        "hash_algorithm": "sha256",
        "family": "travel_agency_derived_fg_ducs",
        "canonical_source": source_record,
        "adaptation_status": {
            "classification": "derived_fg_ducs_adaptation_not_original_benchmark",
            "claim_limit": (
                "Results apply to this documented source-structure-derived "
                "FG-DUCS family only. The canonical hash binds provenance, not "
                "equivalence: the family must not be reported as the unmodified "
                "OTF-DCS benchmark or as trace equivalent, bisimilar, or "
                "semantically equivalent to it."
            ),
            "preserved": [
                "Agency and per-amenity Service orchestration topology",
                "Amenities (N) and Steps (K) scaling axes",
                "K-way steps choice followed by repeated select actions",
                "direct-purchase and reservation purchase branches",
                "nonblocking endpoint-controller synthesis",
                "uncontrollable service outcome and completion actions",
            ],
            "changed": [
                "The source's direct branch is isolated as the old endpoint.",
                "The source's reservation branch is isolated as the new endpoint.",
                "agency.request and query[i] are controllable admission actions so "
                "the update controller can stop admitting new transactions.",
                "The Agency and Service components are duplicated by version.",
                "Transfer relations contain only idle-state pairs (quiescent transfer).",
                "The source ServiceMonitor and AgencyMonitor are not reused; endpoint "
                "goals retain the source nonblocking marking objective.",
            ],
            "not_preserved": [
                "source controllability partition: agency.request and query[i] "
                "are uncontrollable in the canonical source but controllable here",
                "source monitor composition",
                "source transition system and trace language",
                "trace equivalence, bisimulation, and semantic equivalence",
            ],
        },
        "factor_definitions": {
            "amenities_n": "number of amenity Service pairs",
            "protocol_step_choices_k": (
                "number of steps[i][s] outcomes, s=0..K-1; the maximum "
                "number of repeated select[i] actions is K-1"
            ),
            "updated_components": "N Service pairs plus one Agency pair",
        },
        "constructive_decision_oracle": {
            "expected_decision": "realizable",
            "q0_scope": "every reachable old closed-loop state",
            "strategy": (
                "Disable new controllable admissions (agency.request and root "
                "query[i]); every already-active Service has only a finite "
                "acyclic uncontrollable completion burst. Permit the required "
                "chain query[i], terminal cancel, and agency acknowledgement "
                "actions until Agency and all Services are idle; then execute "
                "the N+1 idle-only component transfers sequentially."
            ),
            "uncontrollable_cycle_argument": (
                "The generator checks each Service's uncontrollable-only "
                "abstract graph is acyclic. Every uncontrollable product step "
                "strictly decreases the sum of local longest-path ranks, so "
                "parallel synchronization cannot create an uncontrollable cycle."
            ),
            "controllable_drain_actions": [
                "chain-required query[i]",
                "cancel[i]",
                "agency.succ",
                "agency.fail",
            ],
            "transfer_stage": (
                "After global idle is reached, all N+1 registered idle-state "
                "relations are enabled and can be executed in any sequential order."
            ),
            "scope": "every registered N,K instance",
        },
        "models": model_records,
    }
    manifest_path = output_directory / "manifest.json"
    manifest_payload = canonical_json_bytes(manifest)

    expected_payloads = dict(payloads)
    expected_payloads[manifest_path] = manifest_payload
    for path, payload in expected_payloads.items():
        if path.exists() and (
            not path.is_file()
            or path.is_symlink()
            or path.read_bytes() != payload
        ):
            raise ValueError(
                "existing generated file differs; choose a new output directory: "
                + str(path)
            )
    for path, payload in expected_payloads.items():
        atomic_write_exact(path, payload)

    return {
        "status": "READY",
        "output_directory": str(output_directory),
        "manifest": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "generated_models": len(model_records),
        "instances": [
            {"amenities_n": n, "protocol_step_choices_k": k}
            for n, k in normalized
        ],
    }


def parse_arguments(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--instances",
        type=parse_instances,
        default=None,
        help=(
            "strictly increasing N:K pairs, for example 1:1,2:2,3:4; "
            "defaults to 1:1,2:2,3:4,4:6"
        ),
    )
    return parser.parse_args(arguments)


def main(arguments: Sequence[str] | None = None) -> int:
    args = parse_arguments(arguments)
    try:
        instances = (
            list(DEFAULT_INSTANCES)
            if args.instances is None
            else args.instances
        )
        summary = prepare(args.output, instances)
    except (OSError, ValueError) as error:
        print("GENERATION FAIL: " + str(error), file=sys.stderr)
        return 2
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
