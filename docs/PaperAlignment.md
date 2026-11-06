# DecisionMesh — Research Paper Alignment

Originally reviewed: 2026-11-05. The subsequent local enterprise implementation is summarized first; the original gap analysis is retained below as a baseline. Implementation does not establish empirical validity.

## Current implementation update

The five requested gaps now have a connected implementation for one local supply-chain domain. See [EnterpriseLoop.md](EnterpriseLoop.md) for setup, contracts, assumptions, and the complete module/API map.

| Previous gap | Implemented mechanism | Remaining research/production scope |
| --- | --- | --- |
| Negotiation and conflict resolution | [Bounded Agno rounds](../backend/app/services/research_jobs.py), [validated proposals and deterministic arbitration](../backend/app/orchestration/negotiation.py), evidence links, priority rules, rejected alternatives, and human escalation | Additional protocols, objectives/domains, distributed autonomy, and empirical conflict-resolution evaluation |
| Enterprise event ingestion | [Normalized HTTP ingestion](../backend/app/services/enterprise.py), [atomic receipt/state/case storage](../backend/app/storage/enterprise.py), deduplication, freshness/order checks, automatic reassessment, and an external producer CLI | Authenticated production source adapters and enterprise throughput/freshness validation |
| Digital twin and simulation | [Versioned inventory twin](../backend/app/orchestration/twin.py) with four candidate actions, calculated outcomes, state transitions, and inventory drift from new observations | Stochastic/multientity models, wider domains, live ERP synchronization, and calibrated simulation validity |
| Governed action and feedback | Scoped local approval, hard-budget enforcement, state/revision/expiry/fingerprint checks, idempotent [local action adapter](../backend/app/actions/simulator.py), acknowledgment, override records, and feedback reassessment | Authenticated organizational authority, real action adapters, and real-world outcome validation |
| Research evaluation | [Six-case corpus](../backend/app/services/benchmark_cases.json), [centralized/orchestrated comparison](../backend/app/services/evaluation.py), published simulation quality/oracle rubric, repetitions, runtime/policy/conflict/evidence metrics, and persisted JSON exports | Live trials, measured recovery/trust/intervention, semantic explanation assessment, equal-compute variants, and enterprise field evidence |

The React **Enterprise lab** and **Research** pages expose these features. Saved enterprise evidence can also feed the existing advisory workspace, where required review is enforced. The full local loop is event → state → proposals → arbitration → simulation → scoped approval → simulated action → feedback case.

Current verification: the production build, 50 backend tests, and 5 frontend protocol/format tests pass. The subsequent live Chrome follow-up completed the enterprise loop, seven-role workflow, review/rerun/reload flows, mobile layouts, cancellation, and a 12-trial system-model benchmark with saved results/exports. See [Testing.md](Testing.md). These local checks do not establish enterprise field validity.

The project remains a local research prototype with partial coverage of the paper's broader enterprise architecture. It is not a complete distributed enterprise implementation or a reproduction of empirical paper results.

---

## Original baseline audit (before the enterprise extension)

The following sections describe the pre-extension source. Statements about missing functionality below are historical; the current status is in the table above and [Tasks.md](Tasks.md).

### Baseline assessment

**DecisionMesh is a partially aligned MVP inspired by the paper.** It implements role-based analysis, an explicit coordinator, a durable human-review checkpoint, local execution records, and runtime analytics. It does not yet implement the paper's broader architecture for live enterprise events, negotiation, digital-twin coordination, and governed action execution.

The [reference paper](Multi-agent_orchestration_architectures_for_real-t.pdf), *Multi-agent orchestration architectures for real-time enterprise decision intelligence systems* by Swaroop Suresh Borukar, is a literature review and conceptual architecture. It does not supply a single executable algorithm, fixed agent count, required agent framework, or reproducible software implementation. Seven roles, Agno, Python, React, and SQLite are project choices. Figure 3 uses qualitative comparative scores; those scores are not measured performance targets for this application. A percentage of overall compliance would imply precision the paper does not provide.

The closest architectural interpretation of the current application is a **central coordinator with specialist LLM roles and optional human supervision**. The human-governed hybrid discussed in Figure 3 is the closest conceptual fit; distributed enterprise autonomy and digital-twin coordination remain absent. This classification is our interpretation of the code.

## How to read the mapping

- **Implemented for the MVP:** a concrete mechanism exists, with the local scope stated.
- **Partial:** a narrower mechanism exists, but material aspects of the paper's concept are missing.
- **Missing:** no corresponding operational mechanism was found in the reviewed application modules.

Paper references below include both the PDF page number and the printed journal page. Future Directions are research priorities, not mandatory specifications for every MVP.

## Architecture mapping

| Paper concept and location | Status | Current implementation and evidence | Gap |
| --- | --- | --- | --- |
| Specialized sensing, analytical, policy/risk, and action roles; Figure 1, PDF p. 5 / journal p. 180 | Partial | [Seven starter definitions](../backend/app/agents/defaults.json) cover event analysis, risk, operations, finance, compliance, oversight, and synthesis. [The factory](../backend/app/agents/factory.py) creates real Agno agents. | Event analysis reads user text; no sensor/enterprise ingestion or action agent executes anything. Roles share the selected model and have no enterprise tools. |
| Orchestration as a separate architectural layer; Section 3 and Figure 1, PDF pp. 4–5 / journal pp. 179–180 | Implemented for the MVP | [Coordinator](../backend/app/orchestration/coordinator.py) controls analysis, review, and synthesis; [run service](../backend/app/services/runs.py) handles durability and revisions; HTTP transport is separate. | The implemented orchestration is a fixed workflow. Dynamic task routing, priority scheduling, negotiation, and arbitration are not included in this status. |
| Inter-agent coordination, negotiation, conflict resolution, and priority rules; Figure 1 and Discussion, PDF pp. 5–7 / journal pp. 180–182 | Partial | Selected specialists assess the same scenario and operator guidance. Oversight and synthesis receive collected findings and failures. | Specialists do not exchange proposals or see one another's findings. No structured conflict detection, negotiation rounds, arbitration rules, or priority model exists. A synthesis paragraph is not evidence that a conflict was resolved. |
| Enterprise event streams and timely data pipelines; Sections 2–3 and Figure 1, PDF pp. 2–5 / journal pp. 177–180 | Missing | [Run input](../backend/app/schemas/runs.py) accepts one scenario submitted through [the run API](../backend/app/api/runs.py). | No enterprise source adapter, continuous input subscription, ingestion/normalization pipeline, event freshness, deduplication, or changing-world trigger. Browser SSE carries execution progress; it is not enterprise event ingestion. |
| Digital twin and shared operational state; Figure 1 and Future Directions, PDF pp. 5, 7–8 / journal pp. 180, 182–183 | Partial for shared context; digital twin missing | [Shared context](../backend/app/orchestration/coordinator.py) collects bounded reports. [SQLite storage](../backend/app/storage/database.py) retains run snapshots, events, and revisions. | No versioned domain-state model, synchronization with real entities, simulated transitions, what-if engine, or drift detection. Saved runs and six text presets do not constitute a digital twin. History is not automatically recalled into future prompts. |
| Human oversight and approval gates; Figure 1 and Future Directions, PDF pp. 5, 7–8 / journal pp. 180, 182–183 | Implemented for the local review workflow; enterprise governance partial | [Review dialog](../frontend/src/components/ReviewDialog.tsx), [review contract](../backend/app/schemas/reviews.py), and [review persistence](../backend/app/storage/runs.py) support finalize, feedback-based rerun, review later, and cancellation. Pending checkpoints survive restart and duplicate submissions are rejected atomically. | Review is operator-selectable. No authenticated decision owner, role-based authority, mandatory risk/policy-triggered escalation, or approval to execute a specific external action. The AI oversight assessment is separate from the human choice. |
| Audit, explanation, rejected alternatives, and accountability; Discussion/Future Directions, PDF pp. 6–8 / journal pp. 181–183 | Partial | [Run repository](../backend/app/storage/runs.py) saves role/instruction snapshots, findings, events, review choices, feedback, and parent-child links. Synthesis is prompted for rationale, uncertainty, and rejected alternatives. | No structured evidence-to-claim links, proposal/alternative records, negotiation transcript, arbitration rationale, complete constructed-prompt/request provenance, or tamper-resistant audit mechanism. Explanation content is requested from the model rather than validated. |
| Governed enterprise action and execution feedback; Section 3/Figure 1 and Conclusion, PDF pp. 4–5, 8 / journal pp. 179–180, 183 | Missing by MVP scope | Agent instructions explicitly limit outputs to recommendations. The final brief suggests owners and next steps. | No action tools, authorization boundary for execution, idempotent dispatch, execution acknowledgments, measured outcomes, or feedback loop from the enterprise. Finalizing a brief is not executing or authorizing an enterprise transaction. |
| Adaptability, resilience, and real-time operation; Discussion, PDF pp. 6–7 / journal pp. 181–182 | Partial | [Agno runner](../backend/app/agents/factory.py) bounds concurrency and timeouts; [coordinator](../backend/app/orchestration/coordinator.py) reports partial failures; [SSE transport](../backend/app/api/runs.py) sends heartbeats. Storage retains cancellations and marks interrupted generations on startup. | One process and sequential model calls; no decision deadline, freshness budget, priority queue, automatic active-run resume/replay, distributed failover, or measured recovery objective. Interactive updates alone do not demonstrate low-latency enterprise performance. |
| Interoperability and gradual enterprise adoption; Future Directions, PDF p. 8 / journal p. 183 | Partial | Provider-neutral OpenAI-compatible model settings and a modular API/backend permit different model servers. | Model-provider compatibility is only one integration surface. ERP, MES, CRM, SCM, cloud/edge adapters and enterprise event/action contracts are absent. |
| Joint latency, quality, conflict, recovery, explanation, compliance, and intervention metrics; Future Directions, PDF p. 7 / journal p. 182 | Partial | [Analytics service](../backend/app/services/analytics.py) reports run outcomes/activity and per-agent attempt success, average duration, and P95 duration. | No evaluated decision quality, measured conflict rate, recovery time, explanation completeness, policy pass rate, human trust, or intervention-rate metric. Completed workflow duration includes human waiting; separate machine and review latency is needed for meaningful comparisons. |
| Comparative architecture evaluation and enterprise-scale evidence; Discussion/Future Directions, PDF pp. 7–8 / journal pp. 182–183 | Missing | Existing tests check local behavior; scenario presets make manual demonstrations easier. | No common benchmark dataset with expected outcomes/rubrics, architecture variants under identical conditions, controlled repeated trials, or enterprise load/field evaluation. |

## Code-level distinctions that affect claims

1. **Agent roles versus autonomous distributed agents.** Each call constructs an Agno agent with its role instructions, uses the selected model, and returns a text assessment. Model calls share a semaphore of one. The Orchestrator node represents Python coordination logic rather than an additional reasoning agent. This is a valid local design, but it does not demonstrate independent distributed workers or peer negotiation.
2. **Information flow.** In `Coordinator.events`, non-core specialists receive the scenario and operator guidance. They do not receive the event analyst's extracted facts or other specialists' findings. Collected reports flow to oversight and synthesis. Consequently, even Figure 1's perception-to-analytics stage is only approximated by the current role names.
3. **Policy advice versus enforced policy.** Compliance instructions ask the model to flag concerns. The review preference determines whether oversight and the checkpoint run; compliance findings do not deterministically force review or block a decision. Completing a run does not establish that the recommendation satisfies policy.
4. **Execution success versus useful decisions.** Agent success measures a completed response rather than correctness. Workflow completion can include failed specialist perspectives and is marked partial. These are reliability metrics; no decision-quality claim follows from them.
5. **Resumable review versus resumable generation.** A saved human checkpoint can continue after restart. An in-progress model workflow is marked interrupted rather than resuming computation. SQLite history and SSE sequence IDs do not yet provide browser reconnect/replay or durable job execution.

## Original proposed order for closer alignment

This was the proposed implementation order before the extension. Local implementations are now described above; broader production and evaluation work remains in the current tracker.

| Priority | Work | Reviewable acceptance condition |
| --- | --- | --- |
| 1 | Structured observations, proposals, alternatives, and conflicts | Persist typed records with source references, assumptions, proposed actions, and constraints. Detect a supplied operations-versus-finance conflict and retain both proposals, the resolution rule, and the rejected option's reason. Feed normalized observations into downstream analysis. |
| 2 | Explicit arbitration and policy escalation | Add bounded negotiation/arbitration with deterministic priority rules and unresolved-conflict escalation. A configured policy violation forces review even when the operator requested automatic synthesis. Persist the rules and reasons used. |
| 3 | Event ingestion and versioned shared state | Add one simulated enterprise feed or authorized adapter with timestamps, IDs, deduplication, and entity versions. New relevant state can trigger reassessment; the saved decision identifies the state version and event evidence used. Define a domain latency/freshness target before measuring it. |
| 4 | Small domain digital twin | Start with one supply-chain inventory/capacity state model. Simulate the same disruption under at least two candidate actions; retain the assumptions, state transitions, and outcome differences separately from LLM prose. |
| 5 | Governed action and outcome feedback | First implement a simulated action adapter. Require authority for the specific proposed action, dispatch idempotently, retain the acknowledgment/outcome, and use the resulting state for reassessment. Real enterprise adapters require the corresponding authorization model. |
| 6 | Reproducible evaluation | Run centralized and current orchestrated baselines on the same saved scenarios/model configuration with explicit quality rubrics and repeated trials. Measure machine time separately from human wait, plus conflict/resolution, recovery, explanation, policy, and intervention metrics. Record sample sizes and uncertainty. |

Authenticated decision ownership, durable jobs/reconnect, and enterprise scale validation should grow alongside the relevant stages. No hard real-time or enterprise performance claim should precede measurements against a defined domain target.

## Verification boundary and project description

The previously recorded checks in [Tasks.md](Tasks.md) cover 33 backend tests, 5 frontend checks, a successful production build, and targeted browser flows with fixture responses. The test sources include review gating, revisions, persistence, partial failure, cancellation, and runtime analytics. Those checks support local workflow behavior; they do not establish research-level decision quality or enterprise-scale validity. A full seven-role run against the configured live model remains an open verification task.

Suggested description after the local extension:

> DecisionMesh is a local multi-agent decision workbench with normalized enterprise observations, bounded negotiation, inventory digital-twin simulation, human-governed simulated actions, outcome feedback, and reproducible synthetic model evaluation. Production enterprise integration and empirical field validation remain future work.
