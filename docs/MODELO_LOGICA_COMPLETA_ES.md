# LoRP-FSD vía PyVRP — lógica completa del modelo y decisiones

_Documento técnico exhaustivo en español. Explica, sin omitir detalles, qué
hace el modelo, cómo está modelado, y por qué se tomó cada decisión. Pensado
para el profesor y para cualquier persona que continúe el trabajo._

Fecha: 2026-06-08 · Rama: `phase9-soft-penalty-tabu`

---

## 0. Resumen en una frase

Tomamos cada fila del Excel del MILP (que ya decidió qué depósitos abrir y de
qué tamaño), reconstruimos esa decisión como un **MD-VRP con capacidad de
depósito relajada**, lo resolvemos con PyVRP, **reconstruimos el costo real**
desde la geometría, **auditamos** todas las restricciones, y si un depósito
queda sobrecargado aplicamos una **reparación por ahorros** que hoy usa
**penalización suave con memoria tabú** para empujar clientes fuera del ruteo de
ese depósito.

---

## 1. El problema LoRP-FSD

LoRP-FSD = Location-Routing Problem con Facility Sizing y Direct Shipping. Cada
cliente debe ser servido de **una** de dos formas:

- **Ruteo (routing):** un vehículo sale de un depósito, visita varios clientes
  en una ruta, y vuelve. Costo proporcional a la distancia de la ruta por un
  factor `F_R`.
- **Asignación directa (DA, Direct Allocation / Direct Shipping):** se sirve al
  cliente directamente desde un depósito, sin formar ruta con otros. Costo
  proporcional a la distancia depósito→cliente (ida) por un factor `F_A`. Solo
  válida si la distancia ≤ radio `R`.

Restricciones principales:

- Cada cliente servido **exactamente una vez**.
- **Capacidad de vehículo** `Q` por ruta.
- **Longitud de ruta** ≤ `Length` (distancia total de la ruta).
- **Radio de DA** ≤ `R`.
- **Capacidad de depósito** `Cap_i`: la demanda total servida desde el depósito
  `i` (ruteo + DA) no puede exceder `Cap_i`.

El MILP original resuelve **todo a la vez** (qué depósitos abrir, su tamaño, y
cómo servir). Nosotros **no** reoptimizamos la apertura: tomamos esa decisión
del MILP y solo resolvemos el subproblema de "asignar o rutear".

---

## 2. Punto de partida: fila Excel + instancia `.dat`

- **`results_MILP.xlsx`, hoja `LoRP-FSD`:** una fila por instancia con los
  parámetros (`F_R`, `F_A`, `R`, `Length`, `VFX`), la cota del MILP (`UB`, `LB`,
  `status`, `gap`), el desglose de costo del MILP (ruteo, DA, vehículos,
  depósitos), y qué depósitos abrió y de qué tamaño.
- **Instancia `.dat`:** coordenadas de depósitos y clientes, demandas, capacidad
  de vehículo `Q`, costo fijo de vehículo, `problemID`.

`problemID = 0` (escalado de Arslan) es el único soportado hoy; cualquier otro
levanta `NotImplementedError` (decisión consciente: no adivinar escalados que no
se validaron).

---

## 3. Fijación del diseño de instalaciones

`build_facility_design` toma de la fila del MILP **qué depósitos están abiertos
y con qué capacidad** y los fija. A partir de aquí el problema es: con estos
depósitos y tamaños dados, ¿cómo sirvo a los clientes minimizando costo? Esto es
exactamente el subproblema que el profesor pidió transformar a MD-VRP.

---

## 4. Escalado y enteros (canal de distancia)

PyVRP trabaja con **enteros**. Convertimos las distancias continuas escaladas a
enteros multiplicando por `PYVRP_INT_SCALE = 10_000` y redondeando.

- `route_max_distance_int = round(Length * 10_000)`. Con `Length = 100` esto es
  `1_000_000`.
- Regla dura de modelado: **nunca dividir por `scale`** al reconstruir costo. El
  escalado es solo para integerizar la búsqueda; el costo real se reconstruye
  desde la geometría escalada continua.

---

## 5. Transformación a MD-VRP relajado (el corazón del modelo)

Construido en `pyvrp_builder.build_relaxed_model`. Decisiones de codificación
(decisiones asentadas #13/#14):

### 5.1 Dos canales: distancia y duración

Cada arista de PyVRP lleva **dos** números:

- **Canal de distancia** = `round(dist_escalada * 10_000)`. Este canal alimenta
  el límite de longitud de ruta `max_distance`. Controla la **factibilidad de
  longitud**.
- **Canal de duración** = `round(F * dist_escalada * 10_000)`, donde `F = F_R`
  para ruteo y `F = F_A` para la ida de DA (el retorno de DA cuesta 0). Con
  `unit_distance_cost = 0` y `unit_duration_cost = 1`, **el objetivo que PyVRP
  minimiza es la suma de duraciones**, es decir el costo ponderado.

Por qué dos canales: la longitud de ruta se mide en distancia geométrica pura,
pero el costo se mide en distancia × factor. Separarlos permite respetar
`Length` exactamente mientras se optimiza costo ponderado. **Esta separación es
la clave que hace posible la penalización suave de la Fase 9** (ver §10).

### 5.2 Nodos

- Un nodo depósito por cada depósito abierto.
- Un nodo cliente por cada cliente, marcado `required=True` (debe ser servido
  → fuerza "servido exactamente una vez").

### 5.3 Vehículos de ruteo

Por cada depósito abierto se crea un **perfil de ruteo** con aristas
depósito↔cliente y cliente↔cliente entre los clientes alcanzables.

La capacidad `Cap_i` del depósito se descompone en vehículos
(`routing_vehicle_specs`): `floor(Cap_i / Q)` vehículos "full" de capacidad `Q`
más, si sobra, un vehículo "residual" con la capacidad restante. Aritmética
entera ⇒ la capacidad total de ruteo del depósito es `<= Cap_i`. Cada vehículo
lleva `max_distance = route_max_distance_int` (límite de longitud) y un costo
fijo de vehículo integerizado (`veh_fixed * VFX * 10_000`).

### 5.4 DA como "vehículo artificial de un cliente"

Cada opción DA factible `(depósito, cliente)` (distancia ≤ `R`) se modela como
un **perfil propio** con exactamente dos aristas: ida (costo ponderado `F_A`) y
retorno (costo 0), y **un** vehículo de capacidad igual a la demanda del
cliente, disponible una vez. Así ese vehículo solo puede servir a ese cliente.

**Aclaración conceptual importante:** la DA real es una **asignación**, no una
ruta. El "vehículo de un cliente" es un truco de modelado para que PyVRP la
represente. En la reconstrucción de costo y en la auditoría la tratamos como
asignación directa, no como ruta.

### 5.5 "Depósitos sin capacidad" (la relajación)

El MD-VRP del profesor se resuelve con **depósitos sin capacidad**. Aquí eso
significa: **se relaja la capacidad agregada del depósito** durante el solve.
PyVRP no puede modelar nativamente "la suma de ruteo + DA desde el depósito `i`
no excede `Cap_i`" porque ruteo y DA usan vehículos/perfiles independientes. Por
eso permitimos que esa suma exceda `Cap_i` durante el solve y la **recuperamos
después** con la reparación (§9–§11).

Lo que **sí** se sigue respetando durante el solve: capacidad de vehículo `Q` y
longitud de ruta `Length`. Solo la capacidad **agregada de depósito** se relaja.

---

## 6. Resolución con PyVRP

`runner._solve_multi`: se resuelve `num_solve_runs` veces con semillas distintas,
cada una con `MaxRuntime(seconds_per_run)`. Se elige la mejor solución con la
clave `(0 si factible si no 1, costo)` → **se prefiere factible, y entre
factibles el de menor costo**. Es una metaheurística estocástica, de ahí las
corridas múltiples.

---

## 7. Parseo de la solución

`solution_parser.parse_solution` traduce las rutas de PyVRP de vuelta a
decisiones semánticas LoRP:

- Distingue rutas de **ruteo** de asignaciones **DA** mirando el tipo de
  vehículo / perfil.
- Para cada ruta de ruteo guarda la **distancia reconstruida desde geometría**
  (`reconstructed_scaled_distance`, autoritativa) y el **costo ponderado
  reconstruido** `reconstructed_weighted_cost = F_R * distancia_reconstruida`.
- Para cada DA guarda la distancia escalada y `cost = F_A * dist` (solo ida).

Clave: la distancia y el costo **no** se leen del objetivo entero de PyVRP; se
**recomputan desde la geometría**. Esto es lo que aísla el costo reportado de
cualquier penalización de búsqueda (§10).

---

## 8. Reconstrucción del costo (unidades comparables al MILP)

`cost_reconstruction.reconstruct_cost` (decisión asentada #15, unidades mixtas):

```
Z = Cost_Routing(escalado)  +  Cost_Direct_All(escalado)
    + Cost_Vehicles(crudo)  +  Cost_Depots(crudo)
```

- `Cost_Routing` = Σ `F_R * distancia_ruta_reconstruida` (escalado).
- `Cost_Direct_All` = Σ `F_A * dist(depósito, cliente)` (escalado, solo ida).
- `Cost_Vehicles` = nº rutas de ruteo usadas × `veh_fixed * VFX` (crudo).
- `Cost_Depots` = costo fijo del diseño de depósitos (crudo).

Regla: ruteo y DA en distancias escaladas; vehículos y depósitos en crudo;
nunca dividir por `scale`. Este `Z` es el `Z_PyVRP` que se compara contra `UB`
del MILP.

---

## 9. Auditoría ex-post

Tras reconstruir, se auditan **todas** las restricciones (`capacity_audit`,
`feasibility`):

1. **Servido exactamente una vez** (todos los clientes, sin duplicados).
2. **Capacidad de vehículo** por ruta (`demanda_ruta ≤ Q`).
3. **Longitud de ruta** (`distancia_reconstruida ≤ Length`).
4. **Radio de DA** (`dist(depósito, cliente) ≤ R`).
5. **Binding de DA** (cada DA atada a un único cliente/depósito válido).
6. **Capacidad de depósito** = ruteo + DA por depósito (`demanda_total ≤
   Cap_i`). Aquí es donde se detecta el exceso que la relajación permitió.
7. **Reconstrucción del objetivo** (que el `Z` reconstruido sea coherente).

Un flag adicional, `penalty_distance_suspected`, detecta si PyVRP metió
distancias de penalización internas anómalas.

Si la capacidad de depósito está violada (algún `excess > 0`), comienza la
**reparación**.

---

## 10. Métrica de comparación y el GAP

`comparison_metric` (decisión asentada #15):

- Si la fila **no** es totalmente factible: `RELAXATION_DEVIATION = (UB − Z)/UB`
  (cuánto se desvió la relajación; informativo, no es un GAP válido).
- Si **es** totalmente factible: `GAP = (Z − UB)/UB`.
  - El `UB` del Excel está redondeado a 3 decimales; por eso un GAP negativo
    dentro de tolerancia (`1e-4` relativo) se **absorbe** y no se marca.
  - Un GAP negativo **mayor** que la tolerancia se marca como
    `NEGATIVE_GAP_MODELING_INCONSISTENCY`: solo es aceptable por
    suboptimalidad/redondeo del MILP; si aparece de otra forma, señala un error
    de modelado.

**El GAP solo se reporta para filas FEASIBLE.**

---

## 11. Reparación por ahorros (Paso 4 del profesor)

Cuando un depósito está sobrecargado (`repair.py`):

### 11.1 Candidatos

Solo los clientes servidos por **ruteo** desde depósitos **sobrecargados**. Un
cliente servido por DA, o por ruteo desde un depósito no sobrecargado, no es
candidato.

### 11.2 Ahorro (saving)

`compute_route_savings`: ahorro **marginal de distancia de ruta** al quitar al
cliente de su ruta. Cuatro casos:

- interno `c_m`: `d(p,c_m) + d(c_m,s) − d(p,s)`,
- primero `c1`: `d(depósito,c1) + d(c1,c2) − d(depósito,c2)`,
- último `ck`: `d(c_{k−1},ck) + d(ck,depósito) − d(c_{k−1},depósito)`,
- único cliente: `d(depósito,c1) + d(c1,depósito)`.

Se ordena por **ahorro ponderado** `F_R * saving` (mayor primero) y se van
seleccionando clientes hasta cubrir el exceso del depósito.

### 11.3 Validación ex-ante (cortes seguros) — políticas

Antes de actuar sobre un candidato se diagnostica (`diagnose_repair_candidate`)
y, según la política, se rechaza:

- **`baseline`**: solo evita **stranding** (no dejar al cliente sin ninguna
  opción de servicio).
- **`safe_length`**: además exige que tras el corte el cliente tenga una
  **alternativa factible en longitud** — DA dentro de `R`, o una ruta unitaria
  con `2·dist ≤ Length`.
- **`safe_capacity_release`**: además rechaza el **riesgo de DA en el mismo
  depósito**: si tras quitar el ruteo `(i,j)` el cliente `j` puede ser
  direct-allocated desde el **mismo** depósito `i`, la capacidad agregada de `i`
  **no se libera** (la demanda sigue contando contra `i`). Cortar ahí no resuelve
  la sobrecarga.
- **`safe_both`** (usado en los experimentos): aplica ambos filtros.

Los rechazos se registran con su razón (`same_depot_DA_risk`,
`no_length_feasible_alternative`, `strands_client`).

### 11.4 Qué se hace con el candidato seleccionado — modos de reparación (Fase 9)

`penalty_tabu.RepairModeState` decide **cómo** el siguiente grafo reacciona a la
selección. **No borra al cliente del problema** en ningún modo; el cliente
permanece y puede servirse por DA o por otro depósito.

- **`hard_forbid` (línea base histórica):** el par `(depósito, cliente)` se
  **elimina** del grafo reconstruido (sin arista de ruteo desde ese depósito).
- **`soft_penalty`:** el par **sigue factible**, pero se le suma una
  **penalización grande al canal de duración/costo** (no al de distancia). El
  solver lo evita salvo que sea imprescindible.
- **`tabu_penalty` (DEFAULT operacional):** penalización suave + **tenencia
  tabú**: cada par penalizado lleva una cuenta regresiva; al llegar a 0 la
  penalización se retira salvo que el par se vuelva a seleccionar.

#### Cómo se aplica la penalización (detalle fino)

- Valor: `penalty = factor * route_max_distance_int` (con `factor = 100` y
  `Length = 100`, eso es `100 * 1_000_000 = 100_000_000`). Es enorme a propósito:
  hace que una sola visita penalizada cueste muchos "presupuestos de longitud",
  así el solver casi nunca usa el par, pero **sigue siendo factible** si no hay
  alternativa.
- Se cobra **una vez por llegada** al cliente penalizado en el perfil de ese
  depósito: se suma a todas las aristas cuyo **destino** es ese cliente
  (depósito→cliente y cliente→cliente). Como una ruta visita al cliente una sola
  vez, paga la penalización una sola vez, sin importar su posición en la ruta.
- **Solo toca el canal de duración.** El canal de distancia queda intacto ⇒ la
  factibilidad de longitud de ruta **no cambia**.

#### Por qué la penalización NO contamina el costo reportado

El costo reportado se reconstruye desde la **geometría** (§7–§8):
`reconstructed_weighted_cost = F_R * distancia_geométrica`. La penalización vive
en el objetivo entero de PyVRP, que **no** se usa para reportar. Verificado por
test: modelo penalizado vs base tienen **matriz de distancia idéntica** y `+P`
solo en la duración de las aristas que llegan al cliente penalizado.

#### Tabú: tenencia y expiración

Al seleccionar un par en `tabu_penalty`: `penalty[(i,j)] = valor` y
`tabu[(i,j)] = tenencia` (3 por defecto). Al inicio de cada iteración se
decrementa la tenencia; al llegar a 0 se elimina la penalización (evento
`tabu_expire`) salvo que el par se haya vuelto a seleccionar. Es una memoria
tabú **simple por par**, sin criterio de aspiración. Limitación documentada: un
par cuya penalización expira puede volver a seleccionarse después.

### 11.5 Por qué penalización en vez de prohibición

Prohibir es irreversible y puede empujar al cliente a una violación que no es de
capacidad (p. ej. dejarlo sin ruteo y forzar una solución peor → estado
`STUCK_NONCAPACITY`). La penalización mantiene la opción viva pero cara, dando al
solver libertad para encontrar una mejor reconstrucción. En la prueba de 10
filas esto subió las factibles de 7 a 8 y eliminó un caso STUCK.

---

## 12. El bucle iterativo y los estados de terminación

`runner.run_row`:

```
estado = RepairModeState(modo, penalización, tenencia)
para it en 0 .. max_repair_iterations:
    estado.tick(it)                       # decrementa/expira tabú
    forbidden, penalty = estado.builder_args()
    construir MD-VRP relajado (forbidden, penalty)
    resolver (num_solve_runs × seconds)   # preferir factible, luego menor costo
    parsear → reconstruir costo → auditar capacidad y factibilidad
    guardar artefactos (+ plots)
    si totalmente factible: PARAR (FEASIBLE, reportar GAP)
    seleccionar reparación por ahorros (política)
    si la reparación es infactible: PARAR (REPAIR_INFEASIBLE)
    si no hay nada que seleccionar: PARAR (STUCK_NONCAPACITY_VIOLATION)
    si es la última iteración: PARAR (MAX_ITERATIONS)
    estado.apply(seleccionados, it)       # forbidden / penalty / penalty+tabú
```

### Clasificaciones finales

- **FEASIBLE** — todas las verificaciones pasaron; el GAP es válido.
- **REPAIR_INFEASIBLE** — el exceso de un depósito no se puede cubrir con cortes
  seguros. **No** es prueba de infactibilidad matemática; es fallo de la
  heurística.
- **STUCK_NONCAPACITY_VIOLATION** — la capacidad ya está bien, pero queda una
  violación que **no** es de capacidad (longitud, radio) que la reparación de
  capacidad no resuelve.
- **MAX_ITERATIONS** — se agotó el presupuesto de iteraciones.
- **TIMEOUT** — la guarda de tiempo de pared por fila detuvo la fila (existe en
  el runner de lotes; cada fila corre en un proceso hijo).
- **ERROR** — error interno; la fila se registra como ERROR sin abortar el lote.

---

## 13. Artefactos generados por fila

`outputs/<run_id>/<instancia>/`:

- `report.json`, `report.md` — resumen estructurado y legible.
- `cost-breakdown.csv` — MILP vs PyVRP por componente.
- `depot_usage.csv` — demanda ruteo/DA/total, capacidad, exceso por depósito.
- `iteration_summary.csv` — una fila por iteración (estado, costo, exceso,
  conteos de forbidden/seleccionados/rechazados).
- `repair_trace.csv` — traza de reparación; en Fase 9 incluye `repair_mode`,
  `penalty_value`, `tabu_remaining`, `saving`, `demand` y eventos
  `hard_forbid` / `soft_penalty` / `tabu_add` / `tabu_expire`.
- `iteration_XX_audit.json`, `iteration_XX_routes.csv`,
  `iteration_XX_assignments.csv` — detalle por iteración.
- `iteration_XX_instance.png`, `iteration_XX_solution.png` — gráficos.
- `index.html` (opcional, generado aparte) — reporte estático navegable.

---

## 14. Mapa explícito al algoritmo del profesor

1. Transformar el subproblema asignar-o-rutear en un MD-VRP relajado → §5.
2. Resolver el MD-VRP con depósitos sin capacidad → §5.5 + §6.
3. Auditar capacidad de depósito ex-post; si no hay violación, parar → §9.
4. Para cada depósito sobrecargado: calcular ahorro por cliente, ordenar, y
   quitar arcos hasta no exceder capacidad → §11 (con validación segura y, en
   Fase 9, penalización/tabú en vez de borrado permanente).
5. Reconstruir el grafo y volver al paso 2 → §12.

---

## 15. Decisiones de modelado clave (y por qué)

- **No reoptimizar apertura de depósitos:** el MILP ya decidió; nuestro alcance
  es el subproblema asignar-o-rutear, igual que pidió el profesor.
- **Dos canales (distancia/duración):** separa factibilidad de longitud de la
  optimización de costo, y habilita la penalización suave sin tocar longitud.
- **DA como vehículo de un cliente:** única forma de representar asignación
  directa dentro de PyVRP; tratada como asignación en costo/auditoría.
- **Relajar solo capacidad agregada de depósito:** es la única restricción que
  PyVRP no puede modelar nativamente; todo lo demás se respeta en el solve.
- **Reconstruir costo desde geometría, nunca desde el objetivo entero:** aísla
  el costo reportado del escalado y de las penalizaciones de búsqueda.
- **Penalización en duración, una vez por llegada, valor enorme:** casi-prohíbe
  manteniendo factibilidad; reversible vía tabú.
- **Políticas de corte seguro:** evitan cortes que no liberan capacidad
  (same-depot DA) o que dejan al cliente sin alternativa de longitud.
- **GAP solo en FEASIBLE; flag de GAP negativo:** disciplina para no reportar
  números inválidos ni esconder inconsistencias de modelado.
- **Timeout por fila en proceso hijo:** un solve que se cuelga no bloquea el
  lote.

---

## 16. Limitaciones actuales

- Falta la **corrida completa de todo el Excel**.
- La **interfaz/visualización** aún no muestra el `repair_mode` ni tiene una
  vista compacta por defecto.
- La **interfaz de congruencia C/PyVRP** no está cerrada.
- **Sin barrido de parámetros** de `penalty_factor` / `tabu_tenure` (solo
  100 / 3).
- **Sin búsqueda local** en el bucle de reparación.
- La memoria **tabú es simple** (por par, sin aspiración).
- `REPAIR_INFEASIBLE` y `MAX_ITERATIONS` siguen apareciendo en filas difíciles;
  la penalización suave no las resolvió dentro del presupuesto.
