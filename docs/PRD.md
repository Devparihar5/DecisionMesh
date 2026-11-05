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
6. **Governance:** communicate that output is advisory; surface whether a human approval is required.
7. **Decision brief:** provide one synthesized recommendation, supporting evidence, trade-offs, uncertainties, and next steps.
8. **Local memory:** retain accepted runs, scenarios, model/role snapshots, outputs, execution events, timings, and terminal outcomes in SQLite across restarts. Persist custom agent changes.
9. **Run history:** provide a separate searchable, paginated history page with outcome filters and saved-run details.
10. **Analytics:** provide a separate page with time filters, workflow outcomes/activity, and agent-by-agent attempt counts, success/failure rates, average response duration, P95 duration, and cancellation/interruption breakdowns.

## Non-goals for the MVP

- Execute enterprise transactions or connect to production ERP/CRM/MES systems.
- Claim regulatory certification or provide cryptographic audit guarantees.
- Multi-user identity, permissions, or remote hosting.
- Digital-twin simulation or durable benchmark corpus (planned follow-up areas).

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
