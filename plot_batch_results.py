from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Plot LoRP-FSD batch result CSV.")
    p.add_argument("--csv", default="pipeline_out/fsd_batch_results_with_stats.csv")
    p.add_argument("--out-dir", default="pipeline_out/plots")
    p.add_argument("--gap-threshold", type=float, default=0.20)
    return p.parse_args()


def _load(csv_path: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    df = pd.read_csv(csv_path)
    results = df[df["record_type"] == "RESULT"].copy()
    ok = results[results["run_status"] == "OK"].copy()
    return df, results, ok


def _save(fig, out_dir: Path, name: str) -> None:
    path = out_dir / name
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {path}")


def plot_status_counts(results: pd.DataFrame, out_dir: Path) -> None:
    counts = results["run_status"].fillna("UNKNOWN").value_counts().sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars = ax.bar(counts.index.astype(str), counts.values, color="steelblue", alpha=0.85)
    for b in bars:
        ax.text(b.get_x() + b.get_width() / 2, b.get_height(), f"{int(b.get_height())}", ha="center", va="bottom", fontsize=9)
    ax.set_title("Run status counts")
    ax.set_ylabel("Rows")
    ax.grid(axis="y", alpha=0.25, linestyle="--")
    _save(fig, out_dir, "status_counts.png")


def plot_gap_hist(ok: pd.DataFrame, out_dir: Path, threshold: float) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(ok["abs_gap_pyvrp_vs_milp"].dropna(), bins=30, color="steelblue", alpha=0.85, edgecolor="white")
    ax.axvline(threshold, color="red", linestyle="--", linewidth=1.5, label=f"threshold={threshold:.0%}")
    ax.set_title("Absolute gap distribution |PyVRP − MILP| / MILP")
    ax.set_xlabel("Absolute gap")
    ax.set_ylabel("Rows")
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.legend()
    ax.grid(alpha=0.25, linestyle="--")
    _save(fig, out_dir, "gap_hist.png")


def plot_raw_gap_hist(ok: pd.DataFrame, out_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(ok["raw_gap_pyvrp_minus_milp"].dropna(), bins=30, color="darkorange", alpha=0.85, edgecolor="white")
    ax.axvline(0, color="black", linestyle="--", linewidth=1.2, label="PyVRP = MILP")
    ax.set_title("Signed gap distribution (PyVRP − MILP) / MILP")
    ax.set_xlabel("Signed gap")
    ax.set_ylabel("Rows")
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.legend()
    ax.grid(alpha=0.25, linestyle="--")
    _save(fig, out_dir, "raw_gap_hist.png")


def plot_pyvrp_vs_milp(ok: pd.DataFrame, out_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 7))
    colors = ok["raw_gap_pyvrp_minus_milp"].map(lambda g: "crimson" if g < 0 else "steelblue")
    ax.scatter(ok["milp_ub"], ok["pyvrp_total_cost"], c=colors, alpha=0.65, s=28)
    mn = min(ok["milp_ub"].min(), ok["pyvrp_total_cost"].min())
    mx = max(ok["milp_ub"].max(), ok["pyvrp_total_cost"].max())
    ax.plot([mn, mx], [mn, mx], color="black", linestyle="--", linewidth=1, label="equal cost")
    ax.set_title("PyVRP total cost vs MILP UB")
    ax.set_xlabel("MILP UB")
    ax.set_ylabel("PyVRP total cost")
    ax.legend()
    ax.grid(alpha=0.25, linestyle="--")
    _save(fig, out_dir, "pyvrp_vs_milp_scatter.png")


def plot_gap_by_fa(ok: pd.DataFrame, out_dir: Path) -> None:
    data = [grp["abs_gap_pyvrp_vs_milp"].dropna().values for _, grp in ok.groupby("F_A")]
    labels = [str(k) for k in sorted(ok["F_A"].dropna().unique())]
    if not data:
        return
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.boxplot(data, tick_labels=labels, showmeans=True)
    ax.set_title("Absolute gap by F_A")
    ax.set_xlabel("F_A")
    ax.set_ylabel("Absolute gap")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.grid(axis="y", alpha=0.25, linestyle="--")
    _save(fig, out_dir, "gap_by_fa.png")


def plot_gap_by_r(ok: pd.DataFrame, out_dir: Path) -> None:
    grouped = ok.groupby("R")["abs_gap_pyvrp_vs_milp"].mean().sort_index()
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(grouped.index, grouped.values, marker="o", color="steelblue")
    ax.set_title("Mean absolute gap by R")
    ax.set_xlabel("R")
    ax.set_ylabel("Mean absolute gap")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.grid(alpha=0.25, linestyle="--")
    _save(fig, out_dir, "gap_by_r.png")


def plot_cost_breakdown_mean(ok: pd.DataFrame, out_dir: Path) -> None:
    labels = ["Routing", "DA", "Vehicles", "Depots"]
    py = [
        ok["pyvrp_routing_cost"].mean(),
        ok["pyvrp_da_cost"].mean(),
        ok["pyvrp_vehicle_cost"].mean(),
        ok["pyvrp_depot_cost_from_excel"].mean(),
    ]
    milp = [
        ok["milp_cost_routing"].mean(),
        ok["milp_cost_da"].mean(),
        ok["milp_cost_vehicles"].mean(),
        ok["milp_cost_depots"].mean(),
    ]
    x = range(len(labels))
    width = 0.36
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar([i - width / 2 for i in x], py, width, label="PyVRP", color="steelblue", alpha=0.85)
    ax.bar([i + width / 2 for i in x], milp, width, label="MILP", color="darkorange", alpha=0.85)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylabel("Mean cost")
    ax.set_title("Mean cost breakdown: PyVRP vs MILP")
    ax.legend()
    ax.grid(axis="y", alpha=0.25, linestyle="--")
    _save(fig, out_dir, "cost_breakdown_mean.png")


def _scatter_cost(ok: pd.DataFrame, xcol: str, ycol: str, title: str, out_dir: Path, name: str) -> None:
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.scatter(ok[xcol], ok[ycol], alpha=0.55, s=24, color="steelblue")
    mn = min(ok[xcol].min(), ok[ycol].min())
    mx = max(ok[xcol].max(), ok[ycol].max())
    ax.plot([mn, mx], [mn, mx], color="black", linestyle="--", linewidth=1)
    ax.set_title(title)
    ax.set_xlabel(xcol)
    ax.set_ylabel(ycol)
    ax.grid(alpha=0.25, linestyle="--")
    _save(fig, out_dir, name)


def plot_cost_scatters(ok: pd.DataFrame, out_dir: Path) -> None:
    _scatter_cost(ok, "milp_cost_routing", "pyvrp_routing_cost", "Routing cost: PyVRP vs MILP", out_dir, "routing_cost_pyvrp_vs_milp.png")
    _scatter_cost(ok, "milp_cost_da", "pyvrp_da_cost", "DA cost: PyVRP vs MILP", out_dir, "da_cost_pyvrp_vs_milp.png")


def plot_capacity_usage(ok: pd.DataFrame, out_dir: Path) -> None:
    usage_cols = [c for c in ok.columns if c.endswith("_pyvrp_usage_total")]
    if not usage_cols:
        return
    long = ok[usage_cols].melt(var_name="depot", value_name="usage").dropna()
    long["depot"] = long["depot"].str.extract(r"d(\d+)_pyvrp_usage_total")[0]
    data = [grp["usage"].values for _, grp in long.groupby("depot")]
    labels = [f"D{k}" for k in sorted(long["depot"].dropna().unique(), key=lambda x: int(x))]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.boxplot(data, tick_labels=labels, showmeans=True)
    ax.axhline(1.0, color="red", linestyle="--", linewidth=1.2, label="100% capacity")
    ax.set_title("PyVRP depot capacity utilization")
    ax.set_xlabel("Depot id")
    ax.set_ylabel("Usage")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.legend()
    ax.grid(axis="y", alpha=0.25, linestyle="--")
    _save(fig, out_dir, "capacity_usage_boxplot.png")


def plot_runtime(ok: pd.DataFrame, out_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(ok["runtime_seconds"].dropna(), bins=30, color="slategray", alpha=0.85, edgecolor="white")
    ax.set_title("Runtime distribution")
    ax.set_xlabel("Seconds per row")
    ax.set_ylabel("Rows")
    ax.grid(alpha=0.25, linestyle="--")
    _save(fig, out_dir, "runtime_hist.png")


def main() -> None:
    args = parse_args()
    csv_path = Path(args.csv)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    _, results, ok = _load(csv_path)
    print(f"RESULT rows: {len(results)}")
    print(f"OK rows    : {len(ok)}")
    print(f"Out dir    : {out_dir}")

    plot_status_counts(results, out_dir)
    if ok.empty:
        print("No OK rows to plot.")
        return

    plot_gap_hist(ok, out_dir, args.gap_threshold)
    plot_raw_gap_hist(ok, out_dir)
    plot_pyvrp_vs_milp(ok, out_dir)
    plot_gap_by_fa(ok, out_dir)
    plot_gap_by_r(ok, out_dir)
    plot_cost_breakdown_mean(ok, out_dir)
    plot_cost_scatters(ok, out_dir)
    plot_capacity_usage(ok, out_dir)
    plot_runtime(ok, out_dir)


if __name__ == "__main__":
    main()
