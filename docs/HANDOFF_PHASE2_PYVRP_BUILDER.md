# Handoff — Phase 2: Capacity-Relaxed PyVRP Builder (LoRP-FSD v3)

Readable without prior context. Companion to `docs/IMPLEMENTATION_PLAN.md`
(Phase 2) and `docs/HANDOFF_PHASE1_PREPROCESSING.md`.

Date: 2026-06-05 · Host: macOS arm64 · Working dir: `/Users/apena/lor-v3`

## 1. Files created / modified

### Created
- `src/lorp_fsd/da_options.py` — DA option construction.
- `src/lorp_fsd/pyvrp_builder.py` — capacity-relaxed model builder + metadata.
- `tests/test_da_options.py` — 6 tests.
- `tests/test_pyvrp_builder.py` — 11 tests.

### Modified
- `src/lorp_fsd/__init__.py` — export Phase 2 API.

No legacy modules and no Phase 1 modules were modified.

## 2. What Phase 2 implemented

- **Capacity-relaxed PyVRP model builder** (`build_relaxed_model`): one model per
  Excel row under a fixed facility design. Relaxed because each open depot gets
  routing vehicles totalling ~`Cap_i` AND independent DA options, so aggregate
  `routing + DA` demand can exceed `Cap_i` (the shared constraint PyVRP cannot
  model). Repair (Phase 4) claws it back.
- **Routing vehicle decomposition** (`routing_vehicle_specs`): for each open
  depot, `n_full = floor(Cap_i / Q)` vehicles of capacity `Q`, plus one residual
  vehicle of capacity `Cap_i − n_full·Q` when positive. Integer arithmetic keeps
  routing capacity ≤ `Cap_i`.
- **DA options** (`build_da_options`): one per feasible `(open_depot, client)`
  pair with `dist_scaled ≤ R` (continuous radius). Each carries
  `cost_int = round(F_A · dist_scaled · PYVRP_INT_SCALE)`.
- **Zero-return DA**: per-pair profile with two edges — outbound (weighted cost)
  and return (`distance=0, duration=0`).
- **DA single-client binding**: the per-pair profile leaves every other client at
  PyVRP's 2⁴⁴ missing-edge sentinel → the DA vehicle physically cannot serve any
  other client. (Phase 3 still re-checks → `DA_ASSIGNMENT_BINDING_VIOLATION`.)
- **`forbidden_routing_assignments`**: routing uses one profile per open depot;
  forbidden `(depot, client)` pairs get no routing edge (unreachable by routing)
  but their DA profile is untouched → same-depot DA stays allowed.
- **Dual-channel encoding**:
  - `distance` = `round(dist_scaled · PYVRP_INT_SCALE)` (geometry) → drives the
    route-length limit `max_distance = round(Length · PYVRP_INT_SCALE)`.
  - `duration` = `round(F · dist_scaled · PYVRP_INT_SCALE)` (cost) with
    `unit_distance_cost=0`, `unit_duration_cost=1`.
  - Correct for all `F_R`/`F_A`: `F_R=1` for all 1185 rows; `F_A∈{0,0.5,1}` but DA
    has no length cap, so no conflict.
- **`BuildInfo` / `VehicleTypeMeta`**: every PyVRP vehicle-type index maps back to
  its service mode (`routing` / `direct_allocation`), depot id, capacity, and (DA)
  bound client — plus scaling params, routing reachability, DA pairs, and node
  handles, so Phase 3 can parse and audit.

## 3. Row 0 regression facts (`r40x5a-1.dat`)

| Quantity | Value |
|---|---|
| Routing vehicle count | 12 (4 depots × (2×340 + 1×195)) |
| Routing vehicle types | 8 (4 depots × {full, residual}) |
| DA options (feasible pairs) | 60 |
| Clients DA-coverable | 38 (uncoverable: clients 1 and 33) |
| `route_max_distance_int` | 1,000,000 (`Length=100 × 10000`) |
| Relaxed smoke solve (3s) | feasible: 1 routing route + 38 DA assignments |

The smoke solve reproduces the C-optimal structure: 38 clients direct-allocated
(free, `F_A=0`), clients 1 & 33 served by a single routing route.

## 4. Tests

- Phase 2 tests: **17 passed** (`test_da_options.py` 6, `test_pyvrp_builder.py` 11).
- Full repository suite: **174 passed** (157 prior + 17), no regressions.

## 5. Known caveats

1. **Solve smoke was throwaway**, run only to validate model well-formedness — not
   yet formal parsing/reporting.
2. **Solution parser / cost reconstruction / capacity audit not yet implemented**
   (Phase 3).
3. **Repair loop not yet implemented** (Phase 4).
4. **Plotting / batch runner not yet implemented** (Phase 5/6).
5. **Vehicle fixed cost path**: builder sets routing `fixed_cost =
   round(veh_fixed · VFX · PYVRP_INT_SCALE)`; this is 0 for the current dataset
   (`veh_fixed=0`), so it is wired but not yet stress-tested.
6. **Fractional depot capacities** (sizes 2/4 → ×0.75/×1.25) are floored to int
   for vehicle capacities; row 0 (size 1 → 875) is exact.

## 6. Phase 3 readiness

**READY / GO.** The builder yields a valid, solvable `ProblemData` plus
`BuildInfo`/`VehicleTypeMeta` that recover service mode, depot, and bound client
for every route. The smoke solve confirms routes are parseable and the
DA/routing split is recoverable — exactly what Phase 3 (`solution_parser`,
`cost_reconstruction`, `capacity_audit`, `feasibility`) needs. No blockers.
