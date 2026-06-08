#!/usr/bin/env python
"""Component-level comparison of PyVRP vs MILP from a consolidated CSV.

Usage::

    .venv/bin/python scripts/compare_with_milp.py outputs/first10/consolidated.csv

Prints a per-row and per-component comparison table and summary delta statistics.
"""

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


def main():
    parser = argparse.ArgumentParser(description="Compare PyVRP vs MILP objective components.")
    parser.add_argument("csv_path", help="Path to consolidated CSV from batch runner")
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    args = parser.parse_args()

    with open(args.csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        print("No rows in CSV.")
        return

    def _f(v):
        try:
            return float(v) if v not in (None, "", "None") else None
        except (ValueError, TypeError):
            return None

    # Build comparison table.
    components = [
        ("routing", "cost_routing_pyvrp", "cost_routing_milp"),
        ("da", "cost_da_pyvrp", "cost_da_milp"),
        ("vehicle", "cost_vehicle_pyvrp", "cost_vehicle_milp"),
        ("depot", "cost_depot_pyvrp", "cost_depot_milp"),
    ]

    lines = []
    header = (
        f"{'row':>5} {'instance':<20} {'status':<28} "
        f"{'Z_PyVRP':>10} {'UB_MILP':>10} {'metric':>10} "
        f"{'Δrouting':>10} {'Δda':>10} {'Δvehicle':>10} {'Δdepot':>10}"
    )
    lines.append(header)
    lines.append("-" * len(header))

    deltas_by_component = {name: [] for name, _, _ in components}
    total_deltas = []

    for row in rows:
        if row.get("status") == "ERROR":
            lines.append(f"{row.get('row_id', '?'):>5} {row.get('instance', '?'):<20} {'ERROR':<28}")
            continue

        z = _f(row.get("Z_PyVRP"))
        ub = _f(row.get("UB_MILP"))
        metric_val = _f(row.get("comparison_metric_value"))

        delta_parts = []
        for name, pyvrp_col, milp_col in components:
            p = _f(row.get(pyvrp_col))
            m = _f(row.get(milp_col))
            if p is not None and m is not None:
                d = p - m
                delta_parts.append(f"{d:>10.3f}")
                deltas_by_component[name].append(d)
            else:
                delta_parts.append(f"{'N/A':>10}")

        if z is not None and ub is not None:
            total_deltas.append(z - ub)

        lines.append(
            f"{row.get('row_id', '?'):>5} {row.get('instance', '?'):<20} {row.get('status', '?'):<28} "
            f"{z or 0:>10.3f} {ub or 0:>10.3f} {metric_val or 0:>10.6f} "
            f"{'  '.join(delta_parts)}"
        )

    lines.append("")
    lines.append("=" * 60)
    lines.append("Component Delta Summary (PyVRP − MILP)")
    lines.append("=" * 60)
    lines.append(f"{'Component':<12} {'Count':>6} {'Mean':>10} {'Min':>10} {'Max':>10}")
    lines.append("-" * 50)
    for name, _, _ in components:
        vals = deltas_by_component[name]
        if vals:
            lines.append(
                f"{name:<12} {len(vals):>6} {sum(vals)/len(vals):>10.4f} "
                f"{min(vals):>10.4f} {max(vals):>10.4f}"
            )
        else:
            lines.append(f"{name:<12} {'N/A':>6}")

    if total_deltas:
        lines.append(
            f"{'TOTAL':<12} {len(total_deltas):>6} {sum(total_deltas)/len(total_deltas):>10.4f} "
            f"{min(total_deltas):>10.4f} {max(total_deltas):>10.4f}"
        )

    output = "\n".join(lines) + "\n"

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Written to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
