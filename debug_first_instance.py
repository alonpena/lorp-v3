from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from da_geometry import assign_da_clients, build_direct_allocation_data, compute_max_distance, dist_euclid
from dat_loader import load_dat
from instance_adapter import adapt_instance, spec_from_row
from instance_resolver import resolve_instance_path
from pyvrp_model import build_full_model, solve_fast
from reporting import build_full_report, extract_kpis_level1, extract_kpis_level2
from xlsx_loader import load_lorp_fsd_mapping

OUT = Path("pipeline_out/debug_first_instance")
OUT.mkdir(parents=True, exist_ok=True)
ROW_ID = 0


def p(msg=""):
    print(msg)


def main():
    df = load_lorp_fsd_mapping("results_MILP.xlsx", instance_folder=None)
    row = df[df.row_id == ROW_ID].iloc[0]
    config = spec_from_row(row)
    resolution = resolve_instance_path(config.instance, "instances")
    base = load_dat(resolution.path)
    inst = adapt_instance(base, config)

    p("=" * 100)
    p("0) EXCEL CONFIG")
    p("=" * 100)
    p(f"row_id                 : {config.row_id}")
    p(f"instance               : {config.instance}")
    p(f"resolved               : {resolution.status} -> {resolution.path}")
    p(f"R                      : {config.R}")
    p(f"F_R                    : {config.F_R}")
    p(f"F_A                    : {config.F_A}")
    p(f"Length                 : {config.Length}")
    p(f"UB MILP                : {config.UB}")
    p(f"MILP routing cost      : {config.routing_cost_milp}")
    p(f"MILP DA cost           : {config.da_cost_milp}")
    p(f"MILP vehicle cost      : {config.vehicle_cost_milp}")
    p(f"MILP depot cost        : {config.cost_depots}")
    p(f"MILP total components  : {config.routing_cost_milp + config.da_cost_milp + config.vehicle_cost_milp + config.cost_depots}")
    p("Excel depots:")
    for did, d in config.depots.items():
        m = config.depots_milp.get(did, {})
        p(f"  depot {did}: cap={d.get('capacity')} milp_demand={m.get('demand')} usage={m.get('usage')} vehicles={m.get('vehicles')}")

    p("\n" + "=" * 100)
    p("1) BASE INSTANCE")
    p("=" * 100)
    p(f"n_clients              : {base.data['n_clients']}")
    p(f"n_depots               : {base.data['n_depots']}")
    p(f"max_depots_open        : {base.data['max_depots_open']}")
    p(f"veh_cap Q              : {base.data['veh_cap']}")
    p(f"veh_fixed_cost         : {base.data['veh_fixed_cost']}")
    p("base depots:")
    for did, d in base.depots.items():
        p(f"  d{did}: x={d['x']:.1f} y={d['y']:.1f} cap={d['cap']} fixed={d['fixed_cost']}")
    p("first 10 clients:")
    for j, c in list(base.clients.items())[:10]:
        p(f"  c{j}: x={c['x']:.1f} y={c['y']:.1f} demand={c['demand']}")

    p("\n" + "=" * 100)
    p("2) ADAPTED INSTANCE")
    p("=" * 100)
    p(f"active depots          : {list(inst.depots.keys())}")
    p(f"n_depots active        : {inst.data['n_depots']}")
    p(f"R/F_R/F_A/Length       : {inst.data['R']}/{inst.data['F_R']}/{inst.data['F_A']}/{inst.data['Length']}")
    p(f"total demand           : {sum(c['demand'] for c in inst.clients.values())}")
    p("adapted depots:")
    for did, d in inst.depots.items():
        p(f"  d{did}: x={d['x']:.1f} y={d['y']:.1f} cap={d['cap']} fixed={d['fixed_cost']}")

    maxdist = compute_max_distance(inst)
    escala = 100 / maxdist
    p("\n" + "=" * 100)
    p("3) DISTANCE SCALING (ARSLAN)")
    p("=" * 100)
    p(f"max individual arc raw : {maxdist:.12f}")
    p(f"Arslan scale           : {escala:.12f} (=100/maxdist)")
    p("sample scaled depot-client distances:")
    for did, d in inst.depots.items():
        vals = []
        for j, c in inst.clients.items():
            raw = dist_euclid((d['x'], d['y']), (c['x'], c['y']))
            vals.append((raw, j, raw * escala))
        vals.sort()
        p(f"  depot {did}: nearest 5 -> " + ", ".join(f"c{j}:raw={raw:.2f},sc={sc:.2f}" for raw, j, sc in vals[:5]))

    da_data, max_clients_da = build_direct_allocation_data(inst, inst.data["R"])
    p("\n" + "=" * 100)
    p("4) DA FEASIBILITY BY RADIUS")
    p("=" * 100)
    p(f"R                      : {inst.data['R']}")
    p(f"depots with feasible DA: {list(da_data.keys())}")
    p(f"max_clients_per_depot  : {max_clients_da}")
    for did, perfil in da_data.items():
        p(f"  depot {did}: {len(perfil['clients'])} clients")
        detail = []
        for j in perfil['clients']:
            d = perfil['cost_ij'][(did, j)]
            detail.append((d, j, inst.clients[j]['demand']))
        detail.sort()
        p("    " + ", ".join(f"c{j}(dem={dem},raw={d:.2f},sc={d*escala:.2f})" for d, j, dem in detail))

    da_assigned, routing_set = assign_da_clients(inst, da_data, int(inst.data['veh_cap']))
    p("\n" + "=" * 100)
    p("5) DA ASSIGNMENT + REPAIR")
    p("=" * 100)
    p(f"DA clients             : {sum(len(v) for v in da_assigned.values())}")
    p(f"Routing clients        : {len(routing_set)} -> {sorted(routing_set)}")
    for did in sorted(inst.depots):
        clients = da_assigned.get(did, [])
        da_dem = sum(inst.clients[j]['demand'] for j in clients)
        cap = inst.depots[did]['cap']
        rem = cap - da_dem
        q = int(inst.data['veh_cap'])
        p(f"  d{did}: DA_clients={len(clients)} ids={sorted(clients)} DA_dem={da_dem} cap={cap} usage={da_dem/cap:.2%} rem={rem} full_rt={int(rem)//q} residual={int(rem)%q}")

    p("\n" + "=" * 100)
    p("6) PYVRP MODEL CODIFICATION")
    p("=" * 100)
    model, info = build_full_model(inst)
    p(f"escala                 : {info['escala']:.12f}")
    p(f"max_distance raw       : {info['max_distance']:.12f}")
    p(f"routing max_distance   : Length * escala = {inst.data['Length'] * info['escala']:.6f}")
    p(f"vehicle types          : {len(info['vehicle_types'])}")
    for idx, vt in enumerate(info['vehicle_types']):
        if vt['type'] == 'direct_allocation':
            j = vt['client']
            p(f"  vt[{idx:02d}] DA depot={vt['depot']} client={j} cap=demand={inst.clients[j]['demand']}")
        else:
            p(f"  vt[{idx:02d}] RT depot={vt['depot']} num={vt.get('num_available')} cap={vt.get('residual_capacity', inst.data['veh_cap'])} max_distance={inst.data['Length'] * info['escala']:.6f}")

    p("\n" + "=" * 100)
    p("7) SOLVE")
    p("=" * 100)
    res = solve_fast(model, runtime=1, n_runs=1)
    sol = res.best
    vt_list = info['vehicle_types']
    p(f"feasible               : {sol.is_feasible()}")
    p(f"objective scaled       : {sol.distance():.6f}")
    p(f"routes                 : {len(sol.routes())}")
    for ridx, route in enumerate(sol.routes()):
        vt = vt_list[route.vehicle_type()]
        trips = list(route.trips())
        demand = sum((t.delivery()[0] if t.delivery() else 0) for t in trips)
        visits = [list(t.visits()) for t in trips]
        p(f"  route[{ridx:02d}] vt_idx={route.vehicle_type()} {vt['type']:<18} depot={vt['depot']} trips={len(trips)} demand={demand:.0f} dist_scaled={route.distance():.4f} visits={visits}")

    p("\n" + "=" * 100)
    p("8) KPI + REPORT")
    p("=" * 100)
    k1 = extract_kpis_level1(inst, res, info)
    k2 = extract_kpis_level2(inst, res, info)
    report = build_full_report(inst, res, config, info)
    p(f"total demand           : {k1['total_demand']}")
    p(f"served demand          : {k1['served_demand']}")
    p(f"pending demand         : {k1['pending_demand']}")
    p(f"service level          : {report['nivel_servicio']:.2%}")
    p("by type:")
    for typ in ['routing', 'direct_allocation']:
        x = k1[typ]
        p(f"  {typ}: veh={x['n_vehicles']} clients={x['n_clients']} demand={x['demand']} dist_scaled={x['distance']}")
    p("by depot:")
    for did in sorted(inst.depots):
        cap = inst.depots[did]['cap']
        rt = k2.get(did, {}).get('routing', {'demand':0,'n_clients':0,'n_vehicles':0,'distance':0})
        da = k2.get(did, {}).get('direct_allocation', {'demand':0,'n_clients':0,'n_vehicles':0,'distance':0})
        total = rt['demand'] + da['demand']
        p(f"  d{did}: cap={cap} total={total} usage={total/cap:.2%} | DA={da['demand']} ({da['n_clients']} clients,{da['n_vehicles']} veh,dist={da['distance']}) | RT={rt['demand']} ({rt['n_clients']} clients,{rt['n_vehicles']} veh,dist={rt['distance']})")
    p("costs:")
    p(f"  PyVRP routing         : {report['costo_routing_pyvrp']}")
    p(f"  PyVRP DA              : {report['costo_da_pyvrp']}")
    p(f"  PyVRP vehicles        : {report['costo_vehiculos_pyvrp']}")
    p(f"  depot cost Excel      : {report['costo_depositos']}")
    p(f"  PyVRP total           : {report['costo_total_pyvrp']}")
    p(f"  MILP UB               : {config.UB}")
    p(f"  raw gap               : {report['raw_gap_pyvrp_minus_milp']:.4%}")
    p(f"  abs gap               : {report['gap_final']:.4%}")
    p(f"  capacity violation    : {report['violacion_capacidad']}")

    make_plots(inst, res, info, da_assigned, routing_set, report)


def make_plots(inst, res, info, da_assigned, routing_set, report):
    assigned_da = {j for cs in da_assigned.values() for j in cs}
    vt_list = info['vehicle_types']
    locs = info.get('locations')

    fig, axes = plt.subplots(1, 3, figsize=(21, 6.5))
    ax0, ax1, ax2 = axes

    for j, c in inst.clients.items():
        color = 'seagreen' if j in assigned_da else 'steelblue'
        ax0.scatter(c['x'], c['y'], color=color, s=45)
        ax0.annotate(str(j), (c['x'], c['y']), fontsize=6)
    for did, d in inst.depots.items():
        ax0.scatter(d['x'], d['y'], color='crimson', marker='*', s=300, edgecolor='black')
        ax0.annotate(f'D{did}', (d['x'], d['y']), color='crimson', weight='bold')
        ax0.add_patch(plt.Circle((d['x'], d['y']), float(inst.data['R']), edgecolor='crimson', facecolor='none', linestyle='--', alpha=.25))
    ax0.set_title(f"Assignment DA={len(assigned_da)} RT={len(routing_set)}")

    for ax, profile, cmap in [(ax1, 'routing', plt.cm.Blues), (ax2, 'direct_allocation', plt.cm.Greens)]:
        for _, c in inst.clients.items():
            ax.scatter(c['x'], c['y'], color='lightgray', s=18, alpha=.5)
        for did, node in info['depot_nodes'].items():
            ax.scatter(node.x, node.y, color='crimson', marker='*', s=300, edgecolor='black')
            ax.annotate(f'D{did}', (node.x, node.y), color='crimson', weight='bold')
        routes = [r for r in res.best.routes() if vt_list[r.vehicle_type()]['type'] == profile]
        for idx, route in enumerate(routes):
            col = cmap(.3 + .6 * idx / max(1, len(routes)-1))
            for trip in route.trips():
                if locs is None:
                    continue
                seq = [trip.start_depot(), *trip.visits(), trip.end_depot()]
                xs = [locs[i].x for i in seq]
                ys = [locs[i].y for i in seq]
                ax.plot(xs, ys, '-o', color=col, linewidth=1.2, markersize=3)
        ax.set_title(f"{profile} routes={len(routes)} dist={sum(r.distance() for r in routes):.1f}")

    for ax in axes:
        ax.set_aspect('equal', 'box')
        ax.grid(alpha=.25, linestyle='--')
    fig.suptitle(f"row0 {inst.data['R']=} total={report['costo_total_pyvrp']:.1f} gap={report['gap_final']:.2%}")
    fig.tight_layout()
    out = OUT / 'row0_debug_assignment_routes.png'
    fig.savefig(out, dpi=160, bbox_inches='tight')
    print(f"\nPLOT saved: {out}")


if __name__ == '__main__':
    main()
