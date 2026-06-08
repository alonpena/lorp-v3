# Handoff — Phase 1: Data & C-Compatible Preprocessing (LoRP-FSD v3)

Readable without prior context. Companion to `docs/IMPLEMENTATION_PLAN.md` (Phase 1)
and `docs/C_CONGRUENCY_TEST.md`.

Date: 2026-06-05 · Host: macOS arm64 · Working dir: `/Users/apena/lor-v3`

## 1. Files created / modified

### Created — package `src/lorp_fsd/` (no legacy imports)
- `__init__.py` — public API surface.
- `geometry.py` — raw Euclidean distance + `max_pairwise_distance`.
- `dat_parser.py` — `ParsedInstance` (1-based IDs), `parse_dat`, trailing-flag
  validation, and `resolve_dat_path` (EXACT / COORD_PREFIX / SUFFIX_GLOB /
  MISSING / AMBIGUOUS — reports, never guesses).
- `scaling.py` — `ScaledGeometry`, `build_scaled_geometry`, `PYVRP_INT_SCALE`.
- `facility_sizing.py` — C 5-size formula, capacity/cost, Excel cross-check.
- `experiment_config.py` — `ExperimentConfig`, `SelectedDepot`, `problemID==0` guard.
- `excel_loader.py` — loads only `LoRP-FSD`, real depot IDs from labels.
- `instance.py` — `build_facility_design` (fixed-facility design + Excel check).

### Created — tests (`tests/`)
- `test_dat_parser.py`, `test_scaling.py`, `test_facility_sizing.py`,
  `test_experiment_config.py`, `test_excel_loader.py`, `test_instance.py`.

### Modified
- `pyproject.toml` — pytest `pythonpath = ["src", "."]`; setuptools
  `packages.find` for `lorp_fsd*` (legacy flat modules untouched).

No legacy source files were modified.

## 2. What each new module does

| Module | Responsibility |
|---|---|
| `geometry` | Raw Euclidean distance; max-pairwise over all nodes. |
| `dat_parser` | Parse C `.dat` (counts, coords, caps, demands, fixed costs, trailing flag); 1-based depot/client IDs; resolve instance paths across real folders. |
| `scaling` | Arslan scaling `scale = 100/max_dist` (max over all nodes); scaled-distance lookups; integerization via `PYVRP_INT_SCALE`; raw-equivalent helpers; `problemID!=0` raises. |
| `facility_sizing` | C size formula: `cap = base·(1+(s−3)·0.25)`, `cost = fixed+((cap−base)/(2·base))·(totalfix/T)`; multipliers `{1:.5,2:.75,3:1,4:1.25,5:1.5}`; Excel cross-check. |
| `experiment_config` | One Excel row's run params + benchmark values; `problemID==0` guard; selected depots with MILP slots. |
| `excel_loader` | Read `LoRP-FSD` sheet; map columns by name; parse depot labels `'d5'→5`; no row-dropping on filename mismatch; inject `problemID=0`. |
| `instance` | Build fixed `FacilityDesign` from Excel-selected depots/sizes; recompute caps/costs via C formula; cross-check Excel `CapD*`. |

## 3. Row 0 regression constants (`r40x5a-1.dat`)

| Quantity | Value |
|---|---|
| Instance name | `r40x5a-1.dat` |
| Selected (open) depots | `(1, 2, 3, 5)` — note Excel `Depot4='d5'` → real ID 5 |
| `max_dist` (all node pairs) | `125.399362` |
| `scale = 100/max_dist` | `0.79745222` |
| Selected capacities | `875.0` each (size 1 → base 1750 × 0.50) |
| Depot cost (recomputed) | `300.0` (4 × 75) |
| Reconstructed routing cost | `95.3087` (route d3 → client1 → client33 → d3, F_R=1) |
| Reconstructed total | `95.3087 + 0 + 300 + 0 = 395.3087` (Excel UB `395.309`) |

## 4. Test results

- Phase 1 v3 tests: **38 passed**
  (`test_dat_parser`, `test_scaling`, `test_facility_sizing`,
  `test_experiment_config`, `test_excel_loader`, `test_instance`).
- Full repository suite (legacy + v3): **157 passed** — no regressions from the
  `pythonpath` change.

## 5. Known caveats

1. **Standalone import requires `PYTHONPATH=src`** (or an editable install).
   Tests work directly because pytest is configured with `pythonpath = ["src", "."]`.
   Scripts/REPL must use `PYTHONPATH=src python ...` until the package is installed.
2. **`instances_LRP` folder does not exist.** `resolve_dat_path` searches the real
   folders: `instances/`, `instances_old/`, `reference/LoRPSD/instances_LLRP/`.
   All four located copies of `r40x5a-1.dat` are byte-identical.
3. **`problemID` is not an Excel column.** It is injected as `0` (Arslan),
   confirmed by the C congruency test; any other value raises `NotImplementedError`.
4. **VFX / vehicle fixed cost are 0 on row 0** (instance `veh_fixed=0`), so the
   vehicle-cost path is exercised but not stress-tested until a nonzero-fixed row.

## 6. Phase 2 readiness

**READY.** Phase 1 provides everything Phase 2 needs:
- `ParsedInstance` (coords, demands, `Q`, base caps),
- `ScaledGeometry` (scaled distances + `to_int` / `PYVRP_INT_SCALE`),
- `ExperimentConfig` (`F_R`, `F_A`, `R`, `Length`, selected depots),
- `FacilityDesign` (active depots, selected `Cap_i`, costs).

Phase 2 builds the capacity-relaxed PyVRP model (`da_options.py`,
`pyvrp_builder.py`) — routing vehicles from `floor(Cap/Q)`+residual, integerized
weighted edge costs, single-client-bound zero-return DA options, and
`forbidden_routing_assignments` support — with no repair loop, parser, audit,
plotting, or batch execution.
