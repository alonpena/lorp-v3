"""Unit tests for row-level reporting artifacts."""
from __future__ import annotations

import csv
import json
from types import SimpleNamespace

from lorp_fsd.artifacts import write_basic_row_report_artifacts, write_row_reporting_artifacts
from lorp_fsd.capacity_audit import CapacityAudit, DepotAuditRecord
from lorp_fsd.repair import RepairSelection, REJECTION_NO_LENGTH_ALTERNATIVE, REJECTION_STRANDS_CLIENT


def _iteration(repair_selection):
    capacity = CapacityAudit(
        by_depot={
            1: DepotAuditRecord(1, demand_routing=15.0, demand_da=0.0, demand_total=15.0, capacity=10.0, excess=5.0),
            2: DepotAuditRecord(2, demand_routing=3.0, demand_da=0.0, demand_total=3.0, capacity=10.0, excess=0.0),
        },
        capacity_feasible=False,
        total_excess=5.0,
    )
    return SimpleNamespace(
        iteration=0,
        cost=SimpleNamespace(
            cost_routing=10.0,
            cost_direct_all=20.0,
            cost_vehicles=30.0,
            cost_depots=40.0,
            total=100.0,
        ),
        metric=SimpleNamespace(label="RELAXATION_DEVIATION", value=0.25, flags=set()),
        feasibility=SimpleNamespace(
            fully_feasible=False,
            capacity_feasible=False,
            served_exactly_once=True,
            route_length_violations=[],
            route_capacity_violations=[],
            da_radius_violations=[],
            penalty_distance_suspected=False,
        ),
        capacity=capacity,
        forbidden_before=frozenset({(2, 8)}),
        repair_selection=repair_selection,
        solve_time=1.5,
    )


def test_row_reporting_artifacts_include_summary_and_repair_trace(tmp_path):
    repair = RepairSelection(
        selected={(1, 7)},
        updated_forbidden={(2, 8), (1, 7)},
        removed_demand_by_depot={1: 10.0},
        repair_infeasible=True,
        infeasible_depots=[1],
        rejected_candidates={(1, 9, REJECTION_NO_LENGTH_ALTERNATIVE), (2, 10, REJECTION_STRANDS_CLIENT)},
    )

    paths = write_row_reporting_artifacts(tmp_path, [_iteration(repair)], "REPAIR_INFEASIBLE")

    assert paths["iteration_summary"].name == "iteration_summary.csv"
    assert paths["repair_trace"].name == "repair_trace.csv"

    with paths["iteration_summary"].open(newline="") as f:
        summary_rows = list(csv.DictReader(f))
    assert len(summary_rows) == 1
    summary = summary_rows[0]
    assert summary["iteration"] == "0"
    assert summary["iteration_status"] == "RELAXED_INFEASIBLE"
    assert summary["final_status"] == "REPAIR_INFEASIBLE"
    assert summary["overloaded_depots"] == "[1]"
    assert summary["total_excess"] == "5.0"
    assert summary["forbidden_count_before"] == "1"
    assert summary["forbidden_count_after"] == "2"
    assert summary["selected_count"] == "1"
    assert summary["rejected_count"] == "2"
    assert summary["repair_infeasible"] == "True"
    assert summary["infeasible_depots"] == "[1]"

    with paths["repair_trace"].open(newline="") as f:
        trace_rows = list(csv.DictReader(f))
    assert len(trace_rows) == 3

    selected = [r for r in trace_rows if r["action"] == "selected"]
    assert len(selected) == 1
    assert selected[0]["depot_id"] == "1"
    assert selected[0]["client_id"] == "7"
    assert selected[0]["reason"] == "selected_for_capacity_repair"
    assert selected[0]["overloaded_depot"] == "True"
    assert selected[0]["excess"] == "5.0"
    assert selected[0]["final_status"] == "REPAIR_INFEASIBLE"

    rejected_reasons = {r["reason"] for r in trace_rows if r["action"] == "rejected"}
    assert rejected_reasons == {REJECTION_NO_LENGTH_ALTERNATIVE, REJECTION_STRANDS_CLIENT}


def test_repair_trace_deduplicates_cumulative_rejections(tmp_path):
    repair1 = RepairSelection(
        selected=set(),
        updated_forbidden=set(),
        removed_demand_by_depot={1: 0.0},
        repair_infeasible=True,
        infeasible_depots=[1],
        rejected_candidates={(1, 9, REJECTION_NO_LENGTH_ALTERNATIVE)},
    )
    repair2 = RepairSelection(
        selected=set(),
        updated_forbidden=set(),
        removed_demand_by_depot={1: 0.0},
        repair_infeasible=True,
        infeasible_depots=[1],
        rejected_candidates={(1, 9, REJECTION_NO_LENGTH_ALTERNATIVE)},
    )
    it1 = _iteration(repair1)
    it2 = _iteration(repair2)
    it2.iteration = 1

    paths = write_row_reporting_artifacts(tmp_path, [it1, it2], "REPAIR_INFEASIBLE")

    with paths["repair_trace"].open(newline="") as f:
        trace_rows = list(csv.DictReader(f))
    assert len(trace_rows) == 1
    assert trace_rows[0]["iteration"] == "0"


def _result(iteration):
    return SimpleNamespace(
        row_index=7,
        instance_name="sample.dat",
        status="REPAIR_INFEASIBLE",
        final_iteration=iteration.iteration,
        iterations=[iteration],
        n_iterations=1,
        total_solve_time=3.0,
        final_forbidden=frozenset({(1, 7), (2, 8)}),
        repair_candidate_policy="safe_both",
        final=iteration,
    )


def _config():
    return SimpleNamespace(
        F_R=1.0,
        F_A=2.0,
        R=3.0,
        Length=4.0,
        UB=90.0,
        LB=80.0,
        status="Optimal",
        gap=0.0,
        cost_routing=9.0,
        cost_direct_all=18.0,
        cost_vehicles=27.0,
        cost_depots=36.0,
    )


def test_basic_row_report_artifacts_include_json_md_cost_and_depot_usage(tmp_path):
    repair = RepairSelection(
        selected={(1, 7)},
        updated_forbidden={(1, 7), (2, 8)},
        removed_demand_by_depot={1: 10.0},
        repair_infeasible=False,
        infeasible_depots=[],
        rejected_candidates={(1, 9, REJECTION_NO_LENGTH_ALTERNATIVE)},
    )
    result = _result(_iteration(repair))

    paths = write_basic_row_report_artifacts(tmp_path, result, _config())

    assert {p.name for p in paths.values()} == {
        "report.json",
        "report.md",
        "cost-breakdown.csv",
        "depot_usage.csv",
    }

    report = json.loads(paths["report_json"].read_text())
    assert report["row_id"] == 7
    assert report["instance_name"] == "sample.dat"
    assert report["status"] == "REPAIR_INFEASIBLE"
    assert report["final_forbidden_count"] == 2
    assert report["pyvrp"]["total"] == 100.0
    assert report["milp"]["UB"] == 90.0
    assert report["capacity"]["overloaded_depots"] == [1]
    assert report["repair"]["selected_candidates"] == [[1, 7]]
    assert report["repair"]["rejected_candidates"] == [[1, 9, REJECTION_NO_LENGTH_ALTERNATIVE]]

    with paths["cost_breakdown"].open(newline="") as f:
        cost_rows = list(csv.DictReader(f))
    total = next(r for r in cost_rows if r["component"] == "total")
    assert total["milp"] == "90.0"
    assert total["pyvrp"] == "100.0"
    assert total["delta"] == "10.0"

    with paths["depot_usage"].open(newline="") as f:
        depot_rows = list(csv.DictReader(f))
    assert depot_rows[0]["depot_id"] == "1"
    assert depot_rows[0]["usage_pct"] == "150.0"
    assert depot_rows[0]["overloaded"] == "True"

    md = paths["report_md"].read_text()
    assert "# Row 7 — sample.dat" in md
    assert "`cost-breakdown.csv`" in md
