from __future__ import annotations

from pathlib import Path

import pandas as pd
from tqdm.auto import tqdm

from da_geometry import assign_da_clients, build_direct_allocation_data, compute_max_distance
from dat_loader import load_dat
from instance_adapter import adapt_instance, spec_from_row
from instance_resolver import resolve_instance_path
from pyvrp_model import build_full_model, solve_fast
from reporting import build_full_report, extract_kpis_level1, extract_kpis_level2
from xlsx_loader import load_lorp_fsd_mapping

OUT_DIR = Path("pipeline_out/iteration_first10")
OUT_DIR.mkdir(parents=True, exist_ok=True)
CSV_OUT = OUT_DIR / "first10_resolved_current_policy.csv"
XLSX_OUT = OUT_DIR / "first10_resolved_current_policy.xlsx"
LOG_OUT = OUT_DIR / "first10_resolved_current_policy.log"

RUNTIME = 1
RUNS = 1
N = 10


def log(lines: list[str], text: str = "") -> None:
    print(text)
    lines.append(text)


def selected_rows() -> pd.DataFrame:
    df = load_lorp_fsd_mapping("results_MILP.xlsx", instance_folder=None)
    rows = []
    for _, row in df.iterrows():
        config = spec_from_row(row)
        resolution = resolve_instance_path(config.instance, "instances")
        if resolution.ok:
            rows.append(row)
        if len(rows) >= N:
            break
    return pd.DataFrame(rows)


def run_one(row, lines: list[str]) -> dict:
    config = spec_from_row(row)
    resolution = resolve_instance_path(config.instance, "instances")
    base = load_dat(resolution.path)
    inst = adapt_instance(base, config)

    total_demand = sum(c["demand"] for c in inst.clients.values())
    maxdist = compute_max_distance(inst)
    escala = 100 / maxdist if maxdist > 0 else 1.0

    log(lines, "=" * 100)
    log(lines, f"ROW {config.row_id} | {config.instance} | resolved={resolution.status}:{resolution.path}")
    log(lines, f"PARAMS R={config.R} F_R={config.F_R} F_A={config.F_A} Length={config.Length} UB={config.UB}")
    log(lines, f"BASE depots={len(base.depots)} ACTIVE depots={list(inst.depots.keys())} clients={len(inst.clients)} demand={total_demand}")
    log(lines, f"veh_cap={inst.data['veh_cap']} veh_fixed_cost={inst.data['veh_fixed_cost']} maxdist={maxdist:.6f} arslan_scale={escala:.8f}")

    da_data, max_clients = build_direct_allocation_data(inst, inst.data["R"])
    log(lines, f"DA geometry: depots_with_DA={list(da_data.keys())} max_clients_per_depot={max_clients}")
    for did, perfil in da_data.items():
        ds = list(perfil["cost_ij"].values())
        log(lines, f"  depot {did}: feasible={len(perfil['clients'])} dist_raw=[{min(ds):.2f},{max(ds):.2f}] dist_scaled=[{min(ds)*escala:.2f},{max(ds)*escala:.2f}]")

    da_assigned, routing_set = assign_da_clients(inst, da_data, int(inst.data["veh_cap"]))
    log(lines, f"DA assignment repaired: DA_clients={sum(len(v) for v in da_assigned.values())} routing_clients={len(routing_set)} routing_ids={sorted(routing_set)}")
    for did in sorted(inst.depots):
        da_clients = da_assigned.get(did, [])
        da_dem = sum(inst.clients[j]["demand"] for j in da_clients)
        cap = inst.depots[did]["cap"]
        rem = cap - da_dem
        q = int(inst.data["veh_cap"])
        log(lines, f"  depot {did}: cap={cap:.0f} DA_dem={da_dem:.0f} DA_usage={da_dem/cap:.2%} rem_for_routing={rem:.0f} full_rt={int(rem)//q} residual={int(rem)%q}")

    model, info = build_full_model(inst)
    log(lines, f"Model: vehicle_types={len(info['vehicle_types'])} DA_types={sum(1 for v in info['vehicle_types'] if v['type']=='direct_allocation')} RT_types={sum(1 for v in info['vehicle_types'] if v['type']=='routing')}")

    res = solve_fast(model, runtime=RUNTIME, n_runs=RUNS)
    sol = res.best
    vt = info["vehicle_types"]
    log(lines, f"Solve: feasible={sol.is_feasible()} objective_scaled={sol.distance():.4f} routes={len(sol.routes())}")
    for idx, route in enumerate(sol.routes()):
        meta = vt[route.vehicle_type()]
        dem = sum((trip.delivery()[0] if trip.delivery() else 0) for trip in route.trips())
        visits = sum(len(trip.visits()) for trip in route.trips())
        log(lines, f"  route[{idx:02d}] {meta['type']:<18} depot={meta['depot']} clients={visits} demand={dem:.0f} dist_scaled={route.distance():.4f}")

    k1 = extract_kpis_level1(inst, res, info)
    k2 = extract_kpis_level2(inst, res, info)
    report = build_full_report(inst, res, config, info)
    log(lines, f"KPI: served={k1['served_demand']:.0f}/{k1['total_demand']:.0f} pending={k1['pending_demand']:.0f} service={report['nivel_servicio']:.2%}")
    log(lines, f"Costs: RT={report['costo_routing_pyvrp']:.4f} DA={report['costo_da_pyvrp']:.4f} VEH={report['costo_vehiculos_pyvrp']:.4f} DEP={report['costo_depositos']:.4f} TOTAL={report['costo_total_pyvrp']:.4f}")
    log(lines, f"Gap: raw={(report['raw_gap_pyvrp_minus_milp']):.4%} abs={report['gap_final']:.4%} cap_violation={report['violacion_capacidad']}")

    rec = {
        "row_id": config.row_id,
        "instance": config.instance,
        "resolved_path": str(resolution.path),
        "R": config.R,
        "F_R": config.F_R,
        "F_A": config.F_A,
        "Length": config.Length,
        "milp_ub": config.UB,
        "pyvrp_routing_cost": report["costo_routing_pyvrp"],
        "pyvrp_da_cost": report["costo_da_pyvrp"],
        "pyvrp_vehicle_cost": report["costo_vehiculos_pyvrp"],
        "pyvrp_depot_cost": report["costo_depositos"],
        "pyvrp_total": report["costo_total_pyvrp"],
        "raw_gap_pyvrp_minus_milp": report["raw_gap_pyvrp_minus_milp"],
        "abs_gap": report["gap_final"],
        "service_level": report["nivel_servicio"],
        "capacity_violation": report["violacion_capacidad"],
        "n_da_clients": k1["direct_allocation"]["n_clients"],
        "n_rt_clients": k1["routing"]["n_clients"],
        "n_da_vehicles": k1["direct_allocation"]["n_vehicles"],
        "n_rt_vehicles": k1["routing"]["n_vehicles"],
    }
    for slot, did in enumerate(sorted(inst.depots), start=1):
        if slot > 4:
            break
        rt = k2.get(did, {}).get("routing", {"demand": 0, "n_clients": 0, "n_vehicles": 0, "distance": 0})
        da = k2.get(did, {}).get("direct_allocation", {"demand": 0, "n_clients": 0, "n_vehicles": 0, "distance": 0})
        cap = inst.depots[did]["cap"]
        rec[f"Depot{slot}"] = f"d{did}"
        rec[f"Depot{slot}_id"] = did
        rec[f"CapD{slot}"] = cap
        rec[f"DemandD{slot}_PyVRP_Total"] = rt["demand"] + da["demand"]
        rec[f"DemandD{slot}_PyVRP_DA"] = da["demand"]
        rec[f"DemandD{slot}_PyVRP_Routing"] = rt["demand"]
        rec[f"UsageD{slot}_PyVRP_Total"] = (rt["demand"] + da["demand"]) / cap if cap else None
    return rec


def main() -> None:
    rows = selected_rows()
    lines: list[str] = []
    log(lines, f"Selected first {len(rows)} resolved LoRP-FSD rows: {rows['row_id'].tolist()}")
    records = []
    for _, row in tqdm(rows.iterrows(), total=len(rows), desc="first10", unit="row", dynamic_ncols=True):
        records.append(run_one(row, lines))

    out = pd.DataFrame(records)
    out.to_csv(CSV_OUT, index=False)
    out.to_excel(XLSX_OUT, index=False)
    LOG_OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nWrote CSV : {CSV_OUT}")
    print(f"Wrote XLSX: {XLSX_OUT}")
    print(f"Wrote LOG : {LOG_OUT}")
    print(out[["row_id", "instance", "milp_ub", "pyvrp_total", "abs_gap", "raw_gap_pyvrp_minus_milp", "capacity_violation"]].to_string(index=False))


if __name__ == "__main__":
    main()
