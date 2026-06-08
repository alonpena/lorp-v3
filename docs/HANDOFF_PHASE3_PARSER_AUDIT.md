# Handoff — Phase 3: Solution Parsing, Cost Reconstruction & Audit (LoRP-FSD v3)

Readable without prior context. Companion to `docs/IMPLEMENTATION_PLAN.md`
(Phase 3) and the Phase 1/2 handoffs.

Date: 2026-06-05 · Host: macOS arm64 · Working dir: `/Users/apena/lor-v3`

## 1. Files created / modified

### Created
- `src/lorp_fsd/solution_parser.py` — parse PyVRP routes → semantic records.
- `src/lorp_fsd/cost_reconstruction.py` — ex-post objective + comparison metric.
- `src/lorp_fsd/capacity_audit.py` — per-depot aggregate capacity audit.
- `src/lorp_fsd/feasibility.py` — route/solution feasibility audit.
- `tests/test_phase3_audit.py` — 16 tests.

### Modified
- `src/lorp_fsd/__init__.py` — export Phase 3 API (and `load_row`).

No Phase 1/2 modules or legacy modules were changed.

## 2. What Phase 3 implemented

- **Solution parser** (`parse_solution`): maps `route.visits()` → client IDs via
  `model.locations[i].name`, and `route.vehicle_type()` → `VehicleTypeMeta`
  (service mode, depot, bound client). Per route it records mode, depot, client
  sequence, demand, the solver's integerized distance, and a **continuous-scaled
  geometric reconstruction** (authoritative). DA routes are checked for
  single-client binding (`len==1`, correct bound client, `dist_scaled ≤ R`) →
  `DA_ASSIGNMENT_BINDING_VIOLATION`. Produces service-by-client map,
  missing/duplicate sets, and a served-exactly-once verdict.
- **Cost reconstruction** (`reconstruct_cost`): mixed-unit objective —
  `Cost_Routing = Σ F_R·scaled route dist`, `Cost_Direct_All = Σ F_A·dist_scaled`
  (one-way only), `Cost_Vehicles = used_routes·veh_fixed·VFX` (raw),
  `Cost_Depots` = facility design total (raw). No DA return/client-client/multitrip
  cost; never divides by scale.
- **Comparison metric** (`comparison_metric`): `RELAXATION_DEVIATION` when not
  fully feasible, `GAP` when fully feasible; flags
  `NEGATIVE_GAP_MODELING_INCONSISTENCY` only for a *material* negative gap (a
  relative `negative_gap_tol=1e-4` absorbs Excel's 3-decimal UB rounding).
- **Capacity audit** (`audit_capacity`): per depot `demand_routing`, `demand_da`,
  `demand_total = routing + DA`, `excess = max(0, total − Cap)`; `capacity_feasible`
  and `overloaded_depots`.
- **Feasibility audit** (`audit_feasibility`): served-exactly-once, route capacity,
  route length (scaled, small tol), DA radius, DA binding, aggregate capacity, and
  a penalty-distance diagnostic `max(1_000_000, 1000·Length)` →
  `PENALTY_DISTANCE_SUSPECTED`. Combines into `fully_feasible`.

All audit/result records carry an `iteration` field (default 0) so Phase 4 can
thread the repair-iteration counter through unchanged. See §6.

## 3. Row 0 parsed / cost / audit results (relaxed solve, seed 0, 3s)

| Aspect | Result |
|---|---|
| Routing routes | 1 (depot d3, clients {1, 33}, demand 85) |
| DA assignments | 38 |
| Clients served exactly once | yes (0 missing, 0 duplicate) |
| DA binding / radius | all 38 valid, none exceed R=30 |
| Route length / capacity | 95.3087 ≤ 100; 85 ≤ 340; no violations |
| Cost Routing | 95.3087 |
| Cost Direct All | 0.0 (F_A=0) |
| Cost Vehicles | 0.0 (veh_fixed=0) |
| Cost Depots | 300.0 |
| **Z_PyVRP total** | **395.3087** (Excel UB 395.309) |
| Capacity audit | feasible; per-depot totals 332 / 380 / 638 / 581 ≤ 875 |
| Penalty distance | not suspected |
| Comparison metric | `GAP` ≈ −1e-6 → **no** spurious negative flag (within rounding tol) |

The relaxed solution for row 0 is already fully feasible (the free-DA optimum
matches the C structure), so it reports `GAP` ≈ 0. This will not generally hold:
other rows' relaxed solves may overload depots and report `RELAXATION_DEVIATION`.

## 4. Tests

- Phase 3 tests: **16 passed** (`tests/test_phase3_audit.py`, marked
  `integration` since they perform a short solve).
- Full repository suite: **190 passed** (174 prior + 16), no regressions.

## 5. Known caveats

1. **Tests solve** (deterministic seed 0, 3s). The row-0 structure is trivial and
   reliably found; still, these are `integration`-marked.
2. **`NEGATIVE_GAP` tolerance**: Excel stores `UB` to 3 decimals, so an exact
   reconstruction can read ~1e-6 below UB. The metric uses a relative
   `negative_gap_tol=1e-4` to avoid spurious modeling-inconsistency flags. The raw
   gap value is still reported truthfully.
3. **Penalty threshold units**: compared against the solver's scaled route
   distance (`route.distance()/PYVRP_INT_SCALE`); a sentinel/penalty edge (2⁴⁴)
   would read ~1.75e9 scaled and trip the 1e6 threshold.
4. **No repair, plotting, or batch yet** (Phases 4–6).

## 6. Phase 4 readiness & repair-iteration note

**GO for Phase 4 (savings repair).** Phase 3 supplies exactly the inputs the
repair loop consumes:
- `CapacityAudit.overloaded_depots` + per-depot `excess` → which depots to repair
  and by how much demand.
- `ParsedSolution.routes` (client sequences, per-route demand, scaled geometry) →
  savings candidates.
- `FeasibilityReport.fully_feasible` → loop stop condition.
- `comparison_metric` → `RELAXATION_DEVIATION` (pre-feasible) vs `GAP` (final).

**Repair-iteration accounting (per the note):** every Phase 3 record already
carries `iteration` (default 0 = the relaxed solve). Phase 4 should:
- increment `iteration` per rebuild/solve,
- pass the accumulated `forbidden_routing_assignments` to `build_relaxed_model`,
- re-run parse → reconstruct → audit each iteration,
- stop when `fully_feasible` or a `max_repair_iterations` cap is hit (record the
  final iteration count and a `REPAIR_INFEASIBLE` flag on cap-out).

For **row 0 specifically, repair iterations are not exercised**: the relaxed solve
is already capacity-feasible (0 overloaded depots), so the loop would terminate at
iteration 0 with `GAP`. A row whose relaxed solve overloads a depot is needed to
exercise the iteration counter — to be selected in Phase 4 testing.
