"""Ex-post objective reconstruction in C/MILP-comparable units (Phase 3).

Reconstructs the objective from parsed semantic decisions using *continuous
scaled* geometry — never the PyVRP integer objective. Mixed units (settled
decision #15): routing and DA costs use scaled distances; vehicle and depot
fixed costs are raw. Never divide by ``scale``.

    Z = Cost_Routing(scaled) + Cost_Direct_All(scaled)
        + Cost_Vehicles(raw)  + Cost_Depots(raw)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set

RELAXATION_DEVIATION = "RELAXATION_DEVIATION"
GAP = "GAP"
NEGATIVE_GAP = "NEGATIVE_GAP_MODELING_INCONSISTENCY"


@dataclass(frozen=True)
class CostBreakdown:
    cost_routing: float  # sum(F_R * scaled routing route distance)
    cost_direct_all: float  # sum(F_A * dist_scaled(depot, client))
    cost_vehicles: float  # used routing routes * veh_fixed * VFX (raw)
    cost_depots: float  # selected depot/sizing fixed cost (raw)
    total: float
    n_used_routing_routes: int


def reconstruct_cost(parsed, instance, config, facility_design) -> CostBreakdown:
    cost_routing = sum(r.reconstructed_weighted_cost for r in parsed.routes)
    cost_direct_all = sum(a.cost for a in parsed.da_assignments)

    n_used = len(parsed.routes)
    veh_fixed = float(instance.vehicle_fixed_cost) * float(config.VFX)
    cost_vehicles = n_used * veh_fixed  # raw units

    cost_depots = float(facility_design.total_cost)  # raw units

    total = cost_routing + cost_direct_all + cost_vehicles + cost_depots
    return CostBreakdown(
        cost_routing=cost_routing, cost_direct_all=cost_direct_all,
        cost_vehicles=cost_vehicles, cost_depots=cost_depots, total=total,
        n_used_routing_routes=n_used,
    )


@dataclass(frozen=True)
class ComparisonMetric:
    label: str  # RELAXATION_DEVIATION | GAP
    value: Optional[float]
    z_pyvrp: float
    ub_milp: Optional[float]
    fully_feasible: bool
    flags: frozenset  # may contain NEGATIVE_GAP_MODELING_INCONSISTENCY


def comparison_metric(
    z_pyvrp: float,
    ub_milp: Optional[float],
    fully_feasible: bool,
    *,
    negative_gap_tol: float = 1e-4,
) -> ComparisonMetric:
    """Pick the correct label/value (spec §15).

    Relaxed/infeasible -> RELAXATION_DEVIATION = (UB - Z)/UB.
    Fully feasible      -> GAP = (Z - UB)/UB; flag NEGATIVE_GAP if Z materially
    below UB. ``negative_gap_tol`` (relative) absorbs Excel UB rounding (UB is
    stored to 3 decimals), so a rounding-level negative gap does not flag a
    spurious modeling inconsistency.
    """
    flags: Set[str] = set()
    if ub_milp is None or ub_milp == 0:
        return ComparisonMetric(GAP if fully_feasible else RELAXATION_DEVIATION,
                                None, z_pyvrp, ub_milp, fully_feasible, frozenset(flags))

    if not fully_feasible:
        value = (ub_milp - z_pyvrp) / ub_milp
        return ComparisonMetric(RELAXATION_DEVIATION, value, z_pyvrp, ub_milp, False, frozenset(flags))

    value = (z_pyvrp - ub_milp) / ub_milp
    if value < -negative_gap_tol:
        flags.add(NEGATIVE_GAP)
    return ComparisonMetric(GAP, value, z_pyvrp, ub_milp, True, frozenset(flags))


__all__ = [
    "RELAXATION_DEVIATION",
    "GAP",
    "NEGATIVE_GAP",
    "CostBreakdown",
    "reconstruct_cost",
    "ComparisonMetric",
    "comparison_metric",
]
