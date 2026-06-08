"""Unit tests for row-level reporting artifacts."""
from __future__ import annotations

import csv
from types import SimpleNamespace

from lorp_fsd.artifacts import write_row_reporting_artifacts
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
        cost=SimpleNamespace(total=123.0),
        metric=SimpleNamespace(label="RELAXATION_DEVIATION", value=0.25),
        feasibility=SimpleNamespace(fully_feasible=False),
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
