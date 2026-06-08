# Next Agent Rules — LoRP-FSD v3

Operating rules for any agent continuing this project. Read
`docs/FULL_IMPLEMENTATION_AUDIT_20260608.md` first.

## Working directory & git

1. **Work only in `/Users/apena/lorp-v3`.** This is the single source of truth. The
   former `lor-v3` and all archive backups no longer exist on disk.
2. **One branch per feature.** Never commit a feature directly to `main`; branch first.
3. **One feature per commit.** Keep commits atomic and reviewable.
4. **No outputs in git.** `outputs/`, `pipeline_out/`, `.venv/`, `__pycache__/` stay
   ignored. Never commit run artefacts or solver logs.

## Experiments

5. **No long experiment before per-row timeout exists.** Row 228 (`r30x5a-1.dat`)
   stalls any 30s/3run sample for hours. Implement the per-row wall-time timeout in
   `batch.py` before running anything larger than a fast (5s/1run) smoke.

## Documentation

6. **Update audit/control docs after meaningful changes.** When a feature lands, update
   `FULL_IMPLEMENTATION_AUDIT_20260608.md` (or a new dated audit) and the relevant phase
   handoff so the next agent inherits accurate state.

## Modelling correctness (non-negotiable)

7. **Do not claim mathematical infeasibility when only the repair heuristic failed.**
   `REPAIR_INFEASIBLE` / `STUCK_NONCAPACITY_VIOLATION` mean the greedy capacity-only
   repair could not find a safe cut set — **not** that the MILP instance is infeasible.
   Report it as a heuristic limitation.
8. **Preserve real objective reconstruction.** The reported `Z_PyVRP` must always be
   rebuilt ex-post from semantic decisions on continuous scaled geometry
   (`cost_reconstruction.py`). Distance terms scaled, fixed terms raw; never scale fixed
   costs; never divide final costs by `scale`.
9. **Never report the penalized PyVRP search cost as the real LoRP cost.** PyVRP's
   internal integer objective includes artificial DA arcs, rounding, and possible
   penalty distances. It is a search signal only — never the final reported number, and
   never compared directly to the Excel UB.

## Quick verification before any commit

```
.venv/bin/python -m py_compile src/lorp_fsd/*.py
.venv/bin/python -m pytest -q -m "not integration"
```

Both must pass (currently: py_compile OK; 193 passed, 32 deselected).
