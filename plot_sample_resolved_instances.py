from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from da_geometry import assign_da_clients, build_direct_allocation_data
from dat_loader import load_dat
from instance_adapter import adapt_instance, spec_from_row
from instance_resolver import resolve_instance_path
from pyvrp_model import build_full_model, solve_fast
from xlsx_loader import load_lorp_fsd_mapping

CSV = Path("pipeline_out/fsd_batch_results_with_stats.csv")
OUT = Path("pipeline_out/sample_instance_plots")
OUT.mkdir(parents=True, exist_ok=True)


def select_samples(df: pd.DataFrame) -> list[tuple[str, int]]:
    res = df[(df.record_type == "RESULT") & (df.run_status == "OK")].copy()
    samples: list[tuple[str, int]] = []

    def pick(label: str, mask):
        cand = res[mask].sort_values("row_id")
        if len(cand):
            samples.append((label, int(cand.iloc[0].row_id)))

    pick("capacity_violation", res.capacity_violation == True)
    pick("pyvrp_below_milp", (res.raw_gap_pyvrp_minus_milp < 0) & (res.capacity_violation != True))
    pick("too_far_gap", (res.abs_gap_pyvrp_vs_milp > 0.20) & (res.raw_gap_pyvrp_minus_milp > 0) & (res.capacity_violation != True))
    pick("ok_range", (res.abs_gap_pyvrp_vs_milp <= 0.20) & (res.raw_gap_pyvrp_minus_milp > 0) & (res.capacity_violation != True))
    pick("high_da_fa_positive", (res.F_A > 0) & (res.pyvrp_da_clients > 0) & (res.capacity_violation != True))

    # de-duplicate row ids while preserving labels
    out = []
    seen = set()
    for label, rid in samples:
        if rid not in seen:
            out.append((label, rid))
            seen.add(rid)
    return out[:5]


def plot_row(label: str, row_id: int) -> None:
    mapping = load_lorp_fsd_mapping("results_MILP.xlsx", instance_folder=None)
    row = mapping[mapping.row_id == row_id].iloc[0]
    config = spec_from_row(row)
    resolution = resolve_instance_path(config.instance, "instances")
    base = load_dat(resolution.path)
    inst = adapt_instance(base, config)
    da_data, _ = build_direct_allocation_data(inst, inst.data["R"])
    da_assigned, routing_set = assign_da_clients(inst, da_data, int(inst.data["veh_cap"]))
    model, info = build_full_model(inst)
    res = solve_fast(model, runtime=1, n_runs=1)
    sol = res.best
    vt_list = info["vehicle_types"]
    locs = info.get("locations")

    assigned_da_clients = {j for cs in da_assigned.values() for j in cs}

    fig, axes = plt.subplots(1, 3, figsize=(21, 6.5))
    ax0, ax1, ax2 = axes

    # panel 1: assignment
    for j, c in inst.clients.items():
        if j in assigned_da_clients:
            color = "seagreen"
        elif j in routing_set:
            color = "steelblue"
        else:
            color = "lightgray"
        ax0.scatter(c["x"], c["y"], color=color, s=45, alpha=0.85)
        ax0.annotate(str(j), (c["x"], c["y"]), fontsize=6, ha="center", va="bottom")
    for did, d in inst.depots.items():
        ax0.scatter(d["x"], d["y"], marker="*", s=260, color="crimson", edgecolor="black", zorder=5)
        ax0.annotate(f"D{did}", (d["x"], d["y"]), color="crimson", weight="bold", ha="center", va="top")
        ax0.add_patch(plt.Circle((d["x"], d["y"]), float(inst.data["R"]), edgecolor="crimson", facecolor="none", linestyle="--", alpha=0.25))
    ax0.set_title(f"Assignment\nDA={len(assigned_da_clients)} Routing={len(routing_set)}")

    # panel 2/3: routes by profile
    for ax, profile, cmap in [(ax1, "routing", plt.cm.Blues), (ax2, "direct_allocation", plt.cm.Greens)]:
        for _, c in inst.clients.items():
            ax.scatter(c["x"], c["y"], color="lightgray", s=22, alpha=0.6)
        for did, dnode in info["depot_nodes"].items():
            ax.scatter(dnode.x, dnode.y, marker="*", s=260, color="crimson", edgecolor="black", zorder=5)
            ax.annotate(f"D{did}", (dnode.x, dnode.y), color="crimson", weight="bold", ha="center", va="top")
        routes = [r for r in sol.routes() if vt_list[r.vehicle_type()]["type"] == profile]
        for idx, route in enumerate(routes):
            col = cmap(0.3 + 0.6 * idx / max(1, len(routes) - 1))
            for trip in route.trips():
                if locs is None:
                    continue
                seq = [trip.start_depot(), *trip.visits(), trip.end_depot()]
                xs = [locs[i].x for i in seq]
                ys = [locs[i].y for i in seq]
                ax.plot(xs, ys, "-o", color=col, linewidth=1.3, markersize=3, alpha=0.9)
        ax.set_title(f"{profile}\nroutes={len(routes)} dist={sum(r.distance() for r in routes):.1f}")

    for ax in axes:
        ax.set_aspect("equal", "box")
        ax.grid(alpha=0.25, linestyle="--")
        ax.set_xlabel("X")
        ax.set_ylabel("Y")

    # capacity summary
    cap_lines = []
    for did, d in inst.depots.items():
        da = sum(inst.clients[j]["demand"] for j in da_assigned.get(did, []))
        cap_lines.append(f"D{did}: cap={d['cap']:.0f} DApre={da:.0f}")
    fig.suptitle(
        f"{label} | row={row_id} | {config.instance} | R={config.R} F_A={config.F_A} | "
        + " | ".join(cap_lines),
        fontsize=11,
        weight="bold",
    )
    fig.tight_layout()
    out = OUT / f"sample_{label}_row{row_id}.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {out}")


def main() -> None:
    df = pd.read_csv(CSV)
    samples = select_samples(df)
    print("samples:", samples)
    for label, row_id in samples:
        plot_row(label, row_id)


if __name__ == "__main__":
    main()
