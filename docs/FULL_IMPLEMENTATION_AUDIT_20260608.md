# Full Implementation Audit — LoRP-FSD v3

**Mode:** CAVEMAN, read-only audit. No source modified. Only this doc and
`docs/NEXT_AGENT_RULES.md` were written.
**Date:** 2026-06-08.
**Working dir:** `/Users/apena/lorp-v3`.
**Purpose:** single readable end-to-end audit of repository situation, development
history, modelling logic, results, tests, gaps, and next priorities — so Alonso
can explain the entire system and the next agent can continue safely.

---

## A. Repository situation

### A.1 What happened with `lor-v3`, `lorp-v3`, and the backups

- All listed external backup paths are **MISSING** on disk (verified this session):
  - `/Users/apena/lor-v3` — MISSING
  - `/Users/apena/lor_archives_20260608/lor-v3_SOURCE_BACKUP` — MISSING
  - `/Users/apena/lor_archives_20260608/lor-v3_ADVANCED_SOURCE_BACKUP` — MISSING
  - `/Users/apena/lor_archives_20260608/lorp-v3_INCOMPLETE_BACKUP` — MISSING
- The **only** project tree that exists now is `/Users/apena/lorp-v3` (with the `p`).
- Earlier handoffs (`HANDOFF_2026_06_08_MORNING.md`, `WHAT_WE_HAVE_BUILT_ASSESSMENT.md`)
  describe the live work tree as `/Users/apena/lor-v3` (no `p`), with **no own git**
  (only a single `f705cb0 "first commit"` in the `/Users/apena` parent, zero tracked
  files). That highest-severity risk has since been resolved: the complete
  implementation was **restored into `/Users/apena/lorp-v3` and committed to its own
  git repo** as commit `ab83d31 "Restore complete LoRP-FSD v3 implementation"`.
- Net interpretation: `lorp-v3` is the **restored, version-controlled successor** of
  the former on-disk-only `lor-v3` work tree. The "incomplete backup" and the two
  source backups referenced in the task no longer exist on disk; recovery is complete
  enough that they are not needed (see folder-congruency, §A.6 below).

### A.2 Source of truth (now)

`/Users/apena/lorp-v3` is the **single source of truth**. It contains the full
`src/lorp_fsd/` package (19 modules), the test suite (21 test files), the v3 scripts,
all docs, `results_MILP.xlsx`, the `instances/` data, and the C reference under
`reference/LoRPSD`.

### A.3 Current git commit and remote

```
branch:  main  (tracks origin/main)
commit:  ab83d31  Restore complete LoRP-FSD v3 implementation
remote:  origin  git@github.com:alonpena/lorp-v3.git  (fetch + push)
```

### A.4 Remaining untracked files

```
?? checkpoint_phase7_repair_safety_morning.patch
?? checkpoint_phase7_repair_safety_morning_manifest.txt
```

These are a patch + manifest of the Phase 7A morning checkpoint, left in the repo
root. They are not committed. Decide explicitly whether to archive them outside the
repo or commit them; do not silently delete (they may be the only record of an
intermediate state).

### A.5 What should and should NOT be touched

**Do not touch / do not modify** (source of truth, regression-locked):
- `src/lorp_fsd/*.py` — the v3 package.
- `tests/*` — the passing suite.
- `results_MILP.xlsx` — MILP benchmark (read-only data).
- `reference/LoRPSD/*` — C source of truth.
- `instances/`, `instances_old/` — instance data.
- The doc set under `docs/` describing settled decisions (`PYVRP_REPLICATION_SPEC.md`,
  `IMPLEMENTATION_PLAN.md`, `C_SOLVER_AUDIT.md`, `C_CONGRUENCY_TEST.md`, phase handoffs).

**May be created/edited:** new markdown audit/control docs (like this file), and —
only when implementing an approved feature — the specific source files that feature
touches.

**Do NOT commit to git:** `outputs/`, `pipeline_out/`, `.venv/`, `__pycache__/`
(already in `.gitignore`).

### A.6 Was anything important lost during repo restoration?

No evidence of loss in the working artefacts:
- `py_compile` over all `src/lorp_fsd/*.py` → **OK** (no syntax breakage).
- Targeted repair tests → **15 passed**.
- Full non-integration suite → **193 passed, 32 deselected**.
- All 19 modules and 21 test files are present and consistent with the phase handoffs.

Caveat: the prior "225 passed" figure (Phase 7A handoffs) is now **193 passed + 32
deselected** in the non-integration run. The handoffs already flagged this drift
(possible test reorg/removal). It is not a restoration regression per se — the
non-integration default deselects the 32 integration (solve-driven) tests. Confirm
the integration count separately if a "total passed" figure is needed for the meeting.

---

## B. Development history (reconstructed from the `.md` files)

The project was rebuilt cleanly as **LoRP-FSD v3**, a new `src/lorp_fsd/` package that
does not import the legacy root modules. Phases (all dated 2026-06-05 unless noted):

### B.0 C congruency phase (`HANDOFF_C_CONGRUENCY_PHASE.md`, `C_CONGRUENCY_TEST.md`)
Verified the original C/Gurobi solver, Excel row 0 (sheet `LoRP-FSD`), and
`r40x5a-1.dat` are parameter-congruent **before** writing any PyVRP. The C binary
could not run (Linux x86-64 ELF on macOS arm64 → `exec format error`), so row 0 was
reproduced by an **exact static reconstruction** from `.dat` geometry + C formulas +
row-0 CLI params: `Z = 95.3087 (routing) + 0 (vehicles) + 300 (depots) + 0 (DA) =
395.3087`, equal to Excel `UB = 395.309`. Verdict: **GO** for PyVRP Phase 1 under
fixed-facility design.

### B.1 Phase 1 — preprocessing (`HANDOFF_PHASE1_PREPROCESSING.md`)
Created `geometry`, `dat_parser`, `scaling`, `facility_sizing`, `experiment_config`,
`excel_loader`, `instance`. C-compatible `.dat` parsing (1-based IDs, trailing-flag
validation, path resolution), Arslan scaling (`scale = 100/max_dist`), the C 5-size
facility formula, Excel `LoRP-FSD` row loading with **real depot IDs from labels**.
Row-0 regression constants locked (scale `0.79745222`, cap 875, depot cost 300, UB
395.3087). 38 Phase-1 tests; full suite 157 passed.

### B.2 Phase 2 — PyVRP builder (`HANDOFF_PHASE2_PYVRP_BUILDER.md`)
Created `da_options`, `pyvrp_builder`. Capacity-relaxed model: routing-vehicle
decomposition `floor(Cap_i/Q)` + residual; DA options per feasible `(depot,client)`
with `dist_scaled ≤ R`; zero-return DA; single-client DA binding;
`forbidden_routing_assignments` support; dual-channel distance/duration encoding.
Row-0 smoke reproduced the C-optimal structure (1 route + 38 DA). 17 Phase-2 tests;
full suite 174 passed.

### B.3 Phase 3 — parser / cost / audit (`HANDOFF_PHASE3_PARSER_AUDIT.md`)
Created `solution_parser`, `cost_reconstruction`, `capacity_audit`, `feasibility`.
Ex-post semantic parsing, mixed-unit objective reconstruction, `GAP` vs
`RELAXATION_DEVIATION` metric (with `NEGATIVE_GAP_MODELING_INCONSISTENCY` only on a
material negative gap), aggregate capacity audit (routing + DA), full feasibility
audit + penalty-distance diagnostic. Row-0 `Z_PyVRP = 395.3087`, GAP ≈ 0. 16 tests;
full suite 190 passed.

### B.4 Phase 4 — repair (`HANDOFF_PHASE4_REPAIR.md`)
Created `repair`; extended `feasibility` with `client_has_service_option` /
`make_feasibility_checker`. Savings formula (first/internal/last/single), candidates
only from overloaded depots, greedy largest-weighted-saving selection until excess
covered, stranding skip → `REPAIR_INFEASIBLE`. Removals are routing-only forbids; the
client is never deleted. 9 tests; full suite 199 passed.

### B.5 Phase 5 — iterative runner + artifacts (`HANDOFF_PHASE5_ROW_RUNNER_ARTIFACTS.md`)
Created `runner`, `artifacts`, `plotting`, `scripts/run_row.py`. The build→solve→
parse→reconstruct→audit→repair→rebuild loop with statuses `FEASIBLE` /
`REPAIR_INFEASIBLE` / `STUCK_NONCAPACITY_VIOLATION` / `MAX_ITERATIONS`, per-iteration
JSON + routes/assignments CSV + solution PNG. Row 5 demonstrated capacity repair
succeeding but leaving a route-length violation → `STUCK_NONCAPACITY_VIOLATION`. 6
tests; full suite 205 passed.

### B.6 Phase 6 — batch (`HANDOFF_PHASE6_BATCH.md`, `HANDOFF_TO_NEXT_AGENT_PHASE6_BATCH.md`)
Created `batch` + `scripts/run_first_n.py`, `run_random_sample.py`, `run_full_excel.py`,
`compare_with_milp.py`. Per-row try/except → `ERROR` status, resumable checkpoints,
consolidated CSV/XLSX + aggregate summary. 14 tests; full suite 219 passed. Documented
that full batch at 3×30s ≈ 50+ hours.

### B.7 Phase 7A — repair safety (`HANDOFF_PHASE7_REPAIR_SAFETY.md`,
`PHASE7_ROUTE_LENGTH_REPAIR_DESIGN.md`)
Added `RepairCandidateSafety` diagnostics + 4 policies (`baseline`, `safe_length`,
`safe_capacity_release`, `safe_both`), rejection reasons (`same_depot_DA_risk`,
`no_length_feasible_alternative`, `strands_client`), cross-iteration
`rejected_repair_candidates`, batch/artifact diagnostic fields, `--repair-policy`
CLI plumbing. Suite reached 225 passed at that time. **Phase 7B** (post-rerun
rollback/backtracking, `forbidden_depot_assignments`, local search) **not** done.

### B.8 Phase 7A sample assessment + 2026-06-08 morning audit
(`HANDOFF_PHASE7A_SAMPLE_ASSESSMENT.md`, `HANDOFF_2026_06_08_MORNING.md`)
Attempted k=20 30s/3run baseline and safe_both samples — **both stalled at row 228**
(`r30x5a-1.dat`, ~2h wall, `PenaltyBoundWarning`). Fell back to fast (5s/1run) k=20
comparison. Full Excel verdict: **NO-GO** until a per-row wall-time timeout exists.

### B.9 Current outputs / results
See §K. Headline: feasible rows are within ~0.4–0.6% mean GAP of the MILP UB (max ~4%),
no negative-gap inconsistency flagged anywhere, but the two real (30s/3run) samples
never completed because of the row-228 stall.

---

## C. C / MILP source-of-truth logic

Authoritative model: `det_LoRP_DSD()` in `reference/LoRPSD/stcmodels.cpp`, reached via
`-original 0` (Excel sheet `LoRP-FSD`). Audited in `C_SOLVER_AUDIT.md`, confirmed in
`C_CONGRUENCY_TEST.md`.

- **LoRP-FSD / deterministic sizing model:** deterministic Location-Routing with depot
  **sizing** decisions plus **direct allocation**. Binary `Y[depot][size]` chooses one
  size per open depot.
- **`original = 0`:** selects the LoRP-FSD/sizing model. `original = 1` would select the
  standard LoRP (`createmodelnew()`) with no depot sizing — not what the Excel sheet holds.
- **`problemID = 0` Arslan scaling:** `dist_scaled = dist_original · 100 / max_dist`,
  where `max_dist` is the max Euclidean distance over **all** depot/client nodes. For
  row 0, `max_dist = 125.399362`, `scale = 0.79745222`.
- **R and Length are in scaled units:** the model compares the DA radius and route
  length against the already-scaled `dist`/`t`. Do **not** convert `R/scale` except for
  plotting.
- **Objective components** `Z = Cost1 + Cost2 + Cost4 + DirectALL`:
  - **Routing cost** `Cost1 = Σ WR · dist_scaled · X` (routing arcs).
  - **Direct allocation cost** `DirectALL = Σ WA · dist_scaled(depot,client) · A`
    (one-way assignment).
  - **Vehicle fixed cost** `Cost2 = Σ vehiclesfixed · X[depot][customer]` (one per
    routing departure arc; `vehiclesfixed *= VFX`).
  - **Depot sizing/opening cost** `Cost4 = Σ dep_cost[i][size] · Y[i][size]`.
- **Facility sizing formula** (`files.cpp::ReadData_sizing`, `facsize = 5`):
  `dep_cap[i][s] = base_QD_i · (1 + (s−2)·0.25)` for `s=0..4` → multipliers
  `{0.50, 0.75, 1.00, 1.25, 1.50}` (output sizes 1..5); cost
  `dep_cost[i][s] = cost_i + ((dep_cap−base)/(2·base))·(totalfix/T)`.
- **Direct allocation is assignment, not a route:** `A[client][depot] ∈ {0,1}`, no
  return arc, no client-client DA travel, no DA vehicle fixed cost. Each client is
  routed **or** DA, exactly once (`Σ f + Σ A == 1`).
- **Depot capacity = routing + DA shared demand:**
  `Σ (f[j][i] + A[i][j]) · demand_i ≤ Σ dep_cap[j][s] · Y[j][s]`. Moving a client from
  routing to DA **at the same depot does not free depot capacity**.
- **Per-route vehicle capacity:** `W[i][j] ≤ Q · X[i][j]` (single-commodity load-flow,
  `stcmodels.cpp:782`). PyVRP's native per-vehicle cap `Q` **matches** the C model — it
  is not an extra constraint.
- **Why row-0 congruency matters:** it is the regression anchor proving the Python
  pipeline reproduces the C objective to full precision (UB 395.3087) under the exact
  flags, scaling, units, and the per-route capacity assumption — the precondition for
  trusting every later PyVRP comparison.

---

## D. Excel loading logic

Module: `excel_loader.py` (Phase 1).

- Reads **only** the `LoRP-FSD` sheet of `results_MILP.xlsx`.
- One Excel row → one run configuration; columns mapped by name (`F_R`, `F_A`, `R`,
  `Length`, `VFX`, `UB`, `LB`, status, the four MILP cost components, and the
  per-depot slots).
- **Instance name resolution:** Excel names do not always match files exactly; some have
  a `coord` prefix. `dat_parser.resolve_dat_path` resolves by EXACT → COORD_PREFIX →
  SUFFIX_GLOB, reporting MISSING / AMBIGUOUS and **never guessing** an unsafe match.
  Rows are **not** dropped on filename mismatch.
- **Real depot IDs from Excel labels:** the `Depot1..Depot4` cells hold labels like
  `'d5'`; the loader parses `'d5' → 5`. Slot position is **not** the depot ID (e.g. row
  0 `Depot4 = 'd5'` → real depot 5).
- **Selected depot sizes/capacities:** read from `sizeD*`/`CapD*` and cross-checked
  against the recomputed C sizing formula in `instance.build_facility_design`.
- **UB/LB/cost-component interpretation:** `UB = ObjVal`, `LB = ObjBound`; distance
  components (`Cost Routing`, `Cost Direct All`) are in **scaled** units; fixed
  components (`Cost (Vehicles)`, `Cost (Depots)`) are **raw**. Never divide by scale.
- **`problemID` is not an Excel column:** injected as `0` (Arslan); any other value
  raises `NotImplementedError`.
- **Missing/ambiguous `.dat` handling:** flagged, not silently skipped; a row whose
  instance cannot be resolved becomes an `ERROR` row at batch time, not a crash.

---

## E. Instance building logic

Modules: `dat_parser.py`, `geometry.py`, `scaling.py`, `facility_sizing.py`,
`instance.py` (Phase 1).

- **`.dat` parser:** reads the C format — counts, depot coords, client coords, `Q`,
  depot capacities, client demands, depot fixed costs, vehicle fixed cost, trailing
  flag. Validates the trailing flag where present.
- **Depot/client IDs:** 1-based, matching the C output convention (depots `1..T`,
  clients `1..N`).
- **Demands, capacities, fixed costs:** preserved per node from the `.dat`.
- **Scaled geometry:** `build_scaled_geometry` computes `max_dist` over all node pairs,
  `scale = 100/max_dist`, and scaled-distance lookups plus integerization
  (`PYVRP_INT_SCALE = 10_000`).
- **Facility design from Excel-selected depots:** `build_facility_design` opens exactly
  the Excel-selected depots at their selected sizes, recomputes capacities/costs via the
  C formula, and cross-checks against Excel `CapD*` / `Cost (Depots)`.
- **C-compatible preprocessing:** the goal throughout is byte/number fidelity to the C
  model so PyVRP results are comparable to the MILP Excel benchmark.

---

## F. PyVRP modelling logic

Modules: `da_options.py`, `pyvrp_builder.py` (Phase 2).

- **Relaxed MD-VRP approximation:** for a fixed Excel facility design, PyVRP opens the
  selected depots and serves all clients. The shared depot-capacity constraint
  (`routing + DA ≤ Cap_i`) is **not** representable in PyVRP, so it is **relaxed** at
  build time and clawed back by repair.
- **Routing vehicle types by depot:** one routing profile per open depot, vehicles bound
  to that depot (`start_depot = end_depot`).
- **Vehicle capacity decomposition:** `n_full = floor(Cap_i/Q)` vehicles of capacity
  `Q`, plus one residual vehicle of capacity `Cap_i − n_full·Q` if positive — integer
  arithmetic keeps routing capacity ≤ `Cap_i`.
- **Direct allocation as artificial one-client vehicle/profile:** one profile per
  feasible `(depot,client)` pair with `dist_scaled ≤ R`, a single vehicle of capacity
  `demand_client`, two edges only.
- **Zero-return DA:** outbound edge cost `round(F_A · dist_scaled · 1e4)`; return edge
  `distance=0, duration=0`.
- **Binding DA vehicle to one client:** the per-pair profile leaves every other client at
  PyVRP's `2^44` missing-edge sentinel, so the DA vehicle physically cannot serve any
  other client. The parser re-checks and flags `DA_ASSIGNMENT_BINDING_VIOLATION`.
- **Dual-channel distance/duration design:** the **distance** channel carries scaled
  geometric distance (drives `max_distance = round(Length·1e4)`); the **duration**
  channel carries weighted cost (`round(F·dist_scaled·1e4)`) with `unit_distance_cost=0`,
  `unit_duration_cost=1`. This keeps the length constraint and the cost objective
  independent and correct for all `F_R`/`F_A`.
- **Why final cost is reconstructed ex-post:** PyVRP's internal objective is an
  **integer** approximation that includes artificial DA arcs and rounding. The reported
  `Z_PyVRP` is rebuilt from semantic decisions on **continuous scaled geometry**
  (`cost_reconstruction.py`); the PyVRP integer objective is never the final number.
- **What PyVRP cannot natively model:** facility opening/sizing binaries, per-client
  service-mode choice (routing vs DA), shared depot capacity across both modes, one-way
  DA assignment cost outside route distance, and exact C-style component reporting.
  Hence v3 is a relaxation + audit + repair heuristic, not a native LoRP-FSD solver.

---

## G. Relax-and-repair logic

Modules: `runner.py` (loop), `repair.py` (selection). Spec: `PYVRP_REPLICATION_SPEC.md`
§§8–11.

1. **Initial relaxed solve:** build with empty `forbidden`, solve
   (`num_solve_runs` seeds × `seconds_per_run`; keep best feasible, else min-cost).
2. **Parse solution** into routing/DA semantic records.
3. **Reconstruct cost** in scaled MILP-comparable units.
4. **Audit capacity and feasibility** (aggregate `routing + DA`, route length, route
   capacity, DA radius, binding, service-exactly-once, penalty distance).
5. **Overloaded depot detection:** per depot `excess = max(0, demand_total − Cap)`.
6. **Routing savings:** `compute_route_savings` — marginal scaled-distance saving of
   removing each client (first/internal/last/single-client), weighted by `F_R`.
7. **Hard forbidden routing assignment `(depot, client)`:** selected removals are added
   to `forbidden_routing_assignments`; the next rebuild creates no routing edge for those
   pairs. It is a **hard structural restriction**, not a soft penalty, not a live-model
   arc deletion.
8. **Customer is not deleted:** a forbidden pair only blocks routing of that client from
   that depot; the client stays required and may be served by DA (incl. same depot) or
   routed from another non-forbidden depot.
9. **Rebuild and re-solve loop:** rebuild PyVRP with the accumulated forbidden set,
   re-solve, re-audit.
10. **Max iterations:** loop up to `max_repair_iterations`.
11. **Status classification** (see §J).

Ranking is largest weighted saving first, deterministic tie-break
`(-saving, depot_id, route_id, client_id)`. Selection covers `Σ removed_demand ≥ excess_i`,
skipping any removal that would strand a client.

---

## H. Ex-post audit logic

Modules: `solution_parser.py`, `cost_reconstruction.py`, `capacity_audit.py`,
`feasibility.py` (Phase 3).

- **Served exactly once:** every client served by exactly one routing or DA assignment.
- **Missing / duplicate clients:** sets reported by the parser.
- **Route capacity:** per route `demand ≤ vehicle capacity`.
- **Route length:** reconstructed scaled distance `≤ Length + tol`.
- **DA radius:** `dist_scaled(depot, client) ≤ R` for each DA assignment.
- **DA binding:** DA route must be length 1, correct bound client, within radius — else
  `DA_ASSIGNMENT_BINDING_VIOLATION`.
- **Depot capacity:** per depot `demand_routing + demand_DA ≤ Cap_i`; compute `excess`
  and `overloaded_depots`.
- **Penalty-distance suspected:** `solver_distance_scaled > max(1e6, 1000·Length)` flags
  `PENALTY_DISTANCE_SUSPECTED` (missing arcs / penalty routes).
- **Objective reconstruction:** `Z = F_R·Σroute_dist + F_A·ΣDA_dist + vehicles(raw) +
  depots(raw)`; distance terms scaled, fixed terms raw; never scale fixed terms.
- **GAP vs RELAXATION_DEVIATION:** `RELAXATION_DEVIATION = (UB − Z)/UB` while not fully
  feasible; `GAP = (Z − UB)/UB` once fully feasible. A material negative final gap flags
  `NEGATIVE_GAP_MODELING_INCONSISTENCY`; a ~1e-6 negative reading from Excel's 3-decimal
  UB rounding is absorbed by `negative_gap_tol = 1e-4`.

---

## I. Ex-ante validation logic

Modules: `feasibility.py`, `repair.py` (Phase 4 + 7A). Spec: `PYVRP_REPLICATION_SPEC.md`
§10, `PHASE7_ROUTE_LENGTH_REPAIR_DESIGN.md` §§6–7.

Run **before** accepting a cut:

- **Stranding check** (`client_has_service_option`, all policies): a client is
  serviceable if routable from some non-forbidden depot **or** DA-feasible
  (`dist_scaled(h,j) ≤ R`) from some depot.
- **`diagnose_repair_candidate`** (Phase 7A, when policy ≠ baseline) computes:
  - `same_depot_DA_risk = dist_scaled(depot,client) ≤ R`
  - `length_serviceable_after_cut`: exists depot `h` with `dist_scaled(h,j) ≤ R`, or
    `(h,j)` not forbidden and `2·dist_scaled(h,j) ≤ Length` (singleton route feasible).
- **Same-depot DA risk** matters because forbidding routing of `j` from overloaded depot
  `i` does **not** release aggregate capacity if `j` is DA-feasible from `i`: PyVRP can
  reassign `j` to same-depot DA, leaving `demand_total_i` unchanged.

**Repair policies:**

| Policy | Rejects a candidate if |
|---|---|
| `baseline` | it strands the client (no service option) |
| `safe_length` | client has no length-feasible alternative after cut |
| `safe_capacity_release` | `same_depot_DA_risk` (DA-feasible from same depot) |
| `safe_both` | either of the above (recommended) |

---

## J. Classification of results

Statuses (`runner.py` / `batch.py`):

- **`FEASIBLE`** — fully feasible solution; report `GAP`, all feasibility flags True.
- **`REPAIR_INFEASIBLE`** — an overloaded depot's excess cannot be covered with
  non-stranding (and, under safe policies, safe) removals; `repair_failed=True`.
- **`STUCK_NONCAPACITY_VIOLATION`** — capacity satisfied but a non-capacity constraint
  (typically route length) violated; capacity-only repair cannot fix it
  (`stuck_noncapacity=True`, `route_length_feasible=False`).
- **`MAX_ITERATIONS`** — repair budget exhausted while still capacity-infeasible.
- **`ERROR`** — row-level exception (e.g. instance not found, build/solve crash);
  `error_message` carries details; never crashes the batch.

**Negative-gap flag:** `NEGATIVE_GAP_MODELING_INCONSISTENCY` is raised only when a
**final feasible** solution materially beats the MILP UB on an optimal row (relative
tol `1e-4`). It signals remaining relaxation / reconstruction / scaling / data mismatch
— not normal rounding. **GAP is meaningful only for `FEASIBLE` rows**; for non-feasible
rows the comparison metric is `RELAXATION_DEVIATION` (which can be negative when the
kept solution is penalized/infeasible — a signal, not a clean relaxation).

---

## K. Existing results / outputs

Read from checkpoint/summary files only — **no rerun**.

| Run | Rows | Status counts | Completeness | Notes |
|---|---|---|---|---|
| `smoke3` | 3 | FEASIBLE 3 | complete | all `r40x5a-1.dat` variants, feasible at iter 0 |
| `smoke_phase7_sample5` | 5 | FEASIBLE 4, STUCK 1 | complete | rows [51,228,457,501,563]; mean GAP 0.0052, max 0.0208; row 228 STUCK |
| `phase6_sample20_baseline` | 7/20 | FEASIBLE 4, REPAIR_INFEASIBLE 3 | **partial** (stalled row 228) | no consolidated/summary |
| `phase7_sample20_safe_both` | 7/20 | FEASIBLE 4, REPAIR_INFEASIBLE 3 | **partial** (stalled row 228) | no consolidated/summary |
| `phase6_sample20_baseline_fast` | 20 | FEASIBLE 12, REPAIR_INFEASIBLE 4, STUCK 1, MAX_ITER 2, ERROR 1 | complete | 5s/1run; ERROR row 1149 `r40x5b-2.dat` |
| `phase7_sample20_safe_both_fast` | 20 | FEASIBLE 12, REPAIR_INFEASIBLE 5, STUCK 1, MAX_ITER 1, ERROR 1 | complete | 5s/1run; same ERROR row |
| `diag_row5` | row 5 | RELAXED_INFEASIBLE iters | complete | **only run with solution PNGs** |

**`phase7a_sample20_fast_comparison.md` (baseline vs safe_both, fast k=20):**
FEASIBLE 12 = 12; REPAIR_INFEASIBLE 4 → 5; STUCK 1 = 1; MAX_ITER 2 → 1; gap_feasible_mean
0.00638 both; negative_gap 0 both; `capacity_not_freed` 7 → 0 (safe_both removes them);
`length_unsafe_candidate` 0 → 18 (filter active). Only status change: row 407
`coord50-5-3.dat` MAX_ITERATIONS → REPAIR_INFEASIBLE.

**Honest meeting story:**
- *Can show:* the two complete `_fast` k=20 consolidated tables + summaries, the
  `smoke_phase7_sample5` summary, the `phase7a_sample20_fast_comparison.md` table, and
  the `diag_row5` solution plots. Headline: on feasible rows, PyVRP is within ~0.4–0.6%
  mean GAP of the MILP UB (max ~4%), and **no negative-gap inconsistency** anywhere.
- *Cannot show:* any complete real (30s/3run) sample or a full all-instance run — both
  real samples stalled at row 228 (`r30x5a-1.dat`).

---

## L. Tests

Run this session (fast only; no long experiments):

```
.venv/bin/python -m py_compile src/lorp_fsd/*.py
  → PYCOMPILE_OK

.venv/bin/python -m pytest tests/test_repair_savings.py tests/test_phase7_repair_safety.py -q
  → 15 passed in 5.53s

.venv/bin/python -m pytest -q -m "not integration"
  → 193 passed, 32 deselected in 19.09s
```

The 32 deselected are `@pytest.mark.integration` tests that drive real PyVRP solves.
End-to-end convergence on hard instances, per-row timeout behaviour, and full-Excel
completion are **not** asserted by the unit suite.

---

## M. What is NOT implemented

Explicitly absent (confirmed in handoffs + source):

- **Per-row wall-time timeout** in batch — one slow row (228) blocks an entire run.
- **`repair_trace.csv`** — no temporal trace of which pairs were forbidden in which
  iteration.
- **Tabu list** — `rejected_repair_candidates` has no tenure, no expiry, no aspiration;
  the forbidden set is monotonic for the row.
- **Soft arc penalties** — repair only hard-restricts; no high-factor penalty path.
- **Rollback / backtracking** (Phase 7B) — `max_repair_attempts` exists but is reserved
  (always 1, no internal logic).
- **Full local search / ALNS / LNS / SA.**
- **`forbidden_depot_assignments`** (depot-level both-mode cut).
- **Simple HTML UI** — only partial Streamlit fragments; no consolidated viewer.
- **Full all-instance final run** — only partial/sample runs exist.

---

## N. Next implementation priority (queue)

1. **Per-row timeout** in `batch.py` — record a hard row as `ERROR`/`TIMEOUT` instead of
   stalling. Unblocks every larger run. Highest priority.
2. **Consolidate existing results** — build consolidated/summary from the partial
   checkpoints (no rerun).
3. **`repair_trace.csv`** — per-iteration auditability of forbidden pairs.
4. **Selected plots** — for REPAIR_INFEASIBLE / STUCK / negative-gap instances.
5. **Simple HTML report** — browse instances, status, costs, plots.
6. **Tabu expiry** — tenure ~ f(n_depots), aspiration on best cost.
7. **Soft arc penalties** — high-factor cost as an alternative to hard restriction.
8. **Full all-instance run** — only after (1) makes it safe.

---

## O. Explicación para el profesor (oral, máx. 12 viñetas)

1. El modelo original es **LoRP-FSD**: localización-ruteo con **decisión de tamaño de
   depósito** y **asignación directa**, resuelto en C con Gurobi (`original=0`).
2. Usa **escalamiento de Arslan** (`problemID=0`): toda distancia se multiplica por
   `100/max_dist`; el radio `R`, la longitud `Length` y los costos del Excel están en
   esas unidades escaladas.
3. La **asignación directa (DA)** es una asignación binaria cliente→depósito, costo de
   ida solamente, sin arco de retorno, sin viaje cliente-cliente y sin costo fijo de
   vehículo.
4. La **capacidad del depósito es compartida**: `demanda_ruteo + demanda_DA ≤ Cap`.
   Mover un cliente de ruteo a DA en el **mismo** depósito no libera capacidad.
5. Verificamos **congruencia exacta de la fila 0** contra el C: `UB = 395.3087`
   reproducido al detalle (ruteo 95.31 + depósitos 300). Esa fila es nuestro ancla de
   regresión.
6. PyVRP **no puede** modelar tamaño de depósito, elección de modo por cliente, ni
   capacidad compartida; por eso construimos un MD-VRP **relajado** y reparamos después.
7. Codificamos costos con **doble canal**: distancia (controla `Length`) y duración
   (controla el costo con pesos `F_R`/`F_A`); el costo final se **reconstruye ex-post**
   con geometría continua, no se toma del objetivo entero de PyVRP.
8. La **reparación por ahorros** prohíbe asignaciones de ruteo `(depósito, cliente)` en
   depósitos sobrecargados; el cliente **no se elimina**, sigue disponible por DA u otro
   depósito.
9. **Fase 7A** añade chequeos de seguridad: rechaza cortes que dejarían al cliente sin
   opción de longitud factible, y detecta el riesgo de DA del mismo depósito que no
   libera capacidad.
10. Clasificamos cada fila: `FEASIBLE`, `REPAIR_INFEASIBLE`, `STUCK_NONCAPACITY`,
    `MAX_ITERATIONS`, `ERROR`. El **GAP solo tiene sentido en filas FEASIBLE**.
11. Resultados honestos: en filas factibles el GAP medio es ~0.4–0.6% (máx ~4%) y **no**
    hay inconsistencia de gap negativo; pero las muestras reales (30s/3run) **no
    terminaron** por una fila que se cuelga (fila 228, `r30x5a-1.dat`).
12. Lo más urgente es un **timeout por fila** para poder correr lotes grandes sin que una
    sola instancia bloquee todo; luego consolidar resultados y, recién después, la corrida
    completa.

---

*End of audit. No source files were modified producing this document.*
