# Handoff — Phase 4: Savings-Based Routing-Elimination Repair (LoRP-FSD v3)

Readable without prior context. Companion to `docs/IMPLEMENTATION_PLAN.md`
(Phase 4) and the Phase 1–3 handoffs.

Date: 2026-06-05 · Host: macOS arm64 · Working dir: `/Users/apena/lor-v3`

## 1. Files created / modified

### Created
- `src/lorp_fsd/repair.py` — savings candidate generation + greedy selection.
- `tests/test_repair_savings.py` — 9 tests (no solve).

### Modified
- `src/lorp_fsd/feasibility.py` — added `client_has_service_option` and
  `make_feasibility_checker` (stranding check, spec §10).
- `src/lorp_fsd/__init__.py` — export Phase 4 API.

No Phase 1–3 record types or legacy modules were changed.

## 2. What Phase 4 implemented

- **`compute_route_savings(depot_id, client_sequence, geometry)`** — marginal
  scaled-distance saving of removing each client (spec §8):
  - first `c1`: `d(depot,c1)+d(c1,c2)−d(depot,c2)`
  - internal `c_m`: `d(p,c_m)+d(c_m,s)−d(p,s)`
  - last `ck`: `d(c_{k-1},ck)+d(ck,depot)−d(c_{k-1},depot)`
  - single client: `d(depot,c1)+d(c1,depot)`
- **`build_repair_candidates(routes, capacity_audit, geometry, F_R, demands)`** —
  candidates only from routing routes of **overloaded** depots; each carries
  `saving` and `weighted_saving = F_R · saving`. (`demands` maps
  `client_id → demand`, built from the instance.)
- **`select_forbidden_assignments(candidates, excess_by_depot, current_forbidden,
  feasibility_checker)`** — per overloaded depot, sort by **largest weighted
  saving** (settled decision #8), select until `Σ demand_removed ≥ excess_i`,
  skipping any removal that would strand a client. Returns a `RepairSelection`
  with `selected`, `updated_forbidden` (= current ∪ selected),
  `removed_demand_by_depot`, `repair_infeasible`, `infeasible_depots`, and flags
  (`REPAIR_INFEASIBLE` if any depot's excess cannot be safely covered).
- **`client_has_service_option` / `make_feasibility_checker`** (feasibility.py) —
  a client is serviceable if routable from some non-forbidden depot OR
  DA-feasible (`dist_scaled ≤ R`) from some depot.

### Design fidelity
- Removals are **routing-only** `(depot_id, client_id)` forbidden assignments
  (settled decision #16); the client is **not** deleted — it stays in the problem
  and may be re-served by DA (incl. same-depot DA) or routing elsewhere.
- The module documents the caveat (audit §5): forbidding same-depot routing does
  not by itself guarantee aggregate `routing + DA` demand drops; capacity is
  re-audited only after the next solve (Phase 5).

## 3. Tests

- Phase 4 tests: **9 passed** (`tests/test_repair_savings.py`) — pure unit tests,
  no solve. Exact savings verified on a synthetic instance with `max_dist = 100`
  so `scale = 1` (scaled == raw): first=20, internal=`30+50−√(60²+40²)`, last=60,
  single=80.
- Full repository suite: **199 passed** (190 prior + 9), no regressions.

Coverage: savings per position, weighted saving applies `F_R`, candidates only
from overloaded depots, selection covers excess by demand, largest-saving-first,
removal does not delete the client globally, stranding → skip →
`REPAIR_INFEASIBLE`, feasibility checker routing/DA logic.

## 4. End-to-end demonstration on real overloading rows (validation, not a test)

A bounded scan (relaxed solve, seed 0, 2s) found rows whose relaxed solution
overloads a depot, exercising the full audit → candidate → selection path:

| Row | Instance | F_A | Overloaded depot (excess) | Candidates | Removals selected | Demand shed | Repair |
|---|---|---|---|---|---|---|---|
| 3 | `r30x5a-2.dat` | 0.0 | d4 (+30) | 2 | 1 | 45 ≥ 30 | feasible |
| 5 | `r40x5b-1.dat` | 0.5 | d4 (+121) | 7 | 4 | 131 ≥ 121 | feasible |

(Row 0 `r40x5a-1.dat` does not overload — its relaxed solve is already feasible.)

These confirm the selector covers excess by demand and only acts on overloaded
depots, on real data.

## 5. Known caveats

1. **No iterative rerun yet.** Phase 4 selects removals for *one* repair step.
   Rebuilding the model with `updated_forbidden`, re-solving, and re-auditing is
   the Phase 5 loop. The demonstration above is a single step, not convergence.
2. **Optimistic demand accounting.** Selection assumes shed routing demand
   reduces depot excess; same-depot DA may re-absorb the client, so the *actual*
   excess reduction is only known after the Phase 5 re-audit. Documented in
   `repair.py`.
3. **`demands` mapping is caller-supplied** (`{j: c.demand}`) because
   `RouteRecord` carries only the route total, not per-client demand. This keeps
   `repair.py` decoupled from the instance type.
4. No plotting / batch runner yet (Phases 5/6).

## 6. Phase 5 readiness & iteration note

**GO for Phase 5 (iterative runner + artifacts).** Phase 4 provides the single
repair step; Phase 5 wraps it in the loop:

1. `forbidden = set()`, `iteration = 0`.
2. `build_relaxed_model(..., forbidden)` → solve → `parse_solution(..., iteration)`.
3. `reconstruct_cost` + `audit_capacity(..., iteration)` + `audit_feasibility(..., iteration)`.
4. if `fully_feasible`: stop → report `GAP`.
5. else: `cands = build_repair_candidates(routes, cap, geom, F_R, demands)`;
   `sel = select_forbidden_assignments(cands, excess_by_depot, forbidden, checker)`.
6. if `sel.repair_infeasible` or `sel.selected == set()`: stop →
   `REPAIR_INFEASIBLE` (carry `RELAXATION_DEVIATION`).
7. `forbidden = sel.updated_forbidden`; `iteration += 1`; loop to 2 until a
   `max_repair_iterations` cap.

**Iteration counter (per the standing note):** every record already carries
`iteration` (default 0). Phase 5 increments it per rebuild and records the final
count; on cap-out it sets `REPAIR_INFEASIBLE`. **Recommended Phase 5 test rows:**
**row 3** (`r30x5a-2.dat`, single-removal repair — minimal iteration case) and
**row 5** (`r40x5b-1.dat`, multi-removal repair — exercises larger excess and
likely ≥1 iteration to feasibility). Row 0 remains the iteration-0 / already-
feasible regression case.
