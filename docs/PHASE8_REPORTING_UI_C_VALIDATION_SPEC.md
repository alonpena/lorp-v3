# Phase 8 Spec — Reporting, Full Run, Plots, UI, C/PyVRP Validation

**Status:** specification only. Do **not** implement until approved.
**Working dir:** `/Users/apena/lorp-v3`.
**Companions:** `FULL_IMPLEMENTATION_AUDIT_20260608.md`, `NEXT_AGENT_RULES.md`,
`PYVRP_REPLICATION_SPEC.md`, `C_SOLVER_AUDIT.md`, `C_CONGRUENCY_TEST.md`.

This spec defines exactly what to build next for per-row reporting, per-instance
output folders, full-run output + HTML index, plots, an interactive single-row UI,
and a C/PyVRP validation interface. The sibling spec
`PHASE8_REPAIR_PENALTY_TABU_HTML_SPEC.md` covers the repair-side changes (soft
penalty, tabu, conflictive-client assessment). Read both together.

**Hard prerequisite:** none of the full-run or large-batch items run before the
**per-row timeout** (P1) exists. The current `_solve_multi` already bounds each
solve with `MaxRuntime(seconds_per_run)`, yet row 228 (`r30x5a-1.dat`) overran a
~450s nominal budget to ~2h — so the leak is **outside** the bounded solve (build,
parse, or the repair loop). The timeout must therefore wrap the **whole row**
(process-level), not a single solve.

---

## 1. Per-row result contract

For every solved Excel row, produce a complete row-level report. Source modules:
`runner.RowRunResult`, `cost_reconstruction`, `capacity_audit`, `feasibility`,
`repair`, `pyvrp_builder.BuildInfo`. Fields:

- `row_id`, `instance_name`, resolved `.dat` path
- MILP: `UB`, `LB`, `status`, `gap` (from `results_MILP.xlsx`)
- MILP cost components (Excel): `Cost Routing`, `Cost (Vehicles)`, `Cost (Depots)`,
  `Cost Direct All`
- PyVRP reconstructed components: routing cost, DA cost, vehicle fixed cost, depot
  fixed cost, **total**
- `GAP` if feasible; `RELAXATION_DEVIATION` if not feasible
- `negative_gap_flag`
- `final_status` (`FEASIBLE` / `REPAIR_INFEASIBLE` / `STUCK_NONCAPACITY_VIOLATION` /
  `MAX_ITERATIONS` / `ERROR` / new `TIMEOUT`)
- `n_repair_iterations`, `total_runtime`, per-iteration solve runtime
- `repair_policy`
- builder counts: `n_routing_vehicles_generated`, `n_da_options_generated`,
  `n_used_routing_routes`, `n_da_assignments`
- depot usage table (per depot: cap, routing demand, DA demand, total, % usage, excess)
- checks: route length, route capacity, DA radius, demand satisfaction, service
  exactness, `penalty_distance_suspected`
- repair: `rejected_repair_candidates` (with reasons), `selected_repair_candidates`,
  current `forbidden` / `penalized` / `tabu` pairs (whichever the active mode uses)

The contract is the canonical schema; `report.json` (§2) is its serialization, and
every other artefact (CSV/HTML/plots) is a projection of it. Implement it as a single
`RowReport` dataclass so JSON, CSV, and HTML never diverge.

---

## 2. Per-instance output folder

For every row/instance run:

```
outputs/<run_id>/<row_id>_<instance>/
  report.md          # human-readable summary
  report.json        # full RowReport serialization (canonical)
  cost_breakdown.csv # MILP vs PyVRP per component + delta
  depot_usage.csv    # per depot: cap, routing/DA/total demand, %usage, excess
  route_profiles.csv # per routing route: depot, sequence, demand, scaled dist, checks
  client_assignments.csv  # per client: service mode, depot, demand, dist_scaled, checks
  feasibility_checks.csv  # one row per named check + pass/fail + short explanation
  iteration_summary.csv   # per iteration: status, cost, excess, selected/rejected counts
  repair_trace.csv        # per iteration × pair: action (forbid/penalize/tabu), reason
  iteration_00_solution.png
  iteration_01_solution.png
  ...
  index.html         # per-instance page linking the above + embedding plots
```

`<row_id>_<instance>` replaces the current `<instance_name>` directory so multiple
Excel rows sharing one `.dat` no longer collide (today two rows on `r40x5a-1.dat`
overwrite each other's artefacts). `repair_trace.csv` is new (P3).

---

## 3. Full-run output

```
outputs/<run_id>/
  checkpoint.csv       # existing, resumable
  consolidated.csv     # existing
  consolidated.xlsx    # existing
  summary.json         # existing
  summary.md           # existing
  index.html           # NEW: full-run browser
  plots/               # NEW: full-run aggregate plots (§4)
  instances/<row_id>_<instance>/...   # per-instance folders (§2)
```

The full-run `index.html` shows:
- a table of all rows (one line per row)
- filters: by status, by instance, by negative-gap flag, by repair-iteration count
- sortable columns: `GAP`, `runtime`, `status`
- a link from each row to its per-instance `index.html`

Static HTML only — no server. Generate from `consolidated.csv` + per-instance
`report.json` files (so it can be regenerated without rerunning solves).

---

## 4. Plot requirements

Generated only when `--plots` is requested (default off in batch).

Single-row / per-instance:
- solution plot per iteration (already exists in `plotting.py`)
- depot capacity usage bar/table
- cost breakdown MILP vs PyVRP (grouped bars per component)

Full-run aggregate (under `plots/`):
- GAP distribution (histogram, FEASIBLE rows only)
- status-count bar plot
- runtime distribution (histogram)
- DA-vs-routing mix plot (share of clients served each mode)
- repair-iterations histogram
- rejected-candidate-reasons bar plot

All via the existing Agg/matplotlib backend. Plots are projections of `report.json`
/ `consolidated.csv`; never recompute costs inside the plotter.

---

## 5. Interactive UI requirement

Alonso wants an interactive UI, HTML-first. Two levels:

**A. Static HTML report (primary).**
- Generated after a run; no server needed.
- Browse rows, per-instance reports, embedded plots.
- This is §3 `index.html` + §2 per-instance `index.html`.

**B. Lightweight interactive local UI (secondary).**
- Run a single row on demand.
- Choose Excel row, `seconds`, `runs`, `max_iter`, `repair_policy`.
- Open generated plots and tables; compare MILP vs PyVRP.
- Show a one-line explanation of each feasibility check.

Existing assets: legacy `app_capacity_repair_solver.py` (Streamlit, imports **legacy**
root modules — `dat_loader`, `instance_adapter`, `run_capacity_repair_batch`, not the
v3 `lorp_fsd` package) and stale `pipeline_out/streamlit_demo_row*` outputs.
**Recommendation:** do not extend the legacy Streamlit app. Build the static HTML
report first (level A); only if a live runner is needed, add a thin level-B UI that
calls the v3 `runner.run_row_from_excel` directly. Prefer a minimal Flask/FastAPI
single-endpoint runner over Streamlit so the HTML stays the primary surface. See ADR
`0005-static-html-reporting.md` in the sibling spec.

---

## 6. Single-row run UI

The single-row UI (level B, or a CLI that emits the same HTML) must:
- select a `row_id` from `results_MILP.xlsx`
- show MILP parameters: `F_R`, `F_A`, `R`, `Length`, `VFX`, selected depots, sizes,
  capacities
- show the resolved `.dat` path
- run PyVRP via `run_row_from_excel`
- show iteration-by-iteration: cost, feasibility, overloaded depots, selected repair
  candidates, rejected candidates
- show plots
- export the report (the §2 folder)

This is a thin wrapper over the existing runner; it adds **no** modelling logic.

---

## 7. C solver validation interface

Spec a script `scripts/c_command_for_row.py` (or `validation/c_interface.py`) that,
given a `row_id`, generates the exact C command from Excel + resolved `.dat`:

```bash
reference/LoRPSD/LoRPSD \
  -results outputs/<run_id>/<row>/c_results.txt \
  -problemID 0 \
  -WR <F_R> \
  -WA <F_A> \
  -Radius <R> \
  -instance <resolved_dat_path> \
  -VFX <VFX> \
  -OF 1 \
  -original 0 \
  -model 1 \
  -length <Length>
```

The interface must also:
- print the expected row info (MILP UB/LB/status, cost components, selected depots).
- detect the binary: `file reference/LoRPSD/LoRPSD` → if Linux x86-64 ELF on macOS
  arm64, **print the command but do not run** (matches the C-congruency finding;
  `exec format error`). Offer the mac-arm64 recompile recipe pointer
  (`HANDOFF_C_CONGRUENCY_PHASE.md`).
- if a runnable (recompiled) binary exists, run it and capture the tab-separated
  output row.
- compare the C output row vs Excel row vs PyVRP reconstructed report (§9).

This script generates commands and comparison scaffolding only — it never modifies
the C source.

---

## 8. PyVRP validation interface

For the same row, emit a build/validation summary (from `BuildInfo` + audit):
- build summary (scale, max_dist, active depots, caps)
- vehicle generation by depot (`n_full`, residual capacity)
- DA option count (feasible `(depot,client)` pairs within R)
- routing profile count
- cost-reconstruction inputs (per-arc scaled distances feeding `Z_PyVRP`)
- feasibility audit (all checks from §H of the audit)
- final comparison table (§9)

---

## 9. Compatibility validation report

One report `validation_<row>.md` comparing three columns:

| Quantity | MILP (Excel) | C (expected/run if available) | PyVRP (reconstructed) |
|---|---|---|---|
| objective total | UB | ObjVal | Z_PyVRP |
| routing cost | Cost Routing | Cost1 | cost_routing_pyvrp |
| DA cost | Cost Direct All | DirectALL | cost_da_pyvrp |
| vehicle cost | Cost (Vehicles) | Cost2 | cost_vehicle_pyvrp |
| depot cost | Cost (Depots) | Cost4 | cost_depot_pyvrp |
| selected depots/caps | DepotX/CapDX | emitted `d#`/`s#` | facility_design |
| depot demand usage | DemandDX | per-depot demand sum | capacity_audit totals |
| vehicle count / routes | TotalVehicles | NVE | n_used_routing_routes |
| status / gap | status / gap | Status / MIPGap | final_status / GAP |

Row 0 (`r40x5a-1.dat`) is the locked regression: all three columns must agree at
`Z = 395.3087` (per `C_CONGRUENCY_TEST.md`).

---

## 10. Full-run strategy

1. Do **not** run the full all-instance benchmark before the per-row timeout exists.
2. Implement per-row timeout (P1) — process-level wall guard around the whole row,
   recording `TIMEOUT` status (distinct from `ERROR`).
3. Fast full run with low `seconds/runs` (e.g. 5s/1run) to get a complete scan.
4. Selected conflictive reruns (REPAIR_INFEASIBLE / STUCK / negative-gap) with `--plots`.
5. Longer run only after the timeout is proven on row 228.

---

## 11. Minimal implementation order

| Prio | Item |
|---|---|
| P1 | Per-row timeout (whole-row process guard, `TIMEOUT` status) |
| P2 | Row-level report contract (`RowReport` + `report.json`/`report.md`) |
| P3 | `repair_trace.csv` |
| P4 | Plots per iteration |
| P5 | Static HTML report (per-instance + full-run index) |
| P6 | Single-row UI runner |
| P7 | C/PyVRP validation command interface |
| P8 | Fast full run |
| P9 | Tabu / soft penalties (see sibling spec) |

---

## 12. Grill questions (25)

C/PyVRP congruence:
1. Why was row-0 congruency proven by static reconstruction instead of running the C binary?
2. Are `R` and `Length` in scaled or raw units, and which constraints compare against scaled `dist`?
3. Why are routing/DA costs scaled but vehicle/depot costs raw in the same objective?
4. What is `max_dist` taken over — depot-depot, depot-client, or all node pairs?
5. Does PyVRP's per-vehicle capacity `Q` add a constraint the MILP lacks, or match it?

DA artificial vehicle encoding:
6. Why is each DA option a one-client vehicle with capacity = that client's demand?
7. What stops a DA option from serving a different, closer client (binding)?
8. Why is the DA return arc cost zero, and what would a nonzero return cost corrupt?
9. Why does DA have no vehicle fixed cost in the reconstructed objective?
10. What does `DA_ASSIGNMENT_BINDING_VIOLATION` detect and why is it a parser-level check?

Why cost is reconstructed:
11. Why is `Z_PyVRP` rebuilt from geometry instead of read from PyVRP's objective?
12. What discretization error does `PYVRP_INT_SCALE = 10_000` introduce, and is it reported or searched on?
13. Could the dual-channel (distance vs duration) encoding ever double-count cost? Why not?

Relaxation:
14. What exactly is relaxed in the first PyVRP solve?
15. Why can the first relaxed solve be super-optimal (below UB)?
16. Why is the first-pass metric `RELAXATION_DEVIATION` and not `GAP`?

Repair:
17. What does a `(depot, client)` forbidden assignment actually remove, and what does it leave intact?
18. Why does forbidding routing not delete the client from the problem?
19. Why might routing-only forbidding fail to release aggregate depot capacity?

Why safe cuts matter:
20. What made the row-5 `(4,18)` cut unsafe, and which check now rejects it?
21. Why can `safe_both` turn a `STUCK_NONCAPACITY` row into `REPAIR_INFEASIBLE`, and is that wrong?
22. What is `same_depot_DA_risk` and why does it block capacity release?

Full run needs timeout:
23. Given `MaxRuntime` already bounds each solve, why did row 228 still overrun ~450s to ~2h?

MILP vs PyVRP comparison & negative gap:
24. When is `GAP` meaningful, and when must it never be reported?
25. If a feasible PyVRP solution beats an optimal MILP UB materially, what does that imply and what is flagged?

---

*Stop after writing this spec. No source modified.*
