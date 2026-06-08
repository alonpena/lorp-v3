# Handoff — Phase 7A: Repair Candidate Safety Checks

Date: 2026-06-05 · Working dir: `/Users/apena/lor-v3`

## Recovery audit refresh — 2026-06-05

Status audit found Phase 7A **implemented and coherent**. No syntax errors in
`src/lorp_fsd/repair.py`, `src/lorp_fsd/feasibility.py`, or
`src/lorp_fsd/runner.py` (`py_compile` passed).

Files touched by Phase 7A per source/docs:

- `src/lorp_fsd/repair.py`
- `src/lorp_fsd/feasibility.py`
- `src/lorp_fsd/runner.py`
- `src/lorp_fsd/artifacts.py`
- `src/lorp_fsd/batch.py`
- `src/lorp_fsd/__init__.py`
- `scripts/run_row.py`
- `scripts/run_first_n.py`
- `scripts/run_random_sample.py`
- `scripts/run_full_excel.py`
- `tests/test_phase7_repair_safety.py`
- `docs/PHASE7_ROUTE_LENGTH_REPAIR_DESIGN.md`
- `docs/HANDOFF_PHASE7_REPAIR_SAFETY.md`

Checks confirmed:

- `(4,18)` detected unsafe for length:
  `length_serviceable_after_cut=False`, no DA alternative, no singleton routing
  alternative after cut.
- Same-depot DA risk detected, e.g. `(4,11)`:
  `same_depot_DA_risk=True`.
- Policies supported: `baseline`, `safe_length`, `safe_capacity_release`,
  `safe_both`.
- Rejected repair candidates tracked with reasons including
  `same_depot_DA_risk`, `no_length_feasible_alternative`, `strands_client`.
- Runner accepts and passes `repair_candidate_policy` through row, batch, and
  script CLIs. `max_repair_attempts` exists but remains reserved.

Tests run in this audit:

```bash
.venv/bin/python -m pytest tests/test_repair.py tests/test_runner.py -q
# code 4: tests/test_repair.py does not exist in this tree; equivalent file is tests/test_repair_savings.py

.venv/bin/python -m pytest tests/test_repair_savings.py tests/test_runner.py tests/test_phase7_repair_safety.py -q
# 21 passed

.venv/bin/python -m pytest -q
# 225 passed
```

Phase 7A complete: **YES** for candidate safety diagnostics/filtering and CLI/reporting plumbing.
Full Excel: **NO-GO** until sample baseline-vs-`safe_both` comparison is reviewed.
Recommended next action: run k=20 sample comparison, not full Excel.

---

Status: **implemented Phase 7A safety checks and diagnostics**. Full local search
/ ALNS / tabu / SA was **not** implemented. Full Excel was **not** run.

Known prior suite status: 219 passed. Current suite after Phase 7A: **225 passed**.

---

## 1. What Phase 7A implemented

Phase 7A adds safety diagnostics and optional filtering around the existing
savings-based capacity repair. The repair still uses routing-only
`forbidden_routing_assignments` and the same greedy largest weighted saving
baseline unless a safer policy is requested.

Implemented policies:

- `baseline` — existing behavior, only current service checker.
- `safe_length` — rejects cuts that leave the client with no DA and no singleton
  length-feasible routing option.
- `safe_capacity_release` — rejects candidates with same-depot DA risk.
- `safe_both` — requires both safe length serviceability and no same-depot DA
  risk. Recommended for Phase 7 experiments.

---

## 2. Files created / modified

Created:

- `tests/test_phase7_repair_safety.py`
- `docs/HANDOFF_PHASE7_REPAIR_SAFETY.md`

Modified:

- `src/lorp_fsd/repair.py`
- `src/lorp_fsd/feasibility.py`
- `src/lorp_fsd/runner.py`
- `src/lorp_fsd/artifacts.py`
- `src/lorp_fsd/batch.py`
- `src/lorp_fsd/__init__.py`
- `scripts/run_row.py`
- `scripts/run_first_n.py`
- `scripts/run_random_sample.py`
- `scripts/run_full_excel.py`
- `docs/PHASE7_ROUTE_LENGTH_REPAIR_DESIGN.md`

---

## 3. Candidate safety checks

New dataclass: `RepairCandidateSafety`.

For each candidate `(i,j)` evaluated under a tentative cut, Phase 7A computes:

```python
same_depot_DA_feasible: bool
same_depot_DA_risk: bool
length_serviceable_after_cut: bool
has_DA_alternative_after_cut: bool
has_routing_singleton_alternative_after_cut: bool
safe_for_capacity_release: bool
safe_for_length_serviceability: bool
```

Policy filtering happens in `select_forbidden_assignments(...)` via:

```python
repair_candidate_policy="baseline" | "safe_length" | "safe_capacity_release" | "safe_both"
```

Rejected candidates are tracked as:

```python
rejected_repair_candidates: set[tuple[int, int, str]]
```

Reasons currently used:

- `same_depot_DA_risk`
- `no_length_feasible_alternative`
- `strands_client`

`causes_route_length_violation` is reserved for future post-rerun attribution.

---

## 4. Same-depot DA risk

For capacity candidate `(i,j)` from overloaded depot `i`:

```python
same_depot_DA_feasible = dist_scaled(i,j) <= R
same_depot_DA_risk = same_depot_DA_feasible
```

If true, routing-only forbid may not release aggregate capacity because PyVRP can
serve `j` by DA from same depot `i` after rerun:

```text
demand_routing_i decreases
demand_DA_i increases
demand_total_i unchanged
```

`safe_capacity_release` and `safe_both` reject these candidates.

---

## 5. Length serviceability pre-check

After tentative cut `(i,j)`, Phase 7A requires at least one active depot `h` with:

```python
dist_scaled(h,j) <= R
```

or:

```python
(h,j) not in forbidden_after_cut
and 2 * dist_scaled(h,j) <= Length
```

This guarantees the client retains at least one DA option or one singleton
route-length-feasible routing option. It prevents row-5-style unsafe cuts.

---

## 6. Rejected repair candidates

`RepairSelection` now carries:

- `candidate_safety`
- `rejected_candidates`
- `same_depot_DA_risk_count`
- `length_invalid_cut_count`
- `rejected_candidates_count`
- `repair_candidate_policy`

Artifacts and batch outputs expose these diagnostics.

---

## 7. Bounded backtracking status

Post-rerun bounded backtracking was **not fully implemented** in this pass. Reason:
current runner applies a selected repair set in the next outer iteration; clean
rollback and re-solving from the previous parsed/capacity state would require a
larger runner refactor.

Implemented instead:

- pre-rerun candidate safety filtering,
- rejected candidate tracking,
- CLI plumbing for `--max-repair-attempts` as reserved/future,
- diagnostics needed to implement post-rerun attribution later.

Future Phase 7B can add `causes_route_length_violation` attribution and rollback.

---

## 8. Test results

Commands run:

```bash
cd /Users/apena/lor-v3
PYTHONPATH=src .venv/bin/python -m pytest tests/test_phase7_repair_safety.py -q
PYTHONPATH=src .venv/bin/python -m pytest tests/test_repair_savings.py tests/test_phase7_repair_safety.py -q
.venv/bin/python -m pytest -q
```

Results:

```text
6 passed
15 passed
225 passed
```

---

## 9. Row 5 result under new policy

Command run:

```bash
.venv/bin/python scripts/run_row.py \
  --row 5 \
  --seconds 5 \
  --runs 1 \
  --max-iter 3 \
  --repair-policy safe_both \
  --run-id phase7_row5_safe_both_smoke \
  --no-plots
```

Result:

```text
status: REPAIR_INFEASIBLE
iterations: 1
repair policy: safe_both
```

Important diagnostics from `iteration_00_audit.json`:

- `(4,18)` rejected with `no_length_feasible_alternative`.
- Same-depot DA-risk candidates rejected: `(4,11)`, `(4,15)`, `(4,37)`, `(4,39)`.
- Safe selected candidates: `(4,19)`, `(4,20)`.
- Selected safe candidates did not cover depot 4 excess, so repair marked
  `REPAIR_INFEASIBLE` under conservative `safe_both`.

Interpretation: Phase 7A prevents the unsafe row-5 cut that caused route-length
violation. It may become more conservative and classify row 5 as repair-infeasible
unless Phase 7B introduces stronger or smarter offload cuts/local search.

---

## 10. Sample comparison results

Small safe policy smoke run:

```bash
.venv/bin/python scripts/run_random_sample.py \
  --k 5 \
  --seed 42 \
  --seconds 5 \
  --runs 1 \
  --max-iter 3 \
  --repair-policy safe_both \
  --run-id smoke_phase7_sample5
```

Rows sampled: `[51, 228, 457, 501, 563]`.

Summary:

```text
Rows: 5
FEASIBLE: 4
STUCK_NONCAPACITY_VIOLATION: 1
REPAIR_INFEASIBLE: 0
MAX_ITERATIONS: 0
ERROR: 0
```

Diagnostics from summary:

```text
n_same_depot_DA_risk: 0
n_capacity_not_freed: 0
n_length_invalid_cut: 4
n_rejected_candidates: 2
```

This is a smoke run only, not a full evaluation. Run the planned k=20 baseline vs
safe comparison before drawing conclusions.

---

## 11. Known limitations

1. `safe_capacity_release` is conservative. It may reject candidates that could
   be moved to another depot by a feasible solution.
2. `safe_both` can convert a previous `STUCK_NONCAPACITY_VIOLATION` into
   `REPAIR_INFEASIBLE` because unsafe cuts are no longer allowed.
3. Full post-rerun rollback/backtracking is not implemented yet.
4. `capacity_not_freed_count` detects same-depot DA reabsorption between selected
   repair pairs and the next parsed solution, but richer candidate-level capacity
   attribution remains future work.
5. `forbidden_depot_assignments` is not implemented.

---

## 12. Is Phase 7B / local search needed?

Likely yes if conservative `safe_both` creates many `REPAIR_INFEASIBLE` rows or
if route-length stuck rows remain common. Candidate next steps:

- Phase 7B: `forbidden_depot_assignments` / capacity-offload cuts.
- Bounded post-rerun rollback using `causes_route_length_violation` attribution.
- Small neighborhood search over alternative candidate sets only for stuck rows.

Do not jump to full ALNS/tabu/SA until sample data justify it.

---

## 13. Recommended next command

Run comparable baseline and safe samples (not full Excel):

```bash
cd /Users/apena/lor-v3
.venv/bin/python scripts/run_random_sample.py \
  --k 20 \
  --seed 42 \
  --seconds 30 \
  --runs 3 \
  --max-iter 5 \
  --run-id phase6_sample20_pre_phase7

.venv/bin/python scripts/run_random_sample.py \
  --k 20 \
  --seed 42 \
  --seconds 30 \
  --runs 3 \
  --max-iter 5 \
  --repair-policy safe_both \
  --run-id phase7_sample20_safe_both
```

If time is limited, first run k=5 smoke with 5s/1run as above.
