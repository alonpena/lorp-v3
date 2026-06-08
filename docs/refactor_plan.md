# Refactor & Test Plan

## Status
- **Tests**: zero project tests (only venv third-party tests exist)
- **Coverage**: 0%
- **Modularization**: `lor_pyvrp_benchmark.py` conflates 5 concerns in ~400 lines

---

## 1. Modularization

### Target layout

```
lor_pyvrp_benchmark.py   ← facade only (re-exports __all__, no logic)
da_geometry.py           ← NEW: pure distance/DA math
pyvrp_model.py           ← NEW: Model build + solve (pyvrp-only)
reporting.py             ← NEW: KPI extraction + report rows
viz.py                   ← NEW: plot_instance, plot_solution
dat_loader.py            ← unchanged
instance_adapter.py      ← unchanged
xlsx_loader.py           ← unchanged
```

### Modules to extract

#### `da_geometry.py`  ← Priority 1 (highest ROI)
Pull from `lor_pyvrp_benchmark.py`:
- `_dist_euclid`
- `_dist_manhattan` (currently unused — delete or keep with note)
- `compute_max_distance`
- `build_direct_allocation_data`
- `assign_da_clients`

**Zero pyvrp / matplotlib deps. Testable today without any optional deps.**

#### `pyvrp_model.py`  ← Priority 2
Pull from `lor_pyvrp_benchmark.py`:
- `_require_pyvrp`
- `build_full_model`
- `solve_fast`

Owns the `try/except pyvrp` guard. Import from here, not facade.

#### `reporting.py`  ← Priority 3
Pull from `lor_pyvrp_benchmark.py`:
- `extract_kpis_level1`
- `extract_kpis_level2`
- `extract_solution_metrics`
- `compute_solution_costs`
- `build_full_report`

`build_full_report` is 80+ lines — biggest single unit, frequently iterated.

#### `viz.py`  ← Priority 4
Pull from `lor_pyvrp_benchmark.py`:
- `plot_instance`
- `plot_solution`

Matplotlib already lazy-imported inside functions. Just finish the isolation.

### Facade after refactor

`lor_pyvrp_benchmark.py` becomes:
```python
from da_geometry import *        # noqa: F401,F403
from pyvrp_model import *        # noqa: F401,F403
from reporting import *          # noqa: F401,F403
from viz import *                # noqa: F401,F403
from dat_loader import *         # noqa: F401,F403
from instance_adapter import *   # noqa: F401,F403
from xlsx_loader import *        # noqa: F401,F403

# keep __all__ as-is for backward compat
```

---

## 2. Test Plan

### Setup (do first)
```toml
# pyproject.toml additions
[project.optional-dependencies]
dev = ["pytest>=8", "pytest-cov"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

```
tests/
  __init__.py
  conftest.py            ← shared Instance/ExcelSpec fixtures
  test_dat_loader.py
  test_instance_adapter.py
  test_xlsx_loader.py
  test_da_geometry.py    ← after da_geometry.py extracted
  test_reporting.py      ← after reporting.py extracted
```

---

### `tests/conftest.py`
Shared fixtures, no file I/O:

```python
import pytest
from dat_loader import Instance

MINIMAL_DAT = """\
3
2
2
4
0.0 0.0
10.0 0.0
0.0 5.0
10.0 5.0
5.0 5.0
10
200
150
6
5
4
100.0
50.0
20.0
"""

@pytest.fixture
def minimal_instance():
    return Instance.from_dat(MINIMAL_DAT.splitlines())

@pytest.fixture
def minimal_spec():
    from instance_adapter import ExcelSpec
    return ExcelSpec(
        row_id=0, instance="test.dat",
        R=8.0, F_R=1.0, F_A=0.5, Length=100.0,
        UB=500.0, status="Optimal", gap=0.0,
        cost_depots=100.0, vehicle_cost_milp=50.0,
        routing_cost_milp=200.0, da_cost_milp=80.0,
        depots={1: {"label": "d1", "capacity": 200.0},
                2: {"label": "d2", "capacity": 150.0}},
        depots_milp={1: {"demand": 80.0, "usage": 0.4, "vehicles": 2.0},
                     2: {"demand": 60.0, "usage": 0.4, "vehicles": 1.0}},
    )
```

---

### `tests/test_dat_loader.py`

| Test | What | Why |
|---|---|---|
| `test_parse_valid` | `Instance.from_dat(MINIMAL_DAT)` → correct depot/client counts | core parse |
| `test_depot_coords` | depot 1 x=0,y=0; depot 2 x=10,y=0 | coord mapping |
| `test_client_demands` | client demands match input | demand parse |
| `test_vehicle_cap` | `data["veh_cap"] == 10` | scalar fields |
| `test_veh_fixed_cost` | `data["veh_fixed_cost"] == 20.0` | scalar fields |
| `test_max_depots_open` | `data["max_depots_open"] == 2` | constraint |
| `test_invalid_veh_cap_zero` | cap=0 → `ValueError` | guard |
| `test_invalid_max_depots_open` | max_open > n_depots → `ValueError` | guard |
| `test_eof_coords` | truncated coords block → `ValueError` | guard |
| `test_bad_coord_format` | single number on coord line → `ValueError` | guard |
| `test_from_path` | `load_dat("instances/Exp5x3-a.dat")` round-trip | file I/O |
| `test_load_dat_folder` | `load_dat_folder("instances/")` → dict of Instance | folder loader |
| `test_list_dat_files` | returns sorted Path list | listing |
| `test_cola_optional` | parse without cola line → `data["cola"] is None` | optional field |
| `test_cola_present` | parse with cola line → `data["cola"] == value` | optional field |

---

### `tests/test_instance_adapter.py`

| Test | What | Why |
|---|---|---|
| `test_spec_from_row_fields` | all ExcelSpec fields populated from dict-like row | mapping |
| `test_spec_from_row_defaults` | missing vehicle_cost_milp/routing_cost_milp/da_cost_milp → 0.0 | optional fields |
| `test_adapt_keeps_active_depots` | only depots in spec survive | filter logic |
| `test_adapt_overwrites_capacity` | spec capacity replaces base capacity | cap override |
| `test_adapt_fallback_capacity` | spec capacity=None → base capacity kept | fallback |
| `test_adapt_injects_params` | R/F_R/F_A/Length in `data` after adapt | param injection |
| `test_adapt_depot_not_in_base` | spec depot absent from base → silently skipped | robustness |
| `test_adapt_zero_fixed_cost` | adapted depot fixed_cost == 0.0 | cost zeroing |
| `test_adapt_clients_unchanged` | clients dict identical after adapt | immutability |
| `test_load_and_adapt_instance` | round-trip from .dat file + row | integration |

---

### `tests/test_xlsx_loader.py`

| Test | What | Why |
|---|---|---|
| `test_infer_sheet_spec_lorp_fsd` | kind="lorp-fsd", depot_slots=4 | spec inference |
| `test_infer_sheet_spec_lorp_fc` | kind="lorp-fixedcost", depot_slots=5 | spec inference |
| `test_infer_sheet_spec_itor` | kind="itor", depot_slots=5 | spec inference |
| `test_infer_sheet_spec_unknown` | unrecognised name → kind="unknown" | fallback |
| `test_maybe_num_nan` | `pd.NA` → None | null handling |
| `test_maybe_num_valid` | `"3.14"` → 3.14 | parse |
| `test_maybe_str_nan` | `pd.NA` → None | null handling |
| `test_maybe_str_empty` | `"  "` → None | whitespace |
| `test_row_to_depots_two_depots` | Series with Depot1/Depot2 → two entries | depot parse |
| `test_row_to_depots_missing_cap` | CapD1 absent → capacity None | missing col |
| `test_normalize_sheet_strips_cols` | column names stripped | normalization |
| `test_load_lorp_fsd_mapping_integration`* | loads `results_MILP.xlsx`, checks row count > 0 | integration |
| `test_load_lorp_fsd_mapping_missing_col` | DataFrame missing required col → `KeyError` | guard |

\* mark with `@pytest.mark.integration` — skipped in CI without xlsx file.

---

### `tests/test_da_geometry.py`  *(after extraction)*

| Test | What | Why |
|---|---|---|
| `test_dist_euclid_zero` | same point → 0.0 | trivial |
| `test_dist_euclid_3_4_5` | (0,0)→(3,4) == 5.0 | known triangle |
| `test_dist_manhattan` | (0,0)→(3,4) == 7.0 | formula |
| `test_compute_max_distance_two_depots` | two depots, no clients | max across nodes |
| `test_compute_max_distance_includes_clients` | max is between client and depot | all nodes |
| `test_build_da_data_within_radius` | client inside radius → appears in da_data | radius filter |
| `test_build_da_data_outside_radius` | client outside radius → absent | radius filter |
| `test_build_da_data_cost_return_zero` | cost_ji always 0.0 | DA semantics |
| `test_build_da_data_empty_when_no_clients_nearby` | all clients far → empty da_data | edge case |
| `test_assign_da_clients_within_cap` | demand fits cap → assigned, not in routing_set | happy path |
| `test_assign_da_clients_over_cap` | demand exceeds cap → goes to routing_set | cap exceeded |
| `test_assign_da_clients_prefers_nearest` | two depots equidistant-ish → nearest chosen | sort logic |
| `test_assign_da_clients_no_feasible` | client outside all radii → routing_set | no coverage |
| `test_assign_da_clients_partial` | some assigned, some not | mixed |

---

### `tests/test_reporting.py`  *(after extraction, mocks pyvrp solution)*

| Test | What | Why |
|---|---|---|
| `test_compute_solution_costs_math` | known inputs → exact cost breakdown | arithmetic |
| `test_compute_solution_costs_gap` | gap = (ub - total)/ub | gap formula |
| `test_compute_solution_costs_zero_ub` | UB=0 → gap=None | divide-by-zero guard |
| `test_extract_solution_metrics_keys` | all expected keys present | contract |
| `test_build_full_report_no_capacity_violation` | demand ≤ cap → `violacion_capacidad=False` | constraint check |
| `test_build_full_report_capacity_violation` | demand > cap → `violacion_capacidad=True` | constraint check |
| `test_build_full_report_service_level` | served/total demand | KPI calc |
| `test_extract_kpis_level1_totals` | routing + DA distance summed | aggregation |
| `test_extract_kpis_level2_per_depot` | each depot keyed separately | grouping |

---

## 3. Execution order

```
1. Add pytest + pytest-cov to pyproject.toml dev deps
2. Create tests/ + conftest.py
3. Write test_dat_loader.py   → run → green (no new code needed)
4. Write test_instance_adapter.py → run → green
5. Write test_xlsx_loader.py (unit tests only) → run → green
6. Extract da_geometry.py from lor_pyvrp_benchmark.py
7. Write test_da_geometry.py → run → green
8. Extract reporting.py
9. Write test_reporting.py with mocked solution objects
10. Extract pyvrp_model.py
11. Extract viz.py
12. Reduce lor_pyvrp_benchmark.py to facade
13. Smoke-test: `python -c "import lor_pyvrp_benchmark"` still works
```

---

## 4. Notes / debt

- `_dist_manhattan` defined in `lor_pyvrp_benchmark.py` but never called → delete or add a test and use it
- `benchmarking_instancias_lor_pyvrp.py` not reviewed — may duplicate pipeline logic worth testing
- `extract_solution_metrics` and `compute_solution_costs` overlap in purpose — consider merging after tests exist
- `build_full_report` rebuilds per-depot loop already done in `extract_kpis_level2` — potential DRY pass after tests pass
