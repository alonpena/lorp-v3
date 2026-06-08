"""Capacity-relaxed PyVRP builder (Phase 2).

Builds the first-pass / rebuildable PyVRP model for one Excel row under a fixed
facility design. The model is *capacity-relaxed*: each open depot gets routing
vehicles totalling ~``Cap_i`` AND independent DA options, so the aggregate
``routing + DA`` demand can exceed ``Cap_i`` (the shared depot-capacity
constraint that PyVRP cannot model natively). The repair loop (Phase 4) claws
this back; Phase 2 only constructs.

Encoding (settled decisions #13/#14, spec §1/§6):

- **distance channel** = ``round(dist_scaled * PYVRP_INT_SCALE)`` (geometry) —
  drives the route-length limit ``max_distance = round(Length * PYVRP_INT_SCALE)``.
- **duration channel** = weighted cost ``round(F * dist_scaled * PYVRP_INT_SCALE)``
  (``F_R`` routing, ``F_A`` DA outbound, ``0`` DA return) with
  ``unit_distance_cost = 0`` and ``unit_duration_cost = 1``.
- Routing: one profile per open depot; clients in
  ``forbidden_routing_assignments`` get no routing edge (unreachable) — this does
  NOT remove their DA reachability.
- DA: one profile per ``(depot, client)`` option with exactly two edges
  (out cost, return 0) → the DA vehicle can serve only that client.

This module does not parse solutions, audit, repair, plot, or batch.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

from .da_options import DAOption, build_da_options
from .scaling import PYVRP_INT_SCALE, SUPPORTED_PROBLEM_ID

try:  # isolate the optional pyvrp dependency
    from pyvrp import Model
except Exception:  # pragma: no cover
    Model = Any  # type: ignore[assignment]


def _require_pyvrp() -> None:
    if Model is Any:
        raise ImportError("pyvrp not installed. Run `uv sync`.")


ForbiddenRoutingAssignments = FrozenSet[Tuple[int, int]]


@dataclass(frozen=True)
class RoutingVehicleSpec:
    depot_id: int
    capacity: int
    num_available: int
    kind: str  # "full" | "residual"


@dataclass(frozen=True)
class VehicleTypeMeta:
    """Maps a PyVRP vehicle-type index back to its semantic role (for Phase 3)."""

    index: int
    mode: str  # "routing" | "direct_allocation"
    depot_id: int
    capacity: int
    num_available: int
    client_id: Optional[int] = None  # DA only: the single bound client
    kind: Optional[str] = None  # routing only: "full" | "residual"
    profile_name: str = ""


@dataclass
class BuildInfo:
    """Everything Phase 3 needs to interpret the model and audit it."""

    # parameters / scaling
    F_R: float
    F_A: float
    R: float
    Length: float
    scale: float
    max_dist: float
    int_scale: int
    route_max_distance_int: int

    # design
    active_depot_ids: Tuple[int, ...]
    capacity_by_depot: Dict[int, float]
    vehicle_capacity: int

    # construction
    routing_vehicles: List[RoutingVehicleSpec]
    da_options: List[DAOption]
    forbidden_routing_assignments: ForbiddenRoutingAssignments
    vehicle_type_meta: List[VehicleTypeMeta]

    # reachability helpers (for tests / feasibility)
    routing_reachable: Dict[int, Set[int]] = field(default_factory=dict)
    da_pairs: Set[Tuple[int, int]] = field(default_factory=set)

    # pyvrp handles (opaque to callers; used by later phases)
    depot_nodes: Dict[int, Any] = field(default_factory=dict)
    client_nodes: Dict[int, Any] = field(default_factory=dict)

    @property
    def n_routing_vehicles(self) -> int:
        return sum(v.num_available for v in self.routing_vehicles)

    def routing_capacity(self, depot_id: int) -> int:
        return sum(v.capacity * v.num_available for v in self.routing_vehicles if v.depot_id == depot_id)


def routing_vehicle_specs(cap_i: float, vehicle_capacity: int, depot_id: int) -> List[RoutingVehicleSpec]:
    """Decompose ``Cap_i`` into ``floor(Cap_i / Q)`` full vehicles + one residual.

    Integer arithmetic keeps total routing capacity ``<= Cap_i`` (fractional
    capacities from sizes 2/4 are floored).
    """
    cap_int = int(math.floor(cap_i))
    q = int(vehicle_capacity)
    n_full = cap_int // q
    residual = cap_int - n_full * q

    specs: List[RoutingVehicleSpec] = []
    if n_full > 0:
        specs.append(RoutingVehicleSpec(depot_id, q, n_full, "full"))
    if residual > 0:
        specs.append(RoutingVehicleSpec(depot_id, residual, 1, "residual"))
    return specs


def build_relaxed_model(
    instance,
    config,
    geometry,
    facility_design,
    forbidden_routing_assignments: ForbiddenRoutingAssignments = frozenset(),
) -> Tuple[Any, BuildInfo]:
    """Construct the capacity-relaxed PyVRP model + :class:`BuildInfo`."""
    _require_pyvrp()
    if config.problem_id != SUPPORTED_PROBLEM_ID:
        raise NotImplementedError("LoRP-v3 currently supports only problemID=0 Arslan scaling.")

    forbidden: ForbiddenRoutingAssignments = frozenset(forbidden_routing_assignments)
    F_R = float(config.F_R)
    F_A = float(config.F_A)
    Q = int(instance.vehicle_capacity)
    route_max_distance_int = round(float(config.Length) * PYVRP_INT_SCALE)
    veh_fixed_int = round(float(instance.vehicle_fixed_cost) * float(config.VFX) * PYVRP_INT_SCALE)

    m = Model()

    # Nodes: open depots + all clients (clients required → served exactly once).
    depot_nodes: Dict[int, Any] = {
        i: m.add_depot(x=instance.depots[i].x, y=instance.depots[i].y, name=f"d{i}")
        for i in facility_design.active_depot_ids
    }
    client_nodes: Dict[int, Any] = {
        j: m.add_client(x=c.x, y=c.y, delivery=int(c.demand), required=True, name=f"c{j}")
        for j, c in instance.clients.items()
    }

    def dur(a_xy, b_xy, weight: float) -> int:
        return round(weight * geometry.dist_scaled(a_xy, b_xy) * PYVRP_INT_SCALE)

    routing_vehicles: List[RoutingVehicleSpec] = []
    vehicle_meta: List[VehicleTypeMeta] = []
    routing_reachable: Dict[int, Set[int]] = {}
    vt_index = 0

    # ── Routing: one profile per open depot, forbidden pairs excluded ─────────
    for depot_id in facility_design.active_depot_ids:
        prof = m.add_profile(name=f"routing_d{depot_id}")
        depot_node = depot_nodes[depot_id]
        depot_xy = instance.depot_xy(depot_id)

        allowed = [j for j in instance.clients if (depot_id, j) not in forbidden]
        routing_reachable[depot_id] = set(allowed)

        # depot <-> allowed client (dual-channel)
        for j in allowed:
            cj = client_nodes[j]
            cj_xy = instance.client_xy(j)
            d_int = geometry.dist_scaled_int(depot_xy, cj_xy)
            m.add_edge(depot_node, cj, distance=d_int, duration=dur(depot_xy, cj_xy, F_R), profile=prof)
            m.add_edge(cj, depot_node, distance=d_int, duration=dur(cj_xy, depot_xy, F_R), profile=prof)

        # client <-> client among allowed
        for a in allowed:
            ca = client_nodes[a]
            a_xy = instance.client_xy(a)
            for b in allowed:
                if a == b:
                    continue
                cb = client_nodes[b]
                b_xy = instance.client_xy(b)
                m.add_edge(ca, cb, distance=geometry.dist_scaled_int(a_xy, b_xy),
                           duration=dur(a_xy, b_xy, F_R), profile=prof)

        specs = routing_vehicle_specs(facility_design.depots[depot_id].capacity, Q, depot_id)
        routing_vehicles.extend(specs)
        for spec in specs:
            m.add_vehicle_type(
                num_available=spec.num_available,
                capacity=spec.capacity,
                start_depot=depot_node,
                end_depot=depot_node,
                fixed_cost=veh_fixed_int,
                max_distance=route_max_distance_int,
                unit_distance_cost=0,
                unit_duration_cost=1,
                profile=prof,
                name=f"route_d{depot_id}_{spec.kind}",
            )
            vehicle_meta.append(VehicleTypeMeta(
                index=vt_index, mode="routing", depot_id=depot_id,
                capacity=spec.capacity, num_available=spec.num_available,
                kind=spec.kind, profile_name=f"routing_d{depot_id}",
            ))
            vt_index += 1

    # ── DA: one profile per (depot, client) option, single 1:1 vehicle ────────
    da_options: List[DAOption] = build_da_options(instance, config, geometry, facility_design)
    for opt in da_options:
        depot_node = depot_nodes[opt.depot_id]
        cj = client_nodes[opt.client_id]
        depot_xy = instance.depot_xy(opt.depot_id)
        cj_xy = instance.client_xy(opt.client_id)

        prof = m.add_profile(name=f"da_d{opt.depot_id}_c{opt.client_id}")
        # outbound: geometric distance + weighted one-way cost; return: zero cost
        m.add_edge(depot_node, cj, distance=geometry.dist_scaled_int(depot_xy, cj_xy),
                   duration=opt.cost_int, profile=prof)
        m.add_edge(cj, depot_node, distance=0, duration=0, profile=prof)

        m.add_vehicle_type(
            num_available=1,
            capacity=int(opt.demand),
            start_depot=depot_node,
            end_depot=depot_node,
            fixed_cost=0,
            unit_distance_cost=0,
            unit_duration_cost=1,
            profile=prof,
            name=f"da_d{opt.depot_id}_c{opt.client_id}",
        )
        vehicle_meta.append(VehicleTypeMeta(
            index=vt_index, mode="direct_allocation", depot_id=opt.depot_id,
            capacity=int(opt.demand), num_available=1, client_id=opt.client_id,
            profile_name=f"da_d{opt.depot_id}_c{opt.client_id}",
        ))
        vt_index += 1

    info = BuildInfo(
        F_R=F_R, F_A=F_A, R=float(config.R), Length=float(config.Length),
        scale=geometry.scale, max_dist=geometry.max_dist,
        int_scale=PYVRP_INT_SCALE, route_max_distance_int=route_max_distance_int,
        active_depot_ids=facility_design.active_depot_ids,
        capacity_by_depot=facility_design.capacity_by_depot,
        vehicle_capacity=Q,
        routing_vehicles=routing_vehicles,
        da_options=da_options,
        forbidden_routing_assignments=forbidden,
        vehicle_type_meta=vehicle_meta,
        routing_reachable=routing_reachable,
        da_pairs={o.pair for o in da_options},
        depot_nodes=depot_nodes,
        client_nodes=client_nodes,
    )
    return m, info


__all__ = [
    "ForbiddenRoutingAssignments",
    "RoutingVehicleSpec",
    "VehicleTypeMeta",
    "BuildInfo",
    "routing_vehicle_specs",
    "build_relaxed_model",
]
