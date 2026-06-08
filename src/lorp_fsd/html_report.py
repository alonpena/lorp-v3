"""Static HTML row report (Phase 8).

Reads the artifacts already produced by the row runner inside one output
folder and emits a single self-contained ``index.html`` file:

    outputs/<run_id>/<instance_name>/report.json
    outputs/<run_id>/<instance_name>/cost-breakdown.csv
    outputs/<run_id>/<instance_name>/depot_usage.csv
    outputs/<run_id>/<instance_name>/iteration_summary.csv
    outputs/<run_id>/<instance_name>/repair_trace.csv
    outputs/<run_id>/<instance_name>/iteration_XX_audit.json
    outputs/<run_id>/<instance_name>/iteration_XX_routes.csv
    outputs/<run_id>/<instance_name>/iteration_XX_assignments.csv
    outputs/<run_id>/<instance_name>/iteration_XX_instance.png
    outputs/<run_id>/<instance_name>/iteration_XX_solution.png
        -> outputs/<run_id>/<instance_name>/index.html

This module is a pure reader. It does NOT touch the solver, repair, cost
reconstruction, or any runner logic. It only renders existing files, so it can
be regenerated at any time and run on historical output folders.

The output is HTML-first and academic: white background, dark text, subtle
blue/gray accents, no external CDN. View tabs and iteration tabs use a small
amount of embedded JavaScript; plots are embedded as base64 so the single file
is portable.
"""

from __future__ import annotations

import base64
import csv
import datetime as _dt
import html
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── status explanations (kept in one place; shown verbatim in the report) ─────

STATUS_EXPLANATIONS: Dict[str, str] = {
    "FEASIBLE": "All ex-post checks passed and the reported GAP is valid.",
    "REPAIR_INFEASIBLE": "Heuristic repair failed to remove a violation. This is a "
    "failure of the heuristic, not a proof of mathematical infeasibility.",
    "STUCK_NONCAPACITY_VIOLATION": "Capacity repair cannot fix a remaining "
    "non-capacity violation (e.g. route length or DA radius).",
    "MAX_ITERATIONS": "The repair loop reached its iteration budget before "
    "reaching a feasible solution.",
    "TIMEOUT": "The row-level wall-clock guard stopped the row before it finished.",
    "ERROR": "The row aborted with an internal error; inspect logs.",
}

# repair candidate policy explanations
REPAIR_POLICY_EXPLANATIONS: Dict[str, str] = {
    "baseline": "Only prevents stranding (never removes a client's last service option).",
    "safe_length": "Also rejects cuts with no length-feasible service alternative.",
    "safe_capacity_release": "Also rejects same-depot DA risk (a routing→DA move at "
    "the same overloaded depot does not release aggregate depot capacity).",
    "safe_both": "Applies both the length-safety and capacity-release filters.",
}

PROFESSOR_MAPPING = [
    "Transform the allocation-or-routing subproblem into a capacity-relaxed MD-VRP.",
    "Solve the relaxed MD-VRP (depot aggregate capacity relaxed; vehicle capacity "
    "and route length still enforced).",
    "Audit depot capacity ex-post on the reconstructed LoRP solution.",
    "Repair overloaded depots: rank routing clients by cost saving, validate safe "
    "candidates, forbid the routing pair (depot, client).",
    "Rebuild the graph and solve again until feasible or a stop condition fires.",
]

_STATUS_CLASS = {
    "FEASIBLE": "ok",
    "REPAIR_INFEASIBLE": "bad",
    "STUCK_NONCAPACITY_VIOLATION": "bad",
    "MAX_ITERATIONS": "warn",
    "TIMEOUT": "warn",
    "ERROR": "bad",
}

_ITER_RE = re.compile(r"iteration_(\d+)_(instance|solution)\.png$")
_AUDIT_RE = re.compile(r"iteration_(\d+)_audit\.json$")

VIEWS = ["Summary", "Costs", "Capacity", "Feasibility", "Iterations", "Plots", "Files"]


# ── small helpers ─────────────────────────────────────────────────────────────

def _esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def _fmt(value: Any, digits: int = 4) -> str:
    if value is None or value == "":
        return "—"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        if value != value:  # NaN
            return "—"
        return f"{value:.{digits}g}"
    return str(value)


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


def _read_csv(path: Path) -> List[List[str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        return [row for row in csv.reader(f)]


def _img_data_uri(path: Optional[Path]) -> Optional[str]:
    if path is None or not path.exists():
        return None
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def _overloaded_from_excess(excess: Dict[str, Any]) -> List[str]:
    return [d for d, v in sorted(excess.items()) if isinstance(v, (int, float)) and v > 0]


# ── table builders ─────────────────────────────────────────────────────────────

def _kv_table(rows: List[Tuple[Any, Any]]) -> str:
    body = "".join(f"<tr><th>{_esc(k)}</th><td>{_esc(v)}</td></tr>" for k, v in rows)
    return f'<table class="kv">{body}</table>'


def _csv_table(rows: List[List[str]], *, numeric_from: int = 1, scroll: bool = False) -> str:
    if not rows:
        return '<p class="muted">No data.</p>'
    head, *body = rows
    if not body:
        return '<p class="muted">No rows.</p>'
    ths = "".join(f"<th>{_esc(c)}</th>" for c in head)
    trs = []
    for r in body:
        tds = "".join(
            f'<td class="{"num" if i >= numeric_from else ""}">{_esc(c)}</td>'
            for i, c in enumerate(r)
        )
        trs.append(f"<tr>{tds}</tr>")
    tbl = (
        f'<table class="grid"><thead><tr>{ths}</tr></thead>'
        f'<tbody>{"".join(trs)}</tbody></table>'
    )
    return f'<div class="scroll">{tbl}</div>' if scroll else tbl


# ── summary view ────────────────────────────────────────────────────────────────

def _cards(payload: Dict[str, Any]) -> str:
    milp = payload.get("milp", {})
    pyvrp = payload.get("pyvrp", {})
    metric = payload.get("comparison_metric", {})
    feas = payload.get("feasibility", {})
    status = payload.get("status", "")
    sclass = _STATUS_CLASS.get(status, "warn")
    cards = [
        ("MILP UB", _fmt(milp.get("UB"))),
        ("PyVRP total", _fmt(pyvrp.get("total"))),
        (f"{metric.get('label', 'metric')}", _fmt(metric.get("value"), 3)),
        ("Runtime (s)", _fmt(payload.get("total_solve_time"), 4)),
        ("Iterations", _fmt(payload.get("n_iterations"))),
    ]
    items = "".join(
        f'<div class="card"><div class="card-val">{_esc(v)}</div>'
        f'<div class="card-lab">{_esc(k)}</div></div>'
        for k, v in cards
    )
    feas_txt = "FEASIBLE" if feas.get("fully_feasible") else "NOT FEASIBLE"
    items += (
        f'<div class="card status-{sclass}"><div class="card-val">{_esc(status)}</div>'
        f'<div class="card-lab">{_esc(feas_txt)}</div></div>'
    )
    return f'<div class="cards">{items}</div>'


def _professor_box() -> str:
    items = "".join(f"<li>{_esc(s)}</li>" for s in PROFESSOR_MAPPING)
    return (
        '<div class="explain"><p class="cur">How this maps to the professor’s '
        'algorithm</p><ol>' + items + "</ol></div>"
    )


# ── feasibility view ─────────────────────────────────────────────────────────────

def _feasibility_table(feas: Dict[str, Any]) -> str:
    checks = [
        ("Service exactly once", feas.get("served_exactly_once")),
        ("Depot capacity", feas.get("capacity_feasible")),
        ("Route length", feas.get("route_length_feasible")),
        ("Vehicle (route) capacity", feas.get("route_capacity_feasible")),
        ("DA radius", feas.get("da_radius_feasible")),
        ("No penalty-distance suspicion", not feas.get("penalty_distance_suspected")),
    ]
    rows = []
    for name, ok in checks:
        cls = "ok" if ok else "bad"
        label = "PASS" if ok else "FAIL"
        rows.append(
            f'<tr><th>{_esc(name)}</th>'
            f'<td><span class="pill {cls}">{label}</span></td></tr>'
        )
    return f'<table class="kv">{"".join(rows)}</table>'


def _status_legend(status: str) -> str:
    items = "".join(
        f"<li><b>{_esc(k)}</b> — {_esc(v)}</li>" for k, v in STATUS_EXPLANATIONS.items()
    )
    note = STATUS_EXPLANATIONS.get(status)
    cur = (
        f'<p class="cur">This row is <b>{_esc(status)}</b>: {_esc(note)}</p>'
        if note else ""
    )
    return f'<div class="explain">{cur}<ul>{items}</ul></div>'


# ── capacity view: repair-policy explanation ────────────────────────────────────

def _repair_policy_box(active: str) -> str:
    rows = []
    for name, desc in REPAIR_POLICY_EXPLANATIONS.items():
        cls = " class='active'" if name == active else ""
        mark = " ← active" if name == active else ""
        rows.append(
            f"<tr{cls}><th><code>{_esc(name)}</code>{mark}</th>"
            f"<td>{_esc(desc)}</td></tr>"
        )
    head = f"<p class='cur'>Repair candidate policy: <code>{_esc(active or '—')}</code></p>"
    detail = ""
    if active == "safe_both":
        detail = (
            "<p><b>safe_both</b> requires a candidate to pass both filters:</p><ul>"
            "<li><b>length safety</b>: after forbidding routing from the overloaded "
            "depot, the client must still have a feasible alternative — DA within R, "
            "or a singleton route with 2·dist ≤ Length.</li>"
            "<li><b>capacity-release safety</b>: reject candidates that would only "
            "move to DA from the same overloaded depot, because routing→DA at the "
            "same depot does not release aggregate depot capacity.</li></ul>"
        )
    return (
        f'<div class="explain">{head}{detail}'
        f'<table class="kv">{"".join(rows)}</table></div>'
    )


# ── plots view ───────────────────────────────────────────────────────────────────

def _collect_iteration_plots(output_dir: Path) -> Dict[int, Dict[str, Path]]:
    out: Dict[int, Dict[str, Path]] = {}
    for p in sorted(output_dir.glob("iteration_*_*.png")):
        m = _ITER_RE.search(p.name)
        if not m:
            continue
        out.setdefault(int(m.group(1)), {})[m.group(2)] = p
    return out


def _figure(label: str, path: Optional[Path]) -> str:
    uri = _img_data_uri(path)
    if uri is None:
        return ""
    return (
        f'<figure><figcaption>{_esc(label)} — <code>{_esc(path.name)}</code></figcaption>'
        f'<img alt="{_esc(label)}" src="{uri}"></figure>'
    )


def _final_plots_section(output_dir: Path) -> str:
    plots = _collect_iteration_plots(output_dir)
    if not plots:
        return '<p class="muted">No plots found in this folder.</p>'
    first, last = min(plots), max(plots)
    blocks = [
        _figure("Basal instance", plots[first].get("instance")),
        _figure("Combined solution", plots[last].get("solution")),
    ]
    blocks = [b for b in blocks if b]
    return f'<div class="plots">{"".join(blocks)}</div>' if blocks else \
        '<p class="muted">No plots found in this folder.</p>'


# ── iterations view ─────────────────────────────────────────────────────────────

def _iteration_audits(output_dir: Path) -> List[Tuple[int, Dict[str, Any]]]:
    found = []
    for p in sorted(output_dir.glob("iteration_*_audit.json")):
        m = _AUDIT_RE.search(p.name)
        if not m:
            continue
        data = _read_json(p)
        if data is not None:
            found.append((int(m.group(1)), data))
    return sorted(found, key=lambda t: t[0])


def _iteration_panel(it: int, audit: Dict[str, Any], output_dir: Path, active: bool) -> str:
    excess = audit.get("excess", {}) or {}
    overloaded = _overloaded_from_excess(excess)
    selected = audit.get("selected_repair_removals", []) or []
    rejected = audit.get("rejected_repair_candidates", []) or []

    summary = _kv_table([
        ("Iteration", it),
        ("Status", audit.get("status")),
        ("Fully feasible", audit.get("fully_feasible")),
        ("Capacity feasible", audit.get("capacity_feasible")),
        ("Z PyVRP", _fmt(audit.get("z_pyvrp"))),
        (f"{audit.get('comparison_metric_label', 'metric')}",
         _fmt(audit.get("comparison_metric_value"), 3)),
        ("Solve time (s)", _fmt(audit.get("solve_time"), 4)),
        ("Overloaded depots", overloaded or "none"),
        ("Total excess", _fmt(sum(v for v in excess.values() if isinstance(v, (int, float))))),
    ])

    feas = {
        "served_exactly_once": audit.get("all_clients_served_exactly_once"),
        "capacity_feasible": audit.get("capacity_feasible"),
        "route_length_feasible": audit.get("route_length_feasible"),
        "route_capacity_feasible": audit.get("route_capacity_feasible"),
        "da_radius_feasible": audit.get("da_radius_feasible"),
        "penalty_distance_suspected": audit.get("penalty_distance_suspected"),
    }

    def _pairs(items: List[Any]) -> str:
        if not items:
            return '<p class="muted">none</p>'
        cells = "".join(
            f"<li>depot {_esc(p[0])} → client {_esc(p[1])}"
            + (f" <span class='muted'>({_esc(p[2])})</span>" if len(p) > 2 else "")
            + "</li>"
            for p in items
        )
        return f"<ul class='pairs'>{cells}</ul>"

    repair = (
        "<div class='two'>"
        f"<div><h4>Selected repair candidates</h4>{_pairs(selected)}</div>"
        f"<div><h4>Rejected candidates</h4>{_pairs(rejected)}</div>"
        "</div>"
    )

    routes = _csv_table(_read_csv(output_dir / f"iteration_{it:02d}_routes.csv"), scroll=True)
    assigns = _csv_table(_read_csv(output_dir / f"iteration_{it:02d}_assignments.csv"), scroll=True)

    plots = _collect_iteration_plots(output_dir).get(it, {})
    plot_blocks = [_figure("Instance", plots.get("instance")), _figure("Solution", plots.get("solution"))]
    plot_blocks = [b for b in plot_blocks if b]
    plots_html = f'<div class="plots">{"".join(plot_blocks)}</div>' if plot_blocks else \
        '<p class="muted">No plots for this iteration.</p>'

    cls = "iter-panel active" if active else "iter-panel"
    return (
        f'<div class="{cls}" data-iter="{it}">'
        f"<div class='two'><div><h4>Audit summary</h4>{summary}</div>"
        f"<div><h4>Feasibility</h4>{_feasibility_table(feas)}</div></div>"
        f"<h4>Repair</h4>{repair}"
        f"<h4>Routes</h4>{routes}"
        f"<h4>Assignments</h4>{assigns}"
        f"<h4>Plots</h4>{plots_html}"
        "</div>"
    )


def _iterations_section(output_dir: Path) -> str:
    audits = _iteration_audits(output_dir)
    if not audits:
        return '<p class="muted">No per-iteration audit files found.</p>'
    tabs = "".join(
        f'<button class="iter-tab{" active" if i == 0 else ""}" '
        f'onclick="showIter({it})" data-iter="{it}">Iteration {it}</button>'
        for i, (it, _) in enumerate(audits)
    )
    panels = "".join(
        _iteration_panel(it, audit, output_dir, active=(i == 0))
        for i, (it, audit) in enumerate(audits)
    )
    return f'<div class="iter-tabs">{tabs}</div>{panels}'


def _artifact_list(output_dir: Path) -> str:
    names = [
        "report.json", "report.md", "cost-breakdown.csv", "depot_usage.csv",
        "iteration_summary.csv", "repair_trace.csv",
    ]
    names += sorted(p.name for p in output_dir.glob("iteration_*.png"))
    names += sorted(p.name for p in output_dir.glob("iteration_*.csv"))
    names += sorted(p.name for p in output_dir.glob("iteration_*_audit.json"))
    items = []
    for n in names:
        present = (output_dir / n).exists()
        cls = "" if present else " class='muted'"
        mark = "" if present else " (missing)"
        items.append(f"<li{cls}><code>{_esc(n)}</code>{mark}</li>")
    return f"<ul class='files'>{''.join(items)}</ul>"


# ── CSS + JS (embedded, no CDN) ─────────────────────────────────────────────────

_CSS = """
:root{--ink:#1f2933;--muted:#6b7280;--line:#e5e9f0;--accent:#2c5282;
--accent-2:#3a6ea5;--accent-bg:#eef3fa;--ok:#1f7a4d;--ok-bg:#e6f4ec;
--bad:#9b2c2c;--bad-bg:#fbeaea;--warn:#8a6d1f;--warn-bg:#fbf4e0;--panel:#fbfcfe;}
*{box-sizing:border-box}
body{font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
color:var(--ink);background:#f6f8fb;margin:0;padding:0 0 4rem}
.wrap{max-width:1000px;margin:0 auto;padding:0 1.5rem}
header{background:#fff;border-bottom:3px solid var(--accent);padding:1.6rem 0 1.1rem;margin-bottom:0}
header .wrap{padding-top:0;padding-bottom:0}
h1{font-size:1.45rem;margin:0 0 .3rem;color:var(--accent);letter-spacing:-.01em}
.sub{color:var(--muted);font-size:.92rem;margin:.12rem 0}
.sub b{color:var(--ink)}
h2{font-size:1.12rem;margin:0 0 .8rem;padding-bottom:.35rem;border-bottom:1px solid var(--line);color:var(--accent)}
h4{font-size:.92rem;margin:1rem 0 .4rem;color:var(--accent-2);text-transform:uppercase;letter-spacing:.04em}
/* sticky view nav */
nav.views{position:sticky;top:0;z-index:5;background:#fff;border-bottom:1px solid var(--line);
box-shadow:0 1px 4px rgba(31,41,51,.05);padding:.5rem 0;margin-bottom:1.5rem}
nav.views .wrap{display:flex;flex-wrap:wrap;gap:.4rem;padding-top:0;padding-bottom:0}
.view-tab{border:1px solid var(--line);background:#fff;color:var(--ink);padding:.35rem .85rem;
border-radius:6px;font-size:.86rem;cursor:pointer;transition:all .12s}
.view-tab:hover{border-color:var(--accent-2);color:var(--accent)}
.view-tab.active{background:var(--accent);border-color:var(--accent);color:#fff}
section.view{display:none}section.view.active{display:block}
.panel{background:#fff;border:1px solid var(--line);border-radius:10px;padding:1.3rem 1.5rem;margin-bottom:1.3rem}
.cards{display:flex;flex-wrap:wrap;gap:.7rem}
.card{flex:1 1 120px;border:1px solid var(--line);border-radius:8px;padding:.7rem .9rem;background:var(--panel)}
.card-val{font-size:1.3rem;font-weight:600;letter-spacing:-.01em}
.card-lab{color:var(--muted);font-size:.72rem;text-transform:uppercase;letter-spacing:.04em;margin-top:.15rem}
.status-ok{background:var(--ok-bg);border-color:#bfe3cd}.status-ok .card-val{color:var(--ok)}
.status-bad{background:var(--bad-bg);border-color:#f0c9c9}.status-bad .card-val{color:var(--bad)}
.status-warn{background:var(--warn-bg);border-color:#ecdca6}.status-warn .card-val{color:var(--warn)}
table{border-collapse:collapse;width:100%;margin:.3rem 0 .6rem;font-size:.88rem}
table.kv th{text-align:left;width:42%;color:var(--muted);font-weight:500;vertical-align:top}
table.kv th,table.kv td{padding:.34rem .5rem;border-bottom:1px solid var(--line)}
table.kv tr.active th,table.kv tr.active td{background:var(--accent-bg)}
table.grid th{position:sticky;top:0;background:var(--accent-bg);color:var(--accent);text-align:left;
font-weight:600;border:1px solid var(--line);padding:.4rem .6rem}
table.grid td{padding:.36rem .6rem;border:1px solid var(--line)}
table.grid tbody tr:nth-child(even){background:#f8fafc}
td.num{text-align:right;font-variant-numeric:tabular-nums}
.scroll{max-height:340px;overflow:auto;border:1px solid var(--line);border-radius:6px}
.scroll table{margin:0}
.pill{display:inline-block;padding:.1rem .55rem;border-radius:99px;font-size:.76rem;font-weight:600}
.pill.ok{background:var(--ok-bg);color:var(--ok)}.pill.bad{background:var(--bad-bg);color:var(--bad)}
.two{display:flex;flex-wrap:wrap;gap:1.5rem}.two>div{flex:1 1 320px;min-width:0}
.explain{background:var(--accent-bg);border:1px solid #cfe0f3;border-radius:8px;padding:1rem 1.2rem;margin:.6rem 0}
.explain .cur{margin:0 0 .55rem;font-weight:600;color:var(--accent)}
.explain ul,.explain ol{margin:.3rem 0 0;padding-left:1.2rem}
.explain li{margin:.25rem 0;font-size:.88rem}
.explain table.kv{margin-top:.6rem;background:#fff;border-radius:6px}
.pairs{margin:.2rem 0;padding-left:1.1rem;font-size:.86rem}.pairs li{margin:.15rem 0}
.iter-tabs{display:flex;flex-wrap:wrap;gap:.4rem;margin-bottom:1rem}
.iter-tab{border:1px solid var(--line);background:#fff;padding:.32rem .8rem;border-radius:6px;
font-size:.85rem;cursor:pointer}
.iter-tab:hover{border-color:var(--accent-2)}
.iter-tab.active{background:var(--accent-2);border-color:var(--accent-2);color:#fff}
.iter-panel{display:none}.iter-panel.active{display:block}
.plots{display:flex;flex-wrap:wrap;gap:1rem}
figure{margin:0;flex:1 1 380px;border:1px solid var(--line);border-radius:8px;padding:.6rem;background:#fff}
figcaption{color:var(--muted);font-size:.8rem;margin-bottom:.4rem}
figure img{width:100%;height:auto;border-radius:4px}
code{font:.85em ui-monospace,SFMono-Regular,Menlo,monospace;background:#eef1f6;padding:.05rem .3rem;border-radius:3px}
.files{columns:2;font-size:.85rem;margin:0}.muted{color:var(--muted)}
footer{margin-top:1rem;color:var(--muted);font-size:.82rem}
"""

_JS = """
function showView(name,btn){
  document.querySelectorAll('section.view').forEach(function(s){
    s.classList.toggle('active', s.dataset.view===name);});
  document.querySelectorAll('.view-tab').forEach(function(b){b.classList.remove('active');});
  if(btn)btn.classList.add('active');
  window.scrollTo({top:0,behavior:'instant'});
}
function showIter(it){
  document.querySelectorAll('.iter-panel').forEach(function(p){
    p.classList.toggle('active', p.dataset.iter==String(it));});
  document.querySelectorAll('.iter-tab').forEach(function(b){
    b.classList.toggle('active', b.dataset.iter==String(it));});
}
"""


# ── main render ──────────────────────────────────────────────────────────────────

def _view(name: str, *blocks: str) -> str:
    inner = "".join(blocks)
    active = " active" if name == "Summary" else ""
    return f'<section class="view{active}" data-view="{name}">{inner}</section>'


def _panel(title: str, *blocks: str) -> str:
    body = "".join(blocks)
    head = f"<h2>{_esc(title)}</h2>" if title else ""
    return f'<div class="panel">{head}{body}</div>'


def render_index_html(output_dir: Path) -> str:
    """Build the HTML string for one row output folder."""
    output_dir = Path(output_dir)
    payload = _read_json(output_dir / "report.json")
    if payload is None:
        raise FileNotFoundError(f"report.json not found in {output_dir}")

    params = payload.get("parameters", {})
    instance = payload.get("instance", {})
    facility = payload.get("facility_design", {})
    milp = payload.get("milp", {})
    metric = payload.get("comparison_metric", {})
    mix = payload.get("service_mix", {})
    repair = payload.get("repair", {})
    status = payload.get("status", "")
    policy = payload.get("repair_candidate_policy", "")

    subtitle = (
        f"F_R={_fmt(params.get('F_R'))} · F_A={_fmt(params.get('F_A'))} · "
        f"R={_fmt(params.get('R'))} · Length={_fmt(params.get('Length'))} · "
        f"repair policy={_esc(policy or '—')}"
    )

    instance_tbl = _kv_table([
        ("Row id", payload.get("row_id")),
        ("Instance", payload.get("instance_name")),
        ("Clients", instance.get("n_clients")),
        ("Depots", instance.get("n_depots")),
        ("Vehicle capacity Q", _fmt(instance.get("vehicle_capacity_Q"))),
        ("Open depots", facility.get("open_depots")),
        ("Depot capacities", facility.get("depot_capacities")),
    ])
    milp_tbl = _kv_table([
        ("MILP UB", _fmt(milp.get("UB"))),
        ("MILP LB", _fmt(milp.get("LB"))),
        ("MILP status", milp.get("status")),
        ("MILP gap", _fmt(milp.get("gap"))),
        (f"{metric.get('label', 'metric')}", _fmt(metric.get("value"), 3)),
        ("Metric flags", metric.get("flags") or "none"),
    ])
    mix_tbl = _kv_table([
        ("Clients by routing", mix.get("routing_clients")),
        ("Clients by DA", mix.get("da_clients")),
        ("Routing routes", mix.get("routing_routes")),
        ("Routing demand", _fmt(mix.get("total_routing_demand"))),
        ("DA demand", _fmt(mix.get("total_DA_demand"))),
    ])
    repair_tbl = _kv_table([
        ("Selected candidates", repair.get("selected_count")),
        ("Rejected candidates", repair.get("rejected_count")),
        ("Rejected reasons", repair.get("rejected_reason_counts") or "none"),
        ("Forbidden routing pairs", payload.get("final_forbidden_count")),
    ])

    cost_tbl = _csv_table(_read_csv(output_dir / "cost-breakdown.csv"))
    depot_tbl = _csv_table(_read_csv(output_dir / "depot_usage.csv"))
    itersum_tbl = _csv_table(_read_csv(output_dir / "iteration_summary.csv"), scroll=True)
    trace_tbl = _csv_table(_read_csv(output_dir / "repair_trace.csv"), scroll=True)

    nav = "".join(
        f'<button class="view-tab{" active" if v == "Summary" else ""}" '
        f'onclick="showView(\'{v}\',this)">{v}</button>'
        for v in VIEWS
    )

    views = "".join([
        _view(
            "Summary",
            _panel("Summary", _cards(payload)),
            _panel("", f'<div class="two"><div><h2>Instance &amp; facility design</h2>{instance_tbl}</div>'
                       f'<div><h2>MILP benchmark</h2>{milp_tbl}</div></div>'),
            _panel("Professor's algorithm", _professor_box()),
            _panel("Status meaning", _status_legend(status)),
        ),
        _view(
            "Costs",
            _panel("MILP vs PyVRP cost", cost_tbl),
            _panel("Routing / DA mix", mix_tbl),
        ),
        _view(
            "Capacity",
            _panel("Depot usage", depot_tbl),
            _panel("Repair policy", _repair_policy_box(policy)),
            _panel("Repair summary", repair_tbl),
        ),
        _view(
            "Feasibility",
            _panel("Feasibility checks", _feasibility_table(payload.get("feasibility", {}))),
            _panel("Iteration summary", itersum_tbl),
            _panel("Repair trace", trace_tbl),
        ),
        _view("Iterations", _panel("Per-iteration detail", _iterations_section(output_dir))),
        _view("Plots", _panel("Plots", _final_plots_section(output_dir))),
        _view("Files", _panel("Generated artifacts", _artifact_list(output_dir))),
    ])

    ts = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LoRP-FSD row {_esc(payload.get('row_id'))} — {_esc(payload.get('instance_name'))}</title>
<style>{_CSS}</style></head>
<body>

<header><div class="wrap">
  <h1>LoRP-FSD · PyVRP Benchmark</h1>
  <p class="sub">Row {_esc(payload.get('row_id'))} · {_esc(payload.get('instance_name'))}
     · status <b>{_esc(status)}</b></p>
  <p class="sub">{subtitle}</p>
</div></header>

<nav class="views"><div class="wrap">{nav}</div></nav>

<div class="wrap">
{views}
<footer><p>Generated {_esc(ts)} · static report, no server required.</p></footer>
</div>

<script>{_JS}</script>
</body></html>
"""


def write_index_html(output_dir: Path) -> Path:
    """Render and write ``index.html`` into the row output folder."""
    output_dir = Path(output_dir)
    path = output_dir / "index.html"
    path.write_text(render_index_html(output_dir), encoding="utf-8")
    return path


__all__ = [
    "render_index_html",
    "write_index_html",
    "STATUS_EXPLANATIONS",
    "REPAIR_POLICY_EXPLANATIONS",
    "PROFESSOR_MAPPING",
]
