# xlsx_loader

Loader for `results_MILP.xlsx`.

## Workbook sheets
Observed sheets:
- `LoRP-FSD`
- `LoRP+FixedCost`
- `LRP_ITOR`

Current pipeline uses only `LoRP-FSD`.

## Main columns used for `LoRP-FSD`
- `name`
- `F_R`
- `F_A`
- `R`
- `Length`
- `UB`
- `Status name`
- `gap`
- `Cost (Depots)`
- `Cost (Vehicles)`
- `Cost Routing`
- `Cost Direct All`
- `Depot1..Depot4`
- `CapD1..CapD4`
- `DemandD1..DemandD4`
- `%UsageD1..%UsageD4`
- `VehiclesD1..VehiclesD4`

## API

### `workbook_sheets(path)`
Return sheet names.

### `load_lorp_fsd_mapping(excel_path, instance_folder=None)`
Load only `LoRP-FSD` and return normalized mapping DataFrame.

Output cols:
- `row_id`
- `instance`
- `F_R`, `F_A`, `R`, `Length`
- `UB`, `status`, `gap`
- `cost_depots`
- `vehicle_cost_milp`
- `routing_cost_milp`
- `da_cost_milp`
- `depots`
- `depots_milp`

`depots` / `depots_milp` are dicts keyed by depot id.

### `load_workbook(path, sheet_name=None, normalize=True)`
Generic workbook loader.

### `normalize_sheet(df, sheet_name)`
Trim names, attach attrs, parse depot slots.

### `infer_sheet_spec(sheet_name)`
Return light metadata for each known sheet.

### `sheet_to_records(sheet_result)`
Convert normalized sheet to record list.

## Example
```python
from xlsx_loader import load_lorp_fsd_mapping

df = load_lorp_fsd_mapping("results_MILP.xlsx", instance_folder="instances")
row = df.iloc[0]
print(row["instance"])
print(row["depots"])
```
