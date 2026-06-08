"""Streamlit demo: endogenous-DA capacity-repair LoRP-FSD solver.

Run:
    uv run streamlit run app_capacity_repair_solver.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from da_geometry import compute_max_distance
from dat_loader import load_dat
from instance_adapter import adapt_instance, spec_from_row
from instance_resolver import resolve_instance_path
from run_capacity_repair_batch import run_one
from xlsx_loader import load_lorp_fsd_mapping

EXCEL_PATH = "results_MILP.xlsx"
INSTANCE_FOLDER = "instances"

st.set_page_config(
    layout="wide",
    page_title="Endogenous DA Capacity-Repair Solver",
    page_icon="🛣️",
)


# ── data loaders ─────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def _load_mapping() -> pd.DataFrame:
    return load_lorp_fsd_mapping(EXCEL_PATH, instance_folder=None)


# ── plot helpers (Streamlit-native, no subprocess) ───────────────────────────

def _plot_instance(inst, config, escala: float) -> plt.Figure:
    radius_raw = float(config.R) / escala if escala > 0 else float(config.R)
    fig, ax = plt.subplots(figsize=(8, 7))
    for c in inst.clients.values():
        ax.scatter(c["x"], c["y"], s=35, color="lightgray", zorder=2)
    for did, d in inst.depots.items():
        ax.scatter(d["x"], d["y"], s=320, color="crimson", marker="*",
                   edgecolor="black", linewidth=0.8, zorder=5)
        ax.annotate(f"D{did}", (d["x"], d["y"]), fontsize=10, fontweight="bold",
                    color="crimson", ha="center", va="top",
                    xytext=(0, -12), textcoords="offset points")
        circle = plt.Circle((d["x"], d["y"]), radius_raw, edgecolor="crimson",
                             facecolor="none", linestyle="--", alpha=0.35, linewidth=1.2)
        ax.add_patch(circle)
    ax.set_aspect("equal", "box")
    ax.set_title(f"{config.instance}  |  R={config.R} (scaled)  "
                 f"R_raw≈{radius_raw:.2f}  scale={escala:.4f}", fontsize=10)
    ax.set_xlabel("X"); ax.set_ylabel("Y")
    ax.grid(alpha=0.25, linestyle="--")
    return fig


def _plot_solution(inst, config, iteration: int, routes_df: pd.DataFrame,
                   repairs_df: pd.DataFrame, escala: float, status: str) -> plt.Figure:
    radius_raw = float(config.R) / escala if escala > 0 else float(config.R)
    excluded = set()
    if not repairs_df.empty:
        rep = repairs_df[repairs_df["iteration"] <= iteration]
        excluded = set(zip(rep["depot_id"].astype(int), rep["client_id"].astype(int)))

    fig, ax = plt.subplots(figsize=(8, 7))
    for c in inst.clients.values():
        ax.scatter(c["x"], c["y"], s=25, color="lightgray", alpha=0.7, zorder=2)
    for did, d in inst.depots.items():
        ax.scatter(d["x"], d["y"], s=320, color="crimson", marker="*",
                   edgecolor="black", linewidth=0.7, zorder=5)
        ax.annotate(f"D{did}", (d["x"], d["y"]), fontsize=9, fontweight="bold",
                    color="crimson", ha="center", va="top",
                    xytext=(0, -12), textcoords="offset points")
        circle = plt.Circle((d["x"], d["y"]), radius_raw, edgecolor="crimson",
                             facecolor="none", linestyle="--", alpha=0.2, linewidth=1.0)
        ax.add_patch(circle)

    sub = routes_df[routes_df["iteration"] == iteration]
    for _, rec in sub.iterrows():
        depot = inst.depots[int(rec["depot_id"])]
        seq_ids = [int(s) for s in str(rec["client_sequence"]).split() if s]
        if not seq_ids:
            continue
        xs = [depot["x"]] + [inst.clients[c]["x"] for c in seq_ids] + [depot["x"]]
        ys = [depot["y"]] + [inst.clients[c]["y"] for c in seq_ids] + [depot["y"]]
        if rec["kind"] == "routing":
            ax.plot(xs, ys, "-o", color="steelblue", linewidth=1.3, markersize=4,
                    alpha=0.9, zorder=3)
        else:
            ax.plot(xs[:2], ys[:2], "--o", color="seagreen", linewidth=1.0,
                    markersize=4, alpha=0.85, zorder=3)
    for _, cid in excluded:
        c = inst.clients.get(cid)
        if c is None:
            continue
        ax.scatter(c["x"], c["y"], s=130, facecolor="none", edgecolor="red",
                   linewidth=1.8, zorder=6)

    handles = [
        mpatches.Patch(color="steelblue", label="Routing"),
        mpatches.Patch(color="seagreen", label="DA"),
        mpatches.Patch(facecolor="none", edgecolor="red", label="Excluded"),
    ]
    ax.legend(handles=handles, loc="upper left", fontsize=8)
    ax.set_aspect("equal", "box")
    ax.set_title(f"Iteration {iteration}  status={status}", fontsize=10)
    ax.set_xlabel("X"); ax.set_ylabel("Y")
    ax.grid(alpha=0.25, linestyle="--")
    return fig


def _plot_cost_decomposition(report: Dict[str, Any]) -> plt.Figure:
    cats = ["Routing", "DA", "Vehicles", "Depots"]
    vals = [
        float(report.get("costo_routing_pyvrp") or 0.0),
        float(report.get("costo_da_pyvrp") or 0.0),
        float(report.get("costo_vehiculos_pyvrp") or 0.0),
        float(report.get("costo_depositos") or 0.0),
    ]
    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar(cats, vals, color=["steelblue", "seagreen", "goldenrod", "slategray"])
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height(), f"{v:.1f}",
                ha="center", va="bottom", fontsize=9)
    total = sum(vals)
    ub = float(report.get("milp_ub") or 0.0)
    ax.axhline(ub, color="red", linewidth=1.0, linestyle="--",
               label=f"MILP UB={ub:.1f}")
    ax.set_ylabel("Cost")
    ax.set_title(f"Cost decomposition — total={total:.1f}", fontsize=11)
    ax.legend()
    ax.grid(axis="y", alpha=0.3, linestyle="--")
    return fig


def _plot_capacity_audit(audit_df: pd.DataFrame) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(7, 4))
    if audit_df.empty:
        ax.text(0.5, 0.5, "No audit data", ha="center", va="center")
        return fig
    audit_df = audit_df.sort_values("depot_id")
    x = list(range(len(audit_df)))
    rt = audit_df["routing_demand"].values
    da = audit_df["da_demand"].values
    caps = audit_df["capacity"].values
    ax.bar(x, rt, label="Routing demand", color="steelblue")
    ax.bar(x, da, bottom=rt, label="DA demand", color="seagreen")
    for i, c in enumerate(caps):
        ax.hlines(c, i - 0.4, i + 0.4, colors="red", linewidth=2,
                  label="Capacity" if i == 0 else None)
    ax.set_xticks(x)
    ax.set_xticklabels([f"D{int(d)}" for d in audit_df["depot_id"]])
    ax.set_ylabel("Demand")
    ax.set_title("Per-depot demand vs capacity")
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.3, linestyle="--")
    return fig


# ── solver runner ────────────────────────────────────────────────────────────

def _run_solver(row, runtime: int, runs: int, max_iters: int,
                encode_cost_factors: bool, out_dir: Path,
                progress_placeholder) -> Dict[str, Any]:
    convergence: List[Dict[str, Any]] = []
    repairs: List[Dict[str, Any]] = []
    depot_audit: List[Dict[str, Any]] = []
    routes: List[Dict[str, Any]] = []
    da_pool: List[Dict[str, Any]] = []

    args_ns = SimpleNamespace(
        runtime=runtime,
        runs=runs,
        max_iters=max_iters,
        encode_cost_factors=encode_cost_factors,
    )

    progress_placeholder.info("Running solver — see terminal/log for live trace.")
    result_rec = run_one(
        row, Path(INSTANCE_FOLDER), args_ns,
        convergence, repairs, depot_audit, routes, da_pool,
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([result_rec]).to_csv(out_dir / "results.csv", index=False)
    pd.DataFrame(convergence).to_csv(out_dir / "convergence.csv", index=False)
    pd.DataFrame(repairs).to_csv(out_dir / "repairs.csv", index=False)
    pd.DataFrame(depot_audit).to_csv(out_dir / "depot_audit.csv", index=False)
    pd.DataFrame(routes).to_csv(out_dir / "routes.csv", index=False)
    pd.DataFrame(da_pool).to_csv(out_dir / "da_pool_stats.csv", index=False)

    return {
        "result": result_rec,
        "convergence": pd.DataFrame(convergence),
        "repairs": pd.DataFrame(repairs),
        "depot_audit": pd.DataFrame(depot_audit),
        "routes": pd.DataFrame(routes),
        "da_pool_stats": pd.DataFrame(da_pool),
        "out_dir": str(out_dir),
    }


# ── UI ───────────────────────────────────────────────────────────────────────

st.title("Endogenous DA Capacity-Repair Solver Demo")
st.caption("Interactive LoRP-FSD PyVRP heuristic with shared depot-capacity audit")

mapping = _load_mapping()

with st.sidebar:
    st.header("Run config")
    row_ids = mapping["row_id"].tolist()
    default_idx = row_ids.index(3) if 3 in row_ids else 0
    row_id = st.selectbox(
        "row_id",
        options=row_ids,
        index=default_idx,
        format_func=lambda r: f"{r} — {mapping.loc[mapping['row_id'] == r, 'instance'].iloc[0]}",
    )
    runtime = st.number_input("runtime (s/seed)", min_value=1, max_value=300, value=15, step=1)
    runs = st.number_input("runs (seeds)", min_value=1, max_value=20, value=3, step=1)
    max_iters = st.number_input("max_iters", min_value=1, max_value=30, value=3, step=1)
    encode_cost_factors = st.checkbox("encode_cost_factors (weighted objective)", value=True)
    run_clicked = st.button("Run selected row", type="primary", use_container_width=True)

# Trigger run
if run_clicked:
    row = mapping[mapping["row_id"] == row_id].iloc[0]
    out_dir = Path(f"pipeline_out/streamlit_demo_row{row_id}")
    progress = st.empty()
    started = time.perf_counter()
    with st.spinner(f"Solving row {row_id}…"):
        outputs = _run_solver(
            row, int(runtime), int(runs), int(max_iters),
            bool(encode_cost_factors), out_dir, progress,
        )
    elapsed = time.perf_counter() - started
    progress.success(f"Done in {elapsed:.1f}s")
    st.session_state["outputs"] = outputs
    st.session_state["row_id"] = int(row_id)

# ── Render outputs from session state ───────────────────────────────────────
outputs = st.session_state.get("outputs")
if outputs is None:
    st.info("Select a row and press **Run selected row** in the sidebar to start.")
    st.stop()

result = outputs["result"]
convergence_df = outputs["convergence"]
repairs_df = outputs["repairs"]
audit_df = outputs["depot_audit"]
routes_df = outputs["routes"]
da_pool_df = outputs["da_pool_stats"]

row_id = st.session_state.get("row_id")
row = mapping[mapping["row_id"] == row_id].iloc[0]
config = spec_from_row(row)
resolution = resolve_instance_path(config.instance, Path(INSTANCE_FOLDER))
inst = adapt_instance(load_dat(resolution.path), config) if resolution.ok else None
max_dist = compute_max_distance(inst) if inst is not None else 1.0
escala = 100.0 / max_dist if max_dist > 0 else 1.0

# ── A. Summary metric cards ──
st.subheader(f"Row {row_id} — {result.get('instance')}")
cards = st.columns(5)
cards[0].metric("Final status", result.get("status"))
cards[1].metric("Final iteration", result.get("final_iteration"))
cards[2].metric("PyVRP feasible", str(result.get("pyvrp_feasible_final")))
cards[3].metric("MILP UB", f"{result.get('milp_ub'):.2f}" if result.get("milp_ub") else "-")
cards[4].metric("PyVRP total", f"{result.get('costo_total_pyvrp'):.2f}"
                if result.get("costo_total_pyvrp") is not None else "-")

cards2 = st.columns(5)
raw_gap = result.get("raw_gap_pyvrp_minus_milp")
abs_gap = result.get("abs_gap_pyvrp_vs_milp")
cards2[0].metric("Raw gap", f"{raw_gap*100:.2f}%" if raw_gap is not None else "-")
cards2[1].metric("|Gap|", f"{abs_gap*100:.2f}%" if abs_gap is not None else "-")
cards2[2].metric("Max excess (final)", f"{result.get('max_excess_final'):.1f}"
                if result.get("max_excess_final") is not None else "-")
cards2[3].metric("Exclusions applied", result.get("n_exclusions_total"))
cards2[4].metric("Missing clients", result.get("missing_clients_final"))

st.divider()

# ── B. Cost decomposition ──
st.subheader("Cost decomposition")
col_cost1, col_cost2 = st.columns([2, 1])
with col_cost1:
    st.pyplot(_plot_cost_decomposition(result), use_container_width=True)
with col_cost2:
    F_R = float(config.F_R)
    F_A = float(config.F_A)
    decomp = pd.DataFrame([
        {"field": "routing_distance_scaled", "value": result.get("routing_distance_scaled")},
        {"field": "da_distance_scaled", "value": result.get("da_distance_scaled")},
        {"field": "F_R", "value": F_R},
        {"field": "F_A", "value": F_A},
        {"field": "n_veh_routing", "value": result.get("n_veh_routing")},
        {"field": "n_veh_da", "value": result.get("n_veh_da")},
        {"field": "veh_fixed_cost", "value": inst.data["veh_fixed_cost"] if inst is not None else None},
        {"field": "depot_cost (Excel)", "value": result.get("costo_depositos")},
    ])
    st.dataframe(decomp, hide_index=True, use_container_width=True)

st.divider()

# ── C. Iteration tabs ──
st.subheader("Iteration explorer")
iter_values = sorted(int(i) for i in convergence_df["iteration"].unique()) if not convergence_df.empty else []
final_iter = max(iter_values) if iter_values else 0
tab_labels = [f"Iteration {i}" for i in iter_values] + ["Final"]
tabs = st.tabs(tab_labels) if iter_values else [st.container()]

def _render_iter_view(container, iteration: int):
    with container:
        conv_iter = convergence_df[convergence_df["iteration"] == iteration]
        if conv_iter.empty:
            container.write("No data.")
            return
        row_iter = conv_iter.iloc[0]
        m1 = st.columns(5)
        m1[0].metric("Objective", f"{row_iter['best_objective_scaled']:.2f}")
        m1[1].metric("Total cost", f"{row_iter['post_total_cost']:.2f}")
        rg = row_iter.get("raw_gap_pyvrp_minus_milp")
        m1[2].metric("Raw gap",
                     f"{rg*100:.2f}%" if pd.notna(rg) else "-")
        ab = abs(rg) if pd.notna(rg) else None
        m1[3].metric("|Gap|", f"{ab*100:.2f}%" if ab is not None else "-")
        m1[4].metric("PyVRP feasible", str(bool(row_iter.get("pyvrp_feasible"))))

        m2 = st.columns(5)
        m2[0].metric("Max excess", f"{row_iter['max_excess']:.1f}")
        m2[1].metric("Cap violated", str(bool(row_iter["capacity_violated"])))
        m2[2].metric("Overloaded", str(row_iter.get("overloaded_depots") or "-"))
        m2[3].metric("Exclusions added", int(row_iter["n_exclusions_added"]))
        m2[4].metric("Objective mode", str(row_iter.get("objective_mode")))

        c1, c2 = st.columns([1, 1])
        with c1:
            st.markdown("**Capacity audit**")
            sub = audit_df[audit_df["iteration"] == iteration]
            st.dataframe(
                sub[["depot_id", "capacity", "routing_demand", "da_demand",
                     "total_demand", "usage", "excess", "violated"]]
                if not sub.empty else sub,
                hide_index=True, use_container_width=True,
            )
            st.pyplot(_plot_capacity_audit(sub), use_container_width=True)
        with c2:
            st.markdown("**Solution plot**")
            if inst is not None:
                st.pyplot(_plot_solution(inst, config, iteration, routes_df,
                                          repairs_df, escala,
                                          str(result.get("status"))),
                          use_container_width=True)

        st.markdown("**Repairs this iteration**")
        r_iter = repairs_df[repairs_df["iteration"] == iteration]
        if r_iter.empty:
            st.write("No repair in this iteration.")
        else:
            st.dataframe(r_iter, hide_index=True, use_container_width=True)

        st.markdown("**Routes this iteration**")
        rt_iter = routes_df[routes_df["iteration"] == iteration]
        st.dataframe(rt_iter, hide_index=True, use_container_width=True)

for label_idx, it in enumerate(iter_values):
    _render_iter_view(tabs[label_idx], it)
if iter_values:
    _render_iter_view(tabs[-1], final_iter)

st.divider()

# ── D, E, F shown inside tabs above. Now G plots overview, H methodology.

st.subheader("Instance plot")
if inst is not None:
    st.pyplot(_plot_instance(inst, config, escala), use_container_width=True)

with st.expander("Methodology & caveats", expanded=False):
    st.markdown(
        """
**Scaling and constraints**

- Arslan scaling: `dist_scaled = raw_dist * 100 / max_dist`.
- **R** (DA eligibility) is in scaled-distance units. A client is DA-eligible from depot d iff `raw_dist(d, j) * scale ≤ R`. Equivalently the raw radius is `R / scale` — used only for plotting in raw coords.
- **Length** is the maximum routing route length in scaled-distance units. Applied **only** to routing vehicles via `max_distance=Length`.
- DA vehicles use **no** `max_distance`; DA feasibility is governed solely by R.

**Solver representation**

- One routing profile per depot; routing graph excludes any `(depot, client)` pair flagged by repair.
- One DA profile per `(depot, client)` candidate (1:1 vehicle, capacity = client demand, return cost 0).
- PyVRP cannot enforce shared depot capacity DA+routing. Real capacity is audited ex post.

**Repair**

- For each route in an overloaded depot, removal savings:
  `Δ = d(i,j) + d(j,k) − d(i,k)` for each client j with predecessor i and successor k.
- Greedy descending Δ until excess covered. Excluded pairs are added to the routing graph mask.
- Isolation guard skips exclusions that would leave a client with no remaining service option.

**Cost decomposition**

- `routing_cost = routing_distance_scaled * F_R`
- `da_cost = da_distance_scaled * F_A`
- `vehicle_cost = n_routing_vehicles * veh_fixed_cost` (DA vehicles excluded)
- `depot_cost = config.cost_depots` (from Excel)

**encode_cost_factors flag**

- False: edge cost = `raw * scale` (unweighted). PyVRP objective = total scaled distance.
- True: routing edge = `raw * scale * F_R`; DA edge = `raw * scale * F_A`. PyVRP optimizes the weighted Arslan objective, which lines up the solver with Alan-C / former Colab.
- Reporting always uses unweighted scaled distances reconstructed geometrically, so F_R/F_A are applied exactly once and never double-counted.
        """
    )
