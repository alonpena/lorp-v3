# PyVRP Replication Spec — LoRP-FSD v3

Source of truth: `docs/C_SOLVER_AUDIT.md` and C solver under `reference/LoRPSD`.

Purpose: define how Python/PyVRP v3 benchmarks against the C/Gurobi LoRP-FSD results in `results_MILP.xlsx`.

Core v3 method:

```text
capacity-relaxed PyVRP construction
+ post-solve aggregate capacity audit
+ savings-based routing elimination repair
+ model rebuild and rerun
```

The first PyVRP solution is intentionally capacity-relaxed and may be super-optimal. A standard gap is reported only after repair yields a solution feasible for the C/MILP constraints.

---

## 1. Canonical scaling policy

For Excel `LoRP-FSD` rows generated with `problemID=0`:

```python
max_dist = max(euclidean_distance(u, v) for all depots/customers u,v)
scale = 100.0 / max_dist
dist_scaled(u, v) = euclidean_distance(u, v) * scale
```

All objective costs and feasibility thresholds use `dist_scaled`.

Do not divide final costs by `scale` when comparing to Excel. Excel `UB`, `Cost Routing`, and `Cost Direct All` are in scaled objective units.

Raw distances may be used only for plotting/debug labels.

### Supported scaling modes

Settled v3 baseline decision: initial v3 supports only:

```python
problemID = 0
```

which corresponds to Arslan scaling:

```python
scale = 100 / max_dist
dist_scaled = dist_original * scale
```

If another `problemID` is requested, fail loudly:

```python
raise NotImplementedError("LoRP-v3 currently supports only problemID=0 Arslan scaling.")
```

Rationale:

- Current benchmark focus is LoRP-FSD with Arslan scaling.
- Supporting multiple scaling modes now adds unnecessary complexity.
- First objective is correctness on row 0 and controlled batch execution.
- Other scaling modes are future extensions after v3 validation.

### PyVRP integer discretization policy

The C solver uses **continuous** scaled distances for `problemID=0`:

```python
scale = 100 / max_dist
dist_scaled = dist_original * scale
```

The Excel objective is in these continuous scaled units.

PyVRP uses **integer** costs/distances, so v3 uses high-precision integerized
distances internally, while reporting final costs from continuous scaled geometry.

Discretization constant:

```python
PYVRP_INT_SCALE = 10_000
dist_pyvrp_int = round(dist_scaled * PYVRP_INT_SCALE)
```

Weighted internal edge costs:

```python
routing_edge_cost_int = round(F_R * dist_scaled * PYVRP_INT_SCALE)
da_edge_cost_int      = round(F_A * dist_scaled * PYVRP_INT_SCALE)
```

Route length constraint (internal):

```python
route_max_distance_int = round(Length * PYVRP_INT_SCALE)
```

DA feasibility stays **continuous** (never integerized):

```python
DA_feasible(i, j) = dist_scaled(i, j) <= R
```

Final reporting stays **continuous scaled**, reconstructed ex-post from geometry:

```python
Cost_Routing = sum(F_R * dist_scaled arcs used in routing routes)
Cost_Direct_All = sum(
    F_A * dist_scaled(depot, client)
    for each final DA assignment
)
```

Rules:

- C/MILP benchmark = continuous scaled objective.
- PyVRP internal search = high-precision integer approximation.
- Final report = continuous scaled ex-post reconstruction.
- Do **not** compare the PyVRP integer objective directly against Excel.
- Do **not** divide final costs by `scale`.

The integer search and the continuous report differ by a controlled
discretization error (bounded by `1 / PYVRP_INT_SCALE` per arc). This is an
inherent integrality gap between the continuous C/MILP objective and the integer
PyVRP search, and is expected.

---

## 2. DA feasibility rule

Direct Allocation feasibility from depot `i` to client `j`:

```python
DA_feasible(i, j) = dist_scaled(i, j) <= R
```

`R` is already in scaled distance units for `problemID=0`.

C equivalent:

```cpp
Data.dist[client][depot] * A[client][depot] <= Radius * selected_depot
```

---

## 3. Route length rule

Routing route length must be computed using scaled distances.

```python
route_dist_scaled = sum(dist_scaled(a, b) for consecutive route nodes)
route_dist_scaled <= Length
```

`Length` is already in scaled distance units for `problemID=0`.

C equivalent uses `t` flow variables and:

```cpp
t[i][j] <= Data.lenghtMax * X[i][j]
```

with `Data.dist` already scaled.

---

## 4. Objective reconstruction

Final reported cost must be reconstructed from semantic solution decisions, not blindly from PyVRP technical route distance if DA uses artificial arcs.

Canonical C objective:

```python
Z = routing_cost + vehicle_cost + depot_cost + direct_allocation_cost
```

### Mixed-unit objective warning

The C/MILP objective mixes two unit systems. Distance-based components use
Arslan-scaled distances; fixed components use **raw, unscaled** instance costs.
C simply sums them:

```python
Z = Cost_Routing_scaled_distance     # scaled
  + Cost_Direct_All_scaled_distance  # scaled
  + Cost_Vehicles_raw_fixed          # raw, NOT scaled
  + Cost_Depots_raw_fixed            # raw, NOT scaled
```

Therefore:

- Do **not** scale depot fixed costs.
- Do **not** scale vehicle fixed costs.
- Only distance components (`Cost_Routing`, `Cost_Direct_All`) use Arslan-scaled
  distances.

A contributor who scales the fixed-cost terms will silently corrupt the objective
and the gap. This asymmetry is intentional and matches C.

### Routing cost

```python
routing_cost = sum(F_R * dist_scaled(a, b) for every routing arc a -> b used)
```

Use actual route geometry. Include depot-to-client, client-to-client, and client-to-depot routing arcs.

### Direct Allocation cost — zero return, one-way only

Direct Allocation is one-way assignment:

```python
direct_allocation_cost = sum(
    F_A * dist_scaled(depot_i, client_j)
    for each DA assignment (i, j)
)
```

No DA return cost.
No DA client-client cost.
No DA vehicle fixed cost.

The intended DA model is:

```text
depot -> client: F_A * dist_scaled(depot, client)
client -> depot: 0
```

Zero-return DA is the v3 default. PyVRP has handled zero-return DA arcs acceptably in previous experiments, so the technical return arc should be `0` by default.

Only if a concrete solver/penalty issue appears during execution may v3 activate a technical fallback: use a small positive technical return cost for PyVRP stability, exclude that technical return from reported objective, and keep `Cost Direct All` as one-way C/MILP assignment cost only. This is an implementation fallback, not an unresolved modeling ambiguity.

### Vehicle fixed cost

C counts one routing vehicle per depot-to-client route departure arc:

```python
vehicle_cost = n_used_routing_routes * veh_fixed_cost * VFX
```

For many current `.dat` instances, `veh_fixed_cost` is zero.

Do not count DA assignments as vehicles for fixed vehicle cost unless a future C audit contradicts this. Current C says no DA vehicle fixed cost.

### Depot fixed/opening cost

For LoRP-FSD, depot cost depends on selected size:

```python
depot_cost = sum(dep_cost[i][selected_size_i] for selected depots)
```

When reproducing an Excel row with fixed selected depots/sizes, read this as `Cost (Depots)` or recompute via C formula for validation.

---

## 5. F_R and F_A policy — encode weights in PyVRP, reconstruct ex-post

Settled v3 baseline decision: PyVRP internal edge costs encode the objective weights so the solver searches under the same economic tradeoff as the C/MILP objective.

Routing profile:

```python
routing_edge_cost_ij = F_R * dist_scaled_ij
```

Direct Allocation profile:

```python
da_edge_cost_depot_client = F_A * dist_scaled_depot_client
da_edge_cost_client_depot = 0
```

Final reported costs must still be reconstructed ex-post from the parsed solution using the C/MILP objective definition:

```python
Cost_Routing = sum(F_R * dist_scaled(a, b) for routing arcs a -> b)
Cost_Direct_All = sum(
    F_A * dist_scaled(depot_i, client_j)
    for each final DA assignment (i, j)
)
Cost_Vehicles = fixed_vehicle_cost * number_of_used_routing_vehicles
Cost_Depots = selected depot/sizing fixed cost
Z_PyVRP = Cost_Routing + Cost_Direct_All + Cost_Vehicles + Cost_Depots
```

Rationale:

- Encoding `F_R` and `F_A` inside PyVRP gives solver correct search incentives.
- Ex-post reconstruction gives academically traceable objective components.
- Ex-post reconstruction protects reports from PyVRP rounding, technical arcs, or internal representation issues.
- DA remains one-way only.
- DA return cost remains zero.
- No client-client DA cost.
- No multitrip DA.

---

## 6. Core v3 PyVRP construction: capacity-relaxed model

The v3 PyVRP builder intentionally relaxes aggregate depot capacity at construction time because PyVRP cannot natively enforce:

```python
demand_routing_i + demand_DA_i <= Cap_i
```

### Routing service options

For each active depot `i` with selected capacity `Cap_i` and vehicle capacity `Q`:

```python
n_full = floor(Cap_i / Q)
residual = Cap_i - n_full * Q
```

Create:

- `n_full` routing vehicles with capacity `Q`,
- one residual routing vehicle with capacity `residual` if `residual > 0`.

Routing uses a complete routing graph over depots and clients, except forbidden routing assignments from repair iterations.

Routing graph exclusion rule:

```python
(depot_i, client_j) in forbidden_routing_assignments
    => client_j cannot be served by routing from depot_i in this model rebuild
```

### Direct Allocation service options

For every active depot `i` and client `j` satisfying:

```python
dist_scaled(i, j) <= R
```

create a DA service option/vehicle for that depot-client pair:

- capacity exactly `demand_j`,
- no fixed vehicle cost,
- **serves only client `j`** (hard requirement, see below),
- true cost `F_A * dist_scaled(i, j)`,
- technical return arc cost `0` if PyVRP can handle it,
- no multitrip DA,
- no client-client DA travel as real cost.

### DA exact service binding (hard v3 requirement)

Creating "one DA vehicle per feasible depot-client pair" is **not sufficient**
unless that DA option can only ever serve its intended client. A DA option for
`(depot_i, client_j)` with capacity `demand_j` could otherwise serve a different
client `k` with `demand_k <= demand_j`, where `dist_scaled(i, k) > R` — silently
violating the radius rule.

For each DA option `(depot_i, client_j)`:

- it may serve **only** `client_j`,
- conceptual reachability is exactly:

  ```text
  depot_i  -> client_j
  client_j -> depot_i
  ```

- it must not serve any other client.

If the builder can enforce this cleanly (per-pair restricted reachability /
mutually-exclusive service options), do so. If PyVRP cannot enforce it cleanly
through the builder, the parser/audit **must reject** any DA route that violates:

```python
len(route.clients) == 1
route.client == intended_client_for_DA_option
dist_scaled(depot, client) <= R
```

Flag any violation as:

```text
DA_ASSIGNMENT_BINDING_VIOLATION
```

DA remains: one-way cost, zero return cost, no client-client DA, no multitrip DA,
no DA vehicle fixed cost.

### Consequence

The first model can assign full routing capacity from a depot and also assign DA clients to the same depot. Therefore it may violate C/MILP aggregate capacity and may produce a super-optimal relaxed objective.

The first-pass metric is not standard gap. Use `RELAXATION_DEVIATION` until repaired feasibility is achieved.

### `.dat` global vehicle count policy

Settled v3 baseline decision: do not enforce the `.dat` global vehicle count as a binding fleet cap unless the C congruency test later proves it is binding.

Treat `.dat` `n_vehicles` as a legacy/global availability parameter, not as the primary capacity mechanism for LoRP-FSD v3.

Routing vehicle availability is generated from selected depot capacity:

```python
n_full = floor(Cap_i / Q)
residual = Cap_i - n_full * Q
```

For each active depot:

- add `n_full` routing vehicles with capacity `Q`,
- add one residual routing vehicle with capacity `residual` if `residual > 0`.

DA service options are generated per feasible depot-client pair and do not consume fixed vehicle activations.

Rationale:

- Central capacity mechanism in LoRP-FSD is selected depot capacity.
- PyVRP cannot model aggregate depot capacity directly, so v3 uses capacity-relaxed construction plus repair.
- Enforcing `.dat` `n_vehicles` globally too early may add an artificial restriction not aligned with C/MILP sizing formulation.
- C congruency may later reveal whether `n_vehicles` is binding; until then, it is not a hard v3 cap.

---

## 7. Post-solve capacity and feasibility audit

After every solve, reconstruct semantic records:

```python
demand_routing_i = sum(demand_j for clients routed from depot_i)
demand_DA_i = sum(demand_j for clients directly allocated from depot_i)
demand_total_i = demand_routing_i + demand_DA_i
excess_i = max(0, demand_total_i - Cap_i)
```

A solution is feasible for the fixed facility design only if:

- every client is served exactly once,
- all `excess_i == 0`,
- all route distances satisfy `Length`,
- all route vehicle loads satisfy vehicle capacity,
- all DA assignments satisfy `dist_scaled <= R`,
- no suspicious huge PyVRP penalty distances appear.

Penalty-distance diagnostic default:

```python
penalty_distance_threshold = max(1_000_000, 1000 * Length)
```

If any route distance exceeds this threshold, flag:

```text
PENALTY_DISTANCE_SUSPECTED
```

This is an audit diagnostic for missing arcs, invalid graph construction, internal PyVRP penalty routes, or distances impossible under scaled `Length`. It does not repair the model by itself.

If all excess values are zero and other checks pass, the relaxed solution is already feasible.

If any `excess_i > 0`, start repair.

---

## 8. Savings-based routing elimination repair

Repair acts only on routing routes from overloaded depots.

For every routing route from overloaded depot `i`:

```text
Depot_i -> c1 -> c2 -> ... -> ck -> Depot_i
```

compute the marginal scaled distance saving from removing each client.

Internal client `c_m` with predecessor `p` and successor `s`:

```python
saving(c_m) = dist_scaled(p, c_m) + dist_scaled(c_m, s) - dist_scaled(p, s)
```

First client `c1`:

```python
saving(c1) = dist_scaled(depot_i, c1) + dist_scaled(c1, c2) - dist_scaled(depot_i, c2)
```

Last client `ck`:

```python
saving(ck) = dist_scaled(c_{k-1}, ck) + dist_scaled(ck, depot_i) - dist_scaled(c_{k-1}, depot_i)
```

Single-client route:

```python
saving(c1) = dist_scaled(depot_i, c1) + dist_scaled(c1, depot_i)
```

If using objective savings:

```python
weighted_saving = F_R * saving
```

For each overloaded depot, create candidate rows:

```text
depot
route_id
client_id
client_demand
saving
weighted_saving
```

Sort by largest `weighted_saving` first.

Select candidates until:

```python
sum(demand_removed) >= excess_i
```

Greedy savings repair is the v3 baseline. Candidates are sorted by **largest weighted saving** first. If a candidate would strand a client, skip it and try the next candidate. If no feasible candidate set can cover the depot excess, mark repair failed for that row. Backtracking/local-search repair is future work, not part of v3 baseline.

Future extension: compare largest-saving vs saving-per-demand repair policies. The v3 baseline keeps largest weighted saving only.
---

## 9. Meaning of removal and forbidden routing assignments

Removing a client from an overloaded depot does not delete the client. It forbids one routing assignment in the next PyVRP rebuild.

Representation:

```python
forbidden_routing_assignments: set[tuple[int, int]]
```

If client `j` is selected for removal from routing at depot `i`:

```python
forbidden_routing_assignments.add((i, j))
```

The next PyVRP model must be rebuilt so client `j` cannot be served by routing from depot `i`.

Client `j` must still have at least one feasible service option:

- DA from depot `i` if `dist_scaled(i, j) <= R`,
- DA from another depot `h` if `dist_scaled(h, j) <= R`,
- routing from another depot `h` if `(h, j)` is not forbidden,
- otherwise repair is infeasible or candidate must be skipped.

### Why `forbidden_routing_assignments` (not depot-level forbidding) is the v3 baseline

The v3 baseline keeps the routing-only restriction abstraction:

```python
forbidden_routing_assignments: set[tuple[int, int]]   # (depot_id, client_id)
```

meaning: `client_id` cannot be served by **routing** from `depot_id` in the next
iteration. This restriction does **not** forbid DA from the same depot.

The repair heuristic first eliminates problematic routing structure/arcs from
overloaded depots. A removed routing client may still be served by DA from the
same depot, DA from another depot, routing from another depot, or any other
feasible option the rebuilt model allows.

**Critical caveat — same-depot DA does not auto-repair capacity.** Because C/MILP
depot capacity is `demand_routing_i + demand_DA_i <= Cap_i`, moving a client from
routing to DA *within the same depot* does **not** reduce that depot's total
demand. Therefore:

- capacity feasibility is judged **only after rerun**, by re-auditing aggregate
  `routing + DA` demand,
- routing-to-same-depot-DA is **not assumed** to repair capacity by itself,
- if same-depot DA does not clear the excess, the next iteration continues
  forbidding additional routing assignments until the solution becomes feasible
  or repair fails (`REPAIR_INFEASIBLE`).

Stronger depot-level forbidding (forbidding both routing and DA at a depot) and
local search are explicitly **future work**, not part of the v3 baseline.

---

## 10. Demand satisfaction check before rerun

Before rebuilding/rerunning after adding restrictions, check every client.

For every client `j`:

```python
has_routing = any((h, j) not in forbidden_routing_assignments for active depot h)
has_DA = any(dist_scaled(h, j) <= R for active depot h)
feasible = has_routing or has_DA
```

If any client has no feasible service option:

- reject that removal candidate and try the next-best candidate, or
- flag repair infeasible if no safe candidate set exists.

No rerun should start from a restriction set that strands a client.

---

## 11. Iterative model rebuild and stopping criteria

Repair changes the feasible routing assignment set. Therefore each repair iteration rebuilds the PyVRP model from scratch with the updated:

```python
forbidden_routing_assignments
```

Loop:

1. build relaxed PyVRP model with current forbidden set,
2. solve,
3. parse semantic routes and DA assignments,
4. reconstruct cost,
5. audit service, route length, DA radius, vehicle load, and aggregate depot capacity,
6. if feasible, stop,
7. if overloaded, compute savings candidates,
8. add safe forbidden routing assignments,
9. save diagnostics,
10. rebuild and rerun.

Stop when:

- all clients are served exactly once,
- all depot capacities satisfy `demand_routing_i + demand_DA_i <= Cap_i`,
- all route lengths respect `Length` in scaled units,
- all DA assignments respect `R` in scaled units,
- no astronomical PyVRP penalty distances appear,
- or maximum repair iteration limit is reached.

---

## 12. Plot and audit artifacts after every iteration

The v3 runner must save diagnostics after every solve/repair iteration.

Directory structure:

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
- `Cap_i`,
- `excess_i`,
- service coverage status,
- clients served exactly once flag/count,
- route length violations,
- route capacity violations,
- DA radius violations,
- current `forbidden_routing_assignments`,
- selected repair removals,
- route count by depot,
- route count by profile,
- maximum route distance,
- penalty distance suspected flag using `max(1_000_000, 1000 * Length)`,
- `Cost Routing`,
- `Cost Direct All`,
- `Cost Vehicles`,
- `Cost Depots`,
- total objective,
- comparison against MILP UB,
- metric label (`RELAXATION_DEVIATION`, `GAP`, or failure diagnostic).

---

## 13. Facility sizing policy

Exact C LoRP-FSD chooses depot and size with binary `Y[depot][size]`.

Size multipliers:

| size | multiplier |
|---:|---:|
| 1 | 0.50 |
| 2 | 0.75 |
| 3 | 1.00 |
| 4 | 1.25 |
| 5 | 1.50 |

Exact PyVRP alone cannot choose facility size. v3 first uses fixed Excel facilities/sizes:

```text
Depot1..4, sizeD*, CapD*, Cost (Depots)
```

This benchmarks routing/DA/service-mode behavior under the MILP selected facility design. If repaired solution satisfies all original constraints under that fixed design, report `GAP`. If not feasible, report relaxation/failure diagnostics.

Future versions may add external facility-size heuristics.

---

## 14. What PyVRP cannot model natively

PyVRP does not natively optimize full LoRP-FSD because it lacks direct support for:

- facility opening and sizing binary decisions,
- alternative service mode per client (routing vs DA assignment),
- shared depot capacity consumed by both routed and directly allocated clients,
- DA assignment variables with one-way assignment cost outside route distance,
- exact C-style objective component reporting.

Therefore v3 is a heuristic/approximation with explicit feasibility audit and iterative repair. It can produce a feasible solution under fixed facility design, but the first pass is a relaxation.

---

## 15. Comparison metric policy

### First relaxed solution

Do not call first-pass result a standard gap.

```python
RELAXATION_DEVIATION = (UB_MILP - Z_relaxed) / UB_MILP
```

Positive means relaxed solution is below MILP UB, as expected for a relaxation.

### Final repaired feasible solution

If final solution satisfies service, route length, DA radius, vehicle load, and aggregate depot capacity constraints:

```python
GAP = (Z_PyVRP - UB_MILP) / UB_MILP
```

Expected sign: nonnegative when `UB_MILP` is optimal or near-optimal and same constraints/objective are used.

If a final repaired feasible solution has `Z_PyVRP < UB_MILP` on an optimal MILP row, flag:

```text
NEGATIVE_GAP_MODELING_INCONSISTENCY
```

A feasible heuristic solution for the same minimization problem should not beat the exact MILP optimum/UB when the MILP row is optimal. Negative final gaps indicate one of:

- remaining relaxation,
- objective reconstruction mismatch,
- scaling mismatch,
- facility/depot cost mismatch,
- MILP row not optimal (check `gap`),
- data mismatch.

### Fixed facility design label

Because v3 initially uses Excel-selected facilities/sizes, reports should label the final gap as fixed-facility or conditional if needed:

```python
CONDITIONAL_GAP = (Z_PyVRP_fixed_facilities - UB_MILP) / UB_MILP
```

Use `GAP` only when docs/report clarify this is under fixed MILP facility design.

---

## 16. Settled v3 baseline decisions

These are implementation decisions, not open blockers:

1. **Initial v3 supports only `problemID=0`.**

   Use Arslan scaling:

   ```python
   scale = 100 / max_dist
   dist_scaled = dist_original * scale
   ```

   If another `problemID` is requested, raise `NotImplementedError("LoRP-v3 currently supports only problemID=0 Arslan scaling.")`.

2. **PyVRP edge costs encode `F_R` and `F_A`; reports reconstruct ex-post.**

   Routing edge cost = `F_R * dist_scaled`. DA outbound edge cost = `F_A * dist_scaled`. DA return edge cost = `0`. Final reported components are recomputed from parsed route and assignment records using C/MILP formulas.

3. **`.dat` `n_vehicles` is not binding in v3 baseline.**

   Routing vehicle availability is generated from selected depot capacity decomposition. The `.dat` global vehicle count is retained as metadata/diagnostic unless C congruency later proves it is binding.

4. **Zero-return DA is default.**

   ```text
   depot -> client: F_A * dist_scaled(depot, client)
   client -> depot: 0
   ```

5. **Reported `Cost Direct All` is one-way assignment cost only.**

   ```python
   sum(F_A * dist_scaled(depot, client) for DA assignments)
   ```

6. **A small positive DA return cost is fallback only if empirically needed.**

   If PyVRP produces concrete penalty/stability issues, a technical positive return cost may be used but is excluded from reported objective.

7. **Penalty-distance threshold is an audit diagnostic.**

   ```python
   penalty_distance_threshold = max(1_000_000, 1000 * Length)
   ```

8. **Greedy savings repair is v3 baseline.**

   If greedy repair cannot find a non-stranding candidate set, row is marked repair failed. Backtracking/local-search repair is future work.

9. **Each repair iteration rebuilds PyVRP model from scratch.**

   The accumulated `forbidden_routing_assignments: set[tuple[int, int]]` is passed to the builder. Repair forbids selected client `j` from routing service at overloaded depot `i` in next model. Client remains in problem.

10. **First relaxed solve is not standard gap.**

    Report `RELAXATION_DEVIATION = (UB_MILP - Z_relaxed) / UB_MILP`.

11. **Final feasible repaired solve uses standard gap.**

    If all C/MILP feasibility rules hold, report `GAP = (Z_PyVRP - UB_MILP) / UB_MILP`. If final feasible `Z_PyVRP < UB_MILP` on an optimal MILP row, flag `NEGATIVE_GAP_MODELING_INCONSISTENCY`.

12. **Scaled units are mandatory.**

    DA feasible iff `dist_scaled <= R`; route feasible iff `route_dist_scaled <= Length`; objective components remain scaled for Excel comparison; never divide final costs by scale.

13. **PyVRP uses high-precision integer discretization.**

    `PYVRP_INT_SCALE = 10_000`; internal edge costs and route-length limits are integerized via `round(value * PYVRP_INT_SCALE)`; DA feasibility and final reported costs remain continuous scaled. Never compare the PyVRP integer objective directly against Excel.

14. **DA options are bound to exactly one client.**

    Each `(depot_i, client_j)` DA option may serve only `client_j`. If the builder cannot enforce this cleanly, the parser/audit rejects any DA route with more than one client, a wrong client, or `dist_scaled > R`, flagging `DA_ASSIGNMENT_BINDING_VIOLATION`.

15. **The objective mixes scaled distance costs and raw fixed costs.**

    Routing and DA costs use Arslan-scaled distances; vehicle and depot fixed costs stay raw/unscaled. Never scale fixed-cost terms.

16. **`forbidden_routing_assignments` stays routing-only.**

    Repair forbids routing `(depot_id, client_id)` only and allows same-depot DA. Same-depot DA is not assumed to repair aggregate capacity; feasibility is re-audited after each rerun. Depot-level forbidding and local search are future work.

### Remaining unresolved blockers

None before C congruency test.

---

## 17. Required v3 audit outputs per solved row

Every row result should include:

- instance name and resolved file path,
- `problemID`, `R`, `Length`, `F_R`, `F_A`, `VFX`, `original`,
- `max_dist`, `scale`,
- selected depots/sizes/capacities,
- iteration number,
- current `forbidden_routing_assignments`,
- routing route records with scaled distance and assigned depot,
- DA assignment records with one-way scaled distance,
- repair candidate rows and selected removals,
- per-depot demand split: routing, DA, total, capacity, excess,
- route length violations,
- route capacity violations,
- DA radius violations,
- suspicious huge distance diagnostics,
- service level and served-exactly-once check,
- objective components:
  - routing cost,
  - DA cost,
  - vehicle fixed cost,
  - depot cost,
  - total,
- comparison metric with correct label.
