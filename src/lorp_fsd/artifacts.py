"""Per-iteration artifact export (Phase 5): audit JSON + routes/assignments CSV.

Directory layout::

    outputs/<run_id>/<instance_name>/iteration_00_audit.json
    outputs/<run_id>/<instance_name>/iteration_00_routes.csv
    outputs/<run_id>/<instance_name>/iteration_00_assignments.csv
    outputs/<run_id>/<instance_name>/iteration_00_solution.png   (written by the runner)

No pyvrp dependency here — operates purely on Phase 1–4 records.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


def iteration_dir(output_root, run_id: str, instance_name: str) -> Path:
    d = Path(output_root) / run_id / instance_name
    d.mkdir(parents=True, exist_ok=True)
    return d


def _stem(iteration: int) -> str:
    return f"iteration_{iteration:02d}"


def _client_depot_map(parsed) -> Dict[int, int]:
    m: Dict[int, int] = {}
    for r in parsed.routes:
        for c in r.client_sequence:
            m[c] = r.depot_id
    for a in parsed.da_assignments:
        m[a.client_id] = a.depot_id
    return m


def build_audit_payload(
    *, row_index, iteration, instance, config, geometry, facility_design,
    parsed, cost, capacity, feasibility, metric, forbidden, repair_selection, solve_time, status,
    capacity_not_freed_count: int = 0,
) -> dict:
    removals = sorted(repair_selection.selected) if repair_selection is not None else []
    candidate_safety = getattr(repair_selection, "candidate_safety", {}) if repair_selection is not None else {}
    rejected = getattr(repair_selection, "rejected_candidates", set()) if repair_selection is not None else set()
    return {
        "row_id": row_index,
        "instance_name": instance.name,
        "iteration": iteration,
        "F_R": config.F_R, "F_A": config.F_A, "R": config.R, "Length": config.Length,
        "scale": geometry.scale, "max_dist": geometry.max_dist,
        "active_depots": list(facility_design.active_depot_ids),
        "depot_capacities": {str(i): facility_design.depots[i].capacity for i in facility_design.active_depot_ids},
        "forbidden_routing_assignments": [list(p) for p in sorted(forbidden)],
        "selected_repair_removals": [list(p) for p in removals],
        "repair_candidate_policy": getattr(repair_selection, "repair_candidate_policy", "") if repair_selection is not None else "",
        "repair_candidate_safety": [s.to_dict() for s in candidate_safety.values()],
        "rejected_repair_candidates": [list(p) for p in sorted(rejected)],
        "same_depot_DA_risk_count": getattr(repair_selection, "same_depot_DA_risk_count", 0) if repair_selection is not None else 0,
        "length_invalid_cut_count": getattr(repair_selection, "length_invalid_cut_count", 0) if repair_selection is not None else 0,
        "rejected_candidates_count": getattr(repair_selection, "rejected_candidates_count", 0) if repair_selection is not None else 0,
        "capacity_not_freed_count": capacity_not_freed_count,
        "route_length_repair_attempts": 0,
        "demand_routing": {str(i): r.demand_routing for i, r in capacity.by_depot.items()},
        "demand_DA": {str(i): r.demand_da for i, r in capacity.by_depot.items()},
        "demand_total": {str(i): r.demand_total for i, r in capacity.by_depot.items()},
        "excess": {str(i): r.excess for i, r in capacity.by_depot.items()},
        "capacity_feasible": capacity.capacity_feasible,
        "all_clients_served_exactly_once": parsed.served_exactly_once,
        "route_length_feasible": not feasibility.route_length_violations,
        "route_capacity_feasible": not feasibility.route_capacity_violations,
        "da_radius_feasible": not feasibility.da_radius_violations,
        "penalty_distance_suspected": feasibility.penalty_distance_suspected,
        "cost_routing_pyvrp": cost.cost_routing,
        "cost_direct_all_pyvrp": cost.cost_direct_all,
        "cost_vehicles_pyvrp": cost.cost_vehicles,
        "cost_depots_pyvrp": cost.cost_depots,
        "z_pyvrp": cost.total,
        "ub_milp": config.UB,
        "cost_routing_milp": config.cost_routing,
        "cost_direct_all_milp": config.cost_direct_all,
        "cost_vehicles_milp": config.cost_vehicles,
        "cost_depots_milp": config.cost_depots,
        "comparison_metric_label": metric.label,
        "comparison_metric_value": metric.value,
        "metric_flags": sorted(metric.flags),
        "solution_flags": sorted(feasibility.flags),
        "fully_feasible": feasibility.fully_feasible,
        "solve_time": solve_time,
        "status": status,
    }


def write_iteration_artifacts(
    *, output_dir: Path, iteration: int, row_index, instance, config, geometry,
    facility_design, parsed, cost, capacity, feasibility, metric, forbidden,
    repair_selection, solve_time, status, capacity_not_freed_count: int = 0,
) -> Dict[str, Path]:
    out = Path(output_dir)
    stem = _stem(iteration)

    audit_path = out / f"{stem}_audit.json"
    payload = build_audit_payload(
        row_index=row_index, iteration=iteration, instance=instance, config=config,
        geometry=geometry, facility_design=facility_design, parsed=parsed, cost=cost,
        capacity=capacity, feasibility=feasibility, metric=metric, forbidden=forbidden,
        repair_selection=repair_selection, solve_time=solve_time, status=status,
        capacity_not_freed_count=capacity_not_freed_count,
    )
    audit_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # routes CSV (one row per routing route)
    Length = float(config.Length)
    routes_path = out / f"{stem}_routes.csv"
    with routes_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["iteration", "route_id", "vehicle_type", "service_mode", "depot_id",
                    "client_sequence", "demand", "scaled_distance", "weighted_cost",
                    "route_length_feasible", "capacity_feasible"])
        for rid, r in enumerate(parsed.routes):
            w.writerow([
                iteration, rid, r.vehicle_type_index, r.mode, r.depot_id,
                ";".join(str(c) for c in r.client_sequence), r.demand,
                round(r.reconstructed_scaled_distance, 6), round(r.reconstructed_weighted_cost, 6),
                r.reconstructed_scaled_distance <= Length + 1e-3,
                r.demand <= r.capacity,
            ])

    # assignments CSV (one row per client)
    R = float(config.R)
    client_depot = _client_depot_map(parsed)
    assignments_path = out / f"{stem}_assignments.csv"
    with assignments_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["iteration", "client_id", "service_mode", "depot_id", "demand",
                    "da_feasible", "dist_scaled_to_depot", "forbidden_from_routing_depots"])
        for cid in sorted(instance.clients):
            mode = parsed.service_by_client.get(cid, "UNSERVED")
            depot = client_depot.get(cid)
            dist = geometry.depot_client_scaled(depot, cid) if depot is not None else None
            forb_depots = sorted(h for (h, c) in forbidden if c == cid)
            w.writerow([
                iteration, cid, mode, depot if depot is not None else "",
                instance.clients[cid].demand,
                (dist is not None and dist <= R) if dist is not None else "",
                round(dist, 6) if dist is not None else "",
                ";".join(str(h) for h in forb_depots),
            ])

    return {"audit": audit_path, "routes": routes_path, "assignments": assignments_path}


__all__ = ["iteration_dir", "build_audit_payload", "write_iteration_artifacts"]
