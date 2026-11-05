# DecisionMesh — Project Memory

## Objective and user requirements

Build a Python/Agno MVP inspired by `docs/Multi-agent_orchestration_architectures_for_real-t.pdf`, with at least seven starting agents, custom agent creation, and a live orchestration UI. Use a configurable OpenAI-compatible model provider; support Ollama across Windows, macOS, and Linux through generic settings. Python dependency management must use Poetry. The UI must use React, and backend directories must contain their actual modules rather than leaving logic in `main.py`.

## Current implementation

- Backend is a modular FastAPI application under `backend/app/`. `main.py` only assembles the app and services.
- Routes, Pydantic schemas, settings, agent catalog, Agno factory/runner, async model discovery, workflow coordinator, and SSE contracts have separate modules.
- Frontend is React 19 + TypeScript + Vite under `frontend/`, with real component, hook, page, API/stream service, and style files.
- Removed the previous `frontend/public/index.html`, `app.js`, and `app.css` implementation. React now enters through `frontend/index.html` and `src/main.tsx`.
- Seven default agents are in `backend/app/agents/defaults.json`. Specialist CRUD is supported; oversight and synthesis are protected core roles.
- The coordinator passes oversight output into synthesis, marks partial failures, measures per-agent durations, and cancels async work on disconnect.
- UI includes model refresh/selection, scenario composer, agent management, graph, findings, execution log, cancellation, and advisory review status.
- Added local SQLite memory at `data/decisionmesh.sqlite3` (override with `MEMORY_DB_PATH`). `storage/` owns schema and repositories; `services/runs.py` records accepted runs, events, snapshots, outputs, durations, failures, and cancellation. Agent catalog changes persist.
- Added separate Run History and Analytics pages with hash navigation. The live workspace stays mounted across navigation. History includes search/filter/pagination and saved findings/instructions/logs; analytics includes period filters, daily activity, and per-agent response/reliability metrics.
- Startup marks abandoned running jobs interrupted. Use a single API process per database. Invalid request schemas/unknown teams are rejected before a run exists; accepted runs with model discovery failures are saved.
- SSE version 1 envelopes match frontend TypeScript contracts. Keep transport changes coordinated.
- Poetry generated `poetry.lock`. Existing environment has Agno 3.1.12 and OpenAI 3.46.0; declared ranges target those major versions. Do not revert to outdated major bounds without checking compatibility.
- Root `.env` is loaded automatically; never print or overwrite it. Shell values take precedence.

## Verification and limits

Backend behavioral checks and Node stream parser checks are implemented. The adapter check uses real Agno code with mocked OpenAI-compatible HTTP. Check `Tasks.md` for the latest recorded results.

Resolved the reported model-server HTTP 400 / Invalid JSON error: installed Agno maps `system` messages to `developer` by default, and the local server rejects that role. The factory now maps both instruction roles to `system`. The server also returns SSE when `stream` is omitted; explicit `stream: false` is required for Agno's JSON completion path. Reproduced the original 400 live, verified a corrected raw request returns JSON/HTTP 200, and successfully ran the patched Agno agent against the actual on-device `system` model. The regression test now asserts message roles and `stream: false`. Twenty-six backend checks pass, including persistence/analytics and database rename migration checks. Full seven-agent live verification remains outstanding.

Frontend dependencies and package-lock.json are now present. TypeScript checking and the Vite production build pass. Browser interaction/visual verification is still outstanding. Protocol and display-format tests use the Node test runner.

## Operating context

Start the configured model server, then `poetry run uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000`. In `frontend/`, use `npm install` and `npm run dev`. View the app at `http://127.0.0.1:5173`; the API is on port 8000. A direct file URL cannot serve the React application.

Agent definitions and run history are persisted locally and shared by the local workspace. Earlier runs from before SQLite recording cannot be recovered automatically. The archive is not automatically injected into new model prompts. Generation is sequential and limited to one active model call across runs. Model context/output are bounded. Human oversight is a model assessment; the operator review flag is advisory rather than a stored approval action. Digital twins, negotiation/arbitration, enterprise connectors, and action execution are not implemented.

Analytics definitions: completed/(completed+failed) for agent success rate; completed attempt durations only for averages and nearest-rank P95. Workflow completion rate counts partial completions and excludes running jobs from the denominator. UTC calendar-day periods; all-time totals with a last-90-day chart. Unknown metrics remain null rather than being displayed as zero.

## DecisionMesh branding and documentation media

The product is named **DecisionMesh** across the UI, browser title, API metadata, Python/npm project metadata, README, and project docs. Default memory is `data/decisionmesh.sqlite3`. `Database` imports the previous default file using SQLite backup only when the new file does not exist; the source is preserved, committed WAL data is included, and an explicit database override stays effective. Legacy names should remain only in this compatibility path/tests.
## Provider-neutral model configuration

Use `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL` in settings, `.env`, and docs. Health JSON uses `llm_url`/`llm_online`. Defaults and `.env.example` target `http://127.0.0.1:11434/v1` (Ollama); the existing private `.env` keys were renamed while preserving connection values. Errors/UI do not refer to a specific server. The adapter preserves `system` role mapping and explicit non-streaming JSON requests for compatibility. README includes Windows PowerShell/macOS/Linux setup and links to official Ollama docs. Provider behavior is tested through mocked HTTP, not a live Ollama instance.

## Compact workspace layout

Removed the workspace intro banner, tagline, and selected-agent/system-ready counter at the user’s request. The scenario/team and live orchestration panels now start directly below the model toolbar with a compact gap. A visually hidden page heading preserves an accessible document structure.
