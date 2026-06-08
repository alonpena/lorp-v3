# C Solver Audit — LoRP-FSD Source of Truth

Audit target: `/Users/apena/lor-v3/reference/LoRPSD` copied from `/Users/apena/Desktop/LoRPSD`.

Files inspected:

- `main.cpp`
- `models.cpp`
- `stcmodels.cpp`
- `stcmodels.h`
- `files.cpp`
- `files.h`
- `bash_LoRP.sh`
- `startJob.sh`
- `CMakeLists.txt`
- Excel schema from `/Users/apena/lor-v3/results_MILP.xlsx`, sheet `LoRP-FSD`

Conclusion: for the Excel `LoRP-FSD` sheet, the relevant model is the deterministic LoRP with depot sizing decisions and direct allocation, implemented by `det_LoRP_DSD()` in `stcmodels.cpp`, called through `create_detLoRP_sizing()` when `-original 0`.

---

## 1. CLI flags

CLI parsing lives in `files.cpp::ReadAlgorithmParams()`. It requires exactly 11 flag-value pairs.

| Flag | C target | Meaning in current deterministic run |
|---|---:|---|
| `-results` | `results` string | Output file path. C appends one tab-separated result row. |
| `-problemID` | `MetaData.problemID` → `Data.problemID` | Scaling mode. `0` = Arslan scaling; `1` = Prodhon scaling; `2` = no scaling. |
| `-WR` | `Data.WR` | Routing arc weight. Multiplies routing distance terms. |
| `-WA` | `Data.WA` | Direct allocation weight. Multiplies DA assignment distance terms. |
| `-Radius` | `Data.Radius` | DA coverage threshold, compared to `Data.dist` after scaling if `problemID < 2`. |
| `-instance` | `instance` string | `.dat` instance path. |
| `-VFX` | `Data.VFX` | Boolean-like multiplier for vehicle fixed cost. With `problemID == 0`, `Data.vehiclesfixed = Data.vehiclesfixed * Data.VFX`. If `0`, vehicle fixed costs become zero. If `1`, original vehicle fixed cost retained. |
| `-OF` | `MetaData.OF` | Parsed but then ignored in `main.cpp`, because `Data.OF=1` is hard-coded. Current deterministic runs are always cost objective. |
| `-original` | `Data.originalLoRP` | Model selector. `1` calls standard LoRP (`createmodelnew()` in `models.cpp`). `0` calls LoRP-FSD / sizing (`create_detLoRP_sizing()` in `stcmodels.cpp`). |
| `-model` | `Data.model` | Parsed and stored, but not used to choose model in current `main.cpp` deterministic path. |
| `-length` | `Data.lenghtMax` | Maximum route length, compared against scaled routing route distance if `problemID < 2`. |

Alan command example uses `-original 1`, which this source maps to standard LoRP, not LoRP-FSD. Excel sheet `LoRP-FSD` corresponds to `-original 0` in this code path.

Important code facts:

- `main.cpp` sets `Data.OF=1; //always cost`, regardless of `-OF`.
- `main.cpp` calls `ReadData_sizing(instance, Data)` unconditionally for this executable path.
- `main.cpp` dispatches:
  - `Data.originalLoRP == 1` → `createmodelnew()` → standard LoRP.
  - else → `create_detLoRP_sizing()` → LoRP-FSD / sizing.

---

## 2. Scaling

Scaling lives in `main.cpp::scaledistance()`.

### `problemID = 0`: Arslan scaling

Confirmed.

Formula:

```cpp
Data.dist[i][j] = Data.dist[i][j] * (100 / Data.maxdist);
Data.worstd[i] = Data.worstd[i] * 100 / Data.maxdist;
```

where `Data.maxdist` is the maximum original Euclidean distance over all depot/client nodes.

Python policy for `problemID=0`:

```python
scale = 100.0 / max_dist
scaled_distance = euclidean_distance * scale
```

### `problemID = 1`: Prodhon scaling

C applies:

```cpp
Data.dist[i][j] = 1.0 * int(ceil(Data.dist[i][j] * 100));
Data.dep_cost[i][j] = 1.0 * round(Data.dep_cost[i][j]);
```

Not source of truth for current Alan LoRP-FSD Excel command, which uses `problemID=0`.

### `problemID = 2`: no scaling

`main.cpp` only calls `scaledistance(Data)` if `Data.problemID < 2`.

### Are Radius and Length scaled?

Yes for `problemID=0` runs.

`Radius` and `Length` are not themselves transformed in model code. Instead, all `Data.dist` values are replaced by scaled distances before model creation. Therefore constraints compare against scaled distances:

```cpp
Data.dist[i][j] * A[i - Data.T][j] <= Data.Radius * selected_size_sum

t[i][j] <= Data.lenghtMax * X[i][j]
```

So for Python:

```python
DA feasible iff dist_original * scale <= R
route feasible iff route_distance_original * scale <= Length
```

Do not convert `R_raw = R / scale` except for plotting.

### Are Excel UB and cost columns in scaled units?

Yes, for `problemID=0`. The model objective and output components use `Data.dist` after Arslan scaling. Excel `UB`, `Cost Routing`, and `Cost Direct All` are in scaled objective units. Do **not** divide by `scale` when comparing against Excel.

---

## 3. Objective function

For LoRP-FSD, exact source is `stcmodels.cpp::det_LoRP_DSD()`.

Objective:

```cpp
Cost = Cost1 + Cost2 + Cost4 + DirectALL;
modelo.setObjective(Cost, GRB_MINIMIZE);
```

Components:

### Routing cost (`Cost Routing`)

```cpp
Cost1 += Data.WR * Data.dist[i][j] * X[i][j];
```

- All non-depot-depot routing arcs.
- `Data.dist` is already scaled for `problemID=0`.
- `WR` multiplies routing arcs.

### Direct allocation cost (`Cost Direct All`)

```cpp
DirectALL += Data.WA * Data.dist[i + Data.T][j] * A[i][j];
```

- One-way client-to-depot/depot-client distance (symmetric matrix).
- No return arc.
- No client-client DA travel.
- `WA` multiplies DA assignments.

### Vehicle fixed cost (`Cost (Vehicles)`)

```cpp
Cost2 += Data.vehiclesfixed * X[j][i];
```

where `j` is depot and `i` is customer. This counts vehicles/routes by number of depot-to-customer departure arcs.

For `problemID=0`, `scaledistance()` applies:

```cpp
Data.vehiclesfixed = Data.vehiclesfixed * Data.VFX;
```

So `VFX=0` disables vehicle fixed cost, and `VFX=1` keeps the instance vehicle fixed cost.

### Depot fixed/opening cost (`Cost (Depots)`)

```cpp
Cost4 += Data.dep_cost[i][j] * Y[i][j];
```

- In LoRP-FSD, depot cost depends on selected depot size.
- It is recomputed from `.dat` base costs by `ReadData_sizing()` before model solving.
- Excel stores solved value of this component.

### `OF`

`-OF` is parsed but effectively ignored in current executable path because `main.cpp` hard-codes `Data.OF = 1`. Model objective is cost. Some constraints have `if (Data.OF == 1)`, therefore current generated results use cost-mode constraints.

---

## 4. Direct Allocation exact definition

Direct Allocation is a binary assignment variable:

```cpp
A[customer][depot] ∈ {0,1}
```

It is not a route and not a multi-client tour.

### Service mode exclusivity

Each customer must be either routed or directly allocated:

```cpp
R2 + Rauxi == 1
R2b + Rauxi == 1
```

where `R2/R2b` are incoming/outgoing routing arcs and `Rauxi = sum_depot A[customer][depot]`.

For cost-mode depot assignment:

```cpp
sum_j f[j][i] + sum_j A[i][j] == 1
```

### DA feasibility

For LoRP-FSD:

```cpp
Data.dist[i][j] * A[i - Data.T][j] <= Radius * sum_x Y[j][x]
```

Since `Data.dist` is scaled for `problemID=0`, radius is scaled.

### DA cost

```cpp
DirectALL += WA * Data.dist[customer][depot] * A[customer][depot]
```

One-way assignment cost only.

### No DA vehicle fixed cost

No objective term charges vehicles for DA. `Cost2` only counts routing vehicle departure arcs `X[depot][customer]`.

### Implication

For PyVRP v3, DA must be treated conceptually as assignment. Any PyVRP DA vehicles/arcs are technical artifacts only. Final reported DA cost must be reconstructed as:

```python
cost_DA = sum(WA * dist_scaled(depot, client) for assigned DA pairs)
```

Do not use PyVRP client-client DA route distance as final cost.
Do not use multitrip DA as final semantic model.

---

## 5. Depot capacity

Critical finding: C enforces depot capacity on total demand assigned to depot, including both routing and DA.

For LoRP-FSD:

```cpp
demandssum += (f[j][i] + A[i][j]) * customer_demand[i]
sizesum += dep_cap[j][x] * Y[j][x]
model.addConstr(demandssum <= sizesum)
```

Therefore:

```text
demand_routing_i + demand_DA_i <= selected_depot_capacity_i
```

Moving a client from routing to DA at the same depot does **not** repair depot capacity. It changes service mode and cost, not depot demand.

For PyVRP repair logic:

- If depot is overloaded, repair must move demand to another depot, change selected depot size, or change selected depot set.
- Converting same-depot routing to DA cannot fix total depot capacity.

---

## 6. Facility sizing

LoRP-FSD sizing is generated in `files.cpp::ReadData_sizing()`.

`Data.facsize = 5`.

For each depot `i` and size index `j = 0..4`:

```cpp
dep_cap[i][j] = base_QD_i * (1 + (-2 + j) * 0.25)
```

Thus sizes are:

| C index `j` | Output size | Capacity multiplier |
|---:|---:|---:|
| 0 | 1 | 0.50 |
| 1 | 2 | 0.75 |
| 2 | 3 | 1.00 |
| 3 | 4 | 1.25 |
| 4 | 5 | 1.50 |

Cost formula:

```cpp
dep_cost[i][j] = cost_i + ((dep_cap[i][j] - base_QD_i) / (2 * base_QD_i)) * (totalfix / T)
```

For `problemID=1`, costs are rounded later. For `problemID=0`, this formula remains continuous/double.

Size selection variable:

```cpp
Y[depot][size] ∈ {0,1}
sum_size Y[depot][size] <= 1
```

Capacity:

```cpp
sum_customers (f + A) * demand <= sum_size dep_cap * Y
```

Depot output fields are generated only for selected depot-size pairs.

---

## 7. Output mapping to Excel

C output for LoRP-FSD (`stcmodels.cpp::det_LoRP_DSD`) writes tab-separated values:

```text
instance
"LoRP-SD"
objectivefun
WR
WA
Radius
lenghtMax
f
ObjVal
ObjBound
Status
Runtime
MIPGap
Cost1
Cost2
Cost4
DirectALL
"depots"
[per selected depot slots...]
"ND" NDEP
"NV" NVE
"RAT" avg_usage
```

Excel sheet `LoRP-FSD` columns map as:

| Excel column | C source |
|---|---|
| `name` | instance basename/path postprocessed from C `instance` |
| `problem` | literal `LoRP-SD` |
| `of` | `objectivefun`; current = `cost` |
| `F_R` | `Data.WR` |
| `F_A` | `Data.WA` |
| `R` | `Data.Radius` |
| `Length` | `Data.lenghtMax` |
| `p (not used)` | `Data.f` |
| `UB` | Gurobi `ObjVal` |
| `LB` | Gurobi `ObjBound` |
| `status_numer` | Gurobi numeric status |
| `opt num` | likely postprocessed optimal indicator; not directly emitted by C source seen |
| `Status name` | postprocessed from Gurobi numeric status; not directly emitted by C source seen |
| `cpu time` | Gurobi `Runtime` |
| `gap` | Gurobi `MIPGap` |
| `Cost Routing` | `Cost1.getValue()` |
| `Cost (Vehicles)` | `Cost2.getValue()` |
| `Cost (Depots)` | `Cost4.getValue()` |
| `Cost Direct All` | `DirectALL.getValue()` |
| `depots` | literal `depots` |
| `Depot1..Depot4` | selected depots, emitted as `d{i+1}` in selection order by depot ID |
| `sizeD1..sizeD4` | emitted as literal `s`, then size number `x+1`; Excel keeps numeric size |
| `CapD1..CapD4` | `Data.dep_cap[i][x]` |
| `DemandD1..DemandD4` | `sum_k (f[i][k] + A[k][i]) * demand[k]` |
| `%UsageD1..D4` | `100 * demand / dep_cap[i][x]` |
| `VehiclesD1..D4` | `sum_j round(X[depot][customer_j])`, routing vehicles departing depot |
| `TotalDepots` | `NDEP` |
| `TotalVehicles` | `NVE` |
| `Avg % Usage Deps` | `avgratio / NDEP` |

Note: C writes selected depots in real depot ID order, not positional slot semantics. Excel slots are postprocessed positions. The real depot ID is inside label `d#`.

---

## 8. Instance format

`ReadData_sizing()` confirms expected `.dat` format:

```text
n_clients
n_depots
max_depots_open
n_vehicles
[depot coords: x y, one per depot]
[client coords: x y, one per client]
vehicle_capacity
[depot capacities, one per depot]
[client demands, one per client]
[depot fixed costs, one per depot]
vehicle_fixed_cost
trailing integer flag
```

The trailing integer is mandatory in C and must be `0` or `1`; otherwise C exits. Python may treat it as optional for robustness, but exact C format expects it.

IDs are implicit and 1-indexed in output:

- depots `1..T`
- customers `1..N`

---

## 9. Key findings for Python v3

1. `problemID=0` uses Arslan scaling: `dist_scaled = dist_original * 100 / max_dist`.
2. `R` and `Length` are in scaled units for Excel/MILP comparisons.
3. Excel objective components are in scaled objective units. Do not divide by scale.
4. Direct Allocation is one-way assignment, not routing.
5. DA has no client-client travel and no vehicle fixed activation cost in C.
6. Depot capacity uses total assigned demand: routing + DA.
7. `-original 0` is LoRP-FSD / sizing; `-original 1` is standard LoRP.
8. `-OF` and `-model` do not change current deterministic source path.
9. PyVRP cannot natively reproduce full LoRP-FSD because facility sizing, alternative DA assignment, and shared depot capacity are MILP-level decisions.

