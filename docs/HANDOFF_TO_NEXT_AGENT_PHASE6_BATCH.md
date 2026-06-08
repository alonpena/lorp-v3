# Handoff to Next Agent — Phase 6: Batch Runner & Aggregate Statistics (LoRP-FSD v3)

Self-contained. Read this plus the source-of-truth docs and you can start Phase 6
without prior context.

Date: 2026-06-05 · Host: macOS arm64 · Working dir: `/Users/apena/lor-v3`
Python: `.venv` (uv) · PyVRP installed · Gurobi 12 present (not needed for v3).

Source-of-truth docs (read in this order):
- `docs/C_SOLVER_AUDIT.md` — the C/Gurobi LoRP-FSD model (ground truth).
- `docs/PYVRP_REPLICATION_SPEC.md` — the v3 method + settled decisions.
- `docs/IMPLEMENTATION_PLAN.md` — phase plan (you are starting Phase 6).
- `docs/C_CONGRUENCY_TEST.md` — row-0 parameter congruency (exact reconstruction).
- `docs/HANDOFF_PHASE1_PREPROCESSING.md` … `docs/HANDOFF_PHASE5_ROW_RUNNER_ARTIFACTS.md`.

---

## 1. Current project status

Phases 1–5 are **complete, tested, and documented**. The v3 package
`src/lorp_fsd/` cleanly replaces the legacy root modules (which are untouched and
still pass their own tests). The repo runs **205 tests, all passing**.

You can already, today:
- parse a `.dat` instance and an Excel `LoRP-FSD` row,
- build a capacity-relaxed PyVRP model under the MILP-selected facility design,
- solve it, parse the solution, reconstruct the C/MILP objective, and audit
  capacity + feasibility,
- run the **iterative repair loop for ONE row** and emit per-iteration plots,
  audit JSON, and CSVs.

What is missing (your job): **Phase 6 = run many rows and produce a consolidated
table + aggregate statistics** for the meeting.

---

## 2. Phase 1–5 summary

| Phase | Modules | What it does |
|---|---|---|
| 1 | `dat_parser`, `excel_loader`, `experiment_config`, `geometry`, `scaling`, `facility_sizing`, `instance` | C-compatible parsing; Arslan scaling `scale=100/max_dist`; `PYVRP_INT_SCALE=10_000`; 5-size facility formula; fixed `FacilityDesign` from Excel. |
| 2 | `da_options`, `pyvrp_builder` | Capacity-relaxed PyVRP model: routing vehicles `floor(Cap/Q)`+residual; per-pair single-client zero-return DA options; dual-channel integerized costs; `forbidden_routing_assignments`; `BuildInfo`/`VehicleTypeMeta`. |
| 3 | `solution_parser`, `cost_reconstruction`, `capacity_audit`, `feasibility` | Parse routes → semantic records; ex-post mixed-unit objective; per-depot `routing+DA` capacity audit; route/length/radius/binding/penalty feasibility; `GAP`/`RELAXATION_DEVIATION` metric. |
| 4 | `repair` (+ `feasibility` helpers) | Savings candidate generation (overloaded depots only); greedy largest-saving selection until excess covered; stranding check; routing-only `forbidden_routing_assignments`. |
| 5 | `runner`, `artifacts`, `plotting`, `scripts/run_row.py` | Iterative per-row loop build→solve→parse→cost→audit→repair→rebuild; per-iteration PNG + audit JSON + routes/assignments CSV; status taxonomy. |

Key invariants (do not break — see §11): scaled distances for routing/DA costs;
**raw** fixed costs for vehicles/depots; never divide final costs by `scale`; DA
is one-way / zero-return / single-client / no multitrip; depot capacity is shared
(`routing + DA ≤ Cap_i`); `forbidden_routing_assignments` is routing-only
(same-depot DA still allowed).

**Row 0 regression** (`r40x5a-1.dat`): `scale=0.79745222`, open depots `(1,2,3,5)`,
caps `875`, depot cost `300`, 1 routing route + 38 DA, **Z=395.3087** vs UB 395.309,
`GAP≈0`.

---

## 3. How to run tests

```bash
cd /Users/apena/lor-v3
.venv/bin/python -m pytest -q                 # full suite (205 passing)
.venv/bin/python -m pytest tests/test_runner.py -q          # Phase 5 only
.venv/bin/python -m pytest -m "not integration" -q          # skip solve-based tests
```

`integration`-marked tests perform a short PyVRP solve (deterministic, seed 0).
Tests import the package via pytest `pythonpath = ["src", "."]` (no install needed).

---

## 4. How to run row 0 and row 5

Standalone scripts need `src` on the path; the CLI handles it internally.

```bash
# Row 0 — already feasible at iteration 0 (fast)
.venv/bin/python scripts/run_row.py --row 0 --seconds 1 --runs 1 --max-iter 2 --run-id demo_row0

# Row 5 — overloads depot 4; exercises the repair loop (use real runtime)
.venv/bin/python scripts/run_row.py --row 5 --seconds 30 --runs 3 --max-iter 5 --run-id demo_row5
```

Programmatic (note `PYTHONPATH=src` for ad-hoc scripts/REPL):

```bash
PYTHONPATH=src .venv/bin/python -c "
from lorp_fsd.runner import run_row_from_excel
r = run_row_from_excel('results_MILP.xlsx', 0, root='.', output_root='outputs',
                       run_id='demo', seconds_per_run=1, num_solve_runs=1, max_repair_iterations=2)
print(r.status, r.final.cost.total, r.final.metric.label, r.final.metric.value)
"
```

Outputs land in `outputs/<run_id>/<instance_name>/iteration_NN_*`.

---

## 5. Status taxonomy (`src/lorp_fsd/runner.py`)

| Status | Meaning | Metric reported |
|---|---|---|
| `FEASIBLE` | Fully feasible: served-once, capacity OK, route length/capacity/radius OK, binding OK, no penalty. | `GAP = (Z − UB)/UB` |
| `REPAIR_INFEASIBLE` | An overloaded depot's excess cannot be covered with non-stranding removals (a candidate would leave a client with no routing AND no DA option). | `RELAXATION_DEVIATION` |
| `STUCK_NONCAPACITY_VIOLATION` | Capacity is satisfied, but a **non-capacity** constraint (typically route length) is violated. The v3 baseline repair is capacity-only, so it has nothing to remove. | `RELAXATION_DEVIATION` |
| `MAX_ITERATIONS` | Repair budget exhausted while still capacity-infeasible. | `RELAXATION_DEVIATION` |

`GAP` flags `NEGATIVE_GAP_MODELING_INCONSISTENCY` only for a *material* negative
gap (relative tol `1e-4`, to absorb Excel's 3-decimal UB rounding).

---

## 6. The row 5 finding (read carefully — it drives Phase 6 stats)

`r40x5b-1.dat` (rows 5/6, `F_A=0.5`) demonstrates the repair loop AND a real
baseline limitation:

- **Iteration 0**: relaxed solve overloads depot 4 by **+121**; route length is
  fine; all clients served once. Savings repair selects 4 routing removals at
  depot 4.
- **Iteration 1**: rebuilt with those 4 forbidden routing assignments. **Capacity
  is now feasible (excess 0)** — the repair *worked*. But the new routing layout
  has a **route-length violation** (`route_length_feasible=false`), so the
  solution is not fully feasible.

Why this is **not** `REPAIR_INFEASIBLE`:
- `REPAIR_INFEASIBLE` means *capacity* repair failed (an overloaded depot couldn't
  be covered). Here capacity repair **succeeded**; there are **no overloaded
  depots left** to act on.
- The remaining problem is a route-length violation, which the **capacity-only**
  savings repair (v3 baseline, settled decision #8) is not designed to fix. The
  runner therefore stops with the distinct status `STUCK_NONCAPACITY_VIOLATION`.
- It is also partly a **runtime/quality** artifact: short solves are likelier to
  return a PyVRP-infeasible (length-penalized) solution. Use 3×30s in real runs.

This distinction matters for the professor's summary: count
`STUCK_NONCAPACITY_VIOLATION` separately from `REPAIR_INFEASIBLE`. The per-iteration
audit JSON already records `route_length_feasible`, `capacity_feasible`,
`excess`, etc., so the failure mode is fully traceable. Length-aware /
depot-level repair is explicit **future work**, not a Phase 6 task.

---

## 7. Current output artifact structure

```
outputs/<run_id>/<instance_name>/iteration_00_solution.png
                                 iteration_00_audit.json
                                 iteration_00_routes.csv
                                 iteration_00_assignments.csv
                                 iteration_01_*  ...
```

`outputs/` is git-ignored.

- **audit JSON** keys (per iteration): `row_id, instance_name, iteration,
  F_R, F_A, R, Length, scale, max_dist, active_depots, depot_capacities,
  forbidden_routing_assignments, selected_repair_removals,
  demand_routing, demand_DA, demand_total, excess, capacity_feasible,
  all_clients_served_exactly_once, route_length_feasible, route_capacity_feasible,
  da_radius_feasible, penalty_distance_suspected,
  cost_routing_pyvrp, cost_direct_all_pyvrp, cost_vehicles_pyvrp, cost_depots_pyvrp,
  z_pyvrp, ub_milp, cost_routing_milp, cost_direct_all_milp, cost_vehicles_milp,
  cost_depots_milp, comparison_metric_label, comparison_metric_value, metric_flags,
  solution_flags, fully_feasible, solve_time, status`.
- **routes CSV**: `iteration, route_id, vehicle_type, service_mode, depot_id,
  client_sequence, demand, scaled_distance, weighted_cost, route_length_feasible,
  capacity_feasible`.
- **assignments CSV**: `iteration, client_id, service_mode, depot_id, demand,
  da_feasible, dist_scaled_to_depot, forbidden_from_routing_depots`.

`RowRunResult` (returned by `run_row` / `run_row_from_excel`) carries:
`row_index, instance_name, status, final_iteration, iterations[...], final_metric,
output_dir, total_solve_time, final_forbidden`. Each `IterationResult` holds
`parsed, cost, capacity, feasibility, metric, repair_selection, solve_time,
forbidden_before, removed_clients_prev, artifact_paths`.

---

## 8. Phase 6 objective

Build the **batch layer** over the existing per-row runner. Do **not** modify the
per-row runner's semantics. Deliver:

1. **Batch runner** — run an arbitrary set of Excel rows, collect one consolidated
   record per row, write a consolidated CSV (and optionally Excel).
2. **First-N runner** — rows `0..N-1`.
3. **Random-sample runner** — `k` rows with a fixed seed (reproducible).
4. **Full-Excel runner** — all 1185 rows (resumable / skippable, robust to
   per-row failures — one bad row must not abort the batch).
5. **Aggregate summary statistics** — a separate summary file (CSV/JSON/Markdown).

Robustness requirements:
- Per-row try/except: a row that fails instance resolution, build, solve, or audit
  is recorded with a `status = ERROR` (and the exception message) — never crashes
  the batch.
- Deterministic seeding; configurable `seconds_per_run`, `num_solve_runs`,
  `max_repair_iterations`, `seed`, `make_plots` (default plots **off** for large
  batches — only the consolidated table is needed; allow opt-in).
- Resumability for the full run (skip rows whose consolidated record already
  exists, or checkpoint the CSV incrementally).

Performance note: full Excel = 1185 rows × (`num_solve_runs` × `seconds_per_run` ×
iterations). At 3×30s that is large; provide a fast profile (e.g. 1×5s) for smoke
batches and document the trade-off. **Do not run the full 1185-row batch as part
of implementing/testing** — implement + validate on first-N and a small random
sample only.

---

## 9. Required consolidated columns (one row per instance/Excel row)

```
row_id, instance, F_R, F_A, R, Length,
UB_MILP, Z_PyVRP, GAP, comparison_metric_label, comparison_metric_value,
status, iterations, solve_time_total,
cost_routing_milp, cost_da_milp, cost_vehicle_milp, cost_depot_milp,
cost_routing_pyvrp, cost_da_pyvrp, cost_vehicle_pyvrp, cost_depot_pyvrp,
capacity_feasible, service_feasible, route_length_feasible, da_radius_feasible,
penalty_distance_suspected, repair_failed, stuck_noncapacity, negative_gap_flag
```

(`repair_failed` = status `REPAIR_INFEASIBLE`; `stuck_noncapacity` = status
`STUCK_NONCAPACITY_VIOLATION`; `service_feasible` = all clients served exactly
once; `negative_gap_flag` = `NEGATIVE_GAP_MODELING_INCONSISTENCY` in metric flags.)

### Aggregate summary fields

```
n_instances, n_success (FEASIBLE), n_repair_failed, n_stuck_noncapacity,
n_max_iterations, n_error, n_penalty, n_negative_gap,
mean_gap, min_gap, max_gap,                       # over FEASIBLE rows
mean_runtime, min_runtime, max_runtime,
mean_iterations, min_iterations, max_iterations,
cost-decomposition averages (MILP vs PyVRP per component),
component deltas (PyVRP − MILP) per component
```

Pull these from `RowRunResult` + the final `IterationResult` (don't re-parse the
JSON files unless you want a JSON-only path). All values already exist on the
records — no new modeling.

---

## 10. Recommended implementation files / scripts

Create (per `IMPLEMENTATION_PLAN.md` §1, Phase 6):
- `src/lorp_fsd/batch.py` — `run_rows(row_indices, ...) -> list[RowRecord]`,
  `summarize(records) -> dict`, CSV/Excel writers. Keep all batch logic here.
- `scripts/run_first_n.py` — first N rows → consolidated CSV + summary.
- `scripts/run_random_sample.py` — `k` rows, fixed seed → CSV + summary.
- `scripts/run_full_excel.py` — all rows, resumable, plots off by default.
- `scripts/compare_with_milp.py` — component-level MILP-vs-PyVRP comparison table.
- `tests/test_batch.py` — run first 1–2 rows with tiny runtime (1×1s); assert the
  consolidated record has all required columns, the summary aggregates correctly,
  and a deliberately bad row yields `status=ERROR` without aborting.

Reuse — do not reimplement — `run_row_from_excel`, `resolve_dat_path`,
`reconstruct_cost`, the audits, and the metric. Batch = orchestration + tabulation
only.

Excel output: `openpyxl`/`pandas` are already dependencies. A CSV is mandatory; an
Excel sheet is a nice-to-have.

---

## 11. What NOT to change

- **Do not modify** Phase 1–5 modules' behavior: `dat_parser`, `excel_loader`,
  `experiment_config`, `geometry`, `scaling`, `facility_sizing`, `instance`,
  `da_options`, `pyvrp_builder`, `solution_parser`, `cost_reconstruction`,
  `capacity_audit`, `feasibility`, `repair`, `runner`, `artifacts`, `plotting`.
  (Additive exports are fine; semantic changes are not.)
- **Do not change** the settled modeling invariants (scaled vs raw units; one-way
  zero-return single-client DA; shared depot capacity; routing-only forbidding;
  `PYVRP_INT_SCALE=10_000`; `problemID=0`-only).
- **Do not touch** the legacy root modules or their tests.
- **Do not** introduce length-aware/depot-level repair (future work, not Phase 6).
- **Do not** run the full 1185-row batch during development; validate on small sets.
- Keep `outputs/` git-ignored; write consolidated tables somewhere explicit (e.g.
  `outputs/<run_id>/summary.csv` and `outputs/<run_id>/consolidated.csv`).

---

## 12. Exact next command / prompt for the next agent

> Proceed with Phase 6 only (batch runner + consolidated table + aggregate
> statistics). Work in `/Users/apena/lor-v3`. Read
> `docs/HANDOFF_TO_NEXT_AGENT_PHASE6_BATCH.md` and the source-of-truth docs first.
> Do NOT modify Phase 1–5 module behavior or the legacy modules. Do NOT run the
> full 1185-row Excel during development.
>
> Implement `src/lorp_fsd/batch.py` (`run_rows`, `summarize`, CSV/Excel writers),
> plus `scripts/run_first_n.py`, `scripts/run_random_sample.py`,
> `scripts/run_full_excel.py` (resumable, plots off by default), and
> `scripts/compare_with_milp.py`. Reuse `run_row_from_excel` and the existing
> records — batch is orchestration + tabulation only, with per-row try/except so
> one bad row records `status=ERROR` without aborting the batch.
>
> Produce the consolidated columns and aggregate summary fields listed in
> `HANDOFF_TO_NEXT_AGENT_PHASE6_BATCH.md` §9. Add `tests/test_batch.py` that runs
> the first 1–2 rows at 1×1s, asserts the consolidated record has all required
> columns, checks the summary aggregation, and verifies a bad row yields ERROR
> without crashing. Then run the full test suite, validate on first-10 and a
> random sample of 5, write `docs/HANDOFF_PHASE6_BATCH.md`, and stop.
>
> Recommended first validation rows: row 0 (FEASIBLE), row 5
> (STUCK_NONCAPACITY_VIOLATION), and a row that resolves cleanly for ERROR-path
> testing (force a bad instance name).
