# DecisionMesh — Product Requirements

## Product

**DecisionMesh** is a local decision-intelligence workbench that coordinates specialized AI agents around a time-sensitive enterprise scenario. It turns an event or question into a traceable set of specialist assessments and a governed recommendation.

## Users

- An operations or business analyst who needs a fast, cross-functional assessment.
- A decision owner who needs clear trade-offs, uncertainty, and escalation paths.
- A developer evaluating agent orchestration patterns against a local model.

## Problem

Single-model analytics often omit specialist perspectives, coordination, accountability, and human review. The paper motivates a first-class orchestration layer that combines agent coordination, real-time context, explainability, and governance.

## MVP goals

- Use a React + TypeScript frontend with Vite, and a Python backend separated into functioning modules for API, schemas, agents, services, and orchestration.
- Run at least six to seven useful specialist agents on one scenario.
- Use Agno as the Python agent framework and a configurable OpenAI-compatible model server, including Ollama across Windows, macOS, and Linux.
- Show each agent's live state and results in a usable UI.
- Let the operator add and remove specialist agents.
- Produce a synthesis with rationale, risks, next steps, and explicit approval status.
- Make model connection and failure states clear.

## Functional requirements

1. **Local model connection:** inspect health and available model IDs from the configured endpoint; choose an available model.
2. **Agent catalog:** show defaults (Event Analyst, Risk & Resilience, Operations, Finance, Policy & Compliance, Human Oversight, Decision Synthesizer); add/edit/remove specialist agents.
3. **Scenario run:** accept a scenario, selected agents, and approval preference.
4. **Orchestration:** share one scenario across specialists; pass their results to the oversight and synthesis stages.
5. **Live view:** display run lifecycle, agent state, event order, elapsed time, results, and errors as the run proceeds.
6. **Human review:** pause before synthesis when enabled, collect operator suggestions in a modal, and require an explicit choice to finalize or rerun. Persist those choices and support later review from history.
7. **Decision brief:** provide one synthesized recommendation, supporting evidence, trade-offs, uncertainties, and next steps.
8. **Local memory:** retain accepted runs, scenarios, model/role snapshots, outputs, execution events, timings, and terminal outcomes in SQLite across restarts. Persist custom agent changes.
9. **Run history:** provide a separate searchable, paginated history page with outcome filters and saved-run details.
10. **Analytics:** provide a separate page with time filters, workflow outcomes/activity, and agent-by-agent attempt counts, success/failure rates, average response duration, P95 duration, and cancellation/interruption breakdowns.

## Non-goals for the MVP

- Execute enterprise transactions or connect to production ERP/CRM/MES systems.
- Claim regulatory certification or provide cryptographic audit guarantees.
- Multi-user identity, permissions, or remote hosting.
- General digital twins beyond the initial inventory model, enterprise field evaluation, and distributed autonomy.

## Acceptance criteria

- Starts locally with documented commands and talks to the configured model server through its OpenAI-compatible API.
- Displays seven initial agent roles and supports adding a specialist through the UI.
- The user can submit a scenario and see streamed agent starts, completions, errors, and final synthesis.
- The final recommendation explicitly states approval status and does not imply an action was executed.
- Missing Agno, unreachable model endpoint, and empty model catalog produce actionable error messages.
- Backend/frontend responsibilities and setup are documented.
- The frontend runs through Vite on port 5173; the API runs independently on port 8000. HTML files are not the application entry workflow.
- Agent selections persist during a run, and cancellation keeps completed findings visible.
- Python dependencies use Poetry and a lockfile. Frontend dependencies use npm.

- Completed, failed, cancelled, and interrupted runs remain visible after backend restart. Runs interrupted by restart are clearly distinguished from model failures.
- Agent metrics retain historical role snapshots even after an agent is edited or removed.
- Analytics formulas and sample denominators are explicit; unavailable measurements display as unknown.
- Switching pages keeps an ongoing workflow running. Data remains in the configured local database.

## Scenario and review acceptance criteria

- Offer six editable scenario starters spanning supply chain, demand, operations, finance, governance, and logistics.
- No synthesis is generated before an enabled human-review checkpoint is submitted.
- Finalization uses existing findings and operator feedback; rerun requires guidance and creates a linked revision with the same saved role definitions.
- Pending review survives restart; duplicate submissions cannot generate two briefs. Model unavailability leaves review safely pending.
- Cancel, review later, resume from history, and review-disabled automatic synthesis have explicit UI states.

## Enterprise loop and research requirements

- Provide an Enterprise lab for creating inventory twins, ingesting typed observations, viewing versioned state and source evidence, and reviewing decisions.
- Deduplicate producer/event identities, reject stale/out-of-order observations, and create a decision atomically for each accepted state change. Include a demonstration feed and an external producer/API contract.
- Run two to seven selected Agno specialists over at most two proposal rounds. Share peer proposals, validate structured output/evidence, enforce hard budgets, retain conflicts/rejections, and escalate remaining disagreement or incomplete results.
- Simulate normal production, overtime, backup supply, and deferral under published one-day assumptions. Detect inventory drift when new observations arrive after simulation.
- Require explicit, scoped local approval for a simulated action. Retain reviewer attribution, rationale, overrides, expiry, state/case revisions, idempotent acknowledgment, and outcome reassessment. No real enterprise transaction is executed.
- Let the ordinary workspace consume a saved case as evidence. Policy-required review cannot be bypassed through its run request.
- Provide a Research page comparing centralized and orchestrated Agno decisions on six frozen synthetic cases, with repetitions, cancellation, persisted traces, published quality/oracle rules, runtime/policy metrics, and JSON export.
- Keep unmeasured trust/recovery/semantic explanation metrics explicit. Do not present synthetic scores as enterprise decision-quality validation.

See [EnterpriseLoop.md](EnterpriseLoop.md) for the operational workflow and verification boundary.
