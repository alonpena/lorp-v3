"""Phase 7A — repair candidate safety diagnostics and filtering."""
from __future__ import annotations

import pytest

from lorp_fsd.capacity_audit import CapacityAudit, DepotAuditRecord
from lorp_fsd.dat_parser import DEFAULT_INSTANCE_FOLDERS, parse_dat, resolve_dat_path
from lorp_fsd.excel_loader import load_row
from lorp_fsd.instance import build_facility_design
from lorp_fsd.repair import (
    REJECTION_NO_LENGTH_ALTERNATIVE,
    REJECTION_SAME_DEPOT_DA_RISK,
    REPAIR_POLICY_SAFE_BOTH,
    REPAIR_POLICY_SAFE_CAPACITY_RELEASE,
    REPAIR_POLICY_SAFE_LENGTH,
    RepairCandidate,
    diagnose_repair_candidate,
    select_forbidden_assignments,
)
from lorp_fsd.runner import STATUS_FEASIBLE, run_row_from_excel
from lorp_fsd.scaling import build_scaled_geometry


SCALE1_DAT = """\
4
1
1
4
0 0
0 40
30 40
60 0
60 80
100
200
10
10
10
10
100
0
0
"""


def _always_ok(_client_id, _forbidden):
    return True


def _row5_context():
    cfg = load_row("results_MILP.xlsx", 5)
    resolution = resolve_dat_path(cfg.name, DEFAULT_INSTANCE_FOLDERS, root=".")
    assert resolution.ok
    inst = parse_dat(resolution.path)
    geom = build_scaled_geometry(inst)
    design = build_facility_design(inst, cfg)
    return cfg, inst, geom, design


def _scale1_geom():
    return build_scaled_geometry(parse_dat(SCALE1_DAT.splitlines(), name="scale1.dat"))


def test_row5_candidate_4_18_is_unsafe_for_length_serviceability():
    cfg, _inst, geom, design = _row5_context()
    cand = RepairCandidate(depot_id=4, route_id=0, client_id=18, client_demand=1, saving=0, weighted_saving=0)

    safety = diagnose_repair_candidate(
        cand,
        active_depots=design.active_depot_ids,
        geometry=geom,
        R=cfg.R,
        Length=cfg.Length,
        forbidden_after_cut={(4, 18)},
    )

    assert safety.length_serviceable_after_cut is False
    assert safety.has_DA_alternative_after_cut is False
    assert safety.has_routing_singleton_alternative_after_cut is False
    assert safety.safe_for_length_serviceability is False


def test_same_depot_da_risk_detection():
    geom = _scale1_geom()
    cand = RepairCandidate(depot_id=1, route_id=0, client_id=1, client_demand=10, saving=1, weighted_saving=1)

    safety = diagnose_repair_candidate(
        cand,
        active_depots=[1],
        geometry=geom,
        R=100.0,
        Length=100.0,
        forbidden_after_cut={(1, 1)},
    )

    assert safety.same_depot_DA_feasible is True
    assert safety.same_depot_DA_risk is True
    assert safety.safe_for_capacity_release is False


def test_safe_length_policy_skips_row5_unsafe_candidate_4_18():
    cfg, _inst, geom, design = _row5_context()
    cand = RepairCandidate(depot_id=4, route_id=0, client_id=18, client_demand=10, saving=100, weighted_saving=100)

    sel = select_forbidden_assignments(
        [cand],
        {4: 10.0},
        set(),
        _always_ok,
        active_depots=design.active_depot_ids,
        geometry=geom,
        R=cfg.R,
        Length=cfg.Length,
        repair_candidate_policy=REPAIR_POLICY_SAFE_LENGTH,
    )

    assert sel.selected == set()
    assert sel.repair_infeasible is True
    assert (4, 18, REJECTION_NO_LENGTH_ALTERNATIVE) in sel.rejected_candidates


def test_safe_capacity_release_policy_skips_same_depot_da_risk_candidate():
    geom = _scale1_geom()
    cand = RepairCandidate(depot_id=1, route_id=0, client_id=1, client_demand=10, saving=100, weighted_saving=100)

    sel = select_forbidden_assignments(
        [cand],
        {1: 10.0},
        set(),
        _always_ok,
        active_depots=[1],
        geometry=geom,
        R=100.0,
        Length=100.0,
        repair_candidate_policy=REPAIR_POLICY_SAFE_CAPACITY_RELEASE,
    )

    assert sel.selected == set()
    assert sel.repair_infeasible is True
    assert (1, 1, REJECTION_SAME_DEPOT_DA_RISK) in sel.rejected_candidates


def test_safe_both_combines_length_and_capacity_release_filters():
    cfg, _inst, row5_geom, row5_design = _row5_context()
    scale1_geom = _scale1_geom()

    unsafe_length = RepairCandidate(depot_id=4, route_id=0, client_id=18, client_demand=10, saving=100, weighted_saving=100)
    unsafe_capacity = RepairCandidate(depot_id=1, route_id=0, client_id=1, client_demand=10, saving=90, weighted_saving=90)

    sel_length = select_forbidden_assignments(
        [unsafe_length],
        {4: 10.0},
        set(),
        _always_ok,
        active_depots=row5_design.active_depot_ids,
        geometry=row5_geom,
        R=cfg.R,
        Length=cfg.Length,
        repair_candidate_policy=REPAIR_POLICY_SAFE_BOTH,
    )
    assert (4, 18, REJECTION_NO_LENGTH_ALTERNATIVE) in sel_length.rejected_candidates

    sel_capacity = select_forbidden_assignments(
        [unsafe_capacity],
        {1: 10.0},
        set(),
        _always_ok,
        active_depots=[1],
        geometry=scale1_geom,
        R=100.0,
        Length=100.0,
        repair_candidate_policy=REPAIR_POLICY_SAFE_BOTH,
    )
    assert (1, 1, REJECTION_SAME_DEPOT_DA_RISK) in sel_capacity.rejected_candidates


@pytest.mark.integration
def test_row0_no_regression_safe_both(tmp_path):
    result = run_row_from_excel(
        "results_MILP.xlsx",
        0,
        root=".",
        output_root=str(tmp_path),
        run_id="phase7_row0_safe_both",
        seconds_per_run=1,
        num_solve_runs=1,
        max_repair_iterations=2,
        seed=0,
        make_plots=False,
        repair_candidate_policy=REPAIR_POLICY_SAFE_BOTH,
    )

    assert result.status == STATUS_FEASIBLE
    assert result.final_iteration == 0
    assert result.final.feasibility.fully_feasible is True
