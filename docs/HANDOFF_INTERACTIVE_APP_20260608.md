# Handoff — Interactive Local App

Date: 2026-06-08
Repo: `/Users/apena/lorp-v3`

## 1. Current repo state

Active repo: `/Users/apena/lorp-v3`.

Latest implementation commits:

- `49540db feat: add per-row timeout for batch runs` — P1 timeout.
- `5f33d73 feat: add row repair trace artifacts` — P2 repair trace artifacts.
- `9060a78 feat: add basic row reporting artifacts` — P3 row report artifacts.
- `f5c551c feat: improve row reports and plots` — P3D improved reports and plots.

Untracked checkpoint files should stay uncommitted:

- `checkpoint_phase7_repair_safety_morning.patch`
- `checkpoint_phase7_repair_safety_morning_manifest.txt`

## 2. What is implemented now

Implemented in v3 package:

- Per-row wall-clock timeout for batch runs.
- `repair_trace.csv`.
- `iteration_summary.csv`.
- `report.md`.
- `report.json`.
- `cost-breakdown.csv`.
- `depot_usage.csv`.
- Instance-state plot.
- Combined routing + DA solution plot.
- Tests passing:
  - `.venv/bin/python -m py_compile src/lorp_fsd/*.py`
  - `.venv/bin/python -m pytest -q -m "not integration"`
  - `197 passed, 32 deselected`

## 3. Current generated row artifacts

For one row run, output folder includes:

- `report.md`
- `report.json`
- `cost-breakdown.csv`
- `depot_usage.csv`
- `iteration_summary.csv`
- `repair_trace.csv`
- `iteration_XX_instance.png`
- `iteration_XX_solution.png`
- `iteration_XX_audit.json`
- `iteration_XX_routes.csv`
- `iteration_XX_assignments.csv`

Example command used for smoke verification:

```bash
.venv/bin/python scripts/run_row.py \
  --row 0 \
  --seconds 3 \
  --runs 1 \
  --max-iter 2 \
  --repair-policy safe_both \
  --run-id verify_p3d_row0
```

## 4. Next desired feature

Build interactive local app with buttons, similar to old `lor-v2` app, but using v3 package.

App requirements:

- Local interactive UI.
- Select Excel row.
- Show MILP parameters and selected depots.
- Run PyVRP for selected row.
- Choose `seconds`, `runs`, `max_iter`, `repair_policy`, `row_timeout_seconds`, plots on/off.
- Display generated `report.md`.
- Display `report.json` summary.
- Show cost breakdown table.
- Show depot usage table.
- Show iteration summary.
- Show repair trace.
- Show instance plot.
- Show solution plot.
- Show links to output folder files.
- Compare MILP vs PyVRP costs.
- Show final status explanation.
- Do not change modelling logic.
- Call existing v3 runner; do not duplicate solver logic.

## 5. Old UI to inspect

Next agent may inspect old files if present in `/Users/apena/lor-v2`:

- `app_capacity_repair_solver.py`
- Any `*streamlit*`, `*app*`, `*ui*`, `*html*` files.
- `pipeline_out/streamlit_demo_row*` if available.

Warnings:

- Old app likely imports legacy modules, not v3 package.
- Use old app only for visual/layout ideas.
- Do not revive legacy logic blindly.

## 6. Recommended implementation approach

- First build minimal local app around existing outputs and `run_row_from_excel`.
- Static HTML report can come later; Alonso wants interactive app with buttons now.
- Prefer Streamlit if old `lor-v2` app was Streamlit and quick to adapt.
- Otherwise use minimal Flask/FastAPI + static frontend.
- Do not use Antigravity to rewrite modelling core.
- Keep app thin wrapper over runner.

Suggested v3 call path:

- Load available Excel rows with `lorp_fsd.excel_loader.load_lorp_fsd_rows`.
- Run one row through `lorp_fsd.runner.run_row_from_excel` or existing script logic.
- Read outputs from `result.output_dir`:
  - Markdown via `report.md`.
  - JSON via `report.json`.
  - CSV tables via `pandas.read_csv`.
  - PNG plots via file display.

## 7. Safety rules

- Use one branch for app work.
- No `outputs/` in git.
- No long experiments from app by default.
- Defaults:
  - `seconds=3` or `5`
  - `runs=1`
  - `max_iter=3`
  - `row_timeout_seconds=120`
- Expose advanced parameters manually.
- Preserve real objective reconstruction.
- Never report PyVRP internal penalized/search cost as real LoRP cost.
- Do not change repair logic.
- Do not change cost reconstruction.
- Do not implement tabu or soft penalties as part of app shell.
