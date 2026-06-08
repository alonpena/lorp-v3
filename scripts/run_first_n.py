#!/usr/bin/env python
"""Run the first N Excel rows and produce consolidated CSV + summary.

Usage::

    .venv/bin/python scripts/run_first_n.py --n 10 --seconds 30 --runs 3 --max-iter 5 --run-id first10

Outputs land in ``outputs/<run-id>/consolidated.csv`` and ``outputs/<run-id>/summary.json``.
"""

import argparse
import logging
import sys
from pathlib import Path

# Ensure src/ is importable when running as standalone script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from lorp_fsd.batch import run_rows, summarize, write_consolidated_csv, write_consolidated_excel, write_summary, write_summary_markdown


def main():
    parser = argparse.ArgumentParser(description="Run first N Excel rows (LoRP-FSD batch).")
    parser.add_argument("--n", type=int, required=True, help="Number of rows (0..N-1)")
    parser.add_argument("--xlsx", default="results_MILP.xlsx", help="Excel file")
    parser.add_argument("--seconds", type=float, default=30.0, help="Seconds per solve run")
    parser.add_argument("--runs", type=int, default=3, help="Number of solve runs per iteration")
    parser.add_argument("--max-iter", type=int, default=5, help="Max repair iterations")
    parser.add_argument("--row-timeout-seconds", type=float, default=None, help="Wall-clock timeout for each Excel row (disabled by default)")
    parser.add_argument("--repair-policy", default="baseline", choices=["baseline", "safe_length", "safe_capacity_release", "safe_both"], help="Repair candidate safety policy")
    parser.add_argument("--repair-mode", default="tabu_penalty", choices=["hard_forbid", "soft_penalty", "tabu_penalty"], help="How selected routing pairs are suppressed (default: tabu_penalty)")
    parser.add_argument("--penalty-factor", type=float, default=100.0, help="Soft/tabu penalty = factor * route_max_distance_int")
    parser.add_argument("--tabu-tenure", type=int, default=3, help="Tabu tenure (iterations) for tabu_penalty mode")
    parser.add_argument("--max-repair-attempts", type=int, default=1, help="Reserved for bounded Phase 7 repair retries")
    parser.add_argument("--seed", type=int, default=0, help="RNG seed")
    parser.add_argument("--run-id", default="first_n", help="Run identifier")
    parser.add_argument("--plots", action="store_true", help="Generate per-iteration plots (off by default)")
    parser.add_argument("--excel", action="store_true", help="Also write Excel output")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    row_indices = list(range(args.n))
    out_dir = Path("outputs") / args.run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    ckpt = str(out_dir / "checkpoint.csv")

    records = run_rows(
        row_indices,
        args.xlsx,
        root=".",
        output_root="outputs",
        run_id=args.run_id,
        seconds_per_run=args.seconds,
        num_solve_runs=args.runs,
        max_repair_iterations=args.max_iter,
        row_timeout_seconds=args.row_timeout_seconds,
        seed=args.seed,
        make_plots=args.plots,
        checkpoint_csv=ckpt,
        repair_candidate_policy=args.repair_policy,
        max_repair_attempts=args.max_repair_attempts,
        repair_mode=args.repair_mode,
        penalty_factor=args.penalty_factor,
        tabu_tenure=args.tabu_tenure,
    )

    csv_path = write_consolidated_csv(records, str(out_dir / "consolidated.csv"))
    print(f"Consolidated CSV: {csv_path}")

    if args.excel:
        xlsx_path = write_consolidated_excel(records, str(out_dir / "consolidated.xlsx"))
        print(f"Consolidated Excel: {xlsx_path}")

    summary = summarize(records)
    json_path = write_summary(summary, str(out_dir / "summary.json"))
    md_path = write_summary_markdown(summary, str(out_dir / "summary.md"))
    print(f"Summary JSON: {json_path}")
    print(f"Summary MD:   {md_path}")

    # Print quick status table.
    print(f"\n{'='*60}")
    print(f"  Rows: {len(records)}  |  FEASIBLE: {summary['n_success']}  |  "
          f"STUCK: {summary['n_stuck_noncapacity']}  |  "
          f"REPAIR_FAIL: {summary['n_repair_failed']}  |  "
          f"MAX_ITER: {summary['n_max_iterations']}  |  "
          f"ERROR: {summary['n_error']}")
    if summary.get("mean_gap") is not None:
        print(f"  GAP: min={summary['min_gap']:.6f}  mean={summary['mean_gap']:.6f}  max={summary['max_gap']:.6f}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
