"""Per-iteration solution plots (Phase 5+).

Headless matplotlib helpers for row debugging. Generates a route-free instance
state plot and a combined solution plot with routing + DA on one axes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Set, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402


_LABEL_CLIENT_LIMIT = 80


def _row_label(row_index) -> str:
    return "?" if row_index is None else str(row_index)


def _metric_text(metric) -> str:
    if metric is None:
        return "metric=n/a"
    label = getattr(metric, "label", "metric")
    value = getattr(metric, "value", None)
    if value is None:
        return f"{label}=n/a"
    return f"{label}={value:.6g}"


def _subtitle_parts(*, parsed, config, cost=None, metric=None, overloaded=None, forbidden_count: int = 0) -> list[str]:
    overloaded = sorted(overloaded or [])
    z_pyvrp = getattr(cost, "total", None) if cost is not None else None
    ub_milp = getattr(config, "UB", None)
    parts = [
        f"Z={z_pyvrp:.4f}" if z_pyvrp is not None else "Z=n/a",
        f"UB={ub_milp:.4f}" if ub_milp is not None else "UB=n/a",
        _metric_text(metric),
        f"routing={len(parsed.routes)}",
        f"DA={len(parsed.da_assignments)}",
    ]
    if overloaded:
        parts.append(f"overloaded={overloaded}")
    if forbidden_count > 0:
        parts.append(f"forbidden={forbidden_count}")
    return parts


def _draw_clients(ax, instance, *, label_clients: bool = True) -> None:
    do_labels = label_clients and len(instance.clients) <= _LABEL_CLIENT_LIMIT
    xs = [c.x for c in instance.clients.values()]
    ys = [c.y for c in instance.clients.values()]
    ax.scatter(xs, ys, c="lightgray", s=28, alpha=0.72, edgecolors="none", zorder=2)
    if do_labels:
        for cid, c in instance.clients.items():
            ax.annotate(
                str(cid), (c.x, c.y), fontsize=5, color="dimgray", ha="center", va="bottom",
                xytext=(0, 3), textcoords="offset points",
            )


def _draw_depots(ax, instance, facility_design, *, config=None, overloaded=None, show_radius: bool = True) -> None:
    overloaded = set(overloaded or [])
    active = set(facility_design.active_depot_ids)

    for did, depot in instance.depots.items():
        if did in active:
            color = "red" if did in overloaded else "crimson"
            ax.scatter(
                depot.x, depot.y, marker="*", s=360, c=color, edgecolors="black",
                linewidths=0.8, zorder=6,
            )
            ax.annotate(
                f"D{did}", (depot.x, depot.y), fontsize=9, fontweight="bold", color="crimson",
                ha="center", va="top", xytext=(0, -12), textcoords="offset points",
            )
            if show_radius and config is not None:
                ax.add_patch(plt.Circle(
                    (depot.x, depot.y), float(config.R), edgecolor="crimson", facecolor="none",
                    linestyle="--", alpha=0.18, linewidth=1.0, zorder=1,
                ))
            if did in overloaded:
                ax.scatter(
                    depot.x, depot.y, marker="o", s=540, facecolors="none",
                    edgecolors="red", linewidths=2, zorder=5,
                )
        else:
            ax.scatter(
                depot.x, depot.y, marker="^", s=90, c="white", edgecolors="0.45",
                linewidths=1.0, alpha=0.8, zorder=4,
            )
            ax.annotate(f"d{did}", (depot.x, depot.y), fontsize=7, color="0.35", ha="center", va="top", xytext=(0, -9), textcoords="offset points")


def _finish_axes(ax) -> None:
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.grid(alpha=0.25, linestyle="--")


def plot_instance_state(
    path,
    *,
    instance,
    facility_design,
    config,
    iteration: int,
    row_index=None,
) -> Path:
    """Plot base instance state: clients, depots, open depots, DA radii; no routes."""
    fig, ax = plt.subplots(figsize=(9, 8))
    _draw_clients(ax, instance)
    _draw_depots(ax, instance, facility_design, config=config, show_radius=True)

    active = list(facility_design.active_depot_ids)
    ax.set_title(
        f"Row {_row_label(row_index)} — {instance.name} — instance state — iteration {iteration:02d}\n"
        f"clients={instance.n_clients} | depots={instance.n_depots} | R={config.R} | Length={config.Length} | active={active}",
        fontsize=11,
        fontweight="bold",
    )
    handles = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor="lightgray", markeredgecolor="lightgray", markersize=6, label="clients"),
        Line2D([0], [0], marker="^", color="0.45", markerfacecolor="white", linestyle="none", markersize=7, label="closed depots"),
        Line2D([0], [0], marker="*", color="crimson", markeredgecolor="black", linestyle="none", markersize=13, label="open depots"),
        Line2D([0], [0], color="crimson", lw=1.0, linestyle="--", label=f"DA radius R={config.R}"),
    ]
    ax.legend(handles=handles, loc="upper left", fontsize=8, framealpha=0.9)
    _finish_axes(ax)

    out = Path(path)
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def plot_iteration(
    path,
    *,
    instance,
    facility_design,
    parsed,
    capacity,
    config,
    iteration: int,
    forbidden: Set[Tuple[int, int]],
    removed_clients: Optional[Set[int]] = None,
    fully_feasible: bool = False,
    row_index=None,
    status: Optional[str] = None,
    cost=None,
    metric=None,
) -> Path:
    """Plot combined routing + DA solution for one iteration."""
    removed_clients = removed_clients or set()
    overloaded = set(capacity.overloaded_depots)
    status_label = status or ("FEASIBLE" if fully_feasible else "RELAXED_INFEASIBLE")

    fig, ax = plt.subplots(figsize=(10, 9))
    _draw_clients(ax, instance)
    _draw_depots(ax, instance, facility_design, config=config, overloaded=overloaded, show_radius=True)

    # routing routes: solid blue-green paths
    n_routes = max(len(parsed.routes), 1)
    for r_idx, route in enumerate(parsed.routes):
        depot = instance.depots[route.depot_id]
        xs = [depot.x] + [instance.clients[c].x for c in route.client_sequence] + [depot.x]
        ys = [depot.y] + [instance.clients[c].y for c in route.client_sequence] + [depot.y]
        color = plt.cm.Blues(0.35 + 0.55 * (r_idx / max(1, n_routes - 1)))
        ax.plot(xs, ys, "-o", lw=1.7, ms=4, c=color, alpha=0.9, zorder=3)
        for cid in route.client_sequence:
            client = instance.clients[cid]
            ax.scatter(client.x, client.y, s=62, c=[color], edgecolors="black", linewidths=0.5, zorder=4)

    # DA assignments: dashed light green lines
    n_da = max(len(parsed.da_assignments), 1)
    for a_idx, assignment in enumerate(parsed.da_assignments):
        depot = instance.depots[assignment.depot_id]
        client = instance.clients[assignment.client_id]
        color = plt.cm.Greens(0.35 + 0.50 * (a_idx / max(1, n_da - 1)))
        ax.plot([depot.x, client.x], [depot.y, client.y], "--", lw=0.8, c=color, alpha=0.55, zorder=2)
        ax.scatter(client.x, client.y, marker="s", s=45, c=[color], edgecolors="black", linewidths=0.35, zorder=4)

    # previous repair removals only if present
    for cid in removed_clients:
        if cid in instance.clients:
            client = instance.clients[cid]
            ax.scatter(client.x, client.y, marker="x", c="red", s=100, linewidths=2.2, zorder=7)

    title = f"Row {_row_label(row_index)} — {instance.name} — iteration {iteration:02d} — {status_label}"
    subtitle = " | ".join(_subtitle_parts(
        parsed=parsed,
        config=config,
        cost=cost,
        metric=metric,
        overloaded=overloaded,
        forbidden_count=len(forbidden),
    ))
    ax.set_title(f"{title}\n{subtitle}", fontsize=11, fontweight="bold")

    handles = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor="lightgray", markeredgecolor="lightgray", markersize=6, label="clients"),
        Line2D([0], [0], marker="^", color="0.45", markerfacecolor="white", linestyle="none", markersize=7, label="closed depots"),
        Line2D([0], [0], marker="*", color="crimson", markeredgecolor="black", linestyle="none", markersize=13, label="open depots"),
        Line2D([0], [0], color=plt.cm.Blues(0.65), lw=1.8, marker="o", markersize=4, label="routing routes"),
        Line2D([0], [0], color=plt.cm.Greens(0.65), lw=1.2, linestyle="--", marker="s", markersize=4, label="DA assignments"),
        Line2D([0], [0], color="crimson", lw=1.0, linestyle="--", label=f"DA radius R={config.R}"),
    ]
    if overloaded:
        handles.append(Line2D([0], [0], marker="o", color="red", linestyle="none", markerfacecolor="none", markersize=12, label="overloaded depots"))
    if removed_clients:
        handles.append(Line2D([0], [0], marker="x", color="red", linestyle="none", markersize=8, label="prev repair removals"))
    ax.legend(handles=handles, loc="upper left", fontsize=8, framealpha=0.92, ncol=1)
    _finish_axes(ax)

    out = Path(path)
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


__all__ = ["plot_instance_state", "plot_iteration"]
