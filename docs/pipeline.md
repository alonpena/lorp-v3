# pipeline

## Inputs
- `instances/*.dat`
- `results_MILP.xlsx`

## Steps
1. Load mapping from `LoRP-FSD`
2. For each row:
   - get `row['instance']`
   - load matching `.dat`
   - adapt instance with Excel specs
3. Build PyVRP model
4. Solve with multi-seed fast search
5. Extract KPIs and report
6. Compare with MILP benchmark

## Batch pseudo-code
```python
from dat_loader import load_dat
from xlsx_loader import load_lorp_fsd_mapping
from instance_adapter import adapt_instance_from_row
from lor_pyvrp_benchmark import build_full_model, solve_fast, build_full_report, config_from_row

mapping = load_lorp_fsd_mapping("results_MILP.xlsx", instance_folder="instances")
rows = []

for _, row in mapping.iterrows():
    base = load_dat(f"instances/{row['instance']}")
    inst = adapt_instance_from_row(base, row)
    config = config_from_row(row)
    m, info = build_full_model(inst)
    res = solve_fast(m)
    rows.append(build_full_report(inst, res, config, info))
```
