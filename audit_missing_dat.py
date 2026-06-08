from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from instance_resolver import resolve_instance_path
from xlsx_loader import load_lorp_fsd_mapping


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Audit LoRP-FSD Excel rows against available .dat files.")
    p.add_argument("--excel", default="results_MILP.xlsx")
    p.add_argument("--instance-folder", default="instances")
    p.add_argument("--out-missing", default="pipeline_out/missing_dat_rows.csv")
    p.add_argument("--out-summary", default="pipeline_out/dat_audit_summary.csv")
    p.add_argument("--out-unreferenced", default="pipeline_out/unreferenced_dat_files.csv")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    inst_dir = Path(args.instance_folder)
    Path(args.out_missing).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_summary).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_unreferenced).parent.mkdir(parents=True, exist_ok=True)

    # Load all LoRP-FSD rows. Do NOT pass instance_folder because that filters missing files out.
    df_all = load_lorp_fsd_mapping(args.excel, instance_folder=None)
    resolutions = df_all["instance"].map(lambda x: resolve_instance_path(str(x), inst_dir))
    df_all["resolution_status"] = resolutions.map(lambda r: r.status)
    df_all["resolved_dat_path"] = resolutions.map(lambda r: str(r.path) if r.path else None)
    df_all["resolution_candidates"] = resolutions.map(lambda r: " | ".join(str(p) for p in r.candidates))
    df_all["dat_exists"] = resolutions.map(lambda r: r.ok)

    missing = df_all[~df_all["dat_exists"]].copy()
    present = df_all[df_all["dat_exists"]].copy()

    dat_files = sorted(p.name for p in inst_dir.glob("*.dat"))
    referenced = set(df_all["instance"].astype(str))
    unreferenced = sorted(set(dat_files) - referenced)

    missing_cols = [
        "row_id", "instance", "resolution_status", "resolved_dat_path", "resolution_candidates", "R", "F_R", "F_A", "Length", "UB", "status",
        "cost_depots", "vehicle_cost_milp", "routing_cost_milp", "da_cost_milp",
    ]
    missing[missing_cols].to_csv(args.out_missing, index=False)

    used_paths = set(Path(p).name for p in present["resolved_dat_path"].dropna())
    unreferenced = sorted(set(dat_files) - used_paths)

    pd.DataFrame({"instance": unreferenced, "dat_path": [str(inst_dir / x) for x in unreferenced]}).to_csv(
        args.out_unreferenced, index=False
    )

    by_instance = (
        df_all.groupby("instance", dropna=False)
        .agg(
            n_rows=("row_id", "count"),
            first_row_id=("row_id", "min"),
            dat_exists=("dat_exists", "max"),
        )
        .reset_index()
        .sort_values(["dat_exists", "instance"], ascending=[True, True])
    )

    summary_rows = [
        {"metric": "excel_rows_total", "value": len(df_all)},
        {"metric": "excel_rows_with_dat", "value": len(present)},
        {"metric": "excel_rows_missing_dat", "value": len(missing)},
        {"metric": "unique_instances_referenced", "value": df_all["instance"].nunique()},
        {"metric": "unique_instances_with_dat", "value": present["instance"].nunique()},
        {"metric": "unique_instances_missing_dat", "value": missing["instance"].nunique()},
        {"metric": "dat_files_in_folder", "value": len(dat_files)},
        {"metric": "dat_files_unreferenced_by_excel", "value": len(unreferenced)},
    ]
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(args.out_summary, index=False)

    print("DAT AUDIT")
    print("=========")
    print(f"Excel rows total             : {len(df_all)}")
    print(f"Rows with .dat               : {len(present)}")
    print(f"Rows missing .dat            : {len(missing)}")
    print(f"Unique instances referenced  : {df_all['instance'].nunique()}")
    print(f"Unique instances with .dat   : {present['instance'].nunique()}")
    print(f"Unique instances missing .dat: {missing['instance'].nunique()}")
    print(f".dat files in folder         : {len(dat_files)}")
    print(f".dat files unreferenced      : {len(unreferenced)}")
    print()
    print(f"Missing rows CSV             : {args.out_missing}")
    print(f"Summary CSV                  : {args.out_summary}")
    print(f"Unreferenced .dat CSV        : {args.out_unreferenced}")

    if len(missing):
        print("\nMissing instances:")
        print(
            missing.groupby("instance")
            .agg(n_rows=("row_id", "count"), first_row_id=("row_id", "min"))
            .reset_index()
            .sort_values("instance")
            .to_string(index=False)
        )


if __name__ == "__main__":
    main()
