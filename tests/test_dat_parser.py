from __future__ import annotations

from pathlib import Path

import pytest

from lorp_fsd.dat_parser import parse_dat, resolve_dat_path

ROOT = Path(__file__).resolve().parents[1]
ROW0_DAT = ROOT / "instances" / "r40x5a-1.dat"


@pytest.fixture(scope="module")
def row0():
    return parse_dat(ROW0_DAT)


def test_counts_and_scalars(row0):
    assert row0.n_clients == 40
    assert row0.n_depots == 5
    assert row0.max_depots_open == 5
    assert row0.n_vehicles == 40
    assert row0.vehicle_capacity == 340
    assert row0.vehicle_fixed_cost == 0
    assert row0.trailing_flag == 0


def test_ids_are_1_based(row0):
    assert sorted(row0.depots) == [1, 2, 3, 4, 5]
    assert min(row0.clients) == 1
    assert max(row0.clients) == 40


def test_depot_fields(row0):
    # depot 1 coords (25, 75); all base caps 1750; all fixed costs 100
    assert row0.depots[1].xy == (25.0, 75.0)
    assert row0.depots[3].xy == (4.0, 44.0)  # d3, the routing depot in row 0
    assert all(d.base_capacity == 1750 for d in row0.depots.values())
    assert all(d.fixed_cost == 100 for d in row0.depots.values())
    assert row0.total_fixed_cost == 500


def test_client_fields_and_total_demand(row0):
    assert row0.clients[1].xy == (1.0, 4.0)
    assert row0.clients[33].xy == (30.0, 1.0)
    assert row0.clients[1].demand == 17
    assert row0.clients[33].demand == 68
    assert row0.total_demand == 1931


def test_trailing_flag_validation():
    base = ["1", "1", "1", "1", "0 0", "0 5", "10", "200", "6", "100", "20"]
    # valid trailing flag
    inst = parse_dat(base + ["1"], name="t.dat")
    assert inst.trailing_flag == 1
    # absent trailing flag is allowed (robustness)
    inst2 = parse_dat(base, name="t.dat")
    assert inst2.trailing_flag is None
    # invalid trailing flag rejected
    with pytest.raises(ValueError):
        parse_dat(base + ["7"], name="t.dat")


def test_resolution_exact_and_identical_copies():
    res = resolve_dat_path("r40x5a-1.dat", root=ROOT)
    assert res.ok
    assert res.status == "EXACT"
    assert res.path == ROOT / "instances" / "r40x5a-1.dat"


def test_resolution_missing_is_reported_not_raised():
    res = resolve_dat_path("does-not-exist.dat", root=ROOT)
    assert not res.ok
    assert res.status == "MISSING"
    assert res.path is None
