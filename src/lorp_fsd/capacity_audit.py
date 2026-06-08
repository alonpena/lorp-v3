"""Aggregate depot-capacity audit (Phase 3).

C/MILP depot capacity is shared by routing and DA (audit §5):

    demand_routing_i + demand_DA_i <= Cap_i

This audit reconstructs per-depot routing demand, DA demand, total, and excess
from the parsed solution. (Reminder: moving a client from routing to DA at the
*same* depot does not reduce ``demand_total_i``.)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class DepotAuditRecord:
    depot_id: int
    demand_routing: float
    demand_da: float
    demand_total: float
    capacity: float
    excess: float


@dataclass
class CapacityAudit:
    by_depot: Dict[int, DepotAuditRecord]
    capacity_feasible: bool
    total_excess: float
    iteration: int = 0

    @property
    def overloaded_depots(self) -> List[int]:
        return [i for i, r in self.by_depot.items() if r.excess > 0]


def audit_capacity(parsed, facility_design, *, iteration: int = 0) -> CapacityAudit:
    routing_by_depot: Dict[int, float] = {}
    da_by_depot: Dict[int, float] = {}

    for r in parsed.routes:
        routing_by_depot[r.depot_id] = routing_by_depot.get(r.depot_id, 0.0) + r.demand
    for a in parsed.da_assignments:
        da_by_depot[a.depot_id] = da_by_depot.get(a.depot_id, 0.0) + a.demand

    by_depot: Dict[int, DepotAuditRecord] = {}
    total_excess = 0.0
    for depot_id in facility_design.active_depot_ids:
        dr = routing_by_depot.get(depot_id, 0.0)
        dd = da_by_depot.get(depot_id, 0.0)
        total = dr + dd
        cap = facility_design.depots[depot_id].capacity
        excess = max(0.0, total - cap)
        total_excess += excess
        by_depot[depot_id] = DepotAuditRecord(
            depot_id=depot_id, demand_routing=dr, demand_da=dd,
            demand_total=total, capacity=cap, excess=excess,
        )

    return CapacityAudit(
        by_depot=by_depot,
        capacity_feasible=(total_excess == 0.0),
        total_excess=total_excess,
        iteration=iteration,
    )


__all__ = ["DepotAuditRecord", "CapacityAudit", "audit_capacity"]
