# Shared depot capacity handled by capacity-relaxed build + ex-post audit + savings repair

The MILP enforces depot capacity over **both** service modes:
`demand_routing_i + demand_DA_i ≤ Cap_i`. PyVRP cannot represent a capacity shared between
a depot's routing vehicles and its DA assignments. We therefore build the model
**capacity-relaxed** — each open depot gets routing vehicles totalling ~`Cap_i`
(`floor(Cap_i/Q)` full + residual) **and** independent DA options — so the first solve may
exceed `Cap_i` and be super-optimal. An ex-post audit recombines routing + DA per depot,
computes `excess`, and a savings-based repair loop forbids routing assignments on
overloaded depots, rebuilds, and re-solves until feasible or a stop condition.

**Considered options:** a full MILP/LP assignment layer or a metaheuristic over depot
configurations would model the constraint directly, but reintroduce the solver complexity
PyVRP was meant to avoid. The relax-and-repair loop is best understood as an external
lazy-constraint / logic-based-Benders scheme: PyVRP solves the routing subproblem, the
audit adds combinatorial cuts the solver cannot express.

**Consequence:** the first-pass metric is `RELAXATION_DEVIATION`, not `GAP`; `GAP` is
reported only after a repaired feasible solution. Repair cuts must stay **valid** — they
must not strand a mandatory client (see ADR `0004`). Moving a client from routing to DA at
the **same** depot does not free capacity, so capacity is re-judged only after each rerun.
