"""Phase 5 — iterative row runner + per-iteration artifacts (no batch)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lorp_fsd import (
    STATUS_FEASIBLE,
    build_facility_design,
    build_scaled_geometry,
    compute_repair_step,
    parse_dat,
    load_row,
    run_row,
)
from lorp_fsd.capacity_audit import CapacityAudit, DepotAuditRecord
from lorp_fsd.experiment_config import ExperimentConfig, SelectedDepot
from lorp_fsd.solution_parser import ParsedSolution, RouteRecord

ROOT = Path(__file__).resolve().parents[1]
ROW0_DAT = ROOT / "instances" / "r40x5a-1.dat"
XLSX = ROOT / "results_MILP.xlsx"

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def row0_result(tmp_path_factory):
    out = tmp_path_factory.mktemp("phase5_out")
    inst = parse_dat(ROW0_DAT)
    cfg = load_row(XLSX, 0)
    geom = build_scaled_geometry(inst)
    design = build_facility_design(inst, cfg)
    return run_row(
        cfg, inst, geom, design, output_root=out, run_id="test",
        seconds_per_run=1.0, num_solve_runs=1, max_repair_iterations=2, seed=0,
        make_plots=True,
    )


def test_row0_terminates_at_iteration_0_feasible(row0_result):
    assert row0_result.status == STATUS_FEASIBLE
    assert row0_result.final_iteration == 0
    assert row0_result.n_iterations == 1


def test_row0_artifacts_created(row0_result):
    d = row0_result.output_dir
    for suffix in ("audit.json", "routes.csv", "assignments.csv", "solution.png"):
        p = d / f"iteration_00_{suffix}"
        assert p.exists() and p.stat().st_size > 0, p


def test_row0_audit_json_contents(row0_result):
    d = row0_result.output_dir
    audit = json.loads((d / "iteration_00_audit.json").read_text())
    assert audit["instance_name"] == "r40x5a-1.dat"
    assert audit["iteration"] == 0
    assert audit["capacity_feasible"] is True
    assert audit["all_clients_served_exactly_once"] is True
    assert audit["cost_depots_pyvrp"] == pytest.approx(300.0)
    assert audit["z_pyvrp"] == pytest.approx(395.3087, abs=1e-2)
    assert audit["cost_direct_all_pyvrp"] == 0.0
    assert audit["comparison_metric_label"] == "GAP"


def test_row0_final_structure_and_cost(row0_result):
    f = row0_result.final
    assert f.parsed.n_routing_routes == 1
    assert f.parsed.n_da_assignments == 38
    assert f.parsed.served_exactly_once
    assert len(f.parsed.service_by_client) == 40
    assert f.cost.total == pytest.approx(395.3087, abs=1e-2)
    assert f.metric.label == "GAP"
    assert f.metric.value == pytest.approx(0.0, abs=1e-3)


def test_routes_and_assignments_csv_rowcounts(row0_result):
    d = row0_result.output_dir
    routes = (d / "iteration_00_routes.csv").read_text().strip().splitlines()
    assigns = (d / "iteration_00_assignments.csv").read_text().strip().splitlines()
    assert len(routes) == 1 + 1  # header + 1 routing route
    assert len(assigns) == 1 + 40  # header + 40 clients


# ── runner repair-step integration on an artificial overloaded audit ────────
def test_compute_repair_step_on_artificial_overload():
    # synthetic scale=1 instance (max pair = 100): depot 1 + 3 clients
    dat = """4
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
0""".splitlines()
    inst = parse_dat(dat, name="synthetic.dat")
    geom = build_scaled_geometry(inst)
    cfg = ExperimentConfig(
        name="synthetic.dat", F_R=1.0, F_A=0.0, R=100.0, Length=100.0,
        selected_depots={1: SelectedDepot(1, 3, 200.0)},  # size 3 -> cap 200
    )
    design = build_facility_design(inst, cfg)

    route = RouteRecord(
        vehicle_type_index=0, mode="routing", depot_id=1, capacity=100,
        client_sequence=(1, 2, 3), demand=30, solver_distance_int=0,
        solver_distance_scaled=0.0, reconstructed_scaled_distance=0.0,
        reconstructed_weighted_cost=0.0,
    )
    parsed = ParsedSolution(
        routes=[route], da_assignments=[], service_by_client={1: "routing", 2: "routing", 3: "routing"},
        missing_clients=set(), duplicate_clients=set(), binding_violations=[], solver_feasible=True,
    )
    cap = CapacityAudit(
        by_depot={1: DepotAuditRecord(1, demand_routing=30, demand_da=0, demand_total=30, capacity=10, excess=20)},
        capacity_feasible=False, total_excess=20.0,
    )

    sel = compute_repair_step(parsed, cap, geom, cfg, design, inst, set())
    assert not sel.repair_infeasible
    assert sel.removed_demand_by_depot[1] >= 20.0  # excess covered
    assert len(sel.selected) >= 2  # 2 clients @ demand 10 to cover excess 20
    assert all(pair[0] == 1 for pair in sel.selected)
