"""Route extraction, depot capacity audit, unserved sanity checks.

Operates on PyVRP results from build_endogenous_da_model. Relies on
info["vehicle_types"] for vehicle metadata and info["location_to_client"]
to map PyVRP location indices back to client ids.
"""
from __future__ import annotations

from typing import Any, Dict, List, Set

from da_geometry import dist_euclid
from dat_loader import Instance


def extract_routes(inst: Instance, res, info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract a flat list of route records from a PyVRP result.

    distance_scaled is reconstructed geometrically as
        sum(raw_euclid_segment) * escala
    using the depot/client coordinates, so it is unweighted regardless of
    whether F_R/F_A are encoded in PyVRP edge costs. For DA routes, the return
    leg cost is treated as 0 (matches model construction).

    distance_objective is whatever PyVRP reports for the route (weighted if
    encode_cost_factors=True, otherwise == distance_scaled).
    """
    sol = res.best
    vehicle_types = info["vehicle_types"]
    loc_to_client = info.get("location_to_client", {}) or {}
    escala = float(info.get("escala", 1.0))

    records: List[Dict[str, Any]] = []
    for r_idx, route in enumerate(sol.routes()):
        vt_idx = route.vehicle_type()
        if vt_idx >= len(vehicle_types):
            print(f"[warn] route {r_idx}: vehicle_type idx {vt_idx} out of range")
            continue
        vt_meta = vehicle_types[vt_idx]
        kind = vt_meta["type"]
        depot_id = vt_meta["depot"]

        client_ids: List[int] = []
        for trip in route.trips():
            for loc_idx in trip.visits():
                cid = loc_to_client.get(int(loc_idx))
                if cid is None:
                    print(f"[warn] route {r_idx}: location {loc_idx} unmapped, skipping")
                    continue
                client_ids.append(int(cid))

        demand = float(sum(inst.clients[c]["demand"] for c in client_ids))

        # Reconstruct unweighted scaled distance from geometry.
        d_raw = 0.0
        if client_ids:
            depot = inst.depots[depot_id]
            xy_depot = (float(depot["x"]), float(depot["y"]))
            if kind == "direct_allocation":
                cid0 = client_ids[0]
                c0 = inst.clients[cid0]
                d_raw = dist_euclid(xy_depot, (float(c0["x"]), float(c0["y"])))
                # DA return leg has cost 0 in the model; preserve that here.
            else:
                seq_xy: List = [xy_depot]
                for cid in client_ids:
                    c = inst.clients[cid]
                    seq_xy.append((float(c["x"]), float(c["y"])))
                seq_xy.append(xy_depot)
                for a, b in zip(seq_xy[:-1], seq_xy[1:]):
                    d_raw += dist_euclid(a, b)
        distance_scaled = d_raw * escala

        records.append({
            "route_idx": r_idx,
            "vehicle_type_idx": vt_idx,
            "kind": kind,
            "depot_id": depot_id,
            "client_ids": client_ids,
            "demand": demand,
            "distance_scaled": float(distance_scaled),
            "distance_objective": float(route.distance()),
        })
    return records


def audit_capacity(inst: Instance, route_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate routing+DA demand per depot and compare to real capacity."""
    by_depot: Dict[int, Dict[str, Any]] = {}
    for did, depot in inst.depots.items():
        by_depot[did] = {
            "capacity": float(depot["cap"]),
            "routing_demand": 0.0,
            "da_demand": 0.0,
            "total_demand": 0.0,
            "excess": 0.0,
            "violated": False,
        }

    for rec in route_records:
        did = rec["depot_id"]
        if did not in by_depot:
            continue
        if rec["kind"] == "routing":
            by_depot[did]["routing_demand"] += rec["demand"]
        else:
            by_depot[did]["da_demand"] += rec["demand"]

    violated = False
    max_excess = 0.0
    for did, info in by_depot.items():
        total = info["routing_demand"] + info["da_demand"]
        info["total_demand"] = total
        excess = max(0.0, total - info["capacity"])
        info["excess"] = excess
        info["violated"] = excess > 1e-9
        if info["violated"]:
            violated = True
            if excess > max_excess:
                max_excess = excess

    return {
        "violated": violated,
        "max_excess": max_excess,
        "by_depot": by_depot,
    }


def find_unserved_clients(inst: Instance, route_records: List[Dict[str, Any]]) -> Set[int]:
    """Return clients absent from every route."""
    served: Set[int] = set()
    for rec in route_records:
        served.update(rec["client_ids"])
    return set(inst.clients.keys()) - served


__all__ = ["extract_routes", "audit_capacity", "find_unserved_clients"]
