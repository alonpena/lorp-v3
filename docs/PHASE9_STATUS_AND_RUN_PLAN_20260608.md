# Phase 9 status and run plan

Date: 2026-06-08 · Branch: `phase9-soft-penalty-tabu` · Commit: `edd8265`

## 1. What was implemented in Phase 9

Repair mode is now configurable; the operational default changed from a
permanent hard arc removal to a tabu soft penalty.

- **`soft_penalty`** — the selected routing pair `(depot, client)` stays
  feasible in the rebuilt graph, but a large penalty is added to the PyVRP
  **duration/cost** channel only, steering the search away from it.
- **`tabu_penalty` (default)** — soft penalty plus a per-pair tabu tenure
  countdown; when the tenure reaches 0 the penalty is removed unless the pair is
  re-selected.
- **`hard_forbid`** — legacy behaviour retained as a comparison baseline
  (selected pair removed from the rebuilt graph).
- **Penalty affects duration/search cost only.** It is charged once per arrival
  at the penalised client on that depot's routing profile.
- **Distance / Length semantics unchanged.** The distance channel is never
  touched, so route-length feasibility is unaffected.
- **Cost reconstruction ignores the penalty.** The reported `Z_PyVRP` is rebuilt
  from semantic geometry (`reconstructed_weighted_cost = F_R * geometry`), never
  from the penalised PyVRP objective.
- **`repair_trace.csv` extended** with `repair_mode`, `penalty_value`,
  `tabu_remaining`, `saving`, `demand` columns and `hard_forbid` /
  `soft_penalty` / `tabu_add` / `tabu_expire` event rows.
- CLI on `run_row.py`, `run_random_sample.py`, `run_first_n.py`,
  `run_full_excel.py`: `--repair-mode {hard_forbid,soft_penalty,tabu_penalty}`
  (default `tabu_penalty`), `--penalty-factor` (100), `--tabu-tenure` (3).

## 2. Tests

- `py_compile` over `src/lorp_fsd/*.py` + scripts — **OK**.
- `pytest -q -m "not integration"` — **217 passed, 32 deselected** (+11 new in
  `tests/test_penalty_tabu.py`).
- A builder test proves penalty lands on the duration channel only: penalized vs
  base model have an identical distance matrix and a `+P` duration on edges
  arriving at the penalised client.

## 3. Compare-10 results (seed 42, 5 s, safe_both)

| Status | hard_forbid | tabu_penalty |
|---|---:|---:|
| FEASIBLE | 7 | **8** |
| STUCK_NONCAPACITY | 1 | **0** |
| REPAIR_INFEASIBLE | 1 | 1 |
| MAX_ITERATIONS | 1 | 1 |

| GAP (FEASIBLE) | hard_forbid | tabu_penalty |
|---|---:|---:|
| mean | 0.30% | 0.95% |
| max | 2.08% | 5.52% |
| negative-gap flags | 0 | 0 |

Average reconstructed cost: routing Δ vs MILP +45.5 (tabu) vs +64.7 (hard); DA
26.2 vs 33.1. Runtime/iteration envelope identical.

**Interpretation.** `tabu_penalty` improved feasibility (+1 FEASIBLE, the
STUCK_NONCAPACITY case eliminated) and lowered average routing/DA cost. The
higher mean/max GAP on FEASIBLE rows is **not** a regression: the extra row that
becomes feasible under tabu was previously excluded (STUCK) under hard_forbid
and contributes a positive GAP. On the 7 rows feasible under both modes the GAPs
are equivalent. Full detail in
`docs/COMPARE10_HARD_FORBID_VS_TABU_PENALTY.md`.

## 4. What is still missing

- **Full Excel run** (all rows) — not yet executed.
- **UI / browser update** for the Phase 9 reports (repair_mode not yet surfaced
  in the static HTML; compact/classic default view still pending).
- **C / PyVRP compatibility interface** (`C_*` validation docs exist; a clean
  congruency interface is not finished).
- **Deeper parameter sweep** for `penalty_factor` and `tabu_tenure` (only
  100 / 3 tested).
- **Local search** in the repair loop.

## 5. Current serious-run plan (first 20 rows)

```
scripts/run_first_n.py
  --n 20
  --seconds 30
  --runs 3
  --max-iter 10
  --repair-policy safe_both
  --repair-mode tabu_penalty
  --penalty-factor 100
  --tabu-tenure 3
  --row-timeout-seconds 1200
  --run-id first20_tabu_penalty_30s3r
  --plots
```

Output: `outputs/first20_tabu_penalty_30s3r/`. Each row is wall-clock guarded at
1200 s so a stall cannot block the batch. Outputs are not committed.

## 6. Explicación para la reunión (ES)

En la Fase 9 cambiamos el modo de reparación por defecto: en lugar de prohibir
permanentemente el arco de ruteo del par (depósito, cliente) sobrecargado,
ahora aplicamos una **penalización suave con memoria tabú** (`tabu_penalty`). El
par sigue siendo factible en el grafo reconstruido, pero recibe una penalización
grande aplicada **solo al canal de costo/duración** de PyVRP, de modo que el
solver lo evita salvo que sea realmente necesario; la penalización expira tras
un número de iteraciones (tenencia tabú) salvo que se vuelva a seleccionar. La
distancia y la restricción de longitud de ruta no se tocan, y el costo real
reportado (`Z_PyVRP`) se reconstruye desde la geometría semántica e **ignora la
penalización**. El modo histórico `hard_forbid` se conserva como línea base de
comparación. En la prueba de 10 filas, `tabu_penalty` aumentó las filas
factibles de 7 a 8 y eliminó un caso atascado (STUCK), con menor costo medio de
ruteo y asignación directa, manteniendo el mismo tiempo de cómputo.
