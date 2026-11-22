# Zadanie 2 — Static Train Route Optimization with Transfer Penalties

**Team:** 14 (tim14) — Galata Waqwaya Gichile, Oleksiy Orlyk, Rostyslav Matsko  
**Affiliation:** Katedra počítačov a informatiky, Technická univerzita v Košiciach  
**Contact:** galata.waqwaya.gichile@student.tuke.sk, oleksiy.orlyk@student.tuke.sk, rostyslav.matsko@student.tuke.sk  
**Course:** Moderné prístupy v optimalizácii (MPO), FEI KKUI TUKE  
**Python:** 3.12+ (standard library only — no `pip install` required)

---

## Problem (summary)

Find a feasible multi-leg train itinerary \(x = (l_1,\ldots,l_k)\) from origin \(s\) to destination \(z\) that minimises

\[
f(x) = T(x) + \lambda\, N(x), \qquad T(x)=a_k-d_1,\quad N(x)=k-1.
\]

Constraints: departure window \([t_0,t_0+H]\), valid timetable legs, station continuity, distinct consecutive trains, minimum transfer buffer \(\tau_{\min}\), and acyclicity. Evaluation is strictly \(O(k)\).

---

## Data provenance (important)

Shipped JSON files are **hand-crafted, ZSSK-shaped synthetic** timetables (`meta.provenance = hand_crafted_synthetic`), not a verbatim ZSSK GTFS dump. They are sized for reproducible verification (λ trade-off, midnight, infeasible audits).

To rebuild from a real GTFS folder (`stops.txt`, `trips.txt`, `stop_times.txt`):

```bash
python scripts/parse_gtfs.py --gtfs-dir path/to/gtfs --out data/slovak_corridor.json
```

---

## Repository layout

```text
tim14_zadanie2/
├── data/
│   ├── slovak_corridor.json      # Synthetic ZSSK-shaped corridor
│   └── synthetic_cases.json      # Edge cases (midnight, tight transfer, cycle)
├── scripts/
│   └── parse_gtfs.py             # Optional GTFS → JSON converter
├── src/
│   ├── model.py                  # Leg / Instance, O(k) validator, f(x)
│   ├── instances.py              # JSON loader + dual hash indexes
│   └── baseline.py               # Blind Random + Constructive Walk
├── tests/
│   └── test_model.py             # Stdlib unittest suite
├── report/
│   ├── report_tim14_2.tex        # Slovak LaTeX source
│   └── build.ps1                 # pdflatex helper
├── main.py                       # Verification + sensitivity tables
├── report_tim14_2.pdf            # 4–6 page report
└── README.md
```

---

## Quick start

```bash
cd tim14_zadanie2
python main.py
python -m unittest tests.test_model -v
```

Expected: four scenarios + baseline comparison + sensitivity table; total runtime **&lt; 5 seconds**.  
Reproducibility: `random.seed(42)`.

---

## What `main.py` prints

| Block | What is verified |
| :--- | :--- |
| **1. λ trade-off** | Direct \(T=190,N=0\) vs 1-transfer \(T=170,N=1\) under \(\lambda\in\{15,25\}\) |
| **2. Midnight** | \(d_1=1395\), \(a_k=1530\) ⇒ \(T=135\) |
| **3. Infeasible audit** | \(\tau_{\min}\), departure window, cycle \(A\to B\to A\to C\) |
| **4. Unreachable** | `"No feasible route found"` |
| **Baseline** | Blind ≈ 0% vs Constructive feasibility / best \(f\) |
| **Sensitivity** | \(n\) rollouts, \(H\), \(\tau_{\min}\) vs feas.% / best \(f\) |

---

## Design decisions (Assignment 1 feedback)

1. **Timetable source** — honest synthetic corridor + GTFS parser for real feeds.  
2. **Flat indexes** — `NamedTuple` + `dict` (`valid_legs`, `departures_from`).  
3. **No intermediate stops at runtime** — pairwise leg expansion; same-train travel = one leg.  
4. **Single-objective** — \(f=T+\lambda N\); Pareto noted as future work.

---

## Building the Slovak report

```powershell
winget install -e --id MiKTeX.MiKTeX   # once, if needed
cd report
.\build.ps1
```

---

## Packaging for submission

```powershell
# from the parent of tim14_zadanie2/
Compress-Archive -Path tim14_zadanie2 -DestinationPath tim14_zadanie2.zip -Force
# then remove __pycache__ / .git / .venv from the zip if present
```

Or with a Unix-like zip:

```bash
zip -r tim14_zadanie2.zip tim14_zadanie2 \
  -x "*/__pycache__/*" "*.pyc" "*/.git/*" "*/.venv/*" \
     "*/report/*.aux" "*/report/*.log" "*/report/*.out"
```
