from __future__ import annotations

from pathlib import Path

import pytest

from lorp_fsd.dat_parser import parse_dat
from lorp_fsd.excel_loader import load_row
from lorp_fsd.instance import build_facility_design
from lorp_fsd.scaling import PYVRP_INT_SCALE, build_scaled_geometry
from lorp_fsd.pyvrp_builder import build_relaxed_model, routing_vehicle_specs

ROOT = Path(__file__).resolve().parents[1]
ROW0_DAT = ROOT / "instances" / "r40x5a-1.dat"
XLSX = ROOT / "results_MILP.xlsx"


@pytest.fixture(scope="module")
def ctx():
    inst = parse_dat(ROW0_DAT)
    cfg = load_row(XLSX, 0)
    geom = build_scaled_geometry(inst)
    design = build_facility_design(inst, cfg)
    return inst, cfg, geom, design


@pytest.fixture(scope="module")
def built(ctx):
    inst, cfg, geom, design = ctx
    model, info = build_relaxed_model(inst, cfg, geom, design)
    return model, info


# ── routing vehicle decomposition ──────────────────────────────────────────
def test_routing_vehicle_specs_full_and_residual():
    # Cap=875, Q=340 -> floor(875/340)=2 full (340) + residual 195
    specs = routing_vehicle_specs(875, 340, depot_id=3)
    full = [s for s in specs if s.kind == "full"]
    resid = [s for s in specs if s.kind == "residual"]
    assert len(full) == 1 and full[0].num_available == 2 and full[0].capacity == 340
    assert len(resid) == 1 and resid[0].num_available == 1 and resid[0].capacity == 195


def test_routing_vehicle_specs_no_residual_when_exact():
    specs = routing_vehicle_specs(680, 340, depot_id=1)  # 2*340 exactly
    assert all(s.kind == "full" for s in specs)
    assert sum(s.num_available for s in specs) == 2


def test_row0_routing_capacity_per_open_depot(built):
    _, info = built
    # 4 open depots, each Cap 875 -> 2*340 + 195 = 875 routing capacity each
    for did in (1, 2, 3, 5):
        assert info.routing_capacity(did) == 875
    # total routing vehicles = 4 depots * (2 full + 1 residual) = 12
    assert info.n_routing_vehicles == 12


# ── DA options / single-client binding ─────────────────────────────────────
def test_da_feasible_option_count_matches_pairs(built):
    _, info = built
    assert len(info.da_options) == len(info.da_pairs)
    # all DA vehicle metas are single-client bound
    da_meta = [v for v in info.vehicle_type_meta if v.mode == "direct_allocation"]
    assert len(da_meta) == len(info.da_options)
    assert all(v.client_id is not None for v in da_meta)
    assert all(v.num_available == 1 for v in da_meta)


def test_da_single_client_binding_via_profile(built):
    # under each DA profile, only the bound client is reachable from its depot;
    # all other clients are the 2**44 sentinel (unreachable).
    import numpy as np

    model, info = built
    data = model.data()
    profiles = {p.name: idx for idx, p in enumerate(model.profiles)}
    # pick one DA option and verify its profile reachability
    opt = info.da_options[0]
    pidx = profiles[f"da_d{opt.depot_id}_c{opt.client_id}"]
    dm = np.array(data.distance_matrix(pidx))
    sentinel = dm.max()
    assert sentinel > 10**12  # the huge default for missing edges
    # exactly the depot<->client pair is finite among off-diagonal entries
    finite_offdiag = (dm < sentinel) & ~np.eye(dm.shape[0], dtype=bool)
    # each row has at most 1 finite off-diagonal reachable target under a DA profile
    assert finite_offdiag.sum() <= 2  # depot->client and client->depot


def test_zero_return_da(built):
    # DA outbound duration cost present (or 0 if F_A=0); return duration == 0
    model, info = built
    import numpy as np
    data = model.data()
    profiles = {p.name: idx for idx, p in enumerate(model.profiles)}
    opt = info.da_options[0]
    pidx = profiles[f"da_d{opt.depot_id}_c{opt.client_id}"]
    dur = np.array(data.duration_matrix(pidx))
    # locate depot and client location indices via names
    names = [loc.name for loc in model.locations]
    di = names.index(f"d{opt.depot_id}")
    ci = names.index(f"c{opt.client_id}")
    assert dur[ci][di] == 0  # zero-return cost


# ── forbidden routing assignments ──────────────────────────────────────────
def test_forbidden_routing_removes_routing_not_da(ctx):
    inst, cfg, geom, design = ctx
    # choose a (depot, client) that is BOTH routing-allowed and DA-feasible
    from lorp_fsd.da_options import build_da_options
    opts = build_da_options(inst, cfg, geom, design)
    target = opts[0].pair  # a real DA-feasible open-depot/client pair
    i, j = target

    model, info = build_relaxed_model(
        inst, cfg, geom, design, forbidden_routing_assignments=frozenset({target})
    )
    # routing reachability: client j no longer routable from depot i ...
    assert j not in info.routing_reachable[i]
    # ... but still routable from other open depots
    for h in design.active_depot_ids:
        if h != i:
            assert j in info.routing_reachable[h]
    # ... and DA from the same depot i is preserved
    assert target in info.da_pairs


def test_forbidden_does_not_change_da_options(ctx):
    inst, cfg, geom, design = ctx
    _, base = build_relaxed_model(inst, cfg, geom, design)
    _, forb = build_relaxed_model(
        inst, cfg, geom, design, forbidden_routing_assignments=frozenset({(3, 5)})
    )
    assert base.da_pairs == forb.da_pairs


# ── integerization ─────────────────────────────────────────────────────────
def test_route_length_and_edge_costs_use_int_scale(built):
    _, info = built
    assert info.int_scale == PYVRP_INT_SCALE == 10_000
    # Length = 100 -> route_max_distance_int = 1_000_000
    assert info.route_max_distance_int == round(100 * PYVRP_INT_SCALE)
    assert info.route_max_distance_int == 1_000_000


def test_model_builds_to_valid_problemdata(built):
    model, info = built
    data = model.data()
    assert data.num_clients == 40
    # vehicle *count* = 12 (2 full @340 + 1 residual @195, per 4 depots)
    assert info.n_routing_vehicles == 12
    # vehicle *types* = routing types (8 = 4 depots x {full, residual}) + one per DA option
    assert len(info.routing_vehicles) == 8
    assert data.num_vehicle_types == len(info.routing_vehicles) + len(info.da_options)


def test_unsupported_problem_id_blocks_build(ctx):
    from dataclasses import replace
    inst, cfg, geom, design = ctx
    # bypass ExperimentConfig guard by forcing the field post-construction
    object.__setattr__(cfg, "problem_id", 1)
    try:
        with pytest.raises(NotImplementedError):
            build_relaxed_model(inst, cfg, geom, design)
    finally:
        object.__setattr__(cfg, "problem_id", 0)
