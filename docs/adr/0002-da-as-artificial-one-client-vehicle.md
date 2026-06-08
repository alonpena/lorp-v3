# Direct Allocation modelled as a one-client, zero-return artificial PyVRP vehicle

In the MILP, Direct Allocation is a binary assignment `A[client][depot] ∈ {0,1}` with
one-way cost `F_A · dist_scaled(depot, client)`, no return arc, no client-client travel,
and no vehicle fixed cost. PyVRP has no assignment variable — everything is a route — so
each feasible `(depot, client)` pair with `dist_scaled ≤ R` is encoded as an artificial
PyVRP vehicle/profile that visits exactly that one client: capacity = the client's demand,
outbound edge cost `round(F_A · dist_scaled · 1e4)`, return edge `distance=0, duration=0`.

**Why bound to one client:** a one-client capacity alone does not stop the DA vehicle from
serving a different, closer client of equal-or-smaller demand whose `dist_scaled > R` —
silently breaking the radius rule. The builder restricts the per-pair profile's
reachability (every other client sits at PyVRP's 2⁴⁴ missing-edge sentinel), and the
parser independently rejects any DA route that is not length-1, the correct client, and
within `R`, flagging `DA_ASSIGNMENT_BINDING_VIOLATION`.

**Consequence:** reported DA cost is always the one-way C/MILP assignment cost,
reconstructed ex-post; the artificial return arc and any technical PyVRP arcs never enter
the reported objective.
