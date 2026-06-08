# Phase 8 Spec — Soft-Penalty Repair, Tabu, Reporting & HTML

**Status:** specification only. Do **not** implement until approved.
**Working dir:** `/Users/apena/lorp-v3`.
**Companion:** `PHASE8_REPORTING_UI_C_VALIDATION_SPEC.md` (per-row report contract,
per-instance folders, full-run HTML index, C/PyVRP validation). Read both together.
This doc is the **repair-side + reporting + HTML** spec — a practical implementation
plan, not a repo-history audit.

---

## 1. What Alonso wants now

- Replace hard arc deletion/restriction with **penalized routing arcs** where possible.
- Add **tabu search** logic with tenure/expiry.
- **Preserve real objective reconstruction** (geometry-based, never the penalized
  search cost).
- Better reporting **beyond JSON** (text + CSV per instance).
- A **simple HTML UI / report browser**.
- Prepare for a full run — but only **after** the per-row timeout exists.
- Recover/check former **lor-v2 UI** ideas if available.
  - Found in this repo: legacy Streamlit `app_capacity_repair_solver.py` (imports
    legacy root modules, not the v3 `lorp_fsd` package) and stale
    `pipeline_out/streamlit_demo_row*`. No separate `lor-v2` tree exists on disk.
    Treat the legacy Streamlit app as reference only; do not extend it.

---

## 2. Current repair behavior

`src/lorp_fsd/repair.py` + `runner.py`:

- `forbidden_routing_assignments: set[tuple[int, int]]` of `(depot_id, client_id)`.
- The next `build_relaxed_model(..., frozenset(forbidden))` removes routing
  feasibility for that pair (no routing edge); the rebuild is from scratch.
- The **customer is not deleted** — it stays required and may be served by DA (incl.
  same depot) or routed from another non-forbidden depot.
- DA from the **same depot** may still happen unless a safe policy rejects the
  candidate.
- **No tabu, no soft penalty, no `repair_trace.csv`** today. The forbidden set is
  monotonic for the row.

---

## 3. How infeasible cuts are currently prevented

Before accepting a cut (`select_forbidden_assignments`):

- **Stranding check** (`client_has_service_option`, all policies): client keeps ≥1
  option — routing from some non-forbidden depot OR DA within `R`.
- **`safe_length`**: client retains a DA option, or a singleton route `h→j→h` with
  `2·dist_scaled(h,j) ≤ Length` from a non-forbidden depot.
- **`safe_capacity_release`**: rejects `same_depot_DA_risk`, defined as
  `dist_scaled(overloaded_depot, client) ≤ R` — i.e. moving the client from routing to
  DA at the same depot would **not** free aggregate depot capacity (because C/MILP
  capacity is `routing + DA ≤ Cap`).
- **`safe_both`**: applies both the length and capacity-release checks.

---

## 4. Feasibility checks that must always remain ex-post

These are invariant regardless of repair mode (`feasibility.py`,
`capacity_audit.py`, `cost_reconstruction.py`):

- demand satisfaction / every client served exactly once
- no missing clients
- no duplicate clients
- route vehicle capacity
- route length (scaled)
- DA radius (`dist_scaled ≤ R`)
- DA one-client binding
- depot aggregate capacity = routing + DA ≤ `Cap_i`
- objective reconstruction (geometry, scaled distance + raw fixed)
- penalty distance suspected (`> max(1e6, 1000·Length)`)
- negative-gap flag

A soft-penalty or tabu mode changes only **how the search is steered**, never which
checks decide feasibility.

---

## 5. Negative gap rule

- `GAP` is meaningful **only for FEASIBLE rows**.
- A negative gap is acceptable/explainable only if the MILP UB is **suboptimal or
  rounded** (Excel stores UB to 3 decimals; `negative_gap_tol = 1e-4` absorbs that).
- If the MILP row is **optimal** and a feasible PyVRP solution beats the UB
  **materially**, flag `NEGATIVE_GAP_MODELING_INCONSISTENCY`.
- **Never hide** a negative gap — always report the raw value.
- **Never** report an infeasible relaxed solution as `GAP`; use `RELAXATION_DEVIATION`.

---

## 6. Proposed soft penalty design

Instead of removing routing pair `(i,j)`, keep it feasible but penalize it in the
**search** cost only:

```python
# search-only; one of:
penalized_cost = real_cost + penalty_factor * max_scaled_distance
# or multiplicative:
penalized_cost = real_cost * M          # M >> 1
```

Rules:
- The penalty applies **only to the PyVRP builder's search edge cost** (the duration
  channel), never to the distance channel that drives the `Length` constraint.
- The **reported cost ignores the penalty** and is reconstructed from geometry
  (`cost_reconstruction.py`), exactly as today.
- New structure alongside the existing hard set:

```python
penalty_routing_assignments: dict[tuple[int, int], float]   # (depot, client) -> penalty
forbidden_routing_assignments: set[tuple[int, int]]         # retained for hard mode
```

- New config: `repair_mode = "hard_forbid" | "soft_penalty" | "tabu_penalty"`
  (default `hard_forbid` = current baseline).

Builder change (`pyvrp_builder.py`): for a penalized pair, keep the routing edge but
add the penalty to its search-side weighted cost; the geometry/distance and the
`max_distance` limit are unchanged. The parser/audit treat a penalized-but-used arc as
a normal routing arc and reconstruct its **real** cost.

Rationale: a hard forbid can over-constrain (row-407-style premature
`REPAIR_INFEASIBLE`); a soft penalty lets PyVRP still use the arc if no better option
exists, while strongly discouraging it. See ADR `0004`.

---

## 7. Proposed tabu design

```python
tabu_list: dict[tuple[int, int], int]   # (depot, client) -> remaining_iterations
```

- When a candidate is selected, set its tenure.
- Each repair iteration, decrement every tenure.
- When tenure reaches 0, remove the pair from the tabu/penalty set (re-admitted).
- Default tenure = number of active depots, fallback `3`.
- **Aspiration:** allow a tabu move if it improves the best fully-feasible cost found
  so far, or if it resolves an infeasibility no other move can.
- Keep `hard_forbid` available as the baseline; `tabu_penalty` layers tenure/expiry on
  top of the soft penalty (penalize while tabu, expire after tenure).

This converts the monotonic forbidden set into a time-bounded, reversible mechanism —
prerequisite for escaping the local traps that cause `REPAIR_INFEASIBLE` /
`STUCK_NONCAPACITY_VIOLATION`.

---

## 8. Repair candidate scoring

Current: `score = weighted_saving = F_R · routing_saving`.

Proposed richer score (tunable weights, default to recover current behaviour when
extra terms are 0):

```python
score = routing_saving
      + capacity_relief_weight * demand_j
      - same_depot_DA_risk_penalty       # if dist_scaled(i,j) <= R
      - no_alternative_penalty           # if no DA and no singleton-length depot
      - recurrent_conflict_penalty       # pair seen/rejected in prior iterations
      - length_risk_penalty              # small best length margin after cut
```

`recurrent_conflict_penalty` reads from the tabu/rejected history; `length_risk_penalty`
uses `Length − 2·dist_scaled(h,j)` margins. Deterministic tie-break stays
`(-score, depot_id, route_id, client_id)`.

---

## 9. Conflictive-client assessment

New diagnostic (function + report), answering Alonso's question
*"for all depot-conflictive clients, is min distance higher than length?"*

For each overloaded depot × candidate client, emit:
- `dist_to_current_depot` (`dist_scaled(i, j)`)
- `min_dist_any_active_depot` (`min_h dist_scaled(h, j)`)
- `min_singleton_route_length = 2 · min_dist_any_active_depot`
- `singleton_exceeds_length` (`min_singleton_route_length > Length`)
- `has_DA_option_within_R` (`∃h: dist_scaled(h,j) ≤ R`)
- `same_depot_DA_risk` (`dist_scaled(i,j) ≤ R`)
- `length_safe` (passes the `safe_length` check after cut)
- `capacity_release_safe` (not `same_depot_DA_risk`)
- `rejection_reason` if rejected

Output: `conflictive_clients.csv` per instance + an aggregate count in the run summary.
This is pure diagnostics — read-only over geometry + audit; no solver call.

---

## 10. Reporting beyond JSON

Per instance (`outputs/<run_id>/<row_id>_<instance>/`):
- `repair_trace.csv` — per iteration × pair: action (`forbid`/`penalize`/`tabu_set`/
  `tabu_expire`), reason, tenure remaining.
- `repair_summary.txt` — human-readable per-row repair narrative.
- `vehicle_generation.csv` — per depot: `Cap_i`, `Q`, `n_full`, residual capacity.
- `depot_capacity_usage.csv` — per depot: cap, routing demand, DA demand, total,
  %usage, excess.
- `client_service_assignments.csv` — per client: depot, service mode, route/profile id,
  demand, `dist_scaled`.
- `route_profiles.csv` — per routing route: depot, sequence, demand, scaled distance,
  length/capacity checks.
- `da_routing_mix.csv` — per depot/overall: routing demand vs DA demand, client counts.
- `iteration_summary.csv` — per iteration: status, cost, excess, selected/rejected
  counts.

Fields Alonso enumerated, mapped to the above:
- number of generated routing vehicles by depot → `vehicle_generation.csv`
- full/residual vehicle capacities → `vehicle_generation.csv`
- capacity used by depot → `depot_capacity_usage.csv`
- routing demand vs DA demand → `da_routing_mix.csv`
- client, depot, service mode, route/profile id → `client_service_assignments.csv`
- number of iterations, selected per iteration → `iteration_summary.csv`
- rejected candidates + reasons → `repair_trace.csv` / `iteration_summary.csv`
- current forbidden/penalized/tabu list → `repair_trace.csv` (snapshot per iteration)
- final status + GAP / RELAXATION_DEVIATION → `repair_summary.txt` + `report.json`

All are projections of the §1 `RowReport` contract in the companion spec.

---

## 11. Plotting and HTML UI

HTML-first; Streamlit is **not** the main surface.

- Generate static `outputs/<run_id>/index.html`:
  - table of instances with filters by status (and instance / negative-gap /
    iteration count, per companion spec §3)
  - links to per-instance pages
- Each per-instance page (`<row_id>_<instance>/index.html`) shows: summary, status,
  costs (MILP vs PyVRP), capacity table, route table, DA/routing mix, repair trace,
  and embedded PNG plots.
- **No server required** — generated from `report.json` + `consolidated.csv`, so it
  regenerates without rerunning solves.
- Later, compare with old lor-v2 UI if it becomes accessible, but do **not** depend on
  it. See ADR `0005`.

---

## 12. Full run strategy under time pressure

1. Do **not** run the full all-instance benchmark before the per-row timeout.
2. Implement the per-row timeout first (whole-row process guard; new `TIMEOUT`
   status). Note: `_solve_multi` already bounds each solve with `MaxRuntime`, yet row
   228 overran ~450s → ~2h, so the guard must wrap the **entire row**, not one solve.
3. Fast full scan with small `seconds/runs` (e.g. 5s/1run).
4. Selected conflictive reruns (REPAIR_INFEASIBLE / STUCK / negative-gap) with `--plots`.
5. Longer overnight run only if the timeout is proven on row 228.
6. Professor-ready story = fast scan + selected plots + honest limitations.

---

## 13. Minimal implementation order

| Prio | Item |
|---|---|
| P1 | Per-row timeout (`TIMEOUT` status) |
| P2 | `repair_trace.csv` + text/CSV reports (§10) |
| P3 | Conflictive-client assessment (§9) |
| P4 | Selected plots |
| P5 | Static HTML report (§11) |
| P6 | Soft penalty mode (§6) |
| P7 | Tabu expiry (§7) |
| P8 | Full fast run |
| P9 | Longer run |

---

## 14. ADRs

No ADRs existed before this spec. Created under `docs/adr/`:

- `0001-c-pyvrp-congruency.md`
- `0002-da-as-artificial-one-client-vehicle.md`
- `0003-relax-and-repair-shared-depot-capacity.md`
- `0004-hard-forbid-vs-soft-penalty-repair.md`
- `0005-static-html-reporting.md`

---

*Stop after writing this spec. No source modified.*
