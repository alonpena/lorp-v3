"""Route + solution feasibility audit against C/MILP constraints (Phase 3).

Checks (spec §7): clients served exactly once, route capacity, route length
(scaled), DA radius, DA binding, aggregate depot capacity, and a
penalty-distance diagnostic. Combines into a single ``fully_feasible`` verdict
used to pick the comparison metric (GAP vs RELAXATION_DEVIATION).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Set, Tuple

PENALTY_DISTANCE_SUSPECTED = "PENALTY_DISTANCE_SUSPECTED"

# small tolerance for scaled length comparisons (PyVRP integerization granularity)
_LENGTH_TOL = 1.0 / 1000.0


def penalty_distance_threshold(length: float) -> float:
    """Spec §7: ``max(1_000_000, 1000 * Length)`` in scaled units."""
    return max(1_000_000.0, 1000.0 * float(length))


@dataclass
class FeasibilityReport:
    served_exactly_once: bool
    missing_clients: Set[int]
    duplicate_clients: Set[int]
    route_capacity_violations: List[Tuple[int, float, int]]  # (depot, demand, capacity)
    route_length_violations: List[Tuple[int, float, float]]  # (depot, scaled_dist, Length)
    da_radius_violations: List[Tuple[int, int, float]]  # (depot, client, dist_scaled)
    binding_violations: int
    penalty_distance_suspected: bool
    capacity_feasible: bool
    fully_feasible: bool
    flags: Set[str] = field(default_factory=set)
    iteration: int = 0


def audit_feasibility(parsed, capacity_audit, instance, config, geometry, *, iteration: int = 0) -> FeasibilityReport:
    Length = float(config.Length)
    R = float(config.R)
    threshold = penalty_distance_threshold(Length)

    flags: Set[str] = set(parsed.flags)

    route_cap_viol: List[Tuple[int, float, int]] = []
    route_len_viol: List[Tuple[int, float, float]] = []
    penalty = False

    for r in parsed.routes:
        if r.demand > r.capacity:
            route_cap_viol.append((r.depot_id, r.demand, r.capacity))
        if r.reconstructed_scaled_distance > Length + _LENGTH_TOL:
            route_len_viol.append((r.depot_id, r.reconstructed_scaled_distance, Length))
        if r.solver_distance_scaled > threshold:
            penalty = True
    if penalty:
        flags.add(PENALTY_DISTANCE_SUSPECTED)

    da_radius_viol: List[Tuple[int, int, float]] = [
        (a.depot_id, a.client_id, a.dist_scaled) for a in parsed.da_assignments if a.dist_scaled > R
    ]

    served_once = parsed.served_exactly_once
    cap_feasible = capacity_audit.capacity_feasible
    binding_viol = len(parsed.binding_violations)

    fully_feasible = (
        served_once
        and cap_feasible
        and not route_cap_viol
        and not route_len_viol
        and not da_radius_viol
        and binding_viol == 0
        and not penalty
    )

    return FeasibilityReport(
        served_exactly_once=served_once,
        missing_clients=set(parsed.missing_clients),
        duplicate_clients=set(parsed.duplicate_clients),
        route_capacity_violations=route_cap_viol,
        route_length_violations=route_len_viol,
        da_radius_violations=da_radius_viol,
        binding_violations=binding_viol,
        penalty_distance_suspected=penalty,
        capacity_feasible=cap_feasible,
        fully_feasible=fully_feasible,
        flags=flags,
        iteration=iteration,
    )


def client_has_service_option(client_id, active_depots, geometry, R, forbidden_routing_assignments) -> bool:
    """Does ``client_id`` still have at least one feasible service option?

    Spec §10: a client is serviceable if it can be routed from some non-forbidden
    depot OR direct-allocated from some depot within the scaled radius ``R``.
    Used to skip repair removals that would strand a client.
    """
    has_routing = any((h, client_id) not in forbidden_routing_assignments for h in active_depots)
    has_da = any(geometry.depot_client_scaled(h, client_id) <= R for h in active_depots)
    return has_routing or has_da


def client_has_length_feasible_service_option(
    client_id,
    active_depots,
    geometry,
    R,
    Length,
    forbidden_routing_assignments,
) -> bool:
    """Does ``client_id`` have a DA or singleton length-feasible routing option?

    Phase 7A safety check. DA is feasible when ``dist_scaled(h, j) <= R``.
    Routing is considered safe only when the singleton route from depot ``h``
    remains allowed and satisfies ``2 * dist_scaled(h, j) <= Length``. This is a
    sufficient serviceability safety check before forbidding a routing assignment.
    """
    has_da = any(geometry.depot_client_scaled(h, client_id) <= R for h in active_depots)
    has_singleton_routing = any(
        (h, client_id) not in forbidden_routing_assignments
        and 2.0 * geometry.depot_client_scaled(h, client_id) <= Length
        for h in active_depots
    )
    return has_da or has_singleton_routing


def make_feasibility_checker(active_depots, geometry, R):
    """Bind ``active_depots``/``geometry``/``R`` into a ``(client_id, forbidden) -> bool`` checker."""
    active = tuple(active_depots)

    def check(client_id, forbidden_routing_assignments) -> bool:
        return client_has_service_option(client_id, active, geometry, R, forbidden_routing_assignments)

    return check


__all__ = [
    "PENALTY_DISTANCE_SUSPECTED",
    "penalty_distance_threshold",
    "FeasibilityReport",
    "audit_feasibility",
    "client_has_service_option",
    "client_has_length_feasible_service_option",
    "make_feasibility_checker",
]
