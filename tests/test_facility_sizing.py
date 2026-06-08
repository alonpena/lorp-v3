from __future__ import annotations

from pathlib import Path

import pytest

from lorp_fsd.dat_parser import parse_dat
from lorp_fsd.facility_sizing import (
    SIZE_MULTIPLIERS,
    size_capacity,
    size_cost,
    validate_capacity,
)

ROOT = Path(__file__).resolve().parents[1]
ROW0_DAT = ROOT / "instances" / "r40x5a-1.dat"


def test_multipliers():
    assert SIZE_MULTIPLIERS == {1: 0.50, 2: 0.75, 3: 1.00, 4: 1.25, 5: 1.50}


@pytest.mark.parametrize(
    "size, cap",
    [(1, 875.0), (2, 1312.5), (3, 1750.0), (4, 2187.5), (5, 2625.0)],
)
def test_capacity_formula(size, cap):
    assert size_capacity(1750, size) == pytest.approx(cap)


@pytest.mark.parametrize(
    "size, cost",
    [(1, 75.0), (2, 87.5), (3, 100.0), (4, 112.5), (5, 125.0)],
)
def test_cost_formula(size, cost):
    # r40x5a-1: fixed=100, base=1750, total_fixed=500, n_depots=5
    assert size_cost(100, 1750, 500, 5, size) == pytest.approx(cost)


def test_row0_depot_cost_total_is_300():
    # 4 open depots, all size 1 -> 4 * 75 = 300 == Excel Cost (Depots)
    assert 4 * size_cost(100, 1750, 500, 5, 1) == pytest.approx(300.0)


def test_validate_capacity_against_excel():
    inst = parse_dat(ROW0_DAT)
    check = validate_capacity(inst, depot_id=1, size=1, capacity_excel=875.0)
    assert check.capacity_recomputed == pytest.approx(875.0)
    assert check.cost_recomputed == pytest.approx(75.0)
    assert check.capacity_match


def test_invalid_size_rejected():
    with pytest.raises(ValueError):
        size_capacity(1750, 0)
    with pytest.raises(ValueError):
        size_capacity(1750, 6)
