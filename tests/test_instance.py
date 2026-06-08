from __future__ import annotations

from pathlib import Path

import pytest

from lorp_fsd.dat_parser import parse_dat
from lorp_fsd.excel_loader import load_row
from lorp_fsd.instance import build_facility_design

ROOT = Path(__file__).resolve().parents[1]
ROW0_DAT = ROOT / "instances" / "r40x5a-1.dat"
XLSX = ROOT / "results_MILP.xlsx"


@pytest.fixture(scope="module")
def design():
    inst = parse_dat(ROW0_DAT)
    cfg = load_row(XLSX, 0)
    return build_facility_design(inst, cfg)


def test_active_depots_match_excel(design):
    assert design.active_depot_ids == (1, 2, 3, 5)


def test_capacities_match_excel(design):
    assert design.capacity_by_depot == {1: 875.0, 2: 875.0, 3: 875.0, 5: 875.0}
    assert design.mismatches() == []
    assert all(d.capacity_matches_excel for d in design.depots.values())


def test_total_depot_cost_is_300(design):
    # recomputed via C formula; must equal Excel Cost (Depots)
    assert design.total_cost == pytest.approx(300.0)


def test_selected_depot_not_in_instance_raises():
    inst = parse_dat(ROW0_DAT)
    cfg = load_row(XLSX, 0)
    from dataclasses import replace
    from lorp_fsd.experiment_config import SelectedDepot

    bad = dict(cfg.selected_depots)
    bad[99] = SelectedDepot(99, 1, 875.0)
    bad_cfg = replace(cfg, selected_depots=bad)
    with pytest.raises(ValueError):
        build_facility_design(inst, bad_cfg)
