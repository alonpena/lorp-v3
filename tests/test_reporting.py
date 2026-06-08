from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from reporting import (
    build_full_report,
    compute_solution_costs,
    extract_kpis_level1,
    extract_kpis_level2,
    extract_solution_metrics,
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_trip(visits: list, delivery: list) -> MagicMock:
    trip = MagicMock()
    trip.visits.return_value = visits
    trip.delivery.return_value = delivery
    return trip


def _make_route(vt_idx: int, distance: float, trips_data: list) -> MagicMock:
    route = MagicMock()
    route.vehicle_type.return_value = vt_idx
    route.distance.return_value = distance
    route.trips.return_value = [_make_trip(**td) for td in trips_data]
    return route


def _make_res(routes: list) -> MagicMock:
    sol = MagicMock()
    sol.routes.return_value = routes
    sol.distance.return_value = sum(r.distance() for r in routes)
    res = MagicMock()
    res.best = sol
    return res


# Standard scenario:
# route 0 → routing, depot 1, dist=100, delivers demand=11 to 2 clients
# route 1 → DA,      depot 2, dist=60,  delivers demand=4  to 1 client
_VEH_TYPES = [
    {"type": "routing", "depot": 1},
    {"type": "direct_allocation", "depot": 2},
]
_INFO = {"vehicle_types": _VEH_TYPES, "escala": 1.0}


def _std_res():
    routes = [
        _make_route(0, 100.0, [{"visits": [1, 2], "delivery": [11]}]),
        _make_route(1, 60.0,  [{"visits": [3],    "delivery": [4]}]),
    ]
    return _make_res(routes)


# ── compute_solution_costs ────────────────────────────────────────────────────

def test_compute_solution_costs_math(minimal_instance, minimal_spec):
    kpis1 = {
        "routing": {"distance": 200.0, "n_vehicles": 2},
        "direct_allocation": {"distance": 100.0},
    }
    costs = compute_solution_costs(None, kpis1, minimal_spec, minimal_instance, scale=1.0)
    # PyVRP distances are scaled-only; costs apply F_R/F_A ex post.
    # routing=200*1.0=200, da=100*0.5=50, vehicles=40, depots=100 → total=390
    assert costs["cost_routing"] == pytest.approx(200.0)
    assert costs["cost_da"] == pytest.approx(50.0)
    assert costs["vehicle_cost"] == pytest.approx(40.0)
    assert costs["depot_cost"] == pytest.approx(100.0)
    assert costs["total_cost"] == pytest.approx(390.0)


def test_compute_solution_costs_gap(minimal_instance, minimal_spec):
    kpis1 = {
        "routing": {"distance": 200.0, "n_vehicles": 2},
        "direct_allocation": {"distance": 100.0},
    }
    costs = compute_solution_costs(None, kpis1, minimal_spec, minimal_instance, scale=1.0)
    # UB=500, total=390 → abs_gap=abs(390-500)/500=0.22
    assert costs["gap"] == pytest.approx(0.22)
    assert costs["raw_gap_pyvrp_minus_milp"] == pytest.approx(-0.22)


def test_compute_solution_costs_zero_ub(minimal_instance, minimal_spec):
    from dataclasses import replace
    spec = replace(minimal_spec, UB=0.0)
    kpis1 = {"routing": {"distance": 0.0, "n_vehicles": 0}, "direct_allocation": {"distance": 0.0}}
    costs = compute_solution_costs(None, kpis1, spec, minimal_instance, scale=1.0)
    assert costs["gap"] is None


def test_compute_solution_costs_scale_not_recovered(minimal_instance, minimal_spec):
    kpis1 = {"routing": {"distance": 200.0, "n_vehicles": 0}, "direct_allocation": {"distance": 0.0}}
    costs = compute_solution_costs(None, kpis1, minimal_spec, minimal_instance, scale=2.0)
    # Cost uses scaled distance times F_R; no /scale recovery.
    assert costs["routing_distance_scaled"] == pytest.approx(200.0)
    assert costs["cost_routing"] == pytest.approx(200.0)


# ── extract_solution_metrics ──────────────────────────────────────────────────

def test_extract_solution_metrics_keys(adapted_instance):
    res = _std_res()
    kpis1 = {
        "routing": {"distance": 100.0},
        "direct_allocation": {"distance": 60.0},
    }
    metrics = extract_solution_metrics(res, kpis1, adapted_instance)
    for key in ("routing_dist", "da_dist", "n_vehicles", "vehicle_cost", "depot_cost", "F_R", "F_A"):
        assert key in metrics, f"missing key: {key}"


def test_extract_solution_metrics_n_vehicles(adapted_instance):
    routes = [_make_route(0, 50.0, [{"visits": [1], "delivery": [5]}])]
    res = _make_res(routes)
    kpis1 = {"routing": {"distance": 50.0}, "direct_allocation": {"distance": 0.0}}
    metrics = extract_solution_metrics(res, kpis1, adapted_instance)
    assert metrics["n_vehicles"] == 1


def test_extract_solution_metrics_depot_cost_zero(adapted_instance):
    # adapt_instance zeros all depot fixed costs
    res = _std_res()
    kpis1 = {"routing": {"distance": 0.0}, "direct_allocation": {"distance": 0.0}}
    metrics = extract_solution_metrics(res, kpis1, adapted_instance)
    assert metrics["depot_cost"] == pytest.approx(0.0)


# ── extract_kpis_level1 ───────────────────────────────────────────────────────

def test_kpis_level1_routing_distance(minimal_instance):
    res = _std_res()
    kpis = extract_kpis_level1(minimal_instance, res, _INFO)
    assert kpis["routing"]["distance"] == pytest.approx(100.0)


def test_kpis_level1_da_distance(minimal_instance):
    res = _std_res()
    kpis = extract_kpis_level1(minimal_instance, res, _INFO)
    assert kpis["direct_allocation"]["distance"] == pytest.approx(60.0)


def test_kpis_level1_total_distance(minimal_instance):
    res = _std_res()
    kpis = extract_kpis_level1(minimal_instance, res, _INFO)
    assert kpis["total_distance"] == pytest.approx(160.0)


def test_kpis_level1_total_demand(minimal_instance):
    # minimal_instance clients: demand 6+5+4=15
    res = _std_res()
    kpis = extract_kpis_level1(minimal_instance, res, _INFO)
    assert kpis["total_demand"] == pytest.approx(15.0)


def test_kpis_level1_served_demand(minimal_instance):
    res = _std_res()
    kpis = extract_kpis_level1(minimal_instance, res, _INFO)
    # route0 delivers 11, route1 delivers 4 → 15
    assert kpis["served_demand"] == pytest.approx(15.0)


def test_kpis_level1_routing_n_vehicles(minimal_instance):
    res = _std_res()
    kpis = extract_kpis_level1(minimal_instance, res, _INFO)
    assert kpis["routing"]["n_vehicles"] == 1


def test_kpis_level1_da_n_vehicles(minimal_instance):
    res = _std_res()
    kpis = extract_kpis_level1(minimal_instance, res, _INFO)
    assert kpis["direct_allocation"]["n_vehicles"] == 1


# ── extract_kpis_level2 ───────────────────────────────────────────────────────

def test_kpis_level2_per_depot_keys(minimal_instance):
    res = _std_res()
    kpis2 = extract_kpis_level2(minimal_instance, res, _INFO)
    assert 1 in kpis2 and 2 in kpis2


def test_kpis_level2_depot1_routing_distance(minimal_instance):
    res = _std_res()
    kpis2 = extract_kpis_level2(minimal_instance, res, _INFO)
    assert kpis2[1]["routing"]["distance"] == pytest.approx(100.0)


def test_kpis_level2_depot2_da_distance(minimal_instance):
    res = _std_res()
    kpis2 = extract_kpis_level2(minimal_instance, res, _INFO)
    assert kpis2[2]["direct_allocation"]["distance"] == pytest.approx(60.0)


# ── build_full_report ─────────────────────────────────────────────────────────

def _report_inst():
    """Instance where depot caps are > any plausible delivery in tests."""
    from dat_loader import Instance
    return Instance(
        depots={
            1: {"x": 0.0, "y": 0.0, "cap": 200, "fixed_cost": 0.0},
            2: {"x": 10.0, "y": 0.0, "cap": 150, "fixed_cost": 0.0},
        },
        clients={
            1: {"x": 0.0, "y": 5.0, "demand": 6},
            2: {"x": 10.0, "y": 5.0, "demand": 5},
            3: {"x": 5.0, "y": 5.0, "demand": 4},
        },
        data={"veh_cap": 10, "veh_fixed_cost": 20.0},
    )


def test_build_full_report_no_capacity_violation(minimal_spec):
    inst = _report_inst()
    res = _std_res()  # delivers 11 to d1 (cap=200), 4 to d2 (cap=150)
    row = build_full_report(inst, res, minimal_spec, _INFO)
    assert row["violacion_capacidad"] is False


def test_build_full_report_capacity_violation(minimal_spec):
    inst = _report_inst()
    # make route 0 deliver 300 to depot 1 (cap=200) → violation
    routes = [
        _make_route(0, 100.0, [{"visits": [1], "delivery": [300]}]),
        _make_route(1, 60.0,  [{"visits": [2], "delivery": [4]}]),
    ]
    res = _make_res(routes)
    row = build_full_report(inst, res, minimal_spec, _INFO)
    assert row["violacion_capacidad"] is True


def test_build_full_report_service_level_full(minimal_spec):
    inst = _report_inst()
    res = _std_res()  # delivers 11+4=15, total demand=15
    row = build_full_report(inst, res, minimal_spec, _INFO)
    assert row["nivel_servicio"] == pytest.approx(1.0)


def test_build_full_report_service_level_partial(minimal_spec):
    inst = _report_inst()
    # deliver only 7 out of 15
    routes = [_make_route(0, 50.0, [{"visits": [1], "delivery": [7]}])]
    res = _make_res(routes)
    row = build_full_report(inst, res, minimal_spec, _INFO)
    assert row["nivel_servicio"] == pytest.approx(7 / 15)


def test_build_full_report_total_cost_math(minimal_spec):
    inst = _report_inst()
    res = _std_res()  # 1 routing vehicle, dist_routing=100, dist_da=60, escala=1.0
    row = build_full_report(inst, res, minimal_spec, _INFO)
    # routing = 100 * F_R=1.0 = 100
    # DA = 60 * F_A=0.5 = 30
    # n_veh_routing = 1 → costo_vehiculos = 1*20 = 20
    # costo_depositos = 100 (from minimal_spec)
    # total = 250
    assert row["costo_total_pyvrp"] == pytest.approx(250.0)


def test_build_full_report_gap_final(minimal_spec):
    inst = _report_inst()
    res = _std_res()
    row = build_full_report(inst, res, minimal_spec, _INFO)
    # ub=500, total=250 → abs_gap=abs(250-500)/500 = 0.50
    assert row["gap_final"] == pytest.approx(abs(250.0 - 500.0) / 500.0)
    assert row["raw_gap_pyvrp_minus_milp"] == pytest.approx((250.0 - 500.0) / 500.0)


def test_build_full_report_per_depot_keys(minimal_spec):
    inst = _report_inst()
    res = _std_res()
    row = build_full_report(inst, res, minimal_spec, _INFO)
    assert "d1_capacidad" in row
    assert "d2_capacidad" in row


def test_build_full_report_contains_config_fields(minimal_spec):
    inst = _report_inst()
    res = _std_res()
    row = build_full_report(inst, res, minimal_spec, _INFO)
    assert row["F_R"] == minimal_spec.F_R
    assert row["F_A"] == minimal_spec.F_A
    assert row["R"] == minimal_spec.R
