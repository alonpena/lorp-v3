# lor_pyvrp_benchmark

Facade module. Re-exports main API from all modules plus solver/report code.

## What it contains
- `.dat` loading imports from `dat_loader`
- Excel loading imports from `xlsx_loader`
- adaptation imports from `instance_adapter`
- PyVRP model build
- DA heuristic
- KPI extraction
- report generation
- plots

## Main API

### IO
- `load_instances_from_zip(zip_path, extract_to='.')`
- `build_experiments_df(excel_path, instance_folder)`
- `config_from_row(row)`

### Instance / model helpers
- `build_direct_allocation_data(inst, radius)`
- `compute_max_distance(inst)`
- `assign_da_clients(inst, da_data, veh_cap)`
- `build_full_model(inst)`
- `solve_fast(m, runtime=5, n_runs=3)`

### KPI / report
- `extract_kpis_level1(inst, res, info)`
- `extract_kpis_level2(inst, res, info)`
- `build_full_report(inst, res, config, info)`
- `extract_solution_metrics(res, kpis1, inst_mod)`
- `compute_solution_costs(solution, kpis1, config, inst, scale)`

### Plot
- `plot_instance(inst, da_data=None)`
- `plot_solution(inst, res, info)`

## Model logic

### Direct allocation
- Client eligible if distance to depot `<= R`
- Assign to nearest feasible depot
- DA depot capacity = `veh_cap * floor(depot_cap / veh_cap)`
- DA return arc cost = `0`

### Routing
- Routing graph excludes DA-served clients
- Arc cost = Euclidean distance * scale * `F_R`
- DA arc cost = Euclidean distance * scale * `F_A`
- `scale = 100 / max_distance(all nodes)`

### Vehicle types
- Routing vehicles: per depot, capacity residual after DA assignment
- DA vehicle: 1 multitrip vehicle per active depot

### Fixed costs
- Depot fixed cost comes from Excel report, not PyVRP model
- Vehicle cost uses `veh_fixed_cost` from `.dat`

## End-to-end usage
```python
from dat_loader import load_dat
from xlsx_loader import load_lorp_fsd_mapping
from instance_adapter import adapt_instance_from_row
from lor_pyvrp_benchmark import build_full_model, solve_fast, build_full_report, config_from_row

mapping = load_lorp_fsd_mapping("results_MILP.xlsx", instance_folder="instances")
row = mapping.iloc[0]
base = load_dat(f"instances/{row['instance']}")
inst = adapt_instance_from_row(base, row)
config = config_from_row(row)

m, info = build_full_model(inst)
res = solve_fast(m)
report = build_full_report(inst, res, config, info)
```

## Notes
- PyVRP must be installed via `uv sync`
- `load_lorp_fsd_mapping()` filters rows if `instance_folder` given and `.dat` file missing
