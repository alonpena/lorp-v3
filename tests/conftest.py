from __future__ import annotations

import pytest

from dat_loader import Instance

# ── Minimal .dat source (2 depots, 3 clients) ───────────────────────────────
# depot 1: (0,0) cap=200  depot 2: (10,0) cap=150
# client 1: (0,5) demand=6   client 2: (10,5) demand=5   client 3: (5,5) demand=4
# veh_cap=10   veh_fixed_cost=20.0   no cola
MINIMAL_DAT = """\
3
2
2
4
0.0 0.0
10.0 0.0
0.0 5.0
10.0 5.0
5.0 5.0
10
200
150
6
5
4
100.0
50.0
20.0
"""

MINIMAL_DAT_WITH_COLA = MINIMAL_DAT.rstrip() + "\n99\n"


@pytest.fixture
def minimal_instance() -> Instance:
    return Instance.from_dat(MINIMAL_DAT.splitlines())


@pytest.fixture
def minimal_spec():
    from instance_adapter import ExcelSpec

    return ExcelSpec(
        row_id=0,
        instance="test.dat",
        R=8.0,
        F_R=1.0,
        F_A=0.5,
        Length=100.0,
        UB=500.0,
        status="Optimal",
        gap=0.0,
        cost_depots=100.0,
        vehicle_cost_milp=50.0,
        routing_cost_milp=200.0,
        da_cost_milp=80.0,
        depots={
            1: {"label": "d1", "capacity": 200.0},
            2: {"label": "d2", "capacity": 150.0},
        },
        depots_milp={
            1: {"demand": 80.0, "usage": 0.4, "vehicles": 2.0},
            2: {"demand": 60.0, "usage": 0.4, "vehicles": 1.0},
        },
    )


@pytest.fixture
def adapted_instance(minimal_instance, minimal_spec):
    from instance_adapter import adapt_instance

    return adapt_instance(minimal_instance, minimal_spec)
