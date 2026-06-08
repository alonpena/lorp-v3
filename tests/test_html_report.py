"""Tests for the static HTML row report (Phase 8).

Pure reader: builds a minimal output folder (report.json + CSVs + a tiny PNG)
and asserts the rendered index.html contains the expected sections.
"""
from __future__ import annotations

import base64
import json

from lorp_fsd.html_report import (
    STATUS_EXPLANATIONS,
    render_index_html,
    write_index_html,
)

# 1x1 transparent PNG
_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


def _make_folder(tmp_path, status="FEASIBLE"):
    payload = {
        "row_id": 0,
        "instance_name": "r40x5a-1.dat",
        "status": status,
        "final_iteration": 0,
        "n_iterations": 1,
        "total_solve_time": 3.01,
        "repair_candidate_policy": "safe_both",
        "final_forbidden_count": 0,
        "instance": {"n_clients": 40, "n_depots": 5, "vehicle_capacity_Q": 340.0},
        "parameters": {"F_R": 1.0, "F_A": 0.0, "R": 30.0, "Length": 100.0, "scale": 0.79},
        "facility_design": {"open_depots": [1, 2, 3, 5], "depot_capacities": {"1": 875.0}},
        "milp": {"UB": 395.309, "LB": 395.309, "status": "Optimal", "gap": 0.0},
        "pyvrp": {"total": 395.3086},
        "comparison_metric": {"label": "GAP", "value": -8e-07, "flags": []},
        "feasibility": {
            "fully_feasible": status == "FEASIBLE",
            "capacity_feasible": True,
            "served_exactly_once": True,
            "route_length_feasible": True,
            "route_capacity_feasible": True,
            "da_radius_feasible": True,
            "penalty_distance_suspected": False,
        },
        "capacity": {"total_excess": 0.0, "overloaded_depots": [], "depots": []},
        "service_mix": {
            "routing_clients": 2, "da_clients": 38, "routing_routes": 1,
            "total_routing_demand": 85.0, "total_DA_demand": 1846.0,
        },
        "repair": {
            "selected_count": 0, "rejected_count": 0,
            "rejected_reason_counts": {}, "selected_candidates": [], "rejected_candidates": [],
        },
    }
    (tmp_path / "report.json").write_text(json.dumps(payload), encoding="utf-8")
    (tmp_path / "cost-breakdown.csv").write_text(
        "component,milp,pyvrp,delta\nrouting,95.3,95.3,0.0\n", encoding="utf-8"
    )
    (tmp_path / "depot_usage.csv").write_text(
        "depot_id,capacity,demand_total,excess,overloaded\n1,875.0,332.0,0.0,False\n",
        encoding="utf-8",
    )
    (tmp_path / "iteration_summary.csv").write_text(
        "iteration,iteration_status,z_pyvrp\n0,FEASIBLE,395.3\n", encoding="utf-8"
    )
    (tmp_path / "repair_trace.csv").write_text(
        "iteration,action,depot_id,client_id,reason\n", encoding="utf-8"
    )
    (tmp_path / "iteration_00_instance.png").write_bytes(_PNG)
    (tmp_path / "iteration_00_solution.png").write_bytes(_PNG)
    return tmp_path


def test_render_contains_core_sections(tmp_path):
    _make_folder(tmp_path)
    html = render_index_html(tmp_path)
    for needle in [
        "LoRP-FSD", "r40x5a-1.dat", "MILP vs PyVRP cost", "Depot usage",
        "Feasibility checks", "Repair trace", "Plots", "Status meaning",
        "395.3", "GAP",
    ]:
        assert needle in html, needle


def test_status_explanations_rendered_for_current_status(tmp_path):
    _make_folder(tmp_path, status="TIMEOUT")
    html = render_index_html(tmp_path)
    assert "TIMEOUT" in html
    assert STATUS_EXPLANATIONS["TIMEOUT"] in html
    # all canonical statuses are listed in the legend
    for key in STATUS_EXPLANATIONS:
        assert key in html


def test_plots_embedded_as_base64(tmp_path):
    _make_folder(tmp_path)
    html = render_index_html(tmp_path)
    assert "data:image/png;base64," in html


def test_write_index_html_creates_file(tmp_path):
    _make_folder(tmp_path)
    path = write_index_html(tmp_path)
    assert path.exists()
    assert path.name == "index.html"
    assert path.read_text(encoding="utf-8").startswith("<!doctype html>")


def test_missing_report_json_raises(tmp_path):
    import pytest

    with pytest.raises(FileNotFoundError):
        render_index_html(tmp_path)
