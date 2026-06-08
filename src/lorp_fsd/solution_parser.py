"""Parse a PyVRP solution into semantic routing/DA records (Phase 3).

Uses :class:`~lorp_fsd.pyvrp_builder.BuildInfo` / ``VehicleTypeMeta`` to recover,
for every non-empty route: service mode, depot, client sequence, demand, the
solver's (integerized) distance, and a continuous-scaled geometric
reconstruction. DA routes are checked for single-client binding
(``DA_ASSIGNMENT_BINDING_VIOLATION``).

Reconstruction uses continuous scaled geometry, not the PyVRP integer objective.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from .scaling import PYVRP_INT_SCALE

DA_BINDING_VIOLATION = "DA_ASSIGNMENT_BINDING_VIOLATION"


@dataclass(frozen=True)
class RouteRecord:
    vehicle_type_index: int
    mode: str  # "routing" | "direct_allocation"
    depot_id: int
    capacity: int  # vehicle-type capacity (for load checks)
    client_sequence: Tuple[int, ...]
    demand: float
    solver_distance_int: int  # route.distance() (geometric, integerized)
    solver_distance_scaled: float  # solver_distance_int / PYVRP_INT_SCALE
    reconstructed_scaled_distance: float  # from geometry (authoritative)
    reconstructed_weighted_cost: float  # F * reconstructed_scaled_distance


@dataclass(frozen=True)
class DAAssignmentRecord:
    depot_id: int
    client_id: int
    demand: float
    dist_scaled: float
    cost: float  # F_A * dist_scaled (one-way only)
    binding_ok: bool
    violation_reason: Optional[str] = None


@dataclass
class ParsedSolution:
    routes: List[RouteRecord]  # routing routes only
    da_assignments: List[DAAssignmentRecord]
    service_by_client: Dict[int, str]
    missing_clients: Set[int]
    duplicate_clients: Set[int]
    binding_violations: List[DAAssignmentRecord]
    solver_feasible: bool
    flags: Set[str] = field(default_factory=set)
    iteration: int = 0

    @property
    def served_exactly_once(self) -> bool:
        return not self.missing_clients and not self.duplicate_clients

    @property
    def n_routing_routes(self) -> int:
        return len(self.routes)

    @property
    def n_da_assignments(self) -> int:
        return len(self.da_assignments)


def parse_solution(result, model, info, instance, geometry, config, *, iteration: int = 0) -> ParsedSolution:
    best = result.best
    loc_names = [loc.name for loc in model.locations]

    def client_id_of(loc_index: int) -> int:
        name = loc_names[loc_index]
        if not name.startswith("c"):
            raise ValueError(f"expected a client location, got {name!r}")
        return int(name[1:])

    F_R = float(config.F_R)
    F_A = float(config.F_A)
    R = float(config.R)

    routes: List[RouteRecord] = []
    da_assignments: List[DAAssignmentRecord] = []
    binding_violations: List[DAAssignmentRecord] = []
    flags: Set[str] = set()

    for route in best.routes():
        visits = list(route.visits())
        if not visits:
            continue
        meta = info.vehicle_type_meta[route.vehicle_type()]
        depot_id = meta.depot_id
        seq = tuple(client_id_of(i) for i in visits)

        solver_dist_int = int(route.distance())
        solver_dist_scaled = solver_dist_int / PYVRP_INT_SCALE

        if meta.mode == "routing":
            depot_xy = instance.depot_xy(depot_id)
            pts = [depot_xy] + [instance.client_xy(c) for c in seq] + [depot_xy]
            recon = sum(geometry.dist_scaled(pts[k], pts[k + 1]) for k in range(len(pts) - 1))
            demand = sum(instance.clients[c].demand for c in seq)
            routes.append(RouteRecord(
                vehicle_type_index=route.vehicle_type(), mode="routing",
                depot_id=depot_id, capacity=meta.capacity, client_sequence=seq,
                demand=demand, solver_distance_int=solver_dist_int,
                solver_distance_scaled=solver_dist_scaled,
                reconstructed_scaled_distance=recon,
                reconstructed_weighted_cost=F_R * recon,
            ))
        else:  # direct_allocation
            bound = meta.client_id
            reason = None
            if len(seq) != 1:
                reason = f"DA route serves {len(seq)} clients (expected 1)"
            elif seq[0] != bound:
                reason = f"DA route serves client {seq[0]} but is bound to {bound}"
            cid = seq[0] if seq else bound
            ds = geometry.depot_client_scaled(depot_id, cid)
            if reason is None and ds > R:
                reason = f"DA dist_scaled {ds:.4f} exceeds R={R}"
            rec = DAAssignmentRecord(
                depot_id=depot_id, client_id=cid,
                demand=instance.clients[cid].demand, dist_scaled=ds,
                cost=F_A * ds, binding_ok=(reason is None), violation_reason=reason,
            )
            da_assignments.append(rec)
            if reason is not None:
                binding_violations.append(rec)
                flags.add(DA_BINDING_VIOLATION)

    # service map + multiplicity (built from records, robust to the routing loop)
    service_by_client: Dict[int, str] = {}
    served_count = {}
    for r in routes:
        for cid in r.client_sequence:
            served_count[cid] = served_count.get(cid, 0) + 1
            service_by_client[cid] = "routing"
    for a in da_assignments:
        served_count[a.client_id] = served_count.get(a.client_id, 0) + 1
        service_by_client.setdefault(a.client_id, "direct_allocation")

    all_clients = set(instance.clients)
    missing = {c for c in all_clients if served_count.get(c, 0) == 0}
    duplicate = {c for c, n in served_count.items() if n > 1}

    return ParsedSolution(
        routes=routes, da_assignments=da_assignments,
        service_by_client=service_by_client, missing_clients=missing,
        duplicate_clients=duplicate, binding_violations=binding_violations,
        solver_feasible=bool(best.is_feasible()), flags=flags, iteration=iteration,
    )


__all__ = [
    "DA_BINDING_VIOLATION",
    "RouteRecord",
    "DAAssignmentRecord",
    "ParsedSolution",
    "parse_solution",
]
