#!/usr/bin/env python3
"""One-time converter: raw ZSSK GTFS CSVs → filtered corridor JSON.

Usage (optional; the repository already ships a ready-made subset):
  python scripts/parse_gtfs.py --gtfs-dir path/to/gtfs --out data/slovak_corridor.json

Requires only the Python 3.12 standard library. If the GTFS directory is
missing, the script exits with a clear message and does not overwrite data/.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

# Main Slovak rail corridor stop-name substrings (Assignment 1 feedback)
CORRIDOR_KEYWORDS = (
    "Košice",
    "Kosice",
    "Prešov",
    "Presov",
    "Poprad",
    "Vrútky",
    "Vrutky",
    "Žilina",
    "Zilina",
    "Trenčín",
    "Trencin",
    "Trnava",
    "Bratislava",
)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def _parse_time(value: str) -> int | None:
    """GTFS HH:MM:SS → minutes since service-day midnight (hours may exceed 23)."""
    value = (value or "").strip()
    if not value:
        return None
    parts = value.split(":")
    if len(parts) < 2:
        return None
    return int(parts[0]) * 60 + int(parts[1])


def _is_corridor_stop(name: str) -> bool:
    return any(k.lower() in name.lower() for k in CORRIDOR_KEYWORDS)


def convert(gtfs_dir: Path, service_id_filter: str | None = None) -> dict:
    stops_rows = _read_csv(gtfs_dir / "stops.txt")
    trips_rows = _read_csv(gtfs_dir / "trips.txt")
    stop_times = _read_csv(gtfs_dir / "stop_times.txt")

    corridor_stop_ids = {
        r["stop_id"]
        for r in stops_rows
        if _is_corridor_stop(r.get("stop_name", ""))
    }
    stop_name = {r["stop_id"]: r.get("stop_name", r["stop_id"]) for r in stops_rows}

    if service_id_filter:
        trips_rows = [t for t in trips_rows if t.get("service_id") == service_id_filter]

    trip_meta = {t["trip_id"]: t for t in trips_rows}

    by_trip: dict[str, list[dict]] = defaultdict(list)
    for st in stop_times:
        if st["trip_id"] not in trip_meta:
            continue
        if st["stop_id"] not in corridor_stop_ids:
            continue
        dep = _parse_time(st.get("departure_time", ""))
        arr = _parse_time(st.get("arrival_time", ""))
        if dep is None or arr is None:
            continue
        by_trip[st["trip_id"]].append(
            {
                "station": stop_name[st["stop_id"]],
                "arrival": arr,
                "departure": dep,
                "seq": int(st.get("stop_sequence", 0)),
            }
        )

    trips_out = []
    for trip_id, stops in by_trip.items():
        stops.sort(key=lambda s: s["seq"])
        # Drop helper seq field
        clean = [
            {"station": s["station"], "arrival": s["arrival"], "departure": s["departure"]}
            for s in stops
        ]
        if len(clean) < 2:
            continue
        meta = trip_meta[trip_id]
        trips_out.append(
            {
                "train_id": meta.get("trip_short_name") or trip_id,
                "name": meta.get("trip_headsign") or trip_id,
                "day": "D",
                "gtfs_trip_id": trip_id,
                "stops": clean,
            }
        )

    stations = sorted(
        {s["station"] for t in trips_out for s in t["stops"]}
    )
    return {
        "meta": {
            "source": f"ZSSK GTFS filtered corridor ({gtfs_dir})",
            "day": "D",
            "time_unit": "minutes since 00:00 of day D",
            "n_trips": len(trips_out),
        },
        "stations": [{"id": name, "name": name} for name in stations],
        "trips": trips_out,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--gtfs-dir",
        type=Path,
        required=True,
        help="Directory containing stops.txt, trips.txt, stop_times.txt",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "data" / "slovak_corridor.json",
    )
    parser.add_argument("--service-id", default=None, help="Optional GTFS service_id filter")
    args = parser.parse_args(argv)

    required = ["stops.txt", "trips.txt", "stop_times.txt"]
    missing = [f for f in required if not (args.gtfs_dir / f).exists()]
    if missing:
        print(
            f"ERROR: GTFS files missing in {args.gtfs_dir}: {', '.join(missing)}",
            file=sys.stderr,
        )
        print(
            "Ship uses the pre-built data/slovak_corridor.json; this script is optional.",
            file=sys.stderr,
        )
        return 1

    data = convert(args.gtfs_dir, args.service_id)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    print(f"Wrote {len(data['trips'])} trips → {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
