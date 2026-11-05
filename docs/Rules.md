# DecisionMesh — Project Rules

Use **DecisionMesh** for product branding. Preserve domain names such as Orchestrator and orchestration.

## Implementation standards

- Keep backend Python code under `backend/`; keep browser application code under `frontend/`.
- Manage Python dependencies and the virtual environment with Poetry (`pyproject.toml` and `poetry.lock`); do not add a `requirements.txt`.
- keep all python imports on top of the file, instead of with in the function
- Keep SQLite operations in `backend/app/storage/` and metric calculations in the analytics service. Persist run events before emitting them to the UI; retain cancellation and interruption outcomes. Do not commit runtime databases.
- Keep API routes thin. Put agent construction, orchestration, and model transport in their own modules.
- Use type hints and Pydantic request/response schemas at API boundaries.
- Keep provider URLs and credentials in environment configuration; never commit real secrets.
- Use `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL` as the model configuration names unless an explicit migration is documented.
- Define event types and payload shapes in one place. Treat SSE as a versioned frontend/backend contract.
- Keep agent instructions focused on a role; include uncertainty and prohibit claiming external actions were executed.
- Handle provider and per-agent errors as visible run events; do not silently discard partial results.
- Keep human approval distinct from a model's opinion. Do not execute consequential actions in the MVP.
- Make agent IDs stable, lowercase snake_case values. Validate names and instructions before accepting a new agent.

## Frontend standards

- Use React and TypeScript under `frontend/src/`, with Vite as the development/build tool. `frontend/public/` is for assets only.
- Render UI through React state and props. Do not recreate the interface with imperative DOM mutation or inline HTML scripts.
- Keep run lifecycle logic in hooks, HTTP/SSE logic in services, and page composition separate from reusable components.
- Keep API calls in the service layer and reusable visual pieces in components.
- Provide loading, empty, error, success, and approval-required states.
- Support keyboard navigation, visible focus, semantic controls, and reduced motion.
- Do not communicate state through color alone.
- Do not display secrets or full environment variables in the UI.

## Repository and documentation

- Keep the six project documents in `docs/`: `Architecture.md`, `Design.md`, `Memory.md`, `PRD.md`, `Rules.md`, and `Tasks.md`.
- Update `Memory.md` when implementation decisions or important state changes.
- Update `Tasks.md` as work is completed or blockers are discovered.
- Keep the README focused on setup and common operation; link to the deeper project docs.
- Keep generated build output, dependency caches, and runtime data out of source control.
- Commit Poetry and npm lockfiles when generated. Validate backend behavior and TypeScript/build output when the required tools/dependencies are available; record any blocked check accurately.

## Safety and data handling

- The application binds to loopback by default for local development.
- Treat scenarios and model responses as potentially sensitive; avoid logging their full contents by default.
- Clearly identify model-generated content and unresolved uncertainty.
- Any future action execution, external integration, or production deployment requires explicit authorization controls and an auditable approval flow.
