#!/usr/bin/env python
"""Generate a static index.html for one row output folder (Phase 8).

Pure reader: consumes the artifacts already in the folder (report.json, CSVs,
PNGs) and writes a single self-contained index.html. Does not run the solver.

Usage:
    python scripts/make_row_html.py --dir outputs/<run_id>/<instance_name>
    python scripts/make_row_html.py --run-id html_demo_row0   # resolves the
        single instance subfolder under outputs/<run_id>/
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lorp_fsd.html_report import write_index_html  # noqa: E402


def _resolve_dir(args) -> Path:
    if args.dir:
        return Path(args.dir)
    run_root = Path(args.output_root) / args.run_id
    subdirs = [p for p in run_root.iterdir() if p.is_dir()] if run_root.exists() else []
    instance_dirs = [p for p in subdirs if (p / "report.json").exists()]
    if len(instance_dirs) == 1:
        return instance_dirs[0]
    if not instance_dirs:
        raise SystemExit(f"no instance folder with report.json under {run_root}")
    raise SystemExit(
        f"multiple instance folders under {run_root}; pass --dir explicitly:\n  "
        + "\n  ".join(str(p) for p in instance_dirs)
    )


def main() -> int:
    p = argparse.ArgumentParser(description="Generate static index.html for one row output folder.")
    p.add_argument("--dir", help="path to outputs/<run_id>/<instance_name>")
    p.add_argument("--run-id", help="run id under --output-root (single-instance runs)")
    p.add_argument("--output-root", default=str(ROOT / "outputs"))
    args = p.parse_args()
    if not args.dir and not args.run_id:
        p.error("pass --dir or --run-id")

    output_dir = _resolve_dir(args)
    path = write_index_html(output_dir)
    print(f"wrote {path}")
    print(f"open  file://{path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
