"""Build the fixed facility design from an Excel row + parsed instance.

Phase 1 benchmarks routing/DA/service-mode behavior under the MILP-selected
facility design (spec §13). This module fixes the open depots, their selected
sizes, capacities, and opening costs (recomputed via the C formula and
cross-checked against Excel ``CapD*``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .experiment_config import ExperimentConfig
from .facility_sizing import size_capacity, size_cost


@dataclass(frozen=True)
class FacilityDesignDepot:
    depot_id: int
    size: int
    capacity: float  # recomputed via C formula
    cost: float  # recomputed via C formula (raw units)
    capacity_excel: float  # Excel CapD* for cross-check
    capacity_matches_excel: bool


@dataclass(frozen=True)
class FacilityDesign:
    depots: Dict[int, FacilityDesignDepot]

    @property
    def active_depot_ids(self) -> tuple[int, ...]:
        return tuple(sorted(self.depots))

    @property
    def total_cost(self) -> float:
        return sum(d.cost for d in self.depots.values())

    @property
    def capacity_by_depot(self) -> Dict[int, float]:
        return {i: d.capacity for i, d in self.depots.items()}

    def mismatches(self) -> List[int]:
        return [i for i, d in self.depots.items() if not d.capacity_matches_excel]


def build_facility_design(
    instance,
    config: ExperimentConfig,
    *,
    capacity_tol: float = 1e-6,
) -> FacilityDesign:
    """Construct the fixed facility design from Excel-selected depots/sizes.

    Capacities and costs are recomputed from the C sizing formula using the
    instance base capacities, and each capacity is cross-checked against the
    Excel ``CapD*`` value.
    """
    total_fixed = instance.total_fixed_cost
    n_depots = instance.n_depots

    design: Dict[int, FacilityDesignDepot] = {}
    for depot_id, sel in config.selected_depots.items():
        if depot_id not in instance.depots:
            raise ValueError(
                f"selected depot {depot_id} not present in instance {instance.name!r}"
            )
        depot = instance.depots[depot_id]
        cap = size_capacity(depot.base_capacity, sel.size)
        cost = size_cost(
            fixed_cost=depot.fixed_cost,
            base_capacity=depot.base_capacity,
            total_fixed=total_fixed,
            n_depots=n_depots,
            size=sel.size,
        )
        design[depot_id] = FacilityDesignDepot(
            depot_id=depot_id,
            size=sel.size,
            capacity=cap,
            cost=cost,
            capacity_excel=sel.capacity,
            capacity_matches_excel=abs(cap - sel.capacity) <= capacity_tol,
        )

    return FacilityDesign(depots=design)


__all__ = ["FacilityDesign", "FacilityDesignDepot", "build_facility_design"]
