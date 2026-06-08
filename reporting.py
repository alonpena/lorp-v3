"""KPI extraction and solution reporting.

All functions consume pyvrp solution objects (or mocks) plus project dataclasses.
No model-building or plotting here.
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Dict

from dat_loader import Instance
from instance_adapter import ExcelSpec


# ── aggregated KPIs ───────────────────────────────────────────────────────────

def extract_kpis_level1(inst: Instance, res, info: Dict[str, Any]) -> Dict[str, Any]:
    """Total KPIs split by vehicle type (routing vs direct_allocation)."""
    sol = res.best
    per_type: Dict[str, Any] = defaultdict(lambda: {
        "n_vehicles": 0, "distance": 0.0, "n_clients": 0, "demand": 0.0,
    })

    for route in sol.routes():
        vt_idx = route.vehicle_type()
        kind = info["vehicle_types"][vt_idx]["type"]
        per_type[kind]["n_vehicles"] += 1
        per_type[kind]["distance"] += route.distance()
        for trip in route.trips():
            per_type[kind]["n_clients"] += len(trip.visits())
            delivery = trip.delivery()
            if len(delivery) > 0:
                per_type[kind]["demand"] += delivery[0]

    total_demand = sum(c["demand"] for c in inst.clients.values())
    served_demand = sum(v["demand"] for v in per_type.values())

    return {
        "total_distance": sol.distance(),
        "total_demand": total_demand,
        "served_demand": served_demand,
        "pending_demand": total_demand - served_demand,
        "per_type": dict(per_type),
        "routing": per_type["routing"],
        "direct_allocation": per_type["direct_allocation"],
    }


def extract_kpis_level2(inst: Instance, res, info: Dict[str, Any]) -> Dict[int, Any]:
    """KPIs grouped by depot and vehicle type."""
    sol = res.best
    per_depot: Dict[int, Any] = defaultdict(lambda: {
        "routing": {"n_vehicles": 0, "distance": 0.0, "n_clients": 0, "demand": 0.0},
        "direct_allocation": {"n_vehicles": 0, "distance": 0.0, "n_clients": 0, "demand": 0.0},
    })

    for route in sol.routes():
        vt_idx = route.vehicle_type()
        vt_info = info["vehicle_types"][vt_idx]
        kind = vt_info["type"]
        depot = vt_info["depot"]
        per_depot[depot][kind]["n_vehicles"] += 1
        per_depot[depot][kind]["distance"] += route.distance()
        for trip in route.trips():
            per_depot[depot][kind]["n_clients"] += len(trip.visits())
            delivery = trip.delivery()
            if len(delivery) > 0:
                per_depot[depot][kind]["demand"] += delivery[0]

    return dict(per_depot)


# ── per-solution cost breakdown ───────────────────────────────────────────────

def extract_solution_metrics(res, kpis1: Dict[str, Any], inst_mod: Instance) -> Dict[str, Any]:
    return {
        "routing_dist": kpis1["routing"]["distance"],
        "da_dist": kpis1["direct_allocation"]["distance"],
        "n_vehicles": len(res.best.routes()),
        "vehicle_cost": inst_mod.data["veh_fixed_cost"],
        "depot_cost": sum(d["fixed_cost"] for d in inst_mod.depots.values()),
        "F_R": inst_mod.data["F_R"],
        "F_A": inst_mod.data["F_A"],
    }


def compute_solution_costs(
    solution,
    kpis1: Dict[str, Any],
    config: ExcelSpec,
    inst: Instance,
    scale: float,
) -> Dict[str, Any]:
    """Compute ex-post costs from PyVRP scaled distances.

    PyVRP edges store only Arslan-scaled distances. Cost factors are applied
    here, matching the postprocessing interpretation:
    - routing_cost = routing_distance_scaled * F_R
    - da_cost      = da_distance_scaled * F_A
    """
    cost_routing = kpis1["routing"]["distance"] * config.F_R
    cost_da = kpis1["direct_allocation"]["distance"] * config.F_A
    n_vehicles = kpis1["routing"]["n_vehicles"]
    vehicle_fixed_cost = n_vehicles * inst.data["veh_fixed_cost"]
    depot_cost = config.cost_depots
    total_cost = cost_routing + cost_da + vehicle_fixed_cost + depot_cost
    ub = config.UB
    raw_gap_pyvrp_minus_milp = (total_cost - ub) / ub if ub > 0 else None
    abs_gap = abs(raw_gap_pyvrp_minus_milp) if raw_gap_pyvrp_minus_milp is not None else None
    return {
        "routing_distance_scaled": kpis1["routing"]["distance"],
        "da_distance_scaled": kpis1["direct_allocation"]["distance"],
        "cost_routing": cost_routing,
        "cost_da": cost_da,
        "vehicle_cost": vehicle_fixed_cost,
        "depot_cost": depot_cost,
        "total_cost": total_cost,
        "gap": abs_gap,
        "gap_abs": abs_gap,
        "raw_gap_pyvrp_minus_milp": raw_gap_pyvrp_minus_milp,
    }


# ── full benchmark report row ─────────────────────────────────────────────────

def build_full_report(inst: Instance, res, config: ExcelSpec, info: Dict[str, Any]) -> Dict[str, Any]:
    """Produce a flat dict row for the benchmark results DataFrame."""
    sol = res.best
    escala = info["escala"]
    vehicle_types = info["vehicle_types"]

    ids_deposito = sorted(inst.depots.keys())
    per_deposito = {
        d: {
            "dist_routing": 0.0,
            "dist_da": 0.0,
            "n_veh_routing": 0,
            "demanda": 0.0,
            "demanda_da": 0.0,
            "demanda_routing": 0.0,
        }
        for d in ids_deposito
    }

    dist_routing_total = 0.0
    dist_da_total = 0.0
    demanda_total_atendida = 0.0
    demanda_total = sum(c["demand"] for c in inst.clients.values())

    for ruta in sol.routes():
        idx_tipo = ruta.vehicle_type()
        info_tipo = vehicle_types[idx_tipo]
        tipo = info_tipo["type"]
        deposito = info_tipo["depot"]
        dist = ruta.distance()

        if tipo == "routing":
            per_deposito[deposito]["dist_routing"] += dist
            per_deposito[deposito]["n_veh_routing"] += 1
            dist_routing_total += dist
        else:
            per_deposito[deposito]["dist_da"] += dist
            dist_da_total += dist

        for trip in ruta.trips():
            entrega = trip.delivery()
            if len(entrega) > 0:
                d = entrega[0]
                demanda_total_atendida += d
                per_deposito[deposito]["demanda"] += d
                if tipo == "routing":
                    per_deposito[deposito]["demanda_routing"] += d
                else:
                    per_deposito[deposito]["demanda_da"] += d

    costo_routing = dist_routing_total * config.F_R
    costo_da = dist_da_total * config.F_A
    n_veh_total = sum(v["n_veh_routing"] for v in per_deposito.values())
    costo_vehiculos = n_veh_total * inst.data["veh_fixed_cost"]
    costo_depositos = float(config.cost_depots)
    costo_total_pyvrp = costo_routing + costo_da + costo_vehiculos + costo_depositos

    fila: Dict[str, Any] = {
        "id": config.row_id,
        "instancia": config.instance,
        "F_R": config.F_R,
        "F_A": config.F_A,
        "R": config.R,
        "Length": config.Length,
        "costo_routing_pyvrp": costo_routing,
        "costo_da_pyvrp": costo_da,
        "costo_vehiculos_pyvrp": costo_vehiculos,
        "costo_depositos": costo_depositos,
        "costo_total_pyvrp": costo_total_pyvrp,
        "costo_routing_milp": config.routing_cost_milp,
        "costo_da_milp": config.da_cost_milp,
        "costo_vehiculos_milp": config.vehicle_cost_milp,
        "demanda_total": demanda_total,
        "demanda_atendida": demanda_total_atendida,
        "nivel_servicio": demanda_total_atendida / demanda_total if demanda_total > 0 else 0.0,
    }

    violacion_cap = False
    cap_veh = int(inst.data["veh_cap"])
    for d_id in ids_deposito:
        cap_i = inst.depots[d_id]["cap"]
        demanda_dep_i = per_deposito[d_id]["demanda"]
        if demanda_dep_i > cap_i:
            violacion_cap = True
        n_trips_da_i = math.floor(cap_i / cap_veh)
        cap_inducida_i = n_trips_da_i * cap_veh
        fila[f"d{d_id}_capacidad"] = cap_i
        fila[f"d{d_id}_cap_inducida"] = cap_inducida_i
        fila[f"d{d_id}_brecha_cap"] = cap_inducida_i - cap_i
        fila[f"d{d_id}_demanda_pyvrp"] = per_deposito[d_id]["demanda"]
        fila[f"d{d_id}_demanda_da_pyvrp"] = per_deposito[d_id]["demanda_da"]
        fila[f"d{d_id}_demanda_rt_pyvrp"] = per_deposito[d_id]["demanda_routing"]
        fila[f"d{d_id}_uso_pyvrp"] = per_deposito[d_id]["demanda"] / cap_i if cap_i > 0 else 0.0
        fila[f"d{d_id}_veh_pyvrp"] = per_deposito[d_id]["n_veh_routing"]
        milp_dep = config.depots_milp.get(d_id, {})
        fila[f"d{d_id}_demanda_milp"] = milp_dep.get("demand")
        fila[f"d{d_id}_uso_milp"] = milp_dep.get("usage")
        fila[f"d{d_id}_veh_milp"] = milp_dep.get("vehicles")

    ub_milp = config.UB
    fila["ub_milp"] = ub_milp
    fila["ub_pyvrp"] = costo_total_pyvrp
    fila["raw_gap_pyvrp_minus_milp"] = (costo_total_pyvrp - ub_milp) / ub_milp if ub_milp > 0 else None
    fila["gap_final"] = abs(fila["raw_gap_pyvrp_minus_milp"]) if fila["raw_gap_pyvrp_minus_milp"] is not None else None
    fila["violacion_capacidad"] = violacion_cap
    return fila


__all__ = [
    "build_full_report",
    "compute_solution_costs",
    "extract_kpis_level1",
    "extract_kpis_level2",
    "extract_solution_metrics",
]
