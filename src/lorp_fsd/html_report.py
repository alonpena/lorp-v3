"""Static HTML row report (Phase 8).

Reads the artifacts already produced by the row runner inside one output
folder and emits a single self-contained ``index.html`` file:

    outputs/<run_id>/<instance_name>/report.json
    outputs/<run_id>/<instance_name>/cost-breakdown.csv
    outputs/<run_id>/<instance_name>/depot_usage.csv
    outputs/<run_id>/<instance_name>/iteration_summary.csv
    outputs/<run_id>/<instance_name>/repair_trace.csv
    outputs/<run_id>/<instance_name>/iteration_XX_instance.png
    outputs/<run_id>/<instance_name>/iteration_XX_solution.png
        -> outputs/<run_id>/<instance_name>/index.html

This module is a pure reader. It does NOT touch the solver, repair, cost
reconstruction, or any runner logic. It only renders existing files, so it can
be regenerated at any time and run on historical output folders.

The output is HTML-first and academic: white background, dark text, subtle
blue/gray accents, no external CDN, no JavaScript, plots embedded as base64 so
the single file is portable.
"""

from __future__ import annotations

import base64
import csv
import datetime as _dt
import html
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

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

_STATUS_CLASS = {
    "FEASIBLE": "ok",
    "REPAIR_INFEASIBLE": "bad",
    "STUCK_NONCAPACITY_VIOLATION": "bad",
    "MAX_ITERATIONS": "warn",
    "TIMEOUT": "warn",
    "ERROR": "bad",
}

_ITER_RE = re.compile(r"iteration_(\d+)_(instance|solution)\.png$")


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


def _img_data_uri(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    raw = path.read_bytes()
    return "data:image/png;base64," + base64.b64encode(raw).decode("ascii")


def _pick_plots(output_dir: Path) -> Dict[str, Optional[Path]]:
    """Lowest-iteration instance plot and highest-iteration solution plot."""
    instances: Dict[int, Path] = {}
    solutions: Dict[int, Path] = {}
    for p in sorted(output_dir.glob("iteration_*_*.png")):
        m = _ITER_RE.search(p.name)
        if not m:
            continue
        it = int(m.group(1))
        (instances if m.group(2) == "instance" else solutions)[it] = p
    return {
        "instance": instances[min(instances)] if instances else None,
        "solution": solutions[max(solutions)] if solutions else None,
    }


# ── table / section builders ──────────────────────────────────────────────────

def _kv_table(rows: List[tuple]) -> str:
    body = "".join(
        f"<tr><th>{_esc(k)}</th><td>{_esc(v)}</td></tr>" for k, v in rows
    )
    return f'<table class="kv">{body}</table>'


def _csv_table(rows: List[List[str]], *, numeric_from: int = 1) -> str:
    if not rows:
        return '<p class="muted">No data.</p>'
    head, *body = rows
    ths = "".join(f"<th>{_esc(c)}</th>" for c in head)
    trs = []
    for r in body:
        tds = "".join(
            f'<td class="{"num" if i >= numeric_from else ""}">{_esc(c)}</td>'
            for i, c in enumerate(r)
        )
        trs.append(f"<tr>{tds}</tr>")
    return f'<table class="grid"><thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table>'


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


def _explanation_box(status: str) -> str:
    items = "".join(
        f"<li><b>{_esc(k)}</b> — {_esc(v)}</li>"
        for k, v in STATUS_EXPLANATIONS.items()
    )
    note = STATUS_EXPLANATIONS.get(status)
    cur = (
        f'<p class="cur">This row is <b>{_esc(status)}</b>: {_esc(note)}</p>'
        if note
        else ""
    )
    return f'<div class="explain">{cur}<ul>{items}</ul></div>'


def _plots_section(output_dir: Path) -> str:
    plots = _pick_plots(output_dir)
    blocks = []
    for label, path in (("Basal instance", plots["instance"]), ("Combined solution", plots["solution"])):
        if path is None:
            continue
        uri = _img_data_uri(path)
        if uri is None:
            continue
        blocks.append(
            f'<figure><figcaption>{_esc(label)} — '
            f'<code>{_esc(path.name)}</code></figcaption>'
            f'<img alt="{_esc(label)}" src="{uri}"></figure>'
        )
    if not blocks:
        return '<p class="muted">No plots found in this folder.</p>'
    return f'<div class="plots">{"".join(blocks)}</div>'


def _artifact_list(output_dir: Path) -> str:
    names = [
        "report.json", "report.md", "cost-breakdown.csv", "depot_usage.csv",
        "iteration_summary.csv", "repair_trace.csv",
    ]
    names += sorted(p.name for p in output_dir.glob("iteration_*.png"))
    names += sorted(p.name for p in output_dir.glob("iteration_*_audit.json"))
    items = []
    for n in names:
        present = (output_dir / n).exists()
        cls = "" if present else " class='muted'"
        mark = "" if present else " (missing)"
        items.append(f"<li{cls}><code>{_esc(n)}</code>{mark}</li>")
    return f"<ul class='files'>{''.join(items)}</ul>"


# ── CSS (embedded, no CDN) ─────────────────────────────────────────────────────

_CSS = """
:root{--ink:#1f2933;--muted:#6b7280;--line:#e2e8f0;--accent:#2c5282;
--accent-bg:#ebf2f9;--ok:#1f7a4d;--ok-bg:#e6f4ec;--bad:#9b2c2c;--bad-bg:#fbeaea;
--warn:#8a6d1f;--warn-bg:#fbf4e0;}
*{box-sizing:border-box}
body{font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
color:var(--ink);background:#fff;margin:0;padding:0 0 4rem}
.wrap{max-width:980px;margin:0 auto;padding:2rem 1.5rem}
header{border-bottom:2px solid var(--accent);padding-bottom:1rem;margin-bottom:1.5rem}
h1{font-size:1.5rem;margin:0 0 .25rem;color:var(--accent)}
.sub{color:var(--muted);font-size:.92rem;margin:.15rem 0}
h2{font-size:1.1rem;margin:2rem 0 .6rem;padding-bottom:.3rem;border-bottom:1px solid var(--line);color:var(--accent)}
.cards{display:flex;flex-wrap:wrap;gap:.75rem;margin:1rem 0}
.card{flex:1 1 140px;border:1px solid var(--line);border-radius:8px;padding:.8rem 1rem;background:#fbfcfe}
.card-val{font-size:1.35rem;font-weight:600}
.card-lab{color:var(--muted);font-size:.8rem;text-transform:uppercase;letter-spacing:.03em}
.status-ok{background:var(--ok-bg);border-color:#bfe3cd}.status-ok .card-val{color:var(--ok)}
.status-bad{background:var(--bad-bg);border-color:#f0c9c9}.status-bad .card-val{color:var(--bad)}
.status-warn{background:var(--warn-bg);border-color:#ecdca6}.status-warn .card-val{color:var(--warn)}
table{border-collapse:collapse;width:100%;margin:.4rem 0 .8rem;font-size:.9rem}
table.kv th{text-align:left;width:40%;color:var(--muted);font-weight:500;vertical-align:top}
table.kv th,table.kv td{padding:.35rem .5rem;border-bottom:1px solid var(--line)}
table.grid th{background:var(--accent-bg);color:var(--accent);text-align:left;font-weight:600}
table.grid th,table.grid td{padding:.4rem .6rem;border:1px solid var(--line)}
table.grid tbody tr:nth-child(even){background:#f8fafc}
td.num{text-align:right;font-variant-numeric:tabular-nums}
.pill{display:inline-block;padding:.1rem .5rem;border-radius:99px;font-size:.78rem;font-weight:600}
.pill.ok{background:var(--ok-bg);color:var(--ok)}.pill.bad{background:var(--bad-bg);color:var(--bad)}
.two{display:flex;flex-wrap:wrap;gap:1.5rem}.two>div{flex:1 1 320px}
.explain{background:var(--accent-bg);border:1px solid #cfe0f3;border-radius:8px;padding:1rem 1.2rem}
.explain .cur{margin:0 0 .6rem}.explain ul{margin:.3rem 0 0;padding-left:1.1rem}
.explain li{margin:.2rem 0;font-size:.88rem}
.plots{display:flex;flex-wrap:wrap;gap:1rem}
figure{margin:0;flex:1 1 380px;border:1px solid var(--line);border-radius:8px;padding:.6rem;background:#fff}
figcaption{color:var(--muted);font-size:.82rem;margin-bottom:.4rem}
figure img{width:100%;height:auto;border-radius:4px}
code{font:.85em ui-monospace,SFMono-Regular,Menlo,monospace;background:#f1f5f9;padding:.05rem .3rem;border-radius:3px}
.files{columns:2;font-size:.85rem}.muted{color:var(--muted)}
footer{margin-top:2.5rem;border-top:1px solid var(--line);padding-top:1rem;color:var(--muted);font-size:.82rem}
"""


# ── main render ────────────────────────────────────────────────────────────────

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

    subtitle = (
        f"F_R={_fmt(params.get('F_R'))} · F_A={_fmt(params.get('F_A'))} · "
        f"R={_fmt(params.get('R'))} · Length={_fmt(params.get('Length'))} · "
        f"repair policy={_esc(payload.get('repair_candidate_policy', '—'))}"
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
    itersum_tbl = _csv_table(_read_csv(output_dir / "iteration_summary.csv"))
    trace_tbl = _csv_table(_read_csv(output_dir / "repair_trace.csv"))

    ts = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LoRP-FSD row {_esc(payload.get('row_id'))} — {_esc(payload.get('instance_name'))}</title>
<style>{_CSS}</style></head>
<body><div class="wrap">

<header>
  <h1>LoRP-FSD · PyVRP Benchmark</h1>
  <p class="sub">Row {_esc(payload.get('row_id'))} · {_esc(payload.get('instance_name'))}
     · status <b>{_esc(status)}</b></p>
  <p class="sub">{subtitle}</p>
</header>

<h2>Summary</h2>
{_cards(payload)}

<div class="two">
  <div><h2>Instance &amp; facility design</h2>{instance_tbl}</div>
  <div><h2>MILP benchmark</h2>{milp_tbl}</div>
</div>

<h2>MILP vs PyVRP cost</h2>
{cost_tbl}

<h2>Depot usage</h2>
{depot_tbl}

<div class="two">
  <div><h2>Routing / DA mix</h2>{mix_tbl}</div>
  <div><h2>Feasibility checks</h2>{_feasibility_table(payload.get('feasibility', {}))}</div>
</div>

<h2>Repair summary</h2>
{repair_tbl}

<h2>Iteration summary</h2>
{itersum_tbl}

<h2>Repair trace</h2>
{trace_tbl}

<h2>Plots</h2>
{_plots_section(output_dir)}

<h2>Status meaning</h2>
{_explanation_box(status)}

<footer>
  <p>Generated artifacts:</p>
  {_artifact_list(output_dir)}
  <p>Generated {_esc(ts)} · static report, no server required.</p>
</footer>

</div></body></html>
"""


def write_index_html(output_dir: Path) -> Path:
    """Render and write ``index.html`` into the row output folder."""
    output_dir = Path(output_dir)
    path = output_dir / "index.html"
    path.write_text(render_index_html(output_dir), encoding="utf-8")
    return path


__all__ = ["render_index_html", "write_index_html", "STATUS_EXPLANATIONS"]
