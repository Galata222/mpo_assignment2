"""Candidate representation, O(k) constraint validation, and scalar objective.

Implements the flat indexed formulation from Assignment 2:
  x = (l_1, ..., l_k),  l_i = (id_i, u_i, v_i, d_i, a_i)
  f(x) = T(x) + λ · N(x),  T(x) = a_k − d_1,  N(x) = k − 1
"""

from __future__ import annotations

from typing import Dict, List, NamedTuple, Optional, Sequence, Set, Tuple


class Leg(NamedTuple):
    """Direct service segment between two stations on the same train."""

    train_id: str
    origin: str
    destination: str
    departure: int  # minutes since 00:00 of day D
    arrival: int  # minutes since 00:00 of day D (may exceed 1440)


class Instance(NamedTuple):
    """Query parameters for a single origin–destination search."""

    day: str
    origin: str  # s
    destination: str  # z
    t0: int  # earliest acceptable first departure
    H: int = 120  # departure window length [min]
    tau_min: int = 5  # minimum transfer buffer [min]
    lam: float = 15.0  # transfer penalty λ [min]
    k_max: int = 6  # maximum legs in a constructive walk


class EvaluationResult(NamedTuple):
    """Outcome of evaluate_candidate."""

    is_feasible: bool
    violations: Tuple[str, ...]
    T: Optional[int]
    N: Optional[int]
    f: Optional[float]
    a_k: Optional[int]
    d_1: Optional[int]
    comparison: Optional[Tuple[float, int, int]]


# valid_legs key: (day, train_id, origin, destination, departure) -> arrival
ValidLegsIndex = Dict[Tuple[str, str, str, str, int], int]
# departures_from key: (day, station) -> sorted list of Leg
DeparturesIndex = Dict[Tuple[str, str], List[Leg]]


def compute_objective(
    legs: Sequence[Leg],
    lam: float = 15.0,
) -> Tuple[int, int, float, Tuple[float, int, int]]:
    """Return (T, N, f, comparison_tuple) for a feasible route.

    Tie-break order: smaller f, then earlier a_k, then earlier d_1.
    """
    if not legs:
        raise ValueError("Cannot compute objective for an empty route.")
    d1 = legs[0].departure
    ak = legs[-1].arrival
    T = ak - d1
    N = len(legs) - 1
    f = float(T) + lam * float(N)
    return T, N, f, (f, ak, d1)


def evaluate_candidate(
    legs: Sequence[Leg],
    instance: Instance,
    valid_legs: ValidLegsIndex,
    *,
    check_acyclicity: bool = True,
) -> EvaluationResult:
    """Validate route x in O(k) and compute f(x) when feasible.

    Constraint checklist (Assignment 2 §2):
      1. Non-empty: k ≥ 1
      2. Endpoints: u_1 = s, v_k = z
      3. First-departure window: t_0 ≤ d_1 ≤ t_0 + H
      4. Leg validity & positive duration via valid_legs index
      5. Station continuity & distinct trains between consecutive legs
      6. Minimum transfer buffer: d_{i+1} − a_i ≥ τ_min
      7. Acyclicity: no revisited station
    """
    violations: List[str] = []
    k = len(legs)

    # 1. Non-empty
    if k < 1:
        violations.append("empty_route: k < 1")
        return EvaluationResult(
            False, tuple(violations), None, None, None, None, None, None
        )

    # 2. Endpoints
    if legs[0].origin != instance.origin:
        violations.append(
            f"endpoint_origin: u_1={legs[0].origin!r} ≠ s={instance.origin!r}"
        )
    if legs[-1].destination != instance.destination:
        violations.append(
            f"endpoint_destination: v_k={legs[-1].destination!r} ≠ z={instance.destination!r}"
        )

    # 3. First-departure window
    d1 = legs[0].departure
    if not (instance.t0 <= d1 <= instance.t0 + instance.H):
        violations.append(
            f"departure_window: d_1={d1} ∉ [{instance.t0}, {instance.t0 + instance.H}]"
        )

    # 7. Acyclicity tracker (stations boarded / alighted)
    visited: Set[str] = {legs[0].origin}

    for i, leg in enumerate(legs):
        # 4. Leg validity & positive duration
        key = (instance.day, leg.train_id, leg.origin, leg.destination, leg.departure)
        expected_arrival = valid_legs.get(key)
        if expected_arrival is None:
            violations.append(
                f"invalid_leg[{i}]: ({leg.train_id}, {leg.origin}→{leg.destination}, "
                f"d={leg.departure}) ∉ J"
            )
        elif expected_arrival != leg.arrival:
            violations.append(
                f"arrival_mismatch[{i}]: a={leg.arrival} ≠ indexed {expected_arrival}"
            )
        if leg.arrival <= leg.departure:
            violations.append(
                f"nonpositive_duration[{i}]: a={leg.arrival} ≤ d={leg.departure}"
            )

        # Station already visited (destination of this leg)
        if check_acyclicity:
            if leg.destination in visited:
                violations.append(
                    f"cycle[{i}]: station {leg.destination!r} already visited"
                )
            visited.add(leg.destination)

        # 5 & 6. Continuity / distinct trains / transfer buffer (between legs)
        if i + 1 < k:
            nxt = legs[i + 1]
            if leg.destination != nxt.origin:
                violations.append(
                    f"discontinuity[{i}→{i + 1}]: v={leg.destination!r} ≠ "
                    f"u={nxt.origin!r}"
                )
            if leg.train_id == nxt.train_id:
                violations.append(
                    f"same_train[{i}→{i + 1}]: id={leg.train_id!r} (must change trains)"
                )
            wait = nxt.departure - leg.arrival
            if wait < instance.tau_min:
                violations.append(
                    f"transfer_buffer[{i}→{i + 1}]: wait={wait} < τ_min={instance.tau_min}"
                )

    if violations:
        return EvaluationResult(
            False, tuple(violations), None, None, None, None, None, None
        )

    T, N, f, comparison = compute_objective(legs, instance.lam)
    return EvaluationResult(
        True,
        (),
        T,
        N,
        f,
        legs[-1].arrival,
        legs[0].departure,
        comparison,
    )


def format_leg(leg: Leg) -> str:
    """Human-readable single-line leg description."""
    return (
        f"{leg.train_id}: {leg.origin}→{leg.destination} "
        f"d={_fmt_min(leg.departure)} a={_fmt_min(leg.arrival)}"
    )


def _fmt_min(m: int) -> str:
    """Format minute-of-timeline as HH:MM(+Nd) for readability."""
    day_offset, rem = divmod(m, 1440)
    hh, mm = divmod(rem, 60)
    suffix = f"+{day_offset}d" if day_offset else ""
    return f"{hh:02d}:{mm:02d}{suffix}"
