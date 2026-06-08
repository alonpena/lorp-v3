"""Savings-based routing-elimination repair (Phase 4 + Phase 7A safety).

When the post-solve audit finds an overloaded depot, repair removes routing
clients from that depot's routes until enough demand is shed, choosing clients by
largest marginal routing saving first (spec §8, settled decision #8). A removal
is recorded as a *routing-only* forbidden assignment ``(depot_id, client_id)``
(settled decision #16): the client is NOT deleted — it stays in the problem and
may be re-served by DA (incl. same-depot DA), routing from another depot, etc.

Phase 7A adds safety diagnostics and optional candidate filtering:

* ``same_depot_DA_risk``: forbidding routing ``(i, j)`` may not release aggregate
  capacity if client ``j`` can still be direct-allocated from the same depot ``i``.
* ``length_serviceable_after_cut``: after forbidding routing ``(i, j)``, client
  ``j`` must still have a DA option or at least one singleton route option that
  satisfies ``2 * dist_scaled(h, j) <= Length``.

Important caveat: routing-only forbids still do not guarantee aggregate capacity
is reduced. Capacity is re-audited only after the next solve (Phase 5 loop).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional, Set, Tuple

REPAIR_INFEASIBLE = "REPAIR_INFEASIBLE"

REPAIR_POLICY_BASELINE = "baseline"
REPAIR_POLICY_SAFE_LENGTH = "safe_length"
REPAIR_POLICY_SAFE_CAPACITY_RELEASE = "safe_capacity_release"
REPAIR_POLICY_SAFE_BOTH = "safe_both"
REPAIR_POLICIES = {
    REPAIR_POLICY_BASELINE,
    REPAIR_POLICY_SAFE_LENGTH,
    REPAIR_POLICY_SAFE_CAPACITY_RELEASE,
    REPAIR_POLICY_SAFE_BOTH,
}

REJECTION_SAME_DEPOT_DA_RISK = "same_depot_DA_risk"
REJECTION_NO_LENGTH_ALTERNATIVE = "no_length_feasible_alternative"
REJECTION_CAUSES_ROUTE_LENGTH = "causes_route_length_violation"
REJECTION_STRANDS_CLIENT = "strands_client"

# A checker: (client_id, forbidden_routing_assignments) -> bool (still serviceable?)
FeasibilityChecker = Callable[[int, Set[Tuple[int, int]]], bool]
RejectedRepairCandidate = Tuple[int, int, str]


@dataclass(frozen=True)
class RepairCandidate:
    depot_id: int
    route_id: int
    client_id: int
    client_demand: float
    saving: float  # marginal scaled-distance saving from removing the client
    weighted_saving: float  # F_R * saving


@dataclass(frozen=True)
class RepairCandidateSafety:
    """Phase 7A diagnostics for a candidate under a tentative cut set."""

    depot_id: int
    client_id: int
    same_depot_DA_feasible: bool
    same_depot_DA_risk: bool
    length_serviceable_after_cut: bool
    has_DA_alternative_after_cut: bool
    has_routing_singleton_alternative_after_cut: bool
    safe_for_capacity_release: bool
    safe_for_length_serviceability: bool

    def to_dict(self) -> dict:
        return {
            "depot_id": self.depot_id,
            "client_id": self.client_id,
            "same_depot_DA_feasible": self.same_depot_DA_feasible,
            "same_depot_DA_risk": self.same_depot_DA_risk,
            "length_serviceable_after_cut": self.length_serviceable_after_cut,
            "has_DA_alternative_after_cut": self.has_DA_alternative_after_cut,
            "has_routing_singleton_alternative_after_cut": self.has_routing_singleton_alternative_after_cut,
            "safe_for_capacity_release": self.safe_for_capacity_release,
            "safe_for_length_serviceability": self.safe_for_length_serviceability,
        }


def _pair(cand: RepairCandidate) -> Tuple[int, int]:
    return (cand.depot_id, cand.client_id)


def _rejected_pairs(rejected: Iterable[RejectedRepairCandidate]) -> Set[Tuple[int, int]]:
    return {(i, j) for i, j, _reason in rejected}


def compute_route_savings(depot_id: int, client_sequence, geometry) -> Dict[int, float]:
    """Marginal scaled-distance saving of removing each client from one route.

    Cases (spec §8):
      internal c_m:     d(p, c_m) + d(c_m, s) - d(p, s)
      first c1:         d(depot, c1) + d(c1, c2) - d(depot, c2)
      last  ck:         d(c_{k-1}, ck) + d(ck, depot) - d(c_{k-1}, depot)
      single client c1: d(depot, c1) + d(c1, depot)
    """
    seq = list(client_sequence)
    n = len(seq)

    def dc(j: int) -> float:
        return geometry.depot_client_scaled(depot_id, j)

    def cc(a: int, b: int) -> float:
        return geometry.client_client_scaled(a, b)

    savings: Dict[int, float] = {}
    if n == 0:
        return savings
    if n == 1:
        c1 = seq[0]
        savings[c1] = dc(c1) + dc(c1)  # depot -> c1 -> depot
        return savings

    for idx, c in enumerate(seq):
        if idx == 0:
            savings[c] = dc(c) + cc(c, seq[1]) - dc(seq[1])
        elif idx == n - 1:
            savings[c] = cc(seq[idx - 1], c) + dc(c) - dc(seq[idx - 1])
        else:
            p, s = seq[idx - 1], seq[idx + 1]
            savings[c] = cc(p, c) + cc(c, s) - cc(p, s)
    return savings


def build_repair_candidates(
    routes,
    capacity_audit,
    geometry,
    F_R: float,
    demands: Dict[int, float],
) -> List[RepairCandidate]:
    """Candidates from routing routes of OVERLOADED depots only.

    ``demands`` maps ``client_id -> demand`` (caller builds it from the instance:
    ``{j: c.demand for j, c in instance.clients.items()}``).
    """
    overloaded = {i for i, rec in capacity_audit.by_depot.items() if rec.excess > 0}

    candidates: List[RepairCandidate] = []
    for route_id, route in enumerate(routes):
        if route.mode != "routing" or route.depot_id not in overloaded:
            continue
        savings = compute_route_savings(route.depot_id, route.client_sequence, geometry)
        for client_id, saving in savings.items():
            candidates.append(RepairCandidate(
                depot_id=route.depot_id,
                route_id=route_id,
                client_id=client_id,
                client_demand=float(demands[client_id]),
                saving=saving,
                weighted_saving=F_R * saving,
            ))
    return candidates


def diagnose_repair_candidate(
    cand: RepairCandidate,
    *,
    active_depots,
    geometry,
    R: float,
    Length: float,
    forbidden_after_cut: Set[Tuple[int, int]],
) -> RepairCandidateSafety:
    """Compute Phase 7A safety diagnostics for ``cand`` under a tentative cut.

    Length serviceability after cut requires at least one active depot ``h`` with
    either DA feasibility ``dist_scaled(h,j) <= R`` or routing singleton
    feasibility ``(h,j) not in forbidden_after_cut`` and
    ``2 * dist_scaled(h,j) <= Length``.
    """
    depot_id = cand.depot_id
    client_id = cand.client_id
    active = tuple(active_depots)

    same_depot_da = geometry.depot_client_scaled(depot_id, client_id) <= float(R)
    has_da_alt = any(geometry.depot_client_scaled(h, client_id) <= float(R) for h in active)
    has_routing_singleton_alt = any(
        (h, client_id) not in forbidden_after_cut
        and 2.0 * geometry.depot_client_scaled(h, client_id) <= float(Length)
        for h in active
    )
    length_serviceable = has_da_alt or has_routing_singleton_alt

    return RepairCandidateSafety(
        depot_id=depot_id,
        client_id=client_id,
        same_depot_DA_feasible=same_depot_da,
        same_depot_DA_risk=same_depot_da,
        length_serviceable_after_cut=length_serviceable,
        has_DA_alternative_after_cut=has_da_alt,
        has_routing_singleton_alternative_after_cut=has_routing_singleton_alt,
        safe_for_capacity_release=not same_depot_da,
        safe_for_length_serviceability=length_serviceable,
    )


def _policy_rejections(policy: str, safety: RepairCandidateSafety) -> List[str]:
    if policy not in REPAIR_POLICIES:
        raise ValueError(f"unknown repair_candidate_policy {policy!r}; expected one of {sorted(REPAIR_POLICIES)}")

    reasons: List[str] = []
    if policy in {REPAIR_POLICY_SAFE_LENGTH, REPAIR_POLICY_SAFE_BOTH}:
        if not safety.safe_for_length_serviceability:
            reasons.append(REJECTION_NO_LENGTH_ALTERNATIVE)
    if policy in {REPAIR_POLICY_SAFE_CAPACITY_RELEASE, REPAIR_POLICY_SAFE_BOTH}:
        if not safety.safe_for_capacity_release:
            reasons.append(REJECTION_SAME_DEPOT_DA_RISK)
    return reasons


@dataclass
class RepairSelection:
    selected: Set[Tuple[int, int]]  # newly forbidden routing assignments
    updated_forbidden: Set[Tuple[int, int]]  # current ∪ selected
    removed_demand_by_depot: Dict[int, float]
    repair_infeasible: bool
    infeasible_depots: List[int]
    flags: Set[str] = field(default_factory=set)

    # Phase 7A diagnostics.
    repair_candidate_policy: str = REPAIR_POLICY_BASELINE
    candidate_safety: Dict[Tuple[int, int], RepairCandidateSafety] = field(default_factory=dict)
    rejected_candidates: Set[RejectedRepairCandidate] = field(default_factory=set)

    @property
    def same_depot_DA_risk_count(self) -> int:
        return sum(1 for s in self.candidate_safety.values() if s.same_depot_DA_risk)

    @property
    def length_invalid_cut_count(self) -> int:
        return sum(1 for _i, _j, reason in self.rejected_candidates if reason == REJECTION_NO_LENGTH_ALTERNATIVE)

    @property
    def rejected_candidates_count(self) -> int:
        return len(self.rejected_candidates)


def select_forbidden_assignments(
    candidates: List[RepairCandidate],
    excess_by_depot: Dict[int, float],
    current_forbidden: Set[Tuple[int, int]],
    feasibility_checker: FeasibilityChecker,
    *,
    active_depots=None,
    geometry=None,
    R: Optional[float] = None,
    Length: Optional[float] = None,
    repair_candidate_policy: str = REPAIR_POLICY_BASELINE,
    rejected_repair_candidates: Optional[Set[RejectedRepairCandidate]] = None,
) -> RepairSelection:
    """Greedily forbid routing of largest-saving clients until excess is covered.

    Per overloaded depot: sort candidates by largest ``weighted_saving``; select
    until ``sum(demand_removed) >= excess_i``; skip any removal that would strand
    a client. Phase 7A policies can additionally reject unsafe candidates:

    * ``baseline``: current behavior.
    * ``safe_length``: require length serviceability after cut.
    * ``safe_capacity_release``: reject same-depot DA risk.
    * ``safe_both``: require both checks.
    """
    if repair_candidate_policy not in REPAIR_POLICIES:
        raise ValueError(
            f"unknown repair_candidate_policy {repair_candidate_policy!r}; expected one of {sorted(REPAIR_POLICIES)}"
        )

    needs_safety = repair_candidate_policy != REPAIR_POLICY_BASELINE
    if needs_safety and (active_depots is None or geometry is None or R is None or Length is None):
        raise ValueError("safe repair policies require active_depots, geometry, R, and Length")

    working: Set[Tuple[int, int]] = set(current_forbidden)
    selected: Set[Tuple[int, int]] = set()
    removed_by_depot: Dict[int, float] = {}
    infeasible_depots: List[int] = []
    candidate_safety: Dict[Tuple[int, int], RepairCandidateSafety] = {}
    rejected: Set[RejectedRepairCandidate] = set(rejected_repair_candidates or set())
    rejected_pairs = _rejected_pairs(rejected)

    by_depot: Dict[int, List[RepairCandidate]] = {}
    for c in candidates:
        if _pair(c) in rejected_pairs:
            continue
        by_depot.setdefault(c.depot_id, []).append(c)

    for depot_id, excess in excess_by_depot.items():
        if excess <= 0:
            continue
        removed = 0.0
        depot_candidates = sorted(
            by_depot.get(depot_id, []),
            key=lambda c: (-c.weighted_saving, c.depot_id, c.route_id, c.client_id),
        )
        for cand in depot_candidates:
            if removed >= excess:
                break
            pair = (depot_id, cand.client_id)
            if pair in working:
                continue
            tentative = working | {pair}

            if active_depots is not None and geometry is not None and R is not None and Length is not None:
                safety = diagnose_repair_candidate(
                    cand,
                    active_depots=active_depots,
                    geometry=geometry,
                    R=R,
                    Length=Length,
                    forbidden_after_cut=tentative,
                )
                candidate_safety[pair] = safety
                reasons = _policy_rejections(repair_candidate_policy, safety)
                if reasons:
                    for reason in reasons:
                        rejected.add((depot_id, cand.client_id, reason))
                    rejected_pairs.add(pair)
                    continue

            if not feasibility_checker(cand.client_id, tentative):
                rejected.add((depot_id, cand.client_id, REJECTION_STRANDS_CLIENT))
                rejected_pairs.add(pair)
                continue  # would strand the client -> skip

            working.add(pair)
            selected.add(pair)
            removed += cand.client_demand
        removed_by_depot[depot_id] = removed
        if removed < excess:
            infeasible_depots.append(depot_id)

    flags: Set[str] = set()
    if infeasible_depots:
        flags.add(REPAIR_INFEASIBLE)

    return RepairSelection(
        selected=selected,
        updated_forbidden=working,
        removed_demand_by_depot=removed_by_depot,
        repair_infeasible=bool(infeasible_depots),
        infeasible_depots=infeasible_depots,
        flags=flags,
        repair_candidate_policy=repair_candidate_policy,
        candidate_safety=candidate_safety,
        rejected_candidates=rejected,
    )


__all__ = [
    "REPAIR_INFEASIBLE",
    "REPAIR_POLICY_BASELINE",
    "REPAIR_POLICY_SAFE_LENGTH",
    "REPAIR_POLICY_SAFE_CAPACITY_RELEASE",
    "REPAIR_POLICY_SAFE_BOTH",
    "REPAIR_POLICIES",
    "REJECTION_SAME_DEPOT_DA_RISK",
    "REJECTION_NO_LENGTH_ALTERNATIVE",
    "REJECTION_CAUSES_ROUTE_LENGTH",
    "REJECTION_STRANDS_CLIENT",
    "FeasibilityChecker",
    "RejectedRepairCandidate",
    "RepairCandidate",
    "RepairCandidateSafety",
    "compute_route_savings",
    "build_repair_candidates",
    "diagnose_repair_candidate",
    "RepairSelection",
    "select_forbidden_assignments",
]
