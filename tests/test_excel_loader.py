from __future__ import annotations

from pathlib import Path

import pytest

from lorp_fsd.excel_loader import load_lorp_fsd_rows, load_row

ROOT = Path(__file__).resolve().parents[1]
XLSX = ROOT / "results_MILP.xlsx"


@pytest.fixture(scope="module")
def row0():
    return load_row(XLSX, 0)


def test_row0_parameters(row0):
    assert row0.name == "r40x5a-1.dat"
    assert row0.F_R == 1
    assert row0.F_A == 0
    assert row0.R == 30
    assert row0.Length == 100
    assert row0.problem_id == 0
    assert row0.of == "cost"


def test_row0_objective_components(row0):
    assert row0.UB == pytest.approx(395.309, abs=1e-3)
    assert row0.cost_routing == pytest.approx(95.3087, abs=1e-4)
    assert row0.cost_vehicles == 0
    assert row0.cost_depots == pytest.approx(300.0)
    assert row0.cost_direct_all == 0
    assert row0.status == "Optimal"


def test_row0_selected_depots_real_ids(row0):
    # Depot4 label is 'd5' -> real depot id 5 (not slot 4)
    assert row0.active_depot_ids == (1, 2, 3, 5)
    assert row0.total_depots == 4
    assert row0.total_vehicles == 1
    for did in (1, 2, 3, 5):
        sd = row0.selected_depots[did]
        assert sd.size == 1
        assert sd.capacity == pytest.approx(875.0)
    # the single routing vehicle is at depot d3
    assert row0.selected_depots[3].vehicles == 1
    assert row0.selected_depots[1].vehicles == 0


def test_all_rows_loaded_and_problem_id_zero():
    rows = load_lorp_fsd_rows(XLSX)
    assert len(rows) > 1
    assert all(r.problem_id == 0 for r in rows)
    assert all(r.name for r in rows)  # no blank names slipped through
