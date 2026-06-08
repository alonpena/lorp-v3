"""Phase 3 — solution parsing, cost reconstruction, capacity + feasibility audit.

Uses a deterministic short solve of the row-0 relaxed model (seed=0) as the
fixture. The trivial structure (route the 2 DA-uncoverable clients, DA the rest)
is found reliably.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from lorp_fsd import (
    audit_capacity,
    audit_feasibility,
    build_facility_design,
    build_relaxed_model,
    build_scaled_geometry,
    comparison_metric,
    load_row,
    parse_dat,
    parse_solution,
    penalty_distance_threshold,
    reconstruct_cost,
)
from lorp_fsd.cost_reconstruction import GAP, NEGATIVE_GAP, RELAXATION_DEVIATION

ROOT = Path(__file__).resolve().parents[1]
ROW0_DAT = ROOT / "instances" / "r40x5a-1.dat"
XLSX = ROOT / "results_MILP.xlsx"

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def solved():
    from pyvrp.stop import MaxRuntime

    inst = parse_dat(ROW0_DAT)
    cfg = load_row(XLSX, 0)
    geom = build_scaled_geometry(inst)
    design = build_facility_design(inst, cfg)
    model, info = build_relaxed_model(inst, cfg, geom, design)
    res = model.solve(stop=MaxRuntime(3), seed=0, display=False)
    parsed = parse_solution(res, model, info, inst, geom, cfg)
    cost = reconstruct_cost(parsed, inst, cfg, design)
    cap = audit_capacity(parsed, design)
    feas = audit_feasibility(parsed, cap, inst, cfg, geom)
    metric = comparison_metric(cost.total, cfg.UB, feas.fully_feasible)
    return dict(inst=inst, cfg=cfg, parsed=parsed, cost=cost, cap=cap, feas=feas, metric=metric)


# ── parser ─────────────────────────────────────────────────────────────────
def test_parser_recovers_one_route_and_38_da(solved):
    p = solved["parsed"]
    assert p.n_routing_routes == 1
    assert p.n_da_assignments == 38


def test_all_clients_served_exactly_once(solved):
    p = solved["parsed"]
    assert p.served_exactly_once
    assert p.missing_clients == set()
    assert p.duplicate_clients == set()
    assert len(p.service_by_client) == 40


def test_routing_route_is_the_two_uncovered_clients(solved):
    r = solved["parsed"].routes[0]
    assert r.depot_id == 3
    assert set(r.client_sequence) == {1, 33}
    assert r.demand == 85


def test_da_binding_and_radius_hold(solved):
    p, cfg = solved["parsed"], solved["cfg"]
    assert p.binding_violations == []
    assert all(a.binding_ok for a in p.da_assignments)
    assert all(a.dist_scaled <= cfg.R for a in p.da_assignments)


# ── cost reconstruction ────────────────────────────────────────────────────
def test_cost_direct_all_zero_when_fa_zero(solved):
    assert solved["cfg"].F_A == 0
    assert solved["cost"].cost_direct_all == 0.0


def test_cost_depots_is_300(solved):
    assert solved["cost"].cost_depots == pytest.approx(300.0)


def test_cost_routing_close_to_95_3087(solved):
    assert solved["cost"].cost_routing == pytest.approx(95.3087, abs=1e-2)


def test_total_close_to_395_3087(solved):
    assert solved["cost"].total == pytest.approx(395.3087, abs=1e-2)


def test_cost_vehicles_zero(solved):
    # veh_fixed = 0 on this instance
    assert solved["cost"].cost_vehicles == 0.0


# ── capacity + feasibility audit ───────────────────────────────────────────
def test_capacity_audit_components_sum(solved):
    cap = solved["cap"]
    for rec in cap.by_depot.values():
        assert rec.demand_total == rec.demand_routing + rec.demand_da
        assert rec.excess == max(0.0, rec.demand_total - rec.capacity)


def test_capacity_feasible_row0(solved):
    # the relaxed solution happens to be capacity-feasible for row 0 (seed 0)
    cap = solved["cap"]
    assert cap.capacity_feasible
    assert cap.overloaded_depots == []


def test_no_penalty_distance_suspected(solved):
    feas = solved["feas"]
    assert not feas.penalty_distance_suspected
    # sanity: threshold is the spec value
    assert penalty_distance_threshold(solved["cfg"].Length) == 1_000_000.0


def test_route_length_and_capacity_respected(solved):
    feas = solved["feas"]
    assert feas.route_length_violations == []
    assert feas.route_capacity_violations == []
    assert feas.da_radius_violations == []
    assert feas.fully_feasible


# ── comparison metric ──────────────────────────────────────────────────────
def test_metric_is_gap_near_zero_without_spurious_negative_flag(solved):
    m = solved["metric"]
    assert m.label == GAP
    assert m.value == pytest.approx(0.0, abs=1e-3)
    # the -1e-6 rounding-level gap must NOT raise a modeling-inconsistency flag
    assert NEGATIVE_GAP not in m.flags


def test_metric_relaxation_deviation_when_infeasible():
    # unit-level check of the metric selection (no solve needed)
    from lorp_fsd import comparison_metric
    m = comparison_metric(z_pyvrp=380.0, ub_milp=395.309, fully_feasible=False)
    assert m.label == RELAXATION_DEVIATION
    assert m.value == pytest.approx((395.309 - 380.0) / 395.309)


def test_metric_flags_material_negative_gap():
    from lorp_fsd import comparison_metric
    m = comparison_metric(z_pyvrp=350.0, ub_milp=395.309, fully_feasible=True)
    assert m.label == GAP
    assert NEGATIVE_GAP in m.flags
