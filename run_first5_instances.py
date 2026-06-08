from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

from da_geometry import assign_da_clients, build_direct_allocation_data, compute_max_distance
from dat_loader import load_dat
from instance_adapter import adapt_instance, spec_from_row
from pyvrp_model import build_full_model, solve_fast
from reporting import build_full_report, extract_kpis_level1, extract_kpis_level2
from xlsx_loader import load_lorp_fsd_mapping

EXCEL = "results_MILP.xlsx"
INSTANCES = "instances"
START_ROW_ID = 2
N_ROWS = 5
RUNTIME = 3
N_RUNS = 1
OUT = Path("pipeline_out")
OUT.mkdir(exist_ok=True)

SEP = "=" * 88
SUB = "-" * 88


def fmt(x, nd=4):
    if x is None:
        return "None"
    if isinstance(x, float):
        return f"{x:.{nd}f}"
    return str(x)


def run_one(row) -> dict:
    config = spec_from_row(row)
    print(f"\n{SEP}")
    print(f"ROW {config.row_id} | {config.instance} | R={config.R} F_R={config.F_R} F_A={config.F_A}")
    print(SEP)

    # 1. Config / MILP
    print("\n[1] EXCEL / MILP")
    print(f"  UB MILP              : {config.UB:.4f}")
    print(f"  status               : {config.status}")
    print(f"  cost routing MILP    : {config.routing_cost_milp:.4f}")
    print(f"  cost DA MILP         : {config.da_cost_milp:.4f}")
    print(f"  cost vehicles MILP   : {config.vehicle_cost_milp:.4f}")
    print(f"  cost depots Excel    : {config.cost_depots:.4f}")
    print(f"  active depots        : {list(config.depots.keys())}")
    for did, d in config.depots.items():
        milp_d = config.depots_milp.get(did, {})
        print(
            f"    depot {did}: cap_excel={d['capacity']} | "
            f"milp_demand={milp_d.get('demand')} | "
            f"milp_usage_raw={milp_d.get('usage')} | "
            f"milp_veh={milp_d.get('vehicles')}"
        )

    # 2. Instance load/adapt
    print("\n[2] INSTANCE LOAD / ADAPT")
    base = load_dat(Path(INSTANCES) / config.instance)
    inst = adapt_instance(base, config)
    total_demand = sum(c["demand"] for c in inst.clients.values())
    print(f"  base depots           : {len(base.depots)}")
    print(f"  active depots         : {len(inst.depots)}")
    print(f"  clients               : {len(inst.clients)}")
    print(f"  total demand          : {total_demand:.0f}")
    print(f"  veh cap Q             : {inst.data['veh_cap']}")
    print(f"  veh fixed cost        : {inst.data['veh_fixed_cost']}")
    for did, d in inst.depots.items():
        print(f"    depot {did}: xy=({d['x']:.1f},{d['y']:.1f}) cap={d['cap']:.0f}")

    # 3. Geometry / scaling
    print("\n[3] GEOMETRY / SCALING")
    da_data, max_clients = build_direct_allocation_data(inst, inst.data["R"])
    max_dist = compute_max_distance(inst)
    arslan_scale = 100.0 / max_dist if max_dist > 0 else 1.0
    print(f"  max graph arc distance: {max_dist:.6f}")
    print(f"  Arslan scale          : {arslan_scale:.8f} (=100/max_dist; max arc -> 100)")
    print(f"  DA radius R           : {inst.data['R']}")
    print(f"  DA depots covered     : {list(da_data.keys())}")
    print(f"  max DA clients/depot  : {max_clients}")
    for did, perfil in da_data.items():
        ds = list(perfil["cost_ij"].values())
        print(
            f"    depot {did}: feasible_DA_clients={len(perfil['clients'])} | "
            f"min_dist={min(ds):.4f} max_dist={max(ds):.4f} | "
            f"min_scaled={min(ds)*arslan_scale:.6f} max_scaled={max(ds)*arslan_scale:.6f}"
        )

    # 4. DA assignment
    print("\n[4] DA ASSIGNMENT (global nearest-first, cap real)")
    da_assigned, routing_set = assign_da_clients(inst, da_data, int(inst.data["veh_cap"]))
    n_da = sum(len(v) for v in da_assigned.values())
    n_rt = len(routing_set)
    print(f"  clients DA            : {n_da}")
    print(f"  clients routing       : {n_rt}")
    print(f"  routing client IDs    : {sorted(routing_set)}")
    for did in sorted(inst.depots):
        da_clients = da_assigned.get(did, [])
        dem_da = sum(inst.clients[j]["demand"] for j in da_clients)
        cap = inst.depots[did]["cap"]
        cap_rt = cap - dem_da
        q = int(inst.data["veh_cap"])
        n_full = math.floor(cap_rt / q)
        residual = int(cap_rt) % q
        print(
            f"    depot {did}: DA_clients={len(da_clients)} DA_demand={dem_da:.0f} "
            f"cap={cap:.0f} DA_usage={dem_da/cap:.2%} | "
            f"routing_cap={cap_rt:.0f} -> full_veh={n_full} residual_veh_cap={residual}"
        )

    # 5. Build model
    print("\n[5] PYVRP MODEL BUILD")
    model, info = build_full_model(inst)
    vt = info["vehicle_types"]
    print(f"  solver scale          : {info['escala']:.8f} (=100/max_dist; Arslan)")
    print(f"  vehicle types total   : {len(vt)}")
    print(f"  DA vehicle types      : {sum(1 for x in vt if x['type']=='direct_allocation')} (1 per DA client)")
    print(f"  routing vehicle types : {sum(1 for x in vt if x['type']=='routing')}")
    for idx, x in enumerate(vt):
        if x["type"] == "direct_allocation":
            j = x["client"]
            print(f"    vt[{idx:02d}] DA depot={x['depot']} client={j} cap=demand={inst.clients[j]['demand']}")
        else:
            print(
                f"    vt[{idx:02d}] RT depot={x['depot']} num={x.get('num_available')} "
                f"cap={x.get('residual_capacity', inst.data['veh_cap'])}"
            )

    # 6. Solve
    print("\n[6] SOLVE")
    res = solve_fast(model, runtime=RUNTIME, n_runs=N_RUNS)
    sol = res.best
    print(f"  feasible              : {sol.is_feasible()}")
    print(f"  objective scaled      : {sol.distance():.6f}")
    print(f"  routes used           : {len(sol.routes())}")
    for r_idx, route in enumerate(sol.routes()):
        x = vt[route.vehicle_type()]
        trips = list(route.trips())
        dem = sum((t.delivery()[0] if t.delivery() else 0) for t in trips)
        visits = sum(len(t.visits()) for t in trips)
        print(
            f"    route[{r_idx:02d}] {x['type']:<18} depot={x['depot']} "
            f"trips={len(trips)} clients={visits} demand={dem:.0f} dist_scaled={route.distance():.6f}"
        )

    # 7. KPIs
    print("\n[7] KPI GLOBAL + DEPOT")
    k1 = extract_kpis_level1(inst, res, info)
    k2 = extract_kpis_level2(inst, res, info)
    print(f"  total demand          : {k1['total_demand']:.0f}")
    print(f"  served demand         : {k1['served_demand']:.0f}")
    print(f"  pending demand        : {k1['pending_demand']:.0f}")
    print(f"  service level         : {k1['served_demand']/k1['total_demand']:.2%}")
    for mode in ["routing", "direct_allocation"]:
        x = k1[mode]
        print(
            f"    {mode}: veh={x['n_vehicles']} clients={x['n_clients']} "
            f"demand={x['demand']:.0f} dist_scaled={x['distance']:.6f}"
        )
    for did in sorted(inst.depots):
        cap = inst.depots[did]["cap"]
        rt = k2.get(did, {}).get("routing", {"demand": 0.0, "n_clients": 0, "distance": 0.0, "n_vehicles": 0})
        da = k2.get(did, {}).get("direct_allocation", {"demand": 0.0, "n_clients": 0, "distance": 0.0, "n_vehicles": 0})
        total = rt["demand"] + da["demand"]
        print(
            f"    depot {did}: cap={cap:.0f} total={total:.0f} usage={total/cap:.2%} "
            f"| DA={da['demand']:.0f} ({da['n_clients']} clients, {da['n_vehicles']} veh) "
            f"| RT={rt['demand']:.0f} ({rt['n_clients']} clients, {rt['n_vehicles']} veh)"
        )
        if total > cap + 1e-9:
            print(f"      ERROR: capacity violation depot {did}: {total:.0f}>{cap:.0f}")

    # 8. Report/costs
    print("\n[8] COSTS / GAP")
    report = build_full_report(inst, res, config, info)
    print(f"  PyVRP routing cost    : {report['costo_routing_pyvrp']:.4f}")
    print(f"  PyVRP DA cost         : {report['costo_da_pyvrp']:.4f}")
    print(f"  PyVRP vehicle cost    : {report['costo_vehiculos_pyvrp']:.4f}")
    print(f"  depot cost from Excel : {report['costo_depositos']:.4f}")
    print(f"  PyVRP total + depots  : {report['costo_total_pyvrp']:.4f}")
    print(f"  MILP UB               : {config.UB:.4f}")
    raw_gap = report['raw_gap_pyvrp_minus_milp']
    status_gap = "PYVRP_BELOW_MILP_CHECK_MODEL" if raw_gap < 0 else "PYVRP_GE_MILP_OK"
    far_flag = "TOO_FAR" if report['gap_final'] > 0.20 else "OK_RANGE"
    print(f"  raw gap (PyVRP-MILP)/MILP : {raw_gap:.4%}  [{status_gap}]")
    print(f"  abs gap |PyVRP-MILP|/MILP : {report['gap_final']:.4%}  [{far_flag}]")
    print(f"  capacity violation        : {report['violacion_capacidad']}")

    summary = {
        "row_id": config.row_id,
        "instance": config.instance,
        "R": config.R,
        "F_R": config.F_R,
        "F_A": config.F_A,
        "milp_ub": config.UB,
        "pyvrp_routing_cost": report["costo_routing_pyvrp"],
        "pyvrp_da_cost": report["costo_da_pyvrp"],
        "pyvrp_vehicle_cost": report["costo_vehiculos_pyvrp"],
        "pyvrp_depot_cost_excel": report["costo_depositos"],
        "pyvrp_total": report["costo_total_pyvrp"],
        "gap_abs": report["gap_final"],
        "raw_gap_pyvrp_minus_milp": report["raw_gap_pyvrp_minus_milp"],
        "gap_assessment": "PYVRP_BELOW_MILP_CHECK_MODEL" if report["raw_gap_pyvrp_minus_milp"] < 0 else "PYVRP_GE_MILP_OK",
        "gap_distance_assessment": "TOO_FAR" if report["gap_final"] > 0.20 else "OK_RANGE",
        "service_level": report["nivel_servicio"],
        "capacity_violation": report["violacion_capacidad"],
        "n_da_clients": n_da,
        "n_routing_clients": n_rt,
    }
    for did in sorted(inst.depots):
        summary[f"d{did}_cap"] = report[f"d{did}_capacidad"]
        summary[f"d{did}_usage_total"] = report[f"d{did}_uso_pyvrp"]
        summary[f"d{did}_demand_da"] = report[f"d{did}_demanda_da_pyvrp"]
        summary[f"d{did}_demand_routing"] = report[f"d{did}_demanda_rt_pyvrp"]
        summary[f"d{did}_vehicles_routing"] = report[f"d{did}_veh_pyvrp"]
    return summary


def main():
    df = load_lorp_fsd_mapping(EXCEL, instance_folder=INSTANCES)
    rows = df[df["row_id"] >= START_ROW_ID].head(N_ROWS)
    print(f"Running first {N_ROWS} rows with row_id >= {START_ROW_ID}")
    print(f"Selected row_ids: {rows['row_id'].tolist()}")

    summaries = []
    for _, row in rows.iterrows():
        summaries.append(run_one(row))

    out_csv = OUT / "first5_summary.csv"
    pd.DataFrame(summaries).to_csv(out_csv, index=False)

    print(f"\n{SEP}")
    print("SUMMARY TABLE")
    print(SEP)
    cols = [
        "row_id", "instance", "R", "F_R", "F_A", "milp_ub", "pyvrp_total",
        "gap_abs", "raw_gap_pyvrp_minus_milp", "gap_assessment", "gap_distance_assessment", "service_level", "capacity_violation",
        "n_da_clients", "n_routing_clients",
    ]
    print(pd.DataFrame(summaries)[cols].to_string(index=False))
    print(f"\nSaved CSV: {out_csv}")


if __name__ == "__main__":
    main()
