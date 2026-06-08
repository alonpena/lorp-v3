"""Arslan scaling (``problemID=0``) and PyVRP integer discretization.

Canonical policy (spec §1, settled decision #13)::

    scale = 100 / max_dist          # max_dist over ALL depot/client node pairs
    dist_scaled = dist_original * scale

- ``R``, ``Length`` and all objective distance components are in *scaled* units.
- DA radius feasibility uses *continuous* ``dist_scaled`` (never integerized).
- PyVRP search uses high-precision *integer* distances via ``PYVRP_INT_SCALE``.
- Never divide final reported costs by ``scale``.

Only ``problemID=0`` is supported; any other mode fails loudly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from .geometry import Point, euclidean, max_pairwise_distance

# Settled decision #13: PyVRP requires integer edge weights; the C/MILP objective
# is continuous scaled. We integerize internal edge costs / length limits with
# this high-precision factor and report continuous scaled costs ex-post.
PYVRP_INT_SCALE = 10_000

SUPPORTED_PROBLEM_ID = 0

_UNSUPPORTED_MSG = "LoRP-v3 currently supports only problemID=0 Arslan scaling."


@dataclass(frozen=True)
class ScaledGeometry:
    """Scaled-distance lookup for one instance under Arslan scaling."""

    max_dist: float
    scale: float
    depot_xy: Dict[int, Point]
    client_xy: Dict[int, Point]

    # -- continuous scaled distances (for feasibility + final reporting) -----
    def dist_scaled(self, a: Point, b: Point) -> float:
        return euclidean(a, b) * self.scale

    def depot_client_scaled(self, depot_id: int, client_id: int) -> float:
        return self.dist_scaled(self.depot_xy[depot_id], self.client_xy[client_id])

    def client_client_scaled(self, i: int, j: int) -> float:
        return self.dist_scaled(self.client_xy[i], self.client_xy[j])

    # -- integerized values (for the PyVRP model only) -----------------------
    def to_int(self, scaled_value: float) -> int:
        """Integerize a scaled value for PyVRP (``round(value * PYVRP_INT_SCALE)``)."""
        return round(scaled_value * PYVRP_INT_SCALE)

    def dist_scaled_int(self, a: Point, b: Point) -> int:
        return self.to_int(self.dist_scaled(a, b))

    # -- raw equivalents (plotting / debug only; never for reporting) --------
    def raw_from_scaled(self, scaled_value: float) -> float:
        return scaled_value / self.scale


def build_scaled_geometry(instance, *, problem_id: int = SUPPORTED_PROBLEM_ID) -> ScaledGeometry:
    """Build :class:`ScaledGeometry` from a :class:`~lorp_fsd.dat_parser.ParsedInstance`.

    ``max_dist`` is the maximum Euclidean distance over *all* depot and client
    nodes (congruency-confirmed basis), and ``scale = 100 / max_dist``.
    """
    if problem_id != SUPPORTED_PROBLEM_ID:
        raise NotImplementedError(_UNSUPPORTED_MSG)

    depot_xy = {d.id: d.xy for d in instance.depots.values()}
    client_xy = {c.id: c.xy for c in instance.clients.values()}

    max_dist = max_pairwise_distance(list(depot_xy.values()) + list(client_xy.values()))
    if max_dist <= 0:
        raise ValueError("max_dist must be positive")
    scale = 100.0 / max_dist

    return ScaledGeometry(max_dist=max_dist, scale=scale, depot_xy=depot_xy, client_xy=client_xy)


__all__ = [
    "PYVRP_INT_SCALE",
    "SUPPORTED_PROBLEM_ID",
    "ScaledGeometry",
    "build_scaled_geometry",
]
