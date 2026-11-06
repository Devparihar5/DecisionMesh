# DecisionMesh — Enterprise Loop and Research Evaluation

## What is implemented

The application now connects normalized enterprise observations, a versioned inventory twin, bounded Agno proposal exchange, explicit arbitration, operator approval, simulated execution, and outcome reassessment. **Enterprise lab** and **Research** are separate React pages. The existing decision workspace can consume a saved case as evidence.

This is one executable supply-chain domain implementation. Events may be supplied by external producers through HTTP. The included producer/feed generates demonstration observations; no ERP account is connected. The action adapter updates the local twin and never sends supplier orders, payments, or physical commands. Reviewer names provide local attribution rather than authenticated organizational authority.

## Try the complete loop

1. Start the API and React frontend with the existing README commands.
2. Open **Enterprise lab** and expand **Create an inventory twin**. The defaults illustrate inventory, demand, daily production capacity, alternate supply, costs, and remaining budget. Entity IDs are stable lowercase identifiers.
3. Send **Supplier disruption**, **Demand surge**, or an inventory observation. Each accepted observation creates a new state version and a new decision case. The continuous demonstration feed emits an observation every five seconds while enabled on this page; the external HTTP endpoint remains available independently of the browser.
4. Stop the demonstration feed before reviewing a stable decision. The initial proposals are labeled **rule-based**. Select two to seven specialists and a model, then choose **Run agent negotiation** for actual Agno reasoning. This job continues when navigating to another page.
5. Inspect peer proposals, evidence IDs, conflicts, arbitration rationale, and rejected alternatives. Compare normal production, overtime, backup supply, and deferral in the twin table.
6. Choose an action, enter reviewer attribution and a reason, and approve its local simulation. Execute the approved action using the separate button. Hard budget violations cannot be approved. A changed state, changed decision revision, consumed approval, or expired approval prevents execution.
7. Inspect the acknowledgment and open the outcome reassessment. Inventory, backlog, and remaining budget have changed; the feedback case refers to the prior decision. Incoming inventory observations after simulation display drift from the predicted inventory.
8. Use **Open evidence in decision workspace** for an executive brief. The backend attaches the normalized state, candidates, evidence, and latest proposals. A case requiring review forces the existing human checkpoint even if an API client requests automatic synthesis. Brief finalization does not approve an action.

## Event ingestion contract

`POST /api/enterprise/events` accepts an object with:

| Field | Meaning |
| --- | --- |
| `event_id` | Producer's stable event identifier |
| `source` | Producer/source name |
| `entity_id` | Existing inventory entity |
| `occurred_at` | ISO-8601 observation time with timezone |
| `changes` | Nonempty subset of inventory, demand, capacity, backup capacity, unit cost, backup unit cost, and budget |
| `description` | Optional context, maximum 1,000 characters |

Use **Fill an example** in the UI for a current timestamp and editable JSON. The producer contract is independent of SSE; SSE continues to carry advisory workflow progress. Enterprise lab polls committed snapshots and job progress.

The receipt distinguishes `accepted`, `rejected`, and an already-recorded receipt with `duplicate: true`. Retrying the exact same source/event payload does not change state. Reusing that identity with different content returns 409. Stale observations older than 24 hours, times more than 60 seconds ahead, and observations no newer than the entity's last observation are rejected and retained in the event ledger. Unknown entities return 404; invalid schemas return 422. For a rejected event, inspect the receipt even when HTTP status is 200.

Accepted ingestion atomically saves the event, updated state, and decision case. A database transaction provides a consistent snapshot to the UI. The interface shows the most recent 50 cases, 100 events, and 50 executions per entity; older records remain in SQLite.

### External producer example

After creating `demo-warehouse`, this command works with the project's Poetry environment:

```bash
poetry run python scripts/ingest_event.py --entity demo-warehouse --source warehouse-observer --changes '{"demand":180,"capacity":40}'
```

For a finite observation stream, append `--count 6 --interval 5`. The script generates current UTC timestamps and unique event IDs. `--base-url` selects another API base. A real producer should use stable event IDs and resend the same payload for retries. PowerShell users can also use the JSON editor or `Invoke-RestMethod` with the same API contract.

## Twin model and arbitration

The domain model uses a one-day horizon and units of a single item:

- `hold`: normal production up to daily capacity and remaining demand.
- `overtime`: normal production plus up to 25% additional production capacity at 1.5 times unit cost.
- `backup`: normal production plus backup supply, bounded by backup capacity, at the supplied backup unit cost.
- `defer`: serve only from existing inventory and spend nothing on production.

All costs, served demand, shortages, and inventories are calculated in Python. The model does not invent quantities. Hard budget feasibility takes priority. Among feasible proposed actions, arbitration maximizes:

`utility = 100 × served / demand − 5 × cost / max(budget, 1)`

Zero demand is treated as full service. Lower cost breaks utility ties, followed by a stable action ordering. Differences in service/cost/policy outcomes create explicit pairwise conflicts; action names with equivalent outcomes do not create a conflict by themselves. Deferral is the fallback if no valid proposal is available, with mandatory operator escalation.

Agno specialists return validated JSON containing an action, rationale, and compact supplied evidence references, which are resolved to immutable source IDs. Proposal calls disable Markdown and place the JSON contract in system instructions; one explicit format repair is permitted per proposal and retained/counts as another model call. Invalid structured output, unsupported evidence, timeouts, and provider failures are recorded. A second round shares the first round's proposals and arbitration result, allowing agents to revise or defend their choices. A unanimous valid first round can finish without another call. After two rounds, remaining disagreement is escalated to the operator. New events during negotiation make the result stale and prevent it from replacing a newer decision.

Local policy requires review for unmet demand, spend above 500 currency units, differing agent outcomes, invalid/incomplete proposals, or deferral. Simulation execution always requires explicit approval, including cases below those thresholds. A reviewer can choose a different feasible action; the original recommendation, override indicator, and rationale are retained.

## Governed action boundary

Approvals bind the case ID, case revision, state version, candidate fingerprint, selected action, reviewer attribution, and expiry. The execution API accepts an approval ID and an idempotency key. It atomically checks eligibility, consumes the approval, updates the twin, saves an acknowledgment, and creates a feedback case. Repeating the same request/key returns the original receipt. Reusing a key for another approval/action returns 409; a case cannot execute twice.

The local adapter removes served demand, carries unmet demand as backlog, reduces the remaining budget, and increments the state version and simulated-step count. Production capacity is a reusable per-day capacity assumption. No real elapsed production or supplier delivery is being observed. External observations can subsequently reconcile the simulated state.

## Research evaluation

Open **Research**, choose a model and one to three repetitions, and run the benchmark. This triggers real model calls. There are six frozen inventory scenarios and two architectures:

- **Centralized:** one Agno analyst considers all objectives and proposes one action, with at most one format-repair call.
- **Orchestrated:** up to four saved specialist definitions exchange proposals over at most two rounds; deterministic policy/arbitration chooses among their proposals.

The preferred specialist roles are operations, finance, risk, and compliance; if roles have been removed, remaining specialists fill the available slots. At least two are required. Both variants receive the same state, candidate simulations, and evidence. Execution order alternates by scenario and repetition. Call budgets differ and are reported, so latency is not an equal-compute comparison.

The oracle enumerates all four candidate outcomes. Quality is the chosen utility divided by best feasible utility, clamped to 0–100. Equal optimal utility receives 100, including the zero-utility edge case. Hard policy violations or no valid proposal score zero. A multi-agent result can retain a valid decision despite partial call failures; those failures are reported independently.

Saved results include quality, optimal-choice rate, policy compliance, mean/P95 machine-phase duration, model-call count, conflict frequency, review-required rate, evidence-ID coverage, and provider/format failures. Machine-phase duration includes queueing and excludes operator waiting. Approximate quality confidence intervals are descriptive because repeated synthetic cases are not independent field observations. Recovery time, human trust, actual human intervention, and semantic explanation correctness are not measured or fabricated.

The JSON export retains the dataset/version/hash, selected model ID, frozen agent instructions, prompt-template/rule versions, exact proposal prompts, proposal traces, errors, simulated outcomes, repetitions, timing, and limitations. Server seed/default generation settings, hardware, and caching are uncontrolled. The orchestrated variant adds deterministic policy/arbitration, so any improvement cannot be attributed solely to agent reasoning. These results evaluate the published synthetic task rather than general enterprise decision quality.

Jobs persist progress and completed trials, continue across page navigation, and can be cancelled. At most two research jobs run at once; only one benchmark is admitted at a time and only one negotiation per case. All model work shares the existing single-call semaphore. Graceful shutdown cancels jobs; abandoned jobs are marked interrupted on restart. Active generation is not automatically resumed. Job lists prioritize active jobs and omit detailed traces; individual job reads/exports retain them.

## Modules and APIs

| Area | Modules |
| --- | --- |
| Contracts | `backend/app/schemas/enterprise.py` |
| Pure simulation/arbitration | `backend/app/orchestration/twin.py`, `negotiation.py` |
| Local action adapter | `backend/app/actions/simulator.py` |
| Ingestion/decision loop | `backend/app/services/enterprise.py` |
| Agent jobs/evaluation | `backend/app/services/research_jobs.py`, `evaluation.py`, `benchmark_cases.json` |
| Transactions/storage | `backend/app/storage/enterprise.py`, `enterprise_schema.py` |
| HTTP | `backend/app/api/enterprise.py`, `research.py` |
| React pages | `frontend/src/pages/EnterprisePage.tsx`, `ResearchPage.tsx` |
| Frontend contracts/client | `frontend/src/types/enterprise.ts`, `services/enterprise.ts` |

The SQLite schema advances from version 2 to 3 using additive tables; existing run/review records remain in their original tables. Continue using one API process per database.

| Method / path | Purpose |
| --- | --- |
| `GET/POST /api/enterprise/entities` | List/create inventory twins |
| `GET /api/enterprise/entities/{id}` | Consistent state, recent cases, event ledger, and action receipts |
| `POST /api/enterprise/events` | Normalize an external observation and trigger a decision |
| `GET /api/enterprise/cases/{id}` | Saved versioned case with alternatives and negotiation |
| `POST /api/enterprise/cases/{id}/negotiate` | Start a bounded Agno negotiation job |
| `POST /api/enterprise/cases/{id}/approvals` | Approve one feasible simulated action |
| `POST /api/enterprise/cases/{id}/execute` | Idempotently apply an approved action and save feedback |
| `GET /api/research/dataset` | Synthetic benchmark corpus/version |
| `GET /api/research/jobs?kind=benchmark` | Recent job summaries (`negotiation` is also supported) |
| `GET /api/research/jobs/{id}` | Persisted job progress and results |
| `POST /api/research/jobs/{id}/cancel` | Cancel a local research job |
| `GET /api/research/jobs/{id}/export` | Download the full JSON experiment/negotiation record |
| `POST /api/research/benchmarks` | Start a controlled live-model comparison |

## Verification status

The production build, 50 backend tests, and 5 frontend protocol/format tests pass. Live Chrome checks exercised the enterprise loop, real seven-role workflow, feedback rerun/history recovery, mobile layouts, cancellation, and the complete 12-trial system-model benchmark. See [Testing.md](Testing.md) for evidence, fixes, reproduction commands, and limitations; remaining research/production work is in [Tasks.md](Tasks.md).
