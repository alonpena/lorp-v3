# Handoff — Phase 5: Iterative Row Runner & Per-Iteration Artifacts (LoRP-FSD v3)

Readable without prior context. Companion to `docs/IMPLEMENTATION_PLAN.md`
(Phase 5) and the Phase 1–4 handoffs.

Date: 2026-06-05 · Host: macOS arm64 · Working dir: `/Users/apena/lor-v3`

## 1. Files created / modified

### Created
- `src/lorp_fsd/runner.py` — iterative row runner (`run_row`, `run_row_from_excel`, `compute_repair_step`).
- `src/lorp_fsd/artifacts.py` — per-iteration audit JSON + routes/assignments CSV.
- `src/lorp_fsd/plotting.py` — per-iteration solution PNG (Agg backend).
- `scripts/run_row.py` — CLI to run one Excel row.
- `tests/test_runner.py` — 6 tests.

### Modified
- `src/lorp_fsd/__init__.py` — export Phase 5 API.
- `.gitignore` — ignore `outputs/` (runner artifacts).

No Phase 1–4 record types or legacy modules were changed.

## 2. Row runner behavior

`run_row(config, instance, geometry, facility_design, *, output_root, run_id,
seconds_per_run=30, num_solve_runs=3, max_repair_iterations=5, seed=0,
make_plots=True)` executes one row:

```
forbidden = set()
for iteration in 0 .. max_repair_iterations:
    build relaxed model with forbidden
    solve (num_solve_runs seeds x seconds_per_run; prefer PyVRP-feasible, then min cost)
    parse -> reconstruct cost -> audit capacity + feasibility -> comparison metric
    write iteration artifacts (+ plot)
    if fully_feasible:                      -> STATUS = FEASIBLE
    else compute savings repair selection
        if repair cannot cover an overloaded depot's excess -> REPAIR_INFEASIBLE
        elif nothing to remove (capacity OK, non-capacity violation) -> STUCK_NONCAPACITY_VIOLATION
        elif last iteration               -> MAX_ITERATIONS
        else forbidden |= repair.selected; continue
```

`run_row_from_excel(xlsx, row_index, ...)` is the convenience wrapper (load row →
resolve `.dat` → build geometry/design → `run_row`). The CLI `scripts/run_row.py`
wraps it.

### Statuses
- `FEASIBLE` — fully feasible (report `GAP`).
- `REPAIR_INFEASIBLE` — an overloaded depot's excess cannot be covered with
  non-stranding removals.
- `STUCK_NONCAPACITY_VIOLATION` — capacity satisfied but a non-capacity
  constraint (e.g. route length) is violated; the v3 baseline capacity-only
  repair cannot address it (future work: depot-level forbidding / local search /
  length-aware repair).
- `MAX_ITERATIONS` — repair budget exhausted while still capacity-infeasible.

### Solver policy
`num_solve_runs` seeds × `seconds_per_run` each; the best PyVRP-feasible (else
min-cost) solution is kept. Production default 3×30s; tests use 1×1s.

## 3. Artifact structure

```
outputs/<run_id>/<instance_name>/iteration_00_solution.png
                                 iteration_00_audit.json
                                 iteration_00_routes.csv
                                 iteration_00_assignments.csv
                                 iteration_01_*  ...
```

- **audit JSON** (per iteration): row id, instance, iteration, `F_R/F_A/R/Length`,
  `scale`, `max_dist`, active depots + capacities, `forbidden_routing_assignments`,
  selected repair removals, per-depot `demand_routing/DA/total/excess`,
  `capacity_feasible`, `all_clients_served_exactly_once`, route length / capacity /
  DA radius feasibility, `penalty_distance_suspected`, PyVRP cost components +
  `z_pyvrp`, MILP cost components + `ub_milp`, comparison metric label/value +
  flags, `solve_time`, status.
- **routes CSV**: iteration, route_id, vehicle_type, service_mode, depot_id,
  client_sequence, demand, scaled_distance, weighted_cost, route_length_feasible,
  capacity_feasible (one row per routing route).
- **assignments CSV**: iteration, client_id, service_mode, depot_id, demand,
  da_feasible, dist_scaled_to_depot, forbidden_from_routing_depots (one row per
  client).

## 4. Plotting behavior

`plot_iteration` (Agg, headless) draws: clients (grey dots), active depots
(squares; **overloaded depots ringed red**), routing routes (green solid), DA
assignments (orange dashed), **clients removed in the previous repair step (red
X)**, and a title with iteration, feasibility, route/DA counts, accumulated
forbidden count, and overloaded depot list. Simple and debug-oriented.

## 5. Row 0 results (deterministic, seed 0)

Runner on `r40x5a-1.dat` (row 0): **terminates at iteration 0** (already feasible).

| Aspect | Value |
|---|---|
| Status | `FEASIBLE` |
| Iterations | 1 (final iter 0) |
| Routing routes / DA | 1 / 38 |
| Clients served exactly once | yes (40) |
| Z_PyVRP | 395.3087 (UB 395.309) |
| Cost components (PyVRP) | routing 95.3087 · DA 0 · vehicles 0 · depots 300 |
| Metric | `GAP` ≈ −8e-7 (within rounding tol; no negative-gap flag) |
| Artifacts | audit.json, routes.csv, assignments.csv, solution.png all written |

### Multi-iteration demonstration (row 5, `r40x5b-1.dat`, not a test)
Validates the repair loop end-to-end:
- **iter 0**: depot 4 overloaded by 121; length-feasible; repair selects 4 removals.
- **iter 1**: capacity now feasible (excess 0) — repair worked — but a **route-length
  violation** remains → `STUCK_NONCAPACITY_VIOLATION` (capacity-only repair cannot
  fix length). Metric `RELAXATION_DEVIATION` = −0.44 (Z≫UB, an infeasible/penalized
  solution). This is the expected v3-baseline limitation and is fully captured in
  the per-iteration audit (`route_length_feasible=false`).

## 6. Tests

- Phase 5 tests: **6 passed** (`tests/test_runner.py`, `integration`-marked):
  row-0 terminates at iter 0 / FEASIBLE; all four artifacts created; audit JSON
  contents; final structure + cost (1 route, 38 DA, 40 served, Z≈395.3087, GAP≈0);
  routes/assignments CSV row counts; and `compute_repair_step` on an artificial
  overloaded audit produces a valid repair selection.
- Full repository suite: **205 passed** (199 prior + 6), no regressions.

## 7. Known caveats

1. **Tests solve** (deterministic seed 0, 1×1s). Row 0 is trivial and reliably
   feasible at iteration 0.
2. **Short runtime degrades quality.** `STUCK_NONCAPACITY_VIOLATION` / route-length
   violations are more likely with low `seconds_per_run`/`num_solve_runs`; use the
   3×30s production policy for real runs.
3. **Capacity-only repair.** The baseline repair fixes capacity overload only;
   non-capacity violations (route length) stop the loop with
   `STUCK_NONCAPACITY_VIOLATION`. Length-aware / depot-level repair is future work.
4. **`RELAXATION_DEVIATION` can be negative** when the kept solution is
   infeasible/penalized (Z above UB) — a useful signal, not a clean relaxation.
5. No batch runner / aggregate stats yet (Phase 6).

## 8. Phase 6 readiness

**GO for Phase 6 (batch runner + consolidated table + aggregate stats).** Phase 5
gives a stable per-row runner returning a `RowRunResult` (status, iterations,
final metric, per-iteration records, total solve time) plus on-disk per-iteration
artifacts. Phase 6 will wrap `run_row_from_excel` over row sets
(`run_first_n` / `run_random_sample` / `run_full_excel`), collect one consolidated
row per instance, and compute aggregate statistics. The status taxonomy
(`FEASIBLE` / `REPAIR_INFEASIBLE` / `STUCK_NONCAPACITY_VIOLATION` /
`MAX_ITERATIONS`) and per-iteration audit fields already provide exactly the
columns and failure-mode counts the professor's summary needs
(success / repair-failed / penalty / negative-gap / iterations / runtime / gap).

**Do not implement Phase 6 yet** (per instruction) — stop here.
