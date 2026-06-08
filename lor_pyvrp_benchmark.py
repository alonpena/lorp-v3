"""Facade module — re-exports every public symbol for backward compatibility.

Business logic lives in:
  da_geometry    — distance primitives and direct-allocation math
  pyvrp_model    — PyVRP Model construction and solving
  reporting      — KPI extraction and benchmark report rows
  viz            — matplotlib plots
  dat_loader     — .dat file parsing
  instance_adapter — Excel-driven instance tailoring
  xlsx_loader    — results_MILP.xlsx loading
"""
from __future__ import annotations

from da_geometry import (  # noqa: F401
    assign_da_clients,
    build_direct_allocation_data,
    compute_max_distance,
    dist_euclid,
    dist_manhattan,
)
from dat_loader import (  # noqa: F401
    Instance,
    list_dat_files,
    load_dat,
    load_dat_folder,
    load_dat_path,
)
from instance_adapter import (  # noqa: F401
    ExcelSpec,
    adapt_instance,
    adapt_instance_from_row,
    build_adapted_instances,
    load_and_adapt_instance,
    spec_from_row,
)
from pyvrp_model import (  # noqa: F401
    MaxRuntime,
    Model,
    build_full_model,
    solve_fast,
)
from reporting import (  # noqa: F401
    build_full_report,
    compute_solution_costs,
    extract_kpis_level1,
    extract_kpis_level2,
    extract_solution_metrics,
)
from viz import plot_instance, plot_solution  # noqa: F401
from xlsx_loader import (  # noqa: F401
    DepotSlot,
    SheetResult,
    infer_sheet_spec,
    load_lorp_fsd_mapping,
    load_workbook,
    normalize_sheet,
    sheet_to_records,
    workbook_sheets,
)

from pathlib import Path
from typing import Union

PathLike = Union[str, Path]


# ── thin IO helpers that have no better home ──────────────────────────────────

def load_instances_from_zip(zip_path: PathLike, extract_to: PathLike = ".") -> Path:
    import zipfile

    extract_to = Path(extract_to)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_to)
    return extract_to


def build_experiments_df(excel_path: PathLike, instance_folder: PathLike):
    return load_lorp_fsd_mapping(excel_path, instance_folder=instance_folder)


def config_from_row(row) -> ExcelSpec:
    return spec_from_row(row)


__all__ = [
    "DepotSlot",
    "ExcelSpec",
    "Instance",
    "MaxRuntime",
    "Model",
    "SheetResult",
    "adapt_instance",
    "adapt_instance_from_row",
    "assign_da_clients",
    "build_adapted_instances",
    "build_direct_allocation_data",
    "build_experiments_df",
    "build_full_model",
    "build_full_report",
    "build_instances_from_zip",
    "compute_max_distance",
    "compute_solution_costs",
    "config_from_row",
    "dist_euclid",
    "dist_manhattan",
    "extract_kpis_level1",
    "extract_kpis_level2",
    "extract_solution_metrics",
    "infer_sheet_spec",
    "list_dat_files",
    "load_and_adapt_instance",
    "load_dat",
    "load_dat_folder",
    "load_dat_path",
    "load_instances_from_zip",
    "load_lorp_fsd_mapping",
    "load_workbook",
    "normalize_sheet",
    "plot_instance",
    "plot_solution",
    "sheet_to_records",
    "solve_fast",
    "spec_from_row",
    "workbook_sheets",
]
