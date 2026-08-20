#!/usr/bin/env python3
"""Bounded strong reachability synthesis over an explicit callback game.

This module deliberately knows nothing about MTSA, FG-DUCS adapters, or any
historical certificate format.  A caller supplies typed states and actions,
complete candidate/Post callbacks, Safe/Goal predicates, and canonical JSON
payloads.  The result is either a retained strong-rank certificate or an
explicitly inconclusive outcome.  Resource or rank bounds are never converted
to a losing-game claim.
"""

from __future__ import annotations

import json
import math
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Generic, Hashable, Iterable, Mapping, Protocol, TypeVar


StateT = TypeVar("StateT", bound=Hashable)
ActionT = TypeVar("ActionT", bound=Hashable)


class StrongGame(Protocol[StateT, ActionT]):
    """Conclusion-free finite-game interface used by the rank engine."""

    def roots(self) -> Iterable[StateT]: ...

    def safe(self, state: StateT) -> bool: ...

    def goal(self, state: StateT) -> bool: ...

    def candidates(self, state: StateT) -> Iterable[ActionT]: ...

    def post(self, state: StateT, action: ActionT) -> Iterable[StateT]: ...

    def controllable(self, action: ActionT) -> bool: ...

    def state_payload(self, state: StateT) -> Mapping[str, Any]: ...

    def action_payload(self, action: ActionT) -> Mapping[str, Any]: ...

    def action_order_key(self, state: StateT,
                         action: ActionT) -> tuple[int, str]: ...


def canonical_json(value: Any) -> str:
    """Return the single accepted canonical JSON spelling for an object."""
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as error:
        raise ValueError("payload is not canonical-JSON serializable") from error


@dataclass(frozen=True)
class SynthesisLimits:
    max_rank: int = 32
    max_states: int = 2_000_000
    max_candidate_buckets: int = 20_000_000
    max_outcomes: int = 40_000_000
    timeout_seconds: float = 600.0

    def __post_init__(self) -> None:
        if type(self.max_rank) is not int or not 0 <= self.max_rank <= 32:
            raise ValueError("max_rank must be an exact integer in [0, 32]")
        for name in ("max_states", "max_candidate_buckets", "max_outcomes"):
            value = getattr(self, name)
            if type(value) is not int or value < 1:
                raise ValueError(f"{name} must be a positive exact integer")
        if type(self.timeout_seconds) not in {int, float} \
                or isinstance(self.timeout_seconds, bool) \
                or not math.isfinite(self.timeout_seconds) \
                or self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")


@dataclass(frozen=True)
class ExplorationCounts:
    states: int
    candidate_buckets: int
    enabled_candidate_buckets: int
    outcomes: int
    unsafe_states: int
    non_goal_deadlocks: int

    def to_json(self) -> dict[str, int]:
        return {
            "states": self.states,
            "candidate_buckets": self.candidate_buckets,
            "enabled_candidate_buckets": self.enabled_candidate_buckets,
            "outcomes": self.outcomes,
            "unsafe_states": self.unsafe_states,
            "non_goal_deadlocks": self.non_goal_deadlocks,
        }


@dataclass(frozen=True)
class CandidateBucket:
    source_key: str
    action_key: str
    action_payload: Mapping[str, Any]
    controllable: bool
    target_keys: tuple[str, ...]

    def to_json(self) -> dict[str, Any]:
        return {
            "source_key": self.source_key,
            "action_key": self.action_key,
            "action": dict(self.action_payload),
            "controllable": self.controllable,
            "target_keys": list(self.target_keys),
        }


@dataclass(frozen=True)
class RetainedState:
    key: str
    payload: Mapping[str, Any]
    rank: int
    safe: bool
    goal: bool

    def to_json(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "payload": dict(self.payload),
            "rank": self.rank,
            "safe": self.safe,
            "goal": self.goal,
        }


@dataclass(frozen=True)
class StrategyBucket:
    source_key: str
    action_key: str
    action_payload: Mapping[str, Any]
    target_keys: tuple[str, ...]

    def to_json(self) -> dict[str, Any]:
        return {
            "source_key": self.source_key,
            "action_key": self.action_key,
            "action": dict(self.action_payload),
            "target_keys": list(self.target_keys),
        }


@dataclass(frozen=True)
class StrongRankCertificate:
    roots: tuple[str, ...]
    states: tuple[RetainedState, ...]
    candidate_buckets: tuple[CandidateBucket, ...]
    strategy_buckets: tuple[StrategyBucket, ...]
    max_rank: int
    exploration: ExplorationCounts

    def to_json(self) -> dict[str, Any]:
        return {
            "schema_version": "strong-rank-certificate-core-v1",
            "root_state_keys": list(self.roots),
            "states": [state.to_json() for state in self.states],
            "candidate_buckets": [bucket.to_json()
                                  for bucket in self.candidate_buckets],
            "strategy_buckets": [bucket.to_json()
                                 for bucket in self.strategy_buckets],
            "max_rank": self.max_rank,
            "exploration": self.exploration.to_json(),
        }


@dataclass(frozen=True)
class SynthesisResult:
    status: str
    reason: str
    certificate: StrongRankCertificate | None
    exploration: ExplorationCounts
    elapsed_seconds: float

    @property
    def is_win(self) -> bool:
        return self.status == "SUCCESS_WIN"

    def to_json(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reason": self.reason,
            "certificate": (None if self.certificate is None
                            else self.certificate.to_json()),
            "exploration": self.exploration.to_json(),
            "elapsed_seconds": self.elapsed_seconds,
            "loss_claimed": False,
        }


class _Incomplete(RuntimeError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _empty_counts() -> ExplorationCounts:
    return ExplorationCounts(0, 0, 0, 0, 0, 0)


def synthesize_strong_rank(
    game: StrongGame[StateT, ActionT],
    limits: SynthesisLimits = SynthesisLimits(),
) -> SynthesisResult:
    """Synthesize a bounded strong WIN certificate.

    A depth-indexed memoized proof search admits only lower-rank targets.  It
    queries every uncontrollable bucket, then tries controllable buckets in
    canonical priority order until one proves the current depth.  It does not
    recursively admit unselected controllable outcomes.  After every root has
    a minimum rank, the retained strategy domain is extracted and *all*
    candidate/Post buckets are serialized for each retained source.  Failure
    to finish for any resource reason, including ``MemoryError``, is reported
    as ``INCONCLUSIVE`` and never as LOSS.
    """
    started = time.monotonic()
    engine: _Engine[StateT, ActionT] | None = None
    try:
        engine = _Engine(game, limits, started)
        certificate, reason = engine.run()
        elapsed = time.monotonic() - started
        if certificate is None:
            return SynthesisResult(
                "INCONCLUSIVE", reason, None, engine.counts(), elapsed)
        return SynthesisResult(
            "SUCCESS_WIN", "ALL_ROOTS_STRONGLY_REACH_QUIET_GOAL",
            certificate, engine.counts(), elapsed)
    except _Incomplete as error:
        counts = engine.counts() if engine is not None else _empty_counts()
        return SynthesisResult(
            "INCONCLUSIVE", error.reason, None, counts,
            time.monotonic() - started)
    except MemoryError:
        counts = engine.counts() if engine is not None else _empty_counts()
        return SynthesisResult(
            "INCONCLUSIVE", "MEMORY_EXHAUSTED", None, counts,
            time.monotonic() - started)


def _check_deadline(started: float, limits: SynthesisLimits) -> None:
    if time.monotonic() - started > limits.timeout_seconds:
        raise _Incomplete("TIMEOUT")


class _Engine(Generic[StateT, ActionT]):
    def __init__(self, game: StrongGame[StateT, ActionT],
                 limits: SynthesisLimits, started: float) -> None:
        self.game = game
        self.limits = limits
        self.started = started
        # Search is deliberately typed and payload-free.  Canonical JSON keys,
        # action payloads, and complete candidate buckets are constructed only
        # after the bounded proof has found the retained strategy domain.
        self.known_states: set[StateT] = set()
        self.failed_through: dict[StateT, int] = {}
        self.success_depth: dict[StateT, int] = {}
        self.selected: dict[StateT, tuple[ActionT, ...]] = {}
        self._bucket_count = 0
        self._enabled_count = 0
        self._outcome_count = 0
        self._unsafe_count = 0
        self._deadlocks: set[StateT] = set()

    def counts(self) -> ExplorationCounts:
        return ExplorationCounts(
            states=len(self.known_states),
            candidate_buckets=self._bucket_count,
            enabled_candidate_buckets=self._enabled_count,
            outcomes=self._outcome_count,
            unsafe_states=self._unsafe_count,
            non_goal_deadlocks=len(self._deadlocks),
        )

    def _deadline(self) -> None:
        _check_deadline(self.started, self.limits)

    def _register(self, state: StateT) -> None:
        if state in self.known_states:
            return
        self._deadline()
        if len(self.known_states) >= self.limits.max_states:
            raise _Incomplete("STATE_LIMIT")
        safe, goal = self._classification(state)
        self.known_states.add(state)
        self._unsafe_count += int(not safe)
        if goal:
            self.success_depth[state] = 0
            self.selected[state] = ()

    def _classification(self, state: StateT) -> tuple[bool, bool]:
        safe = self.game.safe(state)
        goal = self.game.goal(state)
        if type(safe) is not bool or type(goal) is not bool:
            raise ValueError("Safe/Goal callbacks must return exact Booleans")
        if goal and not safe:
            raise ValueError("Goal is not a subset of Safe")
        return safe, goal

    def _lower_bound(self, state: StateT) -> int:
        callback = getattr(self.game, "rank_lower_bound", None)
        if callback is None:
            return 0
        value = callback(state)
        if type(value) is not int or value < 0:
            raise ValueError("rank lower bound must be a nonnegative exact integer")
        return value

    def _actions(self, state: StateT) -> tuple[
            tuple[ActionT, bool, tuple[int, str]], ...]:
        rows: list[tuple[ActionT, bool, tuple[int, str]]] = []
        seen: set[ActionT] = set()
        for action in self.game.candidates(state):
            if action in seen:
                raise ValueError("candidate action is duplicated")
            seen.add(action)
            controllable = self.game.controllable(action)
            if type(controllable) is not bool:
                raise ValueError("controllability callback is not Boolean")
            order_key = self.game.action_order_key(state, action)
            if (type(order_key) is not tuple or len(order_key) != 2
                    or type(order_key[0]) is not int
                    or type(order_key[1]) is not str):
                raise ValueError("action order key must be (exact int, text)")
            rows.append((action, controllable, order_key))
        return tuple(sorted(rows, key=lambda row: row[2]))

    def _post(self, state: StateT, action: ActionT) -> tuple[StateT, ...]:
        self._deadline()
        if self._bucket_count >= self.limits.max_candidate_buckets:
            raise _Incomplete("CANDIDATE_BUCKET_LIMIT")
        targets: list[StateT] = []
        seen: set[StateT] = set()
        for target in self.game.post(state, action):
            if target in seen:
                continue
            seen.add(target)
            self._register(target)
            targets.append(target)
        if self._outcome_count + len(targets) > self.limits.max_outcomes:
            raise _Incomplete("OUTCOME_LIMIT")
        self._bucket_count += 1
        self._outcome_count += len(targets)
        self._enabled_count += int(bool(targets))
        return tuple(targets)

    def _prove(self, state: StateT, depth: int) -> bool:
        failed = self.failed_through.get(state, -1)
        if depth <= failed:
            return False
        success = self.success_depth.get(state)
        if success is not None and success <= depth:
            return True
        self._deadline()
        safe, goal = self._classification(state)
        if not safe:
            self.failed_through[state] = max(failed, depth)
            return False
        if goal:
            self.success_depth[state] = 0
            self.selected[state] = ()
            return True
        if depth < self._lower_bound(state):
            self.failed_through[state] = max(failed, depth)
            return False
        if depth == 0:
            self.failed_through[state] = max(failed, 0)
            return False

        actions = self._actions(state)
        enabled_uc: list[tuple[ActionT, tuple[StateT, ...]]] = []
        for action, controllable, _order in actions:
            if not controllable:
                targets = self._post(state, action)
                if targets:
                    enabled_uc.append((action, targets))
        if enabled_uc:
            success = all(
                self._prove(target, depth - 1)
                for _action, targets in enabled_uc for target in targets
            )
            if success:
                self.success_depth[state] = depth
                self.selected[state] = tuple(
                    action for action, _targets in enabled_uc)
            else:
                self.failed_through[state] = max(failed, depth)
            return success

        any_enabled = False
        for action, controllable, _order in actions:
            if not controllable:
                continue
            targets = self._post(state, action)
            if not targets:
                continue
            any_enabled = True
            if all(self._prove(target, depth - 1) for target in targets):
                self.success_depth[state] = depth
                self.selected[state] = (action,)
                return True
        if not any_enabled:
            self._deadlocks.add(state)
        self.failed_through[state] = max(failed, depth)
        return False

    def _minimum_rank(self, state: StateT, upper: int) -> int | None:
        for depth in range(upper + 1):
            if self._prove(state, depth):
                return depth
        return None

    def run(self) -> tuple[StrongRankCertificate | None, str]:
        roots_list: list[StateT] = []
        root_seen: set[StateT] = set()
        for state in self.game.roots():
            if state not in root_seen:
                root_seen.add(state)
                self._register(state)
                roots_list.append(state)
        roots = tuple(roots_list)
        if not roots:
            raise ValueError("game has no roots")
        root_ranks: dict[StateT, int] = {}
        for root in roots:
            rank = self._minimum_rank(root, self.limits.max_rank)
            if rank is None:
                return None, "ROOT_NOT_PROVED_WIN_WITHIN_RANK_BOUND"
            root_ranks[root] = rank

        retained_ranks = dict(root_ranks)
        retained: set[StateT] = set(roots)
        queue = deque(roots)
        while queue:
            source = queue.popleft()
            source_rank = retained_ranks[source]
            _safe, goal = self._classification(source)
            if goal:
                continue
            actions = self.selected.get(source, ())
            if not actions:
                raise AssertionError("proved non-Goal has no strategy")
            for action in actions:
                for target in self._post(source, action):
                    target_rank = self._minimum_rank(target, source_rank - 1)
                    if target_rank is None:
                        raise AssertionError("strategy target lacks decreasing rank")
                    old_rank = retained_ranks.get(target)
                    if old_rank is None or target_rank < old_rank:
                        retained_ranks[target] = target_rank
                        queue.append(target)
                    retained.add(target)

        # Recompute exact closure after rank improvements.  This drops states
        # reachable only through an obsolete higher-rank strategy.
        exact_retained: set[StateT] = set(roots)
        queue = deque(roots)
        while queue:
            source = queue.popleft()
            _safe, goal = self._classification(source)
            if goal:
                continue
            for action in self.selected.get(source, ()):
                for target in self._post(source, action):
                    if target not in exact_retained:
                        exact_retained.add(target)
                        queue.append(target)
        retained = exact_retained

        key_by_state: dict[StateT, str] = {}
        state_by_key: dict[str, StateT] = {}

        def state_key(state: StateT) -> str:
            cached = key_by_state.get(state)
            if cached is not None:
                return cached
            key = canonical_json(dict(self.game.state_payload(state)))
            previous = state_by_key.get(key)
            if previous is not None and previous != state:
                raise ValueError("two distinct typed states share one payload key")
            key_by_state[state] = key
            state_by_key[key] = state
            return key

        retained_order = sorted(retained, key=state_key)
        retained_keys = {state_key(state) for state in retained_order}

        candidate_rows: list[
            tuple[StateT, ActionT, CandidateBucket]
        ] = []
        candidates_by_typed: dict[tuple[StateT, ActionT], CandidateBucket] = {}
        # Completeness is required only for retained source states.  Unselected
        # targets receive semantic keys but are never recursively admitted.
        for source in retained_order:
            action_keys: set[str] = set()
            any_enabled = False
            for action, controllable, _order in self._actions(source):
                action_payload = dict(self.game.action_payload(action))
                action_key = canonical_json(action_payload)
                if action_key in action_keys:
                    raise ValueError("candidate action payload is duplicated")
                action_keys.add(action_key)
                targets = self._post(source, action)
                any_enabled = any_enabled or bool(targets)
                bucket = CandidateBucket(
                    state_key(source), action_key, action_payload,
                    controllable,
                    tuple(sorted({state_key(target) for target in targets})),
                )
                candidate_rows.append((source, action, bucket))
                candidates_by_typed[(source, action)] = bucket
            _safe, goal = self._classification(source)
            if not goal and not any_enabled:
                self._deadlocks.add(source)

        states = tuple(
            RetainedState(
                state_key(state),
                dict(self.game.state_payload(state)),
                retained_ranks[state],
                self._classification(state)[0],
                self._classification(state)[1],
            )
            for state in retained_order
        )
        candidate_buckets = tuple(
            bucket for _source, _action, bucket in candidate_rows
        )
        strategy_buckets = tuple(
            StrategyBucket(
                state_key(source),
                candidates_by_typed[(source, action)].action_key,
                candidates_by_typed[(source, action)].action_payload,
                candidates_by_typed[(source, action)].target_keys,
            )
            for source in retained_order
            for action in self.selected.get(source, ())
        )
        require_strategy_closed = all(
            set(bucket.target_keys) <= retained_keys
            for bucket in strategy_buckets)
        if not require_strategy_closed:
            raise AssertionError("strategy serialization leaves retained domain")
        certificate = StrongRankCertificate(
            tuple(sorted(state_key(root) for root in roots)),
            states,
            candidate_buckets,
            strategy_buckets,
            max(retained_ranks.values()),
            self.counts(),
        )
        return certificate, ""
