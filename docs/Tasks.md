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

## Recent requested changes

- [x] Add six editable scenario presets: supplier outage, demand surge, service disruption, budget pressure, data exposure, and warehouse bottleneck.
- [x] Pause before decision synthesis when human review is enabled and open an interactive review dialog.
- [x] Accept operator suggestions and generate the final brief from saved findings plus that guidance.
- [x] Offer a feedback-based rerun as a linked revision, preserving the original run and its metrics.
- [x] Persist operator choices/feedback, support review later, and resume pending reviews from Run History after page/backend restarts.
- [x] Reject empty rerun guidance and duplicate review submissions; retain pending review when model discovery fails.
- [x] Include awaiting-review/revised outcomes in history and analytics, excluding those outcomes from the completion-rate denominator.
- [x] Correct the local endpoint mismatch and show the configured endpoint in connection-error notices.
- [x] Check the browser flows for scenario selection, finalization, rerun, history resume, reload recovery, review-disabled synthesis, and mobile layout using isolated model fixtures.

## Remaining verification

- [x] Frontend npm dependencies and `frontend/package-lock.json` are now available.
- [x] Run `npm run build` for TypeScript and Vite production checks.
- [x] Check scenario/review workflow, cancellation, history resume, and mobile layout in Chrome with an isolated backend and fixture model responses.
- [x] Check live agent CRUD, analytics sorting/outcome details, and all-time filtering in Chrome.
- [x] Complete the real seven-role workflow with the configured system model, human feedback, and final synthesis.
- [x] Check enterprise ingestion/retries, negotiation, stale approvals, idempotent execution, and feedback live; cover ordering/expiry/restart recovery with isolated regression databases.
- [x] Check Enterprise lab and Research in live Chrome, including mobile layouts, real job cancellation, and reload recovery.
- [x] Complete two 12-trial live-model benchmarks (24 total), inspect saved UI results/exports, retain partial failures, and cross-check call counts.

## Follow-up product work

- [x] Persist agent definitions, run records, and execution events locally in SQLite.
- [x] Add history search/filter/pagination and detailed saved context/findings/event timeline.
- [x] Add an Analytics page with period filters, daily activity, and per-agent reliability/latency metrics.
- [x] Retain failed/cancelled runs, recover interrupted runs on restart, and preserve historical agent definitions.
- [x] Verify local persistence, cancellation, historical identity, metric formulas, and history/analytics API routes.
- [x] Save local human-review decisions, suggestions, and revision relationships.
- [ ] Add authenticated reviewer identity, decision ownership, and production approval/override authorization.
- [x] Implement versioned inventory digital-twin state and candidate action simulation.
- [x] Add bounded Agno negotiation, deterministic arbitration, policy escalation, and rejected-alternative tracking for inventory decisions.
- [x] Add normalized external event ingestion and an approval-bound, idempotent local action simulator with outcome feedback.
- [x] Implement centralized/orchestrated synthetic benchmarks for decision quality, machine time, conflicts, policy compliance, evidence references, and review requirements.
- [ ] Add production enterprise adapters, authenticated action authority, and measured recovery, semantic explanation, actual intervention, and field-quality evaluation.
- [ ] Add event replay/reconnect support for long runs.

## Research paper alignment

- [x] Audit the current source against the full paper, including Figure 1, Figure 3, and Future Directions; record evidence and gaps in [PaperAlignment.md](PaperAlignment.md).
- [x] Distinguish the implemented local decision-support MVP from the broader research architecture and separate runtime reliability from decision quality.
- [x] Persist typed observations, source evidence, action proposals, alternatives, and explicit conflicts; pass normalized inventory evidence to linked workspace runs.
- [x] Add bounded negotiation/arbitration, priority rules, and mandatory policy-triggered review for linked inventory cases.
- [x] Add external event ingestion with freshness, deduplication, versioned domain state, and reassessment triggers; include a portable observation producer.
- [x] Implement a domain digital twin that simulates four candidate actions and retains comparable outcomes and observation drift.
- [x] Add a simulated approval-bound action adapter with expiry/revision checks, idempotent dispatch, acknowledgments, override records, and outcome feedback.
- [x] Build two controlled architecture baselines, six saved scenarios, quality/oracle rules, repetitions, machine-phase timing, conflict/policy/evidence metrics, and JSON experiment exports.
- [x] Add Enterprise lab and Research React pages with persisted job progress, cancellation, case traces, and links to the advisory workspace.
- [x] Add transactional schema version 3 and retain previous run/review tables.
- [ ] Measure recovery time, semantic explanation completeness, actual human intervention/trust, and enterprise-scale quality; add additional architecture variants and domains.

These checks record implementation, not new behavioral verification. [EnterpriseLoop.md](EnterpriseLoop.md) describes the executable local scope and remaining limits. Earlier workspace checks do not establish coverage of this extension.

## Known limits

The MVP is an advisory local workspace. Agent definitions, run snapshots, findings, and events survive backend restarts in local SQLite. Automatic cross-run recall into prompts is not implemented. Agent calls run sequentially for local model capacity. The seven-role workflow, human feedback, linked rerun/history recovery, and broader CRUD/analytics interactions have now been checked against the live UI and model. Earlier fixture checks remain useful regression evidence.

The enterprise extension supplies a deterministic inventory twin, generic normalized input API, and local simulated execution. No production ERP or physical action adapter is connected. Reviewer attribution is not authenticated enterprise authority. Research quality is synthetic, source-ID coverage does not prove explanation truth, and active jobs do not automatically resume after restart. Live Chrome flows and the 12-trial benchmark are now verified on the configured local system model. Windows/live Ollama and enterprise field validation remain outside this pass.

## Latest checks

Latest follow-up: **50 backend tests**, **5 frontend protocol/format tests**, and the production build pass. Staged live Chrome checks covered 18 distinct flows. The saved Playwright suite then passed 14 core checks end to end, and a selection stress pass completed 12 immediate multi-entity switches. Two full live benchmarks completed 24 trials total. Fixed proposal JSON/Markdown conflicts, unstable source-ID copying, the favicon 404, and a default-selection/stale-detail race. Added a locked Playwright dependency and `npm --prefix frontend run test:live`. See [Testing.md](Testing.md) for measured results, between-run quality variation, and limits.

The following results are historical, from before the enterprise extension:

- `poetry run python -m unittest discover -s backend/tests -v`: 33 passing checks, including human-review gating, guidance in synthesis, linked reruns, duplicate rejection, restart persistence, cancellation, deterministic metrics, API routes, and mocked Agno transport.
- `node --experimental-strip-types --test tests/*.test.mjs` from `frontend/`: 5 passing protocol/display-format checks.
- `poetry check --lock`: passed, with metadata deprecation warnings from the existing Poetry project format.
- `npm run build`: TypeScript validation and Vite production build passed with scenario presets and interactive review.
- Chrome browser verification: seven scenario/review/navigation/mobile checks passed without JavaScript errors using isolated fixture model responses.

## DecisionMesh branding and README animation

- [x] Apply DecisionMesh branding to UI, browser title, API, Python/npm metadata, README, and docs.
- [x] Rename default storage to `decisionmesh.sqlite3` with a data-preserving legacy import and migration regression checks.
- [x] Record an illustrative seven-agent workflow from the actual React panel and save the looping GIF in `docs/assets/`.
- [x] Embed the GIF in a rewritten README covering features, setup, architecture, memory, analytics, and configuration.
- [x] Replace the failing README architecture rich display with a standalone SVG image and retain editable diagram source.
- [x] Inspect start, intermediate, and completion GIF frames; validate browser execution without JavaScript errors.

## Provider-neutral configuration

- [x] Rename model environment variables to `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL`.
- [x] Rename health contract/UI properties to `llm_url` and `llm_online`.
- [x] Preserve private connection values while migrating local dotenv keys.
- [x] Remove platform/server-specific naming from runtime code, messages, metadata, and docs.
- [x] Document Ollama setup on Windows/macOS/Linux and alternate compatible endpoints.
- [x] Add environment override, default endpoint, Ollama-shaped catalog, and custom-provider tests.

- [x] Remove the workspace intro banner and selected-agent/status counter; move operational panels directly below the toolbar.
