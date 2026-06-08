"""Direct Allocation (DA) option construction.

A DA option is a one-way, single-client, zero-return assignment of a client to an
open depot within the (scaled) coverage radius ``R`` (C audit §4, spec §6). It is
NOT a route: no client–client travel, no multitrip, no fixed vehicle cost.

DA feasibility uses *continuous* ``dist_scaled`` (never integerized):

    DA_feasible(i, j)  <=>  dist_scaled(i, j) <= R

Each option carries an integerized one-way cost for the PyVRP cost channel:

    cost_int = round(F_A * dist_scaled(i, j) * PYVRP_INT_SCALE)

Binding: an option ``(i, j)`` may serve *only* client ``j`` — enforced in the
builder via a per-pair profile, and re-checkable in Phase 3 audit
(``DA_ASSIGNMENT_BINDING_VIOLATION``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Set, Tuple

from .scaling import PYVRP_INT_SCALE


@dataclass(frozen=True)
class DAOption:
    depot_id: int
    client_id: int
    demand: int
    dist_scaled: float
    cost_int: int  # round(F_A * dist_scaled * PYVRP_INT_SCALE), one-way only

    @property
    def pair(self) -> Tuple[int, int]:
        return (self.depot_id, self.client_id)


def build_da_options(instance, config, geometry, facility_design) -> List[DAOption]:
    """Build all feasible DA options over the *open* depots.

    Feasible pairs are ``dist_scaled(i, j) <= R`` for active depot ``i`` and every
    client ``j``. Independent of any forbidden routing assignments.
    """
    R = float(config.R)
    F_A = float(config.F_A)

    options: List[DAOption] = []
    for depot_id in facility_design.active_depot_ids:
        for client_id, client in instance.clients.items():
            ds = geometry.depot_client_scaled(depot_id, client_id)
            if ds <= R:
                options.append(
                    DAOption(
                        depot_id=depot_id,
                        client_id=client_id,
                        demand=int(client.demand),
                        dist_scaled=ds,
                        cost_int=round(F_A * ds * PYVRP_INT_SCALE),
                    )
                )
    return options


def da_pairs(options: List[DAOption]) -> Set[Tuple[int, int]]:
    return {o.pair for o in options}


def da_options_by_depot(options: List[DAOption]) -> Dict[int, List[DAOption]]:
    out: Dict[int, List[DAOption]] = {}
    for o in options:
        out.setdefault(o.depot_id, []).append(o)
    return out


def clients_with_da(options: List[DAOption]) -> Set[int]:
    return {o.client_id for o in options}


__all__ = [
    "DAOption",
    "build_da_options",
    "da_pairs",
    "da_options_by_depot",
    "clients_with_da",
]
