# DecisionMesh — Design

## Product feel

Build a calm, high-signal decision operations workspace. It should feel precise and trustworthy: the operator can see which agents are working, what evidence they returned, where uncertainty remains, and whether a human decision is required.

Implement the interface with React components and TypeScript. Share panel/status/control patterns across the workspace. Keep design tokens in `frontend/src/styles/global.css` and derive the graph, findings, and log from run events through React state.

## Visual system

- Canvas: deep ink `#0B0E14`; elevated surfaces `#111722` and `#171F2C`.
- Primary text: `#F2F5FA`; secondary text: `#9AA7B8`; quiet borders: `#263142`.
- Accent: per-agent colors, with restrained electric blue `#78A9FF` for primary actions.
- Status: green for complete, amber for waiting/approval, red for failure, muted gray for idle.
- Typography: system sans for interface text; monospace for model IDs, timings, and event metadata. Use local system fonts rather than requesting remote font assets.
- Use a consistent 8 px spacing rhythm, rounded 10–14 px panels, and clear focus rings.

## Main workspace

1. **Header:** product name, local model connection state, selected model, and run status.
2. **Scenario composer:** clear prompt label, scenario text area, approval requirement toggle, and run button.
3. **Agent roster:** seven default agents with role, state, and selection controls; provide an add-agent action and specialist removal.
4. **Orchestration visualization:** live graph/timeline showing the scenario entering the coordinator, agents starting and finishing, findings flowing to oversight, and synthesis.
5. **Findings panel:** expandable per-agent result cards with run duration and clear error states.
6. **Decision brief:** recommendation, rationale, confidence/uncertainty, risks, next steps, and human approval status.

## Interaction rules

- Make idle, running, completed, failed, and awaiting-approval states distinct without relying on color alone.
- Stream updates as they occur; animate only active edges/nodes and respect reduced-motion preferences.
- Keep specialist selection visible and preserve the selected scenario when a run fails.
- Surface model endpoint failures with an actionable message (start the configured model server, check the endpoint, then refresh connection status).
- A run button is disabled until a valid scenario and at least one specialist are selected.
- Disable run submission when the model connection or agent runtime is unavailable. Lock model/team/scenario edits during a run and expose a Stop action.
- Preserve partial findings after cancellation or failure, and mark degraded results visibly.
- Never present an agent suggestion as an executed enterprise action.
- New-agent creation asks for name, role, and concise instructions; show validation inline.

## Responsive behavior and accessibility

Use a two-column desktop workspace (controls/agents beside run visualization/findings), collapsing to a single column on narrow screens. Preserve reading order. All controls need labels, keyboard access, visible focus, and sufficient contrast. Provide textual event updates alongside the visual graph.

## Local memory and analytics pages

Use a shared navigation bar for Workspace, Run History, and Analytics, preserving the active workspace during page changes. Match existing ink surfaces, blue accents, muted labels, panel spacing, and accessible focus states.

Run History uses a searchable/filterable run list next to saved details. Run cards expose outcome, model, time, and scenario excerpt. Details preserve the original scenario, instructions, findings, and event timeline. Keep partial, failed, cancelled, skipped, and interrupted outcomes distinct in text and color. Collapse findings for scanning, with synthesis expanded initially.

Analytics uses metric cards, an inspectable daily activity chart, and a sortable agent performance table. Selecting an agent reveals an outcome breakdown. Show unknown values as an em dash. Label UTC chart buckets and metric formulas. Reliability and latency describe execution; do not imply decision-quality scoring. Provide loading, empty, error/retry, and refresh states. Tables/charts scroll on narrow screens; cards collapse to two columns.

## Brand

Use **DecisionMesh** as the visible product name and **Multi-agent decision intelligence** as its descriptor. Use `decisionmesh` for package/file identifiers and `decisionmesh-frontend` for the npm package. Preserve domain terms such as Orchestrator and Live orchestration. The README's animated preview must show the real UI component and label illustrative replay data clearly.

## Scenario starters and review dialog

The composer offers six compact scenario buttons above the editable text area. Indicate the active preset, permit custom edits, and lock the scenario/team during generation or pending review. The review modal summarizes agent findings and asks for suggestions. Primary action: Generate final brief. Secondary action: Revise & rerun agents (guidance required). Review later dismisses the modal while keeping a visible resume banner; cancel closes the pending run. Pending history entries link back to the workspace checkpoint. Expose submitting, retryable provider error, awaiting-review, and revised states. Stack actions on small screens and preserve native dialog focus/keyboard behavior.

## Enterprise lab and research

Add navigation entries for Enterprise lab and Research, with horizontally scrollable navigation on narrow screens. Reuse dark surfaces, blue primary controls, green acknowledgments, amber policy/conflict notices, and existing typography. Domain-specific styles live in `frontend/src/styles/enterprise.css`.

Enterprise lab follows the decision loop in numbered panels: ingestion, proposal exchange/arbitration, candidate twin comparison/approval, outcome feedback, and event ledger. Distinguish rule-based seed proposals from actual Agno rounds. Show source IDs, state versions, stale decisions, policy blocks, and simulation assumptions in plain language. Candidate selection is separate from approval; execution names the approved action explicitly. Reviewer attribution must not imply authenticated authority. Acknowledgments say simulated.

Research separates benchmark configuration, saved results, and interpretation. Display paired architecture summaries, quality bars, comparable trial tables, provider/format failures, live job state, cancellation, and JSON export. Label the simulator-based oracle and unequal call counts. Preserve completed partial trials after cancellation/interruption. Tables scroll within panels on small screens; forms and proposal cards stack.
