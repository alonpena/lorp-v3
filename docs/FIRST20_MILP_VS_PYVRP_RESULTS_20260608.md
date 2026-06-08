# First-20: MILP vs PyVRP results

Date: 2026-06-08 · Branch: `phase9-soft-penalty-tabu`
Run id: `first20_tabu_penalty_30s3r`

Focus: **MILP benchmark vs PyVRP reconstruction** (not hard_forbid vs
tabu_penalty). Sources: `outputs/first20_tabu_penalty_30s3r/`
(`consolidated.csv`, `summary.json`, `summary.md`).

## 1. Run configuration

| Parameter | Value |
|---|---|
| rows | first 20 (0..19) |
| seconds per solve | 30 |
| solve runs (seeds) | 3 |
| max repair iterations | 10 |
| repair policy | safe_both |
| repair mode | tabu_penalty |
| penalty factor | 100 |
| tabu tenure | 3 |
| row timeout (s) | 1200 |

## 2. Status counts

| Status | Count |
|---|---:|
| FEASIBLE | 16 |
| REPAIR_INFEASIBLE | 4 |
| STUCK_NONCAPACITY | 0 |
| MAX_ITERATIONS | 0 |
| ERROR | 0 |
| TIMEOUT | 0 |

## 3. GAP on FEASIBLE rows

| Metric | Fraction | Percent |
|---|---:|---:|
| min | -0.000001 | -0.0001% |
| mean | 0.001078 | **0.108%** |
| max | 0.008047 | **0.805%** |
| negative-gap flags | 0 | — |

PyVRP reconstructed cost matches the MILP upper bound within ~0.1% on average;
the worst feasible row is within ~0.8%.

## 4. Cost component comparison (batch averages)

| Component | MILP | PyVRP | Δ (PyVRP − MILP) |
|---|---:|---:|---:|
| routing | 185.34 | 191.73 | +6.39 |
| direct allocation (DA) | 107.76 | 107.21 | -0.55 |
| vehicles | 0.00 | 0.00 | 0.00 |
| depots | 245.00 | 245.00 | 0.00 |

Depot and vehicle costs reconstruct exactly (depot design is fixed from the
MILP; vehicle fixed cost is 0 in this sample). The small positive routing delta
is the slack the heuristic pays versus the exact MILP routing, partly offset by
a slightly cheaper DA mix.

## 5. The 4 REPAIR_INFEASIBLE rows

| row | instance | iters | cap feas | len feas | DA feas | service | same-depot-DA rej | len-invalid rej | rejected | RELAX_DEV | time (s) |
|---:|---|---:|---|---|---|---|---:|---:|---:|---:|---:|
| 5 | r40x5b-1.dat | 1 | ✗ | ✓ | ✓ | ✓ | 4 | 1 | 5 | +1.30% | 90 |
| 6 | r40x5b-1.dat | 1 | ✗ | ✓ | ✓ | ✓ | 6 | 1 | 7 | +1.30% | 90 |
| 7 | r40x5b-1.dat | 1 | ✗ | ✓ | ✓ | ✓ | 0 | 0 | 0 | -0.00005% | 90 |
| 18 | r40x5b-3.dat | 3 | ✗ | ✓ | ✓ | ✓ | 0 | 5 | 3 | -21.56% | 270 |

All four fail **only** on depot capacity (`capacity_feasible = False`); length,
DA radius and single-service all pass. None reached MAX_ITERATIONS — the loop
stopped because the savings selector could not assemble a **safe** removal set,
not because it ran out of iterations.

- **Rows 5, 6** — the overloaded depot's routing clients are mostly
  `same_depot_DA_risk` (moving them to DA at the *same* depot would not free
  aggregate capacity) plus one with no length-feasible alternative. Under
  `safe_both` these are rejected, leaving nothing safe to cut.
- **Row 7** — 0 candidates and 0 rejections: the overload comes from **DA
  demand**, not routing, so there are no routing clients to remove. Capacity
  repair only displaces routing, so it cannot touch a DA-driven overload.
  RELAX_DEV ≈ 0, i.e. cost is already at the MILP level but capacity is violated.
- **Row 18** — iterated 3×, 5 length-invalid rejections; the cuts pushed the
  reconstruction far above the MILP (RELAX_DEV −21.6%, Z ≈ 708 vs UB 582) and
  still did not free capacity safely.

## 6. Runtime

| Metric | Value |
|---|---:|
| min runtime (s) | 90.0 |
| mean runtime (s) | 112.5 |
| max runtime (s) | 270.1 (row 18, 3 iterations) |
| rows over 5 min | 0 |
| timeouts | 0 |

Feasible single-iteration rows take ~90 s (= 3 runs × 30 s). No row approached
the 1200 s guard.

## 7. Interpretación (ES)

- La heurística obtuvo soluciones **factibles en 16/20 filas**.
- En las filas factibles, el costo reconstruido por PyVRP es **muy cercano a la
  cota `UB` del MILP**.
- **GAP medio ≈ 0.108%, máximo ≈ 0.805%**, sin flags de GAP negativo.
- **Sin STUCK, sin TIMEOUT, sin ERROR.**
- Las 4 fallas restantes son **limitaciones de la heurística de reparación**, no
  infactibilidad matemática: el selector no pudo armar un conjunto de cortes
  *seguros* (riesgo de DA en el mismo depósito, falta de alternativa de
  longitud, o sobrecarga originada por demanda DA sin clientes de ruteo que
  quitar). Ninguna agotó iteraciones.

## 8. Qué mostrar al profesor

- **Fila 0** (`report.md` / `index.html`): demo de congruencia — PyVRP
  reproduce el MILP casi exactamente (GAP ≈ 0).
- **Resumen first-20**: evidencia de benchmark (16/20 factibles, GAP medio
  0.108%).
- **`repair_trace.csv` / `report.json`**: auditabilidad — cada decisión de
  reparación queda trazada (modo, penalización, tabú, candidatos
  seleccionados/rechazados y su razón).
- **Siguiente paso**: corrida completa de todo el Excel.

## 9. Limitations

- Solo las primeras 20 filas (varias comparten instancia con distintos
  parámetros).
- Un único ajuste de parámetros: `penalty_factor = 100`, `tabu_tenure = 3`.
- Falta la corrida completa del Excel.
- Falta validación contra el binario C en vivo (congruencia C/PyVRP).
