"""DA candidate pool per depot with capacity-feasibility filter.

For each depot d:
- eligible: clients within Euclidean distance <= R.
- selected: subset whose total demand <= cap_d. If the eligible total already
  fits the capacity, selected == eligible. Otherwise pick a subset that
  maximizes total selected demand (knapsack-style filter).

Note: This is only a *candidate* filter for DA vehicle generation. Real
depot capacity (shared between DA and routing) is enforced ex post by the
audit + repair loop.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from da_geometry import dist_euclid
from dat_loader import Instance


def eligible_da_clients(
    inst: Instance,
    depot_id: int,
    radius_scaled: float,
    scale: float = 1.0,
) -> List[int]:
    """Clients eligible for DA at depot_id.

    Arslan rule: distance is scaled by `scale = 100 / max_dist`. A client j is
    eligible iff `dist_euclid(depot, j) * scale <= radius_scaled`. Default
    scale=1.0 preserves the old behavior (interprets `radius_scaled` as a raw
    radius).
    """
    depot = inst.depots[depot_id]
    dx, dy = depot["x"], depot["y"]
    tol = 1e-9
    out: List[int] = []
    for cid, c in inst.clients.items():
        if dist_euclid((dx, dy), (c["x"], c["y"])) * scale <= radius_scaled + tol:
            out.append(cid)
    return out


def _is_integerish(v: float) -> bool:
    return abs(v - round(v)) < 1e-9


def select_max_demand_subset_under_capacity(
    demands: Dict[int, float],
    capacity: float,
) -> List[int]:
    """Pick subset of clients maximizing total demand subject to total <= capacity.

    Strategy:
    - If demands and capacity are integer-ish and capacity is moderate, use
      exact 0/1 knapsack DP where value = weight = demand.
    - Otherwise, greedy descending by demand (capacity-feasibility filter,
      not DA policy).
    """
    if not demands:
        return []

    ids = list(demands.keys())
    vals = [float(demands[i]) for i in ids]

    all_int = _is_integerish(capacity) and all(_is_integerish(v) for v in vals)
    cap_int = int(round(capacity))

    # Exact 1D knapsack with per-cell predecessor (bitset, not full n x cap matrix).
    # Memory cap: cap_int <= 20000 keeps the chosen bitset list bounded.
    if all_int and 0 <= cap_int <= 20_000:
        n = len(ids)
        ws = [int(round(v)) for v in vals]
        dp = [0] * (cap_int + 1)
        # chosen[c] is a frozenset of indices forming the optimal subset for cap c
        chosen_for: List[frozenset] = [frozenset()] * (cap_int + 1)
        for i in range(n):
            wi = ws[i]
            if wi <= 0:
                continue
            for c in range(cap_int, wi - 1, -1):
                cand = dp[c - wi] + wi
                if cand > dp[c]:
                    dp[c] = cand
                    chosen_for[c] = chosen_for[c - wi] | {i}
        best = chosen_for[cap_int]
        return sorted(ids[i] for i in best)

    # greedy fallback
    order = sorted(ids, key=lambda i: demands[i], reverse=True)
    total = 0.0
    chosen: List[int] = []
    for i in order:
        d = float(demands[i])
        if total + d <= capacity + 1e-9:
            chosen.append(i)
            total += d
    return sorted(chosen)


def build_da_candidate_pool_with_stats(
    inst: Instance,
    radius_scaled: float,
    scale: float = 1.0,
) -> Tuple[Dict[int, List[int]], Dict[int, Dict[str, Any]]]:
    """Build DA candidate pool per depot + stats dict.

    Eligibility uses Arslan-scaled distance:
        dist_euclid(depot, client) * scale <= radius_scaled
    With scale=1.0 this is equivalent to a raw-radius filter.

    Returns:
        pool: {depot_id -> sorted list of client ids}
        stats: {depot_id -> {eligible_clients, eligible_demand,
                             selected_clients, selected_demand,
                             lost_da_candidate_demand, capacity,
                             radius_scaled, radius_raw_equivalent}}
    """
    pool: Dict[int, List[int]] = {}
    stats: Dict[int, Dict[str, Any]] = {}
    radius_raw_equiv = radius_scaled / scale if scale > 0 else radius_scaled

    for did, depot in inst.depots.items():
        cap = float(depot["cap"])
        eligible = eligible_da_clients(inst, did, radius_scaled, scale)
        eligible_demand = float(sum(inst.clients[j]["demand"] for j in eligible))

        if eligible_demand <= cap + 1e-9:
            selected = sorted(eligible)
        else:
            demands = {j: float(inst.clients[j]["demand"]) for j in eligible}
            selected = select_max_demand_subset_under_capacity(demands, cap)

        selected_demand = float(sum(inst.clients[j]["demand"] for j in selected))
        pool[did] = sorted(selected)
        stats[did] = {
            "eligible_clients": len(eligible),
            "eligible_demand": eligible_demand,
            "selected_clients": len(selected),
            "selected_demand": selected_demand,
            "lost_da_candidate_demand": max(0.0, eligible_demand - selected_demand),
            "capacity": cap,
            "radius_scaled": radius_scaled,
            "radius_raw_equivalent": radius_raw_equiv,
        }

    return pool, stats


__all__ = [
    "eligible_da_clients",
    "select_max_demand_subset_under_capacity",
    "build_da_candidate_pool_with_stats",
]
