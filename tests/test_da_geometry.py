from __future__ import annotations

import math

import pytest

from da_geometry import (
    assign_da_clients,
    build_direct_allocation_data,
    compute_max_distance,
    dist_euclid,
    dist_manhattan,
)
from dat_loader import Instance
from tests.conftest import MINIMAL_DAT


# ── distance primitives ───────────────────────────────────────────────────────

def test_dist_euclid_same_point():
    assert dist_euclid((3.0, 4.0), (3.0, 4.0)) == 0.0


def test_dist_euclid_3_4_5():
    assert dist_euclid((0.0, 0.0), (3.0, 4.0)) == pytest.approx(5.0)


def test_dist_euclid_negative_coords():
    assert dist_euclid((-3.0, 0.0), (0.0, 4.0)) == pytest.approx(5.0)


def test_dist_manhattan_zero():
    assert dist_manhattan((5.0, 5.0), (5.0, 5.0)) == 0.0


def test_dist_manhattan_3_4():
    assert dist_manhattan((0.0, 0.0), (3.0, 4.0)) == pytest.approx(7.0)


# ── compute_max_distance ──────────────────────────────────────────────────────

def test_max_distance_two_depots_no_clients():
    inst = Instance(
        depots={1: {"x": 0.0, "y": 0.0, "cap": 100, "fixed_cost": 0},
                2: {"x": 3.0, "y": 4.0, "cap": 100, "fixed_cost": 0}},
        clients={},
        data={},
    )
    assert compute_max_distance(inst) == pytest.approx(5.0)


def test_max_distance_includes_clients(minimal_instance):
    # depot1=(0,0) depot2=(10,0) client1=(0,5) client2=(10,5) client3=(5,5)
    # max pair: depot1 to client2 = sqrt(100+25) = sqrt(125) ≈ 11.18
    #           depot2 to client1 = same
    #           depot1 to depot2 = 10
    d = compute_max_distance(minimal_instance)
    assert d == pytest.approx(math.hypot(10.0, 5.0))


def test_max_distance_single_node():
    inst = Instance(
        depots={1: {"x": 5.0, "y": 5.0, "cap": 100, "fixed_cost": 0}},
        clients={},
        data={},
    )
    assert compute_max_distance(inst) == 0.0


# ── build_direct_allocation_data ──────────────────────────────────────────────

def _simple_inst(depot_xy, client_xys, demands=None, depot_cap=500, veh_cap=10):
    """Build a minimal Instance from raw coords."""
    depots = {i + 1: {"x": x, "y": y, "cap": depot_cap, "fixed_cost": 0.0}
              for i, (x, y) in enumerate(depot_xy)}
    demands = demands or [10] * len(client_xys)
    clients = {i + 1: {"x": x, "y": y, "demand": d}
               for i, ((x, y), d) in enumerate(zip(client_xys, demands))}
    data = {"veh_cap": veh_cap, "veh_fixed_cost": 0}
    return Instance(depots=depots, clients=clients, data=data)


def test_build_da_client_within_radius():
    inst = _simple_inst([(0.0, 0.0)], [(3.0, 4.0)])  # dist=5
    da_data, _ = build_direct_allocation_data(inst, radius=10.0)
    assert 1 in da_data
    assert 1 in da_data[1]["clients"]


def test_build_da_client_outside_radius():
    inst = _simple_inst([(0.0, 0.0)], [(100.0, 0.0)])  # dist=100
    da_data, _ = build_direct_allocation_data(inst, radius=10.0)
    assert len(da_data) == 0


def test_build_da_cost_return_trip_is_zero():
    inst = _simple_inst([(0.0, 0.0)], [(3.0, 4.0)])
    da_data, _ = build_direct_allocation_data(inst, radius=10.0)
    cost_ji = da_data[1]["cost_ji"]
    assert cost_ji[(1, 1)] == 0.0


def test_build_da_cost_outbound_equals_euclid():
    inst = _simple_inst([(0.0, 0.0)], [(3.0, 4.0)])
    da_data, _ = build_direct_allocation_data(inst, radius=10.0)
    assert da_data[1]["cost_ij"][(1, 1)] == pytest.approx(5.0)


def test_build_da_max_clients_per_depot():
    inst = _simple_inst([(0.0, 0.0)], [(1.0, 0.0), (2.0, 0.0), (3.0, 0.0)])
    _, max_clients = build_direct_allocation_data(inst, radius=10.0)
    assert max_clients == 3


def test_build_da_empty_when_all_outside():
    inst = _simple_inst([(0.0, 0.0)], [(50.0, 0.0), (60.0, 0.0)])
    da_data, max_clients = build_direct_allocation_data(inst, radius=5.0)
    assert da_data == {}
    assert max_clients == 0


def test_build_da_arcs_symmetric():
    inst = _simple_inst([(0.0, 0.0)], [(3.0, 4.0)])
    da_data, _ = build_direct_allocation_data(inst, radius=10.0)
    assert (1, 1) in da_data[1]["arcs_ij"]
    assert (1, 1) in da_data[1]["arcs_ji"]


# ── assign_da_clients ─────────────────────────────────────────────────────────

def test_assign_within_cap():
    inst = _simple_inst([(0.0, 0.0)], [(3.0, 4.0)], demands=[5], depot_cap=100, veh_cap=10)
    da_data, _ = build_direct_allocation_data(inst, radius=10.0)
    assigned, routing_set = assign_da_clients(inst, da_data)
    assert 1 in assigned
    assert 1 in assigned[1]
    assert 1 not in routing_set


def test_assign_over_cap_goes_to_routing():
    # demand=50, depot_cap=30 → 50 > 30 → routing
    inst = _simple_inst([(0.0, 0.0)], [(3.0, 4.0)], demands=[50], depot_cap=30, veh_cap=10)
    da_data, _ = build_direct_allocation_data(inst, radius=10.0)
    assigned, routing_set = assign_da_clients(inst, da_data)
    assert 1 in routing_set
    assert not any(1 in cs for cs in assigned.values())


def test_assign_no_coverage_goes_to_routing():
    inst = _simple_inst([(0.0, 0.0)], [(50.0, 0.0)], demands=[5], depot_cap=100, veh_cap=10)
    da_data, _ = build_direct_allocation_data(inst, radius=5.0)
    assigned, routing_set = assign_da_clients(inst, da_data)
    assert 1 in routing_set


def test_assign_prefers_nearest_depot():
    # depot 1 at (0,0), depot 2 at (20,0); client at (3,0)
    # dist to d1=3, dist to d2=17 → global sort picks d1 first
    inst = _simple_inst(
        [(0.0, 0.0), (20.0, 0.0)],
        [(3.0, 0.0)],
        demands=[5],
        depot_cap=100,
        veh_cap=10,
    )
    da_data, _ = build_direct_allocation_data(inst, radius=25.0)
    assigned, _ = assign_da_clients(inst, da_data)
    assert 1 in assigned.get(1, [])
    assert 1 not in assigned.get(2, [])


def test_assign_partial_some_assigned_some_routing():
    # depot at (0,0), radius=5
    # client 1 at (3,4) dist=5 → within → assigned
    # client 2 at (10,0) dist=10 → outside → routing
    inst = _simple_inst(
        [(0.0, 0.0)],
        [(3.0, 4.0), (10.0, 0.0)],
        demands=[5, 5],
        depot_cap=100,
        veh_cap=10,
    )
    da_data, _ = build_direct_allocation_data(inst, radius=5.0)
    assigned, routing_set = assign_da_clients(inst, da_data)
    assert 1 in assigned.get(1, [])
    assert 2 in routing_set


def test_assign_cumulative_cap_limit():
    # depot_cap=20: client 1 demand=15 → fits (0+15≤20) → assigned
    #               client 2 demand=10 → doesn't fit (15+10=25>20) → routing
    inst = _simple_inst(
        [(0.0, 0.0)],
        [(1.0, 0.0), (2.0, 0.0)],
        demands=[15, 10],
        depot_cap=20,
        veh_cap=10,
    )
    da_data, _ = build_direct_allocation_data(inst, radius=10.0)
    assigned, routing_set = assign_da_clients(inst, da_data)
    assert 1 in assigned.get(1, [])
    assert 2 in routing_set


def test_assign_uses_actual_depot_cap_not_discretized():
    # depot_cap=35, veh_cap=10 → old code: da_cap=30 (floor(35/10)*10)
    #                           → new code: da_cap=35 (actual)
    # client demands [15, 12] → total=27 ≤ 35 → both assigned (new)
    #                          → total=27 ≤ 30 → both assigned (old too, same here)
    # Use demand=33 to distinguish: 33 ≤ 35 (new: assigned) vs 33 > 30 (old: routing)
    inst = _simple_inst(
        [(0.0, 0.0)],
        [(1.0, 0.0)],
        demands=[33],
        depot_cap=35,
        veh_cap=10,
    )
    da_data, _ = build_direct_allocation_data(inst, radius=10.0)
    assigned, routing_set = assign_da_clients(inst, da_data)
    # 33 ≤ 35 → assigned, not in routing
    assert 1 in assigned.get(1, [])
    assert 1 not in routing_set


def test_assign_global_sort_two_clients_two_depots():
    # depot 1 at (0,0), depot 2 at (10,0)
    # client 1 at (1,0): dist to d1=1, dist to d2=9   → nearest: d1
    # client 2 at (9,0): dist to d1=9, dist to d2=1   → nearest: d2
    # global sort: [(1,d1,c1), (1,d2,c2), (9,d1,c2), (9,d2,c1)]
    # c1 → d1, c2 → d2
    inst = _simple_inst(
        [(0.0, 0.0), (10.0, 0.0)],
        [(1.0, 0.0), (9.0, 0.0)],
        demands=[5, 5],
        depot_cap=100,
        veh_cap=10,
    )
    da_data, _ = build_direct_allocation_data(inst, radius=15.0)
    assigned, routing_set = assign_da_clients(inst, da_data)
    assert 1 in assigned.get(1, [])  # client 1 → depot 1
    assert 2 in assigned.get(2, [])  # client 2 → depot 2
    assert not routing_set
