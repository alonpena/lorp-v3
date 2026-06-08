from __future__ import annotations

import argparse
import math
import time
from pathlib import Path
from typing import Any

import pandas as pd
from tqdm.auto import tqdm

from da_geometry import assign_da_clients, build_direct_allocation_data, compute_max_distance
from dat_loader import load_dat
from instance_adapter import adapt_instance, spec_from_row
from instance_resolver import resolve_instance_path
from pyvrp_model import build_full_model, solve_fast
from reporting import build_full_report, extract_kpis_level1, extract_kpis_level2
from xlsx_loader import load_lorp_fsd_mapping


def _safe_div(num: float, den: float) -> float | None:
    return num / den if den and den > 0 else None


def _norm_usage(value: Any) -> float | None:
    """Excel usage sometimes appears as 58.97 for 58.97%.

    Keep raw separately. This returns fraction [0,1] when possible.
    """
    if value is None:
        return None
    try:
        v = float(value)
    except Exception:
        return None
    return v / 100.0 if v > 1.0 else v


def _base_record(config, inst, base_inst, max_dist: float, scale: float) -> dict[str, Any]:
    total_demand = sum(c["demand"] for c in inst.clients.values())
    return {
        "record_type": "RESULT",
        "row_id": config.row_id,
        "instance": config.instance,
        "status_milp": config.status,
        "gap_milp_excel": config.gap,
        "R": config.R,
        "F_R": config.F_R,
        "F_A": config.F_A,
        "Length": config.Length,
        "n_clients": len(inst.clients),
        "n_depots_base": len(base_inst.depots),
        "n_depots_active": len(inst.depots),
        "total_demand": total_demand,
        "veh_cap": inst.data["veh_cap"],
        "veh_fixed_cost": inst.data["veh_fixed_cost"],
        "max_distance_raw": max_dist,
        "arslan_scale": scale,
        "milp_ub": config.UB,
        "milp_cost_routing": config.routing_cost_milp,
        "milp_cost_da": config.da_cost_milp,
        "milp_cost_vehicles": config.vehicle_cost_milp,
        "milp_cost_depots": config.cost_depots,
    }


def _add_assignment_fields(rec: dict[str, Any], inst, config, da_data, da_assigned, routing_set) -> None:
    n_da = sum(len(v) for v in da_assigned.values())
    rec["assign_n_clients_da"] = n_da
    rec["assign_n_clients_routing"] = len(routing_set)
    rec["assign_da_share_clients"] = _safe_div(n_da, len(inst.clients))
    rec["assign_routing_client_ids"] = " ".join(map(str, sorted(routing_set)))

    for did in sorted(inst.depots):
        cap = float(inst.depots[did]["cap"])
        da_clients = da_assigned.get(did, [])
        da_demand = sum(inst.clients[j]["demand"] for j in da_clients)
        feasible = da_data.get(did, {}).get("clients", [])
        routing_cap = cap - da_demand
        q = int(inst.data["veh_cap"])
        n_full = math.floor(routing_cap / q)
        residual = int(routing_cap) % q
        milp_dep = config.depots_milp.get(did, {})
        milp_usage_raw = milp_dep.get("usage")

        prefix = f"d{did}_"
        rec[prefix + "active"] = True
        rec[prefix + "cap"] = cap
        rec[prefix + "feasible_da_clients"] = len(feasible)
        rec[prefix + "assigned_da_clients"] = len(da_clients)
        rec[prefix + "assigned_da_client_ids"] = " ".join(map(str, sorted(da_clients)))
        rec[prefix + "assigned_da_demand"] = da_demand
        rec[prefix + "assigned_da_usage"] = _safe_div(da_demand, cap)
        rec[prefix + "routing_cap_after_da"] = routing_cap
        rec[prefix + "routing_full_vehicle_types_expected"] = n_full
        rec[prefix + "routing_residual_vehicle_cap_expected"] = residual
        rec[prefix + "milp_demand"] = milp_dep.get("demand")
        rec[prefix + "milp_usage_raw"] = milp_usage_raw
        rec[prefix + "milp_usage_norm"] = _norm_usage(milp_usage_raw)
        rec[prefix + "milp_vehicles"] = milp_dep.get("vehicles")


def _add_solution_fields(rec: dict[str, Any], inst, config, res, info) -> None:
    k1 = extract_kpis_level1(inst, res, info)
    k2 = extract_kpis_level2(inst, res, info)
    report = build_full_report(inst, res, config, info)

    rec["pyvrp_feasible"] = res.best.is_feasible()
    rec["pyvrp_objective_scaled"] = res.best.distance()
    rec["pyvrp_n_routes"] = len(res.best.routes())
    rec["pyvrp_total_demand"] = k1["total_demand"]
    rec["pyvrp_served_demand"] = k1["served_demand"]
    rec["pyvrp_pending_demand"] = k1["pending_demand"]
    rec["pyvrp_service_level"] = _safe_div(k1["served_demand"], k1["total_demand"])

    rec["pyvrp_routing_vehicles"] = k1["routing"]["n_vehicles"]
    rec["pyvrp_routing_clients"] = k1["routing"]["n_clients"]
    rec["pyvrp_routing_demand"] = k1["routing"]["demand"]
    rec["pyvrp_routing_distance_scaled"] = k1["routing"]["distance"]
    rec["pyvrp_routing_cost"] = report["costo_routing_pyvrp"]

    rec["pyvrp_da_vehicles"] = k1["direct_allocation"]["n_vehicles"]
    rec["pyvrp_da_clients"] = k1["direct_allocation"]["n_clients"]
    rec["pyvrp_da_demand"] = k1["direct_allocation"]["demand"]
    rec["pyvrp_da_distance_scaled"] = k1["direct_allocation"]["distance"]
    rec["pyvrp_da_cost"] = report["costo_da_pyvrp"]

    rec["pyvrp_vehicle_cost"] = report["costo_vehiculos_pyvrp"]
    rec["pyvrp_depot_cost_from_excel"] = report["costo_depositos"]
    rec["pyvrp_total_cost"] = report["costo_total_pyvrp"]
    rec["raw_gap_pyvrp_minus_milp"] = report["raw_gap_pyvrp_minus_milp"]
    rec["abs_gap_pyvrp_vs_milp"] = report["gap_final"]
    rec["gap_sign_flag"] = "PYVRP_BELOW_MILP_CHECK_MODEL" if report["raw_gap_pyvrp_minus_milp"] < 0 else "PYVRP_GE_MILP_OK"
    rec["gap_distance_flag"] = "TOO_FAR" if report["gap_final"] > 0.20 else "OK_RANGE"
    rec["capacity_violation"] = report["violacion_capacidad"]

    for did in sorted(inst.depots):
        cap = float(inst.depots[did]["cap"])
        rt = k2.get(did, {}).get("routing", {"n_vehicles": 0, "distance": 0.0, "n_clients": 0, "demand": 0.0})
        da = k2.get(did, {}).get("direct_allocation", {"n_vehicles": 0, "distance": 0.0, "n_clients": 0, "demand": 0.0})
        total = rt["demand"] + da["demand"]
        prefix = f"d{did}_pyvrp_"
        rec[prefix + "demand_total"] = total
        rec[prefix + "usage_total"] = _safe_div(total, cap)
        rec[prefix + "routing_demand"] = rt["demand"]
        rec[prefix + "routing_usage"] = _safe_div(rt["demand"], cap)
        rec[prefix + "routing_vehicles"] = rt["n_vehicles"]
        rec[prefix + "routing_clients"] = rt["n_clients"]
        rec[prefix + "routing_distance_scaled"] = rt["distance"]
        rec[prefix + "routing_cost"] = rt["distance"] * config.F_R
        rec[prefix + "da_demand"] = da["demand"]
        rec[prefix + "da_usage"] = _safe_div(da["demand"], cap)
        rec[prefix + "da_vehicles"] = da["n_vehicles"]
        rec[prefix + "da_clients"] = da["n_clients"]
        rec[prefix + "da_distance_scaled"] = da["distance"]
        rec[prefix + "da_cost"] = da["distance"] * config.F_A


def run_row(row, instance_folder: Path, runtime: int, n_runs: int, verbose: bool = False) -> dict[str, Any]:
    t0 = time.perf_counter()
    config = spec_from_row(row)
    resolution = resolve_instance_path(config.instance, instance_folder)
    if not resolution.ok:
        return {
            "record_type": "RESULT",
            "row_id": config.row_id,
            "instance": config.instance,
            "resolution_status": resolution.status,
            "resolution_candidates": " | ".join(str(p) for p in resolution.candidates),
            "run_status": "MISSING_DAT" if resolution.status == "MISSING" else "AMBIGUOUS_DAT",
            "error": f"Could not resolve {config.instance}: {resolution.status}",
            "runtime_seconds": time.perf_counter() - t0,
        }

    base = load_dat(resolution.path)
    inst = adapt_instance(base, config)
    max_dist = compute_max_distance(inst)
    scale = 100.0 / max_dist if max_dist > 0 else 1.0
    rec = _base_record(config, inst, base, max_dist, scale)
    rec["resolution_status"] = resolution.status
    rec["resolved_dat_path"] = str(resolution.path)

    da_data, _ = build_direct_allocation_data(inst, inst.data["R"])
    da_assigned, routing_set = assign_da_clients(inst, da_data, int(inst.data["veh_cap"]))
    _add_assignment_fields(rec, inst, config, da_data, da_assigned, routing_set)

    if verbose:
        print(f"row={config.row_id} inst={config.instance} R={config.R} F_A={config.F_A} DA={rec['assign_n_clients_da']} RT={rec['assign_n_clients_routing']}")

    try:
        model, info = build_full_model(inst)
        res = solve_fast(model, runtime=runtime, n_runs=n_runs)
        _add_solution_fields(rec, inst, config, res, info)
        rec["run_status"] = "OK"
        rec["error"] = None
    except Exception as exc:  # keep batch alive
        rec["run_status"] = "ERROR"
        rec["error"] = repr(exc)

    rec["runtime_seconds"] = time.perf_counter() - t0
    return rec


def make_stats_rows(df: pd.DataFrame) -> list[dict[str, Any]]:
    ok = df[(df["record_type"] == "RESULT") & (df["run_status"] == "OK")].copy()
    stats_cols = [
        "pyvrp_total_cost",
        "milp_ub",
        "abs_gap_pyvrp_vs_milp",
        "raw_gap_pyvrp_minus_milp",
        "pyvrp_service_level",
        "pyvrp_routing_cost",
        "pyvrp_da_cost",
        "pyvrp_vehicle_cost",
        "pyvrp_depot_cost_from_excel",
        "pyvrp_routing_vehicles",
        "pyvrp_da_vehicles",
        "assign_n_clients_da",
        "assign_n_clients_routing",
        "runtime_seconds",
    ]
    stats = []
    base = {
        "record_type": "STAT",
        "row_id": None,
        "instance": "__ALL__",
        "run_status": "OK",
        "n_result_rows": len(df[df["record_type"] == "RESULT"]),
        "n_ok_rows": len(ok),
        "n_error_rows": int((df["run_status"] == "ERROR").sum()),
        "n_missing_dat_rows": int((df["run_status"] == "MISSING_DAT").sum()),
        "n_ambiguous_dat_rows": int((df["run_status"] == "AMBIGUOUS_DAT").sum()),
        "n_pyvrp_below_milp": int((ok["raw_gap_pyvrp_minus_milp"] < 0).sum()) if len(ok) else 0,
        "n_too_far_gap_gt_20pct": int((ok["abs_gap_pyvrp_vs_milp"] > 0.20).sum()) if len(ok) else 0,
        "n_capacity_violations": int(ok["capacity_violation"].sum()) if len(ok) else 0,
    }
    for col in stats_cols:
        if col not in ok.columns:
            continue
        s = pd.to_numeric(ok[col], errors="coerce").dropna()
        if s.empty:
            continue
        for name, value in {
            "mean": s.mean(),
            "std": s.std(ddof=1) if len(s) > 1 else 0.0,
            "median": s.median(),
            "min": s.min(),
            "q25": s.quantile(0.25),
            "q75": s.quantile(0.75),
            "max": s.max(),
        }.items():
            row = dict(base)
            row["stat_metric"] = col
            row["stat_name"] = name
            row["stat_value"] = value
            stats.append(row)
    return stats


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run LoRP-FSD Excel rows with current DA policy and export comparison CSV.")
    p.add_argument("--excel", default="results_MILP.xlsx")
    p.add_argument("--instance-folder", default="instances")
    p.add_argument("--out", default="pipeline_out/fsd_batch_results_with_stats.csv")
    p.add_argument("--runtime", type=int, default=1, help="PyVRP runtime seconds per row/seed.")
    p.add_argument("--runs", type=int, default=1, help="Seeds per row.")
    p.add_argument("--start-row", type=int, default=None, help="Minimum Excel row_id to run.")
    p.add_argument("--limit", type=int, default=None, help="Limit number of rows for smoke tests.")
    p.add_argument("--verbose", action="store_true")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    out = Path(args.out)
    out.parent.mkdir(exist_ok=True, parents=True)
    instance_folder = Path(args.instance_folder)

    # Load all LoRP-FSD rows. Resolution handles exact/coord-prefix/suffix matching.
    mapping = load_lorp_fsd_mapping(args.excel, instance_folder=None)
    if args.start_row is not None:
        mapping = mapping[mapping["row_id"] >= args.start_row]
    if args.limit is not None:
        mapping = mapping.head(args.limit)

    print(f"Rows selected: {len(mapping)}")
    print(f"Runtime per row: {args.runtime}s × {args.runs} run(s)")
    print(f"Output: {out}")

    records: list[dict[str, Any]] = []
    iterator = tqdm(
        mapping.iterrows(),
        total=len(mapping),
        unit="row",
        desc="LoRP-FSD",
        dynamic_ncols=True,
        leave=True,
    )
    for _, row in iterator:
        rec = run_row(row, instance_folder, args.runtime, args.runs, verbose=args.verbose)
        records.append(rec)

        status = rec.get("run_status")
        gap = rec.get("abs_gap_pyvrp_vs_milp")
        gap_txt = f"{gap:.2%}" if isinstance(gap, (int, float)) else "-"
        total = rec.get("pyvrp_total_cost")
        total_txt = f"{total:.2f}" if isinstance(total, (int, float)) else "-"
        iterator.set_postfix_str(
            f"row={rec.get('row_id')} status={status} total={total_txt} gap={gap_txt}",
            refresh=False,
        )

    result_df = pd.DataFrame(records)
    stats_rows = make_stats_rows(result_df)
    combined = pd.concat([result_df, pd.DataFrame(stats_rows)], ignore_index=True, sort=False)
    combined.to_csv(out, index=False)

    ok = result_df[result_df["run_status"] == "OK"]
    print("\nSUMMARY")
    print(f"  result rows              : {len(result_df)}")
    print(f"  ok rows                  : {len(ok)}")
    print(f"  errors                   : {(result_df['run_status'] == 'ERROR').sum()}")
    print(f"  missing dat rows          : {(result_df['run_status'] == 'MISSING_DAT').sum()}")
    print(f"  ambiguous dat rows        : {(result_df['run_status'] == 'AMBIGUOUS_DAT').sum()}")
    if len(ok):
        print(f"  mean abs gap             : {ok['abs_gap_pyvrp_vs_milp'].mean():.4%}")
        print(f"  median abs gap           : {ok['abs_gap_pyvrp_vs_milp'].median():.4%}")
        print(f"  pyvrp below milp count   : {(ok['raw_gap_pyvrp_minus_milp'] < 0).sum()}")
        print(f"  too far gap >20% count   : {(ok['abs_gap_pyvrp_vs_milp'] > 0.20).sum()}")
        print(f"  capacity violations      : {ok['capacity_violation'].sum()}")
    print(f"  CSV written              : {out}")


if __name__ == "__main__":
    main()
