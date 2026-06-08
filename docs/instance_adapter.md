# instance_adapter

Excel-driven instance tailoring.

## Goal
Merge:
- base `.dat` instance
- 1 Excel row from `LoRP-FSD`

Result:
- instance with only active depots from Excel
- depot capacities overwritten from Excel when present
- global params injected from Excel

## API

### `ExcelSpec`
Dataclass with fields:
- `row_id`
- `instance`
- `R`, `F_R`, `F_A`, `Length`
- `UB`, `status`, `gap`
- `cost_depots`
- `vehicle_cost_milp`
- `routing_cost_milp`
- `da_cost_milp`
- `depots`
- `depots_milp`

### `spec_from_row(row)`
Convert mapping row to `ExcelSpec`.

### `adapt_instance(base_inst, spec)`
Return tailored instance.

Rules:
- keep only depots listed in Excel row
- if Excel depot capacity exists, use it
- `fixed_cost` set to `0.0`
- inject `R`, `F_R`, `F_A`, `Length`
- set `n_depots = max_depots_open = active depots count`

### `adapt_instance_from_row(base_inst, row)`
Shortcut: row -> spec -> adapt.

### `load_and_adapt_instance(dat_path, row)`
Load `.dat` then adapt.

### `build_adapted_instances(excel_path, instance_folder)`
Batch build adapted instances for all mapped rows.

## Example
```python
from dat_loader import load_dat
from xlsx_loader import load_lorp_fsd_mapping
from instance_adapter import adapt_instance_from_row

mapping = load_lorp_fsd_mapping("results_MILP.xlsx", instance_folder="instances")
row = mapping.iloc[0]
base = load_dat(f"instances/{row['instance']}")
mod = adapt_instance_from_row(base, row)
```
