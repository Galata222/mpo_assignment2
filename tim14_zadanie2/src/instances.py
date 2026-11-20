"""Timetable loading, dual hash indexes, and synthetic instance builders.

Time encoding: integer minutes elapsed since 00:00 of departure day D
(e.g. 08:10 → 490, next-day 00:30 → 1470).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .model import DeparturesIndex, Instance, Leg, ValidLegsIndex

# Default package-relative data directory
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Main Slovak rail corridor (Assignment 1 feedback: GTFS corridor filter)
CORRIDOR_STATIONS: Tuple[str, ...] = (
    "Košice",
    "Prešov",
    "Poprad-Tatry",
    "Vrútky",
    "Žilina",
    "Trenčín",
    "Trnava",
    "Bratislava",
)


def parse_hhmm(value: str, day_offset: int = 0) -> int:
    """Convert 'HH:MM' or 'HH:MM:SS' GTFS time to minutes since day-D midnight."""
    parts = value.strip().split(":")
    hours = int(parts[0])
    minutes = int(parts[1])
    return day_offset * 1440 + hours * 60 + minutes


def expand_trip_legs(
    train_id: str,
    stops: Sequence[Dict[str, Any]],
) -> List[Leg]:
    """Expand ordered stop sequence into all direct valid legs (a < b, a_b > d_a).

    Intermediate stations are discarded at runtime (Assignment 1 feedback: 'netreba').
    """
    legs: List[Leg] = []
    n = len(stops)
    for a in range(n):
        for b in range(a + 1, n):
            d = int(stops[a]["departure"])
            arr = int(stops[b]["arrival"])
            if arr > d:
                legs.append(
                    Leg(
                        train_id=train_id,
                        origin=str(stops[a]["station"]),
                        destination=str(stops[b]["station"]),
                        departure=d,
                        arrival=arr,
                    )
                )
    return legs


def build_indexes(
    trips: Sequence[Dict[str, Any]],
    day: str,
) -> Tuple[ValidLegsIndex, DeparturesIndex, List[Leg]]:
    """Build dual hash indexes for day D.

    Returns:
      valid_legs[(day, train_id, u, v, d)] = a
      departures_from[(day, u)] = list[Leg] sorted by departure
      all_legs: flat list of every expanded Leg on this day
    """
    valid_legs: ValidLegsIndex = {}
    departures_from: DeparturesIndex = {}
    all_legs: List[Leg] = []

    for trip in trips:
        if trip.get("day") not in (None, day) and trip.get("day") != day:
            # Allow trips that list operating days, or omit day (= always)
            operating = trip.get("days")
            if operating is not None and day not in operating:
                continue
        train_id = str(trip["train_id"])
        stops = trip["stops"]
        for leg in expand_trip_legs(train_id, stops):
            key = (day, leg.train_id, leg.origin, leg.destination, leg.departure)
            # Keep earliest arrival if duplicate keys appear
            prev = valid_legs.get(key)
            if prev is None or leg.arrival < prev:
                valid_legs[key] = leg.arrival
            all_legs.append(leg)
            dep_key = (day, leg.origin)
            departures_from.setdefault(dep_key, []).append(leg)

    for dep_key in departures_from:
        departures_from[dep_key].sort(key=lambda lg: (lg.departure, lg.arrival))

    return valid_legs, departures_from, all_legs


def load_timetable_json(path: Path | str) -> Dict[str, Any]:
    """Load a timetable JSON document (stations + trips)."""
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_corridor(
    path: Optional[Path | str] = None,
    day: str = "D",
) -> Tuple[ValidLegsIndex, DeparturesIndex, List[Leg], Dict[str, Any]]:
    """Load slovak_corridor.json and index for ``day``."""
    path = Path(path) if path else DATA_DIR / "slovak_corridor.json"
    data = load_timetable_json(path)
    valid, deps, legs = build_indexes(data["trips"], day)
    return valid, deps, legs, data


def load_synthetic(
    path: Optional[Path | str] = None,
    day: str = "D",
) -> Tuple[ValidLegsIndex, DeparturesIndex, List[Leg], Dict[str, Any]]:
    """Load synthetic_cases.json and index for ``day``."""
    path = Path(path) if path else DATA_DIR / "synthetic_cases.json"
    data = load_timetable_json(path)
    valid, deps, legs = build_indexes(data["trips"], day)
    return valid, deps, legs, data


def merge_indexes(
    parts: Iterable[Tuple[ValidLegsIndex, DeparturesIndex, List[Leg]]],
) -> Tuple[ValidLegsIndex, DeparturesIndex, List[Leg]]:
    """Merge several index triples (corridor + synthetic)."""
    valid: ValidLegsIndex = {}
    deps: DeparturesIndex = {}
    all_legs: List[Leg] = []
    for v, d, legs in parts:
        valid.update(v)
        all_legs.extend(legs)
        for key, lst in d.items():
            deps.setdefault(key, []).extend(lst)
    for key in deps:
        deps[key].sort(key=lambda lg: (lg.departure, lg.arrival))
    return valid, deps, all_legs


def make_tradeoff_instance(
    lam: float = 15.0,
) -> Instance:
    """Scenario 1: KE→BA morning window for λ trade-off comparison."""
    return Instance(
        day="D",
        origin="Košice",
        destination="Bratislava",
        t0=480,  # 08:00
        H=120,
        tau_min=5,
        lam=lam,
        k_max=4,
    )


def make_midnight_instance() -> Instance:
    """Scenario 2: late evening departure allowing next-day arrival."""
    return Instance(
        day="D",
        origin="Žilina",
        destination="Bratislava",
        t0=1380,  # 23:00
        H=60,
        tau_min=5,
        lam=15.0,
        k_max=3,
    )


def make_unreachable_instance() -> Instance:
    """Scenario 4: late-night window with no path to destination."""
    return Instance(
        day="D",
        origin="Košice",
        destination="Bratislava",
        t0=1410,  # 23:30
        H=30,
        tau_min=5,
        lam=15.0,
        k_max=4,
    )


def timetable_stats(
    valid_legs: ValidLegsIndex,
    departures_from: DeparturesIndex,
    all_legs: Sequence[Leg],
) -> Dict[str, Any]:
    """Compact statistics for the report / README."""
    stations = {lg.origin for lg in all_legs} | {lg.destination for lg in all_legs}
    trains = {lg.train_id for lg in all_legs}
    return {
        "n_stations": len(stations),
        "n_trains": len(trains),
        "n_expanded_legs": len(all_legs),
        "n_valid_leg_keys": len(valid_legs),
        "n_departure_buckets": len(departures_from),
        "stations": sorted(stations),
        "trains": sorted(trains),
    }
