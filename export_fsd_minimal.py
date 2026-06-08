from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

from instance_adapter import spec_from_row
from xlsx_loader import load_lorp_fsd_mapping


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Create compact slot-based FSD comparison table from batch results.")
    p.add_argument("--results", default="pipeline_out/fsd_batch_results_with_stats.csv")
    p.add_argument("--excel", default="results_MILP.xlsx")
    p.add_argument("--out-csv", default="pipeline_out/fsd_minimal_results.csv")
    p.add_argument("--out-excel", default="pipeline_out/fsd_minimal_results.xlsx")
    p.add_argument("--out-euro-csv", default="pipeline_out/fsd_minimal_results_excel_locale.csv")
    return p.parse_args()


def _val(row: pd.Series, key: str, default: Any = None) -> Any:
    if key not in row or pd.isna(row[key]):
        return default
    return row[key]


def build_row(res_row: pd.Series, config) -> dict[str, Any]:
    out: dict[str, Any] = {
        # same spirit as source Excel, plus PyVRP comparison
        "row_id": _val(res_row, "row_id"),
        "name": config.instance,
        "problem": config.instance,
        "F_R": config.F_R,
        "F_A": config.F_A,
        "R": config.R,
        "Length": config.Length,
        "UB": config.UB,
        "Status name": config.status,
        "gap_milp_excel": config.gap,
        "Cost Routing MILP": config.routing_cost_milp,
        "Cost (Vehicles) MILP": config.vehicle_cost_milp,
        "Cost (Depots)": config.cost_depots,
        "Cost Direct All MILP": config.da_cost_milp,
        "Cost Routing PyVRP": _val(res_row, "pyvrp_routing_cost"),
        "Cost Direct All PyVRP": _val(res_row, "pyvrp_da_cost"),
        "Cost (Vehicles) PyVRP": _val(res_row, "pyvrp_vehicle_cost"),
        "Cost Total PyVRP": _val(res_row, "pyvrp_total_cost"),
        "raw_gap_pyvrp_minus_milp": _val(res_row, "raw_gap_pyvrp_minus_milp"),
        "abs_gap_pyvrp_vs_milp": _val(res_row, "abs_gap_pyvrp_vs_milp"),
        "gap_sign_flag": _val(res_row, "gap_sign_flag"),
        "gap_distance_flag": _val(res_row, "gap_distance_flag"),
        "run_status": _val(res_row, "run_status"),
        "error": _val(res_row, "error"),
        "pyvrp_feasible": _val(res_row, "pyvrp_feasible"),
        "capacity_violation": _val(res_row, "capacity_violation"),
        "service_level_pyvrp": _val(res_row, "pyvrp_service_level"),
        "n_clients": _val(res_row, "n_clients"),
        "total_demand": _val(res_row, "total_demand"),
        "veh_cap": _val(res_row, "veh_cap"),
        "max_distance_raw": _val(res_row, "max_distance_raw"),
        "arslan_scale": _val(res_row, "arslan_scale"),
        "resolution_status": _val(res_row, "resolution_status"),
        "resolved_dat_path": _val(res_row, "resolved_dat_path"),
        "clients_DA_pyvrp": _val(res_row, "pyvrp_da_clients"),
        "clients_Routing_pyvrp": _val(res_row, "pyvrp_routing_clients"),
        "vehicles_DA_pyvrp": _val(res_row, "pyvrp_da_vehicles"),
        "vehicles_Routing_pyvrp": _val(res_row, "pyvrp_routing_vehicles"),
    }

    total_usage_vals = []
    total_veh = 0.0

    # Slot-based output: Depot1..Depot4 reflect Excel depot slots, not real sparse id columns.
    depot_items = list(config.depots.items())
    for slot in range(1, 5):
        if slot <= len(depot_items):
            depot_id, depot_info = depot_items[slot - 1]
            did = int(depot_id)
            prefix_src = f"d{did}_"
            prefix_py = f"d{did}_pyvrp_"
            cap = depot_info.get("capacity")
            milp = config.depots_milp.get(did, {})

            demand_total = _val(res_row, prefix_py + "demand_total")
            usage_total = _val(res_row, prefix_py + "usage_total")
            da_demand = _val(res_row, prefix_py + "da_demand")
            rt_demand = _val(res_row, prefix_py + "routing_demand")
            da_usage = _val(res_row, prefix_py + "da_usage")
            rt_usage = _val(res_row, prefix_py + "routing_usage")
            da_veh = _val(res_row, prefix_py + "da_vehicles", 0.0) or 0.0
            rt_veh = _val(res_row, prefix_py + "routing_vehicles", 0.0) or 0.0

            if usage_total is not None:
                total_usage_vals.append(usage_total)
            total_veh += float(da_veh or 0) + float(rt_veh or 0)

            out.update({
                f"Depot{slot}": f"d{did}",
                f"Depot{slot}_id": did,
                f"CapD{slot}": cap,
                f"DemandD{slot}_MILP": milp.get("demand"),
                f"%UsageD{slot}_MILP": milp.get("usage"),
                f"VehiclesD{slot}_MILP": milp.get("vehicles"),
                f"DemandD{slot}_PyVRP_Total": demand_total,
                f"DemandD{slot}_PyVRP_DA": da_demand,
                f"DemandD{slot}_PyVRP_Routing": rt_demand,
                f"%UsageD{slot}_PyVRP_Total": usage_total,
                f"%UsageD{slot}_PyVRP_DA": da_usage,
                f"%UsageD{slot}_PyVRP_Routing": rt_usage,
                f"VehiclesD{slot}_PyVRP_DA": da_veh,
                f"VehiclesD{slot}_PyVRP_Routing": rt_veh,
                f"CostD{slot}_PyVRP_DA": _val(res_row, prefix_py + "da_cost"),
                f"CostD{slot}_PyVRP_Routing": _val(res_row, prefix_py + "routing_cost"),
                f"FeasibleDAClientsD{slot}": _val(res_row, prefix_src + "feasible_da_clients"),
                f"AssignedDAClientsD{slot}": _val(res_row, prefix_src + "assigned_da_clients"),
                f"AssignedDAClientIDsD{slot}": _val(res_row, prefix_src + "assigned_da_client_ids"),
                f"RoutingCapAfterDAD{slot}": _val(res_row, prefix_src + "routing_cap_after_da"),
            })
        else:
            # keep stable headers, blank slot
            out.update({
                f"Depot{slot}": None,
                f"Depot{slot}_id": None,
                f"CapD{slot}": None,
                f"DemandD{slot}_MILP": None,
                f"%UsageD{slot}_MILP": None,
                f"VehiclesD{slot}_MILP": None,
                f"DemandD{slot}_PyVRP_Total": None,
                f"DemandD{slot}_PyVRP_DA": None,
                f"DemandD{slot}_PyVRP_Routing": None,
                f"%UsageD{slot}_PyVRP_Total": None,
                f"%UsageD{slot}_PyVRP_DA": None,
                f"%UsageD{slot}_PyVRP_Routing": None,
                f"VehiclesD{slot}_PyVRP_DA": None,
                f"VehiclesD{slot}_PyVRP_Routing": None,
                f"CostD{slot}_PyVRP_DA": None,
                f"CostD{slot}_PyVRP_Routing": None,
                f"FeasibleDAClientsD{slot}": None,
                f"AssignedDAClientsD{slot}": None,
                f"AssignedDAClientIDsD{slot}": None,
                f"RoutingCapAfterDAD{slot}": None,
            })

    out["TotalDepots"] = len(depot_items)
    out["TotalVehicles_PyVRP"] = total_veh
    out["Avg % Usage Deps PyVRP"] = sum(total_usage_vals) / len(total_usage_vals) if total_usage_vals else None
    return out


def main() -> None:
    args = parse_args()
    results = pd.read_csv(args.results)
    result_rows = results[results["record_type"] == "RESULT"].copy()

    mapping = load_lorp_fsd_mapping(args.excel, instance_folder=None)
    mapping_by_row = {int(row.row_id): spec_from_row(row) for _, row in mapping.iterrows()}

    rows = []
    for _, res_row in result_rows.iterrows():
        row_id = int(res_row["row_id"])
        config = mapping_by_row.get(row_id)
        if config is None:
            continue
        rows.append(build_row(res_row, config))

    out = pd.DataFrame(rows)
    Path(args.out_csv).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out_csv, index=False)
    out.to_csv(args.out_euro_csv, index=False, sep=";", decimal=",")
    out.to_excel(args.out_excel, index=False)

    print(f"rows written: {len(out)}")
    print(f"csv         : {args.out_csv}")
    print(f"excel csv   : {args.out_euro_csv}  (semicolon + decimal comma)")
    print(f"xlsx        : {args.out_excel}")


if __name__ == "__main__":
    main()
