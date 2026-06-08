# WHAT WE HAVE BUILT — Assessment

**Mode:** CAVEMAN, read-only audit. The only file written in this session is this document.
**Audited from:** `/Users/apena/lor-v3` via Desktop Commander.
**Date:** 2026-06-08.
**Purpose:** let Alonso explain the whole implemented system end-to-end.

---

## 1. Current source of truth

- **`/Users/apena/lor-v3` is the real, latest implementation.** All current code,
  tests, outputs and docs live here. 19 modules in `src/lorp_fsd/` (~3,350 LoC),
  193 passing unit tests.
- **`/Users/apena/lorp-v3` is an incomplete GitHub snapshot** (the public mirror,
  e.g. `github.com/alonpena/lor-v3`). It is NOT the working tree and may lag behind.
- **Main risk:** `lor-v3` has **no proper own git repository**. The only `.git`
  is at `/Users/apena` with a single commit `f705cb0 "first commit"` and **zero
  tracked files** under `lor-v3`. The project currently exists only on disk, with
  no version history. Losing the folder loses everything.

---

## 2. What the original C/MILP model does

Source of truth: `det_LoRP_DSD()` in `reference/LoRPSD/stcmodels.cpp`, reached via
`-original 0` (the Excel sheet `LoRP-FSD`). Audited in `docs/C_SOLVER_AUDIT.md`.

- **Arslan scaling (`problemID=0`):** every distance is replaced by
  `dist · 100 / max_dist`, where `max_dist` is the maximum Euclidean distance over
  all depot/client nodes. `Radius`, `Length`, the objective and all cost columns are
  therefore in **scaled units**. Never divide reported costs by `scale`.
- **Direct allocation is an assignment, not a route:** `A[client][depot] ∈ {0,1}`,
  one-way cost only, no return arc, no client-to-client DA travel, and **no DA
  vehicle fixed cost**.
- **Shared depot capacity:** `demand_routing_i + demand_DA_i ≤ Cap_i`. Routing and DA
  consume the SAME depot capacity. Moving a client from routing to DA at the *same*
  depot does NOT free depot capacity.
- **Route length and vehicle capacity:** each route's scaled distance `≤ Length`;
  each route's load `≤ vehicle capacity`. Service exclusivity: every client is either
  routed or directly allocated, exactly once.
- **Objective components:** `Z = Cost_Routing + Cost_DA + Cost_Vehicles + Cost_Depots`
  where routing `= WR·Σ dist·X`, DA `= WA·Σ dist·A`, vehicles `= vehiclesfixed·VFX`
  per routing departure arc, depots `= Σ dep_cost·Y` (sizing-dependent).

---

## 3. What the PyVRP approximation does

PyVRP only routes, so the LoRP-FSD is *emulated*. Builder: `pyvrp_builder.py`.

- **Capacity-relaxed MD-VRP:** for a fixed facility design, the model opens the
  selected depots and serves all clients. The shared depot-capacity constraint
  (routing + DA ≤ Cap_i) is NOT representable in PyVRP, so it is **relaxed** at build
  time and clawed back later by the repair loop.
- **Routing vehicles per depot:** one routing **profile per open depot**; vehicles are
  bound to that depot (`start_depot = end_depot`). `Cap_i` is decomposed into
  `floor(Cap_i/Q)` full vehicles plus one residual vehicle.
- **Dual-channel encoding:** the **distance** channel carries scaled geometric distance
  (drives `max_distance = round(Length·1e4)`); the **duration** channel carries the
  weighted cost `round(F·dist_scaled·1e4)` with `unit_distance_cost=0`,
  `unit_duration_cost=1`. This keeps the length constraint and the cost objective separate.
- **DA as an artificial one-client vehicle/profile:** one profile per `(depot, client)`
  with exactly two edges (outbound cost `F_A·dist`, return cost 0) and a single vehicle
  whose capacity equals that client's demand. It can only ever serve that one client.
- **Cost reconstructed ex-post, not read blindly from PyVRP:** the reported objective
  is rebuilt from semantic decisions using continuous scaled geometry
  (`cost_reconstruction.py`): `Z = F_R·Σroute_dist + F_A·Σ DA_dist + vehicles(raw) +
  depots(raw)`. The PyVRP integer objective is never used as the final number.

---

## 4. Current pipeline

```
Excel row (results_MILP.xlsx, sheet LoRP-FSD)
  → resolve .dat instance (dat_parser)
  → fixed facility design (instance.build_facility_design)
  → scaled geometry, Arslan 100/max_dist (scaling)
  → capacity-relaxed PyVRP model with current forbidden set (pyvrp_builder)
  → solve: num_solve_runs × seconds_per_run, prefer feasible then min cost (runner)
  → parse solution into routing/DA records (solution_parser)
  → reconstruct cost in MILP-comparable scaled units (cost_reconstruction)
  → audit aggregate depot capacity (capacity_audit)
  → audit feasibility: service / route cap / length / DA radius / binding (feasibility)
  → if fully feasible: STOP, report GAP
  → else: savings-based repair selects routing arcs to forbid (repair)
  → rebuild with updated forbidden set; loop up to max_repair_iterations
  → final status + per-iteration artifacts (runner + artifacts + plotting)
```

The batch layer (`batch.py`) wraps this per-row runner over many Excel rows,
catches per-row errors, writes a consolidated CSV/XLSX, and aggregates a summary.

---

## 5. What is implemented (modules in `src/lorp_fsd/`)

| Module | One-line purpose |
|---|---|
| `dat_parser` | Parse `.dat` instances (depots, clients, demands, capacities) + resolve paths. |
| `excel_loader` | Load one Excel row (F_R, F_A, R, Length, VFX, UB, MILP cost columns). |
| `scaling` | Arslan scaling (`100/max_dist`) + integerization for PyVRP (`×1e4`). |
| `facility_sizing` | Compute selected depot sizes/capacities and their fixed costs. |
| `instance` | Build the in-memory instance + fixed facility design. |
| `pyvrp_builder` | Build the capacity-relaxed PyVRP model (routing + DA profiles). |
| `solution_parser` | Turn a PyVRP solution into semantic routing/DA records + binding checks. |
| `cost_reconstruction` | Rebuild Z in scaled MILP units; pick GAP vs RELAXATION_DEVIATION. |
| `capacity_audit` | Aggregate depot-capacity audit: routing + DA ≤ Cap_i, compute excess. |
| `feasibility` | Full feasibility audit + a-priori serviceability checkers. |
| `repair` | Savings-based routing-elimination repair + Phase 7A safety diagnostics. |
| `runner` | Per-row iterative loop (build→solve→audit→repair→rebuild) + status. |
| `batch` | Orchestrate many rows, consolidate CSV/XLSX, aggregate summary, catch errors. |
| `artifacts` | Per-iteration audit JSON + routes.csv + assignments.csv. |
| `plotting` | Per-iteration solution PNG (overloaded depots, removed clients, forbidden). |

---

## 6. Current repair logic

- **Hard routing restriction `(depot_id, client_id)`:** repair accumulates a set of
  *forbidden routing assignments*. The next `build_relaxed_model` simply does not create
  the routing edges for those pairs. It is a hard structural restriction — **not** a soft
  cost penalty, and **not** a deletion of arcs from a live model.
- **Does not delete customers:** a forbidden pair only blocks routing of that client from
  that depot. The client stays required and may still be served by DA (incl. same depot)
  or routed from another non-forbidden depot.
- **Computes routing savings:** `compute_route_savings` gives the marginal scaled-distance
  saving of removing each client from its route (internal / first / last / single-client
  cases), weighted by `F_R`. Candidates are taken only from routes of **overloaded depots**.
- **Uses overloaded depot excess:** per overloaded depot, candidates are sorted by largest
  weighted saving and selected until `Σ removed_demand ≥ excess_i`.
- **Ex-post audit vs ex-ante candidate validation:** capacity/feasibility are audited
  *after* each solve (ex-post); before *accepting* a cut, ex-ante checks run — a stranding
  check (client keeps ≥1 service option) plus the Phase 7A diagnostics
  (`same_depot_DA_risk`, `length_serviceable_after_cut`).
- **Policies:** `baseline` (stranding only), `safe_length` (require length-feasible
  alternative), `safe_capacity_release` (reject same-depot-DA risk), `safe_both` (both).
- **Important caveat:** a routing-only forbid does not *guarantee* aggregate capacity is
  released; capacity is only re-confirmed at the next solve. There is no tabu/expiry: once
  forbidden, a pair stays forbidden for the rest of the row.

---

## 7. What the tests prove

Verified this session (read-only):

```
py_compile (all src + targeted tests) ........ ALL_OK
pytest tests/test_repair_savings.py
       tests/test_phase7_repair_safety.py ..... 15 passed in ~1.8s
pytest -q -m "not integration" ............... 193 passed, 32 deselected in ~2s
```

- **Targeted repair tests:** `test_repair_savings.py` (savings formulas, weighted savings,
  per-depot candidate construction, greedy selection, stranding/feasibility checker) and
  `test_phase7_repair_safety.py` (safety diagnostics, the 4 policies, rejection reasons,
  plus 1 integration test marked and deselected by default).
- **Broad coverage:** parsing, Excel loading, scaling, facility sizing, instance/adapter,
  PyVRP builder, reporting, runner, batch.
- **What is NOT covered:** the 32 `@pytest.mark.integration` tests (which drive real PyVRP
  solves) are deselected in the default run; end-to-end convergence on hard instances,
  per-row timeout behavior, and full-Excel batch completion are not asserted by unit tests.

---

## 8. Existing outputs / results (from checkpoint/summary files only — no rerun)

Status counts read directly from each `outputs/*/checkpoint.csv` this session:

| Run | Rows | Status counts | Total solve | GAP min/mean/max (FEASIBLE) | Neg-gap flags |
|---|---|---|---|---|---|
| `smoke3` | 3 | FEASIBLE 3 | 3s | ~0 / ~0 / ~0 | 0 |
| `smoke_phase7_sample5` | 5 | FEASIBLE 4, STUCK 1 | 35s | 0 / 0.005 / 0.021 | 0 |
| `phase6_sample20_baseline` | 7 (partial) | FEASIBLE 4, REPAIR_INFEAS 3 | 720s | 0 / 0.004 / 0.015 | 0 |
| `phase7_sample20_safe_both` | 7 (partial) | FEASIBLE 4, REPAIR_INFEAS 3 | 720s | 0 / 0.004 / 0.015 | 0 |
| `phase6_sample20_baseline_fast` | 20 | FEASIBLE 12, REPAIR_INFEAS 4, STUCK 1, MAX_ITER 2, ERROR 1 | 166s | 0 / 0.006 / 0.040 | 0 |
| `phase7_sample20_safe_both_fast` | 20 | FEASIBLE 12, REPAIR_INFEAS 5, STUCK 1, MAX_ITER 1, ERROR 1 | 140s | 0 / 0.006 / 0.040 | 0 |

Key reading of the evidence:

- **No negative-gap modeling inconsistency was flagged in any run** (`neg_gap=0` everywhere).
- On feasible instances the heuristic is **within ~0.4–0.6% mean GAP** of the MILP UB
  (max observed 4%), which is the headline comparability result.
- The two 30s/3-run samples stalled at row 228 (`r30x5a-1.dat`) → only 7/20 rows; they have
  checkpoints but no consolidated/summary. The two `_fast` (5s/1run) samples are complete
  (consolidated.csv + .xlsx + summary).
- `diag_row5` is the only run with per-iteration **solution PNGs** (good for a demo).

**Can be shown today:** the two `_fast` k=20 consolidated tables + summaries, the
`smoke_phase7_sample5` summary, the `phase7a_sample20_fast_comparison.md` baseline-vs-safe_both
table, and the `diag_row5` solution plots. **Cannot be shown:** a complete all-instance run.

---

## 9. What is missing

- **Proper git repository for `lor-v3`** (highest risk: no version history at all).
- **Per-row wall-time timeout** in batch — one slow row (e.g. 228) blocks a whole run.
- **`repair_trace.csv`** — no temporal trace of which pairs were forbidden in which iteration.
- **Tabu list** — no tenure / expiry / re-admission of forbidden arcs; current set is monotonic.
- **Soft arc penalties** — repair only hard-restricts; no high-factor penalty alternative.
- **Simple HTML UI** — only partial Streamlit demos exist; no consolidated viewer.
- **Full all-instance run** — only partial/sample runs completed; no 1,000+ instance benchmark.

---

## 10. Next prioritized implementation plan

| Prio | Action |
|---|---|
| **P0** | Preserve `lor-v3` into a proper own git repo (init, .gitignore outputs/.venv, first real commit). |
| **P1** | Commit the assessment docs (this file + `HANDOFF_2026_06_08_MORNING.md`). |
| **P2** | Add a per-row timeout in `batch.py` so a single row cannot stall a run. |
| **P3** | Consolidate existing results (build consolidated/summary from partial checkpoints, no rerun). |
| **P4** | Add `repair_trace.csv` for per-iteration auditability of forbidden pairs. |
| **P5** | Generate selected plots for conflictive instances (REPAIR_INFEASIBLE / STUCK / negative-gap). |
| **P6** | Add tabu expiry (tenure ~ f(n_depots), aspiration on best cost). |
| **P7** | Add soft arc penalties (high-factor cost instead of hard restriction). |
| **P8** | Build a simple HTML UI to browse instances, status, costs and plots. |
| **P9** | Run the full all-instance benchmark once P2/P3 make it safe. |
