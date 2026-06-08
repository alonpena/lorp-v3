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
from typing import Any, Dict, List, Optional, Set, Tuple


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


def _json_cell(value) -> str:
    return json.dumps(value, sort_keys=True)


def _excess_by_depot(capacity) -> Dict[int, float]:
    return {i: rec.excess for i, rec in capacity.by_depot.items()}


def _overloaded_depots(capacity) -> List[int]:
    return sorted(i for i, rec in capacity.by_depot.items() if rec.excess > 0)


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


ITERATION_SUMMARY_COLUMNS = [
    "iteration",
    "iteration_status",
    "final_status",
    "solve_time",
    "z_pyvrp",
    "comparison_metric_label",
    "comparison_metric_value",
    "fully_feasible",
    "capacity_feasible",
    "overloaded_depots",
    "total_excess",
    "excess_by_depot",
    "forbidden_count_before",
    "selected_count",
    "rejected_count",
    "repair_infeasible",
    "infeasible_depots",
    "forbidden_count_after",
]

REPAIR_TRACE_COLUMNS = [
    "iteration",
    "action",
    "depot_id",
    "client_id",
    "reason",
    "overloaded_depot",
    "excess",
    "forbidden_count_before",
    "forbidden_count_after",
    "final_status",
]


def _iteration_status(it) -> str:
    return "FEASIBLE" if it.feasibility.fully_feasible else "RELAXED_INFEASIBLE"


def _forbidden_count_after(it) -> int:
    repair = it.repair_selection
    if repair is None:
        return len(it.forbidden_before)
    return len(repair.updated_forbidden)


def write_iteration_summary_csv(output_dir: Path, iterations, final_status: str) -> Path:
    """Write row-level per-iteration summary CSV."""
    path = Path(output_dir) / "iteration_summary.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ITERATION_SUMMARY_COLUMNS)
        w.writeheader()
        for it in iterations:
            repair = it.repair_selection
            selected = getattr(repair, "selected", set()) if repair is not None else set()
            rejected = getattr(repair, "rejected_candidates", set()) if repair is not None else set()
            infeasible_depots = getattr(repair, "infeasible_depots", []) if repair is not None else []
            w.writerow({
                "iteration": it.iteration,
                "iteration_status": _iteration_status(it),
                "final_status": final_status,
                "solve_time": it.solve_time,
                "z_pyvrp": it.cost.total,
                "comparison_metric_label": it.metric.label,
                "comparison_metric_value": it.metric.value if it.metric.value is not None else "",
                "fully_feasible": it.feasibility.fully_feasible,
                "capacity_feasible": it.capacity.capacity_feasible,
                "overloaded_depots": _json_cell(_overloaded_depots(it.capacity)),
                "total_excess": it.capacity.total_excess,
                "excess_by_depot": _json_cell(_excess_by_depot(it.capacity)),
                "forbidden_count_before": len(it.forbidden_before),
                "selected_count": len(selected),
                "rejected_count": len(rejected),
                "repair_infeasible": bool(getattr(repair, "repair_infeasible", False)) if repair is not None else False,
                "infeasible_depots": _json_cell(sorted(infeasible_depots)),
                "forbidden_count_after": _forbidden_count_after(it),
            })
    return path


def write_repair_trace_csv(output_dir: Path, iterations, final_status: str) -> Path:
    """Write row-level selected/rejected repair candidate trace CSV."""
    path = Path(output_dir) / "repair_trace.csv"
    seen_rejected = set()
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=REPAIR_TRACE_COLUMNS)
        w.writeheader()
        for it in iterations:
            repair = it.repair_selection
            if repair is None:
                continue
            forbidden_before = len(it.forbidden_before)
            forbidden_after = _forbidden_count_after(it)
            excess = _excess_by_depot(it.capacity)

            for depot_id, client_id in sorted(getattr(repair, "selected", set())):
                depot_excess = excess.get(depot_id, 0.0)
                w.writerow({
                    "iteration": it.iteration,
                    "action": "selected",
                    "depot_id": depot_id,
                    "client_id": client_id,
                    "reason": "selected_for_capacity_repair",
                    "overloaded_depot": depot_excess > 0,
                    "excess": depot_excess,
                    "forbidden_count_before": forbidden_before,
                    "forbidden_count_after": forbidden_after,
                    "final_status": final_status,
                })

            for depot_id, client_id, reason in sorted(getattr(repair, "rejected_candidates", set())):
                key = (depot_id, client_id, reason)
                if key in seen_rejected:
                    continue
                seen_rejected.add(key)
                depot_excess = excess.get(depot_id, 0.0)
                w.writerow({
                    "iteration": it.iteration,
                    "action": "rejected",
                    "depot_id": depot_id,
                    "client_id": client_id,
                    "reason": reason,
                    "overloaded_depot": depot_excess > 0,
                    "excess": depot_excess,
                    "forbidden_count_before": forbidden_before,
                    "forbidden_count_after": forbidden_after,
                    "final_status": final_status,
                })
    return path


def write_row_reporting_artifacts(output_dir: Path, iterations, final_status: str) -> Dict[str, Path]:
    """Write minimal row-level reporting trace artifacts without changing JSON."""
    return {
        "iteration_summary": write_iteration_summary_csv(output_dir, iterations, final_status),
        "repair_trace": write_repair_trace_csv(output_dir, iterations, final_status),
    }


COST_BREAKDOWN_COLUMNS = ["component", "milp", "pyvrp", "delta"]
DEPOT_USAGE_COLUMNS = [
    "depot_id",
    "demand_routing",
    "demand_DA",
    "demand_total",
    "capacity",
    "usage_pct",
    "excess",
    "overloaded",
]


def _delta(pyvrp_value, milp_value):
    if pyvrp_value is None or milp_value is None:
        return None
    return pyvrp_value - milp_value


def _cost_breakdown_rows(result, config) -> List[Dict[str, Any]]:
    cost = result.final.cost
    rows = [
        ("routing", getattr(config, "cost_routing", None), getattr(cost, "cost_routing", None)),
        ("direct_allocation", getattr(config, "cost_direct_all", None), getattr(cost, "cost_direct_all", None)),
        ("vehicle", getattr(config, "cost_vehicles", None), getattr(cost, "cost_vehicles", None)),
        ("depot", getattr(config, "cost_depots", None), getattr(cost, "cost_depots", None)),
        ("total", getattr(config, "UB", None), getattr(cost, "total", None)),
    ]
    return [
        {"component": name, "milp": milp, "pyvrp": pyvrp, "delta": _delta(pyvrp, milp)}
        for name, milp, pyvrp in rows
    ]


def _depot_usage_rows(result) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for depot_id, rec in sorted(result.final.capacity.by_depot.items()):
        usage_pct = None if rec.capacity == 0 else 100.0 * rec.demand_total / rec.capacity
        rows.append({
            "depot_id": depot_id,
            "demand_routing": rec.demand_routing,
            "demand_DA": rec.demand_da,
            "demand_total": rec.demand_total,
            "capacity": rec.capacity,
            "usage_pct": usage_pct,
            "excess": rec.excess,
            "overloaded": rec.excess > 0,
        })
    return rows


def build_row_report_payload(result, config) -> Dict[str, Any]:
    """Build basic row-level report payload from final RowRunResult state."""
    final = result.final
    repair_selections = [it.repair_selection for it in result.iterations if it.repair_selection is not None]
    selected = sorted({p for sel in repair_selections for p in getattr(sel, "selected", set())})
    rejected = sorted({p for sel in repair_selections for p in getattr(sel, "rejected_candidates", set())})

    return {
        "row_id": result.row_index,
        "instance_name": result.instance_name,
        "status": result.status,
        "final_iteration": result.final_iteration,
        "n_iterations": result.n_iterations,
        "total_solve_time": result.total_solve_time,
        "repair_candidate_policy": getattr(result, "repair_candidate_policy", ""),
        "final_forbidden_count": len(getattr(result, "final_forbidden", [])),
        "parameters": {
            "F_R": getattr(config, "F_R", None),
            "F_A": getattr(config, "F_A", None),
            "R": getattr(config, "R", None),
            "Length": getattr(config, "Length", None),
        },
        "milp": {
            "UB": getattr(config, "UB", None),
            "LB": getattr(config, "LB", None),
            "status": getattr(config, "status", None),
            "gap": getattr(config, "gap", None),
            "cost_routing": getattr(config, "cost_routing", None),
            "cost_direct_all": getattr(config, "cost_direct_all", None),
            "cost_vehicles": getattr(config, "cost_vehicles", None),
            "cost_depots": getattr(config, "cost_depots", None),
        },
        "pyvrp": {
            "cost_routing": getattr(final.cost, "cost_routing", None),
            "cost_direct_all": getattr(final.cost, "cost_direct_all", None),
            "cost_vehicles": getattr(final.cost, "cost_vehicles", None),
            "cost_depots": getattr(final.cost, "cost_depots", None),
            "total": getattr(final.cost, "total", None),
        },
        "comparison_metric": {
            "label": getattr(final.metric, "label", ""),
            "value": getattr(final.metric, "value", None),
            "flags": sorted(getattr(final.metric, "flags", [])),
        },
        "feasibility": {
            "fully_feasible": getattr(final.feasibility, "fully_feasible", False),
            "capacity_feasible": getattr(final.feasibility, "capacity_feasible", False),
            "served_exactly_once": getattr(final.feasibility, "served_exactly_once", False),
            "route_length_feasible": not getattr(final.feasibility, "route_length_violations", []),
            "route_capacity_feasible": not getattr(final.feasibility, "route_capacity_violations", []),
            "da_radius_feasible": not getattr(final.feasibility, "da_radius_violations", []),
            "penalty_distance_suspected": getattr(final.feasibility, "penalty_distance_suspected", False),
        },
        "capacity": {
            "total_excess": final.capacity.total_excess,
            "overloaded_depots": _overloaded_depots(final.capacity),
            "depots": _depot_usage_rows(result),
        },
        "repair": {
            "selected_candidates": [list(p) for p in selected],
            "rejected_candidates": [list(p) for p in rejected],
            "selected_count": len(selected),
            "rejected_count": len(rejected),
        },
        "artifacts": {
            "report_md": "report.md",
            "report_json": "report.json",
            "cost_breakdown_csv": "cost-breakdown.csv",
            "depot_usage_csv": "depot_usage.csv",
            "iteration_summary_csv": "iteration_summary.csv",
            "repair_trace_csv": "repair_trace.csv",
        },
    }


def write_report_json(output_dir: Path, result, config) -> Path:
    path = Path(output_dir) / "report.json"
    path.write_text(json.dumps(build_row_report_payload(result, config), indent=2), encoding="utf-8")
    return path


def write_cost_breakdown_csv(output_dir: Path, result, config) -> Path:
    path = Path(output_dir) / "cost-breakdown.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COST_BREAKDOWN_COLUMNS)
        w.writeheader()
        for row in _cost_breakdown_rows(result, config):
            w.writerow(row)
    return path


def write_depot_usage_csv(output_dir: Path, result) -> Path:
    path = Path(output_dir) / "depot_usage.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=DEPOT_USAGE_COLUMNS)
        w.writeheader()
        for row in _depot_usage_rows(result):
            w.writerow(row)
    return path


def write_report_md(output_dir: Path, result, config) -> Path:
    payload = build_row_report_payload(result, config)
    path = Path(output_dir) / "report.md"
    metric = payload["comparison_metric"]
    capacity = payload["capacity"]
    repair = payload["repair"]
    lines = [
        f"# Row {payload['row_id']} — {payload['instance_name']}",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| status | {payload['status']} |",
        f"| final_iteration | {payload['final_iteration']} |",
        f"| n_iterations | {payload['n_iterations']} |",
        f"| total_solve_time | {payload['total_solve_time']:.6f} |",
        f"| repair_policy | {payload['repair_candidate_policy']} |",
        f"| metric | {metric['label']}={metric['value']} |",
        f"| total_excess | {capacity['total_excess']} |",
        f"| overloaded_depots | {capacity['overloaded_depots']} |",
        f"| selected_repair_candidates | {repair['selected_count']} |",
        f"| rejected_repair_candidates | {repair['rejected_count']} |",
        "",
        "## Files",
        "",
        "- `report.json`",
        "- `cost-breakdown.csv`",
        "- `depot_usage.csv`",
        "- `iteration_summary.csv`",
        "- `repair_trace.csv`",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_basic_row_report_artifacts(output_dir: Path, result, config) -> Dict[str, Path]:
    """Write basic row-level report.md/report.json/cost/depot CSV artifacts."""
    return {
        "report_json": write_report_json(output_dir, result, config),
        "report_md": write_report_md(output_dir, result, config),
        "cost_breakdown": write_cost_breakdown_csv(output_dir, result, config),
        "depot_usage": write_depot_usage_csv(output_dir, result),
    }


__all__ = [
    "iteration_dir",
    "build_audit_payload",
    "write_iteration_artifacts",
    "ITERATION_SUMMARY_COLUMNS",
    "REPAIR_TRACE_COLUMNS",
    "COST_BREAKDOWN_COLUMNS",
    "DEPOT_USAGE_COLUMNS",
    "write_iteration_summary_csv",
    "write_repair_trace_csv",
    "write_row_reporting_artifacts",
    "build_row_report_payload",
    "write_report_json",
    "write_cost_breakdown_csv",
    "write_depot_usage_csv",
    "write_report_md",
    "write_basic_row_report_artifacts",
]
