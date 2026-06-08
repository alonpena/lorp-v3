# LoR PyVRP docs

Docs for benchmark pipeline.

## Modules
- `dat_loader.md` — `.dat` parser
- `xlsx_loader.md` — `results_MILP.xlsx` loader
- `instance_adapter.md` — Excel row + `.dat` merge
- `lor_pyvrp_benchmark.md` — solver, KPIs, report, plots
- `pyvrp_integration.md` — DA preprocessing + residual PyVRP routing plan

## Pipeline
1. Load Excel first sheet (`LoRP-FSD`)
2. Match row `instance` with `.dat` file
3. Load base `.dat`
4. Adapt instance with Excel specs
5. Build PyVRP model
6. Solve, extract KPIs, write report
