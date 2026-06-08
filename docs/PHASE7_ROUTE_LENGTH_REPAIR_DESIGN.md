# Phase 7 Design — Valid Capacity Cuts and Route-Length-Aware Repair

Status: **Phase 7A implemented** as candidate safety checks + diagnostics.
Phase 7B backtracking / depot-level cuts / local search remain future work.

Current baseline before Phase 7A: Phases 1–6 complete; tests were passing at
**219 passed**. After Phase 7A implementation: **225 passed**.

This document consolidates agreed design points for
`STUCK_NONCAPACITY_VIOLATION`, valid cuts, length serviceability, true capacity
release, bounded backtracking, and future local search.

Do **not** run the full Excel yet.

---

## 1. Current v3 repair recap

Current v3 pipeline:

1. Build capacity-relaxed PyVRP model under fixed Excel facility design.
2. Use DA as one-way assignment:
   - outbound cost `F_A * dist_scaled(depot, client)`,
   - zero conceptual return,
   - no DA client-client travel,
   - no DA multitrip,
   - DA option bound to intended client.
3. Solve with PyVRP.
4. Parse semantic routing routes and DA assignments.
5. Reconstruct costs in continuous scaled units for routing/DA and raw units for
   fixed vehicle/depot costs.
6. Audit:
   - service exactly once,
   - aggregate depot capacity `demand_routing_i + demand_DA_i <= Cap_i`,
   - route length `route_dist_scaled <= Length`,
   - route vehicle capacity,
   - DA radius `dist_scaled <= R`,
   - DA binding,
   - penalty-distance diagnostics.
7. If fully feasible, return `FEASIBLE` and report `GAP`.
8. If aggregate capacity is violated, run savings repair:
   - detect overloaded depots,
   - generate candidates only from routing routes of overloaded depots,
   - compute marginal route saving,
   - rank by largest `weighted_saving = F_R * saving`,
   - greedily select candidates until nominal removed demand covers excess,
   - skip candidates that fail current service-option checker,
   - add selected `(depot_id, client_id)` to `forbidden_routing_assignments`,
   - rebuild and rerun.
9. If capacity is feasible but a non-capacity constraint fails, return
   `STUCK_NONCAPACITY_VIOLATION`.

Current checker in `feasibility.py` is service-existence only:

```python
has_routing = any((h, j) not in forbidden for h in active_depots)
has_DA = any(dist_scaled(h, j) <= R for h in active_depots)
serviceable = has_routing or has_DA
```

It does **not** check whether remaining routing depots can serve `j` within
`Length`, and it does **not** check whether forbidding routing actually releases
aggregate depot capacity.

---

## 2. Row 5 and `STUCK_NONCAPACITY_VIOLATION`

Canonical case:

- Row: `5`
- Instance: `r40x5b-1.dat`
- Known parameters: `F_A=0.5`, `R=40`, `Length=150.0`
- Iteration 0: depot 4 overloaded by about `+121`
- Repair forbade routing pairs including `(4, 18)`
- Iteration 1:
  - capacity feasible,
  - all clients still served,
  - route length infeasible.

Violating route:

```text
depot 3 -> client 18 -> depot 3
```

Diagnostics:

- reconstructed scaled distance: approximately `156.03`
- `Length = 150.0`
- violation: approximately `+6.03`

Client 18 facts:

- DA-infeasible from all depots: `dist_scaled(h,18) > R`.
- Depot 4 likely was the only depot with singleton routing feasibility for
  client 18: `2 * dist_scaled(4,18) ≈ 102.12 <= 150`.
- After forbidding `(4,18)`, PyVRP served client 18 from depot 3, where even the
  singleton round trip violates `Length`.

Conclusion: capacity repair worked, service stayed complete, but the cut `(4,18)`
removed the only length-feasible service option for mandatory client 18. This is
an unsafe repair cut, not automatically a solver or audit bug.

---

## 3. Observation 1: route-length violation means invalid/unsafe cut, not necessarily solver bug

PyVRP may treat `max_distance` as a penalized constraint in the returned solution.
If every client is mandatory and repair restrictions leave a client with no
length-feasible option, PyVRP may return the least-bad penalized route instead of
leaving the client unserved.

Therefore, a route-length violation after repair can mean:

```text
forbidden set made the subproblem length-infeasible for at least one mandatory client
```

It does **not** necessarily mean:

- builder `max_distance` bug,
- audit reconstruction bug,
- PyVRP parsing bug.

For row 5, reconstructed geometry and audit agree: route depot 3 -> client 18 ->
depot 3 has scaled distance about `156.03 > 150`. Root cause is the cut `(4,18)`,
which eliminated client 18's only length-feasible routing depot while no DA option
existed.

Phase 7 should treat this as candidate validity failure first, not as low-level
solver failure.

---

## 4. Observation 2: `forbidden_routing` may not release aggregate capacity

C/MILP capacity constraint is aggregate over service modes:

```python
demand_routing_i + demand_DA_i <= Cap_i
```

PyVRP construction is relaxed: routing and DA are separate service pools, then the
audit recombines them ex-post.

Current repair only does:

```python
forbidden_routing_assignments.add((i, j))
```

This forbids routing of client `j` from depot `i`, but it does **not** forbid DA
from depot `i`.

If `j` is DA-feasible from same overloaded depot `i`:

```python
dist_scaled(i, j) <= R
```

then PyVRP may reassign `j` to DA from the same depot after rerun.

Capacity effect:

```text
demand_routing_i decreases by demand_j
demand_DA_i      increases by demand_j
demand_total_i   unchanged
```

So the repair did **not** release real aggregate capacity from depot `i`.

Row 5 happened to release capacity because client 18 was DA-infeasible from all
depots. But for candidates DA-feasible from the overloaded depot, routing-only
forbid may be a false offload.

### Does `forbidden_routing` actually release capacity?

Phase 7 diagnostics should audit this for every selected repair candidate `(i,j)`:

1. Before rerun:

   ```python
   same_depot_DA_risk = dist_scaled(i, j) <= R
   ```

2. After rerun, inspect final assignment of `j`.
3. If `j` is assigned to DA from same depot `i`, mark:

   ```python
   capacity_not_freed = True
   ```

4. Record counts:

   - `same_depot_DA_risk_count`
   - `capacity_not_freed_count`
   - candidate-level `(i,j)` risk and outcome.

This audit decides whether Phase 7A can keep routing-only cuts or must introduce
stronger depot-level offload cuts.

---

## 5. Logic-based Benders / external lazy-constraint interpretation

Current loop:

```text
solve -> audit -> add restrictions -> rebuild -> solve
```

is not a native PyVRP callback and not a pure metaheuristic. It is best understood
as an external callback-like lazy-constraint loop, similar in spirit to
logic-based Benders / lazy constraint generation.

Interpretation:

- PyVRP solves a subproblem with a current set of allowed service assignments.
- The external master/audit checks constraints PyVRP cannot model natively,
  especially aggregate depot capacity:

  ```python
  demand_routing_i + demand_DA_i <= Cap_i
  ```

- When the audit detects a violation, the external loop adds combinatorial cuts,
  currently:

  ```python
  forbidden_routing_assignments.add((i, j))
  ```

Implication: cuts should be valid or at least safe for the original problem. A cut
should not remove the only feasible way to serve a mandatory client. In row 5,
`(4,18)` was unsafe because it removed the only length-feasible routing option for
client 18.

No PyVRP C++ internals or native callbacks are required. Phase 7 stays external:
solve, audit, reject/add restrictions, rebuild, solve.

---

## 6. Candidate validity pre-check for length serviceability

Main Phase 7A design: before adding repair candidate `(i,j)`, verify that client
`j` keeps at least one feasible service alternative after the cut.

Tentative forbidden set:

```python
forbidden_after_cut = current_forbidden | selected_so_far | {(i, j)}
```

Candidate `(i,j)` is length-serviceable after cut iff there exists an active depot
`h` such that either DA is feasible:

```python
dist_scaled(h, j) <= R
```

or routing singleton is feasible and not forbidden:

```python
(h, j) not in forbidden_after_cut
and 2 * dist_scaled(h, j) <= Length
```

Formal condition:

```python
exists h in active_depots such that:
    dist_scaled(h, j) <= R
    OR (
        (h, j) not in forbidden_after_cut
        and 2 * dist_scaled(h, j) <= Length
    )
```

Important nuances:

- `2 * dist_scaled(h,j) <= Length` guarantees that at least a singleton route
  depot `h -> j -> h` is length-feasible.
- It is a **necessary safety check**, not a guarantee that every multi-client
  route containing `j` will be length-feasible.
- If singleton feasibility exists, PyVRP has at least one valid routing option if
  it needs it.
- If no DA and no singleton-feasible routing option remains, candidate must be
  rejected before rerun.

Candidate rejection example:

```python
rejected_repair_candidates.add((4, 18, "no_length_feasible_alternative"))
```

For row 5, after forbidding `(4,18)`:

```text
has_DA = False
has_singleton_length_feasible_routing = False
```

So the pre-check would reject `(4,18)` before invoking PyVRP.

---

## 7. Capacity release validity / same-depot DA risk

Phase 7 must distinguish **nominal removed routing demand** from **real aggregate
capacity released**.

### Candidate risk flag

For capacity candidate `(i,j)` from overloaded depot `i`:

```python
same_depot_DA_risk = dist_scaled(i, j) <= R
```

If true, routing-only forbid may not offload the client from depot `i` because
same-depot DA remains allowed.

### Option 1 — keep `forbidden_routing_assignments`, restrict candidates

Keep current type:

```python
forbidden_routing_assignments: set[tuple[int, int]]
```

For capacity repair, prioritize or restrict candidates with:

```python
dist_scaled(i, j) > R
```

Meaning: client `j` is DA-infeasible from the overloaded depot `i`, so forbidding
routing from `i` prevents same-depot DA reabsorption.

Advantages:

- Minimal architectural change.
- Keeps current builder/parser/runner contract.
- Same-depot DA remains available outside capacity-offload cuts.
- Conservative and easy to test.

Disadvantages:

- Candidate pool may be too small.
- May mark repair infeasible even when a feasible solution exists by moving a
  DA-feasible client to another depot.
- Does not guarantee real offload when another mechanism reassigns demand in an
  unexpected way; still requires post-rerun audit.

### Option 2 — introduce `forbidden_depot_assignments`

New stronger cut:

```python
forbidden_depot_assignments: set[tuple[int, int]]
```

Meaning:

```text
client j cannot be served by depot i in any mode:
  - not routing
  - not DA
```

Advantages:

- Guarantees selected client leaves depot `i`.
- Directly targets aggregate capacity repair.
- Conceptually closer to a capacity-offload cut.

Disadvantages:

- Stronger change to builder, feasibility checker, parser/audit, artifacts, and
  batch diagnostics.
- Can eliminate feasible original solutions if used aggressively.
- Requires careful selection rules and stricter serviceability checks.

### Recommendation

Phase 7A should first audit `same_depot_DA_risk` and implement length
serviceability candidate filtering.

Decision rule:

- If `same_depot_DA_risk` / `capacity_not_freed` is rare, keep routing-only cuts
  initially with diagnostics.
- If frequent, design Phase 7B with `forbidden_depot_assignments` or explicit
  `capacity_offload_cuts`.

---

## 8. Layered architecture: Capa 0–3

### Capa 0 — current relaxed construction

No change.

- Fixed facility design from Excel.
- Capacity-relaxed PyVRP model.
- Routing and DA service options.
- First solve is relaxed / lower-bound-ish.
- Feasibility determined only after ex-post audit.

### Capa 1 — capacity repair with valid/safe cuts

Improve current greedy repair before accepting candidates:

1. Capacity-release validity:
   - flag `same_depot_DA_risk`,
   - optionally restrict to candidates with no same-depot DA risk,
   - after rerun, measure whether selected candidates actually freed capacity.
2. Length serviceability validity:
   - reject candidates that leave the client with no DA and no singleton
     length-feasible routing option.

Baseline ranking remains largest weighted saving.

### Capa 2 — post-rerun validation + bounded backtracking

If Capa 1 passes but rerun still yields:

```python
capacity_feasible = True
service_feasible = True
route_length_feasible = False
```

then:

1. Identify violating route.
2. Identify affected clients.
3. Compare affected clients with candidates added in last repair step.
4. Reject most likely culprit.
5. Roll back to previous committed forbidden set.
6. Try next candidate set by savings.

Maintain:

```python
rejected_repair_candidates: set[tuple[int, int, str]]
```

Example:

```python
rejected_repair_candidates.add((4, 18, "causes_route_length_violation"))
```

### Capa 3 — future restricted local search

Only for rows still stuck after Capa 1–2. Do not implement now.

Potential neighborhoods:

- replace one forbidden candidate with another,
- move client between depots,
- flip routing <-> DA,
- swap clients between depots,
- destroy-and-repair one overloaded depot,
- small neighborhood search over alternative cut sets,
- bounded beam search over top `K` repair candidates.

Full local search / ALNS / tabu / simulated annealing may be expensive because
each evaluation can require rebuilding and re-solving PyVRP. Use selectively on
stuck rows, not blindly across full batch.

---

## 9. Backtracking / rejected candidates algorithm

Do not implement yet. Proposed baseline:

```python
rejected_repair_candidates: set[tuple[int, int, str]] = set()
max_repair_attempts = small_int  # e.g. 3..10, tune after sample

for attempt in range(max_repair_attempts):
    candidates = build_capacity_repair_candidates(...)

    candidates = exclude_rejected(candidates, rejected_repair_candidates)

    candidates = filter_by_capacity_release_validity(
        candidates,
        mode="audit_or_restrict_same_depot_DA_risk",
    )

    candidates = filter_by_length_serviceability(
        candidates,
        current_forbidden,
        selected_so_far,
        active_depots,
        R,
        Length,
    )

    selected = greedy_select_until_capacity_excess_covered(
        candidates,
        score="largest_weighted_saving",
    )

    if not selected covers excess:
        return REPAIR_INFEASIBLE_OR_STUCK_WITH_DIAGNOSTICS

    trial_forbidden = current_forbidden | selected
    result = solve_with(trial_forbidden)
    audit = audit_solution(result)

    if audit.fully_feasible:
        accept(trial_forbidden)
        return FEASIBLE

    if audit.capacity_feasible and audit.service_feasible and not audit.route_length_feasible:
        culprit = attribute_route_length_violation(selected, audit)
        rejected_repair_candidates.add((culprit.depot, culprit.client, "causes_route_length_violation"))
        rollback_to(current_forbidden)
        continue

    if not audit.service_feasible:
        culprit = attribute_service_failure(selected, audit)
        rejected_repair_candidates.add((culprit.depot, culprit.client, "causes_service_violation"))
        rollback_to(current_forbidden)
        continue

    if audit.capacity_feasible and other_noncapacity_failure:
        record_diagnostics()
        return STUCK_NONCAPACITY_VIOLATION

    if not audit.capacity_feasible:
        # Capacity still violated. Either accept progress and continue normal
        # repair iteration, or reject if capacity_not_freed diagnostics show the
        # selected cuts did not release real capacity.
        if made_real_capacity_progress(audit):
            accept(trial_forbidden)
            continue_outer_repair_loop()
        else:
            reject_capacity_not_freed_candidate()
            rollback_to(current_forbidden)
            continue

return STUCK_OR_REPAIR_INFEASIBLE_WITH_BACKTRACKING_LIMIT
```

Attribution for route-length failure:

1. For each violating route from depot `h`, inspect route client sequence.
2. Prefer clients where singleton lower bound fails:

   ```python
   2 * dist_scaled(h, j) > Length
   ```

3. Intersect those clients with last-step selected candidates:

   ```python
   (old_depot, j) in selected
   ```

4. If one match: reject it.
5. If several: reject highest risk first:
   - no DA alternatives,
   - fewest singleton-feasible routing depots remaining,
   - smallest best length margin,
   - largest caused violation.
6. If none: mark attribution ambiguous and either reject most risky selected
   candidate or stop with diagnostics.

Loop guards:

- finite rejected-candidate set,
- `max_repair_attempts` per repair iteration,
- existing `max_repair_iterations`,
- deterministic sorting tie-breakers:

  ```python
  sort_key = (-score, depot_id, route_id, client_id)
  ```

Rollback rule: only `rejected_repair_candidates` changes after failed trial.
Committed `forbidden_routing_assignments` remains pre-trial until trial accepted.

---

## 10. Candidate scoring alternatives

Do not change baseline scoring until sample data justify it.

Baseline:

```python
score = weighted_saving
```

Future alternatives:

```python
score = weighted_saving / demand
```

```python
score = weighted_saving - penalty_for_low_length_feasibility_margin
```

```python
score = alpha * weighted_saving + beta * alternative_feasibility_margin
```

Possible feasibility margin:

```python
best_margin = max(
    Length - 2 * dist_scaled(h, j)
    for h in active_depots
    if (h, j) not in forbidden_after_cut
)
```

If no DA and no singleton-feasible routing alternative exists, hard reject rather
than only penalize.

Recommended Phase 7A default:

```text
largest weighted saving + hard validity filters + bounded backtracking
```

---

## 11. Status taxonomy and diagnostic fields

Keep current statuses initially:

- `FEASIBLE`
- `REPAIR_INFEASIBLE`
- `STUCK_NONCAPACITY_VIOLATION`
- `MAX_ITERATIONS`
- batch-level `ERROR`

Prefer diagnostic fields over many new statuses:

- `route_length_repair_attempts`
- `rejected_candidates`
- `n_rejected_repair_candidates`
- `last_rejection_reason`
- `same_depot_DA_risk_count`
- `capacity_not_freed_count`
- `length_invalid_cut_count`
- `route_length_backtracked`
- `violating_route_depot`
- `violating_route_clients`
- `violating_route_distance`
- `violating_route_length_limit`
- `culprit_repair_candidate`
- `attribution_confidence`

Only promote to new statuses if batch results show need:

- `ROUTE_LENGTH_BACKTRACKED_FEASIBLE`
- `ROUTE_LENGTH_REPAIR_FAILED`
- `BACKTRACKING_LIMIT_EXCEEDED`

Initial recommendation: keep `FEASIBLE` as final status even if backtracking was
used; expose path through diagnostics. This keeps before/after Phase 7 batch
summaries comparable.

---

## 12. Phase 6 baseline sample plan before implementation

Do **not** implement Phase 7 immediately without measuring.

Run Phase 6 baseline sample first:

```bash
cd /Users/apena/lor-v3
.venv/bin/python scripts/run_random_sample.py \
  --k 20 \
  --seed 42 \
  --seconds 30 \
  --runs 3 \
  --max-iter 5 \
  --run-id phase6_sample20_pre_phase7
```

If runtime allows, increase to `--k 50` or `--k 80` with same seed.

Also run row 5 as focused regression if not included in random sample. Do not run
full Excel.

Measure:

- count `STUCK_NONCAPACITY_VIOLATION`,
- separate stuck by route-length vs other non-capacity diagnostics,
- identify rows where capacity feasible + service feasible + route length false,
- identify rows where repair nominally selected candidates but capacity was not
  freed after rerun,
- count selected candidates with `same_depot_DA_risk`,
- inspect row 5 artifacts as canonical unsafe-cut evidence.

For pre-implementation audit, answer:

1. How many `STUCK_NONCAPACITY_VIOLATION` rows appear?
2. How many are route-length violations?
3. How many selected candidates were same-depot DA feasible?
4. How often did same-depot DA reabsorb a selected routing removal?
5. Is Phase 7A enough, or is `forbidden_depot_assignments` needed?

---

## 13. Implementation implications for later

Likely files after design approval:

- `src/lorp_fsd/repair.py`
  - rejected-candidate filtering,
  - candidate validity filters,
  - capacity-release risk annotations,
  - deterministic scoring/tie-breakers.
- `src/lorp_fsd/feasibility.py`
  - `client_has_length_feasible_service_option(...)`,
  - helper for singleton routing feasibility,
  - optional same-depot DA risk helper.
- `src/lorp_fsd/runner.py`
  - bounded trial/backtracking loop,
  - rollback of trial forbidden sets,
  - attribution diagnostics,
  - preserve current outer repair semantics when no backtracking is needed.
- `src/lorp_fsd/batch.py`
  - add diagnostic columns only after runner produces them.
- Optional `src/lorp_fsd/route_length_repair.py`
  - isolate Phase 7 attribution/backtracking logic if `repair.py` becomes too
    broad.
- If Phase 7B is needed:
  - `src/lorp_fsd/pyvrp_builder.py` must accept `forbidden_depot_assignments`,
  - DA option generation must exclude forbidden depot-client pairs,
  - routing service generation must also exclude them,
  - artifacts and assignment CSVs must report both routing-only and depot-level
    cuts.

Immediate repair.py audit before implementation:

1. Does current repair only add `forbidden_routing_assignments`?
2. Does it check whether client is DA-feasible from same overloaded depot?
3. Does it verify candidate releases aggregate capacity?
4. Does it check length-serviceability before forbidding?
5. Does current feasibility checker only check routing-or-DA existence, or also
   singleton length feasibility?

Current source inspection indicates:

- repair currently only emits routing-only `(depot_id, client_id)` forbids,
- same-depot DA risk is documented but not checked as candidate filter,
- real capacity release is known only after rerun audit,
- length-serviceability pre-check is absent,
- current checker is routing-exists OR DA-exists, without singleton length test.

This audit determines whether Phase 7A is candidate pre-check only, or whether
Phase 7B must add `forbidden_depot_assignments`.

---

## 14. Tests to add later

Add only when implementing Phase 7.

Required tests:

1. **Row 5 regression**
   - candidate `(4,18)` rejected by length-serviceability pre-check or
     post-rerun attribution,
   - no silent route-length unsafe cut,
   - row 0 unaffected.

2. **Synthetic no length-feasible alternative**
   - client has no DA option,
   - all remaining depots fail `2 * dist_scaled(h,j) <= Length`,
   - candidate rejected as `"no_length_feasible_alternative"`.

3. **Rejected candidate not selected again**
   - `rejected_repair_candidates` contains `(i,j,reason)`,
   - selector excludes `(i,j)` even if largest saving.

4. **First candidate fails, second succeeds**
   - first greedy candidate triggers route-length failure,
   - rollback keeps previous forbidden set,
   - second candidate selected and accepted.

5. **Same-depot DA risk flagged**
   - for candidate `(i,j)` with `dist_scaled(i,j) <= R`, diagnostic
     `same_depot_DA_risk=True`.

6. **Capacity not freed after same-depot DA reabsorption**
   - selected `(i,j)` moves from routing at `i` to DA at `i`,
   - `capacity_not_freed=True` recorded.

7. **Length pre-check still allows DA alternative**
   - no singleton routing alternative,
   - DA feasible from some depot,
   - candidate passes length-serviceability check.

8. **Row 0 remains feasible at iteration 0**
   - no repair/backtracking invoked,
   - status `FEASIBLE`,
   - existing objective regression unchanged.

9. **Backtracking limit deterministic**
   - finite candidate set,
   - max attempts reached,
   - stable status/diagnostics.

10. **Batch diagnostic columns**
    - once implemented, consolidated outputs include new diagnostic fields.

---

## 15. Recommended next command

Run Phase 6 baseline sample before Phase 7 implementation:

```bash
cd /Users/apena/lor-v3
.venv/bin/python scripts/run_random_sample.py \
  --k 20 \
  --seed 42 \
  --seconds 30 \
  --runs 3 \
  --max-iter 5 \
  --run-id phase6_sample20_pre_phase7
```

If runtime budget allows, rerun or extend with `--k 50` or `--k 80` using the same
seed. Include row 5 as an explicit regression if it is not selected randomly.

---

## Implementation notes — Phase 7A completed

Implemented on 2026-06-05 as Phase 7A safety layer.

Implemented:

- `repair_candidate_policy` with values:
  - `baseline`,
  - `safe_length`,
  - `safe_capacity_release`,
  - `safe_both`.
- `RepairCandidateSafety` diagnostics.
- Length serviceability pre-check using DA or singleton routing feasibility.
- Same-depot DA risk detection.
- Rejected candidate tracking.
- Artifact and batch diagnostic fields.
- CLI `--repair-policy` support for row, first-N, random-sample, and full-Excel scripts.

Not implemented yet:

- full post-rerun rollback/backtracking,
- `forbidden_depot_assignments`,
- local search / ALNS / tabu / SA.

Row 5 smoke under `safe_both` rejected `(4,18)` as
`no_length_feasible_alternative`, preventing the known unsafe length cut. The row
became `REPAIR_INFEASIBLE` in the short smoke because the remaining safe candidates
did not cover depot 4 excess. This is expected conservative behavior and motivates
Phase 7B if sample data show many such rows.

See `docs/HANDOFF_PHASE7_REPAIR_SAFETY.md` for implementation details, tests, and
smoke results.
