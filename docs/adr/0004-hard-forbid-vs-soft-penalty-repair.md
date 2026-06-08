# Repair baseline is hard routing-forbidding; soft-penalty and tabu are opt-in modes

The v3 baseline repair adds `(depot_id, client_id)` pairs to
`forbidden_routing_assignments`; the next rebuild creates no routing edge for those pairs.
It is a hard structural restriction — not a soft cost penalty and not a deletion of arcs
from a live model — and the forbidden set is monotonic for a row. The client is never
deleted; it may still be served by DA or routed elsewhere. This is simple, deterministic,
and easy to test, and it is what all current results were produced with.

**The trade-off (Phase 8):** hard forbidding can over-constrain — a pair removed for
capacity can eliminate the only length-feasible service for a mandatory client (the row-5
`(4,18)` case) or trigger premature `REPAIR_INFEASIBLE` (row 407). Phase 8 therefore adds
**opt-in** `repair_mode` values: `soft_penalty` (keep the arc, add a search-only penalty so
PyVRP still uses it if nothing better exists) and `tabu_penalty` (penalize with a
tenure/expiry and aspiration). Hard forbidding stays the default baseline.

**Consequence — non-negotiable:** the penalty exists **only** in the PyVRP search edge cost
(duration channel); it never touches the distance channel that drives the `Length`
constraint, and the **reported objective is always reconstructed from geometry**, never
read from the penalized search cost. A `STUCK_NONCAPACITY` / `REPAIR_INFEASIBLE` result is
a heuristic limitation, never a claim of MILP infeasibility.
