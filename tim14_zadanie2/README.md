# Zadanie 2 — Static Train Route Optimization with Transfer Penalties

**Team:** 14 (tim14)  
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

## Repository layout

```text
tim14_zadanie2/
├── data/
│   ├── slovak_corridor.json      # Filtered ZSSK-style corridor timetable
│   └── synthetic_cases.json      # Edge cases (midnight, tight transfer, cycle)
├── scripts/
│   └── parse_gtfs.py             # Optional GTFS → JSON converter
├── src/
│   ├── __init__.py
│   ├── model.py                  # Leg / Instance, O(k) validator, f(x)
│   ├── instances.py              # JSON loader + dual hash indexes
│   └── baseline.py               # Blind Random + Constructive Walk
├── main.py                       # All verification scenarios
└── README.md
```

---

## Quick start

```bash
cd tim14_zadanie2
python main.py
```

Expected: all four scenarios plus the baseline comparison table, total runtime **&lt; 5 seconds**.

Reproducibility: `random.seed(42)` is fixed inside `main.py`.

---

## What `main.py` prints

| Scenario | What is verified |
| :--- | :--- |
| **1. Transfer-penalty trade-off** | Direct \(T=190,N=0\) vs 1-transfer \(T=170,N=1\) under \(\lambda\in\{15,25\}\) |
| **2. Midnight crossover** | \(d_1=1395\), \(a_k=1530\) ⇒ \(T=135\) |
| **3. Infeasible audit** | (a) \(\tau_{\min}\) 4 min wait, (b) departure window, (c) cycle \(A\to B\to A\to C\) |
| **4. Unreachable** | Late-night window with `"No feasible route found"` |
| **Baseline comparison** | Blind Random ≈ 0% feasible vs Constructive Walk feasibility / best \(f\) |

---

## Optional: rebuild corridor JSON from raw GTFS

If you download a ZSSK GTFS dump (`stops.txt`, `trips.txt`, `stop_times.txt`):

```bash
python scripts/parse_gtfs.py --gtfs-dir path/to/gtfs --out data/slovak_corridor.json
```

The shipped `data/slovak_corridor.json` is already sufficient for grading.

---

## Design decisions (Assignment 1 feedback)

1. **Timetable source** — ZSSK-style corridor subset (Košice … Bratislava) + synthetic edge-case file.  
2. **Flat indexes** — `NamedTuple` legs + `dict` maps (`valid_legs`, `departures_from`); no heavy OOP graph classes.  
3. **No intermediate stops at runtime** — all ordered stop-pairs on a trip are pre-expanded into direct legs.  
4. **Single-objective** — scalar \(f(x)=T+\lambda N\) for Zadanie 2; Pareto \((T,N,a_k)\) noted as future work.

---

## Packaging for submission

```bash
# from the parent of tim14_zadanie2/
zip -r tim14_zadanie2.zip tim14_zadanie2 \
  -x "*/__pycache__/*" "*.pyc" "*/.git/*" "*/.venv/*"
```

Include `report_tim14_2.pdf` (4–6 pages, Slovak) in the archive before upload.

---

## Building the Slovak report (LaTeX)

Source: `report/report_tim14_2.tex` (Sections 1–4, Slovak, matching Assignment 1 terminology).

```powershell
# requires MiKTeX or TeX Live (pdflatex on PATH)
winget install -e --id MiKTeX.MiKTeX   # once
cd report
.\build.ps1
# → report/report_tim14_2.pdf  and  ../report_tim14_2.pdf
```
