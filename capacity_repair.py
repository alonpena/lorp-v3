"""Routing-only capacity repair via Clarke-Wright savings deltas.

For each routing client j with previous node i and next node k:
    Δ = d(i,j) + d(j,k) - d(i,k)
Larger Δ => more savings if j is dropped from this route.

Repair removes routing clients (by adding (depot, client) to the routing
exclusions set) until the depot's excess demand is covered. DA candidates
are NOT modified here.
"""
from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple

from da_geometry import dist_euclid
from dat_loader import Instance


def _coord_depot(inst: Instance, did: int) -> Tuple[float, float]:
    d = inst.depots[did]
    return float(d["x"]), float(d["y"])


def _coord_client(inst: Instance, cid: int) -> Tuple[float, float]:
    c = inst.clients[cid]
    return float(c["x"]), float(c["y"])


def compute_routing_removal_deltas(
    inst: Instance,
    route_record: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Δ = d_ij + d_jk - d_ik for each client j in a routing route."""
    if route_record["kind"] != "routing":
        return []

    did = route_record["depot_id"]
    clients = route_record["client_ids"]
    if not clients:
        return []

    depot_xy = _coord_depot(inst, did)
    seq_xy: List[Tuple[float, float]] = [depot_xy]
    for cid in clients:
        seq_xy.append(_coord_client(inst, cid))
    seq_xy.append(depot_xy)

    out: List[Dict[str, Any]] = []
    for pos, cid in enumerate(clients):
        i_xy = seq_xy[pos]
        j_xy = seq_xy[pos + 1]
        k_xy = seq_xy[pos + 2]
        delta = dist_euclid(i_xy, j_xy) + dist_euclid(j_xy, k_xy) - dist_euclid(i_xy, k_xy)
        out.append({
            "depot_id": did,
            "client_id": cid,
            "route_idx": route_record["route_idx"],
            "demand": float(inst.clients[cid]["demand"]),
            "delta": float(delta),
            "position": pos,
        })
    return out


def rank_overloaded_routing_candidates(
    inst: Instance,
    route_records: List[Dict[str, Any]],
    audit: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Candidates from overloaded depots' routing routes, sorted by Δ desc."""
    overloaded = {did for did, info in audit["by_depot"].items() if info["violated"]}
    if not overloaded:
        return []
    candidates: List[Dict[str, Any]] = []
    for rec in route_records:
        if rec["kind"] != "routing":
            continue
        if rec["depot_id"] not in overloaded:
            continue
        candidates.extend(compute_routing_removal_deltas(inst, rec))
    candidates.sort(key=lambda d: d["delta"], reverse=True)
    return candidates


def select_routing_exclusions(
    inst: Instance,
    audit: Dict[str, Any],
    ranked_candidates: List[Dict[str, Any]],
) -> Set[Tuple[int, int]]:
    """Greedy selection per overloaded depot until accumulated demand >= excess."""
    excess_remaining: Dict[int, float] = {
        did: float(info["excess"])
        for did, info in audit["by_depot"].items()
        if info["violated"]
    }
    chosen: Set[Tuple[int, int]] = set()
    for cand in ranked_candidates:
        did = cand["depot_id"]
        if excess_remaining.get(did, 0.0) <= 1e-9:
            continue
        pair = (int(did), int(cand["client_id"]))
        if pair in chosen:
            continue
        chosen.add(pair)
        excess_remaining[did] -= cand["demand"]
    return chosen


def merge_exclusions(
    old: Set[Tuple[int, int]],
    new: Set[Tuple[int, int]],
) -> Set[Tuple[int, int]]:
    return set(old) | set(new)


__all__ = [
    "compute_routing_removal_deltas",
    "rank_overloaded_routing_candidates",
    "select_routing_exclusions",
    "merge_exclusions",
]
