"""Per-iteration solution plot (Phase 5).

Simple, robust debugging plot (Agg backend, no display): depots, clients, routing
routes, DA assignments, overloaded depots highlighted, clients removed in the
previous repair step, and the count of accumulated forbidden routing assignments.
Not meant to be pretty — meant to be useful.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Set, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


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
) -> Path:
    removed_clients = removed_clients or set()
    overloaded = set(capacity.overloaded_depots)

    fig, ax = plt.subplots(figsize=(8, 8))

    # clients
    for cid, c in instance.clients.items():
        ax.scatter(c.x, c.y, c="0.6", s=18, zorder=2)
    # mark clients removed from routing in the previous repair step
    for cid in removed_clients:
        if cid in instance.clients:
            c = instance.clients[cid]
            ax.scatter(c.x, c.y, marker="x", c="red", s=90, linewidths=2, zorder=5)

    # active depots (overloaded highlighted)
    for did in facility_design.active_depot_ids:
        d = instance.depots[did]
        ax.scatter(d.x, d.y, marker="s", s=130,
                   c=("red" if did in overloaded else "tab:blue"),
                   edgecolors="black", zorder=4)
        ax.annotate(f"d{did}", (d.x, d.y), textcoords="offset points", xytext=(6, 6), fontsize=9)
        if did in overloaded:
            ax.scatter(d.x, d.y, marker="o", s=420, facecolors="none",
                       edgecolors="red", linewidths=2, zorder=3)

    # routing routes (solid)
    for r in parsed.routes:
        d = instance.depots[r.depot_id]
        xs = [d.x] + [instance.clients[c].x for c in r.client_sequence] + [d.x]
        ys = [d.y] + [instance.clients[c].y for c in r.client_sequence] + [d.y]
        ax.plot(xs, ys, "-", lw=1.3, c="tab:green", zorder=3)

    # DA assignments (dashed, thin)
    for a in parsed.da_assignments:
        d = instance.depots[a.depot_id]
        c = instance.clients[a.client_id]
        ax.plot([d.x, c.x], [d.y, c.y], "--", lw=0.6, c="tab:orange", alpha=0.7, zorder=1)

    status = "FEASIBLE" if fully_feasible else "relaxed/infeasible"
    ax.set_title(
        f"{instance.name} — iter {iteration} — {status}\n"
        f"routing={len(parsed.routes)} DA={len(parsed.da_assignments)} "
        f"forbidden={len(forbidden)} overloaded={sorted(overloaded)}",
        fontsize=10,
    )
    ax.set_aspect("equal", adjustable="datalim")
    ax.grid(True, ls=":", alpha=0.4)

    out = Path(path)
    fig.savefig(out, dpi=110, bbox_inches="tight")
    plt.close(fig)
    return out


__all__ = ["plot_iteration"]
