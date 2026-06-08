# Static HTML row report — quickstart

HTML-first row report for LoRP-FSD / PyVRP. No server, no Streamlit, no CDN.

## What it does

Reads the artifacts the row runner already produces inside one output folder
(`report.json`, the CSVs, the iteration PNGs) and writes a single
self-contained `index.html`. Plots are embedded as base64, so the file can be
opened or emailed on its own. It is a **pure reader** — it never runs or
modifies the solver/repair/cost logic.

The report is organised into sticky top **view tabs** (JS, no server):
**Summary · Costs · Capacity · Feasibility · Iterations · Plots · Files**.

- **Summary** — cards (MILP UB, PyVRP total, GAP, runtime, iterations,
  feasibility), instance/facility + MILP tables, the professor's-algorithm
  mapping, and the status-meaning legend.
- **Costs** — MILP-vs-PyVRP cost table and routing/DA mix.
- **Capacity** — depot usage, a **repair-policy explanation box** (baseline /
  safe_length / safe_capacity_release / safe_both, active one highlighted), and
  the repair summary.
- **Feasibility** — ex-post checks, iteration summary, repair trace.
- **Iterations** — per-iteration sub-tabs (Iteration 0, 1, …) from the
  `iteration_XX_audit.json` files: audit summary, feasibility, selected/rejected
  repair candidates, routes and assignments tables, and that iteration's plots.
- **Plots** — basal-instance and combined-solution plots.
- **Files** — generated artifact list.

## How to run

Generate the HTML from an existing output folder:

```
.venv/bin/python scripts/make_row_html.py --dir outputs/<run_id>/<instance_name>
```

Or, for a single-instance run, by run id:

```
.venv/bin/python scripts/make_row_html.py --run-id <run_id>
```

Then open the printed `file://…/index.html` path in any browser.

## Safe demo command (row 0)

Row 0 reproduces the MILP almost exactly — a clean FEASIBLE demo.

```
.venv/bin/python scripts/run_row.py --row 0 --seconds 3 --runs 1 --max-iter 2 \
  --repair-policy safe_both --run-id html_demo_row0
.venv/bin/python scripts/make_row_html.py --run-id html_demo_row0
```

(`run_row.py` makes plots by default; pass `--no-plots` to skip. Per-row
timeout lives in the batch runner, not in `run_row.py`.)

- **Suggested demo row: 0** (FEASIBLE, GAP ≈ 0).
- A conflictive row (e.g. one that triggers repair) can be shown from an
  existing output folder via `--dir`; **do not run a conflictive row long**
  during the meeting.

## Warning

- There is **no full batch run from this report yet**. It only renders one row
  folder that already exists.
- Defaults are kept small (seconds=3, runs=1, max-iter=2, row-timeout=120) so a
  demo never hangs.
