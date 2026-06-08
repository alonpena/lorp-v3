"""Batch runner and consolidated reporting (Phase 6).

Wraps the per-row runner (:func:`~lorp_fsd.runner.run_row_from_excel`) over
arbitrary row sets, collects one :class:`RowRecord` per row, writes a
consolidated CSV (+ optional Excel), and produces aggregate summary statistics.

This module is **orchestration + tabulation only**. It does not modify the
per-row runner's semantics, the repair loop, or any Phase 1–5 modules.

Robustness: every row is wrapped in a ``try/except``; a row that fails
instance resolution, build, solve, or audit is recorded with
``status = 'ERROR'`` (and the exception message). Optional per-row wall timeouts
record ``status = 'TIMEOUT'``. Neither case crashes the batch.
"""

from __future__ import annotations

import csv
import json
import logging
import multiprocessing as mp
import queue
import time
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set

from .cost_reconstruction import GAP, NEGATIVE_GAP, RELAXATION_DEVIATION
from .runner import (
    STATUS_FEASIBLE,
    STATUS_MAX_ITERATIONS,
    STATUS_REPAIR_INFEASIBLE,
    STATUS_STUCK_NONCAPACITY,
    RowRunResult,
    run_row_from_excel,
)

logger = logging.getLogger(__name__)

STATUS_ERROR = "ERROR"
STATUS_TIMEOUT = "TIMEOUT"

# ── Consolidated row record ──────────────────────────────────────────────────

CONSOLIDATED_COLUMNS = [
    "row_id",
    "instance",
    "F_R",
    "F_A",
    "R",
    "Length",
    "UB_MILP",
    "Z_PyVRP",
    "GAP",
    "comparison_metric_label",
    "comparison_metric_value",
    "status",
    "iterations",
    "solve_time_total",
    "cost_routing_milp",
    "cost_da_milp",
    "cost_vehicle_milp",
    "cost_depot_milp",
    "cost_routing_pyvrp",
    "cost_da_pyvrp",
    "cost_vehicle_pyvrp",
    "cost_depot_pyvrp",
    "capacity_feasible",
    "service_feasible",
    "route_length_feasible",
    "da_radius_feasible",
    "penalty_distance_suspected",
    "repair_failed",
    "stuck_noncapacity",
    "negative_gap_flag",
    "same_depot_DA_risk_count",
    "capacity_not_freed_count",
    "length_invalid_cut_count",
    "rejected_candidates_count",
    "rejected_candidates",
    "route_length_repair_attempts",
    "artifact_dir",
    "error_message",
]


@dataclass
class RowRecord:
    """One consolidated record per Excel row / instance."""

    row_id: Optional[int] = None
    instance: str = ""
    F_R: Optional[float] = None
    F_A: Optional[float] = None
    R: Optional[float] = None
    Length: Optional[float] = None

    UB_MILP: Optional[float] = None
    Z_PyVRP: Optional[float] = None
    GAP: Optional[float] = None
    comparison_metric_label: str = ""
    comparison_metric_value: Optional[float] = None

    status: str = ""
    iterations: int = 0
    solve_time_total: float = 0.0

    cost_routing_milp: Optional[float] = None
    cost_da_milp: Optional[float] = None
    cost_vehicle_milp: Optional[float] = None
    cost_depot_milp: Optional[float] = None

    cost_routing_pyvrp: Optional[float] = None
    cost_da_pyvrp: Optional[float] = None
    cost_vehicle_pyvrp: Optional[float] = None
    cost_depot_pyvrp: Optional[float] = None

    capacity_feasible: Optional[bool] = None
    service_feasible: Optional[bool] = None
    route_length_feasible: Optional[bool] = None
    da_radius_feasible: Optional[bool] = None

    penalty_distance_suspected: Optional[bool] = None
    repair_failed: bool = False
    stuck_noncapacity: bool = False
    negative_gap_flag: bool = False

    same_depot_DA_risk_count: int = 0
    capacity_not_freed_count: int = 0
    length_invalid_cut_count: int = 0
    rejected_candidates_count: int = 0
    rejected_candidates: str = ""
    route_length_repair_attempts: int = 0

    artifact_dir: str = ""
    error_message: str = ""


# ── Record builders ──────────────────────────────────────────────────────────


def build_row_record(result: RowRunResult, config) -> RowRecord:
    """Extract a consolidated :class:`RowRecord` from a successful run result."""
    final = result.final
    cost = final.cost
    feas = final.feasibility
    metric = final.metric

    gap_value = None
    if metric.label == GAP and metric.value is not None:
        gap_value = metric.value

    repair_selections = [it.repair_selection for it in result.iterations if it.repair_selection is not None]
    rejected = sorted({p for sel in repair_selections for p in getattr(sel, "rejected_candidates", set())})

    return RowRecord(
        row_id=result.row_index,
        instance=result.instance_name,
        F_R=config.F_R,
        F_A=config.F_A,
        R=config.R,
        Length=config.Length,
        UB_MILP=config.UB,
        Z_PyVRP=cost.total,
        GAP=gap_value,
        comparison_metric_label=metric.label,
        comparison_metric_value=metric.value,
        status=result.status,
        iterations=result.n_iterations,
        solve_time_total=result.total_solve_time,
        cost_routing_milp=config.cost_routing,
        cost_da_milp=config.cost_direct_all,
        cost_vehicle_milp=config.cost_vehicles,
        cost_depot_milp=config.cost_depots,
        cost_routing_pyvrp=cost.cost_routing,
        cost_da_pyvrp=cost.cost_direct_all,
        cost_vehicle_pyvrp=cost.cost_vehicles,
        cost_depot_pyvrp=cost.cost_depots,
        capacity_feasible=feas.capacity_feasible,
        service_feasible=feas.served_exactly_once,
        route_length_feasible=(not feas.route_length_violations),
        da_radius_feasible=(not feas.da_radius_violations),
        penalty_distance_suspected=feas.penalty_distance_suspected,
        repair_failed=(result.status == STATUS_REPAIR_INFEASIBLE),
        stuck_noncapacity=(result.status == STATUS_STUCK_NONCAPACITY),
        negative_gap_flag=(NEGATIVE_GAP in metric.flags),
        same_depot_DA_risk_count=sum(getattr(sel, "same_depot_DA_risk_count", 0) for sel in repair_selections),
        capacity_not_freed_count=sum(getattr(it, "capacity_not_freed_count", 0) for it in result.iterations),
        length_invalid_cut_count=sum(getattr(sel, "length_invalid_cut_count", 0) for sel in repair_selections),
        rejected_candidates_count=len(rejected),
        rejected_candidates=json.dumps(rejected),
        route_length_repair_attempts=getattr(result, "route_length_repair_attempts", 0),
        artifact_dir=str(result.output_dir),
    )


def _stub_row_record(row_index: int, config, *, status: str, error_message: str, solve_time_total: float = 0.0) -> RowRecord:
    """Stub record for a row without a successful RowRunResult."""
    return RowRecord(
        row_id=row_index,
        instance=getattr(config, "name", "") if config is not None else "",
        F_R=getattr(config, "F_R", None) if config is not None else None,
        F_A=getattr(config, "F_A", None) if config is not None else None,
        R=getattr(config, "R", None) if config is not None else None,
        Length=getattr(config, "Length", None) if config is not None else None,
        UB_MILP=getattr(config, "UB", None) if config is not None else None,
        cost_routing_milp=getattr(config, "cost_routing", None) if config is not None else None,
        cost_da_milp=getattr(config, "cost_direct_all", None) if config is not None else None,
        cost_vehicle_milp=getattr(config, "cost_vehicles", None) if config is not None else None,
        cost_depot_milp=getattr(config, "cost_depots", None) if config is not None else None,
        solve_time_total=solve_time_total,
        status=status,
        error_message=error_message,
    )


def build_error_record(row_index: int, config, error: Exception) -> RowRecord:
    """Stub record for a row that raised an exception."""
    return _stub_row_record(
        row_index,
        config,
        status=STATUS_ERROR,
        error_message=f"{type(error).__name__}: {error}",
    )


def build_timeout_record(row_index: int, config, timeout_seconds: float, elapsed_seconds: float) -> RowRecord:
    """Stub record for a row killed by the wall-clock timeout."""
    return _stub_row_record(
        row_index,
        config,
        status=STATUS_TIMEOUT,
        error_message=f"TimeoutError: row exceeded {timeout_seconds:g} seconds",
        solve_time_total=elapsed_seconds,
    )


# ── Batch orchestration ─────────────────────────────────────────────────────


def _multiprocessing_context():
    """Prefer fork so test monkeypatches and loaded state carry into row workers."""
    methods = mp.get_all_start_methods()
    if "fork" in methods:
        return mp.get_context("fork")
    return mp.get_context()


def _row_worker(out_q, xlsx_path: str, row_idx: int, config, row_kwargs: Dict[str, Any]) -> None:
    """Run one row in a child process and send back a RowRecord."""
    try:
        result = run_row_from_excel(xlsx_path, row_idx, **row_kwargs)
        rec = build_row_record(result, config)
    except Exception as exc:
        rec = build_error_record(row_idx, config, exc)
    out_q.put(rec)


def _run_row_with_timeout(
    xlsx_path: str,
    row_idx: int,
    config,
    row_kwargs: Dict[str, Any],
    *,
    row_timeout_seconds: float,
    elapsed_seconds_start: float,
) -> RowRecord:
    """Run one row with a process-level wall-clock guard."""
    ctx = _multiprocessing_context()
    out_q = ctx.Queue(maxsize=1)
    proc = ctx.Process(target=_row_worker, args=(out_q, xlsx_path, row_idx, config, row_kwargs))
    proc.start()

    try:
        rec = out_q.get(timeout=row_timeout_seconds)
        proc.join(timeout=5)
        if proc.is_alive():  # pragma: no cover - worker should exit after sending its record
            proc.terminate()
            proc.join(timeout=5)
        return rec
    except queue.Empty:
        if proc.is_alive():
            proc.terminate()
            proc.join(timeout=5)
            if proc.is_alive():  # pragma: no cover - terminate should suffice on supported platforms
                proc.kill()
                proc.join(timeout=5)
            elapsed = time.perf_counter() - elapsed_seconds_start
            return build_timeout_record(row_idx, config, row_timeout_seconds, elapsed)
        return build_error_record(
            row_idx,
            config,
            RuntimeError(f"row worker exited without result (exitcode={proc.exitcode})"),
        )
    finally:
        out_q.close()
        out_q.join_thread()


def run_rows(
    row_indices: Sequence[int],
    xlsx_path: str = "results_MILP.xlsx",
    *,
    root: str = ".",
    output_root: str = "outputs",
    run_id: str = "batch",
    seconds_per_run: float = 30.0,
    num_solve_runs: int = 3,
    max_repair_iterations: int = 5,
    seed: int = 0,
    make_plots: bool = False,
    checkpoint_csv: Optional[str] = None,
    repair_candidate_policy: str = "baseline",
    max_repair_attempts: int = 1,
    return_completed_records: bool = False,
    row_timeout_seconds: Optional[float] = None,
) -> List[RowRecord]:
    """Run an arbitrary set of Excel rows, returning consolidated records.

    Parameters
    ----------
    row_indices
        0-based Excel row indices to run.
    xlsx_path
        Path to the MILP results workbook.
    checkpoint_csv
        If given, append each row's record to this CSV as it completes.
        On restart, rows already present are skipped (resumability).
    make_plots
        Default **False** for batch — per-iteration PNGs are expensive and
        not needed for the consolidated table. Opt in with ``True``.

    One bad row records ``status=ERROR`` without aborting the batch.
    If ``row_timeout_seconds`` is given, each row runs in a child process and
    wall-clock overruns record ``status=TIMEOUT`` before the batch continues.
    """
    if row_timeout_seconds is not None and row_timeout_seconds <= 0:
        raise ValueError("row_timeout_seconds must be positive or None")

    # Resumability: load already-completed row records from checkpoint.
    completed: Set[int] = set()
    completed_records: List[RowRecord] = []
    checkpoint_path: Optional[Path] = None
    if checkpoint_csv is not None:
        checkpoint_path = Path(checkpoint_csv)
        if checkpoint_path.exists():
            requested = set(row_indices)
            completed_records = _load_completed_records(checkpoint_path, requested)
            completed = {r.row_id for r in completed_records if r.row_id is not None}
            logger.info("Resuming: %d rows already completed", len(completed))

    # Pre-load all configs once (fast, ~1s) so we can attach config even on ERROR.
    from .excel_loader import load_lorp_fsd_rows

    all_configs = load_lorp_fsd_rows(xlsx_path)

    records: List[RowRecord] = list(completed_records) if return_completed_records else []
    total = len(row_indices)

    for pos, row_idx in enumerate(row_indices, 1):
        if row_idx in completed:
            logger.info("[%d/%d] row %d: SKIP (already in checkpoint)", pos, total, row_idx)
            continue

        config = all_configs[row_idx] if row_idx < len(all_configs) else None
        logger.info(
            "[%d/%d] row %d (%s) — starting",
            pos,
            total,
            row_idx,
            config.name if config else "?",
        )
        t0 = time.perf_counter()

        row_kwargs = dict(
            root=root,
            output_root=output_root,
            run_id=run_id,
            seconds_per_run=seconds_per_run,
            num_solve_runs=num_solve_runs,
            max_repair_iterations=max_repair_iterations,
            seed=seed,
            make_plots=make_plots,
            repair_candidate_policy=repair_candidate_policy,
            max_repair_attempts=max_repair_attempts,
        )

        try:
            if row_timeout_seconds is None:
                result = run_row_from_excel(xlsx_path, row_idx, **row_kwargs)
                rec = build_row_record(result, config)
            else:
                rec = _run_row_with_timeout(
                    xlsx_path,
                    row_idx,
                    config,
                    row_kwargs,
                    row_timeout_seconds=row_timeout_seconds,
                    elapsed_seconds_start=t0,
                )
        except Exception as exc:
            logger.warning("[%d/%d] row %d ERROR: %s", pos, total, row_idx, exc)
            rec = build_error_record(row_idx, config, exc)

        if rec.status == STATUS_TIMEOUT:
            logger.warning("[%d/%d] row %d TIMEOUT after %.1fs", pos, total, row_idx, time.perf_counter() - t0)

        elapsed = time.perf_counter() - t0
        logger.info(
            "[%d/%d] row %d: %s (%.1fs)",
            pos,
            total,
            row_idx,
            rec.status,
            elapsed,
        )

        records.append(rec)
        if checkpoint_path is not None:
            _append_csv_row(checkpoint_path, rec)

    return records


def _load_completed_rows(csv_path: Path) -> Set[int]:
    """Read row_id column from an existing checkpoint CSV."""
    return {r.row_id for r in _load_completed_records(csv_path) if r.row_id is not None}


def _load_completed_records(csv_path: Path, requested: Optional[Set[int]] = None) -> List[RowRecord]:
    """Read completed :class:`RowRecord` objects from an existing checkpoint CSV."""
    records: List[RowRecord] = []
    with csv_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rec = _row_record_from_csv(row)
            if requested is None or rec.row_id in requested:
                records.append(rec)
    return records


def _row_record_from_csv(row: Dict[str, str]) -> RowRecord:
    """Parse one checkpoint CSV row back into a :class:`RowRecord`."""
    int_fields = {
        "row_id", "iterations", "same_depot_DA_risk_count", "capacity_not_freed_count",
        "length_invalid_cut_count", "rejected_candidates_count", "route_length_repair_attempts",
    }
    float_fields = {
        "F_R", "F_A", "R", "Length", "UB_MILP", "Z_PyVRP", "GAP",
        "comparison_metric_value", "solve_time_total", "cost_routing_milp", "cost_da_milp",
        "cost_vehicle_milp", "cost_depot_milp", "cost_routing_pyvrp", "cost_da_pyvrp",
        "cost_vehicle_pyvrp", "cost_depot_pyvrp",
    }
    bool_fields = {
        "capacity_feasible", "service_feasible", "route_length_feasible", "da_radius_feasible",
        "penalty_distance_suspected", "repair_failed", "stuck_noncapacity", "negative_gap_flag",
    }

    kwargs: Dict[str, Any] = {}
    for field in fields(RowRecord):
        name = field.name
        value = row.get(name, "")
        if value == "":
            continue
        if name in int_fields:
            kwargs[name] = int(value)
        elif name in float_fields:
            kwargs[name] = float(value)
        elif name in bool_fields:
            kwargs[name] = value.lower() == "true"
        else:
            kwargs[name] = value
    return RowRecord(**kwargs)


def _append_csv_row(csv_path: Path, rec: RowRecord) -> None:
    """Append one record to the checkpoint CSV, creating header if new."""
    is_new = not csv_path.exists() or csv_path.stat().st_size == 0
    with csv_path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CONSOLIDATED_COLUMNS)
        if is_new:
            w.writeheader()
        w.writerow(_record_to_dict(rec))


# ── Summary / aggregation ───────────────────────────────────────────────────


def _min_mean_max(values: list, prefix: str) -> Dict[str, Any]:
    """Compute min/mean/max for a numeric list, with keyed output."""
    if not values:
        return {
            f"min_{prefix}": None,
            f"mean_{prefix}": None,
            f"max_{prefix}": None,
        }
    return {
        f"min_{prefix}": min(values),
        f"mean_{prefix}": sum(values) / len(values),
        f"max_{prefix}": max(values),
    }


def summarize(records: List[RowRecord]) -> Dict[str, Any]:
    """Compute aggregate summary statistics from consolidated records."""
    n = len(records)
    if n == 0:
        return {"n_instances": 0}

    statuses = [r.status for r in records]
    n_feasible = statuses.count(STATUS_FEASIBLE)
    n_repair_failed = statuses.count(STATUS_REPAIR_INFEASIBLE)
    n_stuck = statuses.count(STATUS_STUCK_NONCAPACITY)
    n_max_iter = statuses.count(STATUS_MAX_ITERATIONS)
    n_error = statuses.count(STATUS_ERROR)
    n_penalty = sum(1 for r in records if r.penalty_distance_suspected)
    n_neg_gap = sum(1 for r in records if r.negative_gap_flag)
    n_same_depot_da_risk = sum(r.same_depot_DA_risk_count for r in records)
    n_capacity_not_freed = sum(r.capacity_not_freed_count for r in records)
    n_length_invalid_cut = sum(r.length_invalid_cut_count for r in records)
    n_rejected_candidates = sum(r.rejected_candidates_count for r in records)

    # GAP stats over FEASIBLE rows only.
    feasible_gaps = [r.GAP for r in records if r.status == STATUS_FEASIBLE and r.GAP is not None]
    gap_stats = _min_mean_max(feasible_gaps, "gap")

    # Runtime stats over non-ERROR rows.
    runtimes = [r.solve_time_total for r in records if r.status != STATUS_ERROR]
    runtime_stats = _min_mean_max(runtimes, "runtime")

    # Iteration stats over non-ERROR rows.
    iters = [float(r.iterations) for r in records if r.status != STATUS_ERROR]
    iter_stats = _min_mean_max(iters, "iterations")

    # Cost component averages (over non-ERROR rows).
    valid = [r for r in records if r.status != STATUS_ERROR]

    def _avg(vals):
        vals = [v for v in vals if v is not None]
        return sum(vals) / len(vals) if vals else None

    cost_avgs = {
        "avg_cost_routing_pyvrp": _avg([r.cost_routing_pyvrp for r in valid]),
        "avg_cost_da_pyvrp": _avg([r.cost_da_pyvrp for r in valid]),
        "avg_cost_vehicle_pyvrp": _avg([r.cost_vehicle_pyvrp for r in valid]),
        "avg_cost_depot_pyvrp": _avg([r.cost_depot_pyvrp for r in valid]),
        "avg_cost_routing_milp": _avg([r.cost_routing_milp for r in valid]),
        "avg_cost_da_milp": _avg([r.cost_da_milp for r in valid]),
        "avg_cost_vehicle_milp": _avg([r.cost_vehicle_milp for r in valid]),
        "avg_cost_depot_milp": _avg([r.cost_depot_milp for r in valid]),
    }

    # Component deltas (PyVRP − MILP).
    def _avg_delta(pyvrp_attr, milp_attr):
        deltas = []
        for r in valid:
            p = getattr(r, pyvrp_attr)
            m = getattr(r, milp_attr)
            if p is not None and m is not None:
                deltas.append(p - m)
        return sum(deltas) / len(deltas) if deltas else None

    deltas = {
        "delta_routing": _avg_delta("cost_routing_pyvrp", "cost_routing_milp"),
        "delta_da": _avg_delta("cost_da_pyvrp", "cost_da_milp"),
        "delta_vehicle": _avg_delta("cost_vehicle_pyvrp", "cost_vehicle_milp"),
        "delta_depot": _avg_delta("cost_depot_pyvrp", "cost_depot_milp"),
    }

    # Outlier instances (ERROR, negative gap, penalty distance).
    outliers = []
    for r in records:
        if r.status == STATUS_ERROR:
            outliers.append({"row_id": r.row_id, "instance": r.instance, "reason": "ERROR", "message": r.error_message})
        elif r.negative_gap_flag:
            outliers.append({"row_id": r.row_id, "instance": r.instance, "reason": "NEGATIVE_GAP", "gap": r.GAP})
        elif r.penalty_distance_suspected:
            outliers.append({"row_id": r.row_id, "instance": r.instance, "reason": "PENALTY_DISTANCE"})

    return {
        "n_instances": n,
        "n_success": n_feasible,
        "n_repair_failed": n_repair_failed,
        "n_stuck_noncapacity": n_stuck,
        "n_max_iterations": n_max_iter,
        "n_error": n_error,
        "n_penalty": n_penalty,
        "n_negative_gap": n_neg_gap,
        "n_same_depot_DA_risk": n_same_depot_da_risk,
        "n_capacity_not_freed": n_capacity_not_freed,
        "n_length_invalid_cut": n_length_invalid_cut,
        "n_rejected_candidates": n_rejected_candidates,
        **gap_stats,
        **runtime_stats,
        **iter_stats,
        **cost_avgs,
        **deltas,
        "outliers": outliers,
    }


# ── Writers ──────────────────────────────────────────────────────────────────


def _record_to_dict(rec: RowRecord) -> Dict[str, Any]:
    """Convert a RowRecord to an ordered dict matching CONSOLIDATED_COLUMNS."""
    d = asdict(rec)
    return {col: d.get(col, "") for col in CONSOLIDATED_COLUMNS}


def write_consolidated_csv(records: List[RowRecord], path: str) -> Path:
    """Write all records to a consolidated CSV."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CONSOLIDATED_COLUMNS)
        w.writeheader()
        for rec in records:
            w.writerow(_record_to_dict(rec))
    return p


def write_consolidated_excel(records: List[RowRecord], path: str) -> Path:
    """Write all records to an Excel workbook (sheet 'Consolidated')."""
    try:
        import openpyxl
    except ImportError:
        logger.warning("openpyxl not available — skipping Excel output")
        return Path(path)

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Consolidated"

    ws.append(CONSOLIDATED_COLUMNS)
    for rec in records:
        d = _record_to_dict(rec)
        ws.append([d[col] for col in CONSOLIDATED_COLUMNS])

    wb.save(str(p))
    return p


def write_summary(summary: Dict[str, Any], path: str) -> Path:
    """Write aggregate summary as JSON."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    return p


def write_summary_markdown(summary: Dict[str, Any], path: str) -> Path:
    """Write aggregate summary as a Markdown table."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    lines = ["# Batch Summary\n"]
    lines.append("| Metric | Value |")
    lines.append("|---|---|")

    skip_keys = {"outliers"}
    for k, v in summary.items():
        if k in skip_keys:
            continue
        if isinstance(v, float):
            lines.append(f"| {k} | {v:.6f} |")
        else:
            lines.append(f"| {k} | {v} |")

    outliers = summary.get("outliers", [])
    if outliers:
        lines.append("\n## Outliers\n")
        lines.append("| row_id | instance | reason | detail |")
        lines.append("|---|---|---|---|")
        for o in outliers:
            detail = o.get("message", o.get("gap", ""))
            lines.append(f"| {o['row_id']} | {o['instance']} | {o['reason']} | {detail} |")

    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


__all__ = [
    "CONSOLIDATED_COLUMNS",
    "STATUS_ERROR",
    "STATUS_TIMEOUT",
    "RowRecord",
    "build_row_record",
    "build_error_record",
    "build_timeout_record",
    "run_rows",
    "summarize",
    "write_consolidated_csv",
    "write_consolidated_excel",
    "write_summary",
    "write_summary_markdown",
]
