# HANDOFF — 2026-06-08 Morning (Verified Audit)

**Modo:** CAVEMAN — solo lectura. Cero modificaciones de código.
**Auditado por:** Claude claude-sonnet-4-6 via Desktop Commander.
**Fecha:** 2026-06-08.

---

## 1. Directorio de trabajo y git status

```text
Directorio real: /Users/apena/lor-v3
```

> NOTA: el directorio fue solicitado como `/Users/apena/lorp-v3` pero el directorio
> correcto en disco es `/Users/apena/lor-v3` (sin la `p`).

Git status:

```text
Root del repo padre: /Users/apena
lor-v3 aparece como ?? lor-v3/ (completamente untracked bajo el repo padre)
```

El proyecto `lor-v3` no tiene su propio `.git`. Vive dentro de un repo padre en
`/Users/apena`. Todos los archivos de `lor-v3` son untracked para ese repo padre.
`git status` desde `lor-v3` es muy ruidoso (escanea home directory completo).

---

## 2. Branch / commit

```text
Branch: main
Commit: f705cb0  "first commit"
Repo raíz: /Users/apena (NO /Users/apena/lor-v3)
```

**Solo hay 1 commit** en el repo padre. Todo el desarrollo posterior de `lor-v3`
existe exclusivamente en el filesystem, sin historia git propia.

---

## 3. Qué se implementó en la última iteración

**Phase 7A — Repair Candidate Safety Diagnostics:**

- `RepairCandidateSafety` dataclass con 8 campos diagnósticos.
- `diagnose_repair_candidate(...)` — evalúa a priori si un corte es seguro.
- 4 políticas de repair: `baseline`, `safe_length`, `safe_capacity_release`, `safe_both`.
- `REJECTION_SAME_DEPOT_DA_RISK`, `REJECTION_NO_LENGTH_ALTERNATIVE`, `REJECTION_STRANDS_CLIENT`.
- `rejected_repair_candidates` acumulado cross-iteración en runner.
- Diagnósticos en `artifacts.py`: `same_depot_DA_risk_count`, `length_invalid_cut_count`,
  `rejected_candidates_count`, `capacity_not_freed_count`.
- CLI `--repair-policy` en scripts `run_row.py`, `run_random_sample.py`, `run_first_n.py`,
  `run_full_excel.py`.
- Batch `RowRecord` + `summarize()` incluyen todos los campos Phase 7A.
- Tests: `tests/test_phase7_repair_safety.py` (6 tests) + extensiones en `test_repair_savings.py`.

**NO implementado (ausente a la fecha):**
- Tabu list.
- Penalización de arcos (arc penalty vs. hard delete).
- Backtracking / rollback post-rerun.
- `forbidden_depot_assignments` (DA restriction por depósito).
- Local search / ALNS / LNS / SA.
- Per-row wall-time timeout en batch (ver riesgo #3 abajo).

---

## 4. Archivos modificados / relevantes

Núcleo del repair:
```
src/lorp_fsd/repair.py          376 líneas — lógica completa de savings + Phase 7A
src/lorp_fsd/runner.py          289 líneas — loop iterativo + compute_repair_step
src/lorp_fsd/artifacts.py       156 líneas — JSON audit + CSVs por iteración
src/lorp_fsd/batch.py           593 líneas — batch + RowRecord + consolidado + summary
```

Auditores y checker:
```
src/lorp_fsd/feasibility.py     150 líneas — audit_feasibility + make_feasibility_checker
src/lorp_fsd/capacity_audit.py  (existe, importado)
src/lorp_fsd/cost_reconstruction.py (existe, importado)
```

Tests:
```
tests/test_phase7_repair_safety.py  195 líneas — 6 tests unitarios + 1 integration
tests/test_repair_savings.py        172 líneas — 9 tests unitarios de savings
```

Scripts:
```
scripts/run_row.py
scripts/run_random_sample.py
scripts/run_first_n.py
scripts/run_full_excel.py
```

---

## 5. Lógica exacta de repair (Phase 4 + 7A)

```
# runner.py — run_row()

forbidden: set[tuple[int,int]] = set()
rejected_repair_candidates: set[tuple[int,int,str]] = set()

for it in 0..max_repair_iterations:
    model, info = build_relaxed_model(instance, config, geometry, facility_design, frozenset(forbidden))
    res, solve_time = _solve_multi(model, seconds_per_run, num_solve_runs, seed)
    parsed = parse_solution(res, ...)
    cost   = reconstruct_cost(parsed, ...)
    cap    = audit_capacity(parsed, ...)
    feas   = audit_feasibility(parsed, cap, ...)
    metric = comparison_metric(cost.total, config.UB, feas.fully_feasible)

    if feas.fully_feasible: stop FEASIBLE

    repair = compute_repair_step(...)
    rejected_repair_candidates |= repair.rejected_candidates

    write_iteration_artifacts(...)

    if repair.repair_infeasible:  stop REPAIR_INFEASIBLE
    if not repair.selected:       stop STUCK_NONCAPACITY
    if is_last:                   stop MAX_ITERATIONS

    forbidden = repair.updated_forbidden
```

```
# repair.py — select_forbidden_assignments()

Para cada depósito con excess > 0:
  1. Candidatos = clientes en rutas routing de ese depósito.
  2. Ordenar por (-weighted_saving, depot_id, route_id, client_id).
  3. Excluir pares ya rechazados o ya en forbidden.
  4. Para cada candidato:
     a. tentative = working | {(depot, client)}
     b. Si policy != baseline: diagnose_repair_candidate(tentative) -> safety
        - Rechaza si safe_length y not length_serviceable_after_cut
        - Rechaza si safe_capacity_release y same_depot_DA_risk
        - Rechaza si safe_both y cualquiera de los anteriores
     c. Si feasibility_checker(client, tentative) == False: rechaza (STRANDS_CLIENT)
     d. Acepta: working.add(pair), selected.add(pair), removed += demand_j
  5. Si removed < excess: infeasible_depots.append(depot)
```

**Tipo del forbidden set:**
```python
set[tuple[int, int]]  # (depot_id, client_id)
```

**Significado:** ese cliente NO puede ser servido por ROUTING desde ese depósito.
DA desde el mismo depósito sigue siendo válida salvo filtro `safe_capacity_release`.

---

## 6. ¿El repair hard-delete arcos, penaliza arcos, o ambos?

**Hard-restrict únicamente. No existe penalización de arcos.**

El pair `(depot_id, client_id)` se pasa como `frozenset(forbidden)` a
`build_relaxed_model(...)` que excluye esa asignación de routing del perfil PyVRP.

No existe:
- penalización de costo de arco.
- lista de costos penalizados separada de la lista de costos reales.
- mecanismo soft para arcos cuasi-prohibidos.

El repair actual es equivalente a borrar el arco de routing del modelo
para la siguiente iteración.

---

## 7. ¿Existe tabu?

**No existe tabu.**

Lo que sí existe (y se parece conceptualmente):
```
rejected_repair_candidates: set[tuple[int, int, str]]
```
Este set se acumula cross-iteración en runner y excluye pares ya rechazados
por seguridad (no por aspiración). NO es tabu: no tiene tenure, no expira,
no tiene aspiration criterion, no es por costo penalizado.

Lo que falta para implementar tabu:
- `tabu_list: dict[tuple[int,int], int]` (par → iteraciones restantes de prohibición).
- Función de actualización de tenure.
- Aspiration criterion (aceptar movimiento tabu si mejora la mejor solución conocida).
- Separación objetivo real vs. objetivo penalizado.
- `repair_trace.csv` para trazabilidad de movimientos.
- Soporte en builder para costos penalizados por arco.

---

## 8. Dónde se computan los savings de routing

**Archivo:** `src/lorp_fsd/repair.py`

**Función:** `compute_route_savings(depot_id, client_sequence, geometry) -> dict[int, float]`

Fórmulas (distancia escalada):
```
cliente interno c_m:  d(p, c_m) + d(c_m, s) - d(p, s)
primer cliente c1:    d(depot, c1) + d(c1, c2) - d(depot, c2)
último cliente ck:    d(c_{k-1}, ck) + d(ck, depot) - d(c_{k-1}, depot)
cliente único c1:     d(depot, c1) + d(c1, depot)
```

Saving ponderado:
```python
weighted_saving = F_R * saving
```

**Función:** `build_repair_candidates(routes, capacity_audit, geometry, F_R, demands)`
— construye la lista de `RepairCandidate` solo desde depósitos con `excess > 0`.

---

## 9. Auditorías ex-post existentes

Ejecutadas después de cada solve en `runner.py`:

| Auditoría | Archivo | Qué revisa |
|---|---|---|
| `audit_capacity` | `capacity_audit.py` | `demand_routing_i + demand_DA_i <= Cap_i` |
| `audit_feasibility` | `feasibility.py` | servicio exacto, cap. ruta, longitud ruta, radio DA, binding, penalty distance |
| `reconstruct_cost` | `cost_reconstruction.py` | Z_PyVRP reconstruido desde geometría escalada |
| `comparison_metric` | `cost_reconstruction.py` | GAP si feasible, RELAXATION_DEVIATION si no |
| `write_iteration_artifacts` | `artifacts.py` | JSON audit + routes.csv + assignments.csv por iteración |

Checks de `audit_feasibility`:
- `served_exactly_once` — todos los clientes servidos exactamente 1 vez.
- `route_capacity_violations` — `demand > capacity` por ruta.
- `route_length_violations` — `reconstructed_scaled_distance > Length + tol`.
- `da_radius_violations` — `dist_scaled(h,j) > R` para asignación DA.
- `binding_violations` — desde parser flags.
- `penalty_distance_suspected` — `solver_distance_scaled > max(1e6, 1000*Length)`.

---

## 10. Checks a-priori (safety checks)

Ejecutados ANTES de aceptar un corte en `select_forbidden_assignments`:

**1. Stranding check (baseline y todos los políticas):**
```python
client_has_service_option(client_id, active_depots, geometry, R, forbidden_after_cut)
= any((h,j) not in forbidden for h in active) OR any(dist_scaled(h,j) <= R for h in active)
```

**2. `diagnose_repair_candidate` (Phase 7A, cuando policy != baseline):**

```python
same_depot_DA_risk       = dist_scaled(depot_id, client_id) <= R
length_serviceable       = exists h: dist_scaled(h,j)<=R  OR  (h,j)∉forbidden AND 2*dist(h,j)<=Length
safe_for_capacity_release = not same_depot_DA_risk
safe_for_length_serviceability = length_serviceable
```

Políticas:

| Política | Rechaza si |
|---|---|
| `baseline` | solo strands_client |
| `safe_length` | no length_serviceable_after_cut |
| `safe_capacity_release` | same_depot_DA_risk |
| `safe_both` | cualquiera de los anteriores |

---

## 11. Outputs existentes

### `outputs/phase6_sample20_baseline`
- **Estado:** incompleto — 7/20 filas (stall en fila 228 por timeout).
- **Tiene:** checkpoint.csv + subdirectorios por instancia (audit.json, routes.csv, assignments.csv).
- **No tiene:** consolidated.csv, summary.json, summary.md (batch no completó).
- **Filas completadas:** 51, 54, 61, 65, 178, 191, 209.
- **Statuses:** FEASIBLE:4, REPAIR_INFEASIBLE:3.

### `outputs/phase7_sample20_safe_both`
- **Estado:** incompleto — 7/20 filas (mismas filas, mismo stall en 228).
- **Misma estructura que baseline.**
- **Statuses:** FEASIBLE:4, REPAIR_INFEASIBLE:3 (mismas filas).

### `outputs/smoke_phase7_sample5`
- **Estado:** completo — 5/5 filas (settings: 5s/1run/3iter, safe_both).
- **Tiene:** checkpoint.csv, consolidated.csv, consolidated.xlsx, summary.json, summary.md.
- **Filas:** 51 FEASIBLE, 228 STUCK_NONCAPACITY, 457 FEASIBLE, 501 FEASIBLE, 563 FEASIBLE.
- **Notable:** fila 228 `r30x5a-1.dat` → STUCK_NONCAPACITY (ruta de longitud infeasible,
  2 candidatos rechazados por no_length_feasible_alternative).

### `outputs/diag_row5`
- **Estado:** completo — 2 iteraciones (it_00, it_01) sobre `r40x5b-1.dat`.
- **Tiene:** audit.json, routes.csv, assignments.csv, **solution.png** (con plots).
- **Status it_00:** RELAXED_INFEASIBLE, policy=None (baseline por defecto).
- **Status it_01:** RELAXED_INFEASIBLE, repair_candidate_policy=None, selected=[].
- **Nota:** `repair_candidate_policy` en audit JSON aparece como `None` — indica que
  esta corrida fue antes de Phase 7A o con settings que no guardaban el campo.

### Outputs adicionales (no en lista original, pero relevantes)

`outputs/phase6_sample20_baseline_fast` y `outputs/phase7_sample20_safe_both_fast`:
- **Estado:** completos — 20/20 filas (settings: 5s/1run, fast smoke).
- **Tienen:** checkpoint.csv, consolidated.csv, consolidated.xlsx, summary.json, summary.md.
- **16 instancias** por corrida (algunas filas comparten instancia, no se duplican).

`outputs/phase7a_sample20_fast_comparison.md`:
- Tabla comparativa baseline vs. safe_both (fast settings, k=20).
- FEASIBLE: 12 baseline = 12 safe_both.
- REPAIR_INFEASIBLE: 4 baseline vs 5 safe_both (fila 407 cambia MAX_ITER → REPAIR_INFEASIBLE).
- `n_length_invalid_cut = 18` en safe_both (filtro activo).

---

## 12. Comandos usados (verificados o inferidos)

```bash
# Smoke Phase 7, k=5 (verified via checkpoint)
.venv/bin/python scripts/run_random_sample.py \
  --k 5 --seed 42 --seconds 5 --runs 1 --max-iter 3 \
  --repair-policy safe_both --run-id smoke_phase7_sample5

# Long baseline k=20 (partial, stalled row 228)
.venv/bin/python scripts/run_random_sample.py \
  --k 20 --seed 42 --seconds 30 --runs 3 --max-iter 5 \
  --run-id phase6_sample20_baseline

# Long safe_both k=20 (partial, stalled row 228)
.venv/bin/python scripts/run_random_sample.py \
  --k 20 --seed 42 --seconds 30 --runs 3 --max-iter 5 \
  --repair-policy safe_both --run-id phase7_sample20_safe_both

# Fast comparison k=20 (complete)
.venv/bin/python scripts/run_random_sample.py \
  --k 20 --seed 42 --seconds 5 --runs 1 --max-iter 3 \
  --run-id phase6_sample20_baseline_fast

.venv/bin/python scripts/run_random_sample.py \
  --k 20 --seed 42 --seconds 5 --runs 1 --max-iter 3 \
  --repair-policy safe_both --run-id phase7_sample20_safe_both_fast

# Row 5 diagnóstico (con plots)
.venv/bin/python scripts/run_row.py \
  --row 5 --seconds 30 --runs 3 --max-iter 5 --run-id diag_row5
```

---

## 13. Estado de tests

### py_compile — verificado ahora

Archivos compilados sin error:
```bash
.venv/bin/python -m py_compile \
  src/lorp_fsd/repair.py \
  src/lorp_fsd/runner.py \
  src/lorp_fsd/artifacts.py \
  src/lorp_fsd/batch.py \
  tests/test_phase7_repair_safety.py \
  tests/test_repair_savings.py
# → ALL_OK
```

### Pytest targeted — verificado ahora

```bash
.venv/bin/pytest tests/test_repair_savings.py tests/test_phase7_repair_safety.py -v -q
# → 15 passed in 1.74s
```

Desglose:
- `test_repair_savings.py`: 9 tests (savings formula, weighted, candidatos por depósito, selection, strand check, feasibility checker).
- `test_phase7_repair_safety.py`: 6 tests unitarios + 1 integration (`@pytest.mark.integration`, omitido en runs no-integration).

### Pytest full (no integration) — verificado ahora

```bash
.venv/bin/pytest -q -m "not integration"
# → 193 passed, 32 deselected in 1.53s
```

**NOTA:** versión anterior de este handoff decía 225 passed. Hoy son 193 passed.
La diferencia puede ser por tests removidos o reorganización de suite.
Los 32 deselected son los tests marcados `@pytest.mark.integration`.

---

## 14. Bugs conocidos / riesgos

| # | Severidad | Descripción |
|---|---|---|
| 1 | Alta | Sin repo git propio en `lor-v3`. Todo el desarrollo es sin historia. Si se borra el directorio, se pierde todo. |
| 2 | Alta | Fila 228 (`r30x5a-1.dat`) causa stall de varias horas en runs de 30s/3runs. Bloquea batch completo. |
| 3 | Alta | No existe per-row timeout en batch. Un solo row problemático bloquea todo el experimento overnight. |
| 4 | Media | `outputs/phase6_sample20_baseline` y `outputs/phase7_sample20_safe_both` incompletos (7/20). No tienen consolidated.csv ni summary.json. |
| 5 | Media | `safe_both` puede rechazar todos los candidatos disponibles → `REPAIR_INFEASIBLE` prematuro (ej. fila 407 en fast comparison). |
| 6 | Media | No existe `repair_trace.csv`. No hay trazabilidad temporal de qué pares se añadieron en qué iteración. |
| 7 | Baja | `diag_row5` muestra `repair_candidate_policy: None` en audit JSON. Posiblemente corrida pre-Phase 7A o sin field en schema antiguo. |
| 8 | Baja | Batch sin `--plots` → no hay PNGs en sample20. Solo `diag_row5` tiene plots. |
| 9 | Baja | `capacity_not_freed_count` es diagnóstico simple (detecta si pair rechazado reaparece como DA mismo depósito). No es atribución causal completa. |
| 10 | Baja | `max_repair_attempts` existe en firma pero siempre vale 1 y no tiene lógica interna. Campo reservado. |

---

## 15. Próximas 5 acciones recomendadas antes de 10:30

**Acción 1: Crear repo git propio (≤5 min)**
```bash
cd /Users/apena/lor-v3
git init
git add src tests scripts docs pyproject.toml README.md results_MILP.xlsx .gitignore
# No agregar outputs/, .venv/, pipeline_out/, __pycache__/
git commit -m "Phase 7A complete: repair safety diagnostics"
```

**Acción 2: Leer resumen de fast comparison existente (0 min, ya existe)**
```bash
cat /Users/apena/lor-v3/outputs/phase7a_sample20_fast_comparison.md
# Tabla completa baseline vs safe_both k=20, fast settings
```

**Acción 3: Generar consolidated.csv de los runs parciales existentes (sin re-solver)**
```bash
cd /Users/apena/lor-v3
.venv/bin/python - <<'PY'
import csv, collections
for label, path in [
    ("phase6_baseline",    "outputs/phase6_sample20_baseline/checkpoint.csv"),
    ("phase7_safe_both",   "outputs/phase7_sample20_safe_both/checkpoint.csv"),
    ("smoke_phase7_k5",    "outputs/smoke_phase7_sample5/checkpoint.csv"),
]:
    rows = list(csv.DictReader(open(path)))
    statuses = collections.Counter(r['status'] for r in rows)
    t = sum(float(r['solve_time_total']) for r in rows)
    print(f"\n{label}: {len(rows)} filas, {t:.0f}s total")
    print(dict(statuses))
PY
```

**Acción 4: Implementar per-row timeout mínimo en batch (si se va a correr 30s tonight)**

Agregar en `batch.py → run_rows()` alrededor del `run_row_from_excel(...)`:
```python
import signal
# ... o usar multiprocessing.Process con timeout
```
Esto es el único cambio que desbloquea runs overnight seguros. Sin esto, fila 228
vuelve a bloquear cualquier sample grande con 30s/3runs.

**Acción 5: Decidir GO/NO-GO para full Excel overnight**

GO requiere:
- Per-row timeout implementado (Acción 4).
- Test de la fila 228 con timeout de 2 min → confirma que no bloquea.

NO-GO si timeout no implementado.

---

## Frase clave para la reunión

> No se borran clientes. El repair crea restricciones de routing temporales
> `(depot_id, client_id)` que se pasan al siguiente rebuild de PyVRP.
> Phase 7A agrega un filtro a priori: candidatos que dejarían a un cliente
> sin opción de DA ni de ruta singleton son rechazados antes de aplicar el corte.
> El problema permanece que no hay garantía de liberación de capacidad agregada
> hasta el siguiente solve.
