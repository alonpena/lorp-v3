"""Plot helpers for the capacity-repair experiment outputs.

Inputs (under --out-dir): results.csv, convergence.csv, repairs.csv,
depot_audit.csv, routes.csv, da_pool_stats.csv.

Outputs land in <out-dir>/plots/.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import pandas as pd

from da_geometry import compute_max_distance
from dat_loader import load_dat
from instance_adapter import adapt_instance, spec_from_row
from instance_resolver import resolve_instance_path
from xlsx_loader import load_lorp_fsd_mapping


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Plot capacity-repair experiment outputs.")
    p.add_argument("--out-dir", required=True)
    p.add_argument("--rows", nargs="*", type=int, default=[])
    p.add_argument("--excel", default="results_MILP.xlsx")
    p.add_argument("--instance-folder", default="instances")
    p.add_argument("--old-export", default="pipeline_out/fsd_minimal_results.csv")
    return p.parse_args()


def _load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _resolve_inst(row_id: int, excel: str, instance_folder: str):
    mapping = load_lorp_fsd_mapping(excel, instance_folder=None)
    sub = mapping[mapping["row_id"] == row_id]
    if sub.empty:
        return None, None
    row = sub.iloc[0]
    config = spec_from_row(row)
    resolution = resolve_instance_path(config.instance, Path(instance_folder))
    if not resolution.ok:
        return None, config
    base = load_dat(resolution.path)
    return adapt_instance(base, config), config


def plot_instance(row_id: int, inst, config, plots_dir: Path) -> Optional[Path]:
    max_dist = compute_max_distance(inst)
    escala = 100.0 / max_dist if max_dist > 0 else 1.0
    radius_scaled = float(config.R)
    radius_raw = radius_scaled / escala if escala > 0 else radius_scaled

    fig, ax = plt.subplots(figsize=(9, 8))
    for c in inst.clients.values():
        ax.scatter(c["x"], c["y"], s=40, color="steelblue", alpha=0.8, zorder=3)
    for did, d in inst.depots.items():
        ax.scatter(d["x"], d["y"], s=350, color="crimson", marker="*",
                   edgecolor="black", linewidth=0.8, zorder=5)
        ax.annotate(f"D{did}", (d["x"], d["y"]), fontsize=9, fontweight="bold",
                    color="crimson", ha="center", va="top",
                    xytext=(0, -12), textcoords="offset points")
        circle = plt.Circle((d["x"], d["y"]), radius_raw, edgecolor="crimson",
                             facecolor="none", linestyle="--", alpha=0.3, linewidth=1.2)
        ax.add_patch(circle)
    handles = [
        mpatches.Patch(color="steelblue", label="Clients"),
        mpatches.Patch(color="crimson", label=f"Depots ({len(inst.depots)})"),
        mpatches.Patch(color="crimson", alpha=0.3, label=f"DA radius (raw equiv ≈ {radius_raw:.2f})"),
    ]
    ax.legend(handles=handles, loc="upper left", fontsize=9)
    ax.set_aspect("equal", "box")
    ax.set_title(
        f"row {row_id}  {config.instance}\n"
        f"R_scaled={radius_scaled}  R_raw_equiv={radius_raw:.2f}  scale={escala:.4f}",
        fontsize=10,
    )
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.grid(alpha=0.25, linestyle="--")
    path = plots_dir / f"instance_row{row_id}.png"
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_solution(row_id: int, iteration: int, inst, config,
                  routes_df: pd.DataFrame, repairs_df: pd.DataFrame,
                  results_df: pd.DataFrame, plots_dir: Path) -> Optional[Path]:
    sub = routes_df[(routes_df["row_id"] == row_id) & (routes_df["iteration"] == iteration)]
    if sub.empty:
        return None
    excluded_so_far = set()
    if not repairs_df.empty:
        rep = repairs_df[(repairs_df["row_id"] == row_id) & (repairs_df["iteration"] <= iteration)]
        excluded_so_far = set(zip(rep["depot_id"].astype(int), rep["client_id"].astype(int)))

    status_row = results_df[results_df["row_id"] == row_id]
    status = status_row["status"].iloc[0] if not status_row.empty else "?"

    fig, ax = plt.subplots(figsize=(9, 8))
    for c in inst.clients.values():
        ax.scatter(c["x"], c["y"], s=25, color="lightgray", alpha=0.7, zorder=2)
    for did, d in inst.depots.items():
        ax.scatter(d["x"], d["y"], s=320, color="crimson", marker="*",
                   edgecolor="black", linewidth=0.7, zorder=5)
        ax.annotate(f"D{did}", (d["x"], d["y"]), fontsize=9, fontweight="bold",
                    color="crimson", ha="center", va="top",
                    xytext=(0, -12), textcoords="offset points")

    n_violated = 0
    max_excess = 0.0
    for _, rec in sub.iterrows():
        depot = inst.depots[int(rec["depot_id"])]
        xy_dep = (depot["x"], depot["y"])
        seq_ids = [int(s) for s in str(rec["client_sequence"]).split() if s]
        if not seq_ids:
            continue
        xs = [xy_dep[0]] + [inst.clients[c]["x"] for c in seq_ids] + [xy_dep[0]]
        ys = [xy_dep[1]] + [inst.clients[c]["y"] for c in seq_ids] + [xy_dep[1]]
        if rec["kind"] == "routing":
            ax.plot(xs, ys, "-o", color="steelblue", linewidth=1.3, markersize=4,
                    alpha=0.85, zorder=3)
        else:
            ax.plot(xs[:2], ys[:2], "--o", color="seagreen", linewidth=1.0,
                    markersize=4, alpha=0.85, zorder=3)

    # highlight repaired/excluded clients
    for did, cid in excluded_so_far:
        c = inst.clients.get(cid)
        if c is None:
            continue
        ax.scatter(c["x"], c["y"], s=120, facecolor="none", edgecolor="red",
                   linewidth=1.6, zorder=6)

    handles = [
        mpatches.Patch(color="steelblue", label="Routing route"),
        mpatches.Patch(color="seagreen", label="DA route"),
        mpatches.Patch(facecolor="none", edgecolor="red", label="Excluded client"),
    ]
    ax.legend(handles=handles, loc="upper left", fontsize=9)
    ax.set_aspect("equal", "box")
    ax.set_title(
        f"row {row_id}  iter {iteration}  status={status}\n{config.instance}",
        fontsize=10,
    )
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.grid(alpha=0.25, linestyle="--")
    path = plots_dir / f"solution_row{row_id}_iter{iteration}.png"
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_capacity_excess_by_iteration(conv_df: pd.DataFrame, plots_dir: Path) -> Optional[Path]:
    if conv_df.empty:
        return None
    fig, ax = plt.subplots(figsize=(9, 5))
    grouped = conv_df.groupby(["row_id", "iteration"])["max_excess"].max().reset_index()
    repaired_rows = grouped.groupby("row_id")["iteration"].max()
    repaired_rows = repaired_rows[repaired_rows > 0].index.tolist()
    for rid in sorted(set(grouped["row_id"])):
        sub = grouped[grouped["row_id"] == rid].sort_values("iteration")
        marker = "o-" if rid in repaired_rows else "o:"
        ax.plot(sub["iteration"], sub["max_excess"], marker, label=f"row {rid}", alpha=0.7)
    ax.axhline(0, color="black", linewidth=0.6)
    ax.set_xlabel("Iteration")
    ax.set_ylabel("Max excess (demand units)")
    ax.set_title("Capacity excess by iteration")
    ax.grid(alpha=0.3, linestyle="--")
    if len(set(grouped["row_id"])) <= 12:
        ax.legend(fontsize=8, ncol=2)
    path = plots_dir / "capacity_excess_by_iteration.png"
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_repaired_before_after(conv_df: pd.DataFrame, results_df: pd.DataFrame,
                               plots_dir: Path) -> Optional[Path]:
    if conv_df.empty or results_df.empty:
        return None
    final_iter = conv_df.groupby("row_id")["iteration"].max().reset_index()
    repaired = final_iter[final_iter["iteration"] > 0]
    if repaired.empty:
        return None

    rows: List[Dict[str, Any]] = []
    for _, r in repaired.iterrows():
        rid = r["row_id"]
        first = conv_df[(conv_df["row_id"] == rid) & (conv_df["iteration"] == 0)]
        if first.empty:
            continue
        first_total = float(first["post_total_cost"].iloc[0])
        final = results_df[results_df["row_id"] == rid]
        if final.empty:
            continue
        final_total = float(final["costo_total_pyvrp"].iloc[0])
        rows.append({"row_id": rid, "before": first_total, "after": final_total})
    if not rows:
        return None
    df = pd.DataFrame(rows).sort_values("row_id")
    fig, ax = plt.subplots(figsize=(9, 5))
    x = range(len(df))
    width = 0.4
    ax.bar([i - width / 2 for i in x], df["before"], width, label="iter 0", color="steelblue")
    ax.bar([i + width / 2 for i in x], df["after"], width, label="final", color="darkorange")
    ax.set_xticks(list(x))
    ax.set_xticklabels([f"row {r}" for r in df["row_id"]])
    ax.set_ylabel("Total cost")
    ax.set_title("Repaired rows — cost before vs. after")
    ax.legend()
    ax.grid(axis="y", alpha=0.3, linestyle="--")
    path = plots_dir / "repaired_rows_gap_before_after.png"
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_gap_by_FA(results_df: pd.DataFrame, excel: str, plots_dir: Path) -> Optional[Path]:
    if results_df.empty:
        return None
    mapping = load_lorp_fsd_mapping(excel, instance_folder=None)
    if "F_A" not in mapping.columns:
        return None
    merged = results_df.merge(mapping[["row_id", "F_A"]], on="row_id", how="left")
    merged = merged.dropna(subset=["abs_gap_pyvrp_vs_milp", "F_A"])
    if merged.empty:
        return None
    fig, ax = plt.subplots(figsize=(9, 5))
    status_groups = merged.groupby("status")
    for status, g in status_groups:
        ax.scatter(g["F_A"], g["abs_gap_pyvrp_vs_milp"], label=status, alpha=0.7)
    ax.set_xlabel("F_A")
    ax.set_ylabel("|gap| PyVRP vs MILP")
    ax.set_title("Gap by F_A")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3, linestyle="--")
    path = plots_dir / "gap_by_FA.png"
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_gap_old_vs_new(results_df: pd.DataFrame, old_export: Path,
                        plots_dir: Path) -> Optional[Path]:
    if results_df.empty or not old_export.exists():
        return None
    old = pd.read_csv(old_export)
    if "row_id" not in old.columns:
        return None
    new = results_df[["row_id", "abs_gap_pyvrp_vs_milp"]].rename(
        columns={"abs_gap_pyvrp_vs_milp": "abs_gap_new"})
    candidates = ["abs_gap_pyvrp_vs_milp", "gap_final", "abs_gap"]
    old_gap_col = next((c for c in candidates if c in old.columns), None)
    if old_gap_col is None:
        return None
    old_small = old[["row_id", old_gap_col]].rename(columns={old_gap_col: "abs_gap_old"})
    merged = old_small.merge(new, on="row_id", how="inner").dropna()
    if merged.empty:
        return None
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.scatter(merged["abs_gap_old"], merged["abs_gap_new"], alpha=0.7)
    lim_max = float(max(merged["abs_gap_old"].max(), merged["abs_gap_new"].max()))
    ax.plot([0, lim_max], [0, lim_max], "k--", linewidth=1)
    ax.set_xlabel("|gap| old pipeline")
    ax.set_ylabel("|gap| new pipeline")
    ax.set_title("Gap: old vs new")
    ax.grid(alpha=0.3, linestyle="--")
    path = plots_dir / "gap_old_vs_new.png"
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return path


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    plots_dir = out_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    results = _load_csv(out_dir / "results.csv")
    convergence = _load_csv(out_dir / "convergence.csv")
    repairs = _load_csv(out_dir / "repairs.csv")
    routes = _load_csv(out_dir / "routes.csv")

    saved: List[Path] = []

    for row_id in args.rows:
        inst, config = _resolve_inst(row_id, args.excel, args.instance_folder)
        if inst is None or config is None:
            print(f"  [skip] row {row_id} could not be resolved")
            continue
        p = plot_instance(row_id, inst, config, plots_dir)
        if p:
            saved.append(p)
            print(f"  saved {p}")
        if not routes.empty:
            iters = sorted(routes.loc[routes["row_id"] == row_id, "iteration"].unique().tolist())
            for it in iters:
                p = plot_solution(row_id, int(it), inst, config, routes, repairs, results, plots_dir)
                if p:
                    saved.append(p)
                    print(f"  saved {p}")

    p = plot_capacity_excess_by_iteration(convergence, plots_dir)
    if p:
        saved.append(p)
        print(f"  saved {p}")
    p = plot_repaired_before_after(convergence, results, plots_dir)
    if p:
        saved.append(p)
        print(f"  saved {p}")
    p = plot_gap_by_FA(results, args.excel, plots_dir)
    if p:
        saved.append(p)
        print(f"  saved {p}")
    p = plot_gap_old_vs_new(results, Path(args.old_export), plots_dir)
    if p:
        saved.append(p)
        print(f"  saved {p}")

    print(f"\nDone. {len(saved)} plot(s) written to {plots_dir}")


if __name__ == "__main__":
    main()
