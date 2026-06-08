# C/Gurobi LoRP-FSD is the source of truth; congruency proven by static reconstruction

The benchmark of record is the deterministic LoRP-FSD MILP (`det_LoRP_DSD()` in
`reference/LoRPSD/stcmodels.cpp`, reached via `-original 0`), whose solved rows live in
`results_MILP.xlsx` (sheet `LoRP-FSD`). The PyVRP v3 pipeline must reproduce that model's
objective and feasibility semantics, not invent its own. We validated this on row 0
(`r40x5a-1.dat`) by **exact static reconstruction** from `.dat` geometry + the C-source
formulas + the row-0 CLI parameters, obtaining `Z = 95.3087 + 0 + 300 + 0 = 395.3087`,
equal to Excel `UB = 395.309`.

**Considered options:** running the C binary directly was the obvious alternative, but
`reference/LoRPSD/LoRPSD` is a Linux x86-64 ELF and the host is macOS arm64
(`exec format error`); no Docker, Rosetta does not run Linux ELF. Static reconstruction is
a stronger check than re-running Gurobi because it exercises every flag, scaling step, and
unit explicitly. A mac-arm64 recompile recipe is recorded in
`HANDOFF_C_CONGRUENCY_PHASE.md` for optional later confirmation.

**Consequence:** row 0 is a locked regression (`scale = 0.79745222`, cap 875, depot cost
300, `Z = 395.3087`). Any change that moves it is a bug. `problemID = 0` (Arslan scaling)
is the only supported mode; other values raise `NotImplementedError`.
