from __future__ import annotations

import pytest

from instance_adapter import (
    ExcelSpec,
    adapt_instance,
    adapt_instance_from_row,
    load_and_adapt_instance,
    spec_from_row,
)
from tests.conftest import MINIMAL_DAT


# ── spec_from_row ─────────────────────────────────────────────────────────────

def _base_row():
    """Row dict as produced by load_lorp_fsd_mapping (normalized keys)."""
    return {
        "row_id": 7,
        "instance": "foo.dat",
        "R": 10.0,
        "F_R": 1.5,
        "F_A": 0.8,
        "Length": 200.0,
        "UB": 999.0,
        "status": "Optimal",
        "gap": 0.01,
        "cost_depots": 120.0,
        "vehicle_cost_milp": 60.0,
        "routing_cost_milp": 300.0,
        "da_cost_milp": 90.0,
        "depots": {1: {"label": "d1", "capacity": 500.0}},
        "depots_milp": {1: {"demand": 200.0, "usage": 0.4, "vehicles": 3.0}},
    }


def test_spec_from_row_scalar_fields():
    row = _base_row()
    spec = spec_from_row(row)
    assert spec.row_id == 7
    assert spec.instance == "foo.dat"
    assert spec.R == 10.0
    assert spec.F_R == 1.5
    assert spec.F_A == 0.8
    assert spec.Length == 200.0
    assert spec.UB == 999.0
    assert spec.status == "Optimal"
    assert spec.gap == 0.01
    assert spec.cost_depots == 120.0


def test_spec_from_row_cost_fields():
    spec = spec_from_row(_base_row())
    assert spec.vehicle_cost_milp == 60.0
    assert spec.routing_cost_milp == 300.0
    assert spec.da_cost_milp == 90.0


def test_spec_from_row_missing_optional_costs():
    row = _base_row()
    row.pop("vehicle_cost_milp")
    row.pop("routing_cost_milp")
    row.pop("da_cost_milp")
    spec = spec_from_row(row)
    assert spec.vehicle_cost_milp == 0.0
    assert spec.routing_cost_milp == 0.0
    assert spec.da_cost_milp == 0.0


def test_spec_from_row_depots_passed_through():
    spec = spec_from_row(_base_row())
    assert 1 in spec.depots
    assert spec.depots[1]["capacity"] == 500.0


# ── adapt_instance ────────────────────────────────────────────────────────────

def test_adapt_keeps_only_active_depots(minimal_instance, minimal_spec):
    # minimal_spec has depots {1, 2}; minimal_instance has {1, 2} too
    adapted = adapt_instance(minimal_instance, minimal_spec)
    assert set(adapted.depots.keys()) == {1, 2}


def test_adapt_filters_inactive_depot(minimal_instance, minimal_spec):
    # remove depot 2 from spec → only depot 1 survives
    from dataclasses import replace
    spec_one = replace(
        minimal_spec,
        depots={1: {"label": "d1", "capacity": 200.0}},
        depots_milp={1: minimal_spec.depots_milp[1]},
    )
    adapted = adapt_instance(minimal_instance, spec_one)
    assert set(adapted.depots.keys()) == {1}


def test_adapt_overwrites_capacity(minimal_instance, minimal_spec):
    from dataclasses import replace
    spec = replace(
        minimal_spec,
        depots={1: {"label": "d1", "capacity": 999.0}, 2: {"label": "d2", "capacity": 888.0}},
    )
    adapted = adapt_instance(minimal_instance, spec)
    assert adapted.depots[1]["cap"] == 999.0
    assert adapted.depots[2]["cap"] == 888.0


def test_adapt_fallback_to_base_capacity(minimal_instance, minimal_spec):
    from dataclasses import replace
    spec = replace(
        minimal_spec,
        depots={1: {"label": "d1", "capacity": None}, 2: {"label": "d2", "capacity": None}},
    )
    adapted = adapt_instance(minimal_instance, spec)
    assert adapted.depots[1]["cap"] == minimal_instance.depots[1]["cap"]
    assert adapted.depots[2]["cap"] == minimal_instance.depots[2]["cap"]


def test_adapt_injects_params(minimal_instance, minimal_spec):
    adapted = adapt_instance(minimal_instance, minimal_spec)
    assert adapted.data["R"] == minimal_spec.R
    assert adapted.data["F_R"] == minimal_spec.F_R
    assert adapted.data["F_A"] == minimal_spec.F_A
    assert adapted.data["Length"] == minimal_spec.Length


def test_adapt_depot_not_in_base_silently_skipped(minimal_instance, minimal_spec):
    from dataclasses import replace
    spec = replace(
        minimal_spec,
        depots={99: {"label": "d99", "capacity": 500.0}},  # doesn't exist in base
        depots_milp={},
    )
    adapted = adapt_instance(minimal_instance, spec)
    assert len(adapted.depots) == 0


def test_adapt_zero_fixed_cost(minimal_instance, minimal_spec):
    adapted = adapt_instance(minimal_instance, minimal_spec)
    for d in adapted.depots.values():
        assert d["fixed_cost"] == 0.0


def test_adapt_clients_unchanged(minimal_instance, minimal_spec):
    adapted = adapt_instance(minimal_instance, minimal_spec)
    assert adapted.clients == minimal_instance.clients


def test_adapt_n_depots_updated(minimal_instance, minimal_spec):
    adapted = adapt_instance(minimal_instance, minimal_spec)
    assert adapted.data["n_depots"] == len(adapted.depots)


# ── adapt_instance_from_row ───────────────────────────────────────────────────

def test_adapt_instance_from_row(minimal_instance):
    row = _base_row()
    # adjust depots to match minimal_instance which has keys 1,2
    row["depots"] = {1: {"label": "d1", "capacity": 180.0}, 2: {"label": "d2", "capacity": 130.0}}
    row["depots_milp"] = {1: {"demand": 50.0, "usage": 0.25, "vehicles": 1.0}, 2: {"demand": 30.0, "usage": 0.2, "vehicles": 1.0}}
    adapted = adapt_instance_from_row(minimal_instance, row)
    assert adapted.data["R"] == 10.0
    assert adapted.depots[1]["cap"] == 180.0


# ── load_and_adapt_instance ───────────────────────────────────────────────────

def test_load_and_adapt_instance(tmp_path, minimal_spec):
    p = tmp_path / "test.dat"
    p.write_text(MINIMAL_DAT)
    adapted = load_and_adapt_instance(p, minimal_spec)
    assert adapted.data["F_R"] == minimal_spec.F_R
    assert len(adapted.depots) == 2
