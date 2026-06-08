"""PyVRP model construction and solving.

Isolates the pyvrp optional dependency. All pyvrp imports live here.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Set, Tuple

from da_candidate_pool import build_da_candidate_pool_with_stats
from da_geometry import (
    assign_da_clients,
    build_direct_allocation_data,
    compute_max_distance,
    dist_euclid,
)
from dat_loader import Instance

try:
    from pyvrp import Model
    from pyvrp.stop import MaxRuntime
except Exception:  # pragma: no cover
    Model = Any  # type: ignore[assignment]
    MaxRuntime = None  # type: ignore[assignment]


def _require_pyvrp() -> None:
    if Model is Any or MaxRuntime is None:
        raise ImportError("pyvrp not installed. Run `uv sync`.")


def build_full_model(inst: Instance) -> tuple[Any, dict]:
    _require_pyvrp()
    if not inst.depots:
        raise ValueError("Instance has no depots")
    if not inst.clients:
        raise ValueError("Instance has no clients")

    radio = float(inst.data["R"])
    cap_veh = int(inst.data["veh_cap"])
    length = float(inst.data["Length"])
    F_R = float(inst.data["F_R"])
    F_A = float(inst.data["F_A"])

    da_data, _ = build_direct_allocation_data(inst, radio)
    da_asignados, clientes_routing = assign_da_clients(inst, da_data, cap_veh)

    m = Model()
    prof_routing = m.add_profile(name="routing")
    prof_direct_alloc = m.add_profile(name="direct_allocation")

    depot_nodes = {i: m.add_depot(x=d["x"], y=d["y"]) for i, d in inst.depots.items()}
    client_nodes = {
        j: m.add_client(x=c["x"], y=c["y"], delivery=int(c["demand"]))
        for j, c in inst.clients.items()
    }

    max_dist = compute_max_distance(inst)
    escala = 100.0 / max_dist if max_dist > 0 else 1.0

    routing_nodes = {f"d{i}": node for i, node in depot_nodes.items()}
    routing_nodes.update({f"c{j}": client_nodes[j] for j in clientes_routing})

    items_routing = list(routing_nodes.items())
    for id_i, nodo_i in items_routing:
        for id_j, nodo_j in items_routing:
            if id_i == id_j:
                continue
            d = dist_euclid((nodo_i.x, nodo_i.y), (nodo_j.x, nodo_j.y))
            m.add_edge(nodo_i, nodo_j, distance=d * escala, profile=prof_routing)

    # ── DA edges + vehicles (1 vehicle per client, capacity = client demand) ──
    vehicle_types: List[Dict[str, Any]] = []

    for i, lista_clientes in da_asignados.items():
        node_dep = depot_nodes[i]
        xi, yi = inst.depots[i]["x"], inst.depots[i]["y"]
        for j in lista_clientes:
            node_cli = client_nodes[j]
            xj, yj = inst.clients[j]["x"], inst.clients[j]["y"]
            demand_j = int(inst.clients[j]["demand"])
            dist_ida = dist_euclid((xi, yi), (xj, yj))

            # edges only between this depot and this client — no inter-DA-client edges
            m.add_edge(node_dep, node_cli, distance=dist_ida * escala, profile=prof_direct_alloc)
            m.add_edge(node_cli, node_dep, distance=0.0, profile=prof_direct_alloc)

            # 1 vehicle, capacity exactly = client demand → forces 1:1 assignment
            m.add_vehicle_type(
                num_available=1,
                capacity=demand_j,
                start_depot=depot_nodes[i],
                end_depot=depot_nodes[i],
                profile=prof_direct_alloc,
            )
            vehicle_types.append({"type": "direct_allocation", "depot": i, "client": j})

    # ── routing vehicles: floor(remaining / Q) full + 1 residual if needed ──
    for i, d in inst.depots.items():
        da_demand_i = sum(inst.clients[j]["demand"] for j in da_asignados.get(i, []))
        cap_remaining = d["cap"] - da_demand_i

        n_veh = math.floor(cap_remaining / cap_veh)
        if n_veh > 0:
            m.add_vehicle_type(
                num_available=n_veh,
                capacity=cap_veh,
                start_depot=depot_nodes[i],
                end_depot=depot_nodes[i],
                max_distance=length,  # Length comes pre-scaled from Excel; do not apply escala again
                profile=prof_routing,
            )
            vehicle_types.append({"type": "routing", "depot": i, "num_available": n_veh})

        residual = int(cap_remaining) % cap_veh
        if residual > 0:
            m.add_vehicle_type(
                num_available=1,
                capacity=residual,
                start_depot=depot_nodes[i],
                end_depot=depot_nodes[i],
                max_distance=length,  # Length comes pre-scaled from Excel; do not apply escala again
                profile=prof_routing,
            )
            vehicle_types.append({"type": "routing", "depot": i, "num_available": 1, "residual_capacity": residual})

    info = {
        "da_data": da_data,
        "da_asignados": da_asignados,
        "clientes_routing": clientes_routing,
        "escala": escala,
        "max_distance": max_dist,
        "vehicle_types": vehicle_types,
        "tipos_veh": vehicle_types,
        "depot_nodes": depot_nodes,
        "nodos_deposito": depot_nodes,
        "client_nodes": client_nodes,
        "nodos_cliente": client_nodes,
        "locations": getattr(m, "locations", None),
        "profiles": {"routing": prof_routing, "direct_allocation": prof_direct_alloc},
    }
    return m, info


def solve_fast(m, runtime: int = 5, n_runs: int = 3):
    _require_pyvrp()
    best_res = None
    best_cost = float("inf")
    for seed in range(n_runs):
        res = m.solve(stop=MaxRuntime(runtime), seed=seed, display=False)
        cost = res.best.distance()
        if cost < best_cost:
            best_cost = cost
            best_res = res
    return best_res


# ── endogenous DA model + multi-run solver ────────────────────────────────────

def build_endogenous_da_model(
    inst: Instance,
    excluded_routing_pairs: Optional[Set[Tuple[int, int]]] = None,
    encode_cost_factors: bool = False,
) -> Tuple[Any, dict]:
    """Build a PyVRP model where DA-vs-routing mix is chosen by the solver.

    Differences vs build_full_model:
    - DA candidate pool per depot is a capacity-feasible subset of clients
      within Arslan-scaled radius R (see da_candidate_pool).
      The solver may or may not dispatch each DA candidate vehicle.
    - One routing profile per depot. Routing graph for depot d contains only
      edges among (depot_d) and (clients not in excluded_routing_pairs[d]).
    - One DA profile per (depot, client) candidate, with a single 1:1 vehicle.

    Cost-factor handling (encode_cost_factors):
    - False (default): edge distance = raw_dist * escala (unweighted). F_R/F_A
      are applied ex post in reporting. PyVRP objective is total scaled distance.
    - True: routing edge = raw * escala * F_R; DA edge = raw * escala * F_A.
      PyVRP objective is the weighted Arslan objective. Reporting still uses
      unweighted scaled distances reconstructed geometrically from the routes.

    DA vehicles use no max_distance; DA feasibility is governed by the scaled
    radius R, not the routing Length cap. Routing vehicles use max_distance=Length.

    PyVRP cannot enforce shared depot capacity between DA and routing. Real
    capacity is enforced ex post by audit + routing-only repair.
    """
    _require_pyvrp()
    if not inst.depots:
        raise ValueError("Instance has no depots")
    if not inst.clients:
        raise ValueError("Instance has no clients")

    excluded: Set[Tuple[int, int]] = set(excluded_routing_pairs or set())

    radio = float(inst.data["R"])
    cap_veh = int(inst.data["veh_cap"])
    length = float(inst.data["Length"])
    F_R = float(inst.data.get("F_R", 1.0))
    F_A = float(inst.data.get("F_A", 1.0))

    max_dist = compute_max_distance(inst)
    escala = 100.0 / max_dist if max_dist > 0 else 1.0

    routing_weight = F_R if encode_cost_factors else 1.0
    da_weight = F_A if encode_cost_factors else 1.0
    objective_mode = "weighted_scaled_distance" if encode_cost_factors else "scaled_distance"

    m = Model()

    depot_nodes: Dict[int, Any] = {}
    location_to_depot: Dict[int, int] = {}
    for did, d in inst.depots.items():
        node = m.add_depot(x=d["x"], y=d["y"])
        depot_nodes[did] = node
        location_to_depot[len(location_to_depot)] = did

    n_depots = len(depot_nodes)
    client_nodes: Dict[int, Any] = {}
    location_to_client: Dict[int, int] = {}
    for cid, c in inst.clients.items():
        node = m.add_client(x=c["x"], y=c["y"], delivery=int(c["demand"]))
        client_nodes[cid] = node
        location_to_client[n_depots + len(location_to_client)] = cid

    # DA candidate pool (capacity-feasibility filter, scaled-radius eligibility)
    da_pool, da_pool_stats = build_da_candidate_pool_with_stats(inst, radio, escala)

    vehicle_types: List[Dict[str, Any]] = []

    # ── routing: one profile per depot, allowed clients minus excluded pairs ──
    for did, depot in inst.depots.items():
        allowed = [cid for cid in inst.clients if (did, cid) not in excluded]
        prof = m.add_profile(name=f"routing_d{did}")

        depot_node = depot_nodes[did]
        allowed_nodes = [client_nodes[cid] for cid in allowed]
        xy_depot = (depot_node.x, depot_node.y)

        for cnode in allowed_nodes:
            xy_c = (cnode.x, cnode.y)
            d_dc = dist_euclid(xy_depot, xy_c) * escala * routing_weight
            m.add_edge(depot_node, cnode, distance=d_dc, profile=prof)
            m.add_edge(cnode, depot_node, distance=d_dc, profile=prof)

        for i in range(len(allowed_nodes)):
            ni = allowed_nodes[i]
            xy_i = (ni.x, ni.y)
            for j in range(len(allowed_nodes)):
                if i == j:
                    continue
                nj = allowed_nodes[j]
                xy_j = (nj.x, nj.y)
                d_ij = dist_euclid(xy_i, xy_j) * escala * routing_weight
                m.add_edge(ni, nj, distance=d_ij, profile=prof)

        cap_d = float(depot["cap"])
        n_full = int(math.floor(cap_d / cap_veh))
        residual = int(cap_d) % cap_veh

        if n_full > 0:
            m.add_vehicle_type(
                num_available=n_full,
                capacity=cap_veh,
                start_depot=depot_node,
                end_depot=depot_node,
                max_distance=length,
                profile=prof,
            )
            vehicle_types.append({"type": "routing", "depot": did, "num_available": n_full})

        if residual > 0:
            m.add_vehicle_type(
                num_available=1,
                capacity=residual,
                start_depot=depot_node,
                end_depot=depot_node,
                max_distance=length,
                profile=prof,
            )
            vehicle_types.append({
                "type": "routing", "depot": did, "num_available": 1,
                "residual_capacity": residual,
            })

    # ── DA: one profile per (depot, client) candidate, 1:1 vehicle ──
    # DA feasibility governed by scaled radius R, not routing Length.
    for did, depot in inst.depots.items():
        depot_node = depot_nodes[did]
        for cid in da_pool.get(did, []):
            cnode = client_nodes[cid]
            xy_depot = (depot_node.x, depot_node.y)
            xy_c = (cnode.x, cnode.y)
            d_dc = dist_euclid(xy_depot, xy_c) * escala * da_weight

            prof = m.add_profile(name=f"da_d{did}_c{cid}")
            m.add_edge(depot_node, cnode, distance=d_dc, profile=prof)
            m.add_edge(cnode, depot_node, distance=0.0, profile=prof)

            m.add_vehicle_type(
                num_available=1,
                capacity=int(inst.clients[cid]["demand"]),
                start_depot=depot_node,
                end_depot=depot_node,
                profile=prof,
                fixed_cost=0,
            )
            vehicle_types.append({
                "type": "direct_allocation",
                "depot": did,
                "client": cid,
                "num_available": 1,
            })

    info = {
        "da_pool": da_pool,
        "da_pool_stats": da_pool_stats,
        "excluded_routing_pairs": set(excluded),
        "escala": escala,
        "max_distance": max_dist,
        "F_R": F_R,
        "F_A": F_A,
        "encode_cost_factors": bool(encode_cost_factors),
        "objective_mode": objective_mode,
        "vehicle_types": vehicle_types,
        "tipos_veh": vehicle_types,
        "depot_nodes": depot_nodes,
        "client_nodes": client_nodes,
        "location_to_depot": location_to_depot,
        "location_to_client": location_to_client,
        "locations": getattr(m, "locations", None),
    }
    return m, info


def solve_multi_run(m, runtime: int = 30, n_runs: int = 5):
    """Solve with n_runs seeds; prefer feasible, return (best_res, per-run records).

    Selection rule:
    - If any seed produced a feasible best solution: pick min-distance among those.
    - Else pick min-distance infeasible. Each run record carries a
      `chosen_no_feasible_solution` flag set to True only on the final pick.
    """
    _require_pyvrp()
    records: List[Dict[str, Any]] = []
    feasible: List[Any] = []
    infeasible: List[Any] = []
    for seed in range(n_runs):
        res = m.solve(stop=MaxRuntime(runtime), seed=seed, display=False)
        cost = float(res.best.distance())
        is_feas = bool(res.best.is_feasible())
        records.append({
            "seed": seed,
            "objective_scaled": cost,
            "feasible": is_feas,
            "n_routes": len(res.best.routes()),
        })
        if is_feas:
            feasible.append((cost, res))
        else:
            infeasible.append((cost, res))

    if feasible:
        feasible.sort(key=lambda t: t[0])
        best_res = feasible[0][1]
        no_feasible = False
    else:
        infeasible.sort(key=lambda t: t[0])
        best_res = infeasible[0][1] if infeasible else None
        no_feasible = True

    for r in records:
        r["chosen_no_feasible_solution"] = no_feasible
    return best_res, records


__all__ = [
    "Model",
    "MaxRuntime",
    "build_full_model",
    "build_endogenous_da_model",
    "solve_fast",
    "solve_multi_run",
]
