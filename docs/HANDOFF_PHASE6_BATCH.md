# Handoff — Phase 6: Batch Runner & Aggregate Statistics (LoRP-FSD v3)

Readable without prior context. Companion to `docs/IMPLEMENTATION_PLAN.md`
(Phase 6) and the Phase 1–5 handoffs.

Date: 2026-06-05 · Host: macOS arm64 · Working dir: `/Users/apena/lor-v3`

## 1. Files created / modified

### Created
- `src/lorp_fsd/batch.py` — batch orchestration (`run_rows`, `summarize`, CSV/Excel writers, `RowRecord`).
- `scripts/run_first_n.py` — CLI: run first N rows → consolidated CSV + summary.
- `scripts/run_random_sample.py` — CLI: run k random rows (fixed seed) → CSV + summary.
- `scripts/run_full_excel.py` — CLI: run all 1185 rows (resumable, plots off).
- `scripts/compare_with_milp.py` — component-level PyVRP-vs-MILP comparison table from CSV.
- `tests/test_batch.py` — 14 tests (9 unit + 5 integration).

### Modified
- `src/lorp_fsd/__init__.py` — export Phase 6 API.

No Phase 1–5 record types, semantics, or legacy modules were changed.

## 2. Batch runner behavior

`run_rows(row_indices, xlsx_path, ...)` orchestrates multiple rows:

- **Per-row try/except**: one bad row records `status = 'ERROR'` (with exception message), never crashes the batch.
- **Resumability**: when `checkpoint_csv` is given, each completed row is appended incrementally. On restart, rows already present in the checkpoint are skipped.
- **Plots off by default**: per-iteration PNGs are expensive and unnecessary for the consolidated table. Opt in with `make_plots=True`.
- **Deterministic seeding**: configurable `seed` parameter.
- **Configurable runtime**: `seconds_per_run`, `num_solve_runs`, `max_repair_iterations`.

### RowRecord (consolidated columns)

One record per Excel row:

```
row_id, instance, F_R, F_A, R, Length,
UB_MILP, Z_PyVRP, GAP, comparison_metric_label, comparison_metric_value,
status, iterations, solve_time_total,
cost_routing_milp, cost_da_milp, cost_vehicle_milp, cost_depot_milp,
cost_routing_pyvrp, cost_da_pyvrp, cost_vehicle_pyvrp, cost_depot_pyvrp,
capacity_feasible, service_feasible, route_length_feasible, da_radius_feasible,
penalty_distance_suspected, repair_failed, stuck_noncapacity, negative_gap_flag,
artifact_dir, error_message
```

### Status taxonomy (preserved from Phase 5)

| Status | Meaning | Diagnostic fields |
|---|---|---|
| `FEASIBLE` | Fully feasible solution found | `GAP`, all feasibility flags True |
| `REPAIR_INFEASIBLE` | Capacity repair cannot cover an overloaded depot | `repair_failed=True` |
| `STUCK_NONCAPACITY_VIOLATION` | Capacity OK, but route-length or other non-capacity constraint violated | `stuck_noncapacity=True`, `route_length_feasible=False` |
| `MAX_ITERATIONS` | Repair budget exhausted while still capacity-infeasible | `capacity_feasible=False` |
| `ERROR` | Row-level exception (instance not found, build/solve crash, etc.) | `error_message` has details |

### Aggregate summary fields

```
n_instances, n_success, n_repair_failed, n_stuck_noncapacity,
n_max_iterations, n_error, n_penalty, n_negative_gap,
min_gap, mean_gap, max_gap (over FEASIBLE rows),
min_runtime, mean_runtime, max_runtime,
min_iterations, mean_iterations, max_iterations,
avg_cost_{routing,da,vehicle,depot}_{pyvrp,milp},
delta_{routing,da,vehicle,depot} (PyVRP − MILP)
```

## 3. Scripts

### `scripts/run_first_n.py`

```bash
.venv/bin/python scripts/run_first_n.py --n 10 --seconds 30 --runs 3 --max-iter 5 --run-id first10
```

### `scripts/run_random_sample.py`

```bash
.venv/bin/python scripts/run_random_sample.py --k 20 --seed 42 --seconds 30 --runs 3 --run-id sample20
```

### `scripts/run_full_excel.py`

```bash
# First run:
.venv/bin/python scripts/run_full_excel.py --seconds 30 --runs 3 --run-id full_v3

# Resume after interruption (same command — skips completed rows):
.venv/bin/python scripts/run_full_excel.py --seconds 30 --runs 3 --run-id full_v3
```

### `scripts/compare_with_milp.py`

```bash
.venv/bin/python scripts/compare_with_milp.py outputs/first10/consolidated.csv
```

## 4. Output structure

```
outputs/<run_id>/consolidated.csv       # all rows, all columns
outputs/<run_id>/checkpoint.csv         # incremental (for resumability)
outputs/<run_id>/summary.json           # aggregate statistics
outputs/<run_id>/summary.md             # human-readable summary
outputs/<run_id>/consolidated.xlsx      # optional (--excel flag)
outputs/<run_id>/<instance>/iteration_XX_*  # per-iteration artifacts (if plots on)
```

## 5. Tests

- Phase 6 tests: **14 passed** (`tests/test_batch.py`):
  - 9 unit tests: RowRecord columns, summary aggregation (status counts, gap min/mean/max, runtime exclusion of ERROR, outlier detection), CSV writer columns, summary JSON validity.
  - 5 integration tests (marked `integration`): single-row feasible, error row does not crash batch, CSV roundtrip, summary from run, checkpoint resumability.
- Full repository suite: **219 passed** (205 prior + 14 new), no regressions.

## 6. Smoke validation results

### First 3 rows (1×1s, test profile)

```
Rows: 3  |  FEASIBLE: 3  |  STUCK: 0  |  REPAIR_FAIL: 0  |  MAX_ITER: 0  |  ERROR: 0
GAP: min=-0.000001  mean=-0.000001  max=-0.000001
```

All rows are `r40x5a-1.dat` with different F_A/R/Length parameters; all feasible at iteration 0.

## 7. Row 5 finding (from pre-Phase-6 diagnosis)

Row 5 (`r40x5b-1.dat`, F_A=0.5): `STUCK_NONCAPACITY_VIOLATION`.

- **Iteration 0**: depot 4 overloaded by +121; repair forbids clients 11, 18, 20, 37 from routing at depot 4.
- **Iteration 1**: capacity feasible, but **route-length violation** on depot 3 → client 18 → depot 3 (single-client route, distance 156.03 > Length 150.0).
- **Root cause**: client 18 can only be routed within Length from depot 4 (round-trip 102.12). Repair forbade `(4, 18)`, forcing client 18 to depot 3 where the single-client round-trip exceeds Length. Client 18 is DA-infeasible from all depots (all > R=40).
- **Not a bug**: builder `max_distance` is correctly set; reconstructed distances match geometry. This is a genuine side-effect of capacity-only repair.
- **Length-aware repair is future work**, not Phase 6.

The batch runner classifies this as `STUCK_NONCAPACITY_VIOLATION` with `route_length_feasible=False` and `stuck_noncapacity=True`, enabling batch-level quantification of this phenomenon.

## 8. Known caveats

1. **Short runtime degrades quality.** `STUCK_NONCAPACITY_VIOLATION` is more likely with low `seconds_per_run`. Use 3×30s for real experiments.
2. **Full batch is expensive.** At 3×30s, 1185 rows ≈ 50+ hours. Use fast profiles (1×5s) for exploration.
3. **Checkpoint CSV is append-only.** If a row's result changes between runs (e.g., different runtime), the checkpoint will have the first result. Delete the checkpoint to re-run all rows.
4. **No route-length repair.** The batch classifies and counts `STUCK_NONCAPACITY_VIOLATION` rows but does not attempt to fix them. This is by design — quantify the phenomenon first, then design a repair operator.

## 9. Phase 7 readiness

**GO for Phase 7 or route-length repair design** (future work). Phase 6 provides the batch infrastructure to:
- Run arbitrary row sets reproducibly.
- Classify every row by status (FEASIBLE / REPAIR_INFEASIBLE / STUCK_NONCAPACITY_VIOLATION / MAX_ITERATIONS / ERROR).
- Export diagnostic fields (`route_length_feasible`, `capacity_feasible`, `service_feasible`, `penalty_distance_suspected`) for batch-level analysis.
- Produce consolidated CSV + aggregate summary for the professor's meeting.

The `STUCK_NONCAPACITY_VIOLATION` count from a larger batch (first-100 or random-50) will quantify how many rows hit route-length violations after capacity repair, informing whether a length-aware repair operator is worth implementing.
