"""Tests for Phase 9 repair modes: hard_forbid / soft_penalty / tabu_penalty."""
from __future__ import annotations

from pathlib import Path

import pytest

from lorp_fsd.penalty_tabu import (
    ACTION_HARD_FORBID,
    ACTION_SOFT_PENALTY,
    ACTION_TABU_ADD,
    ACTION_TABU_EXPIRE,
    DEFAULT_REPAIR_MODE,
    REPAIR_MODE_HARD_FORBID,
    REPAIR_MODE_SOFT_PENALTY,
    REPAIR_MODE_TABU_PENALTY,
    RepairModeState,
    penalty_value_int,
)


# ── pure unit tests (no pyvrp) ──────────────────────────────────────────────────

def test_default_repair_mode_is_tabu_penalty():
    assert DEFAULT_REPAIR_MODE == REPAIR_MODE_TABU_PENALTY
    assert RepairModeState().mode == REPAIR_MODE_TABU_PENALTY


def test_unknown_mode_rejected():
    with pytest.raises(ValueError):
        RepairModeState(mode="nope")


def test_penalty_value_int_formula():
    assert penalty_value_int(100, 1_000_000) == 100_000_000
    assert penalty_value_int(2.5, 1000) == 2500


def test_hard_forbid_removes_pair_no_penalty():
    st = RepairModeState(mode=REPAIR_MODE_HARD_FORBID, penalty_value=999, tabu_tenure=3)
    st.apply({(1, 7)}, iteration=0)
    forbidden, penalty = st.builder_args()
    assert (1, 7) in forbidden
    assert penalty is None
    assert st.suppressed_pairs() == {(1, 7)}
    assert st.events[0]["action"] == ACTION_HARD_FORBID
    assert st.events[0]["penalty_value"] == ""


def test_soft_penalty_keeps_pair_feasible():
    st = RepairModeState(mode=REPAIR_MODE_SOFT_PENALTY, penalty_value=500, tabu_tenure=3)
    st.apply({(1, 7)}, iteration=0)
    forbidden, penalty = st.builder_args()
    assert forbidden == frozenset()  # pair NOT removed -> still routable
    assert penalty == {(1, 7): 500}
    assert st.suppressed_pairs() == {(1, 7)}
    assert st.events[0]["action"] == ACTION_SOFT_PENALTY
    assert st.events[0]["penalty_value"] == 500


def test_soft_penalty_never_expires_on_tick():
    st = RepairModeState(mode=REPAIR_MODE_SOFT_PENALTY, penalty_value=500)
    st.apply({(1, 7)}, iteration=0)
    for it in range(1, 5):
        st.tick(it)
    assert st.builder_args()[1] == {(1, 7): 500}  # no tabu in soft mode


def test_tabu_decrement_and_expire():
    st = RepairModeState(mode=REPAIR_MODE_TABU_PENALTY, penalty_value=500, tabu_tenure=2)
    st.apply({(1, 7)}, iteration=0)
    assert st.tabu[(1, 7)] == 2
    assert st.penalty == {(1, 7): 500}

    st.tick(1)
    assert st.tabu[(1, 7)] == 1
    assert (1, 7) in st.penalty  # still penalised

    st.tick(2)  # tenure hits 0 -> expire
    assert (1, 7) not in st.tabu
    assert (1, 7) not in st.penalty
    assert st.suppressed_pairs() == set()
    expire = [e for e in st.events if e["action"] == ACTION_TABU_EXPIRE]
    assert expire and expire[0]["client_id"] == 7


def test_tabu_add_event_carries_saving_demand():
    st = RepairModeState(mode=REPAIR_MODE_TABU_PENALTY, penalty_value=500, tabu_tenure=3)
    st.apply(
        {(1, 7)}, iteration=0,
        saving_by_pair={(1, 7): 12.5}, demand_by_pair={(1, 7): 40.0},
    )
    ev = st.events[0]
    assert ev["action"] == ACTION_TABU_ADD
    assert ev["tabu_remaining"] == 3
    assert ev["saving"] == 12.5
    assert ev["demand"] == 40.0


# ── repair_trace extension ──────────────────────────────────────────────────────

def test_repair_trace_includes_mode_and_events(tmp_path):
    from lorp_fsd.artifacts import REPAIR_TRACE_COLUMNS, write_repair_trace_csv
    import csv

    for col in ["repair_mode", "penalty_value", "tabu_remaining", "saving", "demand"]:
        assert col in REPAIR_TRACE_COLUMNS

    events = [
        {"iteration": 0, "action": ACTION_TABU_ADD, "depot_id": 1, "client_id": 7,
         "penalty_value": 500, "tabu_remaining": 3, "saving": 12.5, "demand": 40.0, "reason": ""},
        {"iteration": 2, "action": ACTION_TABU_EXPIRE, "depot_id": 1, "client_id": 7,
         "penalty_value": "", "tabu_remaining": 0, "saving": "", "demand": "", "reason": "tabu_tenure_expired"},
    ]
    path = write_repair_trace_csv(
        tmp_path, iterations=[], final_status="FEASIBLE",
        repair_mode="tabu_penalty", events=events,
    )
    rows = list(csv.DictReader(path.open(newline="")))
    assert len(rows) == 2
    assert {r["action"] for r in rows} == {ACTION_TABU_ADD, ACTION_TABU_EXPIRE}
    assert all(r["repair_mode"] == "tabu_penalty" for r in rows)
    add = next(r for r in rows if r["action"] == ACTION_TABU_ADD)
    assert add["penalty_value"] == "500"
    assert add["tabu_remaining"] == "3"


# ── builder integration (real instance + pyvrp) ─────────────────────────────────

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def ctx():
    from lorp_fsd.dat_parser import parse_dat
    from lorp_fsd.excel_loader import load_row
    from lorp_fsd.instance import build_facility_design
    from lorp_fsd.scaling import build_scaled_geometry

    inst = parse_dat(ROOT / "instances" / "r40x5a-1.dat")
    cfg = load_row(ROOT / "results_MILP.xlsx", 0)
    geom = build_scaled_geometry(inst)
    design = build_facility_design(inst, cfg)
    return inst, cfg, geom, design


def _routing_matrices(model, depot_id):
    import numpy as np

    data = model.data()
    profiles = {p.name: idx for idx, p in enumerate(model.profiles)}
    pidx = profiles[f"routing_d{depot_id}"]
    names = [loc.name for loc in model.locations]
    return (
        np.array(data.distance_matrix(pidx)),
        np.array(data.duration_matrix(pidx)),
        names,
    )


def test_penalty_added_to_duration_not_distance(ctx):
    from lorp_fsd.da_options import build_da_options
    from lorp_fsd.pyvrp_builder import build_relaxed_model

    inst, cfg, geom, design = ctx
    i, j = build_da_options(inst, cfg, geom, design)[0].pair  # routing-allowed & DA pair
    P = 7_000_000

    _, base_info = build_relaxed_model(inst, cfg, geom, design)
    base_model, _ = build_relaxed_model(inst, cfg, geom, design)
    pen_model, pen_info = build_relaxed_model(
        inst, cfg, geom, design, penalty_routing_assignments={(i, j): P}
    )

    # penalty is recorded; pair stays routing-reachable (feasible, not removed)
    assert pen_info.penalty_routing_assignments == {(i, j): P}
    assert j in pen_info.routing_reachable[i]

    bd, bdur, names = _routing_matrices(base_model, i)
    pd, pdur, _ = _routing_matrices(pen_model, i)
    cj = names.index(f"c{j}")

    # distance channel unchanged everywhere (route-length semantics intact)
    assert (bd == pd).all()
    # duration increased by exactly P on every edge arriving at client j
    di = names.index(f"d{i}")
    assert pdur[di][cj] - bdur[di][cj] == P
    # an arbitrary other client -> j edge also carries the penalty
    some_client = next(
        names.index(n) for n in names
        if n.startswith("c") and names.index(n) != cj
    )
    assert pdur[some_client][cj] - bdur[some_client][cj] == P
    # leaving j is NOT penalised (penalty is per-arrival only)
    assert pdur[cj][di] == bdur[cj][di]


def test_no_penalty_matches_baseline(ctx):
    from lorp_fsd.pyvrp_builder import build_relaxed_model

    inst, cfg, geom, design = ctx
    _, info = build_relaxed_model(inst, cfg, geom, design, penalty_routing_assignments=None)
    assert info.penalty_routing_assignments == {}
