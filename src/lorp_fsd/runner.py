"""Row-level iterative runner (Phase 5).

Connects builder → solver → parser → cost reconstruction → capacity/feasibility
audit → savings repair → rebuild/rerun, saving per-iteration artifacts. Runs ONE
Excel row. No full-Excel batch here (Phase 6).

Loop (spec §11)::

    forbidden = set()
    for iteration in 0 .. max_repair_iterations:
        build relaxed model with forbidden
        solve (num_solve_runs x seconds_per_run, prefer feasible)
        parse / reconstruct cost / audit capacity + feasibility
        save artifacts (+ plot)
        if fully_feasible: stop (FEASIBLE, report GAP)
        repair = select savings-based removals
        if repair infeasible or empty: stop (REPAIR_INFEASIBLE)
        forbidden |= repair.selected
    else: stop (MAX_ITERATIONS)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from .artifacts import (
    iteration_dir,
    write_basic_row_report_artifacts,
    write_iteration_artifacts,
    write_row_reporting_artifacts,
)
from .capacity_audit import audit_capacity
from .cost_reconstruction import comparison_metric, reconstruct_cost
from .dat_parser import DEFAULT_INSTANCE_FOLDERS, parse_dat, resolve_dat_path
from .excel_loader import load_row
from .facility_sizing import size_capacity  # noqa: F401  (kept for downstream convenience)
from .feasibility import audit_feasibility, make_feasibility_checker
from .instance import build_facility_design
from .pyvrp_builder import build_relaxed_model
from .repair import REPAIR_POLICY_BASELINE, build_repair_candidates, select_forbidden_assignments
from .scaling import build_scaled_geometry
from .solution_parser import parse_solution

try:
    from pyvrp.stop import MaxRuntime
except Exception:  # pragma: no cover
    MaxRuntime = None  # type: ignore[assignment]

STATUS_FEASIBLE = "FEASIBLE"
STATUS_REPAIR_INFEASIBLE = "REPAIR_INFEASIBLE"  # overloaded depot(s) cannot be safely repaired
STATUS_STUCK_NONCAPACITY = "STUCK_NONCAPACITY_VIOLATION"  # capacity OK, but a non-capacity constraint is violated
STATUS_MAX_ITERATIONS = "MAX_ITERATIONS"


@dataclass
class IterationResult:
    iteration: int
    parsed: object
    cost: object
    capacity: object
    feasibility: object
    metric: object
    repair_selection: Optional[object]
    solve_time: float
    forbidden_before: frozenset
    removed_clients_prev: frozenset
    artifact_paths: Dict[str, Path] = field(default_factory=dict)
    capacity_not_freed_count: int = 0


@dataclass
class RowRunResult:
    row_index: Optional[int]
    instance_name: str
    status: str
    final_iteration: int
    iterations: List[IterationResult]
    final_metric: object
    output_dir: Path
    total_solve_time: float
    final_forbidden: frozenset
    repair_candidate_policy: str = REPAIR_POLICY_BASELINE
    route_length_repair_attempts: int = 0

    @property
    def n_iterations(self) -> int:
        return len(self.iterations)

    @property
    def final(self) -> IterationResult:
        return self.iterations[-1]


def _solve_multi(model, seconds_per_run: float, num_solve_runs: int, seed: int):
    if MaxRuntime is None:  # pragma: no cover
        raise ImportError("pyvrp not installed. Run `uv sync`.")
    best_res = None
    best_key: Optional[Tuple[int, float]] = None
    t0 = time.perf_counter()
    for k in range(num_solve_runs):
        res = model.solve(stop=MaxRuntime(seconds_per_run), seed=seed + k, display=False)
        key = (0 if bool(res.is_feasible()) else 1, float(res.cost()))  # prefer feasible, then min cost
        if best_key is None or key < best_key:
            best_key, best_res = key, res
    return best_res, time.perf_counter() - t0


def compute_repair_step(
    parsed,
    capacity,
    geometry,
    config,
    facility_design,
    instance,
    forbidden,
    *,
    repair_candidate_policy: str = REPAIR_POLICY_BASELINE,
    rejected_repair_candidates=None,
):
    """One savings-repair selection step (no rebuild). Exposed for testing."""
    demands = {j: c.demand for j, c in instance.clients.items()}
    candidates = build_repair_candidates(parsed.routes, capacity, geometry, config.F_R, demands)
    excess_by_depot = {i: rec.excess for i, rec in capacity.by_depot.items()}
    checker = make_feasibility_checker(facility_design.active_depot_ids, geometry, config.R)
    return select_forbidden_assignments(
        candidates,
        excess_by_depot,
        set(forbidden),
        checker,
        active_depots=facility_design.active_depot_ids,
        geometry=geometry,
        R=config.R,
        Length=config.Length,
        repair_candidate_policy=repair_candidate_policy,
        rejected_repair_candidates=rejected_repair_candidates,
    )


def run_row(
    config,
    instance,
    geometry,
    facility_design,
    *,
    output_root="outputs",
    run_id: Optional[str] = None,
    seconds_per_run: float = 30.0,
    num_solve_runs: int = 3,
    max_repair_iterations: int = 5,
    seed: int = 0,
    make_plots: bool = True,
    repair_candidate_policy: str = REPAIR_POLICY_BASELINE,
    max_repair_attempts: int = 1,
) -> RowRunResult:
    if run_id is None:
        run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S")
    out_dir = iteration_dir(output_root, run_id, instance.name)

    forbidden: Set[Tuple[int, int]] = set()
    removed_prev: Set[int] = set()
    selected_prev_pairs: Set[Tuple[int, int]] = set()
    rejected_repair_candidates: Set[Tuple[int, int, str]] = set()
    iterations: List[IterationResult] = []
    total_time = 0.0
    status: Optional[str] = None
    final_metric = None

    for it in range(max_repair_iterations + 1):
        model, info = build_relaxed_model(instance, config, geometry, facility_design, frozenset(forbidden))
        res, solve_time = _solve_multi(model, seconds_per_run, num_solve_runs, seed)
        total_time += solve_time

        parsed = parse_solution(res, model, info, instance, geometry, config, iteration=it)
        cost = reconstruct_cost(parsed, instance, config, facility_design)
        cap = audit_capacity(parsed, facility_design, iteration=it)
        feas = audit_feasibility(parsed, cap, instance, config, geometry, iteration=it)
        metric = comparison_metric(cost.total, config.UB, feas.fully_feasible)
        final_metric = metric

        is_last = it == max_repair_iterations
        repair: Optional[object] = None
        iter_status = STATUS_FEASIBLE if feas.fully_feasible else "RELAXED_INFEASIBLE"

        capacity_not_freed_count = sum(
            1 for a in parsed.da_assignments if (a.depot_id, a.client_id) in selected_prev_pairs
        )

        if not feas.fully_feasible:
            repair = compute_repair_step(
                parsed,
                cap,
                geometry,
                config,
                facility_design,
                instance,
                forbidden,
                repair_candidate_policy=repair_candidate_policy,
                rejected_repair_candidates=rejected_repair_candidates,
            )
            rejected_repair_candidates.update(getattr(repair, "rejected_candidates", set()))

        paths = write_iteration_artifacts(
            output_dir=out_dir, iteration=it, row_index=config.row_index, instance=instance,
            config=config, geometry=geometry, facility_design=facility_design, parsed=parsed,
            cost=cost, capacity=cap, feasibility=feas, metric=metric, forbidden=set(forbidden),
            repair_selection=repair, solve_time=solve_time, status=iter_status,
            capacity_not_freed_count=capacity_not_freed_count,
        )
        if make_plots:
            from .plotting import plot_instance_state, plot_iteration
            paths["instance"] = plot_instance_state(
                out_dir / f"iteration_{it:02d}_instance.png", instance=instance,
                facility_design=facility_design, config=config, iteration=it,
                row_index=config.row_index,
            )
            paths["solution"] = plot_iteration(
                out_dir / f"iteration_{it:02d}_solution.png", instance=instance,
                facility_design=facility_design, parsed=parsed, capacity=cap, config=config,
                iteration=it, forbidden=set(forbidden), removed_clients=set(removed_prev),
                fully_feasible=feas.fully_feasible, row_index=config.row_index,
                status=iter_status, cost=cost, metric=metric,
            )

        iterations.append(IterationResult(
            iteration=it, parsed=parsed, cost=cost, capacity=cap, feasibility=feas, metric=metric,
            repair_selection=repair, solve_time=solve_time, forbidden_before=frozenset(forbidden),
            removed_clients_prev=frozenset(removed_prev), artifact_paths=paths,
            capacity_not_freed_count=capacity_not_freed_count,
        ))

        if feas.fully_feasible:
            status = STATUS_FEASIBLE
            break
        if repair.repair_infeasible:
            # an overloaded depot's excess cannot be covered with safe removals
            status = STATUS_REPAIR_INFEASIBLE
            break
        if not repair.selected:
            # nothing to remove: capacity is satisfied but a non-capacity
            # constraint (e.g. route length) is violated, which the v3 baseline
            # capacity-only repair does not address.
            status = STATUS_STUCK_NONCAPACITY
            break
        if is_last:
            status = STATUS_MAX_ITERATIONS
            break

        forbidden = set(repair.updated_forbidden)
        selected_prev_pairs = set(repair.selected)
        removed_prev = {c for (_, c) in repair.selected}

    result = RowRunResult(
        row_index=config.row_index, instance_name=instance.name, status=status or STATUS_MAX_ITERATIONS,
        final_iteration=iterations[-1].iteration, iterations=iterations, final_metric=final_metric,
        output_dir=out_dir, total_solve_time=total_time, final_forbidden=frozenset(forbidden),
        repair_candidate_policy=repair_candidate_policy, route_length_repair_attempts=0,
    )
    write_row_reporting_artifacts(out_dir, iterations, result.status)
    write_basic_row_report_artifacts(
        out_dir, result, config, instance=instance, geometry=geometry, facility_design=facility_design,
    )
    return result


def run_row_from_excel(
    xlsx_path,
    row_index: int,
    *,
    instance_folders=DEFAULT_INSTANCE_FOLDERS,
    root=".",
    output_root="outputs",
    run_id: Optional[str] = None,
    seconds_per_run: float = 30.0,
    num_solve_runs: int = 3,
    max_repair_iterations: int = 5,
    seed: int = 0,
    make_plots: bool = True,
    repair_candidate_policy: str = REPAIR_POLICY_BASELINE,
    max_repair_attempts: int = 1,
) -> RowRunResult:
    """Convenience: load a row, resolve its instance, build geometry/design, run it."""
    config = load_row(xlsx_path, row_index)
    resolution = resolve_dat_path(config.name, instance_folders, root=root)
    if not resolution.ok:
        raise FileNotFoundError(f"could not resolve instance {config.name!r}: {resolution.status}")
    instance = parse_dat(resolution.path)
    geometry = build_scaled_geometry(instance)
    facility_design = build_facility_design(instance, config)
    return run_row(
        config, instance, geometry, facility_design, output_root=output_root, run_id=run_id,
        seconds_per_run=seconds_per_run, num_solve_runs=num_solve_runs,
        max_repair_iterations=max_repair_iterations, seed=seed, make_plots=make_plots,
        repair_candidate_policy=repair_candidate_policy, max_repair_attempts=max_repair_attempts,
    )


__all__ = [
    "STATUS_FEASIBLE", "STATUS_REPAIR_INFEASIBLE", "STATUS_STUCK_NONCAPACITY",
    "STATUS_MAX_ITERATIONS", "IterationResult", "RowRunResult", "compute_repair_step",
    "run_row", "run_row_from_excel",
]
