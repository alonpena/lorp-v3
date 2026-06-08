"""Euclidean geometry primitives (raw, unscaled).

Scaling (Arslan ``100/max_dist``) lives in :mod:`lorp_fsd.scaling`. This module
only knows raw Euclidean distance, matching the C solver which computes
``Data.dist`` as the Euclidean norm before ``scaledistance()`` is applied.
"""

from __future__ import annotations

import math
from typing import Iterable, Tuple

Point = Tuple[float, float]


def euclidean(a: Point, b: Point) -> float:
    """Raw Euclidean distance between two points."""
    return math.hypot(a[0] - b[0], a[1] - b[1])


def max_pairwise_distance(points: Iterable[Point]) -> float:
    """Maximum Euclidean distance over all distinct pairs.

    Matches the C ``maxdist`` basis: the max over *all* depot/client nodes
    (the congruency check confirmed a client–client pair dominates).
    """
    pts = list(points)
    n = len(pts)
    if n < 2:
        raise ValueError("need at least two points to compute a max pairwise distance")
    best = 0.0
    for i in range(n):
        for j in range(i + 1, n):
            d = euclidean(pts[i], pts[j])
            if d > best:
                best = d
    return best


__all__ = ["Point", "euclidean", "max_pairwise_distance"]
