"""Per-row experiment configuration (one Excel ``LoRP-FSD`` row).

Holds the run parameters (``F_R``, ``F_A``, ``R``, ``Length``) plus the Excel
benchmark values (UB, cost components, selected depots/sizes/capacities) used for
the fixed-facility benchmark. ``problemID`` is a run-level parameter (not an Excel
column); only ``problemID=0`` (Arslan) is supported.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

SUPPORTED_PROBLEM_ID = 0

_UNSUPPORTED_MSG = "LoRP-v3 currently supports only problemID=0 Arslan scaling."


@dataclass(frozen=True)
class SelectedDepot:
    """An Excel-selected (open) depot for one row, with its MILP solution slots."""

    depot_id: int  # real 1-based depot ID (parsed from 'd5' -> 5)
    size: int  # output size 1..5
    capacity: float  # Excel CapD*
    demand: Optional[float] = None  # Excel DemandD* (routing + DA aggregate)
    usage: Optional[float] = None  # Excel %UsageD*
    vehicles: Optional[int] = None  # Excel VehiclesD* (routing routes)


@dataclass(frozen=True)
class ExperimentConfig:
    name: str
    F_R: float
    F_A: float
    R: float
    Length: float

    problem_id: int = SUPPORTED_PROBLEM_ID
    original: int = 0  # LoRP-FSD / sizing
    VFX: int = 1
    of: str = "cost"

    # Excel benchmark values (scaled distance costs + raw fixed costs).
    UB: Optional[float] = None
    LB: Optional[float] = None
    status: Optional[str] = None
    gap: Optional[float] = None
    cost_routing: Optional[float] = None
    cost_vehicles: Optional[float] = None
    cost_depots: Optional[float] = None
    cost_direct_all: Optional[float] = None

    selected_depots: Dict[int, SelectedDepot] = field(default_factory=dict)
    total_depots: Optional[int] = None
    total_vehicles: Optional[int] = None

    # Source bookkeeping (e.g. Excel row index) — never used for modeling.
    row_index: Optional[int] = None

    def __post_init__(self) -> None:
        if self.problem_id != SUPPORTED_PROBLEM_ID:
            raise NotImplementedError(_UNSUPPORTED_MSG)

    @property
    def active_depot_ids(self) -> tuple[int, ...]:
        return tuple(sorted(self.selected_depots))


__all__ = ["ExperimentConfig", "SelectedDepot", "SUPPORTED_PROBLEM_ID"]
