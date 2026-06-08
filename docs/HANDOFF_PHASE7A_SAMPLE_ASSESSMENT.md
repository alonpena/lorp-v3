# Handoff — Phase 7A Sample Assessment

Date: 2026-06-05 · Working dir: `/Users/apena/lor-v3`

## Scope

Controlled Phase 7A assessment only. No Phase 7B, no backtracking, no local
search / ALNS / tabu / LNS, no C solver changes, no full Excel.

## 1. Commands run

Confirmed directory:

```bash
cd /Users/apena/lor-v3
pwd
# /Users/apena/lor-v3
```

Smoke command requested:

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

Initial smoke rerun exposed a resumability bug: all rows were skipped from the
checkpoint, but `run_random_sample.py` wrote an empty consolidated file and then
failed with `KeyError: 'n_success'`. Minimal fix: `run_rows(...,
return_completed_records=True)` support plus CSV checkpoint parsing for resumed
records. No solver/repair semantics changed.

Requested k=20 baseline command attempted:

```bash
.venv/bin/python scripts/run_random_sample.py \
  --k 20 \
  --seed 42 \
  --seconds 30 \
  --runs 3 \
  --max-iter 5 \
  --repair-policy baseline \
  --run-id phase6_sample20_baseline
```

Result: did not complete. It reached row 228 (`r30x5a-1.dat`) and timed out after
2h wall time. A direct row-228 baseline rerun with `--seconds 30 --runs 3
--max-iter 2` also timed out after 15m. PyVRP emitted `PenaltyBoundWarning` and
appeared to struggle on the repaired/infeasible subproblem.

Requested k=20 safe command attempted:

```bash
.venv/bin/python scripts/run_random_sample.py \
  --k 20 \
  --seed 42 \
  --seconds 30 \
  --runs 3 \
  --max-iter 5 \
  --repair-policy safe_both \
  --run-id phase7_sample20_safe_both
```

Result: same stall pattern at row 228; timed out after 2h wall time.

Fallback controlled comparison (same seed/sample, shorter smoke settings) run to
obtain bounded data:

```bash
.venv/bin/python scripts/run_random_sample.py \
  --k 20 \
  --seed 42 \
  --seconds 5 \
  --runs 1 \
  --max-iter 3 \
  --repair-policy baseline \
  --run-id phase6_sample20_baseline_fast

.venv/bin/python scripts/run_random_sample.py \
  --k 20 \
  --seed 42 \
  --seconds 5 \
  --runs 1 \
  --max-iter 3 \
  --repair-policy safe_both \
  --run-id phase7_sample20_safe_both_fast
```

Comparison command:

```bash
.venv/bin/python scripts/compare_sample_runs.py \
  outputs/phase6_sample20_baseline_fast/consolidated.csv \
  outputs/phase7_sample20_safe_both_fast/consolidated.csv \
  --out outputs/phase7a_sample20_fast_comparison.json \
  --md outputs/phase7a_sample20_fast_comparison.md
```

Tests after utility/resume fix:

```bash
.venv/bin/python -m pytest tests/test_batch.py tests/test_phase7_repair_safety.py -q
# 20 passed

.venv/bin/python -m pytest -q
# 225 passed
```

## 2. Output folders/files created

Smoke:

- `outputs/smoke_phase7_sample5/checkpoint.csv`
- `outputs/smoke_phase7_sample5/consolidated.csv`
- `outputs/smoke_phase7_sample5/consolidated.xlsx`
- `outputs/smoke_phase7_sample5/summary.json`
- `outputs/smoke_phase7_sample5/summary.md`

Requested 30s/3run attempts, partial only:

- `outputs/phase6_sample20_baseline/checkpoint.csv` (7 completed rows before row-228 timeout)
- `outputs/phase7_sample20_safe_both/checkpoint.csv` (7 completed rows before row-228 timeout)

Fallback bounded k=20:

- `outputs/phase6_sample20_baseline_fast/*`
- `outputs/phase7_sample20_safe_both_fast/*`
- `outputs/phase7a_sample20_fast_comparison.json`
- `outputs/phase7a_sample20_fast_comparison.md`

Code/docs created or modified:

- `src/lorp_fsd/batch.py` — optional resumed-record return for checkpointed runs.
- `scripts/run_random_sample.py` — requests resumed records so summary is not empty.
- `scripts/compare_sample_runs.py` — lightweight CSV comparison utility.
- `docs/HANDOFF_PHASE7A_SAMPLE_ASSESSMENT.md` — this handoff.

## 3. Smoke test result

Rows sampled: `[51, 228, 457, 501, 563]`.

Status counts:

| status | count |
|---|---:|
| FEASIBLE | 4 |
| STUCK_NONCAPACITY_VIOLATION | 1 |
| REPAIR_INFEASIBLE | 0 |
| MAX_ITERATIONS | 0 |
| ERROR | 0 |

Diagnostics:

- `n_length_invalid_cut`: 4
- `n_rejected_candidates`: 2
- `n_same_depot_DA_risk`: 0
- `n_capacity_not_freed`: 0
- `n_penalty`: 0
- `n_negative_gap`: 0

Smoke passed after resumability fix. CSV, Excel, JSON, MD outputs exist.

## 4. Baseline k=20 status counts

Requested 30s/3run sample did **not** complete; row 228 stalled. Completed first
7 rows only before timeout. Therefore no valid requested 30s/3run k=20 status
counts are available.

Fallback `phase6_sample20_baseline_fast` status counts:

| status | count |
|---|---:|
| FEASIBLE | 12 |
| REPAIR_INFEASIBLE | 4 |
| STUCK_NONCAPACITY_VIOLATION | 1 |
| MAX_ITERATIONS | 2 |
| ERROR | 1 |

Error row:

- row 1149 `r40x5b-2.dat`: `ValueError: Expected at least one depot.`

## 5. safe_both k=20 status counts

Requested 30s/3run sample did **not** complete; row 228 stalled. Completed first
7 rows only before timeout. Therefore no valid requested 30s/3run k=20 status
counts are available.

Fallback `phase7_sample20_safe_both_fast` status counts:

| status | count |
|---|---:|
| FEASIBLE | 12 |
| REPAIR_INFEASIBLE | 5 |
| STUCK_NONCAPACITY_VIOLATION | 1 |
| MAX_ITERATIONS | 1 |
| ERROR | 1 |

Error row is same as baseline: row 1149 `r40x5b-2.dat`.

## 6. Comparison table — fallback k=20 fast sample

| Metric | baseline | safe_both |
|---|---:|---:|
| FEASIBLE | 12 | 12 |
| REPAIR_INFEASIBLE | 4 | 5 |
| STUCK_NONCAPACITY_VIOLATION | 1 | 1 |
| MAX_ITERATIONS | 2 | 1 |
| ERROR | 1 | 1 |
| runtime_mean | 8.73377 | 7.37620 |
| iterations_mean | 1.73684 | 1.47368 |
| gap_feasible_min | -5.155e-07 | -5.155e-07 |
| gap_feasible_mean | 0.0063829 | 0.0063829 |
| gap_feasible_max | 0.0403055 | 0.0403055 |
| comparison_metric_min | -0.498972 | -0.557475 |
| comparison_metric_mean | -0.0374761 | -0.0316111 |
| comparison_metric_max | 0.0403055 | 0.0403055 |
| negative_gap_count | 0 | 0 |
| penalty_distance_suspected_count | 0 | 0 |
| rejected_candidates_count | 10 | 14 |
| same_depot_DA_risk_count | 10 | 5 |
| capacity_not_freed_count | 7 | 0 |
| length_unsafe_candidate_count | 0 | 18 |

Interpretation:

- FEASIBLE count unchanged.
- STUCK count unchanged in this sample.
- safe_both converts one MAX_ITERATIONS row into REPAIR_INFEASIBLE.
- safe_both eliminates observed `capacity_not_freed_count` in fallback sample
  (`7 -> 0`).
- safe_both records length-unsafe candidates (`18`), making unsafe repair causes
  visible instead of silently selecting them.

## 7. Examples of rows changed by safe_both

Only one status change in fallback k=20:

| row_id | instance | baseline | safe_both | safe rejected candidates |
|---:|---|---|---|---:|
| 407 | coord50-5-3.dat | MAX_ITERATIONS | REPAIR_INFEASIBLE | 4 |

Row 407 safe_both rejected:

- `(3,31, no_length_feasible_alternative)`
- `(3,32, same_depot_DA_risk)`
- `(3,38, same_depot_DA_risk)`
- `(3,43, same_depot_DA_risk)`

This is expected conservative behavior: unsafe/false-capacity-release candidates
are not used, so repair can fail earlier rather than chase invalid cuts.

Row 228 remains `STUCK_NONCAPACITY_VIOLATION` under both policies in fast sample.
Under safe_both it rejects length-unsafe candidates `(3,2)` and `(3,6)`, but a
route-length infeasibility still appears after repair. This suggests pre-cut
singleton serviceability is not enough for every row; Phase 7B attribution /
backtracking may still be needed.

## 8. Are (4,18)-type unsafe cuts avoided?

Yes for the specific Phase 7A check: cuts that leave a client with no DA option
and no singleton route-length-feasible routing alternative are rejected under
`safe_length` / `safe_both`.

Smoke and fallback samples show nonzero `length_invalid_cut_count`, meaning this
safety layer is active:

- smoke safe_both k=5: `n_length_invalid_cut = 4`
- fallback safe_both k=20: `n_length_invalid_cut = 18`

Known row-5 `(4,18)` remains detected as unsafe from prior Phase 7A audit.

## 9. Does safe_both increase REPAIR_INFEASIBLE too much?

Fallback k=20: `REPAIR_INFEASIBLE` increases from 4 to 5.

That is not an excessive increase in this small sample, but sample is not enough
for full conclusion because requested 30s/3run k=20 could not complete.

## 10. Is Phase 7B/backtracking needed?

Likely yes, but not full local search.

Evidence:

- `safe_both` is useful: detects length-unsafe and same-depot DA-risk candidates;
  eliminates observed same-depot capacity-not-freed cases in fallback sample.
- `safe_both` does not eliminate all STUCK rows: row 228 remains stuck.
- `safe_both` can classify rows as `REPAIR_INFEASIBLE` earlier (row 407), which
  may be correct under current cut model but may need bounded backtracking or
  stronger depot-level offload cuts.
- Requested 30s/3run samples stall at row 228, so batch robustness needs a
  row-level wall timeout before overnight runs.

Recommended Phase 7B scope: bounded attribution/backtracking and/or stronger
capacity-release cuts. Do **not** jump to full ALNS/tabu/LNS yet.

## 11. Full Excel GO / NO-GO

**NO-GO**.

Reasons:

1. Requested k=20 30s/3run baseline and safe_both both stall at row 228.
2. safe_both still has STUCK rows in fallback sample.
3. Need either row-level timeout guard or Phase 7B bounded repair logic before
   leaving anything overnight.

## 12. Recommended next command

Do not run full Excel overnight.

Next safe step if wanting more data tonight:

```bash
.venv/bin/python scripts/run_random_sample.py \
  --k 50 \
  --seed 42 \
  --seconds 5 \
  --runs 1 \
  --max-iter 3 \
  --repair-policy safe_both \
  --run-id phase7_sample50_safe_both_fast
```

Better engineering next step before 30s/3run samples:

- add a per-row wall-time timeout in batch/sample runner so one hard PyVRP row
  is recorded as `ERROR`/`TIMEOUT` instead of blocking the whole sample.
- then rerun requested 30s/3run k=20 comparison.

## Final decision

Phase 7A is useful and should stay. It gives real safety diagnostics and prevents
known invalid repair candidates. It is not enough to justify full Excel overnight.
Phase 7B bounded backtracking / stronger cut logic is likely needed, but full
local search remains premature.
