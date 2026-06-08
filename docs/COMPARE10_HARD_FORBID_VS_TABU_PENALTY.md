# Compare-10: hard_forbid vs tabu_penalty

Phase 9 repair-mode comparison on a fixed 10-row random sample.

Date: 2026-06-08

## Setup (identical except repair mode)

```
--k 10 --seed 42 --seconds 5 --runs 1 --max-iter 5 \
  --repair-policy safe_both --row-timeout-seconds 120
```

- Baseline: `--repair-mode hard_forbid` → `run_id compare10_hard_forbid`
- New default: `--repair-mode tabu_penalty --penalty-factor 100 --tabu-tenure 3`
  → `run_id compare10_tabu_penalty`

Output folders: `outputs/compare10_hard_forbid/`, `outputs/compare10_tabu_penalty/`
(`summary.md`, `summary.json`, `consolidated.csv`, per-row subfolders).

## Status counts

| Status | hard_forbid | tabu_penalty |
|---|---:|---:|
| FEASIBLE (n_success) | 7 | **8** |
| REPAIR_INFEASIBLE | 1 | 1 |
| STUCK_NONCAPACITY | 1 | **0** |
| MAX_ITERATIONS | 1 | 1 |
| ERROR | 0 | 0 |

## GAP on FEASIBLE rows

| Metric | hard_forbid | tabu_penalty |
|---|---:|---:|
| mean GAP | 0.30% (0.002977) | 0.95% (0.009499) |
| max GAP | 2.08% (0.020841) | 5.52% (0.055152) |
| min GAP | -0.0001% | -0.0001% |
| negative-gap flags | 0 | 0 |

## Runtime / iterations (identical envelope)

| Metric | hard_forbid | tabu_penalty |
|---|---:|---:|
| mean runtime (s) | 8.51 | 8.51 |
| max runtime (s) | 30.08 | 30.02 |
| mean iterations | 1.70 | 1.70 |
| max iterations | 6 | 6 |

## Average reconstructed cost channels

| Channel | hard PyVRP | tabu PyVRP | MILP |
|---|---:|---:|---:|
| routing | 469.12 | **449.88** | 404.42 |
| DA | 33.11 | **26.24** | 33.41 |
| Δ routing vs MILP | +64.70 | **+45.46** | — |
| Δ DA vs MILP | -0.30 | -7.17 | — |

## Did tabu_penalty improve anything?

Yes, on feasibility and search quality:

- **+1 FEASIBLE row** (8 vs 7) and the **STUCK_NONCAPACITY case was eliminated**
  (0 vs 1). Keeping the routing pair feasible-but-expensive let the solver route
  a client that a hard cut had stranded into a non-capacity violation.
- **Lower average routing and DA cost** (routing Δ vs MILP +45.5 vs +64.7; DA
  26.2 vs 33.1). The soft penalty steers the search instead of amputating arcs,
  so it finds cheaper reconstructions on average.
- Runtime and iteration envelope are unchanged.

The **higher mean/max GAP on FEASIBLE rows is not a regression**: the extra row
that becomes FEASIBLE under tabu_penalty (previously STUCK under hard_forbid) is
a harder row and contributes a positive GAP that hard_forbid simply excluded
from its feasible set. Comparing only the 7 rows feasible under both modes, the
GAPs are equivalent; tabu adds an 8th, harder, still-valid row.

## Limitations

- k=10, single seed (42), 5 s/run, 1 run/seed — indicative, not statistically
  powered. Not a full-Excel result.
- Tabu is a simple per-pair countdown (tenure 3); no aspiration criterion. An
  expired pair can be re-selected later.
- Penalty factor 100 was not swept; 100 × route_max_distance_int is large enough
  to almost-forbid in practice while preserving feasibility.
- `n_penalty` / `n_length_invalid_cut` columns are pre-existing batch diagnostics
  and are not the Phase 9 penalty mechanism.
- REPAIR_INFEASIBLE (1 row) and MAX_ITERATIONS (1 row) persist in both modes;
  soft penalty did not resolve those within the 5-iteration budget.
