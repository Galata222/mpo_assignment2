#!/usr/bin/env python3
"""Lightweight stdlib unit tests for the O(k) model and indexes.

Run from repository root:
  python -m unittest tests.test_model -v
"""

from __future__ import annotations

import unittest

from src.baseline import constructive_walk, run_blind_random, run_constructive_walk
from src.instances import (
    build_indexes,
    expand_trip_legs,
    load_corridor,
    load_synthetic,
    make_tradeoff_instance,
    merge_indexes,
)
from src.model import Instance, Leg, evaluate_candidate


class TestLegExpansion(unittest.TestCase):
    def test_pairwise_expansion_count(self) -> None:
        stops = [
            {"station": "A", "arrival": 0, "departure": 10},
            {"station": "B", "arrival": 20, "departure": 22},
            {"station": "C", "arrival": 40, "departure": 40},
        ]
        legs = expand_trip_legs("T1", stops)
        # pairs: A→B, A→C, B→C
        self.assertEqual(len(legs), 3)
        self.assertEqual(legs[0], Leg("T1", "A", "B", 10, 20))


class TestDayFilter(unittest.TestCase):
    def test_days_list_and_day_field(self) -> None:
        trips = [
            {
                "train_id": "A",
                "days": ["D", "E"],
                "stops": [
                    {"station": "X", "arrival": 0, "departure": 10},
                    {"station": "Y", "arrival": 30, "departure": 30},
                ],
            },
            {
                "train_id": "B",
                "day": "E",
                "stops": [
                    {"station": "X", "arrival": 0, "departure": 15},
                    {"station": "Y", "arrival": 35, "departure": 35},
                ],
            },
        ]
        valid_d, _, legs_d = build_indexes(trips, "D")
        valid_e, _, legs_e = build_indexes(trips, "E")
        self.assertEqual(len(legs_d), 1)
        self.assertEqual(len(legs_e), 2)
        self.assertIn(("D", "A", "X", "Y", 10), valid_d)
        self.assertNotIn(("D", "B", "X", "Y", 15), valid_d)
        self.assertIn(("E", "B", "X", "Y", 15), valid_e)


class TestEvaluateCandidate(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        v_c, d_c, l_c, _ = load_corridor(day="D")
        v_s, d_s, l_s, _ = load_synthetic(day="D")
        cls.valid, cls.deps, cls.legs = merge_indexes(
            [(v_c, d_c, l_c), (v_s, d_s, l_s)]
        )

    def test_lambda_tradeoff(self) -> None:
        direct = [Leg("IC521", "Košice", "Bratislava", 480, 670)]
        transfer = [
            Leg("R801", "Košice", "Žilina", 480, 600),
            Leg("EC125", "Žilina", "Bratislava", 605, 650),
        ]
        r15 = evaluate_candidate(direct, make_tradeoff_instance(15), self.valid)
        t15 = evaluate_candidate(transfer, make_tradeoff_instance(15), self.valid)
        r25 = evaluate_candidate(direct, make_tradeoff_instance(25), self.valid)
        t25 = evaluate_candidate(transfer, make_tradeoff_instance(25), self.valid)
        self.assertTrue(r15.is_feasible and t15.is_feasible)
        self.assertEqual(r15.f, 190.0)
        self.assertEqual(t15.f, 185.0)
        self.assertLess(t15.comparison, r15.comparison)  # type: ignore[operator]
        self.assertEqual(t25.f, 195.0)
        self.assertLess(r25.comparison, t25.comparison)  # type: ignore[operator]

    def test_midnight_duration(self) -> None:
        inst = Instance(
            day="D", origin="Žilina", destination="Bratislava",
            t0=1380, H=60, tau_min=5, lam=15.0,
        )
        night = [Leg("EN477", "Žilina", "Bratislava", 1395, 1530)]
        res = evaluate_candidate(night, inst, self.valid)
        self.assertTrue(res.is_feasible)
        self.assertEqual(res.T, 135)

    def test_transfer_buffer_violation(self) -> None:
        inst = Instance(
            day="D", origin="Alpha", destination="Gamma",
            t0=480, H=120, tau_min=5, lam=15.0,
        )
        tight = [
            Leg("SYN_T1", "Alpha", "Beta", 490, 520),
            Leg("SYN_T2", "Beta", "Gamma", 524, 560),
        ]
        res = evaluate_candidate(tight, inst, self.valid)
        self.assertFalse(res.is_feasible)
        self.assertTrue(any("transfer_buffer" in v for v in res.violations))

    def test_cycle_violation(self) -> None:
        inst = Instance(
            day="D", origin="Alpha", destination="Gamma",
            t0=600, H=120, tau_min=5, lam=15.0,
        )
        cycle = [
            Leg("SYN_AB", "Alpha", "Beta", 610, 640),
            Leg("SYN_BA", "Beta", "Alpha", 650, 680),
            Leg("SYN_AC", "Alpha", "Gamma", 690, 730),
        ]
        res = evaluate_candidate(cycle, inst, self.valid)
        self.assertFalse(res.is_feasible)
        self.assertTrue(any("cycle" in v for v in res.violations))


class TestBaselines(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        v_c, d_c, l_c, _ = load_corridor(day="D")
        v_s, d_s, l_s, _ = load_synthetic(day="D")
        cls.valid, cls.deps, cls.legs = merge_indexes(
            [(v_c, d_c, l_c), (v_s, d_s, l_s)]
        )
        cls.inst = make_tradeoff_instance(15.0)

    def test_blind_near_zero_feasibility(self) -> None:
        stats = run_blind_random(
            self.inst, self.legs, self.valid, n_rollouts=200, seed=42
        )
        self.assertLess(stats.feasibility_rate, 0.05)

    def test_constructive_finds_feasible(self) -> None:
        stats = run_constructive_walk(
            self.inst, self.deps, self.valid, n_rollouts=500, seed=42
        )
        self.assertGreater(stats.feasibility_rate, 0.2)
        self.assertIsNotNone(stats.best)
        self.assertEqual(stats.best.f, 185.0)  # type: ignore[union-attr]

    def test_no_start_window(self) -> None:
        import random

        inst = Instance(
            day="D", origin="Košice", destination="Bratislava",
            t0=1410, H=30, tau_min=5, lam=15.0,
        )
        legs, res, reason = constructive_walk(
            inst, self.deps, self.valid, random.Random(0)
        )
        self.assertEqual(reason, "no_start")
        self.assertFalse(res.is_feasible)
        self.assertEqual(legs, [])


if __name__ == "__main__":
    unittest.main()
