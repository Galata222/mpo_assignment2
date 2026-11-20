"""Baseline solvers: Blind Random Sampling and Constructive Randomized Walk.

Both variants pass every candidate through evaluate_candidate(); incomplete
walks are strictly rejected without repair (Assignment 2 §3).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Set, Tuple

from .model import (
    DeparturesIndex,
    EvaluationResult,
    Instance,
    Leg,
    ValidLegsIndex,
    evaluate_candidate,
)


@dataclass
class RolloutRecord:
    """Single rollout outcome for feasibility statistics."""

    legs: Tuple[Leg, ...]
    result: EvaluationResult
    reason: str  # e.g. 'feasible', 'dead_end', 'k_max', 'blind_sample'


@dataclass
class BaselineStats:
    """Aggregated feasibility / objective statistics."""

    total_rollouts: int = 0
    feasible_count: int = 0
    records: List[RolloutRecord] = field(default_factory=list)
    best: Optional[EvaluationResult] = None
    best_legs: Optional[Tuple[Leg, ...]] = None

    @property
    def feasibility_rate(self) -> float:
        if self.total_rollouts == 0:
            return 0.0
        return self.feasible_count / self.total_rollouts

    def register(self, legs: Sequence[Leg], result: EvaluationResult, reason: str) -> None:
        self.total_rollouts += 1
        rec = RolloutRecord(tuple(legs), result, reason)
        self.records.append(rec)
        if result.is_feasible:
            self.feasible_count += 1
            if self.best is None or (
                result.comparison is not None
                and self.best.comparison is not None
                and result.comparison < self.best.comparison
            ):
                self.best = result
                self.best_legs = tuple(legs)


def blind_random_sample(
    instance: Instance,
    all_legs: Sequence[Leg],
    valid_legs: ValidLegsIndex,
    rng: random.Random,
    *,
    k_choices: Sequence[int] = (1, 2, 3),
) -> Tuple[List[Leg], EvaluationResult]:
    """Diagnostic baseline: sample k ∈ {1,2,3} legs uniformly from J.

    Demonstrates near-0% feasibility under tight temporal/topological coupling.
    """
    if not all_legs:
        empty = evaluate_candidate([], instance, valid_legs)
        return [], empty
    k = rng.choice(list(k_choices))
    k = min(k, len(all_legs))
    legs = list(rng.sample(list(all_legs), k))
    result = evaluate_candidate(legs, instance, valid_legs)
    return legs, result


def run_blind_random(
    instance: Instance,
    all_legs: Sequence[Leg],
    valid_legs: ValidLegsIndex,
    *,
    n_rollouts: int = 200,
    seed: int = 42,
    k_choices: Sequence[int] = (1, 2, 3),
) -> BaselineStats:
    """Execute Blind Random Sampling for ``n_rollouts`` trials."""
    rng = random.Random(seed)
    stats = BaselineStats()
    for _ in range(n_rollouts):
        legs, result = blind_random_sample(
            instance, all_legs, valid_legs, rng, k_choices=k_choices
        )
        stats.register(legs, result, "blind_sample")
    return stats


def _eligible_next(
    current: Leg,
    visited: Set[str],
    instance: Instance,
    departures_from: DeparturesIndex,
) -> List[Leg]:
    """Filter outgoing legs satisfying transfer, train-change, and acyclicity."""
    key = (instance.day, current.destination)
    candidates = departures_from.get(key, [])
    eligible: List[Leg] = []
    earliest = current.arrival + instance.tau_min
    for leg in candidates:
        if leg.train_id == current.train_id:
            continue
        if leg.departure < earliest:
            continue
        if leg.destination in visited:
            continue
        eligible.append(leg)
    return eligible


def constructive_walk(
    instance: Instance,
    departures_from: DeparturesIndex,
    valid_legs: ValidLegsIndex,
    rng: random.Random,
) -> Tuple[List[Leg], EvaluationResult, str]:
    """One Constructive Randomized Walk from s toward z.

    Returns (legs, evaluation, termination_reason) where reason ∈
    {'feasible', 'dead_end', 'k_max', 'no_start'}.
    Incomplete walks are still passed to evaluate_candidate() and rejected.
    """
    start_key = (instance.day, instance.origin)
    starters = [
        lg
        for lg in departures_from.get(start_key, [])
        if instance.t0 <= lg.departure <= instance.t0 + instance.H
    ]
    if not starters:
        result = evaluate_candidate([], instance, valid_legs)
        return [], result, "no_start"

    first = rng.choice(starters)
    route: List[Leg] = [first]
    visited: Set[str] = {first.origin, first.destination}

    if first.destination == instance.destination:
        result = evaluate_candidate(route, instance, valid_legs)
        return route, result, "feasible" if result.is_feasible else "rejected"

    while len(route) < instance.k_max:
        current = route[-1]
        options = _eligible_next(current, visited, instance, departures_from)
        if not options:
            result = evaluate_candidate(route, instance, valid_legs)
            return route, result, "dead_end"

        nxt = rng.choice(options)
        route.append(nxt)
        visited.add(nxt.destination)

        if nxt.destination == instance.destination:
            result = evaluate_candidate(route, instance, valid_legs)
            return route, result, "feasible" if result.is_feasible else "rejected"

    result = evaluate_candidate(route, instance, valid_legs)
    return route, result, "k_max"


def run_constructive_walk(
    instance: Instance,
    departures_from: DeparturesIndex,
    valid_legs: ValidLegsIndex,
    *,
    n_rollouts: int = 200,
    seed: int = 42,
) -> BaselineStats:
    """Execute Constructive Randomized Walk for ``n_rollouts`` trials."""
    rng = random.Random(seed)
    stats = BaselineStats()
    for _ in range(n_rollouts):
        legs, result, reason = constructive_walk(
            instance, departures_from, valid_legs, rng
        )
        stats.register(legs, result, reason)
    return stats
