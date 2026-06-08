# Change History / Audit Trail

## 2026-05-07/08 Working Session

### 1. Test infrastructure
- Added pytest dev dependency and pytest config in `pyproject.toml`.
- Created `tests/`.
- Added fixtures in `tests/conftest.py`.
- Added unit/integration tests:
  - `tests/test_dat_loader.py`
  - `tests/test_instance_adapter.py`
  - `tests/test_xlsx_loader.py`
  - `tests/test_da_geometry.py`
  - `tests/test_reporting.py`
- Current status: `119 passed`.

### 2. Modularization
Original `lor_pyvrp_benchmark.py` was doing too much. Extracted:

- `da_geometry.py`
  - `dist_euclid`
  - `dist_manhattan`
  - `compute_max_distance`
  - `build_direct_allocation_data`
  - `assign_da_clients`

- `pyvrp_model.py`
  - PyVRP import guard
  - `build_full_model`
  - `solve_fast`

- `reporting.py`
  - `extract_kpis_level1`
  - `extract_kpis_level2`
  - `extract_solution_metrics`
  - `compute_solution_costs`
  - `build_full_report`

- `viz.py`
  - `plot_instance`
  - `plot_solution`

- `lor_pyvrp_benchmark.py` became facade/re-export layer.

### 3. Instance resolution
Problem: Excel LoRP-FSD names do not always match files exactly. Some files have `coord` prefix.

Added `instance_resolver.py`:
1. exact match
2. `coord` prefix match
3. unique suffix glob
4. report `MISSING` or `AMBIGUOUS`, never guess unsafe matches

Updated:
- `audit_missing_dat.py`
- `run_fsd_batch.py`

Audit after resolver:
- Excel rows total: 1185
- Rows with `.dat`: 915
- Rows missing `.dat`: 270
- Unique referenced instances: 22
- Unique matched instances: 17
- Unique missing instances: 5

Still missing:
- `50-5-2.dat`
- `50-5-3b.dat`
- `r30x5b-1.dat`
- `r40x5a-3.dat`
- `r40x5b-1.dat`

### 4. Arslan distance scaling
Clarified from original C code:

```cpp
dist[i][j] = dist[i][j] * (100 / maxdist)
```

Python model now uses:

```python
escala = 100.0 / max_dist
edge_routing = raw_dist * escala * F_R
edge_da = raw_dist * escala * F_A
```

No `[0,1]` final scaling. No explicit rounding.

### 5. Cost interpretation
Originally we recovered raw distance by dividing by scale. This was wrong for comparison to MILP Excel, because MILP objective uses Arslan-scaled costs.

Changed reporting:
- `costo_routing_pyvrp = dist_routing_total` directly
- `costo_da_pyvrp = dist_da_total` directly
- no `/ escala`
- no double multiplying by `F_R` / `F_A`

Depot costs are still added from Excel:

```python
total = routing + da + vehicles + config.cost_depots
```

### 6. Gap definition
Changed final gap to absolute comparison:

```python
raw_gap = (pyvrp_total - milp_ub) / milp_ub
abs_gap = abs(raw_gap)
```

Interpretation:
- `raw_gap < 0`: PyVRP below MILP, model mismatch warning
- `abs_gap > 0.20`: too far threshold

### 7. Direct Allocation policy
Current DA policy:
1. A client is DA-feasible for depot `i` iff Euclidean distance <= `R`.
2. Build all feasible `(distance, depot, client)` triples.
3. Sort globally by distance.
4. Assign nearest first if depot capacity allows.
5. One client assigned at most once.
6. DA has priority over routing.
7. DA vehicle model:
   - one vehicle per DA client
   - capacity equals that client demand
   - start/end at assigned depot
   - route depot -> client -> depot
   - return arc cost = 0
   - no DA activation cost currently

### 8. Routing vehicle policy
After DA preprocessing:

```python
remaining_i = cap_i - demand_DA_i
n_full = floor(remaining_i / veh_cap)
residual = remaining_i % veh_cap
```

Create:
- `n_full` routing vehicles with full capacity `veh_cap`
- one residual vehicle if residual > 0, with capacity `residual`

### 9. Capacity repair
Problem found: DA greedy could leave routing residual capacity too fragmented/small.

Example row 124 before repair:
- D5 cap = 140
- DA demand = 126
- routing residual = 14
- routing client demand = 18
- total served at D5 = 144 > 140

Added repair in `assign_da_clients()`:
- After greedy DA, build routing residual capacities.
- Check if remaining routing demands can be packed into routing capacities.
- If not feasible, demote DA clients back to routing.
- Demotion preference: farthest DA clients first.
- Repeat until routing demands pack.

Result for row 124 after repair:
- D4 total 173 / 175
- D5 total 137 / 140
- no capacity violation

### 10. Length constraint
Added original Excel `Length` constraint to routing vehicles:

```python
max_distance = Length * escala
```

Applied to:
- full routing vehicle types
- residual routing vehicle types

DA route length constraint not currently applied because DA is one direct client trip.

### 11. Batch script
Added `run_fsd_batch.py`:
- iterates all LoRP-FSD rows
- resolves `.dat` files row-by-row
- keeps missing/ambiguous rows in output
- uses `tqdm`
- exports detailed audit CSV with stats rows

Output:
- `pipeline_out/fsd_batch_results_with_stats.csv`

### 12. Plot scripts
Added:
- `plot_batch_results.py`
- `watch_csv_and_plot.py`
- `plot_sample_resolved_instances.py`

Plots:
- gap histograms
- signed gap histograms
- PyVRP vs MILP scatter
- gap by R/F_A
- cost breakdowns
- depot usage boxplot
- runtime histogram
- sample instance behavior plots

### 13. Minimal analyst export
Problem: detailed CSV had too many sparse real-depot-ID columns (`d1`, `d2`, `d3`, `d5`, etc.).

Added `export_fsd_minimal.py`.

Exports slot-based table like original Excel:
- `Depot1..Depot4`
- `Depot1_id..Depot4_id`
- `CapD1..CapD4`
- MILP demand/usage/vehicles
- PyVRP total/DA/routing demand
- PyVRP total/DA/routing usage
- PyVRP DA/routing vehicles
- PyVRP DA/routing costs

Outputs:
- `pipeline_out/fsd_minimal_results.csv`
- `pipeline_out/fsd_minimal_results_excel_locale.csv` (`;` separator, decimal comma)
- `pipeline_out/fsd_minimal_results.xlsx`

### 14. Current requested isolated iteration
Added `run_fsd_first10_iteration.py`.

Purpose:
- run only first 10 resolvable LoRP-FSD rows
- do not overwrite main batch CSV
- print/log all intermediate steps
- write isolated CSV/XLSX/log

Outputs:
- `pipeline_out/iteration_first10/first10_resolved_current_policy.csv`
- `pipeline_out/iteration_first10/first10_resolved_current_policy.xlsx`
- `pipeline_out/iteration_first10/first10_resolved_current_policy.log`
