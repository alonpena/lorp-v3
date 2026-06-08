"""Phase 6 tests — batch runner, consolidation, summary, error handling."""

import csv
import json
import os
import math
import tempfile
from pathlib import Path

import pytest

from lorp_fsd.batch import (
    CONSOLIDATED_COLUMNS,
    STATUS_ERROR,
    RowRecord,
    build_error_record,
    build_row_record,
    run_rows,
    summarize,
    write_consolidated_csv,
    write_summary,
)
from lorp_fsd.runner import (
    STATUS_FEASIBLE,
    STATUS_REPAIR_INFEASIBLE,
    STATUS_STUCK_NONCAPACITY,
)

XLSX = "results_MILP.xlsx"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _assert_all_columns(rec: RowRecord):
    """Assert that a RowRecord can produce all required consolidated columns."""
    from dataclasses import asdict
    d = asdict(rec)
    for col in CONSOLIDATED_COLUMNS:
        assert col in d, f"missing column {col!r} in RowRecord"


# ── Unit tests (no solve) ───────────────────────────────────────────────────


class TestRowRecordColumns:
    """RowRecord dataclass has all required consolidated columns."""

    def test_all_columns_present(self):
        rec = RowRecord()
        _assert_all_columns(rec)

    def test_error_record_has_all_columns(self):
        rec = build_error_record(999, None, ValueError("boom"))
        _assert_all_columns(rec)
        assert rec.status == STATUS_ERROR
        assert "boom" in rec.error_message


class TestSummarize:
    """Summary aggregation on synthetic records."""

    def _make_records(self):
        return [
            RowRecord(row_id=0, status=STATUS_FEASIBLE, GAP=0.01, iterations=1,
                       solve_time_total=10.0, capacity_feasible=True,
                       service_feasible=True, route_length_feasible=True),
            RowRecord(row_id=1, status=STATUS_FEASIBLE, GAP=0.05, iterations=1,
                       solve_time_total=15.0, capacity_feasible=True,
                       service_feasible=True, route_length_feasible=True),
            RowRecord(row_id=2, status=STATUS_STUCK_NONCAPACITY, iterations=2,
                       solve_time_total=60.0, capacity_feasible=True,
                       service_feasible=True, route_length_feasible=False,
                       stuck_noncapacity=True),
            RowRecord(row_id=3, status=STATUS_ERROR, error_message="FileNotFoundError: x"),
        ]

    def test_status_counts(self):
        s = summarize(self._make_records())
        assert s["n_instances"] == 4
        assert s["n_success"] == 2
        assert s["n_stuck_noncapacity"] == 1
        assert s["n_error"] == 1
        assert s["n_repair_failed"] == 0
        assert s["n_max_iterations"] == 0

    def test_gap_stats_over_feasible_only(self):
        s = summarize(self._make_records())
        assert s["min_gap"] == pytest.approx(0.01)
        assert s["max_gap"] == pytest.approx(0.05)
        assert s["mean_gap"] == pytest.approx(0.03)

    def test_runtime_excludes_error(self):
        s = summarize(self._make_records())
        # ERROR row has solve_time_total=0, but is excluded entirely.
        assert s["min_runtime"] == pytest.approx(10.0)
        assert s["max_runtime"] == pytest.approx(60.0)

    def test_empty(self):
        s = summarize([])
        assert s["n_instances"] == 0

    def test_outliers_include_error(self):
        s = summarize(self._make_records())
        reasons = [o["reason"] for o in s["outliers"]]
        assert "ERROR" in reasons


class TestCSVWriter:
    """Consolidated CSV has all required columns."""

    def test_csv_columns(self, tmp_path):
        recs = [RowRecord(row_id=0, instance="test.dat", status=STATUS_FEASIBLE)]
        p = write_consolidated_csv(recs, str(tmp_path / "consolidated.csv"))
        with open(p, newline="") as f:
            reader = csv.DictReader(f)
            header = reader.fieldnames
        for col in CONSOLIDATED_COLUMNS:
            assert col in header, f"missing CSV column {col!r}"


class TestSummaryWriter:
    """Summary JSON is valid and contains expected keys."""

    def test_summary_json(self, tmp_path):
        s = {"n_instances": 1, "n_success": 1, "outliers": []}
        p = write_summary(s, str(tmp_path / "summary.json"))
        loaded = json.loads(p.read_text())
        assert loaded["n_instances"] == 1


# ── Integration tests (short solve) ─────────────────────────────────────────

@pytest.mark.integration
class TestBatchIntegration:
    """Run first 1–2 rows at minimal runtime; validate consolidated output."""

    def test_single_row_feasible(self, tmp_path):
        """Row 0 produces a FEASIBLE record with all columns."""
        records = run_rows(
            [0], XLSX, root=".", output_root=str(tmp_path),
            run_id="test_batch_row0", seconds_per_run=1, num_solve_runs=1,
            max_repair_iterations=2, seed=0, make_plots=False,
        )
        assert len(records) == 1
        rec = records[0]
        _assert_all_columns(rec)
        assert rec.status == STATUS_FEASIBLE
        assert rec.instance == "r40x5a-1.dat"
        assert rec.Z_PyVRP is not None
        assert rec.Z_PyVRP > 0
        assert rec.capacity_feasible is True
        assert rec.service_feasible is True
        assert rec.route_length_feasible is True
        assert rec.iterations >= 1

    def test_error_row_does_not_crash(self, tmp_path):
        """A bad row index records ERROR without aborting the batch."""
        # Row 9999 is out of range — should trigger an IndexError in load_row.
        records = run_rows(
            [0, 9999], XLSX, root=".", output_root=str(tmp_path),
            run_id="test_batch_error", seconds_per_run=1, num_solve_runs=1,
            max_repair_iterations=1, seed=0, make_plots=False,
        )
        assert len(records) == 2
        ok_rec = records[0]
        err_rec = records[1]
        assert ok_rec.status in {STATUS_FEASIBLE, STATUS_STUCK_NONCAPACITY, STATUS_REPAIR_INFEASIBLE}
        assert err_rec.status == STATUS_ERROR
        assert err_rec.error_message != ""

    def test_consolidated_csv_roundtrip(self, tmp_path):
        """CSV written by run_rows has all columns and can be read back."""
        records = run_rows(
            [0], XLSX, root=".", output_root=str(tmp_path),
            run_id="test_csv_rt", seconds_per_run=1, num_solve_runs=1,
            max_repair_iterations=1, seed=0, make_plots=False,
        )
        csv_path = tmp_path / "consolidated.csv"
        write_consolidated_csv(records, str(csv_path))
        with open(csv_path, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 1
        for col in CONSOLIDATED_COLUMNS:
            assert col in rows[0], f"missing column {col!r} in CSV"

    def test_summary_from_run(self, tmp_path):
        """Summary computed from run results has expected keys."""
        records = run_rows(
            [0], XLSX, root=".", output_root=str(tmp_path),
            run_id="test_summary", seconds_per_run=1, num_solve_runs=1,
            max_repair_iterations=1, seed=0, make_plots=False,
        )
        s = summarize(records)
        assert s["n_instances"] == 1
        assert s["n_success"] + s["n_repair_failed"] + s["n_stuck_noncapacity"] + s["n_max_iterations"] + s["n_error"] == 1

    def test_checkpoint_resumability(self, tmp_path):
        """Rows already in checkpoint CSV are skipped on re-run."""
        ckpt = str(tmp_path / "checkpoint.csv")

        # First run: row 0.
        records1 = run_rows(
            [0], XLSX, root=".", output_root=str(tmp_path),
            run_id="test_resume", seconds_per_run=1, num_solve_runs=1,
            max_repair_iterations=1, seed=0, make_plots=False,
            checkpoint_csv=ckpt,
        )
        assert len(records1) == 1
        assert Path(ckpt).exists()

        # Second run: rows [0, 1]. Row 0 should be skipped (already in checkpoint).
        records2 = run_rows(
            [0, 1], XLSX, root=".", output_root=str(tmp_path),
            run_id="test_resume", seconds_per_run=1, num_solve_runs=1,
            max_repair_iterations=1, seed=0, make_plots=False,
            checkpoint_csv=ckpt,
        )
        # Only row 1 should be newly run (row 0 skipped).
        assert len(records2) == 1
        assert records2[0].row_id == 1
