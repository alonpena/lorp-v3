# Implementation Plan — LoRP-FSD PyVRP v3

Status: planning only. Do not implement until this plan is approved.

Source-of-truth docs:

- `docs/C_SOLVER_AUDIT.md`
- `docs/PYVRP_REPLICATION_SPEC.md`
- C reference: `reference/LoRPSD`

Core v3 method:

```text
capacity-relaxed PyVRP construction
+ post-solve aggregate capacity audit
+ savings-based routing elimination repair
+ rebuild model and rerun
```

---

## 0. Guiding rules

1. C solver is source of truth.
2. No legacy modeling assumptions may enter v3 unless traced to C or explicitly labeled as PyVRP approximation.
3. Direct Allocation is assignment, not route travel.
4. DA real cost is one-way only: `F_A * dist_scaled(depot, client)`.
5. DA return cost is zero conceptually. If PyVRP needs a technical return arc, it must not enter reported DA cost.
6. No DA client-client travel as real cost.
7. Initial v3 supports only `problemID=0` Arslan scaling; other modes fail loudly.
8. PyVRP internal edge costs encode `F_R`/`F_A`; final reports reconstruct objective components ex-post.
9. `.dat` `n_vehicles` is not binding in v3 baseline; selected depot capacity generates routing vehicle availability.
10. Distances, R, Length, and Excel objective components use Arslan scaled units for `problemID=0`.
11. Depot capacity audit uses total assigned demand: routing + DA.
12. First PyVRP pass is capacity-relaxed. Do not report standard gap until repaired feasibility holds.
13. Every solve/repair iteration must save plot and audit artifacts.
14. PyVRP search uses integerized distances/costs (`PYVRP_INT_SCALE = 10_000`); reports use continuous scaled geometry. DA radius `R` stays continuous. Never compare the integer objective to Excel.
15. Each DA option serves exactly its intended client; binding violations are flagged `DA_ASSIGNMENT_BINDING_VIOLATION`.
16. The objective mixes scaled distance costs (routing, DA) with raw fixed costs (vehicles, depots); never scale fixed-cost terms.
17. `forbidden_routing_assignments` stays routing-only; same-depot DA is allowed and does not auto-repair aggregate capacity.

---

## 1. Proposed clean structure

Create package:

```text
src/lorp_fsd/
  __init__.py
  dat_parser.py
  excel_loader.py
  experiment_config.py
  instance.py
  geometry.py
  scaling.py
  facility_sizing.py
  da_options.py
  pyvrp_builder.py
  solution_parser.py
  cost_reconstruction.py
  capacity_audit.py
  repair.py
  feasibility.py
  metrics.py
  artifacts.py
  plotting.py
  runner.py
  cli.py

scripts/
  run_row0.py
  run_first_n.py
  run_full_batch.py
  compare_with_milp.py

tests/
  test_dat_parser.py
  test_excel_loader.py
  test_scaling.py
  test_da_feasibility.py
  test_facility_sizing.py
  test_pyvrp_builder_restrictions.py
  test_solution_parser.py
  test_cost_reconstruction.py
  test_capacity_audit.py
  test_repair_savings.py
  test_repair_feasibility.py
  test_metrics.py
  test_c_solver_row0_regression.py
```

Keep existing legacy modules initially, but do not import them from v3 package.

---

## 2. Files to create/modify

### Create

- `src/lorp_fsd/__init__.py`
- `src/lorp_fsd/dat_parser.py`
- `src/lorp_fsd/excel_loader.py`
- `src/lorp_fsd/experiment_config.py`
- `src/lorp_fsd/instance.py`
- `src/lorp_fsd/geometry.py`
- `src/lorp_fsd/scaling.py`
- `src/lorp_fsd/facility_sizing.py`
- `src/lorp_fsd/da_options.py`
- `src/lorp_fsd/pyvrp_builder.py`
- `src/lorp_fsd/solution_parser.py`
- `src/lorp_fsd/cost_reconstruction.py`
- `src/lorp_fsd/capacity_audit.py`
- `src/lorp_fsd/repair.py`
- `src/lorp_fsd/feasibility.py`
- `src/lorp_fsd/metrics.py`
- `src/lorp_fsd/artifacts.py`
- `src/lorp_fsd/plotting.py`
- `src/lorp_fsd/runner.py`
- `src/lorp_fsd/cli.py`
- `scripts/run_row0.py`
- `scripts/run_first_n.py`
- `scripts/run_full_batch.py`
- `scripts/compare_with_milp.py`
- tests listed above.

### Modify

- `pyproject.toml`
  - add `src` package layout,
  - add script entrypoint if CLI approved,
  - keep PyVRP dependency,
  - move Streamlit to optional dependency if retained.
- `.gitignore`
  - ensure outputs, caches, `.venv`, generated reports excluded.
- `README.md`
  - point users to v3 docs and scripts.

### Do not modify initially

Legacy root modules such as:

- `pyvrp_model.py`
- `run_capacity_repair_batch.py`
- `capacity_repair.py`
- `capacity_audit.py`
- `reporting.py`
- `lor_pyvrp_benchmark.py`

These remain legacy until v3 is validated.

---

## 3. Data structures to define

Recommended dataclasses/records:

```python
ForbiddenRoutingAssignments = set[tuple[int, int]]  # (depot_id, client_id)
```

Core records:

- `ParsedInstance`
  - depots, clients, vehicle capacity, vehicle fixed cost.
- `ExperimentConfig`
  - Excel row fields: `F_R`, `F_A`, `R`, `Length`, `UB`, selected depots/sizes/capacities/costs.
- `ScaledGeometry`
  - `max_dist`, `scale`, scaled distance lookup.
- `FacilityDesign`
  - active depots, selected size, selected capacity, selected depot cost.
- `RouteRecord`
  - iteration, route ID, depot ID, client sequence, load, route distance scaled, vehicle type.
- `DAAssignmentRecord`
  - iteration, depot ID, client ID, demand, dist_scaled, cost = `F_A * dist_scaled`.
- `DepotAuditRecord`
  - depot ID, routing demand, DA demand, total demand, capacity, excess.
- `RepairCandidate`
  - depot, route ID, client ID, client demand, saving, weighted saving.
- `IterationResult`
  - routes, DA assignments, audit, costs, metrics, forbidden set snapshot.

---

## 4. Implementation phases

### Phase 1 — Data and C-compatible preprocessing

Goal: exact C-compatible data loading and scaling.

Implement:

- `dat_parser.py`
  - parse C `.dat` format,
  - require/record trailing flag where present,
  - preserve 1-based depot/client IDs.
- `excel_loader.py`
  - load only `LoRP-FSD`,
  - preserve real depot IDs from `Depot1..4`,
  - preserve size/capacity/demand/usage/vehicles slots,
  - do not silently drop rows because of exact filename mismatch.
- `experiment_config.py`
  - dataclass for row config,
  - store `problemID`, `F_R`, `F_A`, `R`, `Length`,
  - validate `problemID == 0`,
  - raise `NotImplementedError("LoRP-v3 currently supports only problemID=0 Arslan scaling.")` otherwise,
  - store Excel-selected active depots/capacities for initial fixed-depot mode.
- `geometry.py`
  - Euclidean distance.
- `scaling.py`
  - `max_dist`, `scale=100/max_dist`, `dist_scaled`.
- `facility_sizing.py`
  - C formula for 5 sizes,
  - validate Excel `CapD*` and `Cost (Depots)` against recomputation when possible.
- `instance.py`
  - build fixed facility design from Excel selected depots/sizes.

Tests:

- dat parser exact row counts and fields,
- row 0 scale matches expected,
- R/Length treated as scaled,
- selected depots/sizes/capacities match Excel.

Stop after Phase 1 and review.

---

### Phase 2 — Capacity-relaxed PyVRP builder

Goal: build first-pass relaxed model and rebuildable model with forbidden routing assignments.

Implement:

- `da_options.py`
  - DA feasible pairs using `dist_scaled <= R` (continuous, not integerized),
  - create DA option metadata per `(depot_id, client_id)`,
  - capacity exactly `demand_j`,
  - no fixed cost,
  - zero conceptual return cost,
  - no multitrip DA,
  - no client-client DA arcs as real cost,
  - **bind each DA option to exactly its client `j`**: the option may serve only
    `client_j` (per-pair restricted reachability if the builder supports it).
    Capacity alone does not enforce this, so binding must be explicit.
- `pyvrp_builder.py`
  - function:

    ```python
    build_relaxed_model(
        instance,
        config,
        geometry,
        facility_design,
        forbidden_routing_assignments: set[tuple[int, int]],
    ) -> tuple[Model, ModelInfo]
    ```

  - support only `problemID=0`; fail loudly otherwise.
  - integerize all internal edge costs and length limits using
    `PYVRP_INT_SCALE = 10_000`. PyVRP requires integer weights; the C/MILP
    benchmark is continuous scaled. Final report stays continuous (Phase 3).
  - apply `F_R` to routing edge costs (integerized internally):

    ```python
    routing_edge_cost_ij     = F_R * dist_scaled_ij            # continuous, for report
    routing_edge_cost_int_ij = round(F_R * dist_scaled_ij * PYVRP_INT_SCALE)  # PyVRP
    ```

  - apply `F_A` to DA outbound edge costs (integerized internally):

    ```python
    da_edge_cost_depot_client     = F_A * dist_scaled_depot_client
    da_edge_cost_int_depot_client = round(F_A * dist_scaled_depot_client * PYVRP_INT_SCALE)
    da_edge_cost_client_depot     = 0
    ```

  - For each active depot:
    - routing vehicles represent full selected capacity:

      ```python
      n_full = floor(Cap_i / Q)
      residual = Cap_i - n_full * Q
      ```

    - add `n_full` routing vehicles capacity `Q`,
    - add residual routing vehicle if `residual > 0`,
    - do not enforce `.dat` `n_vehicles` as hard global cap,
    - route max distance = `round(Length * PYVRP_INT_SCALE)`, integerized
      scaled units (DA radius `R` stays continuous; only route-length limit and
      edge costs are integerized).
  - Routing graph complete except restrictions:

    ```python
    (i, j) in forbidden_routing_assignments
    => client j cannot be served by routing from depot i
    ```

  - DA service option per feasible depot-client pair.
  - DA technical return arc is zero by default. PyVRP has handled zero-return DA arcs acceptably in previous experiments. If a concrete solver/penalty issue appears, a small positive technical return cost may be used as fallback, marked technical-only and excluded from cost reconstruction.

Tests:

- vehicle capacities per depot equal selected `Cap_i`,
- forbidden `(i,j)` removes only routing service from depot `i`, not client globally,
- forbidden `(i,j)` does **not** forbid DA from depot `i` (same-depot DA still allowed),
- DA options exist exactly for scaled-radius feasible pairs,
- DA option `(i,j)` cannot serve any client other than `j`,
- no DA fixed vehicle cost,
- integerized edge cost equals `round(F * dist_scaled * PYVRP_INT_SCALE)`,
- integerized route-length limit equals `round(Length * PYVRP_INT_SCALE)`,
- DA radius check uses continuous `dist_scaled`, not integerized distance.

Stop after Phase 2 and review.

---

### Phase 3 — Solution parsing, cost reconstruction, and audit

Goal: parse PyVRP result into semantic records and evaluate C-compatible feasibility/cost.

Implement:

- `solution_parser.py`
  - parse PyVRP routes into `RouteRecord` and `DAAssignmentRecord`,
  - recover assigned depot from vehicle metadata,
  - detect service mode from vehicle type metadata,
  - compute route distances from continuous scaled geometry, not the integer
    solver objective,
  - enforce DA binding: reject any DA route with `len(route.clients) != 1`, a
    client other than the option's intended client, or `dist_scaled > R`, and
    flag `DA_ASSIGNMENT_BINDING_VIOLATION`,
  - detect suspicious huge PyVRP distances.
- `cost_reconstruction.py`
  - recompute all reported costs in **continuous scaled** units (never from the
    PyVRP integer objective),
  - recompute `Cost Routing` ex-post from final route sequences: `sum(F_R * scaled routing arc distances)`,
  - recompute `Cost Direct All` ex-post from final DA assignments: `sum(F_A * scaled one-way DA assignment distances)`,
  - no DA return cost,
  - no DA client-client cost,
  - compute `Cost Vehicles = used routing vehicles only * veh_fixed_cost * VFX`
    in **raw/unscaled** units,
  - compute or inject `Cost Depots = selected depot/sizing fixed cost` in
    **raw/unscaled** units,
  - mixed-unit objective: `Z = Cost_Routing(scaled) + Cost_Direct_All(scaled) +
    Cost_Vehicles(raw) + Cost_Depots(raw)`; never scale the fixed-cost terms,
  - produce `Z_PyVRP`,
  - produce either `RELAXATION_DEVIATION` or `GAP` depending on feasibility status.
- `capacity_audit.py`
  - per-depot routing demand, DA demand, total demand, capacity, excess.
- `feasibility.py`
  - clients served exactly once,
  - route length violations,
  - route capacity violations,
  - DA radius violations,
  - aggregate capacity violations,
  - penalty distance diagnostics using:

    ```python
    penalty_distance_threshold = max(1_000_000, 1000 * Length)
    ```

    and flag `PENALTY_DISTANCE_SUSPECTED` when exceeded.
- `metrics.py`
  - `RELAXATION_DEVIATION` for relaxed infeasible solution,
  - `GAP` for final repaired feasible solution,
  - status/label selection.

Tests:

- DA cost one-way only,
- `F_A=0` DA cost zero,
- depot capacity includes routing + DA,
- same-depot routing→DA conversion does not reduce total demand,
- multi-client or wrong-client or out-of-radius DA route triggers `DA_ASSIGNMENT_BINDING_VIOLATION`,
- reconstructed costs are continuous scaled; fixed costs stay raw/unscaled,
- reconstruction uses geometry, not the PyVRP integer objective,
- first relaxed infeasible result gets relaxation metric, not standard gap.

Stop after Phase 3 and review.

---

### Phase 4 — Savings-based routing elimination repair

Goal: implement documented repair loop.

Implement in `repair.py`:

#### Candidate generation

Function:

```python
build_repair_candidates(
    routes: list[RouteRecord],
    audit: list[DepotAuditRecord],
    geometry: ScaledGeometry,
    F_R: float,
) -> list[RepairCandidate]
```

Only inspect routing routes from overloaded depots.

For route:

```text
Depot -> c1 -> c2 -> ... -> ck -> Depot
```

savings:

- internal `c_m`:

  ```python
  saving = d(p, c_m) + d(c_m, s) - d(p, s)
  ```

- first `c1`:

  ```python
  saving = d(depot, c1) + d(c1, c2) - d(depot, c2)
  ```

- last `ck`:

  ```python
  saving = d(c_{k-1}, ck) + d(ck, depot) - d(c_{k-1}, depot)
  ```

- single-client route:

  ```python
  saving = d(depot, c1) + d(c1, depot)
  ```

Weighted saving:

```python
weighted_saving = F_R * saving
```

#### Candidate selection

Function:

```python
select_forbidden_assignments(
    candidates,
    excess_by_depot,
    current_forbidden,
    feasibility_checker,
) -> set[tuple[int, int]]
```

For each overloaded depot:

- sort by largest `weighted_saving` (v3 baseline ranking),
- select candidates until `sum(demand_removed) >= excess_i`,
- represent removals as `(depot_id, client_id)`,
- skip candidates that would strand a client.

Future extension: compare largest-saving vs saving-per-demand repair policies.
v3 baseline keeps largest weighted saving only.

#### Feasibility before rerun

Implement in `feasibility.py`:

```python
client_has_service_option(
    client_id,
    active_depots,
    geometry,
    R,
    forbidden_routing_assignments,
) -> bool
```

Rules:

```python
has_routing = any((h, j) not in forbidden for h in active_depots)
has_DA = any(dist_scaled(h, j) <= R for h in active_depots)
return has_routing or has_DA
```

If any client has no option, repair candidate set is infeasible; skip candidate or stop with `REPAIR_INFEASIBLE`.

Caveat (v3 baseline keeps routing-only forbidding): a client removed from routing
at overloaded depot `i` may be re-served by DA from the *same* depot `i`. Since
C/MILP capacity is `routing + DA <= Cap_i`, this does **not** reduce depot `i`'s
total demand. Capacity is therefore re-audited only after rerun; if same-depot DA
fails to clear the excess, the next iteration forbids further routing assignments
until feasible or `REPAIR_INFEASIBLE`. Depot-level forbidding (both routing and
DA) and local search are future work, not v3 baseline.

Tests:

- savings formula for first/internal/last/single-client,
- candidates only from overloaded depots,
- selection reaches excess by demand,
- forbidden set uses `(depot_id, client_id)`,
- client is not deleted globally,
- no rerun if any client has no service option.

Stop after Phase 4 and review.

---

### Phase 5 — Iterative runner, model rebuild, artifacts

Goal: orchestrate solve → audit → repair → rebuild → rerun.

Implement in `runner.py`:

```python
run_row(
    row_config,
    instance,
    output_dir,
    max_repair_iterations: int,
    runtime: int,
    n_runs: int,
) -> RowRunResult
```

Loop:

1. initialize `forbidden_routing_assignments = set()`.
2. build PyVRP model with current forbidden set.
3. solve.
4. parse solution.
5. reconstruct cost.
6. audit feasibility.
7. save iteration artifacts.
8. if feasible, return final feasible result with `GAP`.
9. if overloaded, compute repair candidates.
10. add safe `(depot_id, client_id)` restrictions.
11. verify every client still has at least one option.
12. rebuild model and rerun.
13. stop at max iterations with failure/relaxation diagnostics.

### Artifact output structure

Implement in `artifacts.py` and `plotting.py`.

For each row/instance/iteration:

```text
outputs/<run_id>/<instance_name>/iteration_00_solution.png
outputs/<run_id>/<instance_name>/iteration_00_audit.json
outputs/<run_id>/<instance_name>/iteration_00_routes.csv
outputs/<run_id>/<instance_name>/iteration_00_assignments.csv
outputs/<run_id>/<instance_name>/iteration_01_solution.png
outputs/<run_id>/<instance_name>/iteration_01_audit.json
outputs/<run_id>/<instance_name>/iteration_01_routes.csv
outputs/<run_id>/<instance_name>/iteration_01_assignments.csv
...
```

Plot must show:

- depots,
- clients,
- routing routes,
- DA assignments,
- overloaded depots if any,
- clients selected for routing removal,
- accumulated `forbidden_routing_assignments`.

Audit JSON/CSV must include:

- `demand_routing_i`,
- `demand_DA_i`,
- `demand_total_i`,
- `Cap_i`,
- `excess_i`,
- clients served exactly once,
- instance name,
- row ID,
- `F_R`,
- `F_A`,
- `R`,
- `Length`,
- `scale`,
- `max_dist`,
- active depots,
- capacities by depot,
- `demand_routing_i`,
- `demand_DA_i`,
- `demand_total_i`,
- `excess_i`,
- service coverage status,
- clients served exactly once,
- forbidden routing assignments,
- selected repair removals,
- route count by depot,
- route count by profile,
- route length violations,
- route capacity violations,
- DA radius violations,
- maximum route distance,
- penalty distance suspected flag,
- `Cost Routing`,
- `Cost Direct All`,
- `Cost Vehicles`,
- `Cost Depots`,
- total objective,
- comparison against MILP UB,
- metric label.

Tests:

- runner rebuilds model after forbidden set changes,
- iteration artifacts paths match spec,
- relaxed first pass uses `RELAXATION_DEVIATION` if capacity violated,
- final feasible solution uses `GAP`,
- max-iteration failure preserves diagnostics.

Stop after Phase 5 row-0 smoke and review.

---

### Phase 6 — Batch scripts and comparison

Implement:

- `scripts/run_row0.py`
  - deterministic row 0 run,
  - save all iteration artifacts,
  - print summary.
- `scripts/run_first_n.py`
  - run first N rows,
  - export CSV.
- `scripts/run_full_batch.py`
  - run all rows with resolver,
  - export results and diagnostics.
- `scripts/compare_with_milp.py`
  - compare objective components:
    - routing,
    - DA,
    - vehicles,
    - depots,
    - total.

Batch outputs:

```text
outputs/<run_id>/summary.csv
outputs/<run_id>/diagnostics.csv
outputs/<run_id>/<instance_name>/iteration_XX_*.{png,json,csv}
```

---

### Phase 7 — Optional full heuristic for facility sizing

Only after fixed-facility v3 is validated.

Possible approaches:

1. Greedy/open-close depot-size local search outside PyVRP.
2. Small MILP/LP assignment layer for facility-size + DA + routing customer-to-depot allocation, then PyVRP routes per depot.
3. Metaheuristic over selected depot-size configurations.

Any full heuristic must produce feasible LoRP-FSD solution before standard `GAP` is reported.

---

## 5. Validation plan

### Row 0 validation

Use Excel row 0 (`r40x5a-1.dat`) as first regression case.

Validate:

- resolved instance path,
- max distance and scale,
- selected depots and sizes match Excel,
- selected capacities match Excel,
- route length uses scaled units,
- DA feasibility uses scaled radius,
- DA cost is one-way only and has no return term,
- total demand served = all client demand,
- no final depot capacity violation,
- objective components are in Excel units,
- iteration artifacts saved.

### Batch validation

Run:

1. first 10 rows,
2. first 100 rows,
3. all rows.

Track:

- failed instance resolution,
- infeasible PyVRP routes,
- service level < 100%,
- route length violations,
- depot capacity violations,
- repair iterations required,
- repair infeasible rows,
- negative final standard gaps,
- relaxation deviations from first pass,
- objective component deltas against Excel.

---

## 6. Settled v3 baseline decisions and remaining blockers

### Settled baseline decisions

These are no longer implementation blockers:

1. **Initial v3 supports only `problemID=0`.**

   Use Arslan scaling:

   ```python
   scale = 100 / max_dist
   dist_scaled = dist_original * scale
   ```

   If another `problemID` is requested, fail loudly:

   ```python
   raise NotImplementedError("LoRP-v3 currently supports only problemID=0 Arslan scaling.")
   ```

2. **PyVRP edge costs encode `F_R` and `F_A`.**

   Routing profile:

   ```python
   routing_edge_cost_ij = F_R * dist_scaled_ij
   ```

   Direct Allocation profile:

   ```python
   da_edge_cost_depot_client = F_A * dist_scaled_depot_client
   da_edge_cost_client_depot = 0
   ```

3. **Final report reconstructs objective ex-post.**

   ```python
   Cost_Routing = sum(F_R * dist_scaled arcs used in routing routes)
   Cost_Direct_All = sum(F_A * dist_scaled(depot, client) for DA assignments)
   Cost_Vehicles = fixed_vehicle_cost * number_of_used_routing_vehicles
   Cost_Depots = selected depot/sizing fixed cost
   Z_PyVRP = Cost_Routing + Cost_Direct_All + Cost_Vehicles + Cost_Depots
   ```

   This gives PyVRP correct search incentives while keeping report components academically traceable and protected from technical arcs/rounding.

4. **`.dat` `n_vehicles` is not binding in v3 baseline.**

   Treat it as legacy/global availability metadata. Routing vehicle availability is generated from selected depot capacity:

   ```python
   n_full = floor(Cap_i / Q)
   residual = Cap_i - n_full * Q
   ```

   Add `n_full` routing vehicles with capacity `Q`; add one residual vehicle when `residual > 0`. Do not impose `.dat` `n_vehicles` as hard global cap unless C congruency later proves it binding.

5. **Zero-return DA is default.**

   DA is one-way assignment in C/MILP. Reported `Cost Direct All` has no return term, no client-client term, no multitrip term, and no fixed DA vehicle activation cost.

6. **Technical positive DA return is fallback only.**

   PyVRP has handled zero-return DA arcs acceptably in previous experiments. Only if a concrete solver/penalty issue appears during execution may we use a small positive technical return cost. That cost is excluded from reported objective.

7. **Penalty-distance threshold is audit diagnostic.**

   Use:

   ```python
   penalty_distance_threshold = max(1_000_000, 1000 * Length)
   ```

   If any route distance exceeds this threshold, flag `PENALTY_DISTANCE_SUSPECTED`. This detects missing arcs, invalid graph construction, PyVRP internal penalty routes, or distances impossible under scaled `Length`. It does not repair the model by itself.

8. **Greedy savings repair is v3 baseline.**

   Candidate removals are sorted by largest weighted saving. If a candidate would strand a client, skip it and try the next one. If no feasible candidate set exists, mark row `REPAIR_INFEASIBLE`. Backtracking/local search is future work.

9. **Each repair iteration rebuilds PyVRP model from scratch.**

   The accumulated `forbidden_routing_assignments: set[tuple[int, int]]` is passed to the builder. Repair does not literally delete one arc; it forbids selected client `j` from routing service at overloaded depot `i` in next model. Client remains in problem.

10. **First relaxed solve is not standard gap.**

    Because each depot can use full routing capacity plus DA service options, first solution may be super-optimal. Report `RELAXATION_DEVIATION = (UB_MILP - Z_relaxed) / UB_MILP`.

11. **Final feasible repaired solve uses standard gap.**

    If all C/MILP feasibility rules hold, report `GAP = (Z_PyVRP - UB_MILP) / UB_MILP`. If final feasible `Z_PyVRP < UB_MILP` on an optimal MILP row, flag `NEGATIVE_GAP_MODELING_INCONSISTENCY`.

12. **Scaled units are mandatory.**

    For `problemID=0`, use Arslan scaling: `scale=100/max_dist`; `dist_scaled=dist_original*scale`; DA feasible iff `dist_scaled<=R`; route feasible iff `route_dist_scaled<=Length`; objective components remain scaled for Excel comparison; never divide final costs by scale.

13. **PyVRP uses high-precision integer discretization.**

    `PYVRP_INT_SCALE = 10_000`. Internal edge costs and route-length limits are integerized via `round(value * PYVRP_INT_SCALE)`; DA radius feasibility and final reported costs stay continuous scaled. Never compare the PyVRP integer objective directly against Excel.

14. **DA options are bound to exactly one client.**

    Each `(depot_i, client_j)` DA option may serve only `client_j`. If the builder cannot enforce this, the parser/audit rejects any DA route with the wrong client count/identity or `dist_scaled > R`, flagging `DA_ASSIGNMENT_BINDING_VIOLATION`.

15. **The objective mixes scaled distance costs and raw fixed costs.**

    Routing and DA use Arslan-scaled distances; vehicle and depot fixed costs stay raw/unscaled. Never scale fixed-cost terms.

16. **`forbidden_routing_assignments` stays routing-only.**

    Repair forbids routing `(depot_id, client_id)` only and allows same-depot DA, which does not auto-repair aggregate capacity. Feasibility is re-audited after each rerun. Depot-level forbidding and local search are future work.

### Remaining unresolved blockers

None before C congruency test.

---

## 7. Next phase: C congruency test before PyVRP implementation

Plan only. Do not execute until approved.

Purpose: verify the copied C solver can reproduce Excel row 0 before implementing PyVRP v3.

Steps:

1. Check whether C binary exists and runs:

   ```text
   /Users/apena/lor-v3/reference/LoRPSD/LoRPSD
   ```

2. Locate the same instance used in Excel row 0, likely:

   ```text
   r40x5a-1.dat
   ```

   Search available folders:

   ```text
   /Users/apena/lor-v3/instances
   /Users/apena/lor-v3/instances_LRP
   /Users/apena/lor-v3/reference/LoRPSD/instances_LLRP
   /Users/apena/lor-v3/reference/LoRPSD/instances_stc
   ```

3. Read row 0 from:

   ```text
   /Users/apena/lor-v3/results_MILP.xlsx
   sheet: LoRP-FSD
   ```

4. Extract row-0 fields:

   - `name`,
   - `F_R`,
   - `F_A`,
   - `R`,
   - `Length`,
   - `UB`,
   - `Cost Routing`,
   - `Cost (Vehicles)`,
   - `Cost (Depots)`,
   - `Cost Direct All`,
   - selected depots,
   - selected capacities.

5. Build equivalent C command using row-0 values:

   ```bash
   /Users/apena/lor-v3/reference/LoRPSD/LoRPSD \
     -results outputs/c_congruency/row0_results.txt \
     -problemID 0 \
     -WR <F_R> \
     -WA <F_A> \
     -Radius <R> \
     -instance <resolved_instance_path> \
     -VFX 1 \
     -OF 1 \
     -original 0 \
     -model 1 \
     -length <Length>
   ```

   Use `-original 0` for LoRP-FSD per C audit. Use `-VFX 1` unless C congruency proves Excel row used different value.

6. Run only row 0.

7. Save output to:

   ```text
   outputs/c_congruency/row0_results.txt
   ```

8. Compare C output against Excel row 0:

   - `UB`,
   - `Cost Routing`,
   - `Cost (Vehicles)`,
   - `Cost (Depots)`,
   - `Cost Direct All`,
   - `TotalVehicles`,
   - selected depots if output contains them.

8a. Inspect the C model for a **per-route vehicle capacity constraint** `Q`:

   - determine whether `det_LoRP_DSD()` enforces individual route load `<= Q`,
     or only the depot-aggregate capacity `routing + DA <= Cap_i` plus route
     length,
   - document whether PyVRP's per-vehicle capacity `Q` matches the C model or
     adds an **extra** constraint not present in the MILP (which would make PyVRP
     spuriously infeasible or higher-cost relative to Excel),
   - do not assume the answer; record the C source evidence.

9. Produce later:

   ```text
   docs/C_CONGRUENCY_TEST.md
   ```

   Include:

   - exact command,
   - whether binary ran,
   - comparison table,
   - mismatches,
   - next fix.

Do not begin PyVRP implementation until C congruency result is documented or explicitly waived.

---

## 8. Acceptance criteria before legacy cleanup

Legacy code can be archived only after:

- v3 row0 audit passes,
- first 10 rows run with iteration artifacts,
- final feasible rows have no service/capacity/length/radius violations,
- docs explain every metric label,
- tests cover scaling, DA, capacity, objective reconstruction, repair savings, forbidden assignment feasibility, model rebuild, artifacts,
- no v3 module imports legacy root modules.
