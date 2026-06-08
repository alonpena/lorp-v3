"""Repair-mode state: hard forbid vs soft penalty vs tabu penalty (Phase 9).

The savings repair in :mod:`lorp_fsd.repair` decides *which* routing pairs
``(depot_id, client_id)`` to act on. This module decides *how* the next graph
reacts to that decision:

* ``hard_forbid`` — legacy baseline: the routing pair is permanently removed
  from the rebuilt graph (the client gets no routing edge from that depot).
* ``soft_penalty`` — the routing pair stays feasible but a large penalty is
  added to the PyVRP *duration/cost* channel only, so the solver avoids it
  unless it is genuinely needed. Distance (route-length) is never touched.
* ``tabu_penalty`` (default operational mode) — soft penalty plus a tabu tenure:
  each penalised pair carries a countdown; when it expires the penalty is
  removed unless the pair is re-selected, so the search is not permanently
  biased.

Cost reconstruction is unaffected: the reported ``Z_PyVRP`` is rebuilt from
semantic geometry (see :mod:`lorp_fsd.cost_reconstruction` /
:mod:`lorp_fsd.solution_parser`), never from the penalised PyVRP objective.

Limitation: the tabu is a simple per-pair countdown with no aspiration
criterion. A pair whose penalty expires can be re-selected on a later
iteration; there is no long-term memory beyond the active tenure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

Pair = Tuple[int, int]

REPAIR_MODE_HARD_FORBID = "hard_forbid"
REPAIR_MODE_SOFT_PENALTY = "soft_penalty"
REPAIR_MODE_TABU_PENALTY = "tabu_penalty"
REPAIR_MODES = {
    REPAIR_MODE_HARD_FORBID,
    REPAIR_MODE_SOFT_PENALTY,
    REPAIR_MODE_TABU_PENALTY,
}
DEFAULT_REPAIR_MODE = REPAIR_MODE_TABU_PENALTY

# trace action vocabulary (in addition to the legacy selected/rejected)
ACTION_HARD_FORBID = "hard_forbid"
ACTION_SOFT_PENALTY = "soft_penalty"
ACTION_TABU_ADD = "tabu_add"
ACTION_TABU_EXPIRE = "tabu_expire"


@dataclass
class RepairModeState:
    """Tracks forbidden pairs, active penalties, and tabu tenure across iterations."""

    mode: str = DEFAULT_REPAIR_MODE
    penalty_value: int = 0
    tabu_tenure: int = 3

    forbidden: Set[Pair] = field(default_factory=set)  # hard_forbid only
    penalty: Dict[Pair, int] = field(default_factory=dict)  # soft/tabu active penalties
    tabu: Dict[Pair, int] = field(default_factory=dict)  # tabu remaining tenure
    events: List[dict] = field(default_factory=list)  # repair_trace event rows

    def __post_init__(self) -> None:
        if self.mode not in REPAIR_MODES:
            raise ValueError(
                f"unknown repair_mode {self.mode!r}; expected one of {sorted(REPAIR_MODES)}"
            )

    @property
    def is_hard(self) -> bool:
        return self.mode == REPAIR_MODE_HARD_FORBID

    def suppressed_pairs(self) -> Set[Pair]:
        """Pairs the savings selector should not re-pick this iteration.

        For ``hard_forbid`` these are the permanently removed pairs; for the
        penalty modes these are the pairs that currently carry an active
        penalty.
        """
        return set(self.forbidden) | set(self.penalty)

    def builder_args(self) -> Tuple[frozenset, Optional[Dict[Pair, int]]]:
        """Return ``(forbidden_routing_assignments, penalty_routing_assignments)``.

        ``hard_forbid`` removes pairs (penalty ``None``); the penalty modes keep
        every pair feasible and only pass the penalty dict.
        """
        if self.is_hard:
            return frozenset(self.forbidden), None
        return frozenset(), dict(self.penalty)

    def tick(self, iteration: int) -> None:
        """Decrement tabu tenure and expire penalties that reach zero."""
        if self.mode != REPAIR_MODE_TABU_PENALTY:
            return
        expired: List[Pair] = []
        for pair in list(self.tabu):
            self.tabu[pair] -= 1
            if self.tabu[pair] <= 0:
                expired.append(pair)
        for pair in expired:
            del self.tabu[pair]
            self.penalty.pop(pair, None)
            self.events.append({
                "iteration": iteration,
                "action": ACTION_TABU_EXPIRE,
                "depot_id": pair[0],
                "client_id": pair[1],
                "penalty_value": "",
                "tabu_remaining": 0,
                "saving": "",
                "demand": "",
                "reason": "tabu_tenure_expired",
            })

    def apply(
        self,
        selected: Set[Pair],
        iteration: int,
        *,
        saving_by_pair: Optional[Dict[Pair, float]] = None,
        demand_by_pair: Optional[Dict[Pair, float]] = None,
    ) -> None:
        """Apply the savings selection under the active repair mode."""
        saving_by_pair = saving_by_pair or {}
        demand_by_pair = demand_by_pair or {}
        for pair in sorted(selected):
            saving = saving_by_pair.get(pair, "")
            demand = demand_by_pair.get(pair, "")
            if self.is_hard:
                self.forbidden.add(pair)
                action, remaining = ACTION_HARD_FORBID, ""
            elif self.mode == REPAIR_MODE_SOFT_PENALTY:
                self.penalty[pair] = self.penalty_value
                action, remaining = ACTION_SOFT_PENALTY, ""
            else:  # tabu_penalty
                self.penalty[pair] = self.penalty_value
                self.tabu[pair] = self.tabu_tenure
                action, remaining = ACTION_TABU_ADD, self.tabu_tenure
            self.events.append({
                "iteration": iteration,
                "action": action,
                "depot_id": pair[0],
                "client_id": pair[1],
                "penalty_value": "" if self.is_hard else self.penalty_value,
                "tabu_remaining": remaining,
                "saving": saving,
                "demand": demand,
                "reason": "",
            })


def penalty_value_int(penalty_factor: float, route_max_distance_int: int) -> int:
    """Scale-consistent integer penalty for one routing arrival at a pair.

    ``penalty_factor * route_max_distance_int`` makes a single penalised visit
    cost many full route-length budgets, so the solver only keeps the pair when
    no feasible alternative exists.
    """
    return int(round(float(penalty_factor) * int(route_max_distance_int)))


__all__ = [
    "Pair",
    "REPAIR_MODE_HARD_FORBID",
    "REPAIR_MODE_SOFT_PENALTY",
    "REPAIR_MODE_TABU_PENALTY",
    "REPAIR_MODES",
    "DEFAULT_REPAIR_MODE",
    "ACTION_HARD_FORBID",
    "ACTION_SOFT_PENALTY",
    "ACTION_TABU_ADD",
    "ACTION_TABU_EXPIRE",
    "RepairModeState",
    "penalty_value_int",
]
