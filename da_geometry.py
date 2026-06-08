"""Pure distance and direct-allocation geometry.

No pyvrp, no matplotlib, no I/O. Safe to import in any environment.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Set, Tuple

from dat_loader import Instance


# ── distance primitives ───────────────────────────────────────────────────────

def dist_euclid(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def dist_manhattan(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


# ── instance geometry ─────────────────────────────────────────────────────────

def compute_max_distance(inst: Instance) -> float:
    nodes = (
        [(d["x"], d["y"]) for d in inst.depots.values()]
        + [(c["x"], c["y"]) for c in inst.clients.values()]
    )
    maxdist = 0.0
    for i in range(len(nodes)):
        for j in range(len(nodes)):
            maxdist = max(maxdist, math.hypot(nodes[i][0] - nodes[j][0], nodes[i][1] - nodes[j][1]))
    return maxdist


# ── direct-allocation data ────────────────────────────────────────────────────

def build_direct_allocation_data(inst: Instance, radius: float) -> Tuple[Dict[int, Dict[str, Any]], int]:
    """For each depot, find clients within *radius* and build cost dicts.

    Returns:
        da_data: depot_id → {clients, arcs_ij, arcs_ji, cost_ij, cost_ji}
        max_clients_per_depot: int
    """
    da_data: Dict[int, Dict[str, Any]] = {}
    max_clients_per_depot = 0

    for i, depot in inst.depots.items():
        xi, yi = depot["x"], depot["y"]
        clients_i: List[int] = []
        arcs_ij: List[Tuple[int, int]] = []
        arcs_ji: List[Tuple[int, int]] = []
        cost_ij: Dict[Tuple[int, int], float] = {}
        cost_ji: Dict[Tuple[int, int], float] = {}

        for j, client in inst.clients.items():
            xj, yj = client["x"], client["y"]
            dij = dist_euclid((xi, yi), (xj, yj))
            if dij <= radius:
                clients_i.append(j)
                arcs_ij.append((i, j))
                arcs_ji.append((j, i))
                cost_ij[(i, j)] = dij
                cost_ji[(j, i)] = 0.0

        if clients_i:
            da_data[i] = {
                "clients": clients_i,
                "arcs_ij": arcs_ij,
                "arcs_ji": arcs_ji,
                "cost_ij": cost_ij,
                "cost_ji": cost_ji,
            }
            max_clients_per_depot = max(max_clients_per_depot, len(clients_i))

    return da_data, max_clients_per_depot


# ── client assignment ─────────────────────────────────────────────────────────

def _routing_vehicle_capacities(inst: Instance, da_assigned: Dict[int, List[int]], veh_cap: int) -> List[int]:
    caps: List[int] = []
    for i, d in inst.depots.items():
        da_demand = sum(inst.clients[j]["demand"] for j in da_assigned.get(i, []))
        remaining = max(0, int(d["cap"] - da_demand))
        caps.extend([veh_cap] * (remaining // veh_cap))
        residual = remaining % veh_cap
        if residual > 0:
            caps.append(residual)
    return caps


def _can_pack_demands(demands: List[int], capacities: List[int]) -> bool:
    """First-fit decreasing feasibility check for routing residual capacities."""
    bins = sorted(capacities, reverse=True)
    for demand in sorted(demands, reverse=True):
        placed = False
        for idx, cap in enumerate(bins):
            if demand <= cap:
                bins[idx] -= demand
                placed = True
                break
        if not placed:
            return False
    return True


def assign_da_clients(
    inst: Instance,
    da_data: Dict[int, Dict[str, Any]],
    veh_cap: int | None = None,
    repair_routing_capacity: bool = True,
) -> Tuple[Dict[int, List[int]], Set[int]]:
    """Greedy DA assignment with global nearest-first priority + optional repair.

    Policy:
    - All feasible (depot, client) pairs ranked globally by distance.
    - Nearest pair processed first; each client assigned once.
    - Capacity limit per depot = real depot capacity.
    - DA is prioritized, but final split must leave routing clients packable in
      routing vehicles generated from remaining capacity.
    - Repair demotes the fewest/farthest DA clients needed to make routing feasible.
    """
    da_used: Dict[int, float] = {i: 0.0 for i in inst.depots}
    da_cap: Dict[int, float] = {i: d["cap"] for i, d in inst.depots.items()}

    candidates: List[Tuple[float, int, int]] = [
        (perfil["cost_ij"][(i, j)], i, j)
        for i, perfil in da_data.items()
        for j in perfil["clients"]
    ]
    candidates.sort()

    # distance lookup for repair priority (demote farthest DA first)
    assigned_dist: Dict[int, float] = {}
    assigned_depot: Dict[int, int] = {}
    assigned_clients: Set[int] = set()
    da_assigned: Dict[int, List[int]] = {i: [] for i in inst.depots}

    for dist, i, j in candidates:
        if j in assigned_clients:
            continue
        dj = inst.clients[j]["demand"]
        if da_used[i] + dj <= da_cap[i]:
            da_assigned[i].append(j)
            da_used[i] += dj
            assigned_clients.add(j)
            assigned_dist[j] = dist
            assigned_depot[j] = i

    routing_set: Set[int] = set(inst.clients.keys()) - assigned_clients

    if repair_routing_capacity and veh_cap is not None:
        veh_cap = int(veh_cap)
        while True:
            routing_demands = [int(inst.clients[j]["demand"]) for j in routing_set]
            routing_caps = _routing_vehicle_capacities(inst, da_assigned, veh_cap)
            if _can_pack_demands(routing_demands, routing_caps):
                break
            if not assigned_clients:
                break

            # Try single demotion that fixes packing. Prefer farthest DA client.
            da_candidates = sorted(
                assigned_clients,
                key=lambda j: (assigned_dist.get(j, 0.0), inst.clients[j]["demand"]),
                reverse=True,
            )
            chosen = da_candidates[0]
            for cand in da_candidates:
                dep = assigned_depot[cand]
                sim_da = {i: list(cs) for i, cs in da_assigned.items()}
                sim_da[dep].remove(cand)
                sim_routing = set(routing_set) | {cand}
                sim_demands = [int(inst.clients[j]["demand"]) for j in sim_routing]
                sim_caps = _routing_vehicle_capacities(inst, sim_da, veh_cap)
                if _can_pack_demands(sim_demands, sim_caps):
                    chosen = cand
                    break

            dep = assigned_depot[chosen]
            da_assigned[dep].remove(chosen)
            da_used[dep] -= inst.clients[chosen]["demand"]
            assigned_clients.remove(chosen)
            routing_set.add(chosen)

    return {i: cs for i, cs in da_assigned.items() if cs}, routing_set


__all__ = [
    "assign_da_clients",
    "build_direct_allocation_data",
    "compute_max_distance",
    "dist_euclid",
    "dist_manhattan",
]
