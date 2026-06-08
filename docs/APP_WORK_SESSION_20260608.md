# App work session — 2026-06-08

Short working audit for the HTML-first row report built before the meeting.

## Repo state at start

- Working dir: `/Users/apena/lorp-v3` (only this repo touched).
- Branch at start: `main` → created `phase8-html-row-report`.
- Untracked checkpoint files left alone (not added):
  `checkpoint_phase7_repair_safety_morning.patch`,
  `checkpoint_phase7_repair_safety_morning_manifest.txt`.
- HEAD: `56ce2e8 docs: handoff interactive app implementation`.

## Implemented features (pre-existing)

per-row timeout · `repair_trace.csv` · `iteration_summary.csv` · `report.md` ·
`report.json` · `cost-breakdown.csv` · `depot_usage.csv` · instance plot ·
solution plot. ~197 tests passing recently.

## Files inspected

- `scripts/run_row.py` — row runner CLI (entry point, params, defaults).
- `src/lorp_fsd/artifacts.py` — full `report.json` / CSV schema.
- `outputs/verify_p3c_row0/r40x5a-1.dat/report.json` — real payload shape.
- PNG naming: `iteration_XX_instance.png`, `iteration_XX_solution.png`.

## Old UI found (inspiration only)

- `/Users/apena/lor-v2/app_capacity_repair_solver.py` (Streamlit) and
  `/Users/apena/lor-v2/reporting.py`. Used for KPI/layout ideas only.
  **No legacy module imported into v3.**

## Implementation choice

HTML-first, per the explicit instruction to **not** make Streamlit the main
surface. Built a pure reader that emits a static, self-contained `index.html`
inside each row output folder. No server, no CDN, plots embedded as base64.
Solver / repair / cost-reconstruction logic untouched; runner not modified.

## What changed

- `src/lorp_fsd/html_report.py` — renderer (`render_index_html`,
  `write_index_html`, `STATUS_EXPLANATIONS`).
- `scripts/make_row_html.py` — CLI (`--dir` or `--run-id`).
- `tests/test_html_report.py` — section/plot/status/error tests.
- `docs/OPERATIONAL_LOGIC_FOR_PROFESSOR.md` — Spanish algorithm-mapping doc.
- `docs/INTERACTIVE_APP_QUICKSTART.md` — how to run.
- `docs/APP_WORK_SESSION_20260608.md` — this file.

## Tests run

- `py_compile` over `src/lorp_fsd/*.py` + new script — OK.
- `pytest -q -m "not integration"` — see commit message / final report.

## Demo commands

```
.venv/bin/python scripts/run_row.py --row 0 --seconds 3 --runs 1 --max-iter 2 \
  --repair-policy safe_both --run-id html_demo_row0
.venv/bin/python scripts/make_row_html.py --run-id html_demo_row0
```

(`run_row.py` plots by default; no `--row-timeout-seconds`/`--plots` flags.)

Open the printed `file://…/index.html`.

## Remaining limitations

- One row per file; no batch view from the report.
- Pure reader — the row must already be solved (artifacts present).
- No interactivity (static HTML by design).
