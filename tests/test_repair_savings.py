"""Phase 4 — savings-based routing-elimination repair (no solve, no runner)."""
from __future__ import annotations

import math

import pytest

from lorp_fsd.dat_parser import parse_dat
from lorp_fsd.scaling import build_scaled_geometry
from lorp_fsd.capacity_audit import CapacityAudit, DepotAuditRecord
from lorp_fsd.feasibility import client_has_service_option, make_feasibility_checker
from lorp_fsd.repair import (
    REPAIR_INFEASIBLE,
    RepairCandidate,
    build_repair_candidates,
    compute_route_savings,
    select_forbidden_assignments,
)
from lorp_fsd.solution_parser import RouteRecord

# ── synthetic instance with max pairwise distance = 100 so scale == 1 ────────
# depot d1 (0,0); c1 (0,40); c2 (30,40); c3 (60,0); c4 (60,80)
# max pair = depot(0,0)..c4(60,80) = sqrt(60^2+80^2) = 100 -> scale = 1
SCALE1_DAT = """\
4
1
1
4
0 0
0 40
30 40
60 0
60 80
100
200
10
10
10
10
100
0
0
"""


@pytest.fixture(scope="module")
def geom_scale1():
    geom = build_scaled_geometry(parse_dat(SCALE1_DAT.splitlines(), name="scale1.dat"))
    assert geom.scale == pytest.approx(1.0)  # max_dist == 100
    return geom


def _route(depot_id, seq, demand=30.0):
    return RouteRecord(
        vehicle_type_index=0, mode="routing", depot_id=depot_id, capacity=100,
        client_sequence=tuple(seq), demand=demand, solver_distance_int=0,
        solver_distance_scaled=0.0, reconstructed_scaled_distance=0.0,
        reconstructed_weighted_cost=0.0,
    )


def _audit(excess_by_depot):
    by = {
        i: DepotAuditRecord(depot_id=i, demand_routing=0, demand_da=0,
                            demand_total=0, capacity=0, excess=e)
        for i, e in excess_by_depot.items()
    }
    total = sum(excess_by_depot.values())
    return CapacityAudit(by_depot=by, capacity_feasible=(total == 0), total_excess=total)


# ── savings formula ──────────────────────────────────────────────────────────
def test_savings_first_internal_last(geom_scale1):
    # route depot -> c1 -> c2 -> c3 (scale=1 so scaled == raw euclidean)
    s = compute_route_savings(1, (1, 2, 3), geom_scale1)
    # c1 first : d(dep,c1)+d(c1,c2)-d(dep,c2) = 40 + 30 - 50 = 20
    assert s[1] == pytest.approx(20.0, abs=1e-6)
    # c2 inner : d(c1,c2)+d(c2,c3)-d(c1,c3) = 30 + 50 - sqrt(60^2+40^2)
    assert s[2] == pytest.approx(30 + 50 - math.hypot(60, 40), abs=1e-6)
    # c3 last  : d(c2,c3)+d(c3,dep)-d(c2,dep) = 50 + 60 - 50 = 60
    assert s[3] == pytest.approx(60.0, abs=1e-6)


def test_savings_single_client(geom_scale1):
    s = compute_route_savings(1, (1,), geom_scale1)
    # depot -> c1 -> depot = 2 * d(depot, c1) = 80
    assert s[1] == pytest.approx(80.0, abs=1e-6)


def test_weighted_saving_applies_F_R(geom_scale1):
    routes = [_route(1, (1, 2, 3))]
    audit = _audit({1: 10.0})
    demands = {1: 10, 2: 10, 3: 10}
    cands = build_repair_candidates(routes, audit, geom_scale1, F_R=2.0, demands=demands)
    for c in cands:
        assert c.weighted_saving == pytest.approx(2.0 * c.saving)


# ── candidate generation only from overloaded depots ────────────────────────
def test_candidates_only_from_overloaded_depots(geom_scale1):
    routes = [_route(1, (1, 2, 3)), _route(2, (1, 2))]  # depot 2 route too
    audit = _audit({1: 10.0, 2: 0.0})  # only depot 1 overloaded
    demands = {1: 10, 2: 10, 3: 10}
    cands = build_repair_candidates(routes, audit, geom_scale1, F_R=1.0, demands=demands)
    assert {c.depot_id for c in cands} == {1}
    assert all(isinstance(c.client_id, int) for c in cands)


# ── selection ────────────────────────────────────────────────────────────────
def _always_ok(client_id, forbidden):
    return True


def test_selection_reaches_excess_by_demand(geom_scale1):
    routes = [_route(1, (1, 2, 3))]
    audit = _audit({1: 25.0})
    demands = {1: 10, 2: 10, 3: 10}
    cands = build_repair_candidates(routes, audit, geom_scale1, F_R=1.0, demands=demands)
    sel = select_forbidden_assignments(cands, {1: 25.0}, set(), _always_ok)
    # removed demand must cover the excess (each client demand 10 -> need 3 removals)
    assert sel.removed_demand_by_depot[1] >= 25.0
    assert not sel.repair_infeasible
    # forbidden entries are (depot_id, client_id) tuples
    for pair in sel.selected:
        assert isinstance(pair, tuple) and len(pair) == 2
        assert pair[0] == 1 and pair[1] in {1, 2, 3}


def test_selection_picks_largest_weighted_saving_first(geom_scale1):
    routes = [_route(1, (1, 2, 3))]
    audit = _audit({1: 10.0})
    demands = {1: 10, 2: 10, 3: 10}
    cands = build_repair_candidates(routes, audit, geom_scale1, F_R=1.0, demands=demands)
    sel = select_forbidden_assignments(cands, {1: 10.0}, set(), _always_ok)
    # only need 10 demand -> 1 client; the largest saving is c3 (60) -> remove c3
    assert sel.selected == {(1, 3)}


def test_removal_does_not_delete_client_globally(geom_scale1):
    # forbidding routing (1, c1) leaves c1 serviceable via DA from depot 1 (in radius)
    active = [1]
    R = 100.0  # everything within radius for this tiny instance
    assert client_has_service_option(1, active, geom_scale1, R, {(1, 1)}) is True


def test_no_rerun_when_candidate_would_strand_client(geom_scale1):
    # checker that refuses to keep client 3 serviceable -> its removal is skipped,
    # so depot 1's excess cannot be covered -> REPAIR_INFEASIBLE.
    routes = [_route(1, (3,))]  # single-client route, only candidate is client 3
    audit = _audit({1: 10.0})
    demands = {3: 10}
    cands = build_repair_candidates(routes, audit, geom_scale1, F_R=1.0, demands=demands)

    def strands_c3(client_id, forbidden):
        return client_id != 3  # forbidding routing of c3 would strand it

    sel = select_forbidden_assignments(cands, {1: 10.0}, set(), strands_c3)
    assert sel.selected == set()
    assert sel.repair_infeasible
    assert sel.infeasible_depots == [1]
    assert REPAIR_INFEASIBLE in sel.flags


def test_make_feasibility_checker_routing_and_da(geom_scale1):
    check = make_feasibility_checker([1], geom_scale1, R=100.0)
    # client still routable from depot 1 (not forbidden) OR DA-feasible
    assert check(2, set()) is True
    # forbid routing (1,2): still DA-feasible within R=100 -> serviceable
    assert check(2, {(1, 2)}) is True
    # with R=0 and routing forbidden everywhere -> not serviceable
    check0 = make_feasibility_checker([1], geom_scale1, R=0.0)
    assert check0(2, {(1, 2)}) is False
