from __future__ import annotations

"""Excel-driven instance tailoring.

Use case:
- load base .dat instance
- load first-sheet row from results_MILP.xlsx
- match row['instance'] to .dat filename
- keep active depots + Excel capacities + global params
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Protocol, Union

from dat_loader import Instance as DatInstance, load_dat
from xlsx_loader import load_lorp_fsd_mapping

PathLike = Union[str, Path]


class _InstanceLike(Protocol):
    depots: Dict[int, Dict[str, Any]]
    clients: Dict[int, Dict[str, Any]]
    data: Dict[str, Any]


@dataclass
class ExcelSpec:
    row_id: int
    instance: str
    R: float
    F_R: float
    F_A: float
    Length: float
    UB: float
    status: str
    gap: float
    cost_depots: float
    vehicle_cost_milp: float
    routing_cost_milp: float
    da_cost_milp: float
    depots: Dict[int, Dict[str, Any]]
    depots_milp: Dict[int, Dict[str, Any]]


def spec_from_row(row) -> ExcelSpec:
    return ExcelSpec(
        row_id=int(row["row_id"]),
        instance=str(row["instance"]),
        R=float(row["R"]),
        F_R=float(row["F_R"]),
        F_A=float(row["F_A"]),
        Length=float(row["Length"]),
        UB=float(row["UB"]),
        status=str(row["status"]),
        gap=float(row["gap"]),
        cost_depots=float(row["cost_depots"]),
        vehicle_cost_milp=float(row.get("vehicle_cost_milp", 0.0)),
        routing_cost_milp=float(row.get("routing_cost_milp", 0.0)),
        da_cost_milp=float(row.get("da_cost_milp", 0.0)),
        depots=dict(row["depots"]),
        depots_milp=dict(row["depots_milp"]),
    )


def adapt_instance(base_inst: _InstanceLike, spec: ExcelSpec) -> _InstanceLike:
    """Tailor base .dat instance with Excel specs.

    - keep only depots listed in Excel row
    - overwrite depot capacity with Excel capacity when present
    - inject global params R/F_R/F_A/Length
    - set open depots count = active depots count
    - zero fixed cost in adapted base; cost handled from Excel report
    """
    active_depots: Dict[int, Dict[str, Any]] = {}
    for depot_id, depot_info in spec.depots.items():
        if depot_id not in base_inst.depots:
            continue
        base = base_inst.depots[depot_id]
        active_depots[depot_id] = {
            "x": base["x"],
            "y": base["y"],
            "cap": depot_info["capacity"] if depot_info.get("capacity") is not None else base["cap"],
            "fixed_cost": 0.0,
        }

    new_data = dict(base_inst.data)
    new_data.update({
        "n_depots": len(active_depots),
        "max_depots_open": len(active_depots),
        "R": spec.R,
        "F_R": spec.F_R,
        "F_A": spec.F_A,
        "Length": spec.Length,
    })

    return type(base_inst)(depots=active_depots, clients=base_inst.clients, data=new_data)


def adapt_instance_from_row(base_inst: _InstanceLike, row) -> _InstanceLike:
    return adapt_instance(base_inst, spec_from_row(row))


def load_and_adapt_instance(dat_path: PathLike, row) -> _InstanceLike:
    base = load_dat(dat_path)
    if isinstance(row, ExcelSpec):
        return adapt_instance(base, row)
    return adapt_instance_from_row(base, row)


def build_adapted_instances(excel_path: PathLike, instance_folder: PathLike) -> List[_InstanceLike]:
    """Batch: first sheet only; match row['instance'] against .dat filename."""
    mapping_df = load_lorp_fsd_mapping(excel_path, instance_folder=instance_folder)
    instances: List[_InstanceLike] = []
    folder = Path(instance_folder)
    for _, row in mapping_df.iterrows():
        dat_path = folder / str(row["instance"])
        base = load_dat(dat_path)
        instances.append(adapt_instance_from_row(base, row))
    return instances


__all__ = [
    "ExcelSpec",
    "adapt_instance",
    "adapt_instance_from_row",
    "build_adapted_instances",
    "load_and_adapt_instance",
    "spec_from_row",
]
