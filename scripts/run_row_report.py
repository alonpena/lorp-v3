#!/usr/bin/env python
"""Run one (or a few) Excel rows with tabu_penalty repair, build the static HTML
report with plots, and open it in the browser (Phase 9 convenience).

Each row gets its own run-id (``<run-id-prefix>_row<NN>``) so rows that share a
``.dat`` instance never overwrite each other's artifacts.

Examples::

    # one row, full solve settings
    python scripts/run_row_report.py --row 7 --seconds 30 --runs 3 --max-iter 10

    # the rows that were REPAIR_INFEASIBLE in first20 (5, 6, 7, 18)
    python scripts/run_row_report.py --conflictive --seconds 30 --runs 3

    # an explicit set
    python scripts/run_row_report.py --rows 5 6 7 18 --seconds 10

Thin wrapper: calls the existing runner + HTML writer. No solver/repair logic.
"""
from __future__ import annotations

import argparse
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lorp_fsd.html_report import write_index_html  # noqa: E402
from lorp_fsd.runner import run_row_from_excel  # noqa: E402

# rows that ended REPAIR_INFEASIBLE in run first20_tabu_penalty_30s3r
CONFLICTIVE_ROWS = [5, 6, 7, 18]


def run_one(args, row: int) -> tuple[str, Path, bool]:
    """Run one row, write its HTML, return (status, index_html_path, opened)."""
    run_id = f"{args.run_id_prefix}_row{row:02d}"
    result = run_row_from_excel(
        args.xlsx, row,
        root=str(ROOT), output_root=args.output_root, run_id=run_id,
        seconds_per_run=args.seconds, num_solve_runs=args.runs,
        max_repair_iterations=args.max_iter, seed=args.seed,
        make_plots=not args.no_plots,
        repair_candidate_policy=args.repair_policy,
        repair_mode=args.repair_mode,
        penalty_factor=args.penalty_factor,
        tabu_tenure=args.tabu_tenure,
    )
    html_path = write_index_html(result.output_dir)
    f = result.final
    print(
        f"row {row:>2} | {result.instance_name:<14} | {result.status:<22} | "
        f"iters={result.n_iterations} | GAP/metric={f.metric.label}="
        f"{f.metric.value} | Z={f.cost.total:.4f} UB={f.metric.ub_milp} | "
        f"{result.total_solve_time:.1f}s"
    )
    print(f"        report: {html_path}")
    opened = False
    if not args.no_open:
        opened = webbrowser.open(f"file://{html_path.resolve()}")
    return result.status, html_path, opened


def main() -> int:
    p = argparse.ArgumentParser(
        description="Run Excel row(s) with tabu_penalty, build + open the HTML report.",
    )
    sel = p.add_mutually_exclusive_group(required=True)
    sel.add_argument("--row", type=int, help="single 0-based Excel row")
    sel.add_argument("--rows", type=int, nargs="+", help="explicit list of rows")
    sel.add_argument("--conflictive", action="store_true",
                     help=f"run the first20 REPAIR_INFEASIBLE rows {CONFLICTIVE_ROWS}")

    p.add_argument("--xlsx", default=str(ROOT / "results_MILP.xlsx"))
    p.add_argument("--output-root", default=str(ROOT / "outputs"))
    p.add_argument("--run-id-prefix", default="ui_tabu",
                   help="run-id prefix; each row becomes <prefix>_row<NN>")
    # solve settings
    p.add_argument("--seconds", type=float, default=30.0, help="seconds per solve run")
    p.add_argument("--runs", type=int, default=3, help="solve runs (seeds)")
    p.add_argument("--max-iter", type=int, default=10, help="max repair iterations")
    p.add_argument("--seed", type=int, default=0)
    # repair settings (tabu_penalty by default)
    p.add_argument("--repair-policy", default="safe_both",
                   choices=["baseline", "safe_length", "safe_capacity_release", "safe_both"])
    p.add_argument("--repair-mode", default="tabu_penalty",
                   choices=["hard_forbid", "soft_penalty", "tabu_penalty"])
    p.add_argument("--penalty-factor", type=float, default=100.0)
    p.add_argument("--tabu-tenure", type=int, default=3)
    p.add_argument("--no-plots", action="store_true")
    p.add_argument("--no-open", action="store_true", help="do not open the browser")
    args = p.parse_args()

    if args.conflictive:
        rows = list(CONFLICTIVE_ROWS)
    elif args.rows is not None:
        rows = args.rows
    else:
        rows = [args.row]

    print(f"running {len(rows)} row(s): {rows} | mode={args.repair_mode} "
          f"policy={args.repair_policy} | {args.seconds}s x {args.runs} runs\n")

    results = []
    for row in rows:
        results.append((row, *run_one(args, row)))

    if len(results) > 1:
        print("\n=== summary ===")
        for row, status, html_path, _opened in results:
            print(f"row {row:>2}: {status:<22} {html_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
