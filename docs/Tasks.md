# DecisionMesh — Tasks

## Completed

- [x] Inspect the reference paper and create six project documents.
- [x] Manage backend dependencies with Poetry and generate `poetry.lock`.
- [x] Split backend responsibilities into implemented modules: core, schemas, API, agents, services, orchestration.
- [x] Keep `main.py` limited to application assembly and service lifespan.
- [x] Replace the standalone DOM-script UI with React + TypeScript + Vite.
- [x] Add actual components, hooks, API/stream services, shared types, and responsive styles under `frontend/src/`.
- [x] Implement seven starter roles with specialist creation, editing, removal, and stable selection.
- [x] Connect local model discovery/selection through the Agno OpenAI-compatible adapter.
- [x] Stream run lifecycle to the graph, findings, timer, and execution log.
- [x] Pass oversight findings into synthesis; expose failed/missing perspectives and partial completion.
- [x] Add cancellation, per-agent timeout, bounded model concurrency, and stream heartbeats.
- [x] Validate backend behavior, mocked Agno transport, and chunk-safe SSE parsing.
- [x] Update README and docs for separate API and React development servers.
- [x] Reproduce model-server HTTP 400 live and fix the rejected `developer` role plus omitted stream mode in the Agno adapter.
- [x] Add request-contract regression assertions and verify the patched Agno agent against the actual local `system` model.

## Remaining verification

- [x] Frontend npm dependencies and `frontend/package-lock.json` are now available.
- [x] Run `npm run build` for TypeScript and Vite production checks.
- [ ] Run a browser interaction check for a complete workflow, CRUD, mobile layout, and cancellation.
- [ ] Verify a full workflow with the configured model server's selected model.

## Follow-up product work

- [x] Persist agent definitions, run records, and execution events locally in SQLite.
- [x] Add history search/filter/pagination and detailed saved context/findings/event timeline.
- [x] Add an Analytics page with period filters, daily activity, and per-agent reliability/latency metrics.
- [x] Retain failed/cancelled runs, recover interrupted runs on restart, and preserve historical agent definitions.
- [x] Verify local persistence, cancellation, historical identity, metric formulas, and history/analytics API routes.
- [ ] Add real human approval/override records and decision ownership.
- [ ] Implement digital-twin state and scenario simulation.
- [ ] Add negotiation/arbitration and rejected-alternative tracking.
- [ ] Add enterprise connectors and an authorized action execution boundary.
- [ ] Compare architectures using latency, quality, conflict rate, recovery, explanation completeness, policy compliance, and human intervention metrics.
- [ ] Add event replay/reconnect support for long runs.

## Known limits

The MVP is an advisory local workspace. Agent definitions, run snapshots, findings, and events survive backend restarts in local SQLite. Automatic cross-run recall into prompts is not implemented. Agent calls run sequentially for local model capacity. A short live Agno generation has succeeded; the full seven-agent live workflow and browser interaction checks remain outstanding.

## Latest checks

- `poetry run python -m unittest discover -s backend/tests -v`: 26 passing checks, including restart persistence, cancellation, deterministic metrics, database rename migration, API routes, and real Agno adapter execution against mocked HTTP.
- `node --experimental-strip-types --test tests/*.test.mjs` from `frontend/`: 5 passing protocol/display-format checks.
- `poetry check --lock`: passed, with metadata deprecation warnings from the existing Poetry project format.
- `npm run build`: TypeScript validation and Vite production build passed with the memory/history/analytics pages.

## DecisionMesh branding and README animation

- [x] Apply DecisionMesh branding to UI, browser title, API, Python/npm metadata, README, and docs.
- [x] Rename default storage to `decisionmesh.sqlite3` with a data-preserving legacy import and migration regression checks.
- [x] Record an illustrative seven-agent workflow from the actual React panel and save the looping GIF in `docs/assets/`.
- [x] Embed the GIF in a rewritten README covering features, setup, architecture, memory, analytics, and configuration.
- [x] Inspect start, intermediate, and completion GIF frames; validate browser execution without JavaScript errors.

## Provider-neutral configuration

- [x] Rename model environment variables to `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL`.
- [x] Rename health contract/UI properties to `llm_url` and `llm_online`.
- [x] Preserve private connection values while migrating local dotenv keys.
- [x] Remove platform/server-specific naming from runtime code, messages, metadata, and docs.
- [x] Document Ollama setup on Windows/macOS/Linux and alternate compatible endpoints.
- [x] Add environment override, default endpoint, Ollama-shaped catalog, and custom-provider tests.

- [x] Remove the workspace intro banner and selected-agent/status counter; move operational panels directly below the toolbar.
