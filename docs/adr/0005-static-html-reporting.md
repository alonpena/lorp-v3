# Reporting is static-HTML-first; the legacy Streamlit app is not the path forward

Reporting and the result browser are built as **static HTML** generated after a run
(`outputs/<run_id>/index.html` + per-instance `index.html`), regenerable from
`report.json` + `consolidated.csv` without rerunning any solve. No server is required to
view results, which suits sharing with the professor and archiving runs.

**Considered options:** the repo contains a legacy Streamlit app
(`app_capacity_repair_solver.py`) that imports the **legacy** root modules
(`dat_loader`, `instance_adapter`, `run_capacity_repair_batch`), not the v3 `lorp_fsd`
package, plus stale `pipeline_out/streamlit_demo_row*` outputs. Extending it would couple
the v3 reporting story to legacy code and require a running Python server for every view.

**Consequence:** the static HTML report is the primary surface. If a live single-row
runner is later needed, it should be a thin layer over `runner.run_row_from_excel`
(prefer a minimal Flask/FastAPI endpoint over Streamlit), emitting the same per-instance
HTML — not a fork of the legacy app.
