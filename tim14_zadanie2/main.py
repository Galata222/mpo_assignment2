#!/usr/bin/env python3
"""Zadanie 2 — verification harness (Team 14).

Runs all four reproducible scenarios with random.seed(42) and prints
formatted tables for the technical report.

Usage (from repository root):
  python main.py
"""

from __future__ import annotations

import random
import time
from collections import Counter
from typing import Sequence

from src.baseline import run_blind_random, run_constructive_walk
from src.instances import (
    load_corridor,
    load_synthetic,
    make_midnight_instance,
    make_tradeoff_instance,
    make_unreachable_instance,
    merge_indexes,
    timetable_stats,
)
from src.model import EvaluationResult, Instance, Leg, evaluate_candidate, format_leg


# Provenance banner (honest about synthetic corridor vs real GTFS)
PROVENANCE_NOTE = (
    "Data provenance: hand-crafted ZSSK-shaped corridor + synthetic edge cases "
    "(not a verbatim GTFS dump). Optional converter: scripts/parse_gtfs.py"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hr() -> None:
    print("-" * 72)


def _banner(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def _print_legs(legs: Sequence[Leg]) -> None:
    if not legs:
        print("  (no legs)")
        return
    for i, leg in enumerate(legs, 1):
        print(f"  l{i}: {format_leg(leg)}")


def _print_result(result: EvaluationResult) -> None:
    if result.is_feasible:
        print(
            f"  FEASIBLE  T={result.T}  N={result.N}  f={result.f:.1f}  "
            f"a_k={result.a_k}  d_1={result.d_1}  cmp={result.comparison}"
        )
    else:
        print("  INFEASIBLE")
        for v in result.violations:
            print(f"    · {v}")


# ---------------------------------------------------------------------------
# Scenario 1 — Transfer-penalty trade-off (λ = 15 vs λ = 25)
# ---------------------------------------------------------------------------

def scenario_transfer_tradeoff(valid_legs, departures_from) -> None:
    _banner("Scenario 1 — Transfer penalty trade-off (λ = 15 vs λ = 25)")

    # Hand-crafted candidates matching the mathematical example in the plan:
    #   direct:  T=190, N=0  → f=190 (any λ)
    #   transfer: T=170, N=1 → f=185 (λ=15) / f=195 (λ=25)
    direct = [
        Leg("IC521", "Košice", "Bratislava", 480, 670),
    ]
    transfer = [
        Leg("R801", "Košice", "Žilina", 480, 600),
        Leg("EC125", "Žilina", "Bratislava", 605, 650),
    ]

    for lam in (15.0, 25.0):
        inst = make_tradeoff_instance(lam=lam)
        print(f"\nλ = {lam:.0f} min   s={inst.origin} → z={inst.destination}  "
              f"t0={inst.t0}  H={inst.H}")
        _hr()
        print("Candidate A — slow direct (N=0):")
        _print_legs(direct)
        ra = evaluate_candidate(direct, inst, valid_legs)
        _print_result(ra)

        print("Candidate B — faster 1-transfer:")
        _print_legs(transfer)
        rb = evaluate_candidate(transfer, inst, valid_legs)
        _print_result(rb)

        if ra.is_feasible and rb.is_feasible:
            winner = "A (direct)" if ra.comparison < rb.comparison else "B (1-transfer)"
            print(f"  → preferred under λ={lam:.0f}: {winner}")


# ---------------------------------------------------------------------------
# Scenario 2 — Midnight crossover
# ---------------------------------------------------------------------------

def scenario_midnight(valid_legs) -> None:
    _banner("Scenario 2 — Midnight crossover (23:15 → 01:30+1d)")

    inst = make_midnight_instance()
    night = [
        Leg("EN477", "Žilina", "Bratislava", 1395, 1530),
    ]
    print(f"s={inst.origin} → z={inst.destination}  t0={inst.t0}  H={inst.H}")
    _print_legs(night)
    result = evaluate_candidate(night, inst, valid_legs)
    _print_result(result)
    if result.is_feasible:
        assert result.T == 135, f"Expected T=135, got {result.T}"
        print("  ✓ T(x) = a_k − d_1 = 1530 − 1395 = 135 min (midnight arithmetic OK)")


# ---------------------------------------------------------------------------
# Scenario 3 — Explicit infeasible candidate audit
# ---------------------------------------------------------------------------

def scenario_infeasible_audit(valid_legs) -> None:
    _banner("Scenario 3 — Explicit infeasible candidate audit")

    # (a) τ_min violation: 4 min transfer (SYN_T1 → SYN_T2)
    inst_a = Instance(
        day="D", origin="Alpha", destination="Gamma",
        t0=480, H=120, tau_min=5, lam=15.0,
    )
    tight = [
        Leg("SYN_T1", "Alpha", "Beta", 490, 520),
        Leg("SYN_T2", "Beta", "Gamma", 524, 560),  # wait = 4 < 5
    ]
    print("\n(a) Transfer buffer violation (wait=4 < τ_min=5):")
    _print_legs(tight)
    _print_result(evaluate_candidate(tight, inst_a, valid_legs))

    # (b) Departure window violation: d_1 before t0
    inst_b = Instance(
        day="D", origin="Košice", destination="Bratislava",
        t0=500, H=60, tau_min=5, lam=15.0,  # window [500, 560]
    )
    early = [
        Leg("IC521", "Košice", "Bratislava", 480, 670),  # 480 < 500
    ]
    print("\n(b) Departure-window violation (d_1=480 ∉ [500, 560]):")
    _print_legs(early)
    _print_result(evaluate_candidate(early, inst_b, valid_legs))

    # (c) Acyclicity: Alpha → Beta → Alpha → Gamma
    inst_c = Instance(
        day="D", origin="Alpha", destination="Gamma",
        t0=600, H=120, tau_min=5, lam=15.0,
    )
    cycle = [
        Leg("SYN_AB", "Alpha", "Beta", 610, 640),
        Leg("SYN_BA", "Beta", "Alpha", 650, 680),
        Leg("SYN_AC", "Alpha", "Gamma", 690, 730),
    ]
    print("\n(c) Acyclicity violation (A→B→A→C revisits Alpha):")
    _print_legs(cycle)
    _print_result(evaluate_candidate(cycle, inst_c, valid_legs))


# ---------------------------------------------------------------------------
# Scenario 4 — Unreachable / empty instance
# ---------------------------------------------------------------------------

def scenario_unreachable(valid_legs, departures_from) -> None:
    _banner("Scenario 4 — Unreachable destination (late-night window)")

    inst = make_unreachable_instance()
    print(f"s={inst.origin} → z={inst.destination}  "
          f"window=[{inst.t0}, {inst.t0 + inst.H}]  (23:30–00:00)")

    starters = [
        lg for lg in departures_from.get((inst.day, inst.origin), [])
        if inst.t0 <= lg.departure <= inst.t0 + inst.H
    ]
    print(f"  eligible first-leg departures: {len(starters)}")

    stats = run_constructive_walk(
        inst, departures_from, valid_legs, n_rollouts=50, seed=42
    )
    print(f"  constructive rollouts: {stats.total_rollouts}")
    print(f"  feasible_count:        {stats.feasible_count}")
    print(f"  feasibility_rate:      {stats.feasibility_rate:.1%}")

    if stats.feasible_count == 0:
        print('  → "No feasible route found"')
    else:
        print("  WARNING: unexpected feasible route in empty window")
        _print_legs(stats.best_legs or [])


# ---------------------------------------------------------------------------
# Baseline comparison (Blind Random vs Constructive Walk)
# ---------------------------------------------------------------------------

def scenario_baseline_comparison(valid_legs, departures_from, all_legs) -> None:
    _banner("Baseline comparison — Blind Random vs Constructive Randomized Walk")

    inst = make_tradeoff_instance(lam=15.0)
    n = 500  # enough under seed=42 to discover the λ=15 optimum (f=185)
    seed = 42

    print(f"Instance: {inst.origin} → {inst.destination}, t0={inst.t0}, H={inst.H}, λ={inst.lam}")
    print(f"Rollouts per method: {n}  (seed={seed})")
    _hr()

    t0 = time.perf_counter()
    blind = run_blind_random(inst, all_legs, valid_legs, n_rollouts=n, seed=seed)
    t_blind = time.perf_counter() - t0

    t0 = time.perf_counter()
    walk = run_constructive_walk(
        inst, departures_from, valid_legs, n_rollouts=n, seed=seed
    )
    t_walk = time.perf_counter() - t0

    print(f"{'Method':<32} {'feasible':>10} {'rate':>8} {'best f':>10} {'time[s]':>8}")
    _hr()
    bf = f"{blind.best.f:.1f}" if blind.best and blind.best.f is not None else "—"
    wf = f"{walk.best.f:.1f}" if walk.best and walk.best.f is not None else "—"
    print(
        f"{'Blind Random Sampling':<32} {blind.feasible_count:>10} "
        f"{blind.feasibility_rate:>7.1%} {bf:>10} {t_blind:>8.3f}"
    )
    print(
        f"{'Constructive Randomized Walk':<32} {walk.feasible_count:>10} "
        f"{walk.feasibility_rate:>7.1%} {wf:>10} {t_walk:>8.3f}"
    )

    if walk.best_legs:
        print("\nBest constructive route:")
        _print_legs(walk.best_legs)
        _print_result(walk.best)  # type: ignore[arg-type]

    reasons = Counter(r.reason for r in walk.records)
    print("\nConstructive termination reasons:")
    for reason, count in sorted(reasons.items()):
        print(f"  {reason:<16} {count:>5}")


# ---------------------------------------------------------------------------
# Sensitivity: rollouts / H / τ_min (for report §3)
# ---------------------------------------------------------------------------

def scenario_sensitivity(valid_legs, departures_from) -> None:
    _banner("Sensitivity — constructive walk (seed=42, Košice→Bratislava)")

    print(f"{'param':<18} {'value':>8} {'feas%':>8} {'best f':>10}")
    _hr()

    # Rollout budget
    for n in (100, 200, 500):
        inst = make_tradeoff_instance(lam=15.0)
        stats = run_constructive_walk(
            inst, departures_from, valid_legs, n_rollouts=n, seed=42
        )
        bf = f"{stats.best.f:.1f}" if stats.best and stats.best.f is not None else "—"
        print(f"{'n_rollouts':<18} {n:>8} {stats.feasibility_rate:>7.1%} {bf:>10}")

    # Departure window H
    for H in (60, 120, 180):
        inst = Instance(
            day="D", origin="Košice", destination="Bratislava",
            t0=480, H=H, tau_min=5, lam=15.0, k_max=4,
        )
        stats = run_constructive_walk(
            inst, departures_from, valid_legs, n_rollouts=300, seed=42
        )
        bf = f"{stats.best.f:.1f}" if stats.best and stats.best.f is not None else "—"
        print(f"{'H [min]':<18} {H:>8} {stats.feasibility_rate:>7.1%} {bf:>10}")

    # Transfer buffer τ_min
    for tau in (3, 5, 10):
        inst = Instance(
            day="D", origin="Košice", destination="Bratislava",
            t0=480, H=120, tau_min=tau, lam=15.0, k_max=4,
        )
        stats = run_constructive_walk(
            inst, departures_from, valid_legs, n_rollouts=300, seed=42
        )
        bf = f"{stats.best.f:.1f}" if stats.best and stats.best.f is not None else "—"
        print(f"{'τ_min [min]':<18} {tau:>8} {stats.feasibility_rate:>7.1%} {bf:>10}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    random.seed(42)
    t_start = time.perf_counter()

    _banner("Team 14 — Zadanie 2  |  Static Train Route Optimization")
    print("Gichile, Orlyk, Matsko · KPI TUKE · Python stdlib · seed=42")
    print(PROVENANCE_NOTE)

    # Load & merge corridor + synthetic indexes
    v_c, d_c, legs_c, data_c = load_corridor(day="D")
    v_s, d_s, legs_s, data_s = load_synthetic(day="D")
    valid_legs, departures_from, all_legs = merge_indexes(
        [(v_c, d_c, legs_c), (v_s, d_s, legs_s)]
    )

    stats = timetable_stats(valid_legs, departures_from, all_legs)
    print(f"\nTimetable index: {stats['n_stations']} stations, "
          f"{stats['n_trains']} trains, {stats['n_expanded_legs']} expanded legs, "
          f"{stats['n_valid_leg_keys']} valid_legs keys")
    print(f"Corridor meta.provenance: {data_c.get('meta', {}).get('provenance', '?')}")
    print(f"Synthetic meta.provenance: {data_s.get('meta', {}).get('provenance', '?')}")

    scenario_transfer_tradeoff(valid_legs, departures_from)
    scenario_midnight(valid_legs)
    scenario_infeasible_audit(valid_legs)
    scenario_unreachable(valid_legs, departures_from)
    scenario_baseline_comparison(valid_legs, departures_from, all_legs)
    scenario_sensitivity(valid_legs, departures_from)

    elapsed = time.perf_counter() - t_start
    _banner(f"Done — total runtime {elapsed:.3f}s")
    if elapsed >= 5.0:
        print("WARNING: runtime ≥ 5 s (submission target is < 5 s)")


if __name__ == "__main__":
    main()
