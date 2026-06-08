from __future__ import annotations

from pathlib import Path

import pytest

from lorp_fsd.dat_parser import parse_dat
from lorp_fsd.excel_loader import load_row
from lorp_fsd.instance import build_facility_design
from lorp_fsd.scaling import PYVRP_INT_SCALE, build_scaled_geometry
from lorp_fsd.da_options import build_da_options, clients_with_da, da_pairs

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
def options(ctx):
    inst, cfg, geom, design = ctx
    return build_da_options(inst, cfg, geom, design)


def test_da_feasibility_uses_continuous_radius(ctx, options):
    inst, cfg, geom, design = ctx
    R = cfg.R
    for o in options:
        assert geom.depot_client_scaled(o.depot_id, o.client_id) <= R
    # every produced option is within radius; none exceeds R
    assert all(o.dist_scaled <= R for o in options)


def test_da_options_only_from_open_depots(ctx, options):
    inst, cfg, geom, design = ctx
    open_ids = set(design.active_depot_ids)
    assert {o.depot_id for o in options} <= open_ids
    assert 4 not in {o.depot_id for o in options}  # depot 4 is closed in row 0


def test_row0_da_covers_38_clients_2_uncovered(ctx, options):
    # congruency: exactly clients 1 and 33 are NOT DA-coverable by any open depot
    inst, cfg, geom, design = ctx
    covered = clients_with_da(options)
    uncovered = set(inst.clients) - covered
    assert uncovered == {1, 33}
    assert len(covered) == 38


def test_da_cost_is_one_way_and_F_A_zero_on_row0(ctx, options):
    # row 0 has F_A = 0 -> every DA cost_int is 0 (one-way, no return)
    inst, cfg, geom, design = ctx
    assert cfg.F_A == 0
    assert all(o.cost_int == 0 for o in options)


def test_da_cost_int_formula_with_nonzero_fa(ctx):
    # synthesize F_A=0.5 to verify integerized one-way cost formula
    from dataclasses import replace

    inst, cfg, geom, design = ctx
    cfg2 = replace(cfg, F_A=0.5)
    opts = build_da_options(inst, cfg2, geom, design)
    for o in opts:
        assert o.cost_int == round(0.5 * o.dist_scaled * PYVRP_INT_SCALE)
    assert any(o.cost_int > 0 for o in opts)


def test_da_pairs_independent_of_demand(ctx, options):
    inst, cfg, geom, design = ctx
    pairs = da_pairs(options)
    # each pair is (open_depot, client) and unique
    assert len(pairs) == len(options)
    for (i, j) in pairs:
        assert i in design.active_depot_ids
        assert j in inst.clients
