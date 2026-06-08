"""C facility-sizing formula (LoRP-FSD, ``ReadData_sizing``).

For each depot ``i`` and output size ``s in {1..5}`` (C index ``j = s-1``):

    cap(i, s)  = base_QD_i * (1 + (-2 + (s-1)) * 0.25)
               = base_QD_i * (1 + (s - 3) * 0.25)
    cost(i, s) = fixed_i + ((cap(i, s) - base_QD_i) / (2 * base_QD_i)) * (totalfix / T)

where ``totalfix`` is the sum of depot fixed costs and ``T`` is the depot count.

These costs are in **raw** units (never scaled). Congruency: r40x5a-1 size 1 →
cap 875, cost 75; 4 open depots × 75 = 300 = Excel ``Cost (Depots)``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

FACILITY_SIZE_COUNT = 5

# Output size (1..5) -> capacity multiplier.
SIZE_MULTIPLIERS: Dict[int, float] = {s: 1.0 + (s - 3) * 0.25 for s in range(1, FACILITY_SIZE_COUNT + 1)}
# => {1: 0.50, 2: 0.75, 3: 1.00, 4: 1.25, 5: 1.50}


def _check_size(size: int) -> None:
    if size not in SIZE_MULTIPLIERS:
        raise ValueError(f"size must be in 1..{FACILITY_SIZE_COUNT}; got {size}")


def size_capacity(base_capacity: float, size: int) -> float:
    """Selected capacity for a depot at output ``size`` (1..5)."""
    _check_size(size)
    return base_capacity * SIZE_MULTIPLIERS[size]


def size_cost(
    fixed_cost: float,
    base_capacity: float,
    total_fixed: float,
    n_depots: int,
    size: int,
) -> float:
    """Depot opening cost for a depot at output ``size`` (1..5), in raw units."""
    _check_size(size)
    cap = size_capacity(base_capacity, size)
    return fixed_cost + ((cap - base_capacity) / (2.0 * base_capacity)) * (total_fixed / n_depots)


@dataclass(frozen=True)
class SizingCheck:
    depot_id: int
    size: int
    capacity_recomputed: float
    capacity_excel: float
    cost_recomputed: float
    capacity_match: bool


def validate_capacity(
    instance,
    depot_id: int,
    size: int,
    capacity_excel: float,
    *,
    tol: float = 1e-6,
) -> SizingCheck:
    """Recompute capacity/cost for a depot+size and compare against an Excel value."""
    depot = instance.depots[depot_id]
    cap = size_capacity(depot.base_capacity, size)
    cost = size_cost(
        fixed_cost=depot.fixed_cost,
        base_capacity=depot.base_capacity,
        total_fixed=instance.total_fixed_cost,
        n_depots=instance.n_depots,
        size=size,
    )
    return SizingCheck(
        depot_id=depot_id,
        size=size,
        capacity_recomputed=cap,
        capacity_excel=capacity_excel,
        cost_recomputed=cost,
        capacity_match=abs(cap - capacity_excel) <= tol,
    )


__all__ = [
    "FACILITY_SIZE_COUNT",
    "SIZE_MULTIPLIERS",
    "size_capacity",
    "size_cost",
    "SizingCheck",
    "validate_capacity",
]
