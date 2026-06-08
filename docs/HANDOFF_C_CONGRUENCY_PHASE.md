# Handoff — C Congruency Phase (LoRP-FSD v3)

Readable without prior context. Companion to `docs/C_CONGRUENCY_TEST.md`.

Date: 2026-06-05 · Host: macOS arm64 (Darwin 25.5.0) · Working dir: `/Users/apena/lor-v3`

## What this phase did

Verified that the original C/Gurobi solver, Excel row 0 (sheet `LoRP-FSD`), and
the `r40x5a-1.dat` instance are **parameter-congruent**, before any PyVRP v3
implementation. No PyVRP was written; no v3 heuristic was changed.

## What was executed

- Located/compared the binary, instance, and Excel files.
- Attempted to run the C binary (failed — wrong architecture, see below).
- Parsed `r40x5a-1.dat`; computed geometry, scale, facility sizing, DA coverage,
  and routing cost in Python (`.venv`).
- Read Excel `LoRP-FSD` row 0.
- Inspected the C source (`stcmodels.cpp` `det_LoRP_DSD`) for the objective and
  for the per-route vehicle-capacity constraint.
- Reconstructed the full row-0 objective from first principles and compared to Excel.

## Exact command(s)

Binary run attempt (failed):

```bash
/Users/apena/lor-v3/reference/LoRPSD/LoRPSD        # -> exec format error
file /Users/apena/lor-v3/reference/LoRPSD/LoRPSD   # -> ELF x86-64, GNU/Linux
```

Intended C command for a future live run (LoRP-FSD ⇒ `-original 0`):

```bash
reference/LoRPSD/LoRPSD \
  -results outputs/c_congruency/row0_results.txt \
  -problemID 0 -WR 1 -WA 0 -Radius 30 \
  -instance instances/r40x5a-1.dat \
  -VFX 1 -OF 1 -original 0 -model 1 -length 100
```

## Files created

- `docs/C_CONGRUENCY_TEST.md` — full test, per-parameter congruency table, source citations.
- `docs/HANDOFF_C_CONGRUENCY_PHASE.md` — this file.
- `outputs/c_congruency/row0_error.txt` — binary execution failure log.
- `outputs/c_congruency/row0_static_reconstruction.txt` — numeric reconstruction.
- `outputs/c_congruency/row0_results.txt` — NOT created (binary did not run).

No source/spec/plan files were modified in this phase.

## Result status

| Question | Answer |
|---|---|
| C binary ran? | **No** — Linux x86-64 ELF on macOS arm64 (`exec format error`); no Docker; Rosetta N/A for Linux ELF. |
| Row 0 matched Excel? | **Yes, exactly** — by static reconstruction. `UB = 95.3087 + 0 + 300 + 0 = 395.3087` == Excel 395.309. |
| Per-route vehicle capacity Q in C? | **Yes** — `W[i][j] ≤ Q·X[i][j]` (`stcmodels.cpp:782`) via single-commodity load-flow. PyVRP per-vehicle cap **matches**; not an extra constraint. |
| `original=0` (sizing)? | **Confirmed** (literal `LoRP-SD` + depot-sizing cost 300 reproduced). |
| `problemID=0` Arslan scaling? | **Confirmed** (`scale=100/max_dist=0.797452`). |
| `R`,`Length` scaled units? | **Confirmed** (compared against scaled `dist`/`t` in source). |
| Mixed-unit objective (scaled dist + raw fixed)? | **Confirmed** (routing/DA scaled; depots/vehicles raw). |

### Key row-0 facts (for the next agent)

- `r40x5a-1.dat`: 40 clients, 5 depots, max_open 5, **Q=340**, base_dep_cap 1750,
  dep_fixed 100, **veh_fixed=0**, total_demand 1931. All 4 located copies identical.
- Row 0 params: **F_R=1, F_A=0, R=30, Length=100**, optimal UB=395.309.
- `scale = 0.79745222`, `max_dist = 125.399362` (a client–client pair).
- Optimal structure: 4 depots open (d1,d2,d3,d5, size 1, cap 875, cost 75 each);
  38/40 clients direct-allocated for free (F_A=0) within R=30; the 2 uncoverable
  clients (#1,#33) served by a single route at **d3** (scaled cost 95.3087).

## Unresolved issues (none are Phase-1 blockers)

1. **VFX untestable on row 0** (veh_fixed=0). Re-verify on a row whose instance
   has nonzero vehicle fixed cost.
2. **No live binary run.** Static proof is exact; a recompiled run is optional
   confirmation and will be needed for rows whose optimum is not analytically
   transparent.
3. `instances_LRP` (named in the plan) does not exist; use `instances/`.

## How to enable a live C run later (recompile recipe, mac arm64)

Prerequisites verified present: Gurobi 12.0.0 (license `LicenseID 2587987`),
`/Library/gurobi1200/macos_universal2/{include,lib}` (`gurobi_c++.h`,
`libgurobi_c++.a`), CMake module `reference/LoRPSD/cmake/FindGUROBI.cmake`.
Missing: **libomp** (CMakeLists does `find_package(OpenMP REQUIRED)`).
CMakeLists also **hardcodes Linux Gurobi paths** (lines 18–19) that must be overridden.

```bash
brew install libomp cmake
cd /Users/apena/lor-v3/reference/LoRPSD
# edit CMakeLists.txt: set GUROBI_DIR=/Library/gurobi1200/macos_universal2
#   (and GRB_LICENSE_FILE=/Users/apena/gurobi.lic), or pass -DGUROBI_DIR=...
cmake -S . -B build_mac \
  -DGUROBI_DIR=/Library/gurobi1200/macos_universal2 \
  -DOpenMP_ROOT=$(brew --prefix libomp)
cmake --build build_mac -j
# then run the §"Exact command(s)" line with build_mac/LoRPSD
```

Risks: Gurobi C++ source built originally against v10.0.3; the C++ API
(`GRBModel`, `GRBLinExpr`, …) is stable to v12, so it should compile, but verify
`FindGUROBI.cmake` resolves `libgurobi120.dylib` + `libgurobi_c++.a`. If the
C++ static lib mismatches the toolchain, link against the mac universal lib in
`/Library/gurobi1200/macos_universal2/lib`.

## Next recommended phase

**PyVRP v3 Phase 1 — Data and C-compatible preprocessing** (per
`docs/IMPLEMENTATION_PLAN.md` §4 Phase 1): `dat_parser`, `excel_loader`,
`experiment_config`, `geometry`, `scaling`, `facility_sizing`, `instance`, with
the row-0 regression asserting the numbers in this handoff (scale 0.797452,
cap 875, depot cost 300, UB 395.3087, the d3 single-route reconstruction).

Optional parallel task: complete the mac recompile above to obtain an independent
live C row-0 result and a machine-readable `row0_results.txt`.

## GO / NO-GO

**GO** for PyVRP Phase 1 under fixed-facility design. Row-0 congruency is proven
exactly; all flags, scaling, R/Length units, objective decomposition, and the
per-route capacity assumption are confirmed against the C source and Excel.
