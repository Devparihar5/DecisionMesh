# DecisionMesh — Architecture

## Scope and stack

This local MVP implements specialist-agent coordination, human review, and a supply-chain enterprise loop: normalized event ingestion, versioned inventory state, bounded proposal negotiation, deterministic arbitration, a digital twin, approved simulated actions, outcome reassessment, and synthetic research evaluation. Real enterprise execution, authenticated organizational authority, distributed deployment, and tamper-resistant auditing remain future work. See [EnterpriseLoop.md](EnterpriseLoop.md) for contracts and assumptions.

- **Backend:** Python 3.12, FastAPI, Pydantic, Agno, async HTTPX, python-dotenv. Dependencies managed with Poetry and `poetry.lock`.
- **Frontend:** React 19, TypeScript, Vite, CSS, browser Fetch/Streams APIs.
- **Models:** Agno `OpenAIChat` calls the configured OpenAI-compatible server through `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL`. The example/default endpoint is `http://127.0.0.1:11434/v1` for Ollama; other compatible servers use the same configuration.
- **Local storage:** standard-library SQLite with WAL, explicit transactions, one-time catalog seeding, and schema versioning.
- **Live updates:** versioned Server-Sent Events over a POST request, consumed with Fetch.

## Components

```mermaid
flowchart LR
  UI[React components] --> HOOK[useRun hook]
  HOOK --> CLIENT[Typed API / SSE services]
  CLIENT -->|Vite proxy /api| API[FastAPI routers]
  API --> CAT[Agent registry]
  API --> MODELS[Model discovery service]
  API --> RUNS[Durable run service]
  RUNS --> DB[(Local SQLite)]
  CAT --> DB
  RUNS --> COORD[Workflow coordinator]
  API --> ANALYTICS[Analytics service]
  ANALYTICS --> DB
  COORD --> RUNNER[Agno runner]
  RUNNER --> LLM[Configured model server]
  MODELS --> LLM
  COORD -->|SSE events| CLIENT
```

## Backend responsibilities

| Path | Responsibility |
| --- | --- |
| `backend/app/main.py` | Composition root: app creation, lifespan, CORS, error handler, router registration |
| `core/config.py` | Environment loading and immutable settings |
| `core/errors.py` | Transport-independent application errors |
| `schemas/` | Agent, run, and health boundary contracts |
| `agents/defaults.json` | Seven starter agent definitions |
| `agents/registry.py` | Catalog CRUD, stable IDs, core-role protection, selection validation |
| `agents/factory.py` | Agno construction, local model adapter, concurrency limit, timeout |
| `services/models.py` | Async discovery, model ID validation, connection health |
| `services/runs.py` | Persisted run lifecycle, including cancellation and setup failures |
| `services/analytics.py` | Aggregate, daily, and per-agent execution metrics |
| `storage/` | SQLite schema, catalog persistence, run/event transactions and queries |
| `orchestration/coordinator.py` | Specialist, oversight, synthesis lifecycle and shared findings |
| `orchestration/events.py` | Version 1 SSE envelope and serialization |
| `api/` | Request validation, service injection, HTTP responses and stream heartbeats |

Services belong to application lifespan state rather than mutable module-level registries. The registry returns copies so a run operates on a snapshot. Agno uses asynchronous calls; cancellation propagates to the in-flight request. Generation is limited to one call at a time across runs to suit a local model server. The service supports a single local workspace backed by SQLite. Catalog caching is per application; the database is authoritative across restarts.

The Agno factory overrides OpenAIChat's default `system` → `developer` role mapping to preserve `system` on the wire. Some compatible servers reject `developer` or default to SSE when `stream` is absent, so the factory explicitly sets `request_params={"stream": False}` for the non-streaming Agno execution path. This model response mode is independent of the API's workflow SSE stream.

## Frontend responsibilities

`src/main.tsx` mounts React. `App.tsx` switches between Workspace, History, Analytics, Enterprise lab, and Research using hash routes. The workspace remains mounted during navigation so it can finish its stream. That page coordinates catalog/configuration state; presentational components render controls and results. `useRun` owns run state, event accumulation, elapsed time, cancellation, and terminal-stream validation. API requests and chunk-safe SSE parsing live in `src/services/`. Shared TypeScript contracts live in `types.ts`; design tokens and responsive styling live in `styles/global.css`. `frontend/public/` contains assets only.

## API and event contracts

| Method / path | Purpose |
| --- | --- |
| `GET /api/health` | Model endpoint, availability, catalog, default model, Agno availability |
| `GET /api/agents` | Current role definitions |
| `POST /api/agents` | Create a specialist |
| `PUT /api/agents/{id}` | Update a specialist without changing its ID |
| `DELETE /api/agents/{id}` | Remove a specialist; core roles are protected |
| `POST /api/run` | Validate scenario/team, persist submission, resolve model, and stream workflow events |
| `GET /api/runs` | Paginated run summaries; search by scenario/ID and filter by outcome |
| `GET /api/runs/{id}` | Saved scenario, immutable team snapshot, execution results, and event timeline |
| `POST /api/runs/{id}/review` | Submit operator guidance and stream finalization or a linked rerun |
| `POST /api/runs/{id}/cancel` | Cancel a pending human-review checkpoint |
| `GET /api/analytics?days=30` | Aggregate and per-agent metrics for 7/30/90 days or all time (`days=0`) |

Each SSE data envelope has `version`, `sequence`, `run_id`, `timestamp`, and `type`. Event types are `start`, `agent_start`, `agent_done`, `agent_error`, `review_required`, `review_submitted`, `complete`, and `error`. Agent events use `agent_id` and `name`; results include content/duration. Completion includes total duration, operator review status, and whether results are partial. A heartbeat comment is sent every 10 seconds while awaiting model output. Reconnection/replay is not implemented.

## Workflow

1. Validate input/team and persist the scenario, review preference, and selected agent snapshot before model discovery. Setup failures are retained as failed runs.
2. Resolve the model and emit run start. Store each event and its execution state in one transaction before publishing it to the browser.
3. Run specialists sequentially against the shared scenario. Publish each result or failure immediately.
4. When enabled, run human oversight against specialist findings. Store its assessment with those findings.
5. When review is enabled, persist a checkpoint and wait for the operator to choose finalization or a linked rerun. On finalization (or immediately when review is disabled), run synthesis against the findings, oversight output, missing perspectives, and operator guidance. Bound accumulated context and label truncation.
6. Emit success (possibly partial) only after synthesis succeeds. If all specialists fail or synthesis fails, emit an error terminal state.

## Development and boundaries

Vite runs on `127.0.0.1:5173` and proxies `/api` to FastAPI at `127.0.0.1:8000`. Backend dependencies use Poetry; frontend dependencies use npm. Environment settings load from root `.env`, with shell values taking precedence. API responses do not expose credentials; Agno telemetry is disabled. UI and service errors avoid dumping scenarios or credentials.

The database contains `agents`, `runs`, `run_events`, `agent_executions`, and initialization metadata. Cancelled work is retained; never-started agents are skipped. On restart, abandoned running workflows become interrupted with unknown total duration rather than counting downtime as generation time. Use one API process per database so startup recovery cannot interrupt another process's live work. Catalog initialization occurs once; removing a starter specialist is respected after restarts. Historical records preserve deleted roles and the instructions that were used.

Analytics derive only from persisted attempts. Agent success rate excludes cancelled, interrupted, active, and skipped executions; average/P95 durations use successful completions. Daily buckets use UTC. Period totals are computed independently of the last-90-day chart limit for all-time queries. The history feature provides local execution memory, not automatic cross-run retrieval into agent prompts or an immutable compliance ledger.

Future work includes authenticated organizational authority, production enterprise connectors/actions, distributed execution, and field evaluation. Digital-twin state, arbitration/negotiation, generic event ingestion, local approval-bound simulated actions, and synthetic comparative benchmarks are now implemented for the inventory domain. No external enterprise actions are performed.

## Brand migration and documentation capture

The default database filename is `decisionmesh.sqlite3`. A missing new default is initialized from the prior default through SQLite backup, which includes committed WAL data and preserves the original file. An existing new database is never reimported, and explicit custom database paths are respected.

Model health responses expose `llm_url` and `llm_online`. UI connection checks and error messages are provider-neutral. Ollama uses its OpenAI-compatible routes, not its native `/api/chat` interface. Connection settings come from generic configuration rather than platform-specific branching.

## Interactive review lifecycle (schema version 2)

When human review is enabled, analysis and the oversight assessment end with a persisted `review_required` event and `awaiting_review` state. The stream closes without running synthesis. The React hook opens the review dialog and retains the checkpoint; history can restore it after reload. A review POST is claimed atomically so duplicate submissions return 409. `finalize` appends `review_submitted` and synthesis to the existing run. `rerun` records the original as `revised` and starts a linked child with frozen role definitions and operator guidance. Review action, feedback, input guidance, parent ID, and timestamps are persisted. Model discovery occurs before claiming, leaving checkpoints retryable if the provider is unavailable. `POST /api/runs/{id}/cancel` cancels a pending review explicitly.

SQLite version 2 migrates existing run rows with nullable revision/review columns and default empty input guidance. Recovery interrupts active generations only; pending human reviews remain pending. Completion metrics exclude running, pending-review, and superseded revisions from the denominator. Scenario starters are frontend data and remain editable before submission.

## Enterprise loop and research extension (schema version 3)

React now also routes to **Enterprise lab** and **Research**. The new clients/contracts/hooks/components are separate from workspace run transport. Enterprise snapshots and jobs use bounded polling; SSE remains the existing advisory run protocol. `RunInput.decision_case_id` attaches a saved case to a brief. The backend validates freshness of the linked state, appends normalized evidence, and forces required review. The start event persists the case link.

`schemas/enterprise.py` defines events, inventory state, proposals, rounds, simulations, approvals, and jobs. `orchestration/twin.py` calculates candidate outcomes; `negotiation.py` validates evidence and arbitrates under the hard budget. `services/enterprise.py` normalizes observations and creates cases. `actions/simulator.py` applies local transitions only. `services/research_jobs.py` supervises bounded Agno work; `evaluation.py` compares architectures against the versioned six-case corpus. All use the existing shared model semaphore.

Schema version 3 adds `twin_entities`, `enterprise_events`, `decision_cases`, `action_approvals`, `action_executions`, and `research_jobs`. Migration is transactional and additive. Ingestion commits an event, state version, and case together. Negotiation checks the state and case revision before atomically committing its result/job completion. Execution checks approval expiry, candidate fingerprint, case revision, state version, hard policy, and idempotency before atomically saving the transition, acknowledgment, and feedback case. Active jobs are recovered as interrupted after a crash; generations are not resumed.

The complete route list, assumptions, and metric definitions are in [EnterpriseLoop.md](EnterpriseLoop.md). Workspace analytics cover `runs`/`agent_executions`; research and enterprise records remain separate populations. Production reviewer authentication, general digital twins, real execution adapters, automatic generation recovery, and enterprise-scale validation remain open.

Proposal generation has a separate Agno runner path with Markdown disabled and a system-level JSON contract. Compact evidence aliases are mapped back to immutable source IDs by strict validation. The shared collector permits one format repair per proposal and retains/counts each attempt, including in the centralized benchmark. The ordinary advisory runner retains its Markdown behavior. Polling consumers verify that snapshot/detail IDs match the current selection; default entity initialization cannot overwrite a later user choice. See [Testing.md](Testing.md) for the live regressions behind these choices.
