#!/usr/bin/env python
"""Run one Excel LoRP-FSD row through the iterative PyVRP runner (Phase 5).

Usage:
    PYTHONPATH=src python scripts/run_row.py --row 0
    python scripts/run_row.py --row 5 --seconds 30 --runs 3 --max-iter 5 --run-id demo
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# allow running without installing the package
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lorp_fsd.runner import run_row_from_excel  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Run one LoRP-FSD Excel row through the iterative runner.")
    p.add_argument("--row", type=int, default=0, help="0-based row index in sheet LoRP-FSD")
    p.add_argument("--xlsx", default=str(ROOT / "results_MILP.xlsx"))
    p.add_argument("--output-root", default=str(ROOT / "outputs"))
    p.add_argument("--run-id", default=None)
    p.add_argument("--seconds", type=float, default=30.0, help="seconds per solve run")
    p.add_argument("--runs", type=int, default=3, help="number of solve runs (seeds)")
    p.add_argument("--max-iter", type=int, default=5, help="max repair iterations")
    p.add_argument("--repair-policy", default="baseline", choices=["baseline", "safe_length", "safe_capacity_release", "safe_both"], help="repair candidate safety policy")
    p.add_argument("--repair-mode", default="tabu_penalty", choices=["hard_forbid", "soft_penalty", "tabu_penalty"], help="how selected routing pairs are suppressed (default: tabu_penalty)")
    p.add_argument("--penalty-factor", type=float, default=100.0, help="soft/tabu penalty = factor * route_max_distance_int")
    p.add_argument("--tabu-tenure", type=int, default=3, help="tabu tenure (iterations) for tabu_penalty mode")
    p.add_argument("--max-repair-attempts", type=int, default=1, help="reserved for bounded Phase 7 repair retries")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--no-plots", action="store_true")
    args = p.parse_args()

    result = run_row_from_excel(
        args.xlsx, args.row, root=str(ROOT), output_root=args.output_root, run_id=args.run_id,
        seconds_per_run=args.seconds, num_solve_runs=args.runs,
        max_repair_iterations=args.max_iter, seed=args.seed, make_plots=not args.no_plots,
        repair_candidate_policy=args.repair_policy, max_repair_attempts=args.max_repair_attempts,
        repair_mode=args.repair_mode, penalty_factor=args.penalty_factor, tabu_tenure=args.tabu_tenure,
    )

    f = result.final
    print(f"\ninstance      : {result.instance_name} (row {result.row_index})")
    print(f"status        : {result.status}")
    print(f"iterations    : {result.n_iterations} (final iter {result.final_iteration})")
    print(f"repair policy : {result.repair_candidate_policy}")
    print(f"repair mode   : {result.repair_mode}")
    print(f"total solve s : {result.total_solve_time:.2f}")
    print(f"Z_PyVRP       : {f.cost.total:.4f}   UB_MILP: {f.metric.ub_milp}")
    print(f"metric        : {f.metric.label} = {f.metric.value}")
    print(f"routing routes: {f.parsed.n_routing_routes}   DA: {f.parsed.n_da_assignments}")
    print(f"capacity feas : {f.capacity.capacity_feasible}   fully feasible: {f.feasibility.fully_feasible}")
    print(f"artifacts     : {result.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
