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
- UI includes model refresh/selection, scenario composer, agent management, graph, findings, execution log, cancellation, and an interactive human-review checkpoint.
- Added local SQLite memory at `data/decisionmesh.sqlite3` (override with `MEMORY_DB_PATH`). `storage/` owns schema and repositories; `services/runs.py` records accepted runs, events, snapshots, outputs, durations, failures, and cancellation. Agent catalog changes persist.
- Added separate Run History and Analytics pages with hash navigation. The live workspace stays mounted across navigation. History includes search/filter/pagination and saved findings/instructions/logs; analytics includes period filters, daily activity, and per-agent response/reliability metrics.
- Startup marks abandoned running jobs interrupted. Use a single API process per database. Invalid request schemas/unknown teams are rejected before a run exists; accepted runs with model discovery failures are saved.
- SSE version 1 envelopes match frontend TypeScript contracts. Keep transport changes coordinated.
- Poetry generated `poetry.lock`. Existing environment has Agno 3.1.12 and OpenAI 3.46.0; declared ranges target those major versions. Do not revert to outdated major bounds without checking compatibility.
- Root `.env` is loaded automatically; never print or overwrite it. Shell values take precedence.

## Verification and limits

Backend behavioral checks and Node stream parser checks are implemented. The adapter check uses real Agno code with mocked OpenAI-compatible HTTP. Check `Tasks.md` for the latest recorded results.

Resolved the reported model-server HTTP 400 / Invalid JSON error: installed Agno maps `system` messages to `developer` by default, and the local server rejects that role. The factory now maps both instruction roles to `system`. The server also returns SSE when `stream` is omitted; explicit `stream: false` is required for Agno's JSON completion path. Reproduced the original 400 live, verified a corrected raw request returns JSON/HTTP 200, and successfully ran the patched Agno agent against the actual on-device `system` model. The regression test now asserts message roles and `stream: false`. Before the enterprise extension, thirty-three backend checks passed, including persistence/analytics and database rename migration checks. The later live UI follow-up completed the full seven-role run and final synthesis.

Frontend dependencies and package-lock.json are now present. TypeScript checking and the Vite production build pass. Scenario presets, interactive review, feedback finalization, linked reruns, history resume, reload recovery, review-disabled execution, and mobile layout have been verified in Chrome with an isolated backend and fixture model responses. The later live UI follow-up also checked agent CRUD, analytics sorting, outcome detail, and all-time filtering. Protocol and display-format tests use the Node test runner.

## Operating context

Start the configured model server, then `poetry run uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000`. In `frontend/`, use `npm install` and `npm run dev`. View the app at `http://127.0.0.1:5173`; the API is on port 8000. A direct file URL cannot serve the React application.

Agent definitions and run history are persisted locally and shared by the local workspace. Earlier runs from before SQLite recording cannot be recovered automatically. The archive is not automatically injected into new model prompts. Generation is sequential and limited to one active model call across runs. Model context/output are bounded. Human oversight produces a model assessment, then the operator explicitly submits feedback and chooses finalization or a linked rerun. These choices are stored locally; authenticated reviewer identity and enterprise action authorization remain future work. The inventory enterprise extension now implements a local twin, bounded negotiation/arbitration, generic event ingestion, and approved simulated action feedback. Production enterprise connectors and real action execution remain outside scope.

Analytics definitions: completed/(completed+failed) for agent success rate; completed attempt durations only for averages and nearest-rank P95. Workflow completion rate counts partial completions and excludes running, awaiting-review, and superseded revision runs from the denominator. UTC calendar-day periods; all-time totals with a last-90-day chart. Unknown metrics remain null rather than being displayed as zero.

## DecisionMesh branding and documentation media

The product is named **DecisionMesh** across the UI, browser title, API metadata, Python/npm project metadata, README, and project docs. Default memory is `data/decisionmesh.sqlite3`. `Database` imports the previous default file using SQLite backup only when the new file does not exist; the source is preserved, committed WAL data is included, and an explicit database override stays effective. Legacy names should remain only in this compatibility path/tests.
## Provider-neutral model configuration

Use `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL` in settings, `.env`, and docs. Health JSON uses `llm_url`/`llm_online`. Defaults and `.env.example` target `http://127.0.0.1:11434/v1` (Ollama); the existing private `.env` keys were renamed while preserving connection values. Errors/UI do not refer to a specific server. The adapter preserves `system` role mapping and explicit non-streaming JSON requests for compatibility. README includes Windows PowerShell/macOS/Linux setup and links to official Ollama docs. Provider behavior is tested through mocked HTTP, not a live Ollama instance.

## Compact workspace layout

Removed the workspace intro banner, tagline, and selected-agent/system-ready counter at the user’s request. The scenario/team and live orchestration panels now start directly below the model toolbar with a compact gap. A visually hidden page heading preserves an accessible document structure.

## Interactive human review and scenario presets

The six starter scenarios live in `frontend/src/data/scenarios.ts`. Human review is a durable checkpoint: `review_required` ends the current SSE stream with run status `awaiting_review`, preserving findings and pending synthesis. `POST /api/runs/{id}/review` accepts `finalize` or `rerun` plus feedback. Finalize continues the original run using saved findings and suggestions. Rerun requires guidance, closes the original as `revised`, and creates a child with `parent_run_id` and the frozen role snapshot. Repeated submissions are rejected atomically. Pending reviews survive restart and can reopen from history; they are never inferred as approval. SQLite schema version 2 adds feedback/action/reviewer-timestamp and revision linkage fields. No reviewer identity/authentication is implied.

The local model warning was traced to a configuration mismatch: the running server was on port 1976 while the local dotenv pointed to 11434. Corrected only the private endpoint and verified backend health online; shared defaults remain provider-neutral. Connection warnings now show the actual configured endpoint.

## Research alignment audit — 2026-11-05

See [PaperAlignment.md](PaperAlignment.md) for the mapping and [EnterpriseLoop.md](EnterpriseLoop.md) for the subsequent implementation. The supplied paper is a conceptual literature review, not an executable algorithm or a fixed seven-agent specification. The initial audit identified absent ingestion, negotiation, twin, action-feedback, and evaluation layers. Those now have a connected local inventory implementation. General distributed enterprise execution, authenticated organizational authority, broader domains, and empirical field validation remain open. SSE is still advisory execution progress; the new ingestion API is separate. Successful model calls do not establish decision quality.

## Enterprise loop implementation — 2026-11-05

- Schema version 3 transactionally adds enterprise events, versioned inventory entities, decision cases, action approvals/executions, and research jobs. Existing run/review records are preserved. Use one API process per database.
- Normalized events are deduplicated by source/event ID, checked for age/order, retained with acceptance/rejection receipts, and atomically trigger state updates and decision cases. `scripts/ingest_event.py` is the portable external producer. Enterprise lab also has editable JSON and a five-second demonstration feed.
- `orchestration/twin.py` calculates one-day normal/overtime/backup/defer candidates; no LLM arithmetic determines outcomes. `negotiation.py` validates proposals/evidence, records service/cost conflicts, enforces a hard budget, and explains arbitration/rejections. Rule-based seed proposals are labeled separately from Agno calls. Actual negotiations share peer proposals over at most two rounds and force review for disagreements/incomplete results.
- `actions/simulator.py` only applies local inventory transitions. Approval binds the case revision, state version, action fingerprint, reviewer attribution, rationale/override, and expiry. Execution is idempotent and atomically saves a receipt and feedback case. Real enterprise rights/authentication and adapters are not implemented.
- Enterprise lab shows snapshots, cases, drift, negotiation traces, simulation comparisons, approvals, outcome feedback, and event receipts. Linked workspace runs receive normalized case evidence; required review is enforced server-side. Free-text workspace specialists still share the scenario independently.
- Research compares one centralized Agno analyst against up to four specialists on six fixed inventory scenarios for one to three repetitions. It saves dataset/hash, instructions, prompts, rules, trials, errors, synthetic quality/oracle comparisons, latency, conflicts, policy/evidence metrics, and JSON exports. Queueing counts as machine time; human wait is excluded. Recovery, trust, actual human intervention, and semantic explanation correctness are unmeasured.
- Jobs persist progress, survive navigation, support cancellation, share the local model semaphore, and become interrupted after a crash; graceful shutdown cancels them. At most two research jobs, one benchmark, and one negotiation per case are admitted. A new observation prevents old negotiation results or approvals from being committed.
- Initial implementation was build-checked. The subsequent live UI follow-up below adds behavioral/browser/model evidence; enterprise field validation is still absent.


## Live UI follow-up — 2026-11-06

Used the actual UI at `http://127.0.0.1:5173/#/` with the configured local system model. Completed the seven-role workflow, saved feedback/finalization, agent CRUD, history/analytics, eight valid proposals over two negotiation rounds, approved simulated action and idempotent retry, outcome/drift ingestion, duplicate/stale protection, continuous feed, policy-linked workspace input, a feedback-based rerun recovered from history after reload, mobile finalization, and benchmark cancellation. The full benchmark completed 12 trials and displayed/exported its saved results. Final Chrome console had no errors. See [Testing.md](Testing.md).

Fixed a real compatibility problem: proposal generation inherited Markdown instructions and the model copied long source IDs inaccurately. `AgnoRunner.propose` now uses system-level JSON instructions with Markdown disabled; prompts give compact E1/E2 aliases that validation resolves to immutable evidence IDs. One explicit format repair is allowed and retained; both benchmark architectures use the same collector and include every repair in call counts/timings. Provider failures remain visible; no unsupported source references are accepted. Added the missing local SVG icon.

The reusable multi-entity live pass also exposed a late default-selection effect overwriting the chosen twin after navigation. Entity initialization now uses a functional state update; entity/case/job views reject data for other selection IDs. The browser suite waits for the exact selected case. Preserve this behavior when changing polling/navigation.

Regression suite now has 50 backend tests plus 5 frontend protocol/format tests; the production build passes. Added Playwright and a reusable live UI script (`npm --prefix frontend run test:live`). QA records are retained; local reports/screenshots are under the ignored `data/ui-tests/` directory. The first measured six-case comparison scored centralized 50.00 and orchestrated 95.44 under the synthetic rubric, with 6 versus 45 model calls and recorded provider failures. This is one small, unequal-compute, policy-confounded local comparison; do not present it as general enterprise performance evidence.

The saved live suite subsequently passed 14 core checks end to end after the selection fix; a separate stress pass checked 12 immediate multi-entity navigation switches. Its second full benchmark scored centralized 50.00 and orchestrated 73.68 with 6 versus 38 calls. Both completed benchmarks contain 12 trials (24 total); cancellation/review recovery were verified separately. The between-run quality variation is material and must accompany any discussion of these local results.
