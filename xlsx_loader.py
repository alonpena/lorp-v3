from __future__ import annotations

"""Loader for results_MILP.xlsx.

Workbook spec (pandas-explored):

Sheets:
- LoRP-FSD: 1185 rows, 47 cols
- LoRP+FixedCost: 1184 rows, 50 cols
- LRP_ITOR: 70 rows, 37 cols

Common core fields by sheet family:
- name / problem / F_R / F_A / R / Length / UB / LB / status / gap
- cost cols: Cost Routing, Cost (Vehicles), Cost (Depots), Cost Direct All
- depot slots: Depot1..DepotN, CapD1.., DemandD1.., %UsageD1.., VehiclesD1..

This module keeps raw DataFrame + a normalized view with depot slots parsed.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Union
import os

import pandas as pd

PathLike = Union[str, Path]
LORP_FSD_SHEET = "LoRP-FSD"
LORP_FSD_REQUIRED_COLUMNS = {
    "name", "F_R", "F_A", "R", "Length", "UB", "Status name", "gap",
    "Cost (Depots)", "Cost (Vehicles)", "Cost Routing", "Cost Direct All",
}


@dataclass
class DepotSlot:
    index: int
    label: Optional[str] = None
    size: Optional[float] = None
    capacity: Optional[float] = None
    demand: Optional[float] = None
    usage: Optional[float] = None
    vehicles: Optional[float] = None


@dataclass
class SheetResult:
    sheet_name: str
    raw: pd.DataFrame
    data: pd.DataFrame


def workbook_sheets(path: PathLike) -> List[str]:
    return pd.ExcelFile(path).sheet_names


def load_lorp_fsd_mapping(excel_path: PathLike, instance_folder: Optional[PathLike] = None) -> pd.DataFrame:
    """Load only LoRP-FSD sheet and keep only fields used by pipeline."""
    df = pd.read_excel(excel_path, sheet_name=LORP_FSD_SHEET)
    df = df.reset_index(drop=True)
    df["row_id"] = df.index
    if "name" in df.columns:
        df["name"] = df["name"].astype(str).str.strip()

    missing = [c for c in LORP_FSD_REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise KeyError(f"Missing required columns in {LORP_FSD_SHEET}: {missing}")

    if instance_folder is not None:
        inst_dir = Path(instance_folder)
    else:
        inst_dir = None

    results: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        instance_name = str(row["name"]).strip()
        if inst_dir is not None and not (inst_dir / instance_name).exists():
            continue

        depots, depots_milp = _row_to_depots(row, df.columns)
        results.append({
            "row_id": int(row["row_id"]),
            "instance": instance_name,
            "F_R": float(row["F_R"]),
            "F_A": float(row["F_A"]),
            "R": float(row["R"]),
            "Length": float(row["Length"]),
            "UB": float(row["UB"]),
            "status": str(row["Status name"]),
            "gap": float(row["gap"]),
            "cost_depots": float(row["Cost (Depots)"]),
            "vehicle_cost_milp": float(row["Cost (Vehicles)"]) if pd.notna(row.get("Cost (Vehicles)")) else 0.0,
            "routing_cost_milp": float(row["Cost Routing"]) if pd.notna(row.get("Cost Routing")) else 0.0,
            "da_cost_milp": float(row["Cost Direct All"]) if pd.notna(row.get("Cost Direct All")) else 0.0,
            "depots": depots,
            "depots_milp": depots_milp,
        })

    out = pd.DataFrame(results)
    out.attrs["sheet_name"] = LORP_FSD_SHEET
    out.attrs["spec"] = infer_sheet_spec(LORP_FSD_SHEET)
    return out


def load_workbook(path: PathLike, sheet_name: Optional[str] = None, normalize: bool = True):
    """Load workbook.

    - sheet_name=None -> dict of SheetResult or raw DataFrames if normalize=False
    - sheet_name='LoRP-FSD' -> single SheetResult or DataFrame if normalize=False
    """
    xls = pd.ExcelFile(path)
    sheets = xls.sheet_names if sheet_name is None else [sheet_name]

    out: Dict[str, Any] = {}
    for s in sheets:
        raw = pd.read_excel(path, sheet_name=s)
        if normalize:
            out[s] = SheetResult(sheet_name=s, raw=raw, data=normalize_sheet(raw, s))
        else:
            out[s] = raw

    if sheet_name is not None:
        return out[sheet_name]
    return out


def normalize_sheet(df: pd.DataFrame, sheet_name: str) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip() for c in out.columns]
    out.attrs["sheet_name"] = sheet_name

    # trim string cells in common name columns
    for col in ["name", "problem", "Status name", "Status", "depots"]:
        if col in out.columns:
            out[col] = out[col].astype("string").str.strip()

    # parse depot slots if present
    depot_slots = _extract_depot_slots(out, sheet_name)
    out.attrs["depot_slots"] = depot_slots
    out.attrs["spec"] = infer_sheet_spec(sheet_name)
    return out


def infer_sheet_spec(sheet_name: str) -> Dict[str, Any]:
    if sheet_name == "LoRP-FSD":
        return {
            "kind": "lorp-fsd",
            "depot_slots": 4,
            "has_size": True,
            "has_total_depots": True,
            "has_total_vehicles": True,
            "status_col": "Status name",
        }
    if sheet_name == "LoRP+FixedCost":
        return {
            "kind": "lorp-fixedcost",
            "depot_slots": 5,
            "has_size": False,
            "has_total_depots": True,
            "has_total_vehicles": True,
            "status_col": "Status name",
        }
    if sheet_name == "LRP_ITOR":
        return {
            "kind": "itor",
            "depot_slots": 5,
            "has_size": True,
            "has_total_depots": False,
            "has_total_vehicles": False,
            "status_col": "Status",
        }
    return {"kind": "unknown", "depot_slots": 0}


def _row_to_depots(row: pd.Series, columns) -> tuple[Dict[int, Dict[str, Any]], Dict[int, Dict[str, Any]]]:
    depots: Dict[int, Dict[str, Any]] = {}
    depots_milp: Dict[int, Dict[str, Any]] = {}
    for i in range(1, 5):
        depot_col = f"Depot{i}"
        cap_col = f"CapD{i}"
        if depot_col not in columns or pd.isna(row.get(depot_col)):
            continue
        label = str(row[depot_col]).strip()
        if not label:
            continue
        depot_id = int(label.replace("d", ""))
        depots[depot_id] = {
            "label": label,
            "capacity": float(row[cap_col]) if cap_col in columns and pd.notna(row.get(cap_col)) else None,
        }
        demand_col = f"DemandD{i}"
        usage_col = f"%UsageD{i}"
        veh_col = f"VehiclesD{i}"
        depots_milp[depot_id] = {
            "demand": float(row[demand_col]) if demand_col in columns and pd.notna(row.get(demand_col)) else 0.0,
            "usage": float(row[usage_col]) if usage_col in columns and pd.notna(row.get(usage_col)) else 0.0,
            "vehicles": float(row[veh_col]) if veh_col in columns and pd.notna(row.get(veh_col)) else 0.0,
        }
    return depots, depots_milp


def _extract_depot_slots(df: pd.DataFrame, sheet_name: str) -> List[List[DepotSlot]]:
    spec = infer_sheet_spec(sheet_name)
    max_slots = int(spec.get("depot_slots", 0))
    rows: List[List[DepotSlot]] = []

    for _, row in df.iterrows():
        slots: List[DepotSlot] = []
        for i in range(1, max_slots + 1):
            if spec["kind"] == "itor":
                label_col = f"D{i}"
                size_col = f"Size_D{i}"
                cap_col = None
                demand_col = None
                usage_col = None
                veh_col = f"Vehicles_D{i}"
            else:
                label_col = f"Depot{i}"
                size_col = f"sizeD{i}" if f"sizeD{i}" in df.columns else None
                cap_col = f"CapD{i}"
                demand_col = f"DemandD{i}" if f"DemandD{i}" in df.columns else None
                usage_col = f"%UsageD{i}" if f"%UsageD{i}" in df.columns else None
                veh_col = f"VehiclesD{i}" if f"VehiclesD{i}" in df.columns else None

            has_any = any(c in df.columns for c in [label_col, size_col, cap_col, demand_col, usage_col, veh_col] if c)
            if not has_any:
                continue

            slot = DepotSlot(
                index=i,
                label=_maybe_str(row.get(label_col)) if label_col and label_col in df.columns else None,
                size=_maybe_num(row.get(size_col)) if size_col and size_col in df.columns else None,
                capacity=_maybe_num(row.get(cap_col)) if cap_col and cap_col in df.columns else None,
                demand=_maybe_num(row.get(demand_col)) if demand_col and demand_col in df.columns else None,
                usage=_maybe_num(row.get(usage_col)) if usage_col and usage_col in df.columns else None,
                vehicles=_maybe_num(row.get(veh_col)) if veh_col and veh_col in df.columns else None,
            )
            slots.append(slot)
        rows.append(slots)

    return rows


def _maybe_num(value: Any) -> Optional[float]:
    if pd.isna(value):
        return None
    try:
        return float(value)
    except Exception:
        return None


def _maybe_str(value: Any) -> Optional[str]:
    if pd.isna(value):
        return None
    text = str(value).strip()
    return text if text else None


def sheet_to_records(sheet: SheetResult) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    slots_by_row = sheet.data.attrs.get("depot_slots", [])
    for idx, row in sheet.data.iterrows():
        rec = row.to_dict()
        rec["_row_index"] = int(idx)
        rec["_depot_slots"] = slots_by_row[idx] if idx < len(slots_by_row) else []
        records.append(rec)
    return records


__all__ = [
    "DepotSlot",
    "SheetResult",
    "infer_sheet_spec",
    "load_lorp_fsd_mapping",
    "load_workbook",
    "normalize_sheet",
    "sheet_to_records",
    "workbook_sheets",
]
