"""Visualization utilities — matplotlib lazy-imported, safe in headless envs."""
from __future__ import annotations

from dat_loader import Instance


def plot_instance(inst: Instance, da_data: dict | None = None) -> None:
    import matplotlib.pyplot as plt

    radius = float(inst.data["R"])
    fig, ax = plt.subplots(figsize=(8, 8))

    clientes_da: set = set()
    if da_data is not None:
        for perfil in da_data.values():
            clientes_da.update(perfil["clients"])

    first_da = True
    first_no_da = True
    for j, c in inst.clients.items():
        if j in clientes_da:
            ax.scatter(c["x"], c["y"], s=40, color="green", alpha=0.9,
                       label="Cliente dentro de radio" if first_da else "")
            first_da = False
        else:
            ax.scatter(c["x"], c["y"], s=40, color="dodgerblue", alpha=0.9,
                       label="Cliente fuera de radio" if first_no_da else "")
            first_no_da = False

    first_depot = True
    for _, d in inst.depots.items():
        ax.scatter(d["x"], d["y"], s=220, color="crimson", marker="*", edgecolor="black",
                   label="Depósito activo" if first_depot else "")
        first_depot = False
        ax.add_patch(plt.Circle((d["x"], d["y"]), radius,
                                edgecolor="gray", facecolor="none", linestyle="--", alpha=0.4))

    ax.set_title("Instancia modificada y cobertura por radio")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_aspect("equal", adjustable="box")
    ax.grid(linestyle="--", alpha=0.3)
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(dict(zip(labels, handles)).values(), dict(zip(labels, handles)).keys(), loc="upper left")
    plt.show()


def plot_solution(inst: Instance, res, info: dict) -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 7))
    for i, dnode in info["depot_nodes"].items():
        ax.scatter(dnode.x, dnode.y, marker="*", s=280, color="red",
                   label="Depot" if i == next(iter(info["depot_nodes"])) else "", zorder=4)

    clients = info["client_nodes"]
    ax.scatter([c.x for c in clients.values()], [c.y for c in clients.values()],
               s=40, color="gray", alpha=0.7, label="Clientes", zorder=2)

    for _, dnode in info["depot_nodes"].items():
        ax.add_patch(plt.Circle((dnode.x, dnode.y), float(inst.data["R"]),
                                edgecolor="grey", facecolor="none", linestyle="--", alpha=0.4, zorder=1))

    routes_by_kind: dict = {"routing": [], "direct_allocation": []}
    for route in res.best.routes():
        vt_idx = route.vehicle_type()
        kind = info["vehicle_types"][vt_idx]["type"]
        routes_by_kind[kind].append(route)

    cmap_kind = {"routing": plt.cm.Blues, "direct_allocation": plt.cm.Greens}
    linestyle_kind = {"routing": "-", "direct_allocation": "--"}
    marker_kind = {"routing": "o", "direct_allocation": "s"}
    width_kind = {"routing": 1.5, "direct_allocation": 2.2}
    labels_used: set = set()
    locs = info.get("locations")

    for kind, routes_k in routes_by_kind.items():
        if not routes_k:
            continue
        cmap = cmap_kind[kind]
        for r_idx, route in enumerate(routes_k):
            col = cmap(0.3 + 0.6 * (r_idx / max(1, len(routes_k) - 1)))
            for trip in route.trips():
                if locs is None:
                    continue
                seq = [trip.start_depot(), *trip.visits(), trip.end_depot()]
                xs = [locs[idx].x for idx in seq]
                ys = [locs[idx].y for idx in seq]
                label = "" if kind in labels_used else kind.replace("_", " ").title()
                labels_used.add(kind)
                ax.plot(xs, ys, linestyle=linestyle_kind[kind], marker=marker_kind[kind],
                        color=col, linewidth=width_kind[kind], markersize=3, alpha=0.9,
                        label=label, zorder=3)

    handles, labels = ax.get_legend_handles_labels()
    ax.legend(dict(zip(labels, handles)).values(), dict(zip(labels, handles)).keys(), loc="upper left")
    ax.set_aspect("equal", "box")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_title("MDVRP + Direct Allocation")
    ax.grid(alpha=0.3)
    plt.show()


__all__ = ["plot_instance", "plot_solution"]
