# Lógica operacional de LoRP-FSD vía PyVRP

_Documento para el profesor. Explica el algoritmo solicitado y cómo lo
implementa nuestra versión v3. No describe el código interno; describe la
lógica de modelado y reparación._

Fecha: 2026-06-08

---

## 1. El algoritmo del profesor

El subproblema "asignar o rutear" multi-depósito se resuelve así:

1. Transformar el subproblema de asignación-o-ruteo multi-depósito en un
   **MD-VRP** (Multi-Depot VRP).
2. Resolver el MD-VRP con **depósitos sin capacidad** (uncapacitated depots).
3. Verificar violación de capacidad de depósito. Si **no** hay violación,
   **detenerse**. Si la hay, ir al Paso 4.
4. Para cada depósito con violación de capacidad:
   1. Calcular el **ahorro de costo** asociado a remover cada cliente servido
      por ruteo.
   2. Ordenar los clientes según su ahorro de costo.
   3. Remover arcos activos (entrante y saliente) de la lista de clientes
      hasta que la capacidad del depósito deje de excederse.
5. Crear un nuevo grafo y volver al Paso 2.

---

## 2. Cómo lo mapea nuestra implementación

### 2.1 Punto de partida

- Partimos de una **fila del Excel MILP** (`results_MILP.xlsx`, hoja
  `LoRP-FSD`) y de la instancia `.dat` correspondiente.
- **Fijamos los depósitos y tamaños seleccionados por el MILP.** No
  reoptimizamos la apertura de depósitos; tomamos la decisión estratégica del
  MILP como dada.
- Construimos un **MD-VRP con capacidad de depósito relajada** para PyVRP.

### 2.2 Qué significa "depósitos sin capacidad" aquí

- **"Uncapacitated depots"** significa que se relaja la **capacidad agregada
  del depósito** durante el solve de PyVRP.
- La **capacidad del vehículo** y la **longitud de ruta** **sí** se siguen
  verificando y respetando.
- La **DA (Direct Allocation / asignación directa)** se codifica como un
  vehículo artificial de un solo cliente. Importante: la DA real es una
  **asignación**, no una ruta; la codificación como "vehículo de un cliente"
  es solo un truco de modelado para que PyVRP la represente.

### 2.3 Después del solve (auditoría ex-post)

Tras resolver, parseamos la solución y **reconstruimos el costo LoRP real**.
Luego corremos una **auditoría ex-post** que verifica:

- cada cliente servido **exactamente una vez**,
- **capacidad del vehículo**,
- **longitud de ruta**,
- **radio de DA**,
- **binding de DA**,
- **capacidad de depósito** (ruteo + DA),
- **reconstrucción del objetivo** (que el costo reconstruido coincida con el
  costo esperado).

Si la capacidad de depósito está violada, comienza la **reparación**.

---

## 3. La reparación (Paso 4 del profesor)

- Los **candidatos** a reparación son **solo** los clientes servidos por
  **ruteo** desde depósitos sobrecargados.
- El **ahorro de costo** es el ahorro marginal de **distancia de ruta** al
  remover ese cliente de su ruta.
- Ordenamos por **ahorro ponderado**.
- **No** borramos al cliente ciegamente. La implementación actual **prohíbe el
  par de ruteo `(depósito, cliente)`** en el siguiente grafo.
- El cliente **permanece en el problema**: puede ser servido por **DA** o por
  **otro depósito** en la siguiente iteración.

### 3.1 Validación ex-ante (cortes seguros)

Antes de aplicar un corte, validamos para evitar cortes inseguros:

- **Stranding check**: que el cliente no quede sin ninguna opción de servicio.
- **Alternativa factible en longitud**: que exista una alternativa de servicio
  que respete la longitud de ruta.
- **Riesgo de DA en el mismo depósito (same-depot DA risk)**: importa porque
  pasar de ruteo a DA **en el mismo depósito** **no libera** capacidad de
  depósito — la demanda sigue contando contra ese depósito. Cortar en ese caso
  no resolvería la sobrecarga.

Luego reconstruimos el grafo de PyVRP y resolvemos de nuevo (volver al Paso 2).

---

## 4. Clasificación de resultados

Cada fila termina en uno de estos estados:

- **FEASIBLE** — todas las verificaciones pasaron y el GAP es válido.
- **REPAIR_INFEASIBLE** — la reparación heurística falló; **no** es prueba de
  infactibilidad matemática.
- **STUCK_NONCAPACITY_VIOLATION** — queda una violación que **no** es de
  capacidad y que la reparación de capacidad no puede arreglar.
- **MAX_ITERATIONS** — se agotó el presupuesto de iteraciones de reparación.
- **TIMEOUT** — la guarda de tiempo de pared a nivel de fila detuvo la fila.
- **ERROR** — error interno.

### 4.1 Sobre el GAP

- El **GAP se reporta solo para filas FEASIBLE**.
- Un **GAP negativo** solo es aceptable por **suboptimalidad o redondeo del
  MILP**; de lo contrario, señala una **inconsistencia de modelado** y debe
  marcarse (flag).

---

## 5. Resultados actuales (resumen)

- La **fila 0** reproduce el MILP de forma aproximadamente exacta.
- En la **muestra rápida de 20 filas**: **12 filas FEASIBLE**.
- **GAP medio de las factibles ≈ 0.6%**.
- **Sin flags de GAP negativo.**
- La **corrida completa sigue pendiente**, pero ahora existe el **timeout por
  fila**, lo que la hace segura de lanzar.

---

## 6. Hoja de ruta (roadmap)

1. **Reporte HTML por fila** (ahora) — superficie de presentación académica.
2. **Corrida rápida completa** (fast full run).
3. **Reparación con penalización suave** (soft penalty).
4. **Tabu tenure** (memoria tabú en la reparación).
5. **Corrida completa más larga**.
