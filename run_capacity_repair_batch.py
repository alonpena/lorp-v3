"""Endogenous-DA capacity-repair runner.

Iterative loop:
    Iter 0: solve with empty exclusions (relaxed: solver picks DA-vs-routing mix).
    Audit: per-depot routing+DA demand vs real capacity.
    If violated: rank routing clients by savings delta Δ = d_ij + d_jk - d_ik,
                 select exclusions per overloaded depot until excess covered,
                 add to exclusion set and re-solve.

Final status:
    OK                          feasible + capacity ok + no missing clients
    PYVRP_INFEASIBLE            capacity ok but PyVRP best is infeasible
    MISSING_CLIENTS             some clients absent from all routes
    MAX_ITERS_CAPACITY_VIOLATED still violated after max_iters
    NOT_REPAIRABLE              audit violated but no new exclusions found
    MISSING_DAT / AMBIGUOUS_DAT instance file resolution failed

Outputs (under --out-dir):
    results.csv, convergence.csv, repairs.csv,
    depot_audit.csv, routes.csv, da_pool_stats.csv

Limitations:
- PyVRP cannot enforce shared depot capacity between DA and routing.
- DA candidate pool is a one-shot capacity-feasibility filter per depot.
- Repair only removes routing arcs (no DA candidate removal yet).
- Real capacity enforced ex post by audit + repair loop.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import pandas as pd

from capacity_audit import audit_capacity, extract_routes, find_unserved_clients
from capacity_repair import (
    merge_exclusions,
    rank_overloaded_routing_candidates,
    select_routing_exclusions,
)
from dat_loader import load_dat
from instance_adapter import adapt_instance, spec_from_row
from instance_resolver import resolve_instance_path
from pyvrp_model import build_endogenous_da_model, solve_multi_run
from xlsx_loader import load_lorp_fsd_mapping


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Endogenous-DA capacity-repair runner.")
    p.add_argument("--excel", default="results_MILP.xlsx")
    p.add_argument("--instance-folder", default="instances")
    p.add_argument("--out-dir", default="pipeline_out/capacity_repair")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--sample-random", type=int, default=None,
                   help="Sample N Excel rows reproducibly before running. Does not affect --limit behavior.")
    p.add_argument("--random-seed", type=int, default=42,
                   help="Seed for --sample-random.")
    p.add_argument("--runtime", type=int, default=30)
    p.add_argument("--runs", type=int, default=5)
    p.add_argument("--max-iters", type=int, default=20)
    p.add_argument("--encode-cost-factors", action="store_true",
                   help="Encode F_R/F_A into PyVRP edge costs (weighted objective).")
    return p.parse_args()


def _fmt_exclusions(ex: Set[Tuple[int, int]]) -> str:
    if not ex:
        return "{}"
    parts = sorted(ex)
    if len(parts) > 8:
        head = ", ".join(f"(d{d},c{c})" for d, c in parts[:8])
        return f"{{{head}, ... total={len(parts)}}}"
    return "{" + ", ".join(f"(d{d},c{c})" for d, c in parts) + "}"


def _overloaded_depots_str(audit: Dict[str, Any]) -> str:
    over = [did for did, info in audit["by_depot"].items() if info["violated"]]
    return ",".join(str(d) for d in sorted(over)) if over else ""


def _per_depot_aggregates(inst, route_records: List[Dict[str, Any]]) -> Dict[int, Dict[str, float]]:
    agg: Dict[int, Dict[str, float]] = {}
    for did in inst.depots:
        agg[did] = {
            "routing_distance_scaled": 0.0,
            "da_distance_scaled": 0.0,
            "n_veh_routing": 0,
            "n_veh_da": 0,
        }
    for rec in route_records:
        did = rec["depot_id"]
        if did not in agg:
            continue
        if rec["kind"] == "routing":
            agg[did]["routing_distance_scaled"] += rec["distance_scaled"]
            agg[did]["n_veh_routing"] += 1
        else:
            agg[did]["da_distance_scaled"] += rec["distance_scaled"]
            agg[did]["n_veh_da"] += 1
    return agg


def build_capacity_repair_report(
    inst,
    config,
    route_records: List[Dict[str, Any]],
    audit: Dict[str, Any],
    info: Dict[str, Any],
    best_res,
) -> Dict[str, Any]:
    """Build a flat report dict from unweighted scaled distances.

    F_R/F_A applied ex post regardless of objective mode, so costs are
    directly comparable to the MILP / old pipeline.
    """
    F_R = float(info.get("F_R", inst.data.get("F_R", 1.0)))
    F_A = float(info.get("F_A", inst.data.get("F_A", 1.0)))

    routing_dist = sum(r["distance_scaled"] for r in route_records if r["kind"] == "routing")
    da_dist = sum(r["distance_scaled"] for r in route_records if r["kind"] == "direct_allocation")
    n_veh_routing = sum(1 for r in route_records if r["kind"] == "routing")
    n_veh_da = sum(1 for r in route_records if r["kind"] == "direct_allocation")

    veh_fixed_cost = float(inst.data["veh_fixed_cost"])
    costo_routing = routing_dist * F_R
    costo_da = da_dist * F_A
    costo_vehiculos = n_veh_routing * veh_fixed_cost
    costo_depositos = float(config.cost_depots)
    costo_total = costo_routing + costo_da + costo_vehiculos + costo_depositos

    ub_milp = float(config.UB)
    raw_gap = (costo_total - ub_milp) / ub_milp if ub_milp > 0 else None
    abs_gap = abs(raw_gap) if raw_gap is not None else None
    gap_distance_flag = (
        "OK_RANGE" if abs_gap is not None and abs_gap <= 0.20
        else ("TOO_FAR" if abs_gap is not None else None)
    )

    total_demand = float(sum(c["demand"] for c in inst.clients.values()))
    served = float(sum(r["demand"] for r in route_records))
    service_level = served / total_demand if total_demand > 0 else 0.0

    report = {
        "costo_routing_pyvrp": costo_routing,
        "costo_da_pyvrp": costo_da,
        "costo_vehiculos_pyvrp": costo_vehiculos,
        "costo_depositos": costo_depositos,
        "costo_total_pyvrp": costo_total,
        "routing_distance_scaled": routing_dist,
        "da_distance_scaled": da_dist,
        "n_veh_routing": n_veh_routing,
        "n_veh_da": n_veh_da,
        "total_demand": total_demand,
        "served_demand": served,
        "service_level": service_level,
        "milp_ub": ub_milp,
        "ub_milp": ub_milp,
        "ub_pyvrp": costo_total,
        "raw_gap_pyvrp_minus_milp": raw_gap,
        "abs_gap_pyvrp_vs_milp": abs_gap,
        "gap_percent": abs_gap * 100.0 if abs_gap is not None else None,
        "gap_distance_flag": gap_distance_flag,
    }
    return report


def _convergence_row_skeleton(config, info: Dict[str, Any], iteration: int, seed: int,
                              best_obj: float, audit: Dict[str, Any], report: Dict[str, Any],
                              missing_count: int, n_before: int, run_record: Dict[str, Any]
                              ) -> Dict[str, Any]:
    return {
        "row_id": config.row_id,
        "instance": config.instance,
        "iteration": iteration,
        "seed": seed,
        "objective_mode": info.get("objective_mode"),
        "encode_cost_factors": info.get("encode_cost_factors"),
        "objective_scaled": run_record["objective_scaled"],
        "feasible": run_record["feasible"],
        "n_routes": run_record["n_routes"],
        "best_objective_scaled": best_obj,
        "pyvrp_feasible": run_record["feasible"],
        "post_total_cost": report["costo_total_pyvrp"],
        "routing_distance_scaled": report["routing_distance_scaled"],
        "da_distance_scaled": report["da_distance_scaled"],
        "costo_routing_pyvrp": report["costo_routing_pyvrp"],
        "costo_da_pyvrp": report["costo_da_pyvrp"],
        "costo_vehiculos_pyvrp": report["costo_vehiculos_pyvrp"],
        "costo_depositos": report["costo_depositos"],
        "milp_ub": report["milp_ub"],
        "raw_gap_pyvrp_minus_milp": report["raw_gap_pyvrp_minus_milp"],
        "capacity_violated": audit["violated"],
        "max_excess": audit["max_excess"],
        "overloaded_depots": _overloaded_depots_str(audit),
        "n_exclusions_before": n_before,
        "n_exclusions_added": 0,
        "n_exclusions_after": n_before,
        "missing_clients": missing_count,
    }


def run_one(
    row,
    instance_folder: Path,
    args,
    convergence_rows: List[Dict[str, Any]],
    repair_rows: List[Dict[str, Any]],
    depot_audit_rows: List[Dict[str, Any]],
    route_rows: List[Dict[str, Any]],
    da_pool_rows: List[Dict[str, Any]],
) -> Dict[str, Any]:
    t0 = time.perf_counter()
    config = spec_from_row(row)

    print(f"\nROW {config.row_id} {config.instance}  R={config.R}  "
          f"F_R={config.F_R}  F_A={config.F_A}  Length={config.Length}  "
          f"encode_cost_factors={args.encode_cost_factors}")

    base_record: Dict[str, Any] = {
        "row_id": config.row_id,
        "instance": config.instance,
    }

    resolution = resolve_instance_path(config.instance, instance_folder)
    if not resolution.ok:
        print(f"  [skip] resolution status={resolution.status}")
        base_record.update({
            "status": resolution.status,
            "final_iteration": -1,
            "pyvrp_feasible_final": None,
            "pyvrp_objective_scaled_final": None,
            "objective_mode": None,
            "encode_cost_factors": args.encode_cost_factors,
            "milp_ub": config.UB,
            "ub_milp": config.UB,
            "ub_pyvrp": None,
            "raw_gap_pyvrp_minus_milp": None,
            "abs_gap_pyvrp_vs_milp": None,
            "gap_percent": None,
            "gap_distance_flag": None,
            "costo_routing_pyvrp": None,
            "costo_da_pyvrp": None,
            "costo_vehiculos_pyvrp": None,
            "costo_depositos": None,
            "costo_total_pyvrp": None,
            "routing_distance_scaled": None,
            "da_distance_scaled": None,
            "n_veh_routing": None,
            "n_veh_da": None,
            "total_demand": None,
            "served_demand": None,
            "service_level": None,
            "capacity_violated_final": None,
            "max_excess_final": None,
            "n_exclusions_total": 0,
            "missing_clients_final": None,
            "runtime_seconds": time.perf_counter() - t0,
        })
        return base_record

    base = load_dat(resolution.path)
    inst = adapt_instance(base, config)

    excluded: Set[Tuple[int, int]] = set()
    final_iteration = 0
    status = "MAX_ITERS_CAPACITY_VIOLATED"
    last_audit: Dict[str, Any] = {}
    last_report: Dict[str, Any] = {}
    last_missing: Set[int] = set()
    last_info: Dict[str, Any] = {}
    last_best_res = None

    for iteration in range(args.max_iters):
        final_iteration = iteration
        n_before = len(excluded)
        print(f"  ITER {iteration}  excluded={n_before}  {_fmt_exclusions(excluded)}")

        model, info = build_endogenous_da_model(
            inst,
            excluded_routing_pairs=excluded,
            encode_cost_factors=args.encode_cost_factors,
        )
        last_info = info

        sel = sum(s["selected_demand"] for s in info["da_pool_stats"].values())
        scale = info["escala"]
        rad_scaled = float(inst.data["R"])
        rad_raw = rad_scaled / scale if scale > 0 else rad_scaled
        print(f"    objective_mode={info['objective_mode']}  scale={scale:.6f}  "
              f"R_scaled={rad_scaled}  R_raw_equiv={rad_raw:.3f}  "
              f"Length={inst.data['Length']}")
        print(f"    DA pool selected demand total = {sel:.1f}")

        best_res, run_records = solve_multi_run(model, runtime=args.runtime, n_runs=args.runs)
        last_best_res = best_res
        best_obj = float(best_res.best.distance())
        pyvrp_feasible = bool(best_res.best.is_feasible())
        print(f"    Solve best objective = {best_obj:.2f}  feasible={pyvrp_feasible}  "
              f"n_routes={len(best_res.best.routes())}")

        routes = extract_routes(inst, best_res, info)
        audit = audit_capacity(inst, routes)
        missing = find_unserved_clients(inst, routes)
        report = build_capacity_repair_report(inst, config, routes, audit, info, best_res)

        last_audit = audit
        last_report = report
        last_missing = missing

        gap_str = (f"{report['raw_gap_pyvrp_minus_milp']:.4%}"
                   if report["raw_gap_pyvrp_minus_milp"] is not None else "-")
        print(f"    Costs: routing={report['costo_routing_pyvrp']:.2f}  "
              f"DA={report['costo_da_pyvrp']:.2f}  "
              f"vehicles={report['costo_vehiculos_pyvrp']:.2f}  "
              f"depots={report['costo_depositos']:.2f}  "
              f"total={report['costo_total_pyvrp']:.2f}  "
              f"MILP UB={report['milp_ub']:.2f}  raw_gap={gap_str}")

        for did, dinfo in audit["by_depot"].items():
            flag = "VIOL" if dinfo["violated"] else "ok"
            print(f"    Audit d{did} total={dinfo['total_demand']:.1f} "
                  f"(rt={dinfo['routing_demand']:.1f} da={dinfo['da_demand']:.1f}) "
                  f"cap={dinfo['capacity']:.1f} excess={dinfo['excess']:.1f}  [{flag}]")
        if missing:
            print(f"    WARNING: missing clients = {sorted(missing)}")

        # Convergence rows (one per seed for this iteration)
        for rr in run_records:
            convergence_rows.append(_convergence_row_skeleton(
                config, info, iteration, rr["seed"], best_obj, audit, report,
                len(missing), n_before, rr,
            ))

        # Depot audit rows + per-depot route aggregates
        agg = _per_depot_aggregates(inst, routes)
        for did, dinfo in audit["by_depot"].items():
            depot_audit_rows.append({
                "row_id": config.row_id,
                "instance": config.instance,
                "iteration": iteration,
                "depot_id": did,
                "capacity": dinfo["capacity"],
                "routing_demand": dinfo["routing_demand"],
                "da_demand": dinfo["da_demand"],
                "total_demand": dinfo["total_demand"],
                "usage": dinfo["total_demand"] / dinfo["capacity"] if dinfo["capacity"] > 0 else None,
                "excess": dinfo["excess"],
                "violated": dinfo["violated"],
                "routing_distance_scaled": agg[did]["routing_distance_scaled"],
                "da_distance_scaled": agg[did]["da_distance_scaled"],
                "n_veh_routing": agg[did]["n_veh_routing"],
                "n_veh_da": agg[did]["n_veh_da"],
            })

        # Routes (one row per route)
        for rec in routes:
            route_rows.append({
                "row_id": config.row_id,
                "instance": config.instance,
                "iteration": iteration,
                "route_idx": rec["route_idx"],
                "vehicle_type_idx": rec["vehicle_type_idx"],
                "depot_id": rec["depot_id"],
                "kind": rec["kind"],
                "client_sequence": " ".join(str(c) for c in rec["client_ids"]),
                "demand": rec["demand"],
                "distance_scaled": rec["distance_scaled"],
                "distance_objective": rec.get("distance_objective"),
            })

        # DA pool stats per depot
        for did, s in info["da_pool_stats"].items():
            da_pool_rows.append({
                "row_id": config.row_id,
                "instance": config.instance,
                "iteration": iteration,
                "depot_id": did,
                "eligible_clients": s["eligible_clients"],
                "eligible_demand": s["eligible_demand"],
                "selected_clients": s["selected_clients"],
                "selected_demand": s["selected_demand"],
                "lost_da_candidate_demand": s["lost_da_candidate_demand"],
                "capacity": s["capacity"],
                "radius_scaled": s["radius_scaled"],
                "radius_raw_equivalent": s["radius_raw_equivalent"],
            })

        # Stopping conditions: feasible + no violation + no missing
        if not audit["violated"]:
            if missing:
                status = "MISSING_CLIENTS"
                print(f"    STATUS: MISSING_CLIENTS ({len(missing)})")
            elif not pyvrp_feasible:
                status = "PYVRP_INFEASIBLE"
                print(f"    STATUS: PYVRP_INFEASIBLE (capacity ok but solver infeasible)")
            else:
                status = "OK"
                print(f"    STATUS: OK")
            break

        # Try to repair
        ranked = rank_overloaded_routing_candidates(inst, routes, audit)
        new_excl = select_routing_exclusions(inst, audit, ranked)
        new_only = new_excl - excluded

        # Isolation guard
        da_pool = info.get("da_pool", {})
        all_depots = list(inst.depots.keys())
        accepted: Set[Tuple[int, int]] = set()
        sim_excluded = set(excluded)
        for cand in ranked:
            pair = (int(cand["depot_id"]), int(cand["client_id"]))
            if pair not in new_only or pair in accepted:
                continue
            cid = pair[1]
            candidate_excluded = sim_excluded | {pair}
            has_routing = any(
                (d, cid) not in candidate_excluded for d in all_depots
            )
            has_da = any(cid in da_pool.get(d, []) for d in all_depots)
            if has_routing or has_da:
                accepted.add(pair)
                sim_excluded.add(pair)
        skipped = new_only - accepted
        if skipped:
            print(f"    [warn] isolation guard skipped: {_fmt_exclusions(skipped)}")
        new_only = accepted

        print(f"    Repair adding exclusions: {_fmt_exclusions(new_only)}")
        for cand in ranked:
            pair = (int(cand["depot_id"]), int(cand["client_id"]))
            if pair in new_only:
                repair_rows.append({
                    "row_id": config.row_id,
                    "instance": config.instance,
                    "iteration": iteration,
                    "depot_id": cand["depot_id"],
                    "client_id": cand["client_id"],
                    "demand": cand["demand"],
                    "delta": cand["delta"],
                    "route_idx": cand["route_idx"],
                    "reason": "routing_excess",
                })

        # Patch convergence rows for this (row_id, iteration)
        for cr in convergence_rows:
            if cr["row_id"] == config.row_id and cr["iteration"] == iteration:
                cr["n_exclusions_added"] = len(new_only)
                cr["n_exclusions_after"] = n_before + len(new_only)

        if not new_only:
            status = "NOT_REPAIRABLE"
            print(f"    STATUS: NOT_REPAIRABLE")
            break

        excluded = merge_exclusions(excluded, new_only)

    if last_audit and last_audit.get("violated") and status == "MAX_ITERS_CAPACITY_VIOLATED":
        print(f"  STATUS: MAX_ITERS_CAPACITY_VIOLATED")

    # Build final result record with per-depot breakdown
    final_rec = dict(base_record)
    final_rec.update({
        "status": status,
        "final_iteration": final_iteration,
        "pyvrp_feasible_final": bool(last_best_res.best.is_feasible()) if last_best_res else None,
        "pyvrp_objective_scaled_final": float(last_best_res.best.distance()) if last_best_res else None,
        "objective_mode": last_info.get("objective_mode"),
        "encode_cost_factors": args.encode_cost_factors,
        "milp_ub": last_report.get("milp_ub"),
        "ub_milp": last_report.get("ub_milp"),
        "ub_pyvrp": last_report.get("ub_pyvrp"),
        "raw_gap_pyvrp_minus_milp": last_report.get("raw_gap_pyvrp_minus_milp"),
        "abs_gap_pyvrp_vs_milp": last_report.get("abs_gap_pyvrp_vs_milp"),
        "gap_percent": last_report.get("gap_percent"),
        "gap_distance_flag": last_report.get("gap_distance_flag"),
        "costo_routing_pyvrp": last_report.get("costo_routing_pyvrp"),
        "costo_da_pyvrp": last_report.get("costo_da_pyvrp"),
        "costo_vehiculos_pyvrp": last_report.get("costo_vehiculos_pyvrp"),
        "costo_depositos": last_report.get("costo_depositos"),
        "costo_total_pyvrp": last_report.get("costo_total_pyvrp"),
        "routing_distance_scaled": last_report.get("routing_distance_scaled"),
        "da_distance_scaled": last_report.get("da_distance_scaled"),
        "n_veh_routing": last_report.get("n_veh_routing"),
        "n_veh_da": last_report.get("n_veh_da"),
        "total_demand": last_report.get("total_demand"),
        "served_demand": last_report.get("served_demand"),
        "service_level": last_report.get("service_level"),
        "capacity_violated_final": bool(last_audit.get("violated")) if last_audit else None,
        "max_excess_final": float(last_audit.get("max_excess", 0.0)) if last_audit else None,
        "n_exclusions_total": len(excluded),
        "missing_clients_final": len(last_missing),
        "runtime_seconds": time.perf_counter() - t0,
    })

    if last_audit:
        # last solve's depot aggregates
        agg = _per_depot_aggregates(inst, extract_routes(inst, last_best_res, last_info))
        for did, dinfo in last_audit["by_depot"].items():
            final_rec[f"d{did}_capacity"] = dinfo["capacity"]
            final_rec[f"d{did}_routing_demand"] = dinfo["routing_demand"]
            final_rec[f"d{did}_da_demand"] = dinfo["da_demand"]
            final_rec[f"d{did}_total_demand"] = dinfo["total_demand"]
            final_rec[f"d{did}_usage"] = (
                dinfo["total_demand"] / dinfo["capacity"] if dinfo["capacity"] > 0 else None
            )
            final_rec[f"d{did}_excess"] = dinfo["excess"]
            final_rec[f"d{did}_violated"] = dinfo["violated"]
            final_rec[f"d{did}_routing_distance_scaled"] = agg[did]["routing_distance_scaled"]
            final_rec[f"d{did}_da_distance_scaled"] = agg[did]["da_distance_scaled"]
            final_rec[f"d{did}_n_veh_routing"] = agg[did]["n_veh_routing"]
            final_rec[f"d{did}_n_veh_da"] = agg[did]["n_veh_da"]

    return final_rec


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    instance_folder = Path(args.instance_folder)

    mapping = load_lorp_fsd_mapping(args.excel, instance_folder=None)
    if args.sample_random is not None:
        n = min(int(args.sample_random), len(mapping))
        mapping = mapping.sample(n=n, random_state=int(args.random_seed)).sort_values("row_id")
    if args.limit is not None:
        mapping = mapping.head(args.limit)

    print(f"Rows selected: {len(mapping)}")
    print(f"runtime={args.runtime}s × runs={args.runs} × max_iters={args.max_iters}  "
          f"encode_cost_factors={args.encode_cost_factors}")
    if args.sample_random is not None:
        print(f"random sample: N={args.sample_random} seed={args.random_seed}")
    print(f"Output dir: {out_dir}")

    results: List[Dict[str, Any]] = []
    convergence: List[Dict[str, Any]] = []
    repairs: List[Dict[str, Any]] = []
    depot_audit: List[Dict[str, Any]] = []
    routes: List[Dict[str, Any]] = []
    da_pool: List[Dict[str, Any]] = []

    for _, row in mapping.iterrows():
        try:
            rec = run_one(row, instance_folder, args, convergence, repairs,
                          depot_audit, routes, da_pool)
        except Exception as exc:
            config = spec_from_row(row)
            print(f"\nROW {config.row_id} {config.instance}  STATUS: ERROR  {repr(exc)}")
            rec = {
                "row_id": config.row_id,
                "instance": config.instance,
                "status": "ERROR",
                "error": repr(exc),
                "final_iteration": -1,
                "pyvrp_feasible_final": None,
                "pyvrp_objective_scaled_final": None,
                "objective_mode": None,
                "encode_cost_factors": args.encode_cost_factors,
                "milp_ub": config.UB,
                "ub_milp": config.UB,
                "ub_pyvrp": None,
                "raw_gap_pyvrp_minus_milp": None,
                "abs_gap_pyvrp_vs_milp": None,
                "gap_percent": None,
                "gap_distance_flag": None,
                "capacity_violated_final": None,
                "max_excess_final": None,
                "n_exclusions_total": 0,
                "missing_clients_final": None,
                "runtime_seconds": None,
            }
        results.append(rec)

    paths = {
        "results": out_dir / "results.csv",
        "convergence": out_dir / "convergence.csv",
        "repairs": out_dir / "repairs.csv",
        "depot_audit": out_dir / "depot_audit.csv",
        "routes": out_dir / "routes.csv",
        "da_pool_stats": out_dir / "da_pool_stats.csv",
    }
    pd.DataFrame(results).to_csv(paths["results"], index=False)
    pd.DataFrame(convergence).to_csv(paths["convergence"], index=False)
    pd.DataFrame(repairs).to_csv(paths["repairs"], index=False)
    pd.DataFrame(depot_audit).to_csv(paths["depot_audit"], index=False)
    pd.DataFrame(routes).to_csv(paths["routes"], index=False)
    pd.DataFrame(da_pool).to_csv(paths["da_pool_stats"], index=False)

    print("\nWrote:")
    for k, p in paths.items():
        print(f"  {p}")


if __name__ == "__main__":
    main()
