#!/usr/bin/env python3
"""Execute and audit typed FG-DUCS handoff bundles.

The Java synthesis path exports its checked winning certificate before Goal
quotienting.  This runner is a separate Python implementation that consumes
that bundle, covers every strategy outcome, performs Goal-to-endpoint state
loading atomically, and executes the post-update endpoint.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Set, Tuple

from independent_raw_oracle import canonical_json_bytes
from campaign_checksums import check_checksums
from harness_common import (
    KNOWN_TERMINAL_PROCESS_STATUSES,
    build_plan,
    load_config,
    resolve_prospective_output,
    resolve_registered_existing,
    status_from_exit,
    validate_preexecution_gate,
)


PROTOCOL_SCHEMA = "fse2027-atomic-handoff-validation-protocol-v1"
BUNDLE_SCHEMA = "fse2027-atomic-handoff-bundle-v1"
SUMMARY_SCHEMA = "fse2027-atomic-handoff-validation-summary-v2"


class BundleViolation(RuntimeError):
    pass


class HandoffExecutionUnavailable(RuntimeError):
    """The registered handoff process did not yield an auditable bundle."""


class HandoffInternalRunnerError(RuntimeError):
    """The runner failed internally before a semantic observation."""


@dataclass(frozen=True)
class Outcome:
    index: int
    target: str
    goal: bool


@dataclass(frozen=True)
class Handoff:
    goal: str
    endpoint_id: str
    post_state: str
    controller_state: int


@dataclass(frozen=True)
class ParsedBundle:
    raw: Mapping[str, Any]
    configurations: Mapping[str, Mapping[str, Any]]
    strategy: Mapping[Tuple[str, str], Tuple[Outcome, ...]]
    handoffs: Mapping[str, Handoff]
    post_states: Mapping[str, Mapping[str, Any]]
    post_transitions: Mapping[Tuple[str, str], Tuple[str, ...]]
    q0_roots: Tuple[str, ...]
    q0_endpoint_entry_count: int
    controllable_actions: Set[str]
    maximum_rank: int


class AtomicHandoffRuntime:
    """Reference executor with one linearization lock across Goal handoff."""

    def __init__(self, bundle: ParsedBundle):
        self.bundle = bundle
        self.lock = threading.RLock()
        self.phase = "IDLE"
        self.mid_state: str | None = None
        self.post_state: str | None = None
        self.controller_state: int | None = None
        self.sequence = 0
        self.max_critical_occupancy = 0
        self._critical_occupancy = 0
        self.partial_load_observations = 0
        self.goal_observations = 0
        self.controller_loads = 0
        self.post_switches = 0

    def _enter(self) -> None:
        self._critical_occupancy += 1
        self.max_critical_occupancy = max(
            self.max_critical_occupancy, self._critical_occupancy
        )

    def _leave(self) -> None:
        self._critical_occupancy -= 1

    def reset_mid(self, configuration: str) -> None:
        if configuration not in self.bundle.configurations:
            raise BundleViolation("unknown MID configuration")
        with self.lock:
            self.phase = "MID"
            self.mid_state = configuration
            self.post_state = None
            self.controller_state = None
            if bool(self.bundle.configurations[configuration]["goal"]):
                self._handoff_locked(configuration, None, None)

    def reset_post(self, state: str) -> None:
        record = self.bundle.post_states.get(state)
        if record is None:
            raise BundleViolation("unknown POST state")
        with self.lock:
            self.phase = "POST"
            self.mid_state = None
            self.post_state = state
            self.controller_state = int(record["controller_state"])

    def dispatch_mid(
        self,
        action: str,
        outcome_index: int,
        *,
        goal_observed: threading.Event | None = None,
        release_handoff: threading.Event | None = None,
    ) -> Mapping[str, Any]:
        arrival = time.monotonic_ns()
        with self.lock:
            self._enter()
            try:
                if self.phase != "MID" or self.mid_state is None:
                    raise BundleViolation("MID event dispatched outside MID")
                source = self.mid_state
                outcomes = self.bundle.strategy.get((source, action))
                if outcomes is None:
                    raise BundleViolation("event is absent from the winning strategy")
                if outcome_index < 0 or outcome_index >= len(outcomes):
                    raise BundleViolation("outcome is absent from the exact event bucket")
                selected = outcomes[outcome_index]
                self.mid_state = selected.target
                handoff_record: Mapping[str, Any] | None = None
                if selected.goal:
                    handoff_record = self._handoff_locked(
                        selected.target, goal_observed, release_handoff
                    )
                self.sequence += 1
                return {
                    "sequence": self.sequence,
                    "arrival_ns": arrival,
                    "source": source,
                    "action": action,
                    "outcome_index": outcome_index,
                    "target_configuration": selected.target,
                    "handoff": handoff_record,
                    "phase_after": self.phase,
                }
            finally:
                self._leave()

    def _handoff_locked(
        self,
        goal: str,
        goal_observed: threading.Event | None,
        release_handoff: threading.Event | None,
    ) -> Mapping[str, Any]:
        if self.phase != "MID" or self.mid_state != goal:
            raise BundleViolation("handoff did not originate at the observed Goal")
        handoff = self.bundle.handoffs.get(goal)
        if handoff is None:
            raise BundleViolation("Goal has no handoff-map entry")
        post = self.bundle.post_states.get(handoff.post_state)
        if post is None:
            raise BundleViolation("handoff names an unknown POST state")
        if int(post["controller_state"]) != handoff.controller_state:
            raise BundleViolation("handoff controller state differs from POST endpoint")

        self.goal_observations += 1
        if goal_observed is not None:
            goal_observed.set()
        if release_handoff is not None and not release_handoff.wait(timeout=10):
            raise HandoffExecutionUnavailable(
                "deterministic handoff-race latch timed out"
            )

        self.controller_state = handoff.controller_state
        self.controller_loads += 1
        self.post_state = handoff.post_state
        self.mid_state = None
        self.phase = "POST"
        self.post_switches += 1
        return {
            "goal": goal,
            "endpoint_id": handoff.endpoint_id,
            "post_state": handoff.post_state,
            "controller_state_loaded": handoff.controller_state,
        }

    def dispatch_post(self, action: str, outcome_index: int) -> Mapping[str, Any]:
        arrival = time.monotonic_ns()
        with self.lock:
            self._enter()
            try:
                if (
                    self.phase != "POST"
                    or self.post_state is None
                    or self.controller_state is None
                ):
                    raise BundleViolation("POST event observed before atomic handoff")
                source = self.post_state
                outcomes = self.bundle.post_transitions.get((source, action))
                if outcomes is None:
                    raise BundleViolation("event is absent from the POST endpoint")
                if outcome_index < 0 or outcome_index >= len(outcomes):
                    raise BundleViolation("outcome is absent from the POST event bucket")
                target = outcomes[outcome_index]
                expected_controller = int(
                    self.bundle.post_states[target]["controller_state"]
                )
                self.post_state = target
                self.controller_state = expected_controller
                self.sequence += 1
                return {
                    "sequence": self.sequence,
                    "arrival_ns": arrival,
                    "source": source,
                    "action": action,
                    "outcome_index": outcome_index,
                    "target": target,
                    "controller_state_after": expected_controller,
                }
            finally:
                self._leave()

    def snapshot(self) -> Mapping[str, Any]:
        with self.lock:
            if self.phase == "POST" and (
                self.post_state is None or self.controller_state is None
            ):
                self.partial_load_observations += 1
            if self.phase == "MID" and (
                self.post_state is not None or self.controller_state is not None
            ):
                self.partial_load_observations += 1
            return {
                "phase": self.phase,
                "mid_state": self.mid_state,
                "post_state": self.post_state,
                "controller_state": self.controller_state,
            }


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--java", type=Path,
        default=Path("/opt/homebrew/opt/openjdk@17/bin/java"),
    )
    parser.add_argument(
        "--decision-campaign", type=Path,
        help="registered six-cell campaign used to authorize positive handoff",
    )
    return parser.parse_args()


def repository_root() -> Path:
    return Path(__file__).resolve().parents[4]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_registered(root: Path, value: str) -> Path:
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("registered path must be repository-relative")
    path = (root / relative).resolve()
    path.relative_to(root)
    if not path.is_file() or path.is_symlink():
        raise ValueError("registered file is missing: " + str(path))
    return path


def require_hash(path: Path, expected: str, label: str) -> None:
    observed = digest(path)
    if observed != expected:
        raise ValueError(
            "%s SHA-256 mismatch: expected %s, observed %s"
            % (label, expected, observed)
        )


def _campaign_file(campaign: Path, relative_text: str, label: str) -> Path:
    relative = Path(relative_text)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(label + " has an unsafe campaign-relative path")
    path = (campaign / relative).resolve()
    path.relative_to(campaign)
    if not path.is_file() or path.is_symlink():
        raise ValueError(label + " is missing")
    return path


def evaluate_decision_precondition(
    root: Path,
    protocol: Mapping[str, Any],
    campaign_argument: Path | None,
    runtime_jar_sha256: str,
) -> Mapping[str, Any]:
    """Validate campaign identity, then decide whether handoff may execute.

    Identity drift is an error.  A retained timeout, crash, invalid result, or
    non-winning decision is an intact observation whose registered consequence
    is to skip the positive-only handoff without launching the synthesis JVM.
    """

    registration = protocol.get("decision_precondition")
    if not isinstance(registration, dict):
        raise ValueError("handoff protocol lacks its decision precondition")
    if campaign_argument is None:
        raise ValueError("--decision-campaign is required by this protocol")
    registered_campaign = Path(str(registration.get("campaign", "")))
    if (
        registered_campaign.is_absolute()
        or ".." in registered_campaign.parts
        or not registered_campaign.parts
    ):
        raise ValueError(
            "decision campaign differs from the prospectively registered path"
        )
    campaign = resolve_registered_existing(
        root, str(registered_campaign), campaign_argument, "directory"
    )

    config = _campaign_file(campaign, "config.json", "campaign config")
    plan = _campaign_file(campaign, "plan.json", "campaign plan")
    raw_path = _campaign_file(campaign, "raw_runs.csv", "campaign raw table")
    require_hash(config, str(registration["config_sha256"]), "campaign config")
    if check_checksums(campaign) <= 0:
        raise ValueError("decision campaign checksum seal is empty")
    plan_data = json.loads(plan.read_text(encoding="utf-8"))
    if plan_data != build_plan(load_config(config)):
        raise ValueError("decision campaign plan is not a pure config derivation")
    if plan_data.get("plan_sha256") != registration.get("plan_semantic_sha256"):
        raise ValueError("campaign plan differs from the registered plan")
    with raw_path.open("r", encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    planned_ids = {str(job["job_id"]) for job in plan_data.get("jobs", [])}
    raw_ids = {str(row.get("job_id", "")) for row in rows}
    if len(rows) != len(raw_ids) or raw_ids != planned_ids or len(rows) != 6:
        raise ValueError("decision campaign does not retain its exact six-cell denominator")
    job_id = str(registration["job_id"])
    matches = [row for row in rows if row.get("job_id") == job_id]
    if len(matches) != 1:
        raise ValueError("decision campaign does not contain exactly one prerequisite row")
    row = matches[0]
    for key, expected in (
        ("model_id", registration["model_id"]),
        ("method_id", registration["method_id"]),
        ("input_sha256", registration["input_sha256"]),
        ("classpath_sha256", runtime_jar_sha256),
        ("config_sha256", registration["config_sha256"]),
        ("plan_sha256", registration["plan_semantic_sha256"]),
    ):
        if row.get(key) != str(expected):
            raise ValueError("prerequisite row identity drift: " + key)
    meta_path = _campaign_file(campaign, row["meta_path"], "prerequisite metadata")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if meta.get("job", {}).get("job_id") != job_id:
        raise ValueError("prerequisite metadata names a different job")
    if meta.get("classpath", {}).get("sha256") != runtime_jar_sha256:
        raise ValueError("prerequisite metadata names a different runtime")
    artifact_text: Dict[str, str] = {}
    for name in ("stdout", "stderr"):
        artifact = _campaign_file(
            campaign, row[name + "_path"], "prerequisite " + name
        )
        require_hash(artifact, row[name + "_sha256"], "prerequisite " + name)
        artifact_text[name] = artifact.read_text(encoding="utf-8", errors="replace")
        if meta.get("artifact_digests", {}).get(name, {}).get("sha256") != row[
            name + "_sha256"
        ]:
            raise ValueError("prerequisite metadata artifact drift: " + name)
    output_relative = Path(row.get("output_path", ""))
    if output_relative.is_absolute() or ".." in output_relative.parts:
        raise ValueError("prerequisite output has an unsafe campaign-relative path")
    output_artifact = (campaign / output_relative).resolve()
    output_artifact.relative_to(campaign)
    output_meta = meta.get("artifact_digests", {}).get("output", {})
    if output_artifact.exists():
        if not output_artifact.is_file() or output_artifact.is_symlink():
            raise ValueError("prerequisite output artifact is malformed")
        require_hash(output_artifact, row["output_sha256"], "prerequisite output")
        if not all((
            output_meta.get("exists") is True,
            output_meta.get("sha256") == row["output_sha256"],
        )):
            raise ValueError("prerequisite output metadata drift")
        artifact_text["output"] = output_artifact.read_text(
            encoding="utf-8", errors="replace"
        )
    else:
        if row.get("output_sha256") or output_meta.get("exists") is not False:
            raise ValueError("prerequisite absent-output metadata drift")
        artifact_text["output"] = ""

    if row.get("completed") != "True":
        raise ValueError("prerequisite row is not a terminal record")
    status = str(row.get("process_status", ""))
    if status not in KNOWN_TERMINAL_PROCESS_STATUSES:
        raise ValueError("prerequisite has an unknown terminal status")
    raw_exit = str(row.get("exit_code", ""))
    exit_code = int(raw_exit) if raw_exit else None
    timed_out = row.get("timed_out") == "True"
    reconstructed = status_from_exit(
        exit_code,
        timed_out,
        artifact_text["stderr"],
        spawn_error=str(row.get("spawn_error", "")),
    )
    if row.get("spawn_error") and "ENOMEM" in row.get("spawn_error", ""):
        reconstructed = "OOM"
    if meta.get("harness_error"):
        harness_errors = meta.get("harness_errors")
        if not all((
            status == "HARNESS_ERROR",
            isinstance(harness_errors, list),
            bool(harness_errors),
            all(isinstance(error, str) and error for error in harness_errors),
            " | ".join(harness_errors) == meta.get("harness_error"),
            all(
                "[HARNESS_ERROR] " + error in artifact_text["stderr"]
                for error in harness_errors
            ),
        )):
            raise ValueError("prerequisite harness-error record is inconsistent")
        reconstructed = "HARNESS_ERROR"
    elif status == "HARNESS_ERROR":
        raise ValueError("prerequisite has a spurious harness-error status")
    if reconstructed != status:
        raise ValueError("prerequisite terminal status is internally inconsistent")
    if not all((
        meta.get("status") == status,
        meta.get("timed_out") is timed_out,
        meta.get("exit_code") == exit_code,
        str(meta.get("spawn_error", "")) == str(row.get("spawn_error", "")),
    )):
        raise ValueError("prerequisite metadata terminal status drift")
    decision_bearing = status in {"SUCCESS", "UNREALIZABLE"}
    if decision_bearing:
        observed = "realizable" if status == "SUCCESS" else "unrealizable"
        expected_exit = "0" if status == "SUCCESS" else "6"
        if not all((
            row.get("timed_out") == "False",
            row.get("exit_code") == expected_exit,
            row.get("revised_decision") == observed,
            row.get("verification_status") == "verified",
            row.get("run_verified") == "true",
            row.get("independent_verification_basis")
            == "exhaustive_reachable_fixed_point",
            row.get("internal_certificate_check") == "passed",
        )):
            raise ValueError("decision-bearing prerequisite is internally inconsistent")
        if status == "SUCCESS" and not all((
            row.get("link_checker") == "passed",
            int(row.get("certificate_states") or 0) > 0,
        )):
            raise ValueError("winning prerequisite lacks its certificate checks")
        if status == "UNREALIZABLE" and not all((
            int(row.get("losing_region_states") or 0) > 0,
            int(row.get("losing_region_phase_masks") or 0) > 0,
        )):
            raise ValueError("losing prerequisite lacks its checked countercertificate")
    elif status == "TIMEOUT":
        if row.get("timed_out") != "True" or not row.get("timeout_termination_action"):
            raise ValueError("timeout prerequisite is internally inconsistent")
    eligible = status == "SUCCESS"
    transition = (campaign / Path(row.get("transitions_path", ""))).resolve()
    transition.relative_to(campaign)
    if eligible:
        if (
            not transition.is_file()
            or transition.is_symlink()
            or not row.get("transitions_sha256")
        ):
            raise ValueError("winning prerequisite lacks its registered controller")
        require_hash(
            transition, row["transitions_sha256"], "prerequisite controller"
        )
        if meta.get("artifact_digests", {}).get("transitions", {}).get(
            "sha256"
        ) != row["transitions_sha256"]:
            raise ValueError("prerequisite controller metadata drift")
    else:
        transition_meta = meta.get("artifact_digests", {}).get("transitions", {})
        if transition.exists():
            if (
                not transition.is_file()
                or transition.is_symlink()
                or not row.get("transitions_sha256")
            ):
                raise ValueError("non-winning diagnostic transition is malformed")
            require_hash(
                transition,
                row["transitions_sha256"],
                "prerequisite diagnostic transition",
            )
            if not all((
                transition_meta.get("exists") is True,
                transition_meta.get("sha256") == row["transitions_sha256"],
            )):
                raise ValueError("non-winning diagnostic transition metadata drift")
        elif row.get("transitions_sha256") or transition_meta.get("exists") is not False:
            raise ValueError("non-winning absent transition metadata drift")
    return {
        "status": "PASS" if eligible else "NOT_MET",
        "eligible": eligible,
        "campaign": str(campaign.relative_to(root)),
        "raw_runs_sha256": digest(raw_path),
        "job_id": job_id,
        "observed_process_status": row.get("process_status", ""),
        "observed_decision": row.get("revised_decision", ""),
        "verified": row.get("run_verified", "") == "true",
        "controller_sha256": row.get("transitions_sha256", ""),
    }


def validate_registered_attestation(
    root: Path,
    protocol: Mapping[str, Any],
    attestation: Path,
) -> Mapping[str, Any]:
    """Validate a build record without creating a protocol/attestation cycle.

    Legacy frozen protocols bind the attestation file hash.  A newly frozen
    protocol may instead require the attestation to validate against the
    *current* source manifest and JAR.  The latter avoids embedding the hash of
    a file whose own source identity contains the protocol bytes.
    """

    mode = protocol.get("build_attestation_validation")
    if mode == "current_source_identity":
        from verify_runtime_build import (  # Imported lazily for CLI startup.
            ATTESTATION_PATH,
            load_and_validate_attestation,
        )

        expected = (root / ATTESTATION_PATH).resolve()
        if attestation.resolve() != expected:
            raise ValueError("protocol names a non-canonical build attestation")
        _, summary = load_and_validate_attestation(root)
        return summary
    if mode is None and isinstance(protocol.get("build_attestation_sha256"), str):
        require_hash(
            attestation,
            str(protocol["build_attestation_sha256"]),
            "build attestation",
        )
        return {"status": "PASS", "validation": "legacy_file_hash"}
    raise ValueError("unsupported build-attestation validation contract")


def validate_registered_runtime(
    protocol: Mapping[str, Any],
    jar: Path,
    attestation_validation: Mapping[str, Any],
) -> str:
    """Return the verified JAR hash under the protocol's binding mode."""

    mode = protocol.get("runtime_jar_validation")
    if mode == "current_build_attestation":
        expected = str(attestation_validation.get("runtime_jar_sha256", ""))
        if len(expected) != 64:
            raise ValueError("validated build record lacks the runtime JAR hash")
        require_hash(jar, expected, "runtime JAR")
        return expected
    if mode is None and isinstance(protocol.get("runtime_jar_sha256"), str):
        expected = str(protocol["runtime_jar_sha256"])
        require_hash(jar, expected, "runtime JAR")
        return expected
    raise ValueError("unsupported runtime-JAR validation contract")


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


def _objects_by_id(rows: Any, label: str) -> Dict[str, Mapping[str, Any]]:
    if not isinstance(rows, list) or not rows:
        raise BundleViolation(label + " must be a non-empty array")
    result: Dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            raise BundleViolation(label + " contains an invalid object")
        identifier = str(row["id"])
        if identifier in result:
            raise BundleViolation(label + " contains duplicate ids")
        result[identifier] = row
    return result


def parse_bundle(raw: Mapping[str, Any]) -> ParsedBundle:
    if raw.get("schema_version") != BUNDLE_SCHEMA:
        raise BundleViolation("unsupported bundle schema")
    configurations = _objects_by_id(raw.get("configurations"), "configurations")
    post_states = _objects_by_id(raw.get("post_states"), "post_states")

    strategy: Dict[Tuple[str, str], Tuple[Outcome, ...]] = {}
    strategy_rows = raw.get("strategy")
    if not isinstance(strategy_rows, list):
        raise BundleViolation("strategy must be an array")
    for row in strategy_rows:
        if not isinstance(row, dict):
            raise BundleViolation("strategy contains a non-object")
        source = str(row.get("source", ""))
        action = str(row.get("action", ""))
        key = (source, action)
        if source not in configurations or not action or key in strategy:
            raise BundleViolation("strategy bucket identity is invalid")
        if bool(configurations[source].get("goal")):
            raise BundleViolation("Goal has an outgoing MID strategy bucket")
        outcome_rows = row.get("outcomes")
        if not isinstance(outcome_rows, list) or not outcome_rows:
            raise BundleViolation("strategy bucket has no outcomes")
        parsed: List[Outcome] = []
        for index, outcome in enumerate(outcome_rows):
            if not isinstance(outcome, dict) or outcome.get("index") != index:
                raise BundleViolation("strategy outcome indices are not canonical")
            target = str(outcome.get("target", ""))
            if target not in configurations:
                raise BundleViolation("strategy outcome names an unknown configuration")
            goal = bool(outcome.get("goal"))
            if goal != bool(configurations[target].get("goal")):
                raise BundleViolation("strategy outcome Goal flag is inconsistent")
            source_rank = int(configurations[source]["rank"])
            target_rank = int(configurations[target]["rank"])
            if target_rank >= source_rank:
                raise BundleViolation("strategy outcome does not decrease rank")
            parsed.append(Outcome(index, target, goal))
        strategy[key] = tuple(parsed)

    handoffs: Dict[str, Handoff] = {}
    handoff_rows = raw.get("handoffs")
    if not isinstance(handoff_rows, list) or not handoff_rows:
        raise BundleViolation("handoffs must be a non-empty array")
    for row in handoff_rows:
        if not isinstance(row, dict):
            raise BundleViolation("handoffs contains a non-object")
        goal = str(row.get("goal_configuration", ""))
        post_state = str(row.get("post_state_id", ""))
        if (
            goal not in configurations
            or not bool(configurations[goal].get("goal"))
            or post_state not in post_states
            or goal in handoffs
        ):
            raise BundleViolation("handoff identity is invalid")
        controller_state = int(row["controller_state_to_load"])
        if controller_state != int(post_states[post_state]["controller_state"]):
            raise BundleViolation("handoff load differs from POST controller state")
        handoffs[goal] = Handoff(
            goal=goal,
            endpoint_id=str(row["endpoint_id"]),
            post_state=post_state,
            controller_state=controller_state,
        )
    goal_ids = {
        identifier
        for identifier, row in configurations.items()
        if bool(row.get("goal"))
    }
    if set(handoffs) != goal_ids:
        raise BundleViolation("handoff map does not cover exactly every Goal")

    post_transitions: Dict[Tuple[str, str], Tuple[str, ...]] = {}
    for state, row in post_states.items():
        transitions = row.get("transitions")
        if not isinstance(transitions, list) or not transitions:
            raise BundleViolation("POST endpoint contains a deadlock")
        for transition in transitions:
            if not isinstance(transition, dict):
                raise BundleViolation("POST transition is not an object")
            action = str(transition.get("action", ""))
            outcomes = transition.get("outcomes")
            key = (state, action)
            if (
                not action
                or key in post_transitions
                or not isinstance(outcomes, list)
                or not outcomes
                or any(str(target) not in post_states for target in outcomes)
            ):
                raise BundleViolation("POST event bucket is invalid")
            post_transitions[key] = tuple(str(target) for target in outcomes)

    q0_rows = raw.get("q0_entries")
    if not isinstance(q0_rows, list) or not q0_rows:
        raise BundleViolation("q0_entries must be a non-empty array")
    if any(not isinstance(row, dict) for row in q0_rows):
        raise BundleViolation("q0_entries contains a non-object row")
    if any(
        type(row.get("old_state_id")) is not str
        or not row.get("old_state_id")
        or type(row.get("root_configuration")) is not str
        or not row.get("root_configuration")
        for row in q0_rows
    ):
        raise BundleViolation("q0_entries contains an invalid typed identifier")
    old_state_ids = tuple(row["old_state_id"] for row in q0_rows)
    if len(old_state_ids) != len(set(old_state_ids)):
        raise BundleViolation("q0_entries must name distinct old endpoint states")
    if any(type(row.get("old_controller_state")) is not int for row in q0_rows):
        raise BundleViolation("q0_entries contains an invalid old controller state")
    q0_entry_roots = tuple(row["root_configuration"] for row in q0_rows)
    if any(root not in configurations for root in q0_entry_roots):
        raise BundleViolation("Q0 entry names an unknown configuration")
    # Several reachable old endpoint states may project to the same canonical
    # FG-DUCS game state after the old controller state is erased.  Preserve
    # the full endpoint-to-root relation in raw.q0_entries, but execute each
    # distinct game root exactly once.
    q0_roots = tuple(dict.fromkeys(q0_entry_roots))
    initial_ids = {
        identifier
        for identifier, row in configurations.items()
        if bool(row.get("initial"))
    }
    if set(q0_roots) != initial_ids:
        raise BundleViolation("Q0 entries do not cover exactly all initial states")

    non_goals = {
        identifier
        for identifier, row in configurations.items()
        if not bool(row.get("goal"))
    }
    strategy_sources = {source for source, _ in strategy}
    if strategy_sources != non_goals:
        raise BundleViolation("strategy does not cover every non-Goal certificate state")

    expected_counts = {
        "initial_configuration_count": len(initial_ids),
        "certificate_state_count": len(configurations),
        "strategy_bucket_count": len(strategy),
        "strategy_outcome_edge_count": sum(len(value) for value in strategy.values()),
        "goal_count": len(goal_ids),
        "post_state_count": len(post_states),
    }
    for field, expected in expected_counts.items():
        if int(raw.get(field, -1)) != expected:
            raise BundleViolation(field + " disagrees with the serialized bundle")
    maximum_rank = max(int(row["rank"]) for row in configurations.values())
    if int(raw.get("maximum_rank", -1)) != maximum_rank:
        raise BundleViolation("maximum rank disagrees with configurations")

    controllable = raw.get("controllable_actions")
    if not isinstance(controllable, list) or any(
        not isinstance(action, str) for action in controllable
    ):
        raise BundleViolation("controllable_actions is invalid")
    return ParsedBundle(
        raw=raw,
        configurations=configurations,
        strategy=strategy,
        handoffs=handoffs,
        post_states=post_states,
        post_transitions=post_transitions,
        q0_roots=q0_roots,
        q0_endpoint_entry_count=len(q0_rows),
        controllable_actions=set(controllable),
        maximum_rank=maximum_rank,
    )


def _first_bucket(bundle: ParsedBundle, state: str) -> Tuple[str, Tuple[Outcome, ...]]:
    candidates = sorted(
        (action, outcomes)
        for (source, action), outcomes in bundle.strategy.items()
        if source == state
    )
    if not candidates:
        raise BundleViolation("non-Goal certificate state has no strategy bucket")
    return candidates[0]


def _first_post_bucket(
    bundle: ParsedBundle, state: str
) -> Tuple[str, Tuple[str, ...]]:
    candidates = sorted(
        (action, outcomes)
        for (source, action), outcomes in bundle.post_transitions.items()
        if source == state
    )
    if not candidates:
        raise BundleViolation("POST endpoint state has no outgoing event")
    return candidates[0]


def validate_required_action_buckets(
    bundle: ParsedBundle,
    required_action: str,
    expected_fanout: int,
) -> Mapping[str, Any]:
    if type(expected_fanout) is not int or expected_fanout < 2:
        raise BundleViolation("required action fan-out must be an integer >= 2")
    if required_action not in bundle.controllable_actions:
        raise BundleViolation("required update action is not controllable")
    buckets = [
        (source, outcomes)
        for (source, action), outcomes in sorted(bundle.strategy.items())
        if action == required_action
    ]
    if not buckets:
        raise BundleViolation("required update action has no strategy bucket")
    for source, outcomes in buckets:
        targets = {outcome.target for outcome in outcomes}
        if len(outcomes) != expected_fanout or len(targets) != expected_fanout:
            raise BundleViolation(
                "required update bucket lacks the registered distinct outcomes: "
                + source
            )
    return {
        "action": required_action,
        "action_controllable": True,
        "outcome_semantics": "all_bucket_results_adversarial",
        "bucket_count": len(buckets),
        "outcome_edges": sum(len(outcomes) for _, outcomes in buckets),
        "minimum_fanout": min(len(outcomes) for _, outcomes in buckets),
        "maximum_fanout": max(len(outcomes) for _, outcomes in buckets),
        "distinct_targets_per_bucket": True,
    }


def execute_q0_traces(bundle: ParsedBundle) -> Mapping[str, Any]:
    records: List[Mapping[str, Any]] = []
    loaded_states: Set[int] = set()
    reached_goals: Set[str] = set()
    for root in bundle.q0_roots:
        runtime = AtomicHandoffRuntime(bundle)
        runtime.reset_mid(root)
        actions: List[str] = []
        visited = [root]
        while runtime.phase == "MID":
            if runtime.mid_state is None:
                raise BundleViolation("MID runtime lost its configuration")
            action, outcomes = _first_bucket(bundle, runtime.mid_state)
            record = runtime.dispatch_mid(action, 0)
            actions.append(action)
            visited.append(str(record["target_configuration"]))
            if len(actions) > bundle.maximum_rank:
                raise BundleViolation("Q0 execution exceeded certificate rank")
        snapshot = runtime.snapshot()
        if snapshot["phase"] != "POST":
            raise BundleViolation("Q0 execution did not complete handoff")
        reached_goals.add(visited[-1])
        loaded_states.add(int(snapshot["controller_state"]))
        post_action, post_outcomes = _first_post_bucket(
            bundle, str(snapshot["post_state"])
        )
        post_record = runtime.dispatch_post(post_action, 0)
        records.append(
            {
                "root": root,
                "mid_actions": actions,
                "visited_configurations": visited,
                "handoff_post_state": snapshot["post_state"],
                "controller_state_loaded": snapshot["controller_state"],
                "post_action": post_action,
                "post_target": post_record["target"],
            }
        )
    return {
        "trace_count": len(records),
        "maximum_mid_steps": max(len(row["mid_actions"]) for row in records),
        "reached_goals": sorted(reached_goals),
        "loaded_controller_states": sorted(loaded_states),
        "traces": records,
    }


def execute_q0_nondeterministic_forks(
    bundle: ParsedBundle,
    required_action: str,
) -> Mapping[str, Any]:
    """Complete one trace per Q0 and per result of a named strategy bucket.

    All other buckets use their canonical first result.  The named action must
    occur exactly once on that canonical policy path from every Q0 root; every
    local result is then replayed from the same root through Goal, atomic load,
    and one POST event.
    """

    if not required_action:
        raise BundleViolation("forked Q0 execution requires an action")
    records: List[Mapping[str, Any]] = []
    fanouts: Set[int] = set()
    for root in bundle.q0_roots:
        root_rank = int(bundle.configurations[root]["rank"])
        probe_state = root
        probe_steps = 0
        required_outcomes: Tuple[Outcome, ...] | None = None
        while not bool(bundle.configurations[probe_state]["goal"]):
            action, outcomes = _first_bucket(bundle, probe_state)
            if action == required_action:
                if required_outcomes is not None:
                    raise BundleViolation(
                        "named nondeterministic action repeats on a Q0 policy path"
                    )
                required_outcomes = outcomes
            probe_state = outcomes[0].target
            probe_steps += 1
            if probe_steps > root_rank:
                raise BundleViolation("Q0 fork discovery exceeded certificate rank")
        if required_outcomes is None:
            raise BundleViolation(
                "named nondeterministic action is absent from a Q0 policy path"
            )
        fanouts.add(len(required_outcomes))

        for required_index in range(len(required_outcomes)):
            runtime = AtomicHandoffRuntime(bundle)
            runtime.reset_mid(root)
            used = False
            actions: List[str] = []
            selected_target = ""
            while runtime.phase == "MID":
                if runtime.mid_state is None:
                    raise BundleViolation("forked Q0 runtime lost its configuration")
                action, outcomes = _first_bucket(bundle, runtime.mid_state)
                outcome_index = 0
                if action == required_action:
                    if used:
                        raise BundleViolation(
                            "named nondeterministic action repeats during Q0 replay"
                        )
                    if required_index >= len(outcomes):
                        raise BundleViolation(
                            "named nondeterministic bucket fan-out varies by path"
                        )
                    outcome_index = required_index
                    selected_target = outcomes[outcome_index].target
                    used = True
                runtime.dispatch_mid(action, outcome_index)
                actions.append(action)
                if len(actions) > root_rank:
                    raise BundleViolation("forked Q0 execution exceeded certificate rank")
            if not used or runtime.phase != "POST":
                raise BundleViolation("forked Q0 execution did not complete handoff")
            snapshot = runtime.snapshot()
            post_action, _ = _first_post_bucket(
                bundle, str(snapshot["post_state"])
            )
            post_record = runtime.dispatch_post(post_action, 0)
            records.append(
                {
                    "root": root,
                    "required_action": required_action,
                    "required_outcome_index": required_index,
                    "required_outcome_target": selected_target,
                    "mid_actions": actions,
                    "handoff_post_state": snapshot["post_state"],
                    "controller_state_loaded": snapshot["controller_state"],
                    "post_action": post_action,
                    "post_target": post_record["target"],
                }
            )
    if len(fanouts) != 1:
        raise BundleViolation("named nondeterministic bucket fan-out varies across Q0")
    fanout = next(iter(fanouts))
    return {
        "required_action": required_action,
        "q0_root_count": len(bundle.q0_roots),
        "fanout_per_root": fanout,
        "trace_count": len(records),
        "expected_trace_count": len(bundle.q0_roots) * fanout,
        "maximum_mid_steps": max(len(row["mid_actions"]) for row in records),
        "traces": records,
    }


def validate_required_actions_per_trace(
    traces: Sequence[Mapping[str, Any]],
    required_actions: Set[str],
) -> Mapping[str, Any]:
    """Require every registered lifecycle action exactly once in every trace."""
    if not traces or not required_actions:
        raise BundleViolation("exact per-trace lifecycle gate is empty")
    for row in traces:
        actions = row.get("mid_actions")
        if not isinstance(actions, list) or any(
            not isinstance(action, str) for action in actions
        ):
            raise BundleViolation("trace has no exact MID action sequence")
        missing = sorted(required_actions.difference(actions))
        repeated = sorted(
            action for action in required_actions if actions.count(action) != 1
        )
        if missing or repeated:
            raise BundleViolation(
                "registered lifecycle actions are not exact on trace "
                + str(row.get("root", ""))
            )
    return {
        "trace_count": len(traces),
        "required_actions": sorted(required_actions),
        "each_required_action_exactly_once": True,
    }


def cover_strategy_edges(bundle: ParsedBundle) -> Mapping[str, Any]:
    covered: Set[Tuple[str, str, int, str]] = set()
    reached_goals: Set[str] = set()
    loaded_states: Set[int] = set()
    post_events_after_handoff = 0
    for (source, action), outcomes in sorted(bundle.strategy.items()):
        for outcome in outcomes:
            runtime = AtomicHandoffRuntime(bundle)
            runtime.reset_mid(source)
            record = runtime.dispatch_mid(action, outcome.index)
            if record["target_configuration"] != outcome.target:
                raise BundleViolation("runtime selected the wrong strategy outcome")
            covered.add((source, action, outcome.index, outcome.target))
            if outcome.goal:
                reached_goals.add(outcome.target)
                snapshot = runtime.snapshot()
                loaded_states.add(int(snapshot["controller_state"]))
                post_action, _ = _first_post_bucket(
                    bundle, str(snapshot["post_state"])
                )
                runtime.dispatch_post(post_action, 0)
                post_events_after_handoff += 1
    expected = {
        (source, action, outcome.index, outcome.target)
        for (source, action), outcomes in bundle.strategy.items()
        for outcome in outcomes
    }
    if covered != expected:
        raise BundleViolation("strategy outcome coverage is incomplete")
    if reached_goals != set(bundle.handoffs):
        raise BundleViolation("not every handoff Goal was reached by edge coverage")
    return {
        "covered_strategy_outcome_edges": len(covered),
        "covered_goals": sorted(reached_goals),
        "loaded_controller_states": sorted(loaded_states),
        "post_events_immediately_after_handoff": post_events_after_handoff,
    }


def cover_post_edges(bundle: ParsedBundle) -> Mapping[str, int]:
    buckets = 0
    edges = 0
    for (source, action), outcomes in sorted(bundle.post_transitions.items()):
        buckets += 1
        for index, target in enumerate(outcomes):
            runtime = AtomicHandoffRuntime(bundle)
            runtime.reset_post(source)
            record = runtime.dispatch_post(action, index)
            if record["target"] != target:
                raise BundleViolation("runtime selected the wrong POST outcome")
            edges += 1
    return {"covered_post_buckets": buckets, "covered_post_outcome_edges": edges}


def negative_controls(bundle: ParsedBundle) -> Mapping[str, int]:
    all_actions = {
        action for _, action in bundle.strategy
    } | {action for _, action in bundle.post_transitions} | {"__unknown_event__"}
    disabled_mid = 0
    out_of_bucket = 0
    wrong_phase = 0
    disabled_post = 0
    for source in sorted(bundle.configurations):
        if bool(bundle.configurations[source]["goal"]):
            continue
        runtime = AtomicHandoffRuntime(bundle)
        runtime.reset_mid(source)
        enabled = {action for state, action in bundle.strategy if state == source}
        disabled = next(action for action in sorted(all_actions) if action not in enabled)
        try:
            runtime.dispatch_mid(disabled, 0)
        except BundleViolation:
            disabled_mid += 1
        else:
            raise BundleViolation("runtime accepted a strategy-external MID event")
        action, outcomes = _first_bucket(bundle, source)
        try:
            runtime.dispatch_mid(action, len(outcomes))
        except BundleViolation:
            out_of_bucket += 1
        else:
            raise BundleViolation("runtime accepted an out-of-bucket MID result")
        try:
            runtime.dispatch_post("__unknown_event__", 0)
        except BundleViolation:
            wrong_phase += 1
        else:
            raise BundleViolation("runtime exposed POST before handoff")
    for source in sorted(bundle.post_states):
        runtime = AtomicHandoffRuntime(bundle)
        runtime.reset_post(source)
        enabled = {action for state, action in bundle.post_transitions if state == source}
        disabled = next(action for action in sorted(all_actions) if action not in enabled)
        try:
            runtime.dispatch_post(disabled, 0)
        except BundleViolation:
            disabled_post += 1
        else:
            raise BundleViolation("runtime accepted a POST-external event")
    return {
        "disabled_mid_event_rejections": disabled_mid,
        "out_of_bucket_result_rejections": out_of_bucket,
        "pre_handoff_post_event_rejections": wrong_phase,
        "disabled_post_event_rejections": disabled_post,
    }


def deterministic_handoff_race(
    bundle: ParsedBundle, repetitions: int
) -> Mapping[str, int]:
    candidates = [
        (source, action, outcome)
        for (source, action), outcomes in bundle.strategy.items()
        for outcome in outcomes
        if outcome.goal
    ]
    if not candidates:
        raise BundleViolation("bundle has no strategy edge entering Goal")
    source, action, outcome = sorted(
        candidates, key=lambda row: (row[0], row[1], row[2].index)
    )[0]
    handoff = bundle.handoffs[outcome.target]
    post_action, _ = _first_post_bucket(bundle, handoff.post_state)
    completed = 0
    contender_accepted = 0
    snapshots_after = 0
    overlap_violations = 0
    partial_load_observations = 0
    for _ in range(repetitions):
        runtime = AtomicHandoffRuntime(bundle)
        runtime.reset_mid(source)
        goal_observed = threading.Event()
        release_handoff = threading.Event()
        contender_started = threading.Event()
        boundary_result: List[Any] = [None]
        contender_result: List[Any] = [None]

        def boundary_worker() -> None:
            try:
                boundary_result[0] = runtime.dispatch_mid(
                    action,
                    outcome.index,
                    goal_observed=goal_observed,
                    release_handoff=release_handoff,
                )
            except BaseException as error:
                boundary_result[0] = error

        def contender_worker() -> None:
            contender_started.set()
            try:
                contender_result[0] = runtime.dispatch_post(post_action, 0)
            except BaseException as error:
                contender_result[0] = error

        boundary = threading.Thread(target=boundary_worker, daemon=True)
        boundary.start()
        if not goal_observed.wait(timeout=10):
            raise HandoffExecutionUnavailable(
                "Goal was not observed at the race latch"
            )
        contender = threading.Thread(target=contender_worker, daemon=True)
        contender.start()
        if not contender_started.wait(timeout=10):
            raise HandoffExecutionUnavailable(
                "contender did not arrive at the handoff lock"
            )
        if not contender.is_alive():
            raise BundleViolation("contender crossed an incomplete handoff")
        release_handoff.set()
        boundary.join(timeout=10)
        contender.join(timeout=10)
        if boundary.is_alive() or contender.is_alive():
            raise HandoffExecutionUnavailable(
                "handoff race workers did not terminate"
            )
        if isinstance(boundary_result[0], BaseException):
            if isinstance(boundary_result[0], HandoffExecutionUnavailable):
                raise boundary_result[0]
            if isinstance(boundary_result[0], BundleViolation):
                raise boundary_result[0]
            raise RuntimeError(
                "internal boundary transaction failure"
            ) from boundary_result[0]
        if isinstance(contender_result[0], BaseException):
            if isinstance(contender_result[0], HandoffExecutionUnavailable):
                raise contender_result[0]
            if isinstance(contender_result[0], BundleViolation):
                raise contender_result[0]
            raise RuntimeError(
                "internal POST contender failure"
            ) from contender_result[0]
        completed += 1
        contender_accepted += 1
        snapshot = runtime.snapshot()
        snapshots_after += 1
        partial_load_observations += runtime.partial_load_observations
        if runtime.max_critical_occupancy != 1:
            overlap_violations += 1
        if snapshot["phase"] != "POST" or snapshot["controller_state"] is None:
            partial_load_observations += 1
    if overlap_violations or partial_load_observations:
        raise BundleViolation("handoff race exposed a partial or overlapping load")
    return {
        "repetitions": repetitions,
        "completed_atomic_handoffs": completed,
        "post_contenders_accepted_after_switch": contender_accepted,
        "post_handoff_snapshots": snapshots_after,
        "maximum_critical_occupancy": 1,
        "overlap_violations": overlap_violations,
        "partial_load_observations": partial_load_observations,
    }


def output_metric(text: str, key: str) -> int:
    import re

    match = re.search(
        r"(?m)^.*\[" + re.escape(key) + r"\]\s*:\s*([0-9]+)\s+", text
    )
    if match is None:
        raise ValueError("missing synthesis metric: " + key)
    return int(match.group(1))


def verify_synthesis_output(
    text: str, require_explicit_crosscheck: bool = True
) -> Mapping[str, int]:
    required = [
        "Decision [revised_decision] : realizable",
        "Atomic Link checker [revised_link_checker] : passed",
        "Internal certificate checker [revised_internal_certificate_check] : passed",
    ]
    required.append(
        "Independent explicit verification status "
        "[revised_independent_verification_status] : "
        + ("passed" if require_explicit_crosscheck else "not_run")
    )
    missing = [line for line in required if line not in text]
    if missing:
        raise ValueError("synthesis/check output lacks: " + " | ".join(missing))
    return {
        "q0": output_metric(text, "revised_initial_endpoint_embeddings"),
        "certificate_states": output_metric(text, "revised_certificate_states"),
        "rank": output_metric(text, "revised_worst_completion_rank"),
    }


def checksum_lines(paths: Iterable[Path], base: Path) -> bytes:
    rows = []
    for path in sorted(paths, key=lambda item: item.relative_to(base).as_posix()):
        rows.append("%s  %s" % (digest(path), path.relative_to(base).as_posix()))
    return ("\n".join(rows) + "\n").encode("utf-8")


def run_case(
    root: Path,
    output: Path,
    java: str,
    jar: Path,
    target: str,
    case: Mapping[str, Any],
    timeout_seconds: float,
    race_repetitions: int,
    java_heap: str,
    independent_state_limit: int,
    independent_query_limit: int,
) -> Mapping[str, Any]:
    case_id = str(case["id"])
    case_dir = output / "cases" / case_id
    case_dir.mkdir(parents=True)
    model = resolve_registered(root, str(case["model"]))
    require_hash(model, str(case["sha256"]), case_id)
    synthesis_output = case_dir / "synthesis-output.txt"
    transition_summary = case_dir / "linked-controller-summary.txt"
    bundle_path = case_dir / "atomic-handoff-bundle.json"
    require_explicit_crosscheck = bool(
        case.get("require_explicit_decision_crosscheck", False)
    )
    command = [
        java,
        "-Xmx" + java_heap,
        "-Dmtsa.evaluation.enabled=true",
        "-Dupdating.controller.evaluation.enabled=true",
        "-Dmtsa.revised.otf.solver=otf",
        "-Dmtsa.revised.otf.policyRestriction=full_fg",
        "-Dmtsa.otf.guidedStateLimit=0",
        "-Dmtsa.otf.guidedQueryLimit=0",
        "-Dmtsa.otf.lazyControllableBuckets=true",
        "-Dmtsa.otf.controllableActionOrder=endpoint_guided",
        "-Dmtsa.revised.otf.independentVerification="
        + ("true" if require_explicit_crosscheck else "false"),
        "-Dmtsa.revised.otf.independentVerificationMode=exhaustive",
        "-Dmtsa.revised.otf.independentStateLimit="
        + str(independent_state_limit),
        "-Dmtsa.revised.otf.independentQueryLimit="
        + str(independent_query_limit),
        "-cp",
        str(jar),
        "ltsa.updatingControllers.cli.SingleCompositionRunner",
        "--lts",
        str(model),
        "--target",
        target,
        "--output",
        str(synthesis_output),
        "--transitions",
        str(transition_summary),
        "--transition-output",
        "summary",
        "--deployment-output",
        str(bundle_path),
    ]
    started = time.monotonic_ns()
    try:
        completed = subprocess.run(
            command,
            cwd=str(root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as timeout:
        stdout = timeout.stdout or ""
        stderr = timeout.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", "replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", "replace")
        write_new(case_dir / "process-stdout.txt", stdout.encode("utf-8"))
        write_new(case_dir / "process-stderr.txt", stderr.encode("utf-8"))
        raise HandoffExecutionUnavailable(
            case_id + " synthesis timed out"
        ) from timeout
    wall_ns = time.monotonic_ns() - started
    write_new(case_dir / "process-stdout.txt", completed.stdout.encode("utf-8"))
    write_new(case_dir / "process-stderr.txt", completed.stderr.encode("utf-8"))
    if completed.returncode in {2, 3, 6, 7, 8}:
        raise BundleViolation(
            "%s synthesis/handoff contract failed with exit code %d"
            % (case_id, completed.returncode)
        )
    if completed.returncode in {4, 5, 9}:
        raise HandoffExecutionUnavailable(
            "%s synthesis was unavailable or inconclusive with exit code %d"
            % (case_id, completed.returncode)
        )
    if completed.returncode != 0:
        raise RuntimeError(
            "%s synthesis returned unexpected exit code %d"
            % (case_id, completed.returncode)
        )
    if (
        not synthesis_output.is_file()
        or not transition_summary.is_file()
        or not bundle_path.is_file()
    ):
        raise BundleViolation(
            case_id + " successful synthesis omitted a required handoff artifact"
        )
    synthesis_metrics = verify_synthesis_output(
        synthesis_output.read_text(encoding="utf-8"),
        require_explicit_crosscheck=require_explicit_crosscheck,
    )
    raw_bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    if not isinstance(raw_bundle, dict):
        raise ValueError("atomic handoff bundle is not an object")
    bundle = parse_bundle(raw_bundle)
    expected_q0 = case.get("expected_q0_roots")
    if expected_q0 is not None and (
        type(expected_q0) is not int or len(bundle.q0_roots) != expected_q0
    ):
        raise ValueError("bundle Q0 count differs from the registered exact value")
    expected_q0_entries = case.get("expected_q0_endpoint_entries")
    if expected_q0_entries is not None and (
        type(expected_q0_entries) is not int
        or bundle.q0_endpoint_entry_count != expected_q0_entries
    ):
        raise ValueError(
            "bundle old-endpoint entry count differs from the registered exact value"
        )
    if synthesis_metrics != {
        "q0": len(bundle.q0_roots),
        "certificate_states": len(bundle.configurations),
        "rank": bundle.maximum_rank,
    }:
        raise ValueError("bundle counts differ from synthesis metrics")

    required_actions = {str(action) for action in case["required_actions"]}
    strategy_actions = {action for _, action in bundle.strategy}
    if not required_actions.issubset(strategy_actions):
        raise ValueError("registered update actions are absent from the bundle")
    nondeterministic = str(case.get("required_nondeterministic_action", ""))
    expected_fanout = case.get("required_nondeterministic_outcomes_per_bucket")
    require_forks = case.get("require_q0_outcome_fork_completion", False)
    if type(require_forks) is not bool:
        raise ValueError("Q0 outcome-fork gate must be boolean")
    if require_forks and (
        not nondeterministic or type(expected_fanout) is not int
    ):
        raise ValueError("Q0 outcome-fork gate lacks an exact action contract")
    if expected_fanout is not None and not nondeterministic:
        raise ValueError("registered fan-out lacks a nondeterministic action")
    nondeterministic_targets = {
        outcome.target
        for (source, action), outcomes in bundle.strategy.items()
        if action == nondeterministic
        for outcome in outcomes
    }
    bucket_validation: Mapping[str, Any] = {"status": "not_required"}
    q0_outcome_forks: Mapping[str, Any] = {"status": "not_required"}
    if nondeterministic:
        if len(nondeterministic_targets) < 2:
            raise ValueError("registered nondeterministic event lacks multiple outcomes")
        if expected_fanout is not None:
            bucket_validation = validate_required_action_buckets(
                bundle, nondeterministic, expected_fanout
            )
            if require_forks:
                q0_outcome_forks = execute_q0_nondeterministic_forks(
                    bundle, nondeterministic
                )
                if (
                    q0_outcome_forks["fanout_per_root"] != expected_fanout
                    or q0_outcome_forks["trace_count"]
                    != q0_outcome_forks["expected_trace_count"]
                ):
                    raise ValueError("Q0 outcome-fork completion is incomplete")

    q0 = execute_q0_traces(bundle)
    exact_actions = case.get("require_actions_exactly_once_per_q0_trace", False)
    if type(exact_actions) is not bool:
        raise ValueError("exact per-Q0 action gate must be boolean")
    action_trace_validation: Mapping[str, Any] = {"status": "not_required"}
    if exact_actions:
        if not require_forks:
            raise ValueError("exact action gate requires the registered Q0 forks")
        q0_validation = validate_required_actions_per_trace(
            q0["traces"], required_actions
        )
        fork_validation = validate_required_actions_per_trace(
            q0_outcome_forks["traces"], required_actions
        )
        action_trace_validation = {
            "status": "PASS",
            "canonical_q0": q0_validation,
            "q0_outcome_forks": fork_validation,
        }
    strategy = cover_strategy_edges(bundle)
    post = cover_post_edges(bundle)
    negatives = negative_controls(bundle)
    race = deterministic_handoff_race(bundle, race_repetitions)
    return {
        "case_id": case_id,
        "status": "PASS",
        "model": str(case["model"]),
        "model_sha256": digest(model),
        "runtime_jar_sha256": digest(jar),
        "command": command,
        "synthesis_wall_ms": wall_ns / 1_000_000.0,
        "synthesis_metrics": synthesis_metrics,
        "explicit_decision_crosscheck": (
            "passed" if require_explicit_crosscheck else "not_run_by_protocol"
        ),
        "bundle_sha256": digest(bundle_path),
        "bundle_counts": {
            "q0_roots": len(bundle.q0_roots),
            "q0_endpoint_entries": bundle.q0_endpoint_entry_count,
            "certificate_states": len(bundle.configurations),
            "strategy_buckets": len(bundle.strategy),
            "strategy_outcome_edges": sum(
                len(outcomes) for outcomes in bundle.strategy.values()
            ),
            "goals": len(bundle.handoffs),
            "post_states": len(bundle.post_states),
            "post_buckets": len(bundle.post_transitions),
            "post_outcome_edges": sum(
                len(outcomes) for outcomes in bundle.post_transitions.values()
            ),
        },
        "required_actions": sorted(required_actions),
        "nondeterministic_action": nondeterministic,
        "nondeterministic_result_configurations": sorted(nondeterministic_targets),
        "required_action_bucket_validation": bucket_validation,
        "all_q0_execution": q0,
        "q0_required_action_outcome_completion": q0_outcome_forks,
        "required_actions_per_trace": action_trace_validation,
        "strategy_edge_coverage": strategy,
        "post_edge_coverage": post,
        "negative_controls": negatives,
        "atomic_handoff_race": race,
        "claim_boundary": (
            "The source-bound reference executor consumed the typed winning "
            "certificate and handoff map for this registered model; this is "
            "not evidence that an unrelated production runtime refines the model."
        ),
    }


def failure_case_record(case_id: str, error: BaseException) -> Mapping[str, Any]:
    """Normalize a failed handoff case without confusing absence with refutation."""

    exception_class = type(error).__name__
    if isinstance(error, HandoffExecutionUnavailable):
        failure_kind = "RESOURCE_OR_PROCESS_UNAVAILABLE"
        failure_basis = "isinstance:HandoffExecutionUnavailable"
        normalized_class = "HandoffExecutionUnavailable"
    elif isinstance(error, OSError):
        failure_kind = "RESOURCE_OR_PROCESS_UNAVAILABLE"
        failure_basis = "isinstance:OSError"
        normalized_class = "OSError"
    elif isinstance(error, BundleViolation):
        failure_kind = "SEMANTIC_OR_CERTIFICATE_GATE_FAILURE"
        failure_basis = "isinstance:BundleViolation"
        normalized_class = "BundleViolation"
    elif isinstance(error, ValueError):
        failure_kind = "SEMANTIC_OR_CERTIFICATE_GATE_FAILURE"
        failure_basis = "isinstance:ValueError"
        normalized_class = "ValueError"
    else:
        failure_kind = "INTERNAL_RUNNER_ERROR"
        failure_basis = "fallback:unclassified_exception"
        normalized_class = exception_class
    return {
        "case_id": case_id,
        "status": "FAIL",
        "failure_kind": failure_kind,
        "failure_exception_class": exception_class,
        "failure_classification_basis": failure_basis,
        "error": normalized_class + ": " + str(error),
        "explicit_decision_crosscheck": "not_completed",
        "bundle_counts": {
            "q0_roots": 0, "q0_endpoint_entries": 0,
            "certificate_states": 0, "strategy_buckets": 0,
            "strategy_outcome_edges": 0, "goals": 0,
            "post_states": 0, "post_buckets": 0,
            "post_outcome_edges": 0,
        },
        "all_q0_execution": {"trace_count": 0},
        "q0_required_action_outcome_completion": {"trace_count": 0},
        "required_action_bucket_validation": {"bucket_count": 0},
        "strategy_edge_coverage": {
            "covered_strategy_outcome_edges": 0,
            "post_events_immediately_after_handoff": 0,
        },
        "atomic_handoff_race": {
            "repetitions": 0,
            "partial_load_observations": 0,
            "overlap_violations": 0,
        },
    }


def main() -> int:
    args = arguments()
    root = repository_root()
    protocol_argument = args.protocol.absolute()
    if protocol_argument.is_symlink():
        raise ValueError("handoff protocol path is a symlink")
    protocol_path = protocol_argument.resolve()
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    if not isinstance(protocol, dict) or protocol.get("schema_version") != PROTOCOL_SCHEMA:
        raise ValueError("unsupported atomic-handoff protocol")
    if not bool(protocol.get("frozen_before_execution")):
        raise ValueError("protocol was not frozen before execution")
    output = resolve_prospective_output(
        root, str(protocol.get("registered_output", "")), args.output
    )
    if args.decision_campaign is not None:
        decision_campaign = args.decision_campaign.resolve()
        if output == decision_campaign or decision_campaign in output.parents:
            raise ValueError("handoff output must be outside the sealed decision campaign")
    preexecution_tree = resolve_registered(
        root, str(protocol["preexecution_gate"]["path"])
    ).parent
    if output == preexecution_tree or preexecution_tree in output.parents:
        raise ValueError("handoff output must be outside the sealed pre-execution tree")
    validate_preexecution_gate(
        protocol["preexecution_gate"],
        root,
        expected_caller_role="handoff_protocol",
        caller_path=protocol_argument,
    )
    preflight: Mapping[str, Any] | None = None
    if "semantic_preflight_summary" in protocol:
        preflight_registration = protocol["semantic_preflight_summary"]
        if not isinstance(preflight_registration, dict):
            raise ValueError("semantic preflight registration is not an object")
        preflight_path = resolve_registered(
            root, str(preflight_registration.get("path", ""))
        )
        require_hash(
            preflight_path,
            str(preflight_registration.get("sha256", "")),
            "semantic preflight summary",
        )
        loaded_preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
        if not isinstance(loaded_preflight, dict):
            raise ValueError("semantic preflight summary is not an object")
        preflight = loaded_preflight
        if (
            preflight.get("status") != "PASS"
            or preflight.get("solver_execution_permitted") is not True
        ):
            raise ValueError("semantic preflight does not permit handoff execution")
        tooling_registration = protocol.get("tooling_protocol")
        if not isinstance(tooling_registration, dict):
            raise ValueError("handoff protocol lacks its tooling registration")
        tooling_path = resolve_registered(
            root, str(tooling_registration.get("path", ""))
        )
        require_hash(
            tooling_path,
            str(tooling_registration.get("sha256", "")),
            "handoff tooling protocol",
        )
        tooling = json.loads(tooling_path.read_text(encoding="utf-8"))
        tooling_files = tooling.get("registered_files")
        if not isinstance(tooling_files, dict):
            raise ValueError("handoff tooling protocol lacks registered files")
        if not all((
            tooling.get("final_preflight")
            == {
                "path": str(preflight_path.relative_to(root)),
                "sha256": digest(preflight_path),
            },
            preflight.get("preflight_runner_v5", {}).get("sha256")
            == tooling_files.get("preflight_runner_v5", {}).get("sha256"),
            preflight.get("raw_lts_oracle_v5", {}).get("sha256")
            == tooling_files.get("raw_lts_oracle_v5", {}).get("sha256"),
        )):
            raise ValueError("handoff preflight differs from its registered tooling")
    jar = resolve_registered(root, str(protocol["runtime_jar"]))
    attestation = resolve_registered(root, str(protocol["build_attestation"]))
    runner = Path(__file__).resolve()
    attestation_validation = validate_registered_attestation(
        root, protocol, attestation
    )
    runtime_jar_sha256 = validate_registered_runtime(
        protocol, jar, attestation_validation
    )
    require_hash(runner, str(protocol["runner_sha256"]), "runner")
    cases = protocol.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("protocol contains no cases")
    protocol_revision = int(protocol.get("protocol_revision", 0))
    if protocol_revision >= 4:
        expected_preflight_schema = (
            "fse2027-prospective-ardrone-preflight-result-v5"
            if protocol_revision >= 6
            else "fse2027-prospective-ardrone-preflight-result-v3"
            if protocol_revision >= 5
            else "fse2027-prospective-ardrone-preflight-result-v2"
        )
        if (
            preflight is None
            or preflight.get("schema_version")
            != expected_preflight_schema
        ):
            raise ValueError("handoff revision requires its registered structural preflight")
        structural_rows = preflight.get("structural_rows")
        semantic_rows = preflight.get("semantic_gate", {}).get("analyses")
        if not isinstance(structural_rows, dict) or not isinstance(semantic_rows, dict):
            raise ValueError("structural preflight lacks exact model rows")
        minimum_roots = int(protocol["minimum_initial_roots"])
        minimum_classes = int(protocol["minimum_activation_language_classes"])
        identifiers: Set[str] = set()
        for case in cases:
            identifier = str(case.get("id", ""))
            if not identifier or identifier in identifiers:
                raise ValueError("handoff case identifier is empty or duplicated")
            identifiers.add(identifier)
            if identifier not in structural_rows or identifier not in semantic_rows:
                raise ValueError("handoff case is absent from structural preflight")
            if semantic_rows[identifier].get("model_sha256") != case.get("sha256"):
                raise ValueError("handoff model hash differs from structural preflight")
            row = structural_rows[identifier]
            if protocol_revision >= 7:
                expected_entries = case.get("expected_q0_endpoint_entries")
                if (
                    type(expected_entries) is not int
                    or expected_entries < int(case.get("expected_q0_roots", -1))
                ):
                    raise ValueError(
                        "handoff revision 7 requires an exact old-endpoint entry census"
                    )
            if protocol_revision >= 6:
                if row.get("java_action_fluent_propositions_persisted") is not True:
                    raise ValueError("handoff preflight omits Java action fluents")
                if row.get("physical_observer_keys") != [
                    "HaveUnblinkedRead", "event:fault", "event:land"
                ]:
                    raise ValueError("handoff preflight physical profile differs")
                if row.get("activation_domain_state_counts") != {
                    "P_NEW_READ_COMPLETION": {"0": 38, "1": 30, "E": 8},
                    "P_NO_FAULT": {"0": 64, "E": 12},
                }:
                    raise ValueError("handoff preflight activation domain differs")
                if row.get("activation_partial_domain_expected") is not True:
                    raise ValueError("handoff preflight partial activation is absent")
                if int(row.get("q0_endpoint_states", -1)) != int(
                    case.get("expected_q0_roots", -2)
                ):
                    raise ValueError("handoff exact Q0 registration differs from preflight")
            elif protocol_revision >= 5:
                if row.get("transient_event_propositions_persisted") is not False:
                    raise ValueError("handoff preflight retains a transient event proposition")
                if row.get("physical_observer_keys") != ["HaveUnblinkedRead"]:
                    raise ValueError("handoff preflight physical profile differs")
                if int(row.get("q0_endpoint_states", -1)) != int(
                    case.get("expected_q0_roots", -2)
                ):
                    raise ValueError("handoff exact Q0 registration differs from preflight")
            if int(row.get("q0_endpoint_states", -1)) < minimum_roots:
                raise ValueError("handoff case does not meet the registered Q0 gate")
            if int(row.get("activation_nonerror_language_class_count", -1)) < minimum_classes:
                raise ValueError("handoff case does not meet the activation-language gate")
            if not all((
                row.get("zload_contains_high") is True,
                row.get("zload_contains_reserve") is True,
                row.get("zload_excludes_fault") is True,
                row.get("raw_new_contains_fault") is True,
            )):
                raise ValueError("handoff case does not meet the loadability boundary")
    timeout_seconds = float(protocol["timeout_seconds_per_case"])
    race_repetitions = int(protocol["race_repetitions"])
    java_heap = str(protocol["java_heap"])
    independent_state_limit = int(protocol["independent_state_limit"])
    independent_query_limit = int(protocol["independent_query_limit"])
    if (
        java_heap != "12g"
        or independent_state_limit != 1_000_000
        or independent_query_limit != 10_000_000
    ):
        raise ValueError("unsupported registered handoff resource limits")
    target = str(protocol["target"])
    java = args.java.resolve()
    if not java.is_file() or java.is_symlink():
        raise ValueError("Java executable is missing or a symlink")
    registered_java = Path(str(protocol["java_executable"])).resolve()
    if java != registered_java:
        raise ValueError("Java executable differs from the registered absolute path")
    require_hash(java, str(protocol["java_executable_sha256"]), "Java executable")
    precondition = evaluate_decision_precondition(
        root, protocol, args.decision_campaign, runtime_jar_sha256
    )
    if output.exists():
        raise ValueError("output directory already exists")
    if not bool(precondition["eligible"]):
        output.mkdir(parents=True)
        skipped = {
            "schema_version": SUMMARY_SCHEMA,
            "status": "SKIPPED_BY_REGISTERED_PRECONDITION",
            "protocol": str(protocol_path.relative_to(root)),
            "protocol_sha256": digest(protocol_path),
            "runner_sha256": digest(runner),
            "runtime_jar_sha256": runtime_jar_sha256,
            "build_attestation_sha256": digest(attestation),
            "build_attestation_validation": attestation_validation,
            "environment_gate_status": "NOT_INVOKED_PRECONDITION",
            "decision_precondition": precondition,
            "environment": {
                "platform": platform.platform(),
                "python": platform.python_version(),
                "java": str(java),
                "java_executable_sha256": digest(java),
                "java_version_not_invoked": True,
            },
            "aggregate": {
                "cases": 0,
                "passed_cases": 0,
                "q0_entries": 0,
                "q0_roots": 0,
                "q0_complete_traces": 0,
                "q0_required_action_outcome_traces": 0,
                "strategy_outcome_edges": 0,
                "covered_strategy_outcome_edges": 0,
                "post_outcome_edges": 0,
                "atomic_handoff_races": 0,
                "partial_load_observations": 0,
                "overlap_violations": 0,
            },
            "cases": [],
            "claim_boundary": (
                "The registered positive winning-certificate precondition was "
                "not met. No synthesis or handoff JVM was launched and no "
                "handoff result is inferred."
            ),
        }
        write_new(output / "summary.json", canonical_json_bytes(skipped))
        write_new(
            output / "SHA256SUMS",
            checksum_lines([output / "summary.json"], output),
        )
        print(json.dumps({"status": skipped["status"]}, sort_keys=True))
        return 0
    output.mkdir(parents=True)
    java_version = ""
    java_version_sha256 = ""
    environment_gate_status = "PASS"
    environment_gate_error: BaseException | None = None
    try:
        probe = subprocess.run(
            [str(java), "-version"], stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, encoding="utf-8",
            errors="replace", check=False, timeout=30,
        )
        java_version = probe.stdout
        java_version_sha256 = hashlib.sha256(
            java_version.encode("utf-8")
        ).hexdigest()
        if (
            probe.returncode != 0
            or 'version "17.' not in java_version
            or java_version_sha256
            != str(protocol["java_version_output_sha256"])
        ):
            environment_gate_status = "INTEGRITY_ENVIRONMENT_DRIFT"
            environment_gate_error = RuntimeError(
                "registered Java version identity drift"
            )
    except (OSError, subprocess.TimeoutExpired) as error:
        environment_gate_status = "RESOURCE_OR_PROCESS_UNAVAILABLE"
        environment_gate_error = HandoffExecutionUnavailable(
            type(error).__name__ + ": " + str(error)
        )
    except Exception as error:
        environment_gate_status = "INTERNAL_RUNNER_ERROR"
        environment_gate_error = HandoffInternalRunnerError(
            type(error).__name__ + ": " + str(error)
        )

    if environment_gate_error is not None:
        case_id = str(cases[0].get("id", ""))
        case_dir = output / "cases" / case_id
        case_dir.mkdir(parents=True)
        failure = failure_case_record(case_id, environment_gate_error)
        write_new(
            case_dir / "terminal-error.txt",
            (str(failure["error"]) + "\n").encode("utf-8"),
        )
        aggregate = {
            "cases": 1,
            "passed_cases": 0,
            "explicitly_crosschecked_cases": 0,
            "q0_entries": 0,
            "q0_roots": 0,
            "certificate_states": 0,
            "strategy_buckets": 0,
            "strategy_outcome_edges": 0,
            "goals": 0,
            "post_states": 0,
            "post_outcome_edges": 0,
            "q0_complete_traces": 0,
            "q0_required_action_outcome_traces": 0,
            "required_action_nondeterministic_buckets": 0,
            "covered_strategy_outcome_edges": 0,
            "post_events_immediately_after_handoff": 0,
            "atomic_handoff_races": 0,
            "partial_load_observations": 0,
            "overlap_violations": 0,
        }
        summary = {
            "schema_version": SUMMARY_SCHEMA,
            "status": "FAIL",
            "protocol": str(protocol_path.relative_to(root)),
            "protocol_sha256": digest(protocol_path),
            "runner_sha256": digest(runner),
            "runtime_jar_sha256": runtime_jar_sha256,
            "build_attestation_sha256": digest(attestation),
            "build_attestation_validation": attestation_validation,
            "environment_gate_status": environment_gate_status,
            "environment": {
                "platform": platform.platform(),
                "python": platform.python_version(),
                "java": str(java),
                "java_executable_sha256": digest(java),
                "java_version_output": java_version,
                "java_version_output_sha256": java_version_sha256,
            },
            "decision_precondition": precondition,
            "aggregate": aggregate,
            "cases": [failure],
            "claim_boundary": (
                "No model synthesis or handoff validation was launched because "
                "the registered Java environment gate did not pass."
            ),
        }
        write_new(output / "summary.json", canonical_json_bytes(summary))
        evidence = [path for path in output.rglob("*") if path.is_file()]
        write_new(output / "SHA256SUMS", checksum_lines(evidence, output))
        print(json.dumps({"status": summary["status"]}, sort_keys=True))
        return 1

    results = []
    for case in cases:
        try:
            results.append(run_case(
                root,
                output,
                str(java),
                jar,
                target,
                case,
                timeout_seconds,
                race_repetitions,
                java_heap,
                independent_state_limit,
                independent_query_limit,
            ))
        except Exception as error:
            case_id = str(case.get("id", ""))
            case_dir = output / "cases" / case_id
            case_dir.mkdir(parents=True, exist_ok=True)
            failure = failure_case_record(case_id, error)
            error_path = case_dir / "terminal-error.txt"
            if not error_path.exists():
                write_new(
                    error_path,
                    (str(failure["error"]) + "\n").encode("utf-8"),
                )
            results.append(failure)

    aggregate = {
        "cases": len(results),
        "passed_cases": sum(row["status"] == "PASS" for row in results),
        "explicitly_crosschecked_cases": sum(
            row["explicit_decision_crosscheck"] == "passed" for row in results
        ),
        "q0_entries": sum(
            row["bundle_counts"]["q0_endpoint_entries"] for row in results
        ),
        "q0_roots": sum(row["bundle_counts"]["q0_roots"] for row in results),
        "certificate_states": sum(
            row["bundle_counts"]["certificate_states"] for row in results
        ),
        "strategy_buckets": sum(
            row["bundle_counts"]["strategy_buckets"] for row in results
        ),
        "strategy_outcome_edges": sum(
            row["bundle_counts"]["strategy_outcome_edges"] for row in results
        ),
        "goals": sum(row["bundle_counts"]["goals"] for row in results),
        "post_states": sum(
            row["bundle_counts"]["post_states"] for row in results
        ),
        "post_outcome_edges": sum(
            row["bundle_counts"]["post_outcome_edges"] for row in results
        ),
        "q0_complete_traces": sum(
            row["all_q0_execution"]["trace_count"] for row in results
        ),
        "q0_required_action_outcome_traces": sum(
            int(
                row["q0_required_action_outcome_completion"].get(
                    "trace_count", 0
                )
            )
            for row in results
        ),
        "required_action_nondeterministic_buckets": sum(
            int(row["required_action_bucket_validation"].get("bucket_count", 0))
            for row in results
        ),
        "covered_strategy_outcome_edges": sum(
            row["strategy_edge_coverage"]["covered_strategy_outcome_edges"]
            for row in results
        ),
        "post_events_immediately_after_handoff": sum(
            row["strategy_edge_coverage"]["post_events_immediately_after_handoff"]
            for row in results
        ),
        "atomic_handoff_races": sum(
            row["atomic_handoff_race"]["repetitions"] for row in results
        ),
        "partial_load_observations": sum(
            row["atomic_handoff_race"]["partial_load_observations"]
            for row in results
        ),
        "overlap_violations": sum(
            row["atomic_handoff_race"]["overlap_violations"] for row in results
        ),
    }
    aggregate_pass = aggregate["passed_cases"] == len(results)
    if aggregate["covered_strategy_outcome_edges"] != aggregate[
        "strategy_outcome_edges"
    ]:
        aggregate_pass = False
    if aggregate["partial_load_observations"] or aggregate["overlap_violations"]:
        aggregate_pass = False

    summary = {
        "schema_version": SUMMARY_SCHEMA,
        "status": "PASS" if aggregate_pass else "FAIL",
        "protocol": str(protocol_path.relative_to(root)),
        "protocol_sha256": digest(protocol_path),
        "runner_sha256": digest(runner),
        "runtime_jar_sha256": digest(jar),
        "build_attestation_sha256": digest(attestation),
        "build_attestation_validation": attestation_validation,
        "environment_gate_status": "PASS",
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "java": str(java),
            "java_executable_sha256": digest(java),
            "java_version_output": java_version,
            "java_version_output_sha256": java_version_sha256,
        },
        "decision_precondition": precondition,
        "runtime_parameters": {
            "java_heap": java_heap,
            "timeout_seconds_per_case": timeout_seconds,
            "independent_state_limit": independent_state_limit,
            "independent_query_limit": independent_query_limit,
            "race_repetitions": race_repetitions,
        },
        "population_claim": protocol["population_claim"],
        "aggregate": aggregate,
        "cases": results,
        "claim_boundary": (
            "PASS establishes executable consumption of the registered typed "
            "FG-DUCS certificates through atomic controller-state handoff and "
            "POST execution. It is not a production-system validation or a "
            "held-out application study."
        ),
    }
    write_new(output / "summary.json", canonical_json_bytes(summary))
    evidence = [path for path in output.rglob("*") if path.is_file()]
    write_new(output / "SHA256SUMS", checksum_lines(evidence, output))
    print(json.dumps(aggregate, ensure_ascii=False, sort_keys=True))
    return 0 if aggregate_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
