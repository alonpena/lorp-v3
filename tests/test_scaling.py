from __future__ import annotations

from pathlib import Path

import pytest

from lorp_fsd.dat_parser import parse_dat
from lorp_fsd.scaling import PYVRP_INT_SCALE, build_scaled_geometry

ROOT = Path(__file__).resolve().parents[1]
ROW0_DAT = ROOT / "instances" / "r40x5a-1.dat"

# Congruency-verified constants (docs/C_CONGRUENCY_TEST.md).
EXPECTED_MAX_DIST = 125.39936203984452
EXPECTED_SCALE = 100.0 / EXPECTED_MAX_DIST  # 0.79745222...


@pytest.fixture(scope="module")
def geom():
    return build_scaled_geometry(parse_dat(ROW0_DAT))


def test_max_dist_and_scale(geom):
    assert geom.max_dist == pytest.approx(EXPECTED_MAX_DIST, abs=1e-9)
    assert geom.scale == pytest.approx(EXPECTED_SCALE, abs=1e-12)
    assert geom.scale == pytest.approx(0.79745222, abs=1e-8)


def test_dist_scaled_known_pair(geom):
    # depot d3 (4,44) -> client 1 (1,4): raw hypot(3,40)=40.1123, scaled *0.797452
    s = geom.depot_client_scaled(3, 1)
    assert s == pytest.approx(40.112344 * EXPECTED_SCALE, rel=1e-6)


def test_row0_single_route_reconstructs_cost_routing(geom):
    # Route d3 -> client1 -> client33 -> d3, F_R = 1, must equal Excel Cost Routing.
    d3 = geom.depot_xy[3]
    c1 = geom.client_xy[1]
    c33 = geom.client_xy[33]
    route = (
        geom.dist_scaled(d3, c1)
        + geom.dist_scaled(c1, c33)
        + geom.dist_scaled(c33, d3)
    )
    assert route == pytest.approx(95.3087, abs=1e-3)


def test_R_and_Length_are_scaled_units(geom):
    # R=30, Length=100 are stored as-is (scaled). Their raw equivalents:
    assert geom.raw_from_scaled(30) == pytest.approx(37.620, abs=1e-3)
    assert geom.raw_from_scaled(100) == pytest.approx(geom.max_dist, abs=1e-6)


def test_integer_discretization(geom):
    assert PYVRP_INT_SCALE == 10_000
    assert geom.to_int(95.3087) == round(95.3087 * 10_000)
    # round(Length * scale_factor) for Length=100
    assert geom.to_int(100) == 1_000_000


def test_other_problem_id_fails_loudly():
    with pytest.raises(NotImplementedError):
        build_scaled_geometry(parse_dat(ROW0_DAT), problem_id=1)
