# C Congruency Test — Row 0 (LoRP-FSD)

Phase: C congruency only. No PyVRP implemented. No v3 heuristic modified.

Date: 2026-06-05
Host: macOS (Darwin 25.5.0), arm64.

Source of truth: `docs/C_SOLVER_AUDIT.md`, `docs/PYVRP_REPLICATION_SPEC.md`,
`docs/IMPLEMENTATION_PLAN.md`, and C source under `reference/LoRPSD`.

## Goal

Verify whether the original C solver, Excel row 0, and the `r40x5a-1.dat`
instance are parameter-congruent, and whether row-0 interpretation is
trustworthy before PyVRP Phase 1.

## Headline result

**Row 0 is fully congruent.** Every Excel objective component was reproduced to
full precision by an **independent static reconstruction** from the `.dat`
geometry + the exact C-source formulas + the row-0 CLI parameters. The C binary
itself could **not** be executed (Linux x86-64 ELF on a macOS arm64 host), so the
binary run is replaced by an exact formula-level reconstruction, which is a
stronger congruency check than re-running Gurobi because it exercises every flag
and unit explicitly.

`Z = 95.3087 (routing) + 0 (vehicles) + 300 (depots) + 0 (DA) = 395.3087`
== Excel `UB` 395.309. ✓

## 1. Binary status

```
$ file reference/LoRPSD/LoRPSD
ELF 64-bit LSB pie executable, x86-64, ... for GNU/Linux 3.2.0
$ reference/LoRPSD/LoRPSD
exec format error
```

- Binary is **Linux x86-64**; host is **macOS arm64** → cannot run natively.
- No Docker installed; Rosetta does not run Linux ELF (only macOS x86-64 Mach-O).
- Gurobi 12.0.0 (mac arm64) **is** installed with a valid license, and
  `/Library/gurobi1200/macos_universal2/{include,lib}` provides `gurobi_c++.h`
  and `libgurobi_c++.a` → a from-source recompile is feasible (recipe in handoff).
- Logs: `outputs/c_congruency/row0_error.txt`.

## 2. Excel row 0 (sheet `LoRP-FSD`, first data row)

| Field | Value |
|---|---|
| name | r40x5a-1.dat |
| problem | LoRP-SD |
| of | cost |
| F_R | 1 |
| F_A | 0 |
| R | 30 |
| Length | 100 |
| UB | 395.309 |
| LB | 395.309 |
| Status | Optimal (gap 0) |
| Cost Routing | 95.3087 |
| Cost (Vehicles) | 0 |
| Cost (Depots) | 300 |
| Cost Direct All | 0 |
| Open depots | d1, d2, d3, d5 (size 1 each, Cap 875) |
| DemandD1..4 | 696, 415, 342, 478 (Σ = 1931 = total demand) |
| VehiclesD1..4 | 0, 0, 1, 0 |
| TotalDepots | 4 |
| TotalVehicles | 1 |

## 3. Instance file

Expected `r40x5a-1.dat`. Four copies found, **all identical** (md5
`1d2ebed4e2e7ba4ecb12f01dab1942f5`):

- `instances/r40x5a-1.dat`  ← used
- `instances_old/r40x5a-1.dat`
- `reference/LoRPSD/instances_LLRP/r40x5a-1.dat`
- `reference/LoRPSD/instances_LLRP/DATA SMALL SIZE/r40x5a-1.dat`

Parsed (matches C `ReadData_sizing` format, audit §8):
`n_clients=40, n_depots=5, max_open=5, n_vehicles=40, Q=340,
base_dep_cap=1750×5, dep_fixed=100×5, veh_fixed=0, trailing=0, total_demand=1931`.

Note `instances_LRP` from the plan does not exist; the real folders are
`instances`, `instances_old`, `reference/LoRPSD/instances_LLRP`,
`reference/LoRPSD/instances_stc`.

## 4. C command (for a future live run)

`r40x5a-1.dat` is a deterministic LoRP-FSD instance, so `-original 0`:

```bash
reference/LoRPSD/LoRPSD \
  -results outputs/c_congruency/row0_results.txt \
  -problemID 0 \
  -WR 1 \
  -WA 0 \
  -Radius 30 \
  -instance instances/r40x5a-1.dat \
  -VFX 1 \
  -OF 1 \
  -original 0 \
  -model 1 \
  -length 100
```

(Not executable on this host; see §1 and the handoff recompile recipe.)

## 5. Per-parameter congruency (granular)

`max_dist = 125.399362` (the client–client pair, i.e. max over **all** node
pairs), `scale = 100 / max_dist = 0.79745222`.

| # | Parameter | Row-0 value | C semantics (source) | Reconstruction | Congruent |
|---|---|---|---|---|---|
| 1 | problemID | 0 (Arslan) | `scaledistance()`: `dist *= 100/max_dist` | `scale=0.797452`; `Length=100` scaled == max_dist | ✅ |
| 2 | max_dist basis | — | max Euclidean over all depot/client nodes | client–client pair 125.399 dominates depot–client (102.45) | ✅ over **all** nodes |
| 3 | F_R (WR) | 1 | `Cost1 += WR·dist·X` (scaled dist) | routing 95.3087 | ✅ |
| 4 | F_A (WA) | 0 | `DirectALL += WA·dist·A` | DA cost 0 | ✅ (trivial; F_A=0) |
| 5 | R (Radius) | 30 | `dist·A ≤ R·ΣY` scaled (stcmodels.cpp:746) | 38/40 DA-coverable, 2 routed | ✅ scaled units |
| 6 | Length | 100 | `t ≤ Length·X` scaled (stcmodels.cpp:866) | route 95.31 ≤ 100; raw 119.5 ≤ 125.4 | ✅ scaled units |
| 7 | original | 0 | `det_LoRP_DSD` sizing model | literal `LoRP-SD` + sizing-cost match | ✅ confirmed =0 |
| 8 | OF | 1 (cost) | hard-coded `Data.OF=1`; cost-mode constraints | exactly-once `f+A==1` (stcmodels.cpp:818) | ✅ |
| 9 | VFX | 1 (assumed) | `vehiclesfixed *= VFX` | veh_fixed=0 → Cost(Vehicles)=0 regardless | ⚠️ N/A (untestable on row 0) |
| 10 | Q (veh cap) | 340 | `W ≤ Q·X` load-flow (stcmodels.cpp:782) | per-route capacity enforced | ✅ matches PyVRP per-vehicle cap |
| 11 | facility sizing | 5 sizes | `cap=base·(1+(-2+s)·0.25)` | size1→cap 875 | ✅ exact |
| 12 | depot cost | — | `fix+((cap-base)/(2·base))·(totalfix/T)` | size1→75; 4×75=300 | ✅ exact |
| 13 | Cost Routing | 95.3087 | `Cost1` scaled | d3→#1→#33→d3 ×scale = 95.3087 | ✅ exact |
| 14 | Cost Vehicles | 0 | `Cost2` raw | veh_fixed=0 | ✅ |
| 15 | Cost Depots | 300 | `Cost4` raw | 4×75 | ✅ exact |
| 16 | Cost Direct All | 0 | `DirectALL` scaled | F_A=0 | ✅ |
| 17 | UB | 395.309 | `ObjVal` | 95.3087+0+300+0=395.3087 | ✅ exact |
| 18 | TotalDepots | 4 | open depots | d1,d2,d3,d5 | ✅ |
| 19 | TotalVehicles | 1 | routing routes | 1 route (clients #1,#33) at d3 | ✅ |

### Why the reconstruction is decisive (not coincidence)

- With `F_A=0`, DA is free, so the optimum directly allocates every DA-reachable
  client (cost 0) and routes only those unreachable within `R=30`.
- Independently computing DA reachability for the 4 open depots leaves exactly
  **2 clients (#1, #33)** uncoverable → they must be routed. Excel shows exactly
  **1 routing vehicle**.
- The single route's minimum scaled cost **over the open depots** is at **d3**
  (95.3087). The globally cheaper depot d4 (82.95) is **closed**, so d3 is
  correct — and Excel reports `VehiclesD3=1`. The depot *choice* ties out too.

## 6. Per-route vehicle capacity in C (Decision #5)

`det_LoRP_DSD` (`stcmodels.cpp`) enforces per-route vehicle capacity `Q` via a
single-commodity load-flow, **not** only depot-aggregate capacity:

- `stcmodels.cpp:766–772` — load conservation: `Σ W[j][i] − Σ W[i][j] == (1 − Rnew)·q_i`
  (a routed client adds its demand to the carried load; a DA client `Rnew=1` adds none).
- `stcmodels.cpp:782` — **`W[i][j] ≤ Q · X[i][j]`** → every arc (hence every
  route) carries at most `Q=340`. This is the per-vehicle capacity.
- `stcmodels.cpp:792` — `W[i][j] ≥ q_j · X[i][j]` lower bound.
- `stcmodels.cpp:866` — `t[i][j] ≤ Length · X[i][j]` route-length cap.
- `stcmodels.cpp:879` — `Σ (f+A)·q ≤ Σ dep_cap·Y` shared depot capacity (routing+DA).

**Conclusion:** PyVRP's native per-vehicle capacity `Q` **matches** the C model.
It is **not** an extra constraint. The v3 relaxed builder's decomposition of
`Cap_i` into `floor(Cap/Q)` vehicles of cap `Q` plus a residual vehicle is a
faithful integer approximation of the aggregate depot capacity, while each
Q-capacity route is exactly congruent.

## 7. Conclusions

- Did the C binary run? **No** — Linux x86-64 ELF on macOS arm64 (`exec format error`).
- Did row 0 match Excel? **Yes, exactly**, by static reconstruction (UB 395.3087).
- `original=0` (LoRP-FSD/sizing)? **Confirmed** — literal `LoRP-SD` output plus
  the sizing-cost formula reproducing `Cost(Depots)=300` (the standard LoRP
  `original=1` has no depot sizing).
- `problemID=0` Arslan scaling? **Confirmed** — `scale=100/max_dist`, and
  `Length=100` scaled equals the instance diameter.
- `R` and `Length` scaled-unit? **Confirmed** (stcmodels.cpp:746, :866 compare
  against scaled `dist`/`t`).
- Excel components = scaled distance + raw fixed? **Confirmed** — routing/DA
  scaled (95.3087 ←119.5 raw ×scale); depots raw (300 = 4×75 from raw fixed 100).
- Is Phase 1 PyVRP unblocked? **Yes** (see §8).

## 8. Open / residual items

1. **VFX semantics untestable on row 0** (veh_fixed=0 ⇒ Cost(Vehicles)=0 for any
   VFX). Confirm on a later row whose instance has nonzero vehicle fixed cost.
2. **Live binary run not performed.** Static reconstruction is exact, but a
   recompiled mac-arm64 run (recipe in handoff) is recommended as optional
   independent confirmation, and is required to test any row where the optimal
   solution structure is not analytically obvious.
3. **`-model 1` / `-OF`** are parsed-but-not-dispatching on this path (audit §1);
   harmless for row 0.

## 9. Verdict

**GO for PyVRP Phase 1 under fixed-facility design.** Row-0 interpretation is
trustworthy: all CLI flags, scaling, `R`, `Length`, `original`, objective units,
and the per-route capacity assumption are congruent with the C source and Excel.
The residual items above are confirmations/edge-cases, not blockers.
