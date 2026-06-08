"""Single-row demo runner for the capacity-repair pipeline.

Runs the same iterative loop as run_capacity_repair_batch.py for a single
selected Excel row, with verbose printing, exports the standard CSVs, and
auto-generates all available plots into <out-dir>/plots/.

Smoke:
    uv run python demo_capacity_repair_row.py \
        --row-id 3 --runtime 1 --runs 1 --max-iters 2 \
        --out-dir pipeline_out/demo_row3_smoke
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from da_geometry import compute_max_distance
from dat_loader import load_dat
from instance_adapter import adapt_instance, spec_from_row
from instance_resolver import resolve_instance_path
from run_capacity_repair_batch import run_one
from xlsx_loader import load_lorp_fsd_mapping


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Single-row capacity-repair demo.")
    p.add_argument("--row-id", type=int, required=True)
    p.add_argument("--excel", default="results_MILP.xlsx")
    p.add_argument("--instance-folder", default="instances")
    p.add_argument("--runtime", type=int, default=5)
    p.add_argument("--runs", type=int, default=2)
    p.add_argument("--max-iters", type=int, default=5)
    p.add_argument("--out-dir", default="pipeline_out/demo_row")
    p.add_argument("--encode-cost-factors", action="store_true")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    mapping = load_lorp_fsd_mapping(args.excel, instance_folder=None)
    sub = mapping[mapping["row_id"] == args.row_id]
    if sub.empty:
        print(f"[error] row_id={args.row_id} not found in Excel")
        sys.exit(1)
    row = sub.iloc[0]
    config = spec_from_row(row)

    # Pre-flight prints
    print("=" * 60)
    print("DEMO capacity-repair (single row)")
    print("=" * 60)
    print(f"row_id  : {config.row_id}")
    print(f"instance: {config.instance}")
    print(f"F_R={config.F_R}  F_A={config.F_A}  R={config.R}  Length={config.Length}")
    print(f"UB MILP : {config.UB}")
    print(f"encode_cost_factors = {args.encode_cost_factors}")

    resolution = resolve_instance_path(config.instance, Path(args.instance_folder))
    if not resolution.ok:
        print(f"[error] cannot resolve instance: {resolution.status}")
        sys.exit(1)
    base = load_dat(resolution.path)
    inst = adapt_instance(base, config)

    max_dist = compute_max_distance(inst)
    escala = 100.0 / max_dist if max_dist > 0 else 1.0
    radius_raw = config.R / escala if escala > 0 else config.R
    print(f"Arslan scale = {escala:.6f}")
    print(f"R_scaled = {config.R}   R_raw_equiv ≈ {radius_raw:.3f}")
    print(f"objective_mode = "
          f"{'weighted_scaled_distance' if args.encode_cost_factors else 'scaled_distance'}")
    print("Active depots:")
    for did, d in inst.depots.items():
        print(f"  d{did}: cap={d['cap']}  fixed_cost={d['fixed_cost']}")
    total_demand = sum(c["demand"] for c in inst.clients.values())
    print(f"Total demand = {total_demand}   n_clients = {len(inst.clients)}")

    # Reuse the same loop as the batch runner.
    class _RunArgs:
        encode_cost_factors = args.encode_cost_factors
        runtime = args.runtime
        runs = args.runs
        max_iters = args.max_iters

    convergence: List[Dict[str, Any]] = []
    repairs: List[Dict[str, Any]] = []
    depot_audit: List[Dict[str, Any]] = []
    routes: List[Dict[str, Any]] = []
    da_pool: List[Dict[str, Any]] = []

    result_rec = run_one(
        row, Path(args.instance_folder), _RunArgs(),
        convergence, repairs, depot_audit, routes, da_pool,
    )

    paths = {
        "results": out_dir / "results.csv",
        "convergence": out_dir / "convergence.csv",
        "repairs": out_dir / "repairs.csv",
        "depot_audit": out_dir / "depot_audit.csv",
        "routes": out_dir / "routes.csv",
        "da_pool_stats": out_dir / "da_pool_stats.csv",
    }
    pd.DataFrame([result_rec]).to_csv(paths["results"], index=False)
    pd.DataFrame(convergence).to_csv(paths["convergence"], index=False)
    pd.DataFrame(repairs).to_csv(paths["repairs"], index=False)
    pd.DataFrame(depot_audit).to_csv(paths["depot_audit"], index=False)
    pd.DataFrame(routes).to_csv(paths["routes"], index=False)
    pd.DataFrame(da_pool).to_csv(paths["da_pool_stats"], index=False)
    print("\nWrote:")
    for k, p in paths.items():
        print(f"  {p}")

    # Auto-plot
    print("\nPlots:")
    cmd = [
        sys.executable,
        "plot_capacity_repair_cases.py",
        "--out-dir", str(out_dir),
        "--rows", str(args.row_id),
        "--excel", args.excel,
        "--instance-folder", args.instance_folder,
    ]
    subprocess.run(cmd, check=False)


if __name__ == "__main__":
    main()
