"""End-to-end pipeline runner with intermediate step output.

Usage:
    uv run python run_pipeline.py
"""
from __future__ import annotations

import math
from pathlib import Path
from pprint import pformat

import matplotlib
matplotlib.use("Agg")  # headless — saves to files
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from dat_loader import load_dat
from instance_adapter import adapt_instance, spec_from_row
from xlsx_loader import load_lorp_fsd_mapping
from da_geometry import (
    assign_da_clients,
    build_direct_allocation_data,
    compute_max_distance,
    dist_euclid,
)
from pyvrp_model import build_full_model, solve_fast
from reporting import (
    build_full_report,
    compute_solution_costs,
    extract_kpis_level1,
    extract_kpis_level2,
)

OUT = Path("pipeline_out")
OUT.mkdir(exist_ok=True)

SEP = "=" * 60

# ─────────────────────────────────────────────────────────────
# STEP 0 — pick row
# ─────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("STEP 0 — load experiment mapping")
print(SEP)

df = load_lorp_fsd_mapping("results_MILP.xlsx", instance_folder="instances")

# row 8: r40x5b-2.dat, R=30, F_R=1.0, F_A=0.5
row = df[df["row_id"] == 8].iloc[0]
config = spec_from_row(row)

print(f"  row_id       : {config.row_id}")
print(f"  instance     : {config.instance}")
print(f"  active depots: {list(config.depots.keys())}")
print(f"  R            : {config.R}")
print(f"  F_R          : {config.F_R}   (routing cost weight)")
print(f"  F_A          : {config.F_A}   (DA cost weight)")
print(f"  Length       : {config.Length}")
print(f"  UB  (MILP)   : {config.UB:.4f}")
print(f"  status       : {config.status}")
print(f"  gap (MILP)   : {config.gap:.4%}")
print(f"\n  Depot specs from Excel:")
for did, dinfo in config.depots.items():
    print(f"    depot {did}: capacity={dinfo['capacity']}")
print(f"\n  MILP per-depot breakdown:")
for did, dm in config.depots_milp.items():
    print(f"    depot {did}: demand={dm['demand']:.1f}  usage={dm['usage']:.1%}  vehicles={dm['vehicles']:.0f}")

# ─────────────────────────────────────────────────────────────
# STEP 1 — load + adapt instance
# ─────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("STEP 1 — load base instance + adapt")
print(SEP)

base_inst = load_dat(f"instances/{config.instance}")
print(f"  Base instance:")
print(f"    n_clients      : {base_inst.data['n_clients']}")
print(f"    n_depots       : {base_inst.data['n_depots']}")
print(f"    max_depots_open: {base_inst.data['max_depots_open']}")
print(f"    veh_cap        : {base_inst.data['veh_cap']}")
print(f"    veh_fixed_cost : {base_inst.data['veh_fixed_cost']}")
print(f"    depots in base :")
for did, d in base_inst.depots.items():
    print(f"      [{did}] x={d['x']:.1f}  y={d['y']:.1f}  cap={d['cap']}  fixed_cost={d['fixed_cost']}")

inst = adapt_instance(base_inst, config)
print(f"\n  Adapted instance (active depots only, Excel caps, R/F_R/F_A injected):")
print(f"    n_depots       : {inst.data['n_depots']}")
print(f"    R injected     : {inst.data['R']}")
print(f"    F_R injected   : {inst.data['F_R']}")
print(f"    F_A injected   : {inst.data['F_A']}")
print(f"    depots after adapt:")
for did, d in inst.depots.items():
    print(f"      [{did}] x={d['x']:.1f}  y={d['y']:.1f}  cap={d['cap']}  fixed_cost={d['fixed_cost']}")

total_demand = sum(c["demand"] for c in inst.clients.values())
print(f"\n  Clients: {len(inst.clients)}  |  total demand: {total_demand}")

# ─────────────────────────────────────────────────────────────
# STEP 2 — geometry
# ─────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("STEP 2 — DA geometry")
print(SEP)

radius = inst.data["R"]
da_data, max_per_depot = build_direct_allocation_data(inst, radius)
max_dist = compute_max_distance(inst)
scale = 100.0 / max_dist if max_dist > 0 else 1.0

print(f"  radius (R)             : {radius}")
print(f"  max inter-node dist    : {max_dist:.4f}")
print(f"  scale factor           : {scale:.8f}  (= 100 / max_dist; Arslan scaling)")
print(f"  depots with DA clients : {list(da_data.keys())}")
print(f"  max clients/depot (DA) : {max_per_depot}")
print(f"\n  Per-depot DA coverage:")
for did, perfil in da_data.items():
    d = inst.depots[did]
    print(f"    depot {did} @ ({d['x']:.1f},{d['y']:.1f}): {len(perfil['clients'])} clients within R={radius}")
    nearest = min(perfil["cost_ij"].values())
    farthest = max(perfil["cost_ij"].values())
    print(f"      dist range: [{nearest:.2f}, {farthest:.2f}]")

# ─────────────────────────────────────────────────────────────
# STEP 3 — DA client assignment
# ─────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("STEP 3 — DA client assignment heuristic")
print(SEP)

veh_cap = int(inst.data["veh_cap"])
da_assigned, routing_set = assign_da_clients(inst, da_data, veh_cap)

n_da = sum(len(cs) for cs in da_assigned.values())
n_routing = len(routing_set)
print(f"  veh_cap                : {veh_cap}")
print(f"  clients via DA         : {n_da}  ({n_da/len(inst.clients):.1%})")
print(f"  clients via routing    : {n_routing}  ({n_routing/len(inst.clients):.1%})")
print(f"\n  DA assignment per depot:")
for did, clients in da_assigned.items():
    d = inst.depots[did]
    da_cap = d["cap"]
    demand_da = sum(inst.clients[j]["demand"] for j in clients)
    print(f"    depot {did}: {len(clients)} clients  "
          f"demand_DA={demand_da:.0f}  cap_real={da_cap:.0f}  "
          f"DA_utilization={demand_da/da_cap:.1%}")

print(f"\n  Routing client IDs: {sorted(routing_set)[:20]}{'...' if len(routing_set) > 20 else ''}")

# ─────────────────────────────────────────────────────────────
# PLOT 1 — instance + DA coverage
# ─────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("PLOT 1 — instance geometry")
print(SEP)

fig, ax = plt.subplots(figsize=(9, 8))
clients_in_da = {j for cs in da_assigned.values() for j in cs}

for j, c in inst.clients.items():
    if j in clients_in_da:
        ax.scatter(c["x"], c["y"], s=50, color="seagreen", alpha=0.85, zorder=3)
    else:
        ax.scatter(c["x"], c["y"], s=50, color="steelblue", alpha=0.85, zorder=3)
    ax.annotate(str(j), (c["x"], c["y"]), fontsize=6, ha="center", va="bottom",
                xytext=(0, 4), textcoords="offset points", color="dimgray")

for did, d in inst.depots.items():
    ax.scatter(d["x"], d["y"], s=350, color="crimson", marker="*",
               edgecolor="black", linewidth=0.8, zorder=5)
    ax.annotate(f"D{did}", (d["x"], d["y"]), fontsize=9, fontweight="bold",
                color="crimson", ha="center", va="top",
                xytext=(0, -12), textcoords="offset points")
    circle = plt.Circle((d["x"], d["y"]), radius, edgecolor="crimson",
                         facecolor="none", linestyle="--", alpha=0.3, linewidth=1.2)
    ax.add_patch(circle)

handles = [
    mpatches.Patch(color="seagreen", label=f"Client → DA ({n_da})"),
    mpatches.Patch(color="steelblue", label=f"Client → routing ({n_routing})"),
    mpatches.Patch(color="crimson", label=f"Depot (active, n={len(inst.depots)})"),
    mpatches.Patch(color="crimson", alpha=0.3, linestyle="--", label=f"DA radius R={radius}"),
]
ax.legend(handles=handles, loc="upper left", fontsize=9)
ax.set_aspect("equal", "box")
ax.set_title(f"Instance: {config.instance}  |  R={radius}  F_R={config.F_R}  F_A={config.F_A}", fontsize=11)
ax.set_xlabel("X")
ax.set_ylabel("Y")
ax.grid(alpha=0.25, linestyle="--")

path1 = OUT / "plot1_instance.png"
fig.savefig(path1, dpi=150, bbox_inches="tight")
plt.close(fig)
print(f"  saved → {path1}")

# ─────────────────────────────────────────────────────────────
# STEP 4 — build PyVRP model
# ─────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("STEP 4 — build PyVRP model")
print(SEP)

model, info = build_full_model(inst)

vt_list = info["vehicle_types"]
print(f"  max graph arc distance : {info['max_distance']:.6f}")
print(f"  solver scale           : {info['escala']:.6f}  (= 100/max_dist; Arslan)")
print(f"  total vehicle types    : {len(vt_list)}")
routing_vts = [v for v in vt_list if v["type"] == "routing"]
da_vts      = [v for v in vt_list if v["type"] == "direct_allocation"]
print(f"    routing types        : {len(routing_vts)}")
print(f"    DA types             : {len(da_vts)}")
print(f"\n  Vehicle type breakdown:")
for idx, vt in enumerate(vt_list):
    if vt["type"] == "direct_allocation":
        extra = f"client={vt['client']}"
    else:
        cap_note = f"  residual_cap={vt['residual_capacity']}" if "residual_capacity" in vt else ""
        extra = f"num_available={vt['num_available']}{cap_note}"
    print(f"    [{idx:>2}] {vt['type']:<20} depot={vt['depot']}  {extra}")

print(f"\n  routing clients  : {len(info['clientes_routing'])}")
print(f"  DA clients       : {sum(len(cs) for cs in info['da_asignados'].values())}")

# ─────────────────────────────────────────────────────────────
# STEP 5 — solve
# ─────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("STEP 5 — solve (3 seeds × 5s each)")
print(SEP)

res = solve_fast(model, runtime=5, n_runs=3)

sol = res.best
print(f"  objective (scaled dist): {sol.distance():.2f}")
print(f"  feasible               : {sol.is_feasible()}")
print(f"  n_routes               : {len(sol.routes())}")

print(f"\n  Route breakdown:")
for route in sol.routes():
    vt_idx = route.vehicle_type()
    vt = vt_list[vt_idx]
    trips = list(route.trips())
    n_clients = sum(len(t.visits()) for t in trips)
    demand    = sum((t.delivery()[0] if t.delivery() else 0) for t in trips)
    print(f"    depot={vt['depot']}  type={vt['type']:<20} "
          f"trips={len(trips)}  clients={n_clients}  "
          f"demand={demand:.0f}  dist={route.distance():.2f}")

# ─────────────────────────────────────────────────────────────
# STEP 6 — KPIs level 1 (global)
# ─────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("STEP 6 — KPIs level 1 (global by type)")
print(SEP)

kpis1 = extract_kpis_level1(inst, res, info)

print(f"  total_distance (scaled): {kpis1['total_distance']:.2f}")
print(f"  total_demand           : {kpis1['total_demand']:.0f}")
print(f"  served_demand          : {kpis1['served_demand']:.0f}")
print(f"  pending_demand         : {kpis1['pending_demand']:.0f}")
print(f"  service_level          : {kpis1['served_demand']/kpis1['total_demand']:.2%}")
print(f"\n  By type:")
for kind in ("routing", "direct_allocation"):
    k = kpis1[kind]
    print(f"    {kind}:")
    print(f"      n_vehicles : {k['n_vehicles']}")
    print(f"      distance   : {k['distance']:.2f}  (scaled)")
    print(f"      n_clients  : {k['n_clients']}")
    print(f"      demand     : {k['demand']:.0f}")

# ─────────────────────────────────────────────────────────────
# STEP 7 — KPIs level 2 (per depot)
# ─────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("STEP 7 — KPIs level 2 (per depot)")
print(SEP)

kpis2 = extract_kpis_level2(inst, res, info)

for depot_id in sorted(kpis2.keys()):
    cap = inst.depots[depot_id]["cap"]
    print(f"\n  Depot {depot_id}  (cap={cap}):")
    for kind in ("routing", "direct_allocation"):
        k = kpis2[depot_id][kind]
        print(f"    {kind}:")
        print(f"      n_vehicles={k['n_vehicles']}  "
              f"dist={k['distance']:.2f}  "
              f"clients={k['n_clients']}  "
              f"demand={k['demand']:.0f}")

# ─────────────────────────────────────────────────────────────
# STEP 8 — solution costs + gap
# ─────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("STEP 8 — solution costs + gap vs MILP")
print(SEP)

costs = compute_solution_costs(sol, kpis1, config, inst, scale=info["escala"])
print(f"  routing_distance scaled: {costs['routing_distance_scaled']:.8f}")
print(f"  da_distance      scaled: {costs['da_distance_scaled']:.8f}")
print(f"  cost_routing           : {costs['cost_routing']:.4f}  (scaled / scale; F_R already in edges)")
print(f"  cost_da                : {costs['cost_da']:.4f}  (scaled / scale; F_A already in edges)")
print(f"  vehicle_cost           : {costs['vehicle_cost']:.4f}  ({kpis1['routing']['n_vehicles']} veh × {inst.data['veh_fixed_cost']})")
print(f"  depot_cost             : {costs['depot_cost']:.4f}  (from MILP Excel)")
print(f"  ─────────────────────────────────")
print(f"  total_cost  (PyVRP)    : {costs['total_cost']:.4f}")
print(f"  UB          (MILP)     : {config.UB:.4f}")
raw_gap = costs['raw_gap_pyvrp_minus_milp']
abs_gap = costs['gap_abs']
symbol = "PYVRP_BELOW_MILP_CHECK_MODEL" if raw_gap < 0 else "PYVRP_GE_MILP_OK"
far_flag = "TOO_FAR" if abs_gap > 0.20 else "OK_RANGE"
print(f"  raw gap (PyVRP−MILP)/MILP : {raw_gap:.4%}  [{symbol}]")
print(f"  abs gap |PyVRP−MILP|/MILP : {abs_gap:.4%}  [{far_flag}]")

# ─────────────────────────────────────────────────────────────
# STEP 9 — full benchmark report row
# ─────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("STEP 9 — full report row (build_full_report)")
print(SEP)

report = build_full_report(inst, res, config, info)

# print organised sections
print("  Identification:")
for k in ("id", "instancia", "F_R", "F_A", "R", "Length"):
    print(f"    {k:<22}: {report[k]}")

print("\n  Costs (PyVRP vs MILP):")
cost_pairs = [
    ("costo_routing_pyvrp", "costo_routing_milp"),
    ("costo_da_pyvrp",      "costo_da_milp"),
    ("costo_vehiculos_pyvrp","costo_vehiculos_milp"),
]
for py_k, milp_k in cost_pairs:
    label = py_k.replace("_pyvrp","").replace("costo_","")
    print(f"    {label:<18}: PyVRP={report[py_k]:.4f}   MILP={report[milp_k]:.4f}")
print(f"    {'depositos':<18}: {report['costo_depositos']:.4f}")
print(f"    {'TOTAL':<18}: PyVRP={report['costo_total_pyvrp']:.4f}   MILP UB={report['ub_milp']:.4f}")

print("\n  Demand / service:")
print(f"    total_demand   : {report['demanda_total']:.0f}")
print(f"    served_demand  : {report['demanda_atendida']:.0f}")
print(f"    service_level  : {report['nivel_servicio']:.2%}")

print("\n  Per depot:")
for did in sorted(inst.depots.keys()):
    print(f"    depot {did}:")
    for suffix in ("capacidad", "cap_inducida", "demanda_pyvrp", "demanda_da_pyvrp",
                   "demanda_rt_pyvrp", "uso_pyvrp", "veh_pyvrp",
                   "demanda_milp", "uso_milp", "veh_milp"):
        val = report.get(f"d{did}_{suffix}")
        if val is None:
            val_str = "None"
        elif isinstance(val, float):
            val_str = f"{val:.4f}" if abs(val) < 1e6 else f"{val:.2e}"
        else:
            val_str = str(val)
        print(f"      {suffix:<22}: {val_str}")

print("\n  Summary:")
print(f"    ub_milp            : {report['ub_milp']:.4f}")
print(f"    ub_pyvrp           : {report['ub_pyvrp']:.4f}")
print(f"    raw_gap_pyvrp_minus_milp: {report['raw_gap_pyvrp_minus_milp']:.4%}")
print(f"    gap_final_abs          : {report['gap_final']:.4%}")
print(f"    violacion_capacidad: {report['violacion_capacidad']}")

# ─────────────────────────────────────────────────────────────
# PLOT 2 — solution routes
# ─────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("PLOT 2 — solution routes")
print(SEP)

fig, axes = plt.subplots(1, 2, figsize=(18, 8))
locs = info.get("locations")
depot_nodes  = info["depot_nodes"]
client_nodes = info["client_nodes"]

cmap_routing = plt.cm.Blues
cmap_da      = plt.cm.Greens

routes_routing = [r for r in sol.routes()
                  if vt_list[r.vehicle_type()]["type"] == "routing"]
routes_da      = [r for r in sol.routes()
                  if vt_list[r.vehicle_type()]["type"] == "direct_allocation"]

for ax_idx, (ax, routes_subset, title, cmap) in enumerate(zip(
    axes,
    [routes_routing, routes_da],
    ["Routing routes", "Direct Allocation routes"],
    [cmap_routing, cmap_da],
)):
    # depots
    for did, dnode in depot_nodes.items():
        ax.scatter(dnode.x, dnode.y, marker="*", s=350, color="crimson",
                   edgecolor="black", linewidth=0.8, zorder=5)
        ax.annotate(f"D{did}", (dnode.x, dnode.y), fontsize=9,
                    fontweight="bold", color="crimson", ha="center", va="top",
                    xytext=(0, -12), textcoords="offset points")
        if title.startswith("Direct"):
            ax.add_patch(plt.Circle((dnode.x, dnode.y), radius,
                                     edgecolor="crimson", facecolor="none",
                                     linestyle="--", alpha=0.2, linewidth=1.0))

    # all clients (background)
    for cnode in client_nodes.values():
        ax.scatter(cnode.x, cnode.y, s=25, color="lightgray", alpha=0.6, zorder=2)

    # routes
    nR = max(len(routes_subset), 1)
    for r_idx, route in enumerate(routes_subset):
        col = cmap(0.35 + 0.55 * (r_idx / max(1, nR - 1)))
        vt = vt_list[route.vehicle_type()]
        for trip in route.trips():
            if locs is None:
                continue
            seq = [trip.start_depot(), *trip.visits(), trip.end_depot()]
            xs = [locs[idx].x for idx in seq]
            ys = [locs[idx].y for idx in seq]
            ax.plot(xs, ys, "-o", color=col, linewidth=1.6,
                    markersize=4, alpha=0.85, zorder=3)
            # highlight visited clients
            for idx in trip.visits():
                ax.scatter(locs[idx].x, locs[idx].y, s=60,
                           color=col, edgecolor="black", linewidth=0.5,
                           zorder=4)

    n_routes_shown = len(routes_subset)
    n_clients_shown = sum(
        len(trip.visits())
        for r in routes_subset
        for trip in r.trips()
    )
    dist_shown = sum(r.distance() for r in routes_subset)
    ax.set_title(
        f"{title}\n"
        f"routes={n_routes_shown}  clients={n_clients_shown}  "
        f"dist={dist_shown:.1f} (scaled)",
        fontsize=10,
    )
    ax.set_aspect("equal", "box")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.grid(alpha=0.2, linestyle="--")

fig.suptitle(
    f"{config.instance}  |  R={radius}  F_R={config.F_R}  F_A={config.F_A}  "
    f"gap={report['gap_final']:.2%}",
    fontsize=12,
    fontweight="bold",
)
fig.tight_layout()

path2 = OUT / "plot2_solution.png"
fig.savefig(path2, dpi=150, bbox_inches="tight")
plt.close(fig)
print(f"  saved → {path2}")

# ─────────────────────────────────────────────────────────────
# PLOT 3 — cost breakdown bar chart (PyVRP vs MILP)
# ─────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("PLOT 3 — cost breakdown (PyVRP vs MILP)")
print(SEP)

categories = ["Routing", "DA", "Vehicles", "Depots"]
pyvrp_vals = [
    report["costo_routing_pyvrp"],
    report["costo_da_pyvrp"],
    report["costo_vehiculos_pyvrp"],
    report["costo_depositos"],
]
milp_vals = [
    report["costo_routing_milp"],
    report["costo_da_milp"],
    report["costo_vehiculos_milp"],
    report["costo_depositos"],   # same — depot cost is fixed from MILP
]

x = range(len(categories))
width = 0.35
fig, ax = plt.subplots(figsize=(9, 5))
bars_py   = ax.bar([i - width/2 for i in x], pyvrp_vals, width, label=f"PyVRP  (total={report['costo_total_pyvrp']:.2f})", color="steelblue", alpha=0.85)
bars_milp = ax.bar([i + width/2 for i in x], milp_vals,  width, label=f"MILP UB (total={report['ub_milp']:.2f})", color="darkorange", alpha=0.85)

for bar in bars_py + bars_milp:
    h = bar.get_height()
    if h > 0:
        ax.text(bar.get_x() + bar.get_width() / 2, h + 0.5, f"{h:.1f}",
                ha="center", va="bottom", fontsize=8)

ax.set_xticks(list(x))
ax.set_xticklabels(categories)
ax.set_ylabel("Cost")
ax.set_title(
    f"Cost breakdown — {config.instance}\n"
    f"abs gap = |PyVRP − MILP| / MILP = {report['gap_final']:.2%}",
    fontsize=11,
)
ax.legend(fontsize=9)
ax.grid(axis="y", alpha=0.3, linestyle="--")

path3 = OUT / "plot3_cost_breakdown.png"
fig.savefig(path3, dpi=150, bbox_inches="tight")
plt.close(fig)
print(f"  saved → {path3}")

# ─────────────────────────────────────────────────────────────
# PLOT 4 — per-depot demand usage (PyVRP vs MILP)
# ─────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("PLOT 4 — per-depot demand utilization")
print(SEP)

depot_ids = sorted(inst.depots.keys())
py_usage  = [report[f"d{d}_uso_pyvrp"] for d in depot_ids]
milp_usage = [report[f"d{d}_uso_milp"] or 0 for d in depot_ids]

fig, ax = plt.subplots(figsize=(7, 4))
x = range(len(depot_ids))
ax.bar([i - width/2 for i in x], py_usage,   width, label="PyVRP", color="steelblue", alpha=0.85)
ax.bar([i + width/2 for i in x], milp_usage, width, label="MILP",  color="darkorange", alpha=0.85)
ax.axhline(1.0, color="red", linestyle="--", linewidth=1, label="100% capacity")
ax.set_xticks(list(x))
ax.set_xticklabels([f"Depot {d}" for d in depot_ids])
ax.set_ylabel("Utilization")
ax.set_ylim(0, 1.15)
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
ax.set_title("Depot capacity utilization — PyVRP vs MILP", fontsize=11)
ax.legend(fontsize=9)
ax.grid(axis="y", alpha=0.3, linestyle="--")

path4 = OUT / "plot4_depot_utilization.png"
fig.savefig(path4, dpi=150, bbox_inches="tight")
plt.close(fig)
print(f"  saved → {path4}")

# ─────────────────────────────────────────────────────────────
# summary
# ─────────────────────────────────────────────────────────────
print(f"\n{SEP}")
print("DONE")
print(SEP)
print(f"  instance       : {config.instance}")
print(f"  clients        : {len(inst.clients)}  (DA: {n_da}  routing: {n_routing})")
print(f"  total cost     : {report['costo_total_pyvrp']:.4f}")
print(f"  MILP UB        : {config.UB:.4f}")
print(f"  abs gap        : {report['gap_final']:.4%}")
print(f"  service level  : {report['nivel_servicio']:.2%}")
print(f"  cap violated   : {report['violacion_capacidad']}")
print(f"\n  outputs:")
for p in sorted(OUT.glob("*.png")):
    print(f"    {p}")
