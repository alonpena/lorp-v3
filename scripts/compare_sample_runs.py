#!/usr/bin/env python
"""Compare two LoRP-FSD consolidated sample outputs."""
from __future__ import annotations

import argparse
import csv
import json
import statistics as stats
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

STATUSES = ["FEASIBLE", "REPAIR_INFEASIBLE", "STUCK_NONCAPACITY_VIOLATION", "MAX_ITERATIONS", "ERROR"]


def _float(row: dict, key: str) -> Optional[float]:
    v = row.get(key, "")
    if v in ("", None):
        return None
    return float(v)


def _int(row: dict, key: str) -> int:
    v = row.get(key, "")
    return int(v) if v not in ("", None) else 0


def _bool(row: dict, key: str) -> bool:
    return str(row.get(key, "")).lower() == "true"


def _load(path: Path) -> List[dict]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _min_mean_max(values: List[float]) -> Dict[str, Optional[float]]:
    if not values:
        return {"min": None, "mean": None, "max": None}
    return {"min": min(values), "mean": sum(values) / len(values), "max": max(values)}


def _summary(rows: List[dict]) -> Dict[str, Any]:
    status_counts = Counter(r.get("status", "") for r in rows)
    gaps = [_float(r, "GAP") for r in rows if r.get("status") == "FEASIBLE" and _float(r, "GAP") is not None]
    metrics = [_float(r, "comparison_metric_value") for r in rows if _float(r, "comparison_metric_value") is not None]
    runtimes = [_float(r, "solve_time_total") for r in rows if r.get("status") != "ERROR" and _float(r, "solve_time_total") is not None]
    iters = [float(_int(r, "iterations")) for r in rows if r.get("status") != "ERROR"]
    return {
        "n_rows": len(rows),
        "status_counts": {s: status_counts.get(s, 0) for s in STATUSES},
        "runtime": _min_mean_max(runtimes),
        "iterations": _min_mean_max(iters),
        "gap_feasible": _min_mean_max([g for g in gaps if g is not None]),
        "comparison_metric": _min_mean_max([m for m in metrics if m is not None]),
        "negative_gap_count": sum(1 for r in rows if _bool(r, "negative_gap_flag")),
        "penalty_distance_suspected_count": sum(1 for r in rows if _bool(r, "penalty_distance_suspected")),
        "rejected_candidates_count": sum(_int(r, "rejected_candidates_count") for r in rows),
        "same_depot_DA_risk_count": sum(_int(r, "same_depot_DA_risk_count") for r in rows),
        "length_unsafe_candidate_count": sum(_int(r, "length_invalid_cut_count") for r in rows),
    }


def _fmt(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        return f"{v:.6g}"
    return str(v)


def _metric_rows(base: Dict[str, Any], safe: Dict[str, Any]) -> List[List[str]]:
    rows: List[List[str]] = []
    for status in STATUSES:
        rows.append([status, base["status_counts"][status], safe["status_counts"][status]])
    for group in ("runtime", "iterations", "gap_feasible", "comparison_metric"):
        for stat in ("min", "mean", "max"):
            rows.append([f"{group}_{stat}", base[group][stat], safe[group][stat]])
    for key in (
        "negative_gap_count",
        "penalty_distance_suspected_count",
        "rejected_candidates_count",
        "same_depot_DA_risk_count",
        "length_unsafe_candidate_count",
    ):
        rows.append([key, base[key], safe[key]])
    return rows


def _changed_rows(base_rows: List[dict], safe_rows: List[dict]) -> List[dict]:
    by_base = {r.get("row_id"): r for r in base_rows}
    by_safe = {r.get("row_id"): r for r in safe_rows}
    changed = []
    for row_id in sorted(set(by_base) & set(by_safe), key=lambda x: int(x)):
        b, s = by_base[row_id], by_safe[row_id]
        if b.get("status") != s.get("status"):
            changed.append({
                "row_id": row_id,
                "instance": b.get("instance") or s.get("instance"),
                "baseline_status": b.get("status"),
                "safe_both_status": s.get("status"),
                "baseline_rejected": b.get("rejected_candidates_count"),
                "safe_rejected": s.get("rejected_candidates_count"),
                "baseline_length_unsafe": b.get("length_invalid_cut_count"),
                "safe_length_unsafe": s.get("length_invalid_cut_count"),
                "baseline_same_depot_DA_risk": b.get("same_depot_DA_risk_count"),
                "safe_same_depot_DA_risk": s.get("same_depot_DA_risk_count"),
            })
    return changed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("baseline_csv")
    parser.add_argument("safe_csv")
    parser.add_argument("--out", default="outputs/phase7a_sample_comparison.json")
    parser.add_argument("--md", default="outputs/phase7a_sample_comparison.md")
    args = parser.parse_args()

    baseline_rows = _load(Path(args.baseline_csv))
    safe_rows = _load(Path(args.safe_csv))
    baseline = _summary(baseline_rows)
    safe = _summary(safe_rows)
    changed = _changed_rows(baseline_rows, safe_rows)

    result = {"baseline": baseline, "safe_both": safe, "changed_rows": changed}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")

    lines = ["# Phase 7A Sample Comparison\n", "| Metric | baseline | safe_both |", "|---|---:|---:|"]
    for name, b, s in _metric_rows(baseline, safe):
        lines.append(f"| {name} | {_fmt(b)} | {_fmt(s)} |")
    lines.append("\n## Rows with changed status\n")
    if changed:
        lines.append("| row_id | instance | baseline | safe_both | baseline rejected | safe rejected |")
        lines.append("|---:|---|---|---|---:|---:|")
        for r in changed:
            lines.append(
                f"| {r['row_id']} | {r['instance']} | {r['baseline_status']} | {r['safe_both_status']} | "
                f"{r['baseline_rejected']} | {r['safe_rejected']} |"
            )
    else:
        lines.append("No status changes.\n")
    Path(args.md).write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(Path(args.out))
    print(Path(args.md))
    for name, b, s in _metric_rows(baseline, safe):
        print(f"{name}: baseline={_fmt(b)} safe_both={_fmt(s)}")
    if changed:
        print("changed rows:")
        for r in changed:
            print(f"  row {r['row_id']} {r['instance']}: {r['baseline_status']} -> {r['safe_both_status']}")


if __name__ == "__main__":
    main()
